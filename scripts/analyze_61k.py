"""分析 61K 请求的消息结构 — 从最新的 compression_logs 中找"""
import json, sys, os

# 用最新的 before.json（虽然那个是触发了压缩的，但结构类似）
# 或者直接分析 after.json 看压缩后的结构
path = sys.argv[1] if len(sys.argv) > 1 else '/opt/apollo/compression_logs/req_075541_before.json'

with open(path) as f:
    data = json.load(f)

msgs = data.get('messages', [])
print(f"File: {os.path.basename(path)}")
print(f"Messages: {len(msgs)}, Token estimate: {data.get('token_estimate', '?')}")
print()

total_by_type = {}  # role -> total chars

for i, m in enumerate(msgs):
    role = m.get('role', '?')
    content = m.get('content', '')
    
    if isinstance(content, str):
        size = len(content)
        # 看看是什么内容
        preview = content[:150].replace('\n', ' ')
        print(f"[{i:2d}] {role:10s} str({size:6d})  {preview}")
        total_by_type[role] = total_by_type.get(role, 0) + size
    elif isinstance(content, list):
        parts = []
        block_sizes = []
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
                    block_sizes.append(('tool_result', len(txt)))
                elif bt == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    inp_size = len(json.dumps(inp, ensure_ascii=False)) if isinstance(inp, dict) else 0
                    parts.append(f"tool_use({name},{inp_size})")
                    block_sizes.append(('tool_use', inp_size))
                elif bt == 'text':
                    tlen = len(b.get('text', ''))
                    parts.append(f"text({tlen})")
                    block_sizes.append(('text', tlen))
                else:
                    parts.append(f"{bt}")
                    block_sizes.append((bt, 0))
        
        total_size = sum(s for _, s in block_sizes)
        total_by_type[role] = total_by_type.get(role, 0) + total_size
        
        # 只显示前几个 block
        display = ' | '.join(parts[:8])
        if len(parts) > 8:
            display += f' | ... +{len(parts)-8} more'
        print(f"[{i:2d}] {role:10s} [{display}]  total={total_size}")
    
    # tool_calls (OpenAI format)
    tc = m.get('tool_calls')
    if tc and isinstance(tc, list):
        tc_parts = []
        tc_total = 0
        for call in tc:
            if isinstance(call, dict):
                func = call.get('function', {})
                name = func.get('name', '?')
                args = func.get('arguments', '')
                tc_parts.append(f"{name}({len(args)})")
                tc_total += len(args)
        print(f"     + tool_calls: {' | '.join(tc_parts[:5])}  total={tc_total}")
        total_by_type['tool_calls'] = total_by_type.get('tool_calls', 0) + tc_total

print()
print("=== SIZE BY ROLE ===")
for role, size in sorted(total_by_type.items(), key=lambda x: -x[1]):
    print(f"  {role:15s}: {size:8d} chars ({size//2800} tokens est)")

# 找最大的单个内容块
print()
print("=== TOP 10 LARGEST BLOCKS ===")
blocks = []
for i, m in enumerate(msgs):
    content = m.get('content', '')
    role = m.get('role', '?')
    if isinstance(content, str):
        blocks.append((len(content), i, role, 'str', content[:80].replace('\n',' ')))
    elif isinstance(content, list):
        for j, b in enumerate(content):
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
                    tuid = b.get('tool_use_id', '')[:15]
                    blocks.append((len(txt), i, role, f'tool_result[{j}] id={tuid}', txt[:80].replace('\n',' ')))
                elif bt == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    inp_str = json.dumps(inp, ensure_ascii=False)
                    blocks.append((len(inp_str), i, role, f'tool_use({name})', inp_str[:80].replace('\n',' ')))
                elif bt == 'text':
                    txt = b.get('text', '')
                    blocks.append((len(txt), i, role, f'text[{j}]', txt[:80].replace('\n',' ')))

blocks.sort(key=lambda x: -x[0])
for size, idx, role, btype, preview in blocks[:10]:
    print(f"  msg[{idx:2d}] {role:10s} {btype:30s} {size:8d} chars  {preview}")
