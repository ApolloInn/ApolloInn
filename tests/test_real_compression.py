import os
#!/usr/bin/env python3
"""Test compression with a real captured request."""
import warnings
warnings.filterwarnings('ignore')
import sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from core.context_compression import (
    compress_context, _TS_AVAILABLE, estimate_request_tokens,
    _detect_language_from_text, _get_result_text,
)

print(f"tree-sitter available: {_TS_AVAILABLE}")

with open('/tmp/real_request.json') as f:
    data = json.load(f)

messages = data['messages']
tools = data.get('tools', [])

print(f"Messages: {len(messages)}")
print(f"Tools: {len(tools)}")

est = estimate_request_tokens(messages, tools)
print(f"Estimated tokens: {est // 1000}K")
print(f"Trigger threshold (128K * 0.625): {int(128000 * 0.625) // 1000}K")
print(f"Target (128K * 0.55): {int(128000 * 0.55) // 1000}K")

# Analyze tool_results before compression
print("\n=== TOOL_RESULT ANALYSIS ===")
for i, m in enumerate(messages):
    if not isinstance(m.get('content'), list):
        continue
    for j, block in enumerate(m['content']):
        if not isinstance(block, dict):
            continue
        if block.get('type') == 'tool_result':
            text = _get_result_text(block)
            if len(text) > 1000:
                lang = _detect_language_from_text(text)
                print(f"  msg[{i}] block[{j}]: {len(text)} chars, lang={lang}, preview={text[:80].replace(chr(10), ' ')}")

# Run compression
print("\n=== COMPRESSING ===")
compressed, stats = compress_context(messages, tools, context_window=128000)

print(f"\n=== RESULTS ===")
print(f"Level: {stats['level']}")
print(f"Original: {stats['original_tokens'] // 1000}K tokens")
print(f"Final: {stats['final_tokens'] // 1000}K tokens")
print(f"Saved: {stats['tokens_saved'] // 1000}K tokens")
print(f"Compression ratio: {1 - stats['final_tokens'] / stats['original_tokens']:.1%}")
print(f"tree_sitter: {stats['tree_sitter']}")

# Show message structure after compression
print(f"\n=== AFTER COMPRESSION ({len(compressed)} messages) ===")
for i, m in enumerate(compressed):
    role = m.get('role', '?')
    content = m.get('content', '')
    if isinstance(content, str):
        clen = len(content)
    elif isinstance(content, list):
        clen = len(json.dumps(content, ensure_ascii=False))
    else:
        clen = 0
    if clen > 500:
        print(f"  [{i:2d}] {role:10s} {clen:6d} chars")

# Verify ChatMessage reconstruction
print("\n=== ChatMessage RECONSTRUCTION TEST ===")
try:
    from core.models_openai import ChatMessage
    for i, m in enumerate(compressed):
        try:
            cm = ChatMessage(**m)
        except Exception as e:
            print(f"  FAIL msg[{i}]: {e}")
            print(f"    keys: {list(m.keys())}")
            if isinstance(m.get('content'), list):
                for j, b in enumerate(m['content'][:2]):
                    print(f"    block[{j}]: type={type(b).__name__} keys={list(b.keys()) if isinstance(b, dict) else 'N/A'}")
            break
    else:
        print("  ALL OK - all messages reconstruct successfully")
except ImportError:
    print("  SKIP - ChatMessage not available")

# Show a sample compressed tool_result
print("\n=== SAMPLE COMPRESSED TOOL_RESULT ===")
for i, m in enumerate(compressed):
    if not isinstance(m.get('content'), list):
        continue
    for j, block in enumerate(m['content']):
        if not isinstance(block, dict):
            continue
        if block.get('type') == 'tool_result':
            text = _get_result_text(block)
            orig_msg = messages[i] if i < len(messages) else None
            if orig_msg and isinstance(orig_msg.get('content'), list):
                for ob in orig_msg['content']:
                    if isinstance(ob, dict) and ob.get('type') == 'tool_result':
                        orig_text = _get_result_text(ob)
                        if len(orig_text) > 3000 and len(text) < len(orig_text):
                            print(f"  msg[{i}] block[{j}]: {len(orig_text)} -> {len(text)} chars ({len(text)/len(orig_text):.1%})")
                            print(f"  First 500 chars of compressed:")
                            print(text[:500])
                            print("  ...")
                            break
