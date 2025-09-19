#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一专业主窗口 - 整合所有最佳功能的完整视频编辑器界面
基于 professional_main_window.py 并整合 professional_video_editor_ui.py 的增强功能
"""

import os
import sys
import json
import psutil
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, QMenuBar, QDockWidget,
    QStackedWidget, QLabel, QFrame, QSizePolicy, QApplication, QStyleFactory,
    QScrollArea, QTabWidget, QMenu, QProgressDialog, QSplashScreen,
    QShortcut, QKeySequence, QToolButton, QPushButton, QComboBox, QSpinBox,
    QSlider, QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QLineEdit,
    QTextEdit, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QListView, QHeaderView,
    QProgressBar, QDialog, QGridLayout, QSpacerItem
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QPoint, QRect, QSettings, QThread, QThreadPool,
    QMimeData, QUrl, QEvent, pyqtSlot, QBuffer, QIODevice, QByteArray, QPointF,
    QRectF, QMargins, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QMutex, QMutexLocker
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont, QPalette, QColor, QCursor, QFontMetrics, QDragEnterEvent,
    QDropEvent, QKeySequence, QDrag, QPainter, QBrush, QPen, QLinearGradient,
    QRadialGradient, QConicalGradient, QPainterPath, QTransform, QPolygon,
    QTextCharFormat, QTextFormat, QFontInfo, QTextCursor, QSyntaxHighlighter,
    QTextDocument, QIntValidator, QDoubleValidator, QRegularExpressionValidator,
    QStandardItemModel, QStandardItem, QAction, QFontDatabase, QCloseEvent
)

# 导入专业UI系统
from .professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme,
    FontScheme, SpacingScheme, create_style_engine, get_color, create_font
)

# 导入组件
from media_library_component import MediaLibraryPanel
from video_preview_component import ProfessionalVideoPreviewPanel
from effects_component import EffectsPanel
from timeline_editor_component import TimelineEditor
from ai_tools_component import AIToolsPanel
from .components.properties_panel import PropertiesPanel
from .components.professional_theme_manager import ProfessionalThemeManager, ThemeConfig
from playback_component import PlaybackControls
from project_manager_component import ProjectPanel
from .components.timeline_controls import TimelineControls

# 导入核心管理器
from ..core.project_manager import ProjectManager
from ..core.video_manager import VideoManager
from ..ai import AIManager
from ..config.settings_manager import SettingsManager


class ApplicationState(Enum):
    """应用状态"""
    INITIALIZING = "initializing"
    READY = "ready"
    LOADING_PROJECT = "loading_project"
    SAVING_PROJECT = "saving_project"
    RENDERING = "rendering"
    BUSY = "busy"


class LayoutMode(Enum):
    """布局模式"""
    DEFAULT = "default"           # 默认布局
    EDITING = "editing"           # 编辑布局
    PREVIEW = "preview"           # 预览布局
    FULLSCREEN = "fullscreen"     # 全屏布局
    COMPACT = "compact"          # 紧凑布局
    FOCUS = "focus"              # 专注模式


class EditorMode(Enum):
    """编辑器模式"""
    SELECT = "select"             # 选择模式
    CROP = "crop"                # 裁剪模式
    TEXT = "text"                # 文字模式
    PEN = "pen"                  # 画笔模式
    HAND = "hand"                # 手动模式


@dataclass
class ApplicationConfig:
    """应用配置"""
    window_geometry: bytes = None
    window_state: bytes = None
    theme: str = "dark_professional"
    layout_mode: str = "default"
    editor_mode: str = "select"
    auto_save: bool = True
    auto_save_interval: int = 300  # 5分钟
    max_recent_files: int = 10
    language: str = "zh_CN"
    hardware_acceleration: bool = True
    cache_size_mb: int = 1024  # 1GB
    memory_monitoring: bool = True
    memory_update_interval: int = 1000  # 1秒


class ProfessionalMainWindow(QMainWindow):
    """统一专业主窗口 - 整合所有最佳功能"""

    # 信号定义
    theme_changed = pyqtSignal(ThemeConfig)          # 主题变更信号
    layout_changed = pyqtSignal(LayoutMode)           # 布局变更信号
    editor_mode_changed = pyqtSignal(EditorMode)      # 编辑器模式变更信号
    state_changed = pyqtSignal(ApplicationState)      # 状态变更信号
    project_loaded = pyqtSignal(str)                 # 项目加载信号
    project_saved = pyqtSignal(str)                 # 项目保存信号
    rendering_progress = pyqtSignal(int)             # 渲染进度信号
    rendering_completed = pyqtSignal(str)            # 渲染完成信号
    error_occurred = pyqtSignal(str)                 # 错误信号
    memory_usage_updated = pyqtSignal(float)         # 内存使用更新信号

    def __init__(self):
        super().__init__()

        # 初始化应用状态
        self.app_state = ApplicationState.INITIALIZING
        self.current_layout = LayoutMode.DEFAULT
        self.current_editor_mode = EditorMode.SELECT
        self.is_dark_theme = True
        self.is_playing = False
        self.current_time = 0.0
        self.video_duration = 0.0

        # 加载配置
        self.config = self._load_config()

        # 初始化管理器
        self.style_engine = None
        self.theme_manager = None
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制线程数

        # 初始化核心管理器
        self.settings_manager = SettingsManager()
        self.project_manager = ProjectManager(self.settings_manager)
        self.video_manager = VideoManager()
        self.ai_manager = AIManager(self.settings_manager)

        # 设置窗口属性
        self._setup_window_properties()

        # 创建核心组件
        self._create_core_components()

        # 创建UI组件
        self._create_ui()

        # 初始化组件
        self._initialize_components()

        # 连接信号
        self._connect_signals()

        # 设置键盘快捷键
        self._setup_keyboard_shortcuts()

        # 设置内存监控
        self._setup_memory_monitoring()

        # 加载设置
        self._load_settings()

        # 设置自动保存
        self._setup_auto_save()

        # 更新状态
        self.app_state = ApplicationState.READY
        self.state_changed.emit(self.app_state)

        # 显示欢迎信息
        self._show_welcome_message()

    def _setup_window_properties(self):
        """设置窗口属性"""
        self.setObjectName("main_window")
        self.setWindowTitle("CineAIStudio - 专业AI视频编辑器")
        self.setMinimumSize(1200, 800)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 设置窗口图标
        self._set_window_icon()

        # 接受文件拖放
        self.setAcceptDrops(True)

        # 设置应用程序样式
        QApplication.setStyle(QStyleFactory.create("Fusion"))

    def _set_window_icon(self):
        """设置窗口图标"""
        icon_paths = [
            "resources/icons/app_icon.png",
            "resources/icons/video_editor.png",
            ":/icons/app_icon"
        ]

        for path in icon_paths:
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                break

    def _create_core_components(self):
        """创建核心组件"""
        # 创建样式引擎
        self.style_engine = create_style_engine(
            UITheme.DARK if self.config.theme.startswith("dark") else UITheme.LIGHT
        )

        # 创建主题管理器
        self.theme_manager = ProfessionalThemeManager()
        self.theme_manager.set_style_engine(self.style_engine)

        # 应用样式
        self.style_engine.set_theme(
            UITheme.DARK if self.config.theme.startswith("dark") else UITheme.LIGHT
        )

    def _create_ui(self):
        """创建用户界面"""
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建菜单栏
        self._create_menu_bar()

        # 创建工具栏
        self._create_toolbars()

        # 创建主工作区
        self._create_main_workspace()

        # 创建状态栏
        self._create_status_bar()

        # 创建停靠面板
        self._create_dock_panels()

        # 应用样式
        self._apply_styles()

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setObjectName("main_menubar")

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 新建项目
        new_project_action = QAction("📄 新建项目(&N)", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.setStatusTip("创建新的视频项目")
        new_project_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_project_action)

        # 打开项目
        open_project_action = QAction("📂 打开项目(&O)", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.setStatusTip("打开现有的视频项目")
        open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_project_action)

        # 最近文件
        self.recent_files_menu = file_menu.addMenu("📚 最近文件")
        self._update_recent_files_menu()

        file_menu.addSeparator()

        # 保存项目
        save_project_action = QAction("💾 保存项目(&S)", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.setStatusTip("保存当前项目")
        save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_project_action)

        # 另存为
        save_as_action = QAction("💾 另存为(&A)", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setStatusTip("项目另存为")
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 导入媒体
        import_media_action = QAction("📥 导入媒体(&I)", self)
        import_media_action.setShortcut("Ctrl+I")
        import_media_action.setStatusTip("导入媒体文件")
        import_media_action.triggered.connect(self._on_import_media)
        file_menu.addAction(import_media_action)

        file_menu.addSeparator()

        # 导出视频
        export_menu = file_menu.addMenu("📤 导出")

        export_video_action = QAction("🎬 导出视频(&V)", self)
        export_video_action.setShortcut("Ctrl+E")
        export_video_action.setStatusTip("导出为视频文件")
        export_video_action.triggered.connect(self._on_export_video)
        export_menu.addAction(export_video_action)

        export_jianying_action = QAction("🎯 导出到剪映(&J)", self)
        export_jianying_action.setStatusTip("导出为剪映项目格式")
        export_jianying_action.triggered.connect(self._on_export_jianying)
        export_menu.addAction(export_jianying_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("🚪 退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        # 撤销/重做
        undo_action = QAction("↶ 撤销(&U)", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setStatusTip("撤销上一步操作")
        edit_menu.addAction(undo_action)

        redo_action = QAction("↷ 重做(&R)", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setStatusTip("重做上一步操作")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # 剪切/复制/粘贴
        cut_action = QAction("✂️ 剪切(&T)", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.setStatusTip("剪切选中内容")
        edit_menu.addAction(cut_action)

        copy_action = QAction("📋 复制(&C)", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.setStatusTip("复制选中内容")
        edit_menu.addAction(copy_action)

        paste_action = QAction("📌 粘贴(&P)", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.setStatusTip("粘贴内容")
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        # 首选项
        preferences_action = QAction("⚙️ 首选项(&P)", self)
        preferences_action.setStatusTip("打开首选项")
        preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(preferences_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 布局子菜单
        layout_menu = view_menu.addMenu("📐 布局(&L)")

        default_layout_action = QAction("🏠 默认布局(&D)", self)
        default_layout_action.setCheckable(True)
        default_layout_action.setChecked(True)
        default_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.DEFAULT))
        layout_menu.addAction(default_layout_action)

        editing_layout_action = QAction("✏️ 编辑布局(&E)", self)
        editing_layout_action.setCheckable(True)
        editing_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.EDITING))
        layout_menu.addAction(editing_layout_action)

        preview_layout_action = QAction("👁️ 预览布局(&P)", self)
        preview_layout_action.setCheckable(True)
        preview_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.PREVIEW))
        layout_menu.addAction(preview_layout_action)

        compact_layout_action = QAction("📦 紧凑布局(&C)", self)
        compact_layout_action.setCheckable(True)
        compact_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.COMPACT))
        layout_menu.addAction(compact_layout_action)

        focus_layout_action = QAction("🎯 专注模式(&F)", self)
        focus_layout_action.setCheckable(True)
        focus_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.FOCUS))
        layout_menu.addAction(focus_layout_action)

        fullscreen_layout_action = QAction("🖥️ 全屏布局(&F)", self)
        fullscreen_layout_action.setCheckable(True)
        fullscreen_layout_action.triggered.connect(lambda: self._change_layout(LayoutMode.FULLSCREEN))
        layout_menu.addAction(fullscreen_layout_action)

        view_menu.addSeparator()

        # 面板显示子菜单
        panels_menu = view_menu.addMenu("🔲 面板(&P)")

        panel_actions = {}
        panel_names = [
            ("媒体库", "media_library_component"),
            ("特效", "effects"),
            ("AI工具", "ai_tools"),
            ("属性", "properties"),
            ("项目", "project"),
            ("历史记录", "history")
        ]

        for display_name, panel_id in panel_names:
            action = QAction(display_name, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, pid=panel_id: self._toggle_panel(pid, checked))
            panels_menu.addAction(action)
            panel_actions[panel_id] = action

        view_menu.addSeparator()

        # 主题子菜单
        theme_menu = view_menu.addMenu("🎨 主题(&T)")

        dark_theme_action = QAction("🌙 深色主题(&D)", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(self.config.theme.startswith("dark"))
        dark_theme_action.triggered.connect(lambda: self._change_theme(UITheme.DARK))
        theme_menu.addAction(dark_theme_action)

        light_theme_action = QAction("☀️ 浅色主题(&L)", self)
        light_theme_action.setCheckable(True)
        light_theme_action.setChecked(not self.config.theme.startswith("dark"))
        light_theme_action.triggered.connect(lambda: self._change_theme(UITheme.LIGHT))
        theme_menu.addAction(light_theme_action)

        theme_menu.addSeparator()

        theme_settings_action = QAction("🎯 主题设置(&S)", self)
        theme_settings_action.triggered.connect(self._on_theme_settings)
        theme_menu.addAction(theme_settings_action)

        view_menu.addSeparator()

        # 缩放控制
        zoom_in_action = QAction("🔍 放大(&I)", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setStatusTip("放大界面")
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("🔍 缩小(&O)", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setStatusTip("缩小界面")
        view_menu.addAction(zoom_out_action)

        zoom_reset_action = QAction("🔄 重置缩放(&R)", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.setStatusTip("重置缩放")
        view_menu.addAction(zoom_reset_action)

        # AI功能菜单
        ai_menu = menubar.addMenu("AI功能(&A)")

        ai_subtitle_action = QAction("🎤 AI字幕识别", self)
        ai_subtitle_action.setStatusTip("使用AI识别视频字幕")
        ai_subtitle_action.triggered.connect(self._on_ai_subtitle)
        ai_menu.addAction(ai_subtitle_action)

        ai_voiceover_action = QAction("🗣️ AI配音生成", self)
        ai_voiceover_action.setStatusTip("使用AI生成配音")
        ai_voiceover_action.triggered.connect(self._on_ai_voiceover)
        ai_menu.addAction(ai_voiceover_action)

        ai_enhance_action = QAction("🎨 AI画质增强", self)
        ai_enhance_action.setStatusTip("使用AI增强画质")
        ai_enhance_action.triggered.connect(self._on_ai_enhance)
        ai_menu.addAction(ai_enhance_action)

        ai_style_transfer_action = QAction("🎭 AI风格迁移", self)
        ai_style_transfer_action.setStatusTip("使用AI进行风格迁移")
        ai_style_transfer_action.triggered.connect(self._on_ai_style_transfer)
        ai_menu.addAction(ai_style_transfer_action)

        ai_scene_analysis_action = QAction("🎯 AI场景分析", self)
        ai_scene_analysis_action.setStatusTip("使用AI分析视频场景")
        ai_scene_analysis_action.triggered.connect(self._on_ai_scene_analysis)
        ai_menu.addAction(ai_scene_analysis_action)

        ai_menu.addSeparator()

        ai_compilation_action = QAction("⚡ AI高能混剪", self)
        ai_compilation_action.setStatusTip("使用AI生成精彩混剪")
        ai_compilation_action.triggered.connect(self._on_ai_compilation)
        ai_menu.addAction(ai_compilation_action)

        ai_commentary_action = QAction("🎬 AI短剧解说", self)
        ai_commentary_action.setStatusTip("使用AI生成短剧解说")
        ai_commentary_action.triggered.connect(self._on_ai_commentary)
        ai_menu.addAction(ai_commentary_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        # 视频工具
        video_tools_menu = tools_menu.addMenu("🎬 视频工具(&V)")

        video_converter_action = QAction("🔄 视频转换器", self)
        video_converter_action.setStatusTip("转换视频格式")
        video_converter_action.triggered.connect(self._on_video_converter)
        video_tools_menu.addAction(video_converter_action)

        audio_extractor_action = QAction("🎵 音频提取器", self)
        audio_extractor_action.setStatusTip("从视频中提取音频")
        audio_extractor_action.triggered.connect(self._on_audio_extractor)
        video_tools_menu.addAction(audio_extractor_action)

        thumbnail_generator_action = QAction("🖼️ 缩略图生成器", self)
        thumbnail_generator_action.setStatusTip("批量生成视频缩略图")
        thumbnail_generator_action.triggered.connect(self._on_thumbnail_generator)
        video_tools_menu.addAction(thumbnail_generator_action)

        tools_menu.addSeparator()

        # 批量处理
        batch_processor_action = QAction("📦 批量处理器", self)
        batch_processor_action.setStatusTip("批量处理视频文件")
        batch_processor_action.triggered.connect(self._on_batch_processor)
        tools_menu.addAction(batch_processor_action)

        tools_menu.addSeparator()

        # 设置
        settings_action = QAction("⚙️ 设置(&S)", self)
        settings_action.setStatusTip("打开设置")
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)

        # 窗口菜单
        window_menu = menubar.addMenu("窗口(&W)")

        # 窗口操作
        minimize_action = QAction("➖ 最小化(&M)", self)
        minimize_action.setShortcut("Ctrl+M")
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)

        maximize_action = QAction("⬜ 最大化(&X)", self)
        maximize_action.triggered.connect(self.showMaximized)
        window_menu.addAction(maximize_action)

        window_menu.addSeparator()

        # 关闭所有面板
        close_all_panels_action = QAction("❌ 关闭所有面板(&A)", self)
        close_all_panels_action.triggered.connect(self._close_all_panels)
        window_menu.addAction(close_all_panels_action)

        # 重置布局
        reset_layout_action = QAction("🔄 重置布局(&R)", self)
        reset_layout_action.triggered.connect(self._reset_layout)
        window_menu.addAction(reset_layout_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        # 文档和教程
        documentation_action = QAction("📚 文档(&D)", self)
        documentation_action.setStatusTip("查看文档")
        documentation_action.triggered.connect(self._on_documentation)
        help_menu.addAction(documentation_action)

        tutorial_action = QAction("🎓 教程(&T)", self)
        tutorial_action.setStatusTip("观看教程")
        tutorial_action.triggered.connect(self._on_tutorial)
        help_menu.addAction(tutorial_action)

        help_menu.addSeparator()

        # 快捷键
        shortcuts_action = QAction("⌨️ 快捷键(&K)", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.setStatusTip("查看快捷键")
        shortcuts_action.triggered.connect(self._on_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        # 检查更新
        check_updates_action = QAction("🔄 检查更新(&U)", self)
        check_updates_action.setStatusTip("检查软件更新")
        check_updates_action.triggered.connect(self._on_check_updates)
        help_menu.addAction(check_updates_action)

        help_menu.addSeparator()

        # 关于
        about_action = QAction("ℹ️ 关于(&A)", self)
        about_action.setStatusTip("关于本软件")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        self.main_toolbar = QToolBar("主工具栏")
        self.main_toolbar.setObjectName("main_toolbar")
        self.main_toolbar.setMovable(False)
        self.main_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.main_toolbar)

        # 文件操作
        new_project_btn = self.main_toolbar.addAction("📄 新建")
        new_project_btn.setToolTip("新建项目 (Ctrl+N)")
        new_project_btn.triggered.connect(self._on_new_project)

        open_project_btn = self.main_toolbar.addAction("📂 打开")
        open_project_btn.setToolTip("打开项目 (Ctrl+O)")
        open_project_btn.triggered.connect(self._on_open_project)

        save_project_btn = self.main_toolbar.addAction("💾 保存")
        save_project_btn.setToolTip("保存项目 (Ctrl+S)")
        save_project_btn.triggered.connect(self._on_save_project)

        self.main_toolbar.addSeparator()

        # 编辑操作
        undo_btn = self.main_toolbar.addAction("↶ 撤销")
        undo_btn.setToolTip("撤销 (Ctrl+Z)")

        redo_btn = self.main_toolbar.addAction("↷ 重做")
        redo_btn.setToolTip("重做 (Ctrl+Y)")

        self.main_toolbar.addSeparator()

        # 导入导出
        import_btn = self.main_toolbar.addAction("📥 导入")
        import_btn.setToolTip("导入媒体 (Ctrl+I)")
        import_btn.triggered.connect(self._on_import_media)

        export_btn = self.main_toolbar.addAction("📤 导出")
        export_btn.setToolTip("导出视频 (Ctrl+E)")
        export_btn.triggered.connect(self._on_export_video)

        # 播放控制工具栏
        self.playback_toolbar = QToolBar("播放控制")
        self.playback_toolbar.setObjectName("playback_toolbar")
        self.playback_toolbar.setMovable(False)
        self.playback_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.playback_toolbar)

        # 创建播放控制组件
        self.playback_controls = PlaybackControls()
        self.playback_toolbar.addWidget(self.playback_controls)

        # 编辑工具栏
        self.edit_toolbar = QToolBar("编辑工具")
        self.edit_toolbar.setObjectName("edit_toolbar")
        self.edit_toolbar.setMovable(True)
        self.edit_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.edit_toolbar)

        # 编辑工具按钮组
        self.edit_tool_group = QButtonGroup(self)

        self.select_tool_btn = QToolButton()
        self.select_tool_btn.setText("👆 选择")
        self.select_tool_btn.setToolTip("选择工具 (V)")
        self.select_tool_btn.setCheckable(True)
        self.select_tool_btn.setChecked(True)
        self.edit_tool_group.addButton(self.select_tool_btn)
        self.edit_toolbar.addWidget(self.select_tool_btn)

        self.crop_tool_btn = QToolButton()
        self.crop_tool_btn.setText("🔲 裁剪")
        self.crop_tool_btn.setToolTip("裁剪工具 (C)")
        self.crop_tool_btn.setCheckable(True)
        self.edit_tool_group.addButton(self.crop_tool_btn)
        self.edit_toolbar.addWidget(self.crop_tool_btn)

        self.text_tool_btn = QToolButton()
        self.text_tool_btn.setText("📝 文字")
        self.text_tool_btn.setToolTip("文字工具 (T)")
        self.text_tool_btn.setCheckable(True)
        self.edit_tool_group.addButton(self.text_tool_btn)
        self.edit_toolbar.addWidget(self.text_tool_btn)

        self.pen_tool_btn = QToolButton()
        self.pen_tool_btn.setText("✏️ 画笔")
        self.pen_tool_btn.setToolTip("画笔工具 (P)")
        self.pen_tool_btn.setCheckable(True)
        self.edit_tool_group.addButton(self.pen_tool_btn)
        self.edit_toolbar.addWidget(self.pen_tool_btn)

        self.hand_tool_btn = QToolButton()
        self.hand_tool_btn.setText("👋 手动")
        self.hand_tool_btn.setToolTip("手动工具 (H)")
        self.hand_tool_btn.setCheckable(True)
        self.edit_tool_group.addButton(self.hand_tool_btn)
        self.edit_toolbar.addWidget(self.hand_tool_btn)

        # 连接编辑工具信号
        self.edit_tool_group.buttonClicked.connect(self._on_editor_tool_changed)

        # AI工具栏
        self.ai_toolbar = QToolBar("AI工具")
        self.ai_toolbar.setObjectName("ai_toolbar")
        self.ai_toolbar.setMovable(True)
        self.ai_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, self.ai_toolbar)

        # AI工具按钮
        self.ai_subtitle_btn = self.ai_toolbar.addAction("🎤 AI字幕")
        self.ai_subtitle_btn.setToolTip("AI字幕识别")
        self.ai_subtitle_btn.triggered.connect(self._on_ai_subtitle)

        self.ai_voice_btn = self.ai_toolbar.addAction("🗣️ AI配音")
        self.ai_voice_btn.setToolTip("AI配音生成")
        self.ai_voice_btn.triggered.connect(self._on_ai_voiceover)

        self.ai_enhance_btn = self.ai_toolbar.addAction("🎨 AI增强")
        self.ai_enhance_btn.setToolTip("AI画质增强")
        self.ai_enhance_btn.triggered.connect(self._on_ai_enhance)

        self.ai_analysis_btn = self.ai_toolbar.addAction("🎯 AI分析")
        self.ai_analysis_btn.setToolTip("AI场景分析")
        self.ai_analysis_btn.triggered.connect(self._on_ai_scene_analysis)

    def _create_main_workspace(self):
        """创建主工作区"""
        # 创建主分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # 创建左侧面板区域
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)
        self.main_splitter.addWidget(self.left_panel)

        # 创建中央工作区
        self.center_area = self._create_center_area()
        self.main_splitter.addWidget(self.center_area)

        # 创建右侧面板区域
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.main_splitter.addWidget(self.right_panel)

        # 设置分割器比例
        self.main_splitter.setStretchFactor(0, 2)  # 左侧
        self.main_splitter.setStretchFactor(1, 6)  # 中央
        self.main_splitter.setStretchFactor(2, 2)  # 右侧

    def _create_center_area(self) -> QWidget:
        """创建中央工作区"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # 创建垂直分割器
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_layout.addWidget(self.center_splitter)

        # 视频预览区域
        self.video_preview = ProfessionalVideoPreviewPanel()
        self.center_splitter.addWidget(self.video_preview)

        # 时间线区域
        self.timeline_widget = self._create_timeline_area()
        self.center_splitter.addWidget(self.timeline_widget)

        # 设置分割器比例
        self.center_splitter.setStretchFactor(0, 6)  # 预览区域
        self.center_splitter.setStretchFactor(1, 4)  # 时间线区域

        return center_widget

    def _create_timeline_area(self) -> QWidget:
        """创建时间线区域"""
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)

        # 时间线控制工具栏
        self.timeline_controls = TimelineControls()
        timeline_layout.addWidget(self.timeline_controls)

        # 时间线编辑器
        self.timeline_editor = TimelineEditor(self.video_manager)
        timeline_layout.addWidget(self.timeline_editor)

        return timeline_widget

    def _create_status_bar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.statusbar.setObjectName("main_statusbar")
        self.setStatusBar(self.statusbar)

        # 状态信息
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 项目信息
        self.project_label = QLabel("未打开项目")
        self.statusbar.addPermanentWidget(self.project_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 分辨率信息
        self.resolution_label = QLabel("1920x1080")
        self.statusbar.addPermanentWidget(self.resolution_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 帧率信息
        self.fps_label = QLabel("30 FPS")
        self.statusbar.addPermanentWidget(self.fps_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 内存使用
        self.memory_label = QLabel("内存: 256 MB")
        self.statusbar.addPermanentWidget(self.memory_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 渲染进度
        self.render_progress_label = QLabel("渲染: --")
        self.statusbar.addPermanentWidget(self.render_progress_label)

        # 进度条
        self.render_progress_bar = QProgressBar()
        self.render_progress_bar.setFixedWidth(100)
        self.render_progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.render_progress_bar)

    def _create_dock_panels(self):
        """创建停靠面板"""
        # 媒体库面板
        self.media_library = MediaLibraryPanel(self.video_manager)
        self.media_library_dock = self._create_dock_panel("媒体库", self.media_library, Qt.DockWidgetArea.LeftDockWidgetArea)

        # 项目面板
        self.project_panel = ProjectPanel()
        self.project_dock = self._create_dock_panel("项目", self.project_panel, Qt.DockWidgetArea.LeftDockWidgetArea)

        # 特效面板
        self.effects_panel = EffectsPanel()
        self.effects_dock = self._create_dock_panel("特效", self.effects_panel, Qt.DockWidgetArea.RightDockWidgetArea)

        # AI工具面板
        self.ai_tools_panel = AIToolsPanel()
        self.ai_tools_dock = self._create_dock_panel("AI工具", self.ai_tools_panel, Qt.DockWidgetArea.RightDockWidgetArea)

        # 属性面板
        self.properties_panel = PropertiesPanel(self.ai_manager)
        self.properties_dock = self._create_dock_panel("属性", self.properties_panel, Qt.DockWidgetArea.RightDockWidgetArea)

        # 历史记录面板
        self.history_panel = QWidget()  # 临时创建，稍后完善
        self.history_dock = self._create_dock_panel("历史记录", self.history_panel, Qt.DockWidgetArea.LeftDockWidgetArea)

        # 标签化面板容器
        self.left_tab_widget = QTabWidget()
        self.left_tab_widget.addTab(self.media_library_dock, "媒体库")
        self.left_tab_widget.addTab(self.project_dock, "项目")
        self.left_tab_widget.addTab(self.history_dock, "历史记录")
        self.left_layout.addWidget(self.left_tab_widget)

        self.right_tab_widget = QTabWidget()
        self.right_tab_widget.addTab(self.effects_dock, "特效")
        self.right_tab_widget.addTab(self.ai_tools_dock, "AI工具")
        self.right_tab_widget.addTab(self.properties_dock, "属性")
        self.right_layout.addWidget(self.right_tab_widget)

    def _create_dock_panel(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        """创建停靠面板"""
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title.lower().replace(' ', '_')}_dock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        self.addDockWidget(area, dock)
        return dock

    def _setup_keyboard_shortcuts(self):
        """设置键盘快捷键"""
        # 播放控制
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self._toggle_playback)

        # 时间控制
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(self._seek_backward)

        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(self._seek_forward)

        self.home_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Home), self)
        self.home_shortcut.activated.connect(self._seek_start)

        self.end_shortcut = QShortcut(QKeySequence(Qt.Key.Key_End), self)
        self.end_shortcut.activated.connect(self._seek_end)

        # 编辑工具
        self.select_shortcut = QShortcut(QKeySequence("V"), self)
        self.select_shortcut.activated.connect(lambda: self.select_tool_btn.setChecked(True))

        self.crop_shortcut = QShortcut(QKeySequence("C"), self)
        self.crop_shortcut.activated.connect(lambda: self.crop_tool_btn.setChecked(True))

        self.text_shortcut = QShortcut(QKeySequence("T"), self)
        self.text_shortcut.activated.connect(lambda: self.text_tool_btn.setChecked(True))

        self.pen_shortcut = QShortcut(QKeySequence("P"), self)
        self.pen_shortcut.activated.connect(lambda: self.pen_tool_btn.setChecked(True))

        self.hand_shortcut = QShortcut(QKeySequence("H"), self)
        self.hand_shortcut.activated.connect(lambda: self.hand_tool_btn.setChecked(True))

        # 缩放控制
        self.zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        self.zoom_in_shortcut.activated.connect(self._zoom_in)

        self.zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        self.zoom_out_shortcut.activated.connect(self._zoom_out)

        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(self._zoom_reset)

    def _setup_memory_monitoring(self):
        """设置内存监控"""
        if self.config.memory_monitoring:
            self.memory_timer = QTimer()
            self.memory_timer.timeout.connect(self._update_memory_display)
            self.memory_timer.start(self.config.memory_update_interval)

    def _update_memory_display(self):
        """更新内存显示"""
        try:
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.memory_label.setText(f"内存: {memory_mb:.0f} MB")
            self.memory_usage_updated.emit(memory_mb)
        except:
            pass

    def _initialize_components(self):
        """初始化组件"""
        # 设置主题
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._on_theme_changed)

        # 初始化媒体库
        self.media_library.set_theme(self.is_dark_theme)

        # 初始化其他组件
        self.effects_panel.set_theme(self.is_dark_theme)
        self.video_preview.set_theme(self.is_dark_theme)
        self.timeline_editor.set_theme(self.is_dark_theme)
        self.ai_tools_panel.set_theme(self.is_dark_theme)
        self.properties_panel.set_theme(self.is_dark_theme)

        # 初始化播放控制
        if hasattr(self.playback_controls, 'play_pause_clicked'):
            self.playback_controls.play_pause_clicked.connect(self._toggle_playback)
        if hasattr(self.playback_controls, 'stop_clicked'):
            self.playback_controls.stop_clicked.connect(self._stop_playback)
        if hasattr(self.playback_controls, 'time_changed'):
            self.playback_controls.time_changed.connect(self._on_time_changed)

        # 初始化时间线控制
        if hasattr(self.timeline_controls, 'zoom_changed'):
            self.timeline_controls.zoom_changed.connect(self._on_timeline_zoom_changed)
        if hasattr(self.timeline_controls, 'snap_toggled'):
            self.timeline_controls.snap_toggled.connect(self._on_snap_toggled)

    def _connect_signals(self):
        """连接信号"""
        # 媒体库信号
        if hasattr(self.media_library, 'video_selected'):
            self.media_library.video_selected.connect(self._on_video_selected)

        # 视频预览信号
        if hasattr(self.video_preview, 'video_selected'):
            self.video_preview.video_selected.connect(self._on_video_selected)

        # 特效面板信号
        if hasattr(self.effects_panel, 'effect_applied'):
            self.effects_panel.effect_applied.connect(self._on_effect_applied)

        # AI工具面板信号
        if hasattr(self.ai_tools_panel, 'ai_task_started'):
            self.ai_tools_panel.ai_task_started.connect(self._on_ai_task_started)

        # 属性面板信号
        if hasattr(self.properties_panel, 'property_changed'):
            self.properties_panel.property_changed.connect(self._on_property_changed)

        # 时间线信号
        if hasattr(self.timeline_editor, 'timeline_changed'):
            self.timeline_editor.timeline_changed.connect(self._on_timeline_changed)
        if hasattr(self.timeline_editor, 'playback_position_changed'):
            self.timeline_editor.playback_position_changed.connect(self._on_playback_position_changed)

        # 主题变更信号
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._on_theme_changed)

        # 视频管理器信号
        self.video_manager.video_added.connect(self._on_video_added)
        self.video_manager.video_removed.connect(self._on_video_removed)
        self.video_manager.thumbnail_generated.connect(self._on_thumbnail_updated)
        self.video_manager.metadata_updated.connect(self._on_metadata_updated)

    def _apply_styles(self):
        """应用样式"""
        # 主窗口样式
        self.setStyleSheet(self.style_engine._generate_stylesheet())

        # 更新所有子组件主题
        self._update_all_components_theme()

    def _update_all_components_theme(self):
        """更新所有组件主题"""
        components = [
            self.media_library, self.effects_panel, self.video_preview,
            self.timeline_editor, self.ai_tools_panel, self.properties_panel,
            self.playback_controls, self.timeline_controls
        ]

        for component in components:
            if hasattr(component, 'set_theme'):
                component.set_theme(self.is_dark_theme)

    def _load_config(self) -> ApplicationConfig:
        """加载应用配置"""
        settings = QSettings("CineAIStudio", "VideoEditor")

        config = ApplicationConfig()
        config.window_geometry = settings.value("window_geometry")
        config.window_state = settings.value("window_state")
        config.theme = settings.value("theme", "dark_professional")
        config.layout_mode = settings.value("layout_mode", "default")
        config.editor_mode = settings.value("editor_mode", "select")
        config.auto_save = settings.value("auto_save", True, type=bool)
        config.auto_save_interval = settings.value("auto_save_interval", 300, type=int)
        config.max_recent_files = settings.value("max_recent_files", 10, type=int)
        config.language = settings.value("language", "zh_CN")
        config.hardware_acceleration = settings.value("hardware_acceleration", True, type=bool)
        config.cache_size_mb = settings.value("cache_size_mb", 1024, type=int)
        config.memory_monitoring = settings.value("memory_monitoring", True, type=bool)
        config.memory_update_interval = settings.value("memory_update_interval", 1000, type=int)

        return config

    def _save_config(self):
        """保存应用配置"""
        settings = QSettings("CineAIStudio", "VideoEditor")

        settings.setValue("window_geometry", self.saveGeometry())
        settings.setValue("window_state", self.saveState())
        settings.setValue("theme", self.config.theme)
        settings.setValue("layout_mode", self.config.layout_mode)
        settings.setValue("editor_mode", self.config.editor_mode)
        settings.setValue("auto_save", self.config.auto_save)
        settings.setValue("auto_save_interval", self.config.auto_save_interval)
        settings.setValue("max_recent_files", self.config.max_recent_files)
        settings.setValue("language", self.config.language)
        settings.setValue("hardware_acceleration", self.config.hardware_acceleration)
        settings.setValue("cache_size_mb", self.config.cache_size_mb)
        settings.setValue("memory_monitoring", self.config.memory_monitoring)
        settings.setValue("memory_update_interval", self.config.memory_update_interval)

    def _load_settings(self):
        """加载设置"""
        # 恢复窗口几何
        if self.config.window_geometry:
            self.restoreGeometry(self.config.window_geometry)

        # 恢复窗口状态
        if self.config.window_state:
            self.restoreState(self.config.window_state)

        # 应用布局模式
        layout_mode_map = {
            "default": LayoutMode.DEFAULT,
            "editing": LayoutMode.EDITING,
            "preview": LayoutMode.PREVIEW,
            "fullscreen": LayoutMode.FULLSCREEN,
            "compact": LayoutMode.COMPACT,
            "focus": LayoutMode.FOCUS
        }
        layout_mode = layout_mode_map.get(self.config.layout_mode, LayoutMode.DEFAULT)
        self._change_layout(layout_mode)

        # 应用编辑器模式
        editor_mode_map = {
            "select": EditorMode.SELECT,
            "crop": EditorMode.CROP,
            "text": EditorMode.TEXT,
            "pen": EditorMode.PEN,
            "hand": EditorMode.HAND
        }
        editor_mode = editor_mode_map.get(self.config.editor_mode, EditorMode.SELECT)
        self._change_editor_mode(editor_mode)

        # 应用主题
        if self.config.theme.startswith("dark"):
            self._change_theme(UITheme.DARK)
        else:
            self._change_theme(UITheme.LIGHT)

    def _setup_auto_save(self):
        """设置自动保存"""
        if self.config.auto_save:
            self.auto_save_timer = QTimer()
            self.auto_save_timer.timeout.connect(self._auto_save)
            self.auto_save_timer.start(self.config.auto_save_interval * 1000)  # 转换为毫秒

    def _auto_save(self):
        """自动保存"""
        if self.app_state == ApplicationState.READY:
            self.status_label.setText("自动保存中...")
            QTimer.singleShot(1000, lambda: self.status_label.setText("就绪"))

    def _change_layout(self, layout_mode: LayoutMode):
        """切换布局模式"""
        self.current_layout = layout_mode
        self.config.layout_mode = layout_mode.value

        # 根据布局模式调整界面
        if layout_mode == LayoutMode.FULLSCREEN:
            self.showFullScreen()
        else:
            if self.isFullScreen():
                self.showNormal()

            if layout_mode == LayoutMode.EDITING:
                # 编辑布局：隐藏部分面板，专注于编辑
                self.media_library_dock.hide()
                self.project_dock.hide()
                self.history_dock.hide()
                self.properties_dock.hide()
                self.ai_tools_dock.show()
                self.effects_dock.show()

            elif layout_mode == LayoutMode.PREVIEW:
                # 预览布局：最大化预览区域
                self.media_library_dock.hide()
                self.project_dock.hide()
                self.history_dock.hide()
                self.properties_dock.hide()
                self.ai_tools_dock.hide()
                self.effects_dock.hide()

                # 调整分割器比例
                self.center_splitter.setStretchFactor(0, 8)  # 预览区域
                self.center_splitter.setStretchFactor(1, 2)  # 时间线区域

            elif layout_mode == LayoutMode.COMPACT:
                # 紧凑布局：隐藏所有面板
                self.media_library_dock.hide()
                self.project_dock.hide()
                self.history_dock.hide()
                self.properties_dock.hide()
                self.ai_tools_dock.hide()
                self.effects_dock.hide()

                # 调整分割器比例
                self.center_splitter.setStretchFactor(0, 7)  # 预览区域
                self.center_splitter.setStretchFactor(1, 3)  # 时间线区域

            elif layout_mode == LayoutMode.FOCUS:
                # 专注模式：只显示预览和时间线
                self.media_library_dock.hide()
                self.project_dock.hide()
                self.history_dock.hide()
                self.properties_dock.show()
                self.ai_tools_dock.show()
                self.effects_dock.hide()

                # 调整分割器比例
                self.center_splitter.setStretchFactor(0, 7)  # 预览区域
                self.center_splitter.setStretchFactor(1, 3)  # 时间线区域

            else:  # DEFAULT
                # 默认布局：显示所有面板
                self.media_library_dock.show()
                self.project_dock.show()
                self.history_dock.show()
                self.properties_dock.show()
                self.ai_tools_dock.show()
                self.effects_dock.show()

                # 恢复默认分割器比例
                self.center_splitter.setStretchFactor(0, 6)  # 预览区域
                self.center_splitter.setStretchFactor(1, 4)  # 时间线区域

        self.layout_changed.emit(layout_mode)

    def _change_editor_mode(self, editor_mode: EditorMode):
        """切换编辑器模式"""
        self.current_editor_mode = editor_mode
        self.config.editor_mode = editor_mode.value

        # 更新工具栏按钮状态
        if editor_mode == EditorMode.SELECT:
            self.select_tool_btn.setChecked(True)
        elif editor_mode == EditorMode.CROP:
            self.crop_tool_btn.setChecked(True)
        elif editor_mode == EditorMode.TEXT:
            self.text_tool_btn.setChecked(True)
        elif editor_mode == EditorMode.PEN:
            self.pen_tool_btn.setChecked(True)
        elif editor_mode == EditorMode.HAND:
            self.hand_tool_btn.setChecked(True)

        self.editor_mode_changed.emit(editor_mode)

    def _change_theme(self, theme: UITheme):
        """切换主题"""
        self.is_dark_theme = (theme == UITheme.DARK)

        # 更新配置
        self.config.theme = "dark_professional" if self.is_dark_theme else "light_professional"

        # 更新样式引擎
        if self.style_engine:
            self.style_engine.set_theme(theme)

        # 更新所有组件主题
        self._update_all_components_theme()

        # 重新应用样式
        self._apply_styles()

    def _toggle_fullscreen(self, checked: bool):
        """切换全屏"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_panel(self, panel_id: str, visible: bool):
        """切换面板可见性"""
        panel_map = {
            "media_library_component": self.media_library_dock,
            "effects": self.effects_dock,
            "ai_tools": self.ai_tools_dock,
            "properties": self.properties_dock,
            "project": self.project_dock,
            "history": self.history_dock
        }

        if panel_id in panel_map:
            panel_map[panel_id].setVisible(visible)

    def _close_all_panels(self):
        """关闭所有面板"""
        for dock in [self.media_library_dock, self.effects_dock, self.ai_tools_dock,
                     self.properties_dock, self.project_dock, self.history_dock]:
            dock.setVisible(False)

    def _reset_layout(self):
        """重置布局"""
        # 显示所有面板
        for dock in [self.media_library_dock, self.effects_dock, self.ai_tools_dock,
                     self.properties_dock, self.project_dock, self.history_dock]:
            dock.setVisible(True)

        # 重置分割器大小
        self.main_splitter.setSizes([300, 800, 300])
        self.center_splitter.setSizes([600, 400])

        # 重置为默认布局
        self._change_layout(LayoutMode.DEFAULT)

    def _on_theme_changed(self, config: ThemeConfig):
        """主题变更处理"""
        self.theme_changed.emit(config)

    def _on_editor_tool_changed(self, button):
        """编辑工具变更处理"""
        tool_map = {
            self.select_tool_btn: EditorMode.SELECT,
            self.crop_tool_btn: EditorMode.CROP,
            self.text_tool_btn: EditorMode.TEXT,
            self.pen_tool_btn: EditorMode.PEN,
            self.hand_tool_btn: EditorMode.HAND
        }

        if button in tool_map:
            self._change_editor_mode(tool_map[button])

    def _on_video_selected(self, video_path: str):
        """视频选中处理"""
        # 在预览器中加载视频
        self.video_preview.load_video(video_path)

        # 更新状态栏
        self.status_label.setText(f"已加载视频: {os.path.basename(video_path)}")

    def _on_effect_applied(self, effect_preset, parameters):
        """特效应用处理"""
        self.status_label.setText(f"已应用特效: {effect_preset.name}")

    def _on_ai_task_started(self, task_type: str):
        """AI任务开始处理"""
        self.status_label.setText(f"AI处理中: {task_type}...")

    def _on_property_changed(self, property_name: str, value: Any):
        """属性变更处理"""
        self.status_label.setText(f"属性已更新: {property_name}")

    def _on_timeline_changed(self):
        """时间线变更处理"""
        # 更新状态栏
        clip_count = len(self.video_manager.timeline_clips)
        self.status_label.setText(f"时间线: {clip_count} 个片段")

    def _on_playback_position_changed(self, position_ms: int):
        """播放位置变更处理"""
        self.current_time = position_ms / 1000.0
        self._update_time_display()

    def _on_timeline_zoom_changed(self, zoom_level: float):
        """时间线缩放变更处理"""
        self.status_label.setText(f"时间线缩放: {zoom_level:.1f}x")

    def _on_snap_toggled(self, enabled: bool):
        """吸附开关变更处理"""
        self.status_label.setText(f"吸附: {'开启' if enabled else '关闭'}")

    def _on_time_changed(self, position_ms: int):
        """时间变更处理"""
        if not self.is_playing:  # 只在非播放状态下响应
            self.current_time = position_ms / 1000.0
            self._update_time_display()

    def _update_time_display(self):
        """更新时间显示"""
        current_str = self._format_time(self.current_time)
        duration_str = self._format_time(self.video_duration)

        if hasattr(self.playback_controls, 'set_time_display'):
            self.playback_controls.set_time_display(current_str, duration_str)

        # 更新状态栏显示播放位置
        self.status_label.setText(f"播放位置: {current_str}")

    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    # 播放控制方法
    def _toggle_playback(self):
        """切换播放状态"""
        self.is_playing = not self.is_playing

        if hasattr(self.playback_controls, 'set_playing_state'):
            self.playback_controls.set_playing_state(self.is_playing)

        if hasattr(self.video_preview, 'toggle_playback'):
            self.video_preview.toggle_playback()

        if self.is_playing:
            self.status_label.setText("播放中...")
        else:
            self.status_label.setText("已暂停")

    def _stop_playback(self):
        """停止播放"""
        self.is_playing = False
        self.current_time = 0.0

        if hasattr(self.playback_controls, 'set_playing_state'):
            self.playback_controls.set_playing_state(False)

        if hasattr(self.playback_controls, 'set_time_position'):
            self.playback_controls.set_time_position(0)

        if hasattr(self.video_preview, 'stop_playback'):
            self.video_preview.stop_playback()

        self.status_label.setText("已停止")

    def _seek_backward(self):
        """快退5秒"""
        self.current_time = max(0, self.current_time - 5)
        self._update_time_display()
        if hasattr(self.video_preview, 'seek_to'):
            self.video_preview.seek_to(self.current_time)

    def _seek_forward(self):
        """快进5秒"""
        self.current_time = min(self.video_duration, self.current_time + 5)
        self._update_time_display()
        if hasattr(self.video_preview, 'seek_to'):
            self.video_preview.seek_to(self.current_time)

    def _seek_start(self):
        """跳转到开始"""
        self.current_time = 0
        self._update_time_display()
        if hasattr(self.video_preview, 'seek_to'):
            self.video_preview.seek_to(self.current_time)

    def _seek_end(self):
        """跳转到结束"""
        self.current_time = self.video_duration
        self._update_time_display()
        if hasattr(self.video_preview, 'seek_to'):
            self.video_preview.seek_to(self.current_time)

    # 缩放控制方法
    def _zoom_in(self):
        """放大"""
        self.status_label.setText("界面已放大")
        # TODO: 实现界面缩放逻辑

    def _zoom_out(self):
        """缩小"""
        self.status_label.setText("界面已缩小")
        # TODO: 实现界面缩放逻辑

    def _zoom_reset(self):
        """重置缩放"""
        self.status_label.setText("缩放已重置")
        # TODO: 实现缩放重置逻辑

    # 菜单事件处理方法
    def _on_new_project(self):
        """新建项目"""
        QMessageBox.information(self, "新建项目", "新建项目功能开发中...")

    def _on_open_project(self):
        """打开项目"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("CineAIStudio项目文件 (*.vep)")

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self._load_project(file_paths[0])

    def _on_save_project(self):
        """保存项目"""
        QMessageBox.information(self, "保存项目", "保存项目功能开发中...")

    def _on_save_as(self):
        """另存为"""
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("CineAIStudio项目文件 (*.vep)")

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self.status_label.setText(f"项目另存为: {file_paths[0]}")

    def _on_import_media(self):
        """导入媒体"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("媒体文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.mp3 *.wav *.aac *.flac *.jpg *.png *.bmp *.tiff)")

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self._import_media_files(file_paths)

    def _on_export_video(self):
        """导出视频"""
        QMessageBox.information(self, "导出视频", "导出视频功能开发中...")

    def _on_export_jianying(self):
        """导出到剪映"""
        QMessageBox.information(self, "导出到剪映", "导出到剪映功能开发中...")

    def _on_preferences(self):
        """首选项"""
        QMessageBox.information(self, "首选项", "首选项功能开发中...")

    def _on_theme_settings(self):
        """主题设置"""
        from .components.professional_theme_manager import get_theme_dialog

        dialog = get_theme_dialog(self)
        if self.theme_manager:
            dialog.theme_manager = self.theme_manager

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 主题已应用
            pass

    def _on_ai_subtitle(self):
        """AI字幕识别"""
        QMessageBox.information(self, "AI字幕识别", "AI字幕识别功能开发中...")

    def _on_ai_voiceover(self):
        """AI配音生成"""
        QMessageBox.information(self, "AI配音生成", "AI配音生成功能开发中...")

    def _on_ai_enhance(self):
        """AI画质增强"""
        QMessageBox.information(self, "AI画质增强", "AI画质增强功能开发中...")

    def _on_ai_style_transfer(self):
        """AI风格迁移"""
        QMessageBox.information(self, "AI风格迁移", "AI风格迁移功能开发中...")

    def _on_ai_scene_analysis(self):
        """AI场景分析"""
        QMessageBox.information(self, "AI场景分析", "AI场景分析功能开发中...")

    def _on_ai_compilation(self):
        """AI高能混剪"""
        QMessageBox.information(self, "AI高能混剪", "AI高能混剪功能开发中...")

    def _on_ai_commentary(self):
        """AI短剧解说"""
        QMessageBox.information(self, "AI短剧解说", "AI短剧解说功能开发中...")

    def _on_video_converter(self):
        """视频转换器"""
        QMessageBox.information(self, "视频转换器", "视频转换器功能开发中...")

    def _on_audio_extractor(self):
        """音频提取器"""
        QMessageBox.information(self, "音频提取器", "音频提取器功能开发中...")

    def _on_thumbnail_generator(self):
        """缩略图生成器"""
        QMessageBox.information(self, "缩略图生成器", "缩略图生成器功能开发中...")

    def _on_batch_processor(self):
        """批量处理器"""
        QMessageBox.information(self, "批量处理器", "批量处理器功能开发中...")

    def _on_settings(self):
        """设置"""
        QMessageBox.information(self, "设置", "设置功能开发中...")

    def _on_documentation(self):
        """文档"""
        QMessageBox.information(self, "文档", "文档功能开发中...")

    def _on_tutorial(self):
        """教程"""
        QMessageBox.information(self, "教程", "教程功能开发中...")

    def _on_shortcuts(self):
        """快捷键"""
        self._show_shortcuts_dialog()

    def _on_check_updates(self):
        """检查更新"""
        QMessageBox.information(self, "检查更新", "检查更新功能开发中...")

    def _on_about(self):
        """关于"""
        QMessageBox.about(self, "关于 CineAIStudio",
                         "CineAIStudio v1.0.0\n\n"
                         "专业AI视频编辑器\n"
                         "基于 PyQt6 和 Material Design\n\n"
                         "© 2024 CineAIStudio Team\n\n"
                         "功能特色:\n"
                         "• AI驱动的视频处理\n"
                         "• 专业级编辑功能\n"
                         "• 剪映项目兼容\n"
                         "• 国产大模型支持\n"
                         "• 内存监控和优化\n"
                         "• 多种布局模式\n"
                         "• 丰富的快捷键支持")

    def _show_shortcuts_dialog(self):
        """显示快捷键对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键")
        dialog.setFixedSize(600, 400)

        layout = QVBoxLayout(dialog)

        # 创建快捷键表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["功能", "快捷键"])
        table.horizontalHeader().setStretchLastSection(True)

        shortcuts_data = [
            ("新建项目", "Ctrl+N"),
            ("打开项目", "Ctrl+O"),
            ("保存项目", "Ctrl+S"),
            ("另存为", "Ctrl+Shift+S"),
            ("导入媒体", "Ctrl+I"),
            ("导出视频", "Ctrl+E"),
            ("撤销", "Ctrl+Z"),
            ("重做", "Ctrl+Y"),
            ("剪切", "Ctrl+X"),
            ("复制", "Ctrl+C"),
            ("粘贴", "Ctrl+V"),
            ("播放/暂停", "Space"),
            ("停止", ""),
            ("快退5秒", "←"),
            ("快进5秒", "→"),
            ("跳转到开始", "Home"),
            ("跳转到结束", "End"),
            ("选择工具", "V"),
            ("裁剪工具", "C"),
            ("文字工具", "T"),
            ("画笔工具", "P"),
            ("手动工具", "H"),
            ("放大", "Ctrl++"),
            ("缩小", "Ctrl+-"),
            ("重置缩放", "Ctrl+0"),
            ("全屏", "F11"),
            ("最小化", "Ctrl+M"),
            ("快捷键帮助", "F1")
        ]

        table.setRowCount(len(shortcuts_data))
        for row, (function, shortcut) in enumerate(shortcuts_data):
            table.setItem(row, 0, QTableWidgetItem(function))
            table.setItem(row, 1, QTableWidgetItem(shortcut))

        layout.addWidget(table)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def _load_project(self, project_path: str):
        """加载项目"""
        self.app_state = ApplicationState.LOADING_PROJECT
        self.state_changed.emit(self.app_state)

        self.status_label.setText(f"加载项目: {os.path.basename(project_path)}")

        # 添加到最近文件
        self._add_to_recent_files(project_path)

        # 模拟加载完成
        QTimer.singleShot(1000, self._on_project_loaded)

    def _on_project_loaded(self):
        """项目加载完成"""
        self.app_state = ApplicationState.READY
        self.state_changed.emit(self.app_state)

        self.status_label.setText("项目加载完成")
        self.project_loaded.emit("当前项目")

    def _add_to_recent_files(self, file_path: str):
        """添加到最近文件"""
        # TODO: 实现最近文件管理
        pass

    def _update_recent_files_menu(self):
        """更新最近文件菜单"""
        # TODO: 实现最近文件菜单更新
        pass

    def _import_media_files(self, file_paths: List[str]):
        """导入媒体文件"""
        added_clips = self.video_manager.add_videos_batch(file_paths)

        if added_clips:
            self.status_label.setText(f"已导入 {len(added_clips)} 个媒体文件")
        else:
            self.status_label.setText("没有导入任何媒体文件")

    def _show_welcome_message(self):
        """显示欢迎信息"""
        self.status_label.setText("CineAIStudio 已就绪")

        # 显示欢迎提示
        welcome_msg = "欢迎使用 CineAIStudio！您可以通过拖拽文件或点击'导入媒体'开始编辑视频。"
        QTimer.singleShot(2000, lambda: self.status_label.setText(welcome_msg))
        QTimer.singleShot(8000, lambda: self.status_label.setText("就绪"))

    # 公共方法
    def update_status(self, message: str):
        """更新状态信息"""
        self.status_label.setText(message)

    def update_project_info(self, project_name: str):
        """更新项目信息"""
        self.project_label.setText(f"项目: {project_name}")

    def update_resolution(self, width: int, height: int):
        """更新分辨率信息"""
        self.resolution_label.setText(f"{width}x{height}")

    def update_fps(self, fps: int):
        """更新帧率信息"""
        self.fps_label.setText(f"{fps} FPS")

    def update_memory_usage(self, usage_mb: int):
        """更新内存使用信息"""
        self.memory_label.setText(f"内存: {usage_mb} MB")

    def update_render_progress(self, progress: int):
        """更新渲染进度"""
        self.render_progress_label.setText(f"渲染: {progress}%")
        self.rendering_progress.emit(progress)

        if progress > 0 and progress < 100:
            self.render_progress_bar.setVisible(True)
            self.render_progress_bar.setValue(progress)
        else:
            self.render_progress_bar.setVisible(False)

    def show_error(self, error_message: str):
        """显示错误信息"""
        self.error_occurred.emit(error_message)
        QMessageBox.critical(self, "错误", error_message)

    def show_info(self, title: str, message: str):
        """显示信息对话框"""
        QMessageBox.information(self, title, message)

    def show_question(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def show_progress_dialog(self, title: str, message: str, maximum: int = 100) -> QProgressDialog:
        """显示进度对话框"""
        progress_dialog = QProgressDialog(message, "取消", 0, maximum, self)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.show()
        return progress_dialog

    # 视频管理器回调方法
    def _on_video_added(self, clip):
        """视频添加回调"""
        self.status_label.setText(f"已添加视频: {clip.name}")

    def _on_video_removed(self, index):
        """视频移除回调"""
        self.status_label.setText("视频已移除")

    def _on_thumbnail_updated(self, clip):
        """缩略图更新回调"""
        # 更新媒体库中的缩略图
        pass

    def _on_metadata_updated(self, clip):
        """元数据更新回调"""
        # 更新媒体库中的元数据
        pass

    # 拖放支持
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为支持的文件类型
            supported_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
                                 ".mp3", ".wav", ".aac", ".flac", ".jpg", ".png", ".bmp", ".tiff"]

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()

                if ext in supported_extensions:
                    event.acceptProposedAction()
                    return

        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放置事件"""
        if event.mimeData().hasUrls():
            supported_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
                                 ".mp3", ".wav", ".aac", ".flac", ".jpg", ".png", ".bmp", ".tiff"]

            video_files = []
            other_files = []

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()

                if ext in supported_extensions:
                    if ext in [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]:
                        video_files.append(file_path)
                    else:
                        other_files.append(file_path)

            # 处理视频文件
            if video_files:
                self.status_label.setText(f"导入 {len(video_files)} 个视频文件...")
                self._import_media_files(video_files)

            # 处理其他文件
            if other_files:
                self.status_label.setText(f"导入 {len(other_files)} 个其他文件...")
                # TODO: 实现其他文件导入

            event.acceptProposedAction()
            return

        event.ignore()

    def closeEvent(self, event: QCloseEvent):
        """关闭事件"""
        # 保存配置
        self._save_config()

        # 询问是否保存
        if self.app_state == ApplicationState.READY:
            reply = QMessageBox.question(
                self, "退出确认",
                "确定要退出 CineAIStudio 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        # 清理资源
        self._cleanup_resources()

        event.accept()

    def _cleanup_resources(self):
        """清理资源"""
        # 停止定时器
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()

        if hasattr(self, 'memory_timer'):
            self.memory_timer.stop()

        # 清理线程池
        self.thread_pool.clear()
        self.thread_pool.waitForDone(1000)  # 等待1秒

        # 清理组件
        if hasattr(self, 'video_preview'):
            self.video_preview.cleanup()

        # 清理主题管理器
        if hasattr(self, 'theme_manager'):
            self.theme_manager.cleanup()

        # 清理管理器
        self.video_manager.cleanup()
        self.ai_manager.cleanup()


# 工厂函数
def create_professional_main_window() -> ProfessionalMainWindow:
    """创建专业主窗口实例"""
    return ProfessionalMainWindow()


def show_splash_screen() -> QSplashScreen:
    """显示启动画面"""
    splash = QSplashScreen()
    splash.setFixedSize(600, 400)

    # 创建启动画面内容
    splash_pixmap = QPixmap(600, 400)
    splash_pixmap.fill(QColor("#1a1a1a"))

    from PyQt6.QtGui import QPainter

    painter = QPainter(splash_pixmap)
    painter.setPen(QColor("#00BCD4"))

    # 绘制Logo
    logo_font = QFont("Arial", 48, QFont.Weight.Bold)
    painter.setFont(logo_font)
    painter.drawText(splash_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "CineAIStudio")

    # 绘制版本信息
    version_font = QFont("Arial", 14)
    painter.setFont(version_font)
    painter.setPen(QColor("#B0BEC5"))
    version_rect = QRect(0, 250, 600, 50)
    painter.drawText(version_rect, Qt.AlignmentFlag.AlignCenter, "专业AI视频编辑器 v1.0.0")

    # 绘制加载信息
    loading_font = QFont("Arial", 12)
    painter.setFont(loading_font)
    painter.setPen(QColor("#90A4AE"))
    loading_rect = QRect(0, 300, 600, 50)
    painter.drawText(loading_rect, Qt.AlignmentFlag.AlignCenter, "正在加载组件...")

    painter.end()

    splash.setPixmap(splash_pixmap)
    splash.show()

    return splash


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 显示启动画面
    splash = show_splash_screen()
    app.processEvents()

    # 创建主窗口
    main_window = create_professional_main_window()

    # 关闭启动画面，显示主窗口
    splash.finish(main_window)
    main_window.show()

    sys.exit(app.exec())
