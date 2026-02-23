#!/usr/bin/env python3
"""
Apollo Local Agent v2 — 用户本机运行的轻量服务。

功能：
1. 接收网页端指令，自动切换 Cursor 账号
2. 集成 cursor-promax API，实时获取新鲜 token（无需安装插件）
3. 完整的 Cursor 环境重置（机器码、缓存、认证）

用户执行一次: python apollo_agent.py
之后网页端点击"一键切换"即可直接操作本机 Cursor。

默认监听 http://127.0.0.1:19080
"""

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import time
import uuid
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, List, Tuple

PORT = int(os.environ.get("APOLLO_AGENT_PORT", "19080"))
_system = platform.system()

# 内嵌 UI 页面
try:
    from agent_ui import AGENT_HTML
except ImportError:
    AGENT_HTML = "<html><body><h1>Apollo Agent</h1><p>UI module not found. API is still functional.</p></body></html>"

# ═══════════════════════════════════════════════════════
#  cursor-promax API 配置
# ═══════════════════════════════════════════════════════


def _config_path() -> Path:
    d = Path.home() / ".apollo"
    d.mkdir(exist_ok=True)
    return d / "agent_config.json"


def load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    _config_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def _http_get(url: str, params: dict = None, timeout: int = 30) -> dict:
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "ApolloAgent/2.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"error": f"HTTP {e.code}"}
        return {"success": False, **body}


def _http_post(url: str, data: dict = None, params: dict = None, timeout: int = 30) -> dict:
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ApolloAgent/2.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read())
        except Exception:
            err_body = {"error": f"HTTP {e.code}"}
        return {"success": False, **err_body}


# ═══════════════════════════════════════════════════════
#  cursor-promax API 交互
# ═══════════════════════════════════════════════════════

def _get_device_id() -> str:
    cfg = load_config()
    did = cfg.get("device_id")
    if did:
        return did
    did = uuid.uuid4().hex
    cfg["device_id"] = did
    save_config(cfg)
    return did










# ═══════════════════════════════════════════════════════
#  Cursor 路径探测
# ═══════════════════════════════════════════════════════

def _candidate_db_paths() -> List[Path]:
    candidates = []
    home = Path.home()
    env_db = os.environ.get("CURSOR_DB_PATH")
    if env_db:
        candidates.append(Path(env_db))
    if _system == "Windows":
        for env_key in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_key)
            if base:
                candidates.append(Path(base) / "Cursor" / "User" / "globalStorage" / "state.vscdb")
        candidates.append(home / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb")
        candidates.append(home / "AppData" / "Local" / "Cursor" / "User" / "globalStorage" / "state.vscdb")
        install_dir = _win_registry_install_dir()
        if install_dir:
            candidates.append(install_dir / "data" / "User" / "globalStorage" / "state.vscdb")
    elif _system == "Darwin":
        candidates.append(home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        candidates.append(Path(xdg) / "Cursor" / "User" / "globalStorage" / "state.vscdb")
        candidates.append(home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb")
    seen = set()
    unique = []
    for p in candidates:
        s = str(p)
        if s not in seen:
            seen.add(s)
            unique.append(p)
    return unique


def _win_registry_install_dir() -> Optional[Path]:
    if _system != "Windows":
        return None
    try:
        import winreg
        for key_path in (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Cursor.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\cursor.exe",
        ):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and Path(val).exists():
                            return Path(val).parent
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return None


def find_cursor_db() -> Tuple[Optional[Path], List[str]]:
    candidates = _candidate_db_paths()
    tried = []
    for p in candidates:
        tried.append(str(p))
        if p.exists():
            return p, tried
    return None, tried


def _candidate_exe_paths() -> List[Path]:
    candidates = []
    home = Path.home()
    env_exe = os.environ.get("CURSOR_EXE_PATH")
    if env_exe:
        candidates.append(Path(env_exe))
    if _system == "Windows":
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        candidates.append(Path(local) / "Programs" / "cursor" / "Cursor.exe")
        candidates.append(Path(local) / "Programs" / "Cursor" / "Cursor.exe")
        candidates.append(home / "AppData" / "Local" / "Programs" / "cursor" / "Cursor.exe")
        install_dir = _win_registry_install_dir()
        if install_dir:
            candidates.append(install_dir / "Cursor.exe")
        for pf in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(pf)
            if base:
                candidates.append(Path(base) / "Cursor" / "Cursor.exe")
    elif _system == "Darwin":
        candidates.append(Path("/Applications/Cursor.app"))
        candidates.append(home / "Applications" / "Cursor.app")
    else:
        candidates.append(Path("/usr/bin/cursor"))
        candidates.append(Path("/usr/local/bin/cursor"))
        candidates.append(Path("/snap/bin/cursor"))
        candidates.append(home / ".local" / "bin" / "cursor")
    seen = set()
    unique = []
    for p in candidates:
        s = str(p)
        if s not in seen:
            seen.add(s)
            unique.append(p)
    return unique


def find_cursor_exe() -> Tuple[Optional[Path], List[str]]:
    candidates = _candidate_exe_paths()
    tried = []
    for p in candidates:
        tried.append(str(p))
        if p.exists():
            return p, tried
    # 系统命令兜底
    try:
        if _system == "Windows":
            result = subprocess.run(["where", "Cursor.exe"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    pp = Path(line.strip())
                    if pp.exists():
                        tried.append(f"(where) {pp}")
                        return pp, tried
        elif _system == "Darwin":
            result = subprocess.run(
                ["mdfind", "kMDItemCFBundleIdentifier == 'com.todesktop.230313mzl4w4u92'"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    pp = Path(line.strip())
                    if pp.exists():
                        tried.append(f"(mdfind) {pp}")
                        return pp, tried
        else:
            result = subprocess.run(["which", "cursor"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pp = Path(result.stdout.strip())
                tried.append(f"(which) {pp}")
                return pp, tried
    except Exception:
        pass
    return None, tried


# ═══════════════════════════════════════════════════════
#  Cursor 进程管理
# ═══════════════════════════════════════════════════════

def kill_cursor() -> bool:
    try:
        if _system == "Darwin":
            subprocess.run(["osascript", "-e", 'quit app "Cursor"'], capture_output=True, timeout=5)
            time.sleep(1)
            subprocess.run(["pkill", "-f", "Cursor Helper"], capture_output=True, timeout=3)
            subprocess.run(["pkill", "-f", "Cursor.app"], capture_output=True, timeout=3)
        elif _system == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "Cursor.exe"], capture_output=True, timeout=5)
        else:
            subprocess.run(["pkill", "-f", "cursor"], capture_output=True, timeout=5)
        time.sleep(2)
        return True
    except Exception:
        return False


def launch_cursor() -> Tuple[bool, str]:
    if _system == "Darwin":
        try:
            subprocess.Popen(["open", "-a", "Cursor"])
            return True, "已启动 Cursor"
        except Exception as e:
            return False, f"启动失败: {e}"
    elif _system == "Windows":
        exe, _ = find_cursor_exe()
        if exe:
            try:
                subprocess.Popen([str(exe)])
                return True, f"已启动 Cursor ({exe})"
            except Exception as e:
                return False, f"启动失败: {e}"
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "Cursor"], shell=False)
            return True, "已启动 Cursor (start)"
        except Exception:
            return False, "启动失败，请手动打开 Cursor"
    else:
        try:
            subprocess.Popen(["cursor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "已启动 Cursor"
        except Exception as e:
            return False, f"启动失败: {e}"


# ═══════════════════════════════════════════════════════
#  机器码重置（参考 cursor-promax resetCursorMachineId）
# ═══════════════════════════════════════════════════════

def _get_cursor_data_dir(db_path: Path) -> Path:
    """从 db_path 推导 Cursor 数据根目录（…/Cursor/User/globalStorage → …/Cursor）。"""
    return db_path.parent.parent.parent


def reset_cursor_machine_ids(db_path: Path, machine_ids: dict = None) -> List[str]:
    """
    写入 Cursor 机器码（storage.json + state.vscdb + machineId 文件）。
    如果提供了 machine_ids（服务端下发），使用固定值；否则随机生成（兼容旧逻辑）。
    返回操作日志列表。
    """

    steps = []
    cursor_dir = _get_cursor_data_dir(db_path)
    global_storage = db_path.parent

    if machine_ids:
        # 使用服务端下发的固定机器码（同账号所有用户一致）
        dev_device_id = machine_ids.get("devDeviceId", str(uuid.uuid4()))
        machine_id = machine_ids.get("machineId", hashlib.sha256(os.urandom(32)).hexdigest())
        mac_machine_id = machine_ids.get("macMachineId", hashlib.sha256(os.urandom(32)).hexdigest())
        sqm_id = machine_ids.get("sqmId", "{" + str(uuid.uuid4()).upper() + "}")
        steps.append("使用服务端下发的固定机器码")
    else:
        # 兼容：随机生成
        dev_device_id = str(uuid.uuid4())
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        mac_machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
        steps.append("随机生成机器码（无服务端下发）")

    new_ids = {
        "telemetry.devDeviceId": dev_device_id,
        "telemetry.macMachineId": mac_machine_id,
        "telemetry.machineId": machine_id,
        "telemetry.sqmId": sqm_id,
        "storage.serviceMachineId": machine_id,
    }

    # 1. 更新 storage.json
    storage_json = global_storage / "storage.json"
    if storage_json.exists():
        try:
            cfg = json.loads(storage_json.read_text(encoding="utf-8"))
            cfg.update(new_ids)
            storage_json.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
            steps.append("已重置 storage.json")
        except Exception as e:
            steps.append(f"storage.json 失败: {e}")
    else:
        steps.append("storage.json 不存在，跳过")

    # 2. 更新 state.vscdb
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for key, value in new_ids.items():
            cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        steps.append("已重置 vscdb 机器码")
    except Exception as e:
        steps.append(f"vscdb 机器码失败: {e}")

    # 3. 更新 machineid 文件（注意：macOS/Linux 上文件名是小写 machineid）
    machine_id_file = cursor_dir / "machineid"
    try:
        machine_id_file.parent.mkdir(parents=True, exist_ok=True)
        # 使用服务端下发的 fileId，或随机生成
        file_machine_id = (machine_ids or {}).get("fileId") or str(uuid.uuid4())
        machine_id_file.write_text(file_machine_id, encoding="utf-8")
        steps.append("已重置 machineid 文件")
    except Exception as e:
        steps.append(f"machineid 文件失败: {e}")

    # 4. macOS: 清理 Keychain 中的 Cursor 条目
    if platform.system() == "Darwin":
        try:
            import subprocess
            subprocess.run(
                'security delete-generic-password -s "Cursor Safe Storage" 2>/dev/null || true',
                shell=True, capture_output=True, timeout=5,
            )
            subprocess.run(
                'security delete-generic-password -s "Cursor" 2>/dev/null || true',
                shell=True, capture_output=True, timeout=5,
            )
            steps.append("已清理 macOS Keychain")
        except Exception as e:
            steps.append(f"Keychain 清理跳过: {e}")

    return steps



# ═══════════════════════════════════════════════════════
#  缓存清理（参考 cursor-promax clearCursorCache）
# ═══════════════════════════════════════════════════════

def clear_cursor_cache() -> List[str]:
    """删除 Cursor 缓存目录，返回操作日志。"""
    steps = []
    home = Path.home()

    if _system == "Darwin":
        dirs = [
            home / "Library" / "Caches" / "Cursor",
            home / "Library" / "Application Support" / "Cursor" / "Cache",
            home / "Library" / "Application Support" / "Cursor" / "CachedData",
        ]
    elif _system == "Windows":
        appdata = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        localappdata = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        dirs = [
            Path(localappdata) / "Cursor" / "Cache",
            Path(localappdata) / "Cursor" / "CachedData",
            Path(appdata) / "Cursor" / "Cache",
            Path(appdata) / "Cursor" / "CachedData",
        ]
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        xdg_cache = os.environ.get("XDG_CACHE_HOME", str(home / ".cache"))
        dirs = [
            Path(xdg_cache) / "Cursor",
            Path(xdg) / "Cursor" / "Cache",
            Path(xdg) / "Cursor" / "CachedData",
        ]

    for d in dirs:
        if d.exists():
            try:
                shutil.rmtree(d)
                steps.append(f"已删除 {d.name}")
            except Exception as e:
                steps.append(f"删除 {d.name} 失败: {e}")
    if not steps:
        steps.append("无缓存需要清理")
    return steps


# ═══════════════════════════════════════════════════════
#  认证操作
# ═══════════════════════════════════════════════════════

AUTH_KEYS = [
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


def clear_cursor_auth(db_path: Path) -> str:
    """清除所有 cursorAuth 字段。"""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for key in AUTH_KEYS:
            cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, ""))
        conn.commit()
        conn.close()
        return "已清除旧认证"
    except Exception as e:
        return f"清除认证失败: {e}"


def write_cursor_creds(db_path: Path, account: dict) -> str:
    """
    写入新鲜凭证。account 字段兼容 cursor-promax API 返回格式：
    - access_token / accessToken
    - refresh_token / refreshToken
    - workos_token / workosSessionToken
    - email
    - user_id / userId
    """
    access_token = account.get("access_token") or account.get("accessToken") or ""
    refresh_token = account.get("refresh_token") or account.get("refreshToken") or ""
    workos_token = account.get("workos_token") or account.get("workosSessionToken") or ""
    email = account.get("email") or ""
    user_id = account.get("user_id") or account.get("userId") or ""

    # 判断 token 类型
    token = workos_token or access_token
    is_workos = "::" in token or "%3A%3A" in token

    if is_workos and not user_id:
        sep = "%3A%3A" if "%3A%3A" in token else "::"
        user_id = token.split(sep)[0]

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        if is_workos:
            entries = [
                ("cursorAuth/workosSessionToken", token),
                ("cursorAuth/accessToken", access_token),
                ("cursorAuth/refreshToken", refresh_token or access_token),
                ("cursorAuth/email", email),
                ("cursorAuth/cachedEmail", email),
                ("cursorAuth/userId", user_id),
                ("cursorAuth/stripeMembershipType", "pro"),
                ("cursorAuth/stripeSubscriptionStatus", "active"),
                ("cursorAuth/sign_up_type", "Auth_0"),
                ("cursorAuth/cachedSignUpType", "Auth_0"),
            ]
        else:
            entries = [
                ("cursorAuth/accessToken", access_token),
                ("cursorAuth/refreshToken", refresh_token),
                ("cursorAuth/email", email),
                ("cursorAuth/cachedEmail", email),
                ("cursorAuth/userId", user_id),
                ("cursorAuth/stripeMembershipType", "pro"),
                ("cursorAuth/stripeSubscriptionStatus", "active"),
                ("cursorAuth/sign_up_type", "Auth_0"),
                ("cursorAuth/cachedSignUpType", "Auth_0"),
            ]

        for key, value in entries:
            cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        return f"已写入凭证 ({email})"
    except Exception as e:
        return f"写入凭证失败: {e}"


def verify_account_written(db_path: Path, email: str) -> Tuple[bool, str]:
    """验证凭证是否写入成功。"""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT value FROM ItemTable WHERE key = ?", ("cursorAuth/email",))
        row = cur.fetchone()
        conn.close()
        if row and row[0] == email:
            return True, "验证通过"
        return False, f"验证失败: 期望 {email}，实际 {row[0] if row else '空'}"
    except Exception as e:
        return False, f"验证异常: {e}"


# ═══════════════════════════════════════════════════════
#  Cursor OpenAI 代理配置
# ═══════════════════════════════════════════════════════

REACTIVE_STORAGE_KEY = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser"

# Cursor 已知默认模型列表（用于 modelOverrideDisabled 预禁用）
CURSOR_KNOWN_MODELS = {
    "claude-4-sonnet", "claude-4-sonnet-1m", "claude-4-sonnet-1m-thinking", "claude-4-sonnet-thinking",
    "claude-4.5-haiku", "claude-4.5-haiku-thinking", "claude-4.5-opus-high", "claude-4.5-opus-high-thinking",
    "claude-4.5-sonnet", "claude-4.5-sonnet-thinking", "claude-4.6-opus-high", "claude-4.6-opus-high-thinking",
    "claude-4.6-opus-high-thinking-fast", "claude-4.6-opus-max", "claude-4.6-opus-max-thinking",
    "claude-4.6-opus-max-thinking-fast", "composer-1", "composer-1.5", "default",
    "gemini-2.5-flash", "gemini-3-flash", "gemini-3-pro",
    "gpt-5-mini", "gpt-5.1-codex-max", "gpt-5.1-codex-max-high", "gpt-5.1-codex-max-high-fast",
    "gpt-5.1-codex-max-low", "gpt-5.1-codex-max-low-fast", "gpt-5.1-codex-max-medium-fast",
    "gpt-5.1-codex-max-xhigh", "gpt-5.1-codex-max-xhigh-fast", "gpt-5.1-codex-mini",
    "gpt-5.1-codex-mini-high", "gpt-5.1-codex-mini-low", "gpt-5.1-high",
    "gpt-5.2", "gpt-5.2-codex", "gpt-5.2-codex-fast", "gpt-5.2-codex-high", "gpt-5.2-codex-high-fast",
    "gpt-5.2-codex-low", "gpt-5.2-codex-low-fast", "gpt-5.2-codex-xhigh", "gpt-5.2-codex-xhigh-fast",
    "gpt-5.2-fast", "gpt-5.2-high", "gpt-5.2-high-fast", "gpt-5.2-low", "gpt-5.2-low-fast",
    "gpt-5.2-xhigh", "gpt-5.2-xhigh-fast",
    "gpt-5.3-codex", "gpt-5.3-codex-fast", "gpt-5.3-codex-high", "gpt-5.3-codex-high-fast",
    "gpt-5.3-codex-low", "gpt-5.3-codex-low-fast", "gpt-5.3-codex-xhigh", "gpt-5.3-codex-xhigh-fast",
    "grok-code-fast-1", "kimi-k2-instruct",
}

def configure_cursor_proxy(db_path: Path, apikey: str, base_url: str, models: list) -> List[str]:
    """
    配置 Cursor 代理：
    1. 写入 API Key
    2. 设置 useOpenAIKey=true, openAIBaseUrl
    不写入模型列表，让用户自行在 Cursor 中添加。
    """
    steps = []
    if not apikey:
        steps.append("无 API Key，跳过代理配置")
        return steps

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # 1. 写入 OpenAI API Key
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                     ("cursorAuth/openAIKey", apikey))
        steps.append(f"已写入 API Key: {apikey[:8]}...")

        # 2. 更新 reactive storage
        cur.execute("SELECT value FROM ItemTable WHERE key = ?", (REACTIVE_STORAGE_KEY,))
        row = cur.fetchone()
        if row and row[0]:
            try:
                reactive = json.loads(row[0])
            except Exception:
                reactive = {}
        else:
            reactive = {}

        reactive["useOpenAIKey"] = True
        if base_url:
            reactive["openAIBaseUrl"] = base_url
            steps.append(f"已设置 Base URL: {base_url}")

        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                     (REACTIVE_STORAGE_KEY, json.dumps(reactive, ensure_ascii=False)))
        conn.commit()
        conn.close()
        steps.append("代理配置完成（模型请在 Cursor 中自行添加）")
    except Exception as e:
        steps.append(f"代理配置失败: {e}")

    return steps


def configure_fake_membership(db_path: Path) -> List[str]:
    """
    伪造 Cursor Pro 会员状态，让 FREE 账号也能使用 BYOK。

    Cursor 的 BYOK 检查逻辑：membershipType 必须不是 FREE 才能用 OpenAI Key。
    我们只需要把会员状态设为 PRO，真实的账号凭证已经由 write_cursor_creds 写入。
    """
    steps = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # 1. stripeMembershipType = "pro"
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                     ("cursorAuth/stripeMembershipType", "pro"))

        # 2. stripeSubscriptionStatus = "active"
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                     ("cursorAuth/stripeSubscriptionStatus", "active"))

        # 3. reactive storage membershipType = 2 (PRO)
        cur.execute("SELECT value FROM ItemTable WHERE key = ?", (REACTIVE_STORAGE_KEY,))
        row = cur.fetchone()
        if row and row[0]:
            try:
                reactive = json.loads(row[0])
            except Exception:
                reactive = {}
        else:
            reactive = {}

        reactive["membershipType"] = 2
        cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                     (REACTIVE_STORAGE_KEY, json.dumps(reactive, ensure_ascii=False)))
        conn.commit()
        conn.close()
        steps.append("已设置会员状态 PRO")
    except Exception as e:
        steps.append(f"设置会员状态失败: {e}")

    return steps


# ═══════════════════════════════════════════════════════
#  编排：完整切换流程
# ═══════════════════════════════════════════════════════

def do_switch(account: dict, proxy_config: dict = None) -> dict:
    """
    完整切换流程：
    1. 关闭 Cursor
    2. 找到数据库
    3. 写入机器码（使用服务端下发的固定值）
    4. 清除旧认证
    5. 写入新凭证
    6. 验证写入
    7. 配置代理
    8. 补丁
    9. 清缓存 + 启动
    """
    steps = []

    # 1. 关闭 Cursor
    kill_cursor()
    steps.append("关闭 Cursor")

    # 2. 找数据库
    db_path, tried = find_cursor_db()
    if not db_path:
        return {"ok": False, "error": f"未找到 Cursor 数据库。尝试过: {tried}", "steps": steps}
    steps.append(f"找到数据库: {db_path.name}")

    # 3. 写入机器码（服务端下发的固定值，同账号所有用户一致）
    machine_ids = account.get("machine_ids") or account.get("machineIds")
    id_steps = reset_cursor_machine_ids(db_path, machine_ids=machine_ids)
    steps.extend(id_steps)

    # 4. 清除旧认证
    clear_msg = clear_cursor_auth(db_path)
    steps.append(clear_msg)

    # 5. 写入新凭证
    write_msg = write_cursor_creds(db_path, account)
    steps.append(write_msg)

    # 6. 验证
    email = account.get("email", "")
    ok, verify_msg = verify_account_written(db_path, email)
    steps.append(verify_msg)
    if not ok:
        return {"ok": False, "error": verify_msg, "steps": steps}

    # 7. 配置 OpenAI 代理（API Key + Base URL + 自定义模型）
    if proxy_config and proxy_config.get("apikey"):
        proxy_steps = configure_cursor_proxy(
            db_path,
            apikey=proxy_config.get("apikey", ""),
            base_url=proxy_config.get("base_url", ""),
            models=proxy_config.get("models", []),
        )
        steps.extend(proxy_steps)

    # 8. 补丁：防止 Cursor 自动关闭 OpenAI Key 转发
    patch_steps = patch_cursor_binary()
    steps.extend(patch_steps)

    # 9. 清缓存 + 启动
    cache_steps = clear_cursor_cache()
    steps.extend(cache_steps)
    launched, launch_msg = launch_cursor()
    steps.append(launch_msg)

    return {"ok": True, "email": email, "steps": steps}


def do_promax_switch() -> dict:
    """
    换号：调 gateway 服务器的 /user/switch 拿完整凭证包（token + machine_ids + proxy），然后本地 do_switch。
    """
    cfg = load_config()
    usertoken = cfg.get("usertoken", "")

    if not usertoken:
        return {"ok": False, "error": "未配置 usertoken，无法换号"}

    try:
        req = urllib.request.Request(
            "https://api.apolloinn.site/user/switch",
            data=b"{}",
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {usertoken}")
        req.add_header("User-Agent", "ApolloAgent/2.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if result.get("ok") and result.get("account"):
            account = result["account"]
            normalized = {
                "email": account.get("email", ""),
                "accessToken": account.get("access_token", "") or account.get("accessToken", ""),
                "refreshToken": account.get("refresh_token", "") or account.get("refreshToken", ""),
                "machine_ids": account.get("machine_ids", {}),
            }
            proxy_config = result.get("proxy_config")
            return do_switch(normalized, proxy_config=proxy_config)
        else:
            return {"ok": False, "error": result.get("error", "服务器返回失败")}
    except Exception as e:
        return {"ok": False, "error": f"Gateway 连接失败: {e}"}


def do_status() -> dict:
    """返回当前状态信息。"""
    db_path, tried = find_cursor_db()
    cfg = load_config()

    info = {
        "ok": True,
        "system": _system,
        "db_found": db_path is not None,
        "db_path": str(db_path) if db_path else None,
        "tried_paths": tried,
        "license_activated": bool(cfg.get("activation_code_id")),
        "activation_code": cfg.get("activation_code", ""),
        "device_id": cfg.get("device_id", ""),
    }

    # 读取当前登录信息
    if db_path and db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT value FROM ItemTable WHERE key = ?", ("cursorAuth/email",))
            row = cur.fetchone()
            info["current_email"] = row[0] if row else ""
            cur.execute("SELECT value FROM ItemTable WHERE key = ?", ("cursorAuth/stripeMembershipType",))
            row = cur.fetchone()
            info["membership"] = row[0] if row else ""
            conn.close()
        except Exception:
            pass

    return info

def do_byok_setup(account: dict = None, proxy_config: dict = None) -> dict:
    """兼容旧调用，直接转发到 do_switch。"""
    if not account or not (account.get("accessToken") or account.get("access_token")):
        return {"ok": False, "error": "无可用账号，请联系管理员"}
    return do_switch(account, proxy_config=proxy_config)


def patch_cursor_binary() -> List[str]:
    """
    补丁 Cursor 的 workbench.desktop.main.js：
    1. 防止订阅变更时自动关闭 OpenAI Key 转发
    2. 防止登录变更时自动关闭 OpenAI Key 转发
    """
    steps = []

    js_path = _find_cursor_js()
    if not js_path:
        steps.append("未找到 Cursor JS 文件，跳过补丁")
        return steps

    try:
        with open(js_path, 'r', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        steps.append(f"读取 JS 文件失败: {e}")
        return steps

    original_len = len(content)
    patches = _get_patches()

    # 备份
    backup_path = str(js_path) + ".apollo_backup"
    if not os.path.exists(backup_path):
        try:
            import shutil
            shutil.copy2(str(js_path), backup_path)
            steps.append("已备份原始 JS")
        except Exception as e:
            steps.append(f"备份失败: {e}")

    # 应用补丁
    applied = 0
    total = len(patches)
    for patch in patches:
        name = patch["name"]
        mode = patch.get("mode", "replace")

        if mode == "hollow_function":
            # 整函数体替换为空格（安全方式，保持大括号匹配）
            sig = patch["sig"]
            idx = content.find(sig)
            if idx < 0:
                # 检查是否已经被 hollow 过（函数体全是空格）
                check_sig = sig[:-1]
                check_idx = content.find(check_sig)
                if check_idx >= 0:
                    brace_pos = content.index('{', check_idx + len(check_sig) - 1)
                    if content[brace_pos+1:brace_pos+10].strip() == '':
                        applied += 1
                        continue
                steps.append(f"跳过 {name}（未找到）")
                continue

            brace_start = idx + len(sig) - 1
            depth = 0
            brace_end = brace_start
            for i in range(brace_start, min(brace_start + 15000, len(content))):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        brace_end = i
                        break

            old_body = content[brace_start+1:brace_end]
            if old_body.strip() == '':
                applied += 1
                continue

            new_body = ' ' * len(old_body)
            content = content[:brace_start+1] + new_body + content[brace_end:]
            applied += 1
            steps.append(f"已补丁: {name}")
        else:
            original = patch["original"]
            patched = patch["patched"]

            if len(original) != len(patched):
                steps.append(f"跳过 {name}（长度不匹配）")
                continue

            if patched in content:
                applied += 1
                continue

            if original in content:
                content = content.replace(original, patched, 1)
                applied += 1
                steps.append(f"已补丁: {name}")

    if applied > 0 and len(content) == original_len:
        try:
            with open(js_path, 'w') as f:
                f.write(content)
            _update_checksum(js_path)
            steps.append(f"补丁完成 ({applied}/{total})")
        except Exception as e:
            steps.append(f"写入补丁失败: {e}")
    elif len(content) != original_len:
        steps.append("补丁导致文件长度变化，已放弃")
    else:
        steps.append("无需补丁")

    return steps


def _find_cursor_js() -> Optional[Path]:
    """找到 Cursor 的 workbench.desktop.main.js 文件。"""
    home = Path.home()
    if _system == "Darwin":
        candidates = [
            Path("/Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js"),
            home / "Applications" / "Cursor.app" / "Contents" / "Resources" / "app" / "out" / "vs" / "workbench" / "workbench.desktop.main.js",
        ]
    elif _system == "Windows":
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        candidates = [
            Path(local) / "Programs" / "cursor" / "resources" / "app" / "out" / "vs" / "workbench" / "workbench.desktop.main.js",
            Path(local) / "Programs" / "Cursor" / "resources" / "app" / "out" / "vs" / "workbench" / "workbench.desktop.main.js",
        ]
    else:
        candidates = [
            Path("/usr/share/cursor/resources/app/out/vs/workbench/workbench.desktop.main.js"),
            Path("/opt/cursor/resources/app/out/vs/workbench/workbench.desktop.main.js"),
        ]
    for p in candidates:
        if p.exists():
            return p
    return None

def _update_checksum(js_path):
    """更新 product.json 中的 JS 文件 checksum，避免 Cursor 完整性警告。    """
    import base64

    product_json = Path(str(js_path)).parent.parent.parent.parent / "product.json"
    if not product_json.exists():
        return

    try:
        with open(str(js_path), 'rb') as f:
            sha256 = hashlib.sha256(f.read()).digest()
        new_cs = base64.b64encode(sha256).decode('ascii').rstrip('=')

        with open(str(product_json), 'r') as f:
            product = json.load(f)

        if 'checksums' in product:
            product['checksums']['vs/workbench/workbench.desktop.main.js'] = new_cs
            with open(str(product_json), 'w') as f:
                json.dump(product, f, indent='\t')
    except Exception:
        pass


def _get_patches() -> list:
    """返回 Cursor 补丁列表 — 仅防止自动关闭 OpenAI Key 转发。"""
    patches = []

    # Patch 1: 防止订阅变更时关闭 OpenAI Key
    patches.append({
        "name": "订阅变更监听",
        "original": 'this.subscriptionChangedListener=m=>{m!==la.FREE&&this.setUseOpenAIKey(',
        "patched":  'this.subscriptionChangedListener=m=>{false      &&this.setUseOpenAIKey(',
    })

    # Patch 2: 防止登录变更时关闭 OpenAI Key
    p_prefix = 'this.loginChangedListener=m=>{('
    p_suffix = ')&&this.setUseOpenAIKey('
    p_part1 = 'this.cursorAuthenticationService.membershipType()===la.PRO'
    p_part2 = 'this.cursorAuthenticationService.membershipType()===la.PRO_PLUS'
    p_part3 = 'this.cursorAuthenticationService.membershipType()===la.ULTRA'
    r1 = 'false' + ' ' * (len(p_part1) - 5)
    r2 = 'false' + ' ' * (len(p_part2) - 5)
    r3 = 'false' + ' ' * (len(p_part3) - 5)
    patches.append({
        "name": "登录变更监听",
        "original": p_prefix + p_part1 + '||' + p_part2 + '||' + p_part3 + p_suffix,
        "patched":  p_prefix + r1 + '||' + r2 + '||' + r3 + p_suffix,
    })

    return patches


def do_extract_cursor(admin_key: str) -> dict:
    """
    提取本机 Cursor 凭证并上传到 gateway 服务器的 cursor_tokens 表。
    需要 admin_key 来调用 gateway 的 /admin/cursor-accounts 接口。
    """
    # 1. 找数据库
    db_path, tried = find_cursor_db()
    if not db_path:
        return {"ok": False, "error": f"未找到 Cursor 数据库。尝试过: {tried}"}

    # 2. 读取凭证 + 机器码
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        kv = {}
        for key in [
            "cursorAuth/workosSessionToken",
            "cursorAuth/email",
            "cursorAuth/cachedEmail",
            "cursorAuth/userId",
            "cursorAuth/accessToken",
            "cursorAuth/refreshToken",
            "cursorAuth/stripeMembershipType",
            "telemetry.devDeviceId",
            "telemetry.machineId",
            "telemetry.macMachineId",
            "telemetry.sqmId",
        ]:
            cur.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
            row = cur.fetchone()
            short_key = key.split("/")[-1] if "/" in key else key.split(".")[-1]
            kv[short_key] = row[0] if row else ""
        conn.close()
    except Exception as e:
        return {"ok": False, "error": f"读取数据库失败: {e}"}

    # 读取 machineid 文件
    cursor_dir = _get_cursor_data_dir(db_path)
    file_id = ""
    machine_id_file = cursor_dir / "machineid"
    if machine_id_file.exists():
        try:
            file_id = machine_id_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    email = kv.get("email", "") or kv.get("cachedEmail", "")
    workos_token = kv.get("workosSessionToken", "")
    access_token = workos_token or kv.get("accessToken", "")
    refresh_token = kv.get("refreshToken", "")
    membership = kv.get("stripeMembershipType", "")

    machine_ids = {
        "devDeviceId": kv.get("devDeviceId", ""),
        "machineId": kv.get("machineId", ""),
        "macMachineId": kv.get("macMachineId", ""),
        "sqmId": kv.get("sqmId", ""),
        "fileId": file_id,
    }

    if not email:
        return {"ok": False, "error": "Cursor 未登录（无 email）"}
    if not access_token and not refresh_token:
        return {"ok": False, "error": f"Cursor 账号 {email} 无 token，可能未完全登录"}

    # 3. 上传到 gateway 服务器（含机器码）
    try:
        payload = json.dumps({
            "email": email,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "machine_ids": machine_ids,
            "note": f"Agent 提取 · {membership}",
        }).encode()
        req = urllib.request.Request(
            "https://api.apolloinn.site/admin/cursor-accounts",
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Admin-Key", admin_key)
        req.add_header("User-Agent", "ApolloAgent/2.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            return {
                "ok": True,
                "email": email,
                "membership": membership,
                "has_access_token": bool(access_token),
                "has_refresh_token": bool(refresh_token),
            }
        return {"ok": False, "error": result.get("error", "上传失败")}
    except Exception as e:
        return {"ok": False, "error": f"上传到服务器失败: {e}"}


# ═══════════════════════════════════════════════════════
#  清除 Cursor 登录态 + 重置机器码（不删应用，方便登下一个号）
# ═══════════════════════════════════════════════════════

def do_reset_cursor() -> dict:
    """
    清除 Cursor 登录凭证 + 重置所有机器码。
    不删除应用本体和用户配置，只清登录态和设备指纹，
    重启 Cursor 后会要求重新登录，且被识别为新设备。
    """
    steps = []

    # 1. 关闭 Cursor
    kill_cursor()
    time.sleep(1)
    steps.append("已关闭 Cursor 进程")

    # 2. 找数据库
    db_path, tried = find_cursor_db()
    if not db_path:
        return {"ok": False, "error": f"未找到 Cursor 数据库。尝试过: {tried}"}

    # 3. 清除登录凭证
    auth_keys = [
        "cursorAuth/accessToken",
        "cursorAuth/refreshToken",
        "cursorAuth/workosSessionToken",
        "cursorAuth/email",
        "cursorAuth/cachedEmail",
        "cursorAuth/userId",
        "cursorAuth/stripeMembershipType",
        "cursorAuth/stripeSubscriptionStatus",
        "cursorAuth/sign_up_type",
        "cursorAuth/cachedSignUpType",
        "cursorAuth/onboardingDate",
    ]
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for key in auth_keys:
            cur.execute("DELETE FROM ItemTable WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        steps.append(f"已清除 {len(auth_keys)} 个登录凭证")
    except Exception as e:
        steps.append(f"清除凭证失败: {e}")

    # 4. 重置机器码（DB 中的 telemetry + storage 字段）
    new_ids = {
        "devDeviceId": str(uuid.uuid4()),
        "machineId": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "macMachineId": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "sqmId": "{" + str(uuid.uuid4()).upper() + "}",
    }
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        mapping = {
            "telemetry.devDeviceId": new_ids["devDeviceId"],
            "telemetry.machineId": new_ids["machineId"],
            "telemetry.macMachineId": new_ids["macMachineId"],
            "telemetry.sqmId": new_ids["sqmId"],
            "storage.serviceMachineId": new_ids["machineId"],
        }
        for key, val in mapping.items():
            cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                (key, val),
            )
        conn.commit()
        conn.close()
        steps.append("已重置 state.vscdb 中的机器码")
    except Exception as e:
        steps.append(f"重置机器码失败: {e}")

    # 5. 重置 machineid 文件
    cursor_dir = _get_cursor_data_dir(db_path)
    machine_id_file = cursor_dir / "machineid"
    try:
        machine_id_file.write_text(str(uuid.uuid4()), encoding="utf-8")
        steps.append("已重置 machineid 文件")
    except Exception as e:
        steps.append(f"重置 machineid 文件失败: {e}")

    # 6. 重置 storage.json 中的机器码
    storage_json = cursor_dir / "storage.json"
    if storage_json.exists():
        try:
            data = json.loads(storage_json.read_text(encoding="utf-8"))
            data["telemetry.machineId"] = new_ids["machineId"]
            data["telemetry.macMachineId"] = new_ids["macMachineId"]
            data["telemetry.devDeviceId"] = new_ids["devDeviceId"]
            data["telemetry.sqmId"] = new_ids["sqmId"]
            storage_json.write_text(
                json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
            )
            steps.append("已重置 storage.json 中的机器码")
        except Exception as e:
            steps.append(f"重置 storage.json 失败: {e}")

    steps.append("重置完成，重启 Cursor 后可登录新账号")
    return {"ok": True, "steps": steps}


# ═══════════════════════════════════════════════════════
#  完全清理 Cursor（跨平台）
# ═══════════════════════════════════════════════════════

def do_clean_cursor() -> dict:
    """
    完全清理 Cursor：关闭进程 → 删除应用 → 删除所有数据/缓存/配置。
    macOS: 删除 .app + ~/Library 下所有 Cursor 相关目录 + Keychain
    Windows: 卸载程序 + 删除数据 + 清理注册表/快捷方式/凭证
    """
    steps = []

    # 1. 关闭所有 Cursor 进程
    kill_cursor()
    time.sleep(1)
    steps.append("已关闭 Cursor 进程")

    home = Path.home()

    if _system == "Darwin":
        # ── macOS 清理 ──

        # 2. 删除应用本体
        app_paths = [
            Path("/Applications/Cursor.app"),
            home / "Applications" / "Cursor.app",
        ]
        for app in app_paths:
            if app.exists():
                try:
                    shutil.rmtree(str(app))
                    steps.append(f"已删除 {app}")
                except Exception as e:
                    # 可能需要权限，尝试 osascript
                    try:
                        subprocess.run(
                            ["osascript", "-e", f'do shell script "rm -rf \'{app}\'" with administrator privileges'],
                            capture_output=True, timeout=30,
                        )
                        steps.append(f"已删除 {app}（管理员权限）")
                    except Exception:
                        steps.append(f"删除 {app} 失败: {e}（请手动拖到废纸篓）")

        # 3. 删除所有数据目录
        dirs_to_delete = [
            (home / "Library" / "Application Support" / "Cursor", "用户数据"),
            (home / "Library" / "Caches" / "Cursor", "缓存"),
            (home / "Library" / "Caches" / "com.todesktop.230313mzl4w4u92", "Electron 缓存"),
            (home / "Library" / "Caches" / "com.todesktop.230313mzl4w4u92.ShipIt", "更新缓存"),
            (home / "Library" / "Saved Application State" / "com.todesktop.230313mzl4w4u92.savedState", "窗口状态"),
            (home / "Library" / "Logs" / "Cursor", "日志"),
            (home / "Library" / "WebKit" / "com.todesktop.230313mzl4w4u92", "WebKit 数据"),
            (home / "Library" / "HTTPStorages" / "com.todesktop.230313mzl4w4u92", "HTTP 存储"),
            (home / ".cursor", "项目索引和扩展"),
            (home / ".cursor-tutor", "教程数据"),
        ]

        # 扫描 Preferences plist
        plist_files = [
            home / "Library" / "Preferences" / "com.todesktop.230313mzl4w4u92.plist",
        ]

        for dir_path, desc in dirs_to_delete:
            if dir_path.exists():
                try:
                    shutil.rmtree(str(dir_path))
                    steps.append(f"已删除 {desc}")
                except Exception as e:
                    steps.append(f"删除 {desc} 失败: {e}")

        for plist in plist_files:
            if plist.exists():
                try:
                    plist.unlink()
                    steps.append("已删除 Preferences plist")
                except Exception:
                    pass

        # 4. 清理 Keychain
        for service in ["Cursor Safe Storage", "Cursor"]:
            try:
                subprocess.run(
                    ["security", "delete-generic-password", "-s", service],
                    capture_output=True, timeout=5,
                )
            except Exception:
                pass
        steps.append("已清理 Keychain")

        # 5. 清理 Launch Agents（自动更新等）
        launch_agents = home / "Library" / "LaunchAgents"
        if launch_agents.exists():
            for f in launch_agents.iterdir():
                if "cursor" in f.name.lower() or "230313mzl4w4u92" in f.name:
                    try:
                        f.unlink()
                        steps.append(f"已删除 LaunchAgent: {f.name}")
                    except Exception:
                        pass

    elif _system == "Windows":
        # ── Windows 清理 ──
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        appdata = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        temp_dir = os.environ.get("TEMP", str(home / "AppData" / "Local" / "Temp"))

        # 尝试卸载
        for base_dir in [Path(local) / "Programs" / "cursor", Path(local) / "Programs" / "Cursor"]:
            update_exe = base_dir / "Update.exe"
            if update_exe.exists():
                try:
                    subprocess.run([str(update_exe), "--uninstall", "-s"],
                                   capture_output=True, timeout=60)
                    time.sleep(3)
                    steps.append(f"已执行 Squirrel 卸载")
                except Exception as e:
                    steps.append(f"卸载失败: {e}")

        dirs_to_delete = [
            (Path(appdata) / "Cursor", "用户数据"),
            (Path(local) / "Cursor", "本地缓存"),
            (home / ".cursor", "项目索引和扩展"),
            (Path(local) / "cursor-updater", "更新缓存"),
            (Path(local) / "Cursor-updater", "更新缓存"),
            (Path(local) / "Programs" / "cursor", "安装目录"),
            (Path(local) / "Programs" / "Cursor", "安装目录"),
        ]
        for dir_path, desc in dirs_to_delete:
            if dir_path.exists():
                try:
                    shutil.rmtree(str(dir_path))
                    steps.append(f"已删除 {desc}")
                except Exception as e:
                    steps.append(f"删除 {desc} 失败: {e}")

        # 清理 Temp
        try:
            for item in Path(temp_dir).iterdir():
                if item.is_dir() and "cursor" in item.name.lower():
                    try:
                        shutil.rmtree(str(item))
                        steps.append(f"已删除临时文件: {item.name}")
                    except Exception:
                        pass
        except Exception:
            pass

    else:
        # ── Linux 清理 ──
        xdg = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        xdg_cache = os.environ.get("XDG_CACHE_HOME", str(home / ".cache"))
        dirs_to_delete = [
            (Path(xdg) / "Cursor", "配置"),
            (Path(xdg_cache) / "Cursor", "缓存"),
            (home / ".cursor", "项目索引和扩展"),
        ]
        for dir_path, desc in dirs_to_delete:
            if dir_path.exists():
                try:
                    shutil.rmtree(str(dir_path))
                    steps.append(f"已删除 {desc}")
                except Exception as e:
                    steps.append(f"删除 {desc} 失败: {e}")

    steps.append("清理完成，可重新安装 Cursor")
    return {"ok": True, "steps": steps}


# ═══════════════════════════════════════════════════════
#  HTTP 服务
# ═══════════════════════════════════════════════════════

class AgentHandler(BaseHTTPRequestHandler):
    """轻量 HTTP handler，供网页端调用。"""

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/ui":
            self._html(AGENT_HTML)

        elif path == "/ping":
            self._json(200, {"ok": True, "agent": "apollo-v2", "system": _system})

        elif path == "/status":
            self._json(200, do_status())

        elif path == "/get-token":
            cfg = load_config()
            self._json(200, {"ok": True, "usertoken": cfg.get("usertoken", "")})

        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_len > 0:
            try:
                body = json.loads(self.rfile.read(content_len))
            except Exception:
                pass

        if path == "/save-token":
            usertoken = body.get("usertoken", "")
            cfg = load_config()
            if usertoken:
                cfg["usertoken"] = usertoken
            else:
                cfg.pop("usertoken", None)
            save_config(cfg)
            self._json(200, {"ok": True})

        elif path == "/switch":
            # 静态 token 切换（从网页端传入凭证）
            email = body.get("email", "")
            access_token = body.get("accessToken", "")
            refresh_token = body.get("refreshToken", "")
            if not access_token:
                self._json(400, {"ok": False, "error": "缺少 accessToken"})
                return
            account = {
                "email": email,
                "accessToken": access_token,
                "refreshToken": refresh_token,
            }
            machine_ids = body.get("machine_ids")
            if machine_ids:
                account["machine_ids"] = machine_ids
            proxy_config = body.get("proxy_config")
            result = do_switch(account, proxy_config=proxy_config)
            self._json(200, result)

        elif path in ("/switch", "/smart-switch", "/byok-setup"):
            # 统一换号：调 gateway /user/switch 拿凭证包，本地 do_switch
            usertoken = body.get("usertoken", "")
            if not usertoken:
                cfg = load_config()
                usertoken = cfg.get("usertoken", "")
            if usertoken:
                cfg = load_config()
                cfg["usertoken"] = usertoken
                save_config(cfg)

            if not usertoken:
                self._json(400, {"ok": False, "error": "缺少 usertoken"})
                return

            # 调 gateway
            try:
                req = urllib.request.Request(
                    "https://api.apolloinn.site/user/switch",
                    data=b"{}",
                    method="POST",
                )
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {usertoken}")
                req.add_header("User-Agent", "ApolloAgent/2.0")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    gw_result = json.loads(resp.read())
            except Exception as e:
                self._json(200, {"ok": False, "error": f"Gateway 连接失败: {e}"})
                return

            if not gw_result.get("ok"):
                self._json(200, {"ok": False, "error": gw_result.get("error", "获取账号失败")})
                return

            gw_account = gw_result.get("account", {})
            account = {
                "email": gw_account.get("email", ""),
                "accessToken": gw_account.get("access_token", "") or gw_account.get("accessToken", ""),
                "refreshToken": gw_account.get("refresh_token", "") or gw_account.get("refreshToken", ""),
                "machine_ids": gw_account.get("machine_ids", {}),
            }
            proxy_config = gw_result.get("proxy_config") or body.get("proxy_config", {})

            try:
                result = do_switch(account, proxy_config=proxy_config)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            self._json(200, result)

        elif path == "/extract-cursor":
            # 提取本机 Cursor 凭证并上传到 gateway 服务器的 cursor_tokens 表
            admin_key = body.get("admin_key", "")
            if not admin_key:
                self._json(400, {"ok": False, "error": "缺少 admin_key"})
                return
            try:
                result = do_extract_cursor(admin_key)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            self._json(200, result)

        elif path == "/patch-cursor":
            # 补丁 Cursor 二进制（移除 BYOK 会员检查）
            try:
                steps = patch_cursor_binary()
                self._json(200, {"ok": True, "steps": steps})
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)})

        elif path == "/revert-patch":
            # 还原 Cursor 补丁
            try:
                js_path = _find_cursor_js()
                if js_path:
                    backup = str(js_path) + ".apollo_backup"
                    if os.path.exists(backup):
                        import shutil as _shutil
                        _shutil.copy2(backup, str(js_path))
                        self._json(200, {"ok": True, "message": "已还原 Cursor 补丁"})
                    else:
                        self._json(200, {"ok": False, "error": "未找到备份文件"})
                else:
                    self._json(200, {"ok": False, "error": "未找到 Cursor JS 文件"})
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)})

        elif path == "/reset-cursor":
            try:
                result = do_reset_cursor()
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            self._json(200, result)

        elif path == "/clean-cursor":
            try:
                result = do_clean_cursor()
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            self._json(200, result)

        elif path == "/license-activate":
            # 激活码激活（通过 gateway 获取）
            usertoken = body.get("usertoken", "") or body.get("code", "")
            if not usertoken:
                self._json(400, {"ok": False, "error": "缺少 usertoken"})
                return
            try:
                req = urllib.request.Request(
                    "https://api.apolloinn.site/user/cursor-activation",
                    method="GET",
                )
                req.add_header("Authorization", f"Bearer {usertoken}")
                req.add_header("User-Agent", "ApolloAgent/2.0")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                self._json(200, {"ok": True, "activation_code": result.get("activation_code", "")})
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)})

        elif path == "/batch-register":
            # 批量注册 Cursor 账号
            admin_key = body.get("admin_key", "")
            count = body.get("count", 1)
            if not admin_key:
                self._json(400, {"ok": False, "error": "缺少 admin_key"})
                return
            try:
                from cursor_register import batch_register
                results = batch_register(
                    count=min(count, 20),  # 单次最多 20 个
                    admin_key=admin_key,
                    headless=body.get("headless", True),
                )
                self._json(200, {
                    "ok": True,
                    "registered": len(results),
                    "accounts": [{"email": a["email"]} for a in results],
                })
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)})

        else:
            self._json(404, {"ok": False, "error": "not found"})

    def log_message(self, format, *args):
        # 简化日志
        print(f"  [{time.strftime('%H:%M:%S')}] {args[0] if args else ''}")


# ═══════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════

def _run_macos_native(url: str):
    """macOS: 用 pywebview 创建原生 WebKit 窗口。"""
    import webview
    webview.create_window(
        "Apollo Agent",
        url,
        width=860,
        height=740,
        min_size=(640, 500),
        resizable=True,
    )
    webview.start()


def _run_windows_native(url: str):
    """Windows: 用 pywebview 创建原生 WebView2/MSHTML 窗口。"""
    import webview
    webview.create_window(
        "Apollo Agent",
        url,
        width=860,
        height=740,
        min_size=(640, 500),
        resizable=True,
    )
    webview.start()


def _kill_existing_on_port(port: int):
    """启动前尝试关闭占用同端口的旧进程。"""
    try:
        if _system == "Windows":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != os.getpid():
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )
            for pid_str in result.stdout.strip().splitlines():
                pid = int(pid_str.strip())
                if pid != os.getpid():
                    os.kill(pid, 9)
    except Exception:
        pass


def main():
    import threading

    url = f"http://127.0.0.1:{PORT}"

    _kill_existing_on_port(PORT)
    time.sleep(0.5)

    # 启动 HTTP server（后台线程）
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AgentHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    opened = False

    if _system == "Darwin":
        try:
            _run_macos_native(url)
            opened = True
        except Exception as e:
            _err = f"[WARN] 原生窗口启动失败，回退到浏览器: {e}"
            print(_err)
            try:
                Path.home().joinpath(".apollo", "agent_error.log").write_text(_err)
            except Exception:
                pass
    elif _system == "Windows":
        try:
            _run_windows_native(url)
            opened = True
        except Exception as e:
            print(f"[WARN] 原生窗口启动失败，回退到浏览器: {e}")

    if opened:
        server.shutdown()
        return

    # fallback: 浏览器（Linux 或依赖缺失时）
    webbrowser.open(url)
    try:
        server_thread.join()
    except KeyboardInterrupt:
        pass
    server.shutdown()


if __name__ == "__main__":
    main()
