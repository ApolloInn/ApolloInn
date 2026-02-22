import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/tools_definition.json'
with open(path) as f:
    tools = json.load(f)

print(f"Total tools: {len(tools)}")
print()

for i, t in enumerate(tools):
    if not t:
        print(f"[{i:2d}] None/empty")
        continue
    func = t.get('function') or t
    if not func:
        print(f"[{i:2d}] No function field")
        continue
    name = func.get('name', '?')
    desc = func.get('description', '') or ''
    params = func.get('parameters') or {}
    props = params.get('properties', {}) if isinstance(params, dict) else {}
    param_names = list(props.keys())
    required = params.get('required', []) if isinstance(params, dict) else []
    
    print(f"[{i:2d}] {name}")
    print(f"     params: {param_names}")
    print(f"     required: {required}")
    print(f"     desc_len: {len(desc)} chars")
    # Show first 200 chars of description
    desc_clean = desc.replace('\n', ' ')[:200]
    print(f"     desc: {desc_clean}")
    print()
