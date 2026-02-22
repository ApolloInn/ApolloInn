#!/usr/bin/env python3
"""分析被砍掉的 pair 的结构 — 看看保留什么信息才够。"""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
if not files:
    print("No files")
    sys.exit(1)

# 用最新的
data = json.load(open(os.path.join(log_dir, files[-1])))
msgs = data['messages']

print("File:", files[-1])
print("Messages:", len(msgs))

# 找所有 assistant(tool_use) + user(tool_result) 对
for i in range(len(msgs) - 2):
    m_curr = msgs[i]
    m_next = msgs[i + 1]
    m_after = msgs[i + 2] if i + 2 < len(msgs) else None

    if m_curr.get('role') != 'assistant' or m_next.get('role') != 'user':
        continue
    if not m_after or m_after.get('role') != 'assistant':
        continue

    # 检查 assistant 有 tool_use
    content = m_curr.get('content', '')
    tool_uses = []
    assistant_text = ''
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict):
                if b.get('type') == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    path = ''
                    if isinstance(inp, dict):
                        path = inp.get('path') or inp.get('relative_workspace_path') or inp.get('pattern') or ''
                    tool_uses.append('%s(%s)' % (name, os.path.basename(path) if path else ''))
                elif b.get('type') == 'text':
                    assistant_text = b.get('text', '').strip()

    if not tool_uses:
        continue

    # 检查 user 有 tool_result
    next_content = m_next.get('content', '')
    result_sizes = []
    if isinstance(next_content, list):
        for b in next_content:
            if isinstance(b, dict) and b.get('type') == 'tool_result':
                bc = b.get('content', '')
                if isinstance(bc, str):
                    result_sizes.append(len(bc))
                elif isinstance(bc, list):
                    result_sizes.append(sum(len(s.get('text','')) for s in bc if isinstance(s, dict)))
                else:
                    result_sizes.append(0)

    total_result_chars = sum(result_sizes)
    print('\n[%d,%d] %d tool_uses, %d tool_results (%d chars total)' % (
        i, i+1, len(tool_uses), len(result_sizes), total_result_chars
    ))
    if assistant_text:
        print('  assistant text: "%s"' % assistant_text[:120])
    print('  tools: %s' % ', '.join(tool_uses[:10]))
    if len(tool_uses) > 10:
        print('  ... and %d more' % (len(tool_uses) - 10))
