#!/usr/bin/env python3
"""测试折叠效果 — 看压缩后的消息结构。"""
import json, os, sys

sys.path.insert(0, '/opt/apollo')
from core.context_compression import compress_context

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
if not files:
    print("No files")
    sys.exit(1)

# 用最新的
data = json.load(open(os.path.join(log_dir, files[-1])))
msgs = data['messages']
tools = data.get('tools')

print("Testing:", files[-1])
print("Before: %d msgs, %dK tokens" % (len(msgs), data.get('token_estimate', 0) // 1000))

compressed, stats = compress_context(msgs, tools, context_window=128000)

print("\nAfter: %d msgs, %dK tokens (level %d, saved %dK)" % (
    len(compressed), stats['final_tokens'] // 1000,
    stats['level'], stats['tokens_saved'] // 1000
))

# 打印每条消息的结构
print("\n--- Message structure ---")
for i, m in enumerate(compressed):
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        desc = 'str(%d)' % len(content)
        # 如果是摘要，显示内容
        if content.startswith('[Previously') or content.startswith('[Results'):
            desc += ': ' + content[:80]
    elif isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'text':
                    t = b.get('text', '')
                    if t.startswith('[Previously') or t.startswith('[Results'):
                        parts.append('SUMMARY: ' + t[:80])
                    else:
                        parts.append('text(%d)' % len(t))
                elif bt == 'tool_result':
                    bc = b.get('content', '')
                    tlen = len(bc) if isinstance(bc, str) else sum(len(s.get('text','')) for s in bc if isinstance(s, dict)) if isinstance(bc, list) else 0
                    parts.append('tool_result(%d)' % tlen)
                elif bt == 'tool_use':
                    parts.append('tool_use(%s)' % b.get('name', '?'))
                else:
                    parts.append(bt)
        desc = '[' + ', '.join(parts) + ']'
    else:
        desc = 'empty'
    print('[%2d] %-10s %s' % (i, role, desc))
