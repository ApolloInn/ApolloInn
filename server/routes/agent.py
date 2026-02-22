"""
Agent API — 二级代理商接口。

用 X-Agent-Key 认证，管理自己名下的用户。
"""

from fastapi import APIRouter, Request, HTTPException
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
    return {"ok": True, "quota": body}
