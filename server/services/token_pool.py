"""
Token Pool — Apollo Gateway 数据管理（PostgreSQL via asyncpg）。

所有方法统一 async，直连服务器本地 PostgreSQL。
热数据内存缓存，减少查询延迟。
"""

import hashlib
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict

from loguru import logger

# 北京时间 UTC+8
_BJ = timezone(timedelta(hours=8))

def _to_bj(dt) -> str:
    """将 datetime 转为北京时间 ISO 字符串。"""
    if dt is None:
        return None
    if hasattr(dt, 'astimezone'):
        return dt.astimezone(_BJ).isoformat()
    return str(dt)

DEFAULT_COMBOS = {
    "kiro-opus-4-6": ["claude-opus-4.6"],
    "kiro-sonnet-4-6": ["claude-sonnet-4.6"],
    "kiro-opus-4-5": ["claude-opus-4.5"],
    "kiro-sonnet-4-5": ["claude-sonnet-4.5"],
    "kiro-sonnet-4": ["claude-sonnet-4"],
    "kiro-haiku-4-5": ["claude-haiku-4.5"],
    "kiro-haiku": ["claude-haiku-4.5"],
    "kiro-auto": ["auto-kiro"],
}

# ── 简易 TTL 缓存（支持 stale 检测） ──
class _Cache:
    def __init__(self, ttl=30):
        self._ttl = ttl
        self._store: Dict[str, tuple] = {}  # key -> (value, expire_time)

    def get(self, key):
        item = self._store.get(key)
        if item and item[1] > time.monotonic():
            return item[0]
        return None

    def is_stale(self, key, threshold=0.8):
        """检查缓存是否即将过期（超过 threshold 比例的 TTL）。用于提前异步刷新。"""
        item = self._store.get(key)
        if not item:
            return True
        remaining = item[1] - time.monotonic()
        return remaining < self._ttl * (1 - threshold)

    def set(self, key, value):
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, *keys):
        for k in keys:
            self._store.pop(k, None)

    def clear(self):
        self._store.clear()


class TokenPool:
    def __init__(self, database_url: str):
        self._dsn = database_url
        self._pool = None
        self._rr_index = 0
        # 内存缓存：认证 120s，模型映射 300s（减少跨海查询）
        self._auth_cache = _Cache(ttl=120)
        self._mapping_cache = _Cache(ttl=300)
        self._quota_cache = _Cache(ttl=15)  # 配额缓存 15s，平衡实时性和性能

    async def init(self):
        import asyncpg
        # 本地 PG 不需要 SSL，远程（Supabase 等）需要
        ssl_param = False
        if 'localhost' not in self._dsn and '127.0.0.1' not in self._dsn:
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            ssl_param = ssl_ctx
        self._pool = await asyncpg.create_pool(self._dsn, min_size=5, max_size=20, ssl=ssl_param)
        await self._ensure_schema()
        await self._seed_builtins()
        logger.info("TokenPool initialized (PostgreSQL)")

    async def _ensure_schema(self):
        schema_file = Path(__file__).parent.parent / "db" / "schema.sql"
        if schema_file.exists():
            sql = schema_file.read_text()
            async with self._pool.acquire() as conn:
                # 用 advisory lock 防止多 worker 同时执行 DDL 导致死锁
                await conn.execute("SELECT pg_advisory_lock(42)")
                try:
                    await conn.execute(sql)
                finally:
                    await conn.execute("SELECT pg_advisory_unlock(42)")

    async def _seed_builtins(self):
        async with self._pool.acquire() as conn:
            for name, targets in DEFAULT_COMBOS.items():
                await conn.execute(
                    """INSERT INTO model_mappings (name, type, targets, is_builtin)
                       VALUES ($1, 'combo', $2, true)
                       ON CONFLICT (name) DO UPDATE SET targets = $2""",
                    name, json.dumps(targets),
                )

    # ── Admin Key ──

    ADMIN_KEY = "Ljc17748697418."

    async def _load_admin_key(self) -> str:
        return self.ADMIN_KEY

    def get_admin_key(self):
        return self.ADMIN_KEY

    def verify_admin_key(self, key):
        return bool(key) and key == self.ADMIN_KEY

    # ── Token CRUD ──

    async def add_token(self, token_data, note: str = ""):
        client_id_hash = token_data.get("clientIdHash", "")
        now = datetime.now(timezone.utc)

        # 同 clientIdHash + 同 refreshToken → 更新（同一账号刷新）
        # 同 clientIdHash + 不同 refreshToken → 新增（同设备不同账号）
        new_refresh = token_data.get("refreshToken", "")
        if client_id_hash:
            async with self._pool.acquire() as conn:
                existing = await conn.fetchrow(
                    "SELECT id, refresh_token FROM tokens WHERE client_id_hash = $1 AND refresh_token = $2",
                    client_id_hash, new_refresh,
                )
            if existing:
                tid = existing["id"]
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE tokens SET refresh_token=$1, access_token=$2, expires_at=$3,
                           region=$4, client_id=$5, client_secret=$6, auth_method=$7,
                           provider=$8, profile_arn=$9, status='active'
                           WHERE id=$10""",
                        new_refresh, token_data.get("accessToken", ""),
                        token_data.get("expiresAt", ""), token_data.get("region", "us-east-1"),
                        token_data.get("clientId", ""), token_data.get("clientSecret", ""),
                        token_data.get("authMethod", ""), token_data.get("provider", ""),
                        token_data.get("profileArn", ""), tid,
                    )
                logger.info(f"Token updated (same account): id={tid} note={note}")
                self._auth_cache.invalidate("all_tokens")
                return {"id": tid, "status": "active", "addedAt": _to_bj(now),
                        "useCount": 0, "updated": True, **token_data}

        # 新凭证 → 插入
        tid = secrets.token_hex(8)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO tokens (id, refresh_token, access_token, expires_at, region,
                   client_id_hash, client_id, client_secret, auth_method, provider, profile_arn,
                   status, added_at, use_count)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'active',$12,0)""",
                tid, token_data.get("refreshToken", ""), token_data.get("accessToken", ""),
                token_data.get("expiresAt", ""), token_data.get("region", "us-east-1"),
                client_id_hash, token_data.get("clientId", ""),
                token_data.get("clientSecret", ""), token_data.get("authMethod", ""),
                token_data.get("provider", ""), token_data.get("profileArn", ""), now,
            )
        entry = {"id": tid, "status": "active", "addedAt": _to_bj(now), "useCount": 0, **token_data}
        logger.info(f"Token added: id={tid}")
        self._auth_cache.invalidate("all_tokens")
        return entry

    async def remove_token(self, token_id):
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM tokens WHERE id = $1", token_id)
        self._auth_cache.invalidate("all_tokens")
        return res == "DELETE 1"

    def _row_to_token(self, r):
        return {
            "id": r["id"], "refreshToken": r["refresh_token"], "accessToken": r["access_token"],
            "expiresAt": r["expires_at"], "region": r["region"], "clientIdHash": r["client_id_hash"],
            "clientId": r["client_id"], "clientSecret": r["client_secret"],
            "authMethod": r["auth_method"], "provider": r["provider"], "profileArn": r["profile_arn"],
            "status": r["status"],
            "addedAt": _to_bj(r["added_at"]),
            "lastUsed": _to_bj(r["last_used"]),
            "useCount": r["use_count"],
        }

    async def list_tokens(self):
        cached = self._auth_cache.get("all_tokens")
        if cached is not None:
            return cached
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tokens ORDER BY added_at")
        result = []
        for r in rows:
            t = self._row_to_token(r)
            for f in ("refreshToken", "accessToken", "clientSecret"):
                if t.get(f):
                    t[f] = t[f][:16] + "..."
            result.append(t)
        self._auth_cache.set("all_tokens", result)
        return result

    async def get_token_full(self, token_id):
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM tokens WHERE id = $1", token_id)
        if not r:
            return None
        return self._row_to_token(r)

    async def get_next_token(self):
        """获取下一个可用 token（轮询）。"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tokens WHERE status = 'active' ORDER BY added_at")
        if not rows:
            return None
        n = len(rows)
        idx = self._rr_index % n
        self._rr_index = (idx + 1) % n
        return self._row_to_token(rows[idx])

    def release_token(self, token_id: str):
        """兼容接口，不再做并发控制。"""
        pass

    async def mark_token_used(self, token_id):
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE tokens SET last_used = $1, use_count = use_count + 1 WHERE id = $2", now, token_id,
            )

    async def set_token_status(self, token_id: str, status: str, reason: str = "") -> bool:
        """设置 token 状态（active/disabled）。致命 403 时自动调用。"""
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE tokens SET status = $1 WHERE id = $2", status, token_id,
            )
            if res == "UPDATE 1":
                logger.warning(
                    f"Token {token_id[:8]} status -> {status}"
                    + (f" (reason: {reason})" if reason else "")
                )
                self._auth_cache.invalidate("all_tokens")
                return True
        return False

    async def update_token_credentials(self, token_id, updates):
        col_map = {"accessToken": "access_token", "refreshToken": "refresh_token",
                    "expiresAt": "expires_at", "clientSecret": "client_secret"}
        sets, vals = [], []
        i = 1
        for k, v in updates.items():
            sets.append(f"{col_map.get(k, k)} = ${i}")
            vals.append(v)
            i += 1
        if sets:
            vals.append(token_id)
            async with self._pool.acquire() as conn:
                await conn.execute(f"UPDATE tokens SET {', '.join(sets)} WHERE id = ${i}", *vals)

    # ── User CRUD ──

    def _row_to_user(self, r, apikeys=None):
        u = {
            "id": r["id"], "name": r["name"], "usertoken": r["usertoken"],
            "status": r["status"],
            "assigned_token_id": r.get("assigned_token_id", "") or "",
            "cursor_email": r.get("cursor_email", "") or "",
            "switch_count": r.get("switch_count", 0) or 0,
            "agent_id": r.get("agent_id", "") or "",
            "createdAt": _to_bj(r["created_at"]),
            "lastUsed": _to_bj(r["last_used"]),
            "requestCount": r["request_count"],
            "token_balance": r["token_balance"], "token_granted": r["token_granted"],
            "quota": {
                "daily_tokens": r["quota_daily_tokens"],
                "monthly_tokens": r["quota_monthly_tokens"],
                "daily_requests": r["quota_daily_requests"],
            },
        }
        if apikeys is not None:
            u["apikeys"] = apikeys
        return u

    async def create_user(self, name="", assigned_token_id=""):
        uid = secrets.token_hex(8)
        uname = name or f"User-{secrets.token_hex(4)}"
        usertoken = f"apollo-{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO users (id, name, usertoken, status, assigned_token_id, created_at, request_count,
                   token_balance, token_granted, quota_daily_tokens, quota_monthly_tokens, quota_daily_requests)
                   VALUES ($1,$2,$3,'active',$4,$5,0,0,0,0,0,0)""",
                uid, uname, usertoken, assigned_token_id, now,
            )
        logger.info(f"User created: {uname}, assigned_token={assigned_token_id or 'none'}")
        self._auth_cache.invalidate("all_users")
        return {
            "id": uid, "name": uname, "usertoken": usertoken, "apikeys": [],
            "status": "active", "assigned_token_id": assigned_token_id,
            "createdAt": _to_bj(now), "lastUsed": None, "requestCount": 0,
            "usage": {"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_tokens": 0, "by_model": {}, "by_date": {}},
            "token_balance": 0, "token_granted": 0,
            "quota": {"daily_tokens": 0, "monthly_tokens": 0, "daily_requests": 0},
        }

    async def remove_user(self, user_id):
        async with self._pool.acquire() as conn:
            # 查询用户的剩余额度和所属代理商
            row = await conn.fetchrow(
                "SELECT token_balance, agent_id, name FROM users WHERE id = $1", user_id
            )
            if not row:
                return False
            balance = row["token_balance"] or 0
            agent_id = row["agent_id"] or ""

            # 写退还流水（在删除前记录）
            if balance > 0 and agent_id:
                await conn.execute(
                    """INSERT INTO token_transactions (user_id, agent_id, type, amount, balance_after, source, note)
                       VALUES ($1, $2, 'refund', $3, 0, 'system', $4)""",
                    user_id, agent_id, balance, f"用户 {row['name']} 删除退还",
                )

            # 删除用户
            res = await conn.execute("DELETE FROM users WHERE id = $1", user_id)

            # 退还剩余额度给代理商
            if balance > 0 and agent_id:
                await conn.execute(
                    "UPDATE agents SET token_used = token_used - $1 WHERE id = $2",
                    balance, agent_id
                )
        self._auth_cache.clear()
        return res == "DELETE 1"

    async def list_users(self):
        cached = self._auth_cache.get("all_users")
        if cached is not None:
            return cached
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY created_at")
            apikeys = await conn.fetch("SELECT user_id, count(*) as cnt FROM user_apikeys GROUP BY user_id")
        key_counts = {r["user_id"]: r["cnt"] for r in apikeys}
        result = []
        for r in rows:
            u = self._row_to_user(r)
            u["usertoken"] = u["usertoken"][:12] + "..."
            u["apikeys_count"] = key_counts.get(r["id"], 0)
            result.append(u)
        self._auth_cache.set("all_users", result)
        return result

    async def get_user_full(self, user_id):
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            if not r:
                return None
            keys = await conn.fetch("SELECT apikey FROM user_apikeys WHERE user_id = $1", user_id)
        return self._row_to_user(r, apikeys=[k["apikey"] for k in keys])

    # ── 认证 ──

    async def validate_login(self, usertoken):
        cache_key = f"login:{usertoken}"
        cached = self._auth_cache.get(cache_key)
        if cached is not None:
            if self._auth_cache.is_stale(cache_key):
                import asyncio
                asyncio.create_task(self._refresh_login_cache(usertoken))
            return cached
        return await self._refresh_login_cache(usertoken)

    async def _refresh_login_cache(self, usertoken):
        cache_key = f"login:{usertoken}"
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM users WHERE usertoken = $1 AND status = 'active'", usertoken)
            if not r:
                return None
            keys = await conn.fetch("SELECT apikey FROM user_apikeys WHERE user_id = $1", r["id"])
        result = self._row_to_user(r, apikeys=[k["apikey"] for k in keys])
        self._auth_cache.set(cache_key, result)
        return result

    async def validate_apikey(self, apikey):
        cache_key = f"apikey:{apikey}"
        cached = self._auth_cache.get(cache_key)
        if cached is not None:
            # 缓存快过期时，后台异步刷新（用户不等待）
            if self._auth_cache.is_stale(cache_key):
                import asyncio
                asyncio.create_task(self._refresh_apikey_cache(apikey))
            return cached
        return await self._refresh_apikey_cache(apikey)

    async def _refresh_apikey_cache(self, apikey):
        cache_key = f"apikey:{apikey}"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT u.* FROM users u JOIN user_apikeys k ON k.user_id = u.id
                   WHERE k.apikey = $1 AND u.status = 'active'""", apikey,
            )
            if not row:
                return None
            keys = await conn.fetch("SELECT apikey FROM user_apikeys WHERE user_id = $1", row["id"])
        result = self._row_to_user(row, apikeys=[k["apikey"] for k in keys])
        self._auth_cache.set(cache_key, result)
        return result

    async def mark_user_used(self, user_id):
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_used = $1, request_count = request_count + 1 WHERE id = $2", now, user_id,
            )

    async def set_user_status(self, user_id, status):
        async with self._pool.acquire() as conn:
            res = await conn.execute("UPDATE users SET status = $1 WHERE id = $2", status, user_id)
            if res == "UPDATE 1":
                logger.info(f"User {user_id} status -> {status}")
                self._auth_cache.clear()
                return True
        return False

    async def assign_token(self, user_id: str, token_id: str) -> bool:
        """给用户分配/更换转发凭证。token_id 为空字符串表示取消绑定（回退到全局轮询）。"""
        async with self._pool.acquire() as conn:
            res = await conn.execute("UPDATE users SET assigned_token_id = $1 WHERE id = $2", token_id, user_id)
            if res == "UPDATE 1":
                self._auth_cache.clear()
                logger.info(f"User {user_id} assigned token -> {token_id or 'global'}")
                return True
        return False

    async def update_cursor_email(self, user_id: str, email: str) -> bool:
        """记录用户当前登录的 Cursor 账号邮箱。"""
        async with self._pool.acquire() as conn:
            res = await conn.execute("UPDATE users SET cursor_email = $1 WHERE id = $2", email, user_id)
            if res == "UPDATE 1":
                self._auth_cache.clear()
                return True
        return False

    async def increment_switch_count(self, user_id: str) -> int:
        """换号计数 +1，返回更新后的值。"""
        async with self._pool.acquire() as conn:
            r = await conn.fetchval(
                "UPDATE users SET switch_count = COALESCE(switch_count, 0) + 1 WHERE id = $1 RETURNING switch_count",
                user_id,
            )
            self._auth_cache.clear()
            return r or 0

    async def reset_switch_count(self, user_id: str) -> bool:
        """管理员重置用户换号次数。"""
        async with self._pool.acquire() as conn:
            res = await conn.execute("UPDATE users SET switch_count = 0 WHERE id = $1", user_id)
            if res == "UPDATE 1":
                self._auth_cache.clear()
                return True
        return False

    async def get_user_token_entry(self, user):
        """获取用户应该使用的凭证。优先用绑定的，否则全局轮询。"""
        assigned = user.get("assigned_token_id", "")
        if assigned:
            entry = await self.get_token_full(assigned)
            if entry and entry.get("status") == "active":
                return entry
            logger.warning(f"User {user['id']} assigned token {assigned} unavailable, falling back to global")
        return await self.get_next_token()

    # ── 用户 API Key ──

    async def create_user_apikey(self, user_id):
        new_key = f"ap-{secrets.token_hex(8)}"
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
            if not r:
                return None
            await conn.execute("INSERT INTO user_apikeys (apikey, user_id) VALUES ($1, $2)", new_key, user_id)
        self._auth_cache.clear()
        logger.info(f"API key created for user {user_id}: {new_key[:8]}...")
        return new_key

    async def revoke_user_apikey(self, user_id, apikey):
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM user_apikeys WHERE apikey = $1 AND user_id = $2", apikey, user_id)
        self._auth_cache.clear()
        return res == "DELETE 1"

    async def list_user_apikeys(self, user_id):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT apikey FROM user_apikeys WHERE user_id = $1", user_id)
        return [r["apikey"] for r in rows]

    # ── Combo ──

    async def resolve_combo(self, name):
        cached = self._mapping_cache.get(f"combo:{name}")
        if cached is not None:
            return cached
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT targets FROM model_mappings WHERE name = $1 AND type = 'combo'", name)
        result = json.loads(r["targets"]) if r else None
        if result is not None:
            self._mapping_cache.set(f"combo:{name}", result)
        return result

    async def list_combos(self):
        cached = self._mapping_cache.get("all_combos")
        if cached is not None:
            return cached
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT name, targets FROM model_mappings WHERE type = 'combo' ORDER BY name")
        result = {r["name"]: json.loads(r["targets"]) for r in rows}
        self._mapping_cache.set("all_combos", result)
        return result

    async def set_combo(self, name, models):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO model_mappings (name, type, targets, is_builtin) VALUES ($1, 'combo', $2, false)
                   ON CONFLICT (name) DO UPDATE SET targets = $2""", name, json.dumps(models),
            )
        self._mapping_cache.clear()

    async def remove_combo(self, name):
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM model_mappings WHERE name = $1 AND type = 'combo' AND is_builtin = false", name)
        self._mapping_cache.clear()
        return res == "DELETE 1"

    async def resolve_model(self, name):
        name_lower = name.lower()
        cache_key = f"resolve:{name_lower}"
        cached = self._mapping_cache.get(cache_key)
        if cached is not None:
            return cached

        # Strip -thinking suffix before combo lookup, re-append after resolution
        # e.g. kiro-opus-4-6-thinking → lookup kiro-opus-4-6 → claude-opus-4.6 → claude-opus-4.6-thinking
        is_thinking = name_lower.endswith('-thinking')
        lookup_name = name_lower[:-len('-thinking')] if is_thinking else name_lower

        combo = await self.resolve_combo(lookup_name)
        if combo:
            resolved = combo[0] + ('-thinking' if is_thinking else '')
            self._mapping_cache.set(cache_key, resolved)
            return resolved
        self._mapping_cache.set(cache_key, name)  # 缓存未命中的也存起来，避免反复查库
        return name

    # ── 用量追踪 ──

    # 模型系列计费权重（以 $25/1M 为 1 计费token 基准）
    # Opus:   input $5/1M → 0.2,  output $25/1M → 1.0
    # Sonnet: input $3/1M → 0.12, output $15/1M → 0.6
    # Haiku:  input $1/1M → 0.04, output $5/1M  → 0.2
    MODEL_BILLING = {
        "opus":   (0.2,  1.0),
        "sonnet": (0.12, 0.6),
        "haiku":  (0.04, 0.2),
    }

    @staticmethod
    def _get_model_tier(model: str) -> str:
        m = model.lower()
        if "opus" in m:
            return "opus"
        if "sonnet" in m:
            return "sonnet"
        if "haiku" in m:
            return "haiku"
        return "opus"  # auto / unknown 按最高档

    async def record_usage(self, user_id: str, model: str, prompt_tokens: int, completion_tokens: int, token_id: str = ""):
        tier = self._get_model_tier(model)
        input_w, output_w = self.MODEL_BILLING.get(tier, (0.2, 1.0))
        total = int(prompt_tokens * input_w) + int(completion_tokens * output_w)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO usage_records (user_id, model, prompt_tokens, completion_tokens, token_id) VALUES ($1,$2,$3,$4,$5)",
                user_id, model, prompt_tokens, completion_tokens, token_id,
            )
            await conn.execute(
                "UPDATE users SET token_balance = GREATEST(0, token_balance - $1) WHERE id = $2", total, user_id,
            )
        self._quota_cache.invalidate(f"quota:{user_id}")
        logger.debug(f"Usage recorded: user={user_id} model={model} token={token_id} +{total}")
        return True

    async def get_token_usage(self, token_id: str) -> Dict:
        """获取某个凭证的用量统计。"""
        async with self._pool.acquire() as conn:
            totals = await conn.fetchrow(
                "SELECT COALESCE(SUM(prompt_tokens),0) as tp, COALESCE(SUM(completion_tokens),0) as tc, COUNT(*) as cnt "
                "FROM usage_records WHERE token_id = $1", token_id,
            )
            by_model = await conn.fetch(
                "SELECT model, SUM(prompt_tokens) as p, SUM(completion_tokens) as c, COUNT(*) as r "
                "FROM usage_records WHERE token_id = $1 GROUP BY model", token_id,
            )
        return {
            "token_id": token_id,
            "total_prompt_tokens": totals["tp"],
            "total_completion_tokens": totals["tc"],
            "total_tokens": totals["tp"] + totals["tc"],
            "total_requests": totals["cnt"],
            "by_model": {r["model"]: {"prompt": r["p"], "completion": r["c"], "requests": r["r"]} for r in by_model},
        }

    async def get_all_token_usage(self) -> Dict[str, Dict]:
        """获取所有凭证的用量统计。"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT token_id, COALESCE(SUM(prompt_tokens),0) as tp, COALESCE(SUM(completion_tokens),0) as tc, COUNT(*) as cnt "
                "FROM usage_records WHERE token_id != '' GROUP BY token_id"
            )
        return {
            r["token_id"]: {
                "total_prompt_tokens": r["tp"], "total_completion_tokens": r["tc"],
                "total_tokens": r["tp"] + r["tc"], "total_requests": r["cnt"],
            } for r in rows
        }

    async def check_quota(self, user_id: str) -> Optional[str]:
        cache_key = f"quota:{user_id}"
        cached = self._quota_cache.get(cache_key)
        if cached is not None:
            return cached if cached != "__pass__" else None
        result = await self._check_quota_db(user_id)
        self._quota_cache.set(cache_key, result if result else "__pass__")
        return result

    async def _check_quota_db(self, user_id: str) -> Optional[str]:
        async with self._pool.acquire() as conn:
            u = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            if not u:
                return None
            if u["token_balance"] <= 0:
                return f"Token balance exhausted (granted: {u['token_granted']})"
            today = datetime.now(_BJ).strftime("%Y-%m-%d")
            if u["quota_daily_requests"] > 0:
                cnt = await conn.fetchval(
                    "SELECT COUNT(*) FROM usage_records WHERE user_id = $1 AND (recorded_at AT TIME ZONE 'Asia/Shanghai')::date = $2::date", user_id, today,
                )
                if cnt >= u["quota_daily_requests"]:
                    return f"Daily request limit reached ({u['quota_daily_requests']})"
            if u["quota_daily_tokens"] > 0:
                t = await conn.fetchval(
                    "SELECT COALESCE(SUM(prompt_tokens+completion_tokens),0) FROM usage_records WHERE user_id=$1 AND (recorded_at AT TIME ZONE 'Asia/Shanghai')::date=$2::date",
                    user_id, today,
                )
                if t >= u["quota_daily_tokens"]:
                    return f"Daily token limit reached ({u['quota_daily_tokens']})"
            if u["quota_monthly_tokens"] > 0:
                ms = datetime.now(_BJ).strftime("%Y-%m-01")
                t = await conn.fetchval(
                    "SELECT COALESCE(SUM(prompt_tokens+completion_tokens),0) FROM usage_records WHERE user_id=$1 AND (recorded_at AT TIME ZONE 'Asia/Shanghai')::date>=$2::date",
                    user_id, ms,
                )
                if t >= u["quota_monthly_tokens"]:
                    return f"Monthly token limit reached ({u['quota_monthly_tokens']})"
        return None

    async def get_user_usage(self, user_id: str) -> Optional[Dict]:
        async with self._pool.acquire() as conn:
            u = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            if not u:
                return None
            by_model_rows = await conn.fetch(
                "SELECT model, SUM(prompt_tokens) as p, SUM(completion_tokens) as c, COUNT(*) as r FROM usage_records WHERE user_id=$1 GROUP BY model", user_id,
            )
            by_date_rows = await conn.fetch(
                "SELECT (recorded_at AT TIME ZONE 'Asia/Shanghai')::date as d, SUM(prompt_tokens) as p, SUM(completion_tokens) as c, COUNT(*) as r FROM usage_records WHERE user_id=$1 GROUP BY d ORDER BY d DESC", user_id,
            )
            totals = await conn.fetchrow(
                "SELECT COALESCE(SUM(prompt_tokens),0) as tp, COALESCE(SUM(completion_tokens),0) as tc FROM usage_records WHERE user_id=$1", user_id,
            )
            # 新计费分界点：2026-02-12 22:00 UTC（中国 2/13 06:00）
            # 之前：prompt + completion（统一）；之后：按模型系列分档计费
            old = await conn.fetchrow(
                "SELECT COALESCE(SUM(prompt_tokens),0) as p, COALESCE(SUM(completion_tokens),0) as c FROM usage_records WHERE user_id=$1 AND recorded_at < '2026-02-12 22:00:00+00'", user_id,
            )
            new_by_model = await conn.fetch(
                "SELECT model, COALESCE(SUM(prompt_tokens),0) as p, COALESCE(SUM(completion_tokens),0) as c FROM usage_records WHERE user_id=$1 AND recorded_at >= '2026-02-12 22:00:00+00' GROUP BY model", user_id,
            )
            new_billed = 0
            for r in new_by_model:
                iw, ow = self.MODEL_BILLING.get(self._get_model_tier(r["model"]), (0.2, 1.0))
                new_billed += int(r["p"] * iw) + int(r["c"] * ow)
            billed_total = (old["p"] + old["c"]) + new_billed
        return {
            "user_id": u["id"], "name": u["name"],
            "token_balance": u["token_balance"], "token_granted": u["token_granted"],
            "usage": {
                "total_prompt_tokens": totals["tp"], "total_completion_tokens": totals["tc"],
                "total_tokens": billed_total,
                "by_model": {r["model"]: {"prompt": r["p"], "completion": r["c"], "requests": r["r"]} for r in by_model_rows},
                "by_date": {str(r["d"]): {"prompt": r["p"], "completion": r["c"], "requests": r["r"]} for r in by_date_rows},
            },
            "quota": {"daily_tokens": u["quota_daily_tokens"], "monthly_tokens": u["quota_monthly_tokens"], "daily_requests": u["quota_daily_requests"]},
            "requestCount": u["request_count"],
        }

    async def get_user_recent_records(self, user_id: str, limit: int = 20) -> Optional[list]:
        async with self._pool.acquire() as conn:
            u = await conn.fetchrow("SELECT id, name FROM users WHERE id = $1", user_id)
            if not u:
                return None
            rows = await conn.fetch(
                "SELECT model, prompt_tokens, completion_tokens, token_id, recorded_at AT TIME ZONE 'Asia/Shanghai' as recorded_at FROM usage_records WHERE user_id=$1 ORDER BY recorded_at DESC LIMIT $2",
                user_id, limit,
            )
        result = []
        for r in rows:
            iw, ow = self.MODEL_BILLING.get(self._get_model_tier(r["model"]), (0.2, 1.0))
            result.append({
                "model": r["model"],
                "prompt_tokens": r["prompt_tokens"],
                "completion_tokens": r["completion_tokens"],
                "billed": int(r["prompt_tokens"] * iw) + int(r["completion_tokens"] * ow),
                "token_id": r["token_id"],
                "recorded_at": str(r["recorded_at"]),
            })
        return result


    async def get_all_usage(self) -> Dict:
        async with self._pool.acquire() as conn:
            totals = await conn.fetchrow("SELECT COALESCE(SUM(prompt_tokens),0) as tp, COALESCE(SUM(completion_tokens),0) as tc FROM usage_records")
            total_requests = await conn.fetchval("SELECT COALESCE(SUM(request_count),0) FROM users")
            by_model_rows = await conn.fetch(
                "SELECT model, SUM(prompt_tokens) as p, SUM(completion_tokens) as c, COUNT(*) as r FROM usage_records GROUP BY model"
            )
            by_date_rows = await conn.fetch(
                "SELECT (recorded_at AT TIME ZONE 'Asia/Shanghai')::date as d, SUM(prompt_tokens) as p, SUM(completion_tokens) as c, COUNT(*) as r FROM usage_records GROUP BY d ORDER BY d DESC"
            )
            users_rows = await conn.fetch(
                """SELECT u.id, u.name, u.status, u.token_balance, u.token_granted, u.request_count,
                   COALESCE(SUM(r.prompt_tokens+r.completion_tokens),0) as raw_tokens,
                   COALESCE(SUM(
                     CASE
                       WHEN r.model ILIKE '%%opus%%' THEN (r.prompt_tokens * 0.2 + r.completion_tokens * 1.0)::bigint
                       WHEN r.model ILIKE '%%sonnet%%' THEN (r.prompt_tokens * 0.12 + r.completion_tokens * 0.6)::bigint
                       WHEN r.model ILIKE '%%haiku%%' THEN (r.prompt_tokens * 0.04 + r.completion_tokens * 0.2)::bigint
                       ELSE (r.prompt_tokens * 0.2 + r.completion_tokens * 1.0)::bigint
                     END
                   ), 0) as total_tokens
                   FROM users u LEFT JOIN usage_records r ON r.user_id=u.id GROUP BY u.id ORDER BY total_tokens DESC"""
            )
        return {
            "total_prompt_tokens": totals["tp"], "total_completion_tokens": totals["tc"],
            "total_tokens": totals["tp"] + totals["tc"], "total_requests": total_requests,
            "by_model": {r["model"]: {"prompt": r["p"], "completion": r["c"], "requests": r["r"]} for r in by_model_rows},
            "by_date": {str(r["d"]): {"prompt": r["p"], "completion": r["c"], "requests": r["r"]} for r in by_date_rows},
            "users": [{"user_id": r["id"], "name": r["name"], "status": r["status"],
                        "token_balance": r["token_balance"], "token_granted": r["token_granted"],
                        "total_tokens": r["total_tokens"], "requestCount": r["request_count"]} for r in users_rows],
        }

    async def set_user_quota(self, user_id: str, quota_updates: Dict) -> bool:
        col_map = {"daily_tokens": "quota_daily_tokens", "monthly_tokens": "quota_monthly_tokens", "daily_requests": "quota_daily_requests"}
        sets, vals = [], []
        i = 1
        for k in ("daily_tokens", "monthly_tokens", "daily_requests"):
            if k in quota_updates:
                sets.append(f"{col_map[k]} = ${i}")
                vals.append(int(quota_updates[k]))
                i += 1
        if not sets:
            return False
        vals.append(user_id)
        async with self._pool.acquire() as conn:
            res = await conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ${i}", *vals)
        self._auth_cache.invalidate("all_users")
        return res == "UPDATE 1"

    async def grant_tokens(self, user_id: str, amount: int) -> Optional[Dict]:
        async with self._pool.acquire() as conn:
            u = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            if not u:
                return None
            new_balance = max(0, u["token_balance"] + amount)
            new_granted = u["token_granted"] + amount if amount > 0 else u["token_granted"]
            await conn.execute("UPDATE users SET token_balance=$1, token_granted=$2 WHERE id=$3", new_balance, new_granted, user_id)
            # 写流水
            await conn.execute(
                """INSERT INTO token_transactions (user_id, agent_id, type, amount, balance_after, source, note)
                   VALUES ($1, $2, $3, $4, $5, 'admin', '')""",
                user_id, u.get("agent_id") or "", "grant" if amount > 0 else "deduct", amount, new_balance,
            )
        logger.info(f"Tokens granted to {user_id}: +{amount}, balance={new_balance}")
        self._auth_cache.invalidate("all_users")
        return {"user_id": user_id, "name": u["name"], "token_balance": new_balance, "token_granted": new_granted}

    async def reset_user_usage(self, user_id: str) -> bool:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM usage_records WHERE user_id = $1", user_id)
            res = await conn.execute("UPDATE users SET request_count = 0 WHERE id = $1", user_id)
        self._auth_cache.invalidate("all_users")
        return res == "UPDATE 1"

    # ── Cursor Pro 凭证管理 ──

    def _row_to_cursor_token(self, r):
        machine_ids = r.get("machine_ids")
        if isinstance(machine_ids, str):
            try:
                machine_ids = json.loads(machine_ids)
            except Exception:
                machine_ids = {}
        return {
            "id": r["id"], "email": r["email"],
            "password": r.get("password", "") or "",
            "access_token": r["access_token"], "refresh_token": r["refresh_token"],
            "note": r["note"], "status": r["status"],
            "assigned_user": r["assigned_user"] or "",
            "machine_ids": machine_ids or {},
            "last_refreshed_at": _to_bj(r.get("last_refreshed_at")),
            "addedAt": _to_bj(r["added_at"]),
            "lastUsed": _to_bj(r["last_used"]),
            "useCount": r["use_count"],
        }

    @staticmethod
    def _generate_machine_ids() -> dict:
        """生成一套固定机器码，存入 DB 后所有共享该账号的用户写入相同值。"""
        dev_device_id = str(uuid.uuid4())
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        mac_machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
        return {
            "devDeviceId": dev_device_id,
            "macMachineId": mac_machine_id,
            "machineId": machine_id,
            "sqmId": sqm_id,
            "serviceMachineId": machine_id,
            "fileId": str(uuid.uuid4()),
        }

    async def add_cursor_token(self, data: Dict) -> Dict:
        email = data.get("email", "")
        password = data.get("password", "")
        now = datetime.now(timezone.utc)
        # 优先使用上传的真实 machine_ids，否则自动生成
        uploaded_ids = data.get("machine_ids")
        if uploaded_ids and isinstance(uploaded_ids, dict) and uploaded_ids.get("machineId"):
            machine_ids = json.dumps(uploaded_ids)
        else:
            machine_ids = json.dumps(self._generate_machine_ids())

        # 同 email 的凭证已存在 → 更新（保留已有 machine_ids）
        if email:
            async with self._pool.acquire() as conn:
                existing = await conn.fetchrow(
                    "SELECT id FROM cursor_tokens WHERE email = $1", email
                )
            if existing:
                tid = existing["id"]
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE cursor_tokens SET access_token=$1, refresh_token=$2,
                           password=$3, note=$4, status='active', last_refreshed_at=$5,
                           machine_ids = CASE WHEN machine_ids IS NULL OR machine_ids = '{}' THEN $6::jsonb ELSE machine_ids END
                           WHERE id=$7""",
                        data.get("accessToken", ""), data.get("refreshToken", ""),
                        password, data.get("note", ""), now, machine_ids, tid,
                    )
                logger.info(f"Cursor token updated (same email): id={tid} email={email}")
                return {"id": tid, "email": email, "status": "active",
                        "note": data.get("note", ""), "addedAt": _to_bj(now),
                        "useCount": 0, "updated": True}

        # 新凭证 → 插入（生成 machine_ids）
        tid = secrets.token_hex(8)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO cursor_tokens (id, email, password, access_token, refresh_token, note, status, added_at, use_count, machine_ids, last_refreshed_at)
                   VALUES ($1,$2,$3,$4,$5,$6,'active',$7,0,$8::jsonb,$7)""",
                tid, email, password, data.get("accessToken", ""),
                data.get("refreshToken", ""), data.get("note", ""), now, machine_ids,
            )
        logger.info(f"Cursor token added: id={tid} email={email}")
        return {"id": tid, "email": email, "status": "active",
                "note": data.get("note", ""), "addedAt": _to_bj(now), "useCount": 0}

    async def list_cursor_tokens(self):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cursor_tokens ORDER BY added_at")
            # 查询所有用户的 cursor_email 映射，用于显示每个账号分配给了哪些用户
            user_rows = await conn.fetch(
                "SELECT name, cursor_email FROM users WHERE cursor_email != '' AND status = 'active'"
            )
        # 构建 email -> [user_name, ...] 映射
        email_users: dict[str, list[str]] = {}
        for u in user_rows:
            email_users.setdefault(u["cursor_email"], []).append(u["name"])
        result = []
        for r in rows:
            t = self._row_to_cursor_token(r)
            # 用 users 表的 cursor_email 反查所有分配用户
            assigned_list = email_users.get(t["email"], [])
            if assigned_list:
                t["assigned_user"] = ", ".join(assigned_list)
            # 脱敏
            if t["access_token"]:
                t["access_token"] = t["access_token"][:16] + "..."
            if t["refresh_token"]:
                t["refresh_token"] = t["refresh_token"][:16] + "..."
            result.append(t)
        return result

    async def remove_cursor_token(self, token_id: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM cursor_tokens WHERE id = $1", token_id)
        return res == "DELETE 1"

    async def get_cursor_token_full(self, token_id: str):
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM cursor_tokens WHERE id = $1", token_id)
        if not r:
            return None
        return self._row_to_cursor_token(r)

    async def assign_cursor_token(self, token_id: str, user_name: str) -> bool:
        """给 Cursor 凭证标记分配用户（仅记录，不强制）。"""
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE cursor_tokens SET assigned_user = $1, last_used = $2, use_count = use_count + 1 WHERE id = $3",
                user_name, now, token_id,
            )
        return res == "UPDATE 1"

    async def claim_cursor_token(self, user_name: str):
        """用户领取一个可用的 Cursor 凭证。同一凭证可被多人重复领取。"""
        async with self._pool.acquire() as conn:
            # 优先返回已分配给该用户的
            r = await conn.fetchrow(
                "SELECT * FROM cursor_tokens WHERE assigned_user = $1 AND status = 'active'", user_name,
            )
            if not r:
                # 取使用次数最少的活跃凭证（不限是否已分配）
                r = await conn.fetchrow(
                    "SELECT * FROM cursor_tokens WHERE status = 'active' ORDER BY use_count ASC LIMIT 1",
                )
            if not r:
                return None
            await conn.execute(
                "UPDATE cursor_tokens SET assigned_user = $1, last_used = $2, use_count = use_count + 1 WHERE id = $3",
                user_name, datetime.now(timezone.utc), r["id"],
            )
            return self._row_to_cursor_token(r)

    async def pick_cursor_account_for_switch(self, user_name: str, current_email: str = ""):
        """
        智能换号：从自己的账号池里挑一个不同于当前的账号。
        优先级：使用次数最少 → 上次使用时间最早（没用过的排最前）。
        只选有有效凭证（refresh_token 非空 或 access_token 为 JWT 格式）的账号。
        如果只有一个账号，也返回它（刷新凭证用）。
        确保返回的账号有 machine_ids，没有则自动生成并存入 DB。
        """
        cred_filter = "(refresh_token != '' OR access_token LIKE 'eyJ%')"
        order = "ORDER BY use_count ASC, last_used ASC NULLS FIRST LIMIT 1"
        async with self._pool.acquire() as conn:
            # 优先选不同于当前邮箱的
            if current_email:
                r = await conn.fetchrow(
                    f"SELECT * FROM cursor_tokens WHERE status = 'active' AND email != $1 AND {cred_filter} {order}",
                    current_email,
                )
                if r:
                    r = await self._ensure_machine_ids(conn, r)
                    await conn.execute(
                        "UPDATE cursor_tokens SET assigned_user = $1, last_used = $2, use_count = use_count + 1 WHERE id = $3",
                        user_name, datetime.now(timezone.utc), r["id"],
                    )
                    return self._row_to_cursor_token(r)
            # 没有不同的，或者没传 current_email
            r = await conn.fetchrow(
                f"SELECT * FROM cursor_tokens WHERE status = 'active' AND {cred_filter} {order}",
            )
            if not r:
                return None
            r = await self._ensure_machine_ids(conn, r)
            await conn.execute(
                "UPDATE cursor_tokens SET assigned_user = $1, last_used = $2, use_count = use_count + 1 WHERE id = $3",
                user_name, datetime.now(timezone.utc), r["id"],
            )
            return self._row_to_cursor_token(r)

    async def _ensure_machine_ids(self, conn, row):
        """如果账号没有 machine_ids，生成一套并写入 DB，返回更新后的 row。"""
        mid = row.get("machine_ids")
        if isinstance(mid, str):
            try:
                mid = json.loads(mid)
            except Exception:
                mid = {}
        if mid and mid.get("telemetry.machineId"):
            return row
        new_ids = json.dumps(self._generate_machine_ids())
        await conn.execute(
            "UPDATE cursor_tokens SET machine_ids = $1::jsonb WHERE id = $2",
            new_ids, row["id"],
        )
        # 重新查一次拿到完整 row
        return await conn.fetchrow("SELECT * FROM cursor_tokens WHERE id = $1", row["id"])

    async def update_cursor_token_creds(self, token_id: str, access_token: str, refresh_token: str) -> bool:
        """登录成功后更新 cursor_token 的 access_token 和 refresh_token。"""
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                """UPDATE cursor_tokens SET access_token = $1, refresh_token = $2,
                   last_used = $3, last_refreshed_at = $3 WHERE id = $4""",
                access_token, refresh_token, datetime.now(timezone.utc), token_id,
            )
        return res == "UPDATE 1"

    # ── Promax 激活码管理 ──

    async def add_promax_key(self, api_key: str, note: str = "") -> Dict:
        tid = secrets.token_hex(8)
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM promax_keys WHERE api_key = $1", api_key)
            if existing:
                await conn.execute(
                    "UPDATE promax_keys SET note=$1, status='active' WHERE id=$2",
                    note, existing["id"],
                )
                return {"id": existing["id"], "api_key": api_key, "note": note, "updated": True}
            await conn.execute(
                """INSERT INTO promax_keys (id, api_key, note, status, added_at, use_count)
                   VALUES ($1,$2,$3,'active',$4,0)""",
                tid, api_key, note, now,
            )
        return {"id": tid, "api_key": api_key, "note": note, "addedAt": _to_bj(now)}

    async def list_promax_keys(self):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM promax_keys ORDER BY added_at")
        result = []
        for r in rows:
            result.append({
                "id": r["id"], "api_key": r["api_key"], "note": r["note"] or "",
                "status": r["status"], "assigned_user": r["assigned_user"] or "",
                "addedAt": _to_bj(r["added_at"]) or "",
                "useCount": r["use_count"] or 0,
            })
        return result

    async def remove_promax_key(self, key_id: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM promax_keys WHERE id = $1", key_id)
        return res == "DELETE 1"

    async def assign_promax_key(self, key_id: str, user_name: str) -> bool:
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE promax_keys SET assigned_user = $1, last_used = $2 WHERE id = $3",
                user_name, now, key_id,
            )
        return res == "UPDATE 1"

    async def get_promax_key_for_user(self, user_name: str) -> Optional[str]:
        """获取分配给用户的激活码。优先已分配的，否则取使用最少的。"""
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT api_key FROM promax_keys WHERE assigned_user = $1 AND status = 'active'",
                user_name,
            )
            if r:
                return r["api_key"]
            # 自动分配使用最少的
            r = await conn.fetchrow(
                "SELECT id, api_key FROM promax_keys WHERE status = 'active' ORDER BY use_count ASC LIMIT 1",
            )
            if r:
                await conn.execute(
                    "UPDATE promax_keys SET assigned_user = $1, last_used = $2, use_count = use_count + 1 WHERE id = $3",
                    user_name, datetime.now(timezone.utc), r["id"],
                )
                return r["api_key"]
        return None

    # ── 二级代理商 ──

    def _row_to_agent(self, r):
        return {
            "id": r["id"], "name": r["name"], "agent_key": r["agent_key"],
            "status": r["status"],
            "createdAt": _to_bj(r["created_at"]),
            "max_users": r["max_users"],
            "token_pool": r["token_pool"], "token_used": r["token_used"],
            "commission_rate": float(r["commission_rate"]) if r["commission_rate"] else 0,
        }

    async def create_agent(self, name: str, max_users: int = 50) -> Dict:
        aid = f"agent_{secrets.token_hex(4)}"
        agent_key = f"agk-{secrets.token_hex(12)}"
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO agents (id, name, agent_key, status, created_at, max_users, token_pool, token_used, commission_rate)
                   VALUES ($1,$2,$3,'active',$4,$5,0,0,0)""",
                aid, name, agent_key, now, max_users,
            )
        logger.info(f"Agent created: {name} ({aid})")
        return {"id": aid, "name": name, "agent_key": agent_key, "status": "active",
                "createdAt": _to_bj(now), "max_users": max_users,
                "token_pool": 0, "token_used": 0, "commission_rate": 0}

    async def list_agents(self) -> list:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM agents ORDER BY created_at")
        result = []
        for r in rows:
            a = self._row_to_agent(r)
            # 统计名下用户数
            async with self._pool.acquire() as conn:
                cnt = await conn.fetchval("SELECT COUNT(*) FROM users WHERE agent_id = $1", r["id"])
            a["user_count"] = cnt
            result.append(a)
        return result

    async def get_agent_full(self, agent_id: str) -> Optional[Dict]:
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
        if not r:
            return None
        return self._row_to_agent(r)

    async def remove_agent(self, agent_id: str) -> bool:
        async with self._pool.acquire() as conn:
            # 先解绑名下用户
            await conn.execute("UPDATE users SET agent_id = '' WHERE agent_id = $1", agent_id)
            res = await conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
        self._auth_cache.invalidate("all_users")
        return res == "DELETE 1"

    async def verify_agent_key(self, key: str) -> Optional[Dict]:
        """验证代理商密钥，返回代理商信息。"""
        if not key:
            return None
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM agents WHERE agent_key = $1 AND status = 'active'", key)
        if not r:
            return None
        return self._row_to_agent(r)

    async def grant_agent_tokens(self, agent_id: str, amount: int) -> Optional[Dict]:
        """Admin 给代理商充值 token 池。"""
        async with self._pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            if not r:
                return None
            new_pool = max(0, r["token_pool"] + amount)
            await conn.execute("UPDATE agents SET token_pool = $1 WHERE id = $2", new_pool, agent_id)
        logger.info(f"Agent {agent_id} token pool: +{amount}, now={new_pool}")
        return {"agent_id": agent_id, "name": r["name"], "token_pool": new_pool, "token_used": r["token_used"]}

    async def set_agent_quota(self, agent_id: str, updates: Dict) -> bool:
        sets, vals = [], []
        i = 1
        for k in ("max_users", "commission_rate"):
            if k in updates:
                sets.append(f"{k} = ${i}")
                vals.append(updates[k])
                i += 1
        if not sets:
            return False
        vals.append(agent_id)
        async with self._pool.acquire() as conn:
            res = await conn.execute(f"UPDATE agents SET {', '.join(sets)} WHERE id = ${i}", *vals)
            return res == "UPDATE 1"

    async def set_agent_status(self, agent_id: str, status: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("UPDATE agents SET status = $1 WHERE id = $2", status, agent_id)
            return res == "UPDATE 1"

    async def agent_create_user(self, agent_id: str, name: str = "", assigned_token_id: str = "") -> Optional[Dict]:
        """代理商创建用户（自动绑定 agent_id，检查配额）。"""
        async with self._pool.acquire() as conn:
            agent = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            if not agent:
                return None
            cnt = await conn.fetchval("SELECT COUNT(*) FROM users WHERE agent_id = $1", agent_id)
            if cnt >= agent["max_users"]:
                return {"error": f"已达用户上限（{agent['max_users']}）"}

        uid = secrets.token_hex(8)
        uname = name or f"User-{secrets.token_hex(4)}"
        usertoken = f"apollo-{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO users (id, name, usertoken, status, assigned_token_id, agent_id, created_at,
                   request_count, token_balance, token_granted, quota_daily_tokens, quota_monthly_tokens, quota_daily_requests)
                   VALUES ($1,$2,$3,'active',$4,$5,$6,0,0,0,0,0,0)""",
                uid, uname, usertoken, assigned_token_id, agent_id, now,
            )
        logger.info(f"Agent {agent_id} created user: {uname}")
        self._auth_cache.invalidate("all_users")
        return {
            "id": uid, "name": uname, "usertoken": usertoken, "status": "active",
            "agent_id": agent_id, "assigned_token_id": assigned_token_id,
            "createdAt": _to_bj(now), "token_balance": 0, "token_granted": 0,
        }

    async def agent_list_users(self, agent_id: str) -> list:
        """列出代理商名下的用户。"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE agent_id = $1 ORDER BY created_at", agent_id)
            apikeys = await conn.fetch(
                "SELECT user_id, count(*) as cnt FROM user_apikeys WHERE user_id = ANY($1::text[]) GROUP BY user_id",
                [r["id"] for r in rows],
            )
        key_counts = {r["user_id"]: r["cnt"] for r in apikeys}
        result = []
        for r in rows:
            u = self._row_to_user(r)
            u["usertoken"] = u["usertoken"][:12] + "..."
            u["apikeys_count"] = key_counts.get(r["id"], 0)
            result.append(u)
        return result

    async def agent_owns_user(self, agent_id: str, user_id: str) -> bool:
        """检查用户是否属于该代理商。"""
        async with self._pool.acquire() as conn:
            r = await conn.fetchval("SELECT agent_id FROM users WHERE id = $1", user_id)
        return r == agent_id

    async def agent_grant_tokens(self, agent_id: str, user_id: str, amount: int) -> Optional[Dict]:
        """代理商给用户充 token（从自己池子扣）。"""
        async with self._pool.acquire() as conn:
            agent = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            if not agent:
                return None
            available = agent["token_pool"] - agent["token_used"]
            if amount > available:
                return {"error": f"代理商池余额不足（可用: {available}，需要: {amount}）"}
            u = await conn.fetchrow("SELECT * FROM users WHERE id = $1 AND agent_id = $2", user_id, agent_id)
            if not u:
                return {"error": "用户不存在或不属于该代理商"}
            new_balance = max(0, u["token_balance"] + amount)
            new_granted = u["token_granted"] + amount if amount > 0 else u["token_granted"]
            new_used = agent["token_used"] + amount
            await conn.execute("UPDATE users SET token_balance=$1, token_granted=$2 WHERE id=$3", new_balance, new_granted, user_id)
            await conn.execute("UPDATE agents SET token_used=$1 WHERE id=$2", new_used, agent_id)
            # 写流水
            await conn.execute(
                """INSERT INTO token_transactions (user_id, agent_id, type, amount, balance_after, source, note)
                   VALUES ($1, $2, $3, $4, $5, 'agent', $6)""",
                user_id, agent_id, "grant" if amount > 0 else "deduct", amount, new_balance, agent["name"],
            )
        logger.info(f"Agent {agent_id} granted {amount} tokens to user {user_id}")
        self._auth_cache.invalidate("all_users")
        return {"user_id": user_id, "name": u["name"], "token_balance": new_balance,
                "agent_pool_remaining": agent["token_pool"] - new_used}
