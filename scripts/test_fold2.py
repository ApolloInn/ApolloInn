#!/usr/bin/env python3
"""测试折叠 — 只运行到 L4-early，看中间结果。"""
import json, os, sys

sys.path.insert(0, '/opt/apollo')
from core.context_compression import (
    _detect_analysis_mode, _clean_retry_loops, _deduplicate_tool_results,
    _compute_priorities, _build_tool_id_to_path, _build_tool_id_to_name,
    _cleanup_digested_reads, _compress_image_blocks, _drop_digested_pairs,
    estimate_request_tokens, COMPRESSION_TRIGGER_RATIO, COMPRESSION_TARGET_RATIO,
)

log_dir = '/opt/apollo/compression_logs'
files = sorted([f for f in os.listdir(log_dir) if f.endswith('_before.json')])
data = json.load(open(os.path.join(log_dir, files[-1])))
msgs = data['messages']
tools = data.get('tools')

print("Before: %d msgs" % len(msgs))

# 模拟 compress_context 的前几步
current = list(msgs)
current, _ = _clean_retry_loops(current)
current, _ = _deduplicate_tool_results(current)

priorities = _compute_priorities(current)
tool_id_map = _build_tool_id_to_path(current)
tool_name_map = _build_tool_id_to_name(current)

current, _ = _cleanup_digested_reads(current, priorities, tool_id_map=tool_id_map)
priorities = _compute_priorities(current)
current, _ = _compress_image_blocks(current, priorities)

current_tokens = estimate_request_tokens(current, tools)
target_tokens = int(128000 * COMPRESSION_TARGET_RATIO)
print("After L0.5/L1: %d msgs, %dK tokens, target=%dK" % (len(current), current_tokens // 1000, target_tokens // 1000))

# 运行 L4-early
current, saved = _drop_digested_pairs(current, target_tokens, current_tokens, tools)
current_tokens = estimate_request_tokens(current, tools)
print("After L4-early: %d msgs, %dK tokens, saved=%dK" % (len(current), current_tokens // 1000, saved // 1000))

# 打印结构
print("\n--- After L4-early ---")
for i, m in enumerate(current):
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        if '[Previously' in content or '[Results' in content:
            print('[%2d] %-10s SUMMARY: %s' % (i, role, content[:100]))
        else:
            print('[%2d] %-10s str(%d)' % (i, role, len(content)))
    elif isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                bt = b.get('type', '?')
                if bt == 'text':
                    t = b.get('text', '')
                    if '[Previously' in t or '[Results' in t:
                        parts.append('SUMMARY(%d)' % len(t))
                    else:
                        parts.append('text(%d)' % len(t))
                elif bt == 'tool_result':
                    bc = b.get('content', '')
                    tlen = len(bc) if isinstance(bc, str) else sum(len(s.get('text','')) for s in bc if isinstance(s, dict)) if isinstance(bc, list) else 0
                    parts.append('tool_result(%d)' % tlen)
                elif bt == 'tool_use':
                    parts.append('tool_use(%s)' % b.get('name', '?'))
                else:
                    parts.append(bt)
        print('[%2d] %-10s [%s]' % (i, role, ', '.join(parts)))
    else:
        print('[%2d] %-10s empty' % (i, role))

# 检查角色序列
print("\nRole sequence:")
for i, m in enumerate(current):
    role = m.get('role', '?')
    print('  [%d] %s' % (i, role))
