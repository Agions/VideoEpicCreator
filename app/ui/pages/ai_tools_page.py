#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI工具页面 - 集成所有AI功能的统一界面
包括解说生成、混剪生成、字幕生成、TTS语音合成等功能
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QGridLayout, QGroupBox, QCheckBox,
    QTabWidget, QSlider, QSpinBox, QFormLayout, QFileDialog,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QProgressBar, QTextEdit,
    QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QToolButton, QMenu,
    QApplication, QSizePolicy, QSpacerItem, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QTimeEdit,
    QSystemTrayIcon, QStatusBar, QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QTime, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QTextCharFormat, QDesktopServices, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from app.ai.ai_service import AIService
from app.ai.generators.text_to_speech import TextToSpeechEngine, get_tts_engine
from app.ai.intelligent_content_generator import IntelligentContentGenerator, create_content_generator
from app.ai.compilation_generator import AICompilationGenerator, create_compilation_generator
from app.ui.components.content_generator_component import AIContentGenerator
from app.ui.components.subtitle_generator_component import AISubtitleGenerator
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class AIToolType(Enum):
    """AI工具类型"""
    COMMENTARY = "commentary"        # AI解说生成
    COMPILATION = "compilation"      # AI混剪生成
    SUBTITLE = "subtitle"           # AI字幕生成
    TTS = "tts"                     # TTS语音合成
    CONTENT_ANALYSIS = "content_analysis"  # 内容分析
    SCRIPT_GENERATION = "script_generation"  # 脚本生成


@dataclass
class AIToolConfig:
    """AI工具配置"""
    tool_type: AIToolType
    name: str
    description: str
    icon: str
    enabled: bool = True
    api_key: str = ""
    model: str = ""
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class AIToolsPanel(QWidget):
    """AI工具面板"""
    
    # 信号定义
    tool_selected = pyqtSignal(AIToolType)        # 工具选择
    task_started = pyqtSignal(str, AIToolType)   # 任务开始
    task_progress = pyqtSignal(str, float)       # 任务进度
    task_completed = pyqtSignal(str, object)     # 任务完成
    task_error = pyqtSignal(str, str)           # 任务错误
    
    def __init__(self, ai_service: AIService, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.settings_manager = settings_manager
        self.tts_engine = get_tts_engine()
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # AI生成器
        self.content_generator = create_content_generator(ai_service)
        self.compilation_generator = create_compilation_generator(ai_service)
        
        # 工具配置
        self.tools_config = self._load_tools_config()
        self.active_tasks: Dict[str, Dict] = {}
        
        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建工具栏
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 创建主要内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建侧边栏
        sidebar = self._create_sidebar()
        content_layout.addWidget(sidebar)
        
        # 创建工作区域
        self.work_area = self._create_work_area()
        content_layout.addWidget(self.work_area, 1)
        
        main_layout.addWidget(content_widget)
        
        # 创建状态栏
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
        
        # 应用样式
        self._apply_styles()
        
    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setObjectName("ai_tools_toolbar")
        
        # 新建任务
        new_action = QAction("🆕 新建任务", self)
        new_action.triggered.connect(self._new_task)
        toolbar.addAction(new_action)
        
        toolbar.addSeparator()
        
        # 导入文件
        import_action = QAction("📁 导入文件", self)
        import_action.triggered.connect(self._import_files)
        toolbar.addAction(import_action)
        
        # 导出结果
        export_action = QAction("📤 导出结果", self)
        export_action.triggered.connect(self._export_results)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # 设置
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)
        
        # 帮助
        help_action = QAction("❓ 帮助", self)
        help_action.triggered.connect(self._show_help)
        toolbar.addAction(help_action)
        
        return toolbar
        
    def _create_sidebar(self) -> QWidget:
        """创建侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("ai_tools_sidebar")
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具列表
        tools_group = QGroupBox("AI工具")
        tools_layout = QVBoxLayout(tools_group)
        
        # 创建工具按钮
        self.tool_buttons = {}
        tool_configs = [
            (AIToolType.COMMENTARY, "🎬 AI解说", "智能生成视频解说内容"),
            (AIToolType.COMPILATION, "⚡ AI混剪", "自动检测精彩片段生成混剪"),
            (AIToolType.SUBTITLE, "📝 AI字幕", "语音识别生成精准字幕"),
            (AIToolType.TTS, "🔊 语音合成", "文本转自然语音"),
            (AIToolType.CONTENT_ANALYSIS, "🔍 内容分析", "深度分析视频内容"),
            (AIToolType.SCRIPT_GENERATION, "📜 脚本生成", "创意视频脚本生成")
        ]
        
        for tool_type, name, description in tool_configs:
            btn = QPushButton(name)
            btn.setObjectName(f"tool_btn_{tool_type.value}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool_type: self._select_tool(t))
            btn.setToolTip(description)
            
            self.tool_buttons[tool_type] = btn
            tools_layout.addWidget(btn)
        
        tools_layout.addStretch()
        layout.addWidget(tools_group)
        
        # 最近任务
        recent_group = QGroupBox("最近任务")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_tasks_list = QListWidget()
        self.recent_tasks_list.setMaximumHeight(150)
        self.recent_tasks_list.itemClicked.connect(self._on_recent_task_clicked)
        recent_layout.addWidget(self.recent_tasks_list)
        
        layout.addWidget(recent_group)
        
        return sidebar
        
    def _create_work_area(self) -> QWidget:
        """创建工作区域"""
        work_area = QWidget()
        work_area.setObjectName("ai_tools_work_area")
        layout = QVBoxLayout(work_area)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 欢迎界面
        self.welcome_widget = self._create_welcome_widget()
        layout.addWidget(self.welcome_widget)
        
        # 工具界面容器
        self.tool_container = QWidget()
        self.tool_layout = QVBoxLayout(self.tool_container)
        layout.addWidget(self.tool_container)
        
        # 默认隐藏工具容器
        self.tool_container.setVisible(False)
        
        return work_area
        
    def _create_welcome_widget(self) -> QWidget:
        """创建欢迎界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(30)
        
        # 标题
        title = QLabel("🤖 AI工具集")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #1890ff; margin: 20px 0;")
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("智能视频创作工具集合")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setStyleSheet("color: #595959; margin-bottom: 40px;")
        layout.addWidget(subtitle)
        
        # 功能介绍
        features_grid = QGridLayout()
        features = [
            ("🎬", "AI解说生成", "智能分析视频内容，生成专业解说词"),
            ("⚡", "AI高能混剪", "自动检测精彩片段，生成激动人心混剪"),
            ("📝", "AI字幕生成", "语音识别生成字幕，支持多语言翻译"),
            ("🔊", "TTS语音合成", "文本转自然语音，多种音色情感"),
            ("🔍", "内容分析", "深度分析视频内容，提供优化建议"),
            ("📜", "脚本生成", "创意视频脚本生成，多种风格模板")
        ]
        
        for i, (icon, title, desc) in enumerate(features):
            row = i // 3
            col = i % 3
            
            feature_widget = QWidget()
            feature_layout = QVBoxLayout(feature_widget)
            
            # 图标
            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setFont(QFont("Arial", 24))
            feature_layout.addWidget(icon_label)
            
            # 标题
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #262626;")
            feature_layout.addWidget(title_label)
            
            # 描述
            desc_label = QLabel(desc)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setFont(QFont("Arial", 10))
            desc_label.setStyleSheet("color: #8c8c8c;")
            desc_label.setWordWrap(True)
            feature_layout.addWidget(desc_label)
            
            features_grid.addWidget(feature_widget, row, col)
        
        layout.addLayout(features_grid)
        
        # 快速开始
        quick_start_label = QLabel("快速开始：选择左侧工具开始创作")
        quick_start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quick_start_label.setStyleSheet("color: #8c8c8c; margin-top: 40px;")
        layout.addWidget(quick_start_label)
        
        layout.addStretch()
        
        return widget
        
    def _create_status_bar(self) -> QStatusBar:
        """创建状态栏"""
        status_bar = QStatusBar()
        status_bar.setObjectName("ai_tools_status_bar")
        
        # 状态标签
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        status_bar.addPermanentWidget(self.progress_bar)
        
        return status_bar
        
    def _select_tool(self, tool_type: AIToolType):
        """选择工具"""
        # 更新按钮状态
        for btn_tool_type, btn in self.tool_buttons.items():
            btn.setChecked(btn_tool_type == tool_type)
        
        # 记录当前工具类型
        self.current_tool_type = tool_type
        
        # 隐藏欢迎界面，显示工具容器
        self.welcome_widget.setVisible(False)
        self.tool_container.setVisible(True)
        
        # 清空工具容器
        self._clear_tool_container()
        
        # 创建对应的工具界面
        if tool_type == AIToolType.COMMENTARY:
            self._create_commentary_tool()
        elif tool_type == AIToolType.COMPILATION:
            self._create_compilation_tool()
        elif tool_type == AIToolType.SUBTITLE:
            self._create_subtitle_tool()
        elif tool_type == AIToolType.TTS:
            self._create_tts_tool()
        elif tool_type == AIToolType.CONTENT_ANALYSIS:
            self._create_content_analysis_tool()
        elif tool_type == AIToolType.SCRIPT_GENERATION:
            self._create_script_generation_tool()
        
        # 发送信号
        self.tool_selected.emit(tool_type)
        
    def _clear_tool_container(self):
        """清空工具容器"""
        while self.tool_layout.count():
            item = self.tool_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
    def _create_commentary_tool(self):
        """创建AI解说工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("🎬 AI解说生成")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 视频信息输入
        info_group = QGroupBox("视频信息")
        info_layout = QFormLayout(info_group)
        
        # 视频时长
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 3600)
        self.duration_input.setValue(60)
        self.duration_input.setSuffix(" 秒")
        info_layout.addRow("视频时长:", self.duration_input)
        
        # 视频类型
        self.video_type_combo = QComboBox()
        self.video_type_combo.addItems(["短视频", "电影解说", "纪录片", "教程", "vlog", "其他"])
        info_layout.addRow("视频类型:", self.video_type_combo)
        
        # 视频内容
        self.video_content_input = QTextEdit()
        self.video_content_input.setPlaceholderText("请输入视频的主要内容描述...")
        self.video_content_input.setMaximumHeight(100)
        info_layout.addRow("视频内容:", self.video_content_input)
        
        layout.addWidget(info_group)
        
        # 解说风格设置
        style_group = QGroupBox("解说风格")
        style_layout = QFormLayout(style_group)
        
        # 风格选择
        self.commentary_style_combo = QComboBox()
        self.commentary_style_combo.addItems(["专业解说", "幽默风趣", "情感丰富", "简洁明了", "生动活泼"])
        style_layout.addRow("解说风格:", self.commentary_style_combo)
        
        # 目标观众
        self.target_audience_input = QLineEdit()
        self.target_audience_input.setPlaceholderText("例如：年轻人、专业人士、普通观众")
        style_layout.addRow("目标观众:", self.target_audience_input)
        
        layout.addWidget(style_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.generate_commentary_btn = QPushButton("🎬 生成解说")
        self.generate_commentary_btn.setObjectName("primary_button")
        self.generate_commentary_btn.clicked.connect(self._generate_commentary)
        control_layout.addWidget(self.generate_commentary_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 进度显示
        self.commentary_progress = QProgressBar()
        self.commentary_progress.setVisible(False)
        layout.addWidget(self.commentary_progress)
        
        # 结果显示
        self.commentary_results = QTextEdit()
        self.commentary_results.setPlaceholderText("生成的解说将在这里显示...")
        self.commentary_results.setReadOnly(True)
        layout.addWidget(self.commentary_results)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _create_compilation_tool(self):
        """创建AI混剪工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("⚡ AI高能混剪")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 混剪设置
        settings_group = QGroupBox("混剪设置")
        settings_layout = QFormLayout(settings_group)
        
        # 视频文件
        file_layout = QHBoxLayout()
        self.compilation_file_input = QLineEdit()
        self.compilation_file_input.setPlaceholderText("选择视频文件")
        file_layout.addWidget(self.compilation_file_input)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(self._browse_compilation_file)
        file_layout.addWidget(browse_btn)
        
        settings_layout.addRow("视频文件:", file_layout)
        
        # 检测类型
        self.detection_type_combo = QComboBox()
        self.detection_type_combo.addItems(["动作场景", "情感高潮", "对话精彩", "综合检测"])
        settings_layout.addRow("检测类型:", self.detection_type_combo)
        
        # 片段长度
        self.clip_length_spin = QSpinBox()
        self.clip_length_spin.setRange(3, 30)
        self.clip_length_spin.setValue(8)
        self.clip_length_spin.setSuffix(" 秒")
        settings_layout.addRow("片段长度:", self.clip_length_spin)
        
        layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.start_compilation_btn = QPushButton("⚡ 开始检测")
        self.start_compilation_btn.setObjectName("primary_button")
        self.start_compilation_btn.clicked.connect(self._start_compilation)
        control_layout.addWidget(self.start_compilation_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 结果显示
        self.compilation_results = QTextEdit()
        self.compilation_results.setPlaceholderText("检测结果将在这里显示...")
        self.compilation_results.setReadOnly(True)
        layout.addWidget(self.compilation_results)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _create_subtitle_tool(self):
        """创建AI字幕工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("📝 AI字幕生成")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 创建字幕生成器
        self.subtitle_generator = AISubtitleGenerator(
            self.ai_service, self.settings_manager
        )
        layout.addWidget(self.subtitle_generator)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _create_tts_tool(self):
        """创建TTS语音合成工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("🔊 TTS语音合成")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # TTS设置
        settings_group = QGroupBox("语音合成设置")
        settings_layout = QFormLayout(settings_group)
        
        # 文本输入
        self.tts_text_input = QTextEdit()
        self.tts_text_input.setPlaceholderText("输入要合成的文本...")
        self.tts_text_input.setMaximumHeight(120)
        settings_layout.addRow("合成文本:", self.tts_text_input)
        
        # 语音类型
        self.voice_type_combo = QComboBox()
        self.voice_type_combo.addItems(self.tts_engine.get_available_voices())
        settings_layout.addRow("语音类型:", self.voice_type_combo)
        
        # 情感类型
        self.emotion_type_combo = QComboBox()
        self.emotion_type_combo.addItems(self.tts_engine.get_available_emotions())
        settings_layout.addRow("情感类型:", self.emotion_type_combo)
        
        # 语速
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        settings_layout.addRow("语速:", speed_layout)
        
        layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.synthesize_btn = QPushButton("🔊 开始合成")
        self.synthesize_btn.setObjectName("primary_button")
        self.synthesize_btn.clicked.connect(self._start_tts_synthesis)
        control_layout.addWidget(self.synthesize_btn)
        
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_tts_audio)
        control_layout.addWidget(self.play_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 进度显示
        self.tts_progress = QProgressBar()
        self.tts_progress.setVisible(False)
        layout.addWidget(self.tts_progress)
        
        # 音频播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _create_content_analysis_tool(self):
        """创建内容分析工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("🔍 内容分析")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 分析设置
        settings_group = QGroupBox("分析设置")
        settings_layout = QFormLayout(settings_group)
        
        # 视频文件
        file_layout = QHBoxLayout()
        self.analysis_file_input = QLineEdit()
        self.analysis_file_input.setPlaceholderText("选择视频文件")
        file_layout.addWidget(self.analysis_file_input)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(self._browse_analysis_file)
        file_layout.addWidget(browse_btn)
        
        settings_layout.addRow("视频文件:", file_layout)
        
        # 分析类型
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["内容概要", "场景分析", "情感分析", "质量评估"])
        settings_layout.addRow("分析类型:", self.analysis_type_combo)
        
        layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.start_analysis_btn = QPushButton("🔍 开始分析")
        self.start_analysis_btn.setObjectName("primary_button")
        self.start_analysis_btn.clicked.connect(self._start_content_analysis)
        control_layout.addWidget(self.start_analysis_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 分析结果
        self.analysis_results = QTextEdit()
        self.analysis_results.setPlaceholderText("分析结果将在这里显示...")
        self.analysis_results.setReadOnly(True)
        layout.addWidget(self.analysis_results)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _create_script_generation_tool(self):
        """创建脚本生成工具"""
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        
        # 工具标题
        title = QLabel("📜 脚本生成")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 脚本设置
        settings_group = QGroupBox("脚本设置")
        settings_layout = QFormLayout(settings_group)
        
        # 脚本类型
        self.script_type_combo = QComboBox()
        self.script_type_combo.addItems(["短视频脚本", "宣传片脚本", "教程脚本", "故事脚本"])
        settings_layout.addRow("脚本类型:", self.script_type_combo)
        
        # 主题
        self.script_theme_input = QLineEdit()
        self.script_theme_input.setPlaceholderText("输入脚本主题...")
        settings_layout.addRow("主题:", self.script_theme_input)
        
        # 时长
        self.script_duration_spin = QSpinBox()
        self.script_duration_spin.setRange(30, 1800)
        self.script_duration_spin.setValue(60)
        self.script_duration_spin.setSuffix(" 秒")
        settings_layout.addRow("预计时长:", self.script_duration_spin)
        
        layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.generate_script_btn = QPushButton("📜 生成脚本")
        self.generate_script_btn.setObjectName("primary_button")
        self.generate_script_btn.clicked.connect(self._generate_script)
        control_layout.addWidget(self.generate_script_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 脚本结果
        self.script_results = QTextEdit()
        self.script_results.setPlaceholderText("生成的脚本将在这里显示...")
        layout.addWidget(self.script_results)
        
        self.tool_layout.addWidget(tool_widget)
        
    def _connect_signals(self):
        """连接信号"""
        # AI服务信号
        try:
            self.ai_service.worker_finished.connect(self._on_ai_task_completed)
            self.ai_service.worker_error.connect(self._on_ai_task_failed)
        except AttributeError as e:
            print(f"AIService信号连接失败: {e}")
        
        # TTS引擎信号
        try:
            self.tts_engine.synthesis_completed.connect(self._on_tts_completed)
            self.tts_engine.synthesis_error.connect(self._on_tts_error)
        except AttributeError as e:
            print(f"TTS引擎信号连接失败: {e}")
        
        # 内容生成器信号
        try:
            self.content_generator.generation_completed.connect(self._on_content_generation_completed)
            self.content_generator.generation_failed.connect(self._on_content_generation_failed)
        except AttributeError as e:
            print(f"内容生成器信号连接失败: {e}")
        
        # 混剪生成器信号
        try:
            self.compilation_generator.analysis_completed.connect(self._on_compilation_analysis_completed)
            self.compilation_generator.analysis_failed.connect(self._on_compilation_analysis_failed)
        except AttributeError as e:
            print(f"混剪生成器信号连接失败: {e}")
        
    def _update_speed_label(self, value):
        """更新语速标签"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        
    def _new_task(self):
        """新建任务"""
        # 显示欢迎界面
        self.welcome_widget.setVisible(True)
        self.tool_container.setVisible(False)
        
        # 取消所有工具按钮的选中状态
        for btn in self.tool_buttons.values():
            btn.setChecked(False)
        
    def _import_files(self):
        """导入文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;音频文件 (*.mp3 *.wav);;所有文件 (*)"
        )
        if files:
            self.status_label.setText(f"已导入 {len(files)} 个文件")
            
    def _export_results(self):
        """导出结果"""
        QMessageBox.information(self, "导出结果", "导出功能开发中...")
        
    def _open_settings(self):
        """打开设置"""
        QMessageBox.information(self, "设置", "设置功能开发中...")
        
    def _show_help(self):
        """显示帮助"""
        QMessageBox.information(self, "帮助", "帮助文档开发中...")
        
    def _browse_compilation_file(self):
        """浏览混剪文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        if file_path:
            self.compilation_file_input.setText(file_path)
    
    def _generate_commentary(self):
        """生成解说"""
        video_content = self.video_content_input.toPlainText().strip()
        if not video_content:
            QMessageBox.warning(self, "警告", "请输入视频内容描述")
            return
        
        # 构建视频信息
        video_info = {
            "duration": self.duration_input.value(),
            "type": self.video_type_combo.currentText(),
            "content": video_content,
            "style": self.commentary_style_combo.currentText(),
            "audience": self.target_audience_input.text() or "普通观众"
        }
        
        # 禁用按钮，显示进度
        self.generate_commentary_btn.setEnabled(False)
        self.commentary_progress.setVisible(True)
        self.commentary_progress.setValue(0)
        self.status_label.setText("正在生成解说...")
        
        # 异步生成解说
        asyncio.create_task(self._execute_commentary_generation(video_info))
    
    async def _execute_commentary_generation(self, video_info: Dict[str, Any]):
        """执行解说生成"""
        try:
            style = video_info.get("style", "专业解说")
            
            # 使用内容生成器生成解说
            result = await self.content_generator.generate_commentary(
                video_info=video_info,
                style=style
            )
            
            if result.success:
                self.commentary_results.setText(result.content)
                self.status_label.setText("解说生成完成")
            else:
                self.commentary_results.setText(f"生成失败: {result.error_message}")
                self.status_label.setText("解说生成失败")
                
        except Exception as e:
            error_msg = f"解说生成出错: {str(e)}"
            self.commentary_results.setText(error_msg)
            self.status_label.setText("解说生成出错")
        finally:
            self.generate_commentary_btn.setEnabled(True)
            self.commentary_progress.setVisible(False)
            
    def _start_compilation(self):
        """开始混剪检测"""
        if not self.compilation_file_input.text():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return
        
        video_path = self.compilation_file_input.text()
        
        # 获取混剪风格
        style_map = {
            "动作场景": "highlights",
            "情感高潮": "emotional", 
            "对话精彩": "dialogue",
            "综合检测": "highlights"
        }
        style_str = self.detection_type_combo.currentText()
        style = style_map.get(style_str, "highlights")
        
        # 获取目标时长
        target_duration = self.clip_length_spin.value() * 5  # 5个片段
        
        # 禁用按钮，显示进度
        self.start_compilation_btn.setEnabled(False)
        self.compilation_results.setText("正在分析视频片段...")
        self.status_label.setText("正在分析视频...")
        
        # 异步执行混剪分析
        asyncio.create_task(self._execute_compilation_analysis(video_path, style, target_duration))
    
    async def _execute_compilation_analysis(self, video_path: str, style: str, target_duration: float):
        """执行混剪分析"""
        try:
            # 使用混剪生成器进行分析
            result = await self.compilation_generator.generate_compilation(
                video_path=video_path,
                style=self.compilation_generator.CompilationStyle(style),
                target_duration=target_duration
            )
            
            if result.success:
                # 显示分析结果
                segments_text = f"混剪风格：{result.compilation_plan.style.value}\n\n"
                segments_text += "检测到以下精彩片段：\n\n"
                
                for i, segment in enumerate(result.segments[:5]):  # 显示前5个片段
                    segments_text += f"{i+1}. {segment.start_time:.1f}-{segment.end_time:.1f}s - {segment.description}\n"
                    segments_text += f"   场景类型: {segment.scene_type.value}\n"
                    segments_text += f"   能量评分: {segment.energy_score:.2f}\n"
                    segments_text += f"   情感评分: {segment.emotion_score:.2f}\n\n"
                
                segments_text += f"总计检测到 {len(result.segments)} 个片段，总时长 {result.compilation_plan.total_duration:.1f} 秒。\n\n"
                
                if result.compilation_plan.music_suggestions:
                    segments_text += "🎵 音乐建议：\n"
                    for music in result.compilation_plan.music_suggestions:
                        segments_text += f"- {music}\n"
                
                if result.compilation_plan.effects:
                    segments_text += "\n✨ 特效建议：\n"
                    for effect in result.compilation_plan.effects:
                        segments_text += f"- {effect}\n"
                
                self.compilation_results.setText(segments_text)
                self.status_label.setText("混剪分析完成")
            else:
                self.compilation_results.setText(f"分析失败: {result.error_message}")
                self.status_label.setText("混剪分析失败")
                
        except Exception as e:
            error_msg = f"混剪分析出错: {str(e)}"
            self.compilation_results.setText(error_msg)
            self.status_label.setText("混剪分析出错")
        finally:
            self.start_compilation_btn.setEnabled(True)
        
    def _browse_analysis_file(self):
        """浏览分析文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        if file_path:
            self.analysis_file_input.setText(file_path)
            
    def _start_content_analysis(self):
        """开始内容分析"""
        if not self.analysis_file_input.text():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return
            
        # 模拟内容分析
        self.start_analysis_btn.setEnabled(False)
        self.status_label.setText("正在分析内容...")
        
        # 模拟分析结果
        QTimer.singleShot(3000, self._analysis_completed)
        
    def _analysis_completed(self):
        """内容分析完成"""
        self.start_analysis_btn.setEnabled(True)
        self.status_label.setText("分析完成")
        
        # 显示模拟结果
        results = """内容分析报告：

📊 基本信息：
- 视频时长：5分32秒
- 分辨率：1920x1080
- 帧率：30fps

🎬 内容概要：
- 类型：教育类视频
- 主题：人工智能技术应用
- 风格：专业讲解

🎭 场景分析：
- 开场介绍：15%
- 主体内容：70%
- 总结结尾：15%

😊 情感分析：
- 整体基调：专业、积极
- 情感变化：平稳→激昂→平和
- 观众吸引力：高

⭐ 质量评估：
- 画面质量：优秀
- 音频质量：良好
- 内容价值：很高
- 推荐指数：⭐⭐⭐⭐⭐"""
        
        self.analysis_results.setText(results)
        
    def _generate_script(self):
        """生成脚本"""
        if not self.script_theme_input.text():
            QMessageBox.warning(self, "警告", "请输入脚本主题")
            return
        
        # 获取脚本参数
        video_type = self.script_type_combo.currentText()
        theme = self.script_theme_input.text()
        duration = self.script_duration_spin.value()
        
        # 禁用按钮，显示进度
        self.generate_script_btn.setEnabled(False)
        self.script_results.setText("正在生成脚本...")
        self.status_label.setText("正在生成脚本...")
        
        # 异步生成脚本
        asyncio.create_task(self._execute_script_generation(video_type, theme, duration))
    
    async def _execute_script_generation(self, video_type: str, theme: str, duration: int):
        """执行脚本生成"""
        try:
            # 使用内容生成器生成脚本
            result = await self.content_generator.generate_script(
                video_type=video_type,
                theme=theme,
                duration=duration
            )
            
            if result.success:
                self.script_results.setText(result.content)
                self.status_label.setText("脚本生成完成")
            else:
                self.script_results.setText(f"生成失败: {result.error_message}")
                self.status_label.setText("脚本生成失败")
                
        except Exception as e:
            error_msg = f"脚本生成出错: {str(e)}"
            self.script_results.setText(error_msg)
            self.status_label.setText("脚本生成出错")
        finally:
            self.generate_script_btn.setEnabled(True)
        
    def _start_tts_synthesis(self):
        """开始TTS语音合成"""
        text = self.tts_text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入要合成的文本")
            return
            
        self.synthesize_btn.setEnabled(False)
        self.tts_progress.setVisible(True)
        self.tts_progress.setValue(0)
        self.status_label.setText("正在合成语音...")
        
        # 开始语音合成
        asyncio.create_task(self._execute_tts_synthesis(text))
        
    async def _execute_tts_synthesis(self, text: str):
        """执行TTS语音合成"""
        try:
            voice_type = self.voice_type_combo.currentText()
            emotion = self.emotion_type_combo.currentText()
            speed = self.speed_slider.value() / 100.0
            
            # 生成输出文件路径
            import tempfile
            output_path = tempfile.mktemp(suffix='.wav')
            
            # 执行语音合成
            success = await self.tts_engine.synthesize(
                text=text,
                output_path=output_path,
                voice_type=voice_type,
                emotion=emotion,
                speed=speed
            )
            
            if success:
                self.current_tts_file = output_path
                self.play_btn.setEnabled(True)
                self.status_label.setText("语音合成完成")
            else:
                self.status_label.setText("语音合成失败")
                
        except Exception as e:
            self.status_label.setText(f"合成错误: {str(e)}")
        finally:
            self.synthesize_btn.setEnabled(True)
            self.tts_progress.setVisible(False)
            
    def _play_tts_audio(self):
        """播放TTS音频"""
        if hasattr(self, 'current_tts_file') and self.current_tts_file:
            self.media_player.setSource(QUrl.fromLocalFile(self.current_tts_file))
            self.media_player.play()
            
    def _on_recent_task_clicked(self, item):
        """最近任务点击"""
        task_data = item.data(Qt.ItemDataRole.UserRole)
        if task_data:
            self._select_tool(task_data['tool_type'])
            
    def _on_ai_task_completed(self, task_id: str, result: Any):
        """AI任务完成"""
        self.status_label.setText(f"任务 {task_id} 完成")
        
    def _on_ai_task_failed(self, task_id: str, error: str):
        """AI任务失败"""
        self.status_label.setText(f"任务 {task_id} 失败: {error}")
        
    def _on_tts_completed(self, output_path: str):
        """TTS合成完成"""
        self.current_tts_file = output_path
        self.play_btn.setEnabled(True)
        
    def _on_tts_error(self, error: str):
        """TTS合成错误"""
        QMessageBox.critical(self, "错误", f"语音合成失败: {error}")
    
    def _on_content_generation_completed(self, request_id: str, result: object):
        """内容生成完成"""
        self.status_label.setText(f"内容生成完成: {request_id}")
        
        # 根据当前工具类型处理结果
        if hasattr(self, 'current_tool_type'):
            if self.current_tool_type == AIToolType.COMMENTARY:
                if hasattr(self, 'commentary_results'):
                    self.commentary_results.setText(result.content)
            elif self.current_tool_type == AIToolType.SCRIPT_GENERATION:
                if hasattr(self, 'script_results'):
                    self.script_results.setText(result.content)
    
    def _on_content_generation_failed(self, request_id: str, error: str):
        """内容生成失败"""
        self.status_label.setText(f"内容生成失败: {error}")
        QMessageBox.warning(self, "警告", f"内容生成失败: {error}")
    
    def _on_compilation_analysis_completed(self, request_id: str, result: object):
        """混剪分析完成"""
        self.status_label.setText(f"混剪分析完成: {request_id}")
        
        if hasattr(self, 'compilation_results') and result.success:
            # 显示混剪结果
            segments_text = "检测到以下精彩片段：\n\n"
            for i, segment in enumerate(result.segments[:5]):  # 显示前5个片段
                segments_text += f"{i+1}. {segment.start_time:.1f}-{segment.end_time:.1f}s - {segment.description}\n"
                segments_text += f"   场景类型: {segment.scene_type.value}, 评分: {segment.energy_score:.2f}\n\n"
            
            segments_text += f"总计检测到 {len(result.segments)} 个片段，总时长 {result.compilation_plan.total_duration:.1f} 秒。"
            self.compilation_results.setText(segments_text)
    
    def _on_compilation_analysis_failed(self, request_id: str, error: str):
        """混剪分析失败"""
        self.status_label.setText(f"混剪分析失败: {error}")
        QMessageBox.warning(self, "警告", f"混剪分析失败: {error}")
        
    def _load_tools_config(self) -> Dict[AIToolType, AIToolConfig]:
        """加载工具配置"""
        return {
            AIToolType.COMMENTARY: AIToolConfig(
                AIToolType.COMMENTARY, "AI解说生成", "智能生成视频解说", "🎬"
            ),
            AIToolType.COMPILATION: AIToolConfig(
                AIToolType.COMPILATION, "AI混剪生成", "自动检测精彩片段", "⚡"
            ),
            AIToolType.SUBTITLE: AIToolConfig(
                AIToolType.SUBTITLE, "AI字幕生成", "语音识别生成字幕", "📝"
            ),
            AIToolType.TTS: AIToolConfig(
                AIToolType.TTS, "TTS语音合成", "文本转自然语音", "🔊"
            ),
            AIToolType.CONTENT_ANALYSIS: AIToolConfig(
                AIToolType.CONTENT_ANALYSIS, "内容分析", "深度分析视频内容", "🔍"
            ),
            AIToolType.SCRIPT_GENERATION: AIToolConfig(
                AIToolType.SCRIPT_GENERATION, "脚本生成", "创意视频脚本生成", "📜"
            )
        }
        
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("ai_tools", {})
        
        # 应用设置
        if "default_voice" in settings:
            index = self.voice_type_combo.findText(settings["default_voice"])
            if index >= 0:
                self.voice_type_combo.setCurrentIndex(index)
                
        if "default_emotion" in settings:
            index = self.emotion_type_combo.findText(settings["default_emotion"])
            if index >= 0:
                self.emotion_type_combo.setCurrentIndex(index)
                
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_voice": self.voice_type_combo.currentText(),
            "default_emotion": self.emotion_type_combo.currentText()
        }
        
        self.settings_manager.set_setting("ai_tools", settings)
        
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #ai_tools_sidebar {
                background-color: #f5f5f5;
                border-right: 1px solid #e8e8e8;
            }
            
            #ai_tools_work_area {
                background-color: #ffffff;
            }
            
            #ai_tools_status_bar {
                background-color: #f0f0f0;
                border-top: 1px solid #e8e8e8;
            }
            
            QPushButton#primary_button {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            
            QPushButton#primary_button:hover {
                background-color: #40a9ff;
            }
            
            QPushButton#primary_button:pressed {
                background-color: #096dd9;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d9d9d9;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 设置工具按钮样式
        for tool_type, btn in self.tool_buttons.items():
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    border: none;
                    border-radius: 4px;
                    background-color: transparent;
                }
                
                QPushButton:hover {
                    background-color: #e6f7ff;
                }
                
                QPushButton:checked {
                    background-color: #1890ff;
                    color: white;
                }
            """)
            
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        
        # 清理TTS引擎
        if hasattr(self, 'tts_engine'):
            self.tts_engine.cleanup()
        
        # 清理内容生成器
        if hasattr(self, 'content_generator'):
            self.content_generator.cleanup()
        
        # 清理混剪生成器
        if hasattr(self, 'compilation_generator'):
            self.compilation_generator.cleanup()
            
        # 清理媒体播放器
        if hasattr(self, 'media_player'):
            self.media_player.stop()
            
        super().closeEvent(event)


class AIToolsPage(QWidget):
    """AI工具页面"""
    
    def __init__(self, ai_service: AIService, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)

        self.ai_service = ai_service
        self.settings_manager = settings_manager
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建AI工具面板
        self.tools_panel = AIToolsPanel(self.ai_service, self.settings_manager)
        layout.addWidget(self.tools_panel)
        
    def get_tools_panel(self) -> AIToolsPanel:
        """获取工具面板"""
        return self.tools_panel