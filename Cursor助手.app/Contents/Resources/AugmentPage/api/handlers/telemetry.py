"""
AugmentPage 遥测处理器
支持跨平台（Windows、macOS、Linux）
此模块处理遥测ID的修改操作
-QW
"""

import json
import os
import time
import shutil
from ...utils.paths import get_storage_path, get_machine_id_path
from ...utils.device_codes import generate_telemetry_ids

def _create_backup(file_path: str) -> str:
    """
    创建指定文件的带时间戳备份 -QW

    Args:
        file_path (str): 要备份的文件路径

    Returns:
        str: 备份文件路径

    格式: <文件名>.bak.<时间戳>
    """
    timestamp = int(time.time())
    backup_path = f"{file_path}.bak.{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"[遥测处理器] 创建备份: {backup_path}")
    return backup_path

def modify_telemetry_ids(editor_type: str = "Cursor") -> dict:
    """
    修改IDE storage.json文件和机器ID文件中的遥测ID -QW
    支持跨平台（Windows、macOS、Linux）
    修改前会创建备份

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    此函数执行以下操作:
    1. 创建storage.json和机器ID文件的备份
    2. 读取storage.json文件
    3. 生成新的完整遥测ID集合
    4. 更新storage.json中的所有遥测ID
    5. 用新的设备ID更新机器ID文件
    6. 保存修改后的文件

    Returns:
        dict: 包含新旧ID和备份信息的字典
        {
            'old_ids': dict,            # 旧ID集合
            'new_ids': dict,            # 新ID集合
            'storage_backup_path': str, # 存储文件备份路径
            'machine_id_backup_path': str, # 机器ID文件备份路径
            'editor_type': str          # 编辑器类型
        }
    """
    print(f"[遥测处理器] 开始修改 {editor_type} 遥测ID...")

    storage_path = get_storage_path(editor_type)
    machine_id_path = get_machine_id_path(editor_type)

    if not os.path.exists(storage_path):
        raise FileNotFoundError(f"存储文件未找到: {storage_path}")

    # 修改前创建备份 -QW
    storage_backup_path = _create_backup(storage_path)
    machine_id_backup_path = None
    if os.path.exists(machine_id_path):
        machine_id_backup_path = _create_backup(machine_id_path)

    # 读取当前JSON内容 -QW
    with open(storage_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 存储旧值 -QW
    old_ids = {}
    telemetry_keys = [
        'telemetry.machineId',
        'telemetry.devDeviceId',
        'telemetry.macMachineId',
        'telemetry.sqmId',
        'storage.serviceMachineId'
    ]

    for key in telemetry_keys:
        old_ids[key] = data.get(key, '')

    # 生成新的完整遥测ID集合 -QW
    new_ids = generate_telemetry_ids()

    # 更新storage.json中的所有遥测ID -QW
    data.update(new_ids)

    # 将修改后的内容写回storage.json -QW
    with open(storage_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    # 将新的设备ID写入机器ID文件 -QW
    os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
    with open(machine_id_path, 'w', encoding='utf-8') as f:
        f.write(new_ids['telemetry.devDeviceId'])

    print(f"[遥测处理器] ✅ {editor_type} 遥测ID修改完成")

    return {
        'old_ids': old_ids,
        'new_ids': new_ids,
        'storage_backup_path': storage_backup_path,
        'machine_id_backup_path': machine_id_backup_path,
        'editor_type': editor_type
    }
