"""
SSE 数据推送 helper — 变更后通知所有相关前端刷新。
"""
from services.event_bus import event_bus


async def push_user_snapshot(pool, user_id: str):
    """拉取用户最新数据并通过 SSE 推送给前端，格式与 /user/me 完全一致。"""
    user = await pool.get_user_full(user_id)
    if not user:
        return
    snapshot = {
        "id": user["id"], "name": user["name"], "status": user["status"],
        "token_balance": user.get("token_balance", 0),
        "token_granted": user.get("token_granted", 0),
        "cursor_email": user.get("cursor_email", ""),
        "cursor_password": user.get("cursor_password", ""),
        "cursor_email_password": user.get("cursor_email_password", ""),
        "claim_remaining": user.get("claim_remaining", 0),
        "apikeys_count": len(user.get("apikeys", [])),
        "createdAt": user.get("createdAt", ""),
        "lastUsed": user.get("lastUsed"),
        "requestCount": user.get("requestCount", 0),
    }
    await event_bus.publish(user_id, "user_snapshot", snapshot)


async def notify_all(pool, user_id: str, source: str):
    """通知所有相关前端刷新：user + admin + agent（如有）。"""
    await push_user_snapshot(pool, user_id)
    await event_bus.publish("admin:global", "data_changed", source)
    user = await pool.get_user_full(user_id)
    if user and user.get("agent_id"):
        await event_bus.publish(f"agent:{user['agent_id']}", "data_changed", source)
