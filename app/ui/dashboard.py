"""
Dashboard component for VideoEpicCreator
Main dashboard with statistics, recent projects, and quick actions
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap


class Dashboard(QWidget):
    """仪表板组件"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("dashboard")
        self.init_ui()
        
    def init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题区域
        title_widget = self.create_title_widget()
        layout.addWidget(title_widget)
        
        # 统计卡片
        stats_widget = self.create_stats_widget()
        layout.addWidget(stats_widget)
        
        # 主要内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 最近项目
        recent_projects_widget = self.create_recent_projects_widget()
        content_layout.addWidget(recent_projects_widget, 2)
        
        # 快速操作和活动动态
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        
        # 快速操作
        quick_actions_widget = self.create_quick_actions_widget()
        right_layout.addWidget(quick_actions_widget)
        
        # 活动动态
        activity_widget = self.create_activity_widget()
        right_layout.addWidget(activity_widget)
        
        content_layout.addWidget(right_widget, 1)
        layout.addLayout(content_layout)
        
        # 系统状态
        system_status_widget = self.create_system_status_widget()
        layout.addWidget(system_status_widget)
        
        layout.addStretch()
        
    def create_title_widget(self):
        """创建标题区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("仪表板")
        title_label.setObjectName("dashboard_title")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        """)
        
        subtitle_label = QLabel("欢迎回来！以下是您的项目概览")
        subtitle_label.setStyleSheet("""
            font-size: 16px;
            color: #666;
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        
        return widget
        
    def create_stats_widget(self):
        """创建统计卡片区域"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(16)
        
        # 统计数据
        stats_data = [
            ("总项目数", "12", "📁", "#1890ff"),
            ("本月完成", "5", "🚀", "#52c41a"),
            ("进行中", "3", "⏰", "#faad14"),
            ("总时长", "2h 45m", "🎬", "#722ed1"),
        ]
        
        self.stats_cards = []
        
        for i, (title, value, icon, color) in enumerate(stats_data):
            card = StatCard(title, value, icon, color)
            layout.addWidget(card, i // 2, i % 2)
            self.stats_cards.append(card)
            
        return widget
        
    def create_recent_projects_widget(self):
        """创建最近项目区域"""
        widget = QFrame()
        widget.setObjectName("recent_projects_widget")
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e8e8e8;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题和按钮
        header_layout = QHBoxLayout()
        
        title_label = QLabel("最近项目")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
        """)
        
        new_project_btn = QPushButton("新建项目")
        new_project_btn.setObjectName("primary_button")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(new_project_btn)
        
        layout.addLayout(header_layout)
        
        # 项目列表
        projects_data = [
            ("旅行_vlog_2024", "旅行视频", "12:34", "已完成", "2小时前", "📹"),
            ("产品演示视频", "商业视频", "08:45", "编辑中", "1天前", "🎬"),
            ("教程系列_第1集", "教育视频", "15:20", "进行中", "3天前", "📚"),
            ("活动精彩集锦", "活动记录", "06:30", "已完成", "1周前", "🎪"),
        ]
        
        for project in projects_data:
            project_item = ProjectItem(*project)
            layout.addWidget(project_item)
            
        layout.addStretch()
        
        return widget
        
    def create_quick_actions_widget(self):
        """创建快速操作区域"""
        widget = QFrame()
        widget.setObjectName("quick_actions_widget")
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e8e8e8;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("快速操作")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
        """)
        layout.addWidget(title_label)
        
        # 快速操作按钮
        actions = [
            ("新建视频项目", "➕", "primary_button"),
            ("AI 内容生成", "🚀", "secondary_button"),
            ("导入媒体文件", "📁", "secondary_button"),
            ("应用模板", "📊", "secondary_button"),
        ]
        
        for text, icon, style in actions:
            btn = QPushButton(f"{icon} {text}")
            btn.setObjectName(style)
            btn.setMinimumHeight(45)
            layout.addWidget(btn)
            
        return widget
        
    def create_activity_widget(self):
        """创建活动动态区域"""
        widget = QFrame()
        widget.setObjectName("activity_widget")
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e8e8e8;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("活动动态")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
        """)
        layout.addWidget(title_label)
        
        # 活动列表
        activities = [
            ("完成了 \"夏季旅行\" 视频项目", "2小时前", "✅"),
            ("为 \"产品评测\" 生成了 AI 旁白", "5小时前", "ℹ️"),
            ("更新了 \"教程系列\" 项目", "1天前", "⚠️"),
            ("导出了 \"活动集锦\" 4K 版本", "2天前", "✅"),
        ]
        
        for action, time, icon in activities:
            activity_item = ActivityItem(action, time, icon)
            layout.addWidget(activity_item)
            
        layout.addStretch()
        
        return widget
        
    def create_system_status_widget(self):
        """创建系统状态区域"""
        widget = QFrame()
        widget.setObjectName("system_status_widget")
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e8e8e8;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("系统状态")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
        """)
        layout.addWidget(title_label)
        
        # 系统状态项
        status_items = [
            ("CPU 使用率", 65),
            ("内存使用", 78),
            ("磁盘空间", 45),
        ]
        
        for label, value in status_items:
            status_item = SystemStatusItem(label, value)
            layout.addWidget(status_item)
            
        return widget


class StatCard(QFrame):
    """统计卡片组件"""
    
    def __init__(self, title, value, icon, color):
        super().__init__()
        self.setObjectName("stat_card")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e8e8e8;
                padding: 20px;
            }}
            QFrame:hover {{
                border-color: {color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 图标和值
        value_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            color: {color};
        """)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {color};
        """)
        
        value_layout.addWidget(icon_label)
        value_layout.addStretch()
        value_layout.addWidget(value_label)
        
        layout.addLayout(value_layout)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            color: #666;
        """)
        layout.addWidget(title_label)


class ProjectItem(QFrame):
    """项目项组件"""
    
    def __init__(self, name, type_name, duration, status, time, icon):
        super().__init__()
        self.setObjectName("project_item")
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 6px;
                border: 1px solid #e8e8e8;
                padding: 15px;
                margin-bottom: 10px;
            }
            QFrame:hover {
                background-color: #f0f0f0;
                border-color: #1890ff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            font-size: 24px;
            background-color: #f0f0f0;
            border-radius: 12px;
            padding: 8px;
        """)
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 项目信息
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(10, 0, 0, 0)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333;
        """)
        
        details_layout = QHBoxLayout()
        details_layout.setSpacing(15)
        
        type_label = QLabel(type_name)
        type_label.setStyleSheet("color: #666; font-size: 12px;")
        
        duration_label = QLabel(f"时长: {duration}")
        duration_label.setStyleSheet("color: #666; font-size: 12px;")
        
        time_label = QLabel(time)
        time_label.setStyleSheet("color: #666; font-size: 12px;")
        
        details_layout.addWidget(type_label)
        details_layout.addWidget(duration_label)
        details_layout.addWidget(time_label)
        
        info_layout.addWidget(name_label)
        info_layout.addLayout(details_layout)
        
        # 状态和操作按钮
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        status_label = QLabel(status)
        status_label.setStyleSheet(f"""
            background-color: {self.get_status_color(status)};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        """)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("secondary_button")
        edit_btn.setFixedSize(60, 30)
        
        play_btn = QPushButton("播放")
        play_btn.setObjectName("primary_button")
        play_btn.setFixedSize(60, 30)
        
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(play_btn)
        
        right_layout.addWidget(status_label)
        right_layout.addLayout(buttons_layout)
        
        layout.addWidget(icon_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(right_layout)
        
    def get_status_color(self, status):
        """获取状态颜色"""
        colors = {
            "已完成": "#52c41a",
            "编辑中": "#1890ff",
            "进行中": "#faad14",
        }
        return colors.get(status, "#d9d9d9")


class ActivityItem(QFrame):
    """活动项组件"""
    
    def __init__(self, action, time, icon):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px 0;
                border-bottom: 1px solid #f0f0f0;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px;")
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 活动信息
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(10, 0, 0, 0)
        
        action_label = QLabel(action)
        action_label.setStyleSheet("""
            font-size: 14px;
            color: #333;
        """)
        
        time_label = QLabel(time)
        time_label.setStyleSheet("""
            font-size: 12px;
            color: #999;
        """)
        
        info_layout.addWidget(action_label)
        info_layout.addWidget(time_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(info_layout)
        layout.addStretch()


class SystemStatusItem(QFrame):
    """系统状态项组件"""
    
    def __init__(self, label, value):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px 0;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            font-size: 14px;
            color: #333;
            font-weight: 500;
        """)
        
        layout.addWidget(label_widget)
        layout.addStretch()
        
        # 进度条
        from PyQt6.QtWidgets import QProgressBar
        progress_bar = QProgressBar()
        progress_bar.setValue(value)
        progress_bar.setFixedWidth(200)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 20px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #1890ff;
                border-radius: 3px;
            }
        """)
        
        layout.addWidget(progress_bar)