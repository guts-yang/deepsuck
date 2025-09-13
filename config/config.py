import os
import pathlib
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.absolute()

# 爬虫配置
class Config:
    # 数据存储目录
    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    # 视频下载地址设置为D:\coding\deepsuck\data\videos (使用原始字符串避免转义问题)
    VIDEO_DIR = r'D:\coding\deepsuck\data\videos'
    AUDIO_DIR = os.path.join(DATA_DIR, 'audios')
    
    # 确保存储目录存在
    @classmethod
    def ensure_dirs(cls):
        for dir_path in [cls.DATA_DIR, cls.VIDEO_DIR, cls.AUDIO_DIR]:
            os.makedirs(dir_path, exist_ok=True)
    
    # 请求头配置
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    ]
    
    # 反爬机制配置
    REQUEST_DELAY = 2  # 请求间隔(秒)
    MAX_RETRY = 3      # 最大重试次数
    RANDOM_DELAY_RANGE = (1, 3)  # 随机延迟范围(秒)
    
    # 下载配置
    DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 下载块大小(1MB)
    MAX_CONCURRENT_DOWNLOADS = 3       # 最大并发下载数
    
    # 登录配置
    COOKIES_DIR = os.path.join(PROJECT_ROOT, 'config', 'cookies')
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = os.path.join(PROJECT_ROOT, 'logs', 'spider.log')
    
    # 合规配置
    ROBOTS_TXT_ENABLED = True  # 遵循robots.txt
    MAX_PAGES_PER_DOMAIN = 100  # 每个域名最大爬取页数
    
    # API密钥配置(从环境变量加载)
    API_KEYS = {
        'youtube': os.getenv('YOUTUBE_API_KEY', ''),
        'spotify': os.getenv('SPOTIFY_API_KEY', ''),
    }

# 导出配置实例
config = Config()

# 确保目录存在
config.ensure_dirs()
os.makedirs(config.COOKIES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)