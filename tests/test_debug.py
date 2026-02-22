#!/usr/bin/env python3
import os
import warnings; warnings.filterwarnings("ignore")
import json, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from core.context_compression import (
    _clean_retry_loops, _deduplicate_tool_results, _compute_priorities,
    estimate_request_tokens, _get_result_text, _detect_language_from_text,
    _compress_content, PRIORITY_RECENT, LARGE_RESULT_THRESHOLD,
)
with open("/tmp/real_request.json") as f:
    data = json.load(f)
msgs = data["messages"]
tools = data.get("tools", [])
msgs, removed = _clean_retry_loops(msgs)
msgs, deduped = _deduplicate_tool_results(msgs)
print(f"After L1: {len(msgs)} msgs (removed {removed}, deduped {deduped})")
priorities = _compute_priorities(msgs)
total = len(msgs)
print(f"\nCompressible big tool_results (pri < {PRIORITY_RECENT}):")
for i, m in enumerate(msgs):
    if priorities[i] >= PRIORITY_RECENT:
        continue
    if m.get("role") != "user" or not isinstance(m.get("content"), list):
        continue
    for j, block in enumerate(m["content"]):
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        text = _get_result_text(block)
        if len(text) < LARGE_RESULT_THRESHOLD:
            continue
        lang = _detect_language_from_text(text)
        compressed = _compress_content(text, i / total)
        print(f"  [{i}] blk[{j}]: {len(text)}ch lang={lang} pri={priorities[i]} -> {len(compressed)}ch ({len(compressed)/len(text):.0%})")
print(f"\nProtected (>= {PRIORITY_RECENT}) with big content:")
for i, (m, p) in enumerate(zip(msgs, priorities)):
    if p < PRIORITY_RECENT:
        continue
    content = m.get("content", "")
    clen = len(content) if isinstance(content, str) else len(json.dumps(content)) if content else 0
    if clen > 3000:
        print(f"  [{i}] {m.get('role')} pri={p} len={clen}")
