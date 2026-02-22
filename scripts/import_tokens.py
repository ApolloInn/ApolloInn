#!/usr/bin/env python3
"""将验证通过的 pro 账号导入到服务器 cursor_tokens 表"""
import json
import hashlib

ACCOUNTS_FILE = "cursor_accounts_export_2026-02-13_11-54-09.json"

# API 验证通过的 pro/enterprise 账号（排除 401 失效的和 free 的）
VALID_PRO_EMAILS = {
    "melissafullerhoc@outlook.cl",
    "barbarawilson6358@outlook.in",
    "danielleandersonemwx@outlook.sg",
    "scottwalker4931@outlook.my",
    "mkdeml6rti05kl@no-email.local",
    "mkden35o8smfpb@no-email.local",
    "johnmoore3488qlxs@outlook.fr",
    "kathrynterrellxuf@outlook.at",
    "michaelmoody9683@outlook.ie",
    "jamesbrown8100e2@outlook.my",
    "vumedvej052@outlook.com",
    "sarahvillanueva1625@hotmail.com",
    "marialang4787@outlook.com",
}

# 已存在于数据库的邮箱
EXISTING_EMAILS = {
    "marialang4787@outlook.com",
}

def gen_id(email):
    return hashlib.md5(email.encode()).hexdigest()[:16]

with open(ACCOUNTS_FILE) as f:
    accounts = json.load(f)

sqls = []
for acc in accounts:
    email = acc["email"]
    if email not in VALID_PRO_EMAILS:
        continue
    if email in EXISTING_EMAILS:
        continue
    
    auth = acc["auth_info"]
    access_token = auth.get("cursorAuth/accessToken", "")
    refresh_token = auth.get("cursorAuth/refreshToken", "")
    password = acc.get("password") or ""
    membership = acc.get("membershipType", "pro")
    
    token_id = gen_id(email)
    note = f"imported-{membership}"
    
    # Escape single quotes
    access_token_esc = access_token.replace("'", "''")
    refresh_token_esc = refresh_token.replace("'", "''")
    email_esc = email.replace("'", "''")
    password_esc = password.replace("'", "''")
    
    sql = (
        f"INSERT INTO cursor_tokens (id, email, access_token, refresh_token, password, note, status) "
        f"VALUES ('{token_id}', '{email_esc}', '{access_token_esc}', '{refresh_token_esc}', "
        f"'{password_esc}', '{note}', 'active') "
        f"ON CONFLICT (id) DO NOTHING;"
    )
    sqls.append(sql)

print(f"-- 共 {len(sqls)} 条 INSERT")
for s in sqls:
    print(s)
