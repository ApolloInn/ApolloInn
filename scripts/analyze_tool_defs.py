"""分析请求中的 tools 定义（OpenAI function calling 格式）。"""
import json, sys, os

# 尝试从多个可能的位置找到 before.json
path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_194124_before.json'

# 如果文件不存在，尝试从 raw_body 中找
if not os.path.exists(path):
    print(f"File not found: {path}")
    sys.exit(1)

with open(path) as f:
    data = json.load(f)

# compression_logs 的 before.json 只有 messages，没有 tools
# 需要从 debug_logs 中找完整请求
msgs = data.get('messages', [])

print(f"Keys in data: {list(data.keys())}")
print()

# 看看有没有 tools 字段
if 'tools' in data:
    tools = data['tools']
    print(f"Found {len(tools)} tool definitions:")
    for i, t in enumerate(tools):
        if isinstance(t, dict):
            func = t.get('function', t)
            name = func.get('name', '?')
            desc = func.get('description', '')[:100]
            params = func.get('parameters', {})
            param_names = list(params.get('properties', {}).keys()) if isinstance(params, dict) else []
            print(f"  [{i:2d}] {name}")
            print(f"       desc: {desc}")
            print(f"       params: {param_names}")
            print()
else:
    print("No 'tools' field in this file.")
    print("Need to check debug_logs for the full request body.")
    print()
    
    # 从 system prompt 中提取工具相关信息
    print("=== Tools mentioned in system prompt ===")
    m0 = msgs[0] if msgs else {}
    c0 = m0.get('content', '')
    text = ''
    if isinstance(c0, list):
        for b in c0:
            if isinstance(b, dict) and b.get('type') == 'text':
                text = b.get('text', '')
                break
    elif isinstance(c0, str):
        text = c0
    
    # 搜索工具相关关键词
    import re
    # 找所有 tool_use name 值
    tool_names_in_content = set()
    for m in msgs:
        content = m.get('content', '')
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict):
                    if b.get('type') == 'tool_use':
                        tool_names_in_content.add(b.get('name', ''))
                    if b.get('type') == 'tool_result':
                        pass
        tc = m.get('tool_calls')
        if tc and isinstance(tc, list):
            for call in tc:
                if isinstance(call, dict):
                    tool_names_in_content.add(call.get('function', {}).get('name', ''))
    
    print(f"Tool names actually used in conversation: {sorted(tool_names_in_content)}")
    print()
    
    # 看看 assistant 的 tool_use 都传了什么参数
    print("=== Sample tool_use inputs ===")
    seen = set()
    for m in msgs:
        if m.get('role') != 'assistant':
            continue
        content = m.get('content', '')
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'tool_use':
                    name = b.get('name', '')
                    if name in seen:
                        continue
                    seen.add(name)
                    inp = b.get('input', {})
                    print(f"  {name}: {json.dumps(inp, ensure_ascii=False)[:200]}")
