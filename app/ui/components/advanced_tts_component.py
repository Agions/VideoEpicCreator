#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业TTS语音合成组件 - 支持多种语音合成服务和高级功能
集成本地和云端TTS引擎，提供自然的语音合成体验
"""

import asyncio
import json
import time
import os
import tempfile
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
    QTableWidget, QTableWidgetItem, QHeaderView, QTimeEdit,
    QSystemTrayIcon, QStatusBar, QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QTime, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QTextCharFormat, QDesktopServices, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from app.ai.generators.text_to_speech import TextToSpeechEngine, get_tts_engine
from app.ai.ai_manager import AIManager
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class TTSEngine(Enum):
    """TTS引擎类型"""
    LOCAL = "local"                    # 本地引擎
    CLOUD = "cloud"                    # 云端引擎
    HYBRID = "hybrid"                  # 混合引擎


class VoiceType(Enum):
    """语音类型"""
    FEMALE = "female"                  # 女声
    MALE = "male"                      # 男声
    CHILD = "child"                    # 童声
    ELDERLY = "elderly"                # 老年声


class EmotionType(Enum):
    """情感类型"""
    NEUTRAL = "neutral"                # 中性
    HAPPY = "happy"                    # 开心
    SAD = "sad"                        # 悲伤
    ANGRY = "angry"                    # 愤怒
    EXCITED = "excited"                # 兴奋
    CALM = "calm"                      # 平静
    FEARFUL = "fearful"                # 恐惧
    SURPRISED = "surprised"            # 惊讶


class AudioFormat(Enum):
    """音频格式"""
    WAV = "wav"                        # WAV格式
    MP3 = "mp3"                        # MP3格式
    OGG = "ogg"                        # OGG格式
    M4A = "m4a"                        # M4A格式


@dataclass
class TTSRequest:
    """TTS请求"""
    request_id: str
    text: str
    voice_type: VoiceType
    emotion: EmotionType
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    engine: TTSEngine = TTSEngine.LOCAL
    output_format: AudioFormat = AudioFormat.WAV
    output_path: str = ""
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class TTSResponse:
    """TTS响应"""
    request_id: str
    success: bool
    output_path: str = ""
    duration: float = 0.0
    file_size: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TTSVoiceProfile:
    """TTS语音配置"""
    
    def __init__(self, name: str, voice_type: VoiceType, 
                 engine: TTSEngine, description: str = ""):
        self.name = name
        self.voice_type = voice_type
        self.engine = engine
        self.description = description
        
        # 默认参数
        self.default_speed = 1.0
        self.default_pitch = 1.0
        self.default_volume = 1.0
        self.default_emotion = EmotionType.NEUTRAL
        
        # 支持的情感
        self.supported_emotions = [EmotionType.NEUTRAL]
        
        # 音频参数
        self.sample_rate = 22050
        self.channels = 1
        self.bit_depth = 16


class AdvancedTTSComponent(QWidget):
    """高级TTS语音合成组件"""
    
    # 信号定义
    synthesis_started = pyqtSignal(str)              # 合成开始
    synthesis_progress = pyqtSignal(str, float)      # 合成进度
    synthesis_completed = pyqtSignal(str, TTSResponse)  # 合成完成
    synthesis_error = pyqtSignal(str, str)           # 合成错误
    playback_started = pyqtSignal(str)               # 播放开始
    playback_stopped = pyqtSignal(str)               # 播放停止
    voice_profile_changed = pyqtSignal(TTSVoiceProfile)  # 语音配置变更
    
    def __init__(self, ai_manager: AIManager, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        
        self.ai_manager = ai_manager
        self.settings_manager = settings_manager
        self.tts_engine = get_tts_engine()
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # 语音配置
        self.voice_profiles = self._create_voice_profiles()
        self.current_profile = self.voice_profiles[0]
        
        # 请求管理
        self.active_requests: Dict[str, TTSRequest] = {}
        self.request_counter = 0
        
        # 媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 当前音频文件
        self.current_audio_file = ""
        
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
        
        # 快速合成标签页
        quick_tab = self._create_quick_tab()
        self.tab_widget.addTab(quick_tab, "⚡ 快速合成")
        
        # 高级设置标签页
        advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(advanced_tab, "⚙️ 高级设置")
        
        # 语音库标签页
        voice_library_tab = self._create_voice_library_tab()
        self.tab_widget.addTab(voice_library_tab, "🎤 语音库")
        
        # 批量合成标签页
        batch_tab = self._create_batch_tab()
        self.tab_widget.addTab(batch_tab, "📚 批量合成")
        
        main_layout.addWidget(self.tab_widget)
        
        # 播放控制区域
        playback_widget = self._create_playback_controls()
        main_layout.addWidget(playback_widget)
        
        # 进度显示
        self.progress_widget = self._create_progress_widget()
        self.progress_widget.setVisible(False)
        main_layout.addWidget(self.progress_widget)
        
    def _create_quick_tab(self) -> QWidget:
        """创建快速合成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 文本输入区域
        text_group = QGroupBox("文本输入")
        text_layout = QVBoxLayout(text_group)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入要合成的文本...")
        self.text_input.setMinimumHeight(150)
        text_layout.addWidget(self.text_input)
        
        # 文本统计
        stats_layout = QHBoxLayout()
        
        self.char_count_label = QLabel("字符数: 0")
        stats_layout.addWidget(self.char_count_label)
        
        self.word_count_label = QLabel("词数: 0")
        stats_layout.addWidget(self.word_count_label)
        
        self.estimated_time_label = QLabel("预计时长: 0秒")
        stats_layout.addWidget(self.estimated_time_label)
        
        stats_layout.addStretch()
        text_layout.addLayout(stats_layout)
        
        layout.addWidget(text_group)
        
        # 快速设置
        settings_group = QGroupBox("快速设置")
        settings_layout = QFormLayout(settings_group)
        
        # 语音配置
        voice_layout = QHBoxLayout()
        
        self.voice_profile_combo = QComboBox()
        self._populate_voice_profiles()
        voice_layout.addWidget(self.voice_profile_combo)
        
        preview_voice_btn = QPushButton("👂 试听")
        preview_voice_btn.clicked.connect(self._preview_voice)
        voice_layout.addWidget(preview_voice_btn)
        
        settings_layout.addRow("语音配置:", voice_layout)
        
        # 情感设置
        self.emotion_combo = QComboBox()
        self._populate_emotions()
        settings_layout.addRow("情感设置:", self.emotion_combo)
        
        # 语速设置
        speed_layout = QHBoxLayout()
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        
        settings_layout.addRow("语速:", speed_layout)
        
        # 音量设置
        volume_layout = QHBoxLayout()
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        self.volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("90%")
        volume_layout.addWidget(self.volume_label)
        
        settings_layout.addRow("音量:", volume_layout)
        
        layout.addWidget(settings_group)
        
        # 合成按钮
        button_layout = QHBoxLayout()
        
        self.synthesize_btn = QPushButton("🔊 开始合成")
        self.synthesize_btn.setObjectName("primary_button")
        self.synthesize_btn.setMinimumHeight(50)
        self.synthesize_btn.clicked.connect(self._start_synthesis)
        button_layout.addWidget(self.synthesize_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        return widget
        
    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 引擎设置
        engine_group = QGroupBox("引擎设置")
        engine_layout = QFormLayout(engine_group)
        
        # TTS引擎
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["本地引擎", "云端引擎", "混合引擎"])
        engine_layout.addRow("TTS引擎:", self.tts_engine_combo)
        
        # 音频格式
        self.audio_format_combo = QComboBox()
        for fmt in AudioFormat:
            self.audio_format_combo.addItem(fmt.value.upper())
        engine_layout.addRow("音频格式:", self.audio_format_combo)
        
        # 采样率
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["22050Hz", "44100Hz", "48000Hz"])
        engine_layout.addRow("采样率:", self.sample_rate_combo)
        
        layout.addWidget(engine_group)
        
        # 高级参数
        params_group = QGroupBox("高级参数")
        params_layout = QFormLayout(params_group)
        
        # 音调设置
        pitch_layout = QHBoxLayout()
        
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(50, 200)
        self.pitch_slider.setValue(100)
        self.pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        pitch_layout.addWidget(self.pitch_slider)
        
        self.pitch_label = QLabel("1.0x")
        pitch_layout.addWidget(self.pitch_label)
        
        params_layout.addRow("音调:", pitch_layout)
        
        # 停顿设置
        self.pause_duration_spin = QSpinBox()
        self.pause_duration_spin.setRange(100, 2000)
        self.pause_duration_spin.setValue(500)
        self.pause_duration_spin.setSuffix(" ms")
        params_layout.addRow("句间停顿:", self.pause_duration_spin)
        
        # 重音设置
        self.emphasis_check = QCheckBox("启用重音处理")
        self.emphasis_check.setChecked(True)
        params_layout.addRow("", self.emphasis_check)
        
        # 标点符号处理
        self.punctuation_check = QCheckBox("智能标点处理")
        self.punctuation_check.setChecked(True)
        params_layout.addRow("", self.punctuation_check)
        
        # 数字处理
        self.number_check = QCheckBox("智能数字处理")
        self.number_check.setChecked(True)
        params_layout.addRow("", self.number_check)
        
        layout.addWidget(params_group)
        
        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout(output_group)
        
        # 输出路径
        path_layout = QHBoxLayout()
        
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("选择输出路径（可选）")
        path_layout.addWidget(self.output_path_input)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.clicked.connect(self._browse_output_path)
        path_layout.addWidget(browse_btn)
        
        output_layout.addLayout(path_layout)
        
        # 自动命名
        self.auto_naming_check = QCheckBox("自动命名文件")
        self.auto_naming_check.setChecked(True)
        output_layout.addWidget(self.auto_naming_check)
        
        # 生成后播放
        self.play_after_synthesis_check = QCheckBox("合成后自动播放")
        self.play_after_synthesis_check.setChecked(False)
        output_layout.addWidget(self.play_after_synthesis_check)
        
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        return widget
        
    def _create_voice_library_tab(self) -> QWidget:
        """创建语音库标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 语音分类
        category_group = QGroupBox("语音分类")
        category_layout = QHBoxLayout(category_group)
        
        self.voice_category_combo = QComboBox()
        self.voice_category_combo.addItems(["全部", "女声", "男声", "童声", "特色语音"])
        self.voice_category_combo.currentTextChanged.connect(self._filter_voices)
        category_layout.addWidget(self.voice_category_combo)
        
        category_layout.addStretch()
        
        # 搜索框
        self.voice_search_input = QLineEdit()
        self.voice_search_input.setPlaceholderText("搜索语音...")
        self.voice_search_input.textChanged.connect(self._filter_voices)
        category_layout.addWidget(self.voice_search_input)
        
        layout.addWidget(category_group)
        
        # 语音列表
        voices_group = QGroupBox("可用语音")
        voices_layout = QVBoxLayout(voices_group)
        
        self.voice_table = QTableWidget()
        self.voice_table.setColumnCount(5)
        self.voice_table.setHorizontalHeaderLabels(["语音名称", "类型", "引擎", "情感支持", "操作"])
        self.voice_table.horizontalHeader().setStretchLastSection(True)
        self.voice_table.itemSelectionChanged.connect(self._on_voice_selected)
        voices_layout.addWidget(self.voice_table)
        
        layout.addWidget(voices_group)
        
        # 语音详情
        details_group = QGroupBox("语音详情")
        details_layout = QVBoxLayout(details_group)
        
        self.voice_details = QTextBrowser()
        self.voice_details.setMaximumHeight(150)
        self.voice_details.setPlaceholderText("选择语音查看详情")
        details_layout.addWidget(self.voice_details)
        
        layout.addWidget(details_group)
        
        # 初始化语音列表
        self._populate_voice_table()
        
        return widget
        
    def _create_batch_tab(self) -> QWidget:
        """创建批量合成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 批量输入
        input_group = QGroupBox("批量输入")
        input_layout = QVBoxLayout(input_group)
        
        # 输入方式
        input_method_group = QGroupBox("输入方式")
        input_method_layout = QHBoxLayout(input_method_group)
        
        self.batch_text_radio = QRadioButton("文本输入")
        self.batch_text_radio.setChecked(True)
        input_method_layout.addWidget(self.batch_text_radio)
        
        self.batch_file_radio = QRadioButton("文件导入")
        input_method_layout.addWidget(self.batch_file_radio)
        
        input_layout.addWidget(input_method_group)
        
        # 文本输入区域
        self.batch_text_input = QTextEdit()
        self.batch_text_input.setPlaceholderText("每行一个文本段落，或使用分隔符分隔多个文本...")
        self.batch_text_input.setMaximumHeight(200)
        input_layout.addWidget(self.batch_text_input)
        
        # 文件导入
        file_layout = QHBoxLayout()
        
        self.batch_file_input = QLineEdit()
        self.batch_file_input.setPlaceholderText("选择文本文件...")
        file_layout.addWidget(self.batch_file_input)
        
        import_btn = QPushButton("📁 导入")
        import_btn.clicked.connect(self._import_batch_file)
        file_layout.addWidget(import_btn)
        
        input_layout.addLayout(file_layout)
        
        layout.addWidget(input_group)
        
        # 批量设置
        batch_settings_group = QGroupBox("批量设置")
        batch_settings_layout = QFormLayout(batch_settings_group)
        
        # 分隔符
        self.delimiter_input = QLineEdit()
        self.delimiter_input.setText("\\n")
        batch_settings_layout.addRow("文本分隔符:", self.delimiter_input)
        
        # 输出目录
        output_dir_layout = QHBoxLayout()
        
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("选择输出目录...")
        output_dir_layout.addWidget(self.output_dir_input)
        
        browse_dir_btn = QPushButton("📁 浏览")
        browse_dir_btn.clicked.connect(self._browse_output_dir)
        output_dir_layout.addWidget(browse_dir_btn)
        
        batch_settings_layout.addRow("输出目录:", output_dir_layout)
        
        # 文件命名模式
        self.naming_pattern_input = QLineEdit()
        self.naming_pattern_input.setText("tts_{index}")
        batch_settings_layout.addRow("命名模式:", self.naming_pattern_input)
        
        # 并发数
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(3)
        batch_settings_layout.addRow("并发数:", self.concurrent_spin)
        
        layout.addWidget(batch_settings_group)
        
        # 批量控制
        control_layout = QHBoxLayout()
        
        self.preview_batch_btn = QPushButton("👁️ 预览")
        self.preview_batch_btn.clicked.connect(self._preview_batch)
        control_layout.addWidget(self.preview_batch_btn)
        
        self.start_batch_btn = QPushButton("🚀 开始批量合成")
        self.start_batch_btn.setObjectName("primary_button")
        self.start_batch_btn.clicked.connect(self._start_batch_synthesis)
        control_layout.addWidget(self.start_batch_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 批量进度
        self.batch_progress_group = QGroupBox("批量合成进度")
        batch_progress_layout = QVBoxLayout(self.batch_progress_group)
        
        self.batch_progress_bar = QProgressBar()
        batch_progress_layout.addWidget(self.batch_progress_bar)
        
        self.batch_status_label = QLabel("准备就绪")
        batch_progress_layout.addWidget(self.batch_status_label)
        
        self.batch_progress_group.setVisible(False)
        layout.addWidget(self.batch_progress_group)
        
        layout.addStretch()
        
        return widget
        
    def _create_playback_controls(self) -> QWidget:
        """创建播放控制"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(widget)
        
        # 播放控制按钮
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_audio)
        layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_audio)
        layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_audio)
        layout.addWidget(self.stop_btn)
        
        layout.addSpacing(20)
        
        # 进度条
        self.playback_progress = QProgressBar()
        self.playback_progress.setTextVisible(False)
        layout.addWidget(self.playback_progress, 1)
        
        layout.addSpacing(20)
        
        # 时间显示
        self.current_time_label = QLabel("00:00")
        layout.addWidget(self.current_time_label)
        
        layout.addWidget(QLabel("/"))
        
        self.total_time_label = QLabel("00:00")
        layout.addWidget(self.total_time_label)
        
        layout.addSpacing(20)
        
        # 音量控制
        self.playback_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_volume_slider.setRange(0, 100)
        self.playback_volume_slider.setValue(70)
        self.playback_volume_slider.setMaximumWidth(100)
        layout.addWidget(self.playback_volume_slider)
        
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
        
        # 取消按钮
        cancel_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.clicked.connect(self._cancel_synthesis)
        cancel_layout.addWidget(self.cancel_btn)
        
        cancel_layout.addStretch()
        layout.addLayout(cancel_layout)
        
        return widget
        
    def _create_voice_profiles(self) -> List[TTSVoiceProfile]:
        """创建语音配置"""
        profiles = []
        
        # 本地女声
        profiles.append(TTSVoiceProfile(
            "温柔女声", VoiceType.FEMALE, TTSEngine.LOCAL,
            "自然温柔的女声，适合解说和故事"
        ))
        
        # 本地男声
        profiles.append(TTSVoiceProfile(
            "沉稳男声", VoiceType.MALE, TTSEngine.LOCAL,
            "沉稳有力的男声，适合专业内容"
        ))
        
        # 童声
        profiles.append(TTSVoiceProfile(
            "可爱童声", VoiceType.CHILD, TTSEngine.LOCAL,
            "活泼可爱的童声，适合儿童内容"
        ))
        
        # 云端女声（模拟）
        profiles.append(TTSVoiceProfile(
            "云端女声", VoiceType.FEMALE, TTSEngine.CLOUD,
            "高质量云端女声，支持多种情感"
        ))
        
        # 为每个语音设置支持的情感
        for profile in profiles:
            if profile.engine == TTSEngine.LOCAL:
                profile.supported_emotions = [EmotionType.NEUTRAL, EmotionType.HAPPY, EmotionType.SAD]
            else:
                profile.supported_emotions = [e for e in EmotionType]
        
        return profiles
        
    def _populate_voice_profiles(self):
        """填充语音配置下拉框"""
        self.voice_profile_combo.clear()
        for profile in self.voice_profiles:
            self.voice_profile_combo.addItem(profile.name, profile)
            
    def _populate_emotions(self):
        """填充情感下拉框"""
        self.emotion_combo.clear()
        if self.current_profile:
            for emotion in self.current_profile.supported_emotions:
                self.emotion_combo.addItem(emotion.value.capitalize())
                
    def _populate_voice_table(self):
        """填充语音表格"""
        self.voice_table.setRowCount(len(self.voice_profiles))
        
        for i, profile in enumerate(self.voice_profiles):
            # 语音名称
            name_item = QTableWidgetItem(profile.name)
            self.voice_table.setItem(i, 0, name_item)
            
            # 类型
            type_item = QTableWidgetItem(profile.voice_type.value.capitalize())
            self.voice_table.setItem(i, 1, type_item)
            
            # 引擎
            engine_item = QTableWidgetItem(profile.engine.value.capitalize())
            self.voice_table.setItem(i, 2, engine_item)
            
            # 情感支持
            emotions_text = ", ".join([e.value.capitalize() for e in profile.supported_emotions])
            emotions_item = QTableWidgetItem(emotions_text)
            self.voice_table.setItem(i, 3, emotions_item)
            
            # 操作
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            preview_btn = QPushButton("👂")
            preview_btn.setMaximumWidth(40)
            preview_btn.clicked.connect(lambda checked, p=profile: self._preview_profile_voice(p))
            actions_layout.addWidget(preview_btn)
            
            select_btn = QPushButton("✅")
            select_btn.setMaximumWidth(40)
            select_btn.clicked.connect(lambda checked, p=profile: self._select_voice_profile(p))
            actions_layout.addWidget(select_btn)
            
            self.voice_table.setCellWidget(i, 4, actions_widget)
            
    def _connect_signals(self):
        """连接信号"""
        # 文本输入变化
        self.text_input.textChanged.connect(self._update_text_stats)
        
        # 滑块变化
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        self.volume_slider.valueChanged.connect(self._update_volume_label)
        self.pitch_slider.valueChanged.connect(self._update_pitch_label)
        
        # 语音配置变化
        self.voice_profile_combo.currentTextChanged.connect(self._on_voice_profile_changed)
        
        # 媒体播放器信号
        self.media_player.positionChanged.connect(self._update_playback_position)
        self.media_player.durationChanged.connect(self._update_duration)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        
        # 音量控制
        self.playback_volume_slider.valueChanged.connect(self._update_playback_volume)
        
    def _update_text_stats(self):
        """更新文本统计"""
        text = self.text_input.toPlainText()
        
        # 字符数
        char_count = len(text)
        self.char_count_label.setText(f"字符数: {char_count}")
        
        # 词数
        words = text.split()
        word_count = len(words)
        self.word_count_label.setText(f"词数: {word_count}")
        
        # 预计时长
        estimated_time = max(char_count * 0.1, 1.0)  # 简单估算
        self.estimated_time_label.setText(f"预计时长: {estimated_time:.1f}秒")
        
    def _update_speed_label(self, value):
        """更新语速标签"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        
    def _update_volume_label(self, value):
        """更新音量标签"""
        self.volume_label.setText(f"{value}%")
        
    def _update_pitch_label(self, value):
        """更新音调标签"""
        pitch = value / 100.0
        self.pitch_label.setText(f"{pitch:.1f}x")
        
    def _on_voice_profile_changed(self, profile_name):
        """语音配置变更"""
        for profile in self.voice_profiles:
            if profile.name == profile_name:
                self.current_profile = profile
                self._populate_emotions()
                self.voice_profile_changed.emit(profile)
                break
                
    def _on_voice_selected(self):
        """语音选择"""
        current_row = self.voice_table.currentRow()
        if current_row >= 0 and current_row < len(self.voice_profiles):
            profile = self.voice_profiles[current_row]
            self._show_voice_details(profile)
            
    def _show_voice_details(self, profile: TTSVoiceProfile):
        """显示语音详情"""
        details = f"""
<h3>{profile.name}</h3>
<p><strong>类型:</strong> {profile.voice_type.value}</p>
<p><strong>引擎:</strong> {profile.engine.value}</p>
<p><strong>描述:</strong> {profile.description}</p>
<p><strong>采样率:</strong> {profile.sample_rate}Hz</p>
<p><strong>声道:</strong> {profile.channels}</p>
<p><strong>位深:</strong> {profile.bit_depth}bit</p>
<p><strong>支持情感:</strong> {', '.join([e.value for e in profile.supported_emotions])}</p>
"""
        self.voice_details.setHtml(details)
        
    def _select_voice_profile(self, profile: TTSVoiceProfile):
        """选择语音配置"""
        index = self.voice_profile_combo.findText(profile.name)
        if index >= 0:
            self.voice_profile_combo.setCurrentIndex(index)
            
    def _preview_profile_voice(self, profile: TTSVoiceProfile):
        """预览语音配置"""
        preview_text = "这是语音预览效果，让您了解这个语音的声音特点。"
        
        # 临时切换到选中的语音
        old_profile = self.current_profile
        self.current_profile = profile
        
        # 播放预览
        asyncio.create_task(self._preview_voice_async(preview_text))
        
        # 恢复原来的语音
        self.current_profile = old_profile
        
    async def _preview_voice_async(self, text: str):
        """异步预览语音"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                output_path = tmp_file.name
            
            # 合成语音
            success = await self.tts_engine.synthesize(
                text=text,
                output_path=output_path,
                voice_type=self.current_profile.voice_type.value,
                emotion=EmotionType.NEUTRAL.value,
                speed=1.0
            )
            
            if success:
                # 播放预览
                self.media_player.setSource(QUrl.fromLocalFile(output_path))
                self.media_player.play()
                
                # 清理临时文件
                QTimer.singleShot(5000, lambda: self._cleanup_temp_file(output_path))
                
        except Exception as e:
            QMessageBox.warning(self, "预览失败", f"语音预览失败: {str(e)}")
            
    def _cleanup_temp_file(self, file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
            
    def _preview_voice(self):
        """预览当前语音"""
        preview_text = "这是语音预览效果，让您了解当前语音的声音特点。"
        asyncio.create_task(self._preview_voice_async(preview_text))
        
    def _start_synthesis(self):
        """开始语音合成"""
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入要合成的文本")
            return
            
        # 创建合成请求
        request = self.create_synthesis_request(text)
        self.active_requests[request.request_id] = request
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在合成语音...")
        self.synthesize_btn.setEnabled(False)
        
        # 发送信号
        self.synthesis_started.emit(request.request_id)
        
        # 开始合成
        asyncio.create_task(self.execute_synthesis(request))
        
    def create_synthesis_request(self, text: str) -> TTSRequest:
        """创建合成请求"""
        # 获取当前选择的情感
        emotion_text = self.emotion_combo.currentText()
        emotion = EmotionType.NEUTRAL
        for e in EmotionType:
            if e.value.capitalize() == emotion_text:
                emotion = e
                break
        
        # 确定输出路径
        output_path = self.output_path_input.text()
        if not output_path:
            # 自动生成输出路径
            import tempfile
            output_path = tempfile.mktemp(suffix=f'.{self.audio_format_combo.currentText().lower()}')
        
        return TTSRequest(
            request_id=f"tts_{self.request_counter}",
            text=text,
            voice_type=self.current_profile.voice_type,
            emotion=emotion,
            speed=self.speed_slider.value() / 100.0,
            pitch=self.pitch_slider.value() / 100.0,
            volume=self.volume_slider.value() / 100.0,
            engine=TTSEngine(self.tts_engine_combo.currentText().lower()),
            output_format=AudioFormat(self.audio_format_combo.currentText().lower()),
            output_path=output_path
        )
        
    async def execute_synthesis(self, request: TTSRequest):
        """执行语音合成"""
        try:
            self.synthesis_progress.emit(request.request_id, 0.0)
            
            # 模拟合成进度
            for i in range(1, 101):
                await asyncio.sleep(0.02)  # 模拟处理时间
                self.synthesis_progress.emit(request.request_id, i)
                self.progress_bar.setValue(i)
                
                if i == 25:
                    self.status_label.setText("正在分析文本...")
                elif i == 50:
                    self.status_label.setText("正在生成语音...")
                elif i == 75:
                    self.status_label.setText("正在优化音频...")
            
            # 执行实际的语音合成
            success = await self.tts_engine.synthesize(
                text=request.text,
                output_path=request.output_path,
                voice_type=request.voice_type.value,
                emotion=request.emotion.value,
                speed=request.speed
            )
            
            if success:
                # 获取文件信息
                file_size = 0
                duration = 0.0
                if os.path.exists(request.output_path):
                    file_size = os.path.getsize(request.output_path)
                    # 简单的时长估算
                    duration = len(request.text) * 0.1 * request.speed
                
                # 创建响应
                response = TTSResponse(
                    request_id=request.request_id,
                    success=True,
                    output_path=request.output_path,
                    duration=duration,
                    file_size=file_size,
                    metadata={
                        "engine": request.engine.value,
                        "voice_type": request.voice_type.value,
                        "emotion": request.emotion.value,
                        "speed": request.speed,
                        "format": request.output_format.value
                    }
                )
                
                # 更新UI
                self.current_audio_file = request.output_path
                self.play_btn.setEnabled(True)
                self.status_label.setText("合成完成")
                
                # 发送信号
                self.synthesis_completed.emit(request.request_id, response)
                
                # 如果设置为合成后播放
                if self.play_after_synthesis_check.isChecked():
                    self._play_audio()
                    
            else:
                raise Exception("语音合成失败")
                
        except Exception as e:
            error_response = TTSResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e)
            )
            
            self.synthesis_error.emit(request.request_id, str(e))
            self.status_label.setText(f"合成失败: {str(e)}")
            
        finally:
            # 清理请求
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            # 隐藏进度条（延迟）
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
            self.synthesize_btn.setEnabled(True)
            
    def _cancel_synthesis(self):
        """取消合成"""
        # 取消所有活跃的合成请求
        for request_id in list(self.active_requests.keys()):
            self.synthesis_error.emit(request_id, "用户取消")
            
        self.active_requests.clear()
        self.progress_widget.setVisible(False)
        self.status_label.setText("已取消")
        self.synthesize_btn.setEnabled(True)
        
    def _play_audio(self):
        """播放音频"""
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            self.media_player.setSource(QUrl.fromLocalFile(self.current_audio_file))
            self.media_player.play()
            self.playback_started.emit(self.current_audio_file)
            
    def _pause_audio(self):
        """暂停音频"""
        self.media_player.pause()
        
    def _stop_audio(self):
        """停止音频"""
        self.media_player.stop()
        self.playback_stopped.emit(self.current_audio_file)
        
    def _update_playback_position(self, position):
        """更新播放位置"""
        if self.media_player.duration() > 0:
            progress = (position / self.media_player.duration()) * 100
            self.playback_progress.setValue(int(progress))
            
        # 更新时间显示
        current_time = QTime(0, 0).addMSecs(position)
        self.current_time_label.setText(current_time.toString("mm:ss"))
        
    def _update_duration(self, duration):
        """更新总时长"""
        total_time = QTime(0, 0).addMSecs(duration)
        self.total_time_label.setText(total_time.toString("mm:ss"))
        
    def _on_playback_state_changed(self, state):
        """播放状态变化"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        else:
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            
    def _update_playback_volume(self, value):
        """更新播放音量"""
        self.audio_output.setVolume(value / 100.0)
        
    def _browse_output_path(self):
        """浏览输出路径"""
        file_format = self.audio_format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", "", f"{file_format.upper()}文件 (*.{file_format})"
        )
        if file_path:
            self.output_path_input.setText(file_path)
            
    def _browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)
            
    def _import_batch_file(self):
        """导入批量文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            self.batch_file_input.setText(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.batch_text_input.setText(content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件读取失败: {str(e)}")
                
    def _preview_batch(self):
        """预览批量合成"""
        text = self.batch_text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入要批量合成的文本")
            return
            
        # 分割文本
        delimiter = self.delimiter_input.text().replace("\\n", "\n")
        texts = [t.strip() for t in text.split(delimiter) if t.strip()]
        
        QMessageBox.information(self, "批量预览", f"找到 {len(texts)} 个文本段落\n第一个段落: {texts[0][:50]}...")
        
    def _start_batch_synthesis(self):
        """开始批量合成"""
        QMessageBox.information(self, "批量合成", "批量合成功能开发中...")
        
    def _filter_voices(self):
        """过滤语音列表"""
        category = self.voice_category_combo.currentText()
        search_text = self.voice_search_input.text().lower()
        
        # 实现语音过滤逻辑
        for i in range(self.voice_table.rowCount()):
            name_item = self.voice_table.item(i, 0)
            if name_item:
                name = name_item.text().lower()
                
                # 检查分类匹配
                category_match = (category == "全部" or category.lower() in name)
                
                # 检查搜索文本匹配
                search_match = (not search_text or search_text in name)
                
                # 显示或隐藏行
                self.voice_table.setRowHidden(i, not (category_match and search_match))
                
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("tts_component", {})
        
        # 应用设置
        if "default_voice" in settings:
            index = self.voice_profile_combo.findText(settings["default_voice"])
            if index >= 0:
                self.voice_profile_combo.setCurrentIndex(index)
                
        if "default_speed" in settings:
            speed = int(settings["default_speed"] * 100)
            self.speed_slider.setValue(speed)
            
        if "default_volume" in settings:
            self.volume_slider.setValue(int(settings["default_volume"] * 100))
            
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_voice": self.voice_profile_combo.currentText(),
            "default_speed": self.speed_slider.value() / 100.0,
            "default_volume": self.volume_slider.value() / 100.0
        }
        
        self.settings_manager.set_setting("tts_component", settings)
        
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        
        # 停止播放
        self.media_player.stop()
        
        # 清理TTS引擎
        self.tts_engine.cleanup()
        
        super().closeEvent(event)