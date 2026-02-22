import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/tools_definition.json'
with open(path) as f:
    tools = json.load(f)

print(f"Total tools: {len(tools)}")
print()

for i, t in enumerate(tools):
    if not t:
        continue
    # Anthropic format: name/description/input_schema at top level
    # OpenAI format: function.name/function.description/function.parameters
    name = t.get('name') or (t.get('function') or {}).get('name', '?')
    desc = t.get('description') or (t.get('function') or {}).get('description', '') or ''
    schema = t.get('input_schema') or (t.get('function') or {}).get('parameters') or {}
    props = schema.get('properties', {}) if isinstance(schema, dict) else {}
    required = schema.get('required', []) if isinstance(schema, dict) else []
    
    param_list = []
    for pname, pinfo in props.items():
        ptype = pinfo.get('type', '?') if isinstance(pinfo, dict) else '?'
        pdesc = (pinfo.get('description', '') if isinstance(pinfo, dict) else '')[:80]
        req_mark = '*' if pname in required else ' '
        param_list.append(f"    {req_mark}{pname}: {ptype} — {pdesc}")
    
    print(f"[{i:2d}] {name} (desc: {len(desc)} chars)")
    if param_list:
        print('\n'.join(param_list))
    else:
        print("    (no params)")
    print()
