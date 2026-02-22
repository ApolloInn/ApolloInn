# NOTE: 此脚本在服务器上运行，路径 /opt/apollo 对应本地 server/ 目录
import os, json

trace_dir = "/opt/apollo/trace_logs/rqx"
dirs = sorted(os.listdir(trace_dir))

# Group by session (by time gap > 5 min)
sessions = []
current_session = []
prev_time = None

for d in dirs:
    parts = d.split("_")
    time_str = parts[1]
    h, m, s = int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6])
    t = h * 3600 + m * 60 + s
    if prev_time is not None and (t - prev_time) > 300:
        if current_session:
            sessions.append(current_session)
        current_session = []
    current_session.append(d)
    prev_time = t

if current_session:
    sessions.append(current_session)

print("Total trace dirs:", len(dirs))
print("Sessions detected:", len(sessions))
for i, s in enumerate(sessions):
    print("  Session %d: %s ~ %s (%d requests)" % (i+1, s[0], s[-1], len(s)))
print()

def analyze_session(session_dirs, label):
    print("=== %s: %s ~ %s (%d requests) ===" % (label, session_dirs[0], session_dirs[-1], len(session_dirs)))
    print()
    
    results = []
    
    for req_dir in session_dirs:
        path = os.path.join(trace_dir, req_dir)
        
        # Read client request
        client_file = os.path.join(path, "request_body.json")
        kiro_file = os.path.join(path, "kiro_request_body.json")
        response_file = os.path.join(path, "response_final_to_cursor.txt")
        raw_file = os.path.join(path, "response_stream_raw.bin")
        logs_file = os.path.join(path, "app_logs.txt")
        
        model = "?"
        msg_count = 0
        tool_count = 0
        tc_in_msgs = 0
        tr_in_msgs = 0
        
        if os.path.exists(client_file):
            try:
                with open(client_file) as f:
                    client = json.load(f)
                model = client.get("model", "?")
                msgs = client.get("messages", [])
                msg_count = len(msgs)
                tools = client.get("tools", [])
                tool_count = len(tools)
                
                for m in msgs:
                    if m.get("tool_calls"):
                        tc_in_msgs += len(m["tool_calls"])
                    if isinstance(m.get("content"), list):
                        for b in m["content"]:
                            if isinstance(b, dict):
                                if b.get("type") == "tool_use":
                                    tc_in_msgs += 1
                                if b.get("type") == "tool_result":
                                    tr_in_msgs += 1
                    if m.get("role") == "tool":
                        tr_in_msgs += 1
            except Exception as e:
                pass
        
        # Parse response chunks from response_final_to_cursor.txt
        chunk_count = 0
        finish_reason = None
        has_tool_calls_resp = False
        prompt_tokens = 0
        completion_tokens = 0
        resp_tool_call_names = []
        
        if os.path.exists(response_file):
            try:
                with open(response_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("data: ") and line != "data: [DONE]":
                            chunk_count += 1
                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if choices:
                                    fr = choices[0].get("finish_reason")
                                    if fr:
                                        finish_reason = fr
                                    delta = choices[0].get("delta", {})
                                    if "tool_calls" in delta:
                                        has_tool_calls_resp = True
                                        for tc in delta.get("tool_calls", []):
                                            fn = tc.get("function", {})
                                            if fn.get("name"):
                                                resp_tool_call_names.append(fn["name"])
                                usage = data.get("usage", {})
                                if usage.get("prompt_tokens"):
                                    prompt_tokens = usage["prompt_tokens"]
                                if usage.get("completion_tokens"):
                                    completion_tokens = usage["completion_tokens"]
                            except:
                                pass
            except:
                pass
        
        # Check app_logs for errors
        has_403 = False
        has_retry = False
        has_empty_retry = False
        token_used = ""
        
        if os.path.exists(logs_file):
            try:
                with open(logs_file) as f:
                    log_text = f.read()
                if "403" in log_text:
                    has_403 = True
                if "retry" in log_text.lower() or "Retry" in log_text:
                    has_retry = True
                if "Empty stream" in log_text:
                    has_empty_retry = True
                # Extract token ID
                import re
                token_match = re.search(r'token=([a-f0-9]{8,16})', log_text)
                if token_match:
                    token_used = token_match.group(1)[:8]
            except:
                pass
        
        # Status determination
        status = "OK"
        if chunk_count == 0:
            status = "EMPTY_STREAM"
        elif finish_reason is None:
            status = "NO_FINISH"
        elif finish_reason == "stop" and not has_tool_calls_resp and tool_count > 0:
            status = "TEXT_REPLY"
        elif finish_reason == "tool_use" or has_tool_calls_resp:
            status = "TOOL_CALL"
        elif finish_reason == "stop":
            status = "OK_STOP"
        elif finish_reason == "length":
            status = "TRUNCATED"
        
        flags = ""
        if has_403:
            flags += " [403]"
        if has_retry:
            flags += " [RETRY]"
        if has_empty_retry:
            flags += " [EMPTY_RETRY]"
        
        seq = req_dir.split("_")[-1]
        time_str = req_dir.split("_")[1]
        tc_flag = "Y" if has_tool_calls_resp else "N"
        
        tc_names_str = ""
        if resp_tool_call_names:
            tc_names_str = " -> " + ",".join(resp_tool_call_names[:3])
            if len(resp_tool_call_names) > 3:
                tc_names_str += "..."
        
        print("  %s [%s] model=%-20s msgs=%3d tools=%3d tc=%2d tr=%2d | chunks=%3d finish=%-10s tc_resp=%s p=%6d c=%5d tok=%s | %s%s%s" % (
            seq, time_str, model[:20], msg_count, tool_count, tc_in_msgs, tr_in_msgs,
            chunk_count, str(finish_reason), tc_flag, prompt_tokens, completion_tokens,
            token_used or "?", status, flags, tc_names_str))
        
        results.append({
            "seq": seq, "status": status, "finish_reason": finish_reason,
            "chunk_count": chunk_count, "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens, "has_tool_calls_resp": has_tool_calls_resp,
            "tc_in_msgs": tc_in_msgs, "tr_in_msgs": tr_in_msgs, "tool_count": tool_count,
            "msg_count": msg_count, "model": model, "has_403": has_403,
            "has_retry": has_retry, "has_empty_retry": has_empty_retry,
            "token_used": token_used, "resp_tool_call_names": resp_tool_call_names,
        })
    
    print()
    
    # Summary
    statuses = {}
    total_p = 0
    total_c = 0
    total_chunks = 0
    tc_total = 0
    tr_total = 0
    count_403 = 0
    count_retry = 0
    count_empty_retry = 0
    tokens_used = {}
    models_used = {}
    
    for r in results:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        total_p += r["prompt_tokens"]
        total_c += r["completion_tokens"]
        total_chunks += r["chunk_count"]
        tc_total += r["tc_in_msgs"]
        tr_total += r["tr_in_msgs"]
        if r["has_403"]:
            count_403 += 1
        if r["has_retry"]:
            count_retry += 1
        if r["has_empty_retry"]:
            count_empty_retry += 1
        if r["token_used"]:
            tokens_used[r["token_used"]] = tokens_used.get(r["token_used"], 0) + 1
        models_used[r["model"]] = models_used.get(r["model"], 0) + 1
    
    # Check orphaned tool results
    orphaned = 0
    for r in results:
        if r["tr_in_msgs"] > 0 and r["tc_in_msgs"] == 0:
            orphaned += r["tr_in_msgs"]
    
    # Check tool_call extraction accuracy
    tc_match = 0
    tc_mismatch = 0
    for r in results:
        if r["tc_in_msgs"] > 0 or r["tr_in_msgs"] > 0:
            if r["tc_in_msgs"] >= r["tr_in_msgs"]:
                tc_match += 1
            else:
                tc_mismatch += 1
    
    print("=== SUMMARY ===")
    print("Total requests: %d" % len(results))
    print()
    print("Status breakdown:")
    for s, c in sorted(statuses.items()):
        pct = c * 100.0 / len(results)
        print("  %-15s: %3d (%5.1f%%)" % (s, c, pct))
    print()
    print("Token usage: prompt=%s completion=%s total=%s" % (
        format(total_p, ","), format(total_c, ","), format(total_p + total_c, ",")))
    print("Total chunks: %d (avg %.1f per request)" % (total_chunks, total_chunks / len(results) if results else 0))
    print()
    print("Tool stats:")
    print("  Tool calls in input: %d" % tc_total)
    print("  Tool results in input: %d" % tr_total)
    print("  Orphaned tool results (tr without matching tc): %d" % orphaned)
    print("  Tool call extraction: match=%d mismatch=%d" % (tc_match, tc_mismatch))
    print()
    print("Error stats:")
    print("  Requests with 403: %d" % count_403)
    print("  Requests with retry: %d" % count_retry)
    print("  Requests with empty stream retry: %d" % count_empty_retry)
    print()
    print("Token distribution:")
    for t, c in sorted(tokens_used.items(), key=lambda x: -x[1]):
        print("  %s: %d requests" % (t, c))
    print()
    print("Model distribution:")
    for m, c in sorted(models_used.items(), key=lambda x: -x[1]):
        print("  %s: %d requests" % (m, c))
    print()

# Analyze latest session
analyze_session(sessions[-1], "LATEST SESSION (Session %d)" % len(sessions))

# Also show previous session for comparison
if len(sessions) >= 2:
    analyze_session(sessions[-2], "PREVIOUS SESSION (Session %d)" % (len(sessions) - 1))
