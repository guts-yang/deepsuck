#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSuck 媒体爬虫 - 主入口文件

这是一个合规的网络爬虫项目，支持爬取多个指定网站的视频及音乐数据，并提供直接下载功能。
项目严格遵循robots协议及相关法律法规，确保数据爬取行为合法合规。
"""

import os
import sys
import argparse
import logging
import json
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入项目模块
from config.config import config
from src.media_crawler import media_crawler
from src.login_manager import login_manager
from src.request_manager import request_manager
from src.robots_checker import robots_checker

# 配置日志
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='DeepSuck 媒体爬虫')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # UI模式命令
    ui_parser = subparsers.add_parser('ui', help='启动图形用户界面')
    
    # 爬取命令
    crawl_parser = subparsers.add_parser('crawl', help='爬取媒体信息')
    crawl_parser.add_argument('url', help='目标URL')
    crawl_parser.add_argument('--login', action='store_true', help='是否需要登录')
    crawl_parser.add_argument('--manual-login', action='store_true', help='是否手动登录')
    crawl_parser.add_argument('--username', help='用户名')
    crawl_parser.add_argument('--password', help='密码')
    crawl_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # 下载命令
    download_parser = subparsers.add_parser('download', help='下载媒体文件')
    download_parser.add_argument('url', help='目标URL')
    download_parser.add_argument('--login', action='store_true', help='是否需要登录')
    download_parser.add_argument('--manual-login', action='store_true', help='是否手动登录')
    download_parser.add_argument('--username', help='用户名')
    download_parser.add_argument('--password', help='密码')
    download_parser.add_argument('--output-dir', '-d', default=str(config.VIDEO_DIR), help='下载目录')
    download_parser.add_argument('--type', choices=['video', 'audio', 'both'], default='both', help='下载类型')
    
    # 登录命令
    login_parser = subparsers.add_parser('login', help='登录网站')
    login_parser.add_argument('url', help='目标网站URL')
    login_parser.add_argument('--manual', action='store_true', help='是否手动登录')
    login_parser.add_argument('--username', help='用户名')
    login_parser.add_argument('--password', help='密码')
    
    # 检查robots.txt命令
    robots_parser = subparsers.add_parser('robots', help='检查网站robots.txt规则')
    robots_parser.add_argument('url', help='目标URL')
    
    return parser.parse_args()

def handle_ui():
    """处理UI模式命令"""
    try:
        from src.ui import main as ui_main
        ui_main()
    except ImportError as e:
        logger.error(f"无法导入UI模块: {e}")
        logger.error("请确保已安装PyQt5: pip install PyQt5")
        sys.exit(1)
    except Exception as e:
        logger.error(f"UI启动失败: {e}")
        sys.exit(1)

def handle_crawl(args):
    """处理爬取命令"""
    try:
        # 如果需要登录
        if args.login:
            login_success = login_manager.login(
                args.url,
                args.username,
                args.password,
                manual=args.manual_login
            )
            if not login_success:
                logger.error("登录失败，无法继续爬取")
                sys.exit(1)
        
        # 执行爬取
        media_info = media_crawler.crawl(args.url)
        
        # 输出结果
        print("\n爬取结果:")
        print(json.dumps(media_info, ensure_ascii=False, indent=2))
        
        # 如果指定了输出文件，保存结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(media_info, f, ensure_ascii=False, indent=2)
            logger.info(f"爬取结果已保存到: {args.output}")
            
    except Exception as e:
        logger.error(f"爬取失败: {e}")
        sys.exit(1)

def handle_download(args):
    """处理下载命令"""
    try:
        # 如果需要登录
        if args.login:
            login_success = login_manager.login(
                args.url,
                args.username,
                args.password,
                manual=args.manual_login
            )
            if not login_success:
                logger.error("登录失败，无法继续下载")
                sys.exit(1)
        
        # 首先爬取媒体信息
        logger.info(f"正在获取媒体信息: {args.url}")
        media_info = media_crawler.crawl(args.url)
        
        # 执行下载
        logger.info(f"正在下载媒体到: {args.output_dir}")
        result = media_crawler.download(media_info, args.output_dir, args.type)
        
        # 输出结果
        print("\n下载结果:")
        for media_type, path in result.items():
            print(f"{media_type}: {path}")
            
    except Exception as e:
        logger.error(f"下载失败: {e}")
        sys.exit(1)

def handle_login(args):
    """处理登录命令"""
    try:
        success = login_manager.login(
            args.url,
            args.username,
            args.password,
            manual=args.manual
        )
        
        if success:
            logger.info("登录成功")
        else:
            logger.error("登录失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"登录失败: {e}")
        sys.exit(1)

def handle_robots(args):
    """处理robots.txt检查命令"""
    try:
        can_fetch = robots_checker.can_fetch(args.url)
        crawl_delay = robots_checker.get_crawl_delay(args.url)
        
        print(f"\nrobots.txt 检查结果:")
        print(f"URL: {args.url}")
        print(f"是否允许爬取: {'是' if can_fetch else '否'}")
        print(f"建议爬取延迟: {crawl_delay}秒" if crawl_delay else "无建议爬取延迟")
        
    except Exception as e:
        logger.error(f"robots.txt检查失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 显示欢迎信息
    print("="*60)
    print("  DeepSuck 媒体爬虫  ")
    print("  合规爬取，尊重版权  ")
    print("="*60)
    
    # 根据命令执行不同的操作
    if args.command == 'ui':
        handle_ui()
    elif args.command == 'crawl':
        handle_crawl(args)
    elif args.command == 'download':
        handle_download(args)
    elif args.command == 'login':
        handle_login(args)
    elif args.command == 'robots':
        handle_robots(args)
    else:
        # 如果没有指定命令，显示帮助信息
        print("请指定一个命令。使用 -h 或 --help 查看帮助信息。")
        print("\n示例:")
        print("  python main.py ui                # 启动图形用户界面")
        print("  python main.py crawl <URL>       # 爬取媒体信息")
        print("  python main.py download <URL>    # 下载媒体文件")
        print("  python main.py login <URL>       # 登录网站")
        print("  python main.py robots <URL>      # 检查robots.txt规则")
        
if __name__ == "__main__":
    main()