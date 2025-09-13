@echo off
REM DeepSuck 媒体爬虫UI启动脚本

REM 设置控制台编码为UTF-8
chcp 65001 > nul

REM 显示启动信息
cls
echo ===========================================================
echo           DeepSuck 媒体爬虫 - 图形用户界面

echo           已将默认下载路径设置为: D:\coding\deepsuck\data\videos

echo ===========================================================
echo.
echo 正在启动程序，请稍候...

echo.
echo 如果需要命令行模式，请使用以下命令:
echo - 爬取媒体信息: python main.py crawl <URL>
echo - 下载媒体文件: python main.py download <URL>
echo - 检查robots.txt: python main.py robots <URL>
echo.

REM 启动UI
python main.py ui

REM 如果程序异常退出，显示错误信息并等待用户按键
echo.
echo 程序已退出。按任意键关闭窗口...
pause > nul