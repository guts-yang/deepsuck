import os
import logging
import time
from typing import Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from config.config import config
from src.request_manager import request_manager

# 配置日志
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class LoginManager:
    """登录管理器，处理网站登录验证和会话管理"""
    
    def __init__(self):
        self._site_login_methods = {
            'youtube.com': self._login_google,
            'bilibili.com': self._login_bilibili,
            'soundcloud.com': self._login_soundcloud,
            # 可以添加更多网站的登录方法
        }
    
    def _get_login_method(self, url: str) -> Optional[callable]:
        """根据URL获取对应的登录方法"""
        domain = urlparse(url).netloc.lower()
        for site_domain, method in self._site_login_methods.items():
            if site_domain in domain:
                return method
        return self._login_generic  # 默认登录方法
    
    def login(self, url: str, username: Optional[str] = None, password: Optional[str] = None, 
              use_selenium: bool = False, manual: bool = False) -> bool:
        """执行登录操作
        Args:
            url: 登录的网站URL
            username: 用户名
            password: 密码
            use_selenium: 是否使用Selenium进行登录
            manual: 是否手动登录（用户在浏览器中操作）
        Returns:
            是否登录成功
        """
        logger.info(f"开始登录: {url}")
        login_method = self._get_login_method(url)
        
        try:
            result = login_method(url, username, password, use_selenium, manual)
            if result:
                logger.info(f"登录成功: {url}")
            else:
                logger.warning(f"登录失败: {url}")
            return result
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    def _create_selenium_driver(self, headless: bool = False) -> webdriver.Chrome:
        """创建Selenium WebDriver实例"""
        chrome_options = ChromeOptions()
        
        # 配置Chrome选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'user-agent={request_manager._random_user_agent()}')
        
        # 是否无头模式
        if headless:
            chrome_options.add_argument('--headless')
        
        # 创建WebDriver
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        return driver
    
    def _extract_cookies_from_driver(self, driver: webdriver.Chrome) -> Dict[str, str]:
        """从Selenium WebDriver中提取cookies"""
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies
    
    def _save_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        """保存cookies到文件"""
        # 创建cookies目录（如果不存在）
        os.makedirs(config.COOKIES_DIR, exist_ok=True)
        
        # 保存cookies文件
        cookie_file = os.path.join(config.COOKIES_DIR, f"{domain.replace('.', '_')}.json")
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Cookies已保存到: {cookie_file}")
    
    def _load_cookies(self, domain: str) -> Optional[Dict[str, str]]:
        """从文件加载cookies"""
        cookie_file = os.path.join(config.COOKIES_DIR, f"{domain.replace('.', '_')}.json")
        
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                logger.info(f"从{cookie_file}加载cookies成功")
                return cookies
            except Exception as e:
                logger.error(f"加载cookies失败: {e}")
        
        return None
    
    # 网站特定登录方法
    def _login_google(self, url: str, username: Optional[str] = None, password: Optional[str] = None, 
                      use_selenium: bool = True, manual: bool = False) -> bool:
        """Google/YouTube登录"""
        domain = 'youtube.com'
        
        # 尝试加载已保存的cookies
        saved_cookies = self._load_cookies(domain)
        if saved_cookies:
            request_manager.set_cookies(saved_cookies)
            # 验证cookies是否有效（可以添加验证逻辑）
            return True
        
        if not use_selenium:
            logger.warning("Google登录需要使用Selenium")
            return False
        
        try:
            # 创建WebDriver
            driver = self._create_selenium_driver(headless=False)
            
            # 导航到登录页面
            driver.get('https://accounts.google.com/ServiceLogin')
            
            if manual:
                logger.info("请在打开的浏览器中手动登录")
                logger.info("登录完成后，请按Enter键继续...")
                input()  # 等待用户手动登录
            elif username and password:
                # 自动填充用户名和密码（简化版，实际可能需要处理验证码等）
                time.sleep(2)
                # 输入用户名
                email_input = driver.find_element('id', 'identifierId')
                email_input.send_keys(username)
                driver.find_element('id', 'identifierNext').click()
                time.sleep(2)
                # 输入密码
                password_input = driver.find_element('name', 'Passwd')
                password_input.send_keys(password)
                driver.find_element('id', 'passwordNext').click()
                time.sleep(5)  # 等待登录完成
            else:
                logger.error("需要提供用户名和密码，或者启用手动登录")
                driver.quit()
                return False
            
            # 提取cookies
            cookies = self._extract_cookies_from_driver(driver)
            
            # 保存cookies
            self._save_cookies(domain, cookies)
            
            # 设置到请求管理器
            request_manager.set_cookies(cookies)
            
            # 关闭浏览器
            driver.quit()
            
            return True
        except Exception as e:
            logger.error(f"Google登录失败: {e}")
            return False
    
    def _login_bilibili(self, url: str, username: Optional[str] = None, password: Optional[str] = None, 
                        use_selenium: bool = True, manual: bool = False) -> bool:
        """Bilibili登录"""
        domain = 'bilibili.com'
        
        # 尝试加载已保存的cookies
        saved_cookies = self._load_cookies(domain)
        if saved_cookies:
            request_manager.set_cookies(saved_cookies)
            # 验证cookies是否有效（可以添加验证逻辑）
            return True
        
        if not use_selenium:
            logger.warning("Bilibili登录需要使用Selenium")
            return False
        
        try:
            # 创建WebDriver
            driver = self._create_selenium_driver(headless=False)
            
            # 导航到登录页面
            driver.get('https://passport.bilibili.com/login')
            
            if manual:
                logger.info("请在打开的浏览器中手动登录")
                logger.info("登录完成后，请按Enter键继续...")
                input()  # 等待用户手动登录
            elif username and password:
                # 实际应用中需要处理B站的登录方式，这里仅作为示例
                logger.warning("Bilibili自动登录功能尚未实现，请使用手动登录")
                driver.quit()
                return False
            else:
                logger.error("需要提供用户名和密码，或者启用手动登录")
                driver.quit()
                return False
            
            # 提取cookies
            cookies = self._extract_cookies_from_driver(driver)
            
            # 保存cookies
            self._save_cookies(domain, cookies)
            
            # 设置到请求管理器
            request_manager.set_cookies(cookies)
            
            # 关闭浏览器
            driver.quit()
            
            return True
        except Exception as e:
            logger.error(f"Bilibili登录失败: {e}")
            return False
    
    def _login_soundcloud(self, url: str, username: Optional[str] = None, password: Optional[str] = None, 
                          use_selenium: bool = True, manual: bool = False) -> bool:
        """SoundCloud登录"""
        domain = 'soundcloud.com'
        
        # 尝试加载已保存的cookies
        saved_cookies = self._load_cookies(domain)
        if saved_cookies:
            request_manager.set_cookies(saved_cookies)
            # 验证cookies是否有效（可以添加验证逻辑）
            return True
        
        if not use_selenium:
            logger.warning("SoundCloud登录需要使用Selenium")
            return False
        
        try:
            # 创建WebDriver
            driver = self._create_selenium_driver(headless=False)
            
            # 导航到登录页面
            driver.get('https://soundcloud.com/login')
            
            if manual:
                logger.info("请在打开的浏览器中手动登录")
                logger.info("登录完成后，请按Enter键继续...")
                input()  # 等待用户手动登录
            elif username and password:
                # 自动填充用户名和密码
                time.sleep(2)
                # 输入用户名
                username_input = driver.find_element('name', 'username')
                username_input.send_keys(username)
                # 输入密码
                password_input = driver.find_element('name', 'password')
                password_input.send_keys(password)
                # 点击登录按钮
                login_button = driver.find_element('class name', 'signinInitial-step0__submitButton')
                login_button.click()
                time.sleep(5)  # 等待登录完成
            else:
                logger.error("需要提供用户名和密码，或者启用手动登录")
                driver.quit()
                return False
            
            # 提取cookies
            cookies = self._extract_cookies_from_driver(driver)
            
            # 保存cookies
            self._save_cookies(domain, cookies)
            
            # 设置到请求管理器
            request_manager.set_cookies(cookies)
            
            # 关闭浏览器
            driver.quit()
            
            return True
        except Exception as e:
            logger.error(f"SoundCloud登录失败: {e}")
            return False
    
    def _login_generic(self, url: str, username: Optional[str] = None, password: Optional[str] = None, 
                       use_selenium: bool = True, manual: bool = False) -> bool:
        """通用登录方法"""
        domain = urlparse(url).netloc
        
        # 尝试加载已保存的cookies
        saved_cookies = self._load_cookies(domain)
        if saved_cookies:
            request_manager.set_cookies(saved_cookies)
            # 验证cookies是否有效（可以添加验证逻辑）
            return True
        
        if not use_selenium:
            logger.warning("通用登录需要使用Selenium")
            return False
        
        try:
            # 创建WebDriver
            driver = self._create_selenium_driver(headless=False)
            
            # 导航到目标URL
            driver.get(url)
            
            if manual:
                logger.info(f"请在打开的浏览器中手动登录 {domain}")
                logger.info("登录完成后，请按Enter键继续...")
                input()  # 等待用户手动登录
            else:
                logger.warning("通用自动登录功能尚未实现，请使用手动登录")
                driver.quit()
                return False
            
            # 提取cookies
            cookies = self._extract_cookies_from_driver(driver)
            
            # 保存cookies
            self._save_cookies(domain, cookies)
            
            # 设置到请求管理器
            request_manager.set_cookies(cookies)
            
            # 关闭浏览器
            driver.quit()
            
            return True
        except Exception as e:
            logger.error(f"通用登录失败: {e}")
            return False

# 导出全局实例
login_manager = LoginManager()