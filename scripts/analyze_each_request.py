#!/usr/bin/env python3
"""逐个请求深度分析：检查解析问题、Kiro回答质量、截断、丢数据等。"""
import json
import os
import sys
import struct


def parse_response_modified(path):
    """解析 response_stream_modified.txt"""
    with open(path) as f:
        data = f.read()
    chunks = []
    for line in data.split("\n"):
        line = line.strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                chunks.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                chunks.append({"_parse_error": line[6:50]})
        elif line == "data: [DONE]":
            chunks.append({"_done": True})
    return chunks


def extract_response_details(chunks):
    """从 chunks 中提取完整的响应细节"""
    text = ""
    reasoning = ""
    tool_calls = {}  # idx -> {name, args, id}
    finish_reason = None
    usage = None
    has_done = False

    for chunk in chunks:
        if chunk.get("_done"):
            has_done = True
            continue
        if chunk.get("_parse_error"):
            continue
        choices = chunk.get("choices", [])
        if not choices:
            if "usage" in chunk:
                usage = chunk["usage"]
            continue
        delta = choices[0].get("delta", {})
        fr = choices[0].get("finish_reason")
        if fr:
            finish_reason = fr
        if "content" in delta:
            text += delta["content"]
        if "reasoning_content" in delta:
            reasoning += delta["reasoning_content"]
        if "tool_calls" in delta:
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in tool_calls:
                    tool_calls[idx] = {"name": "", "args": "", "id": ""}
                fn = tc.get("function", {})
                if fn.get("name"):
                    tool_calls[idx]["name"] = fn["name"]
                if fn.get("arguments"):
                    tool_calls[idx]["args"] += fn["arguments"]
                if tc.get("id"):
                    tool_calls[idx]["id"] = tc["id"]
        if "usage" in chunk:
            usage = chunk["usage"]

    return {
        "text": text,
        "reasoning": reasoning,
        "tool_calls": tool_calls,
        "finish_reason": finish_reason,
        "usage": usage,
        "has_done": has_done,
        "chunk_count": len(chunks),
    }


def check_tool_call_validity(tc):
    """检查单个 tool call 的 args 是否有效 JSON"""
    args = tc["args"]
    if not args:
        return "EMPTY_ARGS", None
    try:
        parsed = json.loads(args)
        return "OK", parsed
    except json.JSONDecodeError as e:
        return f"INVALID_JSON: {e}", None


def parse_raw_binary_frames(path):
    """解析 raw binary 中的 AWS EventStream frames，提取事件类型"""
    with open(path, "rb") as f:
        data = f.read()
    
    events = []
    offset = 0
    while offset + 16 <= len(data):
        total_length = struct.unpack('>I', data[offset:offset+4])[0]
        if total_length < 16 or total_length > 10*1024*1024:
            break
        if offset + total_length > len(data):
            break
        
        headers_length = struct.unpack('>I', data[offset+4:offset+8])[0]
        
        # Parse headers
        headers = {}
        h_offset = offset + 12
        h_end = offset + 12 + headers_length
        while h_offset < h_end:
            if h_offset >= len(data):
                break
            name_len = data[h_offset]
            h_offset += 1
            name = data[h_offset:h_offset+name_len].decode('utf-8', errors='replace')
            h_offset += name_len
            if h_offset >= len(data):
                break
            header_type = data[h_offset]
            h_offset += 1
            if header_type == 7:
                if h_offset + 2 > len(data):
                    break
                val_len = struct.unpack('>H', data[h_offset:h_offset+2])[0]
                h_offset += 2
                value = data[h_offset:h_offset+val_len].decode('utf-8', errors='replace')
                h_offset += val_len
                headers[name] = value
            else:
                break
        
        # Parse payload
        payload_start = offset + 12 + headers_length
        payload_end = offset + total_length - 4
        payload = None
        if payload_end > payload_start:
            payload_bytes = data[payload_start:payload_end]
            try:
                payload = json.loads(payload_bytes.decode('utf-8', errors='replace').strip())
            except:
                payload = {"_raw_size": len(payload_bytes)}
        
        event_type = headers.get(":event-type", "unknown")
        events.append({"type": event_type, "payload": payload, "size": total_length})
        offset += total_length
    
    return events, len(data)


def analyze_request(dirpath):
    """深度分析单个请求"""
    name = os.path.basename(dirpath)
    issues = []
    info = []
    
    req_path = os.path.join(dirpath, "request_body.json")
    kiro_path = os.path.join(dirpath, "kiro_request_body.json")
    resp_mod_path = os.path.join(dirpath, "response_stream_modified.txt")
    resp_raw_path = os.path.join(dirpath, "response_stream_raw.bin")
    app_logs_path = os.path.join(dirpath, "app_logs.txt")
    error_path = os.path.join(dirpath, "error_info.json")
    
    # === 1. 请求分析 ===
    req_data = None
    if os.path.exists(req_path):
        with open(req_path) as f:
            req_data = json.load(f)
        model = req_data.get("model", "?")
        msgs = req_data.get("messages", [])
        tools = req_data.get("tools", [])
        
        # 计算总 content 大小
        total_content_size = 0
        for m in msgs:
            c = m.get("content")
            if isinstance(c, str):
                total_content_size += len(c)
            elif isinstance(c, list):
                total_content_size += sum(len(json.dumps(b, ensure_ascii=False)) for b in c)
        
        info.append(f"model={model} msgs={len(msgs)} tools={len(tools)} content_size={total_content_size}")
        
        # 检查是否有 orphaned tool_results
        for i, m in enumerate(msgs):
            if isinstance(m.get("content"), list):
                for block in m["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        if block.get("is_error"):
                            tid = block.get("tool_use_id", "?")[:25]
                            inner = block.get("content", "")
                            if isinstance(inner, list):
                                inner = str(inner[0].get("text", ""))[:80] if inner else ""
                            elif isinstance(inner, str):
                                inner = inner[:80]
                            info.append(f"  msg[{i}] has ERROR tool_result tid={tid}: {inner}")
    
    # === 2. Kiro payload 大小 ===
    if os.path.exists(kiro_path):
        kiro_size = os.path.getsize(kiro_path)
        info.append(f"kiro_payload={kiro_size}b")
        if kiro_size > 500000:
            issues.append(f"⚠️ LARGE PAYLOAD: {kiro_size}b (>500KB, 可能触发 400 错误)")
    
    # === 3. 错误检查 ===
    if os.path.exists(error_path):
        with open(error_path) as f:
            err = json.load(f)
        issues.append(f"❌ ERROR: HTTP {err.get('status_code')} - {err.get('error_message', '')[:100]}")
    
    # === 4. Raw binary 分析 ===
    raw_events = []
    raw_size = 0
    if os.path.exists(resp_raw_path):
        raw_events, raw_size = parse_raw_binary_frames(resp_raw_path)
        event_types = {}
        for e in raw_events:
            t = e["type"]
            event_types[t] = event_types.get(t, 0) + 1
        info.append(f"raw_size={raw_size}b events={dict(event_types)}")
        
        # 检查是否有 messageStopEvent
        has_stop = any(e["type"] == "messageStopEvent" for e in raw_events)
        has_metering = any(e["type"] == "meteringEvent" for e in raw_events)
        has_context = any(e["type"] == "contextUsageEvent" for e in raw_events)
        
        if not has_stop and raw_size > 100:
            issues.append("⚠️ NO messageStopEvent in raw stream (可能流被截断)")
        
        # toolUseEvent 的 input 是流式分片的，不检查单个 frame 的 JSON 完整性
        # 只统计 tool 类型
        tool_event_names = {}
        for e in raw_events:
            if e["type"] == "toolUseEvent" and e.get("payload"):
                p = e["payload"]
                tn = p.get("name", "input_chunk")
                tool_event_names[tn] = tool_event_names.get(tn, 0) + 1
        if tool_event_names:
            info.append(f"tool_events={dict(tool_event_names)}")
    
    # === 5. Modified response 分析 ===
    if os.path.exists(resp_mod_path):
        chunks = parse_response_modified(resp_mod_path)
        details = extract_response_details(chunks)
        
        info.append(f"chunks={details['chunk_count']} finish={details['finish_reason']} done={details['has_done']}")
        
        if details["usage"]:
            u = details["usage"]
            info.append(f"usage: prompt={u.get('prompt_tokens','?')} completion={u.get('completion_tokens','?')}")
        
        if details["reasoning"]:
            info.append(f"thinking={len(details['reasoning'])}chars")
        
        if details["text"]:
            preview = details['text'][:120].replace('\n', '\\n')
            info.append(f"content={len(details['text'])}chars: {preview}")
        
        # 检查 tool calls
        for idx in sorted(details["tool_calls"].keys()):
            tc = details["tool_calls"][idx]
            validity, parsed = check_tool_call_validity(tc)
            
            if validity == "OK" and parsed:
                if tc["name"] == "Write":
                    fp = parsed.get("file_path", parsed.get("filePath", "?"))
                    contents = parsed.get("contents", parsed.get("content", ""))
                    info.append(f"  tool[{idx}] Write file={fp} contents={len(contents)}chars [OK]")
                elif tc["name"] == "StrReplace":
                    fp = parsed.get("file_path", "?")
                    old = parsed.get("old_string", "")
                    new = parsed.get("new_string", "")
                    info.append(f"  tool[{idx}] StrReplace file={fp} old={len(old)} new={len(new)} [OK]")
                else:
                    info.append(f"  tool[{idx}] {tc['name']} args={len(tc['args'])}b [OK]")
            elif validity == "EMPTY_ARGS":
                issues.append(f"❌ tool[{idx}] {tc['name']} has EMPTY args")
            else:
                issues.append(f"❌ tool[{idx}] {tc['name']} args={len(tc['args'])}b {validity}")
                info.append(f"  tool[{idx}] {tc['name']} args_tail: ...{tc['args'][-80:]}")
        
        # 检查 finish_reason
        if not details["finish_reason"] and not details["has_done"]:
            if details["chunk_count"] > 0:
                issues.append("⚠️ NO finish_reason and NO [DONE] (流未正常结束)")
        
        # 检查是否有 tool_calls 但 finish_reason 不是 tool_calls
        if details["tool_calls"] and details["finish_reason"] != "tool_calls":
            if details["finish_reason"]:
                issues.append(f"⚠️ Has tool_calls but finish_reason={details['finish_reason']} (应该是 tool_calls)")
    else:
        if raw_size > 100:
            issues.append("⚠️ NO response_stream_modified.txt (debug_logger 没记录到修改后的响应)")
    
    # === 6. App logs 关键信息 ===
    if os.path.exists(app_logs_path):
        with open(app_logs_path) as f:
            logs = f.read()
        for line in logs.split("\n"):
            line = line.strip()
            for kw in ["truncat", "ERROR", "recovery", "Anti-lazy", "Improperly", "refusal", "429"]:
                if kw.lower() in line.lower():
                    info.append(f"  LOG: {line[:150]}")
                    break
    
    # === 7. 两个并行会话的检测 ===
    # rqx 同时有两个 Cursor 会话（Ask mode 和 Agent mode），检查是否有串扰
    
    return name, info, issues


def main():
    trace_dir = sys.argv[1] if len(sys.argv) > 1 else "trace_logs/rqx"
    
    dirs = sorted([
        os.path.join(trace_dir, d)
        for d in os.listdir(trace_dir)
        if os.path.isdir(os.path.join(trace_dir, d)) and d.startswith("req_")
    ])
    
    print(f"共 {len(dirs)} 个请求\n")
    
    total_issues = 0
    for d in dirs:
        name, info, issues = analyze_request(d)
        
        # 打印
        marker = "🔴" if issues else "🟢"
        print(f"{marker} {name}")
        for line in info:
            print(f"  {line}")
        if issues:
            total_issues += len(issues)
            for issue in issues:
                print(f"  {issue}")
        print()
    
    print(f"{'='*60}")
    print(f"总计: {len(dirs)} 请求, {total_issues} 个问题")


if __name__ == "__main__":
    main()
