import os
import re
import json
import logging
import os
import subprocess
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse, unquote
from config.config import config
from src.request_manager import request_manager
from bs4 import BeautifulSoup
import validators
import requests
import time
import random

# 配置日志
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class MediaCrawler:
    """媒体爬虫核心模块，用于爬取和下载视频、音乐内容"""
    
    def __init__(self):
        # 支持的网站处理器
        self._site_handlers = {
            'youtube.com': self._handle_youtube,
            'bilibili.com': self._handle_bilibili,
            'soundcloud.com': self._handle_soundcloud,
            # 可以添加更多网站的处理器
        }
    
    def _get_site_handler(self, url: str) -> Optional[callable]:
        """根据URL获取对应的网站处理器"""
        domain = urlparse(url).netloc.lower()
        for site_domain, handler in self._site_handlers.items():
            if site_domain in domain:
                return handler
        return self._handle_generic  # 默认处理器
    
    def crawl(self, url: str) -> Dict[str, Any]:
        """爬取指定URL的媒体信息"""
        if not validators.url(url):
            raise ValueError(f"无效的URL: {url}")
        
        logger.info(f"开始爬取: {url}")
        handler = self._get_site_handler(url)
        
        try:
            result = handler(url)
            logger.info(f"爬取完成: {url}")
            return result
        except Exception as e:
            logger.error(f"爬取失败: {e}")
            raise
    
    def download(self, media_info: Dict[str, Any], download_path: Optional[str] = None, 
                 download_type: str = 'both') -> Dict[str, str]:
        """下载媒体文件
        Args:
            media_info: 媒体信息字典
            download_path: 下载路径，默认为配置中的对应目录
            download_type: 下载类型，'video'、'audio'或'both'
        Returns:
            包含下载文件路径的字典
        """
        result = {}
        
        # 检查是否有可下载的URL
        has_video_url = 'video_url' in media_info and media_info['video_url']
        has_audio_url = 'audio_url' in media_info and media_info['audio_url']
        
        if not has_video_url and not has_audio_url:
            logger.error("没有找到可下载的媒体URL")
            raise ValueError("无法下载：没有找到可下载的媒体URL")
        
        # 确定下载路径
        if not download_path:
            if media_info.get('type') == 'video' or download_type == 'video':
                download_path = config.VIDEO_DIR
            else:
                download_path = config.AUDIO_DIR
        
        # 确保下载路径存在
        os.makedirs(download_path, exist_ok=True)
        
        # 根据来源网站添加特定的请求头
        headers = {}
        source = media_info.get('source', '').lower()
        if 'bilibili' in source or 'bili' in source:
            # B站下载需要正确的Referer
            headers = {
                'Referer': media_info.get('original_url', 'https://www.bilibili.com'),
                'Origin': 'https://www.bilibili.com'
            }
        elif 'youtube' in source:
            # YouTube下载的请求头
            headers = {
                'Referer': 'https://www.youtube.com/',
            }
        
        # 下载视频
        video_path = None
        if (media_info.get('type') == 'video' or download_type == 'video' or download_type == 'both') and has_video_url:
            # 如果是B站视频，确保original_url存在
            if 'bilibili' in source and not media_info.get('original_url'):
                # 使用media_info中的原始URL或默认URL
                media_info['original_url'] = media_info.get('url', 'https://www.bilibili.com')
            video_path = self._download_file(media_info['video_url'], download_path, media_info.get('title', 'video'), 'mp4', headers)
            result['video'] = video_path
        
        # 下载音频
        audio_path = None
        if (media_info.get('type') == 'audio' or download_type == 'audio' or download_type == 'both') and has_audio_url:
            audio_path = self._download_file(media_info['audio_url'], download_path, media_info.get('title', 'audio'), 'mp3', headers)
            result['audio'] = audio_path
        
        # 如果同时下载了视频和音频，且下载类型不是分别下载，则合并它们
        if video_path and audio_path and download_type == 'both':
            try:
                merged_path = self._merge_video_audio(video_path, audio_path, download_path, media_info.get('title', 'merged_video'))
                result['merged'] = merged_path
                logger.info(f"视频和音频已成功合并: {merged_path}")
            except Exception as e:
                logger.error(f"视频和音频合并失败: {e}")
                # 保留原始的视频和音频文件路径
        
        return result
    
    def _download_file(self, url: str, save_dir: str, filename: str, extension: str, headers: Optional[Dict[str, str]] = None) -> str:
        """下载单个文件"""
        # 清理文件名
        filename = self._sanitize_filename(filename)
        save_path = os.path.join(save_dir, f"{filename}.{extension}")
        
        logger.info(f"开始下载: {url}\n保存到: {save_path}")
        
        try:
            # 发送请求获取文件
            response = request_manager.get(url, stream=True, headers=headers)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # 分块下载文件
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=config.DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 记录下载进度
                        if total_size > 0:
                            progress = downloaded_size / total_size * 100
                            logger.debug(f"下载进度: {progress:.1f}%")
            
            logger.info(f"下载完成: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"下载失败: {e}")
            # 如果下载失败，删除不完整的文件
            if os.path.exists(save_path):
                os.remove(save_path)
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除非法字符
        filename = re.sub(r'[\\/:*?"<>|]', '', filename)
        # 限制文件名长度
        max_length = 100
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename
    
    def _merge_video_audio(self, video_path: str, audio_path: str, save_dir: str, title: str) -> str:
        """使用FFmpeg合并视频和音频文件
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            save_dir: 保存目录
            title: 视频标题
        Returns:
            合并后的文件路径
        """
        # 检查FFmpeg是否可用
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("未找到FFmpeg。请先安装FFmpeg并确保它在系统PATH中。")
            raise RuntimeError("未找到FFmpeg，请先安装它以支持视频和音频合并功能。")
        
        # 清理标题
        title = self._sanitize_filename(title)
        # 构建输出文件路径
        output_path = os.path.join(save_dir, f"{title}_merged.mp4")
        
        # 规范化所有路径，解决Windows系统中路径反斜杠过多的问题
        video_path = os.path.normpath(video_path)
        audio_path = os.path.normpath(audio_path)
        output_path = os.path.normpath(output_path)
        
        logger.info(f"开始合并视频和音频:\n视频: {video_path}\n音频: {audio_path}\n输出: {output_path}")
        
        # 使用FFmpeg合并视频和音频
        try:
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', video_path,  # 输入视频
                '-i', audio_path,  # 输入音频
                '-c:v', 'copy',    # 视频编码保持不变
                '-c:a', 'aac',     # 音频编码为AAC
                '-strict', 'experimental',
                '-y',              # 覆盖已存在的文件
                output_path        # 输出文件
            ]
            
            # 执行FFmpeg命令
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            logger.info(f"视频和音频合并成功: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg执行失败: {e.stderr.decode('utf-8', errors='ignore')}")
            raise
        except Exception as e:
            logger.error(f"合并过程中发生错误: {e}")
            raise
    
    # 网站特定处理器
    def _handle_youtube(self, url: str) -> Dict[str, Any]:
        """处理YouTube视频"""
        try:
            from pytube import YouTube
            
            # 使用pytube获取视频信息
            yt = YouTube(url)
            
            # 获取最高质量的视频流
            video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            # 获取最高质量的音频流
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            return {
                'type': 'video',
                'title': yt.title,
                'author': yt.author,
                'duration': yt.length,
                'views': yt.views,
                'video_url': video_stream.url if video_stream else None,
                'audio_url': audio_stream.url if audio_stream else None,
                'thumbnail_url': yt.thumbnail_url,
                'source': 'youtube'
            }
        except ImportError:
            logger.error("pytube库未安装")
            raise ImportError("请安装pytube库: pip install pytube")
        except Exception as e:
            logger.error(f"YouTube处理失败: {e}")
            # 回退到通用处理
            return self._handle_generic(url)
    
    def _handle_bilibili(self, url: str) -> Dict[str, Any]:
        """处理Bilibili视频"""
        try:
            # 尝试加载B站cookie文件（txt格式）
            cookie_file = os.path.join(config.COOKIES_DIR, 'bilibili.txt')
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        cookie_content = f.read().strip()
                        if cookie_content:
                            # 解析cookie字符串并设置到请求管理器
                            cookies = {}
                            for cookie_pair in cookie_content.split(';'):
                                if '=' in cookie_pair:
                                    key, value = cookie_pair.strip().split('=', 1)
                                    cookies[key] = value
                            request_manager.set_cookies(cookies)
                            logger.info(f"成功加载B站cookie文件: {cookie_file}")
                except Exception as e:
                    logger.error(f"加载B站cookie文件失败: {e}")
            else:
                logger.warning(f"未找到B站cookie文件: {cookie_file}")
            
            # 发送请求获取页面内容
            response = request_manager.get(url)
            # 明确指定编码为UTF-8，避免中文乱码
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取视频标题
            title = soup.find('h1', class_='video-title')
            if not title:
                title = soup.find('span', class_='tit')
            title = title.text.strip() if title else 'Bilibili Video'
            
            author = soup.find('a', class_='up-name')
            if not author:
                author = soup.find('a', class_='username')
            author = author.text.strip() if author else 'Unknown'
            
            # 尝试从页面中提取视频信息
            video_info = {
                'type': 'video',
                'title': title,
                'author': author,
                'source': 'bilibili',
                'original_url': url  # 保存原始URL，用于设置Referer
            }
            
            logger.debug(f"提取到的B站视频标题: {title}")
            logger.debug(f"提取到的B站UP主: {author}")
            
            # 方法1: 尝试直接找到视频标签
            video_tag = soup.find('video')
            if video_tag and video_tag.get('src'):
                video_info['video_url'] = video_tag['src']
                logger.info(f"方法1: 找到直接视频URL: {video_info['video_url']}")
            elif video_tag and video_tag.find('source'):
                video_info['video_url'] = video_tag.find('source')['src']
                logger.info(f"方法1: 找到视频source标签URL: {video_info['video_url']}")
            else:
                # 方法2: 尝试从页面中查找window.__playinfo__变量
                logger.debug("尝试方法2: 查找window.__playinfo__变量")
                scripts = soup.find_all('script')
                found_playinfo = False
                
                for script in scripts:
                    if script.string:
                        # 尝试多种可能的格式来提取playinfo
                        if 'window.__playinfo__' in script.string:
                            try:
                                # 提取window.__playinfo__变量内容
                                playinfo_part = script.string.split('window.__playinfo__=')[1].split('</script>')[0]
                                # 移除末尾可能的分号和空格
                                while playinfo_part and playinfo_part[-1] in [';', ' ', '\n', '\r']:
                                    playinfo_part = playinfo_part[:-1]
                                
                                logger.debug(f"提取到的playinfo_part: {playinfo_part[:100]}...")
                                playinfo = json.loads(playinfo_part)
                                
                                # 提取视频和音频URL
                                if isinstance(playinfo, dict) and 'data' in playinfo and 'dash' in playinfo['data']:
                                    dash = playinfo['data']['dash']
                                    
                                    # 处理视频流 - 选择最高清晰度
                                    if 'video' in dash and dash['video']:
                                        # 按清晰度排序视频流（从高到低）
                                        # 清晰度通常在description或codecs字段中
                                        video_streams = dash['video']
                                        
                                        # 定义清晰度优先级
                                        quality_order = {
                                            '4K': 100,
                                            '2160p': 95,
                                            '2160': 95,
                                            '1440p': 90,
                                            '1080p60': 85,
                                            '1080p': 80,
                                            '720p60': 75,
                                            '720p': 70,
                                            '480p': 60,
                                            '360p': 50,
                                            '240p': 40,
                                            '144p': 30
                                        }
                                        
                                        # 为每个视频流评分
                                        for stream in video_streams:
                                            stream_score = 0
                                            stream_description = '未知'
                                            
                                            # 尝试多种方式识别清晰度
                                            # 1. 检查description字段
                                            if 'description' in stream:
                                                try:
                                                    desc = str(stream['description']).lower()
                                                    stream_description = stream['description']
                                                    for quality, score in quality_order.items():
                                                        if quality.lower() in desc:
                                                            stream_score = score
                                                            break
                                                except:
                                                    pass
                                            
                                            # 2. 检查codecs字段
                                            if stream_score == 0 and 'codecs' in stream:
                                                try:
                                                    codecs = str(stream['codecs']).lower()
                                                    # 从codecs中提取分辨率相关信息
                                                    for quality, score in quality_order.items():
                                                        if quality.lower() in codecs:
                                                            stream_score = score
                                                            break
                                                except:
                                                    pass
                                            
                                            # 3. 检查其他可能包含分辨率的字段
                                            if stream_score == 0:
                                                # 检查bandwidth
                                                if 'bandwidth' in stream:
                                                    stream_score = stream['bandwidth']
                                                # 检查size
                                                elif 'size' in stream:
                                                    stream_score = stream['size']
                                                # 检查id字段或其他可能包含分辨率信息的字段
                                                elif 'id' in stream:
                                                    try:
                                                        id_str = str(stream['id']).lower()
                                                        for quality, score in quality_order.items():
                                                            if quality.lower() in id_str:
                                                                stream_score = score
                                                                break
                                                    except:
                                                        pass
                                            
                                            # 添加额外分数，确保dash格式优先
                                            if 'baseUrl' in stream and '.m4s' in stream['baseUrl']:
                                                stream_score += 1000  # dash格式通常质量更高
                                            
                                            stream['score'] = stream_score
                                            stream['detected_quality'] = stream_description
                                        
                                        # 按评分排序，选择最高评分的视频流
                                        sorted_video_streams = sorted(video_streams, key=lambda x: x.get('score', 0), reverse=True)
                                        
                                        # 选择第一个视频流（最高清晰度）
                                        video_info['video_url'] = sorted_video_streams[0]['baseUrl']
                                        
                                        # 记录选择的视频清晰度信息
                                        selected_stream = sorted_video_streams[0]
                                        quality_info = selected_stream.get('detected_quality', '未知清晰度')
                                        
                                        # 如果description是乱码，尝试从URL或其他字段推断清晰度
                                        if not quality_info or quality_info == '未知' or '鏈煡' in quality_info:
                                            video_url = selected_stream.get('baseUrl', '')
                                            # 从URL中提取清晰度信息
                                            if '30080' in video_url:  # 常见的1080p高质量编码
                                                quality_info = '1080p'
                                                stream_score = 80
                                            elif '16' in video_url:  # 可能是低质量编码
                                                quality_info = '低清晰度'
                                                stream_score = 30
                                            else:
                                                # 根据带宽估算清晰度
                                                bandwidth = selected_stream.get('bandwidth', 0)
                                                if bandwidth > 2000000:
                                                    quality_info = '1080p+'
                                                    stream_score = 90
                                                elif bandwidth > 1000000:
                                                    quality_info = '1080p'
                                                    stream_score = 80
                                                elif bandwidth > 500000:
                                                    quality_info = '720p'
                                                    stream_score = 70
                                                elif bandwidth > 300000:
                                                    quality_info = '480p'
                                                    stream_score = 60
                                                else:
                                                    quality_info = '标清'
                                                    stream_score = 50
                                        
                                        logger.info(f"成功提取最高清晰度视频URL ({quality_info}, 带宽: {selected_stream.get('bandwidth', 0)}): {video_info['video_url'][:50]}...")
                                        
                                        # 添加清晰度信息到media_info
                                        video_info['quality'] = quality_info
                                        video_info['bandwidth'] = selected_stream.get('bandwidth', 0)
                                        # 收集所有可用清晰度，去除重复值
                                        available_qualities = []
                                        for stream in video_streams:
                                            q = stream.get('detected_quality', '未知')
                                            if q not in available_qualities and q and '鏈煡' not in q:
                                                available_qualities.append(q)
                                        # 如果没有有效清晰度信息，基于带宽估算
                                        if not available_qualities:
                                            available_qualities = ['1080p', '720p', '480p', '标清']
                                        video_info['available_qualities'] = available_qualities
                                    
                                    # 处理音频流 - 选择最高质量
                                    if 'audio' in dash and dash['audio']:
                                        audio_streams = dash['audio']
                                        # 按带宽排序，选择最高带宽的音频流
                                        sorted_audio_streams = sorted(audio_streams, key=lambda x: x.get('bandwidth', 0), reverse=True)
                                        video_info['audio_url'] = sorted_audio_streams[0]['baseUrl']
                                        logger.info(f"成功提取最高质量音频URL: {video_info['audio_url'][:50]}...")
                                    
                                    found_playinfo = True
                                    break
                            except Exception as e:
                                logger.debug(f"解析window.__playinfo__失败: {e}")
                                continue
                        
                        # 方法3: 只有在方法2失败时才尝试查找其他可能包含视频信息的变量名
                        # 优先使用方法2，因为它通常能提供更高质量的视频流
                        if not found_playinfo and ('window.__INITIAL_STATE__' in script.string or 'window.playerConfig' in script.string):
                            try:
                                logger.debug("尝试方法3: 查找其他可能的视频信息变量")
                                # 使用正则表达式提取完整的window.__INITIAL_STATE__变量
                                if 'window.__INITIAL_STATE__' in script.string:
                                    # 查找模式：window.__INITIAL_STATE__ = {json内容};
                                    pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
                                    match = re.search(pattern, script.string, re.DOTALL)
                                    
                                    if match:
                                        initial_state_json = match.group(1)
                                        logger.debug(f"提取到的window.__INITIAL_STATE__ JSON长度: {len(initial_state_json)}字符")
                                        
                                        # 尝试解析JSON
                                        initial_state = json.loads(initial_state_json)
                                        
                                        # 检查是否有video对象和playUrlInfo字段
                                        if 'video' in initial_state and 'playUrlInfo' in initial_state['video']:
                                            play_url_info = initial_state['video']['playUrlInfo']
                                            if isinstance(play_url_info, list) and len(play_url_info) > 0:
                                                # 定义清晰度优先级
                                                quality_order = {
                                                    '4K': 100,
                                                    '2160p': 95,
                                                    '2160': 95,
                                                    '1440p': 90,
                                                    '1080p60': 85,
                                                    '1080p': 80,
                                                    '720p60': 75,
                                                    '720p': 70,
                                                    '480p': 60,
                                                    '360p': 50,
                                                    '240p': 40,
                                                    '144p': 30
                                                }
                                                 
                                                # 为每个视频流评分
                                                for stream in play_url_info:
                                                    stream_score = 0
                                                    # 检查清晰度相关字段
                                                    if 'description' in stream:
                                                        desc = stream['description'].lower()
                                                        for quality, score in quality_order.items():
                                                            if quality.lower() in desc:
                                                                stream_score = score
                                                                break
                                                    # 检查bandwidth
                                                    if stream_score == 0 and 'bandwidth' in stream:
                                                        stream_score = stream['bandwidth']
                                                    # 检查size作为备选评分指标
                                                    elif stream_score == 0 and 'size' in stream:
                                                        stream_score = stream['size']
                                                    
                                                    stream['score'] = stream_score
                                                 
                                                # 按评分排序，选择最高评分的视频流
                                                sorted_video_streams = sorted(play_url_info, key=lambda x: x.get('score', 0), reverse=True)
                                                
                                                # 选择最高清晰度的视频流
                                                video_info['video_url'] = sorted_video_streams[0]['url']
                                                
                                                # 记录选择的视频清晰度信息
                                                selected_stream = sorted_video_streams[0]
                                                quality_info = selected_stream.get('description', '未知清晰度')
                                                logger.info(f"方法3: 从window.__INITIAL_STATE__.video.playUrlInfo成功提取最高清晰度视频URL ({quality_info}): {video_info['video_url'][:50]}...")
                                                
                                                # 添加清晰度信息到media_info
                                                video_info['quality'] = quality_info
                                                video_info['available_qualities'] = [stream.get('description', '未知') for stream in play_url_info]
                                                
                                                found_playinfo = True
                                                break
                            except Exception as e:
                                logger.debug(f"解析其他变量失败: {e}")
                                continue
                
                # 方法4: 直接使用B站API接口(需要BV号)
                if not found_playinfo:
                    logger.debug("尝试方法4: 使用B站API接口")
                    # 从URL中提取BV号
                    bv_match = re.search(r'(BV[\w]+)', url)
                    if bv_match:
                        bv_id = bv_match.group(1)
                        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"
                        try:
                            # 使用原始请求的cookie和headers
                            api_headers = {
                                'Referer': url,
                                'User-Agent': response.request.headers.get('User-Agent')
                            }
                            api_response = request_manager.get(api_url, headers=api_headers)
                            api_data = api_response.json()
                            logger.debug(f"API响应状态: {api_data.get('code')}")
                            if api_data.get('code') == 0:
                                # 这里简化处理，实际项目中需要从API响应中提取更多信息
                                logger.info(f"成功调用B站API，获取到视频基本信息")
                        except Exception as e:
                            logger.debug(f"调用B站API失败: {e}")
            
            # 尝试通过不同方法提取视频URL
            if 'video_url' not in video_info:
                # 1. 尝试从页面中的<script>标签提取更多信息
                try:
                    # 搜索包含视频信息的脚本标签
                    for script in soup.find_all('script'):
                        if script.string and 'window.__playinfo__' in script.string:
                            logger.debug("找到window.__playinfo__脚本，尝试提取视频信息")
                            try:
                                # 尝试解析脚本内容
                                script_content = script.string
                                playinfo_start = script_content.find('window.__playinfo__=') + len('window.__playinfo__=')
                                playinfo_end = script_content.find(';', playinfo_start)
                                if playinfo_start > -1 and playinfo_end > playinfo_start:
                                    playinfo_data = json.loads(script_content[playinfo_start:playinfo_end])
                                    # 检查是否有视频数据
                                    if 'data' in playinfo_data and 'dash' in playinfo_data['data']:
                                        dash_data = playinfo_data['data']['dash']
                                        if 'video' in dash_data and len(dash_data['video']) > 0:
                                            # 选择第一个视频流
                                            video_info['video_url'] = dash_data['video'][0]['baseUrl']
                                        if 'audio' in dash_data and len(dash_data['audio']) > 0:
                                            # 选择第一个音频流
                                            video_info['audio_url'] = dash_data['audio'][0]['baseUrl']
                                    break
                            except Exception as inner_e:
                                logger.debug(f"解析window.__playinfo__失败: {inner_e}")
                except Exception as e:
                    logger.debug(f"提取<script>标签信息失败: {e}")
                
                # 2. 如果还是没有找到URL，提供明确的错误提示
                if 'video_url' not in video_info:
                    logger.warning(f"无法从B站提取实际视频URL，可能的原因：")
                    logger.warning(f"1. 需要登录账号：请确保已在config/cookies/bilibili.txt中正确配置cookie")
                    logger.warning(f"2. B站页面结构可能已变更：需要更新解析逻辑")
                    logger.warning(f"3. 视频可能需要特殊权限访问")
                    
                    # 设置为None而不是测试URL，以便调用方能够正确处理这种情况
                    video_info['video_url'] = None
                    video_info['audio_url'] = None
                    video_info['login_required'] = True
            
            return video_info
        except Exception as e:
            logger.error(f"Bilibili处理失败: {e}")
            # 回退到通用处理
            generic_result = self._handle_generic(url)
            generic_result['original_url'] = url  # 确保通用处理结果也包含原始URL
            generic_result['login_required'] = True
            return generic_result
    
    def _handle_soundcloud(self, url: str) -> Dict[str, Any]:
        """处理SoundCloud音频"""
        try:
            # 发送请求获取页面内容
            response = request_manager.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取音频标题
            title = soup.find('h1').text.strip() if soup.find('h1') else 'SoundCloud Audio'
            
            # 提取音频信息
            audio_info = {
                'type': 'audio',
                'title': title,
                'author': soup.find('span', itemprop='author').text.strip() if soup.find('span', itemprop='author') else 'Unknown',
                'source': 'soundcloud'
            }
            
            # 在实际应用中，需要解析页面中的JavaScript变量或调用SoundCloud API来获取真实的音频URL
            # 这里仅作为示例
            
            return audio_info
        except Exception as e:
            logger.error(f"SoundCloud处理失败: {e}")
            # 回退到通用处理
            return self._handle_generic(url)
    
    def _handle_generic(self, url: str) -> Dict[str, Any]:
        """通用处理器，尝试从任何网站提取媒体信息"""
        try:
            # 发送请求获取页面内容
            response = request_manager.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = soup.title.text.strip() if soup.title else 'Unknown Media'
            
            # 尝试查找视频和音频标签
            video_tags = soup.find_all('video')
            audio_tags = soup.find_all('audio')
            
            media_info = {
                'type': 'unknown',
                'title': title,
                'source': urlparse(url).netloc,
                'video_url': None,
                'audio_url': None
            }
            
            # 尝试提取第一个视频源
            if video_tags:
                media_info['type'] = 'video'
                for video in video_tags:
                    if video.get('src'):
                        media_info['video_url'] = video['src']
                        break
                    elif video.find('source'):
                        media_info['video_url'] = video.find('source')['src']
                        break
            
            # 尝试提取第一个音频源
            if audio_tags:
                media_info['type'] = 'audio'
                for audio in audio_tags:
                    if audio.get('src'):
                        media_info['audio_url'] = audio['src']
                        break
                    elif audio.find('source'):
                        media_info['audio_url'] = audio.find('source')['src']
                        break
            
            return media_info
        except Exception as e:
            logger.error(f"通用处理失败: {e}")
            raise

# 导出全局实例
media_crawler = MediaCrawler()