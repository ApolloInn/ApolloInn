#!/usr/bin/env python3
"""分析 database.ts 的每次 Read 调用参数 — 搞清楚为什么读了 29 次。"""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'
biggest = max(
    [f for f in os.listdir(log_dir) if f.endswith('_before.json')],
    key=lambda f: os.path.getsize(os.path.join(log_dir, f))
)
data = json.load(open(os.path.join(log_dir, biggest)))
msgs = data['messages']

print(f"=== {biggest}: database.ts 读取参数分析 ===\n")

# 找所有 assistant 消息中对 database.ts 的 Read 调用
for i, m in enumerate(msgs):
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    
    # Anthropic 格式
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict) or b.get('type') != 'tool_use':
                continue
            name = b.get('name', '')
            if name != 'Read':
                continue
            inp = b.get('input', {})
            path = inp.get('path', '')
            if 'database.ts' not in path:
                continue
            # 显示完整参数
            print(f"msg[{i}] Read database.ts:")
            for k, v in inp.items():
                if k == 'path':
                    continue
                print(f"  {k} = {v}")
            if len(inp) == 1:  # 只有 path
                print(f"  (无额外参数 — 全文读取)")
            
            # 看对应的 tool_result 大小
            tid = b.get('id', '')
            # 找下一条 user 消息中的对应 result
            for j in range(i+1, min(i+3, len(msgs))):
                if msgs[j].get('role') != 'user':
                    continue
                uc = msgs[j].get('content', '')
                if not isinstance(uc, list):
                    continue
                for rb in uc:
                    if isinstance(rb, dict) and rb.get('type') == 'tool_result':
                        if rb.get('tool_use_id', '') == tid:
                            bc = rb.get('content', '')
                            if isinstance(bc, str):
                                tlen = len(bc)
                                first = bc[:100]
                            elif isinstance(bc, list):
                                text = '\n'.join(s.get('text','') for s in bc if isinstance(s, dict))
                                tlen = len(text)
                                first = text[:100]
                            else:
                                tlen = 0
                                first = ''
                            print(f"  → result: {tlen} chars")
                            print(f"  → 开头: {first}")
                break
            print()

# 也看看 Grep 对 database.ts 的调用
print("\n=== database.ts Grep 调用 ===\n")
for i, m in enumerate(msgs):
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict) or b.get('type') != 'tool_use':
                continue
            name = b.get('name', '')
            if name != 'Grep':
                continue
            inp = b.get('input', {})
            path = inp.get('path', '')
            if 'database' not in path:
                continue
            print(f"msg[{i}] Grep:")
            for k, v in inp.items():
                val_str = str(v)
                if len(val_str) > 80:
                    val_str = val_str[:80] + '...'
                print(f"  {k} = {val_str}")
            print()
