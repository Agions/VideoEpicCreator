#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业主界面布局 - 基于Material Design的视频编辑器主窗口
参考剪映工作流程，提供专业的视频编辑界面布局
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QMenuBar, QStatusBar, QToolBar, QDockWidget, QSplitter,
    QScrollArea, QFrame, QLabel, QPushButton, QStackedWidget,
    QTabWidget, QMenu, QMessageBox, QApplication,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QKeySequence, QAction

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme,
    FontScheme, SpacingScheme
)
from .professional_theme_manager import ProfessionalThemeManager, ThemeConfig


class WindowLayout(Enum):
    """窗口布局模式"""
    DEFAULT = "default"           # 默认布局
    COMPACT = "compact"           # 紧凑布局
    IMMERSIVE = "immersive"       # 沉浸式布局
    DUAL_MONITOR = "dual_monitor"  # 双显示器布局


class PanelPosition(Enum):
    """面板位置"""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"


@dataclass
class LayoutConfig:
    """布局配置"""
    name: str
    layout: WindowLayout
    panel_positions: Dict[str, PanelPosition]
    panel_sizes: Dict[str, Tuple[int, int]]
    visible_panels: List[str]
    is_default: bool = False


class ProfessionalMainWindow(QMainWindow):
    """专业主窗口 - 基于Material Design的视频编辑器界面"""

    # 信号
    theme_changed = pyqtSignal(ThemeConfig)          # 主题变更信号
    layout_changed = pyqtSignal(WindowLayout)       # 布局变更信号
    panel_visibility_changed = pyqtSignal(str, bool)  # 面板可见性变更信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化组件
        self.style_engine = None
        self.theme_manager = None
        self.current_layout = WindowLayout.DEFAULT
        self.panel_widgets = {}
        self.dock_widgets = {}
        self.layout_configs = {}

        # 设置窗口属性
        self.setObjectName("main_window")
        self.setWindowTitle("CineAIStudio - 专业视频编辑器")
        self.setMinimumSize(1200, 800)

        # 初始化界面
        self._setup_ui()
        self._create_menus()
        self._create_toolbars()
        self._create_statusbar()
        self._create_panels()
        self._setup_layouts()
        self._connect_signals()

        # 应用默认布局
        self._apply_layout(WindowLayout.DEFAULT)

        # 设置快捷键
        self._setup_shortcuts()

    def _setup_ui(self):
        """设置基础UI"""
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建主分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # 创建中央区域
        self.center_area = self._create_center_area()
        self.main_splitter.addWidget(self.center_area)

    def _create_center_area(self) -> QWidget:
        """创建中央区域"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # 创建垂直分割器
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_layout.addWidget(self.center_splitter)

        # 视频预览区域
        self.preview_area = QWidget()
        self.preview_area.setObjectName("preview_area")
        self.preview_area.setMinimumHeight(300)
        self.center_splitter.addWidget(self.preview_area)

        # 时间线区域
        self.timeline_area = QWidget()
        self.timeline_area.setObjectName("timeline_area")
        self.timeline_area.setMinimumHeight(200)
        self.center_splitter.addWidget(self.timeline_area)

        # 设置分割器比例
        self.center_splitter.setStretchFactor(0, 6)  # 预览区域
        self.center_splitter.setStretchFactor(1, 4)  # 时间线区域

        return center_widget

    def _create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setObjectName("main_menubar")

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_project_action = QAction("新建项目(&N)", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+N"))
        new_project_action.setStatusTip("创建新项目")
        file_menu.addAction(new_project_action)

        open_project_action = QAction("打开项目(&O)", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+O"))
        open_project_action.setStatusTip("打开现有项目")
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        save_project_action = QAction("保存项目(&S)", self)
        save_project_action.setShortcut(QKeySequence("Ctrl+S"))
        save_project_action.setStatusTip("保存当前项目")
        file_menu.addAction(save_project_action)

        save_as_action = QAction("另存为(&A)", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.setStatusTip("项目另存为")
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_action = QAction("导入媒体(&I)", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setStatusTip("导入媒体文件")
        file_menu.addAction(import_action)

        export_action = QAction("导出视频(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.setStatusTip("导出视频文件")
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.setStatusTip("撤销操作")
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.setStatusTip("重做操作")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("剪切(&T)", self)
        cut_action.setShortcut(QKeySequence("Ctrl+X"))
        cut_action.setStatusTip("剪切选中内容")
        edit_menu.addAction(cut_action)

        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.setStatusTip("复制选中内容")
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴(&P)", self)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.setStatusTip("粘贴内容")
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        preferences_action = QAction("首选项(&P)", self)
        preferences_action.setStatusTip("打开首选项")
        edit_menu.addAction(preferences_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 布局子菜单
        layout_menu = view_menu.addMenu("布局(&L)")

        default_layout_action = QAction("默认布局(&D)", self)
        default_layout_action.setCheckable(True)
        default_layout_action.setChecked(True)
        default_layout_action.triggered.connect(lambda: self._apply_layout(WindowLayout.DEFAULT))
        layout_menu.addAction(default_layout_action)

        compact_layout_action = QAction("紧凑布局(&C)", self)
        compact_layout_action.setCheckable(True)
        compact_layout_action.triggered.connect(lambda: self._apply_layout(WindowLayout.COMPACT))
        layout_menu.addAction(compact_layout_action)

        immersive_layout_action = QAction("沉浸式布局(&I)", self)
        immersive_layout_action.setCheckable(True)
        immersive_layout_action.triggered.connect(lambda: self._apply_layout(WindowLayout.IMMERSIVE))
        layout_menu.addAction(immersive_layout_action)

        # 面板显示子菜单
        panels_menu = view_menu.addMenu("面板(&P)")

        self.panel_actions = {}
        panel_names = ["媒体库", "特效", "转场", "文字", "音频", "AI工具", "属性", "历史记录"]

        for panel_name in panel_names:
            action = QAction(panel_name, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, name=panel_name: self._toggle_panel(name, checked))
            panels_menu.addAction(action)
            self.panel_actions[panel_name] = action

        view_menu.addSeparator()

        # 主题子菜单
        theme_menu = view_menu.addMenu("主题(&T)")

        dark_theme_action = QAction("深色主题(&D)", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(True)
        dark_theme_action.triggered.connect(lambda: self._change_theme(UITheme.DARK))
        theme_menu.addAction(dark_theme_action)

        light_theme_action = QAction("浅色主题(&L)", self)
        light_theme_action.setCheckable(True)
        light_theme_action.triggered.connect(lambda: self._change_theme(UITheme.LIGHT))
        theme_menu.addAction(light_theme_action)

        theme_menu.addSeparator()

        theme_settings_action = QAction("主题设置(&S)", self)
        theme_settings_action.triggered.connect(self._open_theme_settings)
        theme_menu.addAction(theme_settings_action)

        view_menu.addSeparator()

        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        ai_tools_menu = tools_menu.addMenu("AI工具(&A)")

        ai_subtitle_action = QAction("AI字幕识别", self)
        ai_subtitle_action.setStatusTip("使用AI识别视频字幕")
        ai_tools_menu.addAction(ai_subtitle_action)

        ai_voiceover_action = QAction("AI配音生成", self)
        ai_voiceover_action.setStatusTip("使用AI生成配音")
        ai_tools_menu.addAction(ai_voiceover_action)

        ai_style_transfer_action = QAction("AI风格迁移", self)
        ai_style_transfer_action.setStatusTip("使用AI进行风格迁移")
        ai_tools_menu.addAction(ai_style_transfer_action)

        ai_enhance_action = QAction("AI画质增强", self)
        ai_enhance_action.setStatusTip("使用AI增强画质")
        ai_tools_menu.addAction(ai_enhance_action)

        tools_menu.addSeparator()

        settings_action = QAction("设置(&S)", self)
        settings_action.setStatusTip("打开设置")
        tools_menu.addAction(settings_action)

        # 窗口菜单
        window_menu = menubar.addMenu("窗口(&W)")

        minimize_action = QAction("最小化(&M)", self)
        minimize_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)

        maximize_action = QAction("最大化(&X)", self)
        maximize_action.triggered.connect(self.showMaximized)
        window_menu.addAction(maximize_action)

        window_menu.addSeparator()

        close_all_action = QAction("关闭所有面板(&A)", self)
        close_all_action.triggered.connect(self._close_all_panels)
        window_menu.addAction(close_all_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        documentation_action = QAction("文档(&D)", self)
        documentation_action.setStatusTip("打开文档")
        help_menu.addAction(documentation_action)

        tutorial_action = QAction("教程(&T)", self)
        tutorial_action.setStatusTip("观看教程")
        help_menu.addAction(tutorial_action)

        help_menu.addSeparator()

        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于本软件")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        self.main_toolbar = QToolBar("主工具栏")
        self.main_toolbar.setObjectName("main_toolbar")
        self.main_toolbar.setMovable(False)
        self.addToolBar(self.main_toolbar)

        # 文件操作按钮
        new_project_btn = QAction("📄 新建", self)
        new_project_btn.setStatusTip("新建项目")
        self.main_toolbar.addAction(new_project_btn)

        open_project_btn = QAction("📂 打开", self)
        open_project_btn.setStatusTip("打开项目")
        self.main_toolbar.addAction(open_project_btn)

        save_project_btn = QAction("💾 保存", self)
        save_project_btn.setStatusTip("保存项目")
        self.main_toolbar.addAction(save_project_btn)

        self.main_toolbar.addSeparator()

        # 编辑操作按钮
        undo_btn = QAction("↶ 撤销", self)
        undo_btn.setStatusTip("撤销")
        self.main_toolbar.addAction(undo_btn)

        redo_btn = QAction("↷ 重做", self)
        redo_btn.setStatusTip("重做")
        self.main_toolbar.addAction(redo_btn)

        self.main_toolbar.addSeparator()

        # 播放控制按钮
        play_btn = QAction("▶️ 播放", self)
        play_btn.setStatusTip("播放")
        self.main_toolbar.addAction(play_btn)

        pause_btn = QAction("⏸️ 暂停", self)
        pause_btn.setStatusTip("暂停")
        self.main_toolbar.addAction(pause_btn)

        stop_btn = QAction("⏹️ 停止", self)
        stop_btn.setStatusTip("停止")
        self.main_toolbar.addAction(stop_btn)

        self.main_toolbar.addSeparator()

        # 工具按钮
        cut_btn = QAction("✂️ 剪切", self)
        cut_btn.setStatusTip("剪切")
        self.main_toolbar.addAction(cut_btn)

        split_btn = QAction("🔪 分割", self)
        split_btn.setStatusTip("分割")
        self.main_toolbar.addAction(split_btn)

        # 编辑工具栏
        self.edit_toolbar = QToolBar("编辑工具栏")
        self.edit_toolbar.setObjectName("edit_toolbar")
        self.edit_toolbar.setMovable(True)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.edit_toolbar)

        # 编辑工具
        select_btn = QAction("👆 选择", self)
        select_btn.setStatusTip("选择工具")
        select_btn.setCheckable(True)
        select_btn.setChecked(True)
        self.edit_toolbar.addAction(select_btn)

        crop_btn = QAction("🔲 裁剪", self)
        crop_btn.setStatusTip("裁剪工具")
        crop_btn.setCheckable(True)
        self.edit_toolbar.addAction(crop_btn)

        text_btn = QAction("📝 文字", self)
        text_btn.setStatusTip("文字工具")
        text_btn.setCheckable(True)
        self.edit_toolbar.addAction(text_btn)

        pen_btn = QAction("✏️ 画笔", self)
        pen_btn.setStatusTip("画笔工具")
        pen_btn.setCheckable(True)
        self.edit_toolbar.addAction(pen_btn)

        # AI工具栏
        self.ai_toolbar = QToolBar("AI工具栏")
        self.ai_toolbar.setObjectName("ai_toolbar")
        self.ai_toolbar.setMovable(True)
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, self.ai_toolbar)

        # AI工具按钮
        ai_subtitle_btn = QAction("🎤 AI字幕", self)
        ai_subtitle_btn.setStatusTip("AI字幕识别")
        self.ai_toolbar.addAction(ai_subtitle_btn)

        ai_voice_btn = QAction("🗣️ AI配音", self)
        ai_voice_btn.setStatusTip("AI配音生成")
        self.ai_toolbar.addAction(ai_voice_btn)

        ai_enhance_btn = QAction("🎨 AI增强", self)
        ai_enhance_btn.setStatusTip("AI画质增强")
        self.ai_toolbar.addAction(ai_enhance_btn)

    def _create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.statusbar.setObjectName("main_statusbar")
        self.setStatusBar(self.statusbar)

        # 状态信息
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 分辨率信息
        self.resolution_label = QLabel("1920x1080")
        self.statusbar.addPermanentWidget(self.resolution_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 帧率信息
        self.fps_label = QLabel("30 FPS")
        self.statusbar.addPermanentWidget(self.fps_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 时间信息
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.statusbar.addPermanentWidget(self.time_label)

        self.statusbar.addPermanentWidget(QLabel("|"))

        # 内存使用
        self.memory_label = QLabel("内存: 256 MB")
        self.statusbar.addPermanentWidget(self.memory_label)

    def _create_panels(self):
        """创建面板"""
        # 媒体库面板
        media_panel = self._create_dock_panel("媒体库", PanelPosition.LEFT)
        self._add_panel_to_dock(media_panel, "media_panel")

        # 特效面板
        effects_panel = self._create_dock_panel("特效", PanelPosition.RIGHT)
        self._add_panel_to_dock(effects_panel, "effects_component")

        # AI工具面板
        ai_panel = self._create_dock_panel("AI工具", PanelPosition.RIGHT)
        self._add_panel_to_dock(ai_panel, "ai_panel")

        # 属性面板
        properties_panel = self._create_dock_panel("属性", PanelPosition.RIGHT)
        self._add_panel_to_dock(properties_panel, "properties_panel")

        # 历史记录面板
        history_panel = self._create_dock_panel("历史记录", PanelPosition.LEFT)
        self._add_panel_to_dock(history_panel, "history_panel")

    def _create_dock_panel(self, title: str, position: PanelPosition) -> QDockWidget:
        """创建停靠面板"""
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title.lower()}_dock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # 创建面板内容
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)

        # 添加标题标签
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 添加内容占位符
        placeholder = QLabel(f"{title}内容区域")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(placeholder)

        layout.addStretch()

        dock.setWidget(content)

        # 设置默认位置
        if position == PanelPosition.LEFT:
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        elif position == PanelPosition.RIGHT:
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        elif position == PanelPosition.TOP:
            self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)
        elif position == PanelPosition.BOTTOM:
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        return dock

    def _add_panel_to_dock(self, dock: QDockWidget, panel_id: str):
        """添加面板到停靠窗口"""
        self.dock_widgets[panel_id] = dock
        self.panel_widgets[panel_id] = dock.widget()

    def _setup_layouts(self):
        """设置布局配置"""
        # 默认布局
        self.layout_configs[WindowLayout.DEFAULT] = LayoutConfig(
            name="默认布局",
            layout=WindowLayout.DEFAULT,
            panel_positions={
                "media_panel": PanelPosition.LEFT,
                "effects_component": PanelPosition.RIGHT,
                "ai_panel": PanelPosition.RIGHT,
                "properties_panel": PanelPosition.RIGHT,
                "history_panel": PanelPosition.LEFT
            },
            panel_sizes={
                "media_panel": (250, 400),
                "effects_component": (250, 300),
                "ai_panel": (250, 300),
                "properties_panel": (250, 300),
                "history_panel": (250, 200)
            },
            visible_panels=["media_panel", "effects_component", "ai_panel", "properties_panel", "history_panel"],
            is_default=True
        )

        # 紧凑布局
        self.layout_configs[WindowLayout.COMPACT] = LayoutConfig(
            name="紧凑布局",
            layout=WindowLayout.COMPACT,
            panel_positions={
                "media_panel": PanelPosition.LEFT,
                "effects_component": PanelPosition.LEFT,
                "ai_panel": PanelPosition.LEFT,
                "properties_panel": PanelPosition.RIGHT,
                "history_panel": PanelPosition.RIGHT
            },
            panel_sizes={
                "media_panel": (200, 300),
                "effects_component": (200, 250),
                "ai_panel": (200, 250),
                "properties_panel": (200, 300),
                "history_panel": (200, 200)
            },
            visible_panels=["media_panel", "effects_component", "ai_panel", "properties_panel"]
        )

        # 沉浸式布局
        self.layout_configs[WindowLayout.IMMERSIVE] = LayoutConfig(
            name="沉浸式布局",
            layout=WindowLayout.IMMERSIVE,
            panel_positions={
                "media_panel": PanelPosition.LEFT,
                "properties_panel": PanelPosition.RIGHT
            },
            panel_sizes={
                "media_panel": (200, 400),
                "properties_panel": (200, 300)
            },
            visible_panels=["media_panel", "properties_panel"]
        )

    def _apply_layout(self, layout: WindowLayout):
        """应用布局"""
        if layout not in self.layout_configs:
            return

        config = self.layout_configs[layout]
        self.current_layout = layout

        # 隐藏所有面板
        for dock in self.dock_widgets.values():
            dock.setVisible(False)

        # 显示配置中的面板
        for panel_id in config.visible_panels:
            if panel_id in self.dock_widgets:
                dock = self.dock_widgets[panel_id]
                dock.setVisible(True)

                # 设置面板位置
                if panel_id in config.panel_positions:
                    position = config.panel_positions[panel_id]
                    self._move_dock_to_position(dock, position)

                # 设置面板大小
                if panel_id in config.panel_sizes:
                    size = config.panel_sizes[panel_id]
                    dock.setMinimumSize(size[0], size[1])

        # 调整主分割器比例
        if layout == WindowLayout.DEFAULT:
            self.main_splitter.setStretchFactor(0, 2)  # 左侧面板
            self.main_splitter.setStretchFactor(1, 6)  # 中央区域
            self.main_splitter.setStretchFactor(2, 2)  # 右侧面板
        elif layout == WindowLayout.COMPACT:
            self.main_splitter.setStretchFactor(0, 3)  # 左侧面板
            self.main_splitter.setStretchFactor(1, 7)  # 中央区域
            self.main_splitter.setStretchFactor(2, 2)  # 右侧面板
        elif layout == WindowLayout.IMMERSIVE:
            self.main_splitter.setStretchFactor(0, 1)  # 左侧面板
            self.main_splitter.setStretchFactor(1, 9)  # 中央区域
            self.main_splitter.setStretchFactor(2, 1)  # 右侧面板

        # 发射布局变更信号
        self.layout_changed.emit(layout)

    def _move_dock_to_position(self, dock: QDockWidget, position: PanelPosition):
        """移动停靠窗口到指定位置"""
        if position == PanelPosition.LEFT:
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        elif position == PanelPosition.RIGHT:
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        elif position == PanelPosition.TOP:
            self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)
        elif position == PanelPosition.BOTTOM:
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    def _toggle_panel(self, panel_name: str, visible: bool):
        """切换面板可见性"""
        panel_id = f"{panel_name.lower().replace(' ', '_')}_panel"
        if panel_id in self.dock_widgets:
            self.dock_widgets[panel_id].setVisible(visible)
            self.panel_visibility_changed.emit(panel_name, visible)

    def _close_all_panels(self):
        """关闭所有面板"""
        for dock in self.dock_widgets.values():
            dock.setVisible(False)

        # 更新菜单状态
        for action in self.panel_actions.values():
            action.setChecked(False)

    def _change_theme(self, theme: UITheme):
        """更换主题"""
        if self.style_engine:
            self.style_engine.set_theme(theme)

            # 发射主题变更信号
            if hasattr(self.style_engine, 'current_theme'):
                self.theme_changed.emit(self.style_engine.current_theme)

    def _open_theme_settings(self):
        """打开主题设置"""
        from .professional_theme_manager import get_theme_dialog

        dialog = get_theme_dialog(self)
        if self.theme_manager:
            dialog.theme_manager = self.theme_manager

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 主题已应用
            pass

    def _toggle_fullscreen(self, checked: bool):
        """切换全屏"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 CineAIStudio",
                         "CineAIStudio v1.0.0\n\n"
                         "专业视频编辑器\n"
                         "基于 PyQt6 和 Material Design\n\n"
                         "© 2024 CineAIStudio Team")

    def _setup_shortcuts(self):
        """设置快捷键"""
        # 播放控制
        self.space_shortcut = QShortcut(QKeySequence("Space"), self)
        self.space_shortcut.activated.connect(self._toggle_playback)

        # 时间线导航
        self.left_shortcut = QShortcut(QKeySequence("Left"), self)
        self.left_shortcut.activated.connect(self._seek_backward)

        self.right_shortcut = QShortcut(QKeySequence("Right"), self)
        self.right_shortcut.activated.connect(self._seek_forward)

        # 缩放
        self.zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        self.zoom_in_shortcut.activated.connect(self._zoom_in)

        self.zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        self.zoom_out_shortcut.activated.connect(self._zoom_out)

        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(self._zoom_reset)

    def _toggle_playback(self):
        """切换播放状态"""
        # 这里需要连接到实际的播放控制逻辑
        self.status_label.setText("播放/暂停")

    def _seek_backward(self):
        """向后寻址"""
        # 这里需要连接到实际的时间线控制逻辑
        self.status_label.setText("向后寻址")

    def _seek_forward(self):
        """向前寻址"""
        # 这里需要连接到实际的时间线控制逻辑
        self.status_label.setText("向前寻址")

    def _zoom_in(self):
        """放大"""
        # 这里需要连接到实际的缩放逻辑
        self.status_label.setText("放大")

    def _zoom_out(self):
        """缩小"""
        # 这里需要连接到实际的缩放逻辑
        self.status_label.setText("缩小")

    def _zoom_reset(self):
        """重置缩放"""
        # 这里需要连接到实际的缩放逻辑
        self.status_label.setText("重置缩放")

    def _connect_signals(self):
        """连接信号"""
        # 窗口状态变更信号
        self.window_state_changed = self.windowStateChanged

    def set_style_engine(self, style_engine: ProfessionalStyleEngine):
        """设置样式引擎"""
        self.style_engine = style_engine

        # 应用样式到主窗口
        if style_engine:
            self.setStyleSheet(style_engine._generate_stylesheet())

    def set_theme_manager(self, theme_manager: ProfessionalThemeManager):
        """设置主题管理器"""
        self.theme_manager = theme_manager

        # 连接主题变更信号
        if theme_manager:
            theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, config: ThemeConfig):
        """主题变更处理"""
        # 更新主窗口样式
        if self.style_engine:
            self.style_engine.set_theme(
                UITheme.DARK if config.is_dark else UITheme.LIGHT
            )

        # 发射主题变更信号
        self.theme_changed.emit(config)

    def get_current_layout(self) -> WindowLayout:
        """获取当前布局"""
        return self.current_layout

    def save_layout_state(self) -> bytes:
        """保存布局状态"""
        return self.saveState()

    def restore_layout_state(self, state: bytes):
        """恢复布局状态"""
        self.restoreState(state)

    def get_panel_widget(self, panel_id: str) -> Optional[QWidget]:
        """获取面板组件"""
        return self.panel_widgets.get(panel_id)

    def update_status(self, message: str):
        """更新状态信息"""
        self.status_label.setText(message)

    def update_time_info(self, current: str, total: str):
        """更新时间信息"""
        self.time_label.setText(f"{current} / {total}")

    def update_resolution(self, width: int, height: int):
        """更新分辨率信息"""
        self.resolution_label.setText(f"{width}x{height}")

    def update_fps(self, fps: int):
        """更新帧率信息"""
        self.fps_label.setText(f"{fps} FPS")

    def update_memory_usage(self, usage_mb: int):
        """更新内存使用信息"""
        self.memory_label.setText(f"内存: {usage_mb} MB")


# 工厂函数
def create_main_window(parent=None) -> ProfessionalMainWindow:
    """创建主窗口实例"""
    return ProfessionalMainWindow(parent)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建样式引擎
    from ..professional_ui_system import create_style_engine
    style_engine = create_style_engine(UITheme.DARK)

    # 创建主窗口
    main_window = create_main_window()
    main_window.set_style_engine(style_engine)
    main_window.show()

    sys.exit(app.exec())
