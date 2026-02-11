"""
AugmentPage IDE检测模块
此模块提供跨平台的智能IDE检测功能
支持VSCode系列和JetBrains系列IDE
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import json


class IDEInfo:
    """检测到的IDE信息 -QW"""

    def __init__(self, name: str, display_name: str, ide_type: str, config_path: str, icon: str = "📝"):
        self.name = name  # 内部名称（如 "Code", "VSCodium"） -QW
        self.display_name = display_name  # 显示名称（如 "VS Code", "VSCodium"） -QW
        self.ide_type = ide_type  # IDE类型："vscode" 或 "jetbrains" -QW
        self.config_path = config_path  # 配置目录路径 -QW
        self.icon = icon  # 显示用的表情图标 -QW

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于JSON序列化 -QW"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "ide_type": self.ide_type,
            "config_path": self.config_path,
            "icon": self.icon
        }


class IDEDetector:
    """跨平台IDE检测器 -QW"""

    def __init__(self):
        self.detected_ides: List[IDEInfo] = []
        print("[IDE检测器] 初始化完成")

    def get_standard_directories(self) -> List[Path]:
        """获取IDE可能存储配置的标准目录 -QW"""
        dirs = []

        if sys.platform == "win32":
            # Windows系统 -QW
            if appdata := os.getenv("APPDATA"):
                dirs.append(Path(appdata))
            if localappdata := os.getenv("LOCALAPPDATA"):
                dirs.append(Path(localappdata))
        elif sys.platform == "darwin":
            # macOS系统 -QW
            home = Path.home()
            dirs.extend([
                home / "Library" / "Application Support",
                home / "Library" / "Preferences",
                home / ".config"
            ])
        else:
            # Linux和其他Unix系统 -QW
            home = Path.home()
            dirs.extend([
                home / ".config",
                home / ".local" / "share",
                home / ".cache"
            ])

        # 添加用户主目录作为备选 -QW
        dirs.append(Path.home())

        existing_dirs = [d for d in dirs if d.exists()]
        print(f"[IDE检测器] 找到 {len(existing_dirs)} 个标准目录")
        return existing_dirs

    def detect_vscode_variants(self) -> List[IDEInfo]:
        """检测VSCode及其变体 -QW"""
        print("[IDE检测器] 🔍 开始检测VSCode系列IDE...")
        vscode_variants = []

        # 已知的VSCode变体名称及其显示信息 -QW
        known_variants = {
            "Code": {"display": "VS Code", "icon": "💙"},
            "VSCodium": {"display": "VSCodium", "icon": "🔷"},
            "Cursor": {"display": "Cursor", "icon": "🎯"},
            "Code - OSS": {"display": "Code - OSS", "icon": "🔶"},
            "code-oss": {"display": "Code - OSS", "icon": "🔶"},
            "Codium": {"display": "Codium", "icon": "🔷"},
            "code": {"display": "Code", "icon": "💙"},
        }

        base_dirs = self.get_standard_directories()

        for base_dir in base_dirs:
            try:
                # 扫描可能是VSCode变体的目录 -QW
                for item in base_dir.iterdir():
                    if not item.is_dir():
                        continue

                    item_name = item.name

                    # 检查是否看起来像VSCode变体 -QW
                    for variant_name, variant_info in known_variants.items():
                        if item_name == variant_name or item_name.lower() == variant_name.lower():
                            # 检查是否具有预期的VSCode结构 -QW
                            user_dir = item / "User"
                            global_storage = user_dir / "globalStorage"

                            if user_dir.exists() and global_storage.exists():
                                ide_info = IDEInfo(
                                    name=variant_name,
                                    display_name=variant_info["display"],
                                    ide_type="vscode",
                                    config_path=str(item),
                                    icon=variant_info["icon"]
                                )
                                vscode_variants.append(ide_info)
                                print(f"[IDE检测器] ✅ 找到VSCode变体: {variant_info['display']} - {item}")
                                break
            except (PermissionError, OSError) as e:
                # 跳过无法访问的目录 -QW
                print(f"[IDE检测器] ⚠️ 跳过无法访问的目录: {base_dir} - {str(e)}")
                continue

        print(f"[IDE检测器] VSCode系列检测完成，找到 {len(vscode_variants)} 个")
        return vscode_variants

    def detect_jetbrains_ides(self) -> List[IDEInfo]:
        """检测JetBrains系列IDE -QW"""
        print("[IDE检测器] 🔍 开始检测JetBrains系列IDE...")
        jetbrains_ides = []

        # 已知的JetBrains IDE模式 -QW
        jetbrains_patterns = {
            "IntelliJIdea": {"display": "IntelliJ IDEA", "icon": "🧠"},
            "PyCharm": {"display": "PyCharm", "icon": "🐍"},
            "WebStorm": {"display": "WebStorm", "icon": "🚀"},
            "PhpStorm": {"display": "PhpStorm", "icon": "🐘"},
            "RubyMine": {"display": "RubyMine", "icon": "💎"},
            "CLion": {"display": "CLion", "icon": "⚙️"},
            "DataGrip": {"display": "DataGrip", "icon": "🗄️"},
            "GoLand": {"display": "GoLand", "icon": "🐹"},
            "Rider": {"display": "Rider", "icon": "🏇"},
            "AndroidStudio": {"display": "Android Studio", "icon": "🤖"},
        }

        base_dirs = self.get_standard_directories()

        for base_dir in base_dirs:
            jetbrains_dir = base_dir / "JetBrains"
            if not jetbrains_dir.exists():
                continue

            try:
                for item in jetbrains_dir.iterdir():
                    if not item.is_dir():
                        continue

                    item_name = item.name

                    # 检查JetBrains IDE模式 -QW
                    for pattern, info in jetbrains_patterns.items():
                        if pattern.lower() in item_name.lower():
                            # 验证是否为有效的JetBrains IDE目录 -QW
                            if self._is_valid_jetbrains_dir(item):
                                ide_info = IDEInfo(
                                    name=item_name,
                                    display_name=info["display"],
                                    ide_type="jetbrains",
                                    config_path=str(item),
                                    icon=info["icon"]
                                )
                                jetbrains_ides.append(ide_info)
                                print(f"[IDE检测器] ✅ 找到JetBrains IDE: {info['display']} - {item}")
                                break
            except (PermissionError, OSError) as e:
                print(f"[IDE检测器] ⚠️ 跳过无法访问的JetBrains目录: {jetbrains_dir} - {str(e)}")
                continue

        print(f"[IDE检测器] JetBrains系列检测完成，找到 {len(jetbrains_ides)} 个")
        return jetbrains_ides

    def _is_valid_jetbrains_dir(self, path: Path) -> bool:
        """检查目录是否为有效的JetBrains IDE配置目录 -QW"""
        # 查找常见的JetBrains配置文件/目录 -QW
        indicators = ["options", "config", "system", "plugins"]
        is_valid = any((path / indicator).exists() for indicator in indicators)
        if is_valid:
            print(f"[IDE检测器] 验证JetBrains目录: {path} - 有效")
        return is_valid

    def detect_all_ides(self) -> List[IDEInfo]:
        """检测所有支持的IDE -QW"""
        print("[IDE检测器] 🚀 开始检测所有IDE...")
        all_ides = []

        # 检测VSCode变体 -QW
        all_ides.extend(self.detect_vscode_variants())

        # 检测JetBrains IDE -QW
        all_ides.extend(self.detect_jetbrains_ides())

        # 基于配置路径和显示名称去除重复项 -QW
        seen_items = set()
        unique_ides = []
        for ide in all_ides:
            # 创建结合路径和显示名称的唯一键 -QW
            unique_key = f"{ide.config_path}|{ide.display_name}"
            if unique_key not in seen_items:
                seen_items.add(unique_key)
                unique_ides.append(ide)

        # 强力去重机制：基于display_name进行最终过滤 -QW
        final_unique_ides = []
        seen_display_names = set()
        for ide in unique_ides:
            if ide.display_name not in seen_display_names:
                seen_display_names.add(ide.display_name)
                final_unique_ides.append(ide)

        # 按IDE类型和名称排序 -QW
        final_unique_ides.sort(key=lambda x: (x.ide_type, x.display_name))

        self.detected_ides = final_unique_ides
        print(f"[IDE检测器] ✅ 检测完成，找到 {len(final_unique_ides)} 个唯一IDE")
        return final_unique_ides

    def get_default_ides(self) -> List[IDEInfo]:
        """获取默认IDE列表（当检测失败时使用） -QW"""
        return [
            IDEInfo("Cursor", "Cursor", "vscode", "", "🎯"),
            IDEInfo("VSCodium", "VSCodium", "vscode", "", "🔷"),
            IDEInfo("Code", "VS Code", "vscode", "", "💙")
        ]


def detect_ides() -> Dict[str, Any]:
    """
    检测IDE的主函数 -QW

    Returns:
        dict: 包含IDE列表和摘要的检测结果
    """
    try:
        print("[IDE检测] 🔍 开始IDE检测...")
        detector = IDEDetector()
        detected_ides = detector.detect_all_ides()

        result = {
            "success": True,
            "ides": [ide.to_dict() for ide in detected_ides],
            "count": len(detected_ides),
            "message": f"检测到 {len(detected_ides)} 个IDE"
        }
        
        print(f"[IDE检测] ✅ 检测成功: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f"检测失败: {str(e)}"
        print(f"[IDE检测] ❌ {error_msg}")
        return {
            "success": False,
            "ides": [],
            "count": 0,
            "message": error_msg
        }


if __name__ == "__main__":
    # 测试检测器 -QW
    print("=== AugmentPage IDE检测器测试 ===")
    result = detect_ides()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=== 测试完成 ===")
