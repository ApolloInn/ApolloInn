#!/usr/bin/env python3
"""
Apollo 一键配置 — 完整流程：
1. 重置机器码
2. 清除旧认证
3. 写入有效 token + 假邮箱
4. 配置代理 (API Key + Base URL + 模型)
5. 设置 Pro 会员状态
6. 补丁 Cursor 二进制 (5 patches)
7. 更新 product.json checksum
"""
import sqlite3, json, uuid, hashlib, base64, os, shutil, platform

# ── 路径 ──
HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "Library/Application Support/Cursor/User/globalStorage/state.vscdb")
JS_PATH = "/Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js"
PRODUCT_JSON = "/Applications/Cursor.app/Contents/Resources/app/product.json"
REACTIVE_KEY = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser"

# ── 有效 token (RyanSutton2461 - PRO, expires 2026-04-13) ──
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0RaVkVZTktRWDE3VlBDUTk1UDg3R0daIiwidGltZSI6IjE3NzA4ODY5MTUiLCJyYW5kb21uZXNzIjoiYjk3MTNhNjMtNmZhMS00ZDg3IiwiZXhwIjoxNzc2MDcwOTE1LCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoic2Vzc2lvbiJ9.4dzPmWWAkX2Ya3OgAsJ7AHlGvhxruroolzlLu9n7LbQ"
USER_ID = "auth0|user_01KDZVEYNKQx17VPCQ95P87GGZ"
API_KEY = "ap-6af8fda66031a9dd"
BASE_URL = "https://api.apolloinn.site/v1"
OUR_MODELS = ["kiro-haiku", "kiro-haiku-4-5", "kiro-opus-4-5", "kiro-opus-4-6", "kiro-sonnet-4", "kiro-sonnet-4-5", "kiro-sonnet-4-6"]

# Cursor 已知默认模型（预禁用）
CURSOR_DEFAULTS = [
    "claude-4-sonnet","claude-4-sonnet-1m","claude-4-sonnet-1m-thinking","claude-4-sonnet-thinking",
    "claude-4.5-haiku","claude-4.5-haiku-thinking","claude-4.5-opus-high","claude-4.5-opus-high-thinking",
    "claude-4.5-sonnet","claude-4.5-sonnet-thinking","claude-4.6-opus-high","claude-4.6-opus-high-thinking",
    "claude-4.6-opus-high-thinking-fast","claude-4.6-opus-max","claude-4.6-opus-max-thinking",
    "claude-4.6-opus-max-thinking-fast","composer-1","composer-1.5","default",
    "gemini-2.5-flash","gemini-3-flash","gemini-3-pro",
    "gpt-5-mini","gpt-5.1-codex-max","gpt-5.1-codex-max-high","gpt-5.1-codex-max-high-fast",
    "gpt-5.1-codex-max-low","gpt-5.1-codex-max-low-fast","gpt-5.1-codex-max-medium-fast",
    "gpt-5.1-codex-max-xhigh","gpt-5.1-codex-max-xhigh-fast","gpt-5.1-codex-mini",
    "gpt-5.1-codex-mini-high","gpt-5.1-codex-mini-low","gpt-5.1-high",
    "gpt-5.2","gpt-5.2-codex","gpt-5.2-codex-fast","gpt-5.2-codex-high","gpt-5.2-codex-high-fast",
    "gpt-5.2-codex-low","gpt-5.2-codex-low-fast","gpt-5.2-codex-xhigh","gpt-5.2-codex-xhigh-fast",
    "gpt-5.2-fast","gpt-5.2-high","gpt-5.2-high-fast","gpt-5.2-low","gpt-5.2-low-fast",
    "gpt-5.2-xhigh","gpt-5.2-xhigh-fast",
    "gpt-5.3-codex","gpt-5.3-codex-fast","gpt-5.3-codex-high","gpt-5.3-codex-high-fast",
    "gpt-5.3-codex-low","gpt-5.3-codex-low-fast","gpt-5.3-codex-xhigh","gpt-5.3-codex-xhigh-fast",
    "grok-code-fast-1","kimi-k2-instruct",
]

def main():
    print("=" * 50)
    print("Apollo 一键配置")
    print("=" * 50)

    # ── Step 1: 数据库操作 ──
    if not os.path.exists(DB_PATH):
        print("[ERROR] Cursor 数据库不存在，请先启动一次 Cursor")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 重置机器码
    dev_id = str(uuid.uuid4())
    for k, v in {
        "telemetry.devDeviceId": dev_id,
        "telemetry.macMachineId": hashlib.sha512(os.urandom(64)).hexdigest(),
        "telemetry.machineId": hashlib.sha256(os.urandom(32)).hexdigest(),
        "telemetry.sqmId": "{" + str(uuid.uuid4()).upper() + "}",
        "storage.serviceMachineId": dev_id,
    }.items():
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (k, v))
    print("[OK] 机器码已重置")

    # 2. 清除旧认证
    for k in ["cursorAuth/accessToken","cursorAuth/refreshToken","cursorAuth/workosSessionToken",
               "cursorAuth/userId","cursorAuth/email","cursorAuth/cachedEmail",
               "cursorAuth/stripeMembershipType","cursorAuth/sign_up_type",
               "cursorAuth/cachedSignUpType","cursorAuth/stripeSubscriptionStatus"]:
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (k, ""))
    print("[OK] 旧认证已清除")

    # 3. 写入凭证
    display_email = f"apollo-{uuid.uuid4().hex[:8]}@apolloinn.site"
    workos_token = f"{USER_ID}::{ACCESS_TOKEN}"
    for k, v in [
        ("cursorAuth/accessToken", ACCESS_TOKEN),
        ("cursorAuth/refreshToken", ACCESS_TOKEN),
        ("cursorAuth/workosSessionToken", workos_token),
        ("cursorAuth/email", display_email),
        ("cursorAuth/cachedEmail", display_email),
        ("cursorAuth/userId", USER_ID),
        ("cursorAuth/stripeMembershipType", "pro"),
        ("cursorAuth/stripeSubscriptionStatus", "active"),
        ("cursorAuth/sign_up_type", "Auth_0"),
        ("cursorAuth/cachedSignUpType", "Auth_0"),
        ("cursorAuth/openAIKey", API_KEY),
    ]:
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (k, v))
    print(f"[OK] 凭证已写入: {display_email}")

    # 4. Reactive storage: 会员 + 代理 + 模型
    cur.execute("SELECT value FROM ItemTable WHERE key = ?", (REACTIVE_KEY,))
    row = cur.fetchone()
    reactive = json.loads(row[0]) if row and row[0] else {}

    reactive["membershipType"] = 2
    reactive["useOpenAIKey"] = True
    reactive["openAIBaseUrl"] = BASE_URL

    # 添加 kiro 模型
    existing = reactive.get("availableDefaultModels2", [])
    if not isinstance(existing, list):
        existing = []
    existing_names = {m.get("name") for m in existing if isinstance(m, dict)}
    for mn in OUR_MODELS:
        if mn not in existing_names:
            existing.append({
                "name": mn, "defaultOn": True, "parameterDefinitions": [], "variants": [],
                "supportsAgent": True, "degradationStatus": 0, "supportsThinking": True,
                "supportsImages": True, "supportsMaxMode": True, "clientDisplayName": mn,
                "serverModelName": mn, "supportsNonMaxMode": True,
                "isRecommendedForBackgroundComposer": False, "supportsPlanMode": True,
                "isUserAdded": True, "inputboxShortModelName": mn, "supportsSandboxing": True,
            })
    reactive["availableDefaultModels2"] = existing

    # 模型开关
    ai = reactive.get("aiSettings", {})
    if not isinstance(ai, dict):
        ai = {}
    ai["modelOverrideEnabled"] = OUR_MODELS
    # 禁用所有已知默认模型 + DB 中已有的非 kiro 模型
    all_names = {m.get("name") for m in existing if isinstance(m, dict) and m.get("name")}
    all_names.update(CURSOR_DEFAULTS)
    ai["modelOverrideDisabled"] = sorted(all_names - set(OUR_MODELS))
    ai["userAddedModels"] = OUR_MODELS
    reactive["aiSettings"] = ai

    cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                (REACTIVE_KEY, json.dumps(reactive, ensure_ascii=False)))
    print(f"[OK] 代理配置完成 (enabled={len(OUR_MODELS)}, disabled={len(ai['modelOverrideDisabled'])})")

    conn.commit()
    conn.close()

    # ── Step 2: 补丁 JS ──
    if not os.path.exists(JS_PATH):
        print("[ERROR] Cursor JS 不存在")
        return

    with open(JS_PATH, 'r', errors='ignore') as f:
        content = f.read()
    original_len = len(content)

    # 备份
    backup = JS_PATH + ".apollo_backup"
    if not os.path.exists(backup):
        shutil.copy2(JS_PATH, backup)
        print("[OK] JS 已备份")

    applied = 0

    # Patch 1: BYOK bypass
    p1o = 'e()!==la.FREE&&n.reactiveStorageService.applicationUserPersistentStorage.useOpenAIKey&&'
    p1p = 'true         &&n.reactiveStorageService.applicationUserPersistentStorage.useOpenAIKey&&'
    if p1o in content:
        content = content.replace(p1o, p1p, 1); applied += 1; print("[OK] Patch 1: BYOK bypass")
    elif p1p in content:
        applied += 1
    else:
        print("[SKIP] Patch 1")

    # Patch 2: subscription listener
    p2o = 'this.subscriptionChangedListener=m=>{m!==la.FREE&&this.setUseOpenAIKey('
    p2p = 'this.subscriptionChangedListener=m=>{false      &&this.setUseOpenAIKey('
    if p2o in content:
        content = content.replace(p2o, p2p, 1); applied += 1; print("[OK] Patch 2: Subscription")
    elif p2p in content:
        applied += 1
    else:
        print("[SKIP] Patch 2")

    # Patch 3: login listener
    px = 'this.loginChangedListener=m=>{('
    ps = ')&&this.setUseOpenAIKey('
    a1 = 'this.cursorAuthenticationService.membershipType()===la.PRO'
    a2 = 'this.cursorAuthenticationService.membershipType()===la.PRO_PLUS'
    a3 = 'this.cursorAuthenticationService.membershipType()===la.ULTRA'
    b1 = 'false' + ' '*(len(a1)-5)
    b2 = 'false' + ' '*(len(a2)-5)
    b3 = 'false' + ' '*(len(a3)-5)
    p3o = px + a1 + '||' + a2 + '||' + a3 + ps
    p3p = px + b1 + '||' + b2 + '||' + b3 + ps
    if p3o in content:
        content = content.replace(p3o, p3p, 1); applied += 1; print("[OK] Patch 3: Login listener")
    elif p3p in content:
        applied += 1
    else:
        print("[SKIP] Patch 3")

    # Patch 4 & 5: hollow out refreshMembership and refreshAccessToken
    for name, sig in [
        ("Patch 4: refreshMembership", "this.refreshMembership=async()=>{"),
        ("Patch 5: refreshAccessToken", "this.refreshAccessToken=async(Q=!1)=>{"),
    ]:
        idx = content.find(sig)
        if idx < 0:
            # Check if already hollowed
            check = sig[:-1]
            ci = content.find(check)
            if ci >= 0:
                bi = content.index('{', ci + len(check) - 1)
                if content[bi+1:bi+20].strip() == '':
                    applied += 1; continue
            print(f"[SKIP] {name}")
            continue
        bs = idx + len(sig) - 1
        depth = 0
        be = bs
        for i in range(bs, min(bs + 15000, len(content))):
            if content[i] == '{': depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0: be = i; break
        old = content[bs+1:be]
        if old.strip() == '':
            applied += 1; continue
        content = content[:bs+1] + ' '*len(old) + content[be:]
        applied += 1
        print(f"[OK] {name} ({len(old)} chars hollowed)")

    # 验证长度
    assert len(content) == original_len, f"Length changed! {original_len} -> {len(content)}"

    with open(JS_PATH, 'w') as f:
        f.write(content)
    print(f"[OK] JS 已写入 ({applied}/5 patches)")

    # ── Step 3: 更新 checksum ──
    with open(JS_PATH, 'rb') as f:
        sha = hashlib.sha256(f.read()).digest()
    new_cs = base64.b64encode(sha).decode('ascii').rstrip('=')

    with open(PRODUCT_JSON, 'r') as f:
        product = json.load(f)
    product['checksums']['vs/workbench/workbench.desktop.main.js'] = new_cs
    with open(PRODUCT_JSON, 'w') as f:
        json.dump(product, f, indent='\t')
    print("[OK] Checksum 已更新")

    print("\n" + "=" * 50)
    print("配置完成！启动 Cursor 即可使用")
    print("=" * 50)

if __name__ == "__main__":
    main()
