#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级专业UI设计系统 - 视频编辑器完整界面组件库
基于Material Design和现代UI/UX最佳实践
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QProgressBar, QSlider, QSpinBox,
    QComboBox, QCheckBox, QRadioButton, QButtonGroup, QGroupBox,
    QLineEdit, QTextEdit, QTabWidget, QSplitter, QStackedWidget,
    QToolButton, QMenuBar, QStatusBar, QToolBar, QDockWidget,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem,
    QApplication, QStyleFactory, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QTimer, pyqtSignal, QObject,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QThread, QMutex, QMutexLocker,
    QBuffer, QIODevice, QByteArray, QPointF, QRectF, QMargins
)
from PyQt6.QtGui import (
    QPainter, QColor, QPalette, QFont, QFontMetrics, QIcon,
    QPixmap, QImage, QBrush, QPen, QLinearGradient, QRadialGradient,
    QConicalGradient, QPainterPath, QTransform, QPolygon,
    QKeySequence, QCursor, QFontDatabase, QTextCharFormat,
    QTextFormat, QDrag, QPixmap, QDragEnterEvent, QDropEvent,
    QWheelEvent, QMouseEvent, QPaintEvent, QResizeEvent
)


class UITheme(Enum):
    """UI主题"""
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


class ProfessionalTheme:
    """专业主题"""
    @staticmethod
    def get_colors(dark_theme=False):
        """获取颜色方案"""
        if dark_theme:
            return {
                'background': '#1e1e1e',
                'surface': '#2d2d2d',
                'primary': '#007acc',
                'primary_hover': '#005a9e',
                'primary_active': '#004080',
                'secondary': '#6c757d',
                'text': '#ffffff',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0',
                'text_disabled': '#666666',
                'border': '#404040',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'card': '#2d2d2d',
                'hover': '#3d3d3d'
            }
        else:
            return {
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'primary': '#007acc',
                'primary_hover': '#005a9e',
                'primary_active': '#004080',
                'secondary': '#6c757d',
                'text': '#212529',
                'text_primary': '#212529',
                'text_secondary': '#6c757d',
                'text_disabled': '#999999',
                'border': '#dee2e6',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'card': '#ffffff',
                'hover': '#f0f0f0'
            }

class ProfessionalButton(QPushButton):
    """专业按钮"""
    def __init__(self, text, button_type="default"):
        super().__init__(text)
        self.button_type = button_type
        self._setup_style()
    
    def _setup_style(self):
        """设置按钮样式"""
        self.setMinimumHeight(40)
        self.setProperty("buttonType", self.button_type)
        
        # 基础样式
        if self.button_type == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    color: #212529;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
                QPushButton:pressed {
                    background-color: #dee2e6;
                }
            """)
    
    def set_theme(self, is_dark_theme):
        """设置主题"""
        colors = ProfessionalTheme.get_colors(is_dark_theme)
        
        if self.button_type == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['primary']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {colors['primary']};
                    opacity: 0.8;
                }}
                QPushButton:pressed {{
                    background-color: {colors['primary']};
                    opacity: 0.6;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 6px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {colors['hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['border']};
                }}
            """)

class ProfessionalCard(QFrame):
    """专业卡片"""
    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self._card_layout = None
        self._setup_style()
        self._setup_layout()
    
    def _setup_style(self):
        """设置卡片样式"""
        self.setObjectName("professionalCard")
        self.setStyleSheet("""
            #professionalCard {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        self.setFrameShape(QFrame.Shape.Box)
    
    def _setup_layout(self):
        """设置布局"""
        # 检查是否已有布局，避免重复
        if self.layout() is not None:
            return
            
        self._card_layout = QVBoxLayout(self)
        self._card_layout.setContentsMargins(16, 16, 16, 16)
        self._card_layout.setSpacing(12)
        
        if self.title:
            title_label = QLabel(self.title)
            title_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 8px;")
            self._card_layout.addWidget(title_label)
    
    def add_content(self, widget):
        """添加内容到卡片"""
        if self._card_layout is not None:
            # 检查widget是否已经有父级
            if widget.parent() is None:
                self._card_layout.addWidget(widget)
            else:
                # 如果widget已经有父级，创建一个容器widget
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.addWidget(widget)
                self._card_layout.addWidget(container)
    
    def add_layout(self, layout):
        """添加布局到卡片"""
        if self._card_layout is not None:
            self._card_layout.addLayout(layout)
    
    @property
    def card_layout(self):
        """获取卡片布局"""
        return self._card_layout
    
    def set_theme(self, is_dark_theme):
        """设置主题"""
        colors = ProfessionalTheme.get_colors(is_dark_theme)
        self.setStyleSheet(f"""
            #professionalCard {{
                background-color: {colors['card']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
        """)

class ProfessionalNavigation(QWidget):
    """专业导航 - 垂直左侧布局"""
    
    # 信号
    navigation_changed = pyqtSignal(str)  # 导航变更信号
    
    def __init__(self):
        super().__init__()
        self.current_page = "home"
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 应用Logo和标题
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 30, 20, 30)
        
        logo_label = QLabel("🎬")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("font-size: 48px;")
        logo_label.setObjectName("navLogo")
        
        title_label = QLabel("CineAIStudio")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        title_label.setObjectName("navTitle")
        
        subtitle_label = QLabel("专业视频编辑")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px;")
        subtitle_label.setObjectName("navSubtitle")
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addSpacing(30)
        
        layout.addLayout(header_layout)
        
        # 导航按钮
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(10)
        
        self.home_btn = self._create_nav_button("🏠", "首页", "home")
        self.projects_btn = self._create_nav_button("📁", "项目管理", "projects")
        self.ai_tools_btn = self._create_nav_button("🤖", "AI工具", "ai_tools")
        self.video_edit_btn = self._create_nav_button("🎥", "视频编辑", "video_edit")
        self.subtitle_btn = self._create_nav_button("📝", "字幕生成", "subtitle")
        self.effects_btn = self._create_nav_button("✨", "特效制作", "effects")
        self.export_btn = self._create_nav_button("📤", "导出分享", "export")
        self.analytics_btn = self._create_nav_button("📊", "数据分析", "analytics")
        
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.projects_btn)
        nav_layout.addWidget(self.ai_tools_btn)
        nav_layout.addWidget(self.video_edit_btn)
        nav_layout.addWidget(self.subtitle_btn)
        nav_layout.addWidget(self.effects_btn)
        nav_layout.addWidget(self.export_btn)
        nav_layout.addWidget(self.analytics_btn)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        
        # 底部设置按钮
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(20, 0, 20, 20)
        
        self.settings_btn = self._create_nav_button("⚙️", "设置", "settings")
        footer_layout.addWidget(self.settings_btn)
        
        layout.addLayout(footer_layout)
        
        # 设置默认选中
        self.home_btn.setChecked(True)
        
        # 连接信号
        self._connect_signals()
    
    def _create_nav_button(self, icon: str, text: str, page_id: str) -> QRadioButton:
        """创建导航按钮"""
        btn = QRadioButton(f"{icon} {text}")
        btn.setProperty("page_id", page_id)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 设置工具提示
        tooltips = {
            "home": "首页 - 欢迎页面和快速访问",
            "projects": "项目管理 - 创建和管理视频项目",
            "ai_tools": "AI工具 - 智能视频分析和处理",
            "video_edit": "视频编辑 - 专业视频编辑功能",
            "subtitle": "字幕生成 - AI驱动的字幕创建和编辑",
            "effects": "特效制作 - 视频特效和滤镜",
            "export": "导出分享 - 多格式导出和分享",
            "analytics": "数据分析 - 视频性能和观众分析",
            "settings": "设置 - 应用程序设置和配置"
        }
        
        btn.setToolTip(tooltips.get(page_id, f"{text}页面"))
        
        # 设置基础样式，颜色由set_theme方法动态设置
        btn.setStyleSheet("""
            QRadioButton {
                padding: 15px 20px;
                border-radius: 8px;
                border: 2px solid transparent;
                font-size: 14px;
                font-weight: 500;
            }
            QRadioButton::indicator {
                width: 0px;
                height: 0px;
            }
        """)
        return btn
    
    def _connect_signals(self):
        """连接信号"""
        buttons = [
            (self.home_btn, "home"),
            (self.projects_btn, "projects"),
            (self.ai_tools_btn, "ai_tools"),
            (self.video_edit_btn, "video_edit"),
            (self.subtitle_btn, "subtitle"),
            (self.effects_btn, "effects"),
            (self.export_btn, "export"),
            (self.analytics_btn, "analytics"),
            (self.settings_btn, "settings")
        ]
        
        for btn, page_id in buttons:
            btn.toggled.connect(lambda checked, pid=page_id: self._on_button_toggled(checked, pid))
    
    def _on_button_toggled(self, checked: bool, page_id: str):
        """按钮切换处理"""
        if checked:
            self.current_page = page_id
            self.navigation_changed.emit(page_id)
    
    def set_active_page(self, page_id: str):
        """设置活动页面"""
        self.current_page = page_id
        
        # 更新按钮状态
        buttons = {
            "home": self.home_btn,
            "projects": self.projects_btn,
            "ai_tools": self.ai_tools_btn,
            "video_edit": self.video_edit_btn,
            "subtitle": self.subtitle_btn,
            "effects": self.effects_btn,
            "export": self.export_btn,
            "analytics": self.analytics_btn,
            "settings": self.settings_btn
        }
        
        if page_id in buttons:
            # 取消所有按钮的选中状态
            for btn in buttons.values():
                btn.setChecked(False)
            
            # 选中指定按钮
            buttons[page_id].setChecked(True)
    
    def set_theme(self, is_dark_theme):
        """设置主题"""
        colors = ProfessionalTheme.get_colors(is_dark_theme)
        
        # 设置导航面板整体样式
        self.setStyleSheet(f"""
            ProfessionalNavigation {{
                background-color: {colors['surface']};
                border-right: 1px solid {colors['border']};
                min-width: 250px;
            }}
            QLabel {{
                color: {colors['text']};
            }}
        """)
        
        # 更新按钮样式 - 确保在深色背景下文字清晰可见
        text_color = colors['text_primary'] if is_dark_theme else colors['text']
        text_selected = '#ffffff'
        hover_color = colors['primary'] if is_dark_theme else 'rgba(0, 122, 204, 0.1)'
        border_color = colors['border']
        
        button_style = f"""
            QRadioButton {{
                padding: 15px 20px;
                border-radius: 8px;
                border: 2px solid {border_color};
                font-size: 14px;
                font-weight: 500;
                color: {text_color};
                background-color: transparent;
                margin: 2px 0;
            }}
            QRadioButton::indicator {{
                width: 0px;
                height: 0px;
            }}
            QRadioButton:checked {{
                background-color: {colors['primary']};
                color: {text_selected} !important;
                border-color: {colors['primary']};
                font-weight: 600;
            }}
            QRadioButton:hover {{
                background-color: {hover_color};
                border-color: {colors['primary']};
            }}
            QRadioButton:checked:hover {{
                background-color: {colors['primary_hover']};
            }}
            QRadioButton:pressed {{
                background-color: {colors['primary_active']};
            }}
        """
        
        # 应用到所有导航按钮
        for btn in self.findChildren(QRadioButton):
            btn.setStyleSheet(button_style)
        
        # 更新标题和副标题颜色
        for label in self.findChildren(QLabel):
            if label.objectName() == "navTitle":
                label.setStyleSheet(f"font-size: 18px; font-weight: bold; margin-bottom: 10px; color: {colors['text_primary']};")
            elif label.objectName() == "navSubtitle":
                label.setStyleSheet(f"font-size: 12px; color: {colors['text_secondary']};")
            elif label.objectName() == "navLogo":
                # Logo保持原样，使用emoji
                pass

class ProfessionalHomePage(QWidget):
    """专业首页"""
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 欢迎标题
        welcome_label = QLabel("欢迎使用 CineAIStudio")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(welcome_label)
        
        # 功能卡片
        features_layout = QHBoxLayout()
        
        ai_card = ProfessionalCard("AI功能")
        ai_card.add_content(QLabel("智能视频编辑和分析"))
        
        video_card = ProfessionalCard("视频编辑")
        video_card.add_content(QLabel("专业视频编辑工具"))
        
        export_card = ProfessionalCard("导出分享")
        export_card.add_content(QLabel("多格式导出和分享"))
        
        features_layout.addWidget(ai_card)
        features_layout.addWidget(video_card)
        features_layout.addWidget(export_card)
        
        layout.addLayout(features_layout)
        layout.addStretch()
    
    def set_theme(self, is_dark_theme):
        """设置主题"""
        colors = ProfessionalTheme.get_colors(is_dark_theme)
        self.setStyleSheet(f"""
            ProfessionalHomePage {{
                background-color: {colors['background']};
            }}
            QLabel {{
                color: {colors['text']};
            }}
        """)

class ColorScheme:
    """颜色方案"""
    
    # 深色主题 - 视频编辑器专业配色
    DARK_THEME = {
        # 主要颜色
        "primary": "#00BCD4",           # 青色主色调
        "primary_dark": "#0097A7",      # 深主色
        "primary_light": "#B2EBF2",     # 浅主色
        
        # 视频编辑专用颜色
        "video_bg": "#1A1A1A",          # 视频背景
        "timeline_bg": "#0D0D0D",       # 时间线背景
        "timeline_track": "#2A2A2A",    # 时间线轨道
        "timeline_playhead": "#FF4081",  # 播放头
        
        # 背景颜色
        "background": "#121212",        # 主背景
        "surface": "#1E1E1E",          # 表面背景
        "surface_variant": "#2D2D2D",   # 变体表面
        "card": "#1A1A1A",             # 卡片背景
        "dialog": "#242424",           # 对话框背景
        
        # 文字颜色
        "text_primary": "#FFFFFF",      # 主要文字
        "text_secondary": "#B0BEC5",    # 次要文字
        "text_disabled": "#607D8B",     # 禁用文字
        "text_hint": "#90A4AE",        # 提示文字
        
        # 边框颜色
        "border": "#333333",           # 普通边框
        "border_focus": "#00BCD4",      # 焦点边框
        "border_error": "#F44336",      # 错误边框
        "border_success": "#4CAF50",    # 成功边框
        
        # 状态颜色
        "success": "#4CAF50",           # 成功
        "warning": "#FF9800",           # 警告
        "error": "#F44336",             # 错误
        "info": "#2196F3",              # 信息
        
        # 特殊颜色
        "shadow": "rgba(0, 0, 0, 0.4)", # 阴影
        "overlay": "rgba(0, 0, 0, 0.6)", # 遮罩
        "highlight": "rgba(0, 188, 212, 0.2)",  # 高亮
        "selection": "rgba(0, 188, 212, 0.3)",  # 选择
    }
    
    # 浅色主题
    LIGHT_THEME = {
        # 主要颜色
        "primary": "#00BCD4",
        "primary_dark": "#0097A7",
        "primary_light": "#B2EBF2",
        
        # 视频编辑专用颜色
        "video_bg": "#F5F5F5",
        "timeline_bg": "#EEEEEE",
        "timeline_track": "#E0E0E0",
        "timeline_playhead": "#FF4081",
        
        # 背景颜色
        "background": "#FAFAFA",
        "surface": "#FFFFFF",
        "surface_variant": "#F5F5F5",
        "card": "#FFFFFF",
        "dialog": "#FFFFFF",
        
        # 文字颜色
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "text_disabled": "#BDBDBD",
        "text_hint": "#9E9E9E",
        
        # 边框颜色
        "border": "#E0E0E0",
        "border_focus": "#00BCD4",
        "border_error": "#F44336",
        "border_success": "#4CAF50",
        
        # 状态颜色
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "info": "#2196F3",
        
        # 特殊颜色
        "shadow": "rgba(0, 0, 0, 0.1)",
        "overlay": "rgba(0, 0, 0, 0.3)",
        "highlight": "rgba(0, 188, 212, 0.1)",
        "selection": "rgba(0, 188, 212, 0.2)",
    }


class FontScheme:
    """字体方案"""
    
    # 字体家族 - 专业的视频编辑器字体
    PRIMARY_FONT = "Arial"       # 主要字体
    SECONDARY_FONT = "Helvetica"    # 次要字体
    MONOSPACE_FONT = "Courier New"  # 等宽字体
    
    # 字体大小
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 18
    FONT_SIZE_2XL = 20
    FONT_SIZE_3XL = 24
    
    # 字体权重
    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMI_BOLD = 600
    WEIGHT_BOLD = 700
    
    # 行高
    LINE_HEIGHT_NORMAL = 1.5


class SpacingScheme:
    """间距方案"""
    
    # 基础间距
    UNIT = 8
    
    # 边距
    MARGIN_SM = UNIT * 2     # 16px
    MARGIN_MD = UNIT * 3     # 24px
    MARGIN_LG = UNIT * 4     # 32px
    
    # 内边距
    PADDING_SM = UNIT * 2    # 16px
    PADDING_MD = UNIT * 3    # 24px
    PADDING_LG = UNIT * 4    # 32px
    
    # 圆角
    RADIUS_SM = 6
    RADIUS_MD = 8
    RADIUS_LG = 12
    
    # 间隙
    GAP_SM = UNIT
    GAP_MD = UNIT * 2
    GAP_LG = UNIT * 3
    
    # 阴影 (QSS中不支持，保留用于其他用途)
    SHADOW_SM = "0 2px 4px rgba(0,0,0,0.15)"
    SHADOW_MD = "0 4px 8px rgba(0,0,0,0.2)"
    SHADOW_LG = "0 8px 16px rgba(0,0,0,0.25)"
    
    # 动画时长 (QSS中不支持，保留用于其他用途)
    ANIMATION_NORMAL = 300   # 毫秒


class ProfessionalStyleEngine:
    """专业样式引擎"""
    
    def __init__(self, theme: UITheme = UITheme.DARK):
        self.theme = theme
        self.colors = ColorScheme.DARK_THEME if theme == UITheme.DARK else ColorScheme.LIGHT_THEME
        self.fonts = FontScheme()
        self.spacing = SpacingScheme()
        
        # 应用全局样式
        self._apply_global_styles()
    
    def _apply_global_styles(self):
        """应用全局样式"""
        app = QApplication.instance()
        
        # 设置应用程序字体
        font = QFont(self.fonts.PRIMARY_FONT)
        font.setPointSize(self.fonts.FONT_SIZE_MD)
        font.setWeight(self.fonts.WEIGHT_REGULAR)
        app.setFont(font)
        
        # 应用样式表
        stylesheet = self._generate_stylesheet()
        app.setStyleSheet(stylesheet)
    
    def _generate_stylesheet(self) -> str:
        """生成样式表 - 兼容 PyQt6 QSS"""
        # 预计算所有值以避免f-string中的复杂表达式
        primary_font = self.fonts.PRIMARY_FONT
        secondary_font = self.fonts.SECONDARY_FONT
        font_size_md = self.fonts.FONT_SIZE_MD
        font_size_sm = self.fonts.FONT_SIZE_SM
        font_size_lg = self.fonts.FONT_SIZE_LG
        font_size_xl = self.fonts.FONT_SIZE_XL
        font_size_2xl = self.fonts.FONT_SIZE_2XL
        font_size_3xl = self.fonts.FONT_SIZE_3XL
        weight_regular = self.fonts.WEIGHT_REGULAR
        weight_medium = self.fonts.WEIGHT_MEDIUM
        weight_semi_bold = self.fonts.WEIGHT_SEMI_BOLD
        weight_bold = self.fonts.WEIGHT_BOLD
        line_height_normal = self.fonts.LINE_HEIGHT_NORMAL
        
        # 颜色
        background = self.colors['background']
        surface = self.colors['surface']
        card = self.colors['card']
        text_primary = self.colors['text_primary']
        text_secondary = self.colors['text_secondary']
        text_disabled = self.colors['text_disabled']
        border = self.colors['border']
        border_focus = self.colors['border_focus']
        primary = self.colors['primary']
        primary_dark = self.colors['primary_dark']
        primary_light = self.colors['primary_light']
        error = self.colors['error']
        highlight = self.colors['highlight']
        
        # 间距
        radius_md = self.spacing.RADIUS_MD
        radius_sm = self.spacing.RADIUS_SM
        radius_lg = self.spacing.RADIUS_LG
        padding_md = self.spacing.PADDING_MD
        padding_sm = self.spacing.PADDING_SM
        padding_lg = self.spacing.PADDING_LG
        margin_sm = self.spacing.MARGIN_SM
        
        # 计算间距值
        padding_lg_sm = padding_lg + padding_sm
        padding_md_sm = padding_md + padding_sm
        
        return f"""
        /* 全局样式 */
        QWidget {{
            background-color: {background};
            color: {text_primary};
            font-size: {font_size_md}px;
            font-family: '{primary_font}', '{secondary_font}', sans-serif;
        }}
        
        /* 按钮样式 */
        QPushButton {{
            background-color: {primary};
            color: {text_primary};
            border: none;
            border-radius: {radius_md}px;
            padding: {padding_md}px {padding_lg}px;
            font-weight: {weight_medium};
            font-size: {font_size_md}px;
            min-height: {padding_lg_sm}px;
        }}
        
        QPushButton:hover {{
            background-color: {primary_dark};
        }}
        
        QPushButton:pressed {{
            background-color: {primary_light};
        }}
        
        QPushButton:disabled {{
            background-color: {border};
            color: {text_disabled};
        }}
        
        /* 次要按钮 */
        QPushButton.secondary {{
            background-color: transparent;
            border: 2px solid {primary};
            color: {primary};
        }}
        
        QPushButton.secondary:hover {{
            background-color: {primary};
            color: {text_primary};
        }}
        
        /* 输入框样式 */
        QLineEdit, QTextEdit {{
            background-color: {surface};
            border: 2px solid {border};
            border-radius: {radius_md}px;
            padding: {padding_md}px;
            color: {text_primary};
            font-size: {font_size_md}px;
        }}
        
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {border_focus};
        }}
        
        /* 标签样式 */
        QLabel {{
            color: {text_primary};
            font-size: {font_size_md}px;
            font-weight: {weight_regular};
        }}
        
        QLabel.heading {{
            font-size: {font_size_3xl}px;
            font-weight: {weight_bold};
            color: {text_primary};
            margin-bottom: {margin_sm}px;
        }}
        
        QLabel.subheading {{
            font-size: {font_size_2xl}px;
            font-weight: {weight_semi_bold};
            color: {text_primary};
            margin-bottom: {margin_sm}px;
        }}
        
        /* 卡片样式 */
        QFrame.card {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: {radius_lg}px;
            padding: {padding_lg}px;
        }}
        
        /* 进度条样式 */
        QProgressBar {{
            border: none;
            background: {border};
            border-radius: {radius_sm}px;
            text-align: center;
            color: {text_primary};
            font-weight: {weight_medium};
            height: 8px;
        }}
        
        QProgressBar::chunk {{
            background: {primary};
            border-radius: {radius_sm}px;
        }}
        
        /* 滑块样式 */
        QSlider::groove:horizontal {{
            height: 6px;
            background: {border};
            border-radius: 3px;
            margin: 0;
        }}
        
        QSlider::handle:horizontal {{
            background: {primary};
            border: 2px solid {primary};
            width: 20px;
            height: 20px;
            border-radius: 10px;
            margin: -7px 0;
        }}
        
        /* 选项卡样式 */
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: {radius_md}px;
            background: {surface};
            padding: {padding_md}px;
        }}
        
        QTabBar::tab {{
            background: {surface};
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: {radius_md}px;
            border-top-right-radius: {radius_md}px;
            padding: {padding_md}px {padding_lg}px;
            margin-right: 2px;
            font-weight: {weight_medium};
        }}
        
        QTabBar::tab:selected {{
            background: {card};
            border-color: {primary};
            border-bottom: 2px solid {primary};
            color: {primary};
        }}
        """
    
    def get_color(self, name: str) -> str:
        """获取颜色"""
        return self.colors.get(name, "#000000")
    
    def get_font(self, size: int = FontScheme.FONT_SIZE_MD, weight: int = FontScheme.WEIGHT_REGULAR) -> QFont:
        """获取字体"""
        font = QFont(self.fonts.PRIMARY_FONT)
        font.setPointSize(size)
        font.setWeight(weight)
        return font
    
    def get_spacing(self, name: str) -> int:
        """获取间距"""
        return getattr(self.spacing, name.upper(), 8)
    
    def set_theme(self, theme: UITheme):
        """设置主题"""
        self.theme = theme
        self.colors = ColorScheme.DARK_THEME if theme == UITheme.DARK else ColorScheme.LIGHT_THEME
        self._apply_global_styles()


# 组件工厂函数
def create_style_engine(theme: UITheme = UITheme.DARK) -> ProfessionalStyleEngine:
    """创建样式引擎"""
    return ProfessionalStyleEngine(theme)


def get_color(color_name: str, theme: UITheme = UITheme.DARK) -> str:
    """获取颜色"""
    colors = ColorScheme.DARK_THEME if theme == UITheme.DARK else ColorScheme.LIGHT_THEME
    return colors.get(color_name, "#000000")


def create_font(size: int = FontScheme.FONT_SIZE_MD, weight: int = FontScheme.WEIGHT_REGULAR) -> QFont:
    """创建字体"""
    font = QFont(FontScheme.PRIMARY_FONT)
    font.setPointSize(size)
    font.setWeight(weight)
    return font


def add_shadow_effect(widget: QWidget, shadow_type: str = "medium"):
    """添加阴影效果"""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(0, 0, 0, 50))
    shadow.setOffset(0, 2)
    widget.setGraphicsEffect(shadow)