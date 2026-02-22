#!/usr/bin/env python3
"""分析 database.ts 死循环的根因 — 对比每次 Read 的参数和返回内容。"""
import json, os, sys

log_dir = '/opt/apollo/compression_logs'
biggest = max(
    [f for f in os.listdir(log_dir) if f.endswith('_before.json')],
    key=lambda f: os.path.getsize(os.path.join(log_dir, f))
)
data = json.load(open(os.path.join(log_dir, biggest)))
msgs = data['messages']

print(f"=== {biggest} ===\n")

# 找所有对 database.ts 的 Read 调用及其返回
# 关键：看 assistant 在每次 Read 之间说了什么（思考过程）
for i, m in enumerate(msgs):
    if m.get('role') != 'assistant':
        continue
    content = m.get('content', '')
    if not isinstance(content, list):
        continue
    
    has_db_read = False
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'tool_use':
            if b.get('name') == 'Read':
                inp = b.get('input', {})
                path = inp.get('path', '')
                if 'database.ts' in path:
                    has_db_read = True
                    break
    
    if not has_db_read:
        continue
    
    # 打印 assistant 的文本内容（思考过程）
    text_parts = []
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'text':
            text_parts.append(b.get('text', ''))
    
    if text_parts:
        combined = ' '.join(text_parts).strip()
        if combined:
            print(f"msg[{i}] assistant THINKS: {combined[:300]}")
    
    # 打印 Read 参数
    for b in content:
        if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'Read':
            inp = b.get('input', {})
            path = inp.get('path', '')
            if 'database.ts' in path:
                params = {k: v for k, v in inp.items() if k != 'path'}
                tid = b.get('id', '')
                print(f"  Read database.ts params={params} id={tid[:12]}")
                
                # 找对应的 tool_result
                for j in range(i+1, min(i+3, len(msgs))):
                    if msgs[j].get('role') != 'user':
                        continue
                    uc = msgs[j].get('content', '')
                    if not isinstance(uc, list):
                        continue
                    for rb in uc:
                        if isinstance(rb, dict) and rb.get('type') == 'tool_result':
                            if rb.get('tool_use_id', '') == tid:
                                bc = rb.get('content', '')
                                if isinstance(bc, str):
                                    text = bc
                                elif isinstance(bc, list):
                                    text = '\n'.join(s.get('text','') for s in bc if isinstance(s, dict))
                                else:
                                    text = ''
                                lines = text.split('\n')
                                # 显示返回内容的关键信息
                                print(f"  → result: {len(text)} chars, {len(lines)} lines")
                                # 第一行和最后一行
                                if lines:
                                    print(f"  → first: {lines[0][:100]}")
                                    print(f"  → last:  {lines[-1][:100]}")
                                # 检查是否有截断标记
                                if '... lines not shown ...' in text:
                                    for line in lines[:5]:
                                        if 'not shown' in line:
                                            print(f"  → TRUNCATION: {line}")
                                            break
                    break
    print()

# 也看看 after 文件中这些消息变成了什么
after_file = biggest.replace('_before', '_after')
after_path = os.path.join(log_dir, after_file)
if os.path.exists(after_path):
    after_data = json.load(open(after_path))
    after_msgs = after_data['messages']
    print(f"\n=== AFTER 压缩后 ({after_file}) ===")
    print(f"消息数: {len(after_msgs)}")
    print(f"Token 估算: {after_data.get('token_estimate', '?')}")
    
    # 看压缩后 database.ts 的 tool_result 变成了什么
    db_results_after = 0
    for i, m in enumerate(after_msgs):
        if m.get('role') != 'user':
            continue
        content = m.get('content', '')
        if not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_result':
                bc = b.get('content', '')
                if isinstance(bc, str):
                    text = bc
                elif isinstance(bc, list):
                    text = '\n'.join(s.get('text','') for s in bc if isinstance(s, dict))
                else:
                    text = ''
                if 'database' in text.lower() or 'AURORA' in text:
                    if 'database.ts' in text[:200] or len(text) > 4000:
                        db_results_after += 1
                        print(f"\n  msg[{i}] tool_result: {len(text)} chars")
                        print(f"    first 150: {text[:150]}")
    print(f"\n  database.ts 相关 tool_result 数: {db_results_after}")
