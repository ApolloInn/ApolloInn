#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cursor自动登录功能
实现Cursor账号的自动登录流程
支持邮箱密码登录和验证码自动获取
支持跨平台（Windows、macOS、Linux）
-QW
"""

import logging
import random
import time
import platform
import subprocess
import json
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs


class CursorAutoLogin:
    """Cursor自动登录器 -QW"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化自动登录器
        
        Args:
            config: 配置字典，包含邮箱验证码配置等
        """
        self.config = config or {}
        self.system = platform.system().lower()
        
        # 设置日志 -QW
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        print(f"[自动登录] 初始化完成，系统: {self.system}")
    
    def auto_login(self, account: str, password: str, login_url: str) -> Dict[str, Any]:
        """
        自动登录主方法
        
        Args:
            account: 邮箱账号
            password: 密码
            login_url: 登录页面URL
            
        Returns:
            Dict[str, Any]: 登录结果
        """
        result = {
            "success": False,
            "message": "",
            "session_token": None,
            "error": None
        }
        
        try:
            print(f"[自动登录] 开始自动登录流程")
            print(f"[自动登录] 账号: {account}")
            print(f"[自动登录] 登录URL: {login_url}")
            
            # 检查是否支持自动化登录 -QW
            if not self._check_automation_support():
                result["message"] = "当前系统不支持自动化登录，请手动登录"
                result["error"] = "automation_not_supported"
                return result
            
            # 尝试使用浏览器自动化登录 -QW
            if self._is_browser_automation_available():
                print("[自动登录] 使用浏览器自动化登录")
                return self._browser_auto_login(account, password, login_url)
            else:
                print("[自动登录] 浏览器自动化不可用，使用手动辅助登录")
                return self._manual_assisted_login(account, password, login_url)
                
        except Exception as e:
            error_msg = f"自动登录过程中发生错误: {str(e)}"
            print(f"[自动登录] ❌ {error_msg}")
            result["error"] = str(e)
            result["message"] = error_msg
            return result
    
    def _check_automation_support(self) -> bool:
        """检查系统是否支持自动化 -QW"""
        try:
            if self.system == "darwin":
                # macOS: 检查是否有必要的权限 -QW
                return True  # macOS通常支持自动化
            elif self.system == "windows":
                return True  # Windows通常支持自动化
            else:
                return True  # Linux通常支持自动化
        except Exception:
            return False
    
    def _is_browser_automation_available(self) -> bool:
        """检查浏览器自动化是否可用 -QW"""
        try:
            # 检查是否安装了selenium或其他自动化工具 -QW
            try:
                import selenium
                return True
            except ImportError:
                pass
            
            try:
                from DrissionPage import Chromium
                return True
            except ImportError:
                pass
            
            return False
        except Exception:
            return False
    
    def _browser_auto_login(self, account: str, password: str, login_url: str) -> Dict[str, Any]:
        """使用浏览器自动化登录 -QW"""
        result = {
            "success": False,
            "message": "",
            "session_token": None,
            "error": None
        }
        
        try:
            # 尝试使用DrissionPage -QW
            try:
                from DrissionPage import ChromiumOptions, Chromium
                return self._drission_page_login(account, password, login_url)
            except ImportError:
                pass
            
            # 尝试使用Selenium -QW
            try:
                from selenium import webdriver
                return self._selenium_login(account, password, login_url)
            except ImportError:
                pass
            
            result["message"] = "未找到可用的浏览器自动化库"
            result["error"] = "no_automation_library"
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"浏览器自动化登录失败: {str(e)}"
            return result
    
    def _drission_page_login(self, account: str, password: str, login_url: str) -> Dict[str, Any]:
        """使用DrissionPage进行自动化登录 -QW"""
        from DrissionPage import ChromiumOptions, Chromium
        
        result = {
            "success": False,
            "message": "",
            "session_token": None,
            "error": None
        }
        
        browser = None
        try:
            # 配置浏览器选项 -QW
            co = ChromiumOptions()
            co.set_pref("credentials_enable_service", False)
            co.set_argument("--hide-crash-restore-bubble")
            co.auto_port()
            
            # macOS特殊配置 -QW
            if self.system == "darwin":
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-gpu")
            
            # 初始化浏览器 -QW
            browser = Chromium(co)
            tab = browser.latest_tab
            
            print(f"[自动登录] 正在访问登录页面: {login_url}")
            tab.get(login_url)
            time.sleep(3)
            
            # 检查是否为登录页面 -QW
            if tab.ele("@name=email"):
                print("[自动登录] 检测到登录页面，开始登录流程...")
                
                # 输入邮箱 -QW
                tab.actions.click("@name=email").input(account)
                print(f"[自动登录] 已输入邮箱: {account}")
                
                # 点击提交 -QW
                tab.actions.click("@type=submit").click()
                time.sleep(1)
                
                # 输入密码 -QW
                tab.actions.click("@name=password").input(password)
                print(f"[自动登录] 已输入密码")
                
                # 点击登录 -QW
                tab.actions.click("@name=intent").click()
                time.sleep(10)
                
                # 获取验证码 -QW
                code = self._get_verification_code(account)
                if not code:
                    result["message"] = "获取验证码失败"
                    result["error"] = "verification_code_failed"
                    return result
                
                print(f"[自动登录] 成功获取验证码: {code}")
                
                # 输入验证码 -QW
                print("[自动登录] 正在输入验证码...")
                for i, digit in enumerate(code):
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                
                print("[自动登录] 验证码输入完成")
                time.sleep(1)
                
                # 点击确认按钮 -QW
                submit_btn = tab.ele("@class", "relative inline-flex items-center justify-center")
                if submit_btn:
                    submit_btn.click()
                    time.sleep(5)
                
                # 获取session token -QW
                session_token = self._get_cursor_session_token(tab)
                if session_token:
                    result["success"] = True
                    result["session_token"] = session_token
                    result["message"] = "自动登录成功"
                    print("[自动登录] ✅ 自动登录成功")
                else:
                    result["message"] = "获取session token失败"
                    result["error"] = "session_token_failed"
            else:
                result["message"] = "未检测到登录页面"
                result["error"] = "login_page_not_found"
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"DrissionPage登录失败: {str(e)}"
            return result
        finally:
            if browser:
                try:
                    browser.quit()
                except:
                    pass
    
    def _selenium_login(self, account: str, password: str, login_url: str) -> Dict[str, Any]:
        """使用Selenium进行自动化登录 -QW"""
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        result = {
            "success": False,
            "message": "",
            "session_token": None,
            "error": None
        }
        
        driver = None
        try:
            # 配置Chrome选项 -QW
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            
            if self.system == "darwin":
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-gpu")
            
            # 初始化WebDriver -QW
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 10)
            
            print(f"[自动登录] 正在访问登录页面: {login_url}")
            driver.get(login_url)
            
            # 等待并输入邮箱 -QW
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.send_keys(account)
            print(f"[自动登录] 已输入邮箱: {account}")
            
            # 点击提交 -QW
            submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_btn.click()
            time.sleep(1)
            
            # 输入密码 -QW
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(password)
            print("[自动登录] 已输入密码")
            
            # 点击登录 -QW
            login_btn = driver.find_element(By.NAME, "intent")
            login_btn.click()
            time.sleep(10)
            
            # 获取验证码 -QW
            code = self._get_verification_code(account)
            if not code:
                result["message"] = "获取验证码失败"
                result["error"] = "verification_code_failed"
                return result
            
            print(f"[自动登录] 成功获取验证码: {code}")
            
            # 输入验证码 -QW
            for i, digit in enumerate(code):
                code_input = driver.find_element(By.CSS_SELECTOR, f"input[data-index='{i}']")
                code_input.send_keys(digit)
                time.sleep(random.uniform(0.1, 0.3))
            
            print("[自动登录] 验证码输入完成")
            time.sleep(1)
            
            # 点击确认 -QW
            confirm_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            confirm_btn.click()
            time.sleep(5)
            
            # 获取session token -QW
            session_token = self._get_selenium_session_token(driver)
            if session_token:
                result["success"] = True
                result["session_token"] = session_token
                result["message"] = "自动登录成功"
                print("[自动登录] ✅ 自动登录成功")
            else:
                result["message"] = "获取session token失败"
                result["error"] = "session_token_failed"
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"Selenium登录失败: {str(e)}"
            return result
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _manual_assisted_login(self, account: str, password: str, login_url: str) -> Dict[str, Any]:
        """手动辅助登录 -QW"""
        result = {
            "success": False,
            "message": "",
            "session_token": None,
            "error": None
        }

        try:
            print("\n" + "="*60)
            print("🔐 Cursor 手动辅助登录")
            print("="*60)
            print(f"账号: {account}")
            print(f"登录URL: {login_url}")
            print("="*60)

            # 打开浏览器 -QW
            self._open_browser(login_url)

            print("\n请按照以下步骤手动登录:")
            print("1. 在打开的浏览器中输入邮箱和密码")
            print("2. 等待验证码输入页面")
            print("3. 回到此程序获取验证码")

            # 等待用户确认到达验证码页面 -QW
            input("\n按回车键继续（当您看到验证码输入页面时）...")

            # 获取验证码 -QW
            code = self._get_verification_code(account)
            if code:
                print(f"\n✅ 获取到验证码: {code}")
                print("请在浏览器中输入此验证码")

                # 等待用户完成登录 -QW
                input("\n输入验证码后按回车键继续...")

                result["success"] = True
                result["message"] = "手动辅助登录完成"
                print("[自动登录] ✅ 手动辅助登录完成")
            else:
                print("❌ 获取验证码失败，请手动获取")
                manual_code = input("请手动输入6位验证码: ").strip()
                if manual_code and len(manual_code) == 6:
                    print(f"✅ 手动输入验证码: {manual_code}")
                    result["success"] = True
                    result["message"] = "手动辅助登录完成（手动输入验证码）"
                else:
                    result["message"] = "验证码输入无效"
                    result["error"] = "invalid_verification_code"

            return result

        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"手动辅助登录失败: {str(e)}"
            return result

    def _open_browser(self, url: str):
        """打开系统默认浏览器 -QW"""
        try:
            if self.system == "darwin":
                subprocess.run(["open", url])
            elif self.system == "windows":
                subprocess.run(["start", url], shell=True)
            else:
                subprocess.run(["xdg-open", url])
            print(f"[自动登录] 已打开浏览器: {url}")
        except Exception as e:
            print(f"[自动登录] ⚠️ 打开浏览器失败: {str(e)}")

    def _get_verification_code(self, email_address: str) -> Optional[str]:
        """获取验证码 -QW"""
        try:
            # 尝试使用邮箱验证码获取器 -QW
            from get_email_code import get_cursor_verification_code

            print(f"[自动登录] 正在获取验证码...")
            code = get_cursor_verification_code(email_address, self.config, timeout=60)

            if code:
                print(f"[自动登录] ✅ 自动获取验证码成功: {code}")
                return code
            else:
                print("[自动登录] ⚠️ 自动获取验证码失败")
                return None

        except ImportError:
            print("[自动登录] ⚠️ 邮箱验证码模块不可用")
            return None
        except Exception as e:
            print(f"[自动登录] ⚠️ 获取验证码异常: {str(e)}")
            return None

    def _get_cursor_session_token(self, tab, max_attempts: int = 3, retry_interval: int = 2) -> Optional[str]:
        """获取Cursor会话token（DrissionPage版本） -QW"""
        print("[自动登录] 开始获取session token...")
        attempts = 0

        while attempts < max_attempts:
            try:
                cookies = tab.cookies()
                for cookie in cookies:
                    if cookie.get("name") == "WorkosCursorSessionToken":
                        token = cookie["value"].split("%3A%3A")[1] if "%3A%3A" in cookie["value"] else cookie["value"]
                        print(f"[自动登录] ✅ 获取到session token")
                        return token

                attempts += 1
                if attempts < max_attempts:
                    print(f"[自动登录] 第 {attempts} 次尝试未获取到token，{retry_interval}秒后重试...")
                    time.sleep(retry_interval)
                else:
                    print(f"[自动登录] ❌ 已达到最大尝试次数({max_attempts})，获取token失败")

            except Exception as e:
                print(f"[自动登录] ⚠️ 获取cookie失败: {str(e)}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(retry_interval)

        return None

    def _get_selenium_session_token(self, driver, max_attempts: int = 3, retry_interval: int = 2) -> Optional[str]:
        """获取Cursor会话token（Selenium版本） -QW"""
        print("[自动登录] 开始获取session token...")
        attempts = 0

        while attempts < max_attempts:
            try:
                cookies = driver.get_cookies()
                for cookie in cookies:
                    if cookie.get("name") == "WorkosCursorSessionToken":
                        token = cookie["value"].split("%3A%3A")[1] if "%3A%3A" in cookie["value"] else cookie["value"]
                        print(f"[自动登录] ✅ 获取到session token")
                        return token

                attempts += 1
                if attempts < max_attempts:
                    print(f"[自动登录] 第 {attempts} 次尝试未获取到token，{retry_interval}秒后重试...")
                    time.sleep(retry_interval)
                else:
                    print(f"[自动登录] ❌ 已达到最大尝试次数({max_attempts})，获取token失败")

            except Exception as e:
                print(f"[自动登录] ⚠️ 获取cookie失败: {str(e)}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(retry_interval)

        return None


def create_auto_login(config: Optional[Dict[str, Any]] = None) -> CursorAutoLogin:
    """创建自动登录器的便捷函数 -QW"""
    return CursorAutoLogin(config)


def quick_auto_login(account: str, password: str, login_url: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    快速自动登录的便捷函数 -QW

    Args:
        account: 邮箱账号
        password: 密码
        login_url: 登录页面URL
        config: 配置字典

    Returns:
        Dict[str, Any]: 登录结果
    """
    auto_login = CursorAutoLogin(config)
    return auto_login.auto_login(account, password, login_url)


def test_auto_login():
    """测试自动登录功能 -QW"""
    print("=== Cursor自动登录测试 ===")

    # 示例配置 -QW
    test_config = {
        'imap': {
            'server': 'imap.gmail.com',
            'port': 993,
            'username': 'your_email@gmail.com',
            'password': 'your_app_password'
        },
        'delete_after_read': False
    }

    auto_login = CursorAutoLogin(test_config)

    print(f"系统类型: {auto_login.system}")
    print(f"自动化支持: {auto_login._check_automation_support()}")
    print(f"浏览器自动化可用: {auto_login._is_browser_automation_available()}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 运行测试 -QW
    test_auto_login()

    # 示例使用 -QW
    print("\n=== 示例使用 ===")

    account = input("请输入邮箱账号: ").strip()
    password = input("请输入密码: ").strip()
    login_url = input("请输入登录页面URL: ").strip()

    if account and password and login_url:
        config = {
            'imap': {
                'server': 'imap.gmail.com',
                'port': 993,
                'username': account,
                'password': 'your_app_password'
            }
        }

        result = quick_auto_login(account, password, login_url, config)

        if result["success"]:
            print(f"✅ 登录成功: {result['message']}")
            if result["session_token"]:
                print(f"Session Token: {result['session_token'][:20]}...")
        else:
            print(f"❌ 登录失败: {result['message']}")
    else:
        print("输入信息不完整")
