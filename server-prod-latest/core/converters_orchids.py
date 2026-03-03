# -*- coding: utf-8 -*-
"""
Orchids Format Converters — OpenAI ↔ Orchids 格式转换。

Orchids 的 API 比较特殊：
- 输入是一个单一的 prompt 字符串（包含 system + 对话历史 + 当前请求）
- 输出是 SSE 流，事件格式为 model.text-delta, model.tool-call 等
- 需要将这些转换为 OpenAI SSE 格式
"""

import json
import time
import uuid
import random
from typing import List, Dict, Any, Optional

from loguru import logger


# ==================================================================================================
# OpenAI → Orchids 请求转换
# ==================================================================================================


def _format_tool_result_content(content) -> str:
    """格式化 tool_result 的 content 为字符串。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)
        return json.dumps(content, ensure_ascii=False)
    return json.dumps(content, ensure_ascii=False) if content else ""


def _format_user_message(content) -> str:
    """格式化用户消息内容。"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    text = block.get("text", "").strip()
                    if text:
                        parts.append(text)
                elif block_type == "image":
                    source = block.get("source", {})
                    parts.append(f"[Image: {source.get('media_type', 'unknown')}]")
                elif block_type == "tool_result":
                    tool_use_id = block.get("tool_use_id", "")
                    result_str = _format_tool_result_content(block.get("content"))
                    error_attr = ' is_error="true"' if block.get("is_error") else ""
                    parts.append(
                        f'<tool_result tool_use_id="{tool_use_id}"{error_attr}>\n'
                        f"{result_str}\n</tool_result>"
                    )
        return "\n".join(parts)
    return str(content) if content else ""


def _format_assistant_message(content) -> str:
    """格式化助手消息内容。"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    text = block.get("text", "").strip()
                    if text:
                        parts.append(text)
                elif block_type == "thinking":
                    # 跳过 thinking 块
                    continue
                elif block_type == "tool_use":
                    input_json = json.dumps(block.get("input", {}), ensure_ascii=False)
                    parts.append(
                        f'<tool_use id="{block.get("id", "")}" name="{block.get("name", "")}">\n'
                        f"{input_json}\n</tool_use>"
                    )
        return "\n".join(parts)
    return str(content) if content else ""


def build_orchids_prompt(openai_body: dict) -> str:
    """
    将 OpenAI 格式的 messages/system/tools 构建为 Orchids 的单一 prompt 字符串。
    参考 Orchids-2api 的 BuildPromptV2 格式。
    """
    sections = []

    # 1. System prompt
    system_parts = []
    messages = openai_body.get("messages", [])
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                system_parts.append(content.strip())
    if system_parts:
        sections.append(f"<client_system>\n{chr(10).join(system_parts)}\n</client_system>")

    # 2. 代理指令
    proxy_instructions = (
        "你是 AI 编程助手，通过代理服务与用户交互。\n\n"
        "## 对话历史结构\n"
        '- <turn index="N" role="user|assistant"> 包含每轮对话\n'
        '- <tool_use id="..." name="..."> 表示工具调用\n'
        '- <tool_result tool_use_id="..."> 表示工具执行结果\n\n'
        "## 规则\n"
        "1. 仅依赖当前工具和历史上下文\n"
        "2. 用户在本地环境工作\n"
        "3. 回复简洁专业"
    )
    sections.append(f"<proxy_instructions>\n{proxy_instructions}\n</proxy_instructions>")

    # 3. 工具列表
    tools = openai_body.get("tools", [])
    if tools:
        tool_names = []
        for t in tools:
            func = t.get("function", {})
            name = func.get("name", "") or t.get("name", "")
            if name:
                tool_names.append(name)
        if tool_names:
            sections.append(f"<available_tools>\n{', '.join(tool_names)}\n</available_tools>")

    # 4. 对话历史（不含最后一条 user 消息和 system 消息）
    non_system_msgs = [m for m in messages if m.get("role") != "system"]
    history_msgs = non_system_msgs[:-1] if non_system_msgs and non_system_msgs[-1].get("role") == "user" else non_system_msgs

    history_parts = []
    turn_index = 1
    for msg in history_msgs:
        role = msg.get("role", "")
        if role == "user":
            text = _format_user_message(msg.get("content"))
            if text:
                history_parts.append(f'<turn index="{turn_index}" role="user">\n{text}\n</turn>')
                turn_index += 1
        elif role == "assistant":
            # 处理 tool_calls（OpenAI 格式）
            parts = []
            content = msg.get("content")
            if content:
                formatted = _format_assistant_message(content)
                if formatted:
                    parts.append(formatted)
            for tc in msg.get("tool_calls", []):
                func = tc.get("function", {})
                tc_id = tc.get("id", "")
                tc_name = func.get("name", "")
                tc_args = func.get("arguments", "{}")
                parts.append(f'<tool_use id="{tc_id}" name="{tc_name}">\n{tc_args}\n</tool_use>')
            text = "\n".join(parts)
            if text:
                history_parts.append(f'<turn index="{turn_index}" role="assistant">\n{text}\n</turn>')
                turn_index += 1
        elif role == "tool":
            # OpenAI 格式的 tool response
            tool_call_id = msg.get("tool_call_id", "")
            result = msg.get("content", "")
            text = f'<tool_result tool_use_id="{tool_call_id}">\n{result}\n</tool_result>'
            history_parts.append(f'<turn index="{turn_index}" role="user">\n{text}\n</turn>')
            turn_index += 1

    if history_parts:
        sections.append(f"<conversation_history>\n{chr(10).join(history_parts)}\n</conversation_history>")

    # 5. 当前用户请求
    current_request = "继续"
    if non_system_msgs and non_system_msgs[-1].get("role") == "user":
        text = _format_user_message(non_system_msgs[-1].get("content"))
        if text.strip():
            current_request = text
    sections.append(f"<user_request>\n{current_request}\n</user_request>")

    return "\n\n".join(sections)


def build_orchids_payload(
    openai_body: dict,
    email: str,
    user_id: str,
    agent_mode: str = "claude-sonnet-4-5",
    project_id: str = "",
) -> dict:
    """构建完整的 Orchids API 请求 payload。"""
    from config.orchids import ORCHIDS_DEFAULT_PROJECT_ID

    prompt = build_orchids_prompt(openai_body)
    return {
        "prompt": prompt,
        "chatHistory": [],
        "projectId": project_id or ORCHIDS_DEFAULT_PROJECT_ID,
        "currentPage": {},
        "agentMode": agent_mode,
        "mode": "agent",
        "gitRepoUrl": "",
        "email": email,
        "chatSessionId": random.randint(10000000, 99999999),
        "userId": user_id,
        "apiVersion": 2,
    }


# ==================================================================================================
# Orchids SSE → OpenAI SSE 转换
# ==================================================================================================


class OrchidsSSEParser:
    """将 Orchids SSE 流转换为 OpenAI SSE 格式。"""

    def __init__(self, model: str):
        self.model = model
        self.response_id = f"chatcmpl-orch-{uuid.uuid4().hex[:12]}"
        self.created = int(time.time())
        self._block_index = -1
        self._tool_blocks: Dict[str, int] = {}  # tool_id → block_index
        self._output_tokens = 0
        self._has_finished = False

    def _make_chunk(
        self,
        delta: dict,
        finish_reason: Optional[str] = None,
        usage: Optional[dict] = None,
    ) -> str:
        """构建一个 OpenAI SSE chunk。"""
        chunk = {
            "id": self.response_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
        }
        if usage:
            chunk["usage"] = usage
        return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    def parse_sse_line(self, line: str) -> List[str]:
        """解析一行 Orchids SSE 数据，返回 OpenAI SSE chunks。"""
        line = line.strip()
        if not line or not line.startswith("data: "):
            return []

        raw = line[6:]
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return []

        msg_type = msg.get("type", "")
        if msg_type != "model":
            return []

        event = msg.get("event", {})
        evt_type = event.get("type", "")
        chunks = []

        if evt_type == "text-start":
            # 文本块开始 → role delta
            chunks.append(self._make_chunk({"role": "assistant", "content": ""}))

        elif evt_type == "text-delta":
            delta_text = event.get("delta", "")
            if delta_text:
                self._output_tokens += max(1, len(delta_text) // 4)
                chunks.append(self._make_chunk({"content": delta_text}))

        elif evt_type == "text-end":
            pass  # 不需要单独处理

        elif evt_type == "reasoning-start":
            chunks.append(self._make_chunk({"role": "assistant", "reasoning_content": ""}))

        elif evt_type == "reasoning-delta":
            delta_text = event.get("delta", "")
            if delta_text:
                self._output_tokens += max(1, len(delta_text) // 4)
                chunks.append(self._make_chunk({"reasoning_content": delta_text}))

        elif evt_type == "reasoning-end":
            pass

        elif evt_type == "tool-input-start":
            tool_id = event.get("id", "")
            if tool_id:
                self._block_index += 1
                self._tool_blocks[tool_id] = self._block_index

        elif evt_type == "tool-call":
            tool_id = event.get("toolCallId", "")
            tool_name = event.get("toolName", "")
            input_str = event.get("input", "{}")
            if tool_id and tool_name:
                self._output_tokens += max(1, len(input_str) // 4)
                # 构建 tool_calls delta
                tool_call_delta = {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": input_str,
                            },
                        }
                    ]
                }
                chunks.append(self._make_chunk(tool_call_delta))

        elif evt_type == "finish":
            if not self._has_finished:
                self._has_finished = True
                finish_reason_raw = event.get("finishReason", "stop")
                reason_map = {
                    "stop": "stop",
                    "end_turn": "stop",
                    "tool-calls": "tool_calls",
                    "max_tokens": "length",
                }
                finish_reason = reason_map.get(finish_reason_raw, "stop")
                usage = {
                    "prompt_tokens": 0,  # Orchids 不提供精确值
                    "completion_tokens": self._output_tokens,
                    "total_tokens": self._output_tokens,
                }
                chunks.append(self._make_chunk({}, finish_reason=finish_reason, usage=usage))
                chunks.append("data: [DONE]\n\n")

        return chunks
