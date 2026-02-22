import os
#!/usr/bin/env python3
"""Minimal compression test — small output to avoid SSH pipe clog."""
import warnings; warnings.filterwarnings('ignore')
import sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from core.context_compression import (
    compress_context, _TS_AVAILABLE, estimate_request_tokens,
    _detect_language_from_text, _get_result_text,
)
with open('/tmp/real_request.json') as f:
    data = json.load(f)
msgs = data['messages']
tools = data.get('tools', [])
print(f"TS={_TS_AVAILABLE} msgs={len(msgs)} tools={len(tools)}")
est = estimate_request_tokens(msgs, tools)
print(f"est={est//1000}K trigger={int(128000*0.625)//1000}K target={int(128000*0.55)//1000}K")

# Show lang detection for big blocks BEFORE compression
for i, m in enumerate(msgs):
    if not isinstance(m.get('content'), list): continue
    for j, block in enumerate(m['content']):
        if not isinstance(block, dict) or block.get('type') != 'tool_result': continue
        text = _get_result_text(block)
        if len(text) > 3000:
            lang = _detect_language_from_text(text)
            print(f"  [{i}][{j}] {len(text)}ch lang={lang}")

# Compress
compressed, stats = compress_context(msgs, tools, context_window=128000)
print(f"\nL={stats['level']} orig={stats['original_tokens']//1000}K final={stats['final_tokens']//1000}K saved={stats['tokens_saved']//1000}K ratio={1-stats['final_tokens']/stats['original_tokens']:.1%}")

# Show big messages after compression
for i, m in enumerate(compressed):
    c = m.get('content', '')
    clen = len(c) if isinstance(c, str) else len(json.dumps(c, ensure_ascii=False)) if c else 0
    if clen > 5000:
        print(f"  post[{i}] {m.get('role')} {clen}ch")
