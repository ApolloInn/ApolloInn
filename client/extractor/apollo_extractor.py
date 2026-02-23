#!/usr/bin/env python3
"""
Apollo 凭证提取器 (ApolloExtractor)

双击运行，自动扫描本机 Kiro 和 Cursor 凭证，提取后上传到 Apollo Gateway。

Kiro 凭证来源（按优先级）：
  1. ~/.aws/sso/cache/kiro-auth-token.json（AWS SSO cache）
  2. kiro-cli SQLite 数据库（多路径扫描）

Cursor 凭证来源：
  1. Cursor state.vscdb（ItemTable）

支持 macOS / Windows / Linux。
无需额外依赖（仅用 Python 标准库 + tkinter）。
"""

import json
import os
import platform
import sqlite3
import hashlib
import uuid
import subprocess
import time
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

GATEWAY_URL = "https://api.apolloinn.site"
SYSTEM = platform.system()


# ═══════════════════════════════════════════════════════
#  Kiro 凭证提取
# ═══════════════════════════════════════════════════════

def _extract_kiro_from_aws_sso():
    """从 ~/.aws/sso/cache/kiro-auth-token.json 提取 Kiro 凭证。"""
    home = Path.home()
    if SYSTEM == "Windows":
        # Windows: %USERPROFILE%\.aws\sso\cache
        sso_dir = home / ".aws" / "sso" / "cache"
    else:
        sso_dir = home / ".aws" / "sso" / "cache"

    auth_file = sso_dir / "kiro-auth-token.json"
    if not auth_file.exists():
        return None, str(auth_file)

    try:
        with open(auth_file, "r", encoding="utf-8") as f:
            auth = json.load(f)
    except Exception as e:
        return None, f"{auth_file} → 读取失败: {e}"

    refresh_token = auth.get("refreshToken", "")
    if not refresh_token:
        return None, f"{auth_file} → 无 refreshToken"

    client_id_hash = auth.get("clientIdHash", "")
    creds = {
        "refreshToken": refresh_token,
        "accessToken": auth.get("accessToken", ""),
        "expiresAt": auth.get("expiresAt", ""),
        "region": auth.get("region", "us-east-1"),
        "authMethod": auth.get("authMethod", "IdC"),
        "provider": auth.get("provider", "Enterprise"),
        "clientIdHash": client_id_hash,
    }

    # 读取 device registration（clientId / clientSecret）
    if client_id_hash:
        device_file = sso_dir / f"{client_id_hash}.json"
        if device_file.exists():
            try:
                with open(device_file, "r", encoding="utf-8") as f:
                    device = json.load(f)
                creds["clientId"] = device.get("clientId", "")
                creds["clientSecret"] = device.get("clientSecret", "")
            except Exception:
                pass

    if not creds.get("authMethod") or creds["authMethod"] == "IdC":
        creds["authMethod"] = "AWS_SSO_OIDC"

    return creds, str(auth_file)


def _get_kiro_sqlite_paths():
    """跨平台获取 kiro-cli SQLite 可能路径。"""
    home = Path.home()
    paths = []
    if SYSTEM == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        roaming = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        paths = [
            local / "kiro-cli" / "data.sqlite3",
            local / "amazon-q" / "data.sqlite3",
            local / "kiro" / "data.sqlite3",
            roaming / "kiro-cli" / "data.sqlite3",
            roaming / "amazon-q" / "data.sqlite3",
            roaming / "kiro" / "data.sqlite3",
            home / ".local" / "share" / "kiro-cli" / "data.sqlite3",
            home / ".local" / "share" / "amazon-q" / "data.sqlite3",
        ]
    elif SYSTEM == "Darwin":
        paths = [
            home / ".local" / "share" / "kiro-cli" / "data.sqlite3",
            home / ".local" / "share" / "amazon-q" / "data.sqlite3",
            home / "Library" / "Application Support" / "kiro-cli" / "data.sqlite3",
            home / "Library" / "Application Support" / "amazon-q" / "data.sqlite3",
            home / "Library" / "Application Support" / "kiro" / "data.sqlite3",
        ]
    else:
        xdg = os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
        paths = [
            Path(xdg) / "kiro-cli" / "data.sqlite3",
            Path(xdg) / "amazon-q" / "data.sqlite3",
            home / ".local" / "share" / "kiro-cli" / "data.sqlite3",
            home / ".local" / "share" / "amazon-q" / "data.sqlite3",
        ]
    seen, unique = set(), []
    for p in paths:
        s = str(p)
        if s not in seen:
            seen.add(s)
            unique.append(p)
    return unique


def _extract_kiro_from_sqlite():
    """从 kiro-cli SQLite 数据库提取凭证。"""
    tried = []
    for db_path in _get_kiro_sqlite_paths():
        tried.append(str(db_path))
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_kv'")
            if not cur.fetchone():
                tried.append("  → 无 auth_kv 表")
                conn.close()
                continue
            creds = None
            for tk_key in ["kirocli:social:token", "kirocli:odic:token", "codewhisperer:odic:token"]:
                cur.execute("SELECT value FROM auth_kv WHERE key = ?", (tk_key,))
                row = cur.fetchone()
                if row:
                    data = json.loads(row[0])
                    creds = {
                        "refreshToken": data.get("refresh_token", ""),
                        "accessToken": data.get("access_token", ""),
                        "expiresAt": data.get("expires_at", ""),
                        "region": data.get("region", "us-east-1"),
                        "profileArn": data.get("profile_arn", ""),
                    }
                    for dk in ["kirocli:odic:device-registration", "codewhisperer:odic:device-registration"]:
                        cur.execute("SELECT value FROM auth_kv WHERE key = ?", (dk,))
                        drow = cur.fetchone()
                        if drow:
                            dd = json.loads(drow[0])
                            creds["clientId"] = dd.get("client_id", "")
                            creds["clientSecret"] = dd.get("client_secret", "")
                            break
                    creds["authMethod"] = "AWS_SSO_OIDC" if creds.get("clientId") else "KIRO_DESKTOP"
                    if creds.get("clientId"):
                        creds["clientIdHash"] = hashlib.sha256(creds["clientId"].encode()).hexdigest()[:16]
                    break
            conn.close()
            if creds and creds.get("refreshToken"):
                return creds, str(db_path)
        except Exception as e:
            tried.append(f"  → 读取失败: {e}")
    return None, tried


def extract_kiro_creds():
    """提取 Kiro 凭证（优先 AWS SSO cache，其次 SQLite）。返回 (creds, source, scan_log)。"""
    log_lines = []

    # 策略1: AWS SSO cache
    log_lines.append("策略1: AWS SSO cache")
    creds, src = _extract_kiro_from_aws_sso()
    if creds:
        log_lines.append(f"  ✓ {src}")
        return creds, src, log_lines
    log_lines.append(f"  ✗ {src}")

    # 策略2: kiro-cli SQLite
    log_lines.append("策略2: kiro-cli SQLite")
    creds, result = _extract_kiro_from_sqlite()
    if creds:
        log_lines.append(f"  ✓ {result}")
        return creds, result, log_lines
    # result 是 tried 列表
    for line in result:
        log_lines.append(f"  ✗ {line}")

    return None, None, log_lines


# ═══════════════════════════════════════════════════════
#  Cursor 凭证提取
# ═══════════════════════════════════════════════════════

def get_cursor_db_paths():
    """跨平台获取 Cursor state.vscdb 可能路径。"""
    home = Path.home()
    paths = []
    env_db = os.environ.get("CURSOR_DB_PATH")
    if env_db:
        paths.append(Path(env_db))
    if SYSTEM == "Windows":
        roaming = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        paths += [
            roaming / "Cursor" / "User" / "globalStorage" / "state.vscdb",
            local / "Cursor" / "User" / "globalStorage" / "state.vscdb",
            home / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
            home / "AppData" / "Local" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        ]
    elif SYSTEM == "Darwin":
        paths.append(home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        paths += [
            Path(xdg) / "Cursor" / "User" / "globalStorage" / "state.vscdb",
            home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        ]
    seen, unique = set(), []
    for p in paths:
        s = str(p)
        if s not in seen:
            seen.add(s)
            unique.append(p)
    return unique


def extract_cursor_creds():
    """提取 Cursor 凭证（含机器码）。返回 (creds, source, scan_log)。"""
    log_lines = []
    for db_path in get_cursor_db_paths():
        log_lines.append(str(db_path))
        if not db_path.exists():
            log_lines.append("  → 不存在")
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            if not cur.fetchone():
                log_lines.append("  → 无 ItemTable 表")
                conn.close()
                continue
            kv = {}
            for key in [
                "cursorAuth/workosSessionToken", "cursorAuth/email", "cursorAuth/userId",
                "cursorAuth/accessToken", "cursorAuth/refreshToken", "cursorAuth/cachedEmail",
                "cursorAuth/stripeMembershipType", "cursorAuth/stripeSubscriptionStatus",
                "telemetry.devDeviceId", "telemetry.machineId",
                "telemetry.macMachineId", "telemetry.sqmId",
            ]:
                cur.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                row = cur.fetchone()
                short_key = key.split("/")[-1] if "/" in key else key.split(".")[-1]
                kv[short_key] = row[0] if row else ""
            conn.close()

            workos = kv.get("workosSessionToken", "")
            email = kv.get("email", "") or kv.get("cachedEmail", "")
            access = workos or kv.get("accessToken", "")
            refresh = kv.get("refreshToken", "")
            if not access and not refresh:
                log_lines.append("  → 无有效凭证")
                continue

            # 读取 machineid 文件
            cursor_dir = Path(db_path).parent.parent.parent
            file_id = ""
            machine_id_file = cursor_dir / "machineid"
            if machine_id_file.exists():
                try:
                    file_id = machine_id_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass

            machine_ids = {
                "devDeviceId": kv.get("devDeviceId", ""),
                "machineId": kv.get("machineId", ""),
                "macMachineId": kv.get("macMachineId", ""),
                "sqmId": kv.get("sqmId", ""),
                "fileId": file_id,
            }

            log_lines.append("  ✓ 找到凭证")
            return {
                "email": email, "accessToken": access, "refreshToken": refresh,
                "membership": kv.get("stripeMembershipType", ""),
                "authType": "workos" if workos else "legacy",
                "machine_ids": machine_ids,
            }, str(db_path), log_lines
        except Exception as e:
            log_lines.append(f"  → 读取失败: {e}")
    return None, None, log_lines


# ═══════════════════════════════════════════════════════
#  上传
# ═══════════════════════════════════════════════════════

def upload_to_gateway(creds, cred_type="kiro", note=""):
    """上传凭证到 Apollo Gateway（公开接口，无需 admin key）。"""
    payload_data = {**creds, "type": cred_type}
    if note:
        payload_data["note"] = note
    payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{GATEWAY_URL}/admin/extract/upload",
        data=payload, method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ApolloExtractor/2.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            return False, body.get("detail", f"HTTP {e.code}")
        except Exception:
            return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════
#  工具功能：清除缓存 & 更换机器码
# ═══════════════════════════════════════════════════════

def _get_kiro_vscdb_path():
    """获取 Kiro state.vscdb 路径。"""
    home = Path.home()
    if SYSTEM == "Darwin":
        return home / "Library" / "Application Support" / "Kiro" / "User" / "globalStorage" / "state.vscdb"
    elif SYSTEM == "Windows":
        base = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        return Path(base) / "Kiro" / "User" / "globalStorage" / "state.vscdb"
    else:
        return home / ".config" / "Kiro" / "User" / "globalStorage" / "state.vscdb"


def _get_cursor_vscdb_path():
    """获取 Cursor state.vscdb 路径。"""
    home = Path.home()
    if SYSTEM == "Darwin":
        return home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    elif SYSTEM == "Windows":
        base = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        return Path(base) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    else:
        return home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def _is_process_running(proc_keywords):
    """跨平台检测进程是否在运行。"""
    if SYSTEM == "Windows":
        try:
            r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5)
            output = r.stdout.lower()
            return any(kw.lower() in output for kw in proc_keywords)
        except Exception:
            return False
    else:
        for kw in proc_keywords:
            r = subprocess.run(["pgrep", "-f", kw], capture_output=True)
            if r.returncode == 0:
                return True
        return False


def _kill_process(name, proc_keywords):
    """跨平台优雅退出指定进程，返回日志行列表。"""
    lines = []
    if not _is_process_running(proc_keywords):
        lines.append(f"[i] {name} 未在运行")
        return lines

    # 优雅退出
    try:
        if SYSTEM == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'tell application "{name}" to quit'],
                capture_output=True, timeout=5
            )
        elif SYSTEM == "Windows":
            # Windows: 先尝试 WM_CLOSE（优雅），再 taskkill /F（强杀）
            for kw in proc_keywords:
                subprocess.run(["taskkill", "/IM", kw], capture_output=True, timeout=5)
        else:
            for kw in proc_keywords:
                subprocess.run(["pkill", "-f", kw], capture_output=True, timeout=5)
    except Exception:
        pass

    # 等待退出，最多 5 秒
    for _ in range(10):
        time.sleep(0.5)
        if not _is_process_running(proc_keywords):
            lines.append(f"[ok] 已退出 {name}")
            return lines

    # 优雅退出超时，强杀
    try:
        if SYSTEM == "Windows":
            for kw in proc_keywords:
                subprocess.run(["taskkill", "/F", "/IM", kw], capture_output=True, timeout=5)
        else:
            for kw in proc_keywords:
                subprocess.run(["pkill", "-9", "-f", kw], capture_output=True)
    except Exception:
        pass
    time.sleep(1)
    lines.append(f"[ok] 已强制退出 {name}")
    return lines


def _reset_vscdb_machine_id(name, db_path):
    """重置单个 IDE 的 vscdb 机器码，返回日志行列表。"""
    lines = []
    new_id = str(uuid.uuid4())
    new_mac_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    new_sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
    id_keys = [
        ("telemetry.machineId", new_mac_id),
        ("telemetry.macMachineId", new_mac_id),
        ("telemetry.devDeviceId", new_id),
        ("telemetry.sqmId", new_sqm_id),
        ("storage.serviceMachineId", new_id),
    ]
    if not db_path.exists():
        lines.append(f"[i] {name} state.vscdb 不存在")
        return lines
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        changed = 0
        for key, val in id_keys:
            cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, val))
            changed += 1
            lines.append(f"  [ok] {key} → {val[:20]}...")
        conn.commit()
        conn.close()
        lines.append(f"[ok] {name} vscdb 已更新 {changed} 个字段")
    except Exception as e:
        lines.append(f"[x] {name} vscdb 重置失败: {e}")
    return lines


def switch_kiro():
    """Kiro 换号：杀进程 + 清 SSO 缓存 + 清 enterprise + 重置机器码 + 重置 custom-machine-id"""
    lines = []

    # 1. 杀 Kiro 进程
    if SYSTEM == "Windows":
        lines.extend(_kill_process("Kiro", ["Kiro.exe"]))
    else:
        lines.extend(_kill_process("Kiro", ["Kiro.app", "kiro"]))

    # 2. 清 SSO 缓存
    sso_dir = Path.home() / ".aws" / "sso" / "cache"
    if sso_dir.exists():
        count = 0
        for f in sso_dir.iterdir():
            if f.is_file() and f.suffix == ".json":
                try:
                    f.unlink()
                    count += 1
                except Exception:
                    pass
        lines.append(f"[ok] 删除 SSO 缓存 {count} 个" if count else "[i] SSO 缓存为空")
    else:
        lines.append("[i] SSO 缓存目录不存在")

    # 3. 清 enterprise 配置
    vscdb = _get_kiro_vscdb_path()
    if vscdb.exists():
        try:
            conn = sqlite3.connect(str(vscdb))
            cur = conn.cursor()
            cur.execute("DELETE FROM ItemTable WHERE key LIKE 'kiro.enterprise.%'")
            n = cur.rowcount
            conn.commit()
            conn.close()
            lines.append(f"[ok] 清除 enterprise 配置 {n} 项" if n else "[i] 无 enterprise 配置")
        except Exception as e:
            lines.append(f"[x] 清 enterprise 失败: {e}")

    # 4. 重置 vscdb 机器码
    lines.extend(_reset_vscdb_machine_id("Kiro", vscdb))

    # 5. 重置 custom-machine-id 文件
    kiro_dir = Path.home() / ".kiro"
    for fname in ("custom-machine-id", "custom-machine-id-raw"):
        fpath = kiro_dir / fname
        try:
            new_val = str(uuid.uuid4()) if fname == "custom-machine-id-raw" else hashlib.sha256(uuid.uuid4().bytes).hexdigest()
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(new_val)
            lines.append(f"[ok] {fname} → {new_val[:20]}...")
        except Exception as e:
            lines.append(f"[x] 重置 {fname} 失败: {e}")

    lines.append("")
    lines.append("请重新打开 Kiro，用新账号登录后再扫描上传。")
    return lines


def switch_cursor():
    """Cursor 换号：杀进程 + 清全部登录态 + 重置机器码 + 清缓存 + 清 Keychain"""
    lines = []

    # 1. 杀 Cursor 进程（跨平台）
    if SYSTEM == "Windows":
        lines.extend(_kill_process("Cursor", ["Cursor.exe"]))
    else:
        lines.extend(_kill_process("Cursor", ["Cursor.app", "cursor"]))

    # 2. 找 Cursor 数据库（优先用 get_cursor_db_paths 多路径扫描）
    cursor_db = None
    for p in get_cursor_db_paths():
        if p.exists():
            cursor_db = p
            break
    if not cursor_db:
        cursor_db = _get_cursor_vscdb_path()

    if not cursor_db.exists():
        lines.append("[x] Cursor state.vscdb 不存在，无法换号")
        return lines

    # 3. 清除全部登录态（与 agent 保持一致）
    auth_keys = [
        "cursorAuth/accessToken",
        "cursorAuth/refreshToken",
        "cursorAuth/workosSessionToken",
        "cursorAuth/userId",
        "cursorAuth/email",
        "cursorAuth/cachedEmail",
        "cursorAuth/stripeMembershipType",
        "cursorAuth/stripeSubscriptionStatus",
        "cursorAuth/sign_up_type",
        "cursorAuth/cachedSignUpType",
        "cursorAuth/onboardingDate",
        "cursorAuth/openAIKey",
    ]
    try:
        conn = sqlite3.connect(str(cursor_db))
        cur = conn.cursor()
        cleared = 0
        for key in auth_keys:
            cur.execute("DELETE FROM ItemTable WHERE key = ?", (key,))
            cleared += cur.rowcount
        conn.commit()
        conn.close()
        lines.append(f"[ok] 清除 Cursor 登录态 {cleared} 项")
    except Exception as e:
        lines.append(f"[x] 清 Cursor 登录态失败: {e}")

    # 4. 生成统一的一组新机器码（vscdb + storage.json + machineid 共用）
    new_dev_id = str(uuid.uuid4())
    new_machine_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    new_sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
    new_file_id = str(uuid.uuid4())
    id_map = {
        "telemetry.machineId": new_machine_id,
        "telemetry.macMachineId": new_machine_id,
        "telemetry.devDeviceId": new_dev_id,
        "telemetry.sqmId": new_sqm_id,
        "storage.serviceMachineId": new_dev_id,
    }

    # 4a. 重置 vscdb 机器码
    try:
        conn = sqlite3.connect(str(cursor_db))
        cur = conn.cursor()
        for key, val in id_map.items():
            cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, val))
            lines.append(f"  [ok] {key} → {val[:20]}...")
        conn.commit()
        conn.close()
        lines.append(f"[ok] Cursor vscdb 已更新 {len(id_map)} 个字段")
    except Exception as e:
        lines.append(f"[x] Cursor vscdb 重置失败: {e}")

    # 4b. 重置 storage.json（使用同一组值）
    global_storage = cursor_db.parent
    storage_json = global_storage / "storage.json"
    if storage_json.exists():
        try:
            data = json.loads(storage_json.read_text(encoding="utf-8"))
            for key, val in id_map.items():
                data[key] = val
            storage_json.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
            lines.append("[ok] 已重置 storage.json 机器码（与 vscdb 一致）")
        except Exception as e:
            lines.append(f"[x] 重置 storage.json 失败: {e}")

    # 4c. 重置 machineid 文件
    cursor_dir = cursor_db.parent.parent.parent  # …/Cursor/User/globalStorage → …/Cursor
    machine_id_file = cursor_dir / "machineid"
    try:
        machine_id_file.parent.mkdir(parents=True, exist_ok=True)
        machine_id_file.write_text(new_file_id, encoding="utf-8")
        lines.append(f"[ok] 已重置 machineid 文件")
    except Exception as e:
        lines.append(f"[x] 重置 machineid 文件失败: {e}")

    # 5. 清理缓存目录
    home = Path.home()
    cache_dirs = []
    if SYSTEM == "Darwin":
        cache_dirs = [
            home / "Library" / "Caches" / "Cursor",
            home / "Library" / "Application Support" / "Cursor" / "Cache",
            home / "Library" / "Application Support" / "Cursor" / "CachedData",
        ]
    elif SYSTEM == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        roaming = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        cache_dirs = [
            local / "Cursor" / "Cache",
            local / "Cursor" / "CachedData",
            roaming / "Cursor" / "Cache",
            roaming / "Cursor" / "CachedData",
        ]
    else:
        xdg_cache = Path(os.environ.get("XDG_CACHE_HOME", str(home / ".cache")))
        xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
        cache_dirs = [
            xdg_cache / "Cursor",
            xdg_config / "Cursor" / "Cache",
            xdg_config / "Cursor" / "CachedData",
        ]
    import shutil as _shutil
    cache_cleaned = 0
    for d in cache_dirs:
        if d.exists():
            try:
                _shutil.rmtree(d)
                cache_cleaned += 1
            except Exception:
                pass
    if cache_cleaned:
        lines.append(f"[ok] 清理缓存目录 {cache_cleaned} 个")

    # 6. macOS: 清理 Keychain 中的 Cursor 条目
    if SYSTEM == "Darwin":
        for service in ["Cursor Safe Storage", "Cursor"]:
            try:
                subprocess.run(
                    ["security", "delete-generic-password", "-s", service],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
        lines.append("[ok] 已清理 macOS Keychain")

    lines.append("")
    lines.append("请重新打开 Cursor，用新账号登录后再扫描上传。")
    return lines


# ═══════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════

class ExtractorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Apollo 凭证提取器")
        self.root.geometry("580x600")
        self.root.resizable(False, False)
        self.root.update_idletasks()
        w, h = 580, 600
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.kiro_creds = None
        self.cursor_creds = None
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Apollo 凭证提取器", font=("", 16, "bold")).pack(pady=(0, 4))
        ttk.Label(frame, text="自动扫描本机 Kiro / Cursor 凭证，提取并上传",
                  foreground="gray").pack(pady=(0, 16))

        # 备注
        note_frame = ttk.Frame(frame)
        note_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(note_frame, text="备注:").pack(side="left")
        self.note_var = tk.StringVar()
        ttk.Entry(note_frame, textvariable=self.note_var, width=46).pack(side="left", padx=(8, 0), fill="x", expand=True)

        # 扫描 & 上传按钮（居中）
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 8))
        ttk.Button(btn_frame, text="扫描本机", command=self.do_scan).pack(side="left", padx=4)
        self.upload_kiro_btn = ttk.Button(btn_frame, text="上传 Kiro", command=self.do_upload_kiro, state="disabled")
        self.upload_kiro_btn.pack(side="left", padx=4)
        self.upload_cursor_btn = ttk.Button(btn_frame, text="上传 Cursor", command=self.do_upload_cursor, state="disabled")
        self.upload_cursor_btn.pack(side="left", padx=4)
        self.upload_all_btn = ttk.Button(btn_frame, text="全部上传", command=self.do_upload_all, state="disabled")
        self.upload_all_btn.pack(side="left", padx=4)

        # 工具按钮（居中）
        tool_frame = ttk.Frame(frame)
        tool_frame.pack(pady=(0, 12))
        ttk.Button(tool_frame, text="Kiro 换号", command=self.do_switch_kiro).pack(side="left", padx=4)
        ttk.Button(tool_frame, text="Cursor 换号", command=self.do_switch_cursor).pack(side="left", padx=4)

        # 日志
        self.log = scrolledtext.ScrolledText(frame, height=20, font=("Courier", 11), state="disabled")
        self.log.pack(fill="both", expand=True)

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def do_scan(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.kiro_creds = None
        self.cursor_creds = None
        self.upload_kiro_btn.config(state="disabled")
        self.upload_cursor_btn.config(state="disabled")
        self.upload_all_btn.config(state="disabled")

        self._log(f"系统: {SYSTEM}")
        self._log("")

        # ── Kiro ──
        self._log("━━━ Kiro 扫描 ━━━")
        kiro_creds, kiro_src, kiro_log = extract_kiro_creds()
        for line in kiro_log:
            self._log(f"  {line}")
        if kiro_creds:
            self.kiro_creds = kiro_creds
            self._log(f"✓ Kiro 凭证找到!")
            self._log(f"  来源: {kiro_src}")
            self._log(f"  区域: {kiro_creds.get('region', '?')}")
            self._log(f"  认证: {kiro_creds.get('authMethod', '?')}")
            rt = kiro_creds.get("refreshToken", "")
            self._log(f"  refreshToken: {rt[:20]}..." if len(rt) > 20 else f"  refreshToken: {rt}")
            self.upload_kiro_btn.config(state="normal")
        else:
            self._log("✗ 未找到 Kiro 凭证")
        self._log("")

        # ── Cursor ──
        self._log("━━━ Cursor 扫描 ━━━")
        cursor_creds, cursor_src, cursor_log = extract_cursor_creds()
        for line in cursor_log:
            self._log(f"  {line}")
        if cursor_creds:
            self.cursor_creds = cursor_creds
            self._log(f"✓ Cursor 凭证找到!")
            self._log(f"  来源: {cursor_src}")
            self._log(f"  邮箱: {cursor_creds.get('email', '?')}")
            self._log(f"  会员: {cursor_creds.get('membership', '?')}")
            self._log(f"  认证: {cursor_creds.get('authType', '?')}")
            self.upload_cursor_btn.config(state="normal")
        else:
            self._log("✗ 未找到 Cursor 凭证")

        if self.kiro_creds or self.cursor_creds:
            self.upload_all_btn.config(state="normal")
        self._log("")
        found = []
        if self.kiro_creds:
            found.append("Kiro")
        if self.cursor_creds:
            found.append("Cursor")
        if found:
            self._log(f"可上传: {', '.join(found)}。点击对应按钮上传。")
        else:
            self._log("未找到任何可用凭证。请确保已安装并登录过 Kiro 或 Cursor。")

    def _do_upload(self, creds, cred_type, label):
        note = self.note_var.get().strip()
        self._log(f"上传 {label} 凭证...")
        ok, result = upload_to_gateway(creds, cred_type=cred_type, note=note)
        if ok:
            tid = result.get("id", "?")
            action = "更新" if result.get("updated") else "新增"
            self._log(f"✓ {label} 上传成功! ({action}) ID: {tid}")
            messagebox.showinfo("成功", f"{label} 凭证已{action}上传!\nID: {tid}")
        else:
            self._log(f"✗ {label} 上传失败: {result}")
            messagebox.showerror("失败", f"{label} 上传失败:\n{result}")

    def do_upload_kiro(self):
        if self.kiro_creds:
            self._do_upload(self.kiro_creds, "kiro", "Kiro")

    def do_upload_cursor(self):
        if self.cursor_creds:
            self._do_upload(self.cursor_creds, "cursor", "Cursor")

    def do_upload_all(self):
        if self.kiro_creds:
            self._do_upload(self.kiro_creds, "kiro", "Kiro")
        if self.cursor_creds:
            self._do_upload(self.cursor_creds, "cursor", "Cursor")

    def do_switch_kiro(self):
        self._log("")
        self._log("━━━ Kiro 换号 ━━━")
        try:
            lines = switch_kiro()
            for line in lines:
                self._log(f"  {line}")
        except Exception as e:
            self._log(f"  [x] 异常: {e}")
        messagebox.showinfo("Kiro 换号", "Kiro 换号完成。\n请重新打开 Kiro 用新账号登录。")

    def do_switch_cursor(self):
        self._log("")
        self._log("━━━ Cursor 换号 ━━━")
        try:
            lines = switch_cursor()
            for line in lines:
                self._log(f"  {line}")
        except Exception as e:
            self._log(f"  [x] 异常: {e}")
        messagebox.showinfo("Cursor 换号", "Cursor 换号完成。\n请重新打开 Cursor 用新账号登录。")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ExtractorApp()
    app.run()
