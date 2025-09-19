#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from app.core.project_manager import ProjectManager
from app.ai import AIManager


class FeatureCard(QWidget):
    """功能卡片组件"""

    clicked = pyqtSignal(str)  # 功能ID

    def __init__(self, feature_id: str, title: str, description: str, icon: str = "", parent=None):
        super().__init__(parent)

        self.feature_id = feature_id
        self.setFixedSize(280, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_ui(title, description, icon)
        self._apply_styles()

    def _setup_ui(self, title: str, description: str, icon: str):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 图标
        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Arial", 32))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("card_title")
        layout.addWidget(title_label)

        # 描述
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 12))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("card_description")
        layout.addWidget(desc_label)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            FeatureCard {
                background-color: #ffffff;
                border: 1px solid #f0f0f0;
                border-radius: 12px;
            }

            FeatureCard:hover {
                border-color: #1890ff;
                background-color: #f0f9ff;
            }

            QLabel#card_title {
                color: #262626;
                font-weight: 600;
            }

            QLabel#card_description {
                color: #595959;
                line-height: 1.4;
            }
        """)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.feature_id)
        super().mousePressEvent(event)


class QuickStatsWidget(QWidget):
    """快速统计组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # 统计项目
        stats = [
            ("项目数量", "0", "🎬"),
            ("视频文件", "0", "📹"),
            ("AI处理", "0", "🤖"),
            ("导出视频", "0", "📤")
        ]

        for title, value, icon in stats:
            stat_widget = self._create_stat_item(title, value, icon)
            layout.addWidget(stat_widget)

    def _create_stat_item(self, title: str, value: str, icon: str) -> QWidget:
        """创建统计项目"""
        widget = QWidget()
        widget.setFixedSize(120, 80)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # 图标和数值
        top_layout = QHBoxLayout()

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 20))
        top_layout.addWidget(icon_label)

        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        value_label.setObjectName("stat_value")
        top_layout.addWidget(value_label)

        layout.addLayout(top_layout)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 11))
        title_label.setObjectName("stat_title")
        layout.addWidget(title_label)

        # 样式
        widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #f0f0f0;
                border-radius: 8px;
            }

            QLabel#stat_value {
                color: #1890ff;
                font-weight: 600;
            }

            QLabel#stat_title {
                color: #595959;
            }
        """)

        return widget


class HomePage(QWidget):
    """首页组件"""

    feature_requested = pyqtSignal(str)  # 功能请求信号

    def __init__(self, project_manager: ProjectManager, ai_manager: AIManager, parent=None):
        super().__init__(parent)

        self.project_manager = project_manager
        self.ai_manager = ai_manager

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 主内容
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(32)

        # 欢迎区域
        welcome_section = self._create_welcome_section()
        layout.addWidget(welcome_section)

        # 快速统计
        stats_section = self._create_stats_section()
        layout.addWidget(stats_section)

        # 核心功能
        features_section = self._create_features_section()
        layout.addWidget(features_section)

        # 快速操作
        actions_section = self._create_actions_section()
        layout.addWidget(actions_section)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

    def _create_welcome_section(self) -> QWidget:
        """创建欢迎区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(16)

        # 主标题
        title = QLabel("欢迎使用 CineAIStudio")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("welcome_title")
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("AI驱动的短剧视频编辑器，让创作更简单")
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("welcome_subtitle")
        layout.addWidget(subtitle)

        # 样式
        section.setStyleSheet("""
            QLabel#welcome_title {
                color: #1890ff;
                margin: 20px 0px;
            }

            QLabel#welcome_subtitle {
                color: #595959;
                margin-bottom: 20px;
            }
        """)

        return section

    def _create_stats_section(self) -> QWidget:
        """创建统计区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(16)

        # 标题
        title = QLabel("项目概览")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setObjectName("section_title")
        layout.addWidget(title)

        # 统计组件
        self.stats_widget = QuickStatsWidget()
        layout.addWidget(self.stats_widget)

        return section

    def _create_features_section(self) -> QWidget:
        """创建功能区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(20)

        # 标题
        title = QLabel("核心AI功能")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setObjectName("section_title")
        layout.addWidget(title)

        # 功能卡片网格
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # 功能卡片
        features = [
            ("ai_commentary", "AI短剧解说", "智能生成解说内容并同步到视频", "🎬"),
            ("ai_compilation", "AI高能混剪", "自动检测精彩片段并生成混剪", "⚡"),
            ("ai_monologue", "AI第一人称独白", "生成第一人称叙述内容", "🎭"),
            ("video_management", "视频管理", "管理和组织您的视频项目", "📁")
        ]

        for i, (feature_id, title, desc, icon) in enumerate(features):
            card = FeatureCard(feature_id, title, desc, icon)
            card.clicked.connect(self.feature_requested.emit)

            row = i // 2
            col = i % 2
            grid_layout.addWidget(card, row, col)

        layout.addLayout(grid_layout)

        return section

    def _create_actions_section(self) -> QWidget:
        """创建快速操作区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(16)

        # 标题
        title = QLabel("快速操作")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setObjectName("section_title")
        layout.addWidget(title)

        # 操作按钮
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)

        # 新建项目
        new_project_btn = QPushButton("📁 新建项目")
        new_project_btn.setObjectName("primary_button")
        new_project_btn.setMinimumHeight(44)
        new_project_btn.setFont(QFont("Arial", 14))
        actions_layout.addWidget(new_project_btn)

        # 导入视频
        import_video_btn = QPushButton("📹 导入视频")
        import_video_btn.setMinimumHeight(44)
        import_video_btn.setFont(QFont("Arial", 14))
        actions_layout.addWidget(import_video_btn)

        # 打开设置
        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.setMinimumHeight(44)
        settings_btn.setFont(QFont("Arial", 14))
        actions_layout.addWidget(settings_btn)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        return section

    def _connect_signals(self):
        """连接信号"""
        # 这里可以连接项目管理器的信号来更新统计信息
        pass
