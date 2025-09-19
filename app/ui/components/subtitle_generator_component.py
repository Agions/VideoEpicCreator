#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业AI字幕生成组件 - 支持语音识别、字幕生成、翻译、样式设计等功能
集成多模态AI模型，提供精准的字幕解决方案
"""

import asyncio
import json
import time
import re
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
    QApplication, QSizePolicy, QSpacerItem, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QTimeEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QTime
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QTextCharFormat

from app.ai.ai_service import AIService
from app.ai.interfaces import AITaskType, AIRequest, AIResponse, create_text_generation_request
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class SubtitleFormat(Enum):
    """字幕格式"""
    SRT = "srt"                      # SubRip格式
    VTT = "vtt"                      # WebVTT格式
    ASS = "ass"                      # Advanced SubStation Alpha
    SSA = "ssa"                      # SubStation Alpha
    TXT = "txt"                      # 纯文本格式


class SubtitleStyle(Enum):
    """字幕风格"""
    MODERN = "现代简约"               # 现代简约
    CLASSIC = "经典复古"              # 经典复古
    CARTOON = "卡通可爱"              # 卡通可爱
    ELEGANT = "优雅文艺"              # 优雅文艺
    TECHNOLOGICAL = "科技感"           # 科技感
    MINIMALIST = "极简主义"           # 极简主义
    CINEMATIC = "电影风格"            # 电影风格
    NEWS = "新闻风格"                 # 新闻风格


class Language(Enum):
    """语言类型"""
    CHINESE = "中文"                  # 中文
    ENGLISH = "英文"                  # 英文
    JAPANESE = "日文"                 # 日文
    KOREAN = "韩文"                   # 韩文
    FRENCH = "法文"                   # 法文
    GERMAN = "德文"                   # 德文
    SPANISH = "西班牙文"               # 西班牙文
    RUSSIAN = "俄文"                  # 俄文


class SubtitlePosition(Enum):
    """字幕位置"""
    BOTTOM = "底部"                   # 底部
    TOP = "顶部"                     # 顶部
    MIDDLE = "中间"                   # 中间
    CUSTOM = "自定义"                 # 自定义


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int
    start_time: float                 # 开始时间（秒）
    end_time: float                   # 结束时间（秒）
    text: str                         # 字幕文本
    translation: str = ""              # 翻译文本
    style: Dict[str, Any] = None      # 样式信息
    
    def to_srt(self) -> str:
        """转换为SRT格式"""
        start_str = self._format_time(self.start_time)
        end_str = self._format_time(self.end_time)
        return f"{self.index}\n{start_str} --> {end_str}\n{self.text}\n"
    
    def to_vtt(self) -> str:
        """转换为VTT格式"""
        start_str = self._format_time_vtt(self.start_time)
        end_str = self._format_time_vtt(self.end_time)
        return f"{self.index}\n{start_str} --> {end_str}\n{self.text}\n"
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间（SRT格式）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """格式化时间（VTT格式）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


@dataclass
class SubtitleGenerationRequest:
    """字幕生成请求"""
    request_id: str
    video_file: str
    source_language: Language
    target_language: Language = None
    subtitle_format: SubtitleFormat = SubtitleFormat.SRT
    style: SubtitleStyle = SubtitleStyle.MODERN
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    enable_translation: bool = False
    max_line_length: int = 40
    min_duration: float = 1.0
    max_duration: float = 7.0
    font_size: int = 16
    font_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: float = 0.7
    selected_model: str = "auto"
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.target_language is None:
            self.target_language = self.source_language


class AISubtitleGenerator(QWidget):
    """专业AI字幕生成器"""
    
    # 信号定义
    subtitle_generated = pyqtSignal(str, object)    # 字幕生成完成
    generation_progress = pyqtSignal(str, float)                  # 生成进度
    generation_error = pyqtSignal(str, str)                       # 生成错误
    translation_completed = pyqtSignal(str, object)  # 翻译完成
    style_applied = pyqtSignal(str, object)               # 样式应用完成
    export_completed = pyqtSignal(str, str)                       # 导出完成
    
    def __init__(self, ai_service: AIService, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.settings_manager = settings_manager
        self.cost_manager = ai_service.cost_manager
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # 字幕数据
        self.current_subtitles: List[SubtitleEntry] = []
        self.active_requests: Dict[str, SubtitleGenerationRequest] = {}
        self.request_counter = 0
        
        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 字幕生成标签页
        generate_tab = self._create_generate_tab()
        self.tab_widget.addTab(generate_tab, "🎬 字幕生成")
        
        # 字幕编辑标签页
        edit_tab = self._create_edit_tab()
        self.tab_widget.addTab(edit_tab, "✏️ 字幕编辑")
        
        # 字幕样式标签页
        style_tab = self._create_style_tab()
        self.tab_widget.addTab(style_tab, "🎨 字幕样式")
        
        # 翻译标签页
        translate_tab = self._create_translate_tab()
        self.tab_widget.addTab(translate_tab, "🌐 字幕翻译")
        
        main_layout.addWidget(self.tab_widget)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        # 预览按钮
        preview_btn = QPushButton("👁️ 预览")
        preview_btn.clicked.connect(self.preview_subtitles)
        button_layout.addWidget(preview_btn)
        
        button_layout.addStretch()
        
        # 导出按钮
        export_btn = QPushButton("📤 导出")
        export_btn.clicked.connect(self.export_subtitles)
        export_btn.setObjectName("export_btn")
        button_layout.addWidget(export_btn)
        
        main_layout.addLayout(button_layout)
        
        # 进度显示
        self.progress_widget = self._create_progress_widget()
        self.progress_widget.setVisible(False)
        main_layout.addWidget(self.progress_widget)
        
    def _create_generate_tab(self) -> QWidget:
        """创建字幕生成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 视频文件选择
        file_group = QGroupBox("视频文件")
        file_layout = QFormLayout(file_group)
        
        self.video_file_input = QLineEdit()
        self.video_file_input.setPlaceholderText("选择视频文件")
        file_layout.addRow("视频文件:", self.video_file_input)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(self.browse_video_file)
        file_layout.addRow("", browse_btn)
        
        layout.addWidget(file_group)
        
        # 识别设置
        recognition_group = QGroupBox("语音识别设置")
        recognition_layout = QFormLayout(recognition_group)
        
        # 源语言
        self.source_language_combo = QComboBox()
        for lang in Language:
            self.source_language_combo.addItem(lang.value)
        recognition_layout.addRow("源语言:", self.source_language_combo)
        
        # 识别模型
        self.recognition_model_combo = QComboBox()
        self._populate_recognition_models()
        recognition_layout.addRow("识别模型:", self.recognition_model_combo)
        
        # 高级选项
        advanced_options = QWidget()
        advanced_layout = QVBoxLayout(advanced_options)
        
        self.enable_speaker_diarization = QCheckBox("说话人分离")
        self.enable_speaker_diarization.setChecked(True)
        advanced_layout.addWidget(self.enable_speaker_diarization)
        
        self.enable_punctuation = QCheckBox("自动标点")
        self.enable_punctuation.setChecked(True)
        advanced_layout.addWidget(self.enable_punctuation)
        
        self.enable_number_conversion = QCheckBox("数字转换")
        self.enable_number_conversion.setChecked(True)
        advanced_layout.addWidget(self.enable_number_conversion)
        
        recognition_layout.addRow("高级选项:", advanced_options)
        
        layout.addWidget(recognition_group)
        
        # 生成设置
        generation_group = QGroupBox("生成设置")
        generation_layout = QFormLayout(generation_group)
        
        # 字幕格式
        self.subtitle_format_combo = QComboBox()
        for fmt in SubtitleFormat:
            self.subtitle_format_combo.addItem(fmt.value.upper())
        generation_layout.addRow("字幕格式:", self.subtitle_format_combo)
        
        # 字幕风格
        self.subtitle_style_combo = QComboBox()
        for style in SubtitleStyle:
            self.subtitle_style_combo.addItem(style.value)
        generation_layout.addRow("字幕风格:", self.subtitle_style_combo)
        
        # 字幕位置
        self.subtitle_position_combo = QComboBox()
        for pos in SubtitlePosition:
            self.subtitle_position_combo.addItem(pos.value)
        generation_layout.addRow("字幕位置:", self.subtitle_position_combo)
        
        # 时长设置
        duration_layout = QHBoxLayout()
        
        self.min_duration_spin = QDoubleSpinBox()
        self.min_duration_spin.setRange(0.5, 10.0)
        self.min_duration_spin.setValue(1.0)
        self.min_duration_spin.setSuffix(" 秒")
        self.min_duration_spin.setToolTip("最短显示时长")
        duration_layout.addWidget(self.min_duration_spin)
        
        duration_layout.addWidget(QLabel(" - "))
        
        self.max_duration_spin = QDoubleSpinBox()
        self.max_duration_spin.setRange(1.0, 15.0)
        self.max_duration_spin.setValue(7.0)
        self.max_duration_spin.setSuffix(" 秒")
        self.max_duration_spin.setToolTip("最长显示时长")
        duration_layout.addWidget(self.max_duration_spin)
        
        generation_layout.addRow("显示时长:", duration_layout)
        
        # 最大行长度
        self.max_line_length_spin = QSpinBox()
        self.max_line_length_spin.setRange(20, 80)
        self.max_line_length_spin.setValue(40)
        self.max_line_length_spin.setSuffix(" 字符")
        generation_layout.addRow("最大行长度:", self.max_line_length_spin)
        
        layout.addWidget(generation_group)
        
        # 生成按钮
        generate_btn = QPushButton("🎯 开始生成字幕")
        generate_btn.clicked.connect(self.generate_subtitles)
        generate_btn.setObjectName("generate_btn")
        generate_btn.setMinimumHeight(50)
        layout.addWidget(generate_btn)
        
        layout.addStretch()
        
        return widget
    
    def _create_edit_tab(self) -> QWidget:
        """创建字幕编辑标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 字幕编辑器
        editor_group = QGroupBox("字幕编辑器")
        editor_layout = QVBoxLayout(editor_group)
        
        # 字幕表格
        self.subtitle_table = QTableWidget()
        self.subtitle_table.setColumnCount(5)
        self.subtitle_table.setHorizontalHeaderLabels(["序号", "开始时间", "结束时间", "原文", "译文"])
        self.subtitle_table.horizontalHeader().setStretchLastSection(True)
        self.subtitle_table.itemChanged.connect(self.on_subtitle_item_changed)
        editor_layout.addWidget(self.subtitle_table)
        
        # 编辑工具栏
        tools_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ 添加")
        add_btn.clicked.connect(self.add_subtitle_entry)
        tools_layout.addWidget(add_btn)
        
        delete_btn = QPushButton("➖ 删除")
        delete_btn.clicked.connect(self.delete_subtitle_entry)
        tools_layout.addWidget(delete_btn)
        
        tools_layout.addStretch()
        
        merge_btn = QPushButton("🔗 合并")
        merge_btn.clicked.connect(self.merge_subtitles)
        tools_layout.addWidget(merge_btn)
        
        split_btn = QPushButton("✂️ 分割")
        split_btn.clicked.connect(self.split_subtitle)
        tools_layout.addWidget(split_btn)
        
        time_shift_btn = QPushButton("⏰ 时间轴调整")
        time_shift_btn.clicked.connect(self.adjust_time_shift)
        tools_layout.addWidget(time_shift_btn)
        
        editor_layout.addLayout(tools_layout)
        
        layout.addWidget(editor_group)
        
        # 快速编辑
        quick_edit_group = QGroupBox("快速编辑")
        quick_edit_layout = QFormLayout(quick_edit_group)
        
        # 批量替换
        self.replace_original = QLineEdit()
        self.replace_original.setPlaceholderText("原文本")
        quick_edit_layout.addRow("查找:", self.replace_original)
        
        self.replace_target = QLineEdit()
        self.replace_target.setPlaceholderText("替换为")
        quick_edit_layout.addRow("替换:", self.replace_target)
        
        replace_btn = QPushButton("🔄 批量替换")
        replace_btn.clicked.connect(self.batch_replace)
        quick_edit_layout.addRow("", replace_btn)
        
        # 时间调整
        time_adjust_layout = QHBoxLayout()
        
        self.time_adjust_value = QDoubleSpinBox()
        self.time_adjust_value.setRange(-10.0, 10.0)
        self.time_adjust_value.setValue(0.0)
        self.time_adjust_value.setSuffix(" 秒")
        time_adjust_layout.addWidget(self.time_adjust_value)
        
        adjust_btn = QPushButton("⏱️ 调整时间")
        adjust_btn.clicked.connect(self.adjust_all_times)
        time_adjust_layout.addWidget(adjust_btn)
        
        quick_edit_layout.addRow("时间调整:", time_adjust_layout)
        
        layout.addWidget(quick_edit_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_style_tab(self) -> QWidget:
        """创建字幕样式标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 样式预设
        preset_group = QGroupBox("样式预设")
        preset_layout = QHBoxLayout(preset_group)
        
        self.style_preset_combo = QComboBox()
        self.style_preset_combo.addItems(["自定义", "现代简约", "经典复古", "卡通可爱", "优雅文艺", "科技感"])
        self.style_preset_combo.currentTextChanged.connect(self.on_style_preset_changed)
        preset_layout.addWidget(self.style_preset_combo)
        
        apply_preset_btn = QPushButton("✅ 应用")
        apply_preset_btn.clicked.connect(self.apply_style_preset)
        preset_layout.addWidget(apply_preset_btn)
        
        preset_layout.addStretch()
        
        layout.addWidget(preset_group)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)
        
        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 48)
        self.font_size_spin.setValue(16)
        font_layout.addRow("字体大小:", self.font_size_spin)
        
        # 字体颜色
        color_layout = QHBoxLayout()
        self.font_color_btn = QPushButton()
        self.font_color_btn.clicked.connect(self.choose_font_color)
        self.font_color_btn.setMaximumWidth(50)
        color_layout.addWidget(self.font_color_btn)
        
        self.font_color_label = QLabel("#FFFFFF")
        color_layout.addWidget(self.font_color_label)
        color_layout.addStretch()
        
        font_layout.addRow("字体颜色:", color_layout)
        
        # 字体样式
        self.font_bold = QCheckBox("粗体")
        font_layout.addRow("", self.font_bold)
        
        self.font_italic = QCheckBox("斜体")
        font_layout.addRow("", self.font_italic)
        
        self.font_underline = QCheckBox("下划线")
        font_layout.addRow("", self.font_underline)
        
        layout.addWidget(font_group)
        
        # 背景设置
        bg_group = QGroupBox("背景设置")
        bg_layout = QFormLayout(bg_group)
        
        # 背景颜色
        bg_color_layout = QHBoxLayout()
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_btn.setMaximumWidth(50)
        bg_color_layout.addWidget(self.bg_color_btn)
        
        self.bg_color_label = QLabel("#000000")
        bg_color_layout.addWidget(self.bg_color_label)
        bg_color_layout.addStretch()
        
        bg_layout.addRow("背景颜色:", bg_color_layout)
        
        # 背景透明度
        self.bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_opacity_slider.setRange(0, 100)
        self.bg_opacity_slider.setValue(70)
        self.bg_opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        bg_layout.addRow("背景透明度:", self.bg_opacity_slider)
        
        # 边框设置
        self.border_enabled = QCheckBox("启用边框")
        self.border_enabled.setChecked(False)
        bg_layout.addRow("", self.border_enabled)
        
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(1, 10)
        self.border_width_spin.setValue(2)
        bg_layout.addRow("边框宽度:", self.border_width_spin)
        
        layout.addWidget(bg_group)
        
        # 位置设置
        position_group = QGroupBox("位置设置")
        position_layout = QFormLayout(position_group)
        
        # 位置
        self.position_combo = QComboBox()
        for pos in SubtitlePosition:
            self.position_combo.addItem(pos.value)
        position_layout.addRow("字幕位置:", self.position_combo)
        
        # 边距
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 100)
        self.margin_spin.setValue(20)
        self.margin_spin.setSuffix(" 像素")
        position_layout.addRow("边距:", self.margin_spin)
        
        layout.addWidget(position_group)
        
        # 预览区域
        preview_group = QGroupBox("样式预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.style_preview = QTextBrowser()
        self.style_preview.setMaximumHeight(150)
        self.style_preview.setHtml("""
        <div style='background-color: #000000; padding: 20px; text-align: center;'>
            <span style='color: #FFFFFF; font-size: 16px; font-family: Arial;'>这是字幕样式预览文本</span>
        </div>
        """)
        preview_layout.addWidget(self.style_preview)
        
        update_preview_btn = QPushButton("🔄 更新预览")
        update_preview_btn.clicked.connect(self.update_style_preview)
        preview_layout.addWidget(update_preview_btn)
        
        layout.addWidget(preview_group)
        
        # 应用样式按钮
        apply_style_btn = QPushButton("✨ 应用样式到所有字幕")
        apply_style_btn.clicked.connect(self.apply_style_to_all)
        apply_style_btn.setObjectName("apply_style_btn")
        layout.addWidget(apply_style_btn)
        
        layout.addStretch()
        
        return widget
    
    def _create_translate_tab(self) -> QWidget:
        """创建字幕翻译标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 翻译设置
        settings_group = QGroupBox("翻译设置")
        settings_layout = QFormLayout(settings_group)
        
        # 目标语言
        self.target_language_combo = QComboBox()
        for lang in Language:
            if lang != Language.CHINESE:  # 排除源语言
                self.target_language_combo.addItem(lang.value)
        settings_layout.addRow("目标语言:", self.target_language_combo)
        
        # 翻译模型
        self.translation_model_combo = QComboBox()
        self._populate_translation_models()
        settings_layout.addRow("翻译模型:", self.translation_model_combo)
        
        # 翻译风格
        self.translation_style_combo = QComboBox()
        self.translation_style_combo.addItems(["直译", "意译", "本地化", "创意翻译"])
        settings_layout.addRow("翻译风格:", self.translation_style_combo)
        
        layout.addWidget(settings_group)
        
        # 翻译选项
        options_group = QGroupBox("翻译选项")
        options_layout = QVBoxLayout(options_group)
        
        self.preserve_format = QCheckBox("保留格式")
        self.preserve_format.setChecked(True)
        options_layout.addWidget(self.preserve_format)
        
        self.translate_proper_nouns = QCheckBox("专有名词处理")
        self.translate_proper_nouns.setChecked(True)
        options_layout.addWidget(self.translate_proper_nouns)
        
        self.cultural_adaptation = QCheckBox("文化适应")
        self.cultural_adaptation.setChecked(True)
        options_layout.addWidget(self.cultural_adaptation)
        
        self.auto_detect_context = QCheckBox("自动检测上下文")
        self.auto_detect_context.setChecked(True)
        options_layout.addWidget(self.auto_detect_context)
        
        layout.addWidget(options_group)
        
        # 批量翻译
        batch_group = QGroupBox("批量翻译")
        batch_layout = QHBoxLayout(batch_group)
        
        self.translate_all_btn = QPushButton("🌐 翻译所有字幕")
        self.translate_all_btn.clicked.connect(self.translate_all_subtitles)
        batch_layout.addWidget(self.translate_all_btn)
        
        self.translate_selected_btn = QPushButton("📋 翻译选中字幕")
        self.translate_selected_btn.clicked.connect(self.translate_selected_subtitles)
        batch_layout.addWidget(self.translate_selected_btn)
        
        batch_layout.addStretch()
        
        layout.addWidget(batch_group)
        
        # 翻译历史
        history_group = QGroupBox("翻译历史")
        history_layout = QVBoxLayout(history_group)
        
        self.translation_history = QListWidget()
        self.translation_history.setMaximumHeight(200)
        history_layout.addWidget(self.translation_history)
        
        clear_history_btn = QPushButton("🗑️ 清空历史")
        clear_history_btn.clicked.connect(self.clear_translation_history)
        history_layout.addWidget(clear_history_btn)
        
        layout.addWidget(history_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_progress_widget(self) -> QWidget:
        """创建进度显示组件"""
        widget = QFrame()
        widget.setObjectName("progress_widget")
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 详细信息
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detail_label)
        
        return widget
    
    def _populate_recognition_models(self):
        """填充识别模型下拉框"""
        self.recognition_model_combo.clear()
        self.recognition_model_combo.addItem("🤖 自动选择", "auto")
        
        # 添加支持的识别模型
        recognition_models = [
            ("whisper", "Whisper"),
            ("qianwen", "通义千问"),
            ("xunfei", "讯飞星火")
        ]
        
        for model_id, model_name in recognition_models:
            self.recognition_model_combo.addItem(model_name, model_id)
    
    def _populate_translation_models(self):
        """填充翻译模型下拉框"""
        self.translation_model_combo.clear()
        self.translation_model_combo.addItem("🤖 自动选择", "auto")
        
        # 添加支持的翻译模型
        translation_models = [
            ("qianwen", "通义千问"),
            ("wenxin", "文心一言"),
            ("zhipu", "智谱AI"),
            ("deepseek", "DeepSeek")
        ]
        
        for model_id, model_name in translation_models:
            self.translation_model_combo.addItem(model_name, model_id)
    
    def _connect_signals(self):
        """连接信号"""
        # AI服务信号
        self.ai_service.worker_finished.connect(self.on_ai_response)
        
        # 样式相关信号
        self.font_size_spin.valueChanged.connect(self.update_style_preview)
        self.font_bold.toggled.connect(self.update_style_preview)
        self.font_italic.toggled.connect(self.update_style_preview)
        self.font_underline.toggled.connect(self.update_style_preview)
        self.bg_opacity_slider.valueChanged.connect(self.update_style_preview)
    
    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm)"
        )
        if file_path:
            self.video_file_input.setText(file_path)
    
    def generate_subtitles(self):
        """生成字幕"""
        if not self.video_file_input.text():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return
        
        # 创建生成请求
        request = self.create_generation_request()
        self.active_requests[request.request_id] = request
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在生成字幕...")
        
        # 开始生成
        asyncio.create_task(self.execute_subtitle_generation(request))
    
    def create_generation_request(self) -> SubtitleGenerationRequest:
        """创建生成请求"""
        return SubtitleGenerationRequest(
            request_id=f"subtitle_{self.request_counter}",
            video_file=self.video_file_input.text(),
            source_language=Language(self.source_language_combo.currentText()),
            target_language=Language(self.target_language_combo.currentText()),
            subtitle_format=SubtitleFormat(self.subtitle_format_combo.currentText().lower()),
            style=SubtitleStyle(self.subtitle_style_combo.currentText()),
            position=SubtitlePosition(self.subtitle_position_combo.currentText()),
            enable_translation=False,  # 默认不翻译
            max_line_length=self.max_line_length_spin.value(),
            min_duration=self.min_duration_spin.value(),
            max_duration=self.max_duration_spin.value(),
            font_size=self.font_size_spin.value(),
            font_color=self.font_color_label.text(),
            background_color=self.bg_color_label.text(),
            background_opacity=self.bg_opacity_slider.value() / 100.0,
            selected_model=self.recognition_model_combo.currentData()
        )
    
    async def execute_subtitle_generation(self, request: SubtitleGenerationRequest):
        """执行字幕生成"""
        try:
            self.generation_progress.emit(request.request_id, 0.0)
            
            # 模拟字幕生成过程
            # 在实际应用中，这里会调用语音识别API
            await asyncio.sleep(1)
            
            # 生成示例字幕数据
            sample_subtitles = self.generate_sample_subtitles(request)
            
            # 更新UI
            self.current_subtitles = sample_subtitles
            self.populate_subtitle_table(sample_subtitles)
            
            self.progress_bar.setValue(100)
            self.status_label.setText("字幕生成完成")
            
            # 发送信号
            self.subtitle_generated.emit(request.request_id, sample_subtitles)
            
        except Exception as e:
            self.generation_error.emit(request.request_id, str(e))
            self.status_label.setText(f"生成失败: {str(e)}")
            
        finally:
            # 清理请求
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            # 隐藏进度条（延迟）
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
    
    def generate_sample_subtitles(self, request: SubtitleGenerationRequest) -> List[SubtitleEntry]:
        """生成示例字幕数据"""
        # 这里应该是实际的语音识别结果
        # 现在使用模拟数据
        sample_texts = [
            "欢迎观看本期视频",
            "今天我们要讨论的是人工智能在视频制作中的应用",
            "AI技术正在改变我们的创作方式",
            "从字幕生成到内容创作",
            "AI为创作者提供了更多可能性",
            "让我们开始今天的分享"
        ]
        
        subtitles = []
        current_time = 0.0
        
        for i, text in enumerate(sample_texts):
            start_time = current_time
            duration = min(len(text) * 0.1, request.max_duration)
            duration = max(duration, request.min_duration)
            end_time = start_time + duration
            
            entry = SubtitleEntry(
                index=i + 1,
                start_time=start_time,
                end_time=end_time,
                text=text
            )
            
            subtitles.append(entry)
            current_time = end_time + 0.1
        
        return subtitles
    
    def populate_subtitle_table(self, subtitles: List[SubtitleEntry]):
        """填充字幕表格"""
        self.subtitle_table.setRowCount(len(subtitles))
        
        for i, subtitle in enumerate(subtitles):
            # 序号
            self.subtitle_table.setItem(i, 0, QTableWidgetItem(str(subtitle.index)))
            
            # 开始时间
            start_item = QTableWidgetItem(self._format_time_for_display(subtitle.start_time))
            start_item.setData(Qt.ItemDataRole.UserRole, subtitle.start_time)
            self.subtitle_table.setItem(i, 1, start_item)
            
            # 结束时间
            end_item = QTableWidgetItem(self._format_time_for_display(subtitle.end_time))
            end_item.setData(Qt.ItemDataRole.UserRole, subtitle.end_time)
            self.subtitle_table.setItem(i, 2, end_item)
            
            # 原文
            self.subtitle_table.setItem(i, 3, QTableWidgetItem(subtitle.text))
            
            # 译文
            self.subtitle_table.setItem(i, 4, QTableWidgetItem(subtitle.translation))
    
    def _format_time_for_display(self, seconds: float) -> str:
        """格式化时间用于显示"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 100)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}.{milliseconds:02d}"
    
    def on_subtitle_item_changed(self, item):
        """字幕条目变更"""
        row = item.row()
        col = item.column()
        
        if row < len(self.current_subtitles):
            subtitle = self.current_subtitles[row]
            
            if col == 1:  # 开始时间
                try:
                    subtitle.start_time = self._parse_time_from_display(item.text())
                except:
                    pass
            elif col == 2:  # 结束时间
                try:
                    subtitle.end_time = self._parse_time_from_display(item.text())
                except:
                    pass
            elif col == 3:  # 原文
                subtitle.text = item.text()
            elif col == 4:  # 译文
                subtitle.translation = item.text()
    
    def _parse_time_from_display(self, time_str: str) -> float:
        """从显示字符串解析时间"""
        # 简化的时间解析
        parts = time_str.split(':')
        if len(parts) == 2:  # MM:SS.ms
            minutes, secs_ms = parts
            secs, milliseconds = secs_ms.split('.')
            return int(minutes) * 60 + int(secs) + int(milliseconds) / 100.0
        elif len(parts) == 3:  # HH:MM:SS.ms
            hours, minutes, secs_ms = parts
            secs, milliseconds = secs_ms.split('.')
            return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(milliseconds) / 100.0
        
        return 0.0
    
    def add_subtitle_entry(self):
        """添加字幕条目"""
        new_index = len(self.current_subtitles) + 1
        new_subtitle = SubtitleEntry(
            index=new_index,
            start_time=0.0,
            end_time=3.0,
            text="新字幕"
        )
        
        self.current_subtitles.append(new_subtitle)
        self.populate_subtitle_table(self.current_subtitles)
    
    def delete_subtitle_entry(self):
        """删除字幕条目"""
        current_row = self.subtitle_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_subtitles):
            del self.current_subtitles[current_row]
            
            # 重新编号
            for i, subtitle in enumerate(self.current_subtitles):
                subtitle.index = i + 1
            
            self.populate_subtitle_table(self.current_subtitles)
    
    def merge_subtitles(self):
        """合并字幕"""
        selected_rows = set()
        for item in self.subtitle_table.selectedItems():
            selected_rows.add(item.row())
        
        if len(selected_rows) < 2:
            QMessageBox.warning(self, "警告", "请选择至少两个字幕条目进行合并")
            return
        
        # 按行号排序
        rows = sorted(selected_rows)
        
        # 合并文本
        merged_text = " ".join(self.current_subtitles[row].text for row in rows)
        
        # 使用第一个字幕的开始时间和最后一个字幕的结束时间
        start_time = self.current_subtitles[rows[0]].start_time
        end_time = self.current_subtitles[rows[-1]].end_time
        
        # 创建新字幕
        merged_subtitle = SubtitleEntry(
            index=self.current_subtitles[rows[0]].index,
            start_time=start_time,
            end_time=end_time,
            text=merged_text
        )
        
        # 删除原字幕并插入新字幕
        for row in reversed(rows):
            del self.current_subtitles[row]
        
        self.current_subtitles.insert(rows[0], merged_subtitle)
        
        # 重新编号
        for i, subtitle in enumerate(self.current_subtitles):
            subtitle.index = i + 1
        
        self.populate_subtitle_table(self.current_subtitles)
    
    def split_subtitle(self):
        """分割字幕"""
        current_row = self.subtitle_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_subtitles):
            QMessageBox.warning(self, "警告", "请选择要分割的字幕条目")
            return
        
        subtitle = self.current_subtitles[current_row]
        
        # 在中间位置分割
        mid_time = (subtitle.start_time + subtitle.end_time) / 2
        
        # 分割文本（简单的中间分割）
        text = subtitle.text
        mid_pos = len(text) // 2
        
        # 创建两个新字幕
        subtitle1 = SubtitleEntry(
            index=subtitle.index,
            start_time=subtitle.start_time,
            end_time=mid_time,
            text=text[:mid_pos].strip()
        )
        
        subtitle2 = SubtitleEntry(
            index=subtitle.index + 1,
            start_time=mid_time,
            end_time=subtitle.end_time,
            text=text[mid_pos:].strip()
        )
        
        # 替换原字幕
        self.current_subtitles[current_row] = subtitle1
        self.current_subtitles.insert(current_row + 1, subtitle2)
        
        # 重新编号
        for i, sub in enumerate(self.current_subtitles):
            sub.index = i + 1
        
        self.populate_subtitle_table(self.current_subtitles)
    
    def adjust_time_shift(self):
        """调整时间轴偏移"""
        # 打开时间轴调整对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("时间轴调整")
        dialog.setFixedSize(300, 150)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("时间偏移量（秒）："))
        
        time_input = QDoubleSpinBox()
        time_input.setRange(-3600, 3600)
        time_input.setValue(0.0)
        time_input.setSuffix(" 秒")
        layout.addWidget(time_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            offset = time_input.value()
            self.apply_time_shift(offset)
    
    def apply_time_shift(self, offset: float):
        """应用时间偏移"""
        for subtitle in self.current_subtitles:
            subtitle.start_time = max(0, subtitle.start_time + offset)
            subtitle.end_time = max(0, subtitle.end_time + offset)
        
        self.populate_subtitle_table(self.current_subtitles)
        QMessageBox.information(self, "成功", f"时间轴已调整 {offset} 秒")
    
    def batch_replace(self):
        """批量替换"""
        original = self.replace_original.text()
        target = self.replace_target.text()
        
        if not original:
            QMessageBox.warning(self, "警告", "请输入要替换的文本")
            return
        
        replaced_count = 0
        for subtitle in self.current_subtitles:
            if original in subtitle.text:
                subtitle.text = subtitle.text.replace(original, target)
                replaced_count += 1
        
        self.populate_subtitle_table(self.current_subtitles)
        QMessageBox.information(self, "成功", f"已替换 {replaced_count} 处文本")
    
    def adjust_all_times(self):
        """调整所有时间"""
        offset = self.time_adjust_value.value()
        self.apply_time_shift(offset)
    
    def on_style_preset_changed(self, preset_name):
        """样式预设变更"""
        if preset_name != "自定义":
            # 应用预设样式
            preset_styles = {
                "现代简约": {
                    "font_size": 16,
                    "font_color": "#FFFFFF",
                    "bg_color": "#000000",
                    "bg_opacity": 70
                },
                "经典复古": {
                    "font_size": 18,
                    "font_color": "#FFFF00",
                    "bg_color": "#000000",
                    "bg_opacity": 80
                },
                "卡通可爱": {
                    "font_size": 20,
                    "font_color": "#FF69B4",
                    "bg_color": "#FFC0CB",
                    "bg_opacity": 60
                },
                "优雅文艺": {
                    "font_size": 16,
                    "font_color": "#F0F8FF",
                    "bg_color": "#2F4F4F",
                    "bg_opacity": 75
                },
                "科技感": {
                    "font_size": 14,
                    "font_color": "#00FFFF",
                    "bg_color": "#000033",
                    "bg_opacity": 85
                }
            }
            
            if preset_name in preset_styles:
                style = preset_styles[preset_name]
                self.font_size_spin.setValue(style["font_size"])
                self.font_color_label.setText(style["font_color"])
                self.bg_color_label.setText(style["bg_color"])
                self.bg_opacity_slider.setValue(style["bg_opacity"])
                
                self.update_color_buttons()
                self.update_style_preview()
    
    def apply_style_preset(self):
        """应用样式预设"""
        self.on_style_preset_changed(self.style_preset_combo.currentText())
    
    def choose_font_color(self):
        """选择字体颜色"""
        color = QColorDialog.getColor(QColor(self.font_color_label.text()), self)
        if color.isValid():
            self.font_color_label.setText(color.name())
            self.update_color_buttons()
            self.update_style_preview()
    
    def choose_bg_color(self):
        """选择背景颜色"""
        color = QColorDialog.getColor(QColor(self.bg_color_label.text()), self)
        if color.isValid():
            self.bg_color_label.setText(color.name())
            self.update_color_buttons()
            self.update_style_preview()
    
    def update_color_buttons(self):
        """更新颜色按钮"""
        font_color = QColor(self.font_color_label.text())
        bg_color = QColor(self.bg_color_label.text())
        
        self.font_color_btn.setStyleSheet(f"background-color: {font_color.name()}")
        self.bg_color_btn.setStyleSheet(f"background-color: {bg_color.name()}")
    
    def update_style_preview(self):
        """更新样式预览"""
        font_size = self.font_size_spin.value()
        font_color = self.font_color_label.text()
        bg_color = self.bg_color_label.text()
        bg_opacity = self.bg_opacity_slider.value() / 100.0
        
        # 构建HTML样式
        font_styles = []
        if self.font_bold.isChecked():
            font_styles.append("font-weight: bold")
        if self.font_italic.isChecked():
            font_styles.append("font-style: italic")
        if self.font_underline.isChecked():
            font_styles.append("text-decoration: underline")
        
        font_style_str = "; ".join(font_styles) if font_styles else ""
        
        # 将透明度转换为RGBA
        bg_rgba = QColor(bg_color)
        bg_rgba.setAlpha(int(bg_opacity * 255))
        
        preview_html = f"""
        <div style='background-color: rgba({bg_rgba.red()}, {bg_rgba.green()}, {bg_rgba.blue()}, {bg_opacity}); 
                    padding: 20px; text-align: center; border-radius: 5px;'>
            <span style='color: {font_color}; font-size: {font_size}px; font-family: Arial; {font_style_str}'>
                这是字幕样式预览文本
            </span>
        </div>
        """
        
        self.style_preview.setHtml(preview_html)
    
    def apply_style_to_all(self):
        """应用样式到所有字幕"""
        style_info = {
            "font_size": self.font_size_spin.value(),
            "font_color": self.font_color_label.text(),
            "bg_color": self.bg_color_label.text(),
            "bg_opacity": self.bg_opacity_slider.value() / 100.0,
            "bold": self.font_bold.isChecked(),
            "italic": self.font_italic.isChecked(),
            "underline": self.font_underline.isChecked(),
            "position": self.position_combo.currentText()
        }
        
        for subtitle in self.current_subtitles:
            subtitle.style = style_info.copy()
        
        self.style_applied.emit("all", style_info)
        QMessageBox.information(self, "成功", "样式已应用到所有字幕")
    
    def translate_all_subtitles(self):
        """翻译所有字幕"""
        if not self.current_subtitles:
            QMessageBox.warning(self, "警告", "没有可翻译的字幕")
            return
        
        target_language = Language(self.target_language_combo.currentText())
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在翻译字幕...")
        
        # 开始翻译
        asyncio.create_task(self.execute_translation(self.current_subtitles, target_language))
    
    def translate_selected_subtitles(self):
        """翻译选中的字幕"""
        selected_rows = set()
        for item in self.subtitle_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要翻译的字幕")
            return
        
        selected_subtitles = [self.current_subtitles[row] for row in sorted(selected_rows)]
        target_language = Language(self.target_language_combo.currentText())
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在翻译选中字幕...")
        
        # 开始翻译
        asyncio.create_task(self.execute_translation(selected_subtitles, target_language))
    
    async def execute_translation(self, subtitles: List[SubtitleEntry], target_language: Language):
        """执行翻译"""
        try:
            total_count = len(subtitles)
            
            for i, subtitle in enumerate(subtitles):
                # 构建翻译提示词
                prompt = self.build_translation_prompt(subtitle.text, target_language)
                
                # 调用AI服务进行翻译
                ai_request = create_text_generation_request(
                    prompt=prompt,
                    provider=self.translation_model_combo.currentData(),
                    max_tokens=500
                )

                # 提交请求并等待结果
                response = await self.ai_service.process_request(ai_request)
                
                if response.success:
                    subtitle.translation = response.content.strip()
                    
                    # 更新表格
                    row = self.current_subtitles.index(subtitle)
                    if row >= 0:
                        translation_item = self.subtitle_table.item(row, 4)
                        if translation_item:
                            translation_item.setText(subtitle.translation)
                
                # 更新进度
                progress = (i + 1) / total_count * 100
                self.generation_progress.emit("translation", progress)
                self.progress_bar.setValue(int(progress))
                self.detail_label.setText(f"翻译进度: {i + 1}/{total_count}")
                
                # 添加小延迟避免API限制
                await asyncio.sleep(0.1)
            
            self.status_label.setText("翻译完成")
            self.translation_completed.emit("batch", subtitles)
            
            # 添加到翻译历史
            self.add_to_translation_history(target_language, len(subtitles))
            
        except Exception as e:
            self.generation_error.emit("translation", str(e))
            self.status_label.setText(f"翻译失败: {str(e)}")
            
        finally:
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
    
    def build_translation_prompt(self, text: str, target_language: Language) -> str:
        """构建翻译提示词"""
        style = self.translation_style_combo.currentText()
        
        prompt = f"""
请将以下文本翻译为{target_language.value}：

原文：{text}

翻译要求：
1. 翻译风格：{style}
2. 保持原意不变
3. 语言自然流畅
4. 适合字幕显示
"""
        
        if self.preserve_format.isChecked():
            prompt += "5. 保持原文格式和标点符号\n"
        
        if self.translate_proper_nouns.isChecked():
            prompt += "6. 正确处理专有名词\n"
        
        if self.cultural_adaptation.isChecked():
            prompt += "7. 进行适当的文化适应\n"
        
        if self.auto_detect_context.isChecked():
            prompt += "8. 根据上下文调整翻译\n"
        
        prompt += "\n请只返回翻译结果，不要添加其他说明："
        
        return prompt
    
    def add_to_translation_history(self, target_language: Language, count: int):
        """添加到翻译历史"""
        history_item = QListWidgetItem(
            f"{time.strftime('%H:%M:%S')} - 翻译了 {count} 条字幕到 {target_language.value}"
        )
        self.translation_history.addItem(history_item)
    
    def clear_translation_history(self):
        """清空翻译历史"""
        self.translation_history.clear()
    
    def preview_subtitles(self):
        """预览字幕"""
        if not self.current_subtitles:
            QMessageBox.warning(self, "警告", "没有可预览的字幕")
            return
        
        # 创建预览对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("字幕预览")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 预览区域
        preview = QTextBrowser()
        preview.setReadOnly(True)
        
        # 生成预览HTML
        preview_html = self.generate_preview_html()
        preview.setHtml(preview_html)
        
        layout.addWidget(preview)
        
        # 控制按钮
        controls = QHBoxLayout()
        
        play_btn = QPushButton("▶️ 播放")
        play_btn.clicked.connect(lambda: self.play_preview(preview))
        controls.addWidget(play_btn)
        
        controls.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        controls.addWidget(close_btn)
        
        layout.addLayout(controls)
        
        dialog.exec()
    
    def generate_preview_html(self) -> str:
        """生成预览HTML"""
        html_parts = ["<html><body style='background-color: #000; color: #fff; font-family: Arial;'>"]
        
        for subtitle in self.current_subtitles[:10]:  # 只显示前10条
            start_time_str = self._format_time_for_display(subtitle.start_time)
            html_parts.append(f"""
            <div style='margin: 20px; padding: 10px; background-color: rgba(0,0,0,0.7); border-radius: 5px;'>
                <div style='font-size: 12px; color: #888;'>{start_time_str}</div>
                <div style='font-size: 16px; margin-top: 5px;'>{subtitle.text}</div>
            </div>
            """)
        
        html_parts.append("</body></html>")
        
        return "".join(html_parts)
    
    def play_preview(self, preview_widget):
        """播放预览（模拟）"""
        QMessageBox.information(self, "预览", "预览播放功能需要配合视频播放器使用")
    
    def export_subtitles(self):
        """导出字幕"""
        if not self.current_subtitles:
            QMessageBox.warning(self, "警告", "没有可导出的字幕")
            return
        
        # 选择导出格式
        format_dialog = QDialog(self)
        format_dialog.setWindowTitle("选择导出格式")
        format_dialog.setFixedSize(300, 200)
        
        layout = QVBoxLayout(format_dialog)
        
        layout.addWidget(QLabel("选择导出格式："))
        
        format_combo = QComboBox()
        format_combo.addItems(["SRT", "VTT", "ASS", "TXT"])
        layout.addWidget(format_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(format_dialog.accept)
        buttons.rejected.connect(format_dialog.reject)
        layout.addWidget(buttons)
        
        if format_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        export_format = format_combo.currentText().lower()
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存字幕文件", "", 
            f"{export_format.upper()}文件 (*.{export_format});;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            # 生成字幕内容
            if export_format == "srt":
                content = self.generate_srt_content()
            elif export_format == "vtt":
                content = self.generate_vtt_content()
            elif export_format == "ass":
                content = self.generate_ass_content()
            else:  # txt
                content = self.generate_txt_content()
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.export_completed.emit(file_path, export_format)
            QMessageBox.information(self, "成功", f"字幕文件已保存到：{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")
    
    def generate_srt_content(self) -> str:
        """生成SRT格式内容"""
        return "\n".join(subtitle.to_srt() for subtitle in self.current_subtitles)
    
    def generate_vtt_content(self) -> str:
        """生成VTT格式内容"""
        header = "WEBVTT\n\n"
        content = header + "\n".join(subtitle.to_vtt() for subtitle in self.current_subtitles)
        return content
    
    def generate_ass_content(self) -> str:
        """生成ASS格式内容"""
        header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        events = []
        for subtitle in self.current_subtitles:
            start_time = self._format_time_ass(subtitle.start_time)
            end_time = self._format_time_ass(subtitle.end_time)
            events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{subtitle.text}")
        
        return header + "\n".join(events)
    
    def generate_txt_content(self) -> str:
        """生成TXT格式内容"""
        return "\n".join(subtitle.text for subtitle in self.current_subtitles)
    
    def _format_time_ass(self, seconds: float) -> str:
        """格式化时间（ASS格式）H:MM:SS.CC"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    def on_ai_response(self, model_provider, response):
        """AI响应处理"""
        # 处理AI模型的响应
        if response.success:
            print(f"AI响应成功: {model_provider}")
        else:
            print(f"AI响应失败: {model_provider} - {response.error_message}")
    
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("subtitle_generator", {})
        
        # 应用设置
        if "default_style" in settings:
            index = self.subtitle_style_combo.findText(settings["default_style"])
            if index >= 0:
                self.subtitle_style_combo.setCurrentIndex(index)
        
        if "font_size" in settings:
            self.font_size_spin.setValue(settings["font_size"])
        
        if "font_color" in settings:
            self.font_color_label.setText(settings["font_color"])
        
        if "bg_color" in settings:
            self.bg_color_label.setText(settings["bg_color"])
        
        self.update_color_buttons()
        self.update_style_preview()
    
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_style": self.subtitle_style_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "font_color": self.font_color_label.text(),
            "bg_color": self.bg_color_label.text()
        }
        
        self.settings_manager.set_setting("subtitle_generator", settings)
    
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        super().closeEvent(event)