"""
AugmentPage JetBrains IDE处理器
支持跨平台（Windows、macOS、Linux）
此模块处理JetBrains IDE特定操作，包括:
- PermanentDeviceId文件修改
- PermanentUserId文件修改
- 文件锁定以防止重新生成
-QW
"""

import os
import sys
import stat
import uuid
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any


def generate_uuid() -> str:
    """生成新的UUID字符串 -QW"""
    return str(uuid.uuid4())


def backup_file(file_path: Path) -> str:
    """
    创建文件备份 -QW

    Args:
        file_path (Path): 要备份的文件路径

    Returns:
        str: 备份文件路径
    """
    if not file_path.exists():
        return ""

    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    shutil.copy2(file_path, backup_path)
    print(f"[JetBrains处理器] 创建备份: {backup_path}")
    return str(backup_path)


def lock_file(file_path: Path) -> bool:
    """
    锁定文件以防止修改 -QW
    支持跨平台（Windows、macOS、Linux）

    Args:
        file_path (Path): 要锁定的文件路径

    Returns:
        bool: 成功返回True，否则返回False
    """
    try:
        if not file_path.exists():
            return False

        # 使用Python API将文件设置为只读 -QW
        current_permissions = file_path.stat().st_mode
        file_path.chmod(stat.S_IREAD)

        # 使用平台特定命令进行额外保护 -QW
        if sys.platform == "win32":
            # Windows系统：使用attrib命令 -QW
            try:
                subprocess.run(
                    ["attrib", "+R", str(file_path)],
                    check=False,
                    capture_output=True
                )
            except Exception:
                pass
        else:
            # Unix系统：使用chmod -QW
            try:
                subprocess.run(
                    ["chmod", "444", str(file_path)],
                    check=False,
                    capture_output=True
                )
            except Exception:
                pass

            # macOS系统：使用chflags进行额外保护 -QW
            if sys.platform == "darwin":
                try:
                    subprocess.run(
                        ["chflags", "uchg", str(file_path)],
                        check=False,
                        capture_output=True
                    )
                    print(f"[JetBrains处理器] macOS文件锁定: {file_path}")
                except Exception:
                    pass

        print(f"[JetBrains处理器] 文件已锁定: {file_path}")
        return True
    except Exception as e:
        print(f"[JetBrains处理器] ⚠️ 文件锁定失败: {str(e)}")
        return False


def update_jetbrains_id_file(file_path: Path) -> Dict[str, Any]:
    """
    更新JetBrains ID文件 -QW

    Args:
        file_path (Path): ID文件路径

    Returns:
        Dict[str, Any]: 操作结果
    """
    result = {
        'success': False,
        'old_id': '',
        'new_id': '',
        'backup_path': '',
        'locked': False,
        'file_path': str(file_path)
    }

    try:
        # 读取旧ID -QW
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                result['old_id'] = f.read().strip()
            
            # 创建备份 -QW
            result['backup_path'] = backup_file(file_path)

        # 生成新ID -QW
        new_id = generate_uuid()
        result['new_id'] = new_id

        # 确保目录存在 -QW
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入新ID -QW
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_id)

        # 锁定文件 -QW
        result['locked'] = lock_file(file_path)
        result['success'] = True

        print(f"[JetBrains处理器] ✅ ID文件更新成功: {file_path}")
        return result

    except Exception as e:
        result['error'] = str(e)
        print(f"[JetBrains处理器] ❌ ID文件更新失败: {str(e)}")
        return result


def get_jetbrains_config_dir() -> Path:
    """
    获取JetBrains配置目录 -QW
    支持跨平台（Windows、macOS、Linux）

    Returns:
        Path: JetBrains配置目录路径
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        appdata = os.getenv("APPDATA", "")
        return Path(appdata) / "JetBrains"
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return Path.home() / "Library" / "Application Support" / "JetBrains"
    else:
        # Linux系统 -QW
        return Path.home() / ".config" / "JetBrains"


def modify_jetbrains_ids(ide_name: str = "IntelliJIdea") -> Dict[str, Any]:
    """
    修改JetBrains IDE的设备ID和用户ID -QW
    支持跨平台（Windows、macOS、Linux）

    Args:
        ide_name (str): IDE名称，如 "IntelliJIdea", "PyCharm" 等

    Returns:
        Dict[str, Any]: 操作结果
    """
    print(f"[JetBrains处理器] 开始修改 {ide_name} ID...")
    
    result = {
        'success': False,
        'ide_name': ide_name,
        'device_id_result': {},
        'user_id_result': {},
        'errors': []
    }

    try:
        # 获取JetBrains配置目录 -QW
        jetbrains_dir = get_jetbrains_config_dir()
        
        if not jetbrains_dir.exists():
            error_msg = f"JetBrains配置目录不存在: {jetbrains_dir}"
            result['errors'].append(error_msg)
            print(f"[JetBrains处理器] ❌ {error_msg}")
            return result

        # 查找IDE配置目录 -QW
        ide_dirs = [d for d in jetbrains_dir.iterdir() 
                   if d.is_dir() and ide_name.lower() in d.name.lower()]

        if not ide_dirs:
            error_msg = f"未找到 {ide_name} 配置目录"
            result['errors'].append(error_msg)
            print(f"[JetBrains处理器] ❌ {error_msg}")
            return result

        # 处理找到的每个IDE目录 -QW
        for ide_dir in ide_dirs:
            print(f"[JetBrains处理器] 处理目录: {ide_dir}")
            
            # 更新PermanentDeviceId -QW
            device_id_file = ide_dir / "PermanentDeviceId"
            device_result = update_jetbrains_id_file(device_id_file)
            result['device_id_result'] = device_result
            
            if not device_result['success']:
                result['errors'].append(f"设备ID更新失败: {device_result.get('error', '未知错误')}")

            # 更新PermanentUserId -QW
            user_id_file = ide_dir / "PermanentUserId"
            user_result = update_jetbrains_id_file(user_id_file)
            result['user_id_result'] = user_result
            
            if not user_result['success']:
                result['errors'].append(f"用户ID更新失败: {user_result.get('error', '未知错误')}")

        # 判断整体成功状态 -QW
        result['success'] = (result['device_id_result'].get('success', False) or 
                           result['user_id_result'].get('success', False))

        if result['success']:
            print(f"[JetBrains处理器] ✅ {ide_name} ID修改完成")
        else:
            print(f"[JetBrains处理器] ❌ {ide_name} ID修改失败")

        return result

    except Exception as e:
        error_msg = f"JetBrains ID修改过程中发生错误: {str(e)}"
        result['errors'].append(error_msg)
        print(f"[JetBrains处理器] ❌ {error_msg}")
        return result


def get_jetbrains_info() -> Dict[str, Any]:
    """
    获取JetBrains IDE信息 -QW

    Returns:
        Dict[str, Any]: JetBrains IDE信息
    """
    print("[JetBrains处理器] 获取JetBrains IDE信息...")
    
    result = {
        'success': False,
        'config_dir': '',
        'ides': [],
        'count': 0
    }

    try:
        # 获取配置目录 -QW
        jetbrains_dir = get_jetbrains_config_dir()
        result['config_dir'] = str(jetbrains_dir)

        if not jetbrains_dir.exists():
            result['message'] = f"JetBrains配置目录不存在: {jetbrains_dir}"
            return result

        # 扫描IDE目录 -QW
        ides = []
        for item in jetbrains_dir.iterdir():
            if item.is_dir():
                ide_info = {
                    'name': item.name,
                    'path': str(item),
                    'device_id_exists': (item / "PermanentDeviceId").exists(),
                    'user_id_exists': (item / "PermanentUserId").exists()
                }
                ides.append(ide_info)

        result['ides'] = ides
        result['count'] = len(ides)
        result['success'] = True
        result['message'] = f"找到 {len(ides)} 个JetBrains IDE配置"

        print(f"[JetBrains处理器] ✅ 找到 {len(ides)} 个JetBrains IDE")
        return result

    except Exception as e:
        result['message'] = f"获取JetBrains信息失败: {str(e)}"
        print(f"[JetBrains处理器] ❌ {result['message']}")
        return result


if __name__ == "__main__":
    # 测试JetBrains处理器 -QW
    print("=== JetBrains处理器测试 ===")
    
    # 获取JetBrains信息 -QW
    info = get_jetbrains_info()
    print(f"JetBrains信息: {info}")
    
    # 如果有IDE，测试修改ID -QW
    if info['success'] and info['ides']:
        first_ide = info['ides'][0]['name']
        result = modify_jetbrains_ids(first_ide)
        print(f"修改结果: {result}")
    
    print("=== 测试完成 ===")
