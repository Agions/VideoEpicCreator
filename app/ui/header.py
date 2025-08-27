"""
Header component for VideoEpicCreator
Top header with title, search, and user actions
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont


class Header(QWidget):
    """顶部导航栏组件"""
    
    # 信号定义
    settings_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setObjectName("header")
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI组件"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 左侧：页面标题
        self.page_title = QLabel("仪表板")
        self.page_title.setObjectName("page_title")
        
        # 中间：搜索框
        self.search_input = SearchInput()
        
        # 右侧：操作按钮
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        # 通知按钮
        notification_btn = QPushButton("🔔")
        notification_btn.setObjectName("icon_button")
        notification_btn.setFixedSize(35, 35)
        notification_btn.setToolTip("通知")
        
        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setObjectName("icon_button")
        settings_btn.setFixedSize(35, 35)
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self.settings_clicked)
        
        actions_layout.addWidget(notification_btn)
        actions_layout.addWidget(settings_btn)
        
        # 添加到主布局
        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addStretch()
        layout.addLayout(actions_layout)
        
    def set_page_title(self, title):
        """设置页面标题"""
        self.page_title.setText(title)


class SearchInput(QLineEdit):
    """搜索输入框组件"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("search_input")
        self.setPlaceholderText("搜索项目、文件或设置...")
        self.setFixedWidth(300)
        self.setFixedHeight(35)