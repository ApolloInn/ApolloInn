import json
from collections import defaultdict

with open('/opt/apollo/compression_logs/req_194124_before.json') as f:
    data = json.load(f)

msgs = data['messages']

tool_id_to_name = {}
tool_id_to_path = {}
for m in msgs:
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                tid = b.get('id', '')
                tname = b.get('name', '')
                inp = b.get('input', {})
                path = ''
                if isinstance(inp, dict):
                    path = inp.get('path', '') or inp.get('relative_workspace_path', '') or ''
                if tid:
                    tool_id_to_name[tid] = tname
                    if path:
                        tool_id_to_path[tid] = path

file_reads = defaultdict(list)

for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for j, b in enumerate(content):
        if not isinstance(b, dict) or b.get('type') != 'tool_result':
            continue
        tool_use_id = b.get('tool_use_id', '')
        tool_name = tool_id_to_name.get(tool_use_id, '')
        if tool_name not in ('Read', 'read_file', 'Grep', 'grep', 'Search'):
            continue
        bc = b.get('content', '')
        text = ''
        if isinstance(bc, str):
            text = bc
        elif isinstance(bc, list):
            for sub in bc:
                if isinstance(sub, dict) and sub.get('type') == 'text':
                    text += sub.get('text', '')
        if len(text) < 200:
            continue
        path = tool_id_to_path.get(tool_use_id, '')
        if not path:
            continue
        file_reads[path].append((i, j, len(text)))

print('=== File read frequency ===')
total_saved = 0
for path, reads in sorted(file_reads.items(), key=lambda x: -len(x[1])):
    short = path.split('/')[-1]
    read_count = len(reads)
    total_chars = sum(r[2] for r in reads)
    if read_count >= 2:
        saved = sum(r[2] for r in reads[:-1])
        total_saved += saved
        print(f'  {short:30s}  reads={read_count:2d}  total={total_chars:6d} chars  dedup_saves={saved:6d} chars')
    else:
        print(f'  {short:30s}  reads={read_count:2d}  total={total_chars:6d} chars  (no dedup)')

print(f'\nTotal chars saved by dedup: {total_saved:,d} (~{total_saved//2:,d} tokens)')
print(f'Original token estimate: {data.get("token_estimate", "?")}')
