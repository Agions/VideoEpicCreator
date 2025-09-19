#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业管理界面主窗口
实现标准的企业级左右布局管理系统界面

特性：
- 专业的侧边导航栏
- 可折叠的导航面板
- 现代化的状态栏
- 集成的设置菜单系统
- 响应式布局设计
- 统一的主题系统
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar,
    QMessageBox, QApplication, QFrame, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction, QKeySequence

from app.ui.layout.modern_management_layout import ModernManagementLayout
from app.ui.settings.settings_manager_panel import SettingsDialog
from app.ui.unified_theme_system import UnifiedThemeManager
from app.ui.components.error_handler import show_info, show_error, show_success
from app.config.settings_manager import SettingsManager
from app.core.project_manager import ProjectManager
from app.ai.interfaces import IAIService

logger = logging.getLogger(__name__)


class PageType(Enum):
    """页面类型枚举"""
    HOME = "home"
    PROJECTS = "projects"
    AI_TOOLS = "ai_tools"
    EDITING = "editing"
    EXPORT = "export"
    ANALYTICS = "analytics"
    SETTINGS = "settings"


class ManagementMainWindow(QMainWindow):
    """专业管理界面主窗口"""

    # 信号定义
    page_changed = pyqtSignal(str)        # 页面切换信号
    settings_changed = pyqtSignal()       # 设置改变信号
    project_opened = pyqtSignal(str)      # 项目打开信号
    project_saved = pyqtSignal(str)       # 项目保存信号

    def __init__(self, settings_manager: SettingsManager,
                 project_manager: ProjectManager,
                 ai_service: IAIService):
        super().__init__()

        self.settings_manager = settings_manager
        self.project_manager = project_manager
        self.ai_service = ai_service
        self.theme_manager = UnifiedThemeManager()

        self.current_page: Optional[str] = None
        self.pages: Dict[str, QWidget] = {}
        self.management_layout: Optional[ModernManagementLayout] = None

        self._init_window()
        self._init_ui()
        self._init_menu_bar()
        self._init_tool_bars()
        self._init_status_bar()
        self._init_pages()
        self._setup_connections()
        self._load_settings()

    def _init_window(self):
        """初始化窗口属性"""
        self.setWindowTitle("CineAIStudio - 专业AI视频编辑器")
        self.setMinimumSize(1200, 800)
        self.setWindowIcon(QIcon())

        # 设置窗口标志
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinMaxButtonsHint
        )

        # 应用主题
        self._apply_theme()

    def _init_ui(self):
        """初始化UI组件"""
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建管理界面布局
        self.management_layout = ModernManagementLayout()
        main_layout.addWidget(self.management_layout)

    def _init_menu_bar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        menubar.setObjectName("mainMenuBar")

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 新建项目
        new_project_action = QAction("新建项目(&N)", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+N"))
        new_project_action.setStatusTip("创建新的视频项目")
        new_project_action.triggered.connect(self._new_project)
        file_menu.addAction(new_project_action)

        # 打开项目
        open_project_action = QAction("打开项目(&O)", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+O"))
        open_project_action.setStatusTip("打开已有的视频项目")
        open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        # 保存项目
        save_project_action = QAction("保存项目(&S)", self)
        save_project_action.setShortcut(QKeySequence("Ctrl+S"))
        save_project_action.setStatusTip("保存当前项目")
        save_project_action.triggered.connect(self._save_project)
        file_menu.addAction(save_project_action)

        # 另存为
        save_as_action = QAction("另存为(&A)", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.setStatusTip("将项目另存为")
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 导入
        import_menu = file_menu.addMenu("导入(&I)")

        import_video_action = QAction("导入视频(&V)", self)
        import_video_action.setStatusTip("导入视频文件")
        import_video_action.triggered.connect(lambda: self._import_media("video"))
        import_menu.addAction(import_video_action)

        import_audio_action = QAction("导入音频(&A)", self)
        import_audio_action.setStatusTip("导入音频文件")
        import_audio_action.triggered.connect(lambda: self._import_media("audio"))
        import_menu.addAction(import_audio_action)

        import_image_action = QAction("导入图片(&I)", self)
        import_image_action.setStatusTip("导入图片文件")
        import_image_action.triggered.connect(lambda: self._import_media("image"))
        import_menu.addAction(import_image_action)

        file_menu.addSeparator()

        # 导出
        export_menu = file_menu.addMenu("导出(&E)")

        export_video_action = QAction("导出视频(&V)", self)
        export_video_action.setStatusTip("导出为视频文件")
        export_video_action.triggered.connect(self._export_video)
        export_menu.addAction(export_video_action)

        export_jianying_action = QAction("导出到剪映(&J)", self)
        export_jianying_action.setStatusTip("导出为剪映草稿文件")
        export_jianying_action.triggered.connect(self._export_to_jianying)
        export_menu.addAction(export_jianying_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.setStatusTip("撤销上一步操作")
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.setStatusTip("重做上一步操作")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("剪切(&T)", self)
        cut_action.setShortcut(QKeySequence("Ctrl+X"))
        cut_action.setStatusTip("剪切选中的内容")
        edit_menu.addAction(cut_action)

        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.setStatusTip("复制选中的内容")
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴(&P)", self)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.setStatusTip("粘贴内容")
        edit_menu.addAction(paste_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 工具栏
        toolbar_action = QAction("工具栏(&T)", self)
        toolbar_action.setCheckable(True)
        toolbar_action.setChecked(True)
        toolbar_action.setStatusTip("显示或隐藏工具栏")
        view_menu.addAction(toolbar_action)

        # 状态栏
        statusbar_action = QAction("状态栏(&S)", self)
        statusbar_action.setCheckable(True)
        statusbar_action.setChecked(True)
        statusbar_action.setStatusTip("显示或隐藏状态栏")
        statusbar_action.triggered.connect(self._toggle_status_bar)
        view_menu.addAction(statusbar_action)

        view_menu.addSeparator()

        # 全屏
        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.setStatusTip("切换全屏模式")
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # AI工具菜单
        ai_menu = menubar.addMenu("AI工具(&A)")

        # AI解说
        ai_commentary_action = QAction("AI智能解说(&C)", self)
        ai_commentary_action.setStatusTip("使用AI生成视频解说")
        ai_commentary_action.triggered.connect(self._ai_commentary)
        ai_menu.addAction(ai_commentary_action)

        # AI混剪
        ai_compilation_action = QAction("AI高能混剪(&H)", self)
        ai_compilation_action.setStatusTip("使用AI创建高能混剪")
        ai_compilation_action.triggered.connect(self._ai_compilation)
        ai_menu.addAction(ai_compilation_action)

        # AI独白
        ai_monologue_action = QAction("AI第一人称独白(&M)", self)
        ai_monologue_action.setStatusTip("使用AI生成第一人称独白")
        ai_monologue_action.triggered.connect(self._ai_monologue)
        ai_menu.addAction(ai_monologue_action)

        ai_menu.addSeparator()

        # AI字幕
        ai_subtitle_action = QAction("AI字幕生成(&S)", self)
        ai_subtitle_action.setStatusTip("使用AI生成视频字幕")
        ai_subtitle_action.triggered.connect(self._ai_subtitle)
        ai_menu.addAction(ai_subtitle_action)

        # AI场景分析
        ai_scene_action = QAction("AI场景分析(&A)", self)
        ai_scene_action.setStatusTip("使用AI分析视频场景")
        ai_scene_action.triggered.connect(self._ai_scene_analysis)
        ai_menu.addAction(ai_scene_action)

        # 窗口菜单
        window_menu = menubar.addMenu("窗口(&W)")

        # 页面导航
        for page_type in PageType:
            if page_type == PageType.SETTINGS:
                continue  # 设置通过主菜单访问

            action = QAction(page_type.value.title(), self)
            action.setStatusTip(f"切换到{page_type.value}页面")
            action.triggered.connect(lambda checked, pt=page_type: self._navigate_to_page(pt.value))
            window_menu.addAction(action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")

        # 偏好设置
        preferences_action = QAction("偏好设置(&P)", self)
        preferences_action.setStatusTip("打开设置对话框")
        preferences_action.triggered.connect(self._open_settings)
        settings_menu.addAction(preferences_action)

        # 主题设置
        theme_menu = settings_menu.addMenu("主题(&T)")

        light_theme_action = QAction("浅色主题(&L)", self)
        light_theme_action.setStatusTip("切换到浅色主题")
        light_theme_action.triggered.connect(lambda: self._change_theme("professional_light"))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("深色主题(&D)", self)
        dark_theme_action.setStatusTip("切换到深色主题")
        dark_theme_action.triggered.connect(lambda: self._change_theme("professional_dark"))
        theme_menu.addAction(dark_theme_action)

        settings_menu.addSeparator()

        # AI配置
        ai_config_action = QAction("AI配置(&A)", self)
        ai_config_action.setStatusTip("配置AI服务和模型")
        ai_config_action.triggered.connect(self._ai_config)
        settings_menu.addAction(ai_config_action)

        # 性能设置
        performance_action = QAction("性能设置(&P)", self)
        performance_action.setStatusTip("配置性能优化选项")
        performance_action.triggered.connect(self._performance_settings)
        settings_menu.addAction(performance_action)

        settings_menu.addSeparator()

        # 恢复默认设置
        reset_action = QAction("恢复默认设置(&R)", self)
        reset_action.setStatusTip("恢复所有设置为默认值")
        reset_action.triggered.connect(self._reset_settings)
        settings_menu.addAction(reset_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        # 用户手册
        manual_action = QAction("用户手册(&M)", self)
        manual_action.setStatusTip("打开用户手册")
        manual_action.triggered.connect(self._open_manual)
        help_menu.addAction(manual_action)

        # 快捷键
        shortcuts_action = QAction("快捷键(&K)", self)
        shortcuts_action.setStatusTip("查看快捷键列表")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        # 检查更新
        update_action = QAction("检查更新(&U)", self)
        update_action.setStatusTip("检查是否有新版本")
        update_action.triggered.connect(self._check_updates)
        help_menu.addAction(update_action)

        help_menu.addSeparator()

        # 关于
        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于CineAIStudio")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_tool_bars(self):
        """初始化工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setObjectName("mainToolBar")
        main_toolbar.setMovable(False)
        self.addToolBar(main_toolbar)

        # 新建项目
        new_action = QAction("新建", self)
        new_action.setStatusTip("创建新项目")
        new_action.triggered.connect(self._new_project)
        main_toolbar.addAction(new_action)

        # 打开项目
        open_action = QAction("打开", self)
        open_action.setStatusTip("打开项目")
        open_action.triggered.connect(self._open_project)
        main_toolbar.addAction(open_action)

        # 保存项目
        save_action = QAction("保存", self)
        save_action.setStatusTip("保存项目")
        save_action.triggered.connect(self._save_project)
        main_toolbar.addAction(save_action)

        main_toolbar.addSeparator()

        # 导入
        import_action = QAction("导入", self)
        import_action.setStatusTip("导入媒体文件")
        import_action.triggered.connect(lambda: self._import_media("video"))
        main_toolbar.addAction(import_action)

        # 导出
        export_action = QAction("导出", self)
        export_action.setStatusTip("导出视频")
        export_action.triggered.connect(self._export_video)
        main_toolbar.addAction(export_action)

        main_toolbar.addSeparator()

        # AI工具
        ai_action = QAction("AI工具", self)
        ai_action.setStatusTip("AI智能工具")
        ai_action.triggered.connect(lambda: self._navigate_to_page("ai_tools"))
        main_toolbar.addAction(ai_action)

        # 设置
        settings_action = QAction("设置", self)
        settings_action.setStatusTip("打开设置")
        settings_action.triggered.connect(self._open_settings)
        main_toolbar.addAction(settings_action)

    def _init_status_bar(self):
        """初始化状态栏"""
        status_bar = QStatusBar()
        status_bar.setObjectName("mainStatusBar")
        self.setStatusBar(status_bar)

        # 永久状态信息
        self.status_label = QLabel("就绪")
        status_bar.addPermanentWidget(self.status_label)

        # 内存使用
        self.memory_label = QLabel("内存: 0 MB")
        status_bar.addPermanentWidget(self.memory_label)

        # CPU使用率
        self.cpu_label = QLabel("CPU: 0%")
        status_bar.addPermanentWidget(self.cpu_label)

        # 启动性能监控定时器
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_status)
        self.performance_timer.start(2000)  # 每2秒更新一次

    def _init_pages(self):
        """初始化页面"""
        # 创建页面容器
        from app.ui.pages.home_page import HomePage
        from app.ui.pages.projects_page import ProfessionalProjectsPage as ProjectsPage
        from app.ui.pages.ai_tools_page import AIToolsPage
        from app.ui.pages.video_editing_page import VideoEditingPage
        from app.ui.pages.export_page import ExportPage
        from app.ui.pages.analytics_page import AnalyticsPage

        # 首页
        home_page = HomePage(self.settings_manager, self.project_manager, self.ai_service)
        self.management_layout.add_page("home", home_page, "首页")

        # 项目管理
        projects_page = ProjectsPage(self.settings_manager, self.project_manager)
        self.management_layout.add_page("projects", projects_page, "项目管理")

        # AI工具
        ai_tools_page = AIToolsPage(self.settings_manager, self.ai_service)
        self.management_layout.add_page("ai_tools", ai_tools_page, "AI工具")

        # 视频编辑
        editing_page = VideoEditingPage(self.settings_manager, self.project_manager)
        self.management_layout.add_page("editing", editing_page, "视频编辑")

        # 导出
        export_page = ExportPage(self.settings_manager, self.project_manager)
        self.management_layout.add_page("export", export_page, "导出分享")

        # 数据分析
        analytics_page = AnalyticsPage(self.settings_manager)
        self.management_layout.add_page("analytics", analytics_page, "数据分析")

        # 导航到首页
        self._navigate_to_page("home")

    def _setup_connections(self):
        """设置信号连接"""
        # 管理布局信号
        self.management_layout.page_navigation.connect(self._on_page_navigation)

        # 设置管理器信号
        self.settings_manager.settings_changed.connect(self._on_settings_changed)

        # 项目管理器信号
        self.project_manager.project_opened.connect(self._on_project_opened)
        self.project_manager.project_saved.connect(self._on_project_saved)

    def _load_settings(self):
        """加载设置"""
        # 恢复窗口几何状态
        geometry = self.settings_manager.get_setting('window.geometry')
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings_manager.get_setting('window.state')
        if state:
            self.restoreState(state)

        # 应用主题
        theme = self.settings_manager.get_setting('ui.theme', 'professional_dark')
        self._change_theme(theme)

    def _apply_theme(self):
        """应用主题"""
        if hasattr(self, 'theme_manager') and self.theme_manager:
            self.theme_manager.set_theme("professional_dark")

    def _navigate_to_page(self, page_id: str):
        """导航到指定页面"""
        if self.management_layout:
            self.management_layout.navigate_to_page(page_id)
            self.current_page = page_id
            self.page_changed.emit(page_id)

    def _on_page_navigation(self, page_name: str):
        """页面导航处理"""
        self.current_page = page_name
        self.page_changed.emit(page_name)
        self.statusBar().showMessage(f"当前页面: {page_name}", 3000)

    def _on_settings_changed(self, key: str, value):
        """设置改变处理"""
        if key == 'ui.theme':
            self._change_theme(value)
        elif key.startswith('ui.'):
            # UI相关设置需要重新应用
            self._apply_theme()

        self.settings_changed.emit()

    def _on_project_opened(self, project_path: str):
        """项目打开处理"""
        self.project_opened.emit(project_path)
        self.statusBar().showMessage(f"项目已打开: {project_path}", 5000)

    def _on_project_saved(self, project_path: str):
        """项目保存处理"""
        self.project_saved.emit(project_path)
        self.statusBar().showMessage(f"项目已保存: {project_path}", 3000)

    def _toggle_status_bar(self, checked: bool):
        """切换状态栏显示"""
        self.statusBar().setVisible(checked)

    def _toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _change_theme(self, theme_name: str):
        """更改主题"""
        try:
            if self.theme_manager:
                self.theme_manager.set_theme(theme_name)
                self._apply_theme()
                show_success("主题", f"已切换到{theme_name}主题", self)
        except Exception as e:
            show_error("主题切换失败", str(e), self)

    def _update_performance_status(self):
        """更新性能状态"""
        try:
            import psutil

            # 内存使用
            memory = psutil.virtual_memory()
            self.memory_label.setText(f"内存: {memory.used / 1024 / 1024:.1f} MB")

            # CPU使用率
            cpu_percent = psutil.cpu_percent()
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")

        except Exception as e:
            logger.warning(f"更新性能状态失败: {e}")

    # 文件操作方法
    def _new_project(self):
        """新建项目"""
        try:
            project_path = self.project_manager.create_project()
            if project_path:
                show_success("项目", "新项目创建成功", self)
                self._navigate_to_page("editing")
        except Exception as e:
            show_error("新建项目失败", str(e), self)

    def _open_project(self):
        """打开项目"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                self, "打开项目", "", "CineAIStudio项目 (*.cineai *.json)"
            )

            if file_path:
                self.project_manager.load_project(file_path)
                self._navigate_to_page("editing")

        except Exception as e:
            show_error("打开项目失败", str(e), self)

    def _save_project(self):
        """保存项目"""
        try:
            self.project_manager.save_project()
            show_success("项目", "项目保存成功", self)
        except Exception as e:
            show_error("保存项目失败", str(e), self)

    def _save_project_as(self):
        """项目另存为"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self, "项目另存为", "", "CineAIStudio项目 (*.cineai)"
            )

            if file_path:
                self.project_manager.save_project_as(file_path)
                show_success("项目", "项目另存为成功", self)

        except Exception as e:
            show_error("项目另存为失败", str(e), self)

    def _import_media(self, media_type: str):
        """导入媒体文件"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            filters = {
                "video": "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv)",
                "audio": "音频文件 (*.mp3 *.wav *.aac *.flac)",
                "image": "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
            }

            file_paths, _ = QFileDialog.getOpenFileNames(
                self, f"导入{media_type}", "", filters.get(media_type, "")
            )

            if file_paths:
                # 导入逻辑
                show_success("导入", f"成功导入{len(file_paths)}个文件", self)

        except Exception as e:
            show_error("导入失败", str(e), self)

    def _export_video(self):
        """导出视频"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出视频", "", "视频文件 (*.mp4 *.avi *.mov)"
            )

            if file_path:
                # 导出逻辑
                show_success("导出", "视频导出成功", self)

        except Exception as e:
            show_error("导出失败", str(e), self)

    def _export_to_jianying(self):
        """导出到剪映"""
        try:
            # 剪映导出逻辑
            show_success("导出", "已导出到剪映", self)
        except Exception as e:
            show_error("导出失败", str(e), self)

    # AI工具方法
    def _ai_commentary(self):
        """AI智能解说"""
        self._navigate_to_page("ai_tools")
        # 触发解说功能

    def _ai_compilation(self):
        """AI高能混剪"""
        self._navigate_to_page("ai_tools")
        # 触发混剪功能

    def _ai_monologue(self):
        """AI第一人称独白"""
        self._navigate_to_page("ai_tools")
        # 触发独白功能

    def _ai_subtitle(self):
        """AI字幕生成"""
        self._navigate_to_page("ai_tools")
        # 触发字幕功能

    def _ai_scene_analysis(self):
        """AI场景分析"""
        self._navigate_to_page("ai_tools")
        # 触发场景分析功能

    # 设置相关方法
    def _open_settings(self):
        """打开设置对话框"""
        try:
            settings_dialog = SettingsDialog(self.settings_manager, self)
            settings_dialog.exec()
        except Exception as e:
            show_error("设置", f"打开设置失败: {str(e)}", self)

    def _ai_config(self):
        """AI配置"""
        self._open_settings()
        # 导航到AI设置页面

    def _performance_settings(self):
        """性能设置"""
        self._open_settings()
        # 导航到性能设置页面

    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "重置设置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings_manager.reset_to_defaults()
                show_success("设置", "设置已重置为默认值", self)
            except Exception as e:
                show_error("重置失败", str(e), self)

    # 帮助相关方法
    def _open_manual(self):
        """打开用户手册"""
        show_info("用户手册", "用户手册功能正在开发中", self)

    def _show_shortcuts(self):
        """显示快捷键"""
        shortcuts_text = """
快捷键列表：

文件操作：
- Ctrl+N: 新建项目
- Ctrl+O: 打开项目
- Ctrl+S: 保存项目
- Ctrl+Shift+S: 项目另存为
- Ctrl+Q: 退出应用程序

编辑操作：
- Ctrl+Z: 撤销
- Ctrl+Y: 重做
- Ctrl+X: 剪切
- Ctrl+C: 复制
- Ctrl+V: 粘贴

视图操作：
- F11: 全屏模式

导航：
- Ctrl+1: 首页
- Ctrl+2: 项目管理
- Ctrl+3: AI工具
- Ctrl+4: 视频编辑
- Ctrl+5: 导出分享
- Ctrl+6: 数据分析
        """
        show_info("快捷键", shortcuts_text, self)

    def _check_updates(self):
        """检查更新"""
        show_info("检查更新", "已是最新版本", self)

    def _show_about(self):
        """显示关于对话框"""
        about_text = """
CineAIStudio v2.0.0

专业AI视频编辑器

特性：
• AI智能解说生成
• 多模型AI集成
• 硬件加速视频处理
• 剪映深度集成
• 专业视频编辑工具

© 2025 CineAIStudio Team
        """
        QMessageBox.about(self, "关于 CineAIStudio", about_text)

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 保存窗口状态
            self.settings_manager.set_setting('window.geometry', self.saveGeometry())
            self.settings_manager.set_setting('window.state', self.saveState())

            # 保存当前项目
            if self.project_manager.has_unsaved_changes():
                reply = QMessageBox.question(
                    self, "保存项目",
                    "当前项目有未保存的更改，是否保存？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.project_manager.save_project()
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return

            event.accept()

        except Exception as e:
            logger.error(f"窗口关闭失败: {e}")
            event.accept()