"""
测试 Kiro API 的最大输出 token 数。
发送一个极简 prompt，要求模型输出尽可能长的内容。
"""
import httpx
import sys
import time

# 测试服务器
BASE_URL = "http://207.148.73.138:8000"
API_KEY = "ap-6af8fda66031a9dd"

def test_max_output():
    prompt = (
        "Write a single Python file at /tmp/test_big.py that contains exactly 500 functions. "
        "Each function should be named func_001, func_002, ... func_500. "
        "Each function should have a docstring and return a unique string. "
        "You MUST write all 500 functions in a single Write call. Do not stop early."
    )
    
    payload = {
        "model": "claude-opus-4.6",
        "stream": True,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "Writes a file to the local filesystem. This tool will overwrite the existing file if there is one at the provided path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "The path to write to"},
                            "contents": {"type": "string", "description": "The contents to write"}
                        },
                        "required": ["path", "contents"]
                    }
                }
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    print(f"Sending request to {BASE_URL}/v1/chat/completions")
    print(f"Prompt: {prompt[:80]}...")
    print()
    
    start = time.time()
    total_chars = 0
    total_chunks = 0
    finish_reason = None
    last_content = ""
    usage_info = {}
    tool_call_args = ""
    
    with httpx.stream("POST", f"{BASE_URL}/v1/chat/completions", 
                       json=payload, headers=headers, timeout=300.0) as resp:
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.read().decode()}")
            return
            
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            
            import json
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    total_chars += len(content)
                    total_chunks += 1
                    last_content = content
                
                # Capture tool_call arguments
                tc = delta.get("tool_calls", [])
                if tc:
                    for call in tc:
                        func = call.get("function", {})
                        args = func.get("arguments", "")
                        if args:
                            tool_call_args += args
                            total_chars += len(args)
                            total_chunks += 1
                
                # 每 5000 chars 打印进度
                if total_chars % 5000 < 100 and total_chars > 0:
                    elapsed = time.time() - start
                    print(f"  ... {total_chars} chars, {total_chunks} chunks, {elapsed:.1f}s")
                
                fr = choices[0].get("finish_reason")
                if fr:
                    finish_reason = fr
            
            u = chunk.get("usage")
            if u:
                usage_info = u
    
    elapsed = time.time() - start
    print()
    print(f"=== RESULT ===")
    print(f"Total output: {total_chars} chars")
    print(f"Total chunks: {total_chunks}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Finish reason: {finish_reason}")
    print(f"Usage: {usage_info}")
    print(f"Last content: ...{last_content[-100:]}")
    if tool_call_args:
        print(f"Tool call args: {len(tool_call_args)} chars")
        print(f"Tool call args end: ...{tool_call_args[-200:]}")
    
    # 估算 tokens
    est_tokens = total_chars / 2.8
    print(f"Estimated output tokens: ~{int(est_tokens)}")

if __name__ == "__main__":
    test_max_output()
