"""
User API — 用户端接口。

用 apollo-xxx（usertoken）登录，管理自己的 ap-xxx API key。
"""

from fastapi import APIRouter, Request, HTTPException
from loguru import logger

user_router = APIRouter(tags=["user"])


async def _get_current_user(request: Request):
    """从 Authorization header 提取 apollo-xxx 并验证登录。"""
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else auth
    if not token:
        raise HTTPException(status_code=401, detail="Missing usertoken")
    user = await request.app.state.pool.validate_login(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid usertoken. Use your apollo-xxx token to login.")
    return user


@user_router.get("/me")
async def get_me(request: Request):
    user = await _get_current_user(request)
    return {
        "id": user["id"], "name": user["name"], "status": user["status"],
        "token_balance": user.get("token_balance", 0), "token_granted": user.get("token_granted", 0),
        "cursor_email": user.get("cursor_email", ""),
        "apikeys_count": len(user.get("apikeys", [])),
        "createdAt": user["createdAt"], "lastUsed": user["lastUsed"], "requestCount": user["requestCount"],
    }


@user_router.get("/apikeys")
async def list_apikeys(request: Request):
    user = await _get_current_user(request)
    return {"apikeys": user.get("apikeys", [])}


@user_router.post("/apikeys")
async def create_apikey(request: Request):
    user = await _get_current_user(request)
    key = await request.app.state.pool.create_user_apikey(user["id"])
    if not key:
        raise HTTPException(status_code=500, detail="Failed to create API key")
    return {"apikey": key}


@user_router.delete("/apikeys")
async def revoke_apikey(request: Request):
    user = await _get_current_user(request)
    body = await request.json()
    apikey = body.get("apikey", "")
    if not apikey:
        raise HTTPException(status_code=400, detail="apikey required")
    ok = await request.app.state.pool.revoke_user_apikey(user["id"], apikey)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ok": True}


@user_router.get("/usage")
async def get_my_usage(request: Request):
    user = await _get_current_user(request)
    data = await request.app.state.pool.get_user_usage(user["id"])
    if not data:
        raise HTTPException(status_code=500, detail="Failed to get usage data")
    return data


@user_router.get("/combos")
async def get_combos(request: Request):
    await _get_current_user(request)
    combos = await request.app.state.pool.list_combos()
    return {"combos": combos}


@user_router.get("/cursor-activation")
async def get_cursor_activation(request: Request):
    """获取分配给当前用户的 Cursor 激活码。"""
    user = await _get_current_user(request)
    key = await request.app.state.pool.get_promax_key_for_user(user["name"])
    if not key:
        raise HTTPException(status_code=404, detail="暂无可用激活码，请联系管理员")
    return {"activation_code": key}




@user_router.post("/switch")
async def switch_account(request: Request):
    """
    统一换号接口 — 从 cursor_tokens 账号池取号，返回完整凭证包（token + machine_ids + proxy_config）。

    所有凭证信息由服务端 DB 统一维护，客户端只负责写入本地 Cursor 数据库。
    同账号的所有用户拿到的 token、machine_ids 完全一致。
    """
    user = await _get_current_user(request)
    pool = request.app.state.pool
    current_email = user.get("cursor_email", "")

    # ── 换号次数限制 ──
    MAX_SWITCH = 2
    if user.get("switch_count", 0) >= MAX_SWITCH:
        return {"ok": False, "error": f"换号次数已达上限（{MAX_SWITCH}次），请联系管理员重置"}

    # 从 cursor_tokens 池取号
    picked = await pool.pick_cursor_account_for_switch(user["name"], current_email)
    if not picked:
        return {"ok": False, "error": "账号池为空，请联系管理员添加 Cursor 账号"}

    email = picked["email"]
    access_token = picked.get("access_token", "")
    refresh_token = picked.get("refresh_token", "")
    machine_ids = picked.get("machine_ids", {})

    # 智能刷新：仅当 last_refreshed_at 超过 50 分钟或为空时才刷新
    need_refresh = False
    if refresh_token:
        from datetime import datetime, timezone, timedelta
        last_ref = picked.get("last_refreshed_at")
        if not last_ref:
            need_refresh = True
        else:
            try:
                if isinstance(last_ref, str):
                    from dateutil.parser import parse as dt_parse
                    last_dt = dt_parse(last_ref)
                else:
                    last_dt = last_ref
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - last_dt.astimezone(timezone.utc)
                need_refresh = age > timedelta(minutes=50)
            except Exception:
                need_refresh = True

    if need_refresh and refresh_token:
        from services.cursor_auth import refresh_cursor_token
        result = await refresh_cursor_token(refresh_token)
        if result.get("ok"):
            access_token = result["access_token"]
            new_refresh = result.get("refresh_token", refresh_token)
            await pool.update_cursor_token_creds(picked["id"], access_token, new_refresh)
            refresh_token = new_refresh
            logger.info(f"switch: token refreshed for {email}")
        else:
            logger.warning(f"switch: refresh failed for {email}: {result.get('error')}, using stored token")

    if not access_token and not refresh_token:
        return {"ok": False, "error": f"账号 {email} 无有效凭证，请管理员重新提取"}

    account = {
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "machine_ids": machine_ids,
    }
    await pool.update_cursor_email(user["id"], email)
    await pool.increment_switch_count(user["id"])

    # 返回用户的 API key 和模型映射
    apikeys = user.get("apikeys", [])
    user_apikey = apikeys[0] if apikeys else ""
    combos = await request.app.state.pool.list_combos()
    kiro_models = sorted([n for n in combos if n.startswith("kiro-")])
    cursor_models = ["-".join(w.capitalize() for w in m.split("-")) for m in kiro_models]

    return {
        "ok": True,
        "account": account,
        "proxy_config": {
            "apikey": user_apikey,
            "base_url": "https://api.apolloinn.site/v1",
            "models": cursor_models,
        },
    }


@user_router.post("/switch")
async def switch_cursor(request: Request):
    return await switch_account(request)


