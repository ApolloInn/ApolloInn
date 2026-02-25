"""
Converters for transforming Anthropic Messages API format to Kiro format.

Adapter layer: Anthropic native format → unified format → Kiro payload.
Mirrors converters_openai.py but for the Anthropic /v1/messages endpoint.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.config import HIDDEN_MODELS
from core.model_resolver import get_model_id_for_kiro
from core.converters_core import (
    UnifiedMessage,
    UnifiedTool,
    build_kiro_payload as core_build_kiro_payload,
)


def _extract_anthropic_images(content: list) -> List[Dict[str, Any]]:
    """Extract images from Anthropic content blocks."""
    images = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "image":
            source = block.get("source", {})
            if source.get("type") == "base64":
                images.append({
                    "media_type": source.get("media_type", "image/jpeg"),
                    "data": source.get("data", ""),
                })
    return images


def convert_anthropic_messages_to_unified(
    messages: List[Dict[str, Any]],
    system: Any = None,
) -> Tuple[str, List[UnifiedMessage]]:
    """
    Convert Anthropic Messages API messages to unified format.

    Anthropic format differences from OpenAI:
    - system is a top-level field, not a message role
    - content can be string or list of content blocks
    - tool_use blocks are inside assistant content (not a separate field)
    - tool_result blocks are inside user content (not a separate role)
    """
    # System prompt
    system_prompt = ""
    if isinstance(system, str):
        system_prompt = system
    elif isinstance(system, list):
        system_prompt = " ".join(
            b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text"
        )

    unified: List[UnifiedMessage] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            unified.append(UnifiedMessage(role=role, content=content))
            continue

        if not isinstance(content, list):
            unified.append(UnifiedMessage(role=role, content=str(content)))
            continue

        # List of content blocks
        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        images: List[Dict[str, Any]] = []

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")

            if btype == "text":
                text_parts.append(block.get("text", ""))

            elif btype == "image":
                source = block.get("source", {})
                if source.get("type") == "base64":
                    images.append({
                        "media_type": source.get("media_type", "image/jpeg"),
                        "data": source.get("data", ""),
                    })

            elif btype == "tool_use":
                input_data = block.get("input", {})
                if isinstance(input_data, dict):
                    arguments = json.dumps(input_data)
                elif isinstance(input_data, str):
                    arguments = input_data
                else:
                    arguments = "{}"
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": arguments,
                    },
                })

            elif btype == "tool_result":
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    result_content = " ".join(
                        b.get("text", "") for b in result_content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                elif not isinstance(result_content, str):
                    result_content = str(result_content)
                tr_entry = {
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": result_content or "(empty result)",
                }
                if block.get("is_error"):
                    tr_entry["is_error"] = True
                tool_results.append(tr_entry)

        unified.append(UnifiedMessage(
            role=role,
            content="\n".join(text_parts) if text_parts else "",
            tool_calls=tool_calls or None,
            tool_results=tool_results or None,
            images=images or None,
        ))

    return system_prompt, unified


def convert_anthropic_tools_to_unified(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[UnifiedTool]]:
    """
    Convert Anthropic tools to unified format.

    Anthropic tool format:
    {"name": "...", "description": "...", "input_schema": {...}}

    Also handles built-in tools (e.g. web_search_20250305) by skipping them
    since Kiro API doesn't support them.
    """
    if not tools:
        return None
    unified = []
    for tool in tools:
        # Skip built-in tools (web_search, etc.) — they have "type" != "function" or "custom"
        tool_type = tool.get("type", "")
        if tool_type and tool_type not in ("function", "custom", ""):
            logger.debug(f"Skipping built-in tool type: {tool_type}")
            continue

        name = tool.get("name", "")
        if not name:
            continue
        unified.append(UnifiedTool(
            name=name,
            description=tool.get("description"),
            input_schema=tool.get("input_schema"),
        ))
    return unified or None


def build_kiro_payload_from_anthropic(
    body: Dict[str, Any],
    conversation_id: str,
    profile_arn: str,
) -> dict:
    """
    Build Kiro API payload from an Anthropic Messages API request body.

    Passes through all relevant Anthropic parameters:
    - model, messages, system, tools, tool_choice
    - temperature, top_p, top_k, stop_sequences
    - thinking (extended thinking configuration)
    - max_tokens
    """
    model = body.get("model", "claude-sonnet-4")
    messages = body.get("messages", [])
    system = body.get("system")
    tools = body.get("tools")

    system_prompt, unified_messages = convert_anthropic_messages_to_unified(messages, system)
    unified_tools = convert_anthropic_tools_to_unified(tools)
    model_id = get_model_id_for_kiro(model, HIDDEN_MODELS)

    logger.debug(
        f"Converting Anthropic request: model={model} -> {model_id}, "
        f"messages={len(unified_messages)}, tools={len(unified_tools) if unified_tools else 0}"
    )

    # Determine if thinking should be injected
    # If the client explicitly sends thinking config, respect it (don't double-inject)
    thinking_config = body.get("thinking")
    has_explicit_thinking = thinking_config and thinking_config.get("type") == "enabled"
    inject_thinking = not has_explicit_thinking  # Only inject fake reasoning if client didn't request real thinking

    result = core_build_kiro_payload(
        messages=unified_messages,
        system_prompt=system_prompt,
        model_id=model_id,
        tools=unified_tools,
        conversation_id=conversation_id,
        profile_arn=profile_arn,
        inject_thinking=inject_thinking,
    )
    return result.payload
