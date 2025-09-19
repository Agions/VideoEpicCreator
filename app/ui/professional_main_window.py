#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业主窗口 - 完全重新设计，解决所有UI问题
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QFrame, QSizePolicy, QStatusBar, QMenuBar, QToolBar,
    QTabWidget, QComboBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction, QIcon

from app.config.settings_manager import SettingsManager
from app.core.project_manager import ProjectManager
from app.ai import create_unified_ai_service

from .professional_ui_system import (
    ProfessionalTheme, ProfessionalButton, ProfessionalCard,
    ProfessionalNavigation, ProfessionalHomePage
)
from .unified_theme_system import UnifiedThemeManager, ThemeType
from .global_style_fixer import fix_widget_styles


class ProfessionalSettingsPage(QWidget):
    """专业设置页面"""

    # 信号定义
    theme_changed = pyqtSignal(bool)  # 主题切换信号

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.is_dark_theme = False

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # 页面标题
        title_label = QLabel("设置")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 主题设置
        theme_card = ProfessionalCard("主题设置")

        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(16)

        light_btn = ProfessionalButton("☀️ 浅色主题", "default")
        dark_btn = ProfessionalButton("🌙 深色主题", "default")

        light_btn.clicked.connect(lambda: self._change_theme(False))
        dark_btn.clicked.connect(lambda: self._change_theme(True))

        theme_layout.addWidget(light_btn)
        theme_layout.addWidget(dark_btn)
        theme_layout.addStretch()

        theme_widget = QWidget()
        theme_widget.setLayout(theme_layout)
        theme_card.add_content(theme_widget)

        layout.addWidget(theme_card)

        # AI设置
        ai_card = ProfessionalCard("AI设置")
        ai_desc = QLabel("配置AI模型的API密钥以使用AI功能")
        ai_desc.setWordWrap(True)
        ai_card.add_content(ai_desc)

        configure_ai_btn = ProfessionalButton("配置AI模型", "primary")
        configure_ai_btn.clicked.connect(self._configure_ai)
        ai_card.add_content(configure_ai_btn)

        layout.addWidget(ai_card)

        # 导出设置
        export_card = ProfessionalCard("导出设置")

        export_layout = QVBoxLayout()

        quality_label = QLabel("默认导出质量:")
        quality_combo = QComboBox()
        quality_combo.addItems(["高质量", "标准质量", "压缩质量"])
        export_layout.addWidget(quality_label)
        export_layout.addWidget(quality_combo)

        format_label = QLabel("默认导出格式:")
        format_combo = QComboBox()
        format_combo.addItems(["MP4", "AVI", "MOV"])
        export_layout.addWidget(format_label)
        export_layout.addWidget(format_combo)

        export_widget = QWidget()
        export_widget.setLayout(export_layout)
        export_card.add_content(export_widget)

        layout.addWidget(export_card)

        layout.addStretch()

    def _apply_styles(self):
        """应用样式"""
        colors = ProfessionalTheme.get_colors(self.is_dark_theme)

        self.setStyleSheet(f"""
            ProfessionalSettingsPage {{
                background-color: {colors['surface']};
                color: {colors['text']};
            }}
            QLabel {{
                color: {colors['text']};
                border: none;
            }}
            QComboBox {{
                background-color: {colors['background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

    def _change_theme(self, is_dark):
        """切换主题"""
        if self.settings_manager:
            self.settings_manager.set_setting("ui.dark_theme", is_dark)

        # 通知主窗口切换主题
        if hasattr(self.parent(), 'set_theme'):
            self.parent().set_theme(is_dark)
        else:
            # 如果没有父窗口，直接发射信号
            if hasattr(self, 'theme_changed'):
                self.theme_changed.emit(is_dark)

    def _configure_ai(self):
        """配置AI模型"""
        from app.ui.ai_panel import AIPanel

        dialog = QDialog(self)
        dialog.setWindowTitle("AI模型配置")
        dialog.setModal(True)
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        ai_panel = AIPanel(dialog)
        layout.addWidget(ai_panel)

        dialog.exec()

    def set_theme(self, is_dark):
        """设置主题"""
        self.is_dark_theme = is_dark
        self._apply_styles()

        # 更新所有子组件主题
        for card in self.findChildren(ProfessionalCard):
            card.set_theme(is_dark)
        for button in self.findChildren(ProfessionalButton):
            button.set_theme(is_dark)


class ProfessionalMainWindow(QMainWindow):
    """专业主窗口"""

    # 信号定义
    theme_changed = pyqtSignal(bool)  # 主题切换信号
    project_opened = pyqtSignal(object)  # 项目打开信号
    video_editing_requested = pyqtSignal(dict)  # 视频编辑请求信号

    def __init__(self, ai_service=None, settings_manager=None, theme_manager=None, parent=None):
        super().__init__(parent)

        # 如果传入服务实例，注册到全局容器
        if ai_service or settings_manager:
            from app.core.service_container import ServiceContainer
            container = ServiceContainer()

            if settings_manager:
                container.register_instance(type(settings_manager), settings_manager)

            if ai_service:
                container.register_instance(type(ai_service), ai_service)

        # 获取服务实例
        from app.core.service_config import get_ai_service, get_settings_manager

        try:
            self.ai_service = get_ai_service()
            self.settings_manager = get_settings_manager()
        except RuntimeError:
            # 如果全局容器未初始化，使用传入的实例
            self.ai_service = ai_service
            self.settings_manager = settings_manager

        # 确保服务可用
        if not self.ai_service:
            raise ValueError("AI service is required")
        if not self.settings_manager:
            raise ValueError("Settings manager is required")

        # 获取其他服务
        from app.core.service_container import ServiceContainer
        container = ServiceContainer()
        try:
            self.project_manager = container.get(ProjectManager)
        except (ValueError, AttributeError):
            # 如果ProjectManager未注册，创建一个实例
            from app.project_manager import ProjectManager
            self.project_manager = ProjectManager(self.settings_manager)

        # 获取主题管理器
        if theme_manager:
            self.theme_manager = theme_manager
        else:
            # 如果未传入，尝试从容器获取或创建
            try:
                from app.core.service_container import get_service
                self.theme_manager = get_service(UnifiedThemeManager)
            except:
                self.theme_manager = UnifiedThemeManager()

        self.is_dark_theme = False
        self.current_page = "home"

        # 设置窗口属性
        self.setWindowTitle("CineAIStudio - 专业AI视频编辑器")
        self.setMinimumSize(1200, 800)

        # 初始化UI
        self._setup_ui()
        self._create_pages()
        self._connect_signals()

        # 应用主题
        self._load_theme_settings()
        self._apply_unified_theme()

        # 修复样式
        fix_widget_styles(self)

    def _setup_ui(self):
        """设置UI"""
        # 中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧导航
        self.navigation = ProfessionalNavigation()
        self.navigation.setMinimumWidth(200)
        self.navigation.setMaximumWidth(250)
        self.main_layout.addWidget(self.navigation)

        # 右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setProperty("class", "content-area")
        self.main_layout.addWidget(self.content_stack, 1)

        # 设置布局比例
        self.main_layout.setStretch(0, 0)  # 导航栏
        self.main_layout.setStretch(1, 1)  # 内容区域

    def _create_pages(self):
        """创建所有页面"""
        # 首页
        self.home_page = ProfessionalHomePage()
        self.content_stack.addWidget(self.home_page)

        # 项目管理页面
        from app.ui.pages.projects_page import ProfessionalProjectsPage
        self.projects_page = ProfessionalProjectsPage(self.project_manager)
        self.projects_page.video_editing_requested.connect(self.open_video_editing)
        self.content_stack.addWidget(self.projects_page)

        # AI工具页面
        from app.ui.pages.ai_tools_page import AIToolsPage
        self.ai_tools_page = AIToolsPage(self.ai_manager, self.settings_manager)
        self.content_stack.addWidget(self.ai_tools_page)

        # 视频编辑页面
        from app.ui.pages.video_editing_page import VideoEditingPage
        self.video_edit_page = VideoEditingPage(self.ai_manager, self.project_manager)
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

        # 设置页面
        self.settings_page = ProfessionalSettingsPage(self.settings_manager)
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
            "settings": 8
        }

        # 设置默认页面
        self.content_stack.setCurrentIndex(0)

    def _connect_signals(self):
        """连接信号"""
        # 导航信号
        self.navigation.navigation_changed.connect(self._navigate_to_page)

        # 设置页面信号
        self.settings_page.theme_changed.connect(self.set_theme)

    def _navigate_to_page(self, page_name: str):
        """导航到指定页面"""
        if page_name in self.page_map:
            self.content_stack.setCurrentIndex(self.page_map[page_name])
            self.current_page = page_name

            # 更新导航状态
            self.navigation.set_active_page(page_name)

    def _load_theme_settings(self):
        """加载主题设置"""
        if self.settings_manager:
            self.is_dark_theme = self.settings_manager.get_setting("ui.dark_theme", False)

    def _apply_unified_theme(self):
        """应用统一主题"""
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
        """)

    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark

        # 保存设置
        if self.settings_manager:
            self.settings_manager.set_setting("ui.dark_theme", is_dark)

        # 应用统一主题
        self._apply_unified_theme()

        # 发射信号
        self.theme_changed.emit(is_dark)

    def open_video_editing(self, project_data: dict):
        """打开视频编辑"""
        self._navigate_to_page("video_edit")
        self.video_editing_requested.emit(project_data)

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 清理资源
        for i in range(self.content_stack.count()):
            page = self.content_stack.widget(i)
            if hasattr(page, 'cleanup'):
                try:
                    page.cleanup()
                except:
                    pass

        # 保存设置
        if self.settings_manager:
            self.settings_manager.save_settings()

        super().closeEvent(event)
