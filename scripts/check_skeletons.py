import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_072319_after.json'
with open(path) as f:
    data = json.load(f)

# Show all tool_results with their sizes and first 300 chars
for i, m in enumerate(data['messages']):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for j, b in enumerate(content):
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
        tuid = b.get('tool_use_id', '?')[:20]
        print(f"msg[{i}][{j}] id={tuid} len={len(txt)}")
        # Show first 200 chars
        preview = txt[:200].replace('\n', '\n  ')
        print(f"  {preview}")
        print()
