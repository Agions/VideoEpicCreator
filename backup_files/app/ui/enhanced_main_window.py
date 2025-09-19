#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强主窗口 - 整合所有新功能的专业视频编辑界面
"""

import os
import logging
from typing import Dict, Optional, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QFrame, QSplitter, QDockWidget, QToolBar, QStatusBar,
    QMessageBox, QProgressBar, QMenu, QDialog, QDialogButtonBox, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QThread
from PyQt6.QtGui import QFont, QAction, QIcon, QPainter, QColor

from app.config.settings_manager import SettingsManager
from app.core.project_manager import ProjectManager
from app.ai import create_unified_ai_service
from app.core.performance_optimizer import (
    get_enhanced_performance_optimizer,
    start_enhanced_performance_monitoring
)
from app.core.memory_manager import get_memory_manager, start_memory_monitoring

from .professional_ui_system import (
    ProfessionalTheme, ProfessionalButton, ProfessionalCard,
    ProfessionalNavigation, ProfessionalHomePage
)
from .unified_theme_system import UnifiedThemeManager, ThemeType
from .components.performance_dashboard import PerformanceMetricsWidget
from .global_style_fixer import fix_widget_styles

logger = logging.getLogger(__name__)


class EnhancedStatusBar(QStatusBar):
    """增强状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_performance_monitoring()

    def setup_ui(self):
        """设置UI"""
        # 永久消息
        self.showMessage("就绪", 0)

        # 性能指标
        self.cpu_label = QLabel("CPU: 0%")
        self.addWidget(self.cpu_label)

        self.memory_label = QLabel("内存: 0%")
        self.addWidget(self.memory_label)

        self.fps_label = QLabel("FPS: 0")
        self.addWidget(self.fps_label)

        # 分隔符
        self.addPermanentWidget(QFrame(self).setFrameShape(QFrame.Shape.VLine))

        # 项目信息
        self.project_label = QLabel("无项目")
        self.addPermanentWidget(self.project_label)

        # 性能指示器
        self.performance_progress = QProgressBar()
        self.performance_progress.setRange(0, 100)
        self.performance_progress.setValue(0)
        self.performance_progress.setMaximumWidth(150)
        self.performance_progress.setFixedHeight(16)
        self.performance_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background-color: #4CAF50;
            }
        """)
        self.addPermanentWidget(self.performance_progress)

    def setup_performance_monitoring(self):
        """设置性能监控"""
        self.performance_optimizer = get_enhanced_performance_optimizer()

        # 连接信号
        self.performance_optimizer._monitor.metrics_updated.connect(self.update_metrics)

    def update_metrics(self, metrics):
        """更新性能指标"""
        try:
            # 更新CPU和内存显示
            self.cpu_label.setText(f"CPU: {metrics.cpu_percent:.1f}%")
            self.memory_label.setText(f"内存: {metrics.memory_percent:.1f}%")

            # 更新FPS
            if metrics.fps:
                self.fps_label.setText(f"FPS: {metrics.fps:.1f}")

            # 更新性能进度条
            performance_score = 100 - (metrics.cpu_percent + metrics.memory_percent) / 2
            self.performance_progress.setValue(int(performance_score))

            # 根据性能改变颜色
            if performance_score > 70:
                color = "#4CAF50"
            elif performance_score > 40:
                color = "#FF9800"
            else:
                color = "#F44336"

            self.performance_progress.setStyleSheet(f"""
                QProgressBar::chunk {{
                    border-radius: 7px;
                    background-color: {color};
                }}
            """)

        except Exception as e:
            logger.error(f"更新状态栏指标错误: {e}")

    def set_project_info(self, project_name: str):
        """设置项目信息"""
        self.project_label.setText(f"项目: {project_name}")


class EnhancedNavigation(QWidget):
    """增强导航栏"""

    # 信号定义
    navigation_changed = pyqtSignal(str)  # 导航变更信号
    show_performance_dashboard = pyqtSignal()
    show_ai_panel = pyqtSignal()
    show_media_library = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_page = "home"

        # 导航项
        self.nav_items = [
            ("home", "🏠 首页", "欢迎使用 CineAIStudio"),
            ("projects", "📁 项目", "管理您的视频项目"),
            ("ai_tools", "🤖 AI工具", "智能视频处理"),
            ("video_edit", "🎬 视频编辑", "专业视频编辑器"),
            ("subtitle", "📝 字幕", "AI字幕生成"),
            ("effects", "✨ 特效", "高级特效制作"),
            ("export", "📤 导出", "导出和分享"),
            ("analytics", "📊 分析", "数据分析"),
            ("performance", "⚡ 性能", "性能监控"),
            ("settings", "⚙️ 设置", "系统设置")
        ]

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
        subtitle_label.setStyleSheet("font-size: 14px; color: #666;")
        subtitle_label.setObjectName("navSubtitle")

        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addSpacing(20)

        # 导航按钮
        self.nav_buttons = {}
        for item_id, item_name, item_desc in self.nav_items:
            btn = QPushButton(item_name)
            btn.setObjectName(f"navBtn_{item_id}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, page=item_id: self._on_nav_clicked(page))
            self.nav_buttons[item_id] = btn
            header_layout.addWidget(btn)

        header_layout.addStretch()

        # 添加到主布局
        layout.addLayout(header_layout)

        # 设置默认选中
        self.nav_buttons["home"].setChecked(True)

        # 设置样式
        self._set_style()

    def _on_nav_clicked(self, page_id: str):
        """导航点击处理"""
        self.current_page = page_id
        self.navigation_changed.emit(page_id)

        # 更新按钮状态
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == page_id)

    def _set_style(self):
        """设置样式"""
        self.setStyleSheet("""
            EnhancedNavigation {
                background-color: #2d3748;
                border-right: 1px solid #4a5568;
            }
            QLabel#navLogo {
                color: #63b3ed;
            }
            QLabel#navTitle {
                color: #ffffff;
            }
            QLabel#navSubtitle {
                color: #a0aec0;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e2e8f0;
                padding: 12px 20px;
                text-align: left;
                border-radius: 8px;
                margin: 2px 10px;
            }
            QPushButton:hover {
                background-color: #4a5568;
            }
            QPushButton:checked {
                background-color: #63b3ed;
                color: white;
            }
        """)

    def set_active_page(self, page_id: str):
        """设置活动页面"""
        if page_id in self.nav_buttons:
            self.nav_buttons[page_id].setChecked(True)
            self.current_page = page_id

    def set_theme(self, is_dark: bool):
        """设置主题"""
        if is_dark:
            self.setStyleSheet("""
                EnhancedNavigation {
                    background-color: #2d3748;
                    border-right: 1px solid #4a5568;
                }
                QLabel#navLogo {
                    color: #63b3ed;
                }
                QLabel#navTitle {
                    color: #ffffff;
                }
                QLabel#navSubtitle {
                    color: #a0aec0;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #e2e8f0;
                    padding: 12px 20px;
                    text-align: left;
                    border-radius: 8px;
                    margin: 2px 10px;
                }
                QPushButton:hover {
                    background-color: #4a5568;
                }
                QPushButton:checked {
                    background-color: #63b3ed;
                    color: white;
                }
            """)
        else:
            self.setStyleSheet("""
                EnhancedNavigation {
                    background-color: #f7fafc;
                    border-right: 1px solid #e2e8f0;
                }
                QLabel#navLogo {
                    color: #3182ce;
                }
                QLabel#navTitle {
                    color: #2d3748;
                }
                QLabel#navSubtitle {
                    color: #718096;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #4a5568;
                    padding: 12px 20px;
                    text-align: left;
                    border-radius: 8px;
                    margin: 2px 10px;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                }
                QPushButton:checked {
                    background-color: #3182ce;
                    color: white;
                }
            """)

    # _create_toolbar方法已移除，因为EnhancedNavigation不需要工具栏


class PerformanceDockWidget(QDockWidget):
    """性能监控停靠窗口"""

    def __init__(self, parent=None):
        super().__init__("性能监控", parent)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.performance_widget = PerformanceMetricsWidget()
        self.setWidget(self.performance_widget)

        # 设置默认属性
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )


class AIDockWidget(QDockWidget):
    """AI工具停靠窗口"""

    def __init__(self, ai_manager, parent=None):
        super().__init__("AI工具", parent)
        self.ai_manager = ai_manager
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        from ai_tools_component import AIToolsPanel
        self.ai_panel = AIToolsPanel(self.ai_manager)
        self.setWidget(self.ai_panel)


class MediaLibraryDockWidget(QDockWidget):
    """媒体库停靠窗口"""

    def __init__(self, project_manager, parent=None):
        super().__init__("媒体库", parent)
        self.project_manager = project_manager
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        from media_library_component import MediaLibraryWidget
        self.media_library = MediaLibraryWidget(self.project_manager)
        self.setWidget(self.media_library)


class EnhancedMainWindow(QMainWindow):
    """增强主窗口 - 整合所有新功能的专业视频编辑界面"""

    def __init__(self, settings_manager=None, project_manager=None, ai_manager=None):
        super().__init__()

        # 初始化管理器
        self.settings_manager = settings_manager or SettingsManager()
        self.project_manager = project_manager or ProjectManager()
        self.ai_manager = ai_manager  # 使用传入的ai_manager，不要在内部创建
        self.theme_manager = UnifiedThemeManager()

        # 性能和内存管理
        self.performance_optimizer = get_enhanced_performance_optimizer()
        self.memory_manager = get_memory_manager()

        # 窗口状态
        self.is_dark_theme = False
        self.current_page = "home"
        self.is_initialized = False

        # 初始化UI
        self.setup_ui()
        self.setup_dock_widgets()
        self.setup_status_bar()
        self.setup_menu_bar()
        self.setup_toolbars()

        # 连接信号
        self.connect_signals()

        # 加载设置
        self.load_settings()

        # 启动性能监控
        self.start_performance_monitoring()

        # 应用主题
        self.apply_theme()

        self.is_initialized = True
        logger.info("增强主窗口初始化完成")

    def setup_ui(self):
        """设置主UI"""
        # 窗口基本设置
        self.setWindowTitle("CineAIStudio - 专业AI视频编辑器")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 1000)

        # 中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建增强导航
        self.navigation = EnhancedNavigation()
        main_layout.addWidget(self.navigation)

        # 内容区域
        self.content_area = QFrame()
        self.content_area.setObjectName("content-area")
        self.content_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 创建页面堆栈
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("content-stack")
        content_layout.addWidget(self.content_stack)

        main_layout.addWidget(self.content_area)

        # 创建所有页面
        self.create_pages()

    def create_pages(self):
        """创建所有页面"""
        # 首页
        from app.ui.pages.home_page import HomePage
        # 创建兼容的AIManager包装器
        from app.ai.ai_manager import AIManager
        ai_manager_compat = AIManager(self.settings_manager)
        self.home_page = HomePage(ai_manager_compat, self.project_manager)
        self.content_stack.addWidget(self.home_page)

        # 项目管理页面
        from app.ui.pages.projects_page import ProfessionalProjectsPage
        self.projects_page = ProfessionalProjectsPage(self.project_manager)
        self.content_stack.addWidget(self.projects_page)

        # AI工具页面
        from app.ui.pages.ai_tools_page import AIToolsPage
        self.ai_tools_page = AIToolsPage(self.ai_manager, self.settings_manager)
        self.content_stack.addWidget(self.ai_tools_page)

        # 视频编辑页面
        from app.ui.pages.video_editing_page import VideoEditingPage
        self.video_edit_page = VideoEditingPage(self.project_manager, self.ai_manager)
        self.content_stack.addWidget(self.video_edit_page)

        # 字幕生成页面
        from app.ui.pages.subtitle_page import SubtitlePage
        self.subtitle_page = SubtitlePage(self.ai_manager)
        self.content_stack.addWidget(self.subtitle_page)

        # 特效制作页面
        from app.ui.pages.effects_page import EffectsPage
        self.effects_page = EffectsPage(self.ai_manager)
        self.content_stack.addWidget(self.effects_page)

        # 导出分享页面
        from app.ui.pages.export_page import ExportPage
        self.export_page = ExportPage(self.project_manager)
        self.content_stack.addWidget(self.export_page)

        # 数据分析页面
        from app.ui.pages.analytics_page import AnalyticsPage
        self.analytics_page = AnalyticsPage(self.ai_manager, self.project_manager)
        self.content_stack.addWidget(self.analytics_page)

        # 性能监控页面
        self.performance_page = PerformanceMetricsWidget()
        self.content_stack.addWidget(self.performance_page)

        # 设置页面
        self.settings_page = self.create_settings_page()
        self.content_stack.addWidget(self.settings_page)

        # 创建页面映射
        self.page_map = {
            "home": 0,
            "projects": 1,
            "ai_tools": 2,
            "video_edit": 3,
            "subtitle": 4,
            "effects": 5,
            "export": 6,
            "analytics": 7,
            "performance": 8,
            "settings": 9
        }

        # 设置默认页面
        self.content_stack.setCurrentIndex(0)

    def create_settings_page(self) -> QWidget:
        """创建设置页面"""
        from .professional_main_window import ProfessionalSettingsPage
        settings_page = ProfessionalSettingsPage(self.settings_manager)
        settings_page.theme_changed.connect(self.set_theme)
        return settings_page

    def setup_dock_widgets(self):
        """设置停靠窗口"""
        # 性能监控停靠窗口
        self.performance_dock = PerformanceDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.performance_dock)
        self.performance_dock.hide()

        # AI工具停靠窗口
        self.ai_dock = AIDockWidget(self.ai_manager, self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide()

        # 媒体库停靠窗口
        self.media_dock = MediaLibraryDockWidget(self.project_manager, self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.media_dock)
        self.media_dock.hide()

    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = EnhancedStatusBar(self)
        self.setStatusBar(self.status_bar)

    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_project_action = QAction("新建项目(&N)", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction("打开项目(&O)", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        save_project_action = QAction("保存项目(&S)", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        save_as_action = QAction("另存为(&A)", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction("首选项(&P)", self)
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 停靠窗口菜单
        docks_menu = view_menu.addMenu("停靠窗口")

        performance_dock_action = QAction("性能监控", self)
        performance_dock_action.setCheckable(True)
        performance_dock_action.triggered.connect(self.toggle_performance_dock)
        docks_menu.addAction(performance_dock_action)

        ai_dock_action = QAction("AI工具", self)
        ai_dock_action.setCheckable(True)
        ai_dock_action.triggered.connect(self.toggle_ai_dock)
        docks_menu.addAction(ai_dock_action)

        media_dock_action = QAction("媒体库", self)
        media_dock_action.setCheckable(True)
        media_dock_action.triggered.connect(self.toggle_media_dock)
        docks_menu.addAction(media_dock_action)

        view_menu.addSeparator()

        # 全屏动作
        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        # 性能优化
        optimize_action = QAction("性能优化(&O)", self)
        optimize_action.triggered.connect(self.optimize_performance)
        tools_menu.addAction(optimize_action)

        # 内存清理
        cleanup_action = QAction("清理内存(&C)", self)
        cleanup_action.triggered.connect(self.cleanup_memory)
        tools_menu.addAction(cleanup_action)

        tools_menu.addSeparator()

        # AI配置
        ai_config_action = QAction("AI配置(&A)", self)
        ai_config_action.triggered.connect(self.configure_ai)
        tools_menu.addAction(ai_config_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        help_menu.addSeparator()

        check_update_action = QAction("检查更新(&U)", self)
        check_update_action.triggered.connect(self.check_updates)
        help_menu.addAction(check_update_action)

    def setup_toolbars(self):
        """设置工具栏"""
        # 主工具栏
        main_toolbar = self.addToolBar("主工具栏")
        main_toolbar.setObjectName("main_toolbar")
        main_toolbar.setMovable(False)

        # 新建项目按钮
        new_project_btn = ProfessionalButton("新建项目", "primary")
        new_project_btn.clicked.connect(self.new_project)
        main_toolbar.addWidget(new_project_btn)

        main_toolbar.addSeparator()

        # 性能优化按钮
        optimize_btn = ProfessionalButton("性能优化", "secondary")
        optimize_btn.clicked.connect(self.optimize_performance)
        main_toolbar.addWidget(optimize_btn)

        # 内存清理按钮
        cleanup_btn = ProfessionalButton("清理内存", "secondary")
        cleanup_btn.clicked.connect(self.cleanup_memory)
        main_toolbar.addWidget(cleanup_btn)

        main_toolbar.addSeparator()

        # 主题切换按钮
        theme_btn = ProfessionalButton("🌙", "default")
        theme_btn.setMaximumSize(40, 40)
        theme_btn.clicked.connect(lambda: self.set_theme(not self.is_dark_theme))
        theme_btn.setToolTip("切换主题")
        main_toolbar.addWidget(theme_btn)

    def connect_signals(self):
        """连接信号"""
        # 导航信号
        self.navigation.navigation_changed.connect(self.navigate_to_page)

        # 增强导航信号
        self.navigation.show_performance_dashboard.connect(self.show_performance_dashboard)
        self.navigation.show_ai_panel.connect(self.show_ai_panel)
        self.navigation.show_media_library.connect(self.show_media_library)

        # 性能监控信号
        self.performance_optimizer.performance_alert.connect(self.show_performance_alert)
        self.performance_optimizer.memory_warning.connect(self.show_memory_warning)

    def navigate_to_page(self, page_name: str):
        """导航到指定页面"""
        if page_name in self.page_map:
            self.content_stack.setCurrentIndex(self.page_map[page_name])
            self.current_page = page_name

            # 更新导航状态
            self.navigation.set_active_page(page_name)

            # 更新页面标题
            self.update_window_title()

    def update_window_title(self):
        """更新窗口标题"""
        base_title = "CineAIStudio - 专业AI视频编辑器"

        # 添加当前页面名称
        page_titles = {
            "home": "首页",
            "projects": "项目管理",
            "ai_tools": "AI工具",
            "video_edit": "视频编辑",
            "subtitle": "字幕生成",
            "effects": "特效制作",
            "export": "导出分享",
            "analytics": "数据分析",
            "performance": "性能监控",
            "settings": "系统设置"
        }

        page_title = page_titles.get(self.current_page, "")
        if page_title:
            self.setWindowTitle(f"{base_title} - {page_title}")
        else:
            self.setWindowTitle(base_title)

    def start_performance_monitoring(self):
        """启动性能监控"""
        try:
            # 启动性能监控
            start_enhanced_performance_monitoring(1000)

            # 启动内存监控
            start_memory_monitoring(2000)

            logger.info("性能监控已启动")
        except Exception as e:
            logger.error(f"启动性能监控失败: {e}")

    def load_settings(self):
        """加载设置"""
        try:
            # 加载主题设置
            self.is_dark_theme = self.settings_manager.get_setting("ui.dark_theme", False)

            # 加载窗口几何设置
            geometry = self.settings_manager.get_setting("window.geometry")
            if geometry:
                self.restoreGeometry(geometry)

            # 加载窗口状态
            state = self.settings_manager.get_setting("window.state")
            if state:
                self.restoreState(state)

            # 加载最近项目
            recent_projects = self.settings_manager.get_setting("recent_projects", [])
            if recent_projects:
                self.update_recent_projects_menu(recent_projects)

        except Exception as e:
            logger.error(f"加载设置失败: {e}")

    def save_settings(self):
        """保存设置"""
        try:
            # 保存主题设置
            self.settings_manager.set_setting("ui.dark_theme", self.is_dark_theme)

            # 保存窗口几何设置
            self.settings_manager.set_setting("window.geometry", self.saveGeometry())

            # 保存窗口状态
            self.settings_manager.set_setting("window.state", self.saveState())

        except Exception as e:
            logger.error(f"保存设置失败: {e}")

    def apply_theme(self):
        """应用主题"""
        try:
            # 使用统一主题管理器设置主题
            theme_type = ThemeType.DARK if self.is_dark_theme else ThemeType.LIGHT
            self.theme_manager.set_theme(theme_type)

            # 设置导航主题
            self.navigation.set_theme(self.is_dark_theme)

            # 设置所有页面主题
            for i in range(self.content_stack.count()):
                page = self.content_stack.widget(i)
                if hasattr(page, 'set_theme'):
                    page.set_theme(self.is_dark_theme)

            # 应用窗口样式
            colors = self.theme_manager.get_theme_colors()
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                }}
                .content-area {{
                    background-color: {colors['surface']};
                    border-left: 1px solid {colors['border']};
                }}
                #content-stack {{
                    background-color: {colors['surface']};
                }}
                QToolBar {{
                    background-color: {colors['surface']};
                    border-bottom: 1px solid {colors['border']};
                }}
                QMenuBar {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border-bottom: 1px solid {colors['border']};
                }}
                QStatusBar {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border-top: 1px solid {colors['border']};
                }}
            """)

            # 修复样式问题
            fix_widget_styles(self)

        except Exception as e:
            logger.error(f"应用主题失败: {e}")

    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self.apply_theme()
        self.save_settings()

    # 菜单动作实现
    def new_project(self):
        """新建项目"""
        try:
            project = self.project_manager.create_project("新项目")
            self.status_bar.set_project_info(project.name)
            self.show_info("新建项目成功")
        except Exception as e:
            self.show_error(f"新建项目失败: {e}")

    def open_project(self):
        """打开项目"""
        try:
            # 这里应该添加文件对话框
            project = self.project_manager.load_project("project_path")  # 示例
            self.status_bar.set_project_info(project.name)
            self.show_info("打开项目成功")
        except Exception as e:
            self.show_error(f"打开项目失败: {e}")

    def save_project(self):
        """保存项目"""
        try:
            self.project_manager.save_project()
            self.show_info("保存项目成功")
        except Exception as e:
            self.show_error(f"保存项目失败: {e}")

    def save_project_as(self):
        """另存项目"""
        try:
            # 这里应该添加文件对话框
            self.project_manager.save_project("new_path")  # 示例
            self.show_info("另存项目成功")
        except Exception as e:
            self.show_error(f"另存项目失败: {e}")

    def show_preferences(self):
        """显示首选项"""
        self.navigate_to_page("settings")

    def toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def optimize_performance(self):
        """性能优化"""
        try:
            with self.performance_optimizer.performance_context("system_optimization"):
                results = self.performance_optimizer.optimize_system()
                self.show_info(f"性能优化完成: 释放 {results['memory_freed_mb']} MB 内存")
        except Exception as e:
            self.show_error(f"性能优化失败: {e}")

    def cleanup_memory(self):
        """清理内存"""
        try:
            results = self.memory_manager.perform_cleanup()
            freed_mb = (results['memory_before'] - results['memory_after']) / 1024 / 1024
            self.show_info(f"内存清理完成: 释放 {freed_mb:.2f} MB")
        except Exception as e:
            self.show_error(f"内存清理失败: {e}")

    def configure_ai(self):
        """配置AI"""
        try:
            self.navigate_to_page("ai_tools")
            # 这里可以添加更多AI配置逻辑
        except Exception as e:
            self.show_error(f"AI配置失败: {e}")

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 CineAIStudio",
            "CineAIStudio v2.0\n\n"
            "专业AI视频编辑器\n\n"
            "功能特性:\n"
            "• 智能视频处理\n"
            "• AI字幕生成\n"
            "• 高级特效制作\n"
            "• 性能优化管理\n"
            "• 专业视频导出\n\n"
            "© 2024 CineAIStudio Team")

    def check_updates(self):
        """检查更新"""
        self.show_info("正在检查更新...")
        # 这里可以添加更新检查逻辑

    def show_performance_dashboard(self):
        """显示性能监控面板"""
        self.performance_dock.setVisible(not self.performance_dock.isVisible())

    def show_ai_panel(self):
        """显示AI工具面板"""
        self.ai_dock.setVisible(not self.ai_dock.isVisible())

    def show_media_library(self):
        """显示媒体库面板"""
        self.media_dock.setVisible(not self.media_dock.isVisible())

    def toggle_performance_dock(self, checked: bool):
        """切换性能监控停靠窗口"""
        self.performance_dock.setVisible(checked)

    def toggle_ai_dock(self, checked: bool):
        """切换AI工具停靠窗口"""
        self.ai_dock.setVisible(checked)

    def toggle_media_dock(self, checked: bool):
        """切换媒体库停靠窗口"""
        self.media_dock.setVisible(checked)

    def show_performance_alert(self, resource_type: str, current_value: float, limit_value: float):
        """显示性能警报"""
        self.status_bar.showMessage(
            f"警告: {resource_type} 使用率 {current_value:.1f}% 超过限制 {limit_value:.1f}%",
            5000
        )

    def show_memory_warning(self, message: str, memory_usage: int):
        """显示内存警告"""
        self.status_bar.showMessage(
            f"内存警告: {message} ({memory_usage / 1024 / 1024:.1f} MB)",
            5000
        )

    def update_recent_projects_menu(self, recent_projects: List[str]):
        """更新最近项目菜单"""
        # 这里可以添加最近项目菜单更新逻辑
        pass

    def show_info(self, message: str):
        """显示信息消息"""
        self.status_bar.showMessage(message, 3000)

    def show_error(self, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, "错误", message)

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止性能监控
            self.performance_optimizer.stop_monitoring()

            # 清理内存
            self.memory_manager.cleanup()

            # 保存设置
            self.save_settings()

            # 关闭所有项目
            self.project_manager.close_all_projects()

        except Exception as e:
            logger.error(f"关闭窗口时发生错误: {e}")

        event.accept()


def create_enhanced_main_window() -> EnhancedMainWindow:
    """创建增强主窗口"""
    return EnhancedMainWindow()