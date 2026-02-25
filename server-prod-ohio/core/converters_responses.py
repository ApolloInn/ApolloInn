"""
Responses API ↔ Chat Completions 格式转换器。

将 OpenAI Responses API 请求转为 Chat Completions 格式，
将 Chat Completions 响应转回 Responses API 格式。
"""

import time
import uuid
from typing import Any, Dict, List, Optional


# ============================================================================
# Responses Request → Chat Completions Request
# ============================================================================

def responses_input_to_messages(
    input_data: Any,
    instructions: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    将 Responses API 的 input 转为 chat messages 数组。

    input 可以是:
    - str: 单条 user message
    - list: InputItem 数组 (message / function_call_output 等)
    """
    messages = []

    # system / developer instructions
    if instructions:
        messages.append({"role": "system", "content": instructions})

    if isinstance(input_data, str):
        messages.append({"role": "user", "content": input_data})
        return messages

    if not isinstance(input_data, list):
        messages.append({"role": "user", "content": str(input_data)})
        return messages

    for item in input_data:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
            continue

        item_type = item.get("type", "")
        role = item.get("role", "user")

        if item_type == "message":
            content = _convert_content_parts(item.get("content", []))
            messages.append({"role": role, "content": content})

        elif item_type == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item.get("call_id", ""),
                "content": item.get("output", ""),
            })

        elif item_type == "item_reference":
            pass  # skip references

        else:
            # fallback: treat as user text
            text = item.get("text", item.get("content", str(item)))
            messages.append({"role": role, "content": text})

    return messages


def _convert_content_parts(content: Any) -> Any:
    """将 Responses content parts 转为 Chat Completions content 格式。"""
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    # 如果只有一个 text part，直接返回字符串
    if len(content) == 1 and isinstance(content[0], dict) and content[0].get("type") == "input_text":
        return content[0].get("text", "")

    parts = []
    for part in content:
        if isinstance(part, str):
            parts.append({"type": "text", "text": part})
        elif isinstance(part, dict):
            pt = part.get("type", "")
            if pt == "input_text":
                parts.append({"type": "text", "text": part.get("text", "")})
            elif pt == "input_image":
                url = part.get("image_url", part.get("url", ""))
                if isinstance(url, dict):
                    url = url.get("url", "")
                parts.append({"type": "image_url", "image_url": {"url": url}})
            else:
                parts.append({"type": "text", "text": part.get("text", str(part))})
    return parts if len(parts) > 1 else (parts[0]["text"] if parts else "")


def convert_responses_tools(tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
    """将 Responses API tools 转为 Chat Completions tools 格式。"""
    if not tools:
        return None

    cc_tools = []
    for tool in tools:
        tool_type = tool.get("type", "")
        if tool_type == "function":
            cc_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            })
    return cc_tools or None


def responses_request_to_chat(body: Dict[str, Any]) -> Dict[str, Any]:
    """将完整的 Responses API 请求体转为 Chat Completions 请求体。"""
    messages = responses_input_to_messages(
        body.get("input", ""),
        body.get("instructions"),
    )

    cc_body: Dict[str, Any] = {
        "model": body.get("model", ""),
        "messages": messages,
        "stream": body.get("stream", False),
    }

    if body.get("temperature") is not None:
        cc_body["temperature"] = body["temperature"]
    if body.get("top_p") is not None:
        cc_body["top_p"] = body["top_p"]
    if body.get("max_output_tokens") is not None:
        cc_body["max_tokens"] = body["max_output_tokens"]

    tools = convert_responses_tools(body.get("tools"))
    if tools:
        cc_body["tools"] = tools

    if body.get("tool_choice"):
        cc_body["tool_choice"] = body["tool_choice"]

    return cc_body


# ============================================================================
# Chat Completions Response → Responses API Response
# ============================================================================

def _new_response_id() -> str:
    return f"resp_{uuid.uuid4().hex[:24]}"


def _new_item_id() -> str:
    return f"msg_{uuid.uuid4().hex[:24]}"


def chat_response_to_responses(cc_resp: Dict[str, Any], model: str) -> Dict[str, Any]:
    """将 Chat Completions 非流式响应转为 Responses API 格式。"""
    resp_id = _new_response_id()
    now = int(time.time())

    choice = cc_resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    finish = choice.get("finish_reason", "stop")

    output = []

    # tool calls
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", {})
            output.append({
                "type": "function_call",
                "id": tc.get("id", _new_item_id()),
                "call_id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", "{}"),
            })

    # text content
    content = message.get("content")
    if content:
        output.append({
            "type": "message",
            "id": _new_item_id(),
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": content}],
        })

    # usage
    cc_usage = cc_resp.get("usage", {})
    usage = {
        "input_tokens": cc_usage.get("prompt_tokens", 0),
        "output_tokens": cc_usage.get("completion_tokens", 0),
        "total_tokens": cc_usage.get("total_tokens", 0),
    }

    status = "completed" if finish == "stop" else "incomplete"

    return {
        "id": resp_id,
        "object": "response",
        "created_at": now,
        "model": model,
        "status": status,
        "output": output,
        "usage": usage,
        "metadata": {},
    }


# ============================================================================
# Chat Completions Streaming → Responses API Streaming
# ============================================================================

def chat_stream_chunk_to_responses_events(
    chunk_data: Dict[str, Any],
    response_id: str,
    state: Dict[str, Any],
) -> List[str]:
    """
    将一个 Chat Completions stream chunk 转为 Responses API SSE 事件列表。
    返回格式化好的 SSE 行列表。
    """
    import json
    events = []

    choices = chunk_data.get("choices", [])
    if not choices:
        # usage-only chunk
        usage = chunk_data.get("usage")
        if usage:
            resp_usage = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            events.append(_sse("response.usage", {
                "response_id": response_id,
                "usage": resp_usage,
            }))
        return events

    delta = choices[0].get("delta", {})
    finish_reason = choices[0].get("finish_reason")

    # First chunk with role
    if delta.get("role") and not state.get("message_started"):
        state["message_started"] = True
        state["item_id"] = _new_item_id()
        state["output_index"] = 0
        state["content_index"] = 0
        events.append(_sse("response.output_item.added", {
            "output_index": state["output_index"],
            "item": {
                "type": "message",
                "id": state["item_id"],
                "role": "assistant",
                "status": "in_progress",
                "content": [],
            },
        }))
        events.append(_sse("response.content_part.added", {
            "output_index": state["output_index"],
            "content_index": state["content_index"],
            "part": {"type": "output_text", "text": ""},
        }))

    # Text delta
    text = delta.get("content")
    if text:
        if not state.get("message_started"):
            state["message_started"] = True
            state["item_id"] = _new_item_id()
            state["output_index"] = 0
            state["content_index"] = 0
            events.append(_sse("response.output_item.added", {
                "output_index": 0,
                "item": {
                    "type": "message",
                    "id": state["item_id"],
                    "role": "assistant",
                    "status": "in_progress",
                    "content": [],
                },
            }))
            events.append(_sse("response.content_part.added", {
                "output_index": 0,
                "content_index": 0,
                "part": {"type": "output_text", "text": ""},
            }))

        events.append(_sse("response.output_text.delta", {
            "output_index": state["output_index"],
            "content_index": state["content_index"],
            "delta": text,
        }))

    # Tool calls delta
    tool_calls = delta.get("tool_calls", [])
    for tc in tool_calls:
        tc_idx = tc.get("index", 0)
        tc_key = f"tc_{tc_idx}"
        fn = tc.get("function", {})

        if tc.get("id") and tc_key not in state:
            state[tc_key] = {
                "id": tc["id"],
                "name": fn.get("name", ""),
                "arguments": "",
            }
            events.append(_sse("response.output_item.added", {
                "output_index": tc_idx,
                "item": {
                    "type": "function_call",
                    "id": tc["id"],
                    "call_id": tc["id"],
                    "name": fn.get("name", ""),
                    "arguments": "",
                },
            }))

        if fn.get("arguments"):
            if tc_key in state:
                state[tc_key]["arguments"] += fn["arguments"]
            events.append(_sse("response.function_call_arguments.delta", {
                "output_index": tc_idx,
                "delta": fn["arguments"],
            }))

    # Finish
    if finish_reason:
        if state.get("message_started"):
            events.append(_sse("response.output_text.done", {
                "output_index": state.get("output_index", 0),
                "content_index": state.get("content_index", 0),
                "text": state.get("full_text", ""),
            }))
            events.append(_sse("response.content_part.done", {
                "output_index": state.get("output_index", 0),
                "content_index": state.get("content_index", 0),
                "part": {"type": "output_text", "text": state.get("full_text", "")},
            }))
            events.append(_sse("response.output_item.done", {
                "output_index": state.get("output_index", 0),
                "item": {
                    "type": "message",
                    "id": state.get("item_id", ""),
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": state.get("full_text", "")}],
                },
            }))

        events.append(_sse("response.completed", {
            "response": {
                "id": response_id,
                "object": "response",
                "status": "completed",
                "model": chunk_data.get("model", ""),
            },
        }))

    # Accumulate full text
    if text:
        state["full_text"] = state.get("full_text", "") + text

    return events


def _sse(event_type: str, data: Any) -> str:
    import json
    data["type"] = event_type
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
