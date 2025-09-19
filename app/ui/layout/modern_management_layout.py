#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
现代管理界面布局系统
实现标准的左右布局管理界面，符合企业级应用UI规范

布局结构：
┌─────────────────────────────────────────────────────────────┐
│                        菜单栏                              │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│  侧边栏  │                主内容区域                         │
│  导航    │                                                  │
│          │                                                  │
│  ├──────  │  ┌─────────────────────────────────────────────┐  │
│  │ 首页   │  │                                         │  │
│  ├──────  │  │              页面内容                       │  │
│  │ 项目   │  │                                         │  │
│  ├──────  │  │                                         │  │
│  │ AI工具 │  │                                         │  │
│  ├──────  │  │                                         │  │
│  │ 导出   │  │                                         │  │
│  ├──────  │  │                                         │  │
│  │ 设置   │  │                                         │  │
│  └──────  │  └─────────────────────────────────────────────┘  │
│          │                                                  │
│          │                 状态栏                           │
└──────────┴──────────────────────────────────────────────────┘
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QStackedWidget, QStatusBar,
    QScrollArea, QSplitter, QMenu, QMenuBar, QToolBar,
    QSizePolicy, QSpacerItem, QApplication
)
from PyQt6.QtCore import (
    Qt, QSize, QPoint, pyqtSignal, QTimer, QRect,
    QPropertyAnimation, QEasingCurve, QObject
)
from PyQt6.QtGui import (
    QIcon, QFont, QPixmap, QPainter, QColor, QPalette,
    QLinearGradient, QBrush, QPainterPath, QPen
)

from app.ui.unified_theme_system import UnifiedThemeManager
from app.ui.components.base_component import BaseComponent

logger = logging.getLogger(__name__)


class NavigationItemType(Enum):
    """导航项类型"""
    PAGE = "page"           # 页面导航
    SECTION = "section"     # 分组标题
    ACTION = "action"       # 操作动作
    TOGGLE = "toggle"       # 开关切换
    SEPARATOR = "separator" # 分隔线


@dataclass
class NavigationItem:
    """导航项数据结构"""
    id: str
    title: str
    icon: Optional[str] = None
    tooltip: Optional[str] = None
    type: NavigationItemType = NavigationItemType.PAGE
    page_name: Optional[str] = None
    callback: Optional[Callable] = None
    enabled: bool = True
    visible: bool = True
    children: List['NavigationItem'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class SideNavigationPanel(BaseComponent):
    """侧边导航面板"""

    # 信号定义
    navigation_clicked = pyqtSignal(str)  # 导航点击信号
    navigation_hovered = pyqtSignal(str)  # 导航悬停信号

    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self.navigation_items: List[NavigationItem] = []
        self.current_item_id: Optional[str] = None
        self.item_widgets: Dict[str, QWidget] = {}
        self.title_labels: Dict[str, QLabel] = {}
        self.collapsed = False
        self.animation_duration = 200

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 应用面板样式
        self.setObjectName("sideNavigationPanel")
        self._apply_styles()

        # 创建头部区域
        self.header_widget = self._create_header()
        layout.addWidget(self.header_widget)

        # 创建导航区域
        self.navigation_area = self._create_navigation_area()
        layout.addWidget(self.navigation_area)

        # 创建底部区域
        self.footer_widget = self._create_footer()
        layout.addWidget(self.footer_widget)

        # 设置伸缩因子
        layout.setStretchFactor(self.navigation_area, 1)

    def _create_header(self) -> QWidget:
        """创建头部区域"""
        header = QWidget()
        header.setObjectName("navigationHeader")
        header.setFixedHeight(60)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        # Logo和应用名称
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(32, 32)
        self.logo_label.setScaledContents(True)

        self.app_name_label = QLabel("CineAIStudio")
        self.app_name_label.setObjectName("appNameLabel")

        layout.addWidget(self.logo_label)
        layout.addWidget(self.app_name_label)
        layout.addStretch()

        # 折叠按钮
        self.collapse_button = QPushButton()
        self.collapse_button.setObjectName("collapseButton")
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.clicked.connect(self._toggle_collapse)
        layout.addWidget(self.collapse_button)

        return header

    def _create_navigation_area(self) -> QScrollArea:
        """创建导航区域"""
        scroll_area = QScrollArea()
        scroll_area.setObjectName("navigationArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 导航内容容器
        self.navigation_content = QWidget()
        self.navigation_layout = QVBoxLayout(self.navigation_content)
        self.navigation_layout.setContentsMargins(8, 8, 8, 8)
        self.navigation_layout.setSpacing(2)
        self.navigation_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.navigation_content)
        return scroll_area

    def _create_footer(self) -> QWidget:
        """创建底部区域"""
        footer = QWidget()
        footer.setObjectName("navigationFooter")
        footer.setFixedHeight(80)

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 用户信息
        self.user_info_label = QLabel("用户")
        self.user_info_label.setObjectName("userInfoLabel")
        layout.addWidget(self.user_info_label)

        # 设置按钮
        self.settings_button = QPushButton("设置")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.clicked.connect(lambda: self.navigation_clicked.emit("settings"))
        layout.addWidget(self.settings_button)

        layout.addStretch()

        return footer

    def _setup_connections(self):
        """设置信号连接"""
        pass

    def add_navigation_item(self, item: NavigationItem):
        """添加导航项"""
        self.navigation_items.append(item)

        # 创建导航项控件
        item_widget = self._create_navigation_item_widget(item)
        self.item_widgets[item.id] = item_widget

        # 添加到布局
        if item.type == NavigationItemType.SEPARATOR:
            self.navigation_layout.addWidget(item_widget)
        else:
            self.navigation_layout.addWidget(item_widget)

    def _create_navigation_item_widget(self, item: NavigationItem) -> QWidget:
        """创建导航项控件"""
        if item.type == NavigationItemType.SEPARATOR:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            separator.setObjectName("navigationSeparator")
            return separator

        # 创建导航项容器
        item_widget = QWidget()
        item_widget.setObjectName("navigationItem")
        item_widget.setProperty("itemId", item.id)
        item_widget.setFixedHeight(44)

        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(12, 8, 12, 8)

        # 图标
        if item.icon:
            icon_label = QLabel()
            icon_label.setObjectName("navigationIcon")
            icon_label.setFixedSize(20, 20)
            layout.addWidget(icon_label)
        else:
            spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            layout.addItem(spacer)

        # 标题
        title_label = QLabel(item.title)
        title_label.setObjectName("navigationTitle")
        layout.addWidget(title_label)

        # 展开/折叠时显示标题
        self.title_labels[item.id] = title_label

        layout.addStretch()

        # 子项指示器
        if item.children:
            expand_label = QLabel("▶")
            expand_label.setObjectName("navigationExpand")
            layout.addWidget(expand_label)

        # 鼠标事件
        item_widget.mousePressEvent = lambda event: self._on_item_clicked(item, item_widget)
        item_widget.enterEvent = lambda event: self._on_item_hovered(item, item_widget)

        return item_widget

    def _on_item_clicked(self, item: NavigationItem, widget: QWidget):
        """导航项点击处理"""
        if not item.enabled or item.type != NavigationItemType.PAGE:
            return

        # 更新当前选中状态
        self._set_current_item(item.id)

        # 发送导航信号
        if item.page_name:
            self.navigation_clicked.emit(item.page_name)
        elif item.callback:
            item.callback()

    def _on_item_hovered(self, item: NavigationItem, widget: QWidget):
        """导航项悬停处理"""
        self.navigation_hovered.emit(item.id)

    def _set_current_item(self, item_id: str):
        """设置当前选中的导航项"""
        # 清除之前的选中状态
        if self.current_item_id:
            old_widget = self.item_widgets.get(self.current_item_id)
            if old_widget:
                old_widget.setProperty("selected", False)
                old_widget.style().polish(old_widget)

        # 设置新的选中状态
        self.current_item_id = item_id
        new_widget = self.item_widgets.get(item_id)
        if new_widget:
            new_widget.setProperty("selected", True)
            new_widget.style().polish(new_widget)

    def _toggle_collapse(self):
        """切换折叠状态"""
        self.collapsed = not self.collapsed

        # 隐藏标题标签
        for label in self.title_labels.values():
            label.setVisible(not self.collapsed)

        # 调整面板宽度
        target_width = 60 if self.collapsed else 240

        # 创建动画
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(self.animation_duration)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

        # 更新按钮图标
        self.collapse_button.setText("◀" if not self.collapsed else "▶")

    def _apply_styles(self):
        """应用样式"""
        # 将在主题管理器中统一样式
        pass

    def set_default_navigation(self):
        """设置默认导航项"""
        navigation_items = [
            NavigationItem(
                id="home",
                title="首页",
                icon="home",
                page_name="home",
                tooltip="返回主页"
            ),
            NavigationItem(
                id="projects",
                title="项目管理",
                icon="projects",
                page_name="projects",
                tooltip="管理视频项目"
            ),
            NavigationItem(
                id="ai_tools",
                title="AI工具",
                icon="ai",
                page_name="ai_tools",
                tooltip="AI智能工具"
            ),
            NavigationItem(
                id="editing",
                title="视频编辑",
                icon="editing",
                page_name="editing",
                tooltip="视频编辑界面"
            ),
            NavigationItem(
                id="export",
                title="导出分享",
                icon="export",
                page_name="export",
                tooltip="导出和分享"
            ),
            NavigationItem(
                id="separator1",
                title="",
                type=NavigationItemType.SEPARATOR
            ),
            NavigationItem(
                id="analytics",
                title="数据分析",
                icon="analytics",
                page_name="analytics",
                tooltip="使用数据分析"
            ),
            NavigationItem(
                id="settings",
                title="系统设置",
                icon="settings",
                page_name="settings",
                tooltip="系统设置和偏好"
            )
        ]

        for item in navigation_items:
            self.add_navigation_item(item)


class MainContentArea(BaseComponent):
    """主内容区域"""

    # 信号定义
    page_changed = pyqtSignal(str)  # 页面切换信号

    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self.current_page: Optional[str] = None
        self.pages: Dict[str, QWidget] = {}
        self.page_stack: Optional[QStackedWidget] = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 应用内容区域样式
        self.setObjectName("mainContentArea")

        # 创建页面堆栈
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        layout.addWidget(self.page_stack)

    def _setup_connections(self):
        """设置信号连接"""
        self.page_stack.currentChanged.connect(self._on_page_changed)

    def add_page(self, page_id: str, page_widget: QWidget, page_name: str = None):
        """添加页面"""
        self.pages[page_id] = page_widget
        self.page_stack.addWidget(page_widget)

        # 设置页面名称
        if page_name:
            page_widget.setProperty("pageName", page_name)

    def navigate_to_page(self, page_id: str):
        """导航到指定页面"""
        if page_id in self.pages:
            self.page_stack.setCurrentWidget(self.pages[page_id])
            self.current_page = page_id

    def get_current_page(self) -> Optional[str]:
        """获取当前页面ID"""
        return self.current_page

    def _on_page_changed(self, index: int):
        """页面切换处理"""
        if index >= 0:
            current_widget = self.page_stack.currentWidget()
            if current_widget:
                page_name = current_widget.property("pageName")
                if page_name:
                    self.page_changed.emit(page_name)


class ModernStatusBar(QStatusBar):
    """现代状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        self.setObjectName("modernStatusBar")
        self.setMaximumHeight(30)

        # 永久组件
        self.permanent_widgets = {}

        # 临时消息
        self.showMessage("就绪", 3000)

    def add_permanent_widget(self, name: str, widget: QWidget):
        """添加永久组件"""
        self.permanent_widgets[name] = widget
        self.addPermanentWidget(widget)

    def update_status(self, message: str, timeout: int = 3000):
        """更新状态消息"""
        self.showMessage(message, timeout)

    def set_progress(self, value: int, maximum: int = 100):
        """设置进度"""
        # 实现进度显示逻辑
        pass


class ModernManagementLayout(BaseComponent):
    """现代管理界面布局"""

    # 信号定义
    page_navigation = pyqtSignal(str)  # 页面导航信号
    status_message = pyqtSignal(str)   # 状态消息信号

    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self.splitter: Optional[QSplitter] = None
        self.navigation_panel: Optional[SideNavigationPanel] = None
        self.main_content: Optional[MainContentArea] = None
        self.status_bar: Optional[ModernStatusBar] = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 应用主布局样式
        self.setObjectName("modernManagementLayout")

        # 创建主分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        layout.addWidget(self.splitter)

        # 创建侧边导航面板
        self.navigation_panel = SideNavigationPanel()
        self.navigation_panel.setFixedWidth(240)
        self.splitter.addWidget(self.navigation_panel)

        # 创建主内容区域
        self.main_content = MainContentArea()
        self.splitter.addWidget(self.main_content)

        # 设置分割器比例
        self.splitter.setStretchFactor(0, 0)  # 侧边栏
        self.splitter.setStretchFactor(1, 1)  # 主内容
        self.splitter.setSizes([240, 800])

        # 设置默认导航
        self.navigation_panel.set_default_navigation()

        # 应用样式
        self._apply_styles()

    def _setup_connections(self):
        """设置信号连接"""
        self.navigation_panel.navigation_clicked.connect(self._on_navigation_clicked)
        self.main_content.page_changed.connect(self.page_navigation)

    def _on_navigation_clicked(self, page_name: str):
        """导航点击处理"""
        self.main_content.navigate_to_page(page_name)
        self.status_message.emit(f"导航到: {page_name}")

    def add_page(self, page_id: str, page_widget: QWidget, page_name: str = None):
        """添加页面"""
        self.main_content.add_page(page_id, page_widget, page_name)

    def navigate_to_page(self, page_id: str):
        """导航到指定页面"""
        self.main_content.navigate_to_page(page_id)

    def get_current_page(self) -> Optional[str]:
        """获取当前页面"""
        return self.main_content.get_current_page()

    def set_status_bar(self, status_bar: ModernStatusBar):
        """设置状态栏"""
        self.status_bar = status_bar
        self.status_message.connect(self.status_bar.update_status)

    def _apply_styles(self):
        """应用样式"""
        # 将在主题管理器中统一样式
        pass

    def get_navigation_panel(self) -> SideNavigationPanel:
        """获取导航面板"""
        return self.navigation_panel

    def get_main_content(self) -> MainContentArea:
        """获取主内容区域"""
        return self.main_content