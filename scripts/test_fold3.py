#!/usr/bin/env python3
"""完整测试 — 检查最终结果的角色序列和 orphan tool_result。"""
import json, os, sys

sys.path.insert(0, '/opt/apollo')
from core.context_compression import compress_context

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
data = json.load(open(os.path.join(log_dir, files[-1])))
msgs = data['messages']
tools = data.get('tools')

compressed, stats = compress_context(msgs, tools, context_window=128000)

print("Before: %d msgs, %dK tokens" % (len(msgs), data.get('token_estimate', 0) // 1000))
print("After: %d msgs, %dK tokens (level %d)" % (len(compressed), stats['final_tokens'] // 1000, stats['level']))

# 检查角色序列
print("\nRole sequence:")
for i, m in enumerate(compressed):
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        desc = 'str(%d)' % len(content)
    elif isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'text':
                    t = b.get('text', '')
                    if '[Previously' in t or '[Results' in t:
                        parts.append('FOLD')
                    else:
                        parts.append('text(%d)' % len(t))
                elif bt == 'tool_result':
                    parts.append('TR')
                elif bt == 'tool_use':
                    parts.append('TU(%s)' % b.get('name', '?'))
                else:
                    parts.append(bt)
        desc = '[%s]' % ', '.join(parts)
    else:
        desc = '?'
    print('  [%2d] %-10s %s' % (i, role, desc))

# 检查 orphan tool_result
tool_use_ids = set()
for m in compressed:
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                tool_use_ids.add(b.get('id', ''))
    tc = m.get('tool_calls') or []
    for call in tc:
        if isinstance(call, dict):
            tool_use_ids.add(call.get('id', ''))

orphans = 0
for m in compressed:
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_result':
                tuid = b.get('tool_use_id', '')
                if tuid and tuid not in tool_use_ids:
                    orphans += 1

print("\nOrphan tool_results: %d" % orphans)
if orphans > 0:
    print("!!! WARNING: orphan tool_results will cause API errors!")
