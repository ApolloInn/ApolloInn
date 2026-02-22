#!/usr/bin/env python3
"""分析每个请求的消息流：Kiro输出了什么，Cursor输入了什么，压缩丢了什么。"""
import json
import os
import glob
import sys

log_dir = sys.argv[1] if len(sys.argv) > 1 else "/opt/apollo/compression_logs"
# 可选：只分析指定请求
target_req = sys.argv[2] if len(sys.argv) > 2 else None

def get_text(block):
    bc = block.get("content", "")
    if isinstance(bc, str):
        return bc
    if isinstance(bc, list):
        return "\n".join(sub.get("text", "") for sub in bc if isinstance(sub, dict))
    return block.get("text", "")

def summarize_msg(m, max_preview=80):
    """生成消息的可读摘要。"""
    role = m.get("role", "?")
    content = m.get("content", "")
    tc = m.get("tool_calls") or []

    parts = []

    if isinstance(content, str):
        if content.strip():
            preview = content.strip().replace("\n", " ")[:max_preview]
            parts.append(f'text({len(content)}): "{preview}"')
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            btype = b.get("type", "?")
            if btype == "text":
                txt = b.get("text", "")
                if txt.strip():
                    preview = txt.strip().replace("\n", " ")[:max_preview]
                    parts.append(f'text({len(txt)}): "{preview}"')
            elif btype == "tool_use":
                name = b.get("name", "?")
                inp = b.get("input", {})
                path = inp.get("path", inp.get("relative_workspace_path", ""))
                if path:
                    parts.append(f'{name}("{path}")')
                else:
                    # 显示 input 的 key
                    keys = list(inp.keys())[:3] if isinstance(inp, dict) else []
                    parts.append(f'{name}({",".join(keys)})')
            elif btype == "tool_result":
                tid = b.get("tool_use_id", "?")[:12]
                txt = get_text(b)
                # 提取文件路径
                fpath = "?"
                for line in txt.split("\n", 3)[:3]:
                    line = line.strip()
                    # 去行号
                    import re
                    ln = re.match(r'^\s*\d+\|(.*)', line)
                    if ln:
                        line = ln.group(1).strip()
                    if line.startswith("/") or (len(line) > 2 and line[1] == ":"):
                        fpath = line[:60]
                        break
                    # 检测文件内容特征
                    if line.startswith("Result of search"):
                        fpath = "Glob:" + line[17:60]
                        break
                    if line.startswith("<!DOCTYPE") or line.startswith("<html"):
                        fpath = "HTML"
                        break
                if fpath == "?" and len(txt) > 0:
                    preview = txt[:50].replace("\n", " ")
                    fpath = preview
                parts.append(f'result({len(txt)}) {fpath}')

    # OpenAI format tool_calls
    for call in tc:
        if not isinstance(call, dict):
            continue
        func = call.get("function", {})
        name = func.get("name", "?")
        args_str = func.get("arguments", "")
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except:
            args = {}
        path = ""
        if isinstance(args, dict):
            path = args.get("path", args.get("relative_workspace_path", ""))
        if path:
            parts.append(f'{name}("{path}")')
        else:
            parts.append(f'{name}(...)')

    return parts


def analyze_request(req_id, bf, af):
    with open(bf) as f:
        before = json.load(f)
    with open(af) as f:
        after = json.load(f)

    b_msgs = before.get("messages", [])
    a_msgs = after.get("messages", [])
    orig_tok = before.get("token_estimate", 0)
    final_tok = after.get("token_estimate", 0)

    # 检测分析模式
    is_ask = False
    for m in b_msgs:
        c = m.get("content", "")
        if isinstance(c, str) and "Ask mode is active" in c:
            is_ask = True
            break
        if isinstance(c, list):
            for b2 in c:
                if isinstance(b2, dict) and b2.get("type") == "text" and "Ask mode is active" in b2.get("text", ""):
                    is_ask = True
                    break

    mode = "Ask" if is_ask else "Code"
    print(f"\n{'='*100}")
    print(f"请求 {req_id}  |  {mode}模式  |  {orig_tok//1000}K -> {final_tok//1000}K tokens  |  {len(b_msgs)}条 -> {len(a_msgs)}条消息")
    print(f"{'='*100}")

    # 逐条显示 BEFORE 消息
    print(f"\n--- BEFORE ({len(b_msgs)} msgs) ---")
    for i, m in enumerate(b_msgs):
        role = m.get("role", "?")
        parts = summarize_msg(m)
        # 计算这条消息的大小
        c = m.get("content", "")
        if isinstance(c, str):
            size = len(c)
        elif isinstance(c, list):
            size = sum(len(get_text(b2)) if b2.get("type") == "tool_result" else len(json.dumps(b2, ensure_ascii=False)) for b2 in c if isinstance(b2, dict))
        else:
            size = 0
        tc = m.get("tool_calls")
        if tc:
            size += len(json.dumps(tc, ensure_ascii=False))

        print(f"\n  [{i:2d}] {role:10s} ({size//1000}K chars)")
        for p in parts:
            print(f"       {p}")

    # 找出压缩前后差异最大的 tool_result
    print(f"\n--- 压缩损失分析 ---")
    losses = []
    for mi, m in enumerate(b_msgs):
        if m.get("role") != "user":
            continue
        c = m.get("content", "")
        if not isinstance(c, list):
            continue
        for bi, block in enumerate(c):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            b_text = get_text(block)
            if len(b_text) < 2000:
                continue
            # 找 after 对应
            a_text = ""
            if mi < len(a_msgs):
                ac = a_msgs[mi].get("content", "")
                if isinstance(ac, list) and bi < len(ac):
                    a_text = get_text(ac[bi])
            loss = len(b_text) - len(a_text)
            if loss > 0:
                # 文件路径
                fpath = "?"
                import re
                for line in b_text.split("\n", 5)[:3]:
                    line = line.strip()
                    ln = re.match(r'^\s*\d+\|(.*)', line)
                    if ln:
                        line = ln.group(1).strip()
                    if line.startswith("/"):
                        fpath = line[:80]
                        break
                    if line.startswith("<!DOCTYPE"):
                        fpath = "HTML file"
                        break
                losses.append((loss, len(b_text), len(a_text), fpath, mi, bi))

    losses.sort(key=lambda x: -x[0])
    for loss, blen, alen, fpath, mi, bi in losses[:10]:
        ratio = alen / blen * 100 if blen > 0 else 0
        print(f"  msg[{mi}][{bi}] {blen//1000:>4}K -> {alen//1000:>4}K ({ratio:>5.1f}% kept)  {fpath}")

    # Kiro 最终输出（最后一个 assistant 消息）
    last_assistant = None
    for m in reversed(b_msgs):
        if m.get("role") == "assistant":
            last_assistant = m
            break
    if last_assistant:
        print(f"\n--- Kiro 最后输出 ---")
        parts = summarize_msg(last_assistant)
        for p in parts:
            print(f"  {p}")

    # Cursor 最后输入（最后一个 user 消息）
    last_user = None
    for m in reversed(b_msgs):
        if m.get("role") == "user":
            last_user = m
            break
    if last_user:
        print(f"\n--- Cursor 最后输入 ---")
        parts = summarize_msg(last_user)
        for p in parts[:5]:
            print(f"  {p}")
        if len(parts) > 5:
            print(f"  ... +{len(parts)-5} more blocks")


pairs = {}
for f in sorted(glob.glob(os.path.join(log_dir, "req_*_before.json"))):
    req_id = os.path.basename(f).replace("_before.json", "")
    after_f = f.replace("_before.json", "_after.json")
    if os.path.exists(after_f):
        pairs[req_id] = (f, after_f)

for req_id in sorted(pairs.keys()):
    if target_req and target_req not in req_id:
        continue
    bf, af = pairs[req_id]
    analyze_request(req_id, bf, af)
