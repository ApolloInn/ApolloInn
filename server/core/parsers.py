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
Parsers for AWS Event Stream format.

Contains classes and functions for:
- Parsing binary AWS EventStream frames (like 9router reference)
- Extracting JSON events by event-type headers
- Processing tool calls
- Content deduplication
"""

import json
import re
import struct
from typing import Any, Dict, List, Optional

from loguru import logger

from core.utils import generate_tool_call_id


def find_matching_brace(text: str, start_pos: int) -> int:
    """
    Finds the position of the closing brace considering nesting and strings.
    """
    if start_pos >= len(text) or text[start_pos] != '{':
        return -1
    
    brace_count = 0
    in_string = False
    escape_next = False
    
    for i in range(start_pos, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\' and in_string:
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
    
    return -1


def parse_bracket_tool_calls(response_text: str) -> List[Dict[str, Any]]:
    """
    Parses tool calls in [Called func_name with args: {...}] format.
    """
    if not response_text or "[Called" not in response_text:
        return []
    
    tool_calls = []
    pattern = r'\[Called\s+(\w+)\s+with\s+args:\s*'
    
    for match in re.finditer(pattern, response_text, re.IGNORECASE):
        func_name = match.group(1)
        args_start = match.end()
        
        json_start = response_text.find('{', args_start)
        if json_start == -1:
            continue
        
        json_end = find_matching_brace(response_text, json_start)
        if json_end == -1:
            continue
        
        json_str = response_text[json_start:json_end + 1]
        
        try:
            args = json.loads(json_str)
            tool_call_id = generate_tool_call_id()
            tool_calls.append({
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(args)
                }
            })
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tool call arguments: {json_str[:100]}")
    
    return tool_calls


def deduplicate_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Removes duplicate tool calls by id and by name+arguments.
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    for tc in tool_calls:
        tc_id = tc.get("id", "")
        if not tc_id:
            continue
        
        existing = by_id.get(tc_id)
        if existing is None:
            by_id[tc_id] = tc
        else:
            existing_args = existing.get("function", {}).get("arguments", "{}")
            current_args = tc.get("function", {}).get("arguments", "{}")
            if current_args != "{}" and (existing_args == "{}" or len(current_args) > len(existing_args)):
                by_id[tc_id] = tc
    
    result_with_id = list(by_id.values())
    result_without_id = [tc for tc in tool_calls if not tc.get("id")]
    
    seen = set()
    unique = []
    
    for tc in result_with_id + result_without_id:
        func = tc.get("function") or {}
        func_name = func.get("name") or ""
        func_args = func.get("arguments") or "{}"
        key = f"{func_name}-{func_args}"
        if key not in seen:
            seen.add(key)
            unique.append(tc)
    
    if len(tool_calls) != len(unique):
        logger.debug(f"Deduplicated tool calls: {len(tool_calls)} -> {len(unique)}")
    
    return unique


# ==================================================================================================
# Binary AWS EventStream Frame Parser
# Reference: 9router-master 2/open-sse/executors/kiro.js parseEventFrame()
# ==================================================================================================

def parse_event_frame(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse a single AWS EventStream binary frame.
    
    Frame format:
    - Bytes 0-3: Total length (uint32 big-endian)
    - Bytes 4-7: Headers length (uint32 big-endian)
    - Bytes 8-11: Prelude CRC (uint32 big-endian)
    - Bytes 12..(12+headers_length): Headers
    - Bytes (12+headers_length)..(total_length-4): Payload
    - Last 4 bytes: Message CRC
    
    Headers format (repeated):
    - 1 byte: name length
    - N bytes: name (UTF-8)
    - 1 byte: header type (7 = string)
    - 2 bytes: value length (uint16 big-endian)
    - N bytes: value (UTF-8)
    
    Returns:
        {"headers": {str: str}, "payload": dict|None} or None on error
    """
    try:
        if len(data) < 16:
            return None
        
        # Parse prelude
        total_length = struct.unpack('>I', data[0:4])[0]
        headers_length = struct.unpack('>I', data[4:8])[0]
        # bytes 8-11 = prelude CRC, skip
        
        # Parse headers
        headers = {}
        offset = 12  # After prelude (4 + 4 + 4)
        header_end = 12 + headers_length
        
        while offset < header_end and offset < len(data):
            # Name length (1 byte)
            name_len = data[offset]
            offset += 1
            if offset + name_len > len(data):
                break
            
            # Name
            name = data[offset:offset + name_len].decode('utf-8', errors='replace')
            offset += name_len
            
            # Header type (1 byte)
            if offset >= len(data):
                break
            header_type = data[offset]
            offset += 1
            
            if header_type == 7:  # String type
                if offset + 2 > len(data):
                    break
                value_len = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                if offset + value_len > len(data):
                    break
                value = data[offset:offset + value_len].decode('utf-8', errors='replace')
                offset += value_len
                headers[name] = value
            else:
                # Unknown header type, skip this frame's headers
                break
        
        # Parse payload
        payload_start = 12 + headers_length
        payload_end = total_length - 4  # Exclude message CRC
        
        payload = None
        if payload_end > payload_start:
            payload_bytes = data[payload_start:payload_end]
            payload_str = payload_bytes.decode('utf-8', errors='replace').strip()
            
            if payload_str:
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    # Non-JSON payload, store as raw
                    payload = {"raw": payload_str}
        
        return {"headers": headers, "payload": payload}
    except Exception:
        return None


class AwsEventStreamParser:
    """
    Parser for AWS EventStream binary format.
    
    Uses binary frame parsing (like 9router reference) to extract events
    by :event-type header. This correctly handles all event types including
    messageStopEvent, meteringEvent, contextUsageEvent which have binary
    headers that text-based pattern matching cannot detect.
    
    Supported event types (from :event-type header):
    - assistantResponseEvent: Text content {content: str}
    - codeEvent: Code content {content: str}
    - toolUseEvent: Tool call {toolUseId, name, input}
    - messageStopEvent: Stream end signal
    - contextUsageEvent: Context usage {contextUsagePercentage: float}
    - meteringEvent: Metering/usage data
    - metricsEvent: Token usage metrics
    
    Also falls back to text-based JSON pattern matching for any events
    that don't come through as proper binary frames.
    """
    
    # Text-based fallback patterns (kept for compatibility)
    TEXT_PATTERNS = [
        ('{"content":', 'content'),
        ('{"name":', 'tool_start'),
        ('{"input":', 'tool_input'),
        ('{"stop":', 'tool_stop'),
        ('{"followupPrompt":', 'followup'),
        ('{"usage":', 'usage'),
        ('{"contextUsagePercentage":', 'context_usage'),
    ]
    
    def __init__(self):
        """Initializes the parser."""
        self.binary_buffer = bytearray()
        self.text_buffer = ""
        self.last_content: Optional[str] = None
        self.current_tool_call: Optional[Dict[str, Any]] = None
        # Support interleaved tool calls: multiple tools streaming concurrently
        self._active_tool_calls: Dict[str, Dict[str, Any]] = {}  # toolUseId -> tool_call dict
        self.tool_calls: List[Dict[str, Any]] = []
        self.has_tool_calls = False
        self.message_stop_received = False
        self.seen_tool_ids: Dict[str, int] = {}  # toolUseId -> index
    
    def feed(self, chunk: bytes) -> List[Dict[str, Any]]:
        """
        Adds chunk to buffer and returns parsed events.
        """
        self.binary_buffer.extend(chunk)
        events = []
        
        # Parse binary frames
        iterations = 0
        max_iterations = 1000
        
        while len(self.binary_buffer) >= 16 and iterations < max_iterations:
            iterations += 1
            
            # Read total length from first 4 bytes
            total_length = struct.unpack('>I', self.binary_buffer[0:4])[0]
            
            # Sanity checks
            if total_length < 16 or total_length > 10 * 1024 * 1024:
                # Invalid frame — fall back to text parsing
                try:
                    self.text_buffer += bytes(self.binary_buffer).decode('utf-8', errors='ignore')
                except Exception:
                    pass
                self.binary_buffer.clear()
                break
            
            if len(self.binary_buffer) < total_length:
                # Incomplete frame, wait for more data
                break
            
            # Extract complete frame
            frame_data = bytes(self.binary_buffer[:total_length])
            self.binary_buffer = self.binary_buffer[total_length:]
            
            # Parse the frame
            frame = parse_event_frame(frame_data)
            if not frame:
                continue
            
            event_type = frame["headers"].get(":event-type", "")
            payload = frame["payload"]
            
            # Process by event type (matching 9router logic)
            frame_events = self._process_binary_event(event_type, payload)
            events.extend(frame_events)
        
        # Text-based fallback for any remaining data in text_buffer
        if self.text_buffer:
            text_events = self._parse_text_fallback()
            events.extend(text_events)
        
        return events
    
    def _process_binary_event(self, event_type: str, payload: Optional[dict]) -> List[Dict[str, Any]]:
        """
        Process a binary frame event by its :event-type header.
        Mirrors 9router's transformEventStreamToSSE logic.
        """
        events = []
        
        if event_type == "assistantResponseEvent" and payload:
            content = payload.get("content", "")
            if content:
                # Deduplicate
                if content != self.last_content:
                    self.last_content = content
                    events.append({"type": "content", "data": content})
        
        elif event_type == "codeEvent" and payload:
            content = payload.get("content", "")
            if content:
                events.append({"type": "content", "data": content})
        
        elif event_type == "toolUseEvent" and payload:
            self.has_tool_calls = True
            # toolUseEvent contains complete tool data: {toolUseId, name, input}
            # Can be a single object or array (handle both like 9router)
            # IMPORTANT: Kiro API can interleave events from multiple tool calls
            # (e.g. A-start, B-start, A-input, B-input), so we track all active
            # tool calls in _active_tool_calls dict instead of a single pointer.
            tool_uses = payload if isinstance(payload, list) else [payload]
            
            for tool_use in tool_uses:
                tool_id = tool_use.get("toolUseId", generate_tool_call_id())
                tool_name = tool_use.get("name", "")
                tool_input = tool_use.get("input")
                
                is_new = tool_id not in self.seen_tool_ids
                
                if is_new:
                    idx = len(self.seen_tool_ids)
                    self.seen_tool_ids[tool_id] = idx
                    
                    # Build arguments string
                    if tool_input is not None:
                        if isinstance(tool_input, str):
                            args_str = tool_input
                        elif isinstance(tool_input, dict):
                            args_str = json.dumps(tool_input)
                        else:
                            args_str = str(tool_input)
                    else:
                        args_str = ""
                    
                    tc = {
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": args_str
                        },
                        "_index": idx
                    }
                    self._active_tool_calls[tool_id] = tc
                    # Keep current_tool_call pointing to latest for text-fallback compat
                    self.current_tool_call = tc
                    
                    # Emit tool_start
                    events.append({"type": "tool_start", "data": {
                        "id": tool_id,
                        "name": tool_name,
                        "index": idx,
                        "initial_arguments": args_str
                    }})
                else:
                    # Existing tool — append input as delta (supports interleaving)
                    idx = self.seen_tool_ids[tool_id]
                    tc = self._active_tool_calls.get(tool_id)
                    if tool_input is not None and tc:
                        if isinstance(tool_input, str):
                            delta_str = tool_input
                        elif isinstance(tool_input, dict):
                            delta_str = json.dumps(tool_input)
                        else:
                            delta_str = str(tool_input)
                        
                        tc["function"]["arguments"] += delta_str
                        # Update current_tool_call to this one
                        self.current_tool_call = tc
                        events.append({"type": "tool_input", "data": {
                            "index": idx,
                            "arguments": delta_str
                        }})
        
        elif event_type == "messageStopEvent":
            self.message_stop_received = True
            # Finalize ALL active tool calls (not just current_tool_call)
            for tid, tc in list(self._active_tool_calls.items()):
                self.current_tool_call = tc
                self._finalize_tool_call()
                events.append({"type": "tool_complete", "data": self.tool_calls[-1]})
            self._active_tool_calls.clear()
            # Emit message_stop so streaming layer knows to send finish_reason
            events.append({"type": "message_stop", "data": {
                "has_tool_calls": self.has_tool_calls
            }})
        
        elif event_type == "contextUsageEvent" and payload:
            pct = payload.get("contextUsagePercentage")
            if pct is not None:
                events.append({"type": "context_usage", "data": pct})
        
        elif event_type == "meteringEvent" and payload:
            events.append({"type": "usage", "data": payload})
        
        elif event_type == "metricsEvent" and payload:
            # Extract token usage from metricsEvent
            metrics = payload.get("metricsEvent", payload)
            if isinstance(metrics, dict):
                input_tokens = metrics.get("inputTokens", 0)
                output_tokens = metrics.get("outputTokens", 0)
                if input_tokens > 0 or output_tokens > 0:
                    events.append({"type": "metrics", "data": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }})
        
        # Other event types (followupPromptEvent, etc.) — ignore silently
        
        return events
    
    def _parse_text_fallback(self) -> List[Dict[str, Any]]:
        """
        Text-based fallback parser for non-binary data.
        Uses JSON pattern matching (original approach).
        """
        events = []
        
        while True:
            earliest_pos = -1
            earliest_type = None
            
            for pattern, event_type in self.TEXT_PATTERNS:
                pos = self.text_buffer.find(pattern)
                if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
                    earliest_pos = pos
                    earliest_type = event_type
            
            if earliest_pos == -1:
                break
            
            json_end = find_matching_brace(self.text_buffer, earliest_pos)
            if json_end == -1:
                break
            
            json_str = self.text_buffer[earliest_pos:json_end + 1]
            self.text_buffer = self.text_buffer[json_end + 1:]
            
            try:
                data = json.loads(json_str)
                event = self._process_text_event(data, earliest_type)
                if event:
                    events.append(event)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON in text fallback: {json_str[:100]}")
        
        return events
    
    def _process_text_event(self, data: dict, event_type: str) -> Optional[Dict[str, Any]]:
        """Process a text-parsed event (fallback path)."""
        if event_type == 'content':
            content = data.get('content', '')
            if data.get('followupPrompt'):
                return None
            if content == self.last_content:
                return None
            self.last_content = content
            return {"type": "content", "data": content}
        
        elif event_type == 'tool_start':
            # Has name + possibly toolUseId + input
            if self.current_tool_call:
                self._finalize_tool_call()
            
            input_data = data.get('input', '')
            if isinstance(input_data, dict):
                input_str = json.dumps(input_data)
            else:
                input_str = str(input_data) if input_data else ''
            
            tool_id = data.get('toolUseId', generate_tool_call_id())
            tool_name = data.get('name', '')
            tool_index = len(self.tool_calls)
            
            self.current_tool_call = {
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": input_str
                },
                "_index": tool_index
            }
            self.has_tool_calls = True
            
            if data.get('stop'):
                self._finalize_tool_call()
                return {"type": "tool_complete", "data": self.tool_calls[-1]}
            
            return {"type": "tool_start", "data": {
                "id": tool_id,
                "name": tool_name,
                "index": tool_index,
                "initial_arguments": input_str
            }}
        
        elif event_type == 'tool_input':
            if self.current_tool_call:
                input_data = data.get('input', '')
                if isinstance(input_data, dict):
                    input_str = json.dumps(input_data)
                else:
                    input_str = str(input_data) if input_data else ''
                self.current_tool_call['function']['arguments'] += input_str
                return {"type": "tool_input", "data": {
                    "index": self.current_tool_call.get("_index", 0),
                    "arguments": input_str
                }}
            return None
        
        elif event_type == 'tool_stop':
            if self.current_tool_call and data.get('stop'):
                self._finalize_tool_call()
                return {"type": "tool_complete", "data": self.tool_calls[-1]}
            return None
        
        elif event_type == 'usage':
            return {"type": "usage", "data": data.get('usage', 0)}
        
        elif event_type == 'context_usage':
            return {"type": "context_usage", "data": data.get('contextUsagePercentage', 0)}
        
        return None
    
    def _finalize_tool_call(self) -> None:
        """Finalizes current tool call and adds to list."""
        if not self.current_tool_call:
            return
        
        args = self.current_tool_call['function']['arguments']
        tool_name = self.current_tool_call['function'].get('name', 'unknown')
        tool_id = self.current_tool_call.get('id', '')
        
        if isinstance(args, str):
            if args.strip():
                try:
                    parsed = json.loads(args)
                    self.current_tool_call['function']['arguments'] = json.dumps(parsed)
                except json.JSONDecodeError as e:
                    truncation_info = self._diagnose_json_truncation(args)
                    
                    if truncation_info["is_truncated"]:
                        self.current_tool_call['_truncation_detected'] = True
                        self.current_tool_call['_truncation_info'] = truncation_info
                        # 保存原始截断的 args 供 truncation recovery 使用
                        # streaming 层已经把这些残缺数据发给了客户端，
                        # 所以 recovery 系统需要知道实际发送了什么
                        self.current_tool_call['_truncation_info']['raw_truncated_args'] = args[:500]
                        
                        from core.config import TRUNCATION_RECOVERY
                        
                        logger.error(
                            f"Tool call truncated by Kiro API: "
                            f"tool='{tool_name}', id={tool_id}, size={truncation_info['size_bytes']} bytes, "
                            f"reason={truncation_info['reason']}."
                        )
                    else:
                        logger.warning(f"Failed to parse tool '{tool_name}' arguments: {e}. Raw: {args[:200]}")
                    
                    self.current_tool_call['function']['arguments'] = "{}"
            else:
                self.current_tool_call['function']['arguments'] = "{}"
        elif isinstance(args, dict):
            self.current_tool_call['function']['arguments'] = json.dumps(args)
        else:
            self.current_tool_call['function']['arguments'] = "{}"
        
        # Clean up internal fields
        self.current_tool_call.pop('_index', None)
        
        self.tool_calls.append(self.current_tool_call)
        # Remove from active dict
        if tool_id and tool_id in self._active_tool_calls:
            del self._active_tool_calls[tool_id]
        self.current_tool_call = None
    
    def _diagnose_json_truncation(self, json_str: str) -> Dict[str, Any]:
        """Analyzes a malformed JSON string to determine if it was truncated."""
        size_bytes = len(json_str.encode('utf-8'))
        stripped = json_str.strip()
        
        if not stripped:
            return {"is_truncated": False, "reason": "empty string", "size_bytes": size_bytes}
        
        open_braces = stripped.count('{')
        close_braces = stripped.count('}')
        open_brackets = stripped.count('[')
        close_brackets = stripped.count(']')
        
        if stripped.startswith('{') and not stripped.endswith('}'):
            missing = open_braces - close_braces
            return {"is_truncated": True, "reason": f"missing {missing} closing brace(s)", "size_bytes": size_bytes}
        
        if stripped.startswith('[') and not stripped.endswith(']'):
            missing = open_brackets - close_brackets
            return {"is_truncated": True, "reason": f"missing {missing} closing bracket(s)", "size_bytes": size_bytes}
        
        if open_braces != close_braces:
            return {"is_truncated": True, "reason": f"unbalanced braces ({open_braces} open, {close_braces} close)", "size_bytes": size_bytes}
        
        if open_brackets != close_brackets:
            return {"is_truncated": True, "reason": f"unbalanced brackets ({open_brackets} open, {close_brackets} close)", "size_bytes": size_bytes}
        
        quote_count = 0
        i = 0
        while i < len(stripped):
            if stripped[i] == '\\' and i + 1 < len(stripped):
                i += 2
                continue
            if stripped[i] == '"':
                quote_count += 1
            i += 1
        
        if quote_count % 2 != 0:
            return {"is_truncated": True, "reason": "unclosed string literal", "size_bytes": size_bytes}
        
        return {"is_truncated": False, "reason": "malformed JSON", "size_bytes": size_bytes}
    
    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Returns all collected tool calls."""
        # Finalize all remaining active tool calls
        for tid, tc in list(self._active_tool_calls.items()):
            self.current_tool_call = tc
            self._finalize_tool_call()
        self._active_tool_calls.clear()
        return deduplicate_tool_calls(self.tool_calls)
    
    def reset(self) -> None:
        """Resets parser state."""
        self.binary_buffer = bytearray()
        self.text_buffer = ""
        self.last_content = None
        self.current_tool_call = None
        self._active_tool_calls = {}
        self.tool_calls = []
        self.has_tool_calls = False
        self.message_stop_received = False
        self.seen_tool_ids = {}
