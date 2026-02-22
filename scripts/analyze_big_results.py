#!/usr/bin/env python3
"""分析最大的 tool_result 内容。"""
import json
import sys

log_file = sys.argv[1] if len(sys.argv) > 1 else "/opt/apollo/compression_logs/req_052254_before.json"

with open(log_file) as f:
    data = json.load(f)

msgs = data["messages"]
for mi, m in enumerate(msgs):
    if m.get("role") != "user":
        continue
    c = m.get("content", "")
    if not isinstance(c, list):
        continue
    for bi, block in enumerate(c):
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        bc = block.get("content", "")
        if isinstance(bc, list):
            text = "\n".join(sub.get("text", "") for sub in bc if isinstance(sub, dict))
        elif isinstance(bc, str):
            text = bc
        else:
            text = ""
        if len(text) > 5000:
            tid = block.get("tool_use_id", "?")[:25]
            lines = text.split("\n", 5)
            print(f"msg[{mi}] block[{bi}] {len(text):>7} chars  id={tid}")
            for l in lines[:3]:
                print(f"  {l[:150]}")
            print()

# 也看 after
after_file = log_file.replace("_before.json", "_after.json")
try:
    with open(after_file) as f:
        after_data = json.load(f)
    print("=" * 80)
    print("AFTER compression:")
    print()
    a_msgs = after_data["messages"]
    for mi, m in enumerate(a_msgs):
        if m.get("role") != "user":
            continue
        c = m.get("content", "")
        if not isinstance(c, list):
            continue
        for bi, block in enumerate(c):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            bc = block.get("content", "")
            if isinstance(bc, list):
                text = "\n".join(sub.get("text", "") for sub in bc if isinstance(sub, dict))
            elif isinstance(bc, str):
                text = bc
            else:
                text = ""
            if len(text) > 3000:
                tid = block.get("tool_use_id", "?")[:25]
                lines = text.split("\n", 5)
                print(f"msg[{mi}] block[{bi}] {len(text):>7} chars  id={tid}")
                for l in lines[:3]:
                    print(f"  {l[:150]}")
                print()
except FileNotFoundError:
    pass
