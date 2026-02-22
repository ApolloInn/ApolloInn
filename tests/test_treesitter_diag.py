import os
#!/usr/bin/env python3
"""
Diagnose tree-sitter behavior on real TypeScript blocks.
Run on test server: python3 /tmp/_test_treesitter_diag.py
"""
import warnings; warnings.filterwarnings('ignore')
import sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from core.context_compression import (
    _get_result_text, _detect_language_from_text, _strip_line_numbers,
    _skeletonize_with_treesitter, _skeletonize_with_regex,
    _head_tail_compress, _compress_content,
    _TS_AVAILABLE, _clean_retry_loops, _deduplicate_tool_results,
)

print(f"tree-sitter available: {_TS_AVAILABLE}")

with open('/tmp/real_request.json') as f:
    data = json.load(f)

msgs = data['messages']
# L1 cleanup to align indices
msgs, _ = _clean_retry_loops(list(msgs))
msgs, _ = _deduplicate_tool_results(msgs)

# Find all large tool_result blocks
print(f"\n=== ALL LARGE TOOL_RESULT BLOCKS ===")
for i, m in enumerate(msgs):
    if m.get('role') != 'user' or not isinstance(m.get('content'), list):
        continue
    for j, block in enumerate(m['content']):
        if not isinstance(block, dict) or block.get('type') != 'tool_result':
            continue
        text = _get_result_text(block)
        if len(text) < 3000:
            continue
        
        lang = _detect_language_from_text(text)
        print(f"\nmsg[{i}] block[{j}]: {len(text)} chars, lang={lang}")
        
        # Try tree-sitter
        if lang and lang not in ('markdown', 'json', 'yaml', 'toml', 'html', 'css', 'scss', 'sql'):
            clean_text, had_nums = _strip_line_numbers(text)
            print(f"  clean_text length: {len(clean_text)}, had_line_nums: {had_nums}")
            
            ts_result = _skeletonize_with_treesitter(text, lang)
            if ts_result is None:
                print(f"  tree-sitter: RETURNED NONE (parse failed or no replacements)")
            else:
                ratio = len(ts_result) / len(text)
                print(f"  tree-sitter: {len(ts_result)} chars ({ratio:.1%} of original)")
                threshold_pass = len(ts_result) < len(text) * 0.85
                print(f"  passes 0.85 threshold: {threshold_pass}")
                if not threshold_pass:
                    print(f"  -> Would need threshold >= {ratio:.2f} to use tree-sitter result")
                # Show first 500 chars of skeleton
                print(f"  skeleton preview (first 500 chars):")
                for line in ts_result[:500].split('\n'):
                    print(f"    {line}")
            
            # Also try regex
            regex_result = _skeletonize_with_regex(text)
            regex_ratio = len(regex_result) / len(text)
            print(f"  regex skeleton: {len(regex_result)} chars ({regex_ratio:.1%})")
        
        # What does _compress_content actually produce?
        compressed = _compress_content(text, 0.3)
        comp_ratio = len(compressed) / len(text)
        print(f"  _compress_content result: {len(compressed)} chars ({comp_ratio:.1%})")
        method = "unknown"
        if "chars omitted" in compressed:
            method = "head_tail"
        elif "// ..." in compressed or "# ..." in compressed or "lines of implementation" in compressed:
            method = "tree-sitter or regex skeleton"
        print(f"  compression method used: {method}")
