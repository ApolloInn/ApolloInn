import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_194124_before.json'
with open(path) as f:
    data = json.load(f)

msgs = data['messages']
print(f"Total messages: {len(msgs)}")
print(f"Token estimate: {data.get('token_estimate', '?')}")
print()

for i, m in enumerate(msgs):
    role = m.get('role', '?')
    content = m.get('content', '')
    tc = m.get('tool_calls')
    
    if isinstance(content, str):
        desc = f"str({len(content)})"
    elif isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'tool_result':
                    bc = b.get('content', '')
                    if isinstance(bc, str):
                        tlen = len(bc)
                    elif isinstance(bc, list):
                        tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
                    else:
                        tlen = 0
                    tid = b.get('tool_use_id', '')[:12]
                    parts.append(f"tool_result({tlen})[{tid}]")
                elif bt == 'tool_use':
                    inp = b.get('input', {})
                    name = b.get('name', '?')
                    parts.append(f"tool_use:{name}({len(json.dumps(inp))})")
                elif bt == 'text':
                    parts.append(f"text({len(b.get('text',''))})")
                else:
                    parts.append(f"{bt}(?)")
        desc = "[" + " | ".join(parts) + "]"
    else:
        desc = "empty"
    
    tc_desc = ""
    if tc and isinstance(tc, list):
        tc_names = []
        for call in tc:
            if isinstance(call, dict):
                fn = call.get('function', {}).get('name', '?')
                tc_names.append(fn)
        tc_desc = f" +tool_calls({','.join(tc_names)})"
    
    print(f"[{i:2d}] {role:10s} {desc}{tc_desc}")
