"""
Admin API — 管理员端调用的接口。

所有接口需要 admin_key 认证（header: X-Admin-Key）。
管理：tokens、users、combos、用户 API keys。
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from loguru import logger
import os

from services.sse_push import notify_all
from services.event_bus import event_bus

admin_router = APIRouter(tags=["admin"])


def verify_admin(request: Request):
    key = request.headers.get("X-Admin-Key", "")
    pool = request.app.state.pool
    if not pool.verify_admin_key(key):
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ── Token 管理 ──

@admin_router.get("/tokens", dependencies=[Depends(verify_admin)])
async def list_tokens(request: Request):
    return {"tokens": await request.app.state.pool.list_tokens()}


@admin_router.post("/tokens", dependencies=[Depends(verify_admin)])
async def add_token(request: Request):
    body = await request.json()
    entry = await request.app.state.pool.add_token(body)
    safe = {**entry}
    for f in ("refreshToken", "accessToken", "clientSecret"):
        if safe.get(f):
            safe[f] = safe[f][:16] + "..."
    return {"token": safe}


@admin_router.delete("/tokens/{token_id}", dependencies=[Depends(verify_admin)])
async def remove_token(request: Request, token_id: str):
    ok = await request.app.state.pool.remove_token(token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    request.app.state.bridge.remove_manager(token_id)
    return {"ok": True}


@admin_router.post("/tokens/{token_id}/test", dependencies=[Depends(verify_admin)])
async def test_token(request: Request, token_id: str):
    """测试凭证是否有效：尝试获取 access token 和模型列表。"""
    import httpx
    from core.auth import AuthType
    from core.utils import get_kiro_headers

    pool = request.app.state.pool
    bridge = request.app.state.bridge

    token_entry = await pool.get_token_full(token_id)
    if not token_entry:
        raise HTTPException(status_code=404, detail="Token not found")

    result = {"valid": False, "auth_type": "", "models_count": 0, "error": ""}
    try:
        mgr = bridge.get_or_create_manager(token_entry)
        access_token = await mgr.get_access_token()
        result["auth_type"] = str(mgr.auth_type.value) if hasattr(mgr.auth_type, "value") else str(mgr.auth_type)
        result["valid"] = True

        # 尝试获取模型列表
        headers = get_kiro_headers(mgr, access_token)
        params = {"origin": "AI_EDITOR"}
        if mgr.auth_type == AuthType.KIRO_DESKTOP and mgr.profile_arn:
            params["profileArn"] = mgr.profile_arn
        url = f"{mgr.q_host}/ListAvailableModels"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                result["models_count"] = len(models)
                result["models"] = [m.get("modelId", "") for m in models]
            else:
                result["error"] = f"ListModels returned {resp.status_code}"
    except Exception as e:
        result["valid"] = False
        result["error"] = str(e)[:200]

    # 测试失败 → 自动标记为 expired
    if not result["valid"]:
        async with pool._pool.acquire() as conn:
            await conn.execute("UPDATE tokens SET status = 'expired' WHERE id = $1", token_id)
        pool._auth_cache.invalidate("all_tokens")
        bridge.remove_manager(token_id)
        result["status_updated"] = "expired"
        logger.info(f"Token {token_id} marked as expired (test failed)")

    return result


@admin_router.get("/tokens/usage/all", dependencies=[Depends(verify_admin)])
async def get_all_token_usage(request: Request):
    """获取所有凭证的用量统计。"""
    return {"usage": await request.app.state.pool.get_all_token_usage()}


@admin_router.get("/tokens/{token_id}/usage", dependencies=[Depends(verify_admin)])
async def get_token_usage(request: Request, token_id: str):
    """获取某个凭证的用量统计。"""
    return await request.app.state.pool.get_token_usage(token_id)


# ── 用户管理 ──

@admin_router.get("/users", dependencies=[Depends(verify_admin)])
async def list_users(request: Request):
    return {"users": await request.app.state.pool.list_users()}


@admin_router.post("/users", dependencies=[Depends(verify_admin)])
async def create_user(request: Request):
    body = await request.json()
    name = body.get("name", "")
    assigned_token_id = body.get("assigned_token_id", "")
    user = await request.app.state.pool.create_user(name, assigned_token_id)
    return {"user": user}


@admin_router.delete("/users/{user_id}", dependencies=[Depends(verify_admin)])
async def remove_user(request: Request, user_id: str):
    ok = await request.app.state.pool.remove_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@admin_router.get("/users/{user_id}/token", dependencies=[Depends(verify_admin)])
async def get_user_token(request: Request, user_id: str):
    user = await request.app.state.pool.get_user_full(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"usertoken": user["usertoken"]}


# ── 用户 API Key 管理 ──

@admin_router.get("/users/{user_id}/apikeys", dependencies=[Depends(verify_admin)])
async def list_user_apikeys(request: Request, user_id: str):
    keys = await request.app.state.pool.list_user_apikeys(user_id)
    return {"apikeys": keys}


@admin_router.post("/users/{user_id}/apikeys", dependencies=[Depends(verify_admin)])
async def create_user_apikey(request: Request, user_id: str):
    key = await request.app.state.pool.create_user_apikey(user_id)
    if not key:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "apikey_create")
    return {"apikey": key}


@admin_router.delete("/users/{user_id}/apikeys", dependencies=[Depends(verify_admin)])
async def revoke_user_apikey(request: Request, user_id: str):
    body = await request.json()
    apikey = body.get("apikey", "")
    ok = await request.app.state.pool.revoke_user_apikey(user_id, apikey)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot revoke (not found)")
    await notify_all(request.app.state.pool, user_id, "apikey_revoke")
    return {"ok": True}


# ── Combo 映射 ──

@admin_router.get("/combos", dependencies=[Depends(verify_admin)])
async def list_combos(request: Request):
    return {"combos": await request.app.state.pool.list_combos()}


@admin_router.post("/combos", dependencies=[Depends(verify_admin)])
async def set_combo(request: Request):
    body = await request.json()
    name = body.get("name", "")
    models = body.get("models", [])
    if not name or not models:
        raise HTTPException(status_code=400, detail="name and models required")
    await request.app.state.pool.set_combo(name, models)
    return {"ok": True, "combo": {name: models}}


@admin_router.delete("/combos/{name}", dependencies=[Depends(verify_admin)])
async def remove_combo(request: Request, name: str):
    ok = await request.app.state.pool.remove_combo(name)
    if not ok:
        raise HTTPException(status_code=404, detail="Custom combo not found (built-in combos cannot be deleted)")
    return {"ok": True}


# ── 状态 ──

@admin_router.get("/status", dependencies=[Depends(verify_admin)])
async def status(request: Request):
    pool = request.app.state.pool
    tokens = await pool.list_tokens()
    users = await pool.list_users()
    combos = await pool.list_combos()
    return {
        "tokens": len(tokens),
        "active_tokens": len([t for t in tokens if t.get("status") == "active"]),
        "users": len(users),
        "active_users": len([u for u in users if u.get("status") == "active"]),
        "combos": len(combos),
    }


@admin_router.put("/users/{user_id}/status", dependencies=[Depends(verify_admin)])
async def set_user_status(request: Request, user_id: str):
    body = await request.json()
    st = body.get("status", "")
    if st not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'suspended'")
    ok = await request.app.state.pool.set_user_status(user_id, st)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "status_change")
    return {"ok": True, "status": st}


@admin_router.put("/users/{user_id}/token", dependencies=[Depends(verify_admin)])
async def assign_token(request: Request, user_id: str):
    """给用户分配/更换转发凭证。body: {"token_id": "xxx"} 或 {"token_id": ""} 取消绑定。"""
    body = await request.json()
    token_id = body.get("token_id", "")
    ok = await request.app.state.pool.assign_token(user_id, token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "assign_token")
    return {"ok": True, "assigned_token_id": token_id}


# ── 用量监控 ──

@admin_router.get("/usage", dependencies=[Depends(verify_admin)])
async def get_global_usage(request: Request):
    return await request.app.state.pool.get_all_usage()


@admin_router.get("/usage/{user_id}", dependencies=[Depends(verify_admin)])
async def get_user_usage(request: Request, user_id: str):
    data = await request.app.state.pool.get_user_usage(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data

@admin_router.get("/usage/{user_id}/recent", dependencies=[Depends(verify_admin)])
async def get_user_recent_usage(request: Request, user_id: str):
    limit = int(request.query_params.get("limit", "20"))
    data = await request.app.state.pool.get_user_recent_records(user_id, limit)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"records": data, "count": len(data)}



@admin_router.put("/users/{user_id}/quota", dependencies=[Depends(verify_admin)])
async def set_user_quota(request: Request, user_id: str):
    body = await request.json()
    ok = await request.app.state.pool.set_user_quota(user_id, body)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "quota_change")
    return {"ok": True, "quota": body}


@admin_router.post("/usage/{user_id}/reset", dependencies=[Depends(verify_admin)])
async def reset_user_usage(request: Request, user_id: str):
    ok = await request.app.state.pool.reset_user_usage(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "usage_reset")
    return {"ok": True}


@admin_router.post("/users/{user_id}/adjust-switch", dependencies=[Depends(verify_admin)])
async def adjust_switch(request: Request, user_id: str):
    """管理员调整用户剩余换号次数。body: {"delta": 3} 加3次，{"delta": -1} 减1次。"""
    body = await request.json()
    delta = body.get("delta", 0)
    if not isinstance(delta, int) or delta == 0:
        raise HTTPException(status_code=400, detail="delta 必须为非零整数")
    remaining = await request.app.state.pool.adjust_switch_remaining(user_id, delta)
    await notify_all(request.app.state.pool, user_id, "adjust_switch")
    return {"ok": True, "switch_remaining": remaining}


@admin_router.post("/users/{user_id}/adjust-claim", dependencies=[Depends(verify_admin)])
async def adjust_claim(request: Request, user_id: str):
    """管理员调整用户的账号领取次数（从 admin 全局池分发）。"""
    body = await request.json()
    delta = body.get("delta", 0)
    if not isinstance(delta, int) or delta == 0:
        raise HTTPException(status_code=400, detail="delta must be non-zero integer")
    pool = request.app.state.pool
    async with pool._pool.acquire() as conn:
        new_val = await conn.fetchval(
            "UPDATE users SET claim_remaining = GREATEST(0, claim_remaining + $1) WHERE id = $2 RETURNING claim_remaining",
            delta, user_id,
        )
    if new_val is None:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "adjust_claim")
    return {"ok": True, "claim_remaining": new_val}


@admin_router.post("/users/{user_id}/grant", dependencies=[Depends(verify_admin)])
async def grant_tokens(request: Request, user_id: str):
    body = await request.json()
    amount = body.get("amount", 0)
    if not amount or not isinstance(amount, (int, float)):
        raise HTTPException(status_code=400, detail="amount required (integer)")
    result = await request.app.state.pool.grant_tokens(user_id, int(amount))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "grant")
    return result


# ── 本机配置提取 & Cursor Pro 凭证管理 ──

def _get_cursor_db_path():
    """跨平台获取 Cursor state.vscdb 路径（多策略扫描）。"""
    from services.cursor_utils import find_cursor_db
    db_path, _ = find_cursor_db()
    return db_path


def _get_kiro_cli_paths():
    """跨平台获取 kiro-cli SQLite 可能路径。"""
    import platform
    from pathlib import Path
    system = platform.system()
    if system == "Windows":
        appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return [
            appdata / "kiro-cli" / "data.sqlite3",
            appdata / "amazon-q" / "data.sqlite3",
        ]
    else:  # macOS / Linux
        return [
            Path.home() / ".local" / "share" / "kiro-cli" / "data.sqlite3",
            Path.home() / ".local" / "share" / "amazon-q" / "data.sqlite3",
        ]


@admin_router.post("/extract/cursor", dependencies=[Depends(verify_admin)])
async def extract_cursor_config(request: Request):
    """提取本机 Cursor 登录凭证并直接存入 Cursor 凭证池。"""
    from services.cursor_utils import find_cursor_db, read_cursor_creds

    creds = read_cursor_creds()
    if not creds:
        _, tried = find_cursor_db()
        raise HTTPException(
            status_code=404,
            detail=f"未找到 Cursor 凭证。可能原因：Cursor 未安装、未登录、或数据库路径非标准。\n"
                   f"可设置环境变量 CURSOR_DB_PATH 手动指定。\n"
                   f"已尝试路径:\n" + "\n".join(f"  · {p}" for p in tried),
        )

    email = creds["email"]
    membership = creds["membership"]

    # 直接存入数据库
    pool = request.app.state.pool
    entry = await pool.add_cursor_token({
        "email": email,
        "accessToken": creds["accessToken"],
        "refreshToken": creds["refreshToken"],
        "note": f"本机提取 · {membership}",
    })

    return {"ok": True, "email": email, "membership": membership, "token_id": entry["id"],
            "dbPath": creds.get("dbPath", "")}


@admin_router.post("/extract/kiro", dependencies=[Depends(verify_admin)])
async def extract_kiro_config(request: Request):
    """提取本机 Kiro 凭证（从 kiro-cli SQLite）并直接存入 Kiro 凭证池。"""
    import sqlite3
    import json as _json

    creds = None
    source = ""
    for cli_path in _get_kiro_cli_paths():
        if not cli_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(cli_path))
            cur = conn.cursor()
            for tk in ["kirocli:social:token", "kirocli:odic:token", "codewhisperer:odic:token"]:
                cur.execute("SELECT value FROM auth_kv WHERE key = ?", (tk,))
                row = cur.fetchone()
                if row:
                    data = _json.loads(row[0])
                    creds = {
                        "refreshToken": data.get("refresh_token", ""),
                        "accessToken": data.get("access_token", ""),
                        "expiresAt": data.get("expires_at", ""),
                        "region": data.get("region", "us-east-1"),
                        "profileArn": data.get("profile_arn", ""),
                    }
                    # clientId / clientSecret
                    for dk in ["kirocli:odic:device-registration", "codewhisperer:odic:device-registration"]:
                        cur.execute("SELECT value FROM auth_kv WHERE key = ?", (dk,))
                        drow = cur.fetchone()
                        if drow:
                            dd = _json.loads(drow[0])
                            creds["clientId"] = dd.get("client_id", "")
                            creds["clientSecret"] = dd.get("client_secret", "")
                            break
                    creds["authMethod"] = "AWS_SSO_OIDC" if creds.get("clientId") else "KIRO_DESKTOP"
                    source = str(cli_path)
                    break
            conn.close()
            if creds:
                break
        except Exception as e:
            logger.warning(f"读取 {cli_path} 失败: {e}")

    if not creds or not creds.get("refreshToken"):
        raise HTTPException(status_code=404, detail="未找到 Kiro 凭证。需要 kiro-cli 已登录（~/.local/share/kiro-cli/data.sqlite3）")

    # 直接存入数据库
    pool = request.app.state.pool
    entry = await pool.add_token(creds)

    return {"ok": True, "region": creds.get("region", ""), "authMethod": creds.get("authMethod", ""),
            "source": source, "token_id": entry["id"]}


# ── Cursor 账号池管理 ──

@admin_router.get("/cursor-accounts", dependencies=[Depends(verify_admin)])
async def list_cursor_accounts(request: Request):
    tokens = await request.app.state.pool.list_cursor_tokens()
    return {"accounts": tokens}


@admin_router.post("/cursor-accounts", dependencies=[Depends(verify_admin)])
async def add_cursor_account(request: Request):
    body = await request.json()
    email = body.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")
    entry = await request.app.state.pool.add_cursor_token({
        "email": email,
        "password": body.get("password", "").strip(),
        "accessToken": body.get("accessToken", "").strip(),
        "refreshToken": body.get("refreshToken", "").strip(),
        "note": body.get("note", "手动录入"),
        "email_password": body.get("email_password", "").strip(),
    })
    return {"ok": True, "account": entry}


@admin_router.delete("/cursor-accounts/{token_id}", dependencies=[Depends(verify_admin)])
async def remove_cursor_account(request: Request, token_id: str):
    ok = await request.app.state.pool.remove_cursor_token(token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"ok": True}


@admin_router.post("/cursor-accounts/{token_id}/test", dependencies=[Depends(verify_admin)])
async def test_cursor_account(request: Request, token_id: str):
    """综合检测 Cursor 账号有效性（不刷新 token）。"""
    import httpx, time, base64, json as _json

    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")

    email = token.get("email", "")
    access_token = token.get("access_token", "")
    refresh_token = token.get("refresh_token", "")
    status = token.get("status", "")
    frozen_until = token.get("frozen_until")

    result = {
        "email": email,
        "valid": False,
        "checks": {},       # 各项检查结果
        "warnings": [],     # 警告列表
        "errors": [],       # 错误列表
    }

    # ── 检查 1：数据库状态 ──
    if status != "active":
        result["checks"]["db_status"] = f"❌ 状态: {status}"
        result["errors"].append(f"账号状态为 {status}")
    else:
        result["checks"]["db_status"] = "✅ active"

    # ── 检查 2：冻结状态 ──
    from datetime import datetime, timezone
    if frozen_until:
        fu = frozen_until if isinstance(frozen_until, datetime) else datetime.fromisoformat(str(frozen_until))
        if fu.tzinfo is None:
            fu = fu.replace(tzinfo=timezone.utc)
        if fu > datetime.now(timezone.utc):
            remaining = fu - datetime.now(timezone.utc)
            hours_left = remaining.total_seconds() / 3600
            result["checks"]["frozen"] = f"❌ 冻结中（剩余 {hours_left:.1f}h）"
            result["warnings"].append(f"冻结中，{hours_left:.1f} 小时后解冻")
        else:
            result["checks"]["frozen"] = "✅ 未冻结"
    else:
        result["checks"]["frozen"] = "✅ 未冻结"

    # ── 检查 3：凭证完整性 ──
    if not access_token:
        result["checks"]["credentials"] = "❌ 无 access_token"
        result["errors"].append("缺少 access_token")
    elif not refresh_token:
        result["checks"]["credentials"] = "⚠️ 有 access_token 但无 refresh_token"
        result["warnings"].append("缺少 refresh_token，过期后无法续期")
    else:
        result["checks"]["credentials"] = "✅ access_token + refresh_token 齐全"

    # ── 检查 4：JWT 过期时间 ──
    token_expired = False
    if access_token:
        try:
            parts = access_token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                data = _json.loads(base64.urlsafe_b64decode(payload))
                exp = data.get("exp", 0)
                remaining_sec = exp - time.time()
                if remaining_sec <= 0:
                    token_expired = True
                    hours_ago = abs(remaining_sec) / 3600
                    result["checks"]["jwt_expiry"] = f"⚠️ 已过期 {hours_ago:.1f}h"
                    result["warnings"].append(f"access_token 已过期 {hours_ago:.1f} 小时")
                else:
                    hours_left = remaining_sec / 3600
                    if hours_left < 1:
                        result["checks"]["jwt_expiry"] = f"⚠️ 即将过期（{remaining_sec/60:.0f}min）"
                        result["warnings"].append("access_token 即将过期")
                    else:
                        result["checks"]["jwt_expiry"] = f"✅ 有效（剩余 {hours_left:.1f}h）"
            else:
                result["checks"]["jwt_expiry"] = "⚠️ 非标准 JWT 格式"
        except Exception:
            result["checks"]["jwt_expiry"] = "⚠️ JWT 解析失败"

    # ── 检查 5：machine_ids 完整性 ──
    machine_ids = token.get("machine_ids", {})
    if isinstance(machine_ids, str):
        try:
            machine_ids = _json.loads(machine_ids)
        except Exception:
            machine_ids = {}
    machine_id = machine_ids.get("telemetry.machineId", "") or machine_ids.get("machineId", "")
    if not machine_id:
        result["checks"]["machine_id"] = "⚠️ 无 machineId（检测设备限制不准确）"
        result["warnings"].append("缺少 machineId")
    else:
        result["checks"]["machine_id"] = f"✅ {machine_id[:12]}..."

    # ── 检查 6：Cursor API 在线检测（仅 access_token 未过期时） ──
    if access_token and not token_expired:
        try:
            ts = int(time.time() * 1000 // 1000000)
            raw = [(ts >> 40) & 0xFF, (ts >> 32) & 0xFF, (ts >> 24) & 0xFF,
                   (ts >> 16) & 0xFF, (ts >> 8) & 0xFF, ts & 0xFF]
            key = 165
            for i in range(6):
                raw[i] = ((raw[i] ^ key) + i) % 256
                key = raw[i]
            checksum = base64.urlsafe_b64encode(bytes(raw)).decode().rstrip("=") + machine_id

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api2.cursor.sh/aiserver.v1.AiService/StreamChat",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "x-cursor-checksum": checksum,
                        "x-cursor-client-version": "0.48.0",
                        "Content-Type": "application/connect+proto",
                        "Connect-Protocol-Version": "1",
                    },
                    content=b"",
                )
                body = resp.text.lower()
                if "too many computers" in body:
                    result["checks"]["api_test"] = "❌ Too many computers（设备超限）"
                    result["errors"].append("设备数超限")
                elif "too many free trial" in body:
                    result["checks"]["api_test"] = "❌ Free trial 已用完"
                    result["errors"].append("免费试用已耗尽")
                elif "unauthorized" in body or resp.status_code == 401:
                    result["checks"]["api_test"] = "❌ 认证失败 (401)"
                    result["errors"].append("access_token 被拒绝")
                elif "forbidden" in body or resp.status_code == 403:
                    result["checks"]["api_test"] = "❌ 账号被封禁 (403)"
                    result["errors"].append("账号可能被封禁")
                elif "rate limit" in body or resp.status_code == 429:
                    result["checks"]["api_test"] = "⚠️ 触发速率限制 (429)"
                    result["warnings"].append("当前触发了速率限制")
                else:
                    result["checks"]["api_test"] = f"✅ API 响应正常 ({resp.status_code})"
        except Exception as e:
            result["checks"]["api_test"] = f"⚠️ 请求失败: {str(e)[:100]}"
            result["warnings"].append("API 检测请求失败")
    elif token_expired:
        result["checks"]["api_test"] = "⏭️ 跳过（access_token 已过期，需先刷新）"
    else:
        result["checks"]["api_test"] = "⏭️ 跳过（无 access_token）"

    # ── 综合判定 ──
    result["valid"] = len(result["errors"]) == 0
    return {"ok": True, **result}


@admin_router.post("/cursor-accounts/{token_id}/freeze", dependencies=[Depends(verify_admin)])
async def freeze_cursor_account_endpoint(request: Request, token_id: str):
    """手动冻结 Cursor 账号。"""
    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")
    body = await request.json()
    hours = body.get("hours", 24)
    reason = body.get("reason", "管理员手动冻结")
    ok = await pool.freeze_cursor_account(token["email"], hours=hours, reason=reason)
    if not ok:
        raise HTTPException(status_code=500, detail="冻结失败")
    return {"ok": True, "email": token["email"], "hours": hours}


@admin_router.post("/cursor-accounts/{token_id}/unfreeze", dependencies=[Depends(verify_admin)])
async def unfreeze_cursor_account_endpoint(request: Request, token_id: str):
    """手动解冻 Cursor 账号。"""
    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")
    async with pool._pool.acquire() as conn:
        await conn.execute("UPDATE cursor_tokens SET frozen_until = NULL WHERE id = $1", token_id)
    logger.info(f"Cursor account {token['email']} manually unfrozen")
    return {"ok": True, "email": token["email"]}


@admin_router.get("/cursor-accounts/stats", dependencies=[Depends(verify_admin)])
async def cursor_accounts_stats(request: Request):
    """Cursor 账号池统计：总数、活跃数、冻结数、当前使用人数、历史总使用次数。"""
    pool = request.app.state.pool
    async with pool._pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM cursor_tokens")
        active = await conn.fetchval("SELECT COUNT(*) FROM cursor_tokens WHERE status = 'active'")
        frozen = await conn.fetchval(
            "SELECT COUNT(*) FROM cursor_tokens WHERE frozen_until IS NOT NULL AND frozen_until > NOW()"
        )
        total_use_count = await conn.fetchval("SELECT COALESCE(SUM(use_count), 0) FROM cursor_tokens")
        # 当前使用人数 = users 表中 cursor_email 非空且 status=active 的去重用户数
        active_users = await conn.fetchval(
            "SELECT COUNT(DISTINCT id) FROM users WHERE cursor_email != '' AND status = 'active'"
        )
    return {
        "total": total, "active": active, "frozen": frozen,
        "total_use_count": total_use_count, "active_users": active_users,
    }


@admin_router.get("/cursor-accounts/{token_id}/detail", dependencies=[Depends(verify_admin)])
async def cursor_account_detail(request: Request, token_id: str):
    """获取 Cursor 账号完整详情（含 machine_ids、完整 token 等）。"""
    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")
    # 查询使用该邮箱的用户列表
    async with pool._pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT id, name, status FROM users WHERE cursor_email = $1", token["email"]
        )
    token["current_users"] = [{"id": r["id"], "name": r["name"], "status": r["status"]} for r in users]
    return {"ok": True, "account": token}


@admin_router.post("/cursor-accounts/batch-delete", dependencies=[Depends(verify_admin)])
async def batch_delete_cursor_accounts(request: Request):
    """批量删除 Cursor 账号。"""
    body = await request.json()
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    pool = request.app.state.pool
    deleted = 0
    for tid in ids:
        if await pool.remove_cursor_token(tid):
            deleted += 1
    return {"ok": True, "deleted": deleted, "total": len(ids)}


@admin_router.post("/cursor-accounts/batch-refresh", dependencies=[Depends(verify_admin)])
async def batch_refresh_cursor_accounts(request: Request):
    """批量刷新 Cursor 账号 Token。"""
    body = await request.json()
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    pool = request.app.state.pool
    from services.cursor_auth import refresh_cursor_token
    results = []
    for tid in ids:
        token = await pool.get_cursor_token_full(tid)
        if not token:
            results.append({"id": tid, "ok": False, "error": "不存在"})
            continue
        rt = token.get("refresh_token", "")
        if not rt:
            results.append({"id": tid, "ok": False, "email": token["email"], "error": "无 refreshToken"})
            continue
        r = await refresh_cursor_token(rt)
        if r.get("ok"):
            new_refresh = r.get("refresh_token", rt)
            await pool.update_cursor_token_creds(tid, r["access_token"], new_refresh)
            results.append({"id": tid, "ok": True, "email": token["email"]})
        else:
            results.append({"id": tid, "ok": False, "email": token["email"], "error": r.get("error", "刷新失败")})
    return {"ok": True, "results": results}


@admin_router.post("/cursor-accounts/{token_id}/refresh", dependencies=[Depends(verify_admin)])
async def refresh_cursor_token_endpoint(request: Request, token_id: str):
    """用 refreshToken 刷新 Cursor 账号的 accessToken。"""
    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")

    refresh_token = token.get("refresh_token", "")
    if not refresh_token:
        return {"ok": False, "error": "该账号无 refreshToken，请重新提取凭证"}

    from services.cursor_auth import refresh_cursor_token
    result = await refresh_cursor_token(refresh_token)
    if result.get("ok"):
        new_refresh = result.get("refresh_token", refresh_token)
        await pool.update_cursor_token_creds(token_id, result["access_token"], new_refresh)
        return {"ok": True, "email": token["email"], "message": "Token 刷新成功"}
    return {"ok": False, "error": result.get("error", "刷新失败")}


# ── Promax 激活码管理 ──

@admin_router.get("/promax-keys", dependencies=[Depends(verify_admin)])
async def list_promax_keys(request: Request):
    return {"keys": await request.app.state.pool.list_promax_keys()}


@admin_router.post("/promax-keys", dependencies=[Depends(verify_admin)])
async def add_promax_key(request: Request):
    body = await request.json()
    api_key = body.get("api_key", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    r = await request.app.state.pool.add_promax_key(api_key, body.get("note", ""))
    return r


@admin_router.delete("/promax-keys/{key_id}", dependencies=[Depends(verify_admin)])
async def remove_promax_key(request: Request, key_id: str):
    ok = await request.app.state.pool.remove_promax_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}


@admin_router.put("/promax-keys/{key_id}/assign", dependencies=[Depends(verify_admin)])
async def assign_promax_key(request: Request, key_id: str):
    body = await request.json()
    user_name = body.get("user_name", "")
    ok = await request.app.state.pool.assign_promax_key(key_id, user_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}


# ── 二级代理商管理 ──

# ── 公开凭证上传（提取器客户端用，无需 admin key） ──

@admin_router.post("/extract/upload")
async def public_upload_creds(request: Request):
    """提取器客户端上传凭证（无需 admin key）。支持 Kiro 和 Cursor。"""
    body = await request.json()
    cred_type = body.pop("type", "kiro")
    note = body.pop("note", "")

    pool = request.app.state.pool

    if cred_type == "cursor":
        email = body.get("email", "")
        if not email:
            raise HTTPException(status_code=400, detail="Cursor 凭证需要 email")
        entry = await pool.add_cursor_token({
            "email": email,
            "accessToken": body.get("accessToken", ""),
            "refreshToken": body.get("refreshToken", ""),
            "machine_ids": body.get("machine_ids", {}),
            "note": note or "提取器上传",
        })
        return {"ok": True, "id": entry["id"], "updated": entry.get("updated", False),
                "type": "cursor", "email": email}
    else:
        entry = await pool.add_token(body, note=note)
        safe = {**entry}
        for f in ("refreshToken", "accessToken", "clientSecret"):
            if safe.get(f):
                safe[f] = safe[f][:16] + "..."
        return {"ok": True, "id": entry["id"], "updated": entry.get("updated", False),
                "type": "kiro", "token": safe}


@admin_router.get("/cursor-claim-logs", dependencies=[Depends(verify_admin)])
async def list_cursor_claim_logs(request: Request):
    """查询 Cursor 账号领取/回收日志。"""
    pool = request.app.state.pool
    user_id = request.query_params.get("user_id", "")
    email = request.query_params.get("email", "")
    agent_id = request.query_params.get("agent_id", "")
    limit = int(request.query_params.get("limit", "200"))
    logs = await pool.list_claim_logs(user_id=user_id, email=email, agent_id=agent_id, limit=limit)
    return {"logs": logs}


@admin_router.post("/cursor-accounts/{token_id}/revoke", dependencies=[Depends(verify_admin)])
async def revoke_cursor_by_token(request: Request, token_id: str):
    """按账号 ID 回收：找到使用该账号的用户并回收。"""
    pool = request.app.state.pool
    token = await pool.get_cursor_token_full(token_id)
    if not token:
        raise HTTPException(status_code=404, detail="账号不存在")
    email = token["email"]
    async with pool._pool.acquire() as conn:
        users = await conn.fetch("SELECT id FROM users WHERE cursor_email = $1", email)
    if not users:
        return {"ok": False, "error": "该账号当前无人使用"}
    results = []
    for u in users:
        result = await pool.revoke_cursor_account(u["id"], operator="admin")
        results.append(result)
    return {"ok": True, "results": results}


@admin_router.post("/users/{user_id}/revoke-cursor", dependencies=[Depends(verify_admin)])
async def revoke_user_cursor(request: Request, user_id: str):
    """回收指定用户的 Cursor 账号。"""
    result = await request.app.state.pool.revoke_cursor_account(user_id, operator="admin")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "回收失败"))
    await notify_all(request.app.state.pool, user_id, "revoke_cursor")
    return result


@admin_router.get("/agents", dependencies=[Depends(verify_admin)])
async def list_agents(request: Request):
    return {"agents": await request.app.state.pool.list_agents()}


@admin_router.post("/agents", dependencies=[Depends(verify_admin)])
async def create_agent(request: Request):
    body = await request.json()
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    max_users = body.get("max_users", 50)
    agent = await request.app.state.pool.create_agent(name, max_users)
    return {"agent": agent}


@admin_router.delete("/agents/{agent_id}", dependencies=[Depends(verify_admin)])
async def remove_agent(request: Request, agent_id: str):
    ok = await request.app.state.pool.remove_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}


@admin_router.post("/agents/{agent_id}/grant", dependencies=[Depends(verify_admin)])
async def grant_agent_tokens(request: Request, agent_id: str):
    body = await request.json()
    amount = body.get("amount", 0)
    if not amount or not isinstance(amount, (int, float)):
        raise HTTPException(status_code=400, detail="amount required (integer)")
    result = await request.app.state.pool.grant_agent_tokens(agent_id, int(amount))
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result


@admin_router.put("/agents/{agent_id}/quota", dependencies=[Depends(verify_admin)])
async def set_agent_quota(request: Request, agent_id: str):
    body = await request.json()
    ok = await request.app.state.pool.set_agent_quota(agent_id, body)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}


@admin_router.put("/agents/{agent_id}/status", dependencies=[Depends(verify_admin)])
async def set_agent_status(request: Request, agent_id: str):
    body = await request.json()
    st = body.get("status", "")
    if st not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'suspended'")
    ok = await request.app.state.pool.set_agent_status(agent_id, st)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True, "status": st}

@admin_router.get("/agents/{agent_id}", dependencies=[Depends(verify_admin)])
async def get_agent_detail(request: Request, agent_id: str):
    agent = await request.app.state.pool.get_agent_full(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    users = await request.app.state.pool.agent_list_users(agent_id)
    return {"agent": agent, "users": users}


# ── SSE 实时事件 ──

@admin_router.get("/events")
async def admin_events(request: Request, key: str = ""):
    """SSE 端点 — 实时推送管理后台数据变更事件。支持 ?key=xxx 认证。"""
    tk = key or request.headers.get("X-Admin-Key", "")
    pool = request.app.state.pool
    if not pool.verify_admin_key(tk):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    channel = "admin:global"

    async def generate():
        yield "retry: 3000\n\n"
        async for evt in event_bus.subscribe(channel, timeout=25.0):
            yield f"event: {evt['event']}\ndata: {evt['data']}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

