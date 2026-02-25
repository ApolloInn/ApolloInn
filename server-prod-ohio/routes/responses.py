"""
Responses API Route — /v1/responses

将 OpenAI Responses API 请求转为 Chat Completions 格式，
复用现有 standard 管线处理，再将响应转回 Responses 格式。
"""

import json
import time

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from core.converters_responses import (
    responses_request_to_chat,
    chat_response_to_responses,
    chat_stream_chunk_to_responses_events,
    _new_response_id,
)
from core.models_openai import ChatCompletionRequest, ChatMessage
from core.converters_openai import build_kiro_payload
from core.streaming_openai import stream_kiro_to_openai, collect_stream_response
from core.auth import KiroAuthManager, AuthType
from core.http_client import KiroHttpClient
from core.kiro_errors import enhance_kiro_error
from core.cache import ModelInfoCache

responses_router = APIRouter(tags=["responses"])


async def _validate_user(request: Request) -> dict:
    """验证 API key 并返回用户信息。"""
    auth = request.headers.get("authorization", "")
    api_key = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    pool = request.app.state.pool
    user = await pool.validate_apikey(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


def _generate_conversation_id() -> str:
    import uuid
    return str(uuid.uuid4())


@responses_router.post("/v1/responses")
async def create_response(request: Request):
    """OpenAI Responses API 兼容端点。"""
    user = await _validate_user(request)
    pool = request.app.state.pool
    bridge = request.app.state.bridge
    model_cache: ModelInfoCache = request.app.state.model_cache

    # Quota check
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

    # Convert Responses → Chat Completions
    cc_body = responses_request_to_chat(raw_body)
    is_stream = raw_body.get("stream", False)
    original_model = cc_body["model"]

    try:
        request_data = ChatCompletionRequest(**cc_body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    # Model resolution
    request_data.model = request_data.model.lower()
    resolved_model = await pool.resolve_model(request_data.model)
    if resolved_model != original_model:
        logger.info(f"[responses] Model resolved: {original_model} -> {resolved_model}")
        request_data.model = resolved_model

    logger.info(
        f"[responses][{user['name']}] model={request_data.model} "
        f"stream={is_stream} messages={len(request_data.messages)}"
    )

    auth_manager = bridge.get_or_create_manager(token_entry)

    # Build Kiro payload
    conversation_id = _generate_conversation_id()
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

    # Token rotation on 429/403/402
    max_token_retries = 3
    for token_attempt in range(max_token_retries):
        if token_attempt > 0:
            new_token_entry = await pool.get_next_token()
            if new_token_entry and new_token_entry["id"] != token_entry["id"]:
                token_entry = new_token_entry
                auth_manager = bridge.get_or_create_manager(token_entry)
                logger.info(f"[responses][{user['name']}] Token rotation: attempt {token_attempt + 1}")
            else:
                import asyncio
                await asyncio.sleep(1)
            url = f"{auth_manager.api_host}/generateAssistantResponse"
            profile_arn = ""
            if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
                profile_arn = auth_manager.profile_arn
            try:
                kiro_payload = build_kiro_payload(request_data, conversation_id, profile_arn)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        if is_stream:
            http_client = KiroHttpClient(auth_manager, shared_client=None)
        else:
            http_client = KiroHttpClient(auth_manager, shared_client=request.app.state.http_client)

        try:
            response = await http_client.request_with_retry("POST", url, kiro_payload, stream=True)

            # Fatal 403
            if response.status_code == 403 and getattr(response, '_fatal_403', False):
                fatal_reason = getattr(response, '_fatal_reason', 'unknown')
                logger.error(f"[responses] Token {token_entry['id'][:8]} fatal 403: {fatal_reason}")
                try:
                    await pool.set_token_status(token_entry['id'], 'disabled', reason=fatal_reason)
                except Exception:
                    pass
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return _error_response(403, f"Token disabled: {fatal_reason}")

            # 402 quota
            if response.status_code == 402 and getattr(response, '_quota_402', False):
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return _error_response(402, "All tokens quota exhausted.")

            if response.status_code in (429, 402, 403) and token_attempt < max_token_retries - 1:
                await http_client.close()
                logger.warning(f"[responses] Kiro API {response.status_code}, rotating token")
                continue

            if response.status_code != 200:
                try:
                    error_content = await response.aread()
                except Exception:
                    error_content = b"Unknown error"
                await http_client.close()
                error_text = error_content.decode("utf-8", errors="replace")
                logger.error(f"[responses][{user['name']}] Kiro API {response.status_code}: {error_text[:500]}")
                error_message = error_text
                try:
                    error_json = json.loads(error_text)
                    error_info = enhance_kiro_error(error_json)
                    error_message = error_info.user_message
                except (json.JSONDecodeError, KeyError):
                    pass
                return _error_response(response.status_code, error_message)

            # ── Streaming ──
            if is_stream:
                resp_id = _new_response_id()

                async def stream_wrapper(
                    _http_client=http_client,
                    _response=response,
                    _resp_id=resp_id,
                ):
                    state = {}
                    accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                    try:
                        # Send response.created event
                        yield _sse_line("response.created", {
                            "response": {
                                "id": _resp_id,
                                "object": "response",
                                "status": "in_progress",
                                "model": original_model,
                            },
                        })

                        async for chunk in stream_kiro_to_openai(
                            _http_client.client, _response, request_data.model,
                            model_cache, auth_manager,
                            request_messages=messages_for_tokenizer,
                            request_tools=tools_for_tokenizer,
                        ):
                            if not chunk.startswith("data: ") or chunk.strip() == "data: [DONE]":
                                continue
                            try:
                                cd = json.loads(chunk[6:])
                            except (json.JSONDecodeError, KeyError):
                                continue

                            cd["model"] = original_model
                            if "usage" in cd:
                                accumulated_usage["prompt_tokens"] = cd["usage"].get("prompt_tokens", 0)
                                accumulated_usage["completion_tokens"] = cd["usage"].get("completion_tokens", 0)

                            events = chat_stream_chunk_to_responses_events(cd, _resp_id, state)
                            for ev in events:
                                yield ev

                    except GeneratorExit:
                        logger.debug("[responses] Client disconnected")
                    except Exception as e:
                        logger.error(f"[responses] Streaming error: {type(e).__name__}: {e}")
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
                resp = chat_response_to_responses(openai_response, original_model)

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

                return JSONResponse(content=resp)

        except HTTPException:
            await http_client.close()
            pool.release_token(token_entry["id"])
            raise
        except Exception as e:
            await http_client.close()
            pool.release_token(token_entry["id"])
            logger.error(f"[responses] Internal error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": "api_error", "code": status_code}},
    )


def _sse_line(event_type: str, data: dict) -> str:
    data["type"] = event_type
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
