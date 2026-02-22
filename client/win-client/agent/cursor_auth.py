"""
Cursor Auth — 用 refreshToken 刷新 Cursor 的 accessToken。

Cursor 使用自己的 OAuth 端点（非 WorkOS）：
POST https://api2.cursor.sh/oauth/token
{
    "client_id": "<cursor_auth_client_id>",
    "grant_type": "refresh_token",
    "refresh_token": "<refresh_token>"
}

从 Cursor 二进制文件中提取的关键信息：
- Production backend: https://api2.cursor.sh
- Production authClientId: KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB
- Staging authClientId: OzaBXLClY5CAGxNzUhQ2vlknpi07tGuE
- 刷新后 Cursor 将 access_token 同时存为 accessToken 和 refreshToken
"""

import httpx
from loguru import logger

# Cursor 的 OAuth client_id（从 Cursor 二进制 workbench.desktop.main.js 提取）
CURSOR_AUTH_CLIENT_ID = "KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB"
CURSOR_BACKEND_URL = "https://api2.cursor.sh"


async def refresh_cursor_token(refresh_token: str) -> dict:
    """
    用 refreshToken 刷新 Cursor 的 accessToken。

    Cursor 的刷新逻辑（从源码提取）：
    - POST /oauth/token with grant_type=refresh_token
    - 成功后返回 { access_token: "..." }
    - Cursor 客户端将 access_token 同时存为 accessToken 和 refreshToken

    返回:
    {
        "ok": True,
        "access_token": "...",
        "refresh_token": "...",  # 与 access_token 相同（Cursor 的行为）
    }
    """
    if not refresh_token:
        return {"ok": False, "error": "refreshToken 为空"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{CURSOR_BACKEND_URL}/oauth/token",
                json={
                    "client_id": CURSOR_AUTH_CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )

            if r.status_code == 200:
                data = r.json()

                # 检查是否要求登出
                if data.get("shouldLogout"):
                    logger.warning("Cursor token refresh: server requested logout")
                    return {"ok": False, "error": "服务器要求重新登录，token 已失效"}

                new_access = data.get("access_token", "")
                # Cursor 的行为：刷新后 access_token 同时作为 refreshToken
                new_refresh = data.get("refresh_token", "") or new_access

                if new_access:
                    logger.info("Cursor token refresh OK")
                    return {
                        "ok": True,
                        "access_token": new_access,
                        "refresh_token": new_refresh,
                    }

            # 失败
            error_msg = f"HTTP {r.status_code}"
            try:
                err = r.json()
                error_msg = err.get("message", "") or err.get("error", "") or error_msg
            except Exception:
                pass

            logger.warning(f"Cursor token refresh failed: {error_msg}")
            return {"ok": False, "error": error_msg}

    except httpx.TimeoutException:
        return {"ok": False, "error": "刷新超时"}
    except Exception as e:
        logger.error(f"Cursor token refresh error: {e}")
        return {"ok": False, "error": str(e)}
