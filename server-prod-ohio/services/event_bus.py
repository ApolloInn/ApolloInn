"""
SSE Event Bus — 用 PostgreSQL LISTEN/NOTIFY 跨 worker 广播。

每个 worker 进程启动时调用 event_bus.start(dsn) 建立独立的 PG 监听连接，
收到 NOTIFY 后分发给本进程内的 SSE 订阅者。

用法：
    from services.event_bus import event_bus
    # 启动（lifespan 里调一次）
    await event_bus.start(dsn)
    # 推送（任意 worker 都能触发）
    await event_bus.publish(user_id, "user_updated", "claim")
    # SSE 端点里订阅
    async for event in event_bus.subscribe(user_id):
        yield event
    # 关闭
    await event_bus.stop()
"""

import asyncio
import json
import os
import time
from collections import defaultdict

import asyncpg
from loguru import logger

PG_CHANNEL = "apollo_sse"


class EventBus:
    def __init__(self):
        self._channels: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._listen_conn: asyncpg.Connection | None = None
        self._notify_pool: asyncpg.Pool | None = None
        self._running = False

    # ── lifecycle ──

    async def start(self, dsn: str):
        """启动 PG 监听连接 + 通知连接池。"""
        ssl_param = "prefer" if "sslmode" not in dsn else None
        # 专用监听连接（长连接，不走连接池）
        self._listen_conn = await asyncpg.connect(dsn, ssl=ssl_param)
        await self._listen_conn.add_listener(PG_CHANNEL, self._on_notify)
        # 用于 NOTIFY 的轻量连接池
        self._notify_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3, ssl=ssl_param)
        self._running = True
        logger.info(f"EventBus started, listening on PG channel '{PG_CHANNEL}'")

    async def stop(self):
        self._running = False
        if self._listen_conn:
            await self._listen_conn.remove_listener(PG_CHANNEL, self._on_notify)
            await self._listen_conn.close()
            self._listen_conn = None
        if self._notify_pool:
            await self._notify_pool.close()
            self._notify_pool = None
        logger.info("EventBus stopped")

    # ── PG callback ──

    def _on_notify(self, conn, pid, channel, payload):
        """PG LISTEN 回调 — 在当前 worker 内分发事件。"""
        try:
            msg = json.loads(payload)
            user_id = msg["uid"]
            event = msg["evt"]
            data = msg.get("d", event)
        except Exception:
            logger.warning(f"EventBus: bad payload: {payload}")
            return

        queues = self._channels.get(user_id, set())
        for q in queues:
            try:
                q.put_nowait({"event": event, "data": data})
            except asyncio.QueueFull:
                pass
        if queues:
            logger.debug(f"SSE dispatch [{event}] → user {user_id} ({len(queues)} clients)")

    # ── public API ──

    async def publish(self, user_id: str, event: str, data=None):
        """通过 PG NOTIFY 广播事件到所有 worker。data 可以是 str 或 dict。"""
        if not self._notify_pool:
            logger.warning("EventBus not started, skipping publish")
            return
        # data 为 dict 时序列化为 JSON 字符串
        if isinstance(data, dict):
            d = json.dumps(data, ensure_ascii=False)
        else:
            d = data or event
        payload = json.dumps({"uid": user_id, "evt": event, "d": d})
        safe = payload.replace("'", "''")
        async with self._notify_pool.acquire() as conn:
            await conn.execute(f"NOTIFY {PG_CHANNEL}, '{safe}'")
        logger.debug(f"SSE publish [{event}] → PG NOTIFY for user {user_id}")

    async def subscribe(self, user_id: str, timeout: float = 30.0):
        """Generator that yields SSE events for a user."""
        q: asyncio.Queue = asyncio.Queue()
        self._channels[user_id].add(q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=timeout)
                    yield event
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": str(int(time.time()))}
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            self._channels[user_id].discard(q)
            if not self._channels[user_id]:
                del self._channels[user_id]


event_bus = EventBus()
