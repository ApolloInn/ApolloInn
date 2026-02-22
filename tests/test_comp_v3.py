import os
#!/usr/bin/env python3
"""Diagnose why msg[8] isn't being compressed."""
import warnings; warnings.filterwarnings('ignore')
import sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from core.context_compression import (
    _clean_retry_loops, _deduplicate_tool_results, _compute_priorities,
    _compress_content, _get_result_text, _detect_language_from_text,
    estimate_request_tokens, PRIORITY_RECENT, LARGE_RESULT_THRESHOLD,
)
with open('/tmp/real_request.json') as f:
    data = json.load(f)
msgs = data['messages']
tools = data.get('tools', [])

# L1 cleanup
msgs, removed = _clean_retry_loops(msgs)
msgs, deduped = _deduplicate_tool_results(msgs)
print(f"After L1: {len(msgs)} msgs (removed {removed}, deduped {deduped})")

# Priorities
priorities = _compute_priorities(msgs)
total = len(msgs)

# Show ALL messages with big content and their priorities
print(f"\nAll msgs with content > 3K chars (total={total}, RECENT threshold idx>={total-10}):")
for i, (m, p) in enumerate(zip(msgs, priorities)):
    c = m.get('content', '')
    if isinstance(c, str):
        clen = len(c)
    elif isinstance(c, list):
        clen = sum(len(_get_result_text(b)) if isinstance(b, dict) and b.get('type') == 'tool_result' else 0 for b in c)
    else:
        clen = 0
    if clen > 3000:
        print(f"  [{i:2d}] {m.get('role'):10s} pri={p:3d} content={clen}ch {'*** PROTECTED' if p >= PRIORITY_RECENT else 'compressible'}")

# Try compressing msg[8] blocks manually
print(f"\nManual compression of big tool_results in compressible msgs:")
for i, m in enumerate(msgs):
    if priorities[i] >= PRIORITY_RECENT:
        continue
    if m.get('role') != 'user' or not isinstance(m.get('content'), list):
        continue
    for j, block in enumerate(m['content']):
        if not isinstance(block, dict) or block.get('type') != 'tool_result':
            continue
        text = _get_result_text(block)
        if len(text) < LARGE_RESULT_THRESHOLD:
            continue
        lang = _detect_language_from_text(text)
        compressed = _compress_content(text, i / total)
        ratio = len(compressed) / len(text) if len(text) > 0 else 1
        print(f"  [{i}][{j}] {len(text)}ch lang={lang} -> {len(compressed)}ch ({ratio:.0%})")
