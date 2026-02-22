# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Streaming logic for converting Kiro stream to OpenAI format.

Contains generators for:
- Converting AWS SSE to OpenAI SSE
- Forming streaming chunks
- Processing tool calls in stream

Uses streaming_core.py for parsing Kiro stream into unified KiroEvent objects.
"""

import json
import time
from typing import TYPE_CHECKING, AsyncGenerator, Callable, Awaitable, Optional

import httpx
from fastapi import HTTPException
from loguru import logger

from core.parsers import parse_bracket_tool_calls, deduplicate_tool_calls
from core.utils import generate_completion_id
from core.config import (
    FIRST_TOKEN_TIMEOUT,
    FIRST_TOKEN_MAX_RETRIES,
    FAKE_REASONING_HANDLING,
)
from core.tokenizer import count_tokens, count_message_tokens, count_tools_tokens

# Import from streaming_core - reuse shared parsing logic
from core.streaming_core import (
    parse_kiro_stream,
    FirstTokenTimeoutError,
    KiroEvent,
    calculate_tokens_from_context_usage,
    stream_with_first_token_retry as stream_with_first_token_retry_core,
)

if TYPE_CHECKING:
    from core.auth import KiroAuthManager
    from core.cache import ModelInfoCache

# Import debug_logger for logging
try:
    from core.debug_logger import debug_logger
except ImportError:
    debug_logger = None


# Re-export FirstTokenTimeoutError for backward compatibility
__all__ = ['FirstTokenTimeoutError', 'stream_kiro_to_openai', 'stream_with_first_token_retry', 'collect_stream_response']


async def stream_kiro_to_openai_internal(
    client: httpx.AsyncClient,
    response: httpx.Response,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    first_token_timeout: float = FIRST_TOKEN_TIMEOUT,
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Internal generator for converting Kiro stream to OpenAI format.
    
    Parses AWS SSE stream and converts events to OpenAI chat.completion.chunk.
    Supports tool calls and usage calculation.
    
    IMPORTANT: This function raises FirstTokenTimeoutError if first token
    is not received within first_token_timeout seconds.
    
    Args:
        client: HTTP client (for connection management)
        response: HTTP response with data stream
        model: Model name to include in response
        model_cache: Model cache for getting token limits
        auth_manager: Authentication manager
        first_token_timeout: First token wait timeout (seconds)
        request_messages: Original request messages (for fallback token counting)
        request_tools: Original request tools (for fallback token counting)
        conversation_id: Stable conversation ID for truncation recovery (optional)
        conversation_id: Stable conversation ID for truncation recovery (optional)
    
    Yields:
        Strings in SSE format: "data: {...}\\n\\n" or "data: [DONE]\\n\\n"
    
    Raises:
        FirstTokenTimeoutError: If first token not received within timeout
    
    Example:
        >>> async for chunk in stream_kiro_to_openai_internal(client, response, "claude-sonnet-4", cache, auth):
        ...     print(chunk)
        data: {"id":"chatcmpl-...","object":"chat.completion.chunk",...}
        
        data: [DONE]
    """
    def _log_chunk(chunk_text: str):
        """Log modified chunk to debug_logger if active."""
        if debug_logger:
            debug_logger.log_modified_chunk(chunk_text.encode('utf-8'))

    completion_id = generate_completion_id()
    created_time = int(time.time())
    first_chunk = True
    
    metering_data = None
    context_usage_percentage = None
    full_content = ""
    full_thinking_content = ""  # Accumulated thinking content for non-streaming
    
    streaming_error_occurred = False
    tool_calls_from_stream = []
    has_tool_calls = False
    tool_call_index = 0  # Incremental index for tool_calls (like 9router)
    seen_tool_ids = {}  # Map tool_call_id -> index
    message_stop_received = False
    metrics_data = None
    
    try:
        # Use streaming_core.parse_kiro_stream for unified event parsing
        # This handles AWS SSE parsing, first token timeout, and thinking parser
        async for event in parse_kiro_stream(response, first_token_timeout):
            if event.type == "content" and event.content:
                # Accumulate content for bracket tool call detection
                full_content += event.content
                
                # Format as OpenAI chunk
                delta = {"content": event.content}
                if first_chunk:
                    delta["role"] = "assistant"
                    first_chunk = False
                
                openai_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
                }
                
                chunk_text = f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                
                _log_chunk(chunk_text)
                
                yield chunk_text
            
            elif event.type == "thinking" and event.thinking_content:
                # Accumulate thinking content
                full_thinking_content += event.thinking_content
                
                # Send as reasoning_content or content based on mode
                if FAKE_REASONING_HANDLING == "as_reasoning_content":
                    delta = {"reasoning_content": event.thinking_content}
                else:
                    delta = {"content": event.thinking_content}
                
                if first_chunk:
                    delta["role"] = "assistant"
                    first_chunk = False
                
                openai_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
                }
                
                chunk_text = f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                
                _log_chunk(chunk_text)
                
                yield chunk_text
            
            elif event.type == "tool_start" and event.tool_use:
                # Stream tool_call start immediately (like 9router)
                has_tool_calls = True
                tool_data = event.tool_use
                tool_id = tool_data.get("id", f"call_{int(time.time())}")
                tool_name = tool_data.get("name", "")
                idx = tool_call_index
                tool_call_index += 1
                seen_tool_ids[tool_id] = idx
                
                # First chunk: send tool_call with id, type, function.name, empty arguments
                start_delta = {
                    "tool_calls": [{
                        "index": idx,
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": ""
                        }
                    }]
                }
                if first_chunk:
                    start_delta["role"] = "assistant"
                    first_chunk = False
                
                start_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model,
                    "choices": [{"index": 0, "delta": start_delta, "finish_reason": None}]
                }
                chunk_text = f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
                _log_chunk(chunk_text)
                yield chunk_text
                
                # If there are initial arguments, send them too
                initial_args = tool_data.get("initial_arguments", "")
                if initial_args:
                    args_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model,
                        "choices": [{"index": 0, "delta": {
                            "tool_calls": [{
                                "index": idx,
                                "function": {"arguments": initial_args}
                            }]
                        }, "finish_reason": None}]
                    }
                    chunk_text = f"data: {json.dumps(args_chunk, ensure_ascii=False)}\n\n"
                    _log_chunk(chunk_text)
                    yield chunk_text
            
            elif event.type == "tool_input" and event.tool_use:
                # Stream tool_call arguments incrementally
                tool_data = event.tool_use
                idx = tool_data.get("index", 0)
                args = tool_data.get("arguments", "")
                
                if args:
                    args_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model,
                        "choices": [{"index": 0, "delta": {
                            "tool_calls": [{
                                "index": idx,
                                "function": {"arguments": args}
                            }]
                        }, "finish_reason": None}]
                    }
                    chunk_text = f"data: {json.dumps(args_chunk, ensure_ascii=False)}\n\n"
                    _log_chunk(chunk_text)
                    yield chunk_text
            
            elif event.type == "tool_complete" and event.tool_use:
                # Tool call finalized — emit start+args chunks if not already streamed
                has_tool_calls = True
                tc = event.tool_use
                tool_id = tc.get("id", f"call_{int(time.time())}")
                
                # 截断处理：如果 tool call 被 Kiro API 截断，只记录日志。
                # 不注入 poison pill — 那会导致 Cursor 报 "Invalid arguments" 然后陷入重试循环。
                # 让 Cursor 自己处理截断的 JSON（它通常能容错或让模型重试）。
                if tool_id in seen_tool_ids and tc.get('_truncation_detected'):
                    truncation_info = tc.get('_truncation_info', {})
                    tool_name = tc.get('function', {}).get('name', 'unknown')
                    size_bytes = truncation_info.get('size_bytes', 0)
                    logger.warning(
                        f"Tool call {tool_id} ({tool_name}) truncated at {size_bytes} bytes. "
                        f"Passing through to client as-is (no poison pill)."
                    )
                
                if tool_id not in seen_tool_ids:
                    # This tool wasn't streamed via tool_start (e.g., start+stop in one event)
                    # Emit the full tool_call chunks now
                    func = tc.get("function") or {}
                    tool_name = func.get("name") or ""
                    tool_args = func.get("arguments") or "{}"
                    idx = tool_call_index
                    tool_call_index += 1
                    seen_tool_ids[tool_id] = idx
                    
                    # Start chunk
                    start_delta = {
                        "tool_calls": [{
                            "index": idx,
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": ""
                            }
                        }]
                    }
                    if first_chunk:
                        start_delta["role"] = "assistant"
                        first_chunk = False
                    
                    start_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model,
                        "choices": [{"index": 0, "delta": start_delta, "finish_reason": None}]
                    }
                    chunk_text = f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
                    _log_chunk(chunk_text)
                    yield chunk_text
                    
                    # Arguments chunk
                    if tool_args:
                        args_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [{"index": 0, "delta": {
                                "tool_calls": [{
                                    "index": idx,
                                    "function": {"arguments": tool_args}
                                }]
                            }, "finish_reason": None}]
                        }
                        chunk_text = f"data: {json.dumps(args_chunk, ensure_ascii=False)}\n\n"
                        _log_chunk(chunk_text)
                        yield chunk_text
                
                tool_calls_from_stream.append(tc)
            
            elif event.type == "tool_use" and event.tool_use:
                # Legacy: tool_use events from end-of-stream (bracket tool calls etc.)
                # These still need to be sent as a batch
                tool_calls_from_stream.append(event.tool_use)
                has_tool_calls = True
            
            elif event.type == "usage" and event.usage:
                metering_data = event.usage
            
            elif event.type == "context_usage" and event.context_usage_percentage is not None:
                context_usage_percentage = event.context_usage_percentage
            
            elif event.type == "message_stop":
                # Binary parser detected messageStopEvent — this is the definitive
                # end-of-message signal. Emit finish_reason immediately.
                # (We still continue the loop to collect usage/context_usage events
                # that may follow, but the finish chunk is queued for emission after loop.)
                message_stop_data = event.tool_use or {}
                if message_stop_data.get("has_tool_calls"):
                    has_tool_calls = True
                message_stop_received = True
            
            elif event.type == "metrics" and event.usage:
                # Token usage from metricsEvent
                metrics_data = event.usage
        
        # Track completion signals for truncation detection
        received_usage = metering_data is not None
        received_context_usage = context_usage_percentage is not None
        stream_completed_normally = received_usage or received_context_usage or message_stop_received
        
        # Check bracket-style tool calls in full content (fallback for models that embed tool calls in text)
        bracket_tool_calls = parse_bracket_tool_calls(full_content)
        # Only use bracket tool calls if no real tool calls were streamed
        if bracket_tool_calls and not has_tool_calls:
            bracket_tool_calls = deduplicate_tool_calls(bracket_tool_calls)
            has_tool_calls = True
            
            # Send bracket tool calls as a batch (they weren't streamed incrementally)
            logger.debug(f"Processing {len(bracket_tool_calls)} bracket tool calls")
            for idx, tc in enumerate(bracket_tool_calls):
                func = tc.get("function") or {}
                tool_name = func.get("name") or ""
                tool_args = func.get("arguments") or "{}"
                
                # Start chunk with id, name
                start_delta = {
                    "tool_calls": [{
                        "index": idx,
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": ""
                        }
                    }]
                }
                if first_chunk:
                    start_delta["role"] = "assistant"
                    first_chunk = False
                
                start_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model,
                    "choices": [{"index": 0, "delta": start_delta, "finish_reason": None}]
                }
                chunk_text = f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
                _log_chunk(chunk_text)
                yield chunk_text
                
                # Arguments chunk
                if tool_args:
                    args_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model,
                        "choices": [{"index": 0, "delta": {
                            "tool_calls": [{
                                "index": idx,
                                "function": {"arguments": tool_args}
                            }]
                        }, "finish_reason": None}]
                    }
                    chunk_text = f"data: {json.dumps(args_chunk, ensure_ascii=False)}\n\n"
                    _log_chunk(chunk_text)
                    yield chunk_text
        
        # Detect content truncation (missing completion signals)
        all_tool_calls = tool_calls_from_stream + bracket_tool_calls if bracket_tool_calls and not tool_calls_from_stream else tool_calls_from_stream
        content_was_truncated = (
            not stream_completed_normally and
            len(full_content) > 0 and
            not has_tool_calls
        )
        
        if content_was_truncated:
            from core.config import TRUNCATION_RECOVERY
            logger.error(
                f"Content truncated by Kiro API: stream ended without completion signals, "
                f"length={len(full_content)} chars. "
                f"{'Model will be notified automatically about truncation.' if TRUNCATION_RECOVERY else 'Set TRUNCATION_RECOVERY=true in .env to auto-notify model about truncation.'}"
            )
        
        # Determine finish_reason
        finish_reason = "tool_calls" if has_tool_calls else "stop"
        
        # Count completion_tokens (output) using tiktoken
        completion_tokens = count_tokens(full_content + full_thinking_content)
        
        # Calculate total_tokens based on context_usage_percentage from Kiro API
        # context_usage shows TOTAL percentage of context usage (input + output)
        prompt_tokens, total_tokens, prompt_source, total_source = calculate_tokens_from_context_usage(
            context_usage_percentage, completion_tokens, model_cache, model
        )
        
        # Fallback: Kiro API didn't return context_usage, use tiktoken
        # Count prompt_tokens from original messages
        # IMPORTANT: Don't apply correction coefficient for prompt_tokens,
        # as it was calibrated for completion_tokens
        if prompt_source == "unknown" and request_messages:
            prompt_tokens = count_message_tokens(request_messages, apply_claude_correction=False)
            if request_tools:
                prompt_tokens += count_tools_tokens(request_tools, apply_claude_correction=False)
            total_tokens = prompt_tokens + completion_tokens
            prompt_source = "tiktoken"
            total_source = "tiktoken"
        
        # Save truncation info for recovery (tracked by stable identifiers)
        from core.truncation_recovery import should_inject_recovery
        from core.truncation_state import save_tool_truncation, save_content_truncation
        
        if should_inject_recovery():
            # Save tool truncations (tracked by tool_call_id)
            truncated_count = 0
            for tc in all_tool_calls:
                if tc.get('_truncation_detected'):
                    save_tool_truncation(
                        tool_call_id=tc['id'],
                        tool_name=tc['function']['name'],
                        truncation_info=tc['_truncation_info']
                    )
                    truncated_count += 1
            
            # Save content truncation (tracked by content hash)
            if content_was_truncated:
                save_content_truncation(full_content)
            
            if truncated_count > 0 or content_was_truncated:
                logger.info(
                    f"Truncation detected: {truncated_count} tool(s), "
                    f"content={content_was_truncated}. Will be handled when client sends next request."
                )
        
        # Final chunk with usage
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        }
        
        if metering_data:
            final_chunk["usage"]["credits_used"] = metering_data
        
        # Log final token values being sent to client
        logger.debug(
            f"[Usage] {model}: "
            f"prompt_tokens={prompt_tokens} ({prompt_source}), "
            f"completion_tokens={completion_tokens} (tiktoken), "
            f"total_tokens={total_tokens} ({total_source})"
        )
        
        chunk_text = f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
        _log_chunk(chunk_text)
        yield chunk_text
        _log_chunk("data: [DONE]\n\n")
        yield "data: [DONE]\n\n"
        
    except FirstTokenTimeoutError:
        # Propagate timeout up for retry
        raise
    except GeneratorExit:
        # Client disconnected - this is normal, don't log as error
        logger.debug("Client disconnected (GeneratorExit)")
        streaming_error_occurred = True
    except Exception as e:
        streaming_error_occurred = True
        # Log exception type and message for better diagnostics
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else "(empty message)"
        logger.error(
            f"Error during streaming: [{error_type}] {error_msg}",
            exc_info=True
        )
        # Propagate error up for proper handling in routes_openai.py
        raise
    finally:
        # Always close response
        try:
            await response.aclose()
        except Exception as close_error:
            logger.debug(f"Error closing response: {close_error}")
        
        if streaming_error_occurred:
            logger.debug("Streaming completed with error")
        else:
            logger.debug("Streaming completed successfully")


async def stream_kiro_to_openai(
    client: httpx.AsyncClient,
    response: httpx.Response,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None
) -> AsyncGenerator[str, None]:
    """
    Generator for converting Kiro stream to OpenAI format.
    
    This is a wrapper over stream_kiro_to_openai_internal that does NOT retry.
    Retry logic is implemented in stream_with_first_token_retry.
    
    Args:
        client: HTTP client (for connection management)
        response: HTTP response with data stream
        model: Model name to include in response
        model_cache: Model cache for getting token limits
        auth_manager: Authentication manager
        request_messages: Original request messages (for fallback token counting)
        request_tools: Original request tools (for fallback token counting)
    
    Yields:
        Strings in SSE format: "data: {...}\\n\\n" or "data: [DONE]\\n\\n"
    """
    async for chunk in stream_kiro_to_openai_internal(
        client, response, model, model_cache, auth_manager,
        request_messages=request_messages,
        request_tools=request_tools
    ):
        yield chunk


async def stream_with_first_token_retry(
    make_request: Callable[[], Awaitable[httpx.Response]],
    client: httpx.AsyncClient,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    max_retries: int = FIRST_TOKEN_MAX_RETRIES,
    first_token_timeout: float = FIRST_TOKEN_TIMEOUT,
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None
) -> AsyncGenerator[str, None]:
    """
    Streaming with automatic retry on first token timeout.
    
    If model doesn't respond within first_token_timeout seconds,
    request is cancelled and a new one is made. Maximum max_retries attempts.
    
    This is seamless for user - they just see a delay,
    but eventually get a response (or error after all attempts).
    
    Uses generic stream_with_first_token_retry from streaming_core.py.
    
    Args:
        make_request: Function to create new HTTP request
        client: HTTP client
        model: Model name
        model_cache: Model cache
        auth_manager: Authentication manager
        max_retries: Maximum number of attempts
        first_token_timeout: First token wait timeout (seconds)
        request_messages: Original request messages (for fallback token counting)
        request_tools: Original request tools (for fallback token counting)
    
    Yields:
        Strings in SSE format
    
    Raises:
        HTTPException: After exhausting all attempts
    
    Example:
        >>> async def make_req():
        ...     return await http_client.request_with_retry("POST", url, payload, stream=True)
        >>> async for chunk in stream_with_first_token_retry(make_req, client, model, cache, auth):
        ...     print(chunk)
    """
    def create_http_error(status_code: int, error_text: str) -> HTTPException:
        """Create HTTPException for HTTP errors."""
        return HTTPException(
            status_code=status_code,
            detail=f"Upstream API error: {error_text}"
        )
    
    def create_timeout_error(retries: int, timeout: float) -> HTTPException:
        """Create HTTPException for timeout errors."""
        return HTTPException(
            status_code=504,
            detail=f"Model did not respond within {timeout}s after {retries} attempts. Please try again."
        )
    
    async def stream_processor(response: httpx.Response) -> AsyncGenerator[str, None]:
        """Process response and yield OpenAI SSE chunks."""
        async for chunk in stream_kiro_to_openai_internal(
            client,
            response,
            model,
            model_cache,
            auth_manager,
            first_token_timeout=first_token_timeout,
            request_messages=request_messages,
            request_tools=request_tools
        ):
            yield chunk
    
    async for chunk in stream_with_first_token_retry_core(
        make_request=make_request,
        stream_processor=stream_processor,
        max_retries=max_retries,
        first_token_timeout=first_token_timeout,
        on_http_error=create_http_error,
        on_all_retries_failed=create_timeout_error,
    ):
        yield chunk


async def collect_stream_response(
    client: httpx.AsyncClient,
    response: httpx.Response,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None
) -> dict:
    """
    Collect full response from streaming stream.
    
    Used for non-streaming mode - collects all chunks
    and forms a single response.
    
    Args:
        client: HTTP client
        response: HTTP response with stream
        model: Model name
        model_cache: Model cache
        auth_manager: Authentication manager
        request_messages: Original request messages (for fallback token counting)
        request_tools: Original request tools (for fallback token counting)
    
    Returns:
        Dictionary with full response in OpenAI chat.completion format
    """
    full_content = ""
    full_reasoning_content = ""
    final_usage = None
    tool_calls = []
    completion_id = generate_completion_id()
    
    async for chunk_str in stream_kiro_to_openai(
        client,
        response,
        model,
        model_cache,
        auth_manager,
        request_messages=request_messages,
        request_tools=request_tools
    ):
        if not chunk_str.startswith("data:"):
            continue
        
        data_str = chunk_str[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            continue
        
        try:
            chunk_data = json.loads(data_str)
            
            # Extract data from chunk
            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                full_content += delta["content"]
            if "reasoning_content" in delta:
                full_reasoning_content += delta["reasoning_content"]
            if "tool_calls" in delta:
                tool_calls.extend(delta["tool_calls"])
            
            # Save usage from last chunk
            if "usage" in chunk_data:
                final_usage = chunk_data["usage"]
                
        except (json.JSONDecodeError, IndexError):
            continue
    
    # Form final response
    message = {"role": "assistant", "content": full_content}
    if full_reasoning_content:
        message["reasoning_content"] = full_reasoning_content
    if tool_calls:
        # For non-streaming response remove index field from tool_calls,
        # as it's only required for streaming chunks
        cleaned_tool_calls = []
        for tc in tool_calls:
            # Extract function with None protection
            func = tc.get("function") or {}
            cleaned_tc = {
                "id": tc.get("id"),
                "type": tc.get("type", "function"),
                "function": {
                    "name": func.get("name", ""),
                    "arguments": func.get("arguments", "{}")
                }
            }
            cleaned_tool_calls.append(cleaned_tc)
        message["tool_calls"] = cleaned_tool_calls
    
    finish_reason = "tool_calls" if tool_calls else "stop"
    
    # Form usage for response
    usage = final_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    # Log token info for debugging (non-streaming uses same logs from streaming)
    
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish_reason
        }],
        "usage": usage
    }