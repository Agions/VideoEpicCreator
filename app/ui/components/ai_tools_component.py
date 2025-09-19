#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业AI工具面板 - 集成所有国产大模型的企业级AI解决方案
支持短剧解说生成、混剪脚本生成、字幕生成和翻译、语音合成、场景分析和智能剪辑
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
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
    QApplication, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen

from app.ai.ai_service import AIService
from app.ai.interfaces import AITaskType, AIRequest, AIResponse, create_text_generation_request, create_commentary_request
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class AITaskType(Enum):
    """AI任务类型"""
    COMMENTARY_GENERATION = "commentary_generation"      # 短剧解说生成
    SCRIPT_GENERATION = "script_generation"              # 混剪脚本生成
    SUBTITLE_GENERATION = "subtitle_generation"          # 字幕生成
    SUBTITLE_TRANSLATION = "subtitle_translation"        # 字幕翻译
    SPEECH_SYNTHESIS = "speech_synthesis"                # 语音合成
    SCENE_ANALYSIS = "scene_analysis"                    # 场景分析
    INTELLIGENT_EDITING = "intelligent_editing"          # 智能剪辑
    CONTENT_QUALITY_ASSESSMENT = "content_quality_assessment"  # 内容质量评估


class AIModelProvider(Enum):
    """AI模型提供商"""
    QIANWEN = "qianwen"           # 通义千问
    WENXIN = "wenxin"             # 文心一言
    ZHIPU = "zhipu"               # 智谱AI
    XUNFEI = "xunfei"             # 讯飞星火
    HUNYUAN = "hunyuan"           # 腾讯混元
    DEEPSEEK = "deepseek"          # DeepSeek


@dataclass
class AITask:
    """AI任务数据结构"""
    task_id: str
    task_type: AITaskType
    title: str
    description: str
    input_data: Dict[str, Any]
    selected_model: AIModelProvider
    priority: int = 1
    status: str = "pending"
    progress: float = 0.0
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    result: Any = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class AIContentStyle(Enum):
    """内容风格"""
    HUMOROUS = "幽默风趣"        # 幽默风趣
    PROFESSIONAL = "专业解说"     # 专业解说
    EMOTIONAL = "情感共鸣"       # 情感共鸣
    SUSPENSEFUL = "悬念迭起"     # 悬念迭起
    EDUCATIONAL = "知识科普"     # 知识科普
    ENTERTAINING = "娱乐八卦"     # 娱乐八卦
    INSPIRATIONAL = "励志正能量" # 励志正能量
    DRAMATIC = "戏剧冲突"       # 戏剧冲突


class SubtitleStyle(Enum):
    """字幕风格"""
    MODERN = "现代简约"          # 现代简约
    CLASSIC = "经典复古"        # 经典复古
    CARTOON = "卡通可爱"        # 卡通可爱
    ELEGANT = "优雅文艺"        # 优雅文艺
    TECHNOLOGICAL = "科技感"     # 科技感
    MINIMALIST = "极简主义"      # 极简主义


class AIToolsPanel(QWidget):
    """专业AI工具面板"""
    
    # 信号定义
    task_created = pyqtSignal(object)                    # 任务创建
    task_started = pyqtSignal(str)                       # 任务开始
    task_progress = pyqtSignal(str, float)               # 任务进度
    task_completed = pyqtSignal(str, object)             # 任务完成
    task_failed = pyqtSignal(str, str)                   # 任务失败
    model_status_changed = pyqtSignal(str, bool)        # 模型状态变化
    cost_updated = pyqtSignal(float)                     # 成本更新
    content_generated = pyqtSignal(str, str)             # 内容生成完成
    
    def __init__(self, ai_service: AIService, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.settings_manager = settings_manager
        self.cost_manager = ai_service.cost_manager
        self.load_balancer = ai_service.load_balancer
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # 任务管理
        self.active_tasks: Dict[str, AITask] = {}
        self.completed_tasks: Dict[str, AITask] = {}
        self.task_counter = 0
        
        # 模板系统
        self.templates = self._load_templates()
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # 每秒更新状态
        
        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 标题栏
        title_widget = self._create_title_bar()
        main_layout.addWidget(title_widget)
        
        # 主要内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧工具栏
        left_panel = self._create_left_panel()
        content_splitter.addWidget(left_panel)
        
        # 右侧工作区
        right_panel = self._create_right_panel()
        content_splitter.addWidget(right_panel)
        
        # 设置分割器比例
        content_splitter.setSizes([300, 900])
        main_layout.addWidget(content_splitter)
        
        # 底部状态栏
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
        
    def _create_title_bar(self) -> QWidget:
        """创建标题栏"""
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("🤖 专业AI工具面板")
        title_label.setObjectName("title_label")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 快速操作按钮
        quick_actions = [
            ("📊", "查看统计", self.show_statistics),
            ("⚙️", "设置", self.show_settings),
            ("📚", "模板库", self.show_templates),
            ("💰", "成本管理", self.show_cost_management)
        ]
        
        for icon, tooltip, handler in quick_actions:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(handler)
            btn.setObjectName("quick_action_btn")
            title_layout.addWidget(btn)
        
        return title_widget
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # AI工具选择
        tools_group = QGroupBox("AI工具")
        tools_layout = QVBoxLayout(tools_group)
        
        # 工具列表
        self.tools_list = QListWidget()
        self.tools_list.setObjectName("tools_list")
        
        tools_data = [
            ("🎬", "短剧解说生成", AITaskType.COMMENTARY_GENERATION),
            ("📝", "混剪脚本生成", AITaskType.SCRIPT_GENERATION),
            ("📜", "字幕生成", AITaskType.SUBTITLE_GENERATION),
            ("🌐", "字幕翻译", AITaskType.SUBTITLE_TRANSLATION),
            ("🔊", "语音合成", AITaskType.SPEECH_SYNTHESIS),
            ("🎯", "场景分析", AITaskType.SCENE_ANALYSIS),
            ("✂️", "智能剪辑", AITaskType.INTELLIGENT_EDITING),
            ("📈", "内容质量评估", AITaskType.CONTENT_QUALITY_ASSESSMENT)
        ]
        
        for icon, name, task_type in tools_data:
            item = QListWidgetItem(f"{icon} {name}")
            item.setData(Qt.ItemDataRole.UserRole, task_type)
            self.tools_list.addItem(item)
        
        self.tools_list.currentItemChanged.connect(self.on_tool_selected)
        tools_layout.addWidget(self.tools_list)
        
        left_layout.addWidget(tools_group)
        
        # 模型状态
        model_group = QGroupBox("模型状态")
        model_layout = QVBoxLayout(model_group)
        
        self.model_status_tree = QTreeWidget()
        self.model_status_tree.setHeaderLabels(["模型", "状态", "延迟", "成本"])
        self.model_status_tree.setMaximumHeight(200)
        model_layout.addWidget(self.model_status_tree)
        
        left_layout.addWidget(model_group)
        
        # 快速模板
        template_group = QGroupBox("快速模板")
        template_layout = QVBoxLayout(template_group)
        
        self.template_list = QListWidget()
        self.template_list.setMaximumHeight(150)
        self._populate_template_list()
        template_layout.addWidget(self.template_list)
        
        left_layout.addWidget(template_group)
        
        left_layout.addStretch()
        
        return left_panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧工作区"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 工作区域栈
        self.work_stack = QStackedWidget()
        
        # 创建各个工具的工作界面
        self.work_widgets = {}
        
        # 短剧解说生成
        commentary_widget = self._create_commentary_widget()
        self.work_stack.addWidget(commentary_widget)
        self.work_widgets[AITaskType.COMMENTARY_GENERATION] = commentary_widget
        
        # 混剪脚本生成
        script_widget = self._create_script_widget()
        self.work_stack.addWidget(script_widget)
        self.work_widgets[AITaskType.SCRIPT_GENERATION] = script_widget
        
        # 字幕生成
        subtitle_widget = self._create_subtitle_widget()
        self.work_stack.addWidget(subtitle_widget)
        self.work_widgets[AITaskType.SUBTITLE_GENERATION] = subtitle_widget
        
        # 字幕翻译
        translation_widget = self._create_translation_widget()
        self.work_stack.addWidget(translation_widget)
        self.work_widgets[AITaskType.SUBTITLE_TRANSLATION] = translation_widget
        
        # 语音合成
        speech_widget = self._create_speech_widget()
        self.work_stack.addWidget(speech_widget)
        self.work_widgets[AITaskType.SPEECH_SYNTHESIS] = speech_widget
        
        # 场景分析
        scene_widget = self._create_scene_widget()
        self.work_stack.addWidget(scene_widget)
        self.work_widgets[AITaskType.SCENE_ANALYSIS] = scene_widget
        
        # 智能剪辑
        editing_widget = self._create_editing_widget()
        self.work_stack.addWidget(editing_widget)
        self.work_widgets[AITaskType.INTELLIGENT_EDITING] = editing_widget
        
        # 内容质量评估
        quality_widget = self._create_quality_widget()
        self.work_stack.addWidget(quality_widget)
        self.work_widgets[AITaskType.CONTENT_QUALITY_ASSESSMENT] = quality_widget
        
        right_layout.addWidget(self.work_stack)
        
        return right_panel
    
    def _create_commentary_widget(self) -> QWidget:
        """创建短剧解说生成界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输入区域
        input_group = QGroupBox("视频信息")
        input_layout = QFormLayout(input_group)
        
        # 视频标题
        self.video_title = QLineEdit()
        self.video_title.setPlaceholderText("请输入视频标题")
        input_layout.addRow("视频标题:", self.video_title)
        
        # 视频描述
        self.video_description = QTextEdit()
        self.video_description.setPlaceholderText("请输入视频描述，包括主要情节、人物等信息")
        self.video_description.setMaximumHeight(100)
        input_layout.addRow("视频描述:", self.video_description)
        
        # 视频时长
        self.video_duration = QSpinBox()
        self.video_duration.setRange(1, 3600)
        self.video_duration.setSuffix(" 秒")
        input_layout.addRow("视频时长:", self.video_duration)
        
        # 解说风格
        self.commentary_style = QComboBox()
        for style in AIContentStyle:
            self.commentary_style.addItem(style.value)
        input_layout.addRow("解说风格:", self.commentary_style)
        
        layout.addWidget(input_group)
        
        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)
        
        # 模型选择
        self.commentary_model = QComboBox()
        self._populate_model_combo(self.commentary_model)
        advanced_layout.addRow("AI模型:", self.commentary_model)
        
        # 解说长度
        self.commentary_length = QSlider(Qt.Orientation.Horizontal)
        self.commentary_length.setRange(100, 2000)
        self.commentary_length.setValue(500)
        self.commentary_length.setTickPosition(QSlider.TickPosition.TicksBelow)
        advanced_layout.addRow("解说长度:", self.commentary_length)
        
        # 语言风格
        self.language_style = QComboBox()
        self.language_style.addItems(["口语化", "书面语", "网络用语", "正式用语"])
        advanced_layout.addRow("语言风格:", self.language_style)
        
        layout.addWidget(advanced_group)
        
        # 生成按钮
        generate_btn = QPushButton("🎬 生成解说")
        generate_btn.clicked.connect(lambda: self.generate_commentary())
        generate_btn.setObjectName("generate_btn")
        layout.addWidget(generate_btn)
        
        # 结果显示
        result_group = QGroupBox("生成结果")
        result_layout = QVBoxLayout(result_group)
        
        self.commentary_result = QTextEdit()
        self.commentary_result.setPlaceholderText("生成的解说内容将在这里显示...")
        self.commentary_result.setReadOnly(True)
        result_layout.addWidget(self.commentary_result)
        
        # 结果操作按钮
        result_actions = QHBoxLayout()
        
        copy_btn = QPushButton("📋 复制")
        copy_btn.clicked.connect(lambda: self.copy_result(self.commentary_result))
        result_actions.addWidget(copy_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(lambda: self.save_result(self.commentary_result, "解说"))
        result_actions.addWidget(save_btn)
        
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(lambda: self.edit_result(self.commentary_result))
        result_actions.addWidget(edit_btn)
        
        result_actions.addStretch()
        result_layout.addLayout(result_actions)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_script_widget(self) -> QWidget:
        """创建混剪脚本生成界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 项目信息
        project_group = QGroupBox("项目信息")
        project_layout = QFormLayout(project_group)
        
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("请输入项目名称")
        project_layout.addRow("项目名称:", self.project_name)
        
        self.project_theme = QLineEdit()
        self.project_theme.setPlaceholderText("请输入项目主题")
        project_layout.addRow("项目主题:", self.project_theme)
        
        self.target_audience = QComboBox()
        self.target_audience.addItems(["年轻观众", "成年观众", "专业观众", "大众观众"])
        project_layout.addRow("目标观众:", self.target_audience)
        
        layout.addWidget(project_group)
        
        # 内容规划
        content_group = QGroupBox("内容规划")
        content_layout = QFormLayout(content_group)
        
        self.video_count = QSpinBox()
        self.video_count.setRange(1, 100)
        self.video_count.setValue(10)
        content_layout.addRow("视频数量:", self.video_count)
        
        self.video_duration = QSpinBox()
        self.video_duration.setRange(30, 600)
        self.video_duration.setValue(60)
        self.video_duration.setSuffix(" 秒")
        content_layout.addRow("单集时长:", self.video_duration)
        
        self.content_style = QComboBox()
        for style in AIContentStyle:
            self.content_style.addItem(style.value)
        content_layout.addRow("内容风格:", self.content_style)
        
        layout.addWidget(content_group)
        
        # 生成按钮
        generate_btn = QPushButton("📝 生成脚本")
        generate_btn.clicked.connect(lambda: self.generate_script())
        generate_btn.setObjectName("generate_btn")
        layout.addWidget(generate_btn)
        
        # 结果显示
        result_group = QGroupBox("脚本结果")
        result_layout = QVBoxLayout(result_group)
        
        self.script_result = QTextEdit()
        self.script_result.setPlaceholderText("生成的混剪脚本将在这里显示...")
        self.script_result.setReadOnly(True)
        result_layout.addWidget(self.script_result)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_subtitle_widget(self) -> QWidget:
        """创建字幕生成界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 视频输入
        video_group = QGroupBox("视频信息")
        video_layout = QFormLayout(video_group)
        
        self.subtitle_video_file = QLineEdit()
        self.subtitle_video_file.setPlaceholderText("选择视频文件")
        video_layout.addRow("视频文件:", self.subtitle_video_file)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(lambda: self.browse_video_file(self.subtitle_video_file))
        video_layout.addRow("", browse_btn)
        
        layout.addWidget(video_group)
        
        # 字幕设置
        settings_group = QGroupBox("字幕设置")
        settings_layout = QFormLayout(settings_group)
        
        self.subtitle_language = QComboBox()
        self.subtitle_language.addItems(["中文", "英文", "日文", "韩文"])
        settings_layout.addRow("字幕语言:", self.subtitle_language)
        
        self.subtitle_style = QComboBox()
        for style in SubtitleStyle:
            self.subtitle_style.addItem(style.value)
        settings_layout.addRow("字幕风格:", self.subtitle_style)
        
        self.subtitle_position = QComboBox()
        self.subtitle_position.addItems(["底部", "顶部", "中间"])
        settings_layout.addRow("字幕位置:", self.subtitle_position)
        
        layout.addWidget(settings_group)
        
        # 生成按钮
        generate_btn = QPushButton("📜 生成字幕")
        generate_btn.clicked.connect(lambda: self.generate_subtitle())
        generate_btn.setObjectName("generate_btn")
        layout.addWidget(generate_btn)
        
        # 结果显示
        result_group = QGroupBox("字幕结果")
        result_layout = QVBoxLayout(result_group)
        
        self.subtitle_result = QTextEdit()
        self.subtitle_result.setPlaceholderText("生成的字幕内容将在这里显示...")
        self.subtitle_result.setReadOnly(True)
        result_layout.addWidget(self.subtitle_result)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_translation_widget(self) -> QWidget:
        """创建字幕翻译界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 原字幕输入
        input_group = QGroupBox("原字幕")
        input_layout = QVBoxLayout(input_group)
        
        self.original_subtitle = QTextEdit()
        self.original_subtitle.setPlaceholderText("请输入需要翻译的字幕内容")
        input_layout.addWidget(self.original_subtitle)
        
        layout.addWidget(input_group)
        
        # 翻译设置
        settings_group = QGroupBox("翻译设置")
        settings_layout = QFormLayout(settings_group)
        
        self.source_language = QComboBox()
        self.source_language.addItems(["中文", "英文", "日文", "韩文"])
        settings_layout.addRow("源语言:", self.source_language)
        
        self.target_language = QComboBox()
        self.target_language.addItems(["英文", "中文", "日文", "韩文"])
        settings_layout.addRow("目标语言:", self.target_language)
        
        self.translation_style = QComboBox()
        self.translation_style.addItems(["直译", "意译", "本地化", "创意翻译"])
        settings_layout.addRow("翻译风格:", self.translation_style)
        
        layout.addWidget(settings_group)
        
        # 生成按钮
        generate_btn = QPushButton("🌐 翻译字幕")
        generate_btn.clicked.connect(lambda: self.translate_subtitle())
        generate_btn.setObjectName("generate_btn")
        layout.addWidget(generate_btn)
        
        # 结果显示
        result_group = QGroupBox("翻译结果")
        result_layout = QVBoxLayout(result_group)
        
        self.translation_result = QTextEdit()
        self.translation_result.setPlaceholderText("翻译结果将在这里显示...")
        self.translation_result.setReadOnly(True)
        result_layout.addWidget(self.translation_result)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_speech_widget(self) -> QWidget:
        """创建语音合成界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 文本输入
        input_group = QGroupBox("文本内容")
        input_layout = QVBoxLayout(input_group)
        
        self.speech_text = QTextEdit()
        self.speech_text.setPlaceholderText("请输入需要合成的文本内容")
        input_layout.addWidget(self.speech_text)
        
        layout.addWidget(input_group)
        
        # 语音设置
        settings_group = QGroupBox("语音设置")
        settings_layout = QFormLayout(settings_group)
        
        self.voice_type = QComboBox()
        self.voice_type.addItems(["男声", "女声", "童声", "老年人声音"])
        settings_layout.addRow("语音类型:", self.voice_type)
        
        self.voice_style = QComboBox()
        self.voice_style.addItems(["标准", "温柔", "激昂", "沉稳", "活泼"])
        settings_layout.addRow("语音风格:", self.voice_style)
        
        self.speech_speed = QSlider(Qt.Orientation.Horizontal)
        self.speech_speed.setRange(50, 200)
        self.speech_speed.setValue(100)
        self.speech_speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        settings_layout.addRow("语速:", self.speech_speed)
        
        self.speech_pitch = QSlider(Qt.Orientation.Horizontal)
        self.speech_pitch.setRange(50, 200)
        self.speech_pitch.setValue(100)
        self.speech_pitch.setTickPosition(QSlider.TickPosition.TicksBelow)
        settings_layout.addRow("音调:", self.speech_pitch)
        
        layout.addWidget(settings_group)
        
        # 生成按钮
        generate_btn = QPushButton("🔊 合成语音")
        generate_btn.clicked.connect(lambda: self.generate_speech())
        generate_btn.setObjectName("generate_btn")
        layout.addWidget(generate_btn)
        
        # 播放控制
        playback_group = QGroupBox("播放控制")
        playback_layout = QHBoxLayout(playback_group)
        
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.clicked.connect(self.play_speech)
        playback_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.clicked.connect(self.pause_speech)
        playback_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.clicked.connect(self.stop_speech)
        playback_layout.addWidget(self.stop_btn)
        
        playback_layout.addStretch()
        layout.addWidget(playback_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_scene_widget(self) -> QWidget:
        """创建场景分析界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 视频输入
        video_group = QGroupBox("视频文件")
        video_layout = QFormLayout(video_group)
        
        self.scene_video_file = QLineEdit()
        self.scene_video_file.setPlaceholderText("选择视频文件")
        video_layout.addRow("视频文件:", self.scene_video_file)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(lambda: self.browse_video_file(self.scene_video_file))
        video_layout.addRow("", browse_btn)
        
        layout.addWidget(video_group)
        
        # 分析设置
        settings_group = QGroupBox("分析设置")
        settings_layout = QFormLayout(settings_group)
        
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["场景分割", "物体识别", "情感分析", "动作识别", "质量评估"])
        settings_layout.addRow("分析类型:", self.analysis_type)
        
        self.analysis_detail = QComboBox()
        self.analysis_detail.addItems(["基础", "详细", "专业"])
        settings_layout.addRow("分析程度:", self.analysis_detail)
        
        layout.addWidget(settings_group)
        
        # 分析按钮
        analyze_btn = QPushButton("🎯 开始分析")
        analyze_btn.clicked.connect(lambda: self.analyze_scene())
        analyze_btn.setObjectName("generate_btn")
        layout.addWidget(analyze_btn)
        
        # 结果显示
        result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout(result_group)
        
        self.scene_result = QTextEdit()
        self.scene_result.setPlaceholderText("场景分析结果将在这里显示...")
        self.scene_result.setReadOnly(True)
        result_layout.addWidget(self.scene_result)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_editing_widget(self) -> QWidget:
        """创建智能剪辑界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 项目信息
        project_group = QGroupBox("剪辑项目")
        project_layout = QFormLayout(project_group)
        
        self.editing_project = QLineEdit()
        self.editing_project.setPlaceholderText("选择剪辑项目")
        project_layout.addRow("项目名称:", self.editing_project)
        
        layout.addWidget(project_group)
        
        # 剪辑设置
        settings_group = QGroupBox("剪辑设置")
        settings_layout = QFormLayout(settings_group)
        
        self.editing_style = QComboBox()
        self.editing_style.addItems(["快节奏", "慢节奏", "节奏变化", "情感节奏"])
        settings_layout.addRow("剪辑风格:", self.editing_style)
        
        self.editing_length = QSpinBox()
        self.editing_length.setRange(15, 300)
        self.editing_length.setValue(60)
        self.editing_length.setSuffix(" 秒")
        settings_layout.addRow("目标时长:", self.editing_length)
        
        self.auto_music = QCheckBox()
        self.auto_music.setChecked(True)
        settings_layout.addRow("自动配乐:", self.auto_music)
        
        self.auto_transition = QCheckBox()
        self.auto_transition.setChecked(True)
        settings_layout.addRow("自动转场:", self.auto_transition)
        
        layout.addWidget(settings_group)
        
        # 剪辑按钮
        edit_btn = QPushButton("✂️ 开始剪辑")
        edit_btn.clicked.connect(lambda: self.start_editing())
        edit_btn.setObjectName("generate_btn")
        layout.addWidget(edit_btn)
        
        # 进度显示
        progress_group = QGroupBox("剪辑进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.editing_progress = QProgressBar()
        self.editing_progress.setRange(0, 100)
        progress_layout.addWidget(self.editing_progress)
        
        self.editing_status = QLabel("等待开始...")
        progress_layout.addWidget(self.editing_status)
        
        layout.addWidget(progress_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_quality_widget(self) -> QWidget:
        """创建内容质量评估界面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 内容输入
        input_group = QGroupBox("评估内容")
        input_layout = QVBoxLayout(input_group)
        
        self.quality_content = QTextEdit()
        self.quality_content.setPlaceholderText("请输入需要评估的内容")
        input_layout.addWidget(self.quality_content)
        
        layout.addWidget(input_group)
        
        # 评估设置
        settings_group = QGroupBox("评估设置")
        settings_layout = QFormLayout(settings_group)
        
        self.quality_type = QComboBox()
        self.quality_type.addItems(["综合评估", "创意性", "专业性", "观赏性", "传播性"])
        settings_layout.addRow("评估类型:", self.quality_type)
        
        self.quality_standard = QComboBox()
        self.quality_standard.addItems(["基础标准", "专业标准", "行业标准"])
        settings_layout.addRow("评估标准:", self.quality_standard)
        
        layout.addWidget(settings_group)
        
        # 评估按钮
        assess_btn = QPushButton("📈 开始评估")
        assess_btn.clicked.connect(lambda: self.assess_quality())
        assess_btn.setObjectName("generate_btn")
        layout.addWidget(assess_btn)
        
        # 结果显示
        result_group = QGroupBox("评估结果")
        result_layout = QVBoxLayout(result_group)
        
        self.quality_result = QTextEdit()
        self.quality_result.setPlaceholderText("质量评估结果将在这里显示...")
        self.quality_result.setReadOnly(True)
        result_layout.addWidget(self.quality_result)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_status_bar(self) -> QWidget:
        """创建状态栏"""
        status_bar = QWidget()
        status_bar.setObjectName("status_bar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 任务信息
        self.task_count_label = QLabel("活跃任务: 0")
        status_layout.addWidget(self.task_count_label)
        
        # 成本信息
        self.cost_label = QLabel("今日成本: ¥0.00")
        status_layout.addWidget(self.cost_label)
        
        # 模型状态
        self.model_status_label = QLabel("模型状态: 正常")
        status_layout.addWidget(self.model_status_label)
        
        return status_bar
    
    def _populate_model_combo(self, combo: QComboBox):
        """填充模型下拉框"""
        for provider in AIModelProvider:
            combo.addItem(provider.value)
    
    def _populate_template_list(self):
        """填充模板列表"""
        templates = [
            "搞笑短剧模板",
            "情感短剧模板", 
            "悬疑短剧模板",
            "教育短剧模板",
            "美食短剧模板",
            "旅行短剧模板",
            "科技短剧模板"
        ]
        
        for template in templates:
            item = QListWidgetItem(template)
            self.template_list.addItem(item)
    
    def _connect_signals(self):
        """连接信号"""
        # AI管理器信号
        self.ai_manager.model_response_ready.connect(self.on_ai_response)
        self.ai_manager.metrics_updated.connect(self.on_metrics_updated)
        self.ai_manager.cost_alert.connect(self.on_cost_alert)
        
        # 成本管理器信号
        self.cost_manager.model_costs_updated.connect(self.on_model_costs_updated)
    
    def on_tool_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """工具选择事件"""
        if current:
            task_type = current.data(Qt.ItemDataRole.UserRole)
            if task_type in self.work_widgets:
                self.work_stack.setCurrentWidget(self.work_widgets[task_type])
    
    def generate_commentary(self):
        """生成短剧解说"""
        # 获取输入数据
        video_info = {
            "title": self.video_title.text(),
            "description": self.video_description.toPlainText(),
            "duration": self.video_duration.value(),
            "style": self.commentary_style.currentText()
        }
        
        # 创建任务
        task = AITask(
            task_id=f"commentary_{self.task_counter}",
            task_type=AITaskType.COMMENTARY_GENERATION,
            title="短剧解说生成",
            description=f"为视频《{video_info['title']}》生成解说",
            input_data=video_info,
            selected_model=AIModelProvider(self.commentary_model.currentText())
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        # 发送任务创建信号
        self.task_created.emit(task)
        
        # 异步执行任务
        asyncio.create_task(self._execute_commentary_task(task))
    
    def generate_script(self):
        """生成混剪脚本"""
        project_info = {
            "name": self.project_name.text(),
            "theme": self.project_theme.text(),
            "audience": self.target_audience.currentText(),
            "video_count": self.video_count.value(),
            "duration": self.video_duration.value(),
            "style": self.content_style.currentText()
        }
        
        task = AITask(
            task_id=f"script_{self.task_counter}",
            task_type=AITaskType.SCRIPT_GENERATION,
            title="混剪脚本生成",
            description=f"为项目《{project_info['name']}》生成混剪脚本",
            input_data=project_info,
            selected_model=AIModelProvider.QIANWEN  # 默认使用千问
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_script_task(task))
    
    def generate_subtitle(self):
        """生成字幕"""
        subtitle_info = {
            "video_file": self.subtitle_video_file.text(),
            "language": self.subtitle_language.currentText(),
            "style": self.subtitle_style.currentText(),
            "position": self.subtitle_position.currentText()
        }
        
        task = AITask(
            task_id=f"subtitle_{self.task_counter}",
            task_type=AITaskType.SUBTITLE_GENERATION,
            title="字幕生成",
            description=f"为视频生成{subtitle_info['language']}字幕",
            input_data=subtitle_info,
            selected_model=AIModelProvider.QIANWEN
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_subtitle_task(task))
    
    def translate_subtitle(self):
        """翻译字幕"""
        translation_info = {
            "original_text": self.original_subtitle.toPlainText(),
            "source_language": self.source_language.currentText(),
            "target_language": self.target_language.currentText(),
            "style": self.translation_style.currentText()
        }
        
        task = AITask(
            task_id=f"translation_{self.task_counter}",
            task_type=AITaskType.SUBTITLE_TRANSLATION,
            title="字幕翻译",
            description=f"将{translation_info['source_language']}翻译为{translation_info['target_language']}",
            input_data=translation_info,
            selected_model=AIModelProvider.WENXIN
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_translation_task(task))
    
    def generate_speech(self):
        """生成语音"""
        speech_info = {
            "text": self.speech_text.toPlainText(),
            "voice_type": self.voice_type.currentText(),
            "voice_style": self.voice_style.currentText(),
            "speed": self.speech_speed.value(),
            "pitch": self.speech_pitch.value()
        }
        
        task = AITask(
            task_id=f"speech_{self.task_counter}",
            task_type=AITaskType.SPEECH_SYNTHESIS,
            title="语音合成",
            description="合成语音",
            input_data=speech_info,
            selected_model=AIModelProvider.XUNFEI
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_speech_task(task))
    
    def analyze_scene(self):
        """分析场景"""
        scene_info = {
            "video_file": self.scene_video_file.text(),
            "analysis_type": self.analysis_type.currentText(),
            "detail_level": self.analysis_detail.currentText()
        }
        
        task = AITask(
            task_id=f"scene_{self.task_counter}",
            task_type=AITaskType.SCENE_ANALYSIS,
            title="场景分析",
            description=f"分析视频的{scene_info['analysis_type']}",
            input_data=scene_info,
            selected_model=AIModelProvider.ZHIPU
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_scene_task(task))
    
    def start_editing(self):
        """开始智能剪辑"""
        editing_info = {
            "project": self.editing_project.text(),
            "style": self.editing_style.currentText(),
            "target_length": self.editing_length.value(),
            "auto_music": self.auto_music.isChecked(),
            "auto_transition": self.auto_transition.isChecked()
        }
        
        task = AITask(
            task_id=f"editing_{self.task_counter}",
            task_type=AITaskType.INTELLIGENT_EDITING,
            title="智能剪辑",
            description=f"对项目《{editing_info['project']}》进行智能剪辑",
            input_data=editing_info,
            selected_model=AIModelProvider.HUNYUAN
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_editing_task(task))
    
    def assess_quality(self):
        """评估内容质量"""
        quality_info = {
            "content": self.quality_content.toPlainText(),
            "assessment_type": self.quality_type.currentText(),
            "standard": self.quality_standard.currentText()
        }
        
        task = AITask(
            task_id=f"quality_{self.task_counter}",
            task_type=AITaskType.CONTENT_QUALITY_ASSESSMENT,
            title="内容质量评估",
            description="评估内容质量",
            input_data=quality_info,
            selected_model=AIModelProvider.DEEPSEEK
        )
        
        self.task_counter += 1
        self.active_tasks[task.task_id] = task
        
        self.task_created.emit(task)
        asyncio.create_task(self._execute_quality_task(task))
    
    async def _execute_commentary_task(self, task: AITask):
        """执行解说生成任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            # 构建提示词
            prompt = self._build_commentary_prompt(task.input_data)
            
            # 调用AI服务
            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=task.selected_model.value,
                max_tokens=self.commentary_length.value()
            )

            # 提交请求并等待结果
            response = await self.ai_service.process_request(ai_request)
            
            if response.success:
                task.result = response.content
                task.status = "completed"
                task.completed_at = time.time()
                task.progress = 100.0

                # 更新UI
                self.commentary_result.setText(response.content)
                self.task_completed.emit(task.task_id, response.content)
                self.content_generated.emit(task.task_id, response.content)
                
            else:
                task.status = "failed"
                task.error_message = response.error_message
                self.task_failed.emit(task.task_id, response.error_message)
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            # 移动到已完成任务
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_script_task(self, task: AITask):
        """执行脚本生成任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            prompt = self._build_script_prompt(task.input_data)

            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=task.selected_model.value,
                max_tokens=2000
            )

            response = await self.ai_service.process_request(ai_request)
            
            if response.success:
                task.result = response.content
                task.status = "completed"
                task.completed_at = time.time()
                task.progress = 100.0
                
                self.script_result.setText(response.content)
                self.task_completed.emit(task.task_id, response.content)
                
            else:
                task.status = "failed"
                task.error_message = response.error_message
                self.task_failed.emit(task.task_id, response.error_message)
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_subtitle_task(self, task: AITask):
        """执行字幕生成任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            prompt = self._build_subtitle_prompt(task.input_data)
            
            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=task.selected_model.value,
                max_tokens=1500
            )

            response = await self.ai_service.process_request(ai_request)
            
            if response.success:
                task.result = response.content
                task.status = "completed"
                task.completed_at = time.time()
                task.progress = 100.0
                
                self.subtitle_result.setText(response.content)
                self.task_completed.emit(task.task_id, response.content)
                
            else:
                task.status = "failed"
                task.error_message = response.error_message
                self.task_failed.emit(task.task_id, response.error_message)
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_translation_task(self, task: AITask):
        """执行翻译任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            prompt = self._build_translation_prompt(task.input_data)
            
            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=task.selected_model.value,
                max_tokens=2000
            )

            response = await self.ai_service.process_request(ai_request)
            
            if response.success:
                task.result = response.content
                task.status = "completed"
                task.completed_at = time.time()
                task.progress = 100.0
                
                self.translation_result.setText(response.content)
                self.task_completed.emit(task.task_id, response.content)
                
            else:
                task.status = "failed"
                task.error_message = response.error_message
                self.task_failed.emit(task.task_id, response.error_message)
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_speech_task(self, task: AITask):
        """执行语音合成任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            # 这里应该调用语音合成API
            # 目前模拟处理
            await asyncio.sleep(2)
            
            task.result = "语音合成完成"
            task.status = "completed"
            task.completed_at = time.time()
            task.progress = 100.0
            
            self.task_completed.emit(task.task_id, "语音合成完成")
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_scene_task(self, task: AITask):
        """执行场景分析任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            # 模拟场景分析
            await asyncio.sleep(3)
            
            analysis_result = """
场景分析结果：

1. 场景分割：
   - 00:00-00:15: 开场介绍
   - 00:16-00:45: 主要内容
   - 00:46-01:00: 结尾总结

2. 物体识别：
   - 人物: 2人
   - 物品: 桌子、椅子、电脑
   - 场景: 室内办公室

3. 情感分析：
   - 整体情感: 积极
   - 情感变化: 平稳→上扬→平稳
"""
            
            task.result = analysis_result
            task.status = "completed"
            task.completed_at = time.time()
            task.progress = 100.0
            
            self.scene_result.setText(analysis_result)
            self.task_completed.emit(task.task_id, analysis_result)
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_editing_task(self, task: AITask):
        """执行智能剪辑任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            # 模拟剪辑过程
            for i in range(101):
                task.progress = i
                self.task_progress.emit(task.task_id, i)
                self.editing_progress.setValue(i)
                self.editing_status.setText(f"剪辑进度: {i}%")
                await asyncio.sleep(0.1)
            
            task.result = "智能剪辑完成"
            task.status = "completed"
            task.completed_at = time.time()
            
            self.task_completed.emit(task.task_id, "智能剪辑完成")
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    async def _execute_quality_task(self, task: AITask):
        """执行质量评估任务"""
        try:
            self.task_started.emit(task.task_id)
            task.status = "running"
            task.started_at = time.time()
            
            prompt = self._build_quality_prompt(task.input_data)
            
            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=task.selected_model.value,
                max_tokens=1000
            )

            response = await self.ai_service.process_request(ai_request)
            
            if response.success:
                task.result = response.content
                task.status = "completed"
                task.completed_at = time.time()
                task.progress = 100.0
                
                self.quality_result.setText(response.content)
                self.task_completed.emit(task.task_id, response.content)
                
            else:
                task.status = "failed"
                task.error_message = response.error_message
                self.task_failed.emit(task.task_id, response.error_message)
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.task_failed.emit(task.task_id, str(e))
        
        finally:
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)
    
    def _build_commentary_prompt(self, video_info: Dict[str, Any]) -> str:
        """构建解说生成提示词"""
        return f"""
请为以下短剧视频生成{video_info['style']}的解说内容：

视频信息：
- 标题：{video_info['title']}
- 描述：{video_info['description']}
- 时长：{video_info['duration']}秒

要求：
1. 解说风格：{video_info['style']}
2. 语言生动有趣，吸引观众
3. 突出剧情亮点和关键情节点
4. 适合短视频平台的传播特点
5. 控制在适当长度，语速自然

请生成解说文本：
"""
    
    def _build_script_prompt(self, project_info: Dict[str, Any]) -> str:
        """构建脚本生成提示词"""
        return f"""
请为以下短视频项目生成混剪脚本：

项目信息：
- 项目名称：{project_info['name']}
- 项目主题：{project_info['theme']}
- 目标观众：{project_info['audience']}
- 视频数量：{project_info['video_count']}个
- 单集时长：{project_info['duration']}秒
- 内容风格：{project_info['style']}

要求：
1. 根据项目主题设计连贯的内容线
2. 每个视频都有独立的亮点和看点
3. 适合目标观众的喜好和习惯
4. 考虑短视频平台的算法推荐机制
5. 包含吸引人的开头和结尾

请生成详细的混剪脚本：
"""
    
    def _build_subtitle_prompt(self, subtitle_info: Dict[str, Any]) -> str:
        """构建字幕生成提示词"""
        return f"""
请为以下视频生成字幕：

视频信息：
- 视频文件：{subtitle_info['video_file']}
- 字幕语言：{subtitle_info['language']}
- 字幕风格：{subtitle_info['style']}
- 字幕位置：{subtitle_info['position']}

要求：
1. 准确识别视频中的语音内容
2. 时间轴精确同步
3. 语言简洁明了，便于阅读
4. 符合{subtitle_info['style']}风格
5. 适合在{subtitle_info['position']}位置显示

请生成字幕内容（包含时间轴）：
"""
    
    def _build_translation_prompt(self, translation_info: Dict[str, Any]) -> str:
        """构建翻译提示词"""
        return f"""
请将以下字幕内容进行翻译：

原文：
{translation_info['original_text']}

翻译要求：
- 源语言：{translation_info['source_language']}
- 目标语言：{translation_info['target_language']}
- 翻译风格：{translation_info['style']}
- 保持原意的基础上，使表达更符合目标语言习惯
- 考虑文化差异，进行适当的本地化处理

请翻译：
"""
    
    def _build_quality_prompt(self, quality_info: Dict[str, Any]) -> str:
        """构建质量评估提示词"""
        return f"""
请对以下内容进行质量评估：

评估内容：
{quality_info['content']}

评估要求：
- 评估类型：{quality_info['assessment_type']}
- 评估标准：{quality_info['standard']}
- 请从多个维度进行分析和评分
- 提供具体的改进建议
- 给出整体质量等级（优秀/良好/一般/需改进）

请进行详细评估：
"""
    
    def on_ai_response(self, model_provider: str, response):
        """AI响应处理"""
        print(f"收到AI响应: {model_provider} - {response.success}")
    
    def on_metrics_updated(self, metrics: Dict[str, Any]):
        """性能指标更新"""
        self._update_model_status()
    
    def on_cost_alert(self, message: str, amount: float):
        """成本告警"""
        QMessageBox.warning(self, "成本告警", f"{message}\n当前成本: ¥{amount:.2f}")
    
    def on_model_costs_updated(self):
        """模型成本更新"""
        self._update_model_status()
    
    def _update_status(self):
        """更新状态"""
        # 更新任务数量
        active_count = len(self.active_tasks)
        self.task_count_label.setText(f"活跃任务: {active_count}")
        
        # 更新成本信息
        cost_report = self.cost_manager.get_usage_report(1)
        today_cost = cost_report.get('total_cost', 0)
        self.cost_label.setText(f"今日成本: ¥{today_cost:.2f}")
        
        # 更新模型状态
        self._update_model_status()
    
    def _update_model_status(self):
        """更新模型状态"""
        self.model_status_tree.clear()
        
        for provider in AIModelProvider:
            model = self.ai_manager.get_model(provider.value)
            if model and model.is_available():
                # 获取模型指标
                metrics = self.ai_manager.metrics.get(provider.value)
                if metrics:
                    item = QTreeWidgetItem([
                        provider.value,
                        "✅ 正常",
                        f"{metrics.average_response_time:.0f}ms",
                        f"¥{metrics.total_cost:.2f}"
                    ])
                else:
                    item = QTreeWidgetItem([
                        provider.value,
                        "✅ 正常",
                        "N/A",
                        "¥0.00"
                    ])
            else:
                item = QTreeWidgetItem([
                    provider.value,
                    "❌ 不可用",
                    "N/A",
                    "¥0.00"
                ])
            
            self.model_status_tree.addTopLevelItem(item)
    
    def browse_video_file(self, line_edit: QLineEdit):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def copy_result(self, text_edit: QTextEdit):
        """复制结果"""
        text = text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "成功", "内容已复制到剪贴板")
    
    def save_result(self, text_edit: QTextEdit, file_type: str):
        """保存结果"""
        text = text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "警告", "没有内容可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"保存{file_type}", "", 
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "成功", f"{file_type}已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def edit_result(self, text_edit: QTextEdit):
        """编辑结果"""
        text_edit.setReadOnly(False)
        text_edit.setFocus()
    
    def play_speech(self):
        """播放语音"""
        # 这里应该实现语音播放功能
        QMessageBox.information(self, "信息", "语音播放功能待实现")
    
    def pause_speech(self):
        """暂停语音"""
        QMessageBox.information(self, "信息", "语音暂停功能待实现")
    
    def stop_speech(self):
        """停止语音"""
        QMessageBox.information(self, "信息", "语音停止功能待实现")
    
    def show_statistics(self):
        """显示统计信息"""
        stats = self.ai_manager.get_metrics()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("AI工具统计")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        stats_text.setText(json.dumps(stats, indent=2, ensure_ascii=False))
        layout.addWidget(stats_text)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def show_settings(self):
        """显示设置"""
        QMessageBox.information(self, "设置", "AI设置功能待实现")
    
    def show_templates(self):
        """显示模板库"""
        QMessageBox.information(self, "模板库", "模板库功能待实现")
    
    def show_cost_management(self):
        """显示成本管理"""
        QMessageBox.information(self, "成本管理", "成本管理功能待实现")
    
    def _load_templates(self) -> Dict[str, Any]:
        """加载模板"""
        return {
            "commentary": {
                "幽默风趣": "搞笑解说模板",
                "专业解说": "专业解说模板",
                "情感共鸣": "情感解说模板"
            },
            "script": {
                "快节奏": "快节奏脚本模板",
                "慢节奏": "慢节奏脚本模板",
                "教育类": "教育类脚本模板"
            }
        }
    
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("ai_tools_panel", {})
        
        # 应用设置
        if "default_model" in settings:
            default_model = settings["default_model"]
            # 设置默认模型
            
        if "default_style" in settings:
            default_style = settings["default_style"]
            # 设置默认风格
    
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_model": self.commentary_model.currentText(),
            "default_style": self.commentary_style.currentText()
        }
        
        self.settings_manager.set_setting("ai_tools_panel", settings)
    
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        super().closeEvent(event)