"""
Sidebar navigation component for VideoEpicCreator
Left sidebar with navigation menu and user info
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap


class Sidebar(QWidget):
    """侧边栏组件"""
    
    # 信号定义
    navigation_clicked = pyqtSignal(str)
    settings_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setFixedWidth(250)
        self.setObjectName("sidebar")
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo区域
        logo_widget = self.create_logo_widget()
        layout.addWidget(logo_widget)
        
        # 导航菜单
        nav_widget = self.create_navigation_widget()
        layout.addWidget(nav_widget)
        
        # 底部用户信息
        user_widget = self.create_user_widget()
        layout.addWidget(user_widget)
        
        # 添加弹性空间
        layout.addStretch()
        
    def create_logo_widget(self):
        """创建Logo区域"""
        widget = QFrame()
        widget.setObjectName("logo_widget")
        widget.setFixedHeight(80)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Logo标签
        logo_label = QLabel("VEC")
        logo_label.setObjectName("logo_label")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(logo_label)
        
        return widget
        
    def create_navigation_widget(self):
        """创建导航菜单"""
        widget = QFrame()
        widget.setObjectName("nav_widget")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)
        
        # 导航按钮
        nav_items = [
            ("dashboard", "📊", "仪表板"),
            ("projects", "📁", "项目"),
            ("editor", "🎬", "视频编辑"),
            ("ai_studio", "🤖", "AI工作室"),
            ("import", "📥", "导入"),
            ("export", "📤", "导出"),
        ]
        
        self.nav_buttons = {}
        
        for item_id, icon, text in nav_items:
            btn = NavigationButton(icon, text)
            btn.clicked.connect(lambda checked, id=item_id: self.on_nav_clicked(id))
            layout.addWidget(btn)
            self.nav_buttons[item_id] = btn
            
        # 默认选中仪表板
        self.nav_buttons["dashboard"].set_active(True)
        
        return widget
        
    def create_user_widget(self):
        """创建用户信息区域"""
        widget = QFrame()
        widget.setObjectName("user_widget")
        widget.setFixedHeight(80)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 用户头像
        avatar_label = QLabel("👤")
        avatar_label.setObjectName("avatar_label")
        avatar_label.setFixedSize(40, 40)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 用户信息
        user_info_layout = QVBoxLayout()
        user_info_layout.setContentsMargins(10, 0, 0, 0)
        
        username_label = QLabel("用户")
        username_label.setObjectName("username_label")
        
        user_type_label = QLabel("免费用户")
        user_type_label.setObjectName("user_type_label")
        
        user_info_layout.addWidget(username_label)
        user_info_layout.addWidget(user_type_label)
        
        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setObjectName("settings_btn")
        settings_btn.setFixedSize(30, 30)
        settings_btn.clicked.connect(self.settings_clicked)
        
        layout.addWidget(avatar_label)
        layout.addLayout(user_info_layout)
        layout.addWidget(settings_btn)
        
        return widget
        
    def on_nav_clicked(self, page_name):
        """处理导航点击事件"""
        # 重置所有按钮状态
        for btn in self.nav_buttons.values():
            btn.set_active(False)
            
        # 激活当前按钮
        if page_name in self.nav_buttons:
            self.nav_buttons[page_name].set_active(True)
            
        # 发射信号
        self.navigation_clicked.emit(page_name)


class NavigationButton(QPushButton):
    """导航按钮组件"""
    
    def __init__(self, icon, text):
        super().__init__(f"{icon} {text}")
        self.setObjectName("nav_button")
        self.setFixedHeight(45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_active(self, active):
        """设置按钮激活状态"""
        if active:
            self.setObjectName("nav_button_active")
        else:
            self.setObjectName("nav_button")
            
        self.style().unpolish(self)
        self.style().polish(self)