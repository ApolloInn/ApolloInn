#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cursor Workbench JS 修改工具
独立运行的 modify_workbench_js 方法
支持跨平台（Windows、macOS、Linux）
包含JS文件修改和备份功能
-QW
"""

import os
import sys
import platform
import tempfile
import shutil
import re
import json
import glob
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


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
            # 回退方案 -QW
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif system == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # 获取实际用户的主目录 -QW
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")


def get_workbench_cursor_path() -> str:
    """获取 Cursor workbench.desktop.main.js 路径 -QW"""
    system = platform.system()
    print(f"[路径检测] 检测到系统类型: {system}")

    # 定义路径映射 -QW
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "base": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),
            "main": "out\\vs\\workbench\\workbench.desktop.main.js"
        },
        "Linux": {
            "bases": [
                "/opt/Cursor/resources/app",
                "/usr/share/cursor/resources/app",
                "/usr/lib/cursor/app/",
                os.path.expanduser("~/.local/share/cursor/resources/app")
            ],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }

    # Linux系统添加提取的AppImage路径 -QW
    if system == "Linux":
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)

    if system not in paths_map:
        raise OSError(f"不支持的操作系统: {system}")

    # 根据系统类型查找路径 -QW
    if system == "Linux":
        # Linux系统检查多个可能的路径 -QW
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            if os.path.exists(main_path):
                print(f"[路径检测] 找到Linux Workbench文件: {main_path}")
                return main_path
    else:
        # Windows和macOS系统路径处理 -QW
        base_path = paths_map[system]["base"]
        main_path = os.path.join(base_path, paths_map[system]["main"])
        
        if os.path.exists(main_path):
            print(f"[路径检测] 找到{system} Workbench文件: {main_path}")
            return main_path

    # 如果所有路径都不存在，抛出错误 -QW
    if system == "Linux":
        main_path = os.path.join(paths_map[system]["bases"][0], paths_map[system]["main"])
    else:
        main_path = os.path.join(paths_map[system]["base"], paths_map[system]["main"])
    
    raise OSError(f"未找到 Cursor workbench.desktop.main.js 文件: {main_path}")


def modify_workbench_js(file_path: str) -> bool:
    """
    修改 Cursor workbench.desktop.main.js 文件

    Args:
        file_path: workbench.desktop.main.js 文件路径

    Returns:
        bool: 修改是否成功
    -QW
    """
    print(f"[文件修改] 开始修改文件: {file_path}")

    try:
        # 检查文件是否存在 -QW
        if not os.path.exists(file_path):
            print(f"[文件修改] ❌ 文件不存在: {file_path}")
            return False

        # 检查文件权限 -QW
        if not os.access(file_path, os.R_OK | os.W_OK):
            print(f"[文件修改] ❌ 文件权限不足: {file_path}")
            return False

        # 保存原始文件权限信息 -QW
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid
        print(f"[文件修改] 保存原始文件权限: {oct(original_mode)}")

        # 创建临时文件 -QW
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # 读取原始文件内容 -QW
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()
                print(f"[文件修改] 读取文件内容，大小: {len(content)} 字符")

            # 定义替换模式 -QW
            patterns = {
                # 第一个复杂的替换模式 -QW
                r'if\(h!==void 0&&t!==void 0&&t\.thinking!==void 0\)\{const d=t\.thinking\?\.text\?\?"",g=t\.thinking\?\.signature\?\?"";this\._composerDataService\.updateComposerDataSetStore\(n\.composerId,p=>p\("conversationMap",h,"thinking",v=>v===void 0\?\{text:d,signature:g\}:d\|\|g\?\{text:v\.text\+d,signature:g!==""\?g:v\.signature\}:v\)\)\}return\{thinkingStartTime:u,thinkingBubbleId:h,ignoreThinkTags:a\}\}if\(a&&u!==void 0&&!\("thinking"in t\)&&!\("serviceStatusUpdate"in t\)\)\{const d=Date\.now\(\)-u;if\(h!==void 0\)\{this\._composerDataService\.updateComposerDataSetStore\(n\.composerId,p=>p\("conversationMap",h,"thinkingDurationMs",d\)\);const g=\{\.\.\.ST\(\),type:vl\.AI,text:"",usageUuid:s\.usageUuid\};this\._composerDataService\.updateComposerDataSetStore\(n\.composerId,p=>p\("generatingBubbleIds",v=>\[\.\.\.\(v\|\|\[\]\)\.filter\(y=>y!==h\),g\.bubbleId\]\)\),this\._composerDataService\.appendComposerBubbles\(n\.composerId,\[g\]\)\}u=void 0,h=void 0\}if\(!a&&"text"in t&&t\.text&&t\.text\.trim\(\)==="<think>"&&r===void 0&&\(h=s\.bubbleId,u=Date\.now\(\)\),h!==void 0&&!a&&u!==void 0&&"text"in t&&t\.text&&t\.text\.trim\(\)==="</think>"\)\{const d=Date\.now\(\)-u;u=void 0,this\._composerDataService\.updateComposerDataSetStore\(n\.composerId,g=>g\("conversationMap",h,"thinkingDurationMs",d\)\)\}': 
                'if(h!==void 0&&t!==void 0&&t.thinking!==void 0){const d=t.thinking?.text??"",g=t.thinking?.signature??"";this._composerDataService.updateComposerDataSetStore(n.composerId,p=>p("conversationMap",h,"thinking",v=>v===void 0?{text:d,signature:g}:d||g?{text:v.text+d,signature:g!==""?g:v.signature}:v))}return{thinkingStartTime:u,thinkingBubbleId:h,ignoreThinkTags:a}}if(a&&u!==void 0&&!("thinking"in t)&&!("serviceStatusUpdate"in t)){const d=Date.now()-u;if(h!==void 0){this._composerDataService.updateComposerDataSetStore(n.composerId,p=>p("conversationMap",h,"thinkingDurationMs",d));const g={...ST(),type:vl.AI,text:"",usageUuid:s.usageUuid};this._composerDataService.updateComposerDataSetStore(n.composerId,p=>p("generatingBubbleIds",v=>[...(v||[]).filter(y=>y!==h),g.bubbleId])),this._composerDataService.appendComposerBubbles(n.composerId,[g])}u=void 0,h=void 0}if(!a&&"text"in t&&t.text&&t.text.trim()==="<think>"&&r===void 0&&(h=s.bubbleId,u=Date.now()),h!==void 0&&!a&&u!==void 0&&"text"in t&&t.text&&t.text.trim()==="</think>"){const d=Date.now()-u;u=void 0,this._composerDataService.updateComposerDataSetStore(n.composerId,g=>g("conversationMap",h,"thinkingDurationMs",d))}',
                
                # 第二个替换模式 -QW
                r'computeStreamUnifiedChatRequest called without state!"\);const g=this\._composerModesService\.getModeThinkingLevel\(u\),p=await this\.getModelDetails\(u\);':
                'computeStreamUnifiedChatRequest called without state!");const g=this._composerModesService.getModeThinkingLevel(u),p=await this.getModelDetails(u);'
            }

            # 执行替换操作 -QW
            replacement_count = 0
            for old_pattern, new_pattern in patterns.items():
                old_content = content
                content = re.sub(old_pattern, new_pattern, content)
                if content != old_content:
                    replacement_count += 1
                    print(f"[文件修改] ✅ 成功替换模式: {old_pattern[:50]}...")

            print(f"[文件修改] 总共执行了 {replacement_count} 个替换操作")

            # 写入临时文件 -QW
            tmp_file.write(content)
            tmp_path = tmp_file.name
            print(f"[文件修改] 内容已写入临时文件: {tmp_path}")

        # 创建备份文件 -QW
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"[文件修改] 创建备份文件: {backup_path}")

        # 替换原始文件 -QW
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(tmp_path, file_path)
        print(f"[文件修改] 临时文件已移动到原始位置")

        # 恢复原始权限 -QW
        os.chmod(file_path, original_mode)
        if os.name != "nt":  # 非Windows系统 -QW
            os.chown(file_path, original_uid, original_gid)
        print(f"[文件修改] 恢复原始文件权限")

        print(f"[文件修改] ✅ 工作区JS文件修改成功")
        return True

    except Exception as e:
        print(f"[文件修改] ❌ 修改工作区JS文件失败: {str(e)}")

        # 清理临时文件 -QW
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
                print(f"[文件修改] 清理临时文件: {tmp_path}")
            except:
                pass
        return False


def modify_workbench_with_backup(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    修改Workbench JS文件的便捷函数，包含完整的备份和错误处理 -QW
    
    Args:
        file_path: 可选的文件路径，如果不提供则自动检测
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    result = {
        "success": False,
        "message": "",
        "file_path": "",
        "backup_path": "",
        "error": None
    }
    
    try:
        # 如果没有提供路径，自动检测 -QW
        if not file_path:
            file_path = get_workbench_cursor_path()
        
        result["file_path"] = file_path
        
        # 执行修改 -QW
        success = modify_workbench_js(file_path)
        
        if success:
            result["success"] = True
            result["message"] = "Workbench JS文件修改成功"
            
            # 查找备份文件 -QW
            backup_files = glob.glob(f"{file_path}.backup.*")
            if backup_files:
                result["backup_path"] = max(backup_files)  # 获取最新的备份文件
        else:
            result["message"] = "Workbench JS文件修改失败"
            
    except Exception as e:
        result["error"] = str(e)
        result["message"] = f"修改过程中发生错误: {str(e)}"
    
    return result


def main():
    """
    主函数 - 独立运行modify_workbench_js功能 -QW
    """
    print("=" * 60)
    print("[程序启动] Cursor Workbench JS 修改工具")
    print(f"[程序启动] Python版本: {sys.version}")
    print(f"[程序启动] 系统平台: {platform.platform()}")
    print("=" * 60)

    try:
        # 获取workbench文件路径 -QW
        print("[主程序] 开始获取Cursor Workbench文件路径")
        workbench_path = get_workbench_cursor_path()

        # 修改workbench文件 -QW
        print("[主程序] 开始修改Cursor Workbench文件")
        success = modify_workbench_js(workbench_path)

        if success:
            print("[主程序] ✅ 程序执行成功！")
            print(f"[主程序] 修改的文件: {workbench_path}")
            return 0
        else:
            print("[主程序] ❌ 程序执行失败！")
            return 1

    except Exception as e:
        print(f"[主程序] ❌ 程序执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        print("=" * 60)
        print("[程序结束] Cursor Workbench JS 修改工具结束")


if __name__ == "__main__":
    """程序入口点 -QW"""
    exit_code = main()
    sys.exit(exit_code)
