"""
AugmentPage 工作区处理器
支持跨平台（Windows、macOS、Linux）
此模块处理工作区存储的清理操作
-QW
"""

import os
import shutil
import time
import zipfile
import stat
import platform
from ...utils.paths import get_workspace_storage_path
from pathlib import Path


def remove_readonly(func, path, excinfo):
    """处理删除过程中的只读文件和目录 -QW"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        return False
    return True


def force_delete_directory(path: Path) -> bool:
    """
    强制删除目录及其所有内容 -QW
    成功返回True，否则返回False
    """
    try:
        if os.name == 'nt':
            # Windows系统，处理只读文件并使用长路径 -QW
            path_str = '\\\\?\\' + str(path.resolve())
            shutil.rmtree(path_str, onerror=remove_readonly)
        else:
            # macOS和Linux系统 -QW
            shutil.rmtree(path, onerror=remove_readonly)
        return True
    except Exception:
        return False


def clean_workspace_storage(editor_type: str = "Cursor") -> dict:
    """
    创建备份后清理工作区存储目录 -QW
    支持跨平台（Windows、macOS、Linux）

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    此函数执行以下操作:
    1. 获取工作区存储路径
    2. 创建目录中所有文件的zip备份
    3. 删除目录中的所有文件

    Returns:
        dict: 包含操作结果的字典
        {
            'backup_path': str,         # 备份路径
            'deleted_files_count': int, # 删除的文件数量
            'failed_operations': list,  # 失败的操作
            'failed_compressions': list,# 压缩失败的文件
            'editor_type': str          # 编辑器类型
        }
    """
    print(f"[工作区处理器] 开始清理 {editor_type} 工作区存储...")
    
    workspace_path = get_workspace_storage_path(editor_type)

    if not os.path.exists(workspace_path):
        error_msg = f"工作区存储目录未找到: {workspace_path}"
        print(f"[工作区处理器] ❌ {error_msg}")
        raise FileNotFoundError(error_msg)

    # 转换为Path对象以便更好地处理路径 -QW
    workspace_path = Path(workspace_path)

    # 创建带时间戳的备份文件名 -QW
    timestamp = int(time.time())
    backup_path = f"{workspace_path}_backup_{timestamp}.zip"

    # 创建zip备份 -QW
    failed_compressions = []
    print(f"[工作区处理器] 创建备份: {backup_path}")
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in workspace_path.rglob('*'):
            if file_path.is_file():
                try:
                    file_path_str = str(file_path)
                    if os.name == 'nt':
                        file_path_str = '\\\\?\\' + str(file_path.resolve())

                    arcname = file_path.relative_to(workspace_path)
                    zipf.write(file_path_str, str(arcname))
                except (OSError, PermissionError, zipfile.BadZipFile) as e:
                    failed_compressions.append({
                        'file': str(file_path),
                        'error': str(e)
                    })
                    continue

    # 删除前统计文件数量 -QW
    total_files = sum(1 for _ in workspace_path.rglob('*') if _.is_file())
    print(f"[工作区处理器] 准备删除 {total_files} 个文件")

    # 删除目录中的所有文件 -QW
    failed_operations = []

    def handle_error(e: Exception, path: Path, item_type: str):
        failed_operations.append({
            'type': item_type,
            'path': str(path),
            'error': str(e)
        })

    # 第一次尝试：尝试一次性删除整个目录树 -QW
    if not force_delete_directory(workspace_path):
        print("[工作区处理器] 批量删除失败，尝试逐个删除...")
        
        # 如果批量删除失败，尝试逐个文件删除的方法 -QW
        # 首先删除文件 -QW
        for file_path in workspace_path.rglob('*'):
            if file_path.is_file():
                try:
                    # 如果存在只读属性则清除 -QW
                    if os.name == 'nt':
                        file_path_str = '\\\\?\\' + str(file_path.resolve())
                        os.chmod(file_path_str, stat.S_IWRITE)
                    else:
                        os.chmod(str(file_path), stat.S_IWRITE)

                    file_path.unlink(missing_ok=True)
                except (OSError, PermissionError) as e:
                    handle_error(e, file_path, 'file')

        # 从最深层到根目录删除目录 -QW
        dirs_to_delete = sorted(
            [p for p in workspace_path.rglob('*') if p.is_dir()],
            key=lambda x: len(str(x).split(os.sep)),
            reverse=True
        )

        for dir_path in dirs_to_delete:
            try:
                # 首先尝试强制删除 -QW
                if not force_delete_directory(dir_path):
                    # 如果强制删除失败，尝试常规删除 -QW
                    if os.name == 'nt':
                        dir_path_str = '\\\\?\\' + str(dir_path.resolve())
                        os.rmdir(dir_path_str)
                    else:
                        dir_path.rmdir()
            except (OSError, PermissionError) as e:
                handle_error(e, dir_path, 'directory')

    print(f"[工作区处理器] ✅ {editor_type} 工作区清理完成")
    
    return {
        'backup_path': str(backup_path),
        'deleted_files_count': total_files,
        'failed_operations': failed_operations,
        'failed_compressions': failed_compressions,
        'editor_type': editor_type
    }


if __name__ == "__main__":
    # 测试工作区处理器 -QW
    print("=== 工作区处理器测试 ===")
    
    try:
        result = clean_workspace_storage("Cursor")
        print(f"清理结果: {result}")
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
    except Exception as e:
        print(f"清理失败: {e}")
    
    print("=== 测试完成 ===")
