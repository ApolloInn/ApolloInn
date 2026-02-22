#!/usr/bin/env python3
"""验证 cursor_accounts_export JSON 中所有账号的有效性 — 通过 api2.cursor.sh"""
import json
import base64
import time
import asyncio
import httpx
from datetime import datetime

ACCOUNTS_FILE = "cursor_accounts_export_2026-02-13_11-54-09.json"

def decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload))
    except:
        return {}

async def check_stripe(client, token):
    """通过 api2.cursor.sh 验证 token"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        r = await client.get(
            "https://api2.cursor.sh/auth/full_stripe_profile",
            headers=headers, timeout=15, follow_redirects=True,
        )
        return r.status_code, r.text[:300]
    except Exception as e:
        return -1, str(e)

async def check_usage_api(client, token):
    """通过 www.cursor.com/api/usage 验证"""
    # 构造 WorkosCursorSessionToken cookie
    payload = decode_jwt_payload(token)
    sub = payload.get("sub", "")
    # sub 格式: auth0|user_XXXX
    user_id = sub.split("|")[-1] if "|" in sub else ""
    
    cookie_val = f"{user_id}::{token}" if user_id else token
    headers = {
        "Cookie": f"WorkosCursorSessionToken={cookie_val}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        r = await client.get(
            "https://www.cursor.com/api/usage",
            headers=headers, timeout=15, follow_redirects=True,
        )
        return r.status_code, r.text[:300]
    except Exception as e:
        return -1, str(e)

async def main():
    with open(ACCOUNTS_FILE, "r") as f:
        accounts = json.load(f)

    now = int(time.time())
    print(f"当前时间: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"共 {len(accounts)} 个账号\n")

    async with httpx.AsyncClient() as client:
        # 先测试第一个账号的多种方式
        acc0 = accounts[0]
        token0 = acc0["auth_info"]["cursorAuth/accessToken"]
        
        print("=== 端点探测（第1个账号）===")
        
        # api2.cursor.sh GET
        code, body = await check_stripe(client, token0)
        print(f"  api2.cursor.sh/auth/full_stripe_profile GET -> {code} {body[:150]}")
        
        # api2.cursor.sh POST
        headers = {"Authorization": f"Bearer {token0}", "Content-Type": "application/json"}
        try:
            r = await client.post("https://api2.cursor.sh/auth/full_stripe_profile", headers=headers, json={}, timeout=15, follow_redirects=True)
            print(f"  api2.cursor.sh/auth/full_stripe_profile POST -> {r.status_code} {r.text[:150]}")
        except Exception as e:
            print(f"  api2.cursor.sh/auth/full_stripe_profile POST -> Error: {e}")

        # www.cursor.com/api/usage with cookie
        code2, body2 = await check_usage_api(client, token0)
        print(f"  www.cursor.com/api/usage (cookie) -> {code2} {body2[:150]}")

        # 试试 refreshToken
        rt = acc0["auth_info"].get("cursorAuth/refreshToken", "")
        headers = {"Authorization": f"Bearer {rt}", "Content-Type": "application/json"}
        try:
            r = await client.get("https://api2.cursor.sh/auth/full_stripe_profile", headers=headers, timeout=15, follow_redirects=True)
            print(f"  api2 with refreshToken -> {r.status_code} {r.text[:150]}")
        except Exception as e:
            print(f"  api2 with refreshToken -> Error: {e}")

        print()

        # 批量验证所有账号
        print(f"{'#':<3} {'邮箱':<40} {'会员':<12} {'额度':<10} {'JWT过期':<14} {'API状态'}")
        print("-" * 110)

        for i, acc in enumerate(accounts):
            email = acc["email"]
            membership = acc.get("membershipType", "?")
            usage = acc.get("modelUsage", {})
            used = usage.get("used", 0)
            total = usage.get("total", 0)
            
            token = acc["auth_info"]["cursorAuth/accessToken"]
            payload = decode_jwt_payload(token)
            exp = payload.get("exp", 0)
            
            if exp > now:
                days_left = (exp - now) // 86400
                jwt_status = f"✅ {days_left}天"
            else:
                jwt_status = "❌ 过期"

            # API 验证
            code, body = await check_stripe(client, token)
            if code == 200:
                api_status = "✅ 有效"
            elif code == 401:
                api_status = "❌ 401无效"
            elif code == 403:
                api_status = "❌ 403禁止"
            else:
                api_status = f"⚠️ {code}"

            print(f"{i+1:<3} {email:<40} {membership:<12} {used}/{total:<7} {jwt_status:<14} {api_status}")

if __name__ == "__main__":
    asyncio.run(main())
