#!/usr/bin/env python3
"""
对比压缩前后，看折叠后的消息内容到底是什么。
"""
import json
import sys
import os

sys.path.insert(0, "/opt/apollo")
from core.context_compression import compress_context, _detect_analysis_mode, estimate_request_tokens

def show_msg(i, m, max_text=300):
    role = m.get("role", "?")
    content = m.get("content", "")
    
    if isinstance(content, str):
        print(f"  [{i:2d}] {role}: {content[:max_text]}")
        if len(content) > max_text:
            print(f"       ... ({len(content)} chars)")
        return
    
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                btype = b.get("type", "?")
                if btype == "text":
                    text = b.get("text", "")
                    parts.append(f"text({len(text)}): {text[:150]}")
                elif btype == "tool_use":
                    name = b.get("name", "?")
                    inp = b.get("input", {})
                    if isinstance(inp, dict):
                        path = inp.get("path", inp.get("pattern", ""))
                    else:
                        path = ""
                    parts.append(f"tool_use: {name}({path})" if path else f"tool_use: {name}")
                elif btype == "tool_result":
                    bc = b.get("content", "")
                    if isinstance(bc, str):
                        text = bc
                    elif isinstance(bc, list):
                        text = " ".join(sub.get("text", "") for sub in bc if isinstance(sub, dict))
                    else:
                        text = str(bc)
                    parts.append(f"tool_result({len(text)}): {text[:100]}")
        
        print(f"  [{i:2d}] {role}:")
        for p in parts:
            print(f"       {p}")
        return
    
    tc = m.get("tool_calls") or []
    if tc:
        print(f"  [{i:2d}] {role}: {len(tc)} tool_calls")
        return
    
    print(f"  [{i:2d}] {role}: ???")


# 找最大的 before 文件
log_dir = "/opt/apollo/compression_logs"
files = []
for fname in os.listdir(log_dir):
    if fname.endswith("_before.json"):
        path = os.path.join(log_dir, fname)
        size = os.path.getsize(path)
        files.append((size, fname, path))
files.sort(reverse=True)

if not files:
    print("No files found")
    sys.exit(1)

size, fname, path = files[0]
print(f"=== {fname} ({size//1024}K) ===\n")

with open(path) as f:
    data = json.load(f)

messages = data.get("messages", [])
tools = data.get("tools")

print(f"Before: {len(messages)} msgs, {estimate_request_tokens(messages, tools)//1000}K tokens")
print()

compressed, stats = compress_context(messages, tools)
print(f"\nAfter: {len(compressed)} msgs, {stats.get('final_tokens', 0)//1000}K tokens (level {stats.get('level', 0)})")
print()

print("=== COMPRESSED MESSAGE FLOW ===")
for i, m in enumerate(compressed):
    show_msg(i, m)
    print()
