import sys
import os
import logging
import threading
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QFileDialog, 
    QCheckBox, QProgressBar, QGroupBox, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from config.config import config
from src.media_crawler import media_crawler
from src.login_manager import login_manager

# 配置日志
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class CrawlerThread(QThread):
    """爬虫线程，用于在后台执行爬取任务"""
    # 定义信号
    progress_update = pyqtSignal(int)
    log_message = pyqtSignal(str)
    crawl_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        """线程运行函数"""
        try:
            self.log_message.emit(f"开始爬取: {self.url}")
            self.progress_update.emit(20)
            
            # 执行爬取
            media_info = media_crawler.crawl(self.url)
            
            self.progress_update.emit(100)
            self.log_message.emit(f"爬取完成: {media_info.get('title', '未知媒体')}")
            
            # 发送完成信号
            self.crawl_complete.emit(media_info)
        except Exception as e:
            error_msg = f"爬取失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)

class DownloadThread(QThread):
    """下载线程，用于在后台执行下载任务"""
    # 定义信号
    progress_update = pyqtSignal(int)
    log_message = pyqtSignal(str)
    download_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, media_info: Dict[str, Any], download_path: str, download_type: str):
        super().__init__()
        self.media_info = media_info
        self.download_path = download_path
        self.download_type = download_type
    
    def run(self):
        """线程运行函数"""
        try:
            self.log_message.emit(f"开始下载: {self.media_info.get('title', '未知媒体')}")
            
            # 执行下载
            result = media_crawler.download(self.media_info, self.download_path, self.download_type)
            
            self.progress_update.emit(100)
            
            # 记录下载结果
            for media_type, path in result.items():
                self.log_message.emit(f"{media_type} 下载完成: {path}")
            
            # 发送完成信号
            self.download_complete.emit(result)
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)

class LoginThread(QThread):
    """登录线程，用于在后台执行登录任务"""
    # 定义信号
    log_message = pyqtSignal(str)
    login_complete = pyqtSignal(bool)
    
    def __init__(self, url: str, username: str, password: str, manual: bool):
        super().__init__()
        self.url = url
        self.username = username
        self.password = password
        self.manual = manual
    
    def run(self):
        """线程运行函数"""
        try:
            self.log_message.emit(f"开始登录: {self.url}")
            
            # 执行登录
            success = login_manager.login(
                self.url, 
                self.username if self.username else None, 
                self.password if self.password else None, 
                use_selenium=True, 
                manual=self.manual
            )
            
            if success:
                self.log_message.emit("登录成功")
            else:
                self.log_message.emit("登录失败")
            
            # 发送完成信号
            self.login_complete.emit(success)
        except Exception as e:
            error_msg = f"登录异常: {str(e)}"
            self.log_message.emit(error_msg)
            self.login_complete.emit(False)

class MediaCrawlerUI(QMainWindow):
    """媒体爬虫用户界面"""
    
    def __init__(self):
        super().__init__()
        # 保存当前爬取的媒体信息
        self.current_media_info = None
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("DeepSuck 媒体爬虫")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建URL输入区域
        url_group = QGroupBox("URL输入")
        url_layout = QHBoxLayout()
        
        self.url_label = QLabel("目标URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入视频或音乐的URL...")
        self.crawl_button = QPushButton("爬取")
        self.crawl_button.clicked.connect(self.start_crawl)
        
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.url_input, 1)  # 占据剩余空间
        url_layout.addWidget(self.crawl_button)
        
        url_group.setLayout(url_layout)
        
        # 创建选项区域
        options_group = QGroupBox("选项设置")
        options_layout = QGridLayout()
        
        # 下载类型选择
        self.download_type_label = QLabel("下载类型:")
        self.download_type_combo = QComboBox()
        self.download_type_combo.addItems(["两者都下载", "仅视频", "仅音频"])
        
        # 下载路径选择
        self.download_path_label = QLabel("下载路径:")
        self.download_path_input = QLineEdit(str(config.VIDEO_DIR))
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_download_path)
        
        # 登录选项
        self.login_checkbox = QCheckBox("需要登录")
        self.login_checkbox.stateChanged.connect(self.toggle_login_fields)
        self.manual_login_checkbox = QCheckBox("手动登录")
        
        # 用户名和密码输入
        self.username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        self.password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.start_login)
        
        # 添加到布局
        options_layout.addWidget(self.download_type_label, 0, 0)
        options_layout.addWidget(self.download_type_combo, 0, 1)
        options_layout.addWidget(self.login_checkbox, 0, 2)
        options_layout.addWidget(self.manual_login_checkbox, 0, 3)
        
        options_layout.addWidget(self.download_path_label, 1, 0)
        options_layout.addWidget(self.download_path_input, 1, 1, 1, 2)
        options_layout.addWidget(self.browse_button, 1, 3)
        
        options_layout.addWidget(self.username_label, 2, 0)
        options_layout.addWidget(self.username_input, 2, 1)
        options_layout.addWidget(self.password_label, 2, 2)
        options_layout.addWidget(self.password_input, 2, 3)
        
        options_layout.addWidget(self.login_button, 3, 3)
        
        options_group.setLayout(options_layout)
        
        # 初始隐藏登录字段
        self.toggle_login_fields()
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 创建状态和日志区域
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # 创建媒体信息区域
        media_group = QGroupBox("媒体信息")
        media_layout = QVBoxLayout()
        
        self.media_info_text = QTextEdit()
        self.media_info_text.setReadOnly(True)
        
        # 创建下载按钮
        self.download_button = QPushButton("下载媒体")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)  # 初始禁用
        
        media_layout.addWidget(self.media_info_text)
        media_layout.addWidget(self.download_button)
        
        media_group.setLayout(media_layout)
        
        # 将所有组件添加到主布局
        main_layout.addWidget(url_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(log_group, 1)  # 占据剩余空间
        main_layout.addWidget(media_group)
    
    def toggle_login_fields(self):
        """切换登录字段的显示状态"""
        is_checked = self.login_checkbox.isChecked()
        self.username_label.setVisible(is_checked)
        self.username_input.setVisible(is_checked)
        self.password_label.setVisible(is_checked)
        self.password_input.setVisible(is_checked)
        self.login_button.setVisible(is_checked)
        self.manual_login_checkbox.setVisible(is_checked)
        
        # 如果选择手动登录，禁用用户名和密码输入
        if is_checked:
            manual_checked = self.manual_login_checkbox.isChecked()
            self.username_input.setEnabled(not manual_checked)
            self.password_input.setEnabled(not manual_checked)
    
    def browse_download_path(self):
        """浏览下载路径"""
        path = QFileDialog.getExistingDirectory(self, "选择下载路径", self.download_path_input.text())
        if path:
            self.download_path_input.setText(path)
    
    def log(self, message: str):
        """记录日志信息"""
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        # 同时输出到Python日志
        logger.info(message)
    
    def start_crawl(self):
        """开始爬取任务"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        
        # 禁用爬取按钮
        self.crawl_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建并启动爬取线程
        self.crawler_thread = CrawlerThread(url)
        self.crawler_thread.progress_update.connect(self.update_progress)
        self.crawler_thread.log_message.connect(self.log)
        self.crawler_thread.crawl_complete.connect(self.on_crawl_complete)
        self.crawler_thread.error_occurred.connect(self.on_error)
        
        self.crawler_thread.start()
    
    def start_download(self):
        """开始下载任务"""
        if not self.current_media_info:
            QMessageBox.warning(self, "警告", "请先爬取媒体信息")
            return
        
        # 获取下载设置
        download_path = self.download_path_input.text().strip()
        if not download_path:
            QMessageBox.warning(self, "警告", "请选择有效的下载路径")
            return
        
        # 确保下载路径存在
        os.makedirs(download_path, exist_ok=True)
        
        # 获取下载类型
        download_type_index = self.download_type_combo.currentIndex()
        download_type_map = {0: 'both', 1: 'video', 2: 'audio'}
        download_type = download_type_map.get(download_type_index, 'both')
        
        # 禁用下载按钮
        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建并启动下载线程
        self.download_thread = DownloadThread(
            self.current_media_info, 
            download_path, 
            download_type
        )
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.log_message.connect(self.log)
        self.download_thread.download_complete.connect(self.on_download_complete)
        self.download_thread.error_occurred.connect(self.on_error)
        
        self.download_thread.start()
    
    def start_login(self):
        """开始登录任务"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请先输入URL")
            return
        
        # 获取登录信息
        username = self.username_input.text().strip() if not self.manual_login_checkbox.isChecked() else None
        password = self.password_input.text().strip() if not self.manual_login_checkbox.isChecked() else None
        manual = self.manual_login_checkbox.isChecked()
        
        # 如果不是手动登录，检查用户名和密码
        if not manual and (not username or not password):
            QMessageBox.warning(self, "警告", "请输入用户名和密码")
            return
        
        # 禁用登录按钮
        self.login_button.setEnabled(False)
        
        # 创建并启动登录线程
        self.login_thread = LoginThread(url, username, password, manual)
        self.login_thread.log_message.connect(self.log)
        self.login_thread.login_complete.connect(self.on_login_complete)
        
        self.login_thread.start()
    
    def update_progress(self, value: int):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def on_crawl_complete(self, media_info: Dict[str, Any]):
        """爬取完成回调"""
        # 保存媒体信息
        self.current_media_info = media_info
        
        # 显示媒体信息
        info_text = "媒体信息:\n"
        for key, value in media_info.items():
            info_text += f"{key}: {value}\n"
        
        self.media_info_text.setText(info_text)
        
        # 启用下载按钮
        self.download_button.setEnabled(True)
        # 重新启用爬取按钮
        self.crawl_button.setEnabled(True)
    
    def on_download_complete(self, result: Dict[str, str]):
        """下载完成回调"""
        # 重新启用下载按钮
        self.download_button.setEnabled(True)
        
        # 显示下载完成消息
        QMessageBox.information(self, "下载完成", "媒体文件下载成功！")
    
    def on_login_complete(self, success: bool):
        """登录完成回调"""
        # 重新启用登录按钮
        self.login_button.setEnabled(True)
        
        # 显示登录结果消息
        if success:
            QMessageBox.information(self, "登录成功", "登录成功，可以开始爬取了！")
        else:
            QMessageBox.warning(self, "登录失败", "登录失败，请重试")
    
    def on_error(self, error_msg: str):
        """错误处理回调"""
        # 重新启用相关按钮
        self.crawl_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.login_button.setEnabled(True)
        
        # 显示错误消息
        QMessageBox.critical(self, "错误", error_msg)

# JSON模块导入
import json

def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = MediaCrawlerUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()