import os
#!/usr/bin/env python3
"""Inspect compression results — show before/after for each compressed block."""
import warnings; warnings.filterwarnings('ignore')
import sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from core.context_compression import (
    compress_context, _get_result_text, _detect_language_from_text,
    _clean_retry_loops, _deduplicate_tool_results,
)

with open('/tmp/real_request.json') as f:
    data = json.load(f)

orig_msgs = data['messages']
tools = data.get('tools', [])

# L1 cleanup first (to align indices)
cleaned, removed = _clean_retry_loops(list(orig_msgs))
cleaned, deduped = _deduplicate_tool_results(cleaned)

# Full compression
compressed, stats = compress_context(list(orig_msgs), tools, context_window=128000)

print(f"=== COMPRESSION SUMMARY ===")
print(f"Original: {stats['original_tokens']//1000}K -> Final: {stats['final_tokens']//1000}K (saved {stats['tokens_saved']//1000}K, {1-stats['final_tokens']/stats['original_tokens']:.1%})")
print(f"Level: {stats['level']}, Messages: {len(orig_msgs)} -> {len(cleaned)} (L1) -> {len(compressed)} (final)")

# Compare cleaned vs compressed to find what changed
print(f"\n=== COMPRESSED BLOCKS DETAIL ===")
for i in range(min(len(cleaned), len(compressed))):
    cm = cleaned[i]
    pm = compressed[i]
    
    if cm.get('role') != 'user' or not isinstance(cm.get('content'), list):
        # Check assistant content compression
        if cm.get('role') == 'assistant' and isinstance(cm.get('content'), str) and isinstance(pm.get('content'), str):
            if len(cm['content']) != len(pm['content']):
                print(f"\n--- msg[{i}] assistant ---")
                print(f"  Before: {len(cm['content'])} chars")
                print(f"  After:  {len(pm['content'])} chars ({len(pm['content'])/len(cm['content']):.0%})")
                print(f"  First 200 chars after:")
                print(f"  {pm['content'][:200]}")
        continue
    
    if not isinstance(pm.get('content'), list):
        continue
    
    for j in range(min(len(cm['content']), len(pm['content']))):
        cb = cm['content'][j]
        pb = pm['content'][j]
        
        if not isinstance(cb, dict) or cb.get('type') != 'tool_result':
            continue
        if not isinstance(pb, dict):
            continue
            
        orig_text = _get_result_text(cb)
        comp_text = _get_result_text(pb)
        
        if len(orig_text) < 1000:
            continue
            
        if abs(len(orig_text) - len(comp_text)) < 100:
            continue  # Not compressed
        
        lang = _detect_language_from_text(orig_text)
        ratio = len(comp_text) / len(orig_text) if len(orig_text) > 0 else 1
        
        print(f"\n--- msg[{i}] block[{j}] lang={lang} ---")
        print(f"  Before: {len(orig_text)} chars")
        print(f"  After:  {len(comp_text)} chars ({ratio:.0%})")
        
        # Show first 300 chars of original
        print(f"  ORIGINAL first 300:")
        for line in orig_text[:300].split('\n'):
            print(f"    {line}")
        
        # Show first 500 chars of compressed
        print(f"  COMPRESSED first 500:")
        for line in comp_text[:500].split('\n'):
            print(f"    {line}")
        
        # Show last 200 chars of compressed
        print(f"  COMPRESSED last 200:")
        for line in comp_text[-200:].split('\n'):
            print(f"    {line}")

# Verify ChatMessage reconstruction
print(f"\n=== ChatMessage RECONSTRUCTION ===")
try:
    from core.models_openai import ChatMessage
    for i, m in enumerate(compressed):
        try:
            ChatMessage(**m)
        except Exception as e:
            print(f"  FAIL msg[{i}]: {e}")
            break
    else:
        print("  ALL OK")
except ImportError:
    print("  SKIP")
