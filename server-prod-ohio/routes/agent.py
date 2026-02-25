"""
Agent API — 二级代理商接口。

用 X-Agent-Key 认证，管理自己名下的用户。
"""
from services.sse_push import notify_all
from services.event_bus import event_bus

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

agent_router = APIRouter(tags=["agent"])


async def _get_current_agent(request: Request):
    """从 X-Agent-Key header 验证代理商身份。"""
    key = request.headers.get("X-Agent-Key", "")
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-Agent-Key")
    agent = await request.app.state.pool.verify_agent_key(key)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent key")
    return agent


async def _verify_ownership(request: Request, agent, user_id: str):
    """验证用户属于该代理商。"""
    owns = await request.app.state.pool.agent_owns_user(agent["id"], user_id)
    if not owns:
        raise HTTPException(status_code=403, detail="该用户不属于你")


@agent_router.get("/me")
async def agent_me(request: Request):
    agent = await _get_current_agent(request)
    pool = request.app.state.pool
    # 统计名下用户数
    users = await pool.agent_list_users(agent["id"])
    available = agent["token_pool"] - agent["token_used"]
    return {
        "id": agent["id"], "name": agent["name"], "status": agent["status"],
        "max_users": agent["max_users"], "user_count": len(users),
        "token_pool": agent["token_pool"], "token_used": agent["token_used"],
        "token_available": available,
    }


# ── 用户管理 ──

@agent_router.get("/users")
async def agent_list_users(request: Request):
    agent = await _get_current_agent(request)
    users = await request.app.state.pool.agent_list_users(agent["id"])
    return {"users": users}


@agent_router.post("/users")
async def agent_create_user(request: Request):
    agent = await _get_current_agent(request)
    body = await request.json()
    name = body.get("name", "")
    assigned_token_id = body.get("assigned_token_id", "")
    result = await request.app.state.pool.agent_create_user(agent["id"], name, assigned_token_id)
    if not result:
        raise HTTPException(status_code=500, detail="创建失败")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"user": result}


@agent_router.delete("/users/{user_id}")
async def agent_remove_user(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    ok = await request.app.state.pool.remove_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@agent_router.put("/users/{user_id}/status")
async def agent_set_user_status(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    body = await request.json()
    st = body.get("status", "")
    if st not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'suspended'")
    ok = await request.app.state.pool.set_user_status(user_id, st)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "status_change")
    return {"ok": True, "status": st}


@agent_router.post("/users/{user_id}/grant")
async def agent_grant_tokens(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    body = await request.json()
    amount = body.get("amount", 0)
    if not amount or not isinstance(amount, (int, float)):
        raise HTTPException(status_code=400, detail="amount required (integer)")
    result = await request.app.state.pool.agent_grant_tokens(agent["id"], user_id, int(amount))
    if not result:
        raise HTTPException(status_code=500, detail="操作失败")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await notify_all(request.app.state.pool, user_id, "grant")
    return result


@agent_router.get("/users/{user_id}/usage")
async def agent_get_user_usage(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    data = await request.app.state.pool.get_user_usage(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


@agent_router.post("/users/{user_id}/reset-switch")
async def agent_reset_switch(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    ok = await request.app.state.pool.reset_switch_count(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "reset_switch")
    return {"ok": True}


@agent_router.get("/users/{user_id}/token")
async def agent_get_user_token(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    user = await request.app.state.pool.get_user_full(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"usertoken": user["usertoken"]}


# ── 用户 API Key 管理 ──

@agent_router.get("/users/{user_id}/apikeys")
async def agent_list_apikeys(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    keys = await request.app.state.pool.list_user_apikeys(user_id)
    return {"apikeys": keys}


@agent_router.post("/users/{user_id}/apikeys")
async def agent_create_apikey(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    key = await request.app.state.pool.create_user_apikey(user_id)
    if not key:
        raise HTTPException(status_code=404, detail="User not found")
    return {"apikey": key}


@agent_router.delete("/users/{user_id}/apikeys")
async def agent_revoke_apikey(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    body = await request.json()
    apikey = body.get("apikey", "")
    ok = await request.app.state.pool.revoke_user_apikey(user_id, apikey)
    if not ok:
        raise HTTPException(status_code=400, detail="API key not found")
    return {"ok": True}


@agent_router.put("/users/{user_id}/quota")
async def agent_set_user_quota(request: Request, user_id: str):
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    body = await request.json()
    ok = await request.app.state.pool.set_user_quota(user_id, body)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_all(request.app.state.pool, user_id, "quota_change")
    return {"ok": True, "quota": body}


# ── Cursor 账号池管理 ──

@agent_router.get("/cursor-accounts")
async def agent_list_cursor_accounts(request: Request):
    """列出该代理商上传的 Cursor 账号。"""
    agent = await _get_current_agent(request)
    pool = request.app.state.pool
    async with pool._pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, email, password, email_password, status, assigned_user, use_count, added_at FROM cursor_tokens "
            "WHERE owner_type = 'agent' AND owner_id = $1 ORDER BY added_at DESC",
            agent["id"],
        )
    accounts = []
    for r in rows:
        accounts.append({
            "id": r["id"], "email": r["email"], "status": r["status"],
            "assigned_user": r["assigned_user"] or "",
            "use_count": r["use_count"], "added_at": str(r["added_at"]), "password": r.get("password", ""), "email_password": r.get("email_password", ""),
        })
    return {"accounts": accounts}


@agent_router.post("/cursor-accounts")
async def agent_add_cursor_account(request: Request):
    """代理商上传 Cursor 账号到自己的池子。"""
    agent = await _get_current_agent(request)
    body = await request.json()
    body["owner_type"] = "agent"
    body["owner_id"] = agent["id"]
    if not body.get("note"):
        body["note"] = f"agent:{agent['name']}上传"
    entry = await request.app.state.pool.add_cursor_token(body)
    return {"ok": True, "account": entry}


@agent_router.delete("/cursor-accounts/{token_id}")
async def agent_remove_cursor_account(request: Request, token_id: str):
    """代理商删除自己池子里的账号。"""
    agent = await _get_current_agent(request)
    pool = request.app.state.pool
    async with pool._pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM cursor_tokens WHERE id = $1 AND owner_type = 'agent' AND owner_id = $2",
            token_id, agent["id"],
        )
    if not row:
        raise HTTPException(status_code=404, detail="账号不存在或不属于你")
    async with pool._pool.acquire() as conn:
        await conn.execute("DELETE FROM cursor_tokens WHERE id = $1", token_id)
    return {"ok": True}


# ── 用户领取次数管理 ──

@agent_router.post("/users/{user_id}/adjust-claim")
async def agent_adjust_claim(request: Request, user_id: str):
    """代理商调整名下用户的账号领取次数。"""
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
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


@agent_router.get("/cursor-claim-logs")
async def agent_list_claim_logs(request: Request):
    """查询该代理商相关的领取/回收日志。"""
    agent = await _get_current_agent(request)
    pool = request.app.state.pool
    user_id = request.query_params.get("user_id", "")
    email = request.query_params.get("email", "")
    limit = int(request.query_params.get("limit", "200"))
    logs = await pool.list_claim_logs(user_id=user_id, email=email, agent_id=agent["id"], limit=limit)
    return {"logs": logs}


@agent_router.post("/users/{user_id}/revoke-cursor")
async def agent_revoke_user_cursor(request: Request, user_id: str):
    """代理商回收名下用户的 Cursor 账号。"""
    agent = await _get_current_agent(request)
    await _verify_ownership(request, agent, user_id)
    result = await request.app.state.pool.revoke_cursor_account(
        user_id, operator=f"agent:{agent['name']}", agent_id=agent["id"]
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "回收失败"))
    await notify_all(request.app.state.pool, user_id, "revoke_cursor")
    return result


# ── SSE 实时事件 ──

@agent_router.get("/events")
async def agent_events(request: Request, key: str = ""):
    """SSE 端点 — 实时推送代理商数据变更事件。支持 ?key=xxx 认证。"""
    tk = key or request.headers.get("X-Agent-Key", "")
    if not tk:
        raise HTTPException(status_code=401, detail="Missing agent key")
    pool = request.app.state.pool
    agent = await pool.verify_agent_key(tk)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent key")
    channel = f"agent:{agent['id']}"

    async def generate():
        yield "retry: 3000\n\n"
        async for evt in event_bus.subscribe(channel, timeout=25.0):
            yield f"event: {evt['event']}\ndata: {evt['data']}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

