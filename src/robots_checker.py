import requests
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Optional
import logging
from config.config import config

# 配置日志
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class RobotsChecker:
    """robots.txt规则检查器，用于确保爬虫行为合规"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._user_agent = "DeepSuckBot/1.0 (complying with robots.txt)"
        
    def get_base_url(self, url: str) -> str:
        """提取URL的基础部分"""
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    def fetch_robots_txt(self, base_url: str) -> Optional[str]:
        """获取网站的robots.txt内容"""
        if base_url in self._cache and 'robots_txt' in self._cache[base_url]:
            return self._cache[base_url]['robots_txt']
        
        robots_url = urljoin(base_url, '/robots.txt')
        try:
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                robots_txt = response.text
                # 缓存robots.txt内容
                if base_url not in self._cache:
                    self._cache[base_url] = {}
                self._cache[base_url]['robots_txt'] = robots_txt
                return robots_txt
            else:
                logger.info(f"未找到robots.txt文件: {robots_url}")
                # 如果没有robots.txt，假设允许爬取
                return None
        except Exception as e:
            logger.error(f"获取robots.txt失败: {e}")
            # 出错时也假设允许爬取
            return None
    
    def can_fetch(self, url: str) -> bool:
        """检查是否可以爬取指定URL"""
        if not config.ROBOTS_TXT_ENABLED:
            logger.debug("robots.txt检查已禁用")
            return True
        
        base_url = self.get_base_url(url)
        robots_txt = self.fetch_robots_txt(base_url)
        
        # 如果没有robots.txt或检查被禁用，默认允许
        if not robots_txt:
            return True
        
        # 解析robots.txt并检查是否允许爬取
        # 这里实现一个简化版的robots.txt解析器
        # 完整实现应当处理User-agent和Disallow规则的优先级
        allowed = True
        user_agent_section = False
        
        for line in robots_txt.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                user_agent = line.split(':', 1)[1].strip().lower()
                # 检查是否匹配我们的User-agent或通配符
                if user_agent == '*' or self._user_agent.lower().startswith(user_agent):
                    user_agent_section = True
                else:
                    user_agent_section = False
            elif line.lower().startswith('disallow:') and user_agent_section:
                disallow_path = line.split(':', 1)[1].strip()
                # 如果Disallow路径为空，表示允许所有
                if not disallow_path:
                    continue
                # 检查URL是否匹配Disallow路径
                if url.startswith(urljoin(base_url, disallow_path)):
                    allowed = False
                    break
            elif line.lower().startswith('allow:') and user_agent_section:
                allow_path = line.split(':', 1)[1].strip()
                # 检查URL是否匹配Allow路径（覆盖Disallow）
                if url.startswith(urljoin(base_url, allow_path)):
                    allowed = True
                    break
        
        logger.debug(f"URL {url} 爬取权限: {allowed}")
        return allowed
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """获取网站推荐的爬取延迟"""
        base_url = self.get_base_url(url)
        robots_txt = self.fetch_robots_txt(base_url)
        
        if not robots_txt:
            return None
        
        user_agent_section = False
        
        for line in robots_txt.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                user_agent = line.split(':', 1)[1].strip().lower()
                if user_agent == '*' or self._user_agent.lower().startswith(user_agent):
                    user_agent_section = True
                else:
                    user_agent_section = False
            elif line.lower().startswith('crawl-delay:') and user_agent_section:
                try:
                    delay = float(line.split(':', 1)[1].strip())
                    return delay
                except ValueError:
                    pass
        
        return None
    
    def clear_cache(self, base_url: Optional[str] = None) -> None:
        """清除缓存"""
        if base_url:
            if base_url in self._cache:
                del self._cache[base_url]
        else:
            self._cache.clear()

# 导出全局实例
robots_checker = RobotsChecker()