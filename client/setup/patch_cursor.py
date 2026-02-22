#!/usr/bin/env python3
"""
Cursor Patch — 防止 Cursor 自动关闭 OpenAI Key 转发。

原理：
Cursor 在订阅状态变更和登录状态变更时，会自动关闭 useOpenAIKey。
补丁将这两个 listener 的条件替换为 false，使其永远不触发。

用法：
  python3 patch_cursor.py          # 应用补丁
  python3 patch_cursor.py --revert # 还原补丁
"""

import os
import sys
import shutil
import platform


def get_cursor_js_path():
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Darwin":
        candidates = [
            "/Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js",
            os.path.join(home, "Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js"),
        ]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        candidates = [
            os.path.join(local, "Programs", "cursor", "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"),
            os.path.join(local, "Programs", "Cursor", "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"),
        ]
    else:
        candidates = [
            "/usr/share/cursor/resources/app/out/vs/workbench/workbench.desktop.main.js",
            "/opt/cursor/resources/app/out/vs/workbench/workbench.desktop.main.js",
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# ═══════════════════════════════════════════════════════
#  补丁定义（所有补丁保持原始长度不变）
# ═══════════════════════════════════════════════════════

PATCHES = []

# Patch 1: 防止订阅变更时关闭 OpenAI Key
# 原始: m!==la.FREE&&this.setUseOpenAIKey(
# 替换: false      &&this.setUseOpenAIKey(
PATCHES.append({
    "name": "订阅变更监听",
    "original": 'this.subscriptionChangedListener=m=>{m!==la.FREE&&this.setUseOpenAIKey(',
    "patched":  'this.subscriptionChangedListener=m=>{false      &&this.setUseOpenAIKey(',
})

# Patch 2: 防止登录变更时关闭 OpenAI Key
_p3_prefix = 'this.loginChangedListener=m=>{('
_p3_suffix = ')&&this.setUseOpenAIKey('
_p3_part1 = 'this.cursorAuthenticationService.membershipType()===la.PRO'
_p3_part2 = 'this.cursorAuthenticationService.membershipType()===la.PRO_PLUS'
_p3_part3 = 'this.cursorAuthenticationService.membershipType()===la.ULTRA'
_p3_r1 = 'false' + ' ' * (len(_p3_part1) - 5)
_p3_r2 = 'false' + ' ' * (len(_p3_part2) - 5)
_p3_r3 = 'false' + ' ' * (len(_p3_part3) - 5)

PATCHES.append({
    "name": "登录变更监听",
    "original": _p3_prefix + _p3_part1 + '||' + _p3_part2 + '||' + _p3_part3 + _p3_suffix,
    "patched":  _p3_prefix + _p3_r1 + '||' + _p3_r2 + '||' + _p3_r3 + _p3_suffix,
})


def apply_patch(js_path, revert=False):
    import hashlib
    import base64
    import json

    backup_path = js_path + ".apollo_backup"

    if revert:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, js_path)
            print(f"已还原: {js_path}")
            return True
        else:
            print("未找到备份文件，无法还原")
            return False

    # Read file
    with open(js_path, 'r', errors='ignore') as f:
        content = f.read()
    original_len = len(content)

    # Backup original
    if not os.path.exists(backup_path):
        shutil.copy2(js_path, backup_path)
        print(f"已备份原文件: {backup_path}")

    applied = 0
    for patch in PATCHES:
        name = patch["name"]
        mode = patch.get("mode", "replace")

        if mode == "hollow_function":
            sig = patch["sig"]
            idx = content.find(sig)
            if idx < 0:
                # 检查是否已经被 hollow 过
                check_sig = sig[:-1]
                check_idx = content.find(check_sig)
                if check_idx >= 0:
                    brace_pos = content.index('{', check_idx + len(check_sig) - 1)
                    if content[brace_pos+1:brace_pos+10].strip() == '':
                        applied += 1
                        continue
                print(f"  [跳过] {name}: 未找到目标代码")
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

            content = content[:brace_start+1] + ' ' * len(old_body) + content[brace_end:]
            applied += 1
            print(f"  [成功] {name}: 已替换 ({len(old_body)} chars hollowed)")
        else:
            original = patch["original"]
            patched = patch["patched"]

            if len(original) != len(patched):
                print(f"  [错误] {name}: 补丁长度不匹配 ({len(original)} vs {len(patched)})")
                continue

            if patched in content:
                applied += 1
                continue

            count = content.count(original)
            if count == 0:
                print(f"  [跳过] {name}: 未找到目标代码（可能 Cursor 版本不同）")
                continue
            if count > 1:
                print(f"  [警告] {name}: 找到 {count} 处匹配，仅替换第一处")

            content = content.replace(original, patched, 1)
            applied += 1
            print(f"  [成功] {name}: 已替换")

    if applied == 0:
        print("未能应用任何补丁，可能 Cursor 版本不兼容")
        return False

    if len(content) != original_len:
        print("补丁导致文件长度变化，已放弃")
        return False

    # Write patched file
    with open(js_path, 'w') as f:
        f.write(content)

    # Update checksum in product.json
    product_json = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(js_path)))), "product.json")
    if os.path.exists(product_json):
        try:
            with open(js_path, 'rb') as f:
                sha256 = hashlib.sha256(f.read()).digest()
            new_cs = base64.b64encode(sha256).decode('ascii').rstrip('=')
            with open(product_json, 'r') as f:
                product = json.load(f)
            if 'checksums' in product:
                product['checksums']['vs/workbench/workbench.desktop.main.js'] = new_cs
                with open(product_json, 'w') as f:
                    json.dump(product, f, indent='\t')
                print("  [成功] checksum 已更新")
        except Exception as e:
            print(f"  [警告] checksum 更新失败: {e}")

    print(f"\n补丁已应用 ({applied}/{len(PATCHES)} 处)")
    print("重启 Cursor 后生效")
    return True


def main():
    revert = "--revert" in sys.argv

    js_path = get_cursor_js_path()
    if not js_path:
        print("未找到 Cursor 安装路径")
        sys.exit(1)

    print(f"Cursor JS: {js_path}")
    print(f"操作: {'还原' if revert else '应用补丁'}\n")

    ok = apply_patch(js_path, revert)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
