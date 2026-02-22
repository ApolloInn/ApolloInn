#!/usr/bin/env python3
"""
Validate that code mode L4 no longer creates orphan tool_results.
Tests against captured request data on the test server.
"""
import json
import sys
import os

sys.path.insert(0, "/opt/apollo")
from core.context_compression import compress_context, _detect_analysis_mode, estimate_request_tokens


def check_orphan_tool_results(messages):
    """Check for orphan tool_results (user messages with tool_result whose assistant tool_use was dropped)."""
    orphans = 0
    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        has_tool_result = False
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                has_tool_result = True
                break
        if not has_tool_result:
            continue
        
        # This user message has tool_result — check that the preceding assistant has matching tool_use
        if i == 0:
            orphans += 1
            continue
        prev = messages[i - 1]
        if prev.get("role") != "assistant":
            orphans += 1
            continue
        
        # Check assistant has tool_use or tool_calls
        prev_has_tool = False
        prev_content = prev.get("content", "")
        if isinstance(prev_content, list):
            for b in prev_content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    prev_has_tool = True
                    break
        tc = prev.get("tool_calls")
        if tc and isinstance(tc, list) and len(tc) > 0:
            prev_has_tool = True
        
        # Also check for folded summary messages (these are OK)
        if isinstance(prev_content, list):
            for b in prev_content:
                if isinstance(b, dict) and b.get("type") == "text":
                    text = b.get("text", "")
                    if text.startswith("[Previously called:"):
                        prev_has_tool = True
                        break
        elif isinstance(prev_content, str) and prev_content.startswith("[Previously called:"):
            prev_has_tool = True
        
        if not prev_has_tool:
            orphans += 1
    
    return orphans


def test_file(path):
    with open(path, "r") as f:
        data = json.load(f)
    
    messages = data.get("messages", data.get("body", {}).get("messages", []))
    if not messages:
        print(f"  SKIP: no messages found")
        return
    
    tools = data.get("tools", data.get("body", {}).get("tools"))
    
    before_tokens = estimate_request_tokens(messages, tools)
    is_analysis = _detect_analysis_mode(messages)
    
    # Count tool_use and tool_result
    tool_use_count = 0
    tool_result_count = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict):
                    if b.get("type") == "tool_use":
                        tool_use_count += 1
                    elif b.get("type") == "tool_result":
                        tool_result_count += 1
        tc = m.get("tool_calls") or []
        tool_use_count += len(tc)
    
    print(f"  Before: {len(messages)} msgs, {before_tokens//1000}K tokens")
    print(f"  Tool calls: {tool_use_count} tool_use, {tool_result_count} tool_result")
    print(f"  Analysis mode: {is_analysis}")
    
    compressed, stats = compress_context(messages, tools)
    after_tokens = stats.get("final_tokens", estimate_request_tokens(compressed, tools))
    level = stats.get("level", 0)
    
    orphans = check_orphan_tool_results(compressed)
    
    status = "OK" if orphans == 0 else f"FAIL ({orphans} orphans)"
    print(f"  After: {len(compressed)} msgs, {after_tokens//1000}K tokens (level {level})")
    print(f"  Orphan tool_results: {status}")
    return orphans


# Test captured requests
log_dir = "/opt/apollo/compression_logs"
total_orphans = 0
tested = 0

if os.path.exists(log_dir):
    for fname in sorted(os.listdir(log_dir)):
        if fname.endswith("_before.json"):
            path = os.path.join(log_dir, fname)
            print(f"\n--- {fname} ---")
            try:
                result = test_file(path)
                if result is not None:
                    total_orphans += result
                    tested += 1
            except Exception as e:
                print(f"  ERROR: {e}")

print(f"\n{'='*60}")
print(f"TOTAL: {tested} files tested, {total_orphans} orphan tool_results")
if total_orphans == 0:
    print("ALL PASSED — no orphan tool_results")
else:
    print(f"FAILED — {total_orphans} orphan tool_results found")
