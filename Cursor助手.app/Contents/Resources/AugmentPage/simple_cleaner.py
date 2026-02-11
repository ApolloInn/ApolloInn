"""
简单的清理器，不依赖webview
用于清理IDE的配置数据和遥测信息
支持VSCode系列和JetBrains系列IDE
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
import json
import sqlite3
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List


class SimpleCleaner:
    """简单的清理器类 -QW"""
    
    def __init__(self):
        self.backup_dir = None
        self.setup_backup_dir()
    
    def setup_backup_dir(self):
        """设置备份目录 -QW"""
        try:
            current_dir = Path(__file__).parent
            self.backup_dir = current_dir / "backups"
            self.backup_dir.mkdir(exist_ok=True)
            print(f"[简单清理器] ✅ 备份目录设置完成: {self.backup_dir}")
        except Exception as e:
            print(f"[简单清理器] ⚠️ 备份目录设置失败: {str(e)}")
    
    def cleanup_ide(self, ide_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理IDE数据 -QW"""
        results = {
            "success": True,
            "message": "清理完成",
            "data": {
                "editor": ide_data,
                "operations": {},
                "errors": []
            }
        }
        
        try:
            ide_type = ide_data.get("ide_type", "vscode")
            ide_name = ide_data.get("name", "Unknown")
            
            print(f"[简单清理器] 🧹 开始清理 {ide_name} ({ide_type})")

            if ide_type == "vscode":
                results = self._cleanup_vscode(ide_data, results)
            elif ide_type == "jetbrains":
                results = self._cleanup_jetbrains(ide_data, results)
            else:
                # 默认按VSCode处理 -QW
                results = self._cleanup_vscode(ide_data, results)

            # 检查是否有错误 -QW
            if results["data"]["errors"]:
                results["success"] = False
                results["message"] = "部分操作失败"
                print(f"[简单清理器] ⚠️ 清理完成，但有 {len(results['data']['errors'])} 个错误")
            else:
                print(f"[简单清理器] ✅ 清理完成，所有操作成功")
            
            return results
            
        except Exception as e:
            error_msg = f"清理失败: {str(e)}"
            print(f"[简单清理器] ❌ {error_msg}")
            results["success"] = False
            results["message"] = error_msg
            results["data"]["errors"].append(str(e))
            return results
    
    def _cleanup_vscode(self, ide_data: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """清理VSCode系列IDE -QW"""
        ide_name = ide_data.get("name", "Code")
        
        # 1. 重置遥测数据 -QW
        print(f"[简单清理器] 🔄 重置 {ide_name} 遥测数据...")
        telemetry_result = self._reset_vscode_telemetry(ide_name)
        results["data"]["operations"]["telemetry"] = telemetry_result
        if not telemetry_result.get("success", False):
            results["data"]["errors"].extend(telemetry_result.get("errors", []))
        
        # 2. 清理数据库 -QW
        print(f"[简单清理器] 🗄️ 清理 {ide_name} 数据库...")
        database_result = self._clean_vscode_database(ide_name)
        results["data"]["operations"]["database"] = database_result
        if not database_result.get("success", False):
            results["data"]["errors"].extend(database_result.get("errors", []))
        
        # 3. 清理工作区 -QW
        print(f"[简单清理器] 📁 清理 {ide_name} 工作区...")
        workspace_result = self._clean_vscode_workspace(ide_name)
        results["data"]["operations"]["workspace"] = workspace_result
        if not workspace_result.get("success", False):
            results["data"]["errors"].extend(workspace_result.get("errors", []))
        
        return results
    
    def _cleanup_jetbrains(self, ide_data: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """清理JetBrains系列IDE -QW"""
        print("[简单清理器] 🔄 重置JetBrains ID...")
        jetbrains_result = self._reset_jetbrains_ids()
        results["data"]["operations"]["jetbrains"] = jetbrains_result
        if not jetbrains_result.get("success", False):
            results["data"]["errors"].extend(jetbrains_result.get("errors", []))
        
        return results
    
    def _reset_vscode_telemetry(self, ide_name: str) -> Dict[str, Any]:
        """重置VSCode遥测数据 -QW"""
        try:
            # 获取VSCode配置目录 -QW
            config_paths = self._get_vscode_config_paths(ide_name)
            
            modified_files = []
            errors = []
            
            for config_path in config_paths:
                if not config_path.exists():
                    continue
                
                # 处理storage.json -QW
                storage_file = config_path / "User" / "globalStorage" / "storage.json"
                if storage_file.exists():
                    try:
                        self._backup_file(storage_file)
                        self._modify_storage_json(storage_file)
                        modified_files.append(str(storage_file))
                        print(f"[简单清理器] ✅ 已修改: {storage_file}")
                    except Exception as e:
                        errors.append(f"修改storage.json失败: {str(e)}")
                
                # 处理machineId文件 -QW
                machine_id_file = config_path / "machineid"
                if machine_id_file.exists():
                    try:
                        self._backup_file(machine_id_file)
                        self._modify_machine_id(machine_id_file)
                        modified_files.append(str(machine_id_file))
                        print(f"[简单清理器] ✅ 已修改: {machine_id_file}")
                    except Exception as e:
                        errors.append(f"修改machineId失败: {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "message": f"遥测数据重置完成，修改了 {len(modified_files)} 个文件",
                "modified_files": modified_files,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"遥测重置失败: {str(e)}",
                "modified_files": [],
                "errors": [str(e)]
            }
    
    def _clean_vscode_database(self, ide_name: str) -> Dict[str, Any]:
        """清理VSCode数据库 -QW"""
        try:
            config_paths = self._get_vscode_config_paths(ide_name)
            
            deleted_rows = 0
            errors = []
            
            for config_path in config_paths:
                if not config_path.exists():
                    continue
                
                # 查找数据库文件 -QW
                db_pattern = config_path / "User" / "globalStorage" / "state.vscdb"
                if db_pattern.exists():
                    try:
                        self._backup_file(db_pattern)
                        rows = self._clean_sqlite_database(db_pattern)
                        deleted_rows += rows
                        print(f"[简单清理器] ✅ 数据库清理完成: {db_pattern}, 删除 {rows} 条记录")
                    except Exception as e:
                        errors.append(f"清理数据库失败: {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "message": f"数据库清理完成，删除了 {deleted_rows} 条记录",
                "deleted_rows": deleted_rows,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"数据库清理失败: {str(e)}",
                "deleted_rows": 0,
                "errors": [str(e)]
            }
    
    def _clean_vscode_workspace(self, ide_name: str) -> Dict[str, Any]:
        """清理VSCode工作区 -QW"""
        try:
            config_paths = self._get_vscode_config_paths(ide_name)
            
            deleted_files = 0
            errors = []
            
            for config_path in config_paths:
                if not config_path.exists():
                    continue
                
                # 清理工作区存储 -QW
                workspace_storage = config_path / "User" / "workspaceStorage"
                if workspace_storage.exists():
                    try:
                        for item in workspace_storage.iterdir():
                            if item.is_dir():
                                # 检查是否包含augment相关文件 -QW
                                if self._contains_augment_data(item):
                                    shutil.rmtree(item)
                                    deleted_files += 1
                                    print(f"[简单清理器] ✅ 删除工作区目录: {item}")
                    except Exception as e:
                        errors.append(f"清理工作区失败: {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "message": f"工作区清理完成，删除了 {deleted_files} 个目录",
                "deleted_files": deleted_files,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"工作区清理失败: {str(e)}",
                "deleted_files": 0,
                "errors": [str(e)]
            }
    
    def _reset_jetbrains_ids(self) -> Dict[str, Any]:
        """重置JetBrains ID -QW"""
        try:
            # 获取JetBrains配置目录 -QW
            jetbrains_dirs = self._get_jetbrains_config_dirs()
            
            modified_files = []
            errors = []
            
            for jetbrains_dir in jetbrains_dirs:
                if not jetbrains_dir.exists():
                    continue
                
                # 重置PermanentDeviceId -QW
                device_id_file = jetbrains_dir / "PermanentDeviceId"
                if device_id_file.exists():
                    try:
                        self._backup_file(device_id_file)
                        device_id_file.write_text(str(uuid.uuid4()))
                        modified_files.append(str(device_id_file))
                        print(f"[简单清理器] ✅ 重置设备ID: {device_id_file}")
                    except Exception as e:
                        errors.append(f"重置设备ID失败: {str(e)}")
                
                # 重置PermanentUserId -QW
                user_id_file = jetbrains_dir / "PermanentUserId"
                if user_id_file.exists():
                    try:
                        self._backup_file(user_id_file)
                        user_id_file.write_text(str(uuid.uuid4()))
                        modified_files.append(str(user_id_file))
                        print(f"[简单清理器] ✅ 重置用户ID: {user_id_file}")
                    except Exception as e:
                        errors.append(f"重置用户ID失败: {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "message": f"JetBrains ID重置完成，修改了 {len(modified_files)} 个文件",
                "modified_files": modified_files,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"JetBrains ID重置失败: {str(e)}",
                "modified_files": [],
                "errors": [str(e)]
            }

    def _get_vscode_config_paths(self, ide_name: str) -> List[Path]:
        """获取VSCode配置路径 -QW"""
        paths = []

        if sys.platform == "win32":
            if appdata := os.getenv("APPDATA"):
                base_path = Path(appdata)
                paths.extend([
                    base_path / ide_name,
                    base_path / ide_name.lower(),
                    base_path / f"{ide_name} - Insiders"
                ])
        elif sys.platform == "darwin":
            home = Path.home()
            base_path = home / "Library" / "Application Support"
            paths.extend([
                base_path / ide_name,
                base_path / ide_name.lower()
            ])
        else:
            home = Path.home()
            base_path = home / ".config"
            paths.extend([
                base_path / ide_name,
                base_path / ide_name.lower()
            ])

        return [p for p in paths if p.exists()]

    def _get_jetbrains_config_dirs(self) -> List[Path]:
        """获取JetBrains配置目录 -QW"""
        paths = []

        if sys.platform == "win32":
            if appdata := os.getenv("APPDATA"):
                jetbrains_path = Path(appdata) / "JetBrains"
                if jetbrains_path.exists():
                    paths.extend([d for d in jetbrains_path.iterdir() if d.is_dir()])
        elif sys.platform == "darwin":
            home = Path.home()
            jetbrains_path = home / "Library" / "Application Support" / "JetBrains"
            if jetbrains_path.exists():
                paths.extend([d for d in jetbrains_path.iterdir() if d.is_dir()])
        else:
            home = Path.home()
            jetbrains_path = home / ".config" / "JetBrains"
            if jetbrains_path.exists():
                paths.extend([d for d in jetbrains_path.iterdir() if d.is_dir()])

        return paths

    def _backup_file(self, file_path: Path):
        """备份文件 -QW"""
        if not self.backup_dir:
            return

        try:
            import time
            timestamp = int(time.time())
            backup_name = f"{file_path.name}.{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            shutil.copy2(file_path, backup_path)
            print(f"[简单清理器] 💾 备份文件: {backup_path}")
        except Exception as e:
            print(f"[简单清理器] ⚠️ 备份文件失败: {str(e)}")

    def _modify_storage_json(self, storage_file: Path):
        """修改storage.json文件 -QW"""
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 生成新的ID -QW
            new_machine_id = str(uuid.uuid4())
            new_device_id = str(uuid.uuid4())
            new_mac_machine_id = str(uuid.uuid4())
            new_sqm_id = f"{{{str(uuid.uuid4()).upper()}}}"

            # 修改遥测ID -QW
            if 'telemetry.machineId' in data:
                data['telemetry.machineId'] = new_machine_id
            if 'telemetry.devDeviceId' in data:
                data['telemetry.devDeviceId'] = new_device_id
            if 'telemetry.macMachineId' in data:
                data['telemetry.macMachineId'] = new_mac_machine_id
            if 'telemetry.sqmId' in data:
                data['telemetry.sqmId'] = new_sqm_id

            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            raise Exception(f"修改storage.json失败: {str(e)}")

    def _modify_machine_id(self, machine_id_file: Path):
        """修改machineId文件 -QW"""
        try:
            new_machine_id = str(uuid.uuid4())
            machine_id_file.write_text(new_machine_id)
        except Exception as e:
            raise Exception(f"修改machineId失败: {str(e)}")

    def _clean_sqlite_database(self, db_file: Path) -> int:
        """清理SQLite数据库 -QW"""
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # 查找包含augment的记录 -QW
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            total_deleted = 0
            for table in tables:
                table_name = table[0]
                try:
                    # 删除包含augment的记录 -QW
                    cursor.execute(f"DELETE FROM {table_name} WHERE key LIKE '%augment%' OR value LIKE '%augment%'")
                    deleted = cursor.rowcount
                    total_deleted += deleted
                except sqlite3.Error:
                    continue

            conn.commit()
            conn.close()

            return total_deleted

        except Exception as e:
            raise Exception(f"清理数据库失败: {str(e)}")

    def _contains_augment_data(self, directory: Path) -> bool:
        """检查目录是否包含augment相关数据 -QW"""
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    try:
                        if "augment" in item.name.lower():
                            return True
                        if item.suffix in ['.json', '.txt']:
                            content = item.read_text(encoding='utf-8', errors='ignore')
                            if "augment" in content.lower():
                                return True
                    except:
                        continue
            return False
        except:
            return False


# 创建全局清理器实例 -QW
_cleaner_instance = None

def get_simple_cleaner() -> SimpleCleaner:
    """获取简单清理器实例（单例模式） -QW"""
    global _cleaner_instance
    if _cleaner_instance is None:
        _cleaner_instance = SimpleCleaner()
    return _cleaner_instance


def simple_cleanup_ide(ide_data: Dict[str, Any]) -> Dict[str, Any]:
    """简单清理IDE的便捷函数 -QW"""
    cleaner = get_simple_cleaner()
    return cleaner.cleanup_ide(ide_data)


if __name__ == "__main__":
    # 测试简单清理器 -QW
    print("=== 简单清理器测试 ===")

    test_ide = {
        "name": "Cursor",
        "display_name": "Cursor",
        "ide_type": "vscode",
        "config_path": "",
        "icon": "🎯"
    }

    result = simple_cleanup_ide(test_ide)

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    if result['data']['operations']:
        print("\n执行的操作:")
        for op_name, op_result in result['data']['operations'].items():
            status = "✅" if op_result.get('success', False) else "❌"
            print(f"  {status} {op_name}: {op_result.get('message', 'No message')}")

    if result['data']['errors']:
        print(f"\n错误: {len(result['data']['errors'])} 个")
        for error in result['data']['errors']:
            print(f"  • {error}")

    print("\n=== 测试完成 ===")
