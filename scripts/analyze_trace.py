# NOTE: 此脚本在服务器上运行，路径 /opt/apollo 对应本地 server/ 目录
#!/usr/bin/env python3
"""分析 trace_logs 中 rqx 用户的每一次请求的完整信息流。"""
import json
import sys
import os
import struct

def parse_request(path):
    """解析 request_body.json (Cursor -> Gateway)"""
    with open(path) as f:
        data = json.load(f)
    return data

def summarize_messages(msgs):
    """打印每条消息的摘要"""
    for i, m in enumerate(msgs):
        role = m.get("role", "?")
        c = m.get("content")
        tc = m.get("tool_calls")
        tid = m.get("tool_call_id")

        if isinstance(c, str):
            clen = len(c)
        elif isinstance(c, list):
            clen = sum(len(json.dumps(b, ensure_ascii=False)) for b in c)
        else:
            clen = 0

        extra = ""
        if tc:
            extra += " tool_calls=%d" % len(tc)
        if tid:
            extra += " tid=%s" % tid[:25]

        print("    [%d] %s(%d)%s" % (i, role, clen, extra))

        # tool_calls 详情
        if tc:
            for j, call in enumerate(tc):
                fn = call.get("function", {})
                name = fn.get("name", "?")
                args = fn.get("arguments", "")
                arglen = len(args) if isinstance(args, str) else len(str(args))
                cid = call.get("id", "?")[:30]
                print("         tc[%d]: %s(args=%d) id=%s" % (j, name, arglen, cid))

        # content 是 list 时的详情
        if isinstance(c, list):
            for j, block in enumerate(c):
                if not isinstance(block, dict):
                    continue
                bt = block.get("type", "?")
                if bt == "tool_use":
                    name = block.get("name", "?")
                    bid = block.get("id", "?")[:30]
                    inp = block.get("input", {})
                    if isinstance(inp, dict):
                        if name == "Write":
                            fp = inp.get("file_path", "?")
                            contents = inp.get("contents", "")
                            print("         block[%d]: tool_use %s id=%s file=%s contents=%d chars" % (j, name, bid, fp, len(contents)))
                        else:
                            print("         block[%d]: tool_use %s id=%s input_keys=%s" % (j, name, bid, list(inp.keys())))
                elif bt == "tool_result":
                    tuid = block.get("tool_use_id", "?")[:30]
                    inner = block.get("content", "")
                    if isinstance(inner, str):
                        ilen = len(inner)
                        preview = inner[:80].replace("\n", "\\n")
                    elif isinstance(inner, list):
                        ilen = sum(len(json.dumps(x, ensure_ascii=False)) for x in inner)
                        preview = "[%d sub-blocks]" % len(inner)
                    else:
                        ilen = 0
                        preview = str(inner)[:80]
                    is_err = block.get("is_error", False)
                    err_tag = " [ERROR]" if is_err else ""
                    print("         block[%d]: tool_result%s tid=%s len=%d: %s" % (j, err_tag, tuid, ilen, preview))
                elif bt == "text":
                    txt = block.get("text", "")
                    print("         block[%d]: text(%d): %s" % (j, len(txt), txt[:100].replace("\n", "\\n")))


def parse_response_modified(path):
    """解析 response_stream_modified.txt (Gateway -> Cursor)"""
    with open(path) as f:
        data = f.read()
    
    chunks = []
    for line in data.split("\n"):
        line = line.strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                chunk = json.loads(line[6:])
                chunks.append(chunk)
            except json.JSONDecodeError:
                pass
        elif line == "data: [DONE]":
            chunks.append({"_done": True})
    return chunks

def summarize_response(chunks):
    """打印响应摘要"""
    text_content = ""
    reasoning_content = ""
    tool_calls = {}  # idx -> {name, args_len, id}
    finish_reason = None
    usage = None

    for chunk in chunks:
        if chunk.get("_done"):
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
            text_content += delta["content"]
        if "reasoning_content" in delta:
            reasoning_content += delta["reasoning_content"]
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

    if reasoning_content:
        print("    [thinking] %d chars: %s" % (len(reasoning_content), reasoning_content[:150].replace("\n", "\\n")))
    if text_content:
        print("    [content] %d chars: %s" % (len(text_content), text_content[:200].replace("\n", "\\n")))
    if tool_calls:
        for idx in sorted(tool_calls.keys()):
            tc = tool_calls[idx]
            args_str = tc["args"]
            # 尝试解析 args 看看是否完整
            args_valid = False
            args_preview = ""
            try:
                parsed = json.loads(args_str)
                args_valid = True
                if tc["name"] == "Write":
                    fp = parsed.get("file_path", "?")
                    contents = parsed.get("contents", "")
                    args_preview = "file=%s contents=%d chars" % (fp, len(contents))
                elif tc["name"] == "StrReplace":
                    fp = parsed.get("file_path", "?")
                    old = parsed.get("old_string", "")
                    new = parsed.get("new_string", "")
                    args_preview = "file=%s old=%d new=%d" % (fp, len(old), len(new))
                else:
                    args_preview = "keys=%s" % list(parsed.keys())
            except json.JSONDecodeError:
                args_preview = "INVALID JSON! last 50 chars: %s" % args_str[-50:]
            
            valid_tag = "OK" if args_valid else "BROKEN"
            print("    [tool_call %d] %s id=%s args=%d [%s] %s" % (
                idx, tc["name"], tc["id"][:25], len(args_str), valid_tag, args_preview))
    
    print("    [finish_reason] %s" % finish_reason)
    if usage:
        print("    [usage] prompt=%s completion=%s" % (usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?")))


def analyze_dir(dirpath):
    """分析一个请求目录"""
    name = os.path.basename(dirpath)
    
    req_path = os.path.join(dirpath, "request_body.json")
    kiro_path = os.path.join(dirpath, "kiro_request_body.json")
    resp_mod_path = os.path.join(dirpath, "response_stream_modified.txt")
    resp_raw_path = os.path.join(dirpath, "response_stream_raw.bin")
    app_logs_path = os.path.join(dirpath, "app_logs.txt")
    
    print("=" * 80)
    print("REQUEST: %s" % name)
    print("=" * 80)
    
    # 1. Cursor -> Gateway
    if os.path.exists(req_path):
        req = parse_request(req_path)
        model = req.get("model", "?")
        stream = req.get("stream", "?")
        msgs = req.get("messages", [])
        tools = req.get("tools", [])
        tool_names = []
        for t in tools:
            if "function" in t:
                tool_names.append(t["function"].get("name", "?"))
            else:
                tool_names.append(t.get("name", "?"))
        print("\n  [1] CURSOR -> GATEWAY (request_body.json)")
        print("  Model: %s, Stream: %s, Messages: %d, Tools: %d" % (model, stream, len(msgs), len(tools)))
        if tool_names:
            print("  Tool names: %s" % tool_names)
        summarize_messages(msgs)
    else:
        print("\n  [1] CURSOR -> GATEWAY: (no file)")
    
    # 2. Gateway -> Kiro
    if os.path.exists(kiro_path):
        kiro = parse_request(kiro_path)
        print("\n  [2] GATEWAY -> KIRO (kiro_request_body.json)")
        print("  Size: %d bytes" % os.path.getsize(kiro_path))
        # Kiro payload 结构不同，打印关键字段
        conv_id = kiro.get("conversationState", {}).get("conversationId", "?")
        msgs_kiro = kiro.get("assistantResponseConfiguration", {}).get("conversationState", {})
        print("  ConversationId: %s" % conv_id)
        print("  Keys: %s" % list(kiro.keys()))
    else:
        print("\n  [2] GATEWAY -> KIRO: (no file)")
    
    # 3. Kiro -> Gateway (raw binary)
    if os.path.exists(resp_raw_path):
        raw_size = os.path.getsize(resp_raw_path)
        print("\n  [3] KIRO -> GATEWAY (response_stream_raw.bin)")
        print("  Raw size: %d bytes" % raw_size)
    else:
        print("\n  [3] KIRO -> GATEWAY: (no file)")
    
    # 4. Gateway -> Cursor
    if os.path.exists(resp_mod_path):
        chunks = parse_response_modified(resp_mod_path)
        print("\n  [4] GATEWAY -> CURSOR (response_stream_modified.txt)")
        print("  Chunks: %d, Size: %d bytes" % (len(chunks), os.path.getsize(resp_mod_path)))
        summarize_response(chunks)
    else:
        print("\n  [4] GATEWAY -> CURSOR: (no file / still streaming)")
    
    # 5. App logs 摘要
    if os.path.exists(app_logs_path):
        with open(app_logs_path) as f:
            logs = f.read()
        # 找关键日志
        important = []
        for line in logs.split("\n"):
            for kw in ["truncat", "ERROR", "WARNING", "recovery", "compression", "Anti-lazy"]:
                if kw.lower() in line.lower():
                    important.append(line.strip())
                    break
        if important:
            print("\n  [5] APP LOGS (important lines):")
            for line in important[:10]:
                print("    %s" % line)
    
    print()


def main():
    trace_dir = sys.argv[1] if len(sys.argv) > 1 else "/opt/apollo/trace_logs/rqx"
    
    if not os.path.exists(trace_dir):
        print("Directory not found: %s" % trace_dir)
        return
    
    dirs = sorted([
        os.path.join(trace_dir, d) 
        for d in os.listdir(trace_dir) 
        if os.path.isdir(os.path.join(trace_dir, d)) and d.startswith("req_")
    ])
    
    print("Found %d requests for rqx" % len(dirs))
    print()
    
    for d in dirs:
        analyze_dir(d)


if __name__ == "__main__":
    main()
