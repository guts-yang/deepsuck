# DeepSuck 媒体爬虫

一个高效合规的网络爬虫项目，支持爬取多个主流网站的视频及音乐数据，并提供直接下载、音视频合并等功能。

## 版本信息

- 当前版本：1.0.0
- 最近更新：2025-09-13

## 功能特点

- **多网站支持**：支持爬取YouTube、Bilibili、SoundCloud等多个主流视频和音乐网站
- **媒体下载**：提供视频和音频文件的直接下载功能
- **视频音频同步导出**：自动使用FFmpeg合并视频和音频流，确保导出的MP4文件包含同步音频
- **用户友好界面**：包含URL输入、爬取选项和状态显示的图形用户界面
- **反爬机制**：集成robots协议检查、随机User-Agent、请求延迟等反爬措施
- **登录支持**：提供自动和手动登录功能，支持需要登录才能访问的内容
- **合规性保证**：严格遵循robots协议及相关法律法规
- **灵活配置**：通过配置文件自定义爬虫行为和参数

## 安装指南

### 前提条件

- Python 3.7+ 环境
- 安装Chrome浏览器（用于Selenium登录功能）
- 安装FFmpeg（**必须**，用于视频音频同步导出功能）
  > **重要提示**：视频音频合并功能需要正确安装FFmpeg，否则将无法生成包含同步音频的完整视频文件

### 安装步骤

1. 克隆或下载项目代码到本地

```bash
git clone https://github.com/guts-yang/deepsuck.git
cd deepsuck
```

2. 安装所需依赖

```bash
pip install -r requirements.txt
```

3. 安装FFmpeg（视频音频同步导出功能必需）

#### Windows系统

- 访问FFmpeg官网下载页面：https://ffmpeg.org/download.html
- 选择Windows版本的构建（推荐gyan.dev的构建）
- 下载压缩包并解压到D:\ffmpeg目录
- 将D:\ffmpeg\bin添加到系统环境变量PATH中
- 验证安装：打开命令提示符，输入`ffmpeg -version`（注意是单个短横线），如果显示版本信息则安装成功

#### macOS系统

使用Homebrew安装：

```bash
brew install ffmpeg
```

验证安装：

```bash
ffmpeg -version  # 注意是单个短横线
```

#### Linux系统

Ubuntu/Debian：

```bash
sudo apt update
sudo apt install ffmpeg
```

CentOS/RHEL：

```bash
sudo yum install ffmpeg ffmpeg-devel
```

验证安装：

```bash
ffmpeg -version
```

## 使用方法

### 图形用户界面模式

DeepSuck提供了直观易用的图形用户界面，适合快速操作和可视化管理。

#### 快速启动（Windows系统）

双击项目根目录下的`start_ui.bat`文件，即可快速启动程序。

#### 命令行启动

启动图形用户界面，通过直观的界面进行操作：

```bash
python main.py ui
```

界面功能说明：
- **URL输入**：输入要爬取的媒体URL
- **选项设置**：设置下载类型、下载路径和登录选项
  - **下载路径**：默认设置为`D:\coding\deepsuck\data\videos`
- **日志输出**：显示爬取和下载过程的详细日志
- **媒体信息**：显示爬取到的媒体详情，并提供下载按钮

### 命令行模式

对于高级用户或自动化场景，DeepSuck提供了功能丰富的命令行接口。

#### 爬取媒体信息

```bash
python main.py crawl <URL> [--login] [--manual-login] [--username USERNAME] [--password PASSWORD] [--output OUTPUT_FILE]
```

参数说明：
- `URL`：目标媒体的URL
- `--login`：是否需要登录（可选）
- `--manual-login`：是否手动登录（可选）
- `--username`：用户名（可选，非手动登录时需要）
- `--password`：密码（可选，非手动登录时需要）
- `--output`：爬取结果的输出文件路径（可选）

#### 下载媒体文件

```bash
python main.py download <URL> [--login] [--manual-login] [--username USERNAME] [--password PASSWORD] [--output-dir OUTPUT_DIR] [--type {video,audio,both}]
```

参数说明：
- `URL`：目标媒体的URL
- `--login`：是否需要登录（可选）
- `--manual-login`：是否手动登录（可选）
- `--username`：用户名（可选，非手动登录时需要）
- `--password`：密码（可选，非手动登录时需要）
- `--output-dir`：下载目录（可选，默认为`D:\coding\deepsuck\data\videos`）
- `--type`：下载类型（可选，video/audio/both，默认为both）

**注意**：当选择同时下载视频和音频（--type both）时，系统会自动使用FFmpeg合并两者，生成包含同步音频的MP4文件。

> **重要提示**：确保FFmpeg已正确安装并配置在系统环境变量中，否则视频音频合并可能会失败。

#### 登录网站

```bash
python main.py login <URL> [--manual] [--username USERNAME] [--password PASSWORD]
```

参数说明：
- `URL`：目标网站的URL
- `--manual`：是否手动登录（可选）
- `--username`：用户名（可选，非手动登录时需要）
- `--password`：密码（可选，非手动登录时需要）

#### 检查robots.txt规则

```bash
python main.py robots <URL>
```

参数说明：
- `URL`：要检查的网站URL

## 配置说明

DeepSuck提供了灵活的配置选项，让用户可以根据自己的需求自定义爬虫行为。

### 主配置文件

项目的主要配置位于`config/config.py`文件中，可以根据需要进行自定义修改：

- **USER_AGENTS**：爬虫使用的User-Agent列表
- **REQUEST_DELAY**：请求间隔时间（秒）
- **MAX_RETRY**：请求失败的最大重试次数
- **DOWNLOAD_CHUNK_SIZE**：下载文件的块大小
- **MAX_CONCURRENT_DOWNLOADS**：最大并发下载数
- **ROBOTS_TXT_ENABLED**：是否启用robots.txt检查
- **MAX_PAGES_PER_DOMAIN**：每个域名的最大爬取页数
- **DATA_DIR**：数据存储根目录
- **VIDEO_DIR**：视频下载目录（默认为`D:\coding\deepsuck\data\videos`）
- **AUDIO_DIR**：音频下载目录（默认为`D:\coding\deepsuck\data\audios`）

### 环境变量配置

此外，还可以通过环境变量文件`.env`配置API密钥等敏感信息：

```env
# 示例.env文件
YOUTUBE_API_KEY=your_youtube_api_key
SPOTIFY_API_KEY=your_spotify_api_key
```

## 项目结构

```
deepsuck/
├── src/                # 源代码目录
│   ├── media_crawler.py   # 媒体爬虫核心模块
│   ├── login_manager.py   # 登录管理模块
│   ├── request_manager.py # HTTP请求管理模块
│   ├── robots_checker.py  # robots协议检查模块
│   └── ui.py              # 图形用户界面模块
├── config/             # 配置文件目录
│   ├── config.py          # 主配置文件
│   └── cookies/           # cookies存储目录
├── data/               # 数据存储目录
│   ├── videos/            # 视频文件存储（默认下载路径）
│   └── audios/            # 音频文件存储
├── docs/               # 文档目录
├── logs/               # 日志文件目录
├── main.py             # 主入口文件
├── requirements.txt    # 依赖清单文件
└── start_ui.bat        # Windows快速启动脚本
```

## 合规声明

DeepSuck高度重视网络爬虫的合规性，设计和实现严格遵守以下原则：

1. **遵循robots协议**：在爬取前检查网站的robots.txt文件，并尊重网站的爬取规则
2. **控制爬取频率**：通过配置请求间隔和随机延迟，避免对目标网站造成过大压力
3. **限制爬取范围**：设置每个域名的最大爬取页数，防止过度爬取
4. **合法使用数据**：提醒用户仅将爬取的数据用于合法目的，尊重版权和知识产权

## 注意事项

- **法律合规**：使用本项目时，请确保遵守目标网站的服务条款和相关法律法规
- **版权保护**：下载和使用媒体文件时，请尊重内容创作者的版权
- **网络安全**：不要将本项目用于任何非法或未经授权的活动
- **资源使用**：大量爬取和下载操作可能会消耗较多网络带宽和存储空间
- **FFmpeg依赖**：**视频音频同步导出功能必须正确安装FFmpeg并配置环境变量**，否则可能无法生成包含音频的视频文件
- **默认下载路径**：程序默认的媒体下载路径为`D:\coding\deepsuck\data\videos`，您可以在UI界面或通过命令行参数`--output-dir`进行更改
- **系统性能**：对于大型媒体文件的下载和处理，建议确保您的系统有足够的内存和磁盘空间
- **更新通知**：定期检查项目更新以获取最新功能和错误修复

## 常见问题

### 1. 为什么我的视频下载后没有声音？

请确认FFmpeg已正确安装并配置在系统环境变量中。视频音频合并功能依赖FFmpeg，如未正确安装，可能导致生成的视频文件没有声音。

### 2. 如何更改默认的下载路径？

您可以通过以下方式更改默认下载路径：
- 在图形界面中，直接修改"下载路径"输入框中的路径
- 在命令行中，使用`--output-dir`参数指定下载目录
- 直接修改`config.py`文件中的`VIDEO_DIR`和`AUDIO_DIR`配置项

### 3. 为什么有些网站的内容无法爬取？

可能的原因包括：
- 该网站需要登录才能访问内容，请尝试使用`--login`参数
- 该网站有较强的反爬机制，可能需要调整爬取策略
- 该网站可能不在支持的网站列表中

## 贡献指南

欢迎对DeepSuck项目进行贡献！如果您有任何建议或改进，请通过GitHub提交Issue或Pull Request。

## 免责声明

本项目仅供学习和研究使用。对于使用本项目可能导致的任何法律责任或损失，项目开发者不承担任何责任。用户应自行承担使用本项目的风险，并确保其行为符合所有适用的法律法规。
