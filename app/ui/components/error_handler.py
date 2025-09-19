#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误处理和Toast通知组件
"""

import logging
from enum import Enum
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QObject
)
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ToastWidget(QFrame):
    """Toast通知组件"""

    def __init__(self, title: str, message: str, message_type: MessageType, parent=None):
        super().__init__(parent)
        self.message_type = message_type

        self.setFixedSize(300, 80)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui(title, message)
        self._apply_styles()

        # 设置透明度效果
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        # 动画
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b'opacity')

        # 自动隐藏定时器
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.fade_out)

    def _setup_ui(self, title: str, message: str):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setObjectName("toast-title")
        layout.addWidget(title_label)

        # 消息
        message_label = QLabel(message)
        message_label.setFont(QFont("Arial", 10))
        message_label.setWordWrap(True)
        message_label.setObjectName("toast-message")
        layout.addWidget(message_label)

    def _apply_styles(self):
        """应用样式"""
        colors = {
            MessageType.INFO: {"bg": "#e6f7ff", "border": "#1890ff", "text": "#003a8c"},
            MessageType.SUCCESS: {"bg": "#f6ffed", "border": "#52c41a", "text": "#135200"},
            MessageType.WARNING: {"bg": "#fffbe6", "border": "#faad14", "text": "#613400"},
            MessageType.ERROR: {"bg": "#fff2f0", "border": "#ff4d4f", "text": "#820014"}
        }

        color_scheme = colors[self.message_type]

        self.setStyleSheet(f"""
            ToastWidget {{
                background-color: {color_scheme['bg']};
                border: 2px solid {color_scheme['border']};
                border-radius: 8px;
            }}
            #toast-title {{
                color: {color_scheme['text']};
                border: none;
            }}
            #toast-message {{
                color: {color_scheme['text']};
                border: none;
            }}
        """)

    def show_animated(self, duration: int = 3000):
        """显示动画"""
        # 设置初始透明度
        self.opacity_effect.setOpacity(0.0)
        self.show()

        # 淡入动画
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()

        # 设置自动隐藏
        self.hide_timer.start(duration)

    def fade_out(self):
        """淡出动画"""
        self.hide_timer.stop()

        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()


class ToastManager(QObject):
    """Toast管理器"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return

        super().__init__()
        self.parent = parent
        self.active_toasts = []
        self._initialized = True

    def show_toast(self, title: str, message: str, message_type: MessageType = MessageType.INFO,
                   duration: int = 3000, parent: QWidget = None):
        """显示Toast通知"""
        try:
            # 创建Toast
            toast = ToastWidget(title, message, message_type, parent)

            # 计算位置
            if parent:
                parent_rect = parent.geometry()
                x = parent_rect.right() - toast.width() - 20
                y = parent_rect.top() + 20 + (len(self.active_toasts) * 90)
            else:
                # 默认位置（屏幕右上角）
                from PyQt6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().geometry()
                x = screen.width() - toast.width() - 20
                y = 20 + (len(self.active_toasts) * 90)

            toast.move(x, y)

            # 添加到活动列表
            self.active_toasts.append(toast)

            # 清理回调
            def cleanup_toast():
                if toast in self.active_toasts:
                    self.active_toasts.remove(toast)
                    self._reposition_toasts()

            toast.fade_animation.finished.connect(cleanup_toast)

            # 显示Toast
            toast.show_animated(duration)

        except Exception as e:
            logger.error(f"显示Toast失败: {e}")

    def _reposition_toasts(self):
        """重新定位Toast"""
        for i, toast in enumerate(self.active_toasts):
            if toast.isVisible():
                current_pos = toast.pos()
                new_y = 20 + (i * 90)
                toast.move(current_pos.x(), new_y)

    def clear_all(self):
        """清除所有Toast"""
        for toast in self.active_toasts[:]:
            toast.fade_out()
        self.active_toasts.clear()


# 便利函数
def show_info(title: str, message: str, parent: QWidget = None):
    """显示信息Toast"""
    ToastManager().show_toast(title, message, MessageType.INFO, parent=parent)


def show_success(title: str, message: str, parent: QWidget = None):
    """显示成功Toast"""
    ToastManager().show_toast(title, message, MessageType.SUCCESS, parent=parent)


def show_warning(title: str, message: str, parent: QWidget = None):
    """显示警告Toast"""
    ToastManager().show_toast(title, message, MessageType.WARNING, parent=parent)


def show_error(title: str, message: str, parent: QWidget = None):
    """显示错误Toast"""
    ToastManager().show_toast(title, message, MessageType.ERROR, parent=parent)