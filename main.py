#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import atexit
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.ui.main_window import MainWindow


def cleanup():
    """清理资源"""
    # 这里可以添加应用退出时需要执行的清理操作
    print("正在清理资源...")


def setup_app_icon(app):
    """设置应用程序图标"""
    icon_path = "resources/icons/app_icon.png"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))


def main():
    """主程序入口函数"""
    # 注册退出处理函数
    atexit.register(cleanup)
    
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setApplicationName("VideoEpicCreator")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Agions")
    
    # 设置应用图标
    setup_app_icon(app)
    
    # 设置样式
    try:
        style_path = "resources/styles/style.qss"
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                app.setStyleSheet(f.read())
        else:
            print(f"样式文件不存在: {style_path}")
    except Exception as e:
        print(f"加载样式失败: {e}")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 进入事件循环
    exit_code = app.exec()
    
    # 返回退出码
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 