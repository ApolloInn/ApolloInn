"""
User API — 用户端接口。

用 apollo-xxx（usertoken）登录，管理自己的 ap-xxx API key。
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from services.event_bus import event_bus

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


@user_router.get("/client-config")
async def get_client_config(request: Request):
    """客户端动态配置 — 公告、计费标准、配置指南等，无需登录。"""
    return {
        "announcements": [
            {
                "id": "cursor-version-2025-02",
                "type": "info",
                "title": "关于 Cursor 版本与思考过程显示",
                "sections": [
                    {
                        "title": "问题描述",
                        "style": "neutral",
                        "content": "Cursor 2.5 系列（2月17日起发布）使用 API 模型时，会明文显示思考过程的原始标签，这是 Cursor 2.5 的渲染 bug，**不影响回答质量**，纯粹是显示问题。",
                    },
                    {
                        "title": "✅ 推荐方案：降级到 2.4.37",
                        "style": "success",
                        "content": "2月14日发布的 2.4.37 是 2.4 系列最后一个版本，目前最稳定。等 2.5 修复好渲染问题后再升级回来也来得及。",
                        "link": {"text": "📥 下载 Cursor 2.4.37", "url": "https://cursorhistory.com/versions/2.4.37"},
                    },
                    {
                        "title": "⚡ 不想降级？用 nothink 端点",
                        "style": "warning",
                        "content": "继续用 2.5 系列的话，把 Base URL 改为下方地址。此端点会过滤思考过程，没有渲染问题，但看不到思考过程。其他没有任何差别，自行取舍。",
                        "copyable": "https://api.apolloinn.site/nothink/v1",
                    },
                    {
                        "title": "🌐 关于梯子",
                        "style": "accent",
                        "content": "Cursor 启动时需要开梯子（否则检测到地区限制不让用），进入后可以关掉，看个人习惯。",
                    },
                ],
            },
        ],
        "pricing": {
            "note": "计费标准（每 1M tokens）",
            "formula": "计费Token = 输入Token × 输入权重 + 输出Token × 输出权重",
            "formula_note": "权重 = 模型价格 ÷ $25",
            "tiers": [
                {"name": "旗舰级 (Opus)", "models": "Opus 4.6 / 4.5", "input": 5.00, "output": 25.00},
                {"name": "均衡型 (Sonnet)", "models": "Sonnet 4.6 / 4.5 / 4", "input": 3.00, "output": 15.00},
                {"name": "轻量级 (Haiku)", "models": "Haiku 4.5", "input": 1.00, "output": 5.00},
            ],
        },
        "proxy_guide": {
            "intro": "切换账号后，请按以下步骤配置反向代理以长期稳定使用：",
            "steps": [
                "进入 Cursor 工作区，点击右上角齿轮图标，进入 Cursor Settings",
                "选择 Models 选项卡，展开底部「自定义 API Keys」",
                "打开 OpenAI API Key 和 Override OpenAI Base URL 两个开关",
                "填入你的 API Key（ap-xxx）和接口地址",
            ],
            "base_url": "https://api.apolloinn.site/v1",
            "example_model": "Kiro-Opus-4-6",
            "warning": "请使用反向代理模型（Kiro-开头），不要直接使用 Cursor 自带账号的模型，以免账号透支风控。",
        },
    }


@user_router.get("/me")
async def get_me(request: Request):
    user = await _get_current_user(request)
    return {
        "id": user["id"], "name": user["name"], "status": user["status"],
        "token_balance": user.get("token_balance", 0), "token_granted": user.get("token_granted", 0),
        "cursor_email": user.get("cursor_email", ""),
        "cursor_password": user.get("cursor_password", ""),
        "cursor_email_password": user.get("cursor_email_password", ""),
        "claim_remaining": user.get("claim_remaining", 0),
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





@user_router.post("/claim-cursor-account")
async def claim_cursor_account(request: Request):
    """
    领取 Cursor Pro 账号。

    分发逻辑：
    1. 用户有 agent_id → 从该 agent 的账号池领取
    2. 用户无 agent_id（admin 直接创建的用户）→ 从 admin 全局池领取
    3. 每次领取消耗 claim_remaining 1 次
    """
    user = await _get_current_user(request)
    pool = request.app.state.pool

    # 检查领取次数
    claim_remaining = user.get("claim_remaining", 0)
    if claim_remaining <= 0:
        return {"ok": False, "error": "可领取次数为 0，请联系管理员或代理商充值"}

    agent_id = user.get("agent_id", "")

    # 根据归属选池子
    async with pool._pool.acquire() as conn:
        if agent_id:
            # agent 用户 → 从 agent 池领取
            row = await conn.fetchrow(
                "SELECT * FROM cursor_tokens "
                "WHERE owner_type = 'agent' AND owner_id = $1 "
                "AND status = 'active' AND (assigned_user = '' OR assigned_user IS NULL) "
                "AND (frozen_until IS NULL OR frozen_until < NOW()) "
                "ORDER BY use_count ASC, added_at ASC LIMIT 1",
                agent_id,
            )
        else:
            # admin 用户 → 从 admin 全局池领取
            row = await conn.fetchrow(
                "SELECT * FROM cursor_tokens "
                "WHERE owner_type = 'admin' "
                "AND status = 'active' AND (assigned_user = '' OR assigned_user IS NULL) "
                "AND (frozen_until IS NULL OR frozen_until < NOW()) "
                "ORDER BY use_count ASC, added_at ASC LIMIT 1",
            )

    if not row:
        source = f"代理商 {agent_id}" if agent_id else "管理员"
        return {"ok": False, "error": f"账号池为空，请联系{source}补充账号"}

    email = row["email"]
    password = row.get("password", "")
    email_password = row.get("email_password", "")
    token_id = row["id"]

    # 标记账号已分配 + 扣减领取次数
    async with pool._pool.acquire() as conn:
        await conn.execute(
            "UPDATE cursor_tokens SET assigned_user = $1, use_count = use_count + 1, last_used = NOW() WHERE id = $2",
            user["name"], token_id,
        )
        await conn.execute(
            "UPDATE users SET cursor_email = $1, claim_remaining = GREATEST(0, claim_remaining - 1) WHERE id = $2",
            email, user["id"],
        )

    logger.info(f"claim: {user['name']} claimed {email} from {'agent:'+agent_id if agent_id else 'admin'} pool")

    # SSE 通知
    await event_bus.publish(user["id"], "user_updated", "claim")

    # 写领取日志
    await pool.write_claim_log(
        user["id"], user["name"], email,
        action="claim", source="agent" if agent_id else "admin", agent_id=agent_id,
    )

    return {
        "ok": True,
        "email": email,
        "password": password,
        "email_password": email_password,
        "source": "agent" if agent_id else "admin",
    }


@user_router.get("/events")
async def user_events(request: Request, token: str = ""):
    """SSE 端点 — 实时推送用户数据变更事件。支持 ?token=xxx 认证（EventSource 不支持 header）。"""
    # 优先 query param，fallback header
    tk = token or ""
    if not tk:
        auth = request.headers.get("Authorization", "")
        tk = auth[7:] if auth.startswith("Bearer ") else auth
    if not tk:
        raise HTTPException(status_code=401, detail="Missing token")
    user = await request.app.state.pool.validate_login(tk)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = user["id"]

    async def generate():
        yield "retry: 3000\n\n"
        async for evt in event_bus.subscribe(user_id, timeout=25.0):
            yield f"event: {evt['event']}\ndata: {evt['data']}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@user_router.get("/cursor-claim-logs")
async def user_claim_logs(request: Request):
    """当前用户的领取日志。"""
    user = await _get_current_user(request)
    logs = await request.app.state.pool.list_claim_logs(user_id=user["id"], limit=50)
    return {"logs": logs}


