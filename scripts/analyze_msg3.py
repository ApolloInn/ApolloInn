import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_194124_after.json'
with open(path) as f:
    data = json.load(f)

msgs = data['messages']
print(f"Messages: {len(msgs)}, Level: {data.get('level','?')}, Tokens: {data.get('token_estimate','?')}, Saved: {data.get('tokens_saved','?')}")
print()

# Show what happened to msg[1] — was the user query preserved?
print("=== MSG[1] user query preserved? ===")
m1 = msgs[1]
c1 = m1.get('content', '')
if isinstance(c1, list):
    for b in c1:
        if isinstance(b, dict) and b.get('type') == 'text':
            t = b.get('text', '')
            print(f"  text block: {len(t)} chars, first 200: {t[:200]}")
elif isinstance(c1, str):
    print(f"  str: {len(c1)} chars, first 200: {c1[:200]}")

# Show the last user msg (msg[8]) tool_results — are they full or compressed?
print()
print("=== Last user msg tool_results (msg[8]) ===")
m_last = msgs[-1]
c_last = m_last.get('content', '')
if isinstance(c_last, list):
    for j, b in enumerate(c_last):
        if isinstance(b, dict) and b.get('type') == 'tool_result':
            bc = b.get('content', '')
            if isinstance(bc, str):
                text = bc
            elif isinstance(bc, list):
                text = ''.join(s.get('text','') for s in bc if isinstance(s, dict))
            else:
                text = ''
            # Show first 200 chars to see if it's compressed or full
            preview = text[:200].replace('\n', '\\n')
            print(f"  [{j}] {len(text)} chars: {preview}")

# Also show msg[4] — the second-to-last round's tool_results
print()
print("=== msg[4] tool_results (second-to-last read round) ===")
if len(msgs) > 4:
    m4 = msgs[4]
    c4 = m4.get('content', '')
    if isinstance(c4, list):
        for j, b in enumerate(c4):
            if isinstance(b, dict) and b.get('type') == 'tool_result':
                bc = b.get('content', '')
                if isinstance(bc, str):
                    text = bc
                elif isinstance(bc, list):
                    text = ''.join(s.get('text','') for s in bc if isinstance(s, dict))
                else:
                    text = ''
                preview = text[:200].replace('\n', '\\n')
                print(f"  [{j}] {len(text)} chars: {preview}")

# Show msg[2] — the earliest surviving tool_results
print()
print("=== msg[2] tool_results (earliest surviving) ===")
if len(msgs) > 2:
    m2 = msgs[2]
    c2 = m2.get('content', '')
    if isinstance(c2, list):
        for j, b in enumerate(c2):
            if isinstance(b, dict) and b.get('type') == 'tool_result':
                bc = b.get('content', '')
                if isinstance(bc, str):
                    text = bc
                elif isinstance(bc, list):
                    text = ''.join(s.get('text','') for s in bc if isinstance(s, dict))
                else:
                    text = ''
                preview = text[:200].replace('\n', '\\n')
                print(f"  [{j}] {len(text)} chars: {preview}")
