# NOTE: 此脚本在服务器上运行，路径 /opt/apollo 对应本地 server/ 目录
import json, sys

with open("/opt/apollo/debug_logs/request_body.json") as f:
    data = json.load(f)

mdl = data.get("model", "?")
strm = data.get("stream", "?")
msgs = data.get("messages", [])
tools = data.get("tools", [])

print(f"=== Cursor -> Gateway ===")
print(f"Model: {mdl}, Stream: {strm}, Messages: {len(msgs)}, Tools: {len(tools)}")

if tools:
    names = []
    for t in tools[:10]:
        fn = t.get("function", {})
        names.append(fn.get("name") or t.get("name", "?"))
    print(f"Tool names: {names}")

print()
for i, msg in enumerate(msgs):
    role = msg.get("role", "?")
    content = msg.get("content")
    tc = msg.get("tool_calls")
    tid = msg.get("tool_call_id")
    if isinstance(content, str):
        clen = len(content)
        preview = content[:120].replace("\n", "\\n")
    elif isinstance(content, list):
        clen = sum(len(str(b)) for b in content)
        types = []
        for b in content:
            if isinstance(b, dict):
                types.append(b.get("type", "?"))
            else:
                types.append("?")
        preview = f"[{len(content)} blocks: {types}]"
    else:
        clen = 0
        preview = str(content)[:100]
    extra = ""
    if tc:
        extra += f" tool_calls={len(tc)}"
        for j, call in enumerate(tc):
            fn = call.get("function", {})
            fname = fn.get("name", "?")
            fargs = fn.get("arguments", "")
            arglen = len(fargs) if isinstance(fargs, str) else len(str(fargs))
            print(f"       tc[{j}]: {fname}(args={arglen} chars) id={call.get('id','?')[:25]}")
    if tid:
        extra += f" tid={tid[:25]}"
    print(f"  [{i}] {role}({clen}){extra}: {preview[:150]}")

print()
print("=== Response Stream (modified, to Cursor) ===")
with open("/opt/apollo/debug_logs/response_stream_modified.txt") as f:
    resp = f.read()
print(f"Total size: {len(resp)} bytes")
# Parse SSE chunks
for line in resp.split("\n"):
    line = line.strip()
    if line.startswith("data: ") and line != "data: [DONE]":
        try:
            chunk = json.loads(line[6:])
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                fr = choices[0].get("finish_reason")
                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args = fn.get("arguments", "")
                        idx = tc.get("index", "?")
                        tid = tc.get("id", "")
                        if name:
                            print(f"  -> tool_call start: idx={idx} name={name} id={tid[:25]}")
                        elif args:
                            print(f"  -> tool_call args: idx={idx} +{len(args)} chars")
                if delta.get("content"):
                    c = delta["content"]
                    print(f"  -> content: {c[:100].replace(chr(10), '\\n')}")
                if fr:
                    print(f"  -> finish_reason: {fr}")
            usage = chunk.get("usage")
            if usage:
                print(f"  -> usage: prompt={usage.get('prompt_tokens',0)} completion={usage.get('completion_tokens',0)}")
        except json.JSONDecodeError:
            pass
    elif line == "data: [DONE]":
        print("  -> [DONE]")
