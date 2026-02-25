"""
Streaming logic for converting Kiro stream to Anthropic Messages API SSE format.

Converts KiroEvent stream → Anthropic SSE events (message_start, content_block_start,
content_block_delta, content_block_stop, message_delta, message_stop).

Reuses streaming_core.parse_kiro_stream for the heavy lifting.
"""

import json
import time
from typing import TYPE_CHECKING, AsyncGenerator, Optional

import httpx
from loguru import logger

from core.streaming_core import (
    parse_kiro_stream,
    FirstTokenTimeoutError,
    calculate_tokens_from_context_usage,
)
from core.config import FIRST_TOKEN_TIMEOUT
from core.tokenizer import count_tokens, count_message_tokens, count_tools_tokens
from core.parsers import parse_bracket_tool_calls, deduplicate_tool_calls

if TYPE_CHECKING:
    from core.auth import KiroAuthManager
    from core.cache import ModelInfoCache


def _sse(event_type: str, data: dict) -> str:
    """Format an Anthropic SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_kiro_to_anthropic(
    client: httpx.AsyncClient,
    response: httpx.Response,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    first_token_timeout: float = FIRST_TOKEN_TIMEOUT,
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None,
    max_tokens: int = 8192,
) -> AsyncGenerator[str, None]:
    """
    Convert Kiro stream to Anthropic Messages API SSE format.

    Yields Anthropic-style SSE events:
      event: message_start
      event: content_block_start
      event: content_block_delta
      event: content_block_stop
      event: message_delta
      event: message_stop
    """
    msg_id = f"msg_{int(time.time() * 1000)}"
    block_index = 0
    block_open = False
    current_block_type = None  # "text" or "tool_use" or "thinking"

    metering_data = None
    context_usage_percentage = None
    full_content = ""
    full_thinking = ""
    tool_calls_from_stream = []
    has_tool_calls = False
    message_stop_received = False

    # Emit message_start
    yield _sse("message_start", {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    })

    def _open_text_block():
        nonlocal block_index, block_open, current_block_type
        if block_open and current_block_type == "text":
            return ""
        # Close previous block if open
        out = ""
        if block_open:
            out += _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
            block_index += 1
        out += _sse("content_block_start", {
            "type": "content_block_start",
            "index": block_index,
            "content_block": {"type": "text", "text": ""},
        })
        block_open = True
        current_block_type = "text"
        return out

    def _open_thinking_block():
        nonlocal block_index, block_open, current_block_type
        if block_open and current_block_type == "thinking":
            return ""
        out = ""
        if block_open:
            out += _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
            block_index += 1
        out += _sse("content_block_start", {
            "type": "content_block_start",
            "index": block_index,
            "content_block": {"type": "thinking", "thinking": ""},
        })
        block_open = True
        current_block_type = "thinking"
        return out

    try:
        async for event in parse_kiro_stream(response, first_token_timeout):
            if event.type == "content" and event.content:
                full_content += event.content
                yield _open_text_block()
                yield _sse("content_block_delta", {
                    "type": "content_block_delta",
                    "index": block_index,
                    "delta": {"type": "text_delta", "text": event.content},
                })

            elif event.type == "thinking" and event.thinking_content:
                full_thinking += event.thinking_content
                yield _open_thinking_block()
                yield _sse("content_block_delta", {
                    "type": "content_block_delta",
                    "index": block_index,
                    "delta": {"type": "thinking_delta", "thinking": event.thinking_content},
                })

            elif event.type == "tool_start" and event.tool_use:
                has_tool_calls = True
                td = event.tool_use
                # Close previous block
                if block_open:
                    yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                    block_index += 1
                    block_open = False
                yield _sse("content_block_start", {
                    "type": "content_block_start",
                    "index": block_index,
                    "content_block": {
                        "type": "tool_use",
                        "id": td.get("id", ""),
                        "name": td.get("name", ""),
                        "input": {},
                    },
                })
                block_open = True
                current_block_type = "tool_use"
                initial_args = td.get("initial_arguments", "")
                if initial_args:
                    yield _sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": {"type": "input_json_delta", "partial_json": initial_args},
                    })

            elif event.type == "tool_input" and event.tool_use:
                args = event.tool_use.get("arguments", "")
                if args:
                    yield _sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": {"type": "input_json_delta", "partial_json": args},
                    })

            elif event.type == "tool_complete" and event.tool_use:
                has_tool_calls = True
                tc = event.tool_use
                tool_calls_from_stream.append(tc)
                tool_id = tc.get("id", "")
                # If this tool wasn't streamed incrementally, emit full block
                if current_block_type != "tool_use" or not block_open:
                    if block_open:
                        yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                        block_index += 1
                    func = tc.get("function") or {}
                    yield _sse("content_block_start", {
                        "type": "content_block_start",
                        "index": block_index,
                        "content_block": {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": func.get("name", ""),
                            "input": {},
                        },
                    })
                    block_open = True
                    current_block_type = "tool_use"
                    tool_args = func.get("arguments", "{}")
                    if tool_args:
                        yield _sse("content_block_delta", {
                            "type": "content_block_delta",
                            "index": block_index,
                            "delta": {"type": "input_json_delta", "partial_json": tool_args},
                        })
                # Close the tool_use block
                yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                block_index += 1
                block_open = False
                current_block_type = None

            elif event.type == "tool_use" and event.tool_use:
                tool_calls_from_stream.append(event.tool_use)
                has_tool_calls = True

            elif event.type == "usage" and event.usage:
                metering_data = event.usage

            elif event.type == "context_usage" and event.context_usage_percentage is not None:
                context_usage_percentage = event.context_usage_percentage

            elif event.type == "message_stop":
                message_stop_received = True

        # Bracket tool calls fallback
        bracket_tool_calls = parse_bracket_tool_calls(full_content)
        if bracket_tool_calls and not has_tool_calls:
            bracket_tool_calls = deduplicate_tool_calls(bracket_tool_calls)
            has_tool_calls = True
            for tc in bracket_tool_calls:
                if block_open:
                    yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                    block_index += 1
                    block_open = False
                func = tc.get("function") or {}
                yield _sse("content_block_start", {
                    "type": "content_block_start",
                    "index": block_index,
                    "content_block": {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": {},
                    },
                })
                tool_args = func.get("arguments", "{}")
                if tool_args:
                    yield _sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": {"type": "input_json_delta", "partial_json": tool_args},
                    })
                yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                block_index += 1

        # Close any remaining open block
        if block_open:
            yield _sse("content_block_stop", {"type": "content_block_stop", "index": block_index})

        # Calculate tokens
        completion_tokens = count_tokens(full_content + full_thinking)
        prompt_tokens, total_tokens, _, _ = calculate_tokens_from_context_usage(
            context_usage_percentage, completion_tokens, model_cache, model
        )
        if prompt_tokens == 0 and request_messages:
            prompt_tokens = count_message_tokens(request_messages, apply_claude_correction=False)
            if request_tools:
                prompt_tokens += count_tools_tokens(request_tools, apply_claude_correction=False)

        stop_reason = "tool_use" if has_tool_calls else "end_turn"

        # message_delta with usage
        yield _sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {
                "output_tokens": completion_tokens,
                "input_tokens": prompt_tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        })

        yield _sse("message_stop", {"type": "message_stop"})

    except FirstTokenTimeoutError:
        raise
    except GeneratorExit:
        logger.debug("Client disconnected (GeneratorExit) [anthropic stream]")
    except Exception as e:
        logger.error(f"Error during Anthropic streaming: {type(e).__name__}: {e}", exc_info=True)
        raise
    finally:
        try:
            await response.aclose()
        except Exception:
            pass


async def collect_anthropic_response(
    client: httpx.AsyncClient,
    response: httpx.Response,
    model: str,
    model_cache: "ModelInfoCache",
    auth_manager: "KiroAuthManager",
    request_messages: Optional[list] = None,
    request_tools: Optional[list] = None,
    max_tokens: int = 8192,
) -> dict:
    """Collect full non-streaming Anthropic Messages API response."""
    content_blocks = []
    full_content = ""
    full_thinking = ""
    tool_calls = []
    prompt_tokens = 0
    completion_tokens = 0

    async for sse_line in stream_kiro_to_anthropic(
        client, response, model, model_cache, auth_manager,
        request_messages=request_messages, request_tools=request_tools,
        max_tokens=max_tokens,
    ):
        # Parse SSE lines
        for line in sse_line.strip().split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                evt_type = data.get("type", "")

                if evt_type == "content_block_start":
                    cb = data.get("content_block", {})
                    if cb.get("type") == "text":
                        content_blocks.append({"type": "text", "text": ""})
                    elif cb.get("type") == "tool_use":
                        content_blocks.append({
                            "type": "tool_use",
                            "id": cb.get("id", ""),
                            "name": cb.get("name", ""),
                            "input": {},
                        })
                    elif cb.get("type") == "thinking":
                        content_blocks.append({"type": "thinking", "thinking": ""})

                elif evt_type == "content_block_delta":
                    idx = data.get("index", len(content_blocks) - 1)
                    delta = data.get("delta", {})
                    if idx < len(content_blocks):
                        block = content_blocks[idx]
                        if delta.get("type") == "text_delta":
                            block["text"] = block.get("text", "") + delta.get("text", "")
                        elif delta.get("type") == "input_json_delta":
                            block["_raw_json"] = block.get("_raw_json", "") + delta.get("partial_json", "")
                        elif delta.get("type") == "thinking_delta":
                            block["thinking"] = block.get("thinking", "") + delta.get("thinking", "")

                elif evt_type == "message_delta":
                    usage = data.get("usage", {})
                    completion_tokens = usage.get("output_tokens", completion_tokens)

    # Finalize tool_use input from raw JSON
    for block in content_blocks:
        if block.get("type") == "tool_use" and "_raw_json" in block:
            try:
                block["input"] = json.loads(block.pop("_raw_json"))
            except json.JSONDecodeError:
                block["input"] = {}
                block.pop("_raw_json", None)

    stop_reason = "tool_use" if any(b.get("type") == "tool_use" for b in content_blocks) else "end_turn"

    return {
        "id": f"msg_{int(time.time() * 1000)}",
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        },
    }
