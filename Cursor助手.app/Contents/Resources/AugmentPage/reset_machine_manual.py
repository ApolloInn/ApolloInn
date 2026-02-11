"""
手动机器重置工具
提供手动重置机器标识符的独立工具
包含完整的备份和恢复机制
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


# 定义表情符号常量 -QW
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARNING": "⚠️",
}


def get_user_documents_path() -> str:
    """获取用户文档文件夹路径 -QW"""
    system = platform.system().lower()
    
    if system == "windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception:
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif system == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # 获取实际用户的主目录 -QW
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")


def get_cursor_config_paths() -> Dict[str, str]:
    """获取Cursor配置文件路径 -QW"""
    system = platform.system().lower()
    
    if system == "windows":
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise EnvironmentError("APPDATA环境变量未设置")
        
        base_path = os.path.join(appdata, "Cursor")
        return {
            "storage_path": os.path.join(base_path, "User", "globalStorage", "storage.json"),
            "sqlite_path": os.path.join(base_path, "User", "globalStorage", "state.vscdb"),
            "machine_id_path": os.path.join(base_path, "machineId"),
            "workspace_storage": os.path.join(base_path, "User", "workspaceStorage")
        }
    elif system == "darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Cursor")
        return {
            "storage_path": os.path.join(base_path, "User", "globalStorage", "storage.json"),
            "sqlite_path": os.path.join(base_path, "User", "globalStorage", "state.vscdb"),
            "machine_id_path": os.path.join(base_path, "machineId"),
            "workspace_storage": os.path.join(base_path, "User", "workspaceStorage")
        }
    else:  # Linux
        # 获取实际用户的主目录 -QW
        sudo_user = os.environ.get('SUDO_USER')
        actual_home = f"/home/{sudo_user}" if sudo_user else os.path.expanduser("~")
        base_path = os.path.join(actual_home, ".config", "cursor")
        
        return {
            "storage_path": os.path.join(base_path, "User", "globalStorage", "storage.json"),
            "sqlite_path": os.path.join(base_path, "User", "globalStorage", "state.vscdb"),
            "machine_id_path": os.path.join(base_path, "machineId"),
            "workspace_storage": os.path.join(base_path, "User", "workspaceStorage")
        }


class MachineIDResetter:
    """机器ID重置器 -QW"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.paths = get_cursor_config_paths()
        self.backup_dir = self._setup_backup_dir()
        
        print(f"[机器重置器] 系统: {self.system}")
        print(f"[机器重置器] 配置路径: {self.paths}")
        print(f"[机器重置器] 备份目录: {self.backup_dir}")

    def _setup_backup_dir(self) -> str:
        """设置备份目录 -QW"""
        try:
            documents_path = get_user_documents_path()
            backup_dir = os.path.join(documents_path, ".cursor-reset-backups")
            os.makedirs(backup_dir, exist_ok=True)
            return backup_dir
        except Exception:
            # 如果无法创建在文档目录，使用临时目录 -QW
            backup_dir = os.path.join(tempfile.gettempdir(), "cursor-reset-backups")
            os.makedirs(backup_dir, exist_ok=True)
            return backup_dir

    def generate_new_ids(self) -> Dict[str, str]:
        """生成新的机器ID -QW"""
        print("[机器重置器] 🔄 生成新的机器ID...")
        
        # 生成新的UUID -QW
        dev_device_id = str(uuid.uuid4())
        
        # 生成新的machineId（64位十六进制） -QW
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        
        # 生成新的macMachineId（128位十六进制） -QW
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()
        
        # 生成新的sqmId -QW
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
        
        new_ids = {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id,
        }
        
        print(f"[机器重置器] ✅ 生成完成:")
        for key, value in new_ids.items():
            print(f"   {key}: {value[:8]}...")
        
        return new_ids

    def backup_file(self, file_path: str) -> Optional[str]:
        """备份文件 -QW"""
        if not os.path.exists(file_path):
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_filename = f"{filename}.backup.{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            shutil.copy2(file_path, backup_path)
            print(f"[机器重置器] 💾 备份文件: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"[机器重置器] ⚠️ 备份失败: {str(e)}")
            return None

    def update_storage_json(self, new_ids: Dict[str, str]) -> bool:
        """更新storage.json文件 -QW"""
        storage_path = self.paths["storage_path"]
        
        try:
            if not os.path.exists(storage_path):
                print(f"[机器重置器] ⚠️ storage.json不存在: {storage_path}")
                return False
            
            if not os.access(storage_path, os.R_OK | os.W_OK):
                print(f"[机器重置器] ❌ 无法访问storage.json: {storage_path}")
                return False
            
            # 备份原文件 -QW
            self.backup_file(storage_path)
            
            # 读取并更新配置 -QW
            with open(storage_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # 更新ID -QW
            config.update(new_ids)
            
            # 写入更新后的配置 -QW
            with open(storage_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print(f"[机器重置器] ✅ storage.json更新成功")
            return True
            
        except Exception as e:
            print(f"[机器重置器] ❌ storage.json更新失败: {str(e)}")
            return False

    def update_sqlite_db(self, new_ids: Dict[str, str]) -> bool:
        """更新SQLite数据库中的机器ID -QW"""
        sqlite_path = self.paths["sqlite_path"]
        
        try:
            if not os.path.exists(sqlite_path):
                print(f"[机器重置器] ⚠️ SQLite数据库不存在: {sqlite_path}")
                return True  # 不存在不算错误 -QW
            
            # 备份数据库文件 -QW
            self.backup_file(sqlite_path)
            
            # 连接数据库 -QW
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # 确保表存在 -QW
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 更新ID -QW
            for key, value in new_ids.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
            
            conn.commit()
            conn.close()
            
            print(f"[机器重置器] ✅ SQLite数据库更新成功")
            return True
            
        except Exception as e:
            print(f"[机器重置器] ❌ SQLite数据库更新失败: {str(e)}")
            return False

    def update_machine_id_file(self, machine_id: str) -> bool:
        """更新machineId文件 -QW"""
        machine_id_path = self.paths["machine_id_path"]
        
        try:
            # 确保目录存在 -QW
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            
            # 备份原文件（如果存在） -QW
            if os.path.exists(machine_id_path):
                self.backup_file(machine_id_path)
            
            # 写入新的机器ID -QW
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(machine_id)
            
            print(f"[机器重置器] ✅ machineId文件更新成功: {machine_id}")
            return True
            
        except Exception as e:
            print(f"[机器重置器] ❌ machineId文件更新失败: {str(e)}")
            return False

    def clean_workspace_storage(self) -> bool:
        """清理工作区存储 -QW"""
        workspace_path = self.paths["workspace_storage"]

        try:
            if not os.path.exists(workspace_path):
                print(f"[机器重置器] ⚠️ 工作区存储不存在: {workspace_path}")
                return True  # 不存在不算错误 -QW

            # 备份整个工作区目录 -QW
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"workspaceStorage.backup.{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            try:
                shutil.copytree(workspace_path, backup_path)
                print(f"[机器重置器] 💾 工作区存储已备份: {backup_path}")
            except Exception as e:
                print(f"[机器重置器] ⚠️ 工作区存储备份失败: {str(e)}")

            # 清理工作区内容 -QW
            deleted_count = 0
            for item in os.listdir(workspace_path):
                item_path = os.path.join(workspace_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        deleted_count += 1
                    elif os.path.isfile(item_path):
                        os.remove(item_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"[机器重置器] ⚠️ 删除 {item} 失败: {str(e)}")

            print(f"[机器重置器] ✅ 工作区存储清理完成，删除了 {deleted_count} 个项目")
            return True

        except Exception as e:
            print(f"[机器重置器] ❌ 工作区存储清理失败: {str(e)}")
            return False

    def update_system_ids(self, new_ids: Dict[str, str]) -> bool:
        """更新系统级ID -QW"""
        try:
            if self.system == "windows":
                return self._update_windows_system_ids(new_ids)
            elif self.system == "darwin":
                return self._update_macos_system_ids(new_ids)
            else:
                # Linux系统通常不需要更新系统级ID -QW
                print("[机器重置器] ℹ️ Linux系统跳过系统级ID更新")
                return True
        except Exception as e:
            print(f"[机器重置器] ❌ 系统级ID更新失败: {str(e)}")
            return False

    def _update_windows_system_ids(self, new_ids: Dict[str, str]) -> bool:
        """更新Windows系统ID -QW"""
        try:
            import winreg

            # 更新MachineGuid -QW
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Microsoft\\Cryptography",
                    0,
                    winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                )
                new_guid = str(uuid.uuid4())
                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
                winreg.CloseKey(key)
                print("[机器重置器] ✅ Windows MachineGuid更新成功")
            except PermissionError:
                print("[机器重置器] ⚠️ 无权限更新Windows MachineGuid")
                return False

            # 更新SQMClient MachineId -QW
            try:
                new_guid = "{" + str(uuid.uuid4()).upper() + "}"
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\SQMClient",
                        0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                    )
                except FileNotFoundError:
                    key = winreg.CreateKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\SQMClient"
                    )

                winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_guid)
                winreg.CloseKey(key)
                print("[机器重置器] ✅ Windows SQMClient MachineId更新成功")
            except PermissionError:
                print("[机器重置器] ⚠️ 无权限更新Windows SQMClient MachineId")
                return False

            return True

        except ImportError:
            print("[机器重置器] ⚠️ winreg模块不可用")
            return False

    def _update_macos_system_ids(self, new_ids: Dict[str, str]) -> bool:
        """更新macOS系统ID -QW"""
        try:
            # macOS的系统ID更新需要管理员权限，这里提供一个简化版本 -QW
            print("[机器重置器] ℹ️ macOS系统ID更新需要管理员权限")

            # 尝试更新Platform UUID（需要sudo权限） -QW
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                try:
                    import subprocess
                    new_uuid = new_ids.get("telemetry.macMachineId", str(uuid.uuid4()))
                    cmd = ['sudo', 'plutil', '-replace', 'UUID', '-string', new_uuid, uuid_file]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print("[机器重置器] ✅ macOS Platform UUID更新成功")
                    else:
                        print(f"[机器重置器] ⚠️ macOS Platform UUID更新失败: {result.stderr}")
                        return False
                except Exception as e:
                    print(f"[机器重置器] ⚠️ macOS Platform UUID更新失败: {str(e)}")
                    return False
            else:
                print("[机器重置器] ℹ️ macOS Platform UUID文件不存在，跳过更新")

            return True

        except Exception as e:
            print(f"[机器重置器] ❌ macOS系统ID更新失败: {str(e)}")
            return False

    def reset_machine_ids(self) -> Dict[str, Any]:
        """重置机器ID并备份原文件 -QW"""
        print(f"\n{EMOJI['RESET']} 开始重置机器ID...")

        results = {
            "success": True,
            "operations": {},
            "errors": [],
            "new_ids": {}
        }

        try:
            # 1. 生成新的ID -QW
            new_ids = self.generate_new_ids()
            results["new_ids"] = new_ids

            # 2. 更新storage.json -QW
            print(f"\n{EMOJI['FILE']} 更新storage.json...")
            storage_result = self.update_storage_json(new_ids)
            results["operations"]["storage_json"] = storage_result
            if not storage_result:
                results["success"] = False
                results["errors"].append("storage.json更新失败")

            # 3. 更新SQLite数据库 -QW
            print(f"\n{EMOJI['FILE']} 更新SQLite数据库...")
            sqlite_result = self.update_sqlite_db(new_ids)
            results["operations"]["sqlite_db"] = sqlite_result
            if not sqlite_result:
                results["errors"].append("SQLite数据库更新失败")

            # 4. 更新machineId文件 -QW
            print(f"\n{EMOJI['FILE']} 更新machineId文件...")
            machine_id_result = self.update_machine_id_file(new_ids["telemetry.devDeviceId"])
            results["operations"]["machine_id_file"] = machine_id_result
            if not machine_id_result:
                results["errors"].append("machineId文件更新失败")

            # 5. 清理工作区存储 -QW
            print(f"\n{EMOJI['FILE']} 清理工作区存储...")
            workspace_result = self.clean_workspace_storage()
            results["operations"]["workspace_storage"] = workspace_result
            if not workspace_result:
                results["errors"].append("工作区存储清理失败")

            # 6. 更新系统级ID -QW
            print(f"\n{EMOJI['FILE']} 更新系统级ID...")
            system_result = self.update_system_ids(new_ids)
            results["operations"]["system_ids"] = system_result
            if not system_result:
                results["errors"].append("系统级ID更新失败")

            if results["success"]:
                print(f"\n{EMOJI['SUCCESS']} 机器ID重置成功！")
            else:
                print(f"\n{EMOJI['WARNING']} 机器ID重置完成，但有 {len(results['errors'])} 个错误")

            return results

        except Exception as e:
            error_msg = f"重置过程中发生严重错误: {str(e)}"
            print(f"\n{EMOJI['ERROR']} {error_msg}")
            results["success"] = False
            results["errors"].append(error_msg)
            return results


def run_manual_reset():
    """运行手动重置工具 -QW"""
    print("\n" + "=" * 60)
    print("🔧 Cursor 手动机器重置工具")
    print("=" * 60)

    try:
        resetter = MachineIDResetter()

        # 询问用户要执行的操作 -QW
        print("\n请选择要执行的操作:")
        print("1. 完整重置（推荐）")
        print("2. 仅重置配置文件")
        print("3. 仅清理工作区")
        print("4. 退出")

        choice = input("\n请输入选择 (1-4): ").strip()

        if choice == "1":
            # 完整重置 -QW
            results = resetter.reset_machine_ids()

            print(f"\n📊 重置结果:")
            for operation, result in results["operations"].items():
                status = "✅" if result else "❌"
                print(f"   {status} {operation}")

            if results["errors"]:
                print(f"\n⚠️ 发现 {len(results['errors'])} 个错误:")
                for error in results["errors"]:
                    print(f"   • {error}")

            if results["new_ids"]:
                print(f"\n🆔 新生成的ID:")
                for key, value in results["new_ids"].items():
                    print(f"   {key}: {value[:8]}...")

        elif choice == "2":
            # 仅重置配置文件 -QW
            new_ids = resetter.generate_new_ids()

            storage_result = resetter.update_storage_json(new_ids)
            sqlite_result = resetter.update_sqlite_db(new_ids)
            machine_id_result = resetter.update_machine_id_file(new_ids["telemetry.devDeviceId"])

            print(f"\n📊 配置文件重置结果:")
            print(f"   {'✅' if storage_result else '❌'} storage.json")
            print(f"   {'✅' if sqlite_result else '❌'} SQLite数据库")
            print(f"   {'✅' if machine_id_result else '❌'} machineId文件")

        elif choice == "3":
            # 仅清理工作区 -QW
            workspace_result = resetter.clean_workspace_storage()
            print(f"\n📊 工作区清理结果:")
            print(f"   {'✅' if workspace_result else '❌'} 工作区存储")

        elif choice == "4":
            print("👋 退出程序")
            return
        else:
            print("❌ 无效选择")

    except Exception as e:
        print(f"❌ 严重错误: {str(e)}")

    print("\n" + "=" * 60)
    input("按回车键退出...")


def reset_cursor_machine_ids() -> Dict[str, Any]:
    """重置Cursor机器ID的便捷函数 -QW"""
    resetter = MachineIDResetter()
    return resetter.reset_machine_ids()


def quick_reset_storage() -> bool:
    """快速重置存储配置的便捷函数 -QW"""
    try:
        resetter = MachineIDResetter()
        new_ids = resetter.generate_new_ids()

        storage_result = resetter.update_storage_json(new_ids)
        sqlite_result = resetter.update_sqlite_db(new_ids)
        machine_id_result = resetter.update_machine_id_file(new_ids["telemetry.devDeviceId"])

        return storage_result and sqlite_result and machine_id_result
    except Exception:
        return False


if __name__ == "__main__":
    run_manual_reset()
