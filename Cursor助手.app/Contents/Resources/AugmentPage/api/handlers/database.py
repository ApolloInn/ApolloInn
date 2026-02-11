"""
AugmentPage 数据库处理器
支持跨平台（Windows、macOS、Linux）
此模块处理SQLite数据库的清理操作
-QW
"""

import sqlite3
import shutil
import time
import os
from ...utils.paths import get_db_path

def _create_backup(file_path: str) -> str:
    """
    创建指定文件的带时间戳备份

    Args:
        file_path (str): 要备份的文件路径

    Returns:
        str: 备份文件路径

    格式: <文件名>.bak.<时间戳>
    """
    timestamp = int(time.time())
    backup_path = f"{file_path}.bak.{timestamp}"
    shutil.copy2(file_path, backup_path)
    return backup_path

def clean_augment_data(editor_type: str = "VSCodium") -> dict:
    """
    从SQLite数据库中清理augment相关数据
    修改前会创建备份

    Args:
        editor_type (str): 编辑器类型，"VSCodium" 或 "Code" (VS Code)

    此函数执行以下操作:
    1. 获取SQLite数据库路径
    2. 创建数据库文件备份
    3. 打开数据库连接
    4. 删除键包含'augment'的记录

    Returns:
        dict: 包含操作结果的字典
        {
            'db_backup_path': str,  # 数据库备份路径
            'deleted_rows': int,    # 删除的行数
            'editor_type': str      # 编辑器类型
        }
    """
    db_path = get_db_path(editor_type)

    # 修改前创建备份
    db_backup_path = _create_backup(db_path)

    # 连接到数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 执行删除查询
        cursor.execute("DELETE FROM ItemTable WHERE key LIKE '%augment%'")
        deleted_rows = cursor.rowcount

        # 提交更改
        conn.commit()

        return {
            'db_backup_path': db_backup_path,
            'deleted_rows': deleted_rows,
            'editor_type': editor_type
        }
    finally:
        # 始终关闭连接
        cursor.close()
        conn.close()
