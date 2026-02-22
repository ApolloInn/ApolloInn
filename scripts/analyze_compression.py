#!/usr/bin/env python3
"""分析压缩日志，生成汇总报告。"""
import json
import os
import glob
import sys

log_dir = sys.argv[1] if len(sys.argv) > 1 else "/opt/apollo/compression_logs"

pairs = {}
for f in sorted(glob.glob(os.path.join(log_dir, "req_*_before.json"))):
    req_id = os.path.basename(f).replace("_before.json", "")
    after_f = f.replace("_before.json", "_after.json")
    if os.path.exists(after_f):
        pairs[req_id] = (f, after_f)

header = f"{'请求ID':<14} {'原始tok':>8} {'压缩tok':>8} {'级别':>4} {'模式':>6} {'Read#':>5} {'消息B':>5} {'消息A':>5} {'原始KB':>7} {'压缩KB':>7} {'压缩率':>6}"
print(header)
print("-" * len(header) + "-" * 20)

for req_id in sorted(pairs.keys()):
    bf, af = pairs[req_id]
    with open(bf) as f:
        before = json.load(f)
    with open(af) as f:
        after = json.load(f)

    orig_tokens = before.get("token_estimate", 0)
    final_tokens = after.get("token_estimate", 0)
    level = after.get("level", "?")
    msg_b = before.get("message_count", len(before.get("messages", [])))
    msg_a = after.get("message_count", len(after.get("messages", [])))
    orig_kb = os.path.getsize(bf) // 1024
    comp_kb = os.path.getsize(af) // 1024
    ratio = final_tokens / orig_tokens * 100 if orig_tokens > 0 else 0

    # 检测分析模式
    is_analysis = "Code"
    msgs = before.get("messages", [])
    for m in msgs:
        c = m.get("content", "")
        if isinstance(c, str) and "Ask mode is active" in c:
            is_analysis = "Ask"
            break
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text" and "Ask mode is active" in b.get("text", ""):
                    is_analysis = "Ask"
                    break

    # 统计 Read 调用数
    read_count = 0
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        tc = m.get("tool_calls") or []
        for call in tc:
            if isinstance(call, dict) and call.get("function", {}).get("name", "") in ("Read", "read_file"):
                read_count += 1
        c = m.get("content", "")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name", "") in ("Read", "read_file"):
                    read_count += 1

    mode_str = is_analysis
    print(f"{req_id:<14} {orig_tokens//1000:>7}K {final_tokens//1000:>7}K  L{level:<2} {mode_str:>6} {read_count:>5} {msg_b:>5} {msg_a:>5} {orig_kb:>6}K {comp_kb:>6}K {ratio:>5.1f}%")

# 汇总
print()
print("=" * 80)
total = len(pairs)
ask_count = 0
total_orig = 0
total_final = 0
over_target = 0
target = 51000

for req_id in pairs:
    bf, af = pairs[req_id]
    with open(bf) as f:
        before = json.load(f)
    with open(af) as f:
        after = json.load(f)
    orig = before.get("token_estimate", 0)
    final = after.get("token_estimate", 0)
    total_orig += orig
    total_final += final
    if final > target:
        over_target += 1
    msgs = before.get("messages", [])
    for m in msgs:
        c = m.get("content", "")
        if isinstance(c, str) and "Ask mode is active" in c:
            ask_count += 1
            break
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text" and "Ask mode is active" in b.get("text", ""):
                    ask_count += 1
                    break

print(f"总请求: {total}")
print(f"分析模式(Ask): {ask_count}")
print(f"编码模式(Code): {total - ask_count}")
print(f"总原始tokens: {total_orig//1000}K")
print(f"总压缩后tokens: {total_final//1000}K")
print(f"平均压缩率: {total_final/total_orig*100:.1f}%")
print(f"超过51K目标: {over_target}/{total}")

# 找出最大的 tool_result（压缩前后对比）
print()
print("=" * 80)
print("最大 tool_result 压缩前后对比（前10）:")
print()

big_results = []
for req_id in sorted(pairs.keys()):
    bf, af = pairs[req_id]
    with open(bf) as f:
        before = json.load(f)
    with open(af) as f:
        after = json.load(f)

    b_msgs = before.get("messages", [])
    a_msgs = after.get("messages", [])

    for mi, m in enumerate(b_msgs):
        if m.get("role") != "user":
            continue
        c = m.get("content", "")
        if not isinstance(c, list):
            continue
        for bi, block in enumerate(c):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            bc = block.get("content", "")
            if isinstance(bc, list):
                text = "\n".join(sub.get("text", "") for sub in bc if isinstance(sub, dict))
            elif isinstance(bc, str):
                text = bc
            else:
                text = ""
            if len(text) < 5000:
                continue

            # 找对应的 after
            after_text = ""
            if mi < len(a_msgs):
                ac = a_msgs[mi].get("content", "")
                if isinstance(ac, list) and bi < len(ac):
                    ab = ac[bi]
                    abc = ab.get("content", "")
                    if isinstance(abc, list):
                        after_text = "\n".join(sub.get("text", "") for sub in abc if isinstance(sub, dict))
                    elif isinstance(abc, str):
                        after_text = abc

            # 提取文件路径
            path = "?"
            lines = text.strip().split("\n", 3)
            for line in lines[:3]:
                line = line.strip()
                if line.startswith("/") and not line.startswith("//"):
                    path = line.split("\n")[0][:60]
                    break

            big_results.append({
                "req": req_id,
                "path": path,
                "before": len(text),
                "after": len(after_text),
                "ratio": len(after_text) / len(text) * 100 if len(text) > 0 else 0,
            })

big_results.sort(key=lambda x: -x["before"])
for r in big_results[:15]:
    print(f"  {r['req']}  {r['before']//1000:>5}K -> {r['after']//1000:>5}K ({r['ratio']:>5.1f}%)  {r['path']}")
