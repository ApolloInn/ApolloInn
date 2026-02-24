#!/usr/bin/env python3
"""
Cursor 自动登录脚本 — 用 Playwright 模拟浏览器登录，提取 accessToken/refreshToken。

用法:
    python cursor_login.py                          # 交互式输入
    python cursor_login.py --email x --password y   # 命令行参数
    python cursor_login.py --batch accounts.txt     # 批量模式

accounts.txt 格式（每行）:
    email----password----备注(可选)

依赖:
    pip install playwright httpx
    playwright install chromium
"""

import argparse
import asyncio
import json
import re
import sys
import time
import uuid
import hashlib
import os
from urllib.parse import urlparse, parse_qs

# ── Cursor OAuth 常量（从 Cursor 二进制提取） ──
CURSOR_CLIENT_ID = "KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB"
CURSOR_AUTH_URL = "https://authenticator.cursor.sh"
CURSOR_API_URL = "https://api2.cursor.sh"

# Apollo 服务器
APOLLO_API = "https://api.apolloinn.site"
ADMIN_KEY = "Ljc17748697418."


async def login_cursor_account(email: str, password: str, headless: bool = True, timeout: int = 60) -> dict:
    """
    用 Playwright 模拟 Cursor 登录流程，提取 token。

    流程：
    1. 打开 Cursor 的 Auth0 登录页
    2. 填入邮箱密码
    3. 拦截登录成功后的回调，提取 token
    """
    from playwright.async_api import async_playwright

    result = {"ok": False, "email": email, "error": ""}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Cursor/0.48.6 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        # 用于捕获 token 的容器
        captured_token = {}

        # 拦截所有请求，寻找 token 回调
        async def on_response(response):
            url = response.url
            # Cursor 登录成功后会调用 /oauth/token 或回调中带 token
            if "/oauth/token" in url or "/callback" in url:
                try:
                    body = await response.json()
                    if body.get("access_token") or body.get("accessToken"):
                        captured_token["access_token"] = body.get("access_token") or body.get("accessToken", "")
                        captured_token["refresh_token"] = body.get("refresh_token") or body.get("refreshToken", "") or captured_token["access_token"]
                        captured_token["auth_id"] = body.get("auth_id") or body.get("authId", "")
                except Exception:
                    pass

            # 也监听 /api/auth/session 等端点
            if "api2.cursor.sh" in url and ("auth" in url or "session" in url):
                try:
                    body = await response.json()
                    if body.get("accessToken"):
                        captured_token["access_token"] = body["accessToken"]
                        captured_token["refresh_token"] = body.get("refreshToken", "") or captured_token.get("access_token", "")
                except Exception:
                    pass

        context.on("response", on_response)
        page = await context.new_page()

        try:
            # 1. 打开登录页
            # Cursor 使用 Auth0 Universal Login，入口是 authenticator.cursor.sh
            print(f"  [{email}] 打开登录页...")
            login_url = f"{CURSOR_AUTH_URL}/login"
            await page.goto(login_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 2. 查找并填写邮箱
            print(f"  [{email}] 填写邮箱...")
            # Auth0 登录页通常有 email input
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[name="username"]',
                'input[id="email"]',
                'input[id="username"]',
                '#identifier-field',
            ]
            email_input = None
            for sel in email_selectors:
                try:
                    email_input = await page.wait_for_selector(sel, timeout=5000)
                    if email_input:
                        break
                except Exception:
                    continue

            if not email_input:
                # 截图调试
                await page.screenshot(path=f"/tmp/cursor_login_debug_{email.split('@')[0]}.png")
                result["error"] = "找不到邮箱输入框，已截图到 /tmp/"
                await browser.close()
                return result

            await email_input.fill(email)
            await asyncio.sleep(0.5)

            # 3. 点击继续/下一步按钮（如果有的话）
            continue_btns = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("继续")',
                'button:has-text("Next")',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
            ]
            for sel in continue_btns:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            # 4. 填写密码
            print(f"  [{email}] 填写密码...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[id="password"]',
            ]
            password_input = None
            for sel in password_selectors:
                try:
                    password_input = await page.wait_for_selector(sel, timeout=8000)
                    if password_input:
                        break
                except Exception:
                    continue

            if not password_input:
                await page.screenshot(path=f"/tmp/cursor_login_debug_{email.split('@')[0]}_pw.png")
                result["error"] = "找不到密码输入框，已截图到 /tmp/"
                await browser.close()
                return result

            await password_input.fill(password)
            await asyncio.sleep(0.5)

            # 5. 点击登录按钮
            print(f"  [{email}] 点击登录...")
            login_btns = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
                'button:has-text("登录")',
            ]
            for sel in login_btns:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        break
                except Exception:
                    continue

            # 6. 等待登录完成（token 被捕获 或 页面跳转）
            print(f"  [{email}] 等待登录完成...")
            deadline = time.time() + timeout
            while time.time() < deadline:
                if captured_token.get("access_token"):
                    break

                # 检查 URL 是否包含 token（有些 OAuth 流程会在 URL fragment 中返回）
                current_url = page.url
                if "access_token=" in current_url or "token=" in current_url:
                    parsed = urlparse(current_url)
                    # 检查 fragment
                    if parsed.fragment:
                        params = parse_qs(parsed.fragment)
                        if "access_token" in params:
                            captured_token["access_token"] = params["access_token"][0]
                            captured_token["refresh_token"] = params.get("refresh_token", [captured_token["access_token"]])[0]
                            break
                    # 检查 query
                    params = parse_qs(parsed.query)
                    if "access_token" in params:
                        captured_token["access_token"] = params["access_token"][0]
                        captured_token["refresh_token"] = params.get("refresh_token", [captured_token["access_token"]])[0]
                        break

                # 检查是否有错误提示
                error_selectors = [
                    '.error-message', '.alert-danger', '[role="alert"]',
                    'span:has-text("Wrong email or password")',
                    'span:has-text("Invalid")',
                ]
                for sel in error_selectors:
                    try:
                        err_el = await page.query_selector(sel)
                        if err_el and await err_el.is_visible():
                            err_text = await err_el.inner_text()
                            if err_text.strip():
                                result["error"] = f"登录失败: {err_text.strip()}"
                                await page.screenshot(path=f"/tmp/cursor_login_error_{email.split('@')[0]}.png")
                                await browser.close()
                                return result
                    except Exception:
                        pass

                # 检查页面是否已经到了 Cursor 的 dashboard 或成功页
                if "cursor.sh/settings" in current_url or "cursor.com/settings" in current_url:
                    # 登录成功但没捕获到 token，尝试从 cookie 获取
                    cookies = await context.cookies()
                    for c in cookies:
                        if "token" in c["name"].lower() or "session" in c["name"].lower():
                            if c["value"].startswith("eyJ"):
                                captured_token["access_token"] = c["value"]
                                captured_token["refresh_token"] = c["value"]
                                break
                    if captured_token.get("access_token"):
                        break

                await asyncio.sleep(1)

            # 7. 如果还没拿到 token，尝试从 localStorage/sessionStorage 获取
            if not captured_token.get("access_token"):
                try:
                    storage_data = await page.evaluate("""() => {
                        const result = {};
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            if (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth') || key.toLowerCase().includes('session')) {
                                result[key] = localStorage.getItem(key);
                            }
                        }
                        for (let i = 0; i < sessionStorage.length; i++) {
                            const key = sessionStorage.key(i);
                            if (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth') || key.toLowerCase().includes('session')) {
                                result['session_' + key] = sessionStorage.getItem(key);
                            }
                        }
                        return result;
                    }""")
                    for k, v in storage_data.items():
                        if v and (v.startswith("eyJ") or len(v) > 100):
                            captured_token["access_token"] = v
                            captured_token["refresh_token"] = v
                            break
                except Exception:
                    pass

            if not captured_token.get("access_token"):
                await page.screenshot(path=f"/tmp/cursor_login_timeout_{email.split('@')[0]}.png")
                result["error"] = f"超时未获取到 token，已截图到 /tmp/"
                await browser.close()
                return result

            # 成功
            result["ok"] = True
            result["access_token"] = captured_token["access_token"]
            result["refresh_token"] = captured_token.get("refresh_token", captured_token["access_token"])
            print(f"  [{email}] ✅ 登录成功，token: {result['access_token'][:20]}...")

        except Exception as e:
            result["error"] = f"异常: {str(e)}"
            try:
                await page.screenshot(path=f"/tmp/cursor_login_exception_{email.split('@')[0]}.png")
            except Exception:
                pass

        await browser.close()

    return result


async def upload_to_server(email: str, access_token: str, refresh_token: str, password: str = "", note: str = ""):
    """将提取的 token 上传到 Apollo 服务器，保留已有的 machine_ids。"""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        # 上传凭证（服务端会自动匹配 email，保留已有 machine_ids）
        payload = {
            "email": email,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "password": password,
            "note": note or f"auto-login {time.strftime('%Y-%m-%d %H:%M')}",
        }
        r = await client.post(
            f"{APOLLO_API}/admin/cursor-tokens",
            json=payload,
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "data": data}
        else:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text}"}


async def batch_login(accounts: list, headless: bool = True, upload: bool = True):
    """批量登录并上传。"""
    results = []
    total = len(accounts)

    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        password = acc["password"]
        note = acc.get("note", "")

        print(f"\n[{i}/{total}] 处理 {email}...")
        login_result = await login_cursor_account(email, password, headless=headless)

        if login_result["ok"] and upload:
            print(f"  [{email}] 上传到服务器...")
            upload_result = await upload_to_server(
                email=email,
                access_token=login_result["access_token"],
                refresh_token=login_result["refresh_token"],
                password=password,
                note=note,
            )
            login_result["uploaded"] = upload_result.get("ok", False)
            if not upload_result.get("ok"):
                login_result["upload_error"] = upload_result.get("error", "")
            else:
                print(f"  [{email}] ✅ 上传成功")
        elif not login_result["ok"]:
            print(f"  [{email}] ❌ {login_result['error']}")

        results.append(login_result)
        # 账号间间隔，避免触发风控
        if i < total:
            print(f"  等待 5 秒...")
            await asyncio.sleep(5)

    # 汇总
    print(f"\n{'='*50}")
    print(f"完成: {sum(1 for r in results if r['ok'])}/{total} 成功")
    for r in results:
        status = "✅" if r["ok"] else "❌"
        extra = ""
        if r["ok"] and r.get("uploaded"):
            extra = " (已上传)"
        elif r["ok"] and not r.get("uploaded"):
            extra = " (未上传)"
        elif not r["ok"]:
            extra = f" ({r['error'][:50]})"
        print(f"  {status} {r['email']}{extra}")

    return results


def parse_accounts_file(filepath: str) -> list:
    """解析账号文件，格式: email----password----备注"""
    accounts = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("----")
            if len(parts) >= 2:
                accounts.append({
                    "email": parts[0].strip(),
                    "password": parts[1].strip(),
                    "note": parts[2].strip() if len(parts) > 2 else "",
                })
    return accounts


def parse_inline_accounts(text: str) -> list:
    """解析内联账号文本。"""
    accounts = []
    # 按行或按邮箱分割
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 支持 email----password----note 格式
        parts = line.split("----")
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0].strip(),
                "password": parts[1].strip(),
                "note": parts[2].strip() if len(parts) > 2 else "",
            })
    return accounts


async def main():
    parser = argparse.ArgumentParser(description="Cursor 自动登录提取 Token")
    parser.add_argument("--email", help="邮箱")
    parser.add_argument("--password", help="密码")
    parser.add_argument("--batch", help="批量账号文件路径")
    parser.add_argument("--accounts", help="内联账号文本（email----password 格式，多个用换行分隔）")
    parser.add_argument("--no-upload", action="store_true", help="不上传到服务器")
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口（调试用）")
    parser.add_argument("--timeout", type=int, default=60, help="登录超时秒数")
    args = parser.parse_args()

    headless = not args.headed
    upload = not args.no_upload

    if args.batch:
        accounts = parse_accounts_file(args.batch)
        if not accounts:
            print("❌ 账号文件为空或格式错误")
            sys.exit(1)
        await batch_login(accounts, headless=headless, upload=upload)

    elif args.accounts:
        accounts = parse_inline_accounts(args.accounts)
        if not accounts:
            print("❌ 账号解析失败")
            sys.exit(1)
        await batch_login(accounts, headless=headless, upload=upload)

    elif args.email and args.password:
        result = await login_cursor_account(args.email, args.password, headless=headless, timeout=args.timeout)
        if result["ok"]:
            print(f"\n✅ 登录成功")
            print(f"  access_token: {result['access_token'][:40]}...")
            print(f"  refresh_token: {result['refresh_token'][:40]}...")
            if upload:
                print(f"\n上传到服务器...")
                up = await upload_to_server(args.email, result["access_token"], result["refresh_token"], args.password)
                if up["ok"]:
                    print(f"✅ 上传成功")
                else:
                    print(f"❌ 上传失败: {up['error']}")
        else:
            print(f"\n❌ 登录失败: {result['error']}")
            sys.exit(1)

    else:
        # 交互式
        email = input("邮箱: ").strip()
        password = input("密码: ").strip()
        if not email or not password:
            print("❌ 邮箱和密码不能为空")
            sys.exit(1)
        result = await login_cursor_account(email, password, headless=headless, timeout=args.timeout)
        if result["ok"]:
            print(f"\n✅ 登录成功")
            print(f"  access_token: {result['access_token'][:40]}...")
            if upload:
                up = await upload_to_server(email, result["access_token"], result["refresh_token"], password)
                print(f"  上传: {'✅' if up['ok'] else '❌ ' + up.get('error', '')}")
        else:
            print(f"\n❌ {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
