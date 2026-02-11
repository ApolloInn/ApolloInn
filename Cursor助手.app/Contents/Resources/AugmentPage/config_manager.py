#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage 配置管理模块
管理应用程序配置和用户设置
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import json
import platform
from typing import Dict, Any, Optional, List
from pathlib import Path


class ConfigManager:
    """配置管理器 -QW"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "augmentpage_config.json"
        self.config = self._load_config()
        
        print(f"[配置管理] 初始化完成，配置目录: {self.config_dir}")
    
    def _get_config_dir(self) -> Path:
        """获取配置目录 -QW"""
        if self.system == "windows":
            # Windows: %APPDATA%\AugmentPage
            appdata = os.getenv("APPDATA", "")
            return Path(appdata) / "AugmentPage"
        elif self.system == "darwin":
            # macOS: ~/Library/Application Support/AugmentPage
            return Path.home() / "Library" / "Application Support" / "AugmentPage"
        else:
            # Linux: ~/.config/AugmentPage
            return Path.home() / ".config" / "AugmentPage"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置 -QW"""
        return {
            "version": "2.0.0",
            "system": self.system,
            "settings": {
                "auto_backup": True,
                "backup_retention_days": 30,
                "confirm_dangerous_operations": True,
                "verbose_logging": False,
                "preferred_ide": "Cursor",
                "theme": "auto"
            },
            "paths": {
                "backup_dir": str(self.config_dir / "backups"),
                "logs_dir": str(self.config_dir / "logs"),
                "temp_dir": str(self.config_dir / "temp")
            },
            "email": {
                "imap_enabled": False,
                "imap_server": "",
                "imap_port": 993,
                "imap_username": "",
                "imap_password": "",
                "delete_after_read": False
            },
            "browser": {
                "preferred_automation": "auto",  # auto, drissionpage, selenium
                "headless_mode": False,
                "proxy": "",
                "user_agent": ""
            },
            "ui": {
                "window_width": 800,
                "window_height": 600,
                "remember_window_position": True,
                "show_advanced_options": False,
                "auto_detect_ides": True
            },
            "advanced": {
                "enable_experimental_features": False,
                "debug_mode": False,
                "custom_scripts_enabled": False
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置 -QW"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合并默认配置（处理新增的配置项） -QW
                default_config = self._get_default_config()
                merged_config = self._merge_configs(default_config, config)
                
                print("[配置管理] 配置文件加载成功")
                return merged_config
            else:
                print("[配置管理] 配置文件不存在，使用默认配置")
                return self._get_default_config()
                
        except Exception as e:
            print(f"[配置管理] ⚠️ 配置加载失败，使用默认配置: {str(e)}")
            return self._get_default_config()
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置（递归） -QW"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_config(self) -> bool:
        """保存配置 -QW"""
        try:
            # 确保配置目录存在 -QW
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存配置 -QW
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print("[配置管理] ✅ 配置保存成功")
            return True
            
        except Exception as e:
            print(f"[配置管理] ❌ 配置保存失败: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号分隔的路径） -QW"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值（支持点号分隔的路径） -QW"""
        try:
            keys = key.split('.')
            config = self.config
            
            # 导航到目标位置 -QW
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值 -QW
            config[keys[-1]] = value
            
            print(f"[配置管理] 设置配置: {key} = {value}")
            return True
            
        except Exception as e:
            print(f"[配置管理] ❌ 设置配置失败: {str(e)}")
            return False
    
    def get_backup_dir(self) -> Path:
        """获取备份目录 -QW"""
        backup_dir = Path(self.get("paths.backup_dir", str(self.config_dir / "backups")))
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def get_logs_dir(self) -> Path:
        """获取日志目录 -QW"""
        logs_dir = Path(self.get("paths.logs_dir", str(self.config_dir / "logs")))
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    
    def get_temp_dir(self) -> Path:
        """获取临时目录 -QW"""
        temp_dir = Path(self.get("paths.temp_dir", str(self.config_dir / "temp")))
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def is_auto_backup_enabled(self) -> bool:
        """是否启用自动备份 -QW"""
        return self.get("settings.auto_backup", True)
    
    def should_confirm_dangerous_operations(self) -> bool:
        """是否需要确认危险操作 -QW"""
        return self.get("settings.confirm_dangerous_operations", True)
    
    def get_preferred_ide(self) -> str:
        """获取首选IDE -QW"""
        return self.get("settings.preferred_ide", "Cursor")
    
    def get_email_config(self) -> Dict[str, Any]:
        """获取邮箱配置 -QW"""
        return self.get("email", {})
    
    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置 -QW"""
        return self.get("browser", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置 -QW"""
        return self.get("ui", {})
    
    def is_debug_mode(self) -> bool:
        """是否为调试模式 -QW"""
        return self.get("advanced.debug_mode", False)
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件 -QW"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print(f"[配置管理] ✅ 配置已导出到: {file_path}")
            return True
            
        except Exception as e:
            print(f"[配置管理] ❌ 配置导出失败: {str(e)}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置 -QW"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 合并配置 -QW
            default_config = self._get_default_config()
            self.config = self._merge_configs(default_config, imported_config)
            
            # 保存配置 -QW
            success = self.save_config()
            
            if success:
                print(f"[配置管理] ✅ 配置已从文件导入: {file_path}")
            
            return success
            
        except Exception as e:
            print(f"[配置管理] ❌ 配置导入失败: {str(e)}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置 -QW"""
        try:
            self.config = self._get_default_config()
            success = self.save_config()
            
            if success:
                print("[配置管理] ✅ 配置已重置为默认值")
            
            return success
            
        except Exception as e:
            print(f"[配置管理] ❌ 配置重置失败: {str(e)}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性 -QW"""
        issues = []
        warnings = []
        
        try:
            # 检查必要的配置项 -QW
            required_keys = [
                "version",
                "settings.auto_backup",
                "paths.backup_dir"
            ]
            
            for key in required_keys:
                if self.get(key) is None:
                    issues.append(f"缺少必要配置: {key}")
            
            # 检查路径有效性 -QW
            paths_to_check = [
                ("paths.backup_dir", "备份目录"),
                ("paths.logs_dir", "日志目录"),
                ("paths.temp_dir", "临时目录")
            ]
            
            for path_key, description in paths_to_check:
                path_str = self.get(path_key)
                if path_str:
                    path = Path(path_str)
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        if not path.exists():
                            warnings.append(f"{description}无法创建: {path_str}")
                    except Exception:
                        warnings.append(f"{description}路径无效: {path_str}")
            
            # 检查邮箱配置 -QW
            if self.get("email.imap_enabled", False):
                email_required = ["imap_server", "imap_username", "imap_password"]
                for field in email_required:
                    if not self.get(f"email.{field}"):
                        warnings.append(f"IMAP配置不完整: 缺少 {field}")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"配置验证失败: {str(e)}"],
                "warnings": []
            }


# 全局配置管理器实例 -QW
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例 -QW"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数 -QW"""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> bool:
    """设置配置值的便捷函数 -QW"""
    manager = get_config_manager()
    success = manager.set(key, value)
    if success:
        manager.save_config()
    return success


if __name__ == "__main__":
    # 测试配置管理器 -QW
    print("=== 配置管理器测试 ===")
    
    manager = ConfigManager()
    
    # 测试配置获取和设置 -QW
    print(f"默认IDE: {manager.get_preferred_ide()}")
    print(f"自动备份: {manager.is_auto_backup_enabled()}")
    print(f"调试模式: {manager.is_debug_mode()}")
    
    # 测试配置验证 -QW
    validation = manager.validate_config()
    print(f"配置有效性: {validation}")
    
    print("=== 测试完成 ===")


# 创建日志管理模块
class LogManager:
    """日志管理器 -QW"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_config_manager()
        self.logs_dir = self.config_manager.get_logs_dir()
        self.current_log_file = None
        self._setup_logging()

    def _setup_logging(self):
        """设置日志 -QW"""
        import logging
        from datetime import datetime

        # 创建日志文件名 -QW
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = f"augmentpage_{timestamp}.log"
        self.current_log_file = self.logs_dir / log_filename

        # 配置日志格式 -QW
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # 设置日志级别 -QW
        log_level = logging.DEBUG if self.config_manager.is_debug_mode() else logging.INFO

        # 配置日志 -QW
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(self.current_log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        print(f"[日志管理] 日志文件: {self.current_log_file}")

    def get_log_files(self) -> List[Path]:
        """获取所有日志文件 -QW"""
        return list(self.logs_dir.glob("augmentpage_*.log"))

    def cleanup_old_logs(self, retention_days: int = None) -> int:
        """清理旧日志文件 -QW"""
        if retention_days is None:
            retention_days = self.config_manager.get("settings.backup_retention_days", 30)

        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        for log_file in self.get_log_files():
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"[日志管理] ⚠️ 删除日志文件失败: {log_file} - {str(e)}")

        print(f"[日志管理] 清理了 {deleted_count} 个旧日志文件")
        return deleted_count


def get_log_manager() -> LogManager:
    """获取日志管理器实例 -QW"""
    return LogManager()
