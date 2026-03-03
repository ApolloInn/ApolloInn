# -*- coding: utf-8 -*-
"""
Orchids Auth — Clerk 认证管理。

负责：
- 通过 __client Cookie 从 Clerk 获取用户信息（session, email, userId）
- 获取短期 JWT Token
- Token 自动续签
"""

import time
from typing import Optional, Dict

import httpx
from loguru import logger

from config.orchids import (
    ORCHIDS_CLERK_BASE_URL,
    ORCHIDS_CLERK_API_VERSION,
    ORCHIDS_CLERK_JS_VERSION,
    ORCHIDS_USER_AGENT,
    ORCHIDS_DEFAULT_PROJECT_ID,
)

JWT_CACHE_TTL = 50  # Clerk JWT 约 60s 有效，提前 10s 刷新


class OrchidsAuthManager:
    """管理单个 Orchids 账号的 Clerk 认证。"""

    def __init__(
        self,
        client_cookie: str,
        session_id: str = "",
        user_id: str = "",
        email: str = "",
        client_uat: str = "",
    ):
        self.client_cookie = client_cookie
        self.session_id = session_id
        self.user_id = user_id
        self.email = email
        self.client_uat = client_uat or str(int(time.time()))
        self.project_id = ORCHIDS_DEFAULT_PROJECT_ID

        self._jwt: str = ""
        self._jwt_expires_at: float = 0

    def _get_cookies(self) -> str:
        return f"__client={self.client_cookie}; __client_uat={self.client_uat}"

    async def fetch_account_info(self, http_client: httpx.AsyncClient) -> bool:
        """从 Clerk API 获取账号信息（session_id, user_id, email）。"""
        url = (
            f"{ORCHIDS_CLERK_BASE_URL}/v1/client"
            f"?__clerk_api_version={ORCHIDS_CLERK_API_VERSION}"
            f"&_clerk_js_version={ORCHIDS_CLERK_JS_VERSION}"
        )
        try:
            resp = await http_client.get(
                url,
                headers={
                    "User-Agent": ORCHIDS_USER_AGENT,
                    "Accept-Language": "zh-CN",
                    "Cookie": self._get_cookies(),
                },
            )
            if resp.status_code != 200:
                logger.error(f"Orchids [{self.email or 'unknown'}]: Clerk client request failed {resp.status_code}")
                return False

            data = resp.json()
            response = data.get("response", {})
            sessions = response.get("sessions", [])
            if not sessions:
                logger.error(f"Orchids: no active sessions in Clerk response")
                return False

            session = sessions[0]
            self.session_id = response.get("last_active_session_id", session.get("id", ""))
            user = session.get("user", {})
            self.user_id = user.get("id", "")
            emails = user.get("email_addresses", [])
            if emails:
                self.email = emails[0].get("email_address", "")

            logger.info(f"Orchids [{self.email}]: account info fetched, session={self.session_id[:16]}...")
            return True
        except Exception as e:
            logger.error(f"Orchids: fetch_account_info error: {e}")
            return False

    async def get_jwt(self, http_client: httpx.AsyncClient) -> Optional[str]:
        """获取有效的 JWT Token，过期自动刷新。"""
        if self._jwt and time.time() < self._jwt_expires_at:
            return self._jwt

        if not self.session_id:
            ok = await self.fetch_account_info(http_client)
            if not ok:
                return None

        url = (
            f"{ORCHIDS_CLERK_BASE_URL}/v1/client/sessions/{self.session_id}/tokens"
            f"?__clerk_api_version={ORCHIDS_CLERK_API_VERSION}"
            f"&_clerk_js_version={ORCHIDS_CLERK_JS_VERSION}"
        )
        try:
            resp = await http_client.post(
                url,
                content="organization_id=",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": ORCHIDS_USER_AGENT,
                    "Cookie": self._get_cookies(),
                },
            )
            if resp.status_code != 200:
                logger.error(
                    f"Orchids [{self.email}]: JWT request failed {resp.status_code} "
                    f"{resp.text[:200]}"
                )
                return None

            jwt = resp.json().get("jwt", "")
            if not jwt:
                logger.error(f"Orchids [{self.email}]: empty JWT in response")
                return None

            self._jwt = jwt
            self._jwt_expires_at = time.time() + JWT_CACHE_TTL
            return jwt
        except Exception as e:
            logger.error(f"Orchids [{self.email}]: get_jwt error: {e}")
            return None

    def build_headers(self, jwt: str) -> Dict[str, str]:
        """构建 Orchids API 请求头。"""
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
            "X-Orchids-Api-Version": "2",
            "User-Agent": ORCHIDS_USER_AGENT,
        }

    @staticmethod
    async def validate_cookie(client_cookie: str) -> Optional[Dict]:
        """验证 __client cookie 是否有效，返回账号信息。"""
        mgr = OrchidsAuthManager(client_cookie=client_cookie)
        async with httpx.AsyncClient(timeout=15) as client:
            ok = await mgr.fetch_account_info(client)
            if not ok:
                return None
            jwt = await mgr.get_jwt(client)
            if not jwt:
                return None
        return {
            "session_id": mgr.session_id,
            "user_id": mgr.user_id,
            "email": mgr.email,
            "jwt_preview": jwt[:30] + "...",
        }
