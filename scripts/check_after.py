import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_072319_after.json'
with open(path) as f:
    data = json.load(f)

print(f"Messages: {data['message_count']}, Tokens: {data['token_estimate']}, Level: {data['level']}, Saved: {data['tokens_saved']}")
print()

for i, m in enumerate(data['messages']):
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        print(f"[{i}] {role} str({len(content)})")
    elif isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'tool_result':
                    txt = ''
                    c = b.get('content', '')
                    if isinstance(c, list):
                        for x in c:
                            if isinstance(x, dict):
                                txt += x.get('text', '')
                    elif isinstance(c, str):
                        txt = c
                    parts.append(f"tool_result({len(txt)})")
                elif bt == 'tool_use':
                    name = b.get('name', '?')
                    parts.append(f"tool_use({name})")
                elif bt == 'text':
                    parts.append(f"text({len(b.get('text', ''))})")
                else:
                    parts.append(f"{bt}")
            else:
                parts.append("raw")
        print(f"[{i}] {role} [{' | '.join(parts)}]")

# Show a sample skeleton from a compressed tool_result
print("\n=== SAMPLE COMPRESSED TOOL_RESULT ===")
for i, m in enumerate(data['messages']):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for b in content:
        if not isinstance(b, dict) or b.get('type') != 'tool_result':
            continue
        c = b.get('content', '')
        txt = ''
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict):
                    txt += x.get('text', '')
        elif isinstance(c, str):
            txt = c
        if 500 < len(txt) < 5000:
            print(f"--- tool_result (tool_use_id={b.get('tool_use_id','?')[:20]}) ---")
            print(txt[:2000])
            print("...")
            sys.exit(0)

for i, m in enumerate(data['messages']):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for b in content:
        if not isinstance(b, dict) or b.get('type') != 'tool_result':
            continue
        c = b.get('content', '')
        txt = ''
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict):
                    txt += x.get('text', '')
        elif isinstance(c, str):
            txt = c
        if len(txt) > 200:
            print(f"--- tool_result (tool_use_id={b.get('tool_use_id','?')[:20]}) len={len(txt)} ---")
            print(txt[:2000])
            print("...")
            sys.exit(0)
