#!/usr/bin/env python3
"""
分析 Cursor 请求中每一轮对话的实际内容，看哪些信息有价值。
重点看：
1. assistant 发了什么工具调用
2. user 返回了什么 tool_result（内容摘要）
3. assistant 在工具调用之间说了什么文字
"""
import json
import sys
import os

def summarize_text(text, max_len=200):
    """截取文本摘要"""
    if not text:
        return "(empty)"
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... ({len(text)} chars total)"

def analyze_file(path):
    with open(path, "r") as f:
        data = json.load(f)
    
    messages = data.get("messages", data.get("body", {}).get("messages", []))
    if not messages:
        print("  No messages found")
        return
    
    print(f"  Total messages: {len(messages)}")
    print()
    
    for i, m in enumerate(messages):
        role = m.get("role", "?")
        content = m.get("content", "")
        
        if role == "system":
            if isinstance(content, str):
                print(f"  [{i:2d}] SYSTEM: {len(content)} chars")
            elif isinstance(content, list):
                total = sum(len(json.dumps(b, ensure_ascii=False)) for b in content)
                print(f"  [{i:2d}] SYSTEM: {total} chars ({len(content)} blocks)")
            continue
        
        if role == "assistant":
            text_parts = []
            tool_calls = []
            
            # Anthropic format: content list
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        if b.get("type") == "text":
                            text_parts.append(b.get("text", ""))
                        elif b.get("type") == "tool_use":
                            name = b.get("name", "?")
                            inp = b.get("input", {})
                            if isinstance(inp, dict):
                                path_val = (inp.get("path") or inp.get("relative_workspace_path") 
                                           or inp.get("pattern") or inp.get("command") or "")
                            else:
                                path_val = str(inp)[:100]
                            tool_calls.append(f"{name}({path_val})" if path_val else name)
            elif isinstance(content, str):
                text_parts.append(content)
            
            # OpenAI format: tool_calls field
            tc = m.get("tool_calls") or []
            for call in tc:
                if isinstance(call, dict):
                    func = call.get("function", {})
                    name = func.get("name", "?")
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except:
                        args = {}
                    if isinstance(args, dict):
                        path_val = (args.get("path") or args.get("relative_workspace_path")
                                   or args.get("pattern") or args.get("command") or "")
                    else:
                        path_val = ""
                    tool_calls.append(f"{name}({path_val})" if path_val else name)
            
            print(f"  [{i:2d}] ASSISTANT:")
            if text_parts:
                combined = " ".join(t.strip() for t in text_parts if t.strip())
                if combined:
                    print(f"       Text: {summarize_text(combined, 150)}")
            if tool_calls:
                print(f"       Tools ({len(tool_calls)}): {', '.join(tool_calls[:10])}")
                if len(tool_calls) > 10:
                    print(f"              ... and {len(tool_calls) - 10} more")
            continue
        
        if role == "user":
            text_parts = []
            tool_results = []
            
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        if b.get("type") == "text":
                            text_parts.append(b.get("text", ""))
                        elif b.get("type") == "tool_result":
                            tool_id = b.get("tool_use_id", "")[:8]
                            bc = b.get("content", "")
                            if isinstance(bc, str):
                                result_text = bc
                            elif isinstance(bc, list):
                                parts = []
                                for sub in bc:
                                    if isinstance(sub, dict) and sub.get("type") == "text":
                                        parts.append(sub.get("text", ""))
                                result_text = "\n".join(parts)
                            else:
                                result_text = str(bc)
                            
                            # 提取结果的关键信息
                            first_lines = result_text.strip().split("\n")[:3]
                            preview = " | ".join(l.strip() for l in first_lines if l.strip())
                            tool_results.append({
                                "id": tool_id,
                                "size": len(result_text),
                                "preview": preview[:150],
                            })
            elif isinstance(content, str):
                text_parts.append(content)
            
            print(f"  [{i:2d}] USER:")
            if text_parts:
                combined = " ".join(t.strip() for t in text_parts if t.strip())
                if combined:
                    print(f"       Text: {summarize_text(combined, 150)}")
            if tool_results:
                print(f"       Tool Results ({len(tool_results)}):")
                for tr in tool_results:
                    print(f"         [{tr['id']}] {tr['size']:,} chars: {tr['preview'][:120]}")
            continue
        
        print(f"  [{i:2d}] {role}: ???")


# 分析最大的 before 文件（最有代表性）
log_dir = "/opt/apollo/compression_logs"
files = []
for fname in os.listdir(log_dir):
    if fname.endswith("_before.json"):
        path = os.path.join(log_dir, fname)
        size = os.path.getsize(path)
        files.append((size, fname, path))

files.sort(reverse=True)

# 分析最大的一个
if files:
    size, fname, path = files[0]
    print(f"=== Analyzing: {fname} ({size//1024}K) ===")
    analyze_file(path)
