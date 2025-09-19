#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
加载状态指示器组件 - 提供优雅的加载动画和状态提示
支持多种加载样式和自定义消息
"""

from typing import Optional, Dict, Any
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtCore import QPointF

from .base_component import BaseComponent, ComponentConfig


class LoadingStyle(Enum):
    """加载样式枚举"""
    SPINNER = "spinner"          # 旋转器
    PROGRESS = "progress"        # 进度条
    PULSE = "pulse"              # 脉冲
    DOTS = "dots"                # 点状
    BARS = "bars"                # 条状
    CUSTOM = "custom"            # 自定义


class LoadingIndicator(QWidget):
    """加载状态指示器基础类"""
    
    loading_complete = pyqtSignal()  # 加载完成信号
    
    def __init__(self, parent=None, style: LoadingStyle = LoadingStyle.SPINNER):
        super().__init__(parent)
        self.style = style
        self.is_loading = False
        self.progress = 0
        self.message = "加载中..."
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_step = 0
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置UI"""
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("background-color: transparent;")
    
    def start_loading(self, message: str = "加载中..."):
        """开始加载"""
        self.is_loading = True
        self.message = message
        self.progress = 0
        self.animation_step = 0
        self.animation_timer.start(50)  # 20 FPS
        self.update()
        self.show()
    
    def update_progress(self, progress: int, message: Optional[str] = None):
        """更新进度"""
        self.progress = max(0, min(100, progress))
        if message:
            self.message = message
        
        if self.progress >= 100:
            self.complete_loading()
        
        self.update()
    
    def complete_loading(self):
        """完成加载"""
        self.is_loading = False
        self.progress = 100
        self.animation_timer.stop()
        self.update()
        
        # 延迟隐藏
        QTimer.singleShot(500, self.hide)
        QTimer.singleShot(500, self.loading_complete.emit)
    
    def _update_animation(self):
        """更新动画"""
        self.animation_step = (self.animation_step + 1) % 360
        self.update()
    
    def stop_loading(self):
        """停止加载"""
        self.is_loading = False
        self.animation_timer.stop()
        self.hide()
    
    def paintEvent(self, event):
        """绘制事件"""
        if not self.is_loading and self.progress >= 100:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        if self.style == LoadingStyle.SPINNER:
            self._draw_spinner(painter, center_x, center_y)
        elif self.style == LoadingStyle.PROGRESS:
            self._draw_progress(painter, center_x, center_y)
        elif self.style == LoadingStyle.PULSE:
            self._draw_pulse(painter, center_x, center_y)
        elif self.style == LoadingStyle.DOTS:
            self._draw_dots(painter, center_x, center_y)
        elif self.style == LoadingStyle.BARS:
            self._draw_bars(painter, center_x, center_y)
        
        # 绘制消息
        if self.message:
            self._draw_message(painter, center_x, center_y)
    
    def _draw_spinner(self, painter: QPainter, center_x: int, center_y: int):
        """绘制旋转器"""
        radius = 25
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.animation_step)
        
        # 绘制旋转圆圈
        for i in range(8):
            angle = i * 45
            painter.save()
            painter.rotate(angle)
            
            # 计算透明度
            alpha = 255 - (i * 32)
            color = QColor(0, 122, 204, alpha)
            
            painter.setPen(QPen(color, 3, Qt.PenStyle.SolidLine))
            painter.drawArc(0, -radius, radius * 2, radius * 2, 0, 90 * 16)
            painter.restore()
        
        painter.restore()
    
    def _draw_progress(self, painter: QPainter, center_x: int, center_y: int):
        """绘制进度条"""
        radius = 30
        start_angle = 90 * 16  # 从顶部开始
        
        # 绘制背景圆
        painter.setPen(QPen(QColor(200, 200, 200), 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 绘制进度弧
        span_angle = int((self.progress / 100) * 360 * 16)
        painter.setPen(QPen(QColor(0, 122, 204), 4))
        painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, 
                      start_angle, span_angle)
        
        # 绘制进度文本
        painter.setPen(QPen(QColor(0, 0, 0)))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(center_x - 20, center_y - 10, 40, 20), 
                       Qt.AlignmentFlag.AlignCenter, f"{self.progress}%")
    
    def _draw_pulse(self, painter: QPainter, center_x: int, center_y: int):
        """绘制脉冲效果"""
        # 计算脉冲半径
        pulse_radius = 20 + (self.animation_step % 60) * 0.5
        alpha = max(0, 255 - (self.animation_step % 60) * 4)
        
        # 绘制脉冲圆
        color = QColor(0, 122, 204, alpha)
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - int(pulse_radius), center_y - int(pulse_radius), 
                          int(pulse_radius * 2), int(pulse_radius * 2))
        
        # 绘制中心圆
        painter.setPen(QPen(QColor(0, 122, 204), 3))
        painter.setBrush(QBrush(QColor(0, 122, 204, 50)))
        painter.drawEllipse(center_x - 15, center_y - 15, 30, 30)
    
    def _draw_dots(self, painter: QPainter, center_x: int, center_y: int):
        """绘制点状动画"""
        dot_count = 5
        dot_spacing = 15
        start_x = center_x - (dot_count - 1) * dot_spacing // 2
        
        for i in range(dot_count):
            # 计算每个点的大小和透明度
            phase = (self.animation_step + i * 20) % 100
            size = 4 + (phase // 25) * 2
            alpha = 100 + (phase // 25) * 40
            
            color = QColor(0, 122, 204, alpha)
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            
            x = start_x + i * dot_spacing
            painter.drawEllipse(x - size//2, center_y - size//2, size, size)
    
    def _draw_bars(self, painter: QPainter, center_x: int, center_y: int):
        """绘制条状动画"""
        bar_count = 5
        bar_width = 4
        bar_spacing = 6
        start_x = center_x - (bar_count * bar_width + (bar_count - 1) * bar_spacing) // 2
        
        for i in range(bar_count):
            # 计算每个条的高度
            phase = (self.animation_step + i * 15) % 60
            height = 10 + phase
            
            color = QColor(0, 122, 204)
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            
            x = start_x + i * (bar_width + bar_spacing)
            y = center_y + 20  # 从中心向下绘制
            painter.drawRect(x, y - height, bar_width, height)
    
    def _draw_message(self, painter: QPainter, center_x: int, center_y: int):
        """绘制消息文本"""
        painter.setPen(QPen(QColor(80, 80, 80)))
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        # 计算文本位置
        text_rect = QRect(center_x - 80, center_y + 50, 160, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.message)


class LoadingOverlay(BaseComponent):
    """加载遮罩层 - 覆盖整个组件的加载指示器"""
    
    def __init__(self, parent=None, config: Optional[ComponentConfig] = None):
        if config is None:
            config = ComponentConfig(
                name="LoadingOverlay",
                theme_support=True,
                auto_save=False
            )
        super().__init__(parent, config)
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建加载指示器
        self.indicator = LoadingIndicator(style=LoadingStyle.SPINNER)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # 设置遮罩样式
        self.setStyleSheet("""
            LoadingOverlay {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 8px;
            }
        """)
        
        # 添加加载指示器
        layout.addWidget(self.indicator)
        
        # 默认隐藏
        self.hide()
    
    def _connect_signals(self):
        """连接信号"""
        self.indicator.loading_complete.connect(self.hide)
    
    def show_loading(self, message: str = "加载中...", target_widget: Optional[QWidget] = None):
        """显示加载遮罩"""
        if target_widget:
            # 覆盖目标组件
            self.setParent(target_widget)
            self.setGeometry(target_widget.rect())
        
        self.indicator.start_loading(message)
        self.show()
        
        # 淡入效果
        self.opacity_effect.setOpacity(0.0)
        self.show()
        
        fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.start()
    
    def update_progress(self, progress: int, message: Optional[str] = None):
        """更新进度"""
        self.indicator.update_progress(progress, message)
    
    def hide_loading(self):
        """隐藏加载遮罩"""
        # 淡出效果
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_out.start()
        
        # 动画完成后隐藏
        QTimer.singleShot(200, self.indicator.stop_loading)
        QTimer.singleShot(200, self.hide)
    
    def _apply_styles(self):
        """应用样式"""
        if self._is_dark_theme:
            self.setStyleSheet("""
                LoadingOverlay {
                    background-color: rgba(0, 0, 0, 0.7);
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                LoadingOverlay {
                    background-color: rgba(255, 255, 255, 0.9);
                    border-radius: 8px;
                }
            """)


class ProgressDialog(QWidget):
    """进度对话框"""
    
    def __init__(self, title: str = "处理中", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        self.title_label = QLabel(self.windowTitle())
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # 消息
        self.message_label = QLabel("正在处理...")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 百分比
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent_label)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        layout.addWidget(self.cancel_btn)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #333333;
            }
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)
    
    def update_progress(self, value: int, message: str = ""):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")
        
        if message:
            self.message_label.setText(message)
    
    def set_title(self, title: str):
        """设置标题"""
        self.setWindowTitle(title)
        self.title_label.setText(title)


# 工厂函数
def create_loading_indicator(parent=None, style: LoadingStyle = LoadingStyle.SPINNER) -> LoadingIndicator:
    """创建加载指示器"""
    return LoadingIndicator(parent, style)


def create_loading_overlay(parent=None) -> LoadingOverlay:
    """创建加载遮罩"""
    return LoadingOverlay(parent)


def create_progress_dialog(title: str = "处理中", parent=None) -> ProgressDialog:
    """创建进度对话框"""
    return ProgressDialog(title, parent)


# 便捷函数
def show_loading_overlay(widget: QWidget, message: str = "加载中...") -> LoadingOverlay:
    """在指定组件上显示加载遮罩"""
    overlay = create_loading_overlay(widget)
    overlay.show_loading(message, widget)
    return overlay


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # 测试窗口
    window = QWidget()
    window.setWindowTitle("加载指示器测试")
    window.resize(400, 300)
    
    layout = QVBoxLayout(window)
    
    # 创建不同样式的加载指示器
    spinner_btn = QPushButton("测试旋转器")
    progress_btn = QPushButton("测试进度条")
    pulse_btn = QPushButton("测试脉冲")
    dots_btn = QPushButton("测试点状")
    bars_btn = QPushButton("测试条状")
    
    layout.addWidget(spinner_btn)
    layout.addWidget(progress_btn)
    layout.addWidget(pulse_btn)
    layout.addWidget(dots_btn)
    layout.addWidget(bars_btn)
    
    # 创建加载遮罩
    overlay = create_loading_overlay(window)
    
    def test_spinner():
        overlay.indicator.style = LoadingStyle.SPINNER
        overlay.show_loading("正在加载数据...")
    
    def test_progress():
        overlay.indicator.style = LoadingStyle.PROGRESS
        overlay.show_loading("正在处理文件...")
        # 模拟进度更新
        for i in range(0, 101, 10):
            QTimer.singleShot(i * 50, lambda v=i: overlay.update_progress(v))
    
    def test_pulse():
        overlay.indicator.style = LoadingStyle.PULSE
        overlay.show_loading("正在连接服务器...")
    
    def test_dots():
        overlay.indicator.style = LoadingStyle.DOTS
        overlay.show_loading("正在同步数据...")
    
    def test_bars():
        overlay.indicator.style = LoadingStyle.BARS
        overlay.show_loading("正在分析内容...")
    
    spinner_btn.clicked.connect(test_spinner)
    progress_btn.clicked.connect(test_progress)
    pulse_btn.clicked.connect(test_pulse)
    dots_btn.clicked.connect(test_dots)
    bars_btn.clicked.connect(test_bars)
    
    window.show()
    sys.exit(app.exec())