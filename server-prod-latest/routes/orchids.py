# -*- coding: utf-8 -*-
"""
Orchids Routes — 通过 Orchids AI Coding Agent 代理请求。

将 OpenAI 格式的 /v1/chat/completions 请求转发到 Orchids API，
使用号池中的 Orchids 账号轮询。
"""

import json
import time
import httpx

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from services.orchids_auth import OrchidsAuthManager
from core.converters_orchids import (
    build_orchids_payload,
    OrchidsSSEParser,
)
from config.orchids import (
    ORCHIDS_UPSTREAM_URL,
    ORCHIDS_ONLY_MODELS,
    ORCHIDS_MODEL_MAP,
)
from core.config import STREAMING_READ_TIMEOUT

orchids_router = APIRouter(tags=["orchids"])

_orch_http_client: httpx.AsyncClient = None


def _get_orch_client() -> httpx.AsyncClient:
    global _orch_http_client
    if _orch_http_client is None or _orch_http_client.is_closed:
        _orch_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15, read=STREAMING_READ_TIMEOUT, write=15, pool=15),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
    return _orch_http_client


def _extract_usertoken(request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return auth


async def _validate_user(request):
    usertoken = _extract_usertoken(request)
    if not usertoken:
        raise HTTPException(status_code=401, detail="Missing API key")
    user = await request.app.state.pool.validate_apikey(usertoken)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


def _is_orchids_only(model: str) -> bool:
    """判断模型是否只能走 Orchids。"""
    resolved = ORCHIDS_MODEL_MAP.get(model, model)
    return resolved in ORCHIDS_ONLY_MODELS or model in ORCHIDS_ONLY_MODELS


def _resolve_orch_model(model: str) -> str:
    """解析模型名到 Orchids 实际使用的 agentMode。"""
    return ORCHIDS_MODEL_MAP.get(model, model)


async def handle_orchids_request(
    request: Request, openai_body: dict, user: dict, stream: bool = True
):
    """
    处理 Orchids 请求的核心逻辑。
    可被 proxy.py 调用来路由 Orchids 模型请求。
    """
    pool = request.app.state.pool
    original_model = openai_body.get("model", "")
    agent_mode = _resolve_orch_model(original_model)

    max_retries = 3
    for attempt in range(max_retries):
        token_entry = await pool.get_next_orchids_token()
        if not token_entry:
            raise HTTPException(status_code=503, detail="No available Orchids tokens")

        token_id = token_entry["id"]
        email = token_entry.get("email", "unknown")

        mgr = OrchidsAuthManager(
            client_cookie=token_entry["client_cookie"],
            session_id=token_entry.get("session_id", ""),
            user_id=token_entry.get("user_id", ""),
            email=email,
        )

        try:
            async with httpx.AsyncClient(timeout=15) as auth_client:
                jwt = await mgr.get_jwt(auth_client)
            if not jwt:
                logger.warning(f"Orchids [{email}]: JWT获取失败, disabling")
                await pool.disable_orchids_token(token_id, reason="JWT获取失败")
                continue

            # 如果 session 信息有变化，更新数据库
            if mgr.session_id and mgr.session_id != token_entry.get("session_id"):
                await pool.update_orchids_token_info(
                    token_id,
                    session_id=mgr.session_id,
                    user_id=mgr.user_id,
                    email=mgr.email,
                )

            orchids_payload = build_orchids_payload(
                openai_body,
                email=mgr.email,
                user_id=mgr.user_id,
                agent_mode=agent_mode,
                project_id=mgr.project_id,
            )
            headers = mgr.build_headers(jwt)

            logger.info(f"[{user['name']}] Orchids request: model={original_model} agent_mode={agent_mode} token={email}")

            client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15, read=STREAMING_READ_TIMEOUT, write=15, pool=15),
            )
            response = await client.send(
                client.build_request("POST", ORCHIDS_UPSTREAM_URL, json=orchids_payload, headers=headers),
                stream=True,
            )

            if response.status_code == 401 or response.status_code == 403:
                await response.aclose()
                logger.warning(f"Orchids [{email}] auth error {response.status_code}, disabling")
                await pool.disable_orchids_token(token_id, reason=f"HTTP {response.status_code}")
                continue

            if response.status_code == 429:
                await response.aclose()
                logger.warning(f"Orchids [{email}] rate limited 429")
                await pool.cooldown_orchids_token(token_id, seconds=60)
                continue

            if response.status_code >= 400:
                error_body = (await response.aread()).decode()[:500]
                await response.aclose()
                logger.error(f"Orchids [{email}] error {response.status_code}: {error_body}")
                raise HTTPException(status_code=response.status_code, detail=error_body)

            # 成功
            await pool.mark_orchids_token_used(token_id)
            await pool.mark_user_used(user["id"])

            if stream:
                return _build_stream_response(response, original_model, user, pool, token_id)
            else:
                result = await _build_non_stream_response(response, original_model, user, pool, token_id)
                return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Orchids [{email}] error: {e}", exc_info=True)
            if attempt < max_retries - 1:
                continue
            raise HTTPException(status_code=500, detail=f"Orchids error: {str(e)[:200]}")

    raise HTTPException(status_code=503, detail="All Orchids token attempts exhausted")


def _build_stream_response(response, model, user, pool, token_id):
    """构建流式响应。"""
    parser = OrchidsSSEParser(model)

    async def stream_wrapper():
        try:
            async for line in response.aiter_lines():
                chunks = parser.parse_sse_line(line)
                for chunk in chunks:
                    yield chunk
            # 如果流结束但没有 finish 事件
            if not parser._has_finished:
                yield parser._make_chunk({}, finish_reason="stop")
                yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Orchids stream error: {e}")
            error_chunk = {
                "id": parser.response_id,
                "object": "chat.completion.chunk",
                "created": parser.created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}],
                "error": {"message": f"Stream interrupted: {str(e)[:200]}", "type": "stream_error"},
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await response.aclose()
            try:
                c_tok = parser._output_tokens
                if c_tok:
                    await pool.record_usage(user["id"], model, 0, c_tok, token_id)
                    logger.info(f"[{user['name']}] Orchids stream usage: completion={c_tok}")
            except Exception:
                pass

    return StreamingResponse(
        stream_wrapper(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Provider": "orchids",
            "X-Token-Id": token_id,
        },
    )


async def _build_non_stream_response(response, model, user, pool, token_id):
    """构建非流式响应。"""
    import uuid as _uuid

    parser = OrchidsSSEParser(model)
    all_text = ""
    all_reasoning = ""
    tool_calls_list = []
    finish_reason = "stop"

    async for line in response.aiter_lines():
        chunks = parser.parse_sse_line(line)
        for chunk_str in chunks:
            if chunk_str.strip() == "data: [DONE]":
                continue
            if not chunk_str.startswith("data: "):
                continue
            try:
                chunk_data = json.loads(chunk_str[6:])
                choices = chunk_data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                fr = choices[0].get("finish_reason")
                if fr:
                    finish_reason = fr
                if "content" in delta:
                    all_text += delta["content"]
                if "reasoning_content" in delta:
                    all_reasoning += delta["reasoning_content"]
                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        tool_calls_list.append(tc)
            except (json.JSONDecodeError, KeyError):
                pass

    await response.aclose()

    message = {"role": "assistant", "content": all_text}
    if all_reasoning:
        message["reasoning_content"] = all_reasoning
    if tool_calls_list:
        message["tool_calls"] = tool_calls_list

    usage = {
        "prompt_tokens": 0,
        "completion_tokens": parser._output_tokens,
        "total_tokens": parser._output_tokens,
    }

    openai_resp = {
        "id": f"chatcmpl-orch-{_uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": usage,
    }

    try:
        c_tok = parser._output_tokens
        if c_tok:
            await pool.record_usage(user["id"], model, 0, c_tok, token_id)
            logger.info(f"[{user['name']}] Orchids usage: completion={c_tok}")
    except Exception:
        pass

    return JSONResponse(
        content=openai_resp,
        headers={"X-Provider": "orchids", "X-Token-Id": token_id},
    )
