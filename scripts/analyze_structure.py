#!/usr/bin/env python3
"""Analyze the structure of the largest compression log."""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
if not files:
    print('No files')
    sys.exit()

biggest = max(files, key=lambda f: os.path.getsize(os.path.join(log_dir, f)))
path = os.path.join(log_dir, biggest)
data = json.load(open(path))

msgs = data['messages']
print(f"File: {biggest}")
print(f"Token estimate: {data.get('token_estimate', '?')}")
print(f"Message count: {len(msgs)}")
print()

# Build tool_id -> name map
tid_to_name = {}
tid_to_path = {}
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
                p = args.get('path') or args.get('relative_workspace_path') or ''
                if p and tid:
                    tid_to_path[tid] = p
            except:
                pass

# Analyze each message
for i, m in enumerate(msgs):
    role = m.get('role', '?')
    content = m.get('content', '')
    tc = m.get('tool_calls', [])
    
    if isinstance(content, str):
        desc = f"str({len(content)})"
    elif isinstance(content, list):
        blocks = []
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
                    tuid = b.get('tool_use_id', '')
                    tname = tid_to_name.get(tuid, '?')
                    tpath = tid_to_path.get(tuid, '')
                    label = f"{tname}"
                    if tpath:
                        label += f":{os.path.basename(tpath)}"
                    blocks.append(f"result({label},{tlen})")
                elif bt == 'tool_use':
                    name = b.get('name', '?')
                    inp = b.get('input', {})
                    inp_size = len(json.dumps(inp, ensure_ascii=False)) if isinstance(inp, dict) else 0
                    blocks.append(f"use({name},{inp_size})")
                elif bt == 'text':
                    tl = len(b.get('text', ''))
                    blocks.append(f"text({tl})")
                elif bt == 'image':
                    blocks.append('image')
                else:
                    blocks.append(f"{bt}(?)")
        desc = "[" + " | ".join(blocks) + "]"
    else:
        desc = 'empty'
    
    tc_desc = ''
    if tc:
        tc_names = []
        for c in tc:
            if isinstance(c, dict):
                n = c.get('function',{}).get('name','?')
                a = len(c.get('function',{}).get('arguments',''))
                tc_names.append(f"{n}({a})")
        tc_desc = " +tc=[" + ",".join(tc_names) + "]"
    
    print(f"[{i:3d}] {role:10s} {desc}{tc_desc}")

# Summary stats
print("\n=== SUMMARY ===")
file_reads = {}
total_tool_result_chars = 0
for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'tool_result':
            bc = b.get('content', '')
            if isinstance(bc, str):
                tlen = len(bc)
            elif isinstance(bc, list):
                tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
            else:
                tlen = 0
            total_tool_result_chars += tlen
            tuid = b.get('tool_use_id', '')
            tpath = tid_to_path.get(tuid, '')
            tname = tid_to_name.get(tuid, '')
            if tpath and tname in ('Read', 'read_file', 'ReadFile', 'read'):
                if tpath not in file_reads:
                    file_reads[tpath] = []
                file_reads[tpath].append((i, tlen))

print(f"Total tool_result chars: {total_tool_result_chars:,}")
print(f"Unique files read: {len(file_reads)}")
dup_files = {p: reads for p, reads in file_reads.items() if len(reads) > 1}
if dup_files:
    print(f"Duplicate file reads: {len(dup_files)}")
    dup_chars = sum(sum(r[1] for r in reads[:-1]) for reads in dup_files.values())
    print(f"Duplicate chars (saveable): {dup_chars:,}")
    for p, reads in sorted(dup_files.items(), key=lambda x: -sum(r[1] for r in x[1])):
        print(f"  {p}: {len(reads)}x, sizes={[r[1] for r in reads]}")

tool_counts = {}
for name in tid_to_name.values():
    tool_counts[name] = tool_counts.get(name, 0) + 1
print(f"\nTool usage: {dict(sorted(tool_counts.items(), key=lambda x: -x[1]))}")

print("\nTop 10 largest tool_results:")
big_results = []
for i, m in enumerate(msgs):
    if m.get('role') != 'user':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'tool_result':
            bc = b.get('content', '')
            if isinstance(bc, str):
                tlen = len(bc)
            elif isinstance(bc, list):
                tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
            else:
                tlen = 0
            tuid = b.get('tool_use_id', '')
            tname = tid_to_name.get(tuid, '?')
            tpath = tid_to_path.get(tuid, '')
            big_results.append((tlen, i, tname, tpath))

big_results.sort(reverse=True)
for tlen, mi, tname, tpath in big_results[:10]:
    print(f"  msg[{mi}] {tname}:{os.path.basename(tpath) if tpath else '?'} = {tlen:,} chars")
