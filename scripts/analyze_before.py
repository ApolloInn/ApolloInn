import json, sys

fname = sys.argv[1] if len(sys.argv) > 1 else "/opt/apollo/compression_logs/req_194124_before.json"
with open(fname) as f:
    data = json.load(f)

print(f"Before tokens: {data.get('token_estimate')}")
print(f"Messages: {data.get('message_count')}")
print()

msgs = data["messages"]
for i, m in enumerate(msgs):
    role = m.get("role", "?")
    content = m.get("content", "")
    if isinstance(content, str):
        print(f"[{i:2d}] {role:10s} str({len(content)})")
    elif isinstance(content, list):
        blocks = []
        for b in content:
            if isinstance(b, dict):
                btype = b.get("type", "?")
                if btype == "tool_result":
                    bc = b.get("content", "")
                    text = ""
                    if isinstance(bc, str):
                        text = bc
                    elif isinstance(bc, list):
                        for sub in bc:
                            if isinstance(sub, dict) and sub.get("type") == "text":
                                text += sub.get("text", "")
                    blocks.append(f"tr({len(text)})")
                elif btype == "tool_use":
                    name = b.get("name", "?")
                    inp = b.get("input", {})
                    path = ""
                    if isinstance(inp, dict):
                        path = inp.get("path", "") or inp.get("relative_workspace_path", "") or ""
                    short = path.split("/")[-1] if path else ""
                    blocks.append(f"tu:{name}({short})")
                elif btype == "text":
                    blocks.append(f"tx({len(b.get('text', ''))})")
                else:
                    blocks.append(btype)
        summary = ", ".join(blocks[:10])
        if len(blocks) > 10:
            summary += f"... +{len(blocks)-10} more"
        print(f"[{i:2d}] {role:10s} [{summary}]")
    else:
        print(f"[{i:2d}] {role:10s} empty")
