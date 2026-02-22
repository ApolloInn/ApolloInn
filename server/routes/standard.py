"""
Standard OpenAI Compatible Routes — 纯净的 OpenAI 兼容端点。

与 proxy.py 共享认证、配额、Kiro payload 构建、流式解析等核心逻辑，
但剥离所有 Cursor 特化行为：
- 不做 reasoning_content → <think> 转换（可通过 reasoning_mode 配置）
- 不做 anti-lazy stop
- 不做模型拒绝重试 / 空流重试
- 不注入 heartbeat SSE 注释
- usage 中不返回 credits_used
"""

import json
import time
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from core.converters_openai import build_kiro_payload
from core.streaming_openai import stream_kiro_to_openai, collect_stream_response
from core.auth import KiroAuthManager, AuthType
from core.http_client import KiroHttpClient
from core.kiro_errors import enhance_kiro_error
from core.utils import generate_conversation_id
from core.models_openai import ChatCompletionRequest, ChatMessage
from core.cache import ModelInfoCache

standard_router = APIRouter(tags=["standard"])


# ---------------------------------------------------------------------------
# Helpers (duplicated from proxy.py to avoid touching it)
# ---------------------------------------------------------------------------

def _extract_usertoken(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return auth


async def _validate_user(request: Request):
    usertoken = _extract_usertoken(request)
    if not usertoken:
        raise HTTPException(status_code=401, detail="Missing API key")
    user = await request.app.state.pool.validate_apikey(usertoken)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


# ---------------------------------------------------------------------------
# Reasoning mode processing
# ---------------------------------------------------------------------------

def _process_reasoning_streaming(chunk: str, reasoning_mode: str, state: dict) -> Optional[str]:
    """
    Process a single SSE chunk according to reasoning_mode.

    Returns the (possibly modified) chunk string, or None to skip it.
    """
    if not chunk.startswith("data: ") or chunk.strip() == "data: [DONE]":
        return chunk

    try:
        chunk_data = json.loads(chunk[6:])
    except (json.JSONDecodeError, KeyError):
        return chunk

    choices = chunk_data.get("choices", [])
    if not choices:
        # Strip credits_used from usage-only chunks
        _strip_credits(chunk_data)
        return f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

    delta = choices[0].get("delta", {})
    rc = delta.get("reasoning_content")
    modified = False

    if rc is not None:
        if reasoning_mode == "drop":
            # Remove reasoning_content entirely; if delta has nothing else, skip chunk
            del delta["reasoning_content"]
            if not delta.get("content") and "tool_calls" not in delta and "role" not in delta:
                return None
            modified = True
        elif reasoning_mode == "content":
            # Wrap in <think> tags inside content
            if state.get("thinking_first", True):
                delta["content"] = "<think>\n" + rc
                state["thinking_first"] = False
                state["thinking_sent"] = True
            else:
                delta["content"] = rc
            del delta["reasoning_content"]
            modified = True
        # reasoning_mode == "reasoning_content": pass through as-is

    elif reasoning_mode == "content" and delta.get("content") and state.get("thinking_sent") and not state.get("thinking_closed"):
        delta["content"] = "\n</think>\n" + delta["content"]
        state["thinking_closed"] = True
        modified = True

    _strip_credits(chunk_data)
    modified = True  # always re-serialize to strip credits_used

    return f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"


def _process_reasoning_nonstreaming(response: dict, reasoning_mode: str) -> dict:
    """Process reasoning_content in a non-streaming response."""
    for choice in response.get("choices", []):
        msg = choice.get("message", {})
        rc = msg.get("reasoning_content", "")
        if rc:
            if reasoning_mode == "drop":
                del msg["reasoning_content"]
            elif reasoning_mode == "content":
                original = msg.get("content", "")
                msg["content"] = f"<think>\n{rc}\n</think>\n{original}"
                del msg["reasoning_content"]
            # "reasoning_content" mode: leave as-is

    # Strip credits_used
    usage = response.get("usage", {})
    usage.pop("credits_used", None)
    return response


def _strip_credits(chunk_data: dict):
    """Remove non-standard credits_used from usage."""
    usage = chunk_data.get("usage")
    if usage and "credits_used" in usage:
        del usage["credits_used"]


# ---------------------------------------------------------------------------
# Models endpoint
# ---------------------------------------------------------------------------

@standard_router.get("/standard/v1/models")
async def list_models(request: Request):
    """Standard model list — no -thinking variants."""
    await _validate_user(request)
    model_cache: ModelInfoCache = request.app.state.model_cache
    now = int(time.time())

    models = []
    for model_id in model_cache.get_all_model_ids():
        models.append({"id": model_id, "object": "model", "created": now, "owned_by": "kiro"})

    return {"object": "list", "data": models}


# ---------------------------------------------------------------------------
# Chat completions — the core handler
# ---------------------------------------------------------------------------

async def handle_standard_completions(request: Request):
    """
    Standard OpenAI-compatible chat completions handler.

    Called from:
    - POST /standard/v1/chat/completions  (dedicated route)
    - POST /v1/chat/completions with X-Apollo-Mode: standard  (header dispatch)
    """
    user = await _validate_user(request)
    pool = request.app.state.pool
    bridge = request.app.state.bridge
    model_cache: ModelInfoCache = request.app.state.model_cache

    # ── Quota ──
    quota_error = await pool.check_quota(user["id"])
    if quota_error:
        raise HTTPException(status_code=429, detail=f"Quota exceeded: {quota_error}")

    token_entry = await pool.get_user_token_entry(user)
    if not token_entry:
        raise HTTPException(status_code=503, detail="No available tokens in pool")

    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Extract non-standard params before validation
    reasoning_mode = raw_body.pop("reasoning_mode", "drop")
    if reasoning_mode not in ("drop", "content", "reasoning_content"):
        reasoning_mode = "drop"
    user_compress = raw_body.pop("context_compression", True)
    enable_compression = bool(user_compress)

    try:
        request_data = ChatCompletionRequest(**raw_body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    # ── Model resolution (combo) ──
    original_model = request_data.model
    request_data.model = request_data.model.lower()
    resolved_model = await pool.resolve_model(request_data.model)
    if resolved_model != original_model:
        logger.info(f"[standard] Model resolved: {original_model} -> {resolved_model}")
        request_data.model = resolved_model

    logger.info(
        f"[standard][{user['name']}] model={request_data.model} stream={request_data.stream} "
        f"reasoning_mode={reasoning_mode} messages={len(request_data.messages)}"
    )

    auth_manager = bridge.get_or_create_manager(token_entry)

    # ── Context compression ──
    from core.config import CONTEXT_COMPRESSION, DEFAULT_MAX_INPUT_TOKENS

    if CONTEXT_COMPRESSION and enable_compression:
        from core.context_compression import compress_context

        raw_msgs = [msg.model_dump() for msg in request_data.messages]
        raw_tools = [tool.model_dump() for tool in request_data.tools] if request_data.tools else None
        context_window = min(
            model_cache.get_max_input_tokens(request_data.model) or DEFAULT_MAX_INPUT_TOKENS,
            DEFAULT_MAX_INPUT_TOKENS,
        )
        compressed_msgs, comp_stats = compress_context(raw_msgs, raw_tools, context_window)
        if comp_stats["level"] > 0:
            request_data.messages = [ChatMessage(**m) for m in compressed_msgs]
            logger.info(
                f"[standard][{user['name']}] Context compressed: "
                f"{comp_stats['original_tokens']//1000}K -> {comp_stats['final_tokens']//1000}K tokens"
            )

    # ── Build Kiro payload ──
    conversation_id = generate_conversation_id()
    profile_arn = ""
    if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
        profile_arn = auth_manager.profile_arn

    try:
        kiro_payload = build_kiro_payload(request_data, conversation_id, profile_arn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    url = f"{auth_manager.api_host}/generateAssistantResponse"

    messages_for_tokenizer = [msg.model_dump() for msg in request_data.messages]
    tools_for_tokenizer = (
        [tool.model_dump() for tool in request_data.tools] if request_data.tools else None
    )

    # ── Token rotation on 429/403/402 ──
    max_token_retries = 3
    for token_attempt in range(max_token_retries):
        if token_attempt > 0:
            new_token_entry = await pool.get_next_token()
            if new_token_entry and new_token_entry["id"] != token_entry["id"]:
                token_entry = new_token_entry
                auth_manager = bridge.get_or_create_manager(token_entry)
                logger.info(f"[standard][{user['name']}] Token rotation: attempt {token_attempt + 1}")
            else:
                import asyncio as _asyncio
                await _asyncio.sleep(1)
            url = f"{auth_manager.api_host}/generateAssistantResponse"
            profile_arn = ""
            if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
                profile_arn = auth_manager.profile_arn
            try:
                kiro_payload = build_kiro_payload(request_data, conversation_id, profile_arn)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        if request_data.stream:
            http_client = KiroHttpClient(auth_manager, shared_client=None)
        else:
            http_client = KiroHttpClient(auth_manager, shared_client=request.app.state.http_client)

        try:
            response = await http_client.request_with_retry("POST", url, kiro_payload, stream=True)

            # ── Fatal 403 → disable token ──
            if response.status_code == 403 and getattr(response, '_fatal_403', False):
                fatal_reason = getattr(response, '_fatal_reason', 'unknown')
                logger.error(f"[standard] Token {token_entry['id'][:8]} fatal 403: {fatal_reason}")
                try:
                    await pool.set_token_status(token_entry['id'], 'disabled', reason=fatal_reason)
                except Exception:
                    pass
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return JSONResponse(status_code=403, content={
                    "error": {"message": f"Token disabled: {fatal_reason}", "type": "token_fatal_error", "code": 403}
                })

            # ── 402 quota ──
            if response.status_code == 402 and getattr(response, '_quota_402', False):
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return JSONResponse(status_code=402, content={
                    "error": {"message": "All tokens quota exhausted.", "type": "quota_exhausted", "code": 402}
                })

            if response.status_code in (429, 402, 403) and token_attempt < max_token_retries - 1:
                await http_client.close()
                logger.warning(f"[standard] Kiro API {response.status_code}, rotating token")
                continue

            if response.status_code != 200:
                try:
                    error_content = await response.aread()
                except Exception:
                    error_content = b"Unknown error"
                await http_client.close()
                error_text = error_content.decode("utf-8", errors="replace")
                logger.error(
                    f"[standard][{user['name']}] Kiro API {response.status_code}: {error_text[:500]} | "
                    f"model={request_data.model} messages={len(request_data.messages)} "
                    f"tools={len(request_data.tools) if request_data.tools else 0} "
                    f"stream={request_data.stream}"
                )
                error_message = error_text
                try:
                    error_json = json.loads(error_text)
                    error_info = enhance_kiro_error(error_json)
                    error_message = error_info.user_message
                except (json.JSONDecodeError, KeyError):
                    pass
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": {"message": error_message, "type": "kiro_api_error", "code": response.status_code}},
                )

            # ── Streaming ──
            if request_data.stream:
                async def stream_wrapper(
                    _http_client=http_client,
                    _response=response,
                    _reasoning_mode=reasoning_mode,
                ):
                    accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                    reasoning_state = {"thinking_first": True, "thinking_sent": False, "thinking_closed": False}
                    try:
                        async for chunk in stream_kiro_to_openai(
                            _http_client.client, _response, request_data.model,
                            model_cache, auth_manager,
                            request_messages=messages_for_tokenizer,
                            request_tools=tools_for_tokenizer,
                        ):
                            # Restore original model name
                            if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                                try:
                                    cd = json.loads(chunk[6:])
                                    if cd.get("model") != original_model:
                                        cd["model"] = original_model
                                    if "usage" in cd:
                                        accumulated_usage["prompt_tokens"] = cd["usage"].get("prompt_tokens", 0)
                                        accumulated_usage["completion_tokens"] = cd["usage"].get("completion_tokens", 0)
                                    chunk = f"data: {json.dumps(cd, ensure_ascii=False)}\n\n"
                                except (json.JSONDecodeError, KeyError):
                                    pass

                            processed = _process_reasoning_streaming(chunk, _reasoning_mode, reasoning_state)
                            if processed is not None:
                                yield processed
                    except GeneratorExit:
                        logger.debug("[standard] Client disconnected")
                    except Exception as e:
                        logger.error(f"[standard] Streaming error: {type(e).__name__}: {e}")
                        raise
                    finally:
                        try:
                            await _http_client.close()
                        except Exception:
                            pass
                        pool.release_token(token_entry["id"])
                        try:
                            await pool.mark_token_used(token_entry["id"])
                            await pool.mark_user_used(user["id"])
                            p = accumulated_usage["prompt_tokens"]
                            c = accumulated_usage["completion_tokens"]
                            if p or c:
                                await pool.record_usage(user["id"], request_data.model, p, c, token_entry["id"])
                        except Exception:
                            pass

                return StreamingResponse(
                    stream_wrapper(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "X-Accel-Buffering": "no",
                        "Connection": "keep-alive",
                    },
                )

            # ── Non-streaming ──
            else:
                openai_response = await collect_stream_response(
                    http_client.client, response, request_data.model,
                    model_cache, auth_manager,
                    request_messages=messages_for_tokenizer,
                    request_tools=tools_for_tokenizer,
                )
                await http_client.close()

                openai_response["model"] = original_model
                openai_response = _process_reasoning_nonstreaming(openai_response, reasoning_mode)

                pool.release_token(token_entry["id"])
                await pool.mark_token_used(token_entry["id"])
                await pool.mark_user_used(user["id"])
                try:
                    u = openai_response.get("usage", {})
                    p, c = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
                    if p or c:
                        await pool.record_usage(user["id"], request_data.model, p, c, token_entry["id"])
                except Exception:
                    pass

                return JSONResponse(content=openai_response)

        except HTTPException:
            await http_client.close()
            pool.release_token(token_entry["id"])
            raise
        except Exception as e:
            await http_client.close()
            pool.release_token(token_entry["id"])
            logger.error(f"[standard] Internal error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@standard_router.post("/standard/v1/chat/completions")
async def standard_chat_completions(request: Request):
    """Standard OpenAI-compatible chat completions (dedicated route)."""
    return await handle_standard_completions(request)


