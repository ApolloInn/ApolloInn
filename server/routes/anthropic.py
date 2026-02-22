"""
Anthropic Routes — 原生 Anthropic Messages API 兼容接口。

提供 /v1/messages 端点，接受 Anthropic 原生格式请求，
复用 Kiro Gateway 完整转换、流式、重试管线。
支持 Claude Code CLI 等 Anthropic SDK 客户端直连。

功能对齐 OpenAI 路由：
- 上下文压缩
- 截断恢复
- 429/403 Token 轮换
- 空流重试 / 模型拒绝重试
- Heartbeat 保活
- Anti-lazy stop
- Debug logging
"""

import json
import time

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from core.converters_anthropic import build_kiro_payload_from_anthropic
from core.streaming_anthropic import stream_kiro_to_anthropic, collect_anthropic_response
from core.auth import AuthType
from core.http_client import KiroHttpClient
from core.kiro_errors import enhance_kiro_error
from core.utils import generate_conversation_id

try:
    from core.debug_logger import debug_logger
except Exception:
    debug_logger = None

anthropic_router = APIRouter(tags=["anthropic"])


def _extract_apikey(request: Request) -> str:
    """Extract API key from x-api-key, x-auth-token, or Authorization Bearer."""
    key = request.headers.get("x-api-key", "")
    if key:
        return key
    key = request.headers.get("x-auth-token", "")
    if key:
        return key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


async def _validate_user(request: Request):
    apikey = _extract_apikey(request)
    if not apikey:
        raise HTTPException(status_code=401, detail={"type": "authentication_error", "message": "Missing API key"})
    user = await request.app.state.pool.validate_apikey(apikey)
    if not user:
        raise HTTPException(status_code=401, detail={"type": "authentication_error", "message": "Invalid API key"})
    return user


def _anthropic_error(status_code: int, error_type: str, message: str):
    """Return Anthropic-format error response."""
    return JSONResponse(
        status_code=status_code,
        content={"type": "error", "error": {"type": error_type, "message": message}},
    )


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@anthropic_router.post("/v1/messages")
async def messages(request: Request):
    """
    Anthropic Messages API 兼容端点。

    接受 Anthropic 原生格式，转发到 Kiro API，返回 Anthropic 格式响应。
    支持 stream=true (SSE) 和 stream=false (JSON)。
    完整管线：压缩 → 截断恢复 → 重试 → heartbeat → anti-lazy。
    """
    user = await _validate_user(request)
    pool = request.app.state.pool
    bridge = request.app.state.bridge
    model_cache = request.app.state.model_cache

    # ── 配额检查 ──
    quota_error = await pool.check_quota(user["id"])
    if quota_error:
        return _anthropic_error(429, "rate_limit_error", f"Quota exceeded: {quota_error}")

    token_entry = await pool.get_user_token_entry(user)
    if not token_entry:
        return _anthropic_error(503, "api_error", "No available tokens in pool")

    try:
        raw_body = await request.json()
    except Exception:
        return _anthropic_error(400, "invalid_request_error", "Invalid JSON body")

    # Debug logging
    if debug_logger:
        debug_logger.prepare_new_request(username=user["name"])
        try:
            debug_logger.log_request_body(json.dumps(raw_body, ensure_ascii=False).encode('utf-8'))
        except Exception:
            pass

    # ── 模型解析 ──
    original_model = raw_body.get("model", "claude-sonnet-4").lower()
    resolved_model = await pool.resolve_model(original_model)
    if resolved_model != original_model:
        logger.info(f"Model resolved: {original_model} -> {resolved_model}")
        raw_body["model"] = resolved_model

    stream = raw_body.get("stream", False)
    max_tokens = raw_body.get("max_tokens", 8192)
    msg_count = len(raw_body.get("messages", []))
    has_tools = bool(raw_body.get("tools"))

    logger.info(
        f"[{user['name']}] [anthropic] model={raw_body['model']} stream={stream} "
        f"token={token_entry['id'][:8]}... messages={msg_count} tools={len(raw_body.get('tools', []))}"
    )

    auth_manager = bridge.get_or_create_manager(token_entry)

    # ── 上下文压缩 ──
    from core.config import CONTEXT_COMPRESSION, DEFAULT_MAX_INPUT_TOKENS

    if CONTEXT_COMPRESSION:
        from core.context_compression import compress_context
        from core.models_openai import ChatMessage

        # Convert Anthropic messages to a format compress_context can handle
        raw_msgs_for_compression = _anthropic_msgs_to_openai_like(raw_body.get("messages", []), raw_body.get("system"))
        raw_tools_for_compression = _anthropic_tools_to_openai_like(raw_body.get("tools"))
        context_window = min(
            model_cache.get_max_input_tokens(raw_body["model"]) or DEFAULT_MAX_INPUT_TOKENS,
            DEFAULT_MAX_INPUT_TOKENS,
        )

        compressed_msgs, comp_stats = compress_context(raw_msgs_for_compression, raw_tools_for_compression, context_window)

        if comp_stats["level"] > 0:
            # Convert compressed OpenAI-like messages back to Anthropic format
            raw_body["messages"], raw_body["system"] = _openai_like_msgs_to_anthropic(compressed_msgs)
            logger.info(
                f"[{user['name']}] [anthropic] Context compressed: {comp_stats['original_tokens']//1000}K -> "
                f"{comp_stats['final_tokens']//1000}K tokens (level {comp_stats['level']}, "
                f"saved {comp_stats['tokens_saved']//1000}K)"
            )

    # ── 构建 Kiro payload ──
    conversation_id = generate_conversation_id()
    profile_arn = ""
    if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
        profile_arn = auth_manager.profile_arn

    try:
        kiro_payload = build_kiro_payload_from_anthropic(raw_body, conversation_id, profile_arn)
    except ValueError as e:
        return _anthropic_error(400, "invalid_request_error", str(e))

    if debug_logger:
        try:
            debug_logger.log_kiro_request_body(json.dumps(kiro_payload, ensure_ascii=False).encode('utf-8'))
        except Exception:
            pass

    url = f"{auth_manager.api_host}/generateAssistantResponse"

    # Prepare messages/tools for tokenizer fallback
    messages_for_tokenizer = raw_body.get("messages", [])
    tools_for_tokenizer = raw_body.get("tools")

    # ── 429/403 Token Rotation ──
    max_token_retries = 3
    for token_attempt in range(max_token_retries):
        if token_attempt > 0:
            new_token_entry = await pool.get_next_token()
            if new_token_entry and new_token_entry["id"] != token_entry["id"]:
                token_entry = new_token_entry
                auth_manager = bridge.get_or_create_manager(token_entry)
                logger.info(f"[{user['name']}] [anthropic] Token rotation: {token_entry['id'][:8]}... (attempt {token_attempt + 1})")
            else:
                import asyncio as _asyncio
                await _asyncio.sleep(1)
            url = f"{auth_manager.api_host}/generateAssistantResponse"
            profile_arn = ""
            if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
                profile_arn = auth_manager.profile_arn
            try:
                kiro_payload = build_kiro_payload_from_anthropic(raw_body, conversation_id, profile_arn)
            except ValueError as e:
                return _anthropic_error(400, "invalid_request_error", str(e))

        http_client = KiroHttpClient(auth_manager, shared_client=None if stream else request.app.state.http_client)

        try:
            response = await http_client.request_with_retry("POST", url, kiro_payload, stream=True)

            # ── 致命 403 检测：自动禁用已封禁/失效的 token ──
            if response.status_code == 403 and getattr(response, '_fatal_403', False):
                fatal_reason = getattr(response, '_fatal_reason', 'unknown')
                logger.error(
                    f"[{user['name']}] [anthropic] Token {token_entry['id'][:8]} fatal 403: {fatal_reason}, "
                    f"auto-disabling token"
                )
                try:
                    await pool.set_token_status(token_entry['id'], 'disabled', reason=fatal_reason)
                except Exception as _e:
                    logger.error(f"Failed to disable token {token_entry['id'][:8]}: {_e}")
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return JSONResponse(
                    status_code=403,
                    content={"error": {"message": f"Token disabled: {fatal_reason}", "type": "token_fatal_error"}},
                )

            # ── 402 月度配额耗尽：自动轮换 token ──
            if response.status_code == 402 and getattr(response, '_quota_402', False):
                quota_reason = getattr(response, '_quota_reason', 'MONTHLY_REQUEST_COUNT')
                logger.warning(
                    f"[{user['name']}] [anthropic] Token {token_entry['id'][:8]} quota 402: {quota_reason}, "
                    f"rotating token (attempt {token_attempt + 1}/{max_token_retries})"
                )
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return _anthropic_error(402, "quota_exhausted", "All tokens have reached their monthly request limit. Please try again later or add new tokens.")

            if response.status_code in (429, 402, 403) and token_attempt < max_token_retries - 1:
                await http_client.close()
                logger.warning(f"[{user['name']}] [anthropic] Kiro API {response.status_code}, rotating token")
                continue

            if response.status_code != 200:
                try:
                    error_content = await response.aread()
                except Exception:
                    error_content = b"Unknown error"
                await http_client.close()
                error_text = error_content.decode("utf-8", errors="replace")
                error_message = error_text
                try:
                    error_json = json.loads(error_text)
                    error_info = enhance_kiro_error(error_json)
                    error_message = error_info.user_message
                except (json.JSONDecodeError, KeyError):
                    pass
                logger.warning(f"[anthropic] HTTP {response.status_code} - {error_message[:200]}")
                if response.status_code == 400:
                    try:
                        import os
                        dump_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_logs")
                        os.makedirs(dump_dir, exist_ok=True)
                        dump_file = os.path.join(dump_dir, f"400_anthropic_{int(time.time())}.json")
                        with open(dump_file, "w") as f:
                            json.dump({"kiro_payload": kiro_payload, "error": error_message}, f, indent=2, ensure_ascii=False)
                        logger.warning(f"[anthropic] 400 payload dumped to {dump_file}")
                    except Exception:
                        pass
                if debug_logger:
                    debug_logger.flush_on_error(response.status_code, error_message)
                return _anthropic_error(response.status_code, "api_error", error_message)

            if stream:
                return StreamingResponse(
                    _stream_wrapper(
                        http_client, response, raw_body, original_model,
                        model_cache, auth_manager, user, pool, token_entry,
                        url, kiro_payload, messages_for_tokenizer, tools_for_tokenizer,
                        max_tokens, has_tools,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "X-Accel-Buffering": "no",
                        "Connection": "keep-alive",
                    },
                )
            else:
                # ── Non-streaming ──
                result = await collect_anthropic_response(
                    http_client.client, response, raw_body["model"],
                    model_cache, auth_manager,
                    request_messages=messages_for_tokenizer,
                    request_tools=tools_for_tokenizer,
                    max_tokens=max_tokens,
                )
                await http_client.close()
                result["model"] = original_model
                pool.release_token(token_entry["id"])
                await pool.mark_token_used(token_entry["id"])
                await pool.mark_user_used(user["id"])
                try:
                    p_tok = result.get("usage", {}).get("input_tokens", 0)
                    c_tok = result.get("usage", {}).get("output_tokens", 0)
                    if p_tok or c_tok:
                        await pool.record_usage(user["id"], raw_body["model"], p_tok, c_tok, token_entry["id"])
                except Exception:
                    pass
                logger.info(f"[{user['name']}] [anthropic] Non-streaming completed")
                return JSONResponse(content=result)

        except HTTPException:
            await http_client.close()
            pool.release_token(token_entry["id"])
            raise
        except Exception as e:
            await http_client.close()
            pool.release_token(token_entry["id"])
            logger.error(f"[anthropic] Internal error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"type": "api_error", "message": f"Internal Server Error: {str(e)}"})


async def _stream_wrapper(
    http_client, response, raw_body, original_model,
    model_cache, auth_manager, user, pool, token_entry,
    url, kiro_payload, messages_for_tokenizer, tools_for_tokenizer,
    max_tokens, has_tools,
):
    """
    Anthropic 流式包装器 — 完整管线。

    功能：
    - Heartbeat 保活（15s 超时发 : heartbeat）
    - 空流重试
    - 模型拒绝重试（completion tokens 过少）
    - 上游断开重试
    - Anti-lazy stop（tool_use 场景）
    - Debug logging
    """
    import asyncio

    streaming_error = None
    client_disconnected = False
    accumulated_usage = {"input_tokens": 0, "output_tokens": 0}
    last_stop_reason = None
    has_tool_calls = False
    accumulated_text = ""
    heartbeat_count = 0
    chunk_count = 0

    REFUSAL_MAX_RETRIES = 2
    REFUSAL_TOKEN_THRESHOLD = 100
    cur_http_client = http_client
    cur_response = response

    try:
        for refusal_attempt in range(REFUSAL_MAX_RETRIES + 1):
            try:
                heartbeat_count = 0
                chunk_count = 0
                upstream = stream_kiro_to_anthropic(
                    cur_http_client.client, cur_response, raw_body["model"],
                    model_cache, auth_manager,
                    request_messages=messages_for_tokenizer,
                    request_tools=tools_for_tokenizer,
                    max_tokens=max_tokens,
                ).__aiter__()

                while True:
                    next_coro = upstream.__anext__()
                    task = asyncio.ensure_future(next_coro)
                    try:
                        done, pending = await asyncio.wait({task}, timeout=15)
                    except asyncio.CancelledError:
                        task.cancel()
                        raise

                    if done:
                        try:
                            chunk = task.result()
                            chunk_count += 1
                        except StopAsyncIteration:
                            break
                    else:
                        # Heartbeat loop
                        while True:
                            heartbeat_count += 1
                            yield ": heartbeat\n\n"
                            try:
                                done2, _ = await asyncio.wait({task}, timeout=15)
                            except asyncio.CancelledError:
                                task.cancel()
                                raise
                            if done2:
                                try:
                                    chunk = task.result()
                                    chunk_count += 1
                                    break
                                except StopAsyncIteration:
                                    chunk = None
                                    break
                        if chunk is None:
                            break

                    # ── 后处理：模型名还原 + usage 跟踪 ──
                    if original_model != raw_body["model"]:
                        chunk = chunk.replace(f'"model": "{raw_body["model"]}"', f'"model": "{original_model}"')

                    # Track usage and stop_reason from SSE events
                    for line in chunk.strip().split("\n"):
                        if line.startswith("data: "):
                            try:
                                d = json.loads(line[6:])
                                evt_type = d.get("type", "")
                                if evt_type == "message_delta":
                                    u = d.get("usage", {})
                                    if u.get("output_tokens"):
                                        accumulated_usage["output_tokens"] = u["output_tokens"]
                                    if u.get("input_tokens"):
                                        accumulated_usage["input_tokens"] = u["input_tokens"]
                                    delta = d.get("delta", {})
                                    if delta.get("stop_reason"):
                                        last_stop_reason = delta["stop_reason"]
                                elif evt_type == "content_block_start":
                                    cb = d.get("content_block", {})
                                    if cb.get("type") == "tool_use":
                                        has_tool_calls = True
                                elif evt_type == "content_block_delta":
                                    delta = d.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        accumulated_text += delta.get("text", "")
                            except (json.JSONDecodeError, KeyError):
                                pass

                    if debug_logger:
                        debug_logger.log_final_chunk(chunk.encode('utf-8') if isinstance(chunk, str) else chunk)
                    yield chunk

                # ── 空流重试 ──
                if chunk_count == 0 and last_stop_reason is None and refusal_attempt < REFUSAL_MAX_RETRIES:
                    logger.warning(
                        f"[{user['name']}] [anthropic] Empty stream, retrying {refusal_attempt + 1}/{REFUSAL_MAX_RETRIES}"
                    )
                    try:
                        await cur_http_client.close()
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
                    accumulated_usage = {"input_tokens": 0, "output_tokens": 0}
                    last_stop_reason = None
                    has_tool_calls = False
                    accumulated_text = ""
                    cur_http_client = KiroHttpClient(auth_manager, shared_client=None)
                    cur_response = await cur_http_client.request_with_retry("POST", url, kiro_payload, stream=True)
                    if cur_response.status_code != 200:
                        logger.warning(f"[{user['name']}] [anthropic] Empty stream retry got HTTP {cur_response.status_code}")
                        await cur_http_client.close()
                        break
                    continue

                # ── 模型拒绝重试 ──
                comp_tokens = accumulated_usage.get("output_tokens", 0)
                import re as _re
                has_chinese_resp = bool(_re.search(r'[\u4e00-\u9fff]', accumulated_text))
                if (
                    comp_tokens <= REFUSAL_TOKEN_THRESHOLD
                    and not has_chinese_resp
                    and refusal_attempt < REFUSAL_MAX_RETRIES
                    and not has_tool_calls
                    and chunk_count > 0
                ):
                    logger.warning(
                        f"[{user['name']}] [anthropic] Model refusal detected (output={comp_tokens}, "
                        f"chunks={chunk_count}), retrying {refusal_attempt + 1}/{REFUSAL_MAX_RETRIES}"
                    )
                    try:
                        await cur_http_client.close()
                    except Exception:
                        pass
                    await asyncio.sleep(1)
                    accumulated_usage = {"input_tokens": 0, "output_tokens": 0}
                    last_stop_reason = None
                    has_tool_calls = False
                    accumulated_text = ""
                    cur_http_client = KiroHttpClient(auth_manager, shared_client=None)
                    cur_response = await cur_http_client.request_with_retry("POST", url, kiro_payload, stream=True)
                    if cur_response.status_code != 200:
                        logger.warning(f"[{user['name']}] [anthropic] Refusal retry got HTTP {cur_response.status_code}")
                        await cur_http_client.close()
                        break
                    continue
                else:
                    break  # 正常完成

            except GeneratorExit:
                client_disconnected = True
                logger.warning(f"[anthropic] Client disconnected ({chunk_count} chunks, {heartbeat_count} heartbeats)")
                break
            except Exception as e:
                # ── 上游断开重试 ──
                if chunk_count < 5:
                    logger.warning(
                        f"[{user['name']}] [anthropic] Stream broke early ({chunk_count} chunks), retrying: "
                        f"{type(e).__name__}: {e}"
                    )
                    try:
                        await cur_http_client.close()
                    except Exception:
                        pass
                    retry_ok = False
                    try:
                        await asyncio.sleep(1)
                        retry_client = KiroHttpClient(auth_manager, shared_client=None)
                        retry_resp = await retry_client.request_with_retry("POST", url, kiro_payload, stream=True)
                        if retry_resp.status_code == 200:
                            logger.info(f"[{user['name']}] [anthropic] Stream retry: reconnected")
                            async for retry_chunk in stream_kiro_to_anthropic(
                                retry_client.client, retry_resp, raw_body["model"],
                                model_cache, auth_manager,
                                request_messages=messages_for_tokenizer,
                                request_tools=tools_for_tokenizer,
                                max_tokens=max_tokens,
                            ):
                                if original_model != raw_body["model"]:
                                    retry_chunk = retry_chunk.replace(
                                        f'"model": "{raw_body["model"]}"', f'"model": "{original_model}"'
                                    )
                                chunk_count += 1
                                if debug_logger:
                                    debug_logger.log_final_chunk(retry_chunk.encode('utf-8') if isinstance(retry_chunk, str) else retry_chunk)
                                yield retry_chunk
                            retry_ok = True
                            logger.info(f"[{user['name']}] [anthropic] Stream retry completed ({chunk_count} total chunks)")
                            await retry_client.close()
                        else:
                            await retry_client.close()
                            logger.warning(f"[{user['name']}] [anthropic] Stream retry got HTTP {retry_resp.status_code}")
                    except Exception as retry_err:
                        logger.warning(f"[{user['name']}] [anthropic] Stream retry failed: {type(retry_err).__name__}: {retry_err}")
                    if retry_ok:
                        break
                streaming_error = e
                raise
    finally:
        try:
            await cur_http_client.close()
        except Exception:
            pass
        pool.release_token(token_entry["id"])
        if streaming_error:
            logger.error(f"[anthropic] Streaming error after {chunk_count} chunks: {type(streaming_error).__name__}: {streaming_error}")
            if debug_logger:
                debug_logger.flush_on_error(500, str(streaming_error))
        elif client_disconnected:
            if debug_logger:
                debug_logger.discard_buffers()
        else:
            logger.info(
                f"[{user['name']}] [anthropic] Streaming completed ({chunk_count} chunks, "
                f"{heartbeat_count} heartbeats) stop_reason={last_stop_reason} tool_calls={has_tool_calls}"
            )
            if debug_logger:
                debug_logger.discard_buffers()
        try:
            await pool.mark_token_used(token_entry["id"])
            await pool.mark_user_used(user["id"])
            p_tok = accumulated_usage.get("input_tokens", 0)
            c_tok = accumulated_usage.get("output_tokens", 0)
            if p_tok or c_tok:
                await pool.record_usage(user["id"], raw_body["model"], p_tok, c_tok, token_entry["id"])
                logger.info(f"[{user['name']}] [anthropic] stream usage: input={p_tok} output={c_tok}")
        except Exception:
            pass


# ==================================================================================================
# Anthropic ↔ OpenAI-like format conversion helpers (for compression pipeline)
# ==================================================================================================

def _anthropic_msgs_to_openai_like(messages: list, system=None) -> list:
    """
    Convert Anthropic messages to OpenAI-like format for compress_context.

    The compression pipeline works on OpenAI-format messages. We convert
    Anthropic messages to that format, compress, then convert back.
    """
    result = []

    # System prompt → system message
    if system:
        if isinstance(system, str):
            result.append({"role": "system", "content": system})
        elif isinstance(system, list):
            text = " ".join(b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text")
            if text:
                result.append({"role": "system", "content": text})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            result.append({"role": role, "content": str(content)})
            continue

        # Process content blocks
        text_parts = []
        image_parts = []
        tool_calls = []
        tool_results_msgs = []

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")

            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "image":
                # Preserve image blocks through compression round-trip
                source = block.get("source", {})
                if source.get("type") == "base64":
                    image_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"},
                    })
            elif btype == "tool_use":
                inp = block.get("input", {})
                args = json.dumps(inp) if isinstance(inp, dict) else str(inp)
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {"name": block.get("name", ""), "arguments": args},
                })
            elif btype == "tool_result":
                rc = block.get("content", "")
                if isinstance(rc, list):
                    rc = " ".join(b.get("text", "") for b in rc if isinstance(b, dict) and b.get("type") == "text")
                elif not isinstance(rc, str):
                    rc = str(rc)
                tool_results_msgs.append({
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id", ""),
                    "content": rc or "(empty result)",
                })
            elif btype == "thinking":
                # Preserve thinking as text for compression (won't be compressed aggressively)
                thinking_text = block.get("thinking", "")
                if thinking_text:
                    text_parts.append(f"<thinking>{thinking_text}</thinking>")

        # Emit tool_result messages first (they're role=user in Anthropic but role=tool in OpenAI)
        for tr_msg in tool_results_msgs:
            result.append(tr_msg)

        # Then the main message
        if role == "assistant" and tool_calls:
            entry = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else ""}
            entry["tool_calls"] = tool_calls
            result.append(entry)
        elif text_parts or image_parts:
            if image_parts and role == "user":
                # Multimodal user message: text + images in OpenAI format
                parts = []
                if text_parts:
                    parts.append({"type": "text", "text": "\n".join(text_parts)})
                parts.extend(image_parts)
                result.append({"role": role, "content": parts})
            else:
                result.append({"role": role, "content": "\n".join(text_parts)})
        elif not tool_results_msgs:
            # Empty content — still emit to preserve message ordering
            result.append({"role": role, "content": ""})

    return result


def _anthropic_tools_to_openai_like(tools: list) -> list:
    """Convert Anthropic tools to OpenAI-like format for compression."""
    if not tools:
        return None
    result = []
    for tool in tools:
        tool_type = tool.get("type", "")
        if tool_type and tool_type not in ("function", "custom", ""):
            continue
        result.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return result or None


def _openai_like_msgs_to_anthropic(messages: list):
    """
    Convert compressed OpenAI-like messages back to Anthropic format.

    Returns (messages, system) tuple.
    """
    system_parts = []
    anthropic_msgs = []

    # Group tool messages with their preceding assistant message
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system_parts.append(content)
            i += 1
            continue

        if role == "tool":
            # Convert to Anthropic tool_result in a user message
            tool_result_blocks = []
            while i < len(messages) and messages[i].get("role") == "tool":
                m = messages[i]
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": m.get("tool_call_id", ""),
                    "content": m.get("content", "(empty result)"),
                })
                i += 1
            anthropic_msgs.append({"role": "user", "content": tool_result_blocks})
            continue

        if role == "assistant":
            blocks = []
            if content:
                blocks.append({"type": "text", "text": content})
            tc = msg.get("tool_calls")
            if tc:
                for call in tc:
                    func = call.get("function", {})
                    args = func.get("arguments", "{}")
                    try:
                        inp = json.loads(args) if isinstance(args, str) else args
                    except json.JSONDecodeError:
                        inp = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": call.get("id", ""),
                        "name": func.get("name", ""),
                        "input": inp,
                    })
            anthropic_msgs.append({"role": "assistant", "content": blocks if blocks else ""})
            i += 1
            continue

        # user message
        if isinstance(content, list):
            # Multimodal content — convert image_url back to Anthropic image blocks
            blocks = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type", "")
                if ptype == "text":
                    blocks.append({"type": "text", "text": part.get("text", "")})
                elif ptype == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        try:
                            header, data = url.split(",", 1)
                            media_type = header.split(";")[0].replace("data:", "")
                            blocks.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": data},
                            })
                        except Exception:
                            pass
            anthropic_msgs.append({"role": "user", "content": blocks if blocks else content})
        else:
            anthropic_msgs.append({"role": "user", "content": content})
        i += 1

    # Build system
    system = None
    if system_parts:
        system_text = "\n".join(system_parts)
        system = [{"type": "text", "text": system_text}]

    return anthropic_msgs, system
