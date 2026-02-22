import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

msgs = data.get('messages', [])
tools = data.get('tools', [])

print('Model:', data.get('model'))
print('Messages:', len(msgs))
print('Tools:', len(tools))
print()

# 按 role 统计
role_stats = {}
total_chars = 0
for m in msgs:
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        size = len(content)
    elif isinstance(content, list):
        size = len(json.dumps(content, ensure_ascii=False))
    else:
        size = 0
    tc = m.get('tool_calls', [])
    if tc:
        size += len(json.dumps(tc, ensure_ascii=False))
    if role not in role_stats:
        role_stats[role] = {'count': 0, 'chars': 0, 'max': 0}
    role_stats[role]['count'] += 1
    role_stats[role]['chars'] += size
    role_stats[role]['max'] = max(role_stats[role]['max'], size)
    total_chars += size

print('=== By Role ===')
for role, s in sorted(role_stats.items()):
    pct = s['chars'] * 100.0 / total_chars if total_chars else 0
    print('  %s: %d msgs, %s chars (%.1f%%), max=%s' % (role, s['count'], format(s['chars'], ','), pct, format(s['max'], ',')))
print('  TOTAL: %s chars' % format(total_chars, ','))
print()

# Tools 大小
tools_size = len(json.dumps(tools, ensure_ascii=False))
print('Tools JSON size: %s chars' % format(tools_size, ','))
print()

# 找最大的消息
print('=== Top 10 Largest Messages ===')
msg_sizes = []
for i, m in enumerate(msgs):
    content = m.get('content', '')
    if isinstance(content, str):
        size = len(content)
    elif isinstance(content, list):
        size = len(json.dumps(content, ensure_ascii=False))
    else:
        size = 0
    tc = m.get('tool_calls', [])
    if tc:
        size += len(json.dumps(tc, ensure_ascii=False))
    preview = ''
    if isinstance(content, str):
        preview = content[:100].replace('\n', ' ')
    elif isinstance(content, list):
        preview = '(list: %d blocks)' % len(content)
    msg_sizes.append((i, m.get('role'), size, preview))

msg_sizes.sort(key=lambda x: -x[2])
for rank, (idx, role, size, preview) in enumerate(msg_sizes[:10]):
    print('  #%d [msg %d] %s: %s chars - %s' % (rank+1, idx, role, format(size, ','), preview[:80]))
print()

# tool_result 统计
tr_sizes = []
for i, m in enumerate(msgs):
    if m.get('role') == 'user' and isinstance(m.get('content'), list):
        for block in m['content']:
            if isinstance(block, dict) and block.get('type') == 'tool_result':
                tr_content = block.get('content', '')
                if isinstance(tr_content, list):
                    tr_size = len(json.dumps(tr_content, ensure_ascii=False))
                elif isinstance(tr_content, str):
                    tr_size = len(tr_content)
                else:
                    tr_size = 0
                tool_id = block.get('tool_use_id', '')[:20]
                tr_sizes.append((i, tool_id, tr_size))
    elif m.get('role') == 'tool':
        content = m.get('content', '')
        tr_size = len(content) if isinstance(content, str) else len(json.dumps(content, ensure_ascii=False))
        tool_id = m.get('tool_call_id', '')[:20]
        tr_sizes.append((i, tool_id, tr_size))

tr_sizes.sort(key=lambda x: -x[2])
print('=== Top 10 Largest Tool Results (%d total) ===' % len(tr_sizes))
for idx, tid, size in tr_sizes[:10]:
    print('  msg#%d %s: %s chars' % (idx, tid, format(size, ',')))
print()

# assistant(92) 模式 — 截断重试
print('=== Tiny Assistant Messages (< 200 chars) ===')
tiny_count = 0
for i, m in enumerate(msgs):
    if m.get('role') == 'assistant':
        content = m.get('content', '')
        if isinstance(content, str):
            size = len(content)
        elif isinstance(content, list):
            size = len(json.dumps(content, ensure_ascii=False))
        else:
            size = 0
        if size < 200 and size > 0:
            tiny_count += 1
            preview = content[:80].replace('\n', ' ') if isinstance(content, str) else '(list)'
            print('  msg#%d: %d chars - %s' % (i, size, preview))
print('  Total: %d' % tiny_count)
print()

# Error: Invalid arguments 循环
print('=== Error: Invalid arguments ===')
error_count = 0
for i, m in enumerate(msgs):
    content = m.get('content', '')
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                bc = block.get('content', '')
                if isinstance(bc, list):
                    for sub in bc:
                        if isinstance(sub, dict) and 'Invalid arguments' in str(sub.get('text', '')):
                            error_count += 1
                            print('  msg#%d tool_use_id=%s' % (i, block.get('tool_use_id', '')[:30]))
                elif isinstance(bc, str) and 'Invalid arguments' in bc:
                    error_count += 1
    elif isinstance(content, str) and 'Invalid arguments' in content:
        error_count += 1
print('  Total: %d' % error_count)
