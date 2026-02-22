import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_194124_before.json'
with open(path) as f:
    data = json.load(f)

msgs = data['messages']

# Show system prompt (first 500 chars)
print("=== MSG[0] system prompt (first 500 chars) ===")
m0 = msgs[0]
c0 = m0.get('content', '')
if isinstance(c0, list):
    for b in c0:
        if isinstance(b, dict) and b.get('type') == 'text':
            print(b.get('text', '')[:500])
            break
elif isinstance(c0, str):
    print(c0[:500])

print()
print("=== MSG[1] user query ===")
m1 = msgs[1]
c1 = m1.get('content', '')
if isinstance(c1, list):
    for b in c1:
        if isinstance(b, dict) and b.get('type') == 'text':
            print(b.get('text', '')[:1000])
elif isinstance(c1, str):
    print(c1[:1000])

print()
print("=== MSG[2] (second user msg) ===")
if len(msgs) > 2:
    m2 = msgs[2]
    c2 = m2.get('content', '')
    if isinstance(c2, list):
        for b in c2:
            if isinstance(b, dict) and b.get('type') == 'text':
                print(b.get('text', '')[:500])
    elif isinstance(c2, str):
        print(c2[:500])

# Show what files are being read in each round
print()
print("=== File reads per round ===")

# Build tool_id -> path map
tool_id_to_path = {}
for m in msgs:
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                tid = b.get('id', '')
                name = b.get('name', '')
                inp = b.get('input', {})
                if isinstance(inp, dict):
                    p = inp.get('path', '') or inp.get('relative_workspace_path', '') or ''
                    if p and tid:
                        tool_id_to_path[tid] = p

for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    reads = []
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'tool_result':
            tid = b.get('tool_use_id', '')
            p = tool_id_to_path.get(tid, '?')
            bc = b.get('content', '')
            if isinstance(bc, str):
                tlen = len(bc)
            elif isinstance(bc, list):
                tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
            else:
                tlen = 0
            if tlen > 100:
                short = p.split('/')[-1] if '/' in p else p
                reads.append(f"{short}({tlen})")
    if reads:
        print(f"  msg[{i:2d}]: {' | '.join(reads)}")
