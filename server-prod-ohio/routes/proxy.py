"""
Proxy Routes — 用户请求转发到 Kiro API（完整管线）。

复用 kiro-gateway 的完整转换、流式、重试、截断恢复逻辑。
支持 combo 映射和模型别名解析。
"""

import json
import time

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

# Import debug_logger
try:
    from core.debug_logger import debug_logger
except Exception:
    debug_logger = None

proxy_router = APIRouter(tags=["proxy"])
nothink_router = APIRouter(tags=["proxy-nothink"])


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


@proxy_router.get("/v1/models")
@nothink_router.get("/v1/models")
async def list_models(request: Request):
    await _validate_user(request)
    pool = request.app.state.pool
    model_cache = request.app.state.model_cache
    now = int(time.time())

    models = []
    seen = set()

    for model_id in model_cache.get_all_model_ids():
        models.append({"id": model_id, "object": "model", "created": now, "owned_by": "kiro"})
        seen.add(model_id)
        # Add -thinking variant for Claude models so Cursor can discover them
        if model_id.startswith("claude-"):
            thinking_id = model_id + "-thinking"
            models.append({"id": thinking_id, "object": "model", "created": now, "owned_by": "kiro"})
            seen.add(thinking_id)

    combos = await pool.list_combos()
    for combo_name in combos:
        if combo_name not in seen:
            models.append({"id": combo_name, "object": "model", "created": now, "owned_by": "apollo-combo"})
            seen.add(combo_name)
            # Add -thinking variant for combo models that map to Claude models
            targets = combos[combo_name]
            if targets and any(t.startswith("claude-") for t in targets):
                thinking_id = combo_name + "-thinking"
                if thinking_id not in seen:
                    models.append({"id": thinking_id, "object": "model", "created": now, "owned_by": "apollo-combo"})
                    seen.add(thinking_id)

    # ── Cursor 内部模型名（让 Cursor 识别 API key 可用） ──
    _CURSOR_NATIVE_MODELS = [
        "default", "composer-1.5", "composer-1",
        "claude-4.6-opus-high", "claude-4.6-opus-high-thinking",
        "claude-4.6-opus-max", "claude-4.6-opus-max-thinking",
        "claude-4.6-opus-high-thinking-fast", "claude-4.6-opus-max-thinking-fast",
        "claude-4.5-opus-high", "claude-4.5-opus-high-thinking",
        "claude-4.6-sonnet-medium", "claude-4.6-sonnet-medium-thinking",
        "claude-4.5-sonnet", "claude-4.5-sonnet-thinking",
        "gpt-5.3-codex", "gpt-5.3-codex-low", "gpt-5.3-codex-high", "gpt-5.3-codex-xhigh",
        "gpt-5.3-codex-fast", "gpt-5.3-codex-low-fast", "gpt-5.3-codex-high-fast", "gpt-5.3-codex-xhigh-fast",
        "gpt-5.3-codex-spark-preview", "gpt-5.3-codex-spark-preview-low",
        "gpt-5.3-codex-spark-preview-high", "gpt-5.3-codex-spark-preview-xhigh",
        "gpt-5.2", "gpt-5.2-fast", "gpt-5.2-high", "gpt-5.2-high-fast",
        "gpt-5.2-xhigh", "gpt-5.2-xhigh-fast", "gpt-5.2-low", "gpt-5.2-low-fast",
        "gpt-5.2-codex", "gpt-5.2-codex-high", "gpt-5.2-codex-low", "gpt-5.2-codex-xhigh",
        "gpt-5.2-codex-fast", "gpt-5.2-codex-high-fast", "gpt-5.2-codex-low-fast", "gpt-5.2-codex-xhigh-fast",
        "gpt-5.1-codex-max", "gpt-5.1-codex-max-high", "gpt-5.1-codex-max-low", "gpt-5.1-codex-max-xhigh",
        "gpt-5.1-codex-max-medium-fast", "gpt-5.1-codex-max-high-fast",
        "gpt-5.1-codex-max-low-fast", "gpt-5.1-codex-max-xhigh-fast",
        "gpt-5.1-high", "gpt-5-mini",
        "gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-flash",
        "gpt-5.1-codex-mini", "gpt-5.1-codex-mini-high", "gpt-5.1-codex-mini-low",
        "claude-4.5-haiku", "claude-4.5-haiku-thinking",
        "grok-code-fast-1",
        "claude-4-sonnet", "claude-4-sonnet-thinking",
        "claude-4-sonnet-1m", "claude-4-sonnet-1m-thinking",
    ]
    for mid in _CURSOR_NATIVE_MODELS:
        if mid not in seen:
            models.append({"id": mid, "object": "model", "created": now, "owned_by": "cursor"})
            seen.add(mid)

    return {"object": "list", "data": models}


@proxy_router.post("/v1/chat/completions")
@nothink_router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI 兼容的 chat completions 转发（完整管线）。

    模型解析顺序：combo -> 原名
    
    通过 /nothink/v1/chat/completions 访问时，自动移除思考过程（适用于 Cursor 2.5.x）。
    """
    # 检测是否为 nothink 模式（Cursor 2.5.x 用户使用）
    hide_thinking = request.url.path.startswith("/nothink/")
    
    # 标准模式分流：Header 触发时走独立的标准 OpenAI 路径
    if request.headers.get("x-apollo-mode") == "standard":
        from routes.standard import handle_standard_completions
        return await handle_standard_completions(request)

    user = await _validate_user(request)
    pool = request.app.state.pool
    bridge = request.app.state.bridge
    model_cache = request.app.state.model_cache

    # ── 配额检查 ──
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

    # Debug logging: 记录客户端原始请求
    if debug_logger:
        debug_logger.prepare_new_request(username=user["name"])
        try:
            debug_logger.log_request_body(json.dumps(raw_body, ensure_ascii=False).encode('utf-8'))
        except Exception:
            pass

    try:
        request_data = ChatCompletionRequest(**raw_body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    # ── 模型解析：combo -> 原名 ──
    original_model = request_data.model
    request_data.model = request_data.model.lower()
    resolved_model = await pool.resolve_model(request_data.model)
    if resolved_model != original_model:
        logger.info(f"Model resolved: {original_model} -> {resolved_model}")
        request_data.model = resolved_model

    logger.info(
        f"[{user['name']}] model={request_data.model} stream={request_data.stream} "
        f"token={token_entry['id']} messages={len(request_data.messages)}"
    )

    # ── 详细请求日志（调试用）──
    has_tools = bool(request_data.tools)
    tool_names = []
    if request_data.tools:
        for t in request_data.tools:
            if t.function and t.function.name:
                tool_names.append(t.function.name)
            elif t.name:
                tool_names.append(t.name)
    # 记录每条 message 的 role 和长度
    msg_summary = []
    for m in request_data.messages:
        content_len = len(m.content) if isinstance(m.content, str) else (len(str(m.content)) if m.content else 0)
        has_tc = bool(m.tool_calls)
        has_tid = bool(m.tool_call_id)
        parts = [f"{m.role}({content_len})"]
        if has_tc:
            parts.append(f"tool_calls={len(m.tool_calls)}")
        if has_tid:
            parts.append(f"tool_call_id={m.tool_call_id[:20]}")
        msg_summary.append(" ".join(parts))
    logger.info(
        f"[{user['name']}] tools={len(tool_names)} tool_names={tool_names} "
        f"messages_detail=[{', '.join(msg_summary)}]"
    )
    # ── 临时：dump 完整 tools 定义到文件（只 dump 一次）──
    try:
        import os as _os
        _tools_dump_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "compression_logs", "tools_definition.json")
        if request_data.tools and not _os.path.exists(_tools_dump_path):
            _os.makedirs(_os.path.dirname(_tools_dump_path), exist_ok=True)
            _tools_data = []
            for t in request_data.tools:
                _tools_data.append(t.model_dump())
            with open(_tools_dump_path, "w", encoding="utf-8") as _tf:
                json.dump(_tools_data, _tf, ensure_ascii=False, indent=2)
            logger.info(f"[Tools] Dumped {len(_tools_data)} tool definitions to {_tools_dump_path}")
    except Exception as _te:
        logger.debug(f"[Tools] Failed to dump tools: {_te}")
    # 记录最后一条 user message 的内容（截断到200字符）
    for m in reversed(request_data.messages):
        if m.role == "user" and m.content:
            content_preview = m.content[:200] if isinstance(m.content, str) else str(m.content)[:200]
            logger.info(f"[{user['name']}] last_user_msg: {content_preview}")
            break

    auth_manager = bridge.get_or_create_manager(token_entry)

    # -- 截断恢复检查 --
    # Cursor 发送 tool_result 有两种格式：
    #   1. 标准 OpenAI: role="tool", tool_call_id="xxx"
    #   2. Cursor 风格: role="user", content=[{"type":"tool_result","tool_use_id":"xxx",...}, ...]
    # 必须同时处理两种格式
    from core.truncation_state import get_tool_truncation, get_content_truncation
    from core.truncation_recovery import (
        generate_truncation_tool_result,
        generate_truncation_user_message,
    )

    modified_messages = []
    tool_results_modified = 0
    content_notices_added = 0

    for msg in request_data.messages:
        # 格式1: 标准 OpenAI tool message
        if msg.role == "tool" and msg.tool_call_id:
            truncation_info = get_tool_truncation(msg.tool_call_id)
            if truncation_info:
                synthetic = generate_truncation_tool_result(
                    tool_name=truncation_info.tool_name,
                    tool_use_id=msg.tool_call_id,
                    truncation_info=truncation_info.truncation_info,
                )
                modified_content = f"{synthetic['content']}\n\n---\n\nOriginal tool result:\n{msg.content}"
                modified_msg = msg.model_copy(update={"content": modified_content})
                modified_messages.append(modified_msg)
                tool_results_modified += 1
                continue

        # 格式2: Cursor 风格 — tool_result 嵌在 user message 的 content 数组里
        if msg.role == "user" and isinstance(msg.content, list):
            content_modified = False
            new_content = []
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_use_id = block.get("tool_use_id", "")
                    if tool_use_id:
                        truncation_info = get_tool_truncation(tool_use_id)
                        if truncation_info:
                            synthetic = generate_truncation_tool_result(
                                tool_name=truncation_info.tool_name,
                                tool_use_id=tool_use_id,
                                truncation_info=truncation_info.truncation_info,
                            )
                            # 在 tool_result 前插入截断提示
                            new_content.append({
                                "type": "text",
                                "text": synthetic["content"],
                            })
                            tool_results_modified += 1
                            content_modified = True
                new_content.append(block)
            if content_modified:
                modified_msg = msg.model_copy(update={"content": new_content})
                modified_messages.append(modified_msg)
                continue

        if msg.role == "assistant" and msg.content and isinstance(msg.content, str):
            truncation_info = get_content_truncation(msg.content)
            if truncation_info:
                modified_messages.append(msg)
                synthetic_user_msg = ChatMessage(
                    role="user",
                    content=generate_truncation_user_message(),
                )
                modified_messages.append(synthetic_user_msg)
                content_notices_added += 1
                continue

        modified_messages.append(msg)

    if tool_results_modified > 0 or content_notices_added > 0:
        request_data.messages = modified_messages
        logger.info(
            f"[{user['name']}] Truncation recovery: modified {tool_results_modified} tool_result(s), "
            f"added {content_notices_added} content notice(s)"
        )

    # -- 上下文压缩 --
    from core.config import CONTEXT_COMPRESSION, DEFAULT_MAX_INPUT_TOKENS

    if CONTEXT_COMPRESSION:
        from core.context_compression import compress_context

        raw_msgs = [msg.model_dump() for msg in request_data.messages]
        raw_tools = [tool.model_dump() for tool in request_data.tools] if request_data.tools else None
        context_window = min(
            model_cache.get_max_input_tokens(request_data.model) or DEFAULT_MAX_INPUT_TOKENS,
            DEFAULT_MAX_INPUT_TOKENS,  # Kiro API hard limit is 128K
        )

        compressed_msgs, comp_stats = compress_context(raw_msgs, raw_tools, context_window)

        if comp_stats["level"] > 0:
            from core.models_openai import ChatMessage
            request_data.messages = [ChatMessage(**m) for m in compressed_msgs]
            logger.info(
                f"[{user['name']}] Context compressed: {comp_stats['original_tokens']//1000}K -> "
                f"{comp_stats['final_tokens']//1000}K tokens (level {comp_stats['level']}, "
                f"saved {comp_stats['tokens_saved']//1000}K)"
            )

    # -- 构建 Kiro payload --
    conversation_id = generate_conversation_id()
    profile_arn_for_payload = ""
    if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
        profile_arn_for_payload = auth_manager.profile_arn

    try:
        kiro_payload = build_kiro_payload(request_data, conversation_id, profile_arn_for_payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Debug logging: 记录发给 Kiro API 的请求
    if debug_logger:
        try:
            debug_logger.log_kiro_request_body(json.dumps(kiro_payload, ensure_ascii=False).encode('utf-8'))
        except Exception:
            pass

    url = f"{auth_manager.api_host}/generateAssistantResponse"
    logger.debug(f"Kiro API URL: {url}")

    messages_for_tokenizer = [msg.model_dump() for msg in request_data.messages]
    tools_for_tokenizer = (
        [tool.model_dump() for tool in request_data.tools] if request_data.tools else None
    )

    # ── 429/403 Token Rotation: 遇到 rate limit 或并发冲突自动换 token 重试 ──
    max_token_retries = 3
    for token_attempt in range(max_token_retries):
        if token_attempt > 0:
            # 换一个新的 token
            new_token_entry = await pool.get_next_token()
            if new_token_entry and new_token_entry["id"] != token_entry["id"]:
                token_entry = new_token_entry
                auth_manager = bridge.get_or_create_manager(token_entry)
                logger.info(f"[{user['name']}] Token rotation: switched to token {token_entry['id'][:8]}... (attempt {token_attempt + 1})")
            else:
                logger.warning(f"[{user['name']}] Token rotation: no different token available, retrying same")
                import asyncio as _asyncio
                await _asyncio.sleep(1)
            # 重建 payload（因为 auth_manager 可能变了）
            url = f"{auth_manager.api_host}/generateAssistantResponse"
            profile_arn_for_payload = ""
            if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
                profile_arn_for_payload = auth_manager.profile_arn
            try:
                kiro_payload = build_kiro_payload(request_data, conversation_id, profile_arn_for_payload)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # -- HTTP 客户端（带重试） --
        if request_data.stream:
            http_client = KiroHttpClient(auth_manager, shared_client=None)
        else:
            shared_client = request.app.state.http_client
            http_client = KiroHttpClient(auth_manager, shared_client=shared_client)

        try:
            response = await http_client.request_with_retry("POST", url, kiro_payload, stream=True)

            # ── "电脑太多" 检测：自动冻结 Cursor 账号 24h ──
            if getattr(response, '_too_many_machines', False):
                tmm_reason = getattr(response, '_too_many_machines_reason', 'too many computers')
                # 找到当前用户绑定的 cursor 账号并冻结
                cursor_email = user.get("cursor_email", "")
                logger.error(
                    f"[{user['name']}] Too many machines: {tmm_reason}, "
                    f"cursor_email={cursor_email}, freezing account 24h"
                )
                if cursor_email:
                    try:
                        await pool.freeze_cursor_account(
                            cursor_email, hours=24,
                            reason=f"too_many_machines: {tmm_reason}"
                        )
                    except Exception as _e:
                        logger.error(f"Failed to freeze cursor account {cursor_email}: {_e}")
                # 换 token 重试
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                await http_client.close()
                return JSONResponse(
                    status_code=429,
                    content={"error": {
                        "message": f"当前 Cursor 账号触发机器数限制（24h 内使用设备过多），已自动冻结并切换账号。请重试。",
                        "type": "too_many_machines",
                        "code": 429,
                    }},
                )

            # ── 致命 403 检测：自动禁用已封禁/失效的 token ──
            if response.status_code == 403 and getattr(response, '_fatal_403', False):
                fatal_reason = getattr(response, '_fatal_reason', 'unknown')
                logger.error(
                    f"[{user['name']}] Token {token_entry['id'][:8]} fatal 403: {fatal_reason}, "
                    f"auto-disabling token"
                )
                try:
                    await pool.set_token_status(token_entry['id'], 'disabled', reason=fatal_reason)
                except Exception as _e:
                    logger.error(f"Failed to disable token {token_entry['id'][:8]}: {_e}")
                # 如果还有重试机会，换 token 继续
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                # 没有重试机会了，返回错误
                await http_client.close()
                return JSONResponse(
                    status_code=403,
                    content={"error": {"message": f"Token disabled: {fatal_reason}", "type": "token_fatal_error", "code": 403}},
                )

            # ── 402 月度配额耗尽：自动轮换 token ──
            if response.status_code == 402 and getattr(response, '_quota_402', False):
                quota_reason = getattr(response, '_quota_reason', 'MONTHLY_REQUEST_COUNT')
                logger.warning(
                    f"[{user['name']}] Token {token_entry['id'][:8]} quota 402: {quota_reason}, "
                    f"rotating token (attempt {token_attempt + 1}/{max_token_retries})"
                )
                if token_attempt < max_token_retries - 1:
                    await http_client.close()
                    continue
                # 所有 token 都配额耗尽
                await http_client.close()
                return JSONResponse(
                    status_code=402,
                    content={"error": {"message": "All tokens have reached their monthly request limit. Please try again later or add new tokens.", "type": "quota_exhausted", "code": 402}},
                )

            if response.status_code in (429, 402, 403) and token_attempt < max_token_retries - 1:
                await http_client.close()
                logger.warning(f"[{user['name']}] Kiro API {response.status_code}, rotating token (attempt {token_attempt + 1}/{max_token_retries})")
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
                    logger.debug(f"Kiro error: {error_info.original_message} (reason: {error_info.reason})")
                except (json.JSONDecodeError, KeyError):
                    pass
                logger.warning(f"HTTP {response.status_code} - {error_message[:200]}")
                # Debug logging: flush on error
                if debug_logger:
                    debug_logger.flush_on_error(response.status_code, error_message)
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": {"message": error_message, "type": "kiro_api_error", "code": response.status_code}},
                )

            if request_data.stream:
                async def stream_wrapper():
                    import asyncio
                    streaming_error = None
                    client_disconnected = False
                    accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                    last_finish_reason = None
                    has_tool_calls = False
                    accumulated_text = ""
                    heartbeat_count = 0
                    chunk_count = 0
                    # ── Thinking → <think> 标签转换状态 ──
                    thinking_first = True
                    thinking_sent = False
                    thinking_closed = False
                    _hide_thinking = hide_thinking  # 闭包捕获
                    _debug_chunks = []  # 临时：记录前3个chunk完整内容用于调试

                    # ── 模型拒绝重试：上下文太大导致模型拒绝时，最多重试 2 次 ──
                    REFUSAL_MAX_RETRIES = 2
                    REFUSAL_TOKEN_THRESHOLD = 100
                    cur_http_client = http_client
                    cur_response = response

                    try:
                        for refusal_attempt in range(REFUSAL_MAX_RETRIES + 1):
                            try:
                                heartbeat_count = 0
                                chunk_count = 0
                                upstream = stream_kiro_to_openai(
                                    cur_http_client.client, cur_response, request_data.model,
                                    model_cache, auth_manager,
                                    request_messages=messages_for_tokenizer,
                                    request_tools=tools_for_tokenizer,
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
                                        while True:
                                            heartbeat_count += 1
                                            yield ": heartbeat\n\n"
                                            try:
                                                done2, pending2 = await asyncio.wait({task}, timeout=15)
                                            except asyncio.CancelledError:
                                                task.cancel()
                                                raise
                                            if done2:
                                                try:
                                                    chunk = task.result()
                                                    chunk_count += 1
                                                    break
                                                except StopAsyncIteration:
                                                    if heartbeat_count > 0:
                                                        logger.debug(f"Stream ended after {heartbeat_count} heartbeats, {chunk_count} chunks")
                                                    chunk = None
                                                    break

                                        if chunk is None:
                                            break

                                    # 后处理：模型名还原 + reasoning_content → <think> 转换
                                    if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                                        try:
                                            chunk_data = json.loads(chunk[6:])
                                            modified = False
                                            if chunk_data.get("model") != original_model:
                                                chunk_data["model"] = original_model
                                                modified = True
                                            choices = chunk_data.get("choices", [])
                                            if choices:
                                                delta = choices[0].get("delta", {})
                                                # reasoning_content 处理
                                                rc = delta.get("reasoning_content")
                                                if rc is not None:
                                                    if _hide_thinking:
                                                        # nothink 模式：直接丢弃 reasoning_content
                                                        del delta["reasoning_content"]
                                                        modified = True
                                                        # 如果 delta 只剩空的，跳过这个 chunk
                                                        if not delta.get("content") and not delta.get("tool_calls") and not delta.get("role"):
                                                            continue
                                                    else:
                                                        # 正常模式：reasoning_content → <think> 转换
                                                        if thinking_first:
                                                            delta["content"] = "<think>\n" + rc
                                                            thinking_first = False
                                                            thinking_sent = True
                                                        else:
                                                            delta["content"] = rc
                                                        del delta["reasoning_content"]
                                                        modified = True
                                                elif delta.get("content") and thinking_sent and not thinking_closed:
                                                    delta["content"] = "\n</think>\n" + delta["content"]
                                                    thinking_closed = True
                                                    modified = True
                                            if "usage" in chunk_data:
                                                accumulated_usage["prompt_tokens"] = chunk_data["usage"].get("prompt_tokens", 0)
                                                accumulated_usage["completion_tokens"] = chunk_data["usage"].get("completion_tokens", 0)
                                            if choices:
                                                fr = choices[0].get("finish_reason")
                                                if fr:
                                                    last_finish_reason = fr
                                                delta = choices[0].get("delta", {})
                                                if "tool_calls" in delta:
                                                    has_tool_calls = True
                                                if delta.get("content"):
                                                    accumulated_text += delta["content"]

                                                from core.config import ANTI_LAZY_STOP_THRESHOLD
                                                import re as _re
                                                comp_tokens = accumulated_usage.get("completion_tokens", 0)
                                                prompt_tokens = accumulated_usage.get("prompt_tokens", 0)
                                                has_chinese = bool(_re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\uf900-\ufaff]', accumulated_text))
                                                ANTI_LAZY_MIN_PROMPT = 10000
                                                if (
                                                    fr == "stop"
                                                    and ANTI_LAZY_STOP_THRESHOLD > 0
                                                    and not has_tool_calls
                                                    and has_tools
                                                    and comp_tokens <= ANTI_LAZY_STOP_THRESHOLD
                                                    and prompt_tokens >= ANTI_LAZY_MIN_PROMPT
                                                    and not has_chinese
                                                ):
                                                    choices[0]["finish_reason"] = "length"
                                                    last_finish_reason = "length"
                                                    modified = True
                                                    logger.info(
                                                        f"[{user['name']}] Anti-lazy stop: changed stop->length "
                                                        f"(tokens={comp_tokens}, no_chinese, text={accumulated_text[:80]!r})"
                                                    )
                                                elif (
                                                    fr == "stop"
                                                    and ANTI_LAZY_STOP_THRESHOLD > 0
                                                    and not has_tool_calls
                                                    and has_tools
                                                    and comp_tokens <= ANTI_LAZY_STOP_THRESHOLD
                                                    and prompt_tokens >= ANTI_LAZY_MIN_PROMPT
                                                    and has_chinese
                                                ):
                                                    logger.info(
                                                        f"[{user['name']}] Anti-lazy stop: skipped (has_chinese=True, "
                                                        f"tokens={comp_tokens}, prompt={prompt_tokens}, text={accumulated_text[:80]!r})"
                                                    )
                                            if modified:
                                                chunk = f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                                        except (json.JSONDecodeError, KeyError):
                                            pass
                                    if debug_logger:
                                        debug_logger.log_final_chunk(chunk.encode('utf-8') if isinstance(chunk, str) else chunk)
                                    if len(_debug_chunks) < 3:
                                        _debug_chunks.append(chunk.strip())
                                        if len(_debug_chunks) == 3:
                                            for i, dc in enumerate(_debug_chunks):
                                                logger.info(f"[DEBUG-CHUNK-{i}] {dc}")
                                    yield chunk

                                # ── 空流重试：Kiro API 返回空流时重试一次 ──
                                if chunk_count == 0 and last_finish_reason is None and refusal_attempt < REFUSAL_MAX_RETRIES:
                                    logger.warning(
                                        f"[{user['name']}] Empty stream (0 chunks, no finish_reason), "
                                        f"retrying {refusal_attempt + 1}/{REFUSAL_MAX_RETRIES}"
                                    )
                                    refusal_attempt += 1
                                    try:
                                        await cur_http_client.close()
                                    except Exception:
                                        pass
                                    await asyncio.sleep(0.5)
                                    accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                                    last_finish_reason = None
                                    has_tool_calls = False
                                    accumulated_text = ""
                                    cur_http_client = KiroHttpClient(auth_manager, shared_client=None)
                                    cur_response = await cur_http_client.request_with_retry("POST", url, kiro_payload, stream=True)
                                    if cur_response.status_code != 200:
                                        logger.warning(f"[{user['name']}] Empty stream retry got HTTP {cur_response.status_code}")
                                        await cur_http_client.close()
                                        break
                                    continue

                                # ── 流正常结束：检测是否模型拒绝 ──
                                # 注意：has_tool_calls 时跳过重试！
                                # tool call 响应的 completion_tokens 天然很低，不是拒绝。
                                # 之前误判导致重试 → 403 并发冲突 → 504 超时。
                                comp_tokens = accumulated_usage.get("completion_tokens", 0)
                                import re as _re2
                                has_chinese_resp = bool(_re2.search(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\uf900-\ufaff]', accumulated_text))
                                if (
                                    comp_tokens <= REFUSAL_TOKEN_THRESHOLD
                                    and not has_chinese_resp
                                    and refusal_attempt < REFUSAL_MAX_RETRIES
                                    and not has_tool_calls
                                    and chunk_count > 0
                                ):
                                    logger.warning(
                                        f"[{user['name']}] Model refusal detected (completion={comp_tokens}, "
                                        f"no_chinese, chunks={chunk_count}), retrying {refusal_attempt + 1}/{REFUSAL_MAX_RETRIES}"
                                    )
                                    try:
                                        await cur_http_client.close()
                                    except Exception:
                                        pass
                                    await asyncio.sleep(1)
                                    accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                                    last_finish_reason = None
                                    has_tool_calls = False
                                    accumulated_text = ""
                                    cur_http_client = KiroHttpClient(auth_manager, shared_client=None)
                                    cur_response = await cur_http_client.request_with_retry("POST", url, kiro_payload, stream=True)
                                    if cur_response.status_code != 200:
                                        logger.warning(f"[{user['name']}] Refusal retry got HTTP {cur_response.status_code}")
                                        await cur_http_client.close()
                                        break
                                    continue
                                else:
                                    break  # 正常完成

                            except GeneratorExit:
                                client_disconnected = True
                                logger.warning(f"Client disconnected during streaming (after {chunk_count} chunks, {heartbeat_count} heartbeats)")
                                break
                            except Exception as e:
                                # ── 上游断开重试：chunk 很少时说明是连接问题 ──
                                if chunk_count < 5:
                                    logger.warning(
                                        f"[{user['name']}] Stream broke early ({chunk_count} chunks), retrying once: "
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
                                            retry_stream = stream_kiro_to_openai(
                                                retry_client.client, retry_resp, request_data.model,
                                                model_cache, auth_manager,
                                                request_messages=messages_for_tokenizer,
                                                request_tools=tools_for_tokenizer,
                                            )
                                            logger.info(f"[{user['name']}] Stream retry: reconnected")
                                            async for retry_chunk in retry_stream:
                                                if retry_chunk.startswith("data: ") and retry_chunk.strip() != "data: [DONE]":
                                                    try:
                                                        rcd = json.loads(retry_chunk[6:])
                                                        modified_retry = False
                                                        if rcd.get("model") != original_model:
                                                            rcd["model"] = original_model
                                                            modified_retry = True
                                                        # reasoning_content 处理（和主流程一致）
                                                        r_choices = rcd.get("choices", [])
                                                        if r_choices:
                                                            r_delta = r_choices[0].get("delta", {})
                                                            rc = r_delta.get("reasoning_content")
                                                            if rc is not None:
                                                                if _hide_thinking:
                                                                    del r_delta["reasoning_content"]
                                                                    modified_retry = True
                                                                    if not r_delta.get("content") and not r_delta.get("tool_calls") and not r_delta.get("role"):
                                                                        continue
                                                                else:
                                                                    if thinking_first:
                                                                        r_delta["content"] = "<think>\n" + rc
                                                                        thinking_first = False
                                                                        thinking_sent = True
                                                                    else:
                                                                        r_delta["content"] = rc
                                                                    del r_delta["reasoning_content"]
                                                                    modified_retry = True
                                                            elif r_delta.get("content") and thinking_sent and not thinking_closed:
                                                                r_delta["content"] = "\n</think>\n" + r_delta["content"]
                                                                thinking_closed = True
                                                                modified_retry = True
                                                        if "usage" in rcd:
                                                            accumulated_usage["prompt_tokens"] = rcd["usage"].get("prompt_tokens", 0)
                                                            accumulated_usage["completion_tokens"] = rcd["usage"].get("completion_tokens", 0)
                                                        if r_choices and r_choices[0].get("finish_reason"):
                                                            last_finish_reason = r_choices[0]["finish_reason"]
                                                        if r_choices:
                                                            r_delta = r_choices[0].get("delta", {})
                                                            if "tool_calls" in r_delta:
                                                                has_tool_calls = True
                                                            if r_delta.get("content"):
                                                                accumulated_text += r_delta["content"]
                                                        if modified_retry:
                                                            retry_chunk = f"data: {json.dumps(rcd, ensure_ascii=False)}\n\n"
                                                    except (json.JSONDecodeError, KeyError):
                                                        pass
                                                chunk_count += 1
                                                if debug_logger:
                                                    debug_logger.log_final_chunk(retry_chunk.encode('utf-8') if isinstance(retry_chunk, str) else retry_chunk)
                                                yield retry_chunk
                                            retry_ok = True
                                            logger.info(f"[{user['name']}] Stream retry: completed ({chunk_count} total chunks)")
                                            await retry_client.close()
                                        else:
                                            await retry_client.close()
                                            logger.warning(f"[{user['name']}] Stream retry: got HTTP {retry_resp.status_code}")
                                    except Exception as retry_err:
                                        logger.warning(f"[{user['name']}] Stream retry failed: {type(retry_err).__name__}: {retry_err}")
                                    if retry_ok:
                                        break
                                streaming_error = e
                                try:
                                    if debug_logger:
                                        debug_logger.log_final_chunk(b"data: [DONE]\n\n")
                                    yield "data: [DONE]\n\n"
                                except Exception:
                                    pass
                                raise
                    finally:
                        try:
                            await cur_http_client.close()
                        except Exception:
                            pass
                        # 释放 token 并发锁
                        pool.release_token(token_entry["id"])
                        if streaming_error:
                            logger.error(f"Streaming error after {chunk_count} chunks: {type(streaming_error).__name__}: {streaming_error}")
                            if debug_logger:
                                debug_logger.flush_on_error(500, str(streaming_error))
                        elif client_disconnected:
                            if debug_logger:
                                debug_logger.discard_buffers()
                            pass
                        else:
                            logger.info(f"Streaming: completed ({chunk_count} chunks, {heartbeat_count} heartbeats) finish_reason={last_finish_reason} tool_calls={has_tool_calls}")
                            if debug_logger:
                                debug_logger.discard_buffers()
                        try:
                            await pool.mark_token_used(token_entry["id"])
                            await pool.mark_user_used(user["id"])
                            p_tok = accumulated_usage["prompt_tokens"]
                            c_tok = accumulated_usage["completion_tokens"]
                            if p_tok or c_tok:
                                await pool.record_usage(user["id"], request_data.model, p_tok, c_tok, token_entry["id"])
                                logger.info(f"[{user['name']}] stream usage: prompt={p_tok} completion={c_tok}")
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
            else:
                openai_response = await collect_stream_response(
                    http_client.client, response, request_data.model,
                    model_cache, auth_manager,
                    request_messages=messages_for_tokenizer,
                    request_tools=tools_for_tokenizer,
                )
                await http_client.close()

                openai_response["model"] = original_model
                # 非流式：reasoning_content 处理
                for choice in openai_response.get("choices", []):
                    msg = choice.get("message", {})
                    rc = msg.get("reasoning_content", "")
                    if rc:
                        if hide_thinking:
                            # nothink 模式：直接删除 reasoning_content
                            del msg["reasoning_content"]
                        else:
                            # 正常模式：reasoning_content → <think> 转换
                            original_content = msg.get("content", "")
                            msg["content"] = f"<think>\n{rc}\n</think>\n{original_content}"
                            del msg["reasoning_content"]

                logger.info("Non-streaming: completed")
                pool.release_token(token_entry["id"])
                await pool.mark_token_used(token_entry["id"])
                await pool.mark_user_used(user["id"])

                try:
                    resp_usage = openai_response.get("usage", {})
                    p_tok = resp_usage.get("prompt_tokens", 0)
                    c_tok = resp_usage.get("completion_tokens", 0)
                    if p_tok or c_tok:
                        await pool.record_usage(user["id"], request_data.model, p_tok, c_tok, token_entry["id"])
                        logger.info(f"[{user['name']}] usage: prompt={p_tok} completion={c_tok}")
                except Exception as e:
                    logger.warning(f"Failed to record usage: {e}")

                return JSONResponse(content=openai_response)

        except HTTPException as e:
            await http_client.close()
            pool.release_token(token_entry["id"])
            logger.error(f"HTTP {e.status_code}: {e.detail}")
            raise
        except Exception as e:
            await http_client.close()
            pool.release_token(token_entry["id"])
            logger.error(f"Internal error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
