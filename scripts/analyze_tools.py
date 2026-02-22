"""分析 Cursor 发来的请求中的工具定义和 system prompt 中的工具描述。"""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_194124_before.json'
with open(path) as f:
    data = json.load(f)

msgs = data['messages']

# 1. 看 system prompt 全文（msg[0]）
print("=" * 80)
print("=== SYSTEM PROMPT (msg[0]) — FULL TEXT ===")
print("=" * 80)
m0 = msgs[0]
c0 = m0.get('content', '')
if isinstance(c0, list):
    for b in c0:
        if isinstance(b, dict) and b.get('type') == 'text':
            print(b.get('text', ''))
elif isinstance(c0, str):
    print(c0)

# 2. 看 msg[2] 的所有 text blocks（包含 Ask mode 指令）
print()
print("=" * 80)
print("=== MSG[2] — ALL TEXT BLOCKS ===")
print("=" * 80)
if len(msgs) > 2:
    m2 = msgs[2]
    c2 = m2.get('content', '')
    if isinstance(c2, list):
        for i, b in enumerate(c2):
            if isinstance(b, dict) and b.get('type') == 'text':
                print(f"--- text block [{i}] ({len(b.get('text',''))} chars) ---")
                print(b.get('text', ''))
    elif isinstance(c2, str):
        print(c2)

# 3. 看 assistant 消息中用了哪些工具名
print()
print("=" * 80)
print("=== TOOL NAMES USED BY ASSISTANT ===")
print("=" * 80)
tool_names_used = {}
for i, m in enumerate(msgs):
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                name = b.get('name', '?')
                if name not in tool_names_used:
                    tool_names_used[name] = []
                tool_names_used[name].append(i)
    tc = m.get('tool_calls')
    if tc and isinstance(tc, list):
        for call in tc:
            if isinstance(call, dict):
                name = call.get('function', {}).get('name', '?')
                if name not in tool_names_used:
                    tool_names_used[name] = []
                tool_names_used[name].append(i)

for name, indices in sorted(tool_names_used.items()):
    print(f"  {name}: used in msgs {indices} ({len(indices)} times)")
