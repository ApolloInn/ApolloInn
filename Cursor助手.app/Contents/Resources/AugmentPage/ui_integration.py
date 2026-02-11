#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage UI集成模块
为主程序提供完整的UI集成功能
支持跨平台（Windows、macOS、Linux）
集成所有AugmentPage功能到统一界面
-QW
"""

import sys
import os
import threading
import time
import json
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path


class UIIntegrationManager:
    """UI集成管理器 -QW"""
    
    def __init__(self):
        self.adapter = None
        self.callbacks = {}
        self.status = "ready"
        self.current_operation = None
        
        # 初始化适配器 -QW
        self._init_adapter()
        
        print("[UI集成] 初始化完成")
    
    def _init_adapter(self):
        """初始化适配器 -QW"""
        try:
            from .adapter import get_adapter
            self.adapter = get_adapter()
            print("[UI集成] 适配器初始化成功")
        except Exception as e:
            print(f"[UI集成] ❌ 适配器初始化失败: {str(e)}")
    
    def register_callback(self, event_name: str, callback: Callable):
        """注册回调函数 -QW"""
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []
        self.callbacks[event_name].append(callback)
        print(f"[UI集成] 注册回调: {event_name}")
    
    def emit_event(self, event_name: str, data: Any = None):
        """触发事件 -QW"""
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[UI集成] ⚠️ 回调执行失败: {str(e)}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态 -QW"""
        try:
            if not self.adapter:
                return {"success": False, "message": "适配器未初始化"}
            
            # 获取系统信息 -QW
            system_info = self.adapter.get_system_info()
            
            # 测试模块可用性 -QW
            modules = self.adapter.test_modules()
            available_modules = sum(1 for status in modules.values() if status)
            
            # 检测IDE -QW
            ides_result = self.adapter.detect_ides()
            
            status = {
                "success": True,
                "system_info": system_info,
                "modules": {
                    "available": available_modules,
                    "total": len(modules),
                    "details": modules
                },
                "ides": {
                    "count": ides_result.get("count", 0),
                    "success": ides_result.get("success", False)
                },
                "adapter_status": self.status
            }
            
            return status
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取系统状态失败: {str(e)}"
            }
    
    def async_detect_ides(self, callback: Optional[Callable] = None) -> threading.Thread:
        """异步检测IDE -QW"""
        def detect_task():
            try:
                self.current_operation = "检测IDE"
                self.emit_event("operation_start", "检测IDE")
                
                result = self.adapter.detect_ides()
                
                self.emit_event("operation_complete", result)
                if callback:
                    callback(result)
                    
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"IDE检测失败: {str(e)}"
                }
                self.emit_event("operation_error", error_result)
                if callback:
                    callback(error_result)
            finally:
                self.current_operation = None
        
        thread = threading.Thread(target=detect_task, daemon=True)
        thread.start()
        return thread
    
    def async_generate_codes(self, callback: Optional[Callable] = None) -> threading.Thread:
        """异步生成设备代码 -QW"""
        def generate_task():
            try:
                self.current_operation = "生成设备代码"
                self.emit_event("operation_start", "生成设备代码")
                
                result = self.adapter.generate_device_codes()
                
                self.emit_event("operation_complete", result)
                if callback:
                    callback(result)
                    
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"设备代码生成失败: {str(e)}"
                }
                self.emit_event("operation_error", error_result)
                if callback:
                    callback(error_result)
            finally:
                self.current_operation = None
        
        thread = threading.Thread(target=generate_task, daemon=True)
        thread.start()
        return thread
    
    def async_modify_telemetry(self, ide_name: str, callback: Optional[Callable] = None) -> threading.Thread:
        """异步修改遥测ID -QW"""
        def modify_task():
            try:
                self.current_operation = f"修改{ide_name}遥测ID"
                self.emit_event("operation_start", f"修改{ide_name}遥测ID")
                
                result = self.adapter.modify_telemetry_only(ide_name)
                
                self.emit_event("operation_complete", result)
                if callback:
                    callback(result)
                    
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"遥测ID修改失败: {str(e)}"
                }
                self.emit_event("operation_error", error_result)
                if callback:
                    callback(error_result)
            finally:
                self.current_operation = None
        
        thread = threading.Thread(target=modify_task, daemon=True)
        thread.start()
        return thread
    
    def async_clean_workspace(self, ide_name: str, callback: Optional[Callable] = None) -> threading.Thread:
        """异步清理工作区 -QW"""
        def clean_task():
            try:
                self.current_operation = f"清理{ide_name}工作区"
                self.emit_event("operation_start", f"清理{ide_name}工作区")
                
                result = self.adapter.clean_workspace_only(ide_name)
                
                self.emit_event("operation_complete", result)
                if callback:
                    callback(result)
                    
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"工作区清理失败: {str(e)}"
                }
                self.emit_event("operation_error", error_result)
                if callback:
                    callback(error_result)
            finally:
                self.current_operation = None
        
        thread = threading.Thread(target=clean_task, daemon=True)
        thread.start()
        return thread
    
    def async_full_cleanup(self, ide_name: str, callback: Optional[Callable] = None) -> threading.Thread:
        """异步完整清理 -QW"""
        def cleanup_task():
            try:
                self.current_operation = f"完整清理{ide_name}"
                self.emit_event("operation_start", f"完整清理{ide_name}")
                
                result = self.adapter.cleanup_ide_data(ide_name)
                
                self.emit_event("operation_complete", result)
                if callback:
                    callback(result)
                    
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"完整清理失败: {str(e)}"
                }
                self.emit_event("operation_error", error_result)
                if callback:
                    callback(error_result)
            finally:
                self.current_operation = None
        
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
        return thread
    
    def get_ide_details(self, ide_name: str) -> Dict[str, Any]:
        """获取IDE详细信息 -QW"""
        try:
            # 获取路径信息 -QW
            paths_result = self.adapter.get_ide_paths(ide_name)
            
            # 检查文件存在性 -QW
            file_status = {}
            if paths_result["success"]:
                for key, path_info in paths_result["paths"].items():
                    file_status[key] = {
                        "path": path_info["path"],
                        "exists": path_info["exists"],
                        "readable": os.access(path_info["path"], os.R_OK) if path_info["exists"] else False,
                        "writable": os.access(path_info["path"], os.W_OK) if path_info["exists"] else False
                    }
            
            return {
                "success": True,
                "ide_name": ide_name,
                "paths": paths_result.get("paths", {}),
                "file_status": file_status
            }
            
        except Exception as e:
            return {
                "success": False,
                "ide_name": ide_name,
                "message": f"获取IDE详情失败: {str(e)}"
            }
    
    def validate_operation_safety(self, operation: str, ide_name: str) -> Dict[str, Any]:
        """验证操作安全性 -QW"""
        try:
            ide_details = self.get_ide_details(ide_name)
            
            if not ide_details["success"]:
                return {
                    "safe": False,
                    "message": "无法获取IDE详情"
                }
            
            # 检查关键文件 -QW
            critical_files = ["storage_path", "db_path"]
            missing_files = []
            readonly_files = []
            
            for file_key in critical_files:
                if file_key in ide_details["file_status"]:
                    file_info = ide_details["file_status"][file_key]
                    if not file_info["exists"]:
                        missing_files.append(file_key)
                    elif not file_info["writable"]:
                        readonly_files.append(file_key)
            
            # 评估安全性 -QW
            warnings = []
            if missing_files:
                warnings.append(f"缺少文件: {', '.join(missing_files)}")
            if readonly_files:
                warnings.append(f"只读文件: {', '.join(readonly_files)}")
            
            safe = len(missing_files) == 0 and len(readonly_files) == 0
            
            return {
                "safe": safe,
                "warnings": warnings,
                "missing_files": missing_files,
                "readonly_files": readonly_files,
                "operation": operation,
                "ide_name": ide_name
            }
            
        except Exception as e:
            return {
                "safe": False,
                "message": f"安全性验证失败: {str(e)}"
            }
    
    def get_operation_status(self) -> Dict[str, Any]:
        """获取当前操作状态 -QW"""
        return {
            "current_operation": self.current_operation,
            "is_busy": self.current_operation is not None,
            "status": self.status
        }
    
    def cancel_current_operation(self):
        """取消当前操作 -QW"""
        if self.current_operation:
            print(f"[UI集成] 请求取消操作: {self.current_operation}")
            # 注意：实际的取消逻辑需要在具体的操作中实现 -QW
            self.emit_event("operation_cancel", self.current_operation)


# 全局UI集成管理器实例 -QW
_ui_manager = None


def get_ui_manager() -> UIIntegrationManager:
    """获取UI集成管理器实例 -QW"""
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = UIIntegrationManager()
    return _ui_manager


def create_progress_callback(update_func: Callable):
    """创建进度回调函数 -QW"""
    def progress_callback(data):
        try:
            if isinstance(data, dict):
                if data.get("success", False):
                    update_func("success", data.get("message", "操作成功"))
                else:
                    update_func("error", data.get("message", "操作失败"))
            else:
                update_func("info", str(data))
        except Exception as e:
            print(f"[UI集成] ⚠️ 进度回调失败: {str(e)}")
    
    return progress_callback


def setup_ui_callbacks(ui_manager: UIIntegrationManager, update_functions: Dict[str, Callable]):
    """设置UI回调函数 -QW"""
    # 操作开始回调 -QW
    if "operation_start" in update_functions:
        ui_manager.register_callback("operation_start", update_functions["operation_start"])
    
    # 操作完成回调 -QW
    if "operation_complete" in update_functions:
        ui_manager.register_callback("operation_complete", update_functions["operation_complete"])
    
    # 操作错误回调 -QW
    if "operation_error" in update_functions:
        ui_manager.register_callback("operation_error", update_functions["operation_error"])
    
    # 操作取消回调 -QW
    if "operation_cancel" in update_functions:
        ui_manager.register_callback("operation_cancel", update_functions["operation_cancel"])
    
    print("[UI集成] UI回调函数设置完成")


if __name__ == "__main__":
    # 测试UI集成管理器 -QW
    print("=== UI集成管理器测试 ===")
    
    manager = get_ui_manager()
    
    # 测试系统状态 -QW
    status = manager.get_system_status()
    print(f"系统状态: {status}")
    
    # 测试异步IDE检测 -QW
    def test_callback(result):
        print(f"检测结果: {result}")
    
    print("开始异步IDE检测...")
    thread = manager.async_detect_ides(test_callback)
    thread.join()  # 等待完成
    
    print("=== 测试完成 ===")
