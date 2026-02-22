#!/usr/bin/env python3
"""分析 Cursor 每次请求的完整模式：它发了什么，期望我们返回什么。"""
import json, os, re, sys

d = "/opt/apollo/compression_logs"
files = sorted([f for f in os.listdir(d) if f.endswith("_before.json")])

# 取一个中等大小的请求
target = None
for f in files:
    path = os.path.join(d, f)
    with open(path) as fh:
        data = json.load(fh)
    msgs = data.get("messages", [])
    if 15 <= len(msgs) <= 50:
        target = path
        break

if not target:
    target = os.path.join(d, files[0])

with open(target) as fh:
    data = json.load(fh)

msgs = data.get("messages", [])
tools_list = data.get("tools", [])
print("File:", os.path.basename(target), "  msgs:", len(msgs))
print()

for i, m in enumerate(msgs):
    role = m.get("role", "?")
    content = m.get("content", "")

    if role == "system":
        clen = len(content) if isinstance(content, str) else len(json.dumps(content, ensure_ascii=False))
        print("[%d] SYSTEM: %d chars" % (i, clen))
        continue

    if role == "user":
        if isinstance(content, str):
            preview = content.strip()[:120].replace("\n", " ")
            print("[%d] USER text: %s" % (i, preview))
        elif isinstance(content, list):
            parts = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type", "")
                if btype == "text":
                    t = b.get("text", "").strip()
                    if "<system_reminder>" in t:
                        if "Ask mode" in t:
                            parts.append("system_reminder(Ask mode)")
                        else:
                            parts.append("system_reminder(%d)" % len(t))
                    elif "<user_query>" in t:
                        q = re.search(r"<user_query>(.*?)(?:</user_query>|$)", t, re.DOTALL)
                        if q:
                            parts.append("QUERY: " + q.group(1).strip()[:120])
                        else:
                            parts.append("user_text(%d)" % len(t))
                    elif "<user_info>" in t:
                        parts.append("user_info(%d)" % len(t))
                    else:
                        parts.append("text(%d): %s" % (len(t), t[:80].replace("\n", " ")))
                elif btype == "tool_result":
                    bc = b.get("content", "")
                    if isinstance(bc, str):
                        tlen = len(bc)
                    elif isinstance(bc, list):
                        tlen = sum(len(sub.get("text", "")) for sub in bc if isinstance(sub, dict))
                    else:
                        tlen = 0
                    parts.append("tool_result(%d)" % tlen)
            print("[%d] USER: %s" % (i, ", ".join(parts)))
        continue

    if role == "assistant":
        text_parts = []
        tool_calls = []

        if isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    t = b.get("text", "").strip()
                    if t:
                        text_parts.append(t[:120])
                elif b.get("type") == "tool_use":
                    name = b.get("name", "?")
                    inp = b.get("input", {})
                    if isinstance(inp, dict):
                        arg = inp.get("path") or inp.get("command") or inp.get("pattern") or ""
                        if isinstance(arg, str) and len(arg) > 50:
                            arg = "..." + arg[-47:]
                    else:
                        arg = ""
                    tool_calls.append("%s(%s)" % (name, arg) if arg else name)
        elif isinstance(content, str) and content.strip():
            text_parts.append(content.strip()[:120])

        tc = m.get("tool_calls") or []
        for c in tc:
            if isinstance(c, dict):
                func = c.get("function", {})
                name = func.get("name", "?")
                tool_calls.append(name)

        line = "[%d] ASSISTANT:" % i
        if text_parts:
            line += ' "%s"' % text_parts[0]
        if tool_calls:
            shown = ", ".join(tool_calls[:5])
            if len(tool_calls) > 5:
                shown += " +%d more" % (len(tool_calls) - 5)
            line += " -> " + shown
        print(line)
        continue

print()
print("=" * 60)
print("CURSOR REQUEST PATTERN ANALYSIS")
print("=" * 60)
print()
print("Each request from Cursor is a COMPLETE conversation history:")
print("  [0]    system prompt (model instructions)")
print("  [1]    user_info (OS, workspace path, git status)")
print("  [2]    system_reminder + user_query (the actual task)")
print("  [3..N] alternating assistant/user messages (tool loop)")
print("  [N]    last user message with tool_results")
print()
print("Cursor expects us to return ONE assistant message that:")
print("  - Contains tool_use blocks (to call Read/Write/Shell/etc)")
print("  - And/or contains text (explanation, analysis, answer)")
print()
print("The tool loop works like this:")
print("  1. Cursor sends full history ending with user(tool_results)")
print("  2. We return assistant(text + tool_use calls)")
print("  3. Cursor executes the tools LOCALLY on user's machine")
print("  4. Cursor appends assistant msg + user(tool_results) to history")
print("  5. Cursor sends the ENTIRE updated history back to us")
print("  6. Repeat until assistant returns text-only (no tool calls)")
print()
print("CRITICAL: Each request contains ALL previous messages.")
print("That's why context grows so fast (100K+ tokens).")
print("Our compression must preserve the conversation structure")
print("so the model can continue the tool loop correctly.")
