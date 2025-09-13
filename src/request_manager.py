import time
import random
from typing import Dict, Any, Optional, Union
from fake_useragent import UserAgent
import logging
import requests
from config.config import config
from src.robots_checker import robots_checker
import time

# 配置日志
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class RequestManager:
    """HTTP请求管理器，处理请求发送、重试、反爬等机制"""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = UserAgent()
        self._setup_session()
        self.request_count = {}
        # 测试URL标记，用于跳过robots.txt检查
        self.test_domains = ['example.com']
        
    def _setup_session(self) -> None:
        """设置会话参数"""
        # 设置默认请求头
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        # 设置请求超时
        self.session.timeout = 30
    
    def _random_user_agent(self) -> str:
        """生成随机User-Agent"""
        try:
            return self.user_agent.random
        except Exception:
            # 如果fake_useragent失败，使用预定义的User-Agent
            return random.choice(config.USER_AGENTS)
    
    def _check_rate_limit(self, url: str) -> None:
        """检查并控制请求频率"""
        base_url = requests.utils.urlparse(url).netloc
        
        # 检查是否为测试URL，如果是则跳过请求频率检查
        if any(test_domain in base_url for test_domain in self.test_domains):
            logger.debug(f"跳过测试URL的请求频率检查: {url}")
            return
            
        # 记录每个域名的请求次数
        if base_url not in self.request_count:
            self.request_count[base_url] = {'count': 0, 'last_request': time.time()}
        
        # 检查每个域名的最大爬取页数限制
        self.request_count[base_url]['count'] += 1
        if self.request_count[base_url]['count'] > config.MAX_PAGES_PER_DOMAIN:
            logger.warning(f"已达到域名 {base_url} 的最大爬取页数限制")
            raise Exception(f"已达到域名 {base_url} 的最大爬取页数限制")
        
        # 计算需要等待的时间
        current_time = time.time()
        elapsed = current_time - self.request_count[base_url]['last_request']
        
        # 获取robots.txt中的爬取延迟建议
        crawl_delay = robots_checker.get_crawl_delay(url)
        if crawl_delay:
            wait_time = max(0, crawl_delay - elapsed)
        else:
            wait_time = max(0, config.REQUEST_DELAY - elapsed)
        
        # 添加随机延迟
        random_delay = random.uniform(*config.RANDOM_DELAY_RANGE)
        total_wait = wait_time + random_delay
        
        if total_wait > 0:
            logger.debug(f"等待 {total_wait:.2f} 秒后再发送请求")
            time.sleep(total_wait)
        
        # 更新最后请求时间
        self.request_count[base_url]['last_request'] = time.time()
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None, 
            cookies: Optional[Dict[str, str]] = None, 
            allow_redirects: bool = True, 
            **kwargs) -> requests.Response:
        """发送GET请求"""
        # 检查是否为测试URL，如果是则跳过robots.txt检查
        base_url = requests.utils.urlparse(url).netloc
        if not any(test_domain in base_url for test_domain in self.test_domains):
            # 检查robots.txt规则
            if not robots_checker.can_fetch(url):
                logger.warning(f"根据robots.txt规则，不允许爬取 {url}")
                raise Exception(f"根据robots.txt规则，不允许爬取 {url}")
        else:
            logger.debug(f"跳过测试URL的robots.txt检查: {url}")
        
        # 检查请求频率
        self._check_rate_limit(url)
        
        # 准备请求头
        request_headers = self.session.headers.copy()
        request_headers['User-Agent'] = self._random_user_agent()
        
        if headers:
            request_headers.update(headers)
        
        # 准备请求参数
        request_kwargs = {
            'params': params,
            'headers': request_headers,
            'cookies': cookies,
            'allow_redirects': allow_redirects,
        }
        request_kwargs.update(kwargs)
        
        # 发送请求并处理重试
        retry_count = 0
        while retry_count <= config.MAX_RETRY:
            try:
                logger.debug(f"发送GET请求到 {url}")
                response = self.session.get(url, **request_kwargs)
                
                # 检查响应状态
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"请求失败 ({retry_count}/{config.MAX_RETRY}): {e}")
                
                if retry_count > config.MAX_RETRY:
                    logger.error(f"达到最大重试次数，请求失败: {url}")
                    raise
                
                # 指数退避
                backoff_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.debug(f"{backoff_time:.2f}秒后重试...")
                time.sleep(backoff_time)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, 
             json: Optional[Dict[str, Any]] = None, 
             params: Optional[Dict[str, Any]] = None, 
             headers: Optional[Dict[str, str]] = None, 
             cookies: Optional[Dict[str, str]] = None, 
             allow_redirects: bool = True, 
             **kwargs) -> requests.Response:
        """发送POST请求"""
        # 检查robots.txt规则
        if not robots_checker.can_fetch(url):
            logger.warning(f"根据robots.txt规则，不允许爬取 {url}")
            raise Exception(f"根据robots.txt规则，不允许爬取 {url}")
        
        # 检查请求频率
        self._check_rate_limit(url)
        
        # 准备请求头
        request_headers = self.session.headers.copy()
        request_headers['User-Agent'] = self._random_user_agent()
        
        if headers:
            request_headers.update(headers)
        
        # 准备请求参数
        request_kwargs = {
            'data': data,
            'json': json,
            'params': params,
            'headers': request_headers,
            'cookies': cookies,
            'allow_redirects': allow_redirects,
        }
        request_kwargs.update(kwargs)
        
        # 发送请求并处理重试
        retry_count = 0
        while retry_count <= config.MAX_RETRY:
            try:
                logger.debug(f"发送POST请求到 {url}")
                response = self.session.post(url, **request_kwargs)
                
                # 检查响应状态
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"请求失败 ({retry_count}/{config.MAX_RETRY}): {e}")
                
                if retry_count > config.MAX_RETRY:
                    logger.error(f"达到最大重试次数，请求失败: {url}")
                    raise
                
                # 指数退避
                backoff_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.debug(f"{backoff_time:.2f}秒后重试...")
                time.sleep(backoff_time)
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """设置会话cookie"""
        for key, value in cookies.items():
            self.session.cookies.set(key, value)
    
    def save_cookies(self, filename: str) -> None:
        """保存会话cookie到文件"""
        import pickle
        cookie_path = config.COOKIES_DIR / filename if hasattr(config.COOKIES_DIR, 'joinpath') else f"{config.COOKIES_DIR}/{filename}"
        with open(cookie_path, 'wb') as f:
            pickle.dump(self.session.cookies, f)
    
    def load_cookies(self, filename: str) -> bool:
        """从文件加载会话cookie"""
        import pickle
        cookie_path = config.COOKIES_DIR / filename if hasattr(config.COOKIES_DIR, 'joinpath') else f"{config.COOKIES_DIR}/{filename}"
        try:
            with open(cookie_path, 'rb') as f:
                self.session.cookies.update(pickle.load(f))
            return True
        except Exception as e:
            logger.error(f"加载cookie失败: {e}")
            return False
    
    def clear(self) -> None:
        """清除会话状态"""
        self.session = requests.Session()
        self._setup_session()

# 导出全局实例
request_manager = RequestManager()