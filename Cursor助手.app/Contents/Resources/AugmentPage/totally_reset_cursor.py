"""
完全重置Cursor工具
用于彻底重置Cursor的所有配置和数据
支持跨平台（Windows、macOS、Linux）
包含权限管理和提权功能
-QW
"""

import json
import os
import shutil
import sys
import uuid
import platform
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


def is_admin() -> bool:
    """检查管理员权限 -QW"""
    system = platform.system().lower()
    
    try:
        if system == "windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        elif system == "darwin":
            # macOS: 检查是否为root用户或在admin组中 -QW
            return os.getuid() == 0 or _is_in_admin_group()
        else:
            # Linux: 检查是否为root用户 -QW
            return os.getuid() == 0
    except Exception:
        return False


def _is_in_admin_group() -> bool:
    """检查用户是否在admin组中（macOS） -QW"""
    try:
        import grp
        admin_group = grp.getgrnam('admin')
        return os.getuid() in admin_group.gr_mem or os.getlogin() in admin_group.gr_mem
    except Exception:
        return False


def elevate_privileges():
    """请求提权 -QW"""
    system = platform.system().lower()
    
    try:
        if system == "windows":
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
        elif system == "darwin":
            # macOS: 使用osascript请求管理员权限 -QW
            script = f'''
            do shell script "'{sys.executable}' {' '.join(sys.argv)}" with administrator privileges
            '''
            subprocess.run(['osascript', '-e', script])
            sys.exit(0)
        else:
            # Linux: 使用sudo -QW
            subprocess.run(['sudo', sys.executable] + sys.argv)
            sys.exit(0)
    except Exception as e:
        print(f"❌ 提权失败: {str(e)}")
        sys.exit(1)


class FilePermissionManager:
    """文件权限管理器 -QW"""
    
    def __init__(self, path: str):
        self.path = path
        self.original_permissions = None
        self.system = platform.system().lower()

    def __enter__(self):
        if self.system == "windows":
            return self._enter_windows()
        else:
            return self._enter_unix()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.system == "windows":
            self._exit_windows(exc_type, exc_val, exc_tb)
        else:
            self._exit_unix(exc_type, exc_val, exc_tb)

    def _enter_windows(self):
        """Windows权限管理 -QW"""
        try:
            import win32security
            import win32con
            import win32api
            
            if not is_admin():
                raise PermissionError("需要管理员权限")

            # 获取原始安全描述符 -QW
            self.original_sd = win32security.GetFileSecurity(
                self.path,
                win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
            )
            
            # 设置当前用户为所有者并给完整控制 -QW
            user_sid = win32security.LookupAccountName(None, win32api.GetUserName())[0]
            sd = self.original_sd
            sd.SetSecurityDescriptorOwner(user_sid, False)
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION,
                                     win32con.GENERIC_ALL,
                                     user_sid)
            sd.SetSecurityDescriptorDacl(True, dacl, False)
            win32security.SetFileSecurity(
                self.path,
                win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION,
                sd
            )
            return self
        except ImportError:
            print("⚠️ Windows权限模块不可用，使用基本权限管理")
            return self

    def _enter_unix(self):
        """Unix/macOS权限管理 -QW"""
        try:
            # 保存原始权限 -QW
            stat_info = os.stat(self.path)
            self.original_permissions = stat_info.st_mode
            
            # 设置读写权限 -QW
            os.chmod(self.path, 0o755)
            return self
        except Exception as e:
            print(f"⚠️ 权限设置失败: {str(e)}")
            return self

    def _exit_windows(self, exc_type, exc_val, exc_tb):
        """恢复Windows权限 -QW"""
        try:
            if hasattr(self, 'original_sd') and self.original_sd:
                import win32security
                win32security.SetFileSecurity(
                    self.path,
                    win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION,
                    self.original_sd
                )
        except Exception:
            pass

    def _exit_unix(self, exc_type, exc_val, exc_tb):
        """恢复Unix/macOS权限 -QW"""
        try:
            if self.original_permissions is not None:
                os.chmod(self.path, self.original_permissions)
        except Exception:
            pass


class CursorIDResetter:
    """Cursor ID重置器 -QW"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.db_path = self._get_cursor_config_path()
        self.temp_dir = tempfile.gettempdir()
        print(f"[Cursor重置器] 系统: {self.system}")
        print(f"[Cursor重置器] 配置路径: {self.db_path}")

    def _get_cursor_config_path(self) -> str:
        """获取Cursor配置文件路径 -QW"""
        if self.system == "windows":
            return os.path.expanduser(
                "~\\AppData\\Roaming\\Cursor\\User\\globalStorage\\storage.json"
            )
        elif self.system == "darwin":
            return os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
            )
        else:
            return os.path.expanduser(
                "~/.config/Cursor/User/globalStorage/storage.json"
            )

    def safe_file_update(self) -> Dict[str, Any]:
        """安全地更新文件 -QW"""
        temp_path = None
        result = {
            "success": False,
            "message": "",
            "old_machine_id": None,
            "new_machine_id": None
        }
        
        try:
            # 检查源文件是否存在 -QW
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"找不到Cursor配置文件: {self.db_path}")

            # 检查源文件是否可访问 -QW
            if not os.access(self.db_path, os.R_OK):
                raise PermissionError(f"无法读取Cursor配置文件: {self.db_path}")

            # 读取源文件内容 -QW
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 保存旧的机器ID -QW
            result["old_machine_id"] = data.get("machineId", "未知")
            
            # 生成新的机器ID -QW
            new_machine_id = str(uuid.uuid4())
            data["machineId"] = new_machine_id
            result["new_machine_id"] = new_machine_id
            
            # 同时重置其他相关ID -QW
            if "telemetry.machineId" in data:
                data["telemetry.machineId"] = str(uuid.uuid4())
            if "telemetry.devDeviceId" in data:
                data["telemetry.devDeviceId"] = str(uuid.uuid4())
            if "telemetry.macMachineId" in data:
                data["telemetry.macMachineId"] = str(uuid.uuid4())
            if "telemetry.sqmId" in data:
                data["telemetry.sqmId"] = f"{{{str(uuid.uuid4()).upper()}}}"
            
            new_content = json.dumps(data, indent=2, ensure_ascii=False)

            # 创建临时文件 -QW
            temp_path = os.path.join(self.temp_dir, f"cursor_reset_{uuid.uuid4()}.tmp")
            print(f"[Cursor重置器] 🔄 正在处理临时文件: {temp_path}")

            # 写入临时文件 -QW
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # 确保目标目录存在 -QW
            target_dir = os.path.dirname(self.db_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 备份原文件 -QW
            backup_path = f"{self.db_path}.backup.{int(uuid.uuid4().int % 1000000)}"
            shutil.copy2(self.db_path, backup_path)
            print(f"[Cursor重置器] 💾 已备份原文件: {backup_path}")

            # 替换原文件 -QW
            try:
                # 首先尝试直接替换 -QW
                os.replace(temp_path, self.db_path)
                print("[Cursor重置器] ✅ 直接替换成功")
            except PermissionError:
                # 如果直接替换失败，使用权限管理器 -QW
                print("[Cursor重置器] 🔐 需要提升权限...")
                with FilePermissionManager(target_dir):
                    if os.path.exists(self.db_path):
                        os.unlink(self.db_path)
                    shutil.move(temp_path, self.db_path)
                print("[Cursor重置器] ✅ 权限提升替换成功")

            result["success"] = True
            result["message"] = "机器ID重置成功"
            print("[Cursor重置器] ✅ 机器ID重置成功")
            
            return result

        except Exception as e:
            error_msg = f"重置失败: {str(e)}"
            result["message"] = error_msg
            print(f"[Cursor重置器] ❌ {error_msg}")
            
            # 清理临时文件 -QW
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    print("[Cursor重置器] ⚠️ 无法清理临时文件")
            
            return result

    def reset_machine_id_file(self) -> Dict[str, Any]:
        """重置machineId文件 -QW"""
        result = {"success": False, "message": ""}
        
        try:
            # 获取machineId文件路径 -QW
            if self.system == "windows":
                machine_id_path = os.path.expanduser("~\\AppData\\Roaming\\Cursor\\machineid")
            elif self.system == "darwin":
                machine_id_path = os.path.expanduser("~/Library/Application Support/Cursor/machineid")
            else:
                machine_id_path = os.path.expanduser("~/.config/Cursor/machineid")
            
            if os.path.exists(machine_id_path):
                # 备份原文件 -QW
                backup_path = f"{machine_id_path}.backup.{int(uuid.uuid4().int % 1000000)}"
                shutil.copy2(machine_id_path, backup_path)
                
                # 写入新的机器ID -QW
                new_machine_id = str(uuid.uuid4())
                with open(machine_id_path, 'w', encoding='utf-8') as f:
                    f.write(new_machine_id)
                
                result["success"] = True
                result["message"] = f"machineId文件重置成功: {new_machine_id}"
                print(f"[Cursor重置器] ✅ machineId文件重置成功")
            else:
                result["message"] = "machineId文件不存在"
                print("[Cursor重置器] ⚠️ machineId文件不存在")
                
        except Exception as e:
            result["message"] = f"machineId文件重置失败: {str(e)}"
            print(f"[Cursor重置器] ❌ {result['message']}")
        
        return result

    def full_reset(self) -> Dict[str, Any]:
        """完全重置Cursor -QW"""
        print("[Cursor重置器] 🚀 开始完全重置Cursor...")

        results = {
            "success": True,
            "operations": {},
            "errors": []
        }

        # 1. 重置storage.json -QW
        print("[Cursor重置器] 📝 重置storage.json...")
        storage_result = self.safe_file_update()
        results["operations"]["storage_json"] = storage_result
        if not storage_result["success"]:
            results["success"] = False
            results["errors"].append(storage_result["message"])

        # 2. 重置machineId文件 -QW
        print("[Cursor重置器] 🆔 重置machineId文件...")
        machine_id_result = self.reset_machine_id_file()
        results["operations"]["machine_id_file"] = machine_id_result
        if not machine_id_result["success"]:
            results["errors"].append(machine_id_result["message"])

        # 3. 清理工作区存储 -QW
        print("[Cursor重置器] 🗂️ 清理工作区存储...")
        workspace_result = self._clean_workspace_storage()
        results["operations"]["workspace_storage"] = workspace_result
        if not workspace_result["success"]:
            results["errors"].append(workspace_result["message"])

        # 4. 清理扩展存储 -QW
        print("[Cursor重置器] 🧩 清理扩展存储...")
        extensions_result = self._clean_extensions_storage()
        results["operations"]["extensions_storage"] = extensions_result
        if not extensions_result["success"]:
            results["errors"].append(extensions_result["message"])

        if results["success"]:
            print("[Cursor重置器] ✅ 完全重置成功！")
        else:
            print(f"[Cursor重置器] ⚠️ 重置完成，但有 {len(results['errors'])} 个错误")

        return results

    def _clean_workspace_storage(self) -> Dict[str, Any]:
        """清理工作区存储 -QW"""
        result = {"success": False, "message": "", "deleted_count": 0}

        try:
            # 获取工作区存储路径 -QW
            if self.system == "windows":
                workspace_path = os.path.expanduser("~\\AppData\\Roaming\\Cursor\\User\\workspaceStorage")
            elif self.system == "darwin":
                workspace_path = os.path.expanduser("~/Library/Application Support/Cursor/User/workspaceStorage")
            else:
                workspace_path = os.path.expanduser("~/.config/Cursor/User/workspaceStorage")

            if not os.path.exists(workspace_path):
                result["message"] = "工作区存储目录不存在"
                result["success"] = True
                return result

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
                    print(f"[Cursor重置器] ⚠️ 删除 {item} 失败: {str(e)}")

            result["success"] = True
            result["deleted_count"] = deleted_count
            result["message"] = f"清理工作区存储完成，删除了 {deleted_count} 个项目"

        except Exception as e:
            result["message"] = f"清理工作区存储失败: {str(e)}"

        return result

    def _clean_extensions_storage(self) -> Dict[str, Any]:
        """清理扩展存储 -QW"""
        result = {"success": False, "message": "", "deleted_count": 0}

        try:
            # 获取扩展存储路径 -QW
            if self.system == "windows":
                extensions_path = os.path.expanduser("~\\AppData\\Roaming\\Cursor\\User\\globalStorage")
            elif self.system == "darwin":
                extensions_path = os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage")
            else:
                extensions_path = os.path.expanduser("~/.config/Cursor/User/globalStorage")

            if not os.path.exists(extensions_path):
                result["message"] = "扩展存储目录不存在"
                result["success"] = True
                return result

            deleted_count = 0
            for item in os.listdir(extensions_path):
                # 跳过storage.json文件（已经在其他地方处理） -QW
                if item == "storage.json":
                    continue

                item_path = os.path.join(extensions_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        deleted_count += 1
                    elif os.path.isfile(item_path):
                        os.remove(item_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"[Cursor重置器] ⚠️ 删除 {item} 失败: {str(e)}")

            result["success"] = True
            result["deleted_count"] = deleted_count
            result["message"] = f"清理扩展存储完成，删除了 {deleted_count} 个项目"

        except Exception as e:
            result["message"] = f"清理扩展存储失败: {str(e)}"

        return result


def run_reset_tool():
    """运行重置工具 -QW"""
    print("\n" + "=" * 60)
    print("🎯 Cursor 完全重置工具")
    print("=" * 60)

    # 检查权限 -QW
    if not is_admin():
        print("⚠️ 检测到需要管理员权限，正在请求提升...")
        try:
            elevate_privileges()
        except Exception as e:
            print(f"❌ 权限提升失败: {str(e)}")
            print("请手动以管理员身份运行此程序")
            return

    try:
        resetter = CursorIDResetter()

        # 询问用户要执行的操作 -QW
        print("\n请选择要执行的操作:")
        print("1. 仅重置机器ID")
        print("2. 完全重置（推荐）")
        print("3. 退出")

        choice = input("\n请输入选择 (1-3): ").strip()

        if choice == "1":
            result = resetter.safe_file_update()
            if result["success"]:
                print(f"✅ {result['message']}")
                print(f"   旧ID: {result['old_machine_id']}")
                print(f"   新ID: {result['new_machine_id']}")
            else:
                print(f"❌ {result['message']}")

        elif choice == "2":
            results = resetter.full_reset()

            print(f"\n📊 重置结果:")
            for operation, result in results["operations"].items():
                status = "✅" if result["success"] else "❌"
                print(f"   {status} {operation}: {result['message']}")

            if results["errors"]:
                print(f"\n⚠️ 发现 {len(results['errors'])} 个错误:")
                for error in results["errors"]:
                    print(f"   • {error}")

        elif choice == "3":
            print("👋 退出程序")
            return
        else:
            print("❌ 无效选择")

    except Exception as e:
        print(f"❌ 严重错误: {str(e)}")

    print("\n" + "=" * 60)
    input("按回车键退出...")


def reset_cursor_machine_id() -> Dict[str, Any]:
    """重置Cursor机器ID的便捷函数 -QW"""
    resetter = CursorIDResetter()
    return resetter.safe_file_update()


def full_reset_cursor() -> Dict[str, Any]:
    """完全重置Cursor的便捷函数 -QW"""
    resetter = CursorIDResetter()
    return resetter.full_reset()


if __name__ == "__main__":
    run_reset_tool()
