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




@user_router.post("/smart-switch")
async def smart_switch(request: Request):
    """
    服务端最优换号策略：
    - 每次用全新 device_id（避免 promax 缓存分配）
    - 多轮尝试：request-switch → reassign → 换 device 重试
    - 最终 fallback 到 activate 刷新当前 token
    - 换号后 unbind 旧设备保持干净
    """
    import httpx
    import uuid

    user = await _get_current_user(request)
    key = await request.app.state.pool.get_promax_key_for_user(user["name"])
    if not key:
        raise HTTPException(status_code=404, detail="暂无可用激活码")

    promax_api = "http://api.cursorpromax.cn"
    max_rounds = 3  # 最多尝试 3 轮（每轮换新 device_id）

    async with httpx.AsyncClient(timeout=30) as client:

        for round_i in range(max_rounds):
            device_id = uuid.uuid4().hex  # 每轮全新 device_id

            # Step 1: activate（用新 device 注册，拿到 acid 和当前分配）
            try:
                r = await client.post(f"{promax_api}/api/activate", json={
                    "code": key, "device_id": device_id,
                    "device_name": f"apollo-gw-{round_i}", "plugin_version": "2.0.0-apollo",
                })
                if r.status_code != 200:
                    continue
                act_data = r.json().get("data", {})
                acid = act_data.get("activation_code_id")
                current_account = act_data.get("assigned_account", {})
                current_email = current_account.get("email", "")
            except Exception as e:
                logger.warning(f"round {round_i} activate failed: {e}")
                continue

            # Step 2: request-switch (quota_exhausted)
            try:
                r = await client.post(f"{promax_api}/api/billing/request-switch", json={
                    "activation_code": key, "device_id": device_id, "reason": "quota_exhausted",
                })
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("switched") and data.get("new_account"):
                        account = data["new_account"]
                        logger.info(f"smart-switch round {round_i} OK via request-switch: {account.get('email')}")
                        # unbind 清理
                        await _unbind(client, promax_api, acid, device_id)
                        return {"ok": True, "switched": True, "account": account}
            except Exception:
                pass

            # Step 3: request-switch (user_request)
            try:
                r = await client.post(f"{promax_api}/api/billing/request-switch", json={
                    "activation_code": key, "device_id": device_id, "reason": "user_request",
                })
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("switched") and data.get("new_account"):
                        account = data["new_account"]
                        logger.info(f"smart-switch round {round_i} OK via user_request: {account.get('email')}")
                        await _unbind(client, promax_api, acid, device_id)
                        return {"ok": True, "switched": True, "account": account}
            except Exception:
                pass

            # Step 4: reassign
            try:
                r = await client.post(
                    f"{promax_api}/api/billing/request-reassign",
                    params={"activation_code": key, "device_id": device_id},
                    json={},
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("account"):
                        account = data["account"]
                        if account.get("email") != current_email and account.get("access_token"):
                            logger.info(f"smart-switch round {round_i} OK via reassign: {account.get('email')}")
                            await _unbind(client, promax_api, acid, device_id)
                            return {"ok": True, "switched": True, "account": account}
            except Exception:
                pass

            # unbind 本轮 device，为下一轮准备
            await _unbind(client, promax_api, acid, device_id)

        # 所有轮次都没换成功，fallback: activate 拿当前账号最新 token
        fallback_device = uuid.uuid4().hex
        try:
            r = await client.post(f"{promax_api}/api/activate", json={
                "code": key, "device_id": fallback_device,
                "device_name": "apollo-gw-fallback", "plugin_version": "2.0.0-apollo",
            })
            if r.status_code == 200:
                act_data = r.json().get("data", {})
                assigned = act_data.get("assigned_account")
                acid = act_data.get("activation_code_id")
                if assigned and assigned.get("access_token"):
                    logger.info(f"smart-switch fallback: refreshed token for {assigned.get('email')}")
                    await _unbind(client, promax_api, acid, fallback_device)
                    return {
                        "ok": True, "switched": False, "refreshed": True,
                        "account": assigned,
                        "message": "号池暂无其他可用账号，已刷新当前账号凭证",
                    }
        except Exception as e:
            logger.warning(f"activate fallback failed: {e}")

    return {"ok": False, "error": "号池暂无可用账号且无法刷新凭证，请联系管理员或稍后再试"}


async def _unbind(client, promax_api: str, acid, device_id: str):
    """解绑设备，静默失败。"""
    try:
        await client.post(
            f"{promax_api}/api/device/unbind",
            params={"activation_code_id": str(acid), "device_id": device_id},
            json={},
        )
    except Exception:
        pass


