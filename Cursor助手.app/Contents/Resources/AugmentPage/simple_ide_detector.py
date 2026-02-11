"""
简单的IDE检测器，不依赖webview
用于检测系统中安装的VSCode系列和JetBrains系列IDE
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any


def detect_vscode_variants() -> List[Dict[str, Any]]:
    """检测VSCode系列IDE -QW"""
    vscode_variants = []
    
    # 已知的VSCode变体和它们的配置目录名 -QW
    known_variants = {
        "Code": {"display": "VS Code", "icon": "💙"},
        "VSCodium": {"display": "VSCodium", "icon": "🔷"},
        "Cursor": {"display": "Cursor", "icon": "🎯"},
        "Code - OSS": {"display": "Code - OSS", "icon": "🔶"},
    }
    
    # 获取标准配置目录 -QW
    base_dirs = []
    if sys.platform == "win32":
        # Windows -QW
        if appdata := os.getenv("APPDATA"):
            base_dirs.append(Path(appdata))
    elif sys.platform == "darwin":
        # macOS -QW
        home = Path.home()
        base_dirs.extend([
            home / "Library" / "Application Support",
            home / ".config"
        ])
    else:
        # Linux -QW
        home = Path.home()
        base_dirs.extend([
            home / ".config",
            home / ".local" / "share"
        ])
    
    # 扫描配置目录 -QW
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
            
        try:
            for item in base_dir.iterdir():
                if not item.is_dir():
                    continue
                
                item_name = item.name
                
                # 检查是否是VSCode变体 -QW
                for variant_name, variant_info in known_variants.items():
                    if item_name == variant_name or item_name.lower() == variant_name.lower():
                        # 检查是否有VSCode的特征目录 -QW
                        user_dir = item / "User"
                        if user_dir.exists():
                            vscode_variants.append({
                                "name": variant_name,
                                "display_name": variant_info["display"],
                                "ide_type": "vscode",
                                "config_path": str(item),
                                "icon": variant_info["icon"]
                            })
                            break
        except (PermissionError, OSError):
            continue
    
    return vscode_variants


def detect_jetbrains_ides() -> List[Dict[str, Any]]:
    """检测JetBrains IDE -QW"""
    jetbrains_ides = []
    
    # JetBrains IDE模式 -QW
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
    
    # 获取JetBrains配置目录 -QW
    base_dirs = []
    if sys.platform == "win32":
        if appdata := os.getenv("APPDATA"):
            base_dirs.append(Path(appdata))
    elif sys.platform == "darwin":
        home = Path.home()
        base_dirs.extend([
            home / "Library" / "Application Support",
            home / "Library" / "Preferences"
        ])
    else:
        home = Path.home()
        base_dirs.extend([
            home / ".config",
            home / ".local" / "share"
        ])
    
    # 扫描JetBrains目录 -QW
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
                        # 验证是否是有效的JetBrains目录 -QW
                        indicators = ["options", "config", "system"]
                        if any((item / indicator).exists() for indicator in indicators):
                            jetbrains_ides.append({
                                "name": item_name,
                                "display_name": info["display"],
                                "ide_type": "jetbrains",
                                "config_path": str(item),
                                "icon": info["icon"]
                            })
                            break
        except (PermissionError, OSError):
            continue
    
    return jetbrains_ides


def simple_detect_ides() -> Dict[str, Any]:
    """简单的IDE检测，不依赖外部库 -QW"""
    try:
        all_ides = []
        
        # 检测VSCode系列 -QW
        print("[简单IDE检测器] 🔍 检测VSCode系列IDE...")
        vscode_ides = detect_vscode_variants()
        all_ides.extend(vscode_ides)
        print(f"[简单IDE检测器] ✅ 找到 {len(vscode_ides)} 个VSCode系列IDE")
        
        # 检测JetBrains系列 -QW
        print("[简单IDE检测器] 🔍 检测JetBrains系列IDE...")
        jetbrains_ides = detect_jetbrains_ides()
        all_ides.extend(jetbrains_ides)
        print(f"[简单IDE检测器] ✅ 找到 {len(jetbrains_ides)} 个JetBrains系列IDE")
        
        # 去重 -QW
        seen_names = set()
        unique_ides = []
        for ide in all_ides:
            if ide["display_name"] not in seen_names:
                seen_names.add(ide["display_name"])
                unique_ides.append(ide)
        
        # 排序 -QW
        unique_ides.sort(key=lambda x: (x["ide_type"], x["display_name"]))
        
        print(f"[简单IDE检测器] 📊 总计检测到 {len(unique_ides)} 个唯一IDE")
        
        return {
            "success": True,
            "ides": unique_ides,
            "count": len(unique_ides),
            "message": f"检测到 {len(unique_ides)} 个IDE"
        }
        
    except Exception as e:
        error_msg = f"检测失败: {str(e)}"
        print(f"[简单IDE检测器] ❌ {error_msg}")
        return {
            "success": False,
            "ides": [],
            "count": 0,
            "message": error_msg
        }


def get_default_ides() -> List[Dict[str, Any]]:
    """获取默认IDE列表（当检测失败时使用） -QW"""
    default_ides = [
        {
            "name": "Cursor",
            "display_name": "Cursor",
            "ide_type": "vscode",
            "config_path": "",
            "icon": "🎯"
        },
        {
            "name": "Code",
            "display_name": "VS Code",
            "ide_type": "vscode",
            "config_path": "",
            "icon": "💙"
        },
        {
            "name": "VSCodium",
            "display_name": "VSCodium",
            "ide_type": "vscode",
            "config_path": "",
            "icon": "🔷"
        }
    ]
    
    return default_ides


if __name__ == "__main__":
    # 测试简单检测器 -QW
    print("=== 简单IDE检测器测试 ===")
    result = simple_detect_ides()
    
    if result["success"]:
        print(f"✅ 检测成功，找到 {result['count']} 个IDE:")
        for ide in result["ides"]:
            print(f"   {ide['icon']} {ide['display_name']} ({ide['ide_type']})")
            print(f"      配置路径: {ide['config_path']}")
    else:
        print(f"❌ 检测失败: {result['message']}")
        print("使用默认IDE列表:")
        for ide in get_default_ides():
            print(f"   {ide['icon']} {ide['display_name']} ({ide['ide_type']})")
    
    print("=== 测试完成 ===")
