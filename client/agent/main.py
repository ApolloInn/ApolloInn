#!/usr/bin/env python3
"""
Apollo Local Agent v2 — 用户本机运行的轻量服务。

功能：调 gateway /user/switch 从 cursor_tokens 取号，自动切换本机 Cursor 账号。

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
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
#  配置
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
#  机器码重置
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
#  缓存清理
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
    写入 Cursor 凭证。统一写入所有认证字段，不再区分 workos/legacy。
    """
    access_token = account.get("access_token") or account.get("accessToken") or ""
    refresh_token = account.get("refresh_token") or account.get("refreshToken") or ""
    email = account.get("email") or ""
    user_id = account.get("user_id") or account.get("userId") or ""

    # 从 JWT 的 sub 字段提取 userId
    if not user_id and access_token:
        try:
            import base64
            parts = access_token.split('.')
            if len(parts) >= 2:
                payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                decoded = json.loads(base64.b64decode(payload))
                user_id = decoded.get("sub", "")
        except Exception:
            pass

    # workos 格式兼容（旧版 token 含 ::）
    if not user_id and ("::" in access_token or "%3A%3A" in access_token):
        sep = "%3A%3A" if "%3A%3A" in access_token else "::"
        user_id = access_token.split(sep)[0]

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        entries = [
            ("cursorAuth/accessToken", access_token),
            ("cursorAuth/refreshToken", refresh_token or access_token),
            ("cursorAuth/workosSessionToken", access_token),
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
        return f"已写入凭证 ({email}, userId={user_id[:30]}...)"
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
    8. 清缓存 + 启动
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

    # 8. 清缓存 + 启动
    cache_steps = clear_cursor_cache()
    steps.extend(cache_steps)
    launched, launch_msg = launch_cursor()
    steps.append(launch_msg)

    return {"ok": True, "email": email, "steps": steps}




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
        "usertoken": cfg.get("usertoken", ""),
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
            # 唯一换号路径：调 gateway /user/switch 从 cursor_tokens 取号，本地 do_switch
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
