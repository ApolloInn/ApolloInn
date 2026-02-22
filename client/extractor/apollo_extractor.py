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
    """提取 Cursor 凭证。返回 (creds, source, scan_log)。"""
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
            ]:
                cur.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                row = cur.fetchone()
                kv[key.split("/")[-1]] = row[0] if row else ""
            conn.close()
            workos = kv.get("workosSessionToken", "")
            email = kv.get("email", "") or kv.get("cachedEmail", "")
            access = workos or kv.get("accessToken", "")
            refresh = kv.get("refreshToken", "")
            if not access and not refresh:
                log_lines.append("  → 无有效凭证")
                continue
            log_lines.append("  ✓ 找到凭证")
            return {
                "email": email, "accessToken": access, "refreshToken": refresh,
                "membership": kv.get("stripeMembershipType", ""),
                "authType": "workos" if workos else "legacy",
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


def clear_kiro_cache():
    """清除 Kiro SSO 缓存 + enterprise 配置，返回日志行列表。"""
    import uuid
    lines = []

    # 1. ~/.aws/sso/cache/
    sso_dir = Path.home() / ".aws" / "sso" / "cache"
    if sso_dir.exists():
        count = 0
        for f in sso_dir.iterdir():
            if f.is_file() and f.suffix == ".json":
                f.unlink()
                count += 1
        if count:
            lines.append(f"✓ 删除 SSO 缓存文件 {count} 个 ({sso_dir})")
        else:
            lines.append(f"ℹ SSO 缓存目录为空 ({sso_dir})")
    else:
        lines.append(f"ℹ SSO 缓存目录不存在 ({sso_dir})")

    # 2. Kiro state.vscdb enterprise 配置
    vscdb = _get_kiro_vscdb_path()
    if vscdb.exists():
        try:
            conn = sqlite3.connect(str(vscdb))
            cur = conn.cursor()
            cur.execute("DELETE FROM ItemTable WHERE key LIKE 'kiro.enterprise.%'")
            if cur.rowcount > 0:
                lines.append(f"✓ 清除 Kiro enterprise 配置 ({cur.rowcount} 项)")
            else:
                lines.append("ℹ 无 enterprise 配置需要清除")
            conn.commit()
            conn.close()
        except Exception as e:
            lines.append(f"✗ 清除 state.vscdb 失败: {e}")
    else:
        lines.append(f"ℹ Kiro state.vscdb 不存在 ({vscdb})")

    lines.append("")
    lines.append("请重启 Kiro，用新账号登录后再扫描上传。")
    return lines


def reset_machine_id():
    """重置 Cursor / Kiro 机器码，返回日志行列表。"""
    import uuid

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

    targets = []
    cursor_db = _get_cursor_vscdb_path()
    if cursor_db.exists():
        targets.append(("Cursor", cursor_db))
    kiro_db = _get_kiro_vscdb_path()
    if kiro_db.exists():
        targets.append(("Kiro", kiro_db))

    if not targets:
        lines.append("✗ 未找到 Cursor 或 Kiro 数据库")
        return lines

    for name, db_path in targets:
        lines.append(f"📦 {name}: {db_path}")
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            changed = 0
            for key, val in id_keys:
                cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?", (val, key))
                if cur.rowcount > 0:
                    changed += 1
                    lines.append(f"  ✓ {key} → {val[:20]}...")
            conn.commit()
            conn.close()
            if changed == 0:
                lines.append("  ℹ 未找到机器码字段")
            else:
                lines.append(f"  ✅ 已更新 {changed} 个字段")
        except Exception as e:
            lines.append(f"  ✗ 失败: {e}")

    lines.append("")
    lines.append(f"新 DeviceId: {new_id}")
    lines.append(f"新 MachineId: {new_mac_id[:32]}...")
    lines.append("请重启 IDE 生效。")
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

        # 扫描 & 上传按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 8))
        ttk.Button(btn_frame, text="① 扫描本机", command=self.do_scan).pack(side="left", padx=(0, 8))
        self.upload_kiro_btn = ttk.Button(btn_frame, text="② 上传 Kiro", command=self.do_upload_kiro, state="disabled")
        self.upload_kiro_btn.pack(side="left", padx=(0, 8))
        self.upload_cursor_btn = ttk.Button(btn_frame, text="③ 上传 Cursor", command=self.do_upload_cursor, state="disabled")
        self.upload_cursor_btn.pack(side="left", padx=(0, 8))
        self.upload_all_btn = ttk.Button(btn_frame, text="全部上传", command=self.do_upload_all, state="disabled")
        self.upload_all_btn.pack(side="left")

        # 工具按钮
        tool_frame = ttk.Frame(frame)
        tool_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(tool_frame, text="🧹 清除缓存(换号)", command=self.do_clear_cache).pack(side="left", padx=(0, 8))
        ttk.Button(tool_frame, text="🔄 更换机器码", command=self.do_reset_id).pack(side="left")

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

    def do_clear_cache(self):
        self._log("")
        self._log("━━━ 清除 Kiro 缓存 ━━━")
        lines = clear_kiro_cache()
        for line in lines:
            self._log(f"  {line}")
        messagebox.showinfo("清除缓存", "已清除 Kiro SSO 缓存。\n请重启 Kiro 用新账号登录后再扫描上传。")

    def do_reset_id(self):
        self._log("")
        self._log("━━━ 更换机器码 ━━━")
        lines = reset_machine_id()
        for line in lines:
            self._log(f"  {line}")
        messagebox.showinfo("更换机器码", "机器码已重置。\n请重启 IDE 生效。")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ExtractorApp()
    app.run()
