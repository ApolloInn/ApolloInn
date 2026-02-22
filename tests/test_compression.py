#!/usr/bin/env python3
"""Test the full compress_context pipeline."""
import warnings
warnings.filterwarnings('ignore')
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from core.context_compression import compress_context, _TS_AVAILABLE, estimate_request_tokens

print(f"tree-sitter: {_TS_AVAILABLE}")

# 构造一个 Python 代码文件
py_code = """import os
import sys
from typing import List, Dict, Optional

class TokenPool:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = []
        self._in_use = set()
        self._lock = None
        self._initialized = False

    async def initialize(self):
        self.pool = await self._load_from_db()
        self._initialized = True
        return len(self.pool)

    async def get_next_token(self) -> Optional[Dict]:
        async with self._lock:
            for token in self.pool:
                if token['id'] not in self._in_use:
                    self._in_use.add(token['id'])
                    return token
            return None

    def release_token(self, token_id: str):
        self._in_use.discard(token_id)

    async def _load_from_db(self) -> List[Dict]:
        rows = await self.db.fetch('SELECT * FROM tokens WHERE active=true')
        return [dict(r) for r in rows]

    async def validate_apikey(self, key: str) -> Optional[Dict]:
        row = await self.db.fetchrow('SELECT * FROM users WHERE apikey=$1', key)
        if not row:
            return None
        return dict(row)

    async def check_quota(self, user_id: int) -> Optional[str]:
        usage = await self.db.fetchval('SELECT count FROM usage WHERE user_id=$1', user_id)
        limit = await self.db.fetchval('SELECT daily_limit FROM users WHERE id=$1', user_id)
        if usage and limit and usage >= limit:
            return f'Daily limit {limit} reached'
        return None
""" * 50  # ~15K chars per copy, 50 copies = ~750K chars = ~300K tokens

# 构造消息
messages = [
    {"role": "system", "content": "You are a helpful coding assistant. " * 100},
    {"role": "user", "content": "Help me fix the token pool concurrency issue"},
    {"role": "assistant", "content": "I'll read the token pool file first. Let me analyze the code structure and identify potential race conditions. " * 50},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "read_1", "content": py_code},
    ]},
    {"role": "assistant", "content": "I see the issue. The _in_use set is not thread-safe. Let me also check the proxy routes to understand how tokens are acquired and released. " * 80},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "read_2", "content": py_code},
    ]},
    {"role": "assistant", "content": "Now I have a complete picture. The fix involves adding an asyncio.Lock. " * 40},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "read_3", "content": py_code},
    ]},
    # Recent messages (should be protected)
    {"role": "assistant", "content": "The fix is ready. I've added proper locking."},
    {"role": "user", "content": "Please apply the fix now"},
]

est = estimate_request_tokens(messages)
print(f"Estimated tokens before compression: {est // 1000}K")

compressed, stats = compress_context(messages, context_window=128000)

print(f"\n=== RESULTS ===")
print(f"Level: {stats['level']}")
print(f"Original: {stats['original_tokens'] // 1000}K tokens")
print(f"Final: {stats['final_tokens'] // 1000}K tokens")
print(f"Saved: {stats['tokens_saved'] // 1000}K tokens")
print(f"tree_sitter: {stats['tree_sitter']}")

print(f"\n=== MESSAGE STRUCTURE ===")
for i, m in enumerate(compressed):
    role = m.get("role")
    content = m.get("content")
    if isinstance(content, str):
        clen = len(content)
        preview = content[:80].replace('\n', ' ')
    elif isinstance(content, list):
        clen = sum(len(str(b)) for b in content)
        preview = f"[{len(content)} blocks]"
    else:
        clen = 0
        preview = "None"
    print(f"  [{i}] {role:10s} len={clen:6d}  {preview}")

# Verify structure integrity
for i, m in enumerate(compressed):
    assert "role" in m, f"msg {i}: missing role"
    assert "content" in m or "tool_calls" in m, f"msg {i}: missing content"
    if isinstance(m.get("content"), list):
        for j, b in enumerate(m["content"]):
            assert isinstance(b, dict), f"msg {i} block {j}: not dict"

print("\nStructure integrity: OK")

# Show a compressed tool_result sample
for i, m in enumerate(compressed):
    if isinstance(m.get("content"), list):
        for b in m["content"]:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                text = b.get("content", "")
                if isinstance(text, list):
                    text = text[0].get("text", "") if text else ""
                if len(text) < 3000:
                    print(f"\n=== COMPRESSED TOOL_RESULT (msg {i}) ===")
                    print(text[:800])
                    break
        break
