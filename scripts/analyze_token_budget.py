#!/usr/bin/env python3
"""分析请求中各部分的 token 占比 — before vs after。"""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'
biggest = max(
    [f for f in os.listdir(log_dir) if f.endswith('_before.json')],
    key=lambda f: os.path.getsize(os.path.join(log_dir, f))
)

CPT = 2.8  # chars per token

for suffix in ['_before.json', '_after.json']:
    fname = biggest.replace('_before.json', suffix)
    path = os.path.join(log_dir, fname)
    if not os.path.exists(path):
        continue
    data = json.load(open(path))
    msgs = data['messages']
    
    print(f"\n{'='*60}")
    print(f"  {fname}")
    print(f"  Token estimate: {data.get('token_estimate', '?')}")
    print(f"  Messages: {len(msgs)}")
    print(f"{'='*60}")
    
    # 按类别统计 chars
    categories = {
        'system_prompt': 0,
        'user_text': 0,
        'user_tool_result': 0,
        'assistant_text': 0,
        'assistant_tool_use': 0,
        'assistant_tool_calls': 0,
    }
    
    # 细分 tool_result
    tool_result_detail = {}  # 'Read:database.ts' -> chars
    
    # Build tid maps
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
    
    for i, m in enumerate(msgs):
        role = m.get('role', '')
        content = m.get('content', '')
        tc = m.get('tool_calls', [])
        
        if role == 'system':
            if isinstance(content, str):
                categories['system_prompt'] += len(content)
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get('type') == 'text':
                        categories['system_prompt'] += len(b.get('text', ''))
        
        elif role == 'user':
            if isinstance(content, str):
                categories['user_text'] += len(content)
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        if b.get('type') == 'text':
                            categories['user_text'] += len(b.get('text', ''))
                        elif b.get('type') == 'tool_result':
                            bc = b.get('content', '')
                            if isinstance(bc, str):
                                tlen = len(bc)
                            elif isinstance(bc, list):
                                tlen = sum(len(s.get('text','')) for s in bc if isinstance(s, dict))
                            else:
                                tlen = 0
                            categories['user_tool_result'] += tlen
                            # Detail
                            tuid = b.get('tool_use_id', '')
                            tname = tid_to_name.get(tuid, '?')
                            tpath = tid_to_path.get(tuid, '')
                            key = f"{tname}:{os.path.basename(tpath)}" if tpath else tname
                            tool_result_detail[key] = tool_result_detail.get(key, 0) + tlen
        
        elif role == 'assistant':
            if isinstance(content, str):
                categories['assistant_text'] += len(content)
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        if b.get('type') == 'text':
                            categories['assistant_text'] += len(b.get('text', ''))
                        elif b.get('type') == 'tool_use':
                            inp = b.get('input', {})
                            categories['assistant_tool_use'] += len(json.dumps(inp, ensure_ascii=False))
            if tc:
                categories['assistant_tool_calls'] += len(json.dumps(tc, ensure_ascii=False))
    
    total_chars = sum(categories.values())
    print(f"\n  总 chars: {total_chars:,} (估算 {int(total_chars/CPT):,} tokens)")
    print(f"\n  --- 按类别 ---")
    for cat, chars in sorted(categories.items(), key=lambda x: -x[1]):
        tokens = int(chars / CPT)
        pct = chars * 100 // total_chars if total_chars else 0
        print(f"  {cat:25s}: {chars:>10,} chars ({tokens:>8,} tokens, {pct:>2}%)")
    
    print(f"\n  --- tool_result 细分 (top 15) ---")
    for key, chars in sorted(tool_result_detail.items(), key=lambda x: -x[1])[:15]:
        tokens = int(chars / CPT)
        print(f"  {key:40s}: {chars:>8,} chars ({tokens:>6,} tokens)")
