#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浏览器管理工具
基于DrissionPage和Selenium的浏览器管理器
支持Chrome浏览器自动化操作，包含代理设置和扩展加载
支持跨平台（Windows、macOS、Linux）
-QW
"""

import sys
import os
import logging
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List


class BrowserManager:
    """浏览器管理器 -QW"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化浏览器管理器
        
        Args:
            config: 配置字典，包含代理、扩展等配置
        """
        self.browser = None
        self.config = config or {}
        self.system = platform.system().lower()
        
        # 设置日志 -QW
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        print(f"[浏览器管理器] 初始化完成，系统: {self.system}")
    
    def init_browser(self, user_agent: Optional[str] = None, headless: bool = False) -> Any:
        """
        初始化浏览器
        
        Args:
            user_agent: 自定义User-Agent
            headless: 是否使用无头模式
            
        Returns:
            浏览器实例
        """
        try:
            # 优先尝试DrissionPage -QW
            if self._is_drission_page_available():
                print("[浏览器管理器] 使用DrissionPage初始化浏览器")
                return self._init_drission_page_browser(user_agent, headless)
            
            # 备选Selenium -QW
            elif self._is_selenium_available():
                print("[浏览器管理器] 使用Selenium初始化浏览器")
                return self._init_selenium_browser(user_agent, headless)
            
            else:
                raise ImportError("未找到可用的浏览器自动化库（DrissionPage或Selenium）")
                
        except Exception as e:
            print(f"[浏览器管理器] ❌ 初始化浏览器失败: {str(e)}")
            raise
    
    def _is_drission_page_available(self) -> bool:
        """检查DrissionPage是否可用 -QW"""
        try:
            from DrissionPage import ChromiumOptions, Chromium
            return True
        except ImportError:
            return False
    
    def _is_selenium_available(self) -> bool:
        """检查Selenium是否可用 -QW"""
        try:
            from selenium import webdriver
            return True
        except ImportError:
            return False
    
    def _init_drission_page_browser(self, user_agent: Optional[str] = None, headless: bool = False) -> Any:
        """使用DrissionPage初始化浏览器 -QW"""
        from DrissionPage import ChromiumOptions, Chromium
        
        try:
            co = self._get_drission_page_options(user_agent, headless)
            self.browser = Chromium(co)
            print("[浏览器管理器] ✅ DrissionPage浏览器初始化成功")
            return self.browser
        except Exception as e:
            print(f"[浏览器管理器] ❌ DrissionPage浏览器初始化失败: {str(e)}")
            raise
    
    def _init_selenium_browser(self, user_agent: Optional[str] = None, headless: bool = False) -> Any:
        """使用Selenium初始化浏览器 -QW"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        try:
            chrome_options = self._get_selenium_options(user_agent, headless)
            self.browser = webdriver.Chrome(options=chrome_options)
            print("[浏览器管理器] ✅ Selenium浏览器初始化成功")
            return self.browser
        except Exception as e:
            print(f"[浏览器管理器] ❌ Selenium浏览器初始化失败: {str(e)}")
            raise
    
    def _get_drission_page_options(self, user_agent: Optional[str] = None, headless: bool = False) -> Any:
        """获取DrissionPage浏览器配置 -QW"""
        from DrissionPage import ChromiumOptions
        
        co = ChromiumOptions()
        
        # 基础配置 -QW
        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--disable-extensions-file-access-check")
        
        # 系统特定配置 -QW
        if self.system == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")
            co.set_argument("--disable-dev-shm-usage")
        elif self.system == "linux":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-dev-shm-usage")
        
        # 代理配置 -QW
        proxy = self.config.get('proxy') or os.getenv("BROWSER_PROXY")
        if proxy:
            co.set_proxy(proxy)
            print(f"[浏览器管理器] 设置代理: {proxy}")
        
        # 自动端口 -QW
        co.auto_port()
        
        # User-Agent配置 -QW
        if user_agent:
            co.set_user_agent(user_agent)
            print(f"[浏览器管理器] 设置User-Agent: {user_agent[:50]}...")
        
        # 无头模式 -QW
        if headless:
            co.headless(True)
            print("[浏览器管理器] 启用无头模式")
        else:
            co.headless(False)
        
        # 扩展配置 -QW
        try:
            extension_path = self._get_extension_path()
            if extension_path:
                co.add_extension(extension_path)
                print(f"[浏览器管理器] 加载扩展: {extension_path}")
        except Exception as e:
            print(f"[浏览器管理器] ⚠️ 扩展加载失败: {str(e)}")
        
        return co
    
    def _get_selenium_options(self, user_agent: Optional[str] = None, headless: bool = False) -> Any:
        """获取Selenium浏览器配置 -QW"""
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        
        # 基础配置 -QW
        chrome_options.add_argument("--hide-crash-restore-bubble")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions-file-access-check")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 系统特定配置 -QW
        if self.system == "darwin":
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
        elif self.system == "linux":
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        
        # 代理配置 -QW
        proxy = self.config.get('proxy') or os.getenv("BROWSER_PROXY")
        if proxy:
            chrome_options.add_argument(f"--proxy-server={proxy}")
            print(f"[浏览器管理器] 设置代理: {proxy}")
        
        # User-Agent配置 -QW
        if user_agent:
            chrome_options.add_argument(f"--user-agent={user_agent}")
            print(f"[浏览器管理器] 设置User-Agent: {user_agent[:50]}...")
        
        # 无头模式 -QW
        if headless:
            chrome_options.add_argument("--headless")
            print("[浏览器管理器] 启用无头模式")
        
        # 扩展配置 -QW
        try:
            extension_path = self._get_extension_path()
            if extension_path:
                chrome_options.add_argument(f"--load-extension={extension_path}")
                print(f"[浏览器管理器] 加载扩展: {extension_path}")
        except Exception as e:
            print(f"[浏览器管理器] ⚠️ 扩展加载失败: {str(e)}")
        
        return chrome_options
    
    def _get_extension_path(self) -> Optional[str]:
        """获取扩展路径 -QW"""
        try:
            # 可能的扩展路径 -QW
            possible_paths = [
                # 当前目录下的扩展 -QW
                os.path.join(os.getcwd(), "turnstilePatch"),
                os.path.join(os.getcwd(), "AugmentPage", "turnstilePatch"),
                
                # 打包后的路径 -QW
                os.path.join(getattr(sys, "_MEIPASS", ""), "turnstilePatch"),
                os.path.join(getattr(sys, "_MEIPASS", ""), "AugmentPage", "turnstilePatch"),
                
                # 相对于当前文件的路径 -QW
                os.path.join(os.path.dirname(__file__), "turnstilePatch"),
                os.path.join(os.path.dirname(__file__), "..", "turnstilePatch"),
            ]
            
            # 检查路径是否存在 -QW
            for path in possible_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    print(f"[浏览器管理器] 找到扩展路径: {path}")
                    return path
            
            # 如果都不存在，尝试创建一个简单的扩展目录 -QW
            extension_dir = os.path.join(os.path.dirname(__file__), "turnstilePatch")
            if not os.path.exists(extension_dir):
                print(f"[浏览器管理器] ⚠️ 未找到扩展目录，跳过扩展加载")
                return None
            
            return extension_dir
            
        except Exception as e:
            print(f"[浏览器管理器] ⚠️ 获取扩展路径失败: {str(e)}")
            return None
    
    def get_user_agent(self) -> Optional[str]:
        """获取浏览器User-Agent -QW"""
        try:
            if not self.browser:
                # 临时创建浏览器获取User-Agent -QW
                temp_browser = self.init_browser(headless=True)
                
                if self._is_drission_page_available() and hasattr(temp_browser, 'latest_tab'):
                    user_agent = temp_browser.latest_tab.run_js("return navigator.userAgent")
                elif self._is_selenium_available():
                    user_agent = temp_browser.execute_script("return navigator.userAgent")
                else:
                    user_agent = None
                
                self.quit()
                return user_agent
            else:
                # 使用现有浏览器获取User-Agent -QW
                if hasattr(self.browser, 'latest_tab'):
                    return self.browser.latest_tab.run_js("return navigator.userAgent")
                elif hasattr(self.browser, 'execute_script'):
                    return self.browser.execute_script("return navigator.userAgent")
                else:
                    return None
                    
        except Exception as e:
            print(f"[浏览器管理器] ⚠️ 获取User-Agent失败: {str(e)}")
            return None
    
    def quit(self):
        """关闭浏览器 -QW"""
        if self.browser:
            try:
                self.browser.quit()
                print("[浏览器管理器] ✅ 浏览器已关闭")
            except Exception as e:
                print(f"[浏览器管理器] ⚠️ 关闭浏览器时出错: {str(e)}")
            finally:
                self.browser = None
    
    def __del__(self):
        """析构函数，自动关闭浏览器 -QW"""
        self.quit()


def create_browser_manager(config: Optional[Dict[str, Any]] = None) -> BrowserManager:
    """创建浏览器管理器的便捷函数 -QW"""
    return BrowserManager(config)


def get_default_user_agent() -> str:
    """获取默认User-Agent -QW"""
    system = platform.system().lower()
    
    if system == "darwin":
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    elif system == "windows":
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    else:
        return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def test_browser_manager():
    """测试浏览器管理器 -QW"""
    print("=== 浏览器管理器测试 ===")
    
    # 测试配置 -QW
    test_config = {
        'proxy': None,  # 'http://127.0.0.1:8080'
    }
    
    manager = BrowserManager(test_config)
    
    print(f"系统类型: {manager.system}")
    print(f"DrissionPage可用: {manager._is_drission_page_available()}")
    print(f"Selenium可用: {manager._is_selenium_available()}")
    print(f"默认User-Agent: {get_default_user_agent()}")
    
    # 测试扩展路径 -QW
    extension_path = manager._get_extension_path()
    print(f"扩展路径: {extension_path}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 运行测试 -QW
    test_browser_manager()
    
    # 示例使用 -QW
    print("\n=== 示例使用 ===")
    
    try:
        config = {
            'proxy': None  # 可以设置代理
        }
        
        manager = BrowserManager(config)
        
        # 初始化浏览器 -QW
        browser = manager.init_browser(
            user_agent=get_default_user_agent(),
            headless=False
        )
        
        print("✅ 浏览器初始化成功")
        
        # 获取User-Agent -QW
        user_agent = manager.get_user_agent()
        if user_agent:
            print(f"User-Agent: {user_agent[:50]}...")
        
        # 关闭浏览器 -QW
        manager.quit()
        
    except Exception as e:
        print(f"❌ 示例运行失败: {str(e)}")
        print("请确保安装了DrissionPage或Selenium库")
