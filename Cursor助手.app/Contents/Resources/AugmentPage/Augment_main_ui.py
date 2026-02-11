#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Augment标签页管理器模块
在原有Cursor基础上添加Augment标签页
完全保留原有功能，只添加新的标签页功能
支持跨平台（Windows、macOS、Linux）
-QW
"""

import sys
import threading
import time
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from typing import Optional, Dict, Any
from app_cache_manager import get_app_cache_manager


class WindsurfGuideDialog(QtWidgets.QDialog):
    """Windsurf 功能引导弹窗 -QW"""
    
    go_to_windsurf = QtCore.pyqtSignal()  # 信号：点击"立即获取"按钮
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Windsurf 功能已开放")
        self.setFixedSize(600, 400)
        self.setModal(True)
        
        # 去除边框，半透明背景
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 添加淡入效果
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.init_ui()
        self.start_fade_in_animation()
        
        # 8秒后自动淡出 -QW
        QtCore.QTimer.singleShot(8000, self.auto_close)
    
    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(45, 128, 248, 230),
                    stop:1 rgba(23, 200, 101, 230)
                );
                border-radius: 20px;
            }
        """)
        
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)
        content_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # Logo/图标
        icon_label = QtWidgets.QLabel("🌊")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(60)
        icon_label.setFont(font)
        icon_label.setStyleSheet("color: white; background: transparent; border: none;")
        content_layout.addWidget(icon_label)
        
        # 标题
        title_label = QtWidgets.QLabel("✨ Windsurf 功能已开放！")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setWordWrap(True)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(24)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: white; background: transparent; border: none;")
        content_layout.addWidget(title_label)
        
        # 描述
        desc_label = QtWidgets.QLabel("现在可以快速获取 Windsurf 邮箱和密码\n开启全新的 AI 编程体验")
        desc_label.setAlignment(QtCore.Qt.AlignCenter)
        desc_label.setWordWrap(True)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        desc_label.setFont(font)
        desc_label.setStyleSheet("color: rgba(255, 255, 255, 200); background: transparent; border: none;")
        content_layout.addWidget(desc_label)
        
        # 按钮容器
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(20)
        
        # 立即获取按钮
        go_btn = QtWidgets.QPushButton("立即获取 Windsurf 账号")
        go_btn.setMinimumHeight(50)
        go_btn.setMinimumWidth(200)
        go_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(15)
        font.setBold(True)
        go_btn.setFont(font)
        go_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: rgb(45, 128, 248);
                border: none;
                border-radius: 25px;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 230);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 200);
            }
        """)
        go_btn.clicked.connect(self.on_go_clicked)
        button_layout.addWidget(go_btn)
        
        # 稍后查看按钮
        later_btn = QtWidgets.QPushButton("稍后查看")
        later_btn.setMinimumHeight(50)
        later_btn.setMinimumWidth(120)
        later_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        later_btn.setFont(font)
        later_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 2px solid white;
                border-radius: 25px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 20);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 40);
            }
        """)
        later_btn.clicked.connect(self.on_later_clicked)
        button_layout.addWidget(later_btn)
        
        content_layout.addLayout(button_layout)
        
        main_layout.addWidget(content_widget)
    
    def start_fade_in_animation(self):
        """淡入动画 -QW"""
        self.fade_in = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(500)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()
    
    def start_fade_out_animation(self):
        """淡出动画 -QW"""
        self.fade_out = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.accept)
        self.fade_out.start()
    
    def on_go_clicked(self):
        """点击"立即获取"按钮 -QW"""
        self.go_to_windsurf.emit()
        self.start_fade_out_animation()
    
    def on_later_clicked(self):
        """点击"稍后查看"按钮 -QW"""
        self.start_fade_out_animation()
    
    def auto_close(self):
        """自动关闭 -QW"""
        if self.isVisible():
            self.start_fade_out_animation()


class WindsurfSuccessDialog(QtWidgets.QDialog):
    """Windsurf获取成功的自定义弹窗 -QW"""
    
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.email = email
        self.setWindowTitle("获取成功")
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        # 去除默认边框，使用自定义样式
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.init_ui()
    
    def init_ui(self):
        # 主容器
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 2px solid #4CAF50;
            }
        """)
        
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # 成功图标和标题
        title_label = QtWidgets.QLabel("✓ 邮箱及密码获取成功！")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #4CAF50; border: none;")
        content_layout.addWidget(title_label)
        
        # 邮箱信息
        email_label = QtWidgets.QLabel(f"邮箱: {self.email}")
        email_label.setAlignment(QtCore.Qt.AlignCenter)
        email_label.setWordWrap(True)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        email_label.setFont(font)
        email_label.setStyleSheet("color: #333333; border: none;")
        content_layout.addWidget(email_label)
        
        # 确定按钮
        ok_button = QtWidgets.QPushButton("确定")
        ok_button.setMinimumHeight(40)
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        font.setBold(True)
        ok_button.setFont(font)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        ok_button.clicked.connect(self.accept)
        content_layout.addWidget(ok_button)
        
        main_layout.addWidget(content_widget)


class WindsurfErrorDialog(QtWidgets.QDialog):
    """Windsurf获取失败的自定义弹窗 -QW"""
    
    def __init__(self, error_message, parent=None):
        super().__init__(parent)
        self.error_message = error_message
        self.setWindowTitle("获取失败")
        self.setFixedSize(420, 220)
        self.setModal(True)
        
        # 去除默认边框，使用自定义样式
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.init_ui()
    
    def init_ui(self):
        # 主容器
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 2px solid #FF9800;
            }
        """)
        
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # 失败图标和标题
        title_label = QtWidgets.QLabel("✗ 获取失败")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #FF9800; border: none;")
        content_layout.addWidget(title_label)
        
        # 错误信息
        error_label = QtWidgets.QLabel(self.error_message)
        error_label.setAlignment(QtCore.Qt.AlignCenter)
        error_label.setWordWrap(True)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        error_label.setFont(font)
        error_label.setStyleSheet("color: #333333; border: none;")
        content_layout.addWidget(error_label)
        
        # 确定按钮
        ok_button = QtWidgets.QPushButton("确定")
        ok_button.setMinimumHeight(40)
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        font.setBold(True)
        ok_button.setFont(font)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 30px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
            QPushButton:pressed {
                background-color: #F57C00;
            }
        """)
        ok_button.clicked.connect(self.accept)
        content_layout.addWidget(ok_button)
        
        main_layout.addWidget(content_widget)


class WindsurfTipDialog(QtWidgets.QDialog):
    """Windsurf通用提示弹窗 -QW"""
    
    def __init__(self, message, dialog_type="info", parent=None):
        """
        dialog_type: "success" 成功(绿色), "warning" 警告(橙色), "info" 信息(蓝色)
        """
        super().__init__(parent)
        self.message = message
        self.dialog_type = dialog_type
        self.setWindowTitle("提示")
        self.setFixedSize(380, 180)
        self.setModal(True)
        
        # 去除默认边框，使用自定义样式
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.init_ui()
    
    def init_ui(self):
        # 根据类型设置颜色
        if self.dialog_type == "success":
            color = "#4CAF50"  # 绿色
            icon = "✓"
        elif self.dialog_type == "warning":
            color = "#FF9800"  # 橙色
            icon = "!"
        else:  # info
            color = "#2196F3"  # 蓝色
            icon = "ℹ"
        
        # 主容器
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border-radius: 10px;
                border: 2px solid {color};
            }}
        """)
        
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 25, 30, 25)
        content_layout.setSpacing(15)
        
        # 提示信息
        message_label = QtWidgets.QLabel(f"{icon} {self.message}")
        message_label.setAlignment(QtCore.Qt.AlignCenter)
        message_label.setWordWrap(True)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        font.setBold(True)
        message_label.setFont(font)
        message_label.setStyleSheet(f"color: {color}; border: none;")
        content_layout.addWidget(message_label)
        
        # 确定按钮
        ok_button = QtWidgets.QPushButton("确定")
        ok_button.setMinimumHeight(38)
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        font.setBold(True)
        ok_button.setFont(font)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 25px;
            }}
            QPushButton:hover {{
                background-color: {self._get_hover_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._get_pressed_color(color)};
            }}
        """)
        ok_button.clicked.connect(self.accept)
        content_layout.addWidget(ok_button)
        
        main_layout.addWidget(content_widget)
    
    def _get_hover_color(self, color):
        """获取悬停颜色"""
        hover_colors = {
            "#4CAF50": "#45a049",
            "#FF9800": "#FB8C00",
            "#2196F3": "#1E88E5"
        }
        return hover_colors.get(color, color)
    
    def _get_pressed_color(self, color):
        """获取按下颜色"""
        pressed_colors = {
            "#4CAF50": "#3d8b40",
            "#FF9800": "#F57C00",
            "#2196F3": "#1976D2"
        }
        return pressed_colors.get(color, color)


class TabManager(QtCore.QObject):
    """标签页管理器类 -QW"""
    


    def __init__(self, main_window_instance):
        super().__init__()
        self.main_window = main_window_instance  # 保存主窗口实例的引用 -QW
        self.tab_widget = None  # 标签页控件 -QW
        
        # 标签页开关配置 -QW
        # 1=开启，0=关闭，cursor标签页默认开启
        self.tab_switches = {
            'cursor': 1,      # Cursor标签页（默认开启）
            'augment': 0,     # Augment标签页（默认关闭）
            'cursor_account': 0,  # cursor账号标签页（已关闭）
            'history_account': 1,  # 历史账号标签页（默认开启）
            'windsurf': 0     # Windsurf标签页（默认关闭，仅Auto账号且已激活时显示）
        }
        
        # 历史账号标签页相关控件
        self.history_account_tab = None
        self.history_account_tab_index = -1
        self.history_account_list = None
        
        # Windsurf标签页相关控件 -QW
        self.windsurf_tab = None
        self.windsurf_tab_index = -1
        
        # Augment相关控件 -QW
        # 新版控件（与Windows版本一致）
        self.augment_account_input = None
        self.augment_get_account_btn = None
        self.augment_copy_account_btn = None
        self.augment_code_input = None
        self.augment_get_code_new_btn = None
        self.augment_copy_code_btn = None

        # 旧版控件（保持兼容性）
        self.augment_get_email_btn = None

        # 倒计时相关变量 -QW
        self._countdown_timer = None
        self._countdown_seconds = 0
        self._last_get_account_time = None

        # 获取账号倒计时相关变量 -QW
        self._account_countdown_timer = None
        self._account_countdown_seconds = 0
        self._last_get_account_success_time = None
        self.augment_email_display = None
        self.augment_get_code_btn = None
        self.augment_code_display = None

        # IDE相关控件
        self.augment_ide_combo = None
        self.augment_detect_btn = None
        self.augment_cleanup_btn = None
        

        
        # 加载配置 -QW
        self.load_tab_config()
        
        print("[标签页管理器] 初始化完成")

    def load_tab_config(self):
        """加载Python标签页配置 -QW"""
        try:
            import os
            import sys
            
            # 优先使用新的Python配置系统 -QW
            try:
                from tab_config_manager import TabConfigManager
                config_manager = TabConfigManager("config.py")
                config = config_manager.load_config()
                
                # 更新配置
                for key in self.tab_switches:
                    if key in config:
                        self.tab_switches[key] = config[key]
                        
                print(f"[标签页管理器] ✅ Python配置加载成功: {self.tab_switches}")
                print(f"[标签页管理器] 📄 配置文件: config.py")
                return
                
            except Exception as e:
                print(f"[标签页管理器] ⚠️ Python配置加载失败: {str(e)}")
                print("[标签页管理器] 尝试加载JSON配置...")
                
            # 如果Python配置失败，尝试加载旧的JSON配置（向后兼容）-QW
            import json
            
            possible_paths = [
                "tab_config.json",  # 开发环境：当前目录
                os.path.join(os.path.dirname(sys.executable), "tab_config.json"),  # 打包环境：可执行文件目录
                os.path.join(os.path.dirname(__file__), "..", "..", "tab_config.json"),  # 相对于当前文件
                os.path.join(sys._MEIPASS, "tab_config.json") if hasattr(sys, '_MEIPASS') else None,  # PyInstaller临时目录
            ]
            
            # 过滤掉None值
            possible_paths = [p for p in possible_paths if p is not None]
            
            config_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_file = path
                    print(f"[标签页管理器] 🔍 找到JSON配置文件: {config_file}")
                    break
                else:
                    print(f"[标签页管理器] 🔍 检查路径: {path} (不存在)")
            
            if config_file:
                # 配置文件已找到，读取内容
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 更新开关配置 -QW
                for key in self.tab_switches:
                    if key in config:
                        self.tab_switches[key] = config[key]
                        
                print(f"[标签页管理器] ✅ JSON配置加载成功: {self.tab_switches}")
                print(f"[标签页管理器] 📄 配置文件位置: {config_file}")
            else:
                print("[标签页管理器] ⚠️ 未找到任何配置文件，使用默认配置")
                print(f"[标签页管理器] 使用默认配置: {self.tab_switches}")
                
        except Exception as e:
            print(f"[标签页管理器] ❌ 配置加载失败: {str(e)}")
            print(f"[标签页管理器] 使用默认配置: {self.tab_switches}")

    def save_tab_config(self):
        """保存Python标签页配置 -QW"""
        try:
            # 优先使用Python配置系统保存 -QW
            try:
                from tab_config_manager import TabConfigManager
                config_manager = TabConfigManager("config.py")
                if config_manager.save_config(self.tab_switches):
                    print(f"[标签页管理器] ✅ Python配置保存成功: {self.tab_switches}")
                    return
                else:
                    raise Exception("Python配置保存失败")
                    
            except Exception as e:
                print(f"[标签页管理器] ⚠️ Python配置保存失败: {str(e)}")
                print("[标签页管理器] 尝试保存JSON配置...")
                
            # 如果Python配置保存失败，保存为JSON（向后兼容）-QW
            import json
            import os
            import sys
            
            possible_save_paths = [
                "tab_config.json",  # 当前目录
                os.path.join(os.path.expanduser("~"), "tab_config.json"),  # 用户目录
                os.path.join(os.path.dirname(sys.executable), "tab_config.json"),  # 可执行文件目录
            ]
            
            config_file = None
            for path in possible_save_paths:
                try:
                    # 尝试写入测试
                    test_dir = os.path.dirname(path) if os.path.dirname(path) else "."
                    if os.access(test_dir, os.W_OK):
                        config_file = path
                        print(f"[标签页管理器] 💾 选择JSON保存路径: {config_file}")
                        break
                except:
                    continue
            
            if not config_file:
                config_file = os.path.join(os.path.expanduser("~"), "tab_config.json")
                print(f"[标签页管理器] 💾 使用默认JSON保存路径: {config_file}")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tab_switches, f, ensure_ascii=False, indent=2)
                
            print(f"[标签页管理器] ✅ JSON配置保存成功: {self.tab_switches}")
            print(f"[标签页管理器] 📄 保存位置: {config_file}")
            
        except Exception as e:
            print(f"[标签页管理器] ❌ 配置保存失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_tab_switch(self, tab_name, enabled):
        """设置标签页开关 -QW
        
        Args:
            tab_name (str): 标签页名称 ('cursor', 'augment', 'cursor_account')
            enabled (int): 1=开启, 0=关闭
        """
        if tab_name in self.tab_switches:
            self.tab_switches[tab_name] = int(enabled)
            self.save_tab_config()
            print(f"[标签页管理器] ✅ {tab_name}标签页开关设置为: {enabled}")
            return True
        else:
            print(f"[标签页管理器] ❌ 未知的标签页名称: {tab_name}")
            return False

    def get_tab_switches(self):
        """获取所有标签页开关状态 -QW"""
        return self.tab_switches.copy()

    def update_history_tab_visibility(self, pro_type):
        """根据pro_type更新历史账号标签页和Windsurf标签页的显示状态 -QW
        
        Args:
            pro_type (int): 0=auto，1=pro
            - 历史账号标签页：Pro显示，Auto隐藏
            - Windsurf标签页：Auto显示，Pro隐藏
        """
        # 更新历史账号标签页显示状态 -QW
        if hasattr(self, 'history_account_tab_index') and self.history_account_tab_index >= 0:
            if pro_type == 1:
                # Pro类型：显示历史账号标签页
                self.tab_widget.setTabVisible(self.history_account_tab_index, True)
                print("[标签页管理器] ✅ Pro类型账号，显示历史账号标签页")
            else:
                # Auto类型：隐藏历史账号标签页
                self.tab_widget.setTabVisible(self.history_account_tab_index, False)
                print("[标签页管理器] ⚪ Auto类型账号，隐藏历史账号标签页")
        else:
            print("[标签页管理器] ⚠️ 历史账号标签页未创建，跳过显示状态更新")
        
        # 更新Windsurf标签页显示状态 -QW
        if hasattr(self, 'windsurf_tab_index') and self.windsurf_tab_index >= 0:
            # 检查激活状态（未激活时隐藏Windsurf标签页）-QW
            is_activated = self._check_activation_for_tab()
            
            if not is_activated:
                # 未激活：隐藏Windsurf标签页
                self.tab_widget.setTabVisible(self.windsurf_tab_index, False)
                print("[标签页管理器] ⚪ 设备未激活，隐藏Windsurf标签页")
            elif pro_type == 1:
                # Pro类型：隐藏Windsurf标签页
                self.tab_widget.setTabVisible(self.windsurf_tab_index, False)
                print("[标签页管理器] ⚪ Pro类型账号，隐藏Windsurf标签页")
            else:
                # Auto类型且已激活：显示Windsurf标签页
                self.tab_widget.setTabVisible(self.windsurf_tab_index, True)
                print("[标签页管理器] ✅ Auto类型账号且已激活，显示Windsurf标签页")
        else:
            print("[标签页管理器] ⚠️ Windsurf标签页未创建，跳过显示状态更新")
        
        # 更新顶部标签按钮可见性 -QW
        self._update_tab_buttons()

    def _check_activation_for_tab(self):
        """检查激活状态（用于标签页显示控制，不显示弹窗）-QW"""
        try:
            # 使用与Cursor标签页相同的激活检查逻辑 -QW
            if hasattr(self.main_window, 'get_labl_19'):
                level = self.main_window.get_labl_19()
                if level == '青铜':
                    return False
                else:
                    return True
            # 如果主窗口没有get_labl_19方法，默认返回True -QW
            return True
        except Exception as e:
            print(f"[标签页管理器] ⚠️ 激活状态检查失败: {str(e)}")
            return True

    def setup_tab_interface(self):
        """设置标签页界面，包装原有内容 -QW"""
        print("="*50)
        print("[标签页管理器] 🎯 开始设置标签页界面")
        print("="*50)
        
        try:
            # 获取原有的主要内容容器 -QW
            print("[标签页管理器] 步骤1: 获取原有内容")
            original_widget = self.get_original_content_widget()
            
            # 创建标签页控件 -QW
            print("[标签页管理器] 步骤2: 创建标签页控件")
            self.create_tab_widget()
            
            # 将原有内容完整地移动到Cursor标签页 -QW
            print("[标签页管理器] 步骤3: 移动原有内容到Cursor标签页")
            self.move_original_content_to_cursor_tab(original_widget)
            
            # 重新组织主窗口布局 -QW
            print("[标签页管理器] 步骤4: 重新组织主窗口布局")
            self.reorganize_main_layout()
            
            # 连接事件 -QW
            print("[标签页管理器] 步骤5: 连接事件")
            self.connect_events()
            
            print("="*50)
            print("[标签页管理器] ✅ 标签页界面设置完成")
            print("="*50)
            
        except Exception as e:
            print("="*50)
            print(f"[标签页管理器] ❌ 设置标签页界面失败: {str(e)}")
            print("="*50)
            import traceback
            traceback.print_exc()
            raise

    def get_original_content_widget(self):
        """获取原有的主要内容控件 -QW"""
        print("[标签页管理器] 获取原有内容控件")

        try:
            # 查找主要内容控件，通常是verticalLayout_11下的第一个widget -QW
            main_layout = self.main_window.verticalLayout_11

            if main_layout.count() > 0:
                # 获取第一个控件项 -QW
                first_item = main_layout.itemAt(0)
                if first_item and first_item.widget():
                    original_widget = first_item.widget()
                    print(f"[标签页管理器] 找到原有内容控件: {original_widget.objectName()}")
                    return original_widget

            print("[标签页管理器] ⚠️ 未找到原有内容控件")
            return None

        except AttributeError as e:
            print(f"[标签页管理器] ❌ 获取原有内容控件失败: {str(e)}")
            print("[标签页管理器] 主窗口可能没有verticalLayout_11布局")
            return None

    def create_tab_widget(self):
        """创建标签页控件 -QW"""
        print("[标签页管理器] 创建标签页控件")
        
        # 创建标签页控件 -QW
        self.tab_widget = QtWidgets.QTabWidget(self.main_window.centralwidget)
        self.tab_widget.setObjectName("tab_widget")
        print(f"[标签页管理器] ✅ QTabWidget 创建成功: {self.tab_widget}")
        
        # 设置标签页样式（扁平化设计） -QW
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: rgb(248, 252, 254);
                border-bottom-left-radius: 30px;
                border-bottom-right-radius: 30px;
                margin-top: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
                left: 10px;
            }
            QTabBar::tab {
                background-color: #e8eaed;
                color: #666666;
                padding: 8px 18px;
                margin-right: 8px;
                margin-top: 5px;
                margin-bottom: 5px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QTabBar::tab:selected {
                background-color: rgb(45, 128, 248);
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d0d3d8;
                color: #333333;
            }
        """)
        
        # 根据开关配置创建标签页 -QW
        self.created_tabs = {}  # 记录已创建的标签页 -QW
        
        # 创建Cursor标签页（如果开关开启）-QW
        if self.tab_switches.get('cursor', 1):
            print("[标签页管理器] 创建Cursor标签页...")
            self.cursor_tab = QtWidgets.QWidget()
            self.cursor_tab.setObjectName("cursor_tab")
            self.tab_widget.addTab(self.cursor_tab, "首页")
            self.created_tabs['cursor'] = self.cursor_tab
            print(f"[标签页管理器] ✅ Cursor标签页创建成功，当前标签页数量: {self.tab_widget.count()}")
        else:
            print("[标签页管理器] ⚪ Cursor标签页已关闭，跳过创建")

        # 创建Augment标签页（如果开关开启）-QW
        if self.tab_switches.get('augment', 0):
            print("[标签页管理器] 创建Augment标签页...")
            self.augment_tab = QtWidgets.QWidget()
            self.augment_tab.setObjectName("augment_tab")
            self.tab_widget.addTab(self.augment_tab, "Augment")
            self.created_tabs['augment'] = self.augment_tab
            print(f"[标签页管理器] ✅ Augment标签页创建成功，当前标签页数量: {self.tab_widget.count()}")
        else:
            print("[标签页管理器] ⚪ Augment标签页已关闭，跳过创建")

        # 创建Cursor账号标签页（如果开关开启）-QW
        if self.tab_switches.get('cursor_account', 0):
            print("[标签页管理器] 创建Cursor账号标签页...")
            self.cursor_account_tab = QtWidgets.QWidget()
            self.cursor_account_tab.setObjectName("cursor_account_tab")
            self.tab_widget.addTab(self.cursor_account_tab, "cursor账号")
            self.created_tabs['cursor_account'] = self.cursor_account_tab
            print(f"[标签页管理器] ✅ Cursor账号标签页创建成功，当前标签页数量: {self.tab_widget.count()}")
        else:
            print("[标签页管理器] ⚪ Cursor账号标签页已关闭，跳过创建")

        # 创建历史账号标签页（如果开关开启）-QW
        # 注意：先创建标签页，稍后根据pro_type动态控制显示/隐藏
        if self.tab_switches.get('history_account', 0):
            print("[标签页管理器] 创建历史账号标签页...")
            self.history_account_tab = QtWidgets.QWidget()
            self.history_account_tab.setObjectName("history_account_tab")
            self.history_account_tab_index = self.tab_widget.addTab(self.history_account_tab, "历史账号")
            self.created_tabs['history_account'] = self.history_account_tab
            print(f"[标签页管理器] ✅ 历史账号标签页创建成功，当前标签页数量: {self.tab_widget.count()}")
            # 默认先隐藏，等initCursor完成后根据pro_type决定是否显示
            self.tab_widget.setTabVisible(self.history_account_tab_index, False)
            print("[标签页管理器] ⏳ 历史账号标签页暂时隐藏，等待pro_type检查...")
        else:
            print("[标签页管理器] ⚪ 历史账号标签页已关闭，跳过创建")
            self.history_account_tab = None
            self.history_account_tab_index = -1

        # 创建Windsurf标签页（如果开关开启）-QW
        # 注意：先创建标签页，稍后根据pro_type动态控制显示/隐藏（Auto显示，Pro隐藏）
        if self.tab_switches.get('windsurf', 0):
            print("[标签页管理器] 创建Windsurf标签页...")
            self.windsurf_tab = QtWidgets.QWidget()
            self.windsurf_tab.setObjectName("windsurf_tab")
            self.windsurf_tab_index = self.tab_widget.addTab(self.windsurf_tab, "Windsurf")
            self.created_tabs['windsurf'] = self.windsurf_tab
            print(f"[标签页管理器] ✅ Windsurf标签页创建成功，当前标签页数量: {self.tab_widget.count()}")
            # 默认先隐藏，等initCursor完成后根据pro_type决定是否显示（Auto显示，Pro隐藏）
            self.tab_widget.setTabVisible(self.windsurf_tab_index, False)
            print("[标签页管理器] ⏳ Windsurf标签页暂时隐藏，等待pro_type检查...")
        else:
            print("[标签页管理器] ⚪ Windsurf标签页已关闭，跳过创建")
            self.windsurf_tab = None
            self.windsurf_tab_index = -1

        # 设置默认选中第一个标签页 -QW
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)
            print(f"[标签页管理器] ✅ 默认选中第一个标签页")
        else:
            print("[标签页管理器] ⚠️ 没有启用的标签页")
        
        # 根据开关创建标签页内容 -QW
        if self.tab_switches.get('augment', 0):
            print("[标签页管理器] 创建Augment标签页内容...")
            self.create_augment_tab_content()
            print("[标签页管理器] ✅ Augment标签页内容创建完成")

        if self.tab_switches.get('cursor_account', 0):
            print("[标签页管理器] 创建Cursor账号标签页内容...")
            self.create_cursor_account_tab_content()
            print("[标签页管理器] ✅ Cursor账号标签页内容创建完成")

        # 创建历史账号标签页内容（即使暂时隐藏也需要创建内容）-QW
        if self.tab_switches.get('history_account', 0) and self.history_account_tab is not None:
            print("[标签页管理器] 创建历史账号标签页内容...")
            self.create_history_account_tab_content()
            print("[标签页管理器] ✅ 历史账号标签页内容创建完成")

        # 创建Windsurf标签页内容（即使暂时隐藏也需要创建内容）-QW
        if self.tab_switches.get('windsurf', 0) and self.windsurf_tab is not None:
            print("[标签页管理器] 创建Windsurf标签页内容...")
            self.create_windsurf_tab_content()
            print("[标签页管理器] ✅ Windsurf标签页内容创建完成")

    def move_original_content_to_cursor_tab(self, original_widget):
        """将原有内容完整地移动到Cursor标签页 -QW"""
        print("[标签页管理器] 移动原有内容到Cursor标签页")

        # 设置Cursor标签页背景色和底部圆角 -QW
        self.cursor_tab.setStyleSheet("""
            QWidget {
                background-color: rgb(248, 252, 254);
                border-bottom-left-radius: 30px;
                border-bottom-right-radius: 30px;
            }
        """)

        # 创建Cursor标签页的主布局 -QW
        cursor_main_layout = QtWidgets.QVBoxLayout(self.cursor_tab)
        cursor_main_layout.setContentsMargins(0, 0, 0, 0)
        cursor_main_layout.setSpacing(0)

        # 顶部按钮已移到全局顶部栏，这里不再创建 -QW

        # 如果有原有内容，添加到标签页中 -QW
        if original_widget:
            original_widget.setParent(None)
            self.hide_original_close_buttons(original_widget)
            cursor_main_layout.addWidget(original_widget)
            print("[标签页管理器] ✅ 原有内容已完整移动到Cursor标签页")
        else:
            print("[标签页管理器] ⚠️ 没有找到原有内容，Cursor标签页将为空")

    def hide_original_close_buttons(self, widget):
        """隐藏原有内容中的关闭按钮区域 -QW"""
        try:
            # 递归查找并隐藏原有的关闭按钮 -QW
            def find_and_hide_buttons(parent):
                for child in parent.findChildren(QtWidgets.QPushButton):
                    # 根据按钮文本或对象名称识别关闭和最小化按钮 -QW
                    if (child.text() in ["×", "－"] or
                        child.objectName() in ["pushButton_close", "pushButton_min"]):
                        child.setVisible(False)
                        print(f"[标签页管理器] 隐藏按钮: {child.objectName()} - {child.text()}")
            
            find_and_hide_buttons(widget)
            print("[标签页管理器] ✅ 原有关闭按钮已隐藏")
            
        except Exception as e:
            print(f"[标签页管理器] ⚠️ 隐藏原有按钮时出现错误: {str(e)}")

    def create_augment_tab_content(self):
        """创建Augment标签页内容 -QW"""
        print("[标签页管理器] 创建Augment标签页内容")

        # 设置Augment标签页背景色和底部圆角 -QW
        self.augment_tab.setStyleSheet("""
            QWidget {
                background-color: rgb(248, 252, 254);
                border-bottom-left-radius: 30px;
                border-bottom-right-radius: 30px;
            }
        """)

        # 创建Augment标签页的主布局 -QW
        augment_main_layout = QtWidgets.QVBoxLayout(self.augment_tab)
        augment_main_layout.setContentsMargins(0, 0, 0, 0)
        augment_main_layout.setSpacing(0)

        # 顶部按钮已移到全局顶部栏，这里不再创建 -QW

        # 创建Augment主要内容区域 -QW
        self.create_augment_main_content(augment_main_layout)

    def create_augment_top_buttons(self, parent_layout):
        """创建Augment标签页顶部按钮区域 -QW"""
        # 创建顶部区域，包含最小化和关闭按钮 -QW
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)

        # 添加弹性空间，将按钮推到右边 -QW
        top_layout.addStretch()

        # 创建最小化按钮 -QW
        self.augment_minimize_btn = QtWidgets.QPushButton("−")
        self.augment_minimize_btn.setFixedSize(30, 30)
        self.augment_minimize_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.augment_minimize_btn.setToolTip("最小化窗口")
        self.augment_minimize_btn.clicked.connect(self.minimize_application)

        # 创建关闭按钮 -QW
        self.augment_close_btn = QtWidgets.QPushButton("✕")
        self.augment_close_btn.setFixedSize(30, 30)
        self.augment_close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.augment_close_btn.setToolTip("关闭应用程序")
        self.augment_close_btn.clicked.connect(self.close_application)

        # 添加按钮到布局，最小化在左，关闭在右 -QW
        top_layout.addWidget(self.augment_minimize_btn)
        top_layout.addSpacing(5)  # 按钮之间的间距
        top_layout.addWidget(self.augment_close_btn)

        parent_layout.addWidget(top_widget)

    def create_augment_main_content(self, parent_layout):
        """创建Augment主要内容区域 -QW"""
        print("[标签页管理器] 创建Augment主要内容区域")

        # 创建主要内容容器 -QW
        main_widget = QtWidgets.QWidget()
        main_widget.setObjectName("augment_main_widget")
        main_widget.setStyleSheet("""
            QWidget#augment_main_widget {
                background-color: white;
                border-radius: 12px;
                margin: 10px;
                padding: 0px;
            }
        """)

        # 创建主要内容布局 -QW
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(30)

        # 创建顶部标题区域（包含关闭按钮） -QW
        self.create_augment_title_section(main_layout)

        # 创建清理机器码区域 -QW
        self.create_cleanup_section_new(main_layout)

        # 创建获取邮箱区域 -QW
        self.create_email_section_new(main_layout)

        # 添加弹性空间 -QW
        spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        main_layout.addItem(spacer)

        # 将主要内容容器添加到父布局中 -QW
        parent_layout.addWidget(main_widget)

    def create_augment_title_section(self, parent_layout):
        """创建Augment标签页的简化标题区域（仅包含关闭按钮） -QW"""
        # 创建标题容器 -QW
        title_widget = QtWidgets.QWidget()
        title_widget.setFixedHeight(40)  # 设置较小的固定高度 -QW
        title_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        # 创建标题布局 -QW
        title_layout = QtWidgets.QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        # 添加弹性空间，将关闭按钮推到右侧 -QW
        title_layout.addStretch()

        # 注意：关闭按钮现在在顶部区域创建，这里不再需要 -QW

        # 将标题容器添加到父布局 -QW
        parent_layout.addWidget(title_widget)



    def create_cleanup_section_new(self, parent_layout):
        """创建新的清理机器码区域 -QW"""
        # 创建清理区域标题 -QW
        cleanup_title = QtWidgets.QLabel("清理机器码")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        font.setBold(True)
        cleanup_title.setFont(font)
        cleanup_title.setStyleSheet("color: #333333; margin-bottom: 10px;")
        parent_layout.addWidget(cleanup_title)

        # 创建清理区域容器 -QW
        cleanup_widget = QtWidgets.QWidget()
        cleanup_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        cleanup_layout = QtWidgets.QVBoxLayout(cleanup_widget)
        cleanup_layout.setContentsMargins(20, 20, 20, 20)
        cleanup_layout.setSpacing(15)

        # IDE选择区域 -QW
        ide_layout = QtWidgets.QHBoxLayout()
        ide_layout.setSpacing(15)

        # IDE标签 -QW
        ide_label = QtWidgets.QLabel("编程工具IDE")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(12)
        ide_label.setFont(font)
        ide_label.setStyleSheet("color: #666666; min-width: 100px;")
        ide_layout.addWidget(ide_label)

        # IDE选择下拉框 -QW
        self.augment_ide_combo = QtWidgets.QComboBox()
        self.augment_ide_combo.setMinimumHeight(40)
        self.augment_ide_combo.setMinimumWidth(280)
        self.augment_ide_combo.setMaximumWidth(350)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(12)
        self.augment_ide_combo.setFont(font)

        # 设置下拉框样式 -QW
        combo_style = """
            QComboBox {
                background-color: white;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                padding: 8px 35px 8px 15px;
                color: #2c3e50;
                font-weight: 500;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            QComboBox:focus {
                border-color: #007bff;
                background-color: #f8f9ff;
                outline: none;
            }
            QComboBox:on {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #6c757d;
                margin-right: 10px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #007bff;
            }
            QComboBox::down-arrow:on {
                border-top-color: #007bff;
                border-top: 8px solid #007bff;
                border-bottom: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 8px;
                selection-background-color: #007bff;
                selection-color: white;
                outline: none;
                show-decoration-selected: 1;
                font-size: 12px;
                min-width: 280px;
            }
            QComboBox QAbstractItemView::item {
                height: 40px;
                padding: 8px 15px;
                border: none;
                border-radius: 6px;
                margin: 2px;
                color: #2c3e50;
                background-color: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007bff;
                color: white;
                font-weight: 600;
            }
            QComboBox QAbstractItemView::item:selected:hover {
                background-color: #0056b3;
                color: white;
            }
        """

        self.augment_ide_combo.setStyleSheet(combo_style)
        ide_layout.addWidget(self.augment_ide_combo)

        # 添加弹性空间 -QW
        ide_layout.addStretch()

        # 检测本机IDE按钮 -QW
        self.augment_detect_btn = QtWidgets.QPushButton("检测本机IDE")
        self.augment_detect_btn.setMinimumHeight(40)
        self.augment_detect_btn.setMinimumWidth(120)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        font.setBold(True)
        self.augment_detect_btn.setFont(font)
        self.augment_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        ide_layout.addWidget(self.augment_detect_btn)

        # 重置机器码关闭IDE按钮 -QW
        self.augment_cleanup_btn = QtWidgets.QPushButton("重置机器码关闭IDE")
        self.augment_cleanup_btn.setMinimumHeight(40)
        self.augment_cleanup_btn.setMinimumWidth(180)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        font.setBold(True)
        self.augment_cleanup_btn.setFont(font)
        self.augment_cleanup_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        ide_layout.addWidget(self.augment_cleanup_btn)

        cleanup_layout.addLayout(ide_layout)
        parent_layout.addWidget(cleanup_widget)

        # 连接IDE选择变化事件 -QW
        self.augment_ide_combo.currentTextChanged.connect(self.on_ide_selection_changed)

        # 注意：按钮事件连接在connect_event_handlers方法中统一处理，避免重复连接 -QW

        # 初始化IDE检测 -QW
        self.init_ide_detection()

    def create_email_section_new(self, parent_layout):
        """创建新的获取邮箱区域 -QW"""
        # 创建获取邮箱标题 -QW
        email_title = QtWidgets.QLabel("获取邮箱")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        font.setBold(True)
        email_title.setFont(font)
        email_title.setStyleSheet("color: #333333; margin-bottom: 10px;")
        parent_layout.addWidget(email_title)

        # 创建获取邮箱容器 -QW
        email_widget = QtWidgets.QWidget()
        email_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        email_layout = QtWidgets.QHBoxLayout(email_widget)
        email_layout.setContentsMargins(20, 20, 20, 20)
        email_layout.setSpacing(30)

        # 左侧：账号区域 -QW
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 账号标签 -QW
        account_label = QtWidgets.QLabel("账号")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(12)
        account_label.setFont(font)
        account_label.setStyleSheet("color: #666666;")
        left_layout.addWidget(account_label)

        # 账号输入框容器，包含输入框、下拉按钮和复制按钮 -QW
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
            }
        """)
        input_container.setMinimumHeight(40)
        input_container.setMaximumHeight(40)
        
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 0, 8, 0)
        input_layout.setSpacing(8)
        
        # 账号输入框 -QW
        self.augment_account_input = QtWidgets.QLineEdit()
        self.augment_account_input.setReadOnly(True)
        self.augment_account_input.setFocusPolicy(QtCore.Qt.NoFocus)
        self.augment_account_input.setPlaceholderText("点击获取账号...")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        self.augment_account_input.setFont(font)
        self.augment_account_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        self.augment_account_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        input_layout.addWidget(self.augment_account_input, 1)
        
        # 历史账号下拉按钮 -QW
        self.augment_history_btn = QtWidgets.QPushButton("▼")
        self.augment_history_btn.setStyleSheet("""
            QPushButton {
                color: #999999;
                font-size: 10px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #666666;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 3px;
            }
            QPushButton:pressed {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.augment_history_btn.setFixedSize(16, 16)
        self.augment_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.augment_history_btn.clicked.connect(self.augment_show_history_accounts)
        input_layout.addWidget(self.augment_history_btn, 0)
        
        # 复制账号按钮 -QW
        self.augment_account_copy_icon = QtWidgets.QLabel("📋")
        self.augment_account_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.augment_account_copy_icon.setFixedSize(18, 18)
        self.augment_account_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.augment_account_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.augment_account_copy_icon.mousePressEvent = self.augment_copy_account_icon
        input_layout.addWidget(self.augment_account_copy_icon, 0)
        
        left_layout.addWidget(input_container)

        # 账号按钮布局 -QW
        account_buttons_layout = QtWidgets.QHBoxLayout()
        account_buttons_layout.setSpacing(10)

        # 获取账号按钮 -QW
        self.augment_get_account_btn = QtWidgets.QPushButton("获取账号")
        self.augment_get_account_btn.setMinimumHeight(40)
        self.augment_get_account_btn.setMinimumWidth(100)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        font.setBold(True)
        self.augment_get_account_btn.setFont(font)
        self.augment_get_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        account_buttons_layout.addWidget(self.augment_get_account_btn)

        # 复制账号按钮 -QW
        self.augment_copy_account_btn = QtWidgets.QPushButton("复制账号")
        self.augment_copy_account_btn.setMinimumHeight(40)
        self.augment_copy_account_btn.setMinimumWidth(100)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        self.augment_copy_account_btn.setFont(font)
        self.augment_copy_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #666666;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        account_buttons_layout.addWidget(self.augment_copy_account_btn)

        left_layout.addLayout(account_buttons_layout)
        email_layout.addWidget(left_widget)

        # 右侧：验证码区域 -QW
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 验证码标签 -QW
        code_label = QtWidgets.QLabel("验证码")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(12)
        code_label.setFont(font)
        code_label.setStyleSheet("color: #666666;")
        right_layout.addWidget(code_label)

        # 验证码输入框 -QW
        self.augment_code_input = QtWidgets.QLineEdit()
        self.augment_code_input.setMinimumHeight(40)
        self.augment_code_input.setReadOnly(True)
        self.augment_code_input.setFocusPolicy(QtCore.Qt.NoFocus)
        self.augment_code_input.setPlaceholderText("点击获取验证码...")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        self.augment_code_input.setFont(font)
        self.augment_code_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
            }
            QLineEdit:focus {
                border-color: #28a745;
            }
        """)
        right_layout.addWidget(self.augment_code_input)

        # 验证码按钮布局 -QW
        code_buttons_layout = QtWidgets.QHBoxLayout()
        code_buttons_layout.setSpacing(10)

        # 获取验证码按钮 -QW
        self.augment_get_code_new_btn = QtWidgets.QPushButton("获取验证码")
        self.augment_get_code_new_btn.setMinimumHeight(40)
        self.augment_get_code_new_btn.setMinimumWidth(100)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        font.setBold(True)
        self.augment_get_code_new_btn.setFont(font)
        self.augment_get_code_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
            QPushButton:pressed {
                background-color: #155724;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        code_buttons_layout.addWidget(self.augment_get_code_new_btn)

        # 复制验证码按钮 -QW
        self.augment_copy_code_btn = QtWidgets.QPushButton("复制验证码")
        self.augment_copy_code_btn.setMinimumHeight(40)
        self.augment_copy_code_btn.setMinimumWidth(100)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(11)
        self.augment_copy_code_btn.setFont(font)
        self.augment_copy_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #666666;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        code_buttons_layout.addWidget(self.augment_copy_code_btn)

        right_layout.addLayout(code_buttons_layout)
        email_layout.addWidget(right_widget)

        parent_layout.addWidget(email_widget)

        # 连接按钮事件 -QW
        self.augment_get_account_btn.clicked.connect(self.get_account)
        self.augment_copy_account_btn.clicked.connect(self.copy_account)
        self.augment_get_code_new_btn.clicked.connect(self.get_code)
        self.augment_copy_code_btn.clicked.connect(self.copy_code)



    def check_activation_status(self):
        """检查激活状态 - 引用Cursor标签页的逻辑 -QW"""
        try:
            # 使用与Cursor标签页相同的激活检查逻辑 -QW
            if hasattr(self.main_window, 'get_labl_19'):
                level = self.main_window.get_labl_19()
                print(f"[Augment标签页] 当前会员等级: {level}")

                if level == '青铜':
                    print("[Augment标签页] ❌ 设备未激活")
                    QtWidgets.QMessageBox.warning(None, "提示", "设备未激活")
                    return False
                else:
                    print(f"[Augment标签页] ✅ 设备已激活，等级: {level}")
                    return True

            # 如果主窗口没有get_labl_19方法，尝试其他方法 -QW
            elif hasattr(self.main_window, 'check_activation_status'):
                return self.main_window.check_activation_status()

            # 如果都没有，默认返回True -QW
            print("[Augment标签页] ⚠️ 主窗口没有激活检测方法，默认允许操作")
            return True

        except Exception as e:
            print(f"[Augment标签页] ❌ 激活状态检查失败: {str(e)}")
            # 发生错误时默认返回True，避免阻止用户操作 -QW
            return True

    def copy_account(self):
        """复制账号到剪贴板 -QW"""
        print("[Augment标签页] 📋 复制账号按钮被点击")
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            account = self.augment_account_input.text()
            if account:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(account)

                # 创建自定义对话框，包含Augment官网按钮 -QW
                self._show_copy_success_dialog(account)
                print(f"[Augment标签页] ✅ 账号复制成功: {account}")
            else:
                QtWidgets.QMessageBox.warning(None, "提示", "请先获取账号")
                print("[Augment标签页] ⚠️ 没有账号可复制")
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "错误", f"复制账号失败：{str(e)}")
            print(f"[Augment标签页] ❌ 复制账号失败: {str(e)}")

    def copy_code(self):
        """复制验证码到剪贴板 -QW"""
        print("[Augment标签页] 📋 复制验证码按钮被点击")
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            code = self.augment_code_input.text()
            if code:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(code)
                QtWidgets.QMessageBox.information(None, "复制成功", f"验证码已复制到剪贴板：\n{code}")
                print(f"[Augment标签页] ✅ 验证码复制成功: {code}")
                
                # 复制成功后立即清空验证码显示 -QW
                self._clear_augment_verification_code("复制成功")
            else:
                QtWidgets.QMessageBox.warning(None, "提示", "请先获取验证码")
                print("[Augment标签页] ⚠️ 没有验证码可复制")
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "错误", f"复制验证码失败：{str(e)}")
            print(f"[Augment标签页] ❌ 复制验证码失败: {str(e)}")

    def get_account(self):
        """获取账号 -QW"""
        # ===== 获取账号按钮方法 - 搜索标记: GET_ACCOUNT_METHOD ===== #
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 检查获取账号的10分钟冷却时间 -QW
            if hasattr(self, '_last_get_account_success_time') and self._last_get_account_success_time is not None:
                import time
                current_time = time.time()
                time_diff = current_time - self._last_get_account_success_time
                cooldown_time = 10 * 60  # 10分钟 = 600秒

                if time_diff < cooldown_time:
                    remaining_time = int(cooldown_time - time_diff)
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    QtWidgets.QMessageBox.information(
                        None, "提示",
                        f"获取账号冷却中，请等待 {minutes}分{seconds}秒 后再试"
                    )
                    print(f"[Augment标签页] ⏰ 获取账号冷却中，剩余: {minutes}分{seconds}秒")
                    return

            # 禁用按钮防止重复点击 -QW
            self.augment_get_account_btn.setEnabled(False)
            self.augment_get_account_btn.setText("获取中...")

            print("[Augment标签页] 📧 获取账号按钮被点击")

            # 获取device_code和device_code_md5 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                raise Exception("设备信息未初始化，请重启应用")

            print(
                f"[Augment标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")

            # 调用后端接口获取账号 -QW
            import requests

            # 构造请求URL
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/cursorLoginZs/getCredentialsAm"
            url = f"{base_url}{api_path}?device_code={device_code}&device_code_md5={device_code_md5}"

            print(f"[Augment标签页] 🌐 请求URL: {url}")

            # 发送GET请求
            proxies = {"http": None, "https": None}
            response = requests.get(url, proxies=proxies, timeout=10)

            # 检查响应状态码
            if response.status_code == 200:
                # 解析返回的JSON数据
                data = response.json()
                code = data.get("code")

                if code == '500':
                    error_msg = data.get("msg", "服务器返回错误")
                    raise Exception(f"{error_msg}")

                # 获取账号信息
                result_data = data.get("data")
                if result_data:
                    email = result_data.get("email", "")
                    if email:
                        # 将账号设置到输入框中 -QW
                        self.augment_account_input.setText(email)
                        print(f"[Augment标签页] ✅ 获取账号成功: {email}")
                    else:
                        raise Exception("服务器返回的账号信息为空")
                else:
                    raise Exception("服务器返回的数据格式错误")
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

            # 记录获取账号成功的时间，用于10分钟冷却检查 -QW
            import time
            self._last_get_account_success_time = time.time()
            self._last_get_account_time = time.time()  # 保留原有逻辑用于验证码冷却
            print(f"[Augment标签页] ✅ 获取账号成功，10分钟后可再次获取账号")
            print(f"[Augment标签页] ⏰ 30秒后可获取验证码")

            # 启动获取账号按钮的10分钟倒计时显示 -QW
            self._start_get_account_countdown()

            # 启动获取验证码按钮的30秒倒计时显示 -QW
            self._start_get_code_countdown()

        except Exception as e:
            # 获取失败时恢复按钮状态，不启动倒计时 -QW
            self.augment_get_account_btn.setEnabled(True)
            self.augment_get_account_btn.setText("获取账号")

            # 显示服务器报错信息 -QW
            error_message = str(e)
            QtWidgets.QMessageBox.critical(None, "获取账号失败", error_message)
            print(f"[Augment标签页] ❌ 获取账号失败: {error_message}")

    @QtCore.pyqtSlot(str)
    def update_account_display(self, account):
        """更新账号显示（在主线程中调用） -QW"""
        if account:
            self.augment_account_input.setText(account)
            print(f"[Augment标签页] ✅ 获取账号成功: {account}")
        else:
            self.augment_account_input.setText("")
            self.augment_account_input.setPlaceholderText("获取账号失败，请重试")
            print("[Augment标签页] ❌ 获取账号失败")

        # 恢复按钮状态 -QW
        self.augment_get_account_btn.setEnabled(True)
        self.augment_get_account_btn.setText("获取账号")

    def get_code(self):
        """获取验证码 -QW"""
        # ===== 获取验证码按钮方法 - 搜索标记: GET_CODE_METHOD ===== #
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 检查是否在获取账号后的冷却期内 -QW
            import time
            current_time = time.time()

            # 检查是否有获取账号的时间记录
            if hasattr(self, '_last_get_account_time'):
                time_diff = current_time - self._last_get_account_time
                if time_diff < 30:  # 获取账号后30秒冷却时间
                    remaining_time = int(30 - time_diff)
                    QtWidgets.QMessageBox.information(None, "提示",
                                                      f"请在获取账号后等待 {remaining_time} 秒再获取验证码")
                    print(f"[Augment标签页] ⏰ 获取账号后冷却中，还需等待 {remaining_time} 秒")
                    return
            else:
                # 如果没有获取账号的记录，提示先获取账号
                QtWidgets.QMessageBox.information(None, "提示", "请先获取账号")
                print("[Augment标签页] ⚠️ 请先获取账号")
                return

            # 优先弹出确认弹窗 -QW
            reply = QtWidgets.QMessageBox.question(
                None,
                "确认操作",
                "请先确保您已经使用该邮箱已在Augment官网点击发送验证码按钮。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            # 如果用户点击"否"，则取消操作 -QW
            if reply == QtWidgets.QMessageBox.No:
                print("[Augment标签页] ❌ 用户取消获取验证码操作")
                return

            # 获取邮箱账号 -QW
            email = self.augment_account_input.text().strip()
            if not email:
                QtWidgets.QMessageBox.warning(None, "提示", "请先获取账号")
                return

            # 获取device_code和device_code_md5 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                QtWidgets.QMessageBox.critical(None, "错误", "设备信息未初始化，请重启应用")
                return

            print("[Augment标签页] 🔐 获取验证码按钮被点击，用户已确认")
            print(f"[Augment标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")
            print(f"[Augment标签页] 📧 使用邮箱: {email}")

            # 开始重试获取验证码 -QW
            self._start_verification_code_retry(email, device_code, device_code_md5)

        except Exception as e:
            # 恢复按钮状态 -QW
            self.augment_get_code_new_btn.setEnabled(True)
            self.augment_get_code_new_btn.setText("获取验证码")
            self.augment_get_code_new_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)

            # 显示服务器报错信息 -QW
            error_message = str(e)
            QtWidgets.QMessageBox.critical(None, "获取验证码失败", error_message)
            print(f"[Augment标签页] ❌ 获取验证码失败: {error_message}")

    def _start_verification_code_retry(self, email, device_code, device_code_md5):
        """开始验证码重试流程 -QW"""
        print("[Augment标签页] 🔄 开始验证码重试流程")
        
        # 设置按钮为重试状态 -QW
        self.augment_get_code_new_btn.setEnabled(False)
        self.augment_get_code_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #cccccc;
                color: #666666;
                border: none;
                border-radius: 6px;
            }
        """)
        
        # 初始化重试相关变量 -QW
        self._verification_retry_count = 0
        self._verification_max_retries = 5
        self._verification_retry_interval = 3  # 3秒间隔
        
        # 开始第一次尝试 -QW
        self._attempt_get_verification_code(email, device_code, device_code_md5)

    def _attempt_get_verification_code(self, email, device_code, device_code_md5):
        """尝试获取验证码的单次调用 -QW"""
        self._verification_retry_count += 1
        
        # 更新按钮显示重试次数 -QW
        self.augment_get_code_new_btn.setText(f"获取验证码({self._verification_retry_count}/{self._verification_max_retries})")
        print(f"[Augment标签页] 🔄 第 {self._verification_retry_count} 次尝试获取验证码...")
        
        try:
            import requests

            # 构造请求URL
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/outApi/getEmailCodeAm"
            url = f"{base_url}{api_path}?email={email}&device_code={device_code}&device_code_md5={device_code_md5}"

            print(f"[Augment标签页] 🌐 请求URL: {url}")

            # 发送GET请求
            proxies = {"http": None, "https": None}
            response = requests.get(url, proxies=proxies, timeout=10)

            # 检查响应状态码
            if response.status_code == 200:
                # 解析返回的JSON数据
                data = response.json()
                code = data.get("code")

                if code == '500':
                    error_msg = data.get("msg", "服务器返回错误")
                    raise Exception(f"{error_msg}")

                # 获取验证码
                verification_code = data.get("data")
                if verification_code:
                    # 验证码获取成功 -QW
                    self.augment_code_input.setText(str(verification_code))
                    print(f"[Augment标签页] ✅ 第 {self._verification_retry_count} 次尝试获取验证码成功: {verification_code}")
                    
                    # 启动自动清空定时器 -QW
                    self._start_augment_verification_auto_clear()
                    
                    # 恢复按钮状态 -QW
                    self._restore_verification_button_success()
                    return
                else:
                    raise Exception("服务器返回的验证码为空")
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[Augment标签页] ❌ 第 {self._verification_retry_count} 次尝试失败: {str(e)}")
            
            # 检查是否还有重试次数 -QW
            if self._verification_retry_count < self._verification_max_retries:
                # 还有重试次数，3秒后继续尝试 -QW
                print(f"[Augment标签页] ⏰ {self._verification_retry_interval} 秒后进行第 {self._verification_retry_count + 1} 次尝试...")
                QtCore.QTimer.singleShot(self._verification_retry_interval * 1000, 
                                       lambda: self._attempt_get_verification_code(email, device_code, device_code_md5))
            else:
                # 所有重试都失败了 -QW
                print(f"[Augment标签页] ❌ 所有 {self._verification_max_retries} 次尝试都失败了")
                self._handle_verification_all_failed()

    def _restore_verification_button_success(self):
        """验证码获取成功后恢复按钮状态 -QW"""
        self.augment_get_code_new_btn.setEnabled(True)
        self.augment_get_code_new_btn.setText("获取验证码")
        self.augment_get_code_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

    def _handle_verification_all_failed(self):
        """处理所有验证码获取尝试都失败的情况 -QW"""
        # 恢复按钮状态 -QW
        self.augment_get_code_new_btn.setEnabled(True)
        self.augment_get_code_new_btn.setText("获取验证码")
        self.augment_get_code_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        
        # 显示失败提示弹窗 -QW
        QtWidgets.QMessageBox.critical(
            None, 
            "获取验证码失败", 
            "获取验证码失败，请您确保cursor官网已经发送验证码，并且检查网络后，重新获取验证码"
        )
        print("[Augment标签页] ❌ 显示验证码获取失败提示弹窗")

    @QtCore.pyqtSlot(str)
    def update_code_display(self, code):
        """更新验证码显示（在主线程中调用） -QW"""
        if code:
            self.augment_code_input.setText(code)
            print(f"[Augment标签页] ✅ 获取验证码成功: {code}")
            
            # 启动自动清空定时器 -QW
            self._start_augment_verification_auto_clear()
        else:
            self.augment_code_input.setText("")
            self.augment_code_input.setPlaceholderText("获取验证码失败，请重试")
            print("[Augment标签页] ❌ 获取验证码失败")

        # 恢复按钮状态 -QW
        self.augment_get_code_new_btn.setEnabled(True)
        self.augment_get_code_new_btn.setText("获取验证码")





    def init_ide_detection(self):
        """初始化IDE检测功能 -QW"""
        try:
            # 导入适配器模块 -QW
            from .augment_free_adapter import detect_system_ides

            print("[Augment标签页] 开始检测系统IDE...")
            result = detect_system_ides()

            if result["success"] and result["ides"]:
                print(f"[Augment标签页] ✅ 检测到 {len(result['ides'])} 个IDE")

                # 清空现有选项 -QW
                self.augment_ide_combo.clear()

                # 添加检测到的IDE -QW
                for ide in result["ides"]:
                    display_text = self._format_ide_display_text(ide)
                    self.augment_ide_combo.addItem(display_text, ide)

                # 设置默认选择第一个IDE -QW
                if self.augment_ide_combo.count() > 0:
                    self.augment_ide_combo.setCurrentIndex(0)
                    print(f"[Augment标签页] 默认选择: {self.augment_ide_combo.currentText()}")

            else:
                print("[Augment标签页] ⚠️ IDE检测失败或未检测到IDE，使用默认列表")
                self._add_default_ides()

        except ImportError:
            print("[Augment标签页] ⚠️ 适配器模块不可用，使用默认IDE列表")
            self._add_default_ides()
        except Exception as e:
            print(f"[Augment标签页] ❌ IDE检测失败: {str(e)}")
            self._add_default_ides()

    def _get_ide_icon(self, ide_name):
        """根据IDE名称获取对应的图标 -QW"""
        icon_map = {
            'cursor': '🎯',
            'code': '💙',
            'vscode': '💙',
            'vscodium': '🔷',
            'pycharm': '🐍',
            'webstorm': '🌐',
            'intellij': '💡',
            'idea': '💡',
            'clion': '⚡',
            'phpstorm': '🐘',
            'rubymine': '💎',
            'goland': '🐹',
            'rider': '🏃',
            'datagrip': '🗄️',
            'android studio': '🤖',
            'sublime': '📝',
            'atom': '⚛️',
            'vim': '📄',
            'emacs': '📝',
            'eclipse': '🌙'
        }

        # 查找匹配的图标 -QW
        ide_name_lower = ide_name.lower()
        for key, icon in icon_map.items():
            if key in ide_name_lower:
                return icon

        # 默认图标 -QW
        return '💻'

    def _format_ide_display_text(self, ide):
        """格式化IDE显示文本 -QW"""
        icon = self._get_ide_icon(ide.get('name', ''))
        display_name = ide.get('display_name', ide.get('name', 'Unknown IDE'))

        return f"{icon}  {display_name}"

    def _add_default_ides(self):
        """添加默认IDE选项 -QW"""
        default_ides = [
            {"name": "Cursor", "display_name": "Cursor", "ide_type": "vscode", "config_path": ""},
            {"name": "Code", "display_name": "VS Code", "ide_type": "vscode", "config_path": ""},
            {"name": "VSCodium", "display_name": "VSCodium", "ide_type": "vscode", "config_path": ""},
            {"name": "PyCharm", "display_name": "PyCharm", "ide_type": "jetbrains", "config_path": ""},
            {"name": "WebStorm", "display_name": "WebStorm", "ide_type": "jetbrains", "config_path": ""},
            {"name": "IntelliJ IDEA", "display_name": "IntelliJ IDEA", "ide_type": "jetbrains", "config_path": ""}
        ]

        self.augment_ide_combo.clear()
        for ide in default_ides:
            display_text = self._format_ide_display_text(ide)
            self.augment_ide_combo.addItem(display_text, ide)

        # 设置默认选择第一个IDE -QW
        if self.augment_ide_combo.count() > 0:
            self.augment_ide_combo.setCurrentIndex(0)
            print(f"[Augment标签页] 使用默认IDE列表，默认选择: {self.augment_ide_combo.currentText()}")

    def on_ide_selection_changed(self, text):
        """IDE选择变化时的处理 -QW"""
        if text:
            print(f"[Augment标签页] IDE选择变更为: {text}")
            # 可以在这里添加选择变化时的逻辑 -QW

    def detect_ides_manually(self):
        """手动检测IDE -QW"""
        print("[Augment标签页] 🔍 手动检测IDE按钮被点击")

        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 禁用按钮防止重复点击 -QW
            self.augment_detect_btn.setEnabled(False)
            self.augment_detect_btn.setText("检测中...")

            # 重新初始化IDE检测 -QW
            self.init_ide_detection()

            # 显示检测结果 -QW
            ide_count = self.augment_ide_combo.count()
            if ide_count > 0:
                QtWidgets.QMessageBox.information(
                    None,
                    "检测完成",
                    f"成功检测到 {ide_count} 个IDE\n\n请从下拉列表中选择要操作的IDE。"
                )
                print(f"[Augment标签页] ✅ 检测完成，共找到 {ide_count} 个IDE")
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "检测结果",
                    "未检测到任何IDE\n\n请确保已安装支持的IDE软件。"
                )
                print("[Augment标签页] ⚠️ 未检测到任何IDE")

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "错误", f"IDE检测失败：{str(e)}")
            print(f"[Augment标签页] ❌ IDE检测失败: {str(e)}")

        finally:
            # 恢复按钮状态 -QW
            self.augment_detect_btn.setEnabled(True)
            self.augment_detect_btn.setText("检测本机IDE")

    def reorganize_main_layout(self):
        """重新组织主窗口布局 -QW"""
        print("[标签页管理器] 重新组织主窗口布局")

        try:
            # 清空主布局中剩余的内容 -QW
            while self.main_window.verticalLayout_11.count():
                child = self.main_window.verticalLayout_11.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # 创建主容器 -QW
            main_container = QtWidgets.QWidget()
            main_container.setObjectName("tab_main_container")
            main_container.setStyleSheet("""
                QWidget#tab_main_container {
                    background-color: rgb(248, 252, 254);
                    border-radius: 30px;
                }
            """)
            main_container_layout = QtWidgets.QVBoxLayout(main_container)
            main_container_layout.setContentsMargins(0, 0, 0, 10)
            main_container_layout.setSpacing(0)
            
            # 创建顶部栏（标签按钮 + 最小化/关闭按钮）-QW
            top_bar = QtWidgets.QWidget()
            top_bar.setFixedHeight(42)
            top_bar.setStyleSheet("background-color: transparent;")
            top_bar_layout = QtWidgets.QHBoxLayout(top_bar)
            top_bar_layout.setContentsMargins(12, 8, 12, 0)
            top_bar_layout.setSpacing(8)
            
            # 创建标签按钮 -QW
            self.tab_buttons = {}
            for i in range(self.tab_widget.count()):
                tab_name = self.tab_widget.tabText(i)
                btn = QtWidgets.QPushButton(tab_name)
                btn.setMinimumSize(70, 28)
                btn.setMaximumHeight(28)
                btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                btn.setCheckable(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e8eaed;
                        color: #666666;
                        border: none;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 4px 16px;
                    }
                    QPushButton:checked {
                        background-color: rgb(45, 128, 248);
                        color: white;
                        font-weight: bold;
                    }
                    QPushButton:hover:!checked {
                        background-color: #d0d3d8;
                        color: #333333;
                    }
                """)
                btn.clicked.connect(lambda checked, idx=i: self._on_tab_btn_clicked(idx))
                btn.setVisible(self.tab_widget.isTabVisible(i))
                top_bar_layout.addWidget(btn)
                self.tab_buttons[i] = btn
            
            # 设置第一个可见按钮为选中 -QW
            for idx, btn in self.tab_buttons.items():
                if btn.isVisible():
                    btn.setChecked(True)
                    break
            
            # 添加弹簧 -QW
            top_bar_layout.addStretch()
            
            # 创建最小化按钮 -QW
            self.global_minimize_btn = QtWidgets.QPushButton("−")
            self.global_minimize_btn.setFixedSize(28, 28)
            self.global_minimize_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            self.global_minimize_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                    color: white;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
                }
                QPushButton:pressed {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
                }
            """)
            self.global_minimize_btn.setToolTip("最小化窗口")
            self.global_minimize_btn.clicked.connect(self.minimize_application)
            top_bar_layout.addWidget(self.global_minimize_btn)
            
            # 创建关闭按钮 -QW
            self.global_close_btn = QtWidgets.QPushButton("✕")
            self.global_close_btn.setFixedSize(28, 28)
            self.global_close_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            self.global_close_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                    color: white;
                    border: none;
                    border-radius: 14px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
                }
                QPushButton:pressed {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
                }
            """)
            self.global_close_btn.setToolTip("关闭应用程序")
            self.global_close_btn.clicked.connect(self.close_application)
            top_bar_layout.addWidget(self.global_close_btn)
            
            # 添加顶部栏到主容器 -QW
            main_container_layout.addWidget(top_bar)
            
            # 隐藏QTabWidget内置标签栏 -QW
            self.tab_widget.tabBar().setVisible(False)
            
            # 添加标签页控件到主容器 -QW
            main_container_layout.addWidget(self.tab_widget)
            
            # 添加主容器到主布局 -QW
            self.main_window.verticalLayout_11.addWidget(main_container)
            
            # 确保标签页控件可见 -QW
            self.tab_widget.setVisible(True)
            self.tab_widget.show()
            
            # 设置窗口标题 -QW
            if hasattr(self.main_window, 'setWindowTitle'):
                from tab_config_manager import TabConfigManager
                config_manager = TabConfigManager("config.py")
                config_dict = config_manager.load_config()
                app_version = config_dict.get('app_version')
                window_title = f"Cursor助手 v{app_version} - 多标签页版本"
                self.main_window.setWindowTitle(window_title)
                print(f"[标签页管理器] 🏷️ 窗口标题已设置: {window_title}")
            
            print(f"[标签页管理器] ✅ 主窗口布局重组完成，标签页数量: {self.tab_widget.count()}")
            print(f"[标签页管理器] 标签页名称: {[self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]}")

        except Exception as e:
            print(f"[标签页管理器] ❌ 主窗口布局重组失败: {str(e)}")
            raise

    def _on_tab_btn_clicked(self, tab_index):
        """顶部标签按钮点击事件 -QW"""
        self.tab_widget.setCurrentIndex(tab_index)
        for idx, btn in self.tab_buttons.items():
            btn.setChecked(idx == tab_index)
        self.on_tab_changed(tab_index)
    
    def _update_tab_buttons(self):
        """更新顶部标签按钮可见性 -QW"""
        if not hasattr(self, 'tab_buttons'):
            return
        for idx, btn in self.tab_buttons.items():
            btn.setVisible(self.tab_widget.isTabVisible(idx))

    def connect_events(self):
        """连接事件处理 -QW"""
        print("[标签页管理器] 连接事件处理")

        try:
            # 连接标签页切换事件 -QW
            self.tab_widget.currentChanged.connect(self.on_tab_changed)

            # 连接Augment标签页的按钮事件 -QW
            # 注意：邮箱相关按钮已在create_email_section_new中连接，这里只连接IDE相关按钮 -QW

            if hasattr(self, 'augment_detect_btn') and self.augment_detect_btn:
                self.augment_detect_btn.clicked.connect(self.detect_ides_manually)

            if hasattr(self, 'augment_cleanup_btn') and self.augment_cleanup_btn:
                self.augment_cleanup_btn.clicked.connect(self.execute_cleanup_operations)

            print("[标签页管理器] ✅ 事件连接完成")

        except Exception as e:
            print(f"[标签页管理器] ❌ 事件连接失败: {str(e)}")
            raise

    def on_tab_changed(self, index):
        """标签页切换事件处理 -QW"""
        print(f"[标签页管理器] 标签页切换到索引: {index}")
        
        # 获取当前标签页的名称 -QW
        if index >= 0 and index < self.tab_widget.count():
            tab_name = self.tab_widget.tabText(index)
            print(f"[标签页管理器] 切换到标签页: {tab_name}")
            
            # 根据标签页名称执行相应操作 -QW
            if tab_name == "Cursor":
                print("[标签页管理器] 切换到Cursor标签页")
            elif tab_name == "Augment":
                print("[标签页管理器] 切换到Augment标签页")
            elif tab_name == "cursor账号":
                print("[标签页管理器] 切换到cursor账号标签页")
                # 每次切换到cursor账号标签页时，刷新公告内容 -QW
                if hasattr(self, 'refresh_cursor_notice'):
                    self.refresh_cursor_notice()
            elif tab_name == "历史账号":
                print("[标签页管理器] 切换到历史账号标签页，刷新列表")
                # 每次切换到历史账号标签页时，刷新列表 -QW
                if hasattr(self, 'refresh_history_accounts'):
                    self.refresh_history_accounts()
            elif tab_name == "Windsurf":
                print("[标签页管理器] 切换到Windsurf标签页")
        else:
            print(f"[标签页管理器] ⚠️ 无效的标签页索引: {index}")





    def execute_cleanup_operations(self):
        """执行清理操作 -QW"""
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 获取选中的IDE -QW
            current_index = self.augment_ide_combo.currentIndex()
            if current_index < 0:
                QtWidgets.QMessageBox.warning(None, "警告", "请先选择要清理的IDE")
                return

            ide_data = self.augment_ide_combo.itemData(current_index)
            if not ide_data:
                QtWidgets.QMessageBox.warning(None, "警告", "无效的IDE选择")
                return

            # 第一步：提醒用户关闭编辑器 -QW
            close_editor_msg = QtWidgets.QMessageBox()
            close_editor_msg.setWindowTitle("重要提醒")
            close_editor_msg.setIcon(QtWidgets.QMessageBox.Warning)
            close_editor_msg.setText(f"请先关闭 {ide_data['display_name']} 编辑器")
            close_editor_msg.setInformativeText(
                f"在执行重置机器码操作前，请确保已完全关闭 {ide_data['display_name']} 编辑器客户端。\n\n"
                "这是为了确保清理操作能够正常进行，避免文件被占用。"
            )

            # 添加自定义按钮 -QW
            already_closed_btn = close_editor_msg.addButton("已关闭", QtWidgets.QMessageBox.AcceptRole)
            go_close_btn = close_editor_msg.addButton("我去关闭", QtWidgets.QMessageBox.RejectRole)
            close_editor_msg.setDefaultButton(go_close_btn)

            # 显示对话框并获取用户选择 -QW
            close_editor_msg.exec_()
            clicked_button = close_editor_msg.clickedButton()

            if clicked_button == go_close_btn:
                print(f"[Augment标签页] 用户选择去关闭 {ide_data['display_name']}")
                return  # 用户选择去关闭，退出操作
            elif clicked_button == already_closed_btn:
                print(f"[Augment标签页] 用户确认已关闭 {ide_data['display_name']}")
                # 继续执行清理操作
            else:
                return  # 用户关闭了对话框，退出操作

            # 第二步：确认清理操作 -QW
            reply = QtWidgets.QMessageBox.question(
                None, "确认清理",
                f"确定要清理 {ide_data['display_name']} 的机器码吗？\n\n此操作将：\n• 重置遥测ID\n• 清理配置数据\n• 删除工作区缓存",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply != QtWidgets.QMessageBox.Yes:
                return

            print(f"[Augment标签页] 开始清理 {ide_data['display_name']}...")
            self.augment_cleanup_btn.setText("清理中...")
            self.augment_cleanup_btn.setEnabled(False)

            # 执行清理操作 -QW
            try:
                from .augment_free_adapter import cleanup_ide_data
                result = cleanup_ide_data(ide_data)

                if result["success"]:
                    QtWidgets.QMessageBox.information(None, "清理完成", f"✅ {ide_data['display_name']} 清理完成")
                    print(f"[Augment标签页] ✅ {ide_data['display_name']} 清理成功")
                else:
                    QtWidgets.QMessageBox.warning(None, "清理失败", f"❌ {result.get('message', '清理失败')}")
                    print(f"[Augment标签页] ❌ {ide_data['display_name']} 清理失败")

            except ImportError:
                QtWidgets.QMessageBox.critical(None, "模块错误", "❌ 清理模块不可用")
                print("[Augment标签页] ❌ 清理模块不可用")

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "操作失败", f"❌ 清理操作失败: {str(e)}")
            print(f"[Augment标签页] ❌ 清理操作失败: {str(e)}")
        finally:
            self.augment_cleanup_btn.setText("清理机器码")
            self.augment_cleanup_btn.setEnabled(True)

    def _start_get_code_countdown(self):
        """启动获取验证码按钮的倒计时显示 -QW"""
        try:
            # 禁用获取验证码按钮 -QW
            self.augment_get_code_new_btn.setEnabled(False)

            # 创建定时器 -QW
            self._countdown_timer = QtCore.QTimer()
            self._countdown_timer.timeout.connect(self._update_get_code_countdown)

            # 初始化倒计时 -QW
            self._countdown_seconds = 30
            self._update_get_code_countdown()

            # 每秒更新一次 -QW
            self._countdown_timer.start(1000)

            print("[Augment标签页] ⏰ 获取验证码按钮倒计时已启动")

        except Exception as e:
            print(f"[Augment标签页] ❌ 启动倒计时失败: {str(e)}")

    def _update_get_code_countdown(self):
        """更新获取验证码按钮的倒计时显示 -QW"""
        try:
            if self._countdown_seconds > 0:
                # 显示倒计时 -QW
                self.augment_get_code_new_btn.setText(f"获取验证码({self._countdown_seconds}s)")
                self._countdown_seconds -= 1
            else:
                # 倒计时结束，恢复按钮 -QW
                self._stop_get_code_countdown()

        except Exception as e:
            print(f"[Augment标签页] ❌ 更新倒计时失败: {str(e)}")
            self._stop_get_code_countdown()

    def _stop_get_code_countdown(self):
        """停止获取验证码按钮的倒计时 -QW"""
        try:
            # 停止定时器 -QW
            if hasattr(self, '_countdown_timer') and self._countdown_timer:
                self._countdown_timer.stop()
                self._countdown_timer = None

            # 恢复按钮状态 -QW
            self.augment_get_code_new_btn.setEnabled(True)
            self.augment_get_code_new_btn.setText("获取验证码")

            print("[Augment标签页] ✅ 获取验证码按钮倒计时已结束，按钮已恢复")

        except Exception as e:
            print(f"[Augment标签页] ❌ 停止倒计时失败: {str(e)}")

    def _start_get_account_countdown(self):
        """启动获取账号按钮的10分钟倒计时显示 -QW"""
        try:
            # 禁用获取账号按钮 -QW
            self.augment_get_account_btn.setEnabled(False)

            # 创建定时器 -QW
            self._account_countdown_timer = QtCore.QTimer()
            self._account_countdown_timer.timeout.connect(self._update_get_account_countdown)

            # 初始化倒计时（10分钟 = 600秒）-QW
            self._account_countdown_seconds = 10 * 60
            self._update_get_account_countdown()

            # 每秒更新一次 -QW
            self._account_countdown_timer.start(1000)

            print("[Augment标签页] ⏰ 获取账号按钮10分钟倒计时已启动")

        except Exception as e:
            print(f"[Augment标签页] ❌ 启动获取账号倒计时失败: {str(e)}")

    def _update_get_account_countdown(self):
        """更新获取账号按钮的倒计时显示 -QW"""
        try:
            if self._account_countdown_seconds > 0:
                # 计算分钟和秒数 -QW
                minutes = self._account_countdown_seconds // 60
                seconds = self._account_countdown_seconds % 60

                # 显示倒计时 -QW
                self.augment_get_account_btn.setText(f"获取账号({minutes}分{seconds}秒)")
                self._account_countdown_seconds -= 1
            else:
                # 倒计时结束，恢复按钮 -QW
                self._stop_get_account_countdown()

        except Exception as e:
            print(f"[Augment标签页] ❌ 更新获取账号倒计时失败: {str(e)}")
            self._stop_get_account_countdown()

    def _stop_get_account_countdown(self):
        """停止获取账号按钮的倒计时 -QW"""
        try:
            # 停止定时器 -QW
            if hasattr(self, '_account_countdown_timer') and self._account_countdown_timer:
                self._account_countdown_timer.stop()
                self._account_countdown_timer = None

            # 恢复按钮状态 -QW
            self.augment_get_account_btn.setEnabled(True)
            self.augment_get_account_btn.setText("获取账号")

            print("[Augment标签页] ✅ 获取账号按钮倒计时已结束，按钮已恢复")

        except Exception as e:
            print(f"[Augment标签页] ❌ 停止获取账号倒计时失败: {str(e)}")

    def _show_account_usage_warning_dialog(self):
        """显示账号使用提醒弹窗 -QW"""
        try:
            # 创建自定义消息框 -QW
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("账号使用提醒")
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setText("获取新账号前请确认")
            msg_box.setInformativeText("请您先确保上个账号使用完，账号有单独的有效期，如果没有使用完，可以点击倒三角选择历史账号")
            
            # 添加自定义按钮 -QW
            used_button = msg_box.addButton("获取新账号", QtWidgets.QMessageBox.AcceptRole)
            history_button = msg_box.addButton("我去选择历史账号", QtWidgets.QMessageBox.RejectRole)
            
            # 设置默认按钮 -QW
            msg_box.setDefaultButton(used_button)
            
            # 显示对话框并获取用户选择 -QW
            msg_box.exec_()
            clicked_button = msg_box.clickedButton()
            
            # 处理用户选择 -QW
            if clicked_button == used_button:
                print("[Cursor账号标签页] ✅ 用户确认已使用完上个账号，继续获取新账号")
                return "continue"
            elif clicked_button == history_button:
                print("[Cursor账号标签页] 📋 用户选择查看历史账号，停止获取新账号")
                return "stop"
            else:
                # 默认情况（如用户关闭对话框）
                print("[Cursor账号标签页] ❌ 用户关闭对话框，停止获取新账号")
                return "stop"
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 显示账号使用提醒弹窗失败: {str(e)}")
            # 发生错误时默认继续执行，避免阻塞用户操作
            return "continue"

    def _show_copy_success_dialog(self, account):
        """显示复制成功对话框，包含Augment官网按钮 -QW"""
        try:
            # 创建自定义消息框 -QW
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("复制成功")
            msg_box.setIcon(QtWidgets.QMessageBox.Information)
            msg_box.setText("账号已复制到剪贴板")
            msg_box.setInformativeText(f"复制的账号：{account}")

            # 添加自定义按钮 -QW
            ok_button = msg_box.addButton("确定", QtWidgets.QMessageBox.AcceptRole)
            website_button = msg_box.addButton("Augment官网", QtWidgets.QMessageBox.ActionRole)

            # 设置默认按钮 -QW
            msg_box.setDefaultButton(ok_button)

            # 显示对话框并获取用户选择 -QW
            msg_box.exec_()
            clicked_button = msg_box.clickedButton()

            # 处理用户选择 -QW
            if clicked_button == website_button:
                self._open_augment_website()
                print("[Augment标签页] 🌐 用户点击了Augment官网按钮")
            elif clicked_button == ok_button:
                print("[Augment标签页] ✅ 用户确认复制成功")

        except Exception as e:
            print(f"[Augment标签页] ❌ 显示复制成功对话框失败: {str(e)}")
            # 如果自定义对话框失败，使用简单的信息框 -QW
            QtWidgets.QMessageBox.information(None, "复制成功", f"账号已复制到剪贴板：\n{account}")

    def _open_augment_website(self):
        """打开Augment官网 -QW"""
        try:
            import webbrowser
            url = "https://www.augmentcode.com/"
            webbrowser.open(url)
            print(f"[Augment标签页] 🌐 正在打开Augment官网: {url}")

        except Exception as e:
            print(f"[Augment标签页] ❌ 打开官网失败: {str(e)}")
            # 如果打开失败，显示URL让用户手动复制 -QW
            QtWidgets.QMessageBox.information(
                None, "官网链接",
                "无法自动打开浏览器，请手动访问：\nhttps://www.augmentcode.com/"
            )

    def minimize_application(self):
        """最小化应用程序 -QW"""
        try:
            print("[标签页管理器] 📉 用户点击最小化按钮")

            # 最小化主窗口 -QW
            if hasattr(self.main_window, 'showMinimized'):
                self.main_window.showMinimized()
                print("[标签页管理器] ✅ 应用程序已最小化")
            else:
                print("[标签页管理器] ⚠️ 主窗口没有showMinimized方法")

        except Exception as e:
            print(f"[标签页管理器] ❌ 最小化应用程序失败: {str(e)}")

    def close_application(self):
        """关闭应用程序 -QW"""
        try:
            print("[标签页管理器] 🔴 用户点击关闭按钮")

            # 创建确认对话框 -QW
            reply = QtWidgets.QMessageBox.question(
                None, "确认退出",
                "确定要退出应用程序吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                print("[标签页管理器] ✅ 用户确认退出，正在关闭应用程序")

                # 清理资源 -QW
                if hasattr(self, '_countdown_timer') and self._countdown_timer:
                    self._countdown_timer.stop()
                if hasattr(self, '_account_countdown_timer') and self._account_countdown_timer:
                    self._account_countdown_timer.stop()

                # 退出应用程序 -QW
                QtWidgets.QApplication.quit()
            else:
                print("[标签页管理器] ❌ 用户取消退出")

        except Exception as e:
            print(f"[标签页管理器] ❌ 关闭应用程序失败: {str(e)}")
            # 如果出错，直接退出 -QW
            QtWidgets.QApplication.quit()

    def create_cursor_account_tab_content(self):
        """创建Cursor账号标签页内容 -QW"""
        print("[标签页管理器] 创建Cursor账号标签页内容")

        # 设置Cursor账号标签页背景色 -QW
        self.cursor_account_tab.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)

        # 创建主布局 -QW
        main_layout = QtWidgets.QVBoxLayout(self.cursor_account_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建顶部按钮区域 -QW
        self.create_cursor_account_top_buttons(main_layout)

        # 创建主要内容区域 -QW
        self.create_cursor_account_main_content(main_layout)

    def create_cursor_account_top_buttons(self, parent_layout):
        """创建Cursor账号标签页顶部按钮区域 -QW"""
        # 创建顶部区域，包含最小化和关闭按钮 -QW
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)

        # 添加弹性空间，将按钮推到右边 -QW
        top_layout.addStretch()

        # 创建最小化按钮 -QW
        self.cursor_account_minimize_btn = QtWidgets.QPushButton("−")
        self.cursor_account_minimize_btn.setFixedSize(30, 30)
        self.cursor_account_minimize_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.cursor_account_minimize_btn.setToolTip("最小化窗口")
        self.cursor_account_minimize_btn.clicked.connect(self.minimize_application)

        # 创建关闭按钮 -QW
        self.cursor_account_close_btn = QtWidgets.QPushButton("✕")
        self.cursor_account_close_btn.setFixedSize(30, 30)
        self.cursor_account_close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.cursor_account_close_btn.setToolTip("关闭应用程序")
        self.cursor_account_close_btn.clicked.connect(self.close_application)

        # 添加按钮到布局 -QW
        top_layout.addWidget(self.cursor_account_minimize_btn)
        top_layout.addSpacing(5)
        top_layout.addWidget(self.cursor_account_close_btn)

        parent_layout.addWidget(top_widget)

    def create_cursor_account_main_content(self, parent_layout):
        """创建完全按照设计图的Cursor账号标签页主要内容 -QW"""
        # 创建主容器，完全按照设计图 -QW
        main_container = QtWidgets.QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                padding: 0px;
                margin: 0px;
            }
        """)

        # 创建主布局，严格按照设计图间距 -QW
        main_layout = QtWidgets.QVBoxLayout(main_container)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(30)

        # 创建服务器维护公告区域 -QW
        self.create_notice_area_design(main_layout)

        # 创建获取邮箱标题，严格按照设计图 -QW
        email_title = QtWidgets.QLabel("获取邮箱")
        email_title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        main_layout.addWidget(email_title)

        # 创建三列水平布局 (账号、验证码、密码并排显示) -QW
        columns_widget = QtWidgets.QWidget()
        columns_layout = QtWidgets.QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(20)  # 三列之间的间距

        # 创建三个独立的列 -QW
        self.create_account_column(columns_layout)      # 账号列
        self.create_verification_column(columns_layout) # 验证码列
        self.create_password_column(columns_layout)     # 密码列

        main_layout.addWidget(columns_widget)

        # 创建底部按钮行 -QW
        self.create_bottom_buttons_row(main_layout)

        # 添加底部弹性空间 -QW
        main_layout.addStretch()

        parent_layout.addWidget(main_container)

    def create_notice_area_design(self, parent_layout):
        """创建完全按照设计图的公告区域 -QW"""
        # 创建公告区域容器 -QW
        notice_container = QtWidgets.QWidget()
        notice_layout = QtWidgets.QVBoxLayout(notice_container)
        notice_layout.setContentsMargins(0, 0, 0, 0)
        notice_layout.setSpacing(15)

        # 公告标题 -QW
        title_label = QtWidgets.QLabel("公告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        notice_layout.addWidget(title_label)

        # 公告内容文本框，严格按照设计图 -QW
        self.cursor_notice_text = QtWidgets.QTextEdit()
        self.cursor_notice_text.setPlainText("正在加载公告内容...")
        # 设置为只读，不可修改和不可选中 -QW
        self.cursor_notice_text.setReadOnly(True)
        self.cursor_notice_text.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.cursor_notice_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                color: #666666;
                line-height: 1.5;
            }
        """)
        self.cursor_notice_text.setMinimumHeight(120)
        self.cursor_notice_text.setMaximumHeight(120)
        notice_layout.addWidget(self.cursor_notice_text)

        parent_layout.addWidget(notice_container)
        
        # 首次加载公告内容 -QW
        self.refresh_cursor_notice()

    def refresh_cursor_notice(self):
        """刷新cursor账号标签页的公告内容 -QW"""
        try:
            print("[Cursor账号标签页] 🔄 开始刷新公告内容...")
            
            # 构造请求URL -QW
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/cursorLoginZs/getDlLx"
            dl_id = "996c8b97292742f4959dd545hl7879hkh"
            url = f"{base_url}{api_path}?dl_id={dl_id}"
            
            print(f"[Cursor账号标签页] 🌐 请求URL: {url}")
            
            # 发送GET请求 -QW
            import requests
            proxies = {"http": None, "https": None}
            response = requests.get(url, proxies=proxies, timeout=10)
            
            # 检查响应状态码 -QW
            if response.status_code == 200:
                data = response.json()
                print(f"[Cursor账号标签页] 📨 API响应: {data}")
                
                # 解析公告内容，直接从响应中获取scLx字段 -QW
                # 检查是否有code字段，如果有则按原逻辑处理，如果没有则直接解析 -QW
                if "code" in data:
                    # 有code字段的情况 -QW
                    if data.get("code") == "200" or data.get("code") == 200:
                        data_content = data.get("data", {})
                        notice_content = data_content.get("scLx", "") if isinstance(data_content, dict) else ""
                    else:
                        notice_content = ""
                        error_msg = data.get("message", "未知错误")
                        print(f"[Cursor账号标签页] ❌ API返回错误: {error_msg}")
                else:
                    # 没有code字段，直接从响应中获取scLx字段 -QW
                    notice_content = data.get("scLx", "")
                
                if notice_content:
                    # 更新公告内容 -QW
                    self.cursor_notice_text.setPlainText(notice_content)
                    print(f"[Cursor账号标签页] ✅ 公告内容更新成功(scLx): {notice_content[:50]}...")
                else:
                    # 如果没有内容，显示默认信息 -QW
                    self.cursor_notice_text.setPlainText("暂无公告内容")
                    print("[Cursor账号标签页] ⚠️ scLx字段为空或不存在")
            else:
                # HTTP状态码错误 -QW
                error_msg = f"HTTP {response.status_code}"
                self.cursor_notice_text.setPlainText(f"获取公告失败: {error_msg}")
                print(f"[Cursor账号标签页] ❌ HTTP请求失败: {error_msg}")
                
        except Exception as e:
            # 请求异常处理 -QW
            error_msg = str(e)
            self.cursor_notice_text.setPlainText(f"网络连接失败: {error_msg}")
            print(f"[Cursor账号标签页] ❌ 刷新公告异常: {error_msg}")
            import traceback
            traceback.print_exc()

    def create_left_email_area_design(self, parent_layout):
        """创建完全按照设计图的左侧账号区域 -QW"""
        # 创建左侧容器 -QW
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 账号标签，严格按照设计图 -QW
        account_label = QtWidgets.QLabel("账号")
        account_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        left_layout.addWidget(account_label)

        # 创建账号输入框容器，包含输入框和下拉箭头 -QW
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        input_container.setMinimumHeight(50)
        input_container.setMaximumHeight(50)
        
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 0, 10, 0)
        input_layout.setSpacing(8)

        # 账号输入框，无边框样式，设置为不可操作和不可选中 -QW
        self.cursor_account_input = QtWidgets.QLineEdit()
        self.cursor_account_input.setPlaceholderText("请输入账号")
        # 设置为只读，不可修改 -QW
        self.cursor_account_input.setReadOnly(True)
        self.cursor_account_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保账号完全显示 -QW
        self.cursor_account_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        input_layout.addWidget(self.cursor_account_input, 1)  # 设置拉伸因子为1

        # 下拉箭头按钮，可点击显示历史账号 -QW
        self.cursor_history_btn = QtWidgets.QPushButton("▼")
        self.cursor_history_btn.setStyleSheet("""
            QPushButton {
                color: #999999;
                font-size: 10px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #666666;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 3px;
            }
            QPushButton:pressed {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.cursor_history_btn.setFixedSize(16, 16)
        self.cursor_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_history_btn.clicked.connect(self.show_history_accounts)
        input_layout.addWidget(self.cursor_history_btn, 0)  # 不拉伸

        # 账号复制图标，严格按照设计图 -QW
        self.cursor_account_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_account_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_account_copy_icon.setFixedSize(18, 18)
        self.cursor_account_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_account_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_account_copy_icon.mousePressEvent = self.cursor_copy_account
        input_layout.addWidget(self.cursor_account_copy_icon, 0)  # 不拉伸

        left_layout.addWidget(input_container)

        # 获取账号按钮，严格按照设计图颜色和尺寸 -QW
        self.cursor_get_account_btn = QtWidgets.QPushButton("获取账号")
        self.cursor_get_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 32px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2851a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999999;
            }
        """)
        self.cursor_get_account_btn.setMinimumHeight(50)
        self.cursor_get_account_btn.setMaximumHeight(50)
        left_layout.addWidget(self.cursor_get_account_btn)
        
        # 连接获取账号按钮点击事件 -QW
        self.cursor_get_account_btn.clicked.connect(self.cursor_get_account)
        
        # 检查是否处于冷却期并启动倒计时显示 -QW
        self._check_cursor_account_cooldown_on_init()

        # 添加底部弹性空间 -QW
        left_layout.addStretch()

        parent_layout.addWidget(left_widget)

    def create_right_code_area_design(self, parent_layout):
        """创建完全按照设计图的右侧验证码区域 -QW"""
        # 创建右侧容器 -QW
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # 验证码标签，严格按照设计图 -QW
        code_label = QtWidgets.QLabel("验证码")
        code_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        right_layout.addWidget(code_label)

        # 创建验证码输入框容器，包含输入框和复制图标 -QW
        code_container = QtWidgets.QWidget()
        code_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        code_container.setMinimumHeight(50)
        code_container.setMaximumHeight(50)
        
        code_layout = QtWidgets.QHBoxLayout(code_container)
        code_layout.setContentsMargins(15, 0, 10, 0)
        code_layout.setSpacing(8)

        # 验证码输入框，无边框样式，设置为不可修改和不可选中 -QW
        self.cursor_verification_input = QtWidgets.QLineEdit()
        self.cursor_verification_input.setPlaceholderText("请输入验证码")
        # 设置为只读，不可修改和不可选中 -QW
        self.cursor_verification_input.setReadOnly(True)
        self.cursor_verification_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保验证码完全显示 -QW
        self.cursor_verification_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        code_layout.addWidget(self.cursor_verification_input, 1)  # 设置拉伸因子为1

        # 复制图标，严格按照设计图 -QW
        self.cursor_code_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_code_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_code_copy_icon.setFixedSize(18, 18)
        self.cursor_code_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_code_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_code_copy_icon.mousePressEvent = self.cursor_copy_code
        code_layout.addWidget(self.cursor_code_copy_icon, 0)  # 不拉伸

        right_layout.addWidget(code_container)

        # 获取验证码按钮，严格按照设计图颜色和尺寸 -QW
        self.cursor_get_verification_btn = QtWidgets.QPushButton("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 32px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2d8f47;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999999;
            }
        """)
        self.cursor_get_verification_btn.setMinimumHeight(50)
        self.cursor_get_verification_btn.setMaximumHeight(50)
        right_layout.addWidget(self.cursor_get_verification_btn)
        
        # 连接获取验证码按钮点击事件 -QW
        self.cursor_get_verification_btn.clicked.connect(self.cursor_get_verification_code)
        
        # 检查验证码按钮是否处于冷却期并启动倒计时显示 -QW
        self._check_cursor_verification_cooldown_on_init()

        # ====== 密码区域 ====== -QW
        # 密码标签，严格按照设计图 -QW
        password_label = QtWidgets.QLabel("密码")
        password_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        right_layout.addWidget(password_label)

        # 创建密码输入框容器，包含输入框和复制图标 -QW
        password_container = QtWidgets.QWidget()
        password_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        password_container.setMinimumHeight(50)
        password_container.setMaximumHeight(50)
        
        password_layout = QtWidgets.QHBoxLayout(password_container)
        password_layout.setContentsMargins(15, 0, 10, 0)
        password_layout.setSpacing(8)

        # 密码输入框，无边框样式，设置为不可修改和不可选中 -QW
        self.cursor_password_input = QtWidgets.QLineEdit()
        self.cursor_password_input.setPlaceholderText("请输入密码")
        # 设置为只读，不可修改和不可选中 -QW
        self.cursor_password_input.setReadOnly(True)
        self.cursor_password_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保密码完全显示 -QW
        self.cursor_password_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        password_layout.addWidget(self.cursor_password_input, 1)  # 设置拉伸因子为1

        # 密码复制图标，严格按照设计图 -QW
        self.cursor_password_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_password_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_password_copy_icon.setFixedSize(18, 18)
        self.cursor_password_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_password_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_password_copy_icon.mousePressEvent = self.cursor_copy_password
        password_layout.addWidget(self.cursor_password_copy_icon, 0)  # 不拉伸

        right_layout.addWidget(password_container)

        # 获取密码按钮已移除 -QW (旧布局方法，已弃用)
        # self.cursor_get_password_btn = QtWidgets.QPushButton("获取密码")
        # right_layout.addWidget(self.cursor_get_password_btn)
        # self.cursor_get_password_btn.clicked.connect(self.cursor_get_password)

        # 添加底部弹性空间 -QW
        right_layout.addStretch()

        parent_layout.addWidget(right_widget)

    def create_account_column(self, parent_layout):
        """创建账号列 -QW"""
        # 创建账号列容器 -QW
        account_widget = QtWidgets.QWidget()
        account_layout = QtWidgets.QVBoxLayout(account_widget)
        account_layout.setContentsMargins(0, 0, 0, 0)
        account_layout.setSpacing(15)

        # 账号标签 -QW
        account_label = QtWidgets.QLabel("账号")
        account_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        account_layout.addWidget(account_label)

        # 创建账号输入框容器 -QW
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        input_container.setMinimumHeight(50)
        input_container.setMaximumHeight(50)
        
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 0, 10, 0)
        input_layout.setSpacing(8)

        # 账号输入框 -QW
        self.cursor_account_input = QtWidgets.QLineEdit()
        self.cursor_account_input.setPlaceholderText("请输入账号")
        self.cursor_account_input.setReadOnly(True)
        self.cursor_account_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        self.cursor_account_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        input_layout.addWidget(self.cursor_account_input, 1)

        # 下拉箭头按钮 -QW
        self.cursor_history_btn = QtWidgets.QPushButton("▼")
        self.cursor_history_btn.setStyleSheet("""
            QPushButton {
                color: #999999;
                font-size: 10px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #666666;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 3px;
            }
            QPushButton:pressed {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.cursor_history_btn.setFixedSize(16, 16)
        self.cursor_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_history_btn.clicked.connect(self.show_history_accounts)
        input_layout.addWidget(self.cursor_history_btn, 0)

        # 账号复制图标 -QW
        self.cursor_account_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_account_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_account_copy_icon.setFixedSize(18, 18)
        self.cursor_account_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_account_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_account_copy_icon.mousePressEvent = self.cursor_copy_account
        input_layout.addWidget(self.cursor_account_copy_icon, 0)

        account_layout.addWidget(input_container)
        account_layout.addStretch()  # 添加弹性空间

        parent_layout.addWidget(account_widget, 1)  # 设置为等宽

    def create_verification_column(self, parent_layout):
        """创建验证码列 -QW"""
        # 创建验证码列容器 -QW
        verification_widget = QtWidgets.QWidget()
        verification_layout = QtWidgets.QVBoxLayout(verification_widget)
        verification_layout.setContentsMargins(0, 0, 0, 0)
        verification_layout.setSpacing(15)

        # 验证码标签 -QW
        verification_label = QtWidgets.QLabel("验证码")
        verification_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        verification_layout.addWidget(verification_label)

        # 创建验证码输入框容器 -QW
        code_container = QtWidgets.QWidget()
        code_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        code_container.setMinimumHeight(50)
        code_container.setMaximumHeight(50)
        
        code_layout = QtWidgets.QHBoxLayout(code_container)
        code_layout.setContentsMargins(15, 0, 10, 0)
        code_layout.setSpacing(8)

        # 验证码输入框 -QW
        self.cursor_verification_input = QtWidgets.QLineEdit()
        self.cursor_verification_input.setPlaceholderText("请输入验证码")
        self.cursor_verification_input.setReadOnly(True)
        self.cursor_verification_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        self.cursor_verification_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        code_layout.addWidget(self.cursor_verification_input, 1)

        # 验证码复制图标 -QW
        self.cursor_code_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_code_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_code_copy_icon.setFixedSize(18, 18)
        self.cursor_code_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_code_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_code_copy_icon.mousePressEvent = self.cursor_copy_code
        code_layout.addWidget(self.cursor_code_copy_icon, 0)

        verification_layout.addWidget(code_container)
        verification_layout.addStretch()  # 添加弹性空间

        parent_layout.addWidget(verification_widget, 1)  # 设置为等宽

    def create_password_column(self, parent_layout):
        """创建密码列 -QW"""
        # 创建密码列容器 -QW
        password_widget = QtWidgets.QWidget()
        password_layout = QtWidgets.QVBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(15)

        # 密码标签 -QW
        password_label = QtWidgets.QLabel("密码")
        password_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        password_layout.addWidget(password_label)

        # 创建密码输入框容器 -QW
        password_container = QtWidgets.QWidget()
        password_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        password_container.setMinimumHeight(50)
        password_container.setMaximumHeight(50)
        
        password_layout_inner = QtWidgets.QHBoxLayout(password_container)
        password_layout_inner.setContentsMargins(15, 0, 10, 0)
        password_layout_inner.setSpacing(8)

        # 密码输入框 -QW
        self.cursor_password_input = QtWidgets.QLineEdit()
        self.cursor_password_input.setPlaceholderText("请输入密码")
        self.cursor_password_input.setReadOnly(True)
        self.cursor_password_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        self.cursor_password_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        password_layout_inner.addWidget(self.cursor_password_input, 1)

        # 密码复制图标 -QW
        self.cursor_password_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_password_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_password_copy_icon.setFixedSize(18, 18)
        self.cursor_password_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_password_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_password_copy_icon.mousePressEvent = self.cursor_copy_password
        password_layout_inner.addWidget(self.cursor_password_copy_icon, 0)

        password_layout.addWidget(password_container)
        password_layout.addStretch()  # 添加弹性空间

        parent_layout.addWidget(password_widget, 1)  # 设置为等宽

    def create_left_email_area_design_no_button(self, parent_layout):
        """创建左侧账号区域 (不包含按钮) -QW"""
        # 创建左侧容器 -QW
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 账号标签，严格按照设计图 -QW
        account_label = QtWidgets.QLabel("账号")
        account_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        left_layout.addWidget(account_label)

        # 创建账号输入框容器，包含输入框和下拉箭头 -QW
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        input_container.setMinimumHeight(50)
        input_container.setMaximumHeight(50)
        
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 0, 10, 0)
        input_layout.setSpacing(8)

        # 账号输入框，无边框样式，设置为不可操作和不可选中 -QW
        self.cursor_account_input = QtWidgets.QLineEdit()
        self.cursor_account_input.setPlaceholderText("请输入账号")
        # 设置为只读，不可修改 -QW
        self.cursor_account_input.setReadOnly(True)
        self.cursor_account_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保账号完全显示 -QW
        self.cursor_account_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        input_layout.addWidget(self.cursor_account_input, 1)  # 设置拉伸因子为1

        # 下拉箭头按钮，可点击显示历史账号 -QW
        self.cursor_history_btn = QtWidgets.QPushButton("▼")
        self.cursor_history_btn.setStyleSheet("""
            QPushButton {
                color: #999999;
                font-size: 10px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #666666;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 3px;
            }
            QPushButton:pressed {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.cursor_history_btn.setFixedSize(16, 16)
        self.cursor_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_history_btn.clicked.connect(self.show_history_accounts)
        input_layout.addWidget(self.cursor_history_btn, 0)  # 不拉伸

        # 账号复制图标，严格按照设计图 -QW
        self.cursor_account_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_account_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_account_copy_icon.setFixedSize(18, 18)
        self.cursor_account_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_account_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_account_copy_icon.mousePressEvent = self.cursor_copy_account
        input_layout.addWidget(self.cursor_account_copy_icon, 0)  # 不拉伸

        left_layout.addWidget(input_container)

        # 添加底部弹性空间 -QW
        left_layout.addStretch()

        parent_layout.addWidget(left_widget)

    def create_right_code_password_area_design_no_button(self, parent_layout):
        """创建右侧验证码+密码区域 (不包含按钮) -QW"""
        # 创建右侧容器 -QW
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # ====== 验证码区域 ====== -QW
        # 验证码标签，严格按照设计图 -QW
        code_label = QtWidgets.QLabel("验证码")
        code_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        right_layout.addWidget(code_label)

        # 创建验证码输入框容器，包含输入框和复制图标 -QW
        code_container = QtWidgets.QWidget()
        code_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        code_container.setMinimumHeight(50)
        code_container.setMaximumHeight(50)
        
        code_layout = QtWidgets.QHBoxLayout(code_container)
        code_layout.setContentsMargins(15, 0, 10, 0)
        code_layout.setSpacing(8)

        # 验证码输入框，无边框样式，设置为不可修改和不可选中 -QW
        self.cursor_verification_input = QtWidgets.QLineEdit()
        self.cursor_verification_input.setPlaceholderText("请输入验证码")
        # 设置为只读，不可修改和不可选中 -QW
        self.cursor_verification_input.setReadOnly(True)
        self.cursor_verification_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保验证码完全显示 -QW
        self.cursor_verification_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        code_layout.addWidget(self.cursor_verification_input, 1)  # 设置拉伸因子为1

        # 复制图标，严格按照设计图 -QW
        self.cursor_code_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_code_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_code_copy_icon.setFixedSize(18, 18)
        self.cursor_code_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_code_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_code_copy_icon.mousePressEvent = self.cursor_copy_code
        code_layout.addWidget(self.cursor_code_copy_icon, 0)  # 不拉伸

        right_layout.addWidget(code_container)

        # ====== 密码区域 ====== -QW
        # 密码标签，严格按照设计图 -QW
        password_label = QtWidgets.QLabel("密码")
        password_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        right_layout.addWidget(password_label)

        # 创建密码输入框容器，包含输入框和复制图标 -QW
        password_container = QtWidgets.QWidget()
        password_container.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        password_container.setMinimumHeight(50)
        password_container.setMaximumHeight(50)
        
        password_layout = QtWidgets.QHBoxLayout(password_container)
        password_layout.setContentsMargins(15, 0, 10, 0)
        password_layout.setSpacing(8)

        # 密码输入框，无边框样式，设置为不可修改和不可选中 -QW
        self.cursor_password_input = QtWidgets.QLineEdit()
        self.cursor_password_input.setPlaceholderText("请输入密码")
        # 设置为只读，不可修改和不可选中 -QW
        self.cursor_password_input.setReadOnly(True)
        self.cursor_password_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        # 设置输入框占用更多空间，确保密码完全显示 -QW
        self.cursor_password_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        password_layout.addWidget(self.cursor_password_input, 1)  # 设置拉伸因子为1

        # 密码复制图标，严格按照设计图 -QW
        self.cursor_password_copy_icon = QtWidgets.QLabel("📋")
        self.cursor_password_copy_icon.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cursor_password_copy_icon.setFixedSize(18, 18)
        self.cursor_password_copy_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.cursor_password_copy_icon.setCursor(QtCore.Qt.PointingHandCursor)
        self.cursor_password_copy_icon.mousePressEvent = self.cursor_copy_password
        password_layout.addWidget(self.cursor_password_copy_icon, 0)  # 不拉伸

        right_layout.addWidget(password_container)

        # 添加底部弹性空间 -QW
        right_layout.addStretch()

        parent_layout.addWidget(right_widget)

    def create_bottom_buttons_row(self, parent_layout):
        """创建底部按钮行，包含三个按钮的水平布局 -QW"""
        # 创建按钮行容器 -QW
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 20, 0, 0)  # 添加顶部间距
        buttons_layout.setSpacing(20)  # 按钮之间的间距

        # 获取账号按钮，严格按照设计图颜色和尺寸 -QW
        self.cursor_get_account_btn = QtWidgets.QPushButton("获取账号")
        self.cursor_get_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 32px;
                font-size: 16px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2851a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999999;
            }
        """)
        self.cursor_get_account_btn.setMinimumHeight(50)
        self.cursor_get_account_btn.setMaximumHeight(50)
        buttons_layout.addWidget(self.cursor_get_account_btn)
        
        # 连接获取账号按钮点击事件 -QW
        self.cursor_get_account_btn.clicked.connect(self.cursor_get_account)

        # 获取验证码按钮，严格按照设计图颜色和尺寸 -QW
        self.cursor_get_verification_btn = QtWidgets.QPushButton("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 32px;
                font-size: 16px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2d8f47;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999999;
            }
        """)
        self.cursor_get_verification_btn.setMinimumHeight(50)
        self.cursor_get_verification_btn.setMaximumHeight(50)
        buttons_layout.addWidget(self.cursor_get_verification_btn)
        
        # 连接获取验证码按钮点击事件 -QW
        self.cursor_get_verification_btn.clicked.connect(self.cursor_get_verification_code)

        # 获取密码按钮已移除 -QW
        # self.cursor_get_password_btn = QtWidgets.QPushButton("获取密码")
        # buttons_layout.addWidget(self.cursor_get_password_btn)

        # 添加弹性空间使按钮居中 -QW
        buttons_layout.insertStretch(0)  # 左侧弹性空间
        buttons_layout.addStretch()      # 右侧弹性空间

        parent_layout.addWidget(buttons_widget)

        # 初始化按钮状态检查 -QW
        self._check_cursor_account_cooldown_on_init()
        self._check_cursor_verification_cooldown_on_init()

    def cursor_get_account(self):
        """Cursor账号标签页获取账号 -QW"""
        try:
            # 显示账号使用提醒弹窗 -QW
            dialog_result = self._show_account_usage_warning_dialog()
            if dialog_result != "continue":
                # 用户选择了"我去选择历史账号"，停止获取新账号的逻辑
                return
            
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 检查获取账号的10分钟冷却时间 -QW
            if hasattr(self, '_cursor_last_get_account_success_time') and self._cursor_last_get_account_success_time is not None:
                import time
                current_time = time.time()
                time_diff = current_time - self._cursor_last_get_account_success_time
                cooldown_time = 10 * 60  # 10分钟 = 600秒

                if time_diff < cooldown_time:
                    remaining_time = int(cooldown_time - time_diff)
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    QtWidgets.QMessageBox.information(
                        None, "提示",
                        f"获取账号冷却中，请等待 {minutes}分{seconds}秒 后再试"
                    )
                    print(f"[Cursor账号标签页] ⏰ 获取账号冷却中，剩余: {minutes}分{seconds}秒")
                    
                    # 如果当前没有倒计时显示，启动倒计时
                    if not hasattr(self, '_cursor_account_countdown_timer') or not self._cursor_account_countdown_timer:
                        self._cursor_account_countdown_seconds = remaining_time
                        self._start_cursor_account_countdown()
                    
                    return

            # 禁用按钮防止重复点击 -QW
            self.cursor_get_account_btn.setEnabled(False)
            self.cursor_get_account_btn.setText("获取中...")

            print("[Cursor账号标签页] 📧 获取账号按钮被点击")

            # 获取device_code和device_code_md5 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                raise Exception("设备信息未初始化，请重启应用")

            print(
                f"[Cursor账号标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")

            # 调用后端接口获取账号 -QW
            import requests

            # 构造请求URL，添加type=2参数
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/cursorLoginZs/getCredentialsAm"
            url = f"{base_url}{api_path}?device_code={device_code}&device_code_md5={device_code_md5}&type=2"

            print(f"[Cursor账号标签页] 🌐 请求URL: {url}")

            # 发送GET请求，添加重试机制 -QW
            import time as time_module
            max_retries = 3
            retry_delay = 1  # 1秒延迟
            
            for attempt in range(max_retries):
                try:
                    print(f"[Cursor账号标签页] 🔄 尝试第 {attempt + 1} 次获取账号...")
                    proxies = {"http": None, "https": None}
                    response = requests.get(url, proxies=proxies, timeout=15)
                    break  # 请求成功，跳出重试循环
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt == max_retries - 1:  # 最后一次尝试失败
                        raise Exception(f"网络连接失败，已重试 {max_retries} 次: {str(e)}")
                    else:
                        print(f"[Cursor账号标签页] ⚠️ 第 {attempt + 1} 次获取账号失败，{retry_delay}秒后重试: {str(e)}")
                        time_module.sleep(retry_delay)
                        retry_delay *= 1.5  # 递增延迟时间

            # 检查响应状态码
            if response.status_code == 200:
                # 解析返回的JSON数据
                data = response.json()
                code = data.get("code")

                if code == '500':
                    error_msg = data.get("msg", "服务器返回错误")
                    raise Exception(f"{error_msg}")

                # 获取账号信息
                result_data = data.get("data")
                if result_data:
                    email = result_data.get("email", "")
                    password = result_data.get("password", "")  # 新增获取password字段
                    
                    if email:
                        # 将账号设置到输入框中 -QW
                        self.cursor_account_input.setText(email)
                        print(f"[Cursor账号标签页] ✅ 获取账号成功: {email}")
                        
                        # 将密码设置到密码输入框中 -QW
                        if password and password.strip():
                            # 有密码时显示密码，使用正常样式
                            self.cursor_password_input.setText(password)
                            self.cursor_password_input.setStyleSheet("""
                                QLineEdit {
                                    border: none;
                                    background: transparent;
                                    font-size: 14px;
                                    color: #333333;
                                    padding: 0px;
                                    font-weight: 500;
                                }
                                QLineEdit::placeholder {
                                    color: #999999;
                                }
                            """)
                            print(f"[Cursor账号标签页] ✅ 获取密码成功: ***")
                        else:
                            # 无密码时显示提示信息，使用灰色斜体样式
                            self.cursor_password_input.setText("该账号无密码，请用验证码登陆")
                            self.cursor_password_input.setStyleSheet("""
                                QLineEdit {
                                    border: none;
                                    background: transparent;
                                    font-size: 14px;
                                    color: #888888;
                                    padding: 0px;
                                    font-weight: 400;
                                    font-style: italic;
                                }
                            """)
                            print(f"[Cursor账号标签页] ⚠️ 该账号无密码")
                    else:
                        raise Exception("服务器返回的账号信息为空")
                else:
                    raise Exception("服务器返回的数据格式错误")
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

            # 记录获取账号成功的时间，用于10分钟冷却检查 -QW
            import time
            self._cursor_last_get_account_success_time = time.time()
            print(f"[Cursor账号标签页] ✅ 获取账号成功，10分钟后可再次获取账号")

            # 启动获取账号按钮的10分钟倒计时显示 -QW
            self._start_cursor_account_countdown()
            
            # 启动获取验证码按钮的30秒倒计时显示 -QW
            self._start_cursor_verification_countdown()

        except Exception as e:
            # 获取失败时恢复按钮状态 -QW
            self.cursor_get_account_btn.setEnabled(True)
            self.cursor_get_account_btn.setText("获取账号")

            # 显示服务器报错信息 -QW
            error_message = str(e)
            QtWidgets.QMessageBox.critical(None, "获取账号失败", error_message)
            print(f"[Cursor账号标签页] ❌ 获取账号失败: {error_message}")

    def cursor_copy_account(self, event=None):
        """复制Cursor账号标签页的账号 -QW"""
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
                
            account_text = self.cursor_account_input.text().strip()
            if account_text:
                # 复制到剪贴板 -QW
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(account_text)
                
                # 显示成功提示 -QW
                QtWidgets.QMessageBox.information(None, "复制成功", f"账号已复制到剪贴板：\n{account_text}")
                print(f"[Cursor账号标签页] ✅ 账号复制成功: {account_text}")
            else:
                QtWidgets.QMessageBox.information(None, "提示", "请先获取账号")
                print("[Cursor账号标签页] ⚠️ 账号为空，无法复制")
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 复制账号失败: {str(e)}")

    def cursor_copy_code(self, event=None):
        """复制Cursor账号标签页的验证码 -QW"""
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
                
            code_text = self.cursor_verification_input.text().strip()
            if code_text:
                # 复制到剪贴板 -QW
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(code_text)
                
                # 显示成功提示 -QW
                QtWidgets.QMessageBox.information(None, "复制成功", f"验证码已复制到剪贴板：\n{code_text}")
                print(f"[Cursor账号标签页] ✅ 验证码复制成功: {code_text}")
                
                # 复制成功后立即清空验证码显示 -QW
                self._clear_cursor_verification_code("复制成功")
            else:
                QtWidgets.QMessageBox.information(None, "提示", "请先获取验证码")
                print("[Cursor账号标签页] ⚠️ 验证码为空，无法复制")
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 复制验证码失败: {str(e)}")

    def cursor_copy_password(self, event=None):
        """复制Cursor账号标签页的密码 -QW"""
        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
                
            password_text = self.cursor_password_input.text().strip()
            if password_text:
                # 检查是否是提示信息
                if password_text == "该账号无密码，请用验证码登陆":
                    QtWidgets.QMessageBox.information(None, "提示", "该账号无密码，无法复制。\n请使用验证码功能进行登陆。")
                    print("[Cursor账号标签页] ⚠️ 无密码账号，无法复制")
                    return
                
                # 复制到剪贴板 -QW
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(password_text)
                
                # 显示成功提示 -QW
                QtWidgets.QMessageBox.information(None, "复制成功", f"密码已复制到剪贴板：\n{password_text}")
                print(f"[Cursor账号标签页] ✅ 密码复制成功: {password_text}")
            else:
                QtWidgets.QMessageBox.information(None, "提示", "请先获取密码")
                print("[Cursor账号标签页] ⚠️ 密码为空，无法复制")
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 复制密码失败: {str(e)}")

    def cursor_get_password(self):
        """Cursor账号标签页获取密码 -QW (暂时占位方法)"""
        try:
            print("[Cursor账号标签页] 🔐 获取密码按钮被点击")
            
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
            
            QtWidgets.QMessageBox.information(None, "提示", "获取密码功能开发中...")
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 获取密码失败: {str(e)}")

    def show_history_accounts(self):
        """显示历史账号下拉框 -QW"""
        try:
            print("[Cursor账号标签页] 📋 历史账号按钮被点击")
            
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
            
            # 获取历史账号数据 -QW
            history_accounts = self.get_history_accounts()
            
            if not history_accounts:
                QtWidgets.QMessageBox.information(None, "提示", "暂无历史账号记录")
                return
            
            # 创建下拉菜单 -QW
            menu = QtWidgets.QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 8px 4px;
                    min-width: 320px;
                    max-height: 400px;
                }
                QMenu::item {
                    padding: 12px 20px;
                    margin: 3px 8px;
                    font-size: 13px;
                    color: #333333;
                    font-family: 'Monaco', 'Consolas', monospace;
                    border-radius: 4px;
                    border: 1px solid transparent;
                    background-color: transparent;
                }
                QMenu::item:selected {
                    background-color: #f0f8ff;
                    color: #4285f4;
                    border: 1px solid #d0e4ff;
                }
                QMenu::item:hover {
                    background-color: #f0f8ff;
                    border: 1px solid #d0e4ff;
                }
                QMenu::item:disabled {
                    background-color: #f8f9fa;
                    color: #999999;
                    font-style: italic;
                    font-size: 12px;
                    margin: 0px 8px;
                    border-radius: 0px;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #e0e0e0;
                    margin: 8px 16px;
                }
            """)
            
            # 获取Python配置的显示限制 -QW
            try:
                from tab_config_manager import TabConfigManager
                config_manager = TabConfigManager("config.py")
                display_limit = config_manager.get_history_account_display_limit()
            except:
                display_limit = 12  # 默认限制
            
            # 添加置顶提示信息 -QW
            tip_action = menu.addAction(f"历史账号 (显示前{len(history_accounts)}个，目前最多显示{display_limit}个)")
            tip_action.setEnabled(False)  # 设置为不可点击
            
            # 添加分隔线 -QW
            menu.addSeparator()
            
            # 添加历史账号到菜单，显示格式：序号. 账号 | 密码 --- 时间 -QW
            for index, account_info in enumerate(history_accounts, 1):
                email = account_info.get("email", "")
                use_time = account_info.get("useTime", "")
                password = account_info.get("password", "")
                
                # 格式化显示文本：序号. 账号 | 密码 --- 时间
                if use_time:
                    formatted_time = self.format_time_display(use_time)
                    if password:
                        display_text = f"{index:2d}. {email} | {password} --- {formatted_time}"
                    else:
                        display_text = f"{index:2d}. {email} | (无密码) --- {formatted_time}"
                else:
                    if password:
                        display_text = f"{index:2d}. {email} | {password}"
                    else:
                        display_text = f"{index:2d}. {email} | (无密码)"
                
                action = menu.addAction(display_text)
                # 点击时传递完整的账号信息
                action.triggered.connect(lambda checked, acc_info=account_info: self.select_history_account_with_password(acc_info))
            
            # 在按钮下方显示菜单 -QW
            button_pos = self.cursor_history_btn.mapToGlobal(self.cursor_history_btn.rect().bottomLeft())
            menu.exec_(button_pos)
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 显示历史账号失败: {str(e)}")
            QtWidgets.QMessageBox.critical(None, "错误", f"获取历史账号失败：{str(e)}")

    def get_history_accounts(self):
        """获取历史账号列表 -QW"""
        try:
            print("[Cursor账号标签页] 🔍 开始获取历史账号")
            
            # 获取device_code和device_code_md5，复用获取账号的方法 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                raise Exception("设备信息未初始化，请重启应用")

            print(f"[Cursor账号标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")

            # 调用历史账号接口 -QW
            import requests

            # 构造请求URL
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/cursorLoginZs/getHistoryAccount"
            url = f"{base_url}{api_path}?device_code={device_code}&device_code_md5={device_code_md5}&type=2"

            print(f"[Cursor账号标签页] 🌐 历史账号请求URL: {url}")

            # 发送GET请求，添加重试机制 -QW
            import time
            max_retries = 3
            retry_delay = 1  # 1秒延迟
            
            for attempt in range(max_retries):
                try:
                    print(f"[Cursor账号标签页] 🔄 尝试第 {attempt + 1} 次请求...")
                    proxies = {"http": None, "https": None}
                    response = requests.get(url, proxies=proxies, timeout=15)
                    break  # 请求成功，跳出重试循环
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt == max_retries - 1:  # 最后一次尝试失败
                        raise Exception(f"网络连接失败，已重试 {max_retries} 次: {str(e)}")
                    else:
                        print(f"[Cursor账号标签页] ⚠️ 第 {attempt + 1} 次请求失败，{retry_delay}秒后重试: {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # 递增延迟时间

            # 检查响应状态码
            if response.status_code == 200:
                # 解析返回的JSON数据
                data = response.json()
                code = data.get("code")

                if code == '500':
                    error_msg = data.get("msg", "服务器返回错误")
                    raise Exception(f"{error_msg}")

                # 获取历史账号列表
                result_data = data.get("data")
                if result_data and isinstance(result_data, list):
                    # 处理对象数组，提取邮箱、时间和密码字段 -QW
                    accounts = []
                    for account in result_data:
                        if isinstance(account, dict):
                            # 如果是字典对象，提取email、useTime和password字段
                            email = account.get("email", "")
                            use_time = account.get("useTime", "")
                            password = account.get("password", "")  # 新增password字段
                            if email and email.strip():
                                # 保存完整的账号信息对象
                                accounts.append({
                                    "email": email.strip(),
                                    "useTime": use_time,
                                    "password": password  # 保存密码信息
                                })
                        elif isinstance(account, str):
                            # 如果是字符串，直接处理（兼容旧格式）
                            if account and account.strip():
                                accounts.append({
                                    "email": account.strip(),
                                    "useTime": "",
                                    "password": ""  # 旧格式默认无密码
                                })
                    
                    # 按照时间排序，最新的在前面，根据配置限制显示数量 -QW
                    if accounts:
                        # 按照useTime排序（最新的在前面）
                        accounts_sorted = self.sort_accounts_by_time(accounts)
                        
                        # 从Python配置文件读取显示限制 -QW
                        try:
                            from tab_config_manager import TabConfigManager
                            config_manager = TabConfigManager("config.py")
                            display_limit = config_manager.get_history_account_display_limit()
                        except:
                            display_limit = 12  # 默认限制
                        
                        # 根据配置限制显示数量
                        accounts_limited = accounts_sorted[:display_limit]
                        print(f"[Cursor账号标签页] ✅ 获取到 {len(accounts)} 个历史账号，显示前 {len(accounts_limited)} 个，目前最多显示: {display_limit}）")
                        return accounts_limited
                    else:
                        print(f"[Cursor账号标签页] ✅ 获取到 {len(accounts)} 个历史账号")
                        return accounts
                else:
                    print("[Cursor账号标签页] ⚠️ 暂无历史账号记录")
                    return []
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 获取历史账号失败: {str(e)}")
            raise e

    def select_history_account(self, account):
        """选择历史账号 -QW"""
        try:
            print(f"[Cursor账号标签页] ✅ 选择历史账号: {account}")
            
            # 将选中的账号设置到输入框 -QW
            self.cursor_account_input.setText(account)
            
            # 显示成功提示（可选） -QW
            print(f"[Cursor账号标签页] ✅ 历史账号已设置: {account}")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 选择历史账号失败: {str(e)}")

    def select_history_account_with_password(self, account_info):
        """选择历史账号并同时设置密码 -QW"""
        try:
            email = account_info.get("email", "")
            password = account_info.get("password", "")
            
            print(f"[Cursor账号标签页] 📧 选择历史账号: {email}")
            print(f"[Cursor账号标签页] 🔐 对应密码: {'***' if password else '(无密码)'}")
            
            # 设置账号到输入框
            self.cursor_account_input.setText(email)
            
            # 设置密码到密码输入框
            if password and password.strip():
                # 有密码时直接显示密码，使用正常样式
                self.cursor_password_input.setText(password)
                self.cursor_password_input.setStyleSheet("""
                    QLineEdit {
                        border: none;
                        background: transparent;
                        font-size: 14px;
                        color: #333333;
                        padding: 0px;
                        font-weight: 500;
                    }
                    QLineEdit::placeholder {
                        color: #999999;
                    }
                """)
                print(f"[Cursor账号标签页] ✅ 账号和密码已设置到输入框")
            else:
                # 无密码时显示提示信息，使用灰色斜体样式
                self.cursor_password_input.setText("该账号无密码，请用验证码登陆")
                self.cursor_password_input.setStyleSheet("""
                    QLineEdit {
                        border: none;
                        background: transparent;
                        font-size: 14px;
                        color: #888888;
                        padding: 0px;
                        font-weight: 400;
                        font-style: italic;
                    }
                """)
                print(f"[Cursor账号标签页] ⚠️ 账号已设置，显示无密码提示")
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 设置历史账号和密码失败: {str(e)}")

    def format_time_display(self, time_str):
        """将时间格式转换为"**月**日**:**:**"格式 -QW"""
        try:
            import datetime
            
            # 尝试解析常见的时间格式
            time_formats = [
                "%Y-%m-%d %H:%M:%S",  # 2023-12-01 15:30:00
                "%Y/%m/%d %H:%M:%S",  # 2023/12/01 15:30:00
                "%Y-%m-%d",           # 2023-12-01
                "%Y/%m/%d",           # 2023/12/01
                "%m-%d %H:%M:%S",     # 12-01 15:30:00
                "%m/%d %H:%M:%S",     # 12/01 15:30:00
            ]
            
            parsed_time = None
            for fmt in time_formats:
                try:
                    parsed_time = datetime.datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_time:
                # 转换为"**月**日**:**:**"格式
                month = parsed_time.month
                day = parsed_time.day
                hour = parsed_time.hour
                minute = parsed_time.minute
                second = parsed_time.second
                
                formatted = f"{month}月{day:02d}日 {hour:02d}:{minute:02d}:{second:02d}"
                return formatted
            else:
                # 如果解析失败，返回原始字符串
                print(f"[Cursor账号标签页] ⚠️ 无法解析时间格式: {time_str}")
                return time_str
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 时间格式转换失败: {str(e)}")
            return time_str

    def sort_accounts_by_time(self, accounts):
        """按照使用时间排序账号列表，最新的在前面 -QW"""
        try:
            import datetime
            
            def parse_time_for_sort(time_str):
                """解析时间字符串，用于排序比较 -QW"""
                if not time_str:
                    # 如果没有时间，返回最小时间（排到最后）
                    return datetime.datetime.min
                
                # 尝试解析常见的时间格式
                time_formats = [
                    "%Y-%m-%d %H:%M:%S",  # 2023-12-01 15:30:00
                    "%Y/%m/%d %H:%M:%S",  # 2023/12/01 15:30:00
                    "%Y-%m-%d",           # 2023-12-01
                    "%Y/%m/%d",           # 2023/12/01
                    "%m-%d %H:%M:%S",     # 12-01 15:30:00
                    "%m/%d %H:%M:%S",     # 12/01 15:30:00
                ]
                
                for fmt in time_formats:
                    try:
                        return datetime.datetime.strptime(time_str, fmt)
                    except ValueError:
                        continue
                
                # 如果解析失败，返回最小时间（排到最后）
                print(f"[Cursor账号标签页] ⚠️ 排序时无法解析时间格式: {time_str}")
                return datetime.datetime.min
            
            # 按照时间排序，最新的在前面（降序）
            sorted_accounts = sorted(
                accounts, 
                key=lambda account: parse_time_for_sort(account.get("useTime", "")),
                reverse=True  # 降序，最新的在前面
            )
            
            print(f"[Cursor账号标签页] ✅ 账号按时间排序完成，最新的账号在前面")
            return sorted_accounts
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 账号排序失败: {str(e)}")
            # 排序失败时返回原列表
            return accounts

    def _start_cursor_account_countdown(self, countdown_seconds=None):
        """启动Cursor账号标签页获取账号按钮的倒计时显示 -QW"""
        try:
            # 停止之前的定时器（如果存在）
            if hasattr(self, '_cursor_account_countdown_timer') and self._cursor_account_countdown_timer:
                self._cursor_account_countdown_timer.stop()
                self._cursor_account_countdown_timer.deleteLater()

            # 创建新的定时器
            self._cursor_account_countdown_timer = QtCore.QTimer()
            self._cursor_account_countdown_timer.timeout.connect(self._update_cursor_account_countdown)
            
            # 设置倒计时时间，如果没有传入参数则默认为10分钟
            if countdown_seconds is None:
                self._cursor_account_countdown_seconds = 10 * 60
            # 如果倒计时秒数还没有设置，则使用传入的参数或默认值
            elif not hasattr(self, '_cursor_account_countdown_seconds') or self._cursor_account_countdown_seconds <= 0:
                self._cursor_account_countdown_seconds = countdown_seconds or (10 * 60)
            
            # 立即更新一次按钮显示
            self._update_cursor_account_countdown()
            
            # 每秒更新一次
            self._cursor_account_countdown_timer.start(1000)
            
            minutes = self._cursor_account_countdown_seconds // 60
            seconds = self._cursor_account_countdown_seconds % 60
            print(f"[Cursor账号标签页] ⏰ 启动获取账号按钮倒计时: {minutes}分{seconds}秒")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 启动倒计时失败: {str(e)}")

    def _update_cursor_account_countdown(self):
        """更新Cursor账号标签页获取账号按钮的倒计时显示 -QW"""
        try:
            if self._cursor_account_countdown_seconds > 0:
                # 计算分钟和秒数
                minutes = self._cursor_account_countdown_seconds // 60
                seconds = self._cursor_account_countdown_seconds % 60
                
                # 更新按钮文字显示倒计时
                countdown_text = f"获取账号 ({minutes:02d}:{seconds:02d})"
                self.cursor_get_account_btn.setText(countdown_text)
                
                # 设置按钮为禁用状态和灰色样式
                self.cursor_get_account_btn.setEnabled(False)
                
                # 减少倒计时秒数
                self._cursor_account_countdown_seconds -= 1
                
            else:
                # 倒计时结束，恢复按钮状态
                self._stop_cursor_account_countdown()
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 更新倒计时显示失败: {str(e)}")

    def _stop_cursor_account_countdown(self):
        """停止Cursor账号标签页获取账号按钮的倒计时 -QW"""
        try:
            # 停止定时器
            if hasattr(self, '_cursor_account_countdown_timer') and self._cursor_account_countdown_timer:
                self._cursor_account_countdown_timer.stop()
                self._cursor_account_countdown_timer.deleteLater()
                self._cursor_account_countdown_timer = None
            
            # 恢复按钮状态
            self.cursor_get_account_btn.setEnabled(True)
            self.cursor_get_account_btn.setText("获取账号")
            
            print("[Cursor账号标签页] ✅ 获取账号按钮倒计时结束，按钮已恢复")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 停止倒计时失败: {str(e)}")

    def _check_cursor_account_cooldown_on_init(self):
        """初始化时检查Cursor账号标签页获取账号按钮的冷却状态 -QW"""
        try:
            # 检查是否有上次获取账号的时间记录
            if hasattr(self, '_cursor_last_get_account_success_time') and self._cursor_last_get_account_success_time is not None:
                import time
                current_time = time.time()
                time_diff = current_time - self._cursor_last_get_account_success_time
                cooldown_time = 10 * 60  # 10分钟 = 600秒

                if time_diff < cooldown_time:
                    # 仍在冷却期内，计算剩余时间并启动倒计时
                    remaining_time = int(cooldown_time - time_diff)
                    self._cursor_account_countdown_seconds = remaining_time
                    self._start_cursor_account_countdown()
                    
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    print(f"[Cursor账号标签页] ⏰ 初始化时发现处于冷却期，剩余: {minutes}分{seconds}秒")
                else:
                    # 冷却期已过，确保按钮处于可用状态
                    self.cursor_get_account_btn.setEnabled(True)
                    self.cursor_get_account_btn.setText("获取账号")
                    print("[Cursor账号标签页] ✅ 初始化时冷却期已过，按钮可用")
            else:
                # 没有冷却时间记录，确保按钮处于可用状态
                self.cursor_get_account_btn.setEnabled(True)
                self.cursor_get_account_btn.setText("获取账号")
                print("[Cursor账号标签页] ✅ 初始化时无冷却记录，按钮可用")
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 初始化冷却检查失败: {str(e)}")
            # 出错时确保按钮可用
            self.cursor_get_account_btn.setEnabled(True)
            self.cursor_get_account_btn.setText("获取账号")

    def _start_cursor_verification_countdown(self, countdown_seconds=None):
        """启动Cursor账号标签页获取验证码按钮的倒计时显示 -QW"""
        try:
            # 停止之前的定时器（如果存在）
            if hasattr(self, '_cursor_verification_countdown_timer') and self._cursor_verification_countdown_timer:
                self._cursor_verification_countdown_timer.stop()
                self._cursor_verification_countdown_timer.deleteLater()

            # 创建新的定时器
            self._cursor_verification_countdown_timer = QtCore.QTimer()
            self._cursor_verification_countdown_timer.timeout.connect(self._update_cursor_verification_countdown)
            
            # 设置倒计时时间，如果没有传入参数则默认为30秒
            if countdown_seconds is None:
                self._cursor_verification_countdown_seconds = 30
            # 如果倒计时秒数还没有设置，则使用传入的参数或默认值
            elif not hasattr(self, '_cursor_verification_countdown_seconds') or self._cursor_verification_countdown_seconds <= 0:
                self._cursor_verification_countdown_seconds = countdown_seconds or 30
            
            # 记录验证码倒计时开始时间
            import time
            self._cursor_last_verification_countdown_start_time = time.time()
            
            # 立即更新一次按钮显示
            self._update_cursor_verification_countdown()
            
            # 每秒更新一次
            self._cursor_verification_countdown_timer.start(1000)
            
            print(f"[Cursor账号标签页] ⏰ 启动获取验证码按钮倒计时: {self._cursor_verification_countdown_seconds}秒")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 启动验证码倒计时失败: {str(e)}")

    def _update_cursor_verification_countdown(self):
        """更新Cursor账号标签页获取验证码按钮的倒计时显示 -QW"""
        try:
            if self._cursor_verification_countdown_seconds > 0:
                # 更新按钮文字显示倒计时
                countdown_text = f"获取验证码 ({self._cursor_verification_countdown_seconds}s)"
                self.cursor_get_verification_btn.setText(countdown_text)
                
                # 设置按钮为禁用状态和灰色样式
                self.cursor_get_verification_btn.setEnabled(False)
                
                # 减少倒计时秒数
                self._cursor_verification_countdown_seconds -= 1
                
            else:
                # 倒计时结束，恢复按钮状态
                self._stop_cursor_verification_countdown()
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 更新验证码倒计时显示失败: {str(e)}")

    def _stop_cursor_verification_countdown(self):
        """停止Cursor账号标签页获取验证码按钮的倒计时 -QW"""
        try:
            # 停止定时器
            if hasattr(self, '_cursor_verification_countdown_timer') and self._cursor_verification_countdown_timer:
                self._cursor_verification_countdown_timer.stop()
                self._cursor_verification_countdown_timer.deleteLater()
                self._cursor_verification_countdown_timer = None
            
            # 恢复按钮状态
            self.cursor_get_verification_btn.setEnabled(True)
            self.cursor_get_verification_btn.setText("获取验证码")
            
            print("[Cursor账号标签页] ✅ 获取验证码按钮倒计时结束，按钮已恢复")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 停止验证码倒计时失败: {str(e)}")

    def _check_cursor_verification_cooldown_on_init(self):
        """初始化时检查Cursor账号标签页获取验证码按钮的冷却状态 -QW"""
        try:
            # 确保验证码按钮已经创建
            if not hasattr(self, 'cursor_get_verification_btn'):
                print("[Cursor账号标签页] ⚠️ 验证码按钮尚未创建，跳过冷却检查")
                return
                
            # 检查是否有验证码倒计时开始时间记录
            if hasattr(self, '_cursor_last_verification_countdown_start_time') and self._cursor_last_verification_countdown_start_time is not None:
                import time
                current_time = time.time()
                time_diff = current_time - self._cursor_last_verification_countdown_start_time
                cooldown_time = 30  # 30秒

                if time_diff < cooldown_time:
                    # 仍在冷却期内，计算剩余时间并启动倒计时
                    remaining_time = int(cooldown_time - time_diff)
                    self._cursor_verification_countdown_seconds = remaining_time
                    self._start_cursor_verification_countdown()
                    
                    print(f"[Cursor账号标签页] ⏰ 初始化时发现验证码按钮处于冷却期，剩余: {remaining_time}秒")
                else:
                    # 冷却期已过，确保按钮处于可用状态
                    self.cursor_get_verification_btn.setEnabled(True)
                    self.cursor_get_verification_btn.setText("获取验证码")
                    print("[Cursor账号标签页] ✅ 初始化时验证码按钮冷却期已过，按钮可用")
            else:
                # 没有冷却时间记录，确保按钮处于可用状态
                self.cursor_get_verification_btn.setEnabled(True)
                self.cursor_get_verification_btn.setText("获取验证码")
                print("[Cursor账号标签页] ✅ 初始化时无验证码倒计时记录，按钮可用")
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 初始化验证码倒计时检查失败: {str(e)}")
            # 出错时确保按钮可用
            self.cursor_get_verification_btn.setEnabled(True)
            self.cursor_get_verification_btn.setText("获取验证码")

    def cursor_get_verification_code(self):
        """Cursor账号标签页获取验证码 -QW"""
        try:
            print("[Cursor账号标签页] 🔐 获取验证码按钮被点击")

            # 检查是否有邮箱账号 -QW
            email = self.cursor_account_input.text().strip()
            if not email:
                QtWidgets.QMessageBox.information(None, "提示", "请先获取账号")
                print("[Cursor账号标签页] ⚠️ 邮箱为空，请先获取账号")
                return

            # 检查激活状态 -QW
            if not self.check_activation_status():
                return

            # 添加确认弹窗，确保用户已在Cursor官网发送验证码 -QW
            reply = QtWidgets.QMessageBox.question(
                None,
                "确认操作",
                f"cursor验证码有延迟请等待20秒哦，如果遇到验证码失效，请您在点一下获取验证码！！\n\n"
                f"邮箱：{email}\n\n"
                f"请您先确定已经在cursor官网发送验证码之后，再点击yes按钮，没有请点击no",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            # 如果用户选择"否"（未发送），则直接返回 -QW
            if reply == QtWidgets.QMessageBox.No:
                print("[Cursor账号标签页] ❌ 用户未在Cursor官网发送验证码，取消获取操作")
                return
            
            print("[Cursor账号标签页] ✅ 用户确认已在Cursor官网发送验证码，开始30秒倒计时")

            # 获取device_code和device_code_md5 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                QtWidgets.QMessageBox.critical(None, "错误", "设备信息未初始化，请重启应用")
                return

            print(f"[Cursor账号标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")
            print(f"[Cursor账号标签页] 📧 使用邮箱: {email}")

            # 开始30秒倒计时，倒计时结束后开始重试获取验证码 -QW
            self._start_cursor_verification_prepare_countdown(email, device_code, device_code_md5)

        except Exception as e:
            # 恢复按钮状态 -QW
            self.cursor_get_verification_btn.setEnabled(True)
            self.cursor_get_verification_btn.setText("获取验证码")

            # 显示服务器报错信息 -QW
            error_message = str(e)
            QtWidgets.QMessageBox.critical(None, "获取验证码失败", error_message)
            print(f"[Cursor账号标签页] ❌ 获取验证码失败: {error_message}")

    def _start_cursor_verification_code_retry(self, email, device_code, device_code_md5):
        """开始Cursor账号标签页验证码重试流程 -QW"""
        print("[Cursor账号标签页] 🔄 开始验证码重试流程")
        
        # 设置按钮为重试状态 -QW
        self.cursor_get_verification_btn.setEnabled(False)
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #cccccc;
                color: #666666;
                border: none;
                border-radius: 6px;
            }
        """)
        
        # 初始化重试相关变量 -QW
        self._cursor_verification_retry_count = 0
        self._cursor_verification_max_retries = 5
        self._cursor_verification_retry_interval = 3  # 3秒间隔
        
        # 开始第一次尝试 -QW
        self._cursor_attempt_get_verification_code(email, device_code, device_code_md5)

    def _cursor_attempt_get_verification_code(self, email, device_code, device_code_md5):
        """Cursor账号标签页尝试获取验证码的单次调用 -QW"""
        self._cursor_verification_retry_count += 1
        
        # 更新按钮显示重试次数 -QW
        self.cursor_get_verification_btn.setText(f"获取验证码({self._cursor_verification_retry_count}/{self._cursor_verification_max_retries})")
        print(f"[Cursor账号标签页] 🔄 第 {self._cursor_verification_retry_count} 次尝试获取验证码...")
        
        try:
            import requests

            # 构造请求URL (Cursor账号标签页专用，添加type=2参数)
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/outApi/getEmailCodeAm"
            url = f"{base_url}{api_path}?email={email}&device_code={device_code}&device_code_md5={device_code_md5}&type=2"

            print(f"[Cursor账号标签页] 🌐 验证码请求URL: {url}")

            # 发送GET请求
            proxies = {"http": None, "https": None}
            response = requests.get(url, proxies=proxies, timeout=15)

            # 检查响应状态码
            if response.status_code == 200:
                # 尝试解析JSON数据，如果失败则当作纯文本处理 -QW
                try:
                    data = response.json()
                    # 处理JSON格式响应
                    code = data.get("code")

                    if code == '500':
                        error_msg = data.get("msg", "服务器返回错误")
                        raise Exception(f"{error_msg}")

                    # 获取验证码信息
                    result_data = data.get("data")
                    if result_data:
                        # 处理不同格式的验证码数据 -QW
                        if isinstance(result_data, dict):
                            # 如果data是字典，尝试从不同字段获取验证码
                            verification_code = result_data.get("code", "") or result_data.get("verificationCode", "") or str(result_data)
                        else:
                            # 如果data是字符串，直接使用
                            verification_code = str(result_data)
                        
                        if verification_code:
                            # 验证码获取成功 -QW
                            self.cursor_verification_input.setText(verification_code)
                            print(f"[Cursor账号标签页] ✅ 第 {self._cursor_verification_retry_count} 次尝试获取验证码成功: {verification_code}")
                        
                            # 显示成功提示 -QW
                            QtWidgets.QMessageBox.information(None, "获取成功", f"验证码获取成功：{verification_code}\n\n请点击复制按钮，复制到cursor官网")
                            
                            # 启动自动清空定时器 -QW
                            self._start_cursor_verification_auto_clear()
                            
                            # 恢复按钮状态 -QW
                            self._restore_cursor_verification_button_success()
                            return
                        else:
                            raise Exception("服务器返回的验证码为空")
                    else:
                        raise Exception("服务器未返回验证码数据")
                        
                except ValueError:
                    # JSON解析失败，当作纯文本处理 (type=2接口可能直接返回验证码字符串) -QW
                    verification_code = response.text.strip()
                    if verification_code and verification_code.isdigit():
                        # 验证码获取成功 -QW
                        self.cursor_verification_input.setText(verification_code)
                        print(f"[Cursor账号标签页] ✅ 第 {self._cursor_verification_retry_count} 次尝试获取验证码成功: {verification_code}")
                        
                        # 显示成功提示 -QW
                        QtWidgets.QMessageBox.information(None, "获取成功", f"验证码获取成功：{verification_code}\n\n请点击复制按钮，复制到cursor官网")
                        
                        # 启动自动清空定时器 -QW
                        self._start_cursor_verification_auto_clear()
                        
                        # 恢复按钮状态 -QW
                        self._restore_cursor_verification_button_success()
                        return
                    else:
                        raise Exception(f"服务器返回的内容不是有效验证码: {verification_code}")
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 第 {self._cursor_verification_retry_count} 次尝试失败: {str(e)}")
            
            # 检查是否还有重试次数 -QW
            if self._cursor_verification_retry_count < self._cursor_verification_max_retries:
                # 还有重试次数，3秒后继续尝试 -QW
                print(f"[Cursor账号标签页] ⏰ {self._cursor_verification_retry_interval} 秒后进行第 {self._cursor_verification_retry_count + 1} 次尝试...")
                QtCore.QTimer.singleShot(self._cursor_verification_retry_interval * 1000, 
                                       lambda: self._cursor_attempt_get_verification_code(email, device_code, device_code_md5))
            else:
                # 所有重试都失败了 -QW
                print(f"[Cursor账号标签页] ❌ 所有 {self._cursor_verification_max_retries} 次尝试都失败了")
                self._handle_cursor_verification_all_failed()

    def _restore_cursor_verification_button_success(self):
        """Cursor账号标签页验证码获取成功后恢复按钮状态 -QW"""
        self.cursor_get_verification_btn.setEnabled(True)
        self.cursor_get_verification_btn.setText("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

    def _handle_cursor_verification_all_failed(self):
        """处理Cursor账号标签页所有验证码获取尝试都失败的情况 -QW"""
        # 恢复按钮状态 -QW
        self.cursor_get_verification_btn.setEnabled(True)
        self.cursor_get_verification_btn.setText("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        
        # 显示失败提示弹窗 -QW
        QtWidgets.QMessageBox.critical(
            None, 
            "获取验证码失败", 
            "获取验证码失败，请您确保cursor官网已经发送验证码，并且检查网络后，重新获取验证码"
        )
        print("[Cursor账号标签页] ❌ 显示验证码获取失败提示弹窗")

    def _start_cursor_verification_prepare_countdown(self, email, device_code, device_code_md5):
        """开始获取验证码前的30秒准备倒计时 -QW"""
        try:
            print("[Cursor账号标签页] ⏰ 开始30秒准备倒计时")
            
            # 初始化倒计时相关变量 -QW
            import config
            self._cursor_prepare_countdown_seconds = config.VERIFICATION_CODE_PREPARE_COUNTDOWN
            self._cursor_prepare_email = email
            self._cursor_prepare_device_code = device_code
            self._cursor_prepare_device_code_md5 = device_code_md5
            
            # 停止之前的定时器（如果存在）-QW
            if hasattr(self, '_cursor_prepare_countdown_timer') and self._cursor_prepare_countdown_timer:
                self._cursor_prepare_countdown_timer.stop()
                self._cursor_prepare_countdown_timer.deleteLater()
            
            # 禁用按钮并设置初始倒计时文本 -QW
            self.cursor_get_verification_btn.setEnabled(False)
            self.cursor_get_verification_btn.setText(f"{self._cursor_prepare_countdown_seconds}s后开始获取验证码")
            self.cursor_get_verification_btn.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
            
            # 创建并启动定时器 -QW
            self._cursor_prepare_countdown_timer = QtCore.QTimer()
            self._cursor_prepare_countdown_timer.timeout.connect(self._update_cursor_prepare_countdown)
            self._cursor_prepare_countdown_timer.start(1000)  # 每秒更新
            
            print(f"[Cursor账号标签页] ✅ 30秒准备倒计时已启动，邮箱: {email}")

        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 启动30秒准备倒计时失败: {str(e)}")
            # 出错时直接开始重试逻辑
            self._start_cursor_verification_code_retry(email, device_code, device_code_md5)
    
    def _update_cursor_prepare_countdown(self):
        """更新30秒准备倒计时显示 -QW"""
        try:
            if self._cursor_prepare_countdown_seconds > 0:
                # 更新按钮文字显示倒计时
                countdown_text = f"{self._cursor_prepare_countdown_seconds}s后开始获取验证码"
                self.cursor_get_verification_btn.setText(countdown_text)
                
                # 减少倒计时秒数
                self._cursor_prepare_countdown_seconds -= 1
                
            else:
                # 倒计时结束，开始获取验证码 -QW
                self._stop_cursor_prepare_countdown()
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 更新30秒准备倒计时失败: {str(e)}")
    
    def _stop_cursor_prepare_countdown(self):
        """停止30秒准备倒计时并开始获取验证码 -QW"""
        try:
            # 停止定时器 -QW
            if hasattr(self, '_cursor_prepare_countdown_timer') and self._cursor_prepare_countdown_timer:
                self._cursor_prepare_countdown_timer.stop()
                self._cursor_prepare_countdown_timer.deleteLater()
                self._cursor_prepare_countdown_timer = None
            
            print("[Cursor账号标签页] ✅ 30秒准备倒计时结束，开始获取验证码")
            
            # 开始5次重试获取验证码 -QW
            email = getattr(self, '_cursor_prepare_email', '')
            device_code = getattr(self, '_cursor_prepare_device_code', '')
            device_code_md5 = getattr(self, '_cursor_prepare_device_code_md5', '')
            
            if email and device_code and device_code_md5:
                self._start_cursor_verification_code_retry(email, device_code, device_code_md5)
            else:
                print("[Cursor账号标签页] ❌ 准备倒计时结束但参数丢失，恢复按钮状态")
            self.cursor_get_verification_btn.setEnabled(True)
            self.cursor_get_verification_btn.setText("获取验证码")

        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 停止30秒准备倒计时失败: {str(e)}")

    def _clear_cursor_verification_code(self, reason="自动清空"):
        """清空Cursor账号标签页的验证码显示 -QW"""
        try:
            self.cursor_verification_input.setText("")
            self.cursor_verification_input.setPlaceholderText("验证码已清空")
            print(f"[Cursor账号标签页] 🧹 验证码显示已清空: {reason}")
            
            # 停止可能存在的自动清空定时器 -QW
            if hasattr(self, '_cursor_verification_clear_timer') and self._cursor_verification_clear_timer:
                self._cursor_verification_clear_timer.stop()
                self._cursor_verification_clear_timer.deleteLater()
                self._cursor_verification_clear_timer = None
                
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 清空验证码显示失败: {str(e)}")

    def _start_cursor_verification_auto_clear(self):
        """启动Cursor账号标签页验证码自动清空定时器 -QW"""
        try:
            # 停止之前的定时器（如果存在）-QW
            if hasattr(self, '_cursor_verification_clear_timer') and self._cursor_verification_clear_timer:
                self._cursor_verification_clear_timer.stop()
                self._cursor_verification_clear_timer.deleteLater()
            
            # 获取清空时间配置 -QW
            import config
            clear_time = config.VERIFICATION_CODE_AUTO_CLEAR_TIME * 1000  # 转换为毫秒
            
            # 创建并启动定时器 -QW
            self._cursor_verification_clear_timer = QtCore.QTimer()
            self._cursor_verification_clear_timer.timeout.connect(lambda: self._clear_cursor_verification_code("自动清空"))
            self._cursor_verification_clear_timer.setSingleShot(True)  # 只执行一次
            self._cursor_verification_clear_timer.start(clear_time)
            
            print(f"[Cursor账号标签页] ⏰ 验证码自动清空定时器已启动，{config.VERIFICATION_CODE_AUTO_CLEAR_TIME}秒后清空")
            
        except Exception as e:
            print(f"[Cursor账号标签页] ❌ 启动验证码自动清空定时器失败: {str(e)}")

    def _clear_augment_verification_code(self, reason="自动清空"):
        """清空Augment标签页的验证码显示 -QW"""
        try:
            self.augment_code_input.setText("")
            self.augment_code_input.setPlaceholderText("验证码已清空")
            print(f"[Augment标签页] 🧹 验证码显示已清空: {reason}")
            
            # 停止可能存在的自动清空定时器 -QW
            if hasattr(self, '_augment_verification_clear_timer') and self._augment_verification_clear_timer:
                self._augment_verification_clear_timer.stop()
                self._augment_verification_clear_timer.deleteLater()
                self._augment_verification_clear_timer = None
                
        except Exception as e:
            print(f"[Augment标签页] ❌ 清空验证码显示失败: {str(e)}")

    def _start_augment_verification_auto_clear(self):
        """启动Augment标签页验证码自动清空定时器 -QW"""
        try:
            # 停止之前的定时器（如果存在）-QW
            if hasattr(self, '_augment_verification_clear_timer') and self._augment_verification_clear_timer:
                self._augment_verification_clear_timer.stop()
                self._augment_verification_clear_timer.deleteLater()
            
            # 获取清空时间配置 -QW
            import config
            clear_time = config.VERIFICATION_CODE_AUTO_CLEAR_TIME * 1000  # 转换为毫秒
            
            # 创建并启动定时器 -QW
            self._augment_verification_clear_timer = QtCore.QTimer()
            self._augment_verification_clear_timer.timeout.connect(lambda: self._clear_augment_verification_code("自动清空"))
            self._augment_verification_clear_timer.setSingleShot(True)  # 只执行一次
            self._augment_verification_clear_timer.start(clear_time)
            
            print(f"[Augment标签页] ⏰ 验证码自动清空定时器已启动，{config.VERIFICATION_CODE_AUTO_CLEAR_TIME}秒后清空")
            
        except Exception as e:
            print(f"[Augment标签页] ❌ 启动验证码自动清空定时器失败: {str(e)}")

    def create_server_notice_section_exact(self, parent_layout):
        """创建完全按照设计图的服务器维护公告区域 -QW"""
        # 创建公告容器 -QW
        notice_container = QtWidgets.QWidget()
        notice_container.setStyleSheet("""
            QWidget {
                background-color: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 8px;
            }
        """)
        notice_container.setFixedHeight(80)

        # 创建布局 -QW
        notice_layout = QtWidgets.QHBoxLayout(notice_container)
        notice_layout.setContentsMargins(20, 15, 20, 15)
        notice_layout.setSpacing(15)

        # 添加蓝色图标 -QW
        icon_label = QtWidgets.QLabel("📢")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #1976d2;
                background: transparent;
                border: none;
            }
        """)
        icon_label.setFixedSize(30, 30)
        notice_layout.addWidget(icon_label)

        # 创建文字区域 -QW
        text_container = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        # 标题 -QW
        title_label = QtWidgets.QLabel("服务器维护公告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1976d2;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(title_label)

        # 内容 -QW
        content_label = QtWidgets.QLabel("计划于本周六凌晨 2 点进行系统维护，预计持续 2 小时，请提前做好相关准备")
        content_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #424242;
                background: transparent;
                border: none;
            }
        """)
        content_label.setWordWrap(True)
        text_layout.addWidget(content_label)

        notice_layout.addWidget(text_container)
        notice_layout.addStretch()

        parent_layout.addWidget(notice_container)

    def create_email_section_exact(self, parent_layout):
        """创建完全按照设计图的获取邮箱区域 -QW"""
        # 创建左侧容器 -QW
        email_container = QtWidgets.QWidget()
        email_layout = QtWidgets.QVBoxLayout(email_container)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(25)

        # 标题 -QW
        title_label = QtWidgets.QLabel("获取邮箱")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #212121;
                background: transparent;
                border: none;
            }
        """)
        email_layout.addWidget(title_label)

        # 账号标签 -QW
        account_label = QtWidgets.QLabel("账号")
        account_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #424242;
                background: transparent;
                border: none;
                margin-bottom: 8px;
            }
        """)
        email_layout.addWidget(account_label)

        # 账号输入框 -QW
        self.cursor_account_input = QtWidgets.QLineEdit()
        self.cursor_account_input.setPlaceholderText("请输入账号")
        self.cursor_account_input.setStyleSheet("""
            QLineEdit {
                padding: 14px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
                color: #212121;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #2196f3;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #9e9e9e;
            }
        """)
        self.cursor_account_input.setFixedHeight(50)
        email_layout.addWidget(self.cursor_account_input)

        # 获取账号按钮 -QW
        self.cursor_get_account_btn = QtWidgets.QPushButton("获取账号")
        self.cursor_get_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 14px 24px;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #bbbbbb;
                color: #ffffff;
            }
        """)
        self.cursor_get_account_btn.setFixedHeight(50)
        email_layout.addWidget(self.cursor_get_account_btn)

        # 添加弹性空间 -QW
        email_layout.addStretch()

        parent_layout.addWidget(email_container)

    def create_verification_section_exact(self, parent_layout):
        """创建完全按照设计图的验证码区域 -QW"""
        # 创建右侧容器 -QW
        verification_container = QtWidgets.QWidget()
        verification_layout = QtWidgets.QVBoxLayout(verification_container)
        verification_layout.setContentsMargins(0, 0, 0, 0)
        verification_layout.setSpacing(25)

        # 标题 -QW
        title_label = QtWidgets.QLabel("验证码")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #212121;
                background: transparent;
                border: none;
            }
        """)
        verification_layout.addWidget(title_label)

        # 验证码标签 -QW
        code_label = QtWidgets.QLabel("验证码")
        code_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #424242;
                background: transparent;
                border: none;
                margin-bottom: 8px;
            }
        """)
        verification_layout.addWidget(code_label)

        # 验证码输入框 -QW
        self.cursor_verification_input = QtWidgets.QLineEdit()
        self.cursor_verification_input.setPlaceholderText("请输入验证码")
        self.cursor_verification_input.setStyleSheet("""
            QLineEdit {
                padding: 14px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
                color: #212121;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #4caf50;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #9e9e9e;
            }
        """)
        self.cursor_verification_input.setFixedHeight(50)
        verification_layout.addWidget(self.cursor_verification_input)

        # 获取验证码按钮 -QW
        self.cursor_get_verification_btn = QtWidgets.QPushButton("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 14px 24px;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
            QPushButton:disabled {
                background-color: #bbbbbb;
                color: #ffffff;
            }
        """)
        self.cursor_get_verification_btn.setFixedHeight(50)
        verification_layout.addWidget(self.cursor_get_verification_btn)

        # 添加弹性空间 -QW
        verification_layout.addStretch()

        parent_layout.addWidget(verification_container)

    def create_server_notice_section(self, parent_layout):
        """创建服务器维护公告区域 -QW"""
        # 创建公告容器 -QW
        notice_widget = QtWidgets.QWidget()
        notice_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f7ff;
                border: 1px solid #d1e7ff;
                border-radius: 8px;
                margin-bottom: 20px;
            }
        """)

        notice_layout = QtWidgets.QHBoxLayout(notice_widget)
        notice_layout.setContentsMargins(20, 15, 20, 15)
        notice_layout.setSpacing(15)

        # 添加蓝色图标 -QW
        icon_label = QtWidgets.QLabel("🔔")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #1976d2;
                background: transparent;
                border: none;
            }
        """)
        notice_layout.addWidget(icon_label)

        # 创建文字内容区域 -QW
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(5)

        # 添加标题文本 -QW
        title_label = QtWidgets.QLabel("服务器维护公告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1976d2;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        text_layout.addWidget(title_label)

        # 创建公告内容 -QW
        content_label = QtWidgets.QLabel("计划于本周六凌晨 2 点进行系统维护，预计持续 2 小时，请提前做好相关准备")
        content_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666666;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        content_label.setWordWrap(True)
        text_layout.addWidget(content_label)

        notice_layout.addLayout(text_layout)
        notice_layout.addStretch()

        parent_layout.addWidget(notice_widget)

    def create_email_section(self, parent_layout):
        """创建获取邮箱区域 -QW"""
        # 创建获取邮箱容器 -QW
        email_widget = QtWidgets.QWidget()
        email_layout = QtWidgets.QVBoxLayout(email_widget)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(20)

        # 创建标题 -QW
        email_title = QtWidgets.QLabel("获取邮箱")
        email_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        email_layout.addWidget(email_title)

        # 账号标签 -QW
        account_label = QtWidgets.QLabel("账号")
        account_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666666;
                margin-bottom: 8px;
            }
        """)
        email_layout.addWidget(account_label)

        # 创建输入框容器，包含输入框和图标 -QW
        input_container = QtWidgets.QWidget()
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)

        # 账号输入框 -QW
        self.cursor_account_input = QtWidgets.QLineEdit()
        self.cursor_account_input.setPlaceholderText("请输入账号")
        self.cursor_account_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 40px 12px 16px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #4285f4;
                outline: none;
            }
        """)
        input_layout.addWidget(self.cursor_account_input)

        # 添加输入框右侧图标 -QW
        icon_label = QtWidgets.QLabel("👤")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #999999;
                background: transparent;
                border: none;
                margin-right: 12px;
            }
        """)
        icon_label.setFixedSize(20, 20)
        input_layout.addWidget(icon_label)

        email_layout.addWidget(input_container)

        # 获取账号按钮 -QW
        self.cursor_get_account_btn = QtWidgets.QPushButton("获取账号")
        self.cursor_get_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2851a3;
            }
            QPushButton:disabled {
                background-color: #9aa0a6;
                color: #dadce0;
            }
        """)
        email_layout.addWidget(self.cursor_get_account_btn)

        # 添加弹性空间 -QW
        email_layout.addStretch()

        parent_layout.addWidget(email_widget)

    def create_verification_section(self, parent_layout):
        """创建验证码区域 -QW"""
        # 创建验证码容器 -QW
        verification_widget = QtWidgets.QWidget()
        verification_layout = QtWidgets.QVBoxLayout(verification_widget)
        verification_layout.setContentsMargins(0, 0, 0, 0)
        verification_layout.setSpacing(20)

        # 创建标题 -QW
        verification_title = QtWidgets.QLabel("验证码")
        verification_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        verification_layout.addWidget(verification_title)

        # 验证码标签 -QW
        code_label = QtWidgets.QLabel("验证码")
        code_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666666;
                margin-bottom: 8px;
            }
        """)
        verification_layout.addWidget(code_label)

        # 创建输入框容器，包含输入框和图标 -QW
        input_container = QtWidgets.QWidget()
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)

        # 验证码输入框 -QW
        self.cursor_verification_input = QtWidgets.QLineEdit()
        self.cursor_verification_input.setPlaceholderText("请输入验证码")
        self.cursor_verification_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 40px 12px 16px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #34a853;
                outline: none;
            }
        """)
        input_layout.addWidget(self.cursor_verification_input)

        # 添加输入框右侧图标 -QW
        icon_label = QtWidgets.QLabel("🔒")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #999999;
                background: transparent;
                border: none;
                margin-right: 12px;
            }
        """)
        icon_label.setFixedSize(20, 20)
        input_layout.addWidget(icon_label)

        verification_layout.addWidget(input_container)

        # 获取验证码按钮 -QW
        self.cursor_get_verification_btn = QtWidgets.QPushButton("获取验证码")
        self.cursor_get_verification_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #2d8f47;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #9aa0a6;
                color: #dadce0;
            }
        """)
        verification_layout.addWidget(self.cursor_get_verification_btn)

        # 添加弹性空间 -QW
        verification_layout.addStretch()

        parent_layout.addWidget(verification_widget)

    def augment_show_history_accounts(self):
        """Augment标签页显示历史账号下拉框 -QW"""
        try:
            print("[Augment标签页] 📋 历史账号按钮被点击")
            
            # 检查激活状态 -QW
            if not self.check_activation_status():
                return
            
            # 获取历史账号数据，使用augment专用方法（不带type参数） -QW
            history_accounts = self.augment_get_history_accounts()
            
            if not history_accounts:
                QtWidgets.QMessageBox.information(None, "提示", "暂无历史账号记录")
                return
            
            # 创建下拉菜单 -QW
            menu = QtWidgets.QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 4px 0px;
                    min-width: 300px;
                }
                QMenu::item {
                    padding: 10px 16px;
                    font-size: 13px;
                    color: #333333;
                    font-family: 'Monaco', 'Consolas', monospace;
                }
                QMenu::item:selected {
                    background-color: #f0f8ff;
                    color: #4285f4;
                }
                QMenu::item:hover {
                    background-color: #f0f8ff;
                }
                QMenu::item:disabled {
                    background-color: #f8f9fa;
                    color: #999999;
                    font-style: italic;
                    font-size: 12px;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #e0e0e0;
                    margin: 5px 10px;
                }
            """)
            
            # 获取Python配置的显示限制 -QW
            try:
                from tab_config_manager import TabConfigManager
                config_manager = TabConfigManager("config.py")
                display_limit = config_manager.get_history_account_display_limit()
            except:
                display_limit = 12  # 默认限制
            
            # 添加置顶提示信息 -QW
            tip_action = menu.addAction(f"历史账号 (显示前{len(history_accounts)}个，目前最多显示{display_limit}个)")
            tip_action.setEnabled(False)  # 设置为不可点击
            
            # 添加分隔线 -QW
            menu.addSeparator()
            
            # 添加历史账号到菜单，显示格式：账号 --- 时间 -QW
            for account_info in history_accounts:
                email = account_info.get("email", "")
                use_time = account_info.get("useTime", "")
                
                # 格式化显示文本：账号 --- 时间
                if use_time:
                    formatted_time = self.format_time_display(use_time)
                    display_text = f"{email} --- {formatted_time}"
                else:
                    display_text = email
                
                action = menu.addAction(display_text)
                # 点击时只传递邮箱地址
                action.triggered.connect(lambda checked, acc_email=email: self.augment_select_history_account(acc_email))
            
            # 在按钮下方显示菜单 -QW
            button_pos = self.augment_history_btn.mapToGlobal(self.augment_history_btn.rect().bottomLeft())
            menu.exec_(button_pos)
            
        except Exception as e:
            print(f"[Augment标签页] ❌ 显示历史账号失败: {str(e)}")
            QtWidgets.QMessageBox.critical(None, "错误", f"获取历史账号失败：{str(e)}")

    def augment_select_history_account(self, email):
        """Augment标签页选择历史账号 -QW"""
        try:
            if email and email.strip():
                self.augment_account_input.setText(email.strip())
                print(f"[Augment标签页] ✅ 选择历史账号: {email}")
            else:
                print("[Augment标签页] ⚠️ 选择的历史账号为空")
                
        except Exception as e:
            print(f"[Augment标签页] ❌ 选择历史账号失败: {str(e)}")

    def augment_copy_account_icon(self, event=None):
        """Augment标签页复制账号图标点击事件 -QW"""
        try:
            account_text = self.augment_account_input.text().strip()
            if account_text:
                # 复制到剪贴板 -QW
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(account_text)
                
                # 显示成功提示 -QW
                QtWidgets.QMessageBox.information(None, "复制成功", f"账号已复制到剪贴板：\n{account_text}")
                print(f"[Augment标签页] ✅ 账号复制成功: {account_text}")
            else:
                QtWidgets.QMessageBox.information(None, "提示", "请先获取账号")
                print("[Augment标签页] ⚠️ 账号为空，无法复制")
                
        except Exception as e:
            print(f"[Augment标签页] ❌ 复制账号失败: {str(e)}")
            QtWidgets.QMessageBox.critical(None, "复制失败", f"复制账号时发生错误：{str(e)}")

    def augment_get_history_accounts(self):
        """Augment标签页获取历史账号列表（不带type参数） -QW"""
        try:
            print("[Augment标签页] 🔍 开始获取历史账号")
            
            # 获取device_code和device_code_md5 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                raise Exception("设备信息未初始化，请重启应用")

            print(f"[Augment标签页] 🔑 使用设备信息: device_code={device_code[:20]}..., device_code_md5={device_code_md5[:10]}...")

            # 调用历史账号接口（不带type参数） -QW
            import requests

            # 构造请求URL（注意：不包含type参数）
            base_url = "http://82.157.20.83:9091"
            api_path = "/api/cursorLoginZs/getHistoryAccount"
            url = f"{base_url}{api_path}?device_code={device_code}&device_code_md5={device_code_md5}"

            print(f"[Augment标签页] 🌐 历史账号请求URL: {url}")

            # 发送GET请求
            proxies = {"http": None, "https": None}
            response = requests.get(url, proxies=proxies, timeout=10)

            # 检查响应状态码
            if response.status_code == 200:
                # 解析返回的JSON数据
                data = response.json()
                code = data.get("code")

                if code == '500':
                    error_msg = data.get("msg", "服务器返回错误")
                    raise Exception(f"{error_msg}")

                # 获取历史账号列表
                result_data = data.get("data")
                if result_data and isinstance(result_data, list):
                    # 处理对象数组，提取邮箱和时间字段 -QW
                    accounts = []
                    for account in result_data:
                        if isinstance(account, dict):
                            # 如果是字典对象，提取email和useTime字段
                            email = account.get("email", "")
                            use_time = account.get("useTime", "")
                            if email and email.strip():
                                # 保存完整的账号信息对象
                                accounts.append({
                                    "email": email.strip(),
                                    "useTime": use_time
                                })
                        elif isinstance(account, str):
                            # 如果是字符串，直接处理（兼容旧格式）
                            if account and account.strip():
                                accounts.append({
                                    "email": account.strip(),
                                    "useTime": ""
                                })
                    
                    # 按照时间排序，最新的在前面，根据配置限制显示数量 -QW
                    if accounts:
                        # 按照useTime排序（最新的在前面）
                        accounts_sorted = self.sort_accounts_by_time(accounts)
                        
                        # 从Python配置文件读取显示限制 -QW
                        try:
                            from tab_config_manager import TabConfigManager
                            config_manager = TabConfigManager("config.py")
                            display_limit = config_manager.get_history_account_display_limit()
                        except:
                            display_limit = 12  # 默认限制
                        
                        # 根据配置限制显示数量
                        accounts_limited = accounts_sorted[:display_limit]
                        print(f"[Augment标签页] ✅ 获取到 {len(accounts)} 个历史账号，显示前 {len(accounts_limited)} 个（配置限制: {display_limit}）")
                        return accounts_limited
                    else:
                        print(f"[Augment标签页] ✅ 获取到 {len(accounts)} 个历史账号")
                        return accounts
                else:
                    print("[Augment标签页] ⚠️ 暂无历史账号记录")
                    return []
            else:
                raise Exception(f"网络请求失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[Augment标签页] ❌ 获取历史账号失败: {str(e)}")
            raise e

    def create_history_account_tab_content(self):
        """创建历史账号标签页内容 -QW"""
        print("[标签页管理器] 创建历史账号标签页内容")

        # 设置历史账号标签页背景色和底部圆角 -QW
        self.history_account_tab.setStyleSheet("""
            QWidget {
                background-color: rgb(248, 252, 254);
                border-bottom-left-radius: 30px;
                border-bottom-right-radius: 30px;
            }
        """)

        # 创建主布局 -QW
        main_layout = QtWidgets.QVBoxLayout(self.history_account_tab)
        main_layout.setContentsMargins(10, 5, 10, 10)
        main_layout.setSpacing(10)

        # 顶部按钮已移到全局顶部栏，这里不再创建 -QW

        # 创建标题区域 -QW
        title_widget = QtWidgets.QWidget()
        title_layout = QtWidgets.QHBoxLayout(title_widget)
        title_layout.setContentsMargins(10, 5, 10, 5)

        title_label = QtWidgets.QLabel("Pro历史账号")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #333333;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        main_layout.addWidget(title_widget)

        # 创建历史账号列表区域 -QW
        self.create_history_account_list(main_layout)

        # 添加底部弹性空间 -QW
        main_layout.addStretch()

        # 初始化加载历史账号 -QW
        QtCore.QTimer.singleShot(500, self.refresh_history_accounts)

    def create_history_account_top_buttons(self, parent_layout):
        """创建历史账号标签页顶部按钮区域 -QW"""
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 添加弹性空间，将按钮推到右边 -QW
        top_layout.addStretch()

        # 创建最小化按钮 -QW
        self.history_minimize_btn = QtWidgets.QPushButton("−")
        self.history_minimize_btn.setFixedSize(30, 30)
        self.history_minimize_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
        """)
        self.history_minimize_btn.setToolTip("最小化窗口")
        self.history_minimize_btn.clicked.connect(self.minimize_application)

        # 创建关闭按钮 -QW
        self.history_close_btn = QtWidgets.QPushButton("✕")
        self.history_close_btn.setFixedSize(30, 30)
        self.history_close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
        """)
        self.history_close_btn.setToolTip("关闭应用程序")
        self.history_close_btn.clicked.connect(self.close_application)

        # 添加按钮到布局 -QW
        top_layout.addWidget(self.history_minimize_btn)
        top_layout.addSpacing(5)
        top_layout.addWidget(self.history_close_btn)

        parent_layout.addWidget(top_widget)

    def create_history_account_list(self, parent_layout):
        """创建历史账号表格区域 -QW"""
        # 创建表格控件 -QW
        self.history_table = QtWidgets.QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["序号", "邮箱", "使用时间", "用量", "状态", "操作"])
        
        # 设置表格样式 -QW
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e8eaed;
                border-radius: 12px;
                background-color: white;
                gridline-color: #f0f0f0;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f5f5f5;
            }
            QTableWidget::item:selected {
                background-color: #e8f4fd;
                color: #333333;
            }
            QTableWidget::item:hover {
                background-color: #f0f7ff;
            }
            QHeaderView::section {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                color: #495057;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                border-right: 1px solid #e9ecef;
            }
            QHeaderView::section:first {
                border-top-left-radius: 12px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 12px;
                border-right: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: #f5f5f5;
                border-radius: 4px;
                margin: 4px 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # 设置表格属性 -QW
        self.history_table.setMinimumHeight(350)
        self.history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.history_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        
        # 设置列宽 -QW（显示序号、邮箱、状态、操作四列）
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        
        # 列宽设置
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)     # 序号 - 固定
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)   # 邮箱 - 弹性
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)   # 使用时间 - 弹性（隐藏）
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)   # 用量 - 弹性（隐藏）
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)     # 状态 - 固定
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)     # 操作 - 固定
        
        # 设置固定列宽度
        self.history_table.setColumnWidth(0, 150)  # 序号
        self.history_table.setColumnWidth(4, 80)   # 状态
        self.history_table.setColumnWidth(5, 230)  # 操作
        
        # 隐藏使用时间列（索引2）和用量列（索引3）-QW
        self.history_table.hideColumn(2)
        self.history_table.hideColumn(3)
        
        # 设置行高 -QW
        self.history_table.verticalHeader().setDefaultSectionSize(55)
        
        parent_layout.addWidget(self.history_table)

    def refresh_history_accounts(self):
        """刷新历史账号列表 -QW"""
        import time as time_module
        
        # 刷新间隔检查（5秒内不重复刷新）-QW
        current_time = time_module.time()
        last_refresh = getattr(self, '_last_history_refresh_time', 0)
        if current_time - last_refresh < 5:
            print("[历史账号标签页] ⏳ 刷新间隔过短，跳过")
            return
        self._last_history_refresh_time = current_time
        
        print("[历史账号标签页] 🔄 开始刷新历史账号列表")

        try:
            # 检查激活状态 -QW
            if not self.check_activation_status():
                self.update_history_list_ui([])
                return

            # 获取设备信息 -QW
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                print("[历史账号标签页] ❌ 设备信息未初始化")
                self.update_history_list_ui([])
                return

            # 调用API获取Pro历史账号 -QW
            from CursorZsApi import CursorZsApi
            api = CursorZsApi()
            code, result = api.get_pro_history_account(device_code, device_code_md5)

            if code == '200' and result:
                print(f"[历史账号标签页] ✅ 获取到 {len(result)} 个历史账号")
                self.update_history_list_ui(result)
            else:
                print(f"[历史账号标签页] ⚠️ 获取历史账号失败: {result}")
                self.update_history_list_ui([])

        except Exception as e:
            print(f"[历史账号标签页] ❌ 刷新历史账号失败: {str(e)}")
            self.update_history_list_ui([])

    def update_history_list_ui(self, accounts):
        """更新历史账号表格UI -QW"""
        # 清空表格 -QW
        self.history_table.setRowCount(0)
        
        if not accounts:
            # 显示空表格提示 -QW
            self.history_table.setRowCount(1)
            empty_item = QtWidgets.QTableWidgetItem("暂无历史账号记录")
            empty_item.setTextAlignment(QtCore.Qt.AlignCenter)
            empty_item.setForeground(QtGui.QColor("#999999"))
            self.history_table.setSpan(0, 0, 1, 5)  # 合并所有列
            self.history_table.setItem(0, 0, empty_item)
        else:
            # 填充表格数据 -QW
            self.history_table.setRowCount(len(accounts))
            for row, account in enumerate(accounts):
                self.add_history_table_row(row, account)

    def add_history_table_row(self, row, account):
        """添加历史账号表格行 -QW"""
        # 序号 -QW
        index_item = QtWidgets.QTableWidgetItem(str(row + 1))
        index_item.setTextAlignment(QtCore.Qt.AlignCenter)
        index_item.setForeground(QtGui.QColor("#666666"))
        self.history_table.setItem(row, 0, index_item)
        
        # 邮箱 -QW
        email = account.get('email', '未知邮箱')
        email_item = QtWidgets.QTableWidgetItem(email)
        email_item.setForeground(QtGui.QColor("#333333"))
        font = email_item.font()
        font.setBold(True)
        email_item.setFont(font)
        self.history_table.setItem(row, 1, email_item)
        
        # 使用时间 -QW
        use_time = account.get('useTime', '')
        time_display = ""
        if use_time:
            try:
                from datetime import datetime
                if isinstance(use_time, str):
                    dt = datetime.fromisoformat(use_time.replace('Z', '+00:00'))
                    time_display = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    time_display = str(use_time)
            except:
                time_display = str(use_time) if use_time else ""
        
        time_item = QtWidgets.QTableWidgetItem(time_display if time_display else "-")
        time_item.setTextAlignment(QtCore.Qt.AlignCenter)
        time_item.setForeground(QtGui.QColor("#666666"))
        self.history_table.setItem(row, 2, time_item)
        
        # 用量（初始显示加载中）-QW
        usage_item = QtWidgets.QTableWidgetItem("...")
        usage_item.setTextAlignment(QtCore.Qt.AlignCenter)
        usage_item.setForeground(QtGui.QColor("#6b7280"))
        self.history_table.setItem(row, 3, usage_item)
        
        # 状态 -QW
        status_item = QtWidgets.QTableWidgetItem("Pro")
        status_item.setTextAlignment(QtCore.Qt.AlignCenter)
        status_item.setForeground(QtGui.QColor("#8b5cf6"))  # 紫色
        font = status_item.font()
        font.setBold(True)
        status_item.setFont(font)
        self.history_table.setItem(row, 4, status_item)
        
        # 操作按钮 -QW
        btn_widget = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(4, 4, 4, 4)
        btn_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        login_btn = QtWidgets.QPushButton("登录")
        login_btn.setFixedSize(60, 30)
        login_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        login_btn.clicked.connect(lambda checked, a=account: self.switch_to_history_account(a))
        btn_layout.addWidget(login_btn)
        
        self.history_table.setCellWidget(row, 5, btn_widget)
        
        # 异步加载用量数据（延迟100ms确保表格行已渲染）-QW
        QtCore.QTimer.singleShot(100 + row * 100, lambda r=row, a=account: self.load_account_usage_for_table(r, a))
    
    def load_account_usage_for_table(self, row, account):
        """异步加载表格中账号的用量数据 -QW"""
        import threading
        import time as time_module
        
        email = account.get('email', '')
        
        # 初始化缓存
        if not hasattr(self, '_usage_cache'):
            self._usage_cache = {}
        
        # 检查缓存（60秒内有效）
        cache_entry = self._usage_cache.get(email)
        if cache_entry:
            cache_time = cache_entry.get('time', 0)
            if time_module.time() - cache_time < 60:
                cached_data = cache_entry.get('data', {})
                total_cost = cached_data.get("totalCostUSD", 0) if cached_data.get("success") else -1
                text, color = self._calculate_usage_display(total_cost, account, cached_data)
                self._update_table_usage(row, text, color)
                return
        
        def load_usage():
            try:
                # 获取token
                token = account.get('token', '') or account.get('accessToken', '') or account.get('access_token', '')
                
                # 从token中提取user_id
                user_id = account.get('userId', '') or account.get('user_id', '')
                if not user_id and token:
                    user_id = self.extract_user_id_from_token(token)
                
                usage_data = None
                subscription_info = None
                
                # 1. 优先从客户端API获取
                if user_id and token:
                    subscription_info = self.get_subscription_from_api(user_id, token)
                    usage_data = self.get_model_usage_from_api(user_id, token)
                
                # 2. 如果客户端获取失败，从服务端获取
                if not usage_data or not usage_data.get("success"):
                    usage_data = self.get_usage_from_server(email)
                
                # 3. 计算显示内容
                final_data = usage_data if usage_data else {"success": False}
                total_cost = final_data.get("totalCostUSD", 0) if final_data.get("success") else -1
                
                # 合并订阅信息用于计算
                if subscription_info and subscription_info.get("success"):
                    account['_subscription_info'] = subscription_info
                
                text, color = self._calculate_usage_display(total_cost, account, subscription_info)
                
                # 保存到缓存
                self._usage_cache[email] = {
                    'data': final_data,
                    'time': time_module.time()
                }
                
                # 在主线程更新表格（添加延迟确保UI已渲染）-QW
                def do_update():
                    try:
                        if hasattr(self, 'history_table') and self.history_table is not None:
                            self._update_table_usage(row, text, color)
                    except Exception as ex:
                        print(f"[历史账号表格] ⚠️ 更新UI失败: {str(ex)}")
                
                # 使用定时器在主线程更新，添加50ms延迟确保表格已渲染
                QtCore.QTimer.singleShot(50, do_update)
                
            except Exception as e:
                print(f"[历史账号表格] ⚠️ 加载用量失败: {str(e)}")
                QtCore.QTimer.singleShot(50, lambda: self._update_table_usage(row, "N/A", "#9ca3af"))
        
        # 启动后台线程
        thread = threading.Thread(target=load_usage, daemon=True)
        thread.start()
    
    def _calculate_usage_display(self, total_cost, account, subscription_info=None):
        """计算用量显示文本和颜色 -QW"""
        if total_cost >= 0:
            # 获取订阅类型信息
            membership_type = ""
            individual_type = ""
            
            if subscription_info and isinstance(subscription_info, dict) and subscription_info.get("success"):
                membership_type = str(subscription_info.get('membershipType', '')).lower()
                individual_type = str(subscription_info.get('individualMembershipType', '')).lower()
            else:
                membership_type = str(account.get('membershipType', '')).lower()
                individual_type = str(account.get('individualMembershipType', '')).lower()
            
            subscription_type = str(account.get('subscription_type', '')).lower()
            
            # 判断订阅类型
            is_ultra = 'ultra' in subscription_type or 'ultra' in membership_type or 'ultra' in individual_type
            is_pro = ('pro' in subscription_type or 'pro' in membership_type or 
                     'pro' in individual_type or 'professional' in subscription_type)
            
            # 根据订阅类型设置除数
            if is_ultra:
                divisor = 400
            elif is_pro:
                divisor = 50
            else:
                divisor = 50  # 历史账号默认Pro
            
            percentage = min((total_cost / divisor) * 100, 100.0)
            
            if percentage >= 100:
                return "100%", "#ef4444"
            elif percentage > 80:
                return f"{percentage:.1f}%", "#f59e0b"
            elif percentage > 0:
                return f"{percentage:.1f}%", "#22c55e"
            else:
                return "0%", "#9ca3af"
        else:
            return "N/A", "#9ca3af"
    
    def _update_table_usage(self, row, text, color):
        """更新表格中的用量显示 -QW"""
        try:
            # 检查表格是否存在 -QW
            if not hasattr(self, 'history_table') or self.history_table is None:
                print(f"[历史账号表格] ⚠️ 表格未初始化，跳过更新")
                return
            
            if row < self.history_table.rowCount():
                usage_item = self.history_table.item(row, 3)
                if usage_item:
                    usage_item.setText(text)
                    usage_item.setForeground(QtGui.QColor(color))
                    print(f"[历史账号表格] ✅ 用量更新成功: 行{row} -> {text}")
        except Exception as e:
            print(f"[历史账号表格] ⚠️ 更新用量显示失败: {str(e)}")
    
    def create_history_account_item(self, account):
        """创建单个历史账号列表项（旧版卡片式，保留兼容性）-QW"""
        # 此方法已被表格式替代，保留以备将来使用 -QW
        pass

    def copy_history_account(self, account):
        """复制历史账号到剪贴板 -QW"""
        try:
            email = account.get('email', '')
            if email:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(email)
                print(f"[历史账号标签页] 📋 已复制账号: {email}")
                QtWidgets.QMessageBox.information(None, "提示", f"已复制账号到剪贴板:\n{email}")
        except Exception as e:
            print(f"[历史账号标签页] ❌ 复制账号失败: {str(e)}")

    def show_account_password(self, account):
        """显示账号密码 -QW"""
        try:
            email = account.get('email', '未知邮箱')
            pwd = account.get('pwd', '')
            
            if not pwd:
                QtWidgets.QMessageBox.warning(None, "提示", f"账号: {email}\n\n该账号没有密码信息")
                return
            
            # 创建自定义对话框显示密码 -QW
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("账号密码")
            msg_box.setIcon(QtWidgets.QMessageBox.Information)
            msg_box.setText(f"账号: {email}")
            msg_box.setInformativeText(f"密码: {pwd}")
            
            # 添加复制密码按钮 -QW
            copy_pwd_btn = msg_box.addButton("复制密码", QtWidgets.QMessageBox.ActionRole)
            copy_all_btn = msg_box.addButton("复制全部", QtWidgets.QMessageBox.ActionRole)
            close_btn = msg_box.addButton("关闭", QtWidgets.QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            clicked_btn = msg_box.clickedButton()
            if clicked_btn == copy_pwd_btn:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(pwd)
                print(f"[历史账号标签页] 📋 已复制密码")
                QtWidgets.QMessageBox.information(None, "提示", "密码已复制到剪贴板")
            elif clicked_btn == copy_all_btn:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(f"账号: {email}\n密码: {pwd}")
                print(f"[历史账号标签页] 📋 已复制账号和密码")
                QtWidgets.QMessageBox.information(None, "提示", "账号和密码已复制到剪贴板")
                
        except Exception as e:
            print(f"[历史账号标签页] ❌ 显示密码失败: {str(e)}")

    def switch_to_history_account(self, account):
        """切换到历史账号，执行自动登录 -QW"""
        try:
            email = account.get('email', '')
            token = account.get('token', '')
            pwd = account.get('pwd', '')

            print(f"[历史账号标签页] 🔄 切换到账号: {email}")

            if not email or not token:
                QtWidgets.QMessageBox.warning(None, "警告", "账号信息不完整，无法切换")
                return

            # 确认对话框 -QW
            reply = QtWidgets.QMessageBox.question(
                None,
                "确认切换",
                f"确定要切换到以下账号吗？\n\n{email}\n\nCursor将会重启，请确保代码已保存。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply != QtWidgets.QMessageBox.Yes:
                print("[历史账号标签页] ❌ 用户取消切换")
                return

            # 执行切换逻辑，复用刷新cursor的逻辑 -QW
            print("[历史账号标签页] 🚀 开始执行账号切换...")

            # 关闭Cursor -QW
            try:
                from go import ExitCursor, open_cursor
                ExitCursor()
            except Exception as e:
                print(f"[历史账号标签页] ⚠️ 关闭Cursor失败: {str(e)}")

            # 重置机器码 -QW
            try:
                from ResetMachine import MachineIDResetter
                resetter = MachineIDResetter()
                resetter.reset_machine_ids()
            except Exception as e:
                print(f"[历史账号标签页] ⚠️ 重置机器码失败: {str(e)}")

            # 更新认证信息 -QW
            try:
                from CursorAuthManager import CursorAuthManager
                auth_manager = CursorAuthManager()
                auth_manager.update_auth(email, token, token)
                print(f"[历史账号标签页] ✅ 认证信息更新成功")
            except Exception as e:
                print(f"[历史账号标签页] ❌ 更新认证信息失败: {str(e)}")
                QtWidgets.QMessageBox.critical(None, "错误", f"更新认证信息失败: {str(e)}")
                return

            # 执行突破 -QW
            try:
                from tupo41 import tupo41
                tupo41()
            except Exception as e:
                print(f"[历史账号标签页] ⚠️ 突破执行失败: {str(e)}")

            # 打开Cursor -QW
            try:
                from go import open_cursor
                open_cursor()
            except Exception as e:
                print(f"[历史账号标签页] ⚠️ 打开Cursor失败: {str(e)}")

            print(f"[历史账号标签页] ✅ 账号切换完成")
            QtWidgets.QMessageBox.information(None, "成功", f"账号切换成功！\n\n当前账号: {email}")

            # 刷新历史账号列表 -QW
            self.refresh_history_accounts()
            
            # 刷新主窗口会员状态显示（更新pro_count等）-QW
            try:
                if hasattr(self.main_window, 'initCursor'):
                    self.main_window.initCursor()
                    print("[历史账号标签页] ✅ 已刷新会员状态显示")
            except Exception as e:
                print(f"[历史账号标签页] ⚠️ 刷新会员状态失败: {str(e)}")

        except Exception as e:
            print(f"[历史账号标签页] ❌ 切换账号失败: {str(e)}")
            QtWidgets.QMessageBox.critical(None, "错误", f"切换账号失败: {str(e)}")

    # ==================== 账号用量相关方法 ====================

    def get_api_headers(self, user_id: str, access_token: str) -> dict:
        """生成Cursor API请求的通用headers -QW"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Referer": "https://cursor.com/dashboard",
            "Origin": "https://cursor.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cookie": f"WorkosCursorSessionToken={user_id}%3A%3A{access_token}"
        }

    def get_subscription_from_api(self, user_id: str, access_token: str) -> dict:
        """从Cursor API获取订阅信息 -QW"""
        import requests
        
        try:
            headers = self.get_api_headers(user_id, access_token)
            url = "https://cursor.com/api/auth/stripe"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                membership_type = data.get("membershipType", "")
                individual_type = data.get("individualMembershipType", "")
                print(f"[订阅API] ✅ 获取订阅信息成功: membershipType={membership_type}")
                return {
                    "success": True,
                    "membershipType": membership_type,
                    "individualMembershipType": individual_type,
                    "data": data
                }
            else:
                print(f"[订阅API] ❌ 请求失败: {response.status_code}")
                return {"success": False}
                
        except Exception as e:
            print(f"[订阅API] ❌ 获取订阅信息失败: {str(e)}")
            return {"success": False}

    def get_model_usage_from_api(self, user_id: str, access_token: str) -> dict:
        """从Cursor API获取模型使用量 -QW"""
        import requests
        import time
        
        try:
            headers = self.get_api_headers(user_id, access_token)
            aggregated_url = "https://cursor.com/api/dashboard/get-aggregated-usage-events"
            
            # 构建请求体
            current_time_ms = int(time.time() * 1000)
            start_time_ms = current_time_ms - (30 * 24 * 60 * 60 * 1000)  # 30天前
            
            request_data = {
                "teamId": -1,
                "startDate": start_time_ms,
                "endDate": current_time_ms
            }
            
            response = requests.post(aggregated_url, headers=headers, json=request_data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                total_cost_cents = data.get("totalCostCents", 0)
                total_cost_usd = total_cost_cents / 100 if total_cost_cents else 0
                
                return {
                    "success": True,
                    "totalCostUSD": total_cost_usd,
                    "totalCostCents": total_cost_cents,
                    "source": "client_api"
                }
            else:
                print(f"[用量API] ❌ 请求失败: {response.status_code}")
                return {"success": False, "error": f"API返回 {response.status_code}"}
                
        except Exception as e:
            print(f"[用量API] ❌ 客户端获取用量失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_usage_from_server(self, email: str) -> dict:
        """从服务端获取账号用量（备用方案）-QW"""
        import requests
        
        try:
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)
            
            if not device_code or not device_code_md5:
                return {"success": False, "error": "设备信息未初始化"}
            
            # 调用服务端API获取用量（需要服务端支持此接口）
            from CursorZsApi import CursorZsApi, BASE_URL, BASE_API
            url = f"{BASE_URL}{BASE_API}/getAccountUsage"
            params = {
                "device_code": device_code,
                "device_code_md5": device_code_md5,
                "email": email
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "200":
                    usage_data = data.get("data", {})
                    return {
                        "success": True,
                        "totalCostUSD": usage_data.get("totalCostUSD", 0),
                        "source": "server_api"
                    }
                else:
                    return {"success": False, "error": data.get("msg", "服务端返回错误")}
            else:
                return {"success": False, "error": f"服务端返回 {response.status_code}"}
                
        except Exception as e:
            print(f"[用量API] ❌ 服务端获取用量失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def calculate_usage_percentage(self, total_cost_usd: float, subscription_type: str = "pro") -> float:
        """计算用量百分比 -QW"""
        # 根据订阅类型设置除数
        if "ultra" in subscription_type.lower():
            divisor = 400
        elif "pro" in subscription_type.lower():
            divisor = 50
        else:
            divisor = 10
        
        percentage = (total_cost_usd / divisor) * 100
        return min(percentage, 100.0)  # 封顶100%

    def display_usage_data(self, usage_label: QtWidgets.QLabel, usage_data: dict):
        """显示用量数据到标签 -QW"""
        try:
            if not usage_data.get("success"):
                usage_label.setText("N/A")
                usage_label.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: bold; background: transparent; border: none;")
                return
            
            total_cost = usage_data.get("totalCostUSD", 0)
            percentage = self.calculate_usage_percentage(total_cost)
            
            # 根据百分比设置颜色
            if percentage >= 100:
                usage_label.setText("100%")
                usage_label.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: bold; background: transparent; border: none;")
            elif percentage > 80:
                usage_label.setText(f"{percentage:.1f}%")
                usage_label.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: bold; background: transparent; border: none;")
            elif percentage > 0:
                usage_label.setText(f"{percentage:.1f}%")
                usage_label.setStyleSheet("color: #16a34a; font-size: 12px; font-weight: bold; background: transparent; border: none;")
            else:
                usage_label.setText("0%")
                usage_label.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: bold; background: transparent; border: none;")
                
        except Exception as e:
            print(f"[用量显示] ❌ 显示用量失败: {str(e)}")
            usage_label.setText("错误")
            usage_label.setStyleSheet("color: #ef4444; font-size: 11px; background: transparent; border: none;")

    def extract_user_id_from_token(self, token: str) -> str:
        """从JWT token中提取user_id -QW"""
        import base64
        import json
        
        try:
            if not token:
                return ""
            
            # JWT格式: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return ""
            
            # 解码payload (第二部分)
            payload = parts[1]
            # 添加padding
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            
            # sub字段格式: "auth0|user_01K4RWWBD1V7B7XWA8N83MV0JK"
            sub = data.get('sub', '')
            if '|' in sub:
                user_id = sub.split('|')[1]  # 提取 user_xxx 部分
                print(f"[Token解析] ✅ 提取user_id: {user_id}")
                return user_id
            
            return ""
        except Exception as e:
            print(f"[Token解析] ❌ 解析token失败: {str(e)}")
            return ""

    def load_account_usage_async(self, account: dict, usage_label: QtWidgets.QLabel):
        """异步加载账号用量 -QW"""
        import time as time_module
        
        # 初始化用量缓存
        if not hasattr(self, '_usage_cache'):
            self._usage_cache = {}  # {email: {'data': usage_data, 'time': timestamp}}
        
        # 初始化正在加载的账号集合（防止重复请求）
        if not hasattr(self, '_loading_accounts'):
            self._loading_accounts = set()
        
        email = account.get('email', '')
        
        # 检查是否正在加载
        if email in self._loading_accounts:
            print(f"[用量加载] ⏳ 账号正在加载中，跳过: {email}")
            return
        
        # 检查缓存（60秒内有效）
        cache_entry = self._usage_cache.get(email)
        if cache_entry:
            cache_time = cache_entry.get('time', 0)
            if time_module.time() - cache_time < 60:
                cached_data = cache_entry.get('data', {})
                print(f"[用量加载] 📦 使用缓存数据: {email}")
                # 直接显示缓存数据
                total_cost = cached_data.get("totalCostUSD", 0) if cached_data.get("success") else -1
                if total_cost >= 0:
                    divisor = 50  # Pro默认
                    percentage = min((total_cost / divisor) * 100, 100.0)
                    if percentage >= 100:
                        text, color = "100%", "#dc2626"
                    elif percentage > 80:
                        text, color = f"{percentage:.1f}%", "#f59e0b"
                    elif percentage > 0:
                        text, color = f"{percentage:.1f}%", "#16a34a"
                    else:
                        text, color = "0%", "#9ca3af"
                else:
                    text, color = "N/A", "#9ca3af"
                usage_label.setText(text)
                usage_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
                return
        
        # 标记为正在加载
        self._loading_accounts.add(email)
        
        # 保存引用防止被垃圾回收
        label_ref = usage_label
        
        def load_usage():
            import time as time_mod
            try:
                # 获取token（服务端返回的JWT token）
                token = account.get('token', '') or account.get('accessToken', '') or account.get('access_token', '')
                
                # 从token中提取user_id
                user_id = account.get('userId', '') or account.get('user_id', '')
                if not user_id and token:
                    user_id = self.extract_user_id_from_token(token)
                
                usage_data = None
                subscription_info = None
                
                # 1. 优先从客户端API获取（如果有token信息）
                if user_id and token:
                    print(f"[用量加载] 🔄 尝试从客户端API获取: {email}")
                    print(f"[用量加载] 📋 user_id: {user_id[:20]}...")
                    
                    # 1.1 获取订阅信息（判断账号类型）
                    subscription_info = self.get_subscription_from_api(user_id, token)
                    
                    # 1.2 获取用量数据
                    usage_data = self.get_model_usage_from_api(user_id, token)
                    
                    if usage_data.get("success"):
                        print(f"[用量加载] ✅ 客户端API获取成功: {email} - ${usage_data.get('totalCostUSD', 0):.2f}")
                else:
                    print(f"[用量加载] ⚠️ 账号缺少token信息: {email}")
                
                # 2. 如果客户端获取失败，从服务端获取
                if not usage_data or not usage_data.get("success"):
                    print(f"[用量加载] 🔄 尝试从服务端获取用量: {email}")
                    usage_data = self.get_usage_from_server(email)
                    
                    if usage_data.get("success"):
                        print(f"[用量加载] ✅ 服务端获取成功: {email} - ${usage_data.get('totalCostUSD', 0):.2f}")
                
                # 3. 在主线程更新UI - 使用 invokeMethod 确保线程安全
                final_data = usage_data if usage_data else {"success": False}
                total_cost = final_data.get("totalCostUSD", 0) if final_data.get("success") else -1
                
                # 计算百分比 - 按照XC-Cursor的逻辑
                if total_cost >= 0:
                    # 根据订阅状态决定除数：Ultra除以400，Pro除以50，其他除以10
                    # 优先使用API返回的订阅信息
                    membership_type = ""
                    individual_type = ""
                    
                    if subscription_info and subscription_info.get("success"):
                        membership_type = str(subscription_info.get('membershipType', '')).lower()
                        individual_type = str(subscription_info.get('individualMembershipType', '')).lower()
                    else:
                        # 备用：从account中获取
                        membership_type = str(account.get('membershipType', '')).lower()
                        individual_type = str(account.get('individualMembershipType', '')).lower()
                    
                    subscription_type = str(account.get('subscription_type', '')).lower()
                    
                    # 判断订阅类型
                    is_ultra = (
                        'ultra' in subscription_type or 
                        'ultra' in membership_type or 
                        'ultra' in individual_type
                    )
                    
                    is_pro = (
                        'pro' in subscription_type or 
                        'pro' in membership_type or 
                        'pro' in individual_type or
                        'professional' in subscription_type or
                        'professional' in membership_type
                    )
                    
                    # 根据订阅类型设置除数
                    if is_ultra:
                        divisor = 400
                        sub_label = "Ultra"
                    elif is_pro:
                        divisor = 50
                        sub_label = "Pro"
                    else:
                        divisor = 10
                        sub_label = "Free"
                    
                    percentage = (total_cost / divisor) * 100
                    
                    # 封顶100%
                    if percentage > 100:
                        percentage = 100.0
                    
                    if percentage >= 100:
                        text = "100%"
                        color = "#dc2626"
                    elif percentage > 80:
                        text = f"{percentage:.1f}%"
                        color = "#f59e0b"
                    elif percentage > 0:
                        text = f"{percentage:.1f}%"
                        color = "#16a34a"
                    else:
                        text = "0%"
                        color = "#9ca3af"
                    
                    print(f"[用量计算] {email}: ${total_cost:.2f} / ${divisor} ({sub_label}) = {percentage:.1f}%")
                else:
                    text = "N/A"
                    color = "#9ca3af"
                
                # 保存到缓存 -QW
                self._usage_cache[email] = {
                    'data': final_data,
                    'time': time_mod.time()
                }
                
                # 使用 invokeMethod 在主线程更新
                try:
                    QtCore.QMetaObject.invokeMethod(
                        label_ref,
                        "setText",
                        QtCore.Qt.QueuedConnection,
                        QtCore.Q_ARG(str, text)
                    )
                    QtCore.QMetaObject.invokeMethod(
                        label_ref,
                        "setStyleSheet",
                        QtCore.Qt.QueuedConnection,
                        QtCore.Q_ARG(str, f"color: {color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
                    )
                    print(f"[用量显示] ✅ UI更新: {email} -> {text}")
                except RuntimeError:
                    print(f"[用量显示] ⚠️ 控件已销毁: {email}")
                
            except Exception as e:
                print(f"[用量加载] ❌ 加载用量失败: {str(e)}")
                try:
                    QtCore.QMetaObject.invokeMethod(
                        label_ref,
                        "setText",
                        QtCore.Qt.QueuedConnection,
                        QtCore.Q_ARG(str, "N/A")
                    )
                except:
                    pass
            finally:
                # 从正在加载集合中移除 -QW
                if email in self._loading_accounts:
                    self._loading_accounts.discard(email)
        
        # 启动后台线程
        thread = threading.Thread(target=load_usage, daemon=True)
        thread.start()

    # ==================== Windsurf标签页相关方法 ====================

    def create_windsurf_tab_content(self):
        """创建Windsurf标签页内容 -QW"""
        print("[标签页管理器] 创建Windsurf标签页内容")

        # 设置Windsurf标签页背景色和底部圆角 -QW
        self.windsurf_tab.setStyleSheet("""
            QWidget {
                background-color: rgb(248, 252, 254);
                border-bottom-left-radius: 30px;
                border-bottom-right-radius: 30px;
            }
        """)

        # 创建主布局 -QW
        main_layout = QtWidgets.QVBoxLayout(self.windsurf_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部按钮已移到全局顶部栏，这里不再创建 -QW

        # 创建主要内容区域 -QW
        self.create_windsurf_main_content(main_layout)
        
        # 自动加载缓存的凭证 -QW
        self.load_cached_windsurf_credentials()

    def create_windsurf_top_buttons(self, parent_layout):
        """创建Windsurf标签页顶部按钮区域 -QW"""
        # 创建顶部区域，包含最小化和关闭按钮 -QW
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)

        # 添加弹性空间，将按钮推到右边 -QW
        top_layout.addStretch()

        # 创建最小化按钮 -QW
        self.windsurf_minimize_btn = QtWidgets.QPushButton("−")
        self.windsurf_minimize_btn.setFixedSize(30, 30)
        self.windsurf_minimize_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.windsurf_minimize_btn.setToolTip("最小化窗口")
        self.windsurf_minimize_btn.clicked.connect(self.minimize_application)

        # 创建关闭按钮 -QW
        self.windsurf_close_btn = QtWidgets.QPushButton("✕")
        self.windsurf_close_btn.setFixedSize(30, 30)
        self.windsurf_close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: rgba(255,255,255,200);
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(35, 118, 238), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                padding-left: 2px;
                padding-top: 2px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(25, 108, 228), stop:1 rgb(3, 180, 81));
            }
        """)
        self.windsurf_close_btn.setToolTip("关闭应用程序")
        self.windsurf_close_btn.clicked.connect(self.close_application)

        # 添加按钮到布局 -QW
        top_layout.addWidget(self.windsurf_minimize_btn)
        top_layout.addSpacing(5)
        top_layout.addWidget(self.windsurf_close_btn)

        parent_layout.addWidget(top_widget)

    def create_windsurf_main_content(self, parent_layout):
        """创建Windsurf标签页主要内容 -QW"""
        print("[标签页管理器] 创建Windsurf主要内容区域")

        # 创建主容器 -QW
        main_container = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(main_container)
        main_layout.setContentsMargins(40, 20, 40, 20)
        main_layout.setSpacing(15)

        # 公告区域 -QW
        notice_frame = QtWidgets.QFrame()
        notice_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #e8f4fd, stop:1 #f0f7ff);
                border: 1px solid rgba(45, 128, 248, 0.3);
                border-radius: 12px;
                padding: 12px;
            }
        """)
        notice_layout = QtWidgets.QVBoxLayout(notice_frame)
        notice_layout.setContentsMargins(15, 10, 15, 10)
        notice_layout.setSpacing(5)
        
        notice_title = QtWidgets.QLabel("📢 使用说明")
        notice_title.setStyleSheet("color: #1565c0; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        notice_layout.addWidget(notice_title)
        
        notice_text = QtWidgets.QLabel("点击下方按钮获取 Windsurf 邮箱和密码，获取后请尽快使用。\n教程里面有手动登陆的流程，可以自行搜索一下")
        notice_text.setStyleSheet("color: #1976d2; font-size: 13px; background: transparent; border: none;")
        notice_text.setWordWrap(True)
        notice_layout.addWidget(notice_text)
        
        main_layout.addWidget(notice_frame)

        # 添加间距 -QW
        main_layout.addSpacing(10)

        # 获取按钮 -QW
        self.windsurf_get_account_btn = QtWidgets.QPushButton("获取 Windsurf 账号")
        self.windsurf_get_account_btn.setMinimumHeight(55)
        self.windsurf_get_account_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        self.windsurf_get_account_btn.setFont(font)
        self.windsurf_get_account_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:0.5 rgb(34, 164, 175), stop:1 rgb(23, 200, 101));
                color: white;
                border: none;
                border-radius: 16px;
                padding: 15px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:0.5 rgb(24, 154, 165), stop:1 rgb(13, 190, 91));
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(25, 108, 228), stop:0.5 rgb(14, 144, 155), stop:1 rgb(3, 180, 81));
                padding-left: 1px;
                padding-top: 1px;
            }
            QPushButton:disabled {
                background: #e0e0e0;
                color: #9e9e9e;
            }
        """)
        self.windsurf_get_account_btn.clicked.connect(self.get_windsurf_account)
        main_layout.addWidget(self.windsurf_get_account_btn)

        # 添加间距 -QW
        main_layout.addSpacing(15)

        # 邮箱显示区域 -QW
        email_label = QtWidgets.QLabel("邮箱地址")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        font.setBold(True)
        email_label.setFont(font)
        email_label.setStyleSheet("color: #333333;")
        main_layout.addWidget(email_label)

        email_row = QtWidgets.QWidget()
        email_row_layout = QtWidgets.QHBoxLayout(email_row)
        email_row_layout.setContentsMargins(0, 0, 0, 0)
        email_row_layout.setSpacing(10)

        self.windsurf_email_display = QtWidgets.QLineEdit()
        self.windsurf_email_display.setReadOnly(True)
        self.windsurf_email_display.setPlaceholderText("点击上方按钮获取邮箱")
        self.windsurf_email_display.setMinimumHeight(45)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        self.windsurf_email_display.setFont(font)
        self.windsurf_email_display.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #e8eaed;
                border-radius: 12px;
                padding: 10px 15px;
                color: #333333;
            }
            QLineEdit:hover {
                border: 2px solid #c4c9cf;
            }
            QLineEdit:focus {
                border: 2px solid rgb(45, 128, 248);
                background-color: #fafcff;
            }
        """)
        email_row_layout.addWidget(self.windsurf_email_display)

        self.windsurf_copy_email_btn = QtWidgets.QPushButton("复制")
        self.windsurf_copy_email_btn.setFixedWidth(90)
        self.windsurf_copy_email_btn.setMinimumHeight(45)
        self.windsurf_copy_email_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        font.setBold(True)
        self.windsurf_copy_email_btn.setFont(font)
        self.windsurf_copy_email_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: rgb(45, 128, 248);
                border: 2px solid rgb(45, 128, 248);
                border-radius: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                border: none;
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
                color: white;
                border: none;
            }
        """)
        self.windsurf_copy_email_btn.clicked.connect(self.copy_windsurf_email)
        email_row_layout.addWidget(self.windsurf_copy_email_btn)

        main_layout.addWidget(email_row)

        # 添加间距 -QW
        main_layout.addSpacing(15)

        # 密码显示区域 -QW
        password_label = QtWidgets.QLabel("登录密码")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        font.setBold(True)
        password_label.setFont(font)
        password_label.setStyleSheet("color: #333333;")
        main_layout.addWidget(password_label)

        password_row = QtWidgets.QWidget()
        password_row_layout = QtWidgets.QHBoxLayout(password_row)
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        password_row_layout.setSpacing(10)

        self.windsurf_password_display = QtWidgets.QLineEdit()
        self.windsurf_password_display.setReadOnly(True)
        self.windsurf_password_display.setPlaceholderText("点击上方按钮获取密码")
        self.windsurf_password_display.setMinimumHeight(45)
        self.windsurf_password_display.setEchoMode(QtWidgets.QLineEdit.Password)  # 默认显示为圆点 -QW
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        self.windsurf_password_display.setFont(font)
        self.windsurf_password_display.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #e8eaed;
                border-radius: 12px;
                padding: 10px 15px;
                color: #333333;
            }
            QLineEdit:hover {
                border: 2px solid #c4c9cf;
            }
            QLineEdit:focus {
                border: 2px solid rgb(45, 128, 248);
                background-color: #fafcff;
            }
        """)
        password_row_layout.addWidget(self.windsurf_password_display)

        # 眼睛图标按钮（切换密码显示/隐藏） -QW
        self.windsurf_toggle_password_btn = QtWidgets.QPushButton("👁")
        self.windsurf_toggle_password_btn.setFixedWidth(50)
        self.windsurf_toggle_password_btn.setMinimumHeight(45)
        self.windsurf_toggle_password_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.windsurf_toggle_password_btn.setToolTip("显示/隐藏密码")
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        self.windsurf_toggle_password_btn.setFont(font)
        self.windsurf_toggle_password_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #666666;
                border: 2px solid #e8eaed;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #e8f0fe;
                border-color: rgb(45, 128, 248);
                color: rgb(45, 128, 248);
            }
            QPushButton:pressed {
                background-color: #d2e3fc;
            }
        """)
        self.windsurf_toggle_password_btn.clicked.connect(self.toggle_windsurf_password_visibility)
        self.windsurf_password_visible = False  # 密码可见状态标志 -QW
        password_row_layout.addWidget(self.windsurf_toggle_password_btn)

        self.windsurf_copy_password_btn = QtWidgets.QPushButton("复制")
        self.windsurf_copy_password_btn.setFixedWidth(90)
        self.windsurf_copy_password_btn.setMinimumHeight(45)
        self.windsurf_copy_password_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(13)
        font.setBold(True)
        self.windsurf_copy_password_btn.setFont(font)
        self.windsurf_copy_password_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: rgb(45, 128, 248);
                border: 2px solid rgb(45, 128, 248);
                border-radius: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                border: none;
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
                color: white;
                border: none;
            }
        """)
        self.windsurf_copy_password_btn.clicked.connect(self.copy_windsurf_password)
        password_row_layout.addWidget(self.windsurf_copy_password_btn)

        main_layout.addWidget(password_row)

        # 添加弹性空间 -QW
        main_layout.addStretch()

        # 将主容器添加到父布局 -QW
        parent_layout.addWidget(main_container)

    def get_windsurf_account(self):
        """获取Windsurf账号 -QW"""
        try:
            print("[Windsurf标签页] 开始获取Windsurf账号...")
            
            # 禁用获取按钮，防止重复点击
            self.windsurf_get_account_btn.setEnabled(False)
            self.windsurf_get_account_btn.setText("获取中...")

            # 获取设备信息
            device_code = getattr(self.main_window, 'device_code', None)
            device_code_md5 = getattr(self.main_window, 'device_code_md5', None)

            if not device_code or not device_code_md5:
                print("[Windsurf标签页] ❌ 设备信息未初始化")
                error_dialog = WindsurfErrorDialog("设备信息未初始化，请重启应用", self.windsurf_tab)
                error_dialog.exec_()
                return

            # 调用API获取Windsurf凭证
            from CursorZsApi import CursorZsApi
            api = CursorZsApi()
            code, result = api.get_windsurf_credentials(device_code, device_code_md5)

            if code == '200' and result:
                # 获取成功，显示邮箱和密码
                email = result.get("email", "")
                password = result.get("windsurfPwd", "")  # API返回的字段
                
                self.windsurf_email_display.setText(email)
                self.windsurf_password_display.setText(password)
                
                print(f"[Windsurf标签页] ✅ 获取成功 - 邮箱: {email}")
                
                # 💾 保存到数据库 -QW
                try:
                    cache_manager = get_app_cache_manager()
                    cache_manager.save_windsurf_credentials(email, password)
                except Exception as e:
                    print(f"[Windsurf标签页] ⚠️ 保存到数据库失败: {str(e)}")
                
                # 显示自定义成功弹窗
                success_dialog = WindsurfSuccessDialog(email, self.windsurf_tab)
                success_dialog.exec_()
            else:
                # 获取失败 - 显示错误弹窗
                error_msg = result if isinstance(result, str) else "获取Windsurf账号失败，请稍后重试"
                print(f"[Windsurf标签页] ❌ 获取失败: {error_msg}")
                
                # 显示自定义失败弹窗
                error_dialog = WindsurfErrorDialog(error_msg, self.windsurf_tab)
                error_dialog.exec_()

        except Exception as e:
            error_msg = f"获取Windsurf账号时出错: {str(e)}"
            print(f"[Windsurf标签页] ❌ {error_msg}")
            
            # 显示自定义失败弹窗
            error_dialog = WindsurfErrorDialog(error_msg, self.windsurf_tab)
            error_dialog.exec_()
        finally:
            # 恢复获取按钮状态
            self.windsurf_get_account_btn.setEnabled(True)
            self.windsurf_get_account_btn.setText("获取 Windsurf 账号")

    def copy_windsurf_email(self):
        """复制Windsurf邮箱 -QW"""
        email = self.windsurf_email_display.text()
        if email and email != "点击上方按钮获取邮箱":
            # 先复制到剪贴板
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(email)
            print(f"[Windsurf标签页] ✅ 邮箱已复制: {email}")
            
            # 显示成功提示弹窗
            tip_dialog = WindsurfTipDialog("复制邮箱成功", "success", self.windsurf_tab)
            tip_dialog.exec_()
        else:
            print(f"[Windsurf标签页] ⚠️ 没有可以复制的邮箱")
            
            # 显示警告提示弹窗
            tip_dialog = WindsurfTipDialog("没有可以复制的邮箱", "warning", self.windsurf_tab)
            tip_dialog.exec_()

    def copy_windsurf_password(self):
        """复制Windsurf密码 -QW"""
        password = self.windsurf_password_display.text()
        if password and password != "点击上方按钮获取密码":
            # 先复制到剪贴板
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(password)
            print(f"[Windsurf标签页] ✅ 密码已复制")
            
            # 显示成功提示弹窗
            tip_dialog = WindsurfTipDialog("复制密码成功", "success", self.windsurf_tab)
            tip_dialog.exec_()
        else:
            print(f"[Windsurf标签页] ⚠️ 没有可以复制的密码")
            
            # 显示警告提示弹窗
            tip_dialog = WindsurfTipDialog("没有可以复制的密码", "warning", self.windsurf_tab)
            tip_dialog.exec_()

    def toggle_windsurf_password_visibility(self):
        """切换Windsurf密码显示/隐藏 -QW"""
        if self.windsurf_password_visible:
            # 当前是明文，切换为密文
            self.windsurf_password_display.setEchoMode(QtWidgets.QLineEdit.Password)
            self.windsurf_toggle_password_btn.setText("👁")
            self.windsurf_password_visible = False
            print("[Windsurf标签页] 密码已隐藏")
        else:
            # 当前是密文，切换为明文
            self.windsurf_password_display.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.windsurf_toggle_password_btn.setText("👁‍🗨")
            self.windsurf_password_visible = True
            print("[Windsurf标签页] 密码已显示")

    def load_cached_windsurf_credentials(self):
        """加载缓存的 Windsurf 凭证（从数据库） -QW"""
        try:
            cache_manager = get_app_cache_manager()
            credentials = cache_manager.load_windsurf_credentials()
            
            if credentials:
                email = credentials.get("email", "")
                password = credentials.get("password", "")
                
                if email:
                    self.windsurf_email_display.setText(email)
                    print(f"[Windsurf标签页] ✅ 已自动填充缓存的邮箱: {email}")
                
                if password:
                    self.windsurf_password_display.setText(password)
                    print(f"[Windsurf标签页] ✅ 已自动填充缓存的密码")
        
        except Exception as e:
            print(f"[Windsurf标签页] ⚠️ 加载缓存失败: {str(e)}")
