#!/usr/bin/env python3
"""深度分析 Cursor 发来的原始请求结构 — 每条消息到底包含什么。"""
import json, os, sys, textwrap

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
if not files:
    print('No files')
    sys.exit()

# 取最大的那个（最完整的对话）
biggest = max(files, key=lambda f: os.path.getsize(os.path.join(log_dir, f)))
path = os.path.join(log_dir, biggest)
data = json.load(open(path))
msgs = data['messages']

print(f"=== 文件: {biggest} ===")
print(f"Token 估算: {data.get('token_estimate', '?')}")
print(f"消息数: {len(msgs)}")
print()

# ============================================================
# 1. System Prompt 分析
# ============================================================
print("=" * 80)
print("1. SYSTEM PROMPT 分析")
print("=" * 80)
for i, m in enumerate(msgs):
    if m.get('role') != 'system':
        continue
    content = m.get('content', '')
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'text':
                text = b.get('text', '')
                print(f"  msg[{i}] system text block: {len(text)} chars")
                # 提取关键段落
                lines = text.split('\n')
                print(f"  前 5 行:")
                for l in lines[:5]:
                    print(f"    {l[:120]}")
                # 找关键标记
                for keyword in ['Ask mode', 'Code mode', 'tool', 'function', 'system_reminder']:
                    for li, line in enumerate(lines):
                        if keyword.lower() in line.lower():
                            print(f"  [L{li}] 含 '{keyword}': {line[:120]}")
                            break
    elif isinstance(content, str):
        print(f"  msg[{i}] system str: {len(content)} chars")
        print(f"  前 3 行:")
        for l in content.split('\n')[:3]:
            print(f"    {l[:120]}")

# ============================================================
# 2. User 消息分析（非 tool_result）
# ============================================================
print()
print("=" * 80)
print("2. USER 纯文本消息（非 tool_result）")
print("=" * 80)
for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if isinstance(content, str):
        print(f"  msg[{i}] user str: {len(content)} chars")
        print(f"    {content[:200]}")
    elif isinstance(content, list):
        text_blocks = [b for b in content if isinstance(b, dict) and b.get('type') == 'text']
        if text_blocks:
            for tb in text_blocks:
                t = tb.get('text', '')
                print(f"  msg[{i}] user text block: {len(t)} chars")
                print(f"    {t[:200]}")

# ============================================================
# 3. Assistant 消息分析 — 文本 vs tool_use
# ============================================================
print()
print("=" * 80)
print("3. ASSISTANT 消息结构")
print("=" * 80)
for i, m in enumerate(msgs):
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    tc = m.get('tool_calls', [])
    
    # 文本内容
    if isinstance(content, str) and content.strip():
        print(f"  msg[{i}] assistant TEXT: {len(content)} chars")
        print(f"    {content[:150]}")
    elif isinstance(content, list):
        text_parts = []
        tool_uses = []
        for b in content:
            if isinstance(b, dict):
                if b.get('type') == 'text':
                    text_parts.append(b.get('text', ''))
                elif b.get('type') == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    tool_uses.append((name, inp))
        if text_parts:
            combined = ' '.join(text_parts)
            if combined.strip():
                print(f"  msg[{i}] assistant TEXT in list: {len(combined)} chars")
                print(f"    {combined[:150]}")
        if tool_uses:
            print(f"  msg[{i}] assistant TOOL_USE x{len(tool_uses)}:")
            for name, inp in tool_uses[:3]:  # 只显示前3个
                if isinstance(inp, dict):
                    # 显示关键参数
                    path_val = inp.get('path') or inp.get('relative_workspace_path') or ''
                    if path_val:
                        print(f"    {name}(path={path_val})")
                    else:
                        keys = list(inp.keys())[:3]
                        print(f"    {name}(keys={keys})")
            if len(tool_uses) > 3:
                print(f"    ... +{len(tool_uses)-3} more")
    
    # OpenAI 格式 tool_calls
    if tc and isinstance(tc, list):
        print(f"  msg[{i}] assistant TOOL_CALLS x{len(tc)}:")
        for call in tc[:3]:
            if isinstance(call, dict):
                func = call.get('function', {})
                name = func.get('name', '?')
                args_str = func.get('arguments', '')
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    path_val = args.get('path') or args.get('relative_workspace_path') or ''
                    if path_val:
                        print(f"    {name}(path={path_val})")
                    else:
                        keys = list(args.keys())[:3] if isinstance(args, dict) else []
                        print(f"    {name}(keys={keys})")
                except:
                    print(f"    {name}(args={len(args_str)} chars)")
        if len(tc) > 3:
            print(f"    ... +{len(tc)-3} more")

# ============================================================
# 4. Tool Result 详细分析
# ============================================================
print()
print("=" * 80)
print("4. TOOL RESULT 详细分析")
print("=" * 80)

# Build tool_id maps
tid_to_name = {}
tid_to_path = {}
tid_to_args = {}
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
                if tid and name:
                    tid_to_name[tid] = name
                if isinstance(inp, dict):
                    tid_to_args[tid] = inp
                    p = inp.get('path') or inp.get('relative_workspace_path') or ''
                    if p and tid:
                        tid_to_path[tid] = p
    tc = m.get('tool_calls') or []
    for call in tc:
        if isinstance(call, dict):
            tid = call.get('id', '')
            func = call.get('function', {})
            name = func.get('name', '')
            if tid and name:
                tid_to_name[tid] = name
            args_str = func.get('arguments', '')
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                if isinstance(args, dict):
                    tid_to_args[tid] = args
                    p = args.get('path') or args.get('relative_workspace_path') or ''
                    if p and tid:
                        tid_to_path[tid] = p
            except:
                pass

# 分析每个 tool_result
total_result_chars = 0
result_by_tool = {}  # tool_name -> [(msg_idx, chars, path, first_line)]
file_read_map = {}   # path -> [(msg_idx, chars, line_range)]

for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for b in content:
        if not isinstance(b, dict) or b.get('type') != 'tool_result':
            continue
        bc = b.get('content', '')
        if isinstance(bc, str):
            text = bc
        elif isinstance(bc, list):
            text = '\n'.join(s.get('text', '') for s in bc if isinstance(s, dict))
        else:
            text = ''
        
        tuid = b.get('tool_use_id', '')
        tname = tid_to_name.get(tuid, '?')
        tpath = tid_to_path.get(tuid, '')
        targs = tid_to_args.get(tuid, {})
        
        total_result_chars += len(text)
        
        if tname not in result_by_tool:
            result_by_tool[tname] = []
        first_line = text.split('\n')[0][:80] if text else ''
        result_by_tool[tname].append((i, len(text), tpath, first_line))
        
        # 追踪文件读取
        if tname in ('Read', 'read_file', 'ReadFile', 'read') and tpath:
            if tpath not in file_read_map:
                file_read_map[tpath] = []
            # 提取行范围
            start_line = targs.get('start_line') or targs.get('startLine') or ''
            end_line = targs.get('end_line') or targs.get('endLine') or ''
            line_range = f"L{start_line}-{end_line}" if start_line else "full"
            file_read_map[tpath].append((i, len(text), line_range))

print(f"总 tool_result 字符数: {total_result_chars:,}")
print()

# 按工具类型统计
print("--- 按工具类型 ---")
for tname, results in sorted(result_by_tool.items(), key=lambda x: -sum(r[1] for r in x[1])):
    total_chars = sum(r[1] for r in results)
    count = len(results)
    avg = total_chars // count if count else 0
    print(f"  {tname}: {count}次, 总{total_chars:,}chars, 平均{avg:,}chars")

# 文件读取详情
print()
print("--- 文件读取详情（按总字符数排序）---")
for fpath, reads in sorted(file_read_map.items(), key=lambda x: -sum(r[1] for r in x[1])):
    total_chars = sum(r[1] for r in reads)
    basename = os.path.basename(fpath)
    print(f"  {basename} ({len(reads)}次, 总{total_chars:,}chars):")
    for msg_idx, chars, line_range in reads:
        print(f"    msg[{msg_idx}] {line_range} = {chars:,} chars")

# ============================================================
# 5. 重复读取模式分析
# ============================================================
print()
print("=" * 80)
print("5. 重复读取模式分析")
print("=" * 80)
dup_files = {p: reads for p, reads in file_read_map.items() if len(reads) > 1}
if dup_files:
    total_dup_chars = 0
    for fpath, reads in sorted(dup_files.items(), key=lambda x: -len(x[1])):
        basename = os.path.basename(fpath)
        # 检查是否是相同行范围的重复
        ranges = [r[2] for r in reads]
        unique_ranges = set(ranges)
        total_chars = sum(r[1] for r in reads)
        # 如果只保留每个 unique range 的最后一次
        saveable = 0
        range_last = {}
        for r in reads:
            range_last[r[2]] = r[1]  # 最后一次的大小
        keep_chars = sum(range_last.values())
        saveable = total_chars - keep_chars
        
        total_dup_chars += saveable
        print(f"  {basename}: {len(reads)}次读取, {len(unique_ranges)}种行范围")
        print(f"    总{total_chars:,}chars, 可省{saveable:,}chars")
        print(f"    行范围: {list(unique_ranges)}")
        # 显示读取时间线
        for msg_idx, chars, line_range in reads:
            print(f"      msg[{msg_idx}] {line_range} = {chars:,}")
    print(f"\n  总可省字符: {total_dup_chars:,} ({total_dup_chars*100//total_result_chars}%)")
else:
    print("  无重复读取")

# ============================================================
# 6. 对话流模式分析
# ============================================================
print()
print("=" * 80)
print("6. 对话流模式（每轮交互）")
print("=" * 80)
round_num = 0
i = 0
while i < len(msgs):
    m = msgs[i]
    role = m.get('role', '?')
    
    if role == 'system':
        print(f"  [SYSTEM] msg[{i}]")
        i += 1
        continue
    
    if role == 'user':
        content = m.get('content', '')
        if isinstance(content, str):
            print(f"  [USER TEXT] msg[{i}]: {content[:100]}")
        elif isinstance(content, list):
            text_blocks = [b for b in content if isinstance(b, dict) and b.get('type') == 'text']
            result_blocks = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_result']
            if text_blocks and not result_blocks:
                combined = ' '.join(b.get('text', '') for b in text_blocks)
                print(f"  [USER TEXT] msg[{i}]: {combined[:100]}")
            elif result_blocks:
                result_info = []
                for rb in result_blocks:
                    tuid = rb.get('tool_use_id', '')
                    tname = tid_to_name.get(tuid, '?')
                    tpath = tid_to_path.get(tuid, '')
                    bc = rb.get('content', '')
                    if isinstance(bc, str):
                        tlen = len(bc)
                    elif isinstance(bc, list):
                        tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
                    else:
                        tlen = 0
                    label = f"{tname}"
                    if tpath:
                        label += f":{os.path.basename(tpath)}"
                    result_info.append(f"{label}({tlen})")
                total_chars = sum(int(r.split('(')[1].rstrip(')')) for r in result_info)
                print(f"  [TOOL RESULTS] msg[{i}]: {len(result_blocks)}个结果, 总{total_chars:,}chars")
                for ri in result_info[:5]:
                    print(f"    {ri}")
                if len(result_info) > 5:
                    print(f"    ... +{len(result_info)-5} more")
        i += 1
        continue
    
    if role == 'assistant':
        content = m.get('content', '')
        tc = m.get('tool_calls', [])
        
        tool_names = []
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    p = ''
                    if isinstance(inp, dict):
                        p = inp.get('path') or inp.get('relative_workspace_path') or ''
                    if p:
                        tool_names.append(f"{name}:{os.path.basename(p)}")
                    else:
                        tool_names.append(name)
        if tc:
            for call in tc:
                if isinstance(call, dict):
                    func = call.get('function', {})
                    name = func.get('name', '?')
                    tool_names.append(name)
        
        text_content = ''
        if isinstance(content, str):
            text_content = content
        elif isinstance(content, list):
            text_content = ' '.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
        
        if tool_names:
            round_num += 1
            print(f"  [ROUND {round_num}] msg[{i}] assistant calls: {', '.join(tool_names[:8])}")
            if len(tool_names) > 8:
                print(f"    ... +{len(tool_names)-8} more")
            if text_content.strip():
                print(f"    text: {text_content[:100]}")
        elif text_content.strip():
            print(f"  [ASSISTANT TEXT] msg[{i}]: {text_content[:150]}")
        i += 1
        continue
    
    i += 1
