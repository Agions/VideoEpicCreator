"""
Ant Design 风格仪表板
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .widgets.ant_cards import AntCard, CardMeta, CardContent
from .widgets.ant_buttons import PrimaryButton, TextButton
from .widgets.ant_inputs import AntInput
from .styles.ant_design import theme_manager

class AntDashboard(QWidget):
    """Ant Design 风格仪表板"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # 标题区域
        self._create_header(main_layout)

        # 统计卡片区域
        self._create_stats_cards(main_layout)

        # 项目和活动区域
        self._create_projects_and_activities(main_layout)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_header(self, layout):
        """创建标题区域"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title_label = QLabel("仪表板")
        title_font = QFont()
        title_font.setPixelSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)

        # 搜索框
        search_input = AntInput()
        search_input.setPlaceholderText("搜索项目...")
        search_input.setFixedWidth(300)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(search_input)

        layout.addWidget(header_widget)

    def _create_stats_cards(self, layout):
        """创建统计卡片"""
        # 统计卡片网格
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        # 创建统计卡片
        stats_data = [
            {"title": "总项目数", "value": "24", "description": "较上月增加 12%"},
            {"title": "视频时长", "value": "142h", "description": "较上月增加 8%"},
            {"title": "AI生成内容", "value": "1,248", "description": "较上月增加 23%"},
            {"title": "用户满意度", "value": "98%", "description": "较上月增加 3%"}
        ]

        for i, data in enumerate(stats_data):
            card = AntCard()
            card.setBordered(True)

            # 卡片内容
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 24, 24, 24)
            card_layout.setSpacing(16)

            # 标题
            title_label = QLabel(data["title"])
            title_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary').name()};")

            # 数值
            value_label = QLabel(data["value"])
            value_font = QFont()
            value_font.setPixelSize(32)
            value_font.setBold(True)
            value_label.setFont(value_font)

            # 描述
            desc_label = QLabel(data["description"])
            desc_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary').name()};")

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addWidget(desc_label)
            card_layout.addStretch()

            # 添加到网格
            row = i // 2
            col = i % 2
            stats_grid.addWidget(card, row, col)

        layout.addLayout(stats_grid)

    def _create_projects_and_activities(self, layout):
        """创建项目和活动区域"""
        # 创建水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        # 最近项目卡片
        projects_card = self._create_recent_projects_card()
        content_layout.addWidget(projects_card, 2)

        # 最近活动卡片
        activities_card = self._create_recent_activities_card()
        content_layout.addWidget(activities_card, 1)

        layout.addLayout(content_layout)

    def _create_recent_projects_card(self):
        """创建最近项目卡片"""
        card = AntCard()
        card.setBordered(True)

        # 卡片布局
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 卡片头部
        header = CardMeta("最近项目", "您最近创建的项目")
        card_layout.addWidget(header)

        # 项目列表
        projects_widget = QWidget()
        projects_layout = QVBoxLayout(projects_widget)
        projects_layout.setContentsMargins(24, 0, 24, 24)
        projects_layout.setSpacing(16)

        # 项目数据
        projects_data = [
            {"name": "产品宣传视频", "date": "2024-01-15", "status": "已完成"},
            {"name": "教程系列", "date": "2024-01-10", "status": "进行中"},
            {"name": "品牌故事", "date": "2024-01-05", "status": "待开始"},
            {"name": "社交媒体内容", "date": "2024-01-01", "status": "已完成"}
        ]

        for project in projects_data:
            project_item = self._create_project_item(project)
            projects_layout.addWidget(project_item)

        card_layout.addWidget(projects_widget)

        return card

    def _create_project_item(self, project_data):
        """创建项目项"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)

        # 项目名称
        name_label = QLabel(project_data["name"])
        name_label.setFont(theme_manager.get_font("base"))

        # 日期
        date_label = QLabel(project_data["date"])
        date_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary').name()};")
        date_label.setFont(theme_manager.get_font("sm"))

        # 状态
        status_label = QLabel(project_data["status"])
        status_label.setFont(theme_manager.get_font("sm"))

        # 根据状态设置颜色
        theme = theme_manager.get_current_theme()
        if project_data["status"] == "已完成":
            status_label.setStyleSheet(f"color: {theme.success_color.name()};")
        elif project_data["status"] == "进行中":
            status_label.setStyleSheet(f"color: {theme.primary_color.name()};")
        else:
            status_label.setStyleSheet(f"color: {theme.text_color_secondary.name()};")

        item_layout.addWidget(name_label)
        item_layout.addStretch()
        item_layout.addWidget(date_label)
        item_layout.addWidget(status_label)

        return item_widget

    def _create_recent_activities_card(self):
        """创建最近活动卡片"""
        card = AntCard()
        card.setBordered(True)

        # 卡片布局
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 卡片头部
        header = CardMeta("最近活动", "系统最近的活动记录")
        card_layout.addWidget(header)

        # 活动列表
        activities_widget = QWidget()
        activities_layout = QVBoxLayout(activities_widget)
        activities_layout.setContentsMargins(24, 0, 24, 24)
        activities_layout.setSpacing(16)

        # 活动数据
        activities_data = [
            {"action": "创建了新项目", "target": "产品宣传视频", "time": "2小时前"},
            {"action": "完成了视频渲染", "target": "教程系列#3", "time": "5小时前"},
            {"action": "AI生成了脚本", "target": "品牌故事", "time": "1天前"},
            {"action": "导出了视频", "target": "社交媒体内容", "time": "2天前"}
        ]

        for activity in activities_data:
            activity_item = self._create_activity_item(activity)
            activities_layout.addWidget(activity_item)

        card_layout.addWidget(activities_widget)

        return card

    def _create_activity_item(self, activity_data):
        """创建活动项"""
        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(4)

        # 活动描述
        desc_label = QLabel(f"{activity_data['action']} \"{activity_data['target']}\"")
        desc_label.setFont(theme_manager.get_font("base"))

        # 时间
        time_label = QLabel(activity_data["time"])
        time_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary').name()};")
        time_label.setFont(theme_manager.get_font("sm"))

        item_layout.addWidget(desc_label)
        item_layout.addWidget(time_label)

        return item_widget

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置背景色
        self.setStyleSheet(f"background-color: {theme.background_color.name()};")
