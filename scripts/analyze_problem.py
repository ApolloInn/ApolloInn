#!/usr/bin/env python3
"""分析压缩后的请求结构 — 找出模型回复不符合 Cursor 期望的原因。"""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'

# 取最新的几个 after 文件
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_after.json')])
if not files:
    print("No files")
    sys.exit(1)

# 分析最新的请求
for fname in files[-3:]:
    bname = fname.replace('_after.json', '_before.json')
    
    after_data = json.load(open(os.path.join(log_dir, fname)))
    before_path = os.path.join(log_dir, bname)
    before_data = json.load(open(before_path)) if os.path.exists(before_path) else None
    
    after_msgs = after_data['messages']
    before_msgs = before_data['messages'] if before_data else []
    
    print('\n' + '='*70)
    print('FILE:', fname)
    print('Level:', after_data.get('level'))
    print('Before: %d msgs, %dK tokens' % (len(before_msgs), (before_data or {}).get('token_estimate', 0) // 1000))
    print('After:  %d msgs, %dK tokens' % (len(after_msgs), after_data.get('token_estimate', 0) // 1000))
    print('='*70)
    
    # 1. 检查消息角色序列是否合法
    roles = [m.get('role') for m in after_msgs]
    print('\nRole sequence:', ' -> '.join(roles))
    
    # 2. 检查是否有 orphan tool_result（没有对应的 tool_use）
    # 收集所有 tool_use id
    tool_use_ids = set()
    for m in after_msgs:
        if m.get('role') != 'assistant':
            continue
        content = m.get('content', '')
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'tool_use':
                    tool_use_ids.add(b.get('id', ''))
        tc = m.get('tool_calls') or []
        for call in tc:
            if isinstance(call, dict):
                tool_use_ids.add(call.get('id', ''))
    
    # 收集所有 tool_result id
    tool_result_ids = set()
    orphan_results = []
    for i, m in enumerate(after_msgs):
        if m.get('role') != 'user':
            continue
        content = m.get('content', '')
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'tool_result':
                    tuid = b.get('tool_use_id', '')
                    tool_result_ids.add(tuid)
                    if tuid and tuid not in tool_use_ids:
                        orphan_results.append((i, tuid))
    
    if orphan_results:
        print('\n!!! ORPHAN tool_results (no matching tool_use):')
        for idx, tuid in orphan_results:
            print('  msg[%d] tool_use_id=%s' % (idx, tuid[:30]))
    else:
        print('\nNo orphan tool_results (all have matching tool_use)')
    
    # 3. 检查最后一条消息
    last_msg = after_msgs[-1]
    print('\nLast message role:', last_msg.get('role'))
    last_content = last_msg.get('content', '')
    if isinstance(last_content, str):
        print('Last message content (first 200):', last_content[:200])
    elif isinstance(last_content, list):
        for b in last_content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'text':
                    print('Last msg text block:', b.get('text', '')[:200])
                elif bt == 'tool_result':
                    bc = b.get('content', '')
                    if isinstance(bc, str):
                        print('Last msg tool_result(%d): %s...' % (len(bc), bc[:100]))
                    elif isinstance(bc, list):
                        for s in bc:
                            if isinstance(s, dict) and s.get('type') == 'text':
                                t = s.get('text', '')
                                print('Last msg tool_result(%d): %s...' % (len(t), t[:100]))
    
    # 4. 检查 before 的最后几条消息 vs after 的最后几条
    print('\n--- Before: last 5 messages ---')
    for m in before_msgs[-5:]:
        role = m.get('role', '?')
        content = m.get('content', '')
        if isinstance(content, str):
            print('  %s: str(%d)' % (role, len(content)))
        elif isinstance(content, list):
            parts = []
            for b in content:
                if isinstance(b, dict):
                    bt = b.get('type', '?')
                    if bt == 'tool_result':
                        bc = b.get('content', '')
                        tlen = len(bc) if isinstance(bc, str) else sum(len(s.get('text','')) for s in bc if isinstance(s, dict)) if isinstance(bc, list) else 0
                        parts.append('tool_result(%d)' % tlen)
                    elif bt == 'tool_use':
                        parts.append('tool_use')
                    elif bt == 'text':
                        parts.append('text(%d)' % len(b.get('text', '')))
                    else:
                        parts.append(bt)
            print('  %s: [%s]' % (role, ', '.join(parts)))
        else:
            print('  %s: empty' % role)
    
    print('\n--- After: last 5 messages ---')
    for m in after_msgs[-5:]:
        role = m.get('role', '?')
        content = m.get('content', '')
        if isinstance(content, str):
            print('  %s: str(%d)' % (role, len(content)))
        elif isinstance(content, list):
            parts = []
            for b in content:
                if isinstance(b, dict):
                    bt = b.get('type', '?')
                    if bt == 'tool_result':
                        bc = b.get('content', '')
                        tlen = len(bc) if isinstance(bc, str) else sum(len(s.get('text','')) for s in bc if isinstance(s, dict)) if isinstance(bc, list) else 0
                        parts.append('tool_result(%d)' % tlen)
                    elif bt == 'tool_use':
                        inp = b.get('input', {})
                        parts.append('tool_use(%s)' % b.get('name', '?'))
                    elif bt == 'text':
                        parts.append('text(%d)' % len(b.get('text', '')))
                    else:
                        parts.append(bt)
            print('  %s: [%s]' % (role, ', '.join(parts)))
        else:
            print('  %s: empty' % role)
    
    # 5. 检查 analysis_mode 检测
    # 看 system_reminder 中是否有 Ask mode
    for m in after_msgs[:5]:
        content = m.get('content', '')
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'text':
                    t = b.get('text', '')
                    if 'Ask mode' in t or 'ask mode' in t:
                        print('\nDetected: Ask mode in msg')
                    if 'Agent mode' in t or 'agent mode' in t:
                        print('\nDetected: Agent mode in msg')
        elif isinstance(content, str):
            if 'Ask mode' in content or 'ask mode' in content:
                print('\nDetected: Ask mode in system')
            if 'Agent mode' in content or 'agent mode' in content:
                print('\nDetected: Agent mode in system')
