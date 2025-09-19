#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出设置面板组件
提供完整的视频导出功能，包括格式选择、质量设置、批量导出等
"""

import os
import sys
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QPushButton, QLabel, QComboBox, QSpinBox, QSlider,
    QGroupBox, QTabWidget, QStackedWidget, QSplitter,
    QTextEdit, QLineEdit, QProgressBar, QCheckBox,
    QRadioButton, QButtonGroup, QFormLayout, QGridLayout,
    QMessageBox, QInputDialog, QDialog, QToolButton,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QToolBar, QMenu, QStatusBar, QSizePolicy,
    QScrollArea, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit, QCalendarWidget,
    QFontComboBox, QColorDialog, QFontDialog, QFileDialog,
    QApplication, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, pyqtSignal, QTimer,
    QThread, pyqtSlot, QPropertyAnimation, QEasingCurve,
    QSettings, QStandardPaths, QDir, QFile, QIODevice,
    QTextStream, QBuffer, QMimeData, QUrl, QSortFilterProxyModel
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QIcon,
    QPixmap, QImage, QTextCursor, QTextDocument,
    QLinearGradient, QCursor, QKeySequence, QShortcut,
    QDragEnterEvent, QDropEvent, QWheelEvent, QStandardItemModel, QStandardItem, QAction
)

from .professional_ui_system import ProfessionalStyleEngine


class ExportFormat(Enum):
    """导出格式"""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WMV = "wmv"
    FLV = "flv"
    WEBM = "webm"
    M4V = "m4v"


class VideoCodec(Enum):
    """视频编码器"""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    AV1 = "av1"
    MPEG4 = "mpeg4"
    PRORES = "prores"
    DNxHD = "dnxhd"


class AudioCodec(Enum):
    """音频编码器"""
    AAC = "aac"
    MP3 = "mp3"
    AC3 = "ac3"
    FLAC = "flac"
    WAV = "wav"
    OGG = "ogg"
    OPUS = "opus"


class QualityPreset(Enum):
    """质量预设"""
    LOW = "low"              # 低质量
    MEDIUM = "medium"        # 中等质量
    HIGH = "high"            # 高质量
    ULTRA = "ultra"          # 超高质量
    CUSTOM = "custom"        # 自定义


class ExportProfile(Enum):
    """导出配置文件"""
    YOUTUBE = "youtube"          # YouTube
    BILIBILI = "bilibili"        # B站
    TIKTOK = "tiktok"            # 抖音
    WEIBO = "weibo"              # 微博
    INSTAGRAM = "instagram"      # Instagram
    FACEBOOK = "facebook"        # Facebook
    TWITTER = "twitter"          # Twitter
    CUSTOM = "custom"            # 自定义


@dataclass
class ExportSettings:
    """导出设置数据"""
    format: ExportFormat = ExportFormat.MP4
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.AAC
    quality_preset: QualityPreset = QualityPreset.HIGH
    export_profile: ExportProfile = ExportProfile.CUSTOM

    # 视频设置
    resolution: Tuple[int, int] = (1920, 1080)
    frame_rate: int = 30
    bitrate: int = 8000  # kbps
    keyframe_interval: int = 2  # 秒

    # 音频设置
    audio_bitrate: int = 192  # kbps
    sample_rate: int = 44100  # Hz
    audio_channels: int = 2

    # 高级设置
    use_hardware_acceleration: bool = True
    use_multi_threading: bool = True
    enable_two_pass: bool = False
    pixel_format: str = "yuv420p"
    color_space: str = "bt709"

    # 输出设置
    output_directory: str = ""
    filename_template: str = "{project_name}_{date}_{time}"
    include_watermark: bool = False
    watermark_path: str = ""
    watermark_position: str = "bottom-right"
    watermark_opacity: float = 0.7

    # 元数据设置
    include_metadata: bool = True
    title: str = ""
    description: str = ""
    tags: List[str] = None
    author: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ExportTask:
    """导出任务数据"""
    id: str
    name: str
    source_path: str
    output_path: str
    settings: ExportSettings
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    file_size: int = 0
    error_message: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ExportSettingsPanel(QWidget):
    """导出设置面板"""

    # 信号定义
    exportStarted = pyqtSignal(str)        # 导出开始
    exportProgress = pyqtSignal(str, float) # 导出进度
    exportCompleted = pyqtSignal(str)      # 导出完成
    exportFailed = pyqtSignal(str, str)    # 导出失败
    settingsChanged = pyqtSignal(ExportSettings)  # 设置改变

    def __init__(self, parent=None):
        super().__init__(parent)
        self.style_engine = ProfessionalStyleEngine()

        # 导出任务管理
        self.export_tasks: List[ExportTask] = []
        self.current_task: Optional[ExportTask] = None

        # 导出设置
        self.current_settings = ExportSettings()

        # 预设配置
        self.presets = self._load_presets()

        # 初始化UI
        self.init_ui()
        self.setup_connections()
        self.apply_styles()

        # 加载默认设置
        self.load_default_settings()

    def init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 工具栏
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)

        # 主要内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧设置面板
        left_panel = self.create_settings_panel()
        content_splitter.addWidget(left_panel)

        # 右侧任务面板
        right_panel = self.create_task_panel()
        content_splitter.addWidget(right_panel)

        # 设置分割器比例
        content_splitter.setSizes([700, 500])
        main_layout.addWidget(content_splitter)

        # 底部状态栏
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

    def create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        # 预设管理
        preset_action = toolbar.addAction("预设管理")
        preset_action.triggered.connect(self.show_preset_manager)

        toolbar.addSeparator()

        # 批量导出
        batch_action = toolbar.addAction("批量导出")
        batch_action.triggered.connect(self.show_batch_export)

        toolbar.addSeparator()

        # 历史记录
        history_action = toolbar.addAction("导出历史")
        history_action.triggered.connect(self.show_export_history)

        toolbar.addSeparator()

        # 设置
        settings_action = toolbar.addAction("设置")
        settings_action.triggered.connect(self.show_settings)

        toolbar.addStretch()

        return toolbar

    def create_settings_panel(self) -> QWidget:
        """创建设置面板"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)

        # 预设选择
        preset_group = QGroupBox("导出预设")
        preset_layout = QHBoxLayout(preset_group)

        self.profile_combo = QComboBox()
        self.populate_profile_combo()
        preset_layout.addWidget(self.profile_combo)

        save_preset_btn = QPushButton("保存预设")
        save_preset_btn.clicked.connect(self.save_current_preset)
        preset_layout.addWidget(save_preset_btn)

        settings_layout.addWidget(preset_group)

        # 标签页设置
        self.settings_tabs = QTabWidget()

        # 基本设置标签页
        basic_tab = self.create_basic_settings_tab()
        self.settings_tabs.addTab(basic_tab, "基本设置")

        # 视频设置标签页
        video_tab = self.create_video_settings_tab()
        self.settings_tabs.addTab(video_tab, "视频设置")

        # 音频设置标签页
        audio_tab = self.create_audio_settings_tab()
        self.settings_tabs.addTab(audio_tab, "音频设置")

        # 高级设置标签页
        advanced_tab = self.create_advanced_settings_tab()
        self.settings_tabs.addTab(advanced_tab, "高级设置")

        # 输出设置标签页
        output_tab = self.create_output_settings_tab()
        self.settings_tabs.addTab(output_tab, "输出设置")

        settings_layout.addWidget(self.settings_tabs)

        # 导出按钮
        export_layout = QHBoxLayout()

        self.export_btn = QPushButton("🚀 开始导出")
        self.export_btn.clicked.connect(self.start_export)
        self.export_btn.setObjectName("export_btn")
        export_layout.addWidget(self.export_btn)

        self.preview_btn = QPushButton("👁 预览")
        self.preview_btn.clicked.connect(self.preview_export)
        export_layout.addWidget(self.preview_btn)

        settings_layout.addLayout(export_layout)

        settings_layout.addStretch()

        return settings_widget

    def create_basic_settings_tab(self) -> QWidget:
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 格式选择
        self.format_combo = QComboBox()
        for format_type in ExportFormat:
            self.format_combo.addItem(format_type.value.upper(), format_type)
        layout.addRow("输出格式:", self.format_combo)

        # 质量预设
        self.quality_combo = QComboBox()
        for quality in QualityPreset:
            self.quality_combo.addItem(quality.value.title(), quality)
        layout.addRow("质量预设:", self.quality_combo)

        # 分辨率
        resolution_layout = QHBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "3840×2160 (4K)", "2560×1440 (2K)", "1920×1080 (1080p)",
            "1280×720 (720p)", "854×480 (480p)", "640×360 (360p)", "自定义"
        ])
        resolution_layout.addWidget(self.resolution_combo)

        self.custom_width = QSpinBox()
        self.custom_width.setRange(160, 7680)
        self.custom_width.setValue(1920)
        self.custom_width.setEnabled(False)
        resolution_layout.addWidget(QLabel("×"))

        self.custom_height = QSpinBox()
        self.custom_height.setRange(90, 4320)
        self.custom_height.setValue(1080)
        self.custom_height.setEnabled(False)
        resolution_layout.addWidget(self.custom_height)

        layout.addRow("分辨率:", resolution_layout)

        # 帧率
        self.framerate_combo = QComboBox()
        self.framerate_combo.addItems([
            "24 fps", "25 fps", "30 fps", "50 fps", "60 fps", "自定义"
        ])
        layout.addRow("帧率:", self.framerate_combo)

        # 预计文件大小
        self.filesize_label = QLabel("预计文件大小: -- MB")
        layout.addRow("预计大小:", self.filesize_label)

        return widget

    def create_video_settings_tab(self) -> QWidget:
        """创建视频设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 视频编码器
        self.video_codec_combo = QComboBox()
        for codec in VideoCodec:
            self.video_codec_combo.addItem(codec.value.upper(), codec)
        layout.addRow("视频编码器:", self.video_codec_combo)

        # 比特率
        bitrate_layout = QHBoxLayout()
        self.bitrate_slider = QSlider(Qt.Orientation.Horizontal)
        self.bitrate_slider.setRange(1000, 50000)
        self.bitrate_slider.setValue(8000)
        bitrate_layout.addWidget(self.bitrate_slider)

        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1000, 50000)
        self.bitrate_spin.setValue(8000)
        self.bitrate_spin.setSuffix(" kbps")
        bitrate_layout.addWidget(self.bitrate_spin)

        layout.addRow("视频比特率:", bitrate_layout)

        # 关键帧间隔
        self.keyframe_spin = QSpinBox()
        self.keyframe_spin.setRange(1, 10)
        self.keyframe_spin.setValue(2)
        self.keyframe_spin.setSuffix(" 秒")
        layout.addRow("关键帧间隔:", self.keyframe_spin)

        # 像素格式
        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.addItems([
            "yuv420p", "yuv422p", "yuv444p", "yuv420p10le", "yuv422p10le"
        ])
        layout.addRow("像素格式:", self.pixel_format_combo)

        # 色彩空间
        self.colorspace_combo = QComboBox()
        self.colorspace_combo.addItems([
            "bt709", "bt601", "bt2020", "smpte240m"
        ])
        layout.addRow("色彩空间:", self.colorspace_combo)

        return widget

    def create_audio_settings_tab(self) -> QWidget:
        """创建音频设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 音频编码器
        self.audio_codec_combo = QComboBox()
        for codec in AudioCodec:
            self.audio_codec_combo.addItem(codec.value.upper(), codec)
        layout.addRow("音频编码器:", self.audio_codec_combo)

        # 音频比特率
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems([
            "64 kbps", "96 kbps", "128 kbps", "192 kbps", "256 kbps", "320 kbps"
        ])
        layout.addRow("音频比特率:", self.audio_bitrate_combo)

        # 采样率
        self.samplerate_combo = QComboBox()
        self.samplerate_combo.addItems([
            "22050 Hz", "44100 Hz", "48000 Hz", "96000 Hz"
        ])
        layout.addRow("采样率:", self.samplerate_combo)

        # 声道数
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["单声道", "立体声", "5.1环绕声"])
        layout.addRow("声道数:", self.channels_combo)

        return widget

    def create_advanced_settings_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 性能设置
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout(performance_group)

        self.hardware_accel_check = QCheckBox()
        self.hardware_accel_check.setChecked(True)
        performance_layout.addRow("硬件加速:", self.hardware_accel_check)

        self.multithreading_check = QCheckBox()
        self.multithreading_check.setChecked(True)
        performance_layout.addRow("多线程编码:", self.multithreading_check)

        self.twopass_check = QCheckBox()
        performance_layout.addRow("双通道编码:", self.twopass_check)

        layout.addWidget(performance_group)

        # 滤镜设置
        filter_group = QGroupBox("滤镜设置")
        filter_layout = QFormLayout(filter_group)

        self.sharpness_slider = QSlider(Qt.Orientation.Horizontal)
        self.sharpness_slider.setRange(0, 100)
        self.sharpness_slider.setValue(0)
        filter_layout.addRow("锐化:", self.sharpness_slider)

        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        filter_layout.addRow("对比度:", self.contrast_slider)

        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 200)
        self.brightness_slider.setValue(100)
        filter_layout.addRow("亮度:", self.brightness_slider)

        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(100)
        filter_layout.addRow("饱和度:", self.saturation_slider)

        layout.addWidget(filter_group)

        layout.addStretch()

        return widget

    def create_output_settings_tab(self) -> QWidget:
        """创建输出设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 输出目录
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录")
        output_layout.addRow("输出目录:", self.output_dir_edit)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_output_directory)
        output_layout.addRow("", browse_btn)

        # 文件名模板
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setText("{project_name}_{date}_{time}")
        output_layout.addRow("文件名模板:", self.filename_template_edit)

        # 水印设置
        self.watermark_check = QCheckBox()
        self.watermark_check.setChecked(False)
        output_layout.addRow("添加水印:", self.watermark_check)

        watermark_layout = QHBoxLayout()
        self.watermark_path_edit = QLineEdit()
        self.watermark_path_edit.setPlaceholderText("选择水印图片")
        self.watermark_path_edit.setEnabled(False)
        watermark_layout.addWidget(self.watermark_path_edit)

        watermark_browse_btn = QPushButton("浏览")
        watermark_browse_btn.clicked.connect(self.browse_watermark)
        watermark_browse_btn.setEnabled(False)
        watermark_layout.addWidget(watermark_browse_btn)

        output_layout.addRow("", watermark_layout)

        layout.addWidget(output_group)

        # 元数据设置
        metadata_group = QGroupBox("元数据")
        metadata_layout = QFormLayout(metadata_group)

        self.metadata_check = QCheckBox()
        self.metadata_check.setChecked(True)
        metadata_layout.addRow("包含元数据:", self.metadata_check)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("视频标题")
        metadata_layout.addRow("标题:", self.title_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("视频描述")
        metadata_layout.addRow("描述:", self.description_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("作者")
        metadata_layout.addRow("作者:", self.author_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签，用逗号分隔")
        metadata_layout.addRow("标签:", self.tags_edit)

        layout.addWidget(metadata_group)

        layout.addStretch()

        return widget

    def create_task_panel(self) -> QWidget:
        """创建任务面板"""
        task_widget = QWidget()
        task_layout = QVBoxLayout(task_widget)
        task_layout.setContentsMargins(10, 10, 10, 10)
        task_layout.setSpacing(10)

        # 任务列表
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels([
            "任务名称", "状态", "进度", "文件大小", "创建时间", "操作"
        ])

        # 设置列宽
        self.task_table.setColumnWidth(0, 150)
        self.task_table.setColumnWidth(1, 80)
        self.task_table.setColumnWidth(2, 100)
        self.task_table.setColumnWidth(3, 100)
        self.task_table.setColumnWidth(4, 150)
        self.task_table.setColumnWidth(5, 100)

        # 设置选择模式
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        task_layout.addWidget(self.task_table)

        # 任务操作
        task_actions = QHBoxLayout()

        self.cancel_task_btn = QPushButton("取消任务")
        self.cancel_task_btn.clicked.connect(self.cancel_selected_task)
        self.cancel_task_btn.setEnabled(False)
        task_actions.addWidget(self.cancel_task_btn)

        self.remove_task_btn = QPushButton("移除任务")
        self.remove_task_btn.clicked.connect(self.remove_selected_task)
        task_actions.addWidget(self.remove_task_btn)

        self.clear_completed_btn = QPushButton("清空已完成")
        self.clear_completed_btn.clicked.connect(self.clear_completed_tasks)
        task_actions.addWidget(self.clear_completed_btn)

        task_actions.addStretch()

        task_layout.addLayout(task_actions)

        # 任务详情
        details_group = QGroupBox("任务详情")
        details_layout = QVBoxLayout(details_group)

        self.task_details = QTextEdit()
        self.task_details.setReadOnly(True)
        self.task_details.setMaximumHeight(120)
        details_layout.addWidget(self.task_details)

        task_layout.addWidget(details_group)

        return task_widget

    def setup_connections(self):
        """设置信号连接"""
        # 基本设置连接
        self.format_combo.currentTextChanged.connect(self.on_settings_changed)
        self.quality_combo.currentTextChanged.connect(self.on_settings_changed)
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        self.framerate_combo.currentTextChanged.connect(self.on_settings_changed)

        # 视频设置连接
        self.video_codec_combo.currentTextChanged.connect(self.on_settings_changed)
        self.bitrate_slider.valueChanged.connect(self.on_bitrate_changed)
        self.bitrate_spin.valueChanged.connect(self.on_bitrate_spin_changed)

        # 音频设置连接
        self.audio_codec_combo.currentTextChanged.connect(self.on_settings_changed)
        self.audio_bitrate_combo.currentTextChanged.connect(self.on_settings_changed)
        self.samplerate_combo.currentTextChanged.connect(self.on_settings_changed)
        self.channels_combo.currentTextChanged.connect(self.on_settings_changed)

        # 预设连接
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)

        # 任务选择连接
        self.task_table.itemSelectionChanged.connect(self.on_task_selection_changed)

        # 定时器更新任务状态
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_task_status)
        self.update_timer.start(1000)

    def populate_profile_combo(self):
        """填充预设下拉框"""
        for profile in ExportProfile:
            self.profile_combo.addItem(profile.value.title(), profile)

    def on_settings_changed(self):
        """设置改变事件"""
        self.update_settings_from_ui()
        self.estimate_file_size()
        self.settingsChanged.emit(self.current_settings)

    def on_resolution_changed(self):
        """分辨率改变事件"""
        resolution_text = self.resolution_combo.currentText()
        if resolution_text == "自定义":
            self.custom_width.setEnabled(True)
            self.custom_height.setEnabled(True)
        else:
            self.custom_width.setEnabled(False)
            self.custom_height.setEnabled(False)
            # 解析分辨率
            import re
            match = re.search(r'(\d+)×(\d+)', resolution_text)
            if match:
                width, height = match.groups()
                self.custom_width.setValue(int(width))
                self.custom_height.setValue(int(height))

        self.on_settings_changed()

    def on_bitrate_changed(self, value):
        """比特率滑块改变事件"""
        self.bitrate_spin.setValue(value)
        self.on_settings_changed()

    def on_bitrate_spin_changed(self, value):
        """比特率输入框改变事件"""
        self.bitrate_slider.setValue(value)
        self.on_settings_changed()

    def on_profile_changed(self):
        """预设改变事件"""
        profile_name = self.profile_combo.currentText().lower()

        # 查找对应的预设
        for profile in ExportProfile:
            if profile.value == profile_name:
                self.apply_profile(profile)
                break

    def on_task_selection_changed(self):
        """任务选择改变事件"""
        selected_items = self.task_table.selectedItems()
        has_selection = len(selected_items) > 0

        self.cancel_task_btn.setEnabled(has_selection)

        if has_selection:
            # 显示任务详情
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            task = next((t for t in self.export_tasks if t.id == task_id), None)
            if task:
                self.show_task_details(task)

    def apply_profile(self, profile: ExportProfile):
        """应用预设配置"""
        if profile == ExportProfile.YOUTUBE:
            self.format_combo.setCurrentText("mp4")
            self.video_codec_combo.setCurrentText("h264")
            self.audio_codec_combo.setCurrentText("aac")
            self.resolution_combo.setCurrentText("1920×1080 (1080p)")
            self.framerate_combo.setCurrentText("30 fps")
            self.bitrate_slider.setValue(8000)
            self.audio_bitrate_combo.setCurrentText("192 kbps")

        elif profile == ExportProfile.BILIBILI:
            self.format_combo.setCurrentText("mp4")
            self.video_codec_combo.setCurrentText("h264")
            self.audio_codec_combo.setCurrentText("aac")
            self.resolution_combo.setCurrentText("1920×1080 (1080p)")
            self.framerate_combo.setCurrentText("30 fps")
            self.bitrate_slider.setValue(6000)
            self.audio_bitrate_combo.setCurrentText("128 kbps")

        elif profile == ExportProfile.TIKTOK:
            self.format_combo.setCurrentText("mp4")
            self.video_codec_combo.setCurrentText("h264")
            self.audio_codec_combo.setCurrentText("aac")
            self.resolution_combo.setCurrentText("1080×1920 (1080p)")
            self.framerate_combo.setCurrentText("30 fps")
            self.bitrate_slider.setValue(5000)
            self.audio_bitrate_combo.setCurrentText("128 kbps")

        self.update_settings_from_ui()

    def update_settings_from_ui(self):
        """从UI更新设置"""
        try:
            self.current_settings.format = ExportFormat(self.format_combo.currentText().lower())
            self.current_settings.video_codec = VideoCodec(self.video_codec_combo.currentText().lower())
            self.current_settings.audio_codec = AudioCodec(self.audio_codec_combo.currentText().lower())
            self.current_settings.resolution = (self.custom_width.value(), self.custom_height.value())
            self.current_settings.bitrate = self.bitrate_slider.value()
            self.current_settings.audio_bitrate = int(self.audio_bitrate_combo.currentText().split()[0])
            self.current_settings.use_hardware_acceleration = self.hardware_accel_check.isChecked()
            self.current_settings.use_multi_threading = self.multithreading_check.isChecked()
            self.current_settings.enable_two_pass = self.twopass_check.isChecked()

            # 更新质量预设
            quality_text = self.quality_combo.currentText().lower()
            for quality in QualityPreset:
                if quality.value == quality_text:
                    self.current_settings.quality_preset = quality
                    break

        except Exception as e:
            print(f"更新设置时出错: {e}")

    def estimate_file_size(self):
        """估算文件大小"""
        try:
            # 简单的文件大小估算
            duration_minutes = 5  # 假设5分钟
            video_bitrate_mbps = self.current_settings.bitrate / 1000
            audio_bitrate_mbps = self.current_settings.audio_bitrate / 1000
            total_bitrate_mbps = video_bitrate_mbps + audio_bitrate_mbps

            file_size_mb = (total_bitrate_mbps * 60 * duration_minutes) / 8
            self.filesize_label.setText(f"预计文件大小: {file_size_mb:.1f} MB")

        except Exception as e:
            self.filesize_label.setText("预计文件大小: -- MB")

    def start_export(self):
        """开始导出"""
        if not self.output_dir_edit.text():
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return

        # 创建导出任务
        task = ExportTask(
            id=f"export_{len(self.export_tasks) + 1}",
            name=f"导出任务 {len(self.export_tasks) + 1}",
            source_path="",  # 这里应该从项目获取源文件路径
            output_path="",  # 稍后计算
            settings=self.current_settings
        )

        # 计算输出路径
        filename = self.generate_filename()
        output_path = os.path.join(self.output_dir_edit.text(), filename)
        task.output_path = output_path

        self.export_tasks.append(task)
        self.add_task_to_table(task)

        # 开始导出
        self.exportStarted.emit(task.id)
        self.execute_export_task(task)

    def execute_export_task(self, task: ExportTask):
        """执行导出任务"""
        try:
            task.status = "running"
            task.started_at = datetime.now()
            self.update_task_row(task)

            # 模拟导出过程
            def export_thread():
                import time
                for i in range(101):
                    time.sleep(0.1)  # 模拟处理时间
                    task.progress = i
                    self.exportProgress.emit(task.id, i)

                    # 在主线程中更新UI
                    QTimer.singleShot(0, lambda: self.update_task_progress(task))

                # 导出完成
                task.status = "completed"
                task.completed_at = datetime.now()
                task.file_size = 1024 * 1024 * 50  # 模拟50MB文件

                QTimer.singleShot(0, lambda: self.on_export_completed(task))

            # 在后台线程中运行
            import threading
            threading.Thread(target=export_thread, daemon=True).start()

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.exportFailed.emit(task.id, str(e))
            self.update_task_row(task)

    def on_export_completed(self, task: ExportTask):
        """导出完成事件"""
        self.exportCompleted.emit(task.id)
        self.update_task_row(task)

        QMessageBox.information(
            self, "导出完成",
            f"导出任务完成！\n文件路径: {task.output_path}\n文件大小: {task.file_size / 1024 / 1024:.1f} MB"
        )

    def update_task_progress(self, task: ExportTask):
        """更新任务进度"""
        self.update_task_row(task)

        # 更新状态栏
        self.status_bar.showMessage(f"正在导出: {task.name} - {task.progress:.1f}%")

    def update_task_status(self):
        """更新任务状态"""
        # 更新所有任务的显示
        for task in self.export_tasks:
            self.update_task_row(task)

    def add_task_to_table(self, task: ExportTask):
        """添加任务到表格"""
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)

        # 任务名称
        name_item = QTableWidgetItem(task.name)
        name_item.setData(Qt.ItemDataRole.UserRole, task.id)
        self.task_table.setItem(row, 0, name_item)

        # 状态
        status_item = QTableWidgetItem(self.get_status_text(task.status))
        status_item.setForeground(self.get_status_color(task.status))
        self.task_table.setItem(row, 1, status_item)

        # 进度
        progress_item = QTableWidgetItem(f"{task.progress:.1f}%")
        self.task_table.setItem(row, 2, progress_item)

        # 文件大小
        size_text = f"{task.file_size / 1024 / 1024:.1f} MB" if task.file_size > 0 else "--"
        size_item = QTableWidgetItem(size_text)
        self.task_table.setItem(row, 3, size_item)

        # 创建时间
        time_item = QTableWidgetItem(task.created_at.strftime("%H:%M:%S"))
        self.task_table.setItem(row, 4, time_item)

        # 操作
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        if task.status == "running":
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(lambda: self.cancel_task(task.id))
            actions_layout.addWidget(cancel_btn)
        elif task.status == "completed":
            open_btn = QPushButton("打开")
            open_btn.clicked.connect(lambda: self.open_output_file(task.output_path))
            actions_layout.addWidget(open_btn)

        self.task_table.setCellWidget(row, 5, actions_widget)

    def update_task_row(self, task: ExportTask):
        """更新任务行"""
        for row in range(self.task_table.rowCount()):
            item = self.task_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task.id:
                # 更新状态
                status_item = self.task_table.item(row, 1)
                status_item.setText(self.get_status_text(task.status))
                status_item.setForeground(self.get_status_color(task.status))

                # 更新进度
                progress_item = self.task_table.item(row, 2)
                progress_item.setText(f"{task.progress:.1f}%")

                # 更新文件大小
                if task.file_size > 0:
                    size_item = self.task_table.item(row, 3)
                    size_item.setText(f"{task.file_size / 1024 / 1024:.1f} MB")

                # 更新操作按钮
                self.task_table.removeCellWidget(row, 5)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)

                if task.status == "running":
                    cancel_btn = QPushButton("取消")
                    cancel_btn.clicked.connect(lambda: self.cancel_task(task.id))
                    actions_layout.addWidget(cancel_btn)
                elif task.status == "completed":
                    open_btn = QPushButton("打开")
                    open_btn.clicked.connect(lambda: self.open_output_file(task.output_path))
                    actions_layout.addWidget(open_btn)

                self.task_table.setCellWidget(row, 5, actions_widget)
                break

    def get_status_text(self, status: str) -> str:
        """获取状态文本"""
        status_map = {
            "pending": "等待中",
            "running": "导出中",
            "completed": "已完成",
            "failed": "失败",
            "cancelled": "已取消"
        }
        return status_map.get(status, status)

    def get_status_color(self, status: str) -> QColor:
        """获取状态颜色"""
        color_map = {
            "pending": QColor(128, 128, 128),
            "running": QColor(0, 150, 255),
            "completed": QColor(0, 255, 0),
            "failed": QColor(255, 0, 0),
            "cancelled": QColor(255, 128, 0)
        }
        return color_map.get(status, QColor(128, 128, 128))

    def show_task_details(self, task: ExportTask):
        """显示任务详情"""
        details = f"""
任务名称: {task.name}
任务ID: {task.id}
状态: {self.get_status_text(task.status)}
进度: {task.progress:.1f}%

源文件: {task.source_path}
输出文件: {task.output_path}

创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
        if task.started_at:
            details += f"开始时间: {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        if task.completed_at:
            details += f"完成时间: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if task.file_size > 0:
            details += f"文件大小: {task.file_size / 1024 / 1024:.1f} MB\n"

        if task.error_message:
            details += f"错误信息: {task.error_message}\n"

        # 显示设置详情
        details += f"\n导出设置:\n"
        details += f"格式: {task.settings.format.value.upper()}\n"
        details += f"分辨率: {task.settings.resolution[0]}×{task.settings.resolution[1]}\n"
        details += f"比特率: {task.settings.bitrate} kbps\n"
        details += f"帧率: {task.settings.frame_rate} fps\n"

        self.task_details.setPlainText(details)

    def cancel_task(self, task_id: str):
        """取消任务"""
        task = next((t for t in self.export_tasks if t.id == task_id), None)
        if task and task.status == "running":
            task.status = "cancelled"
            self.update_task_row(task)
            QMessageBox.information(self, "成功", "任务已取消")

    def cancel_selected_task(self):
        """取消选中的任务"""
        selected_items = self.task_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.cancel_task(task_id)

    def remove_selected_task(self):
        """移除选中的任务"""
        selected_items = self.task_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

            # 从列表中移除
            self.export_tasks = [t for t in self.export_tasks if t.id != task_id]

            # 从表格中移除
            self.task_table.removeRow(row)

            # 清空详情
            self.task_details.clear()

    def clear_completed_tasks(self):
        """清空已完成的任务"""
        # 移除已完成的任务
        self.export_tasks = [t for t in self.export_tasks if t.status not in ["completed", "failed", "cancelled"]]

        # 重新构建表格
        self.task_table.setRowCount(0)
        for task in self.export_tasks:
            self.add_task_to_table(task)

        self.task_details.clear()

    def generate_filename(self) -> str:
        """生成文件名"""
        template = self.filename_template_edit.text()

        # 替换模板变量
        replacements = {
            "{project_name}": "视频项目",
            "{date}": datetime.now().strftime("%Y%m%d"),
            "{time}": datetime.now().strftime("%H%M%S"),
            "{resolution}": f"{self.current_settings.resolution[0]}x{self.current_settings.resolution[1]}",
            "{quality}": self.current_settings.quality_preset.value
        }

        filename = template
        for key, value in replacements.items():
            filename = filename.replace(key, str(value))

        # 添加扩展名
        filename += f".{self.current_settings.format.value}"

        return filename

    def browse_output_directory(self):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def browse_watermark(self):
        """浏览水印图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.watermark_path_edit.setText(file_path)
            self.current_settings.watermark_path = file_path

    def preview_export(self):
        """预览导出"""
        QMessageBox.information(self, "预览", "导出预览功能正在开发中...")

    def save_current_preset(self):
        """保存当前设置为预设"""
        name, ok = QInputDialog.getText(
            self, "保存预设", "请输入预设名称:"
        )
        if ok and name:
            # 保存预设
            self.presets[name] = self.current_settings
            QMessageBox.information(self, "成功", f"预设 '{name}' 已保存")

    def show_preset_manager(self):
        """显示预设管理器"""
        QMessageBox.information(self, "预设管理", "预设管理功能正在开发中...")

    def show_batch_export(self):
        """显示批量导出"""
        QMessageBox.information(self, "批量导出", "批量导出功能正在开发中...")

    def show_export_history(self):
        """显示导出历史"""
        QMessageBox.information(self, "导出历史", "导出历史功能正在开发中...")

    def show_settings(self):
        """显示设置"""
        QMessageBox.information(self, "设置", "导出设置功能正在开发中...")

    def open_output_file(self, file_path: str):
        """打开输出文件"""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件: {e}")

    def load_default_settings(self):
        """加载默认设置"""
        # 应用YouTube预设作为默认设置
        self.apply_profile(ExportProfile.YOUTUBE)

        # 设置默认输出目录
        default_dir = os.path.join(os.path.expanduser("~"), "Videos", "CineAIStudio")
        os.makedirs(default_dir, exist_ok=True)
        self.output_dir_edit.setText(default_dir)
        self.current_settings.output_directory = default_dir

    def _load_presets(self) -> Dict[str, ExportSettings]:
        """加载预设"""
        presets = {
            "YouTube 高质量": ExportSettings(
                format=ExportFormat.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                resolution=(1920, 1080),
                frame_rate=30,
                bitrate=8000,
                audio_bitrate=192
            ),
            "Bilibili 推荐": ExportSettings(
                format=ExportFormat.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                resolution=(1920, 1080),
                frame_rate=30,
                bitrate=6000,
                audio_bitrate=128
            ),
            "抖音短视频": ExportSettings(
                format=ExportFormat.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                resolution=(1080, 1920),
                frame_rate=30,
                bitrate=5000,
                audio_bitrate=128
            )
        }

        return presets

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            ExportSettingsPanel {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
            }

            QToolBar {
                background-color: #2d2d30;
                border-bottom: 1px solid #3e3e42;
                spacing: 2px;
            }

            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                padding: 4px;
                margin: 1px;
            }

            QToolButton:hover {
                background-color: #3e3e42;
                border: 1px solid #5e5e62;
            }

            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background-color: #252526;
            }

            QTabBar::tab {
                background-color: #2d2d30;
                color: #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #3e3e42;
            }

            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #007acc;
            }

            QTabBar::tab:hover {
                background-color: #3e3e42;
            }

            QStatusBar {
                background-color: #2d2d30;
                border-top: 1px solid #3e3e42;
                color: #ffffff;
            }

            QGroupBox {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }

            QPushButton {
                background-color: #0e639c;
                color: white;
                border: 1px solid #007acc;
                padding: 6px 12px;
                border-radius: 3px;
                min-width: 80px;
            }

            QPushButton:hover {
                background-color: #1177bb;
            }

            QPushButton:pressed {
                background-color: #0d5487;
            }

            QPushButton#export_btn {
                background-color: #28a745;
                border: 1px solid #34ce57;
                font-weight: bold;
            }

            QPushButton#export_btn:hover {
                background-color: #34ce57;
            }

            QTextEdit, QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3e3e42;
                padding: 4px;
                selection-background-color: #007acc;
            }

            QComboBox {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
                min-width: 100px;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: #3e3e42;
                margin: 2px 0;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #007acc;
                border: 1px solid #007acc;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }

            QSpinBox {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
            }

            QCheckBox {
                color: #ffffff;
            }

            QLabel {
                color: #ffffff;
            }

            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3e3e42;
                alternate-background-color: #252526;
                gridline-color: #3e3e42;
            }

            QTableWidget::item {
                padding: 4px;
            }

            QTableWidget::item:selected {
                background-color: #007acc;
            }

            QHeaderView::section {
                background-color: #2d2d30;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #3e3e42;
            }
        """)

    def get_export_settings(self) -> ExportSettings:
        """获取当前导出设置"""
        return self.current_settings

    def set_export_settings(self, settings: ExportSettings):
        """设置导出配置"""
        self.current_settings = settings
        self.update_ui_from_settings()

    def update_ui_from_settings(self):
        """根据设置更新UI"""
        # 更新基本设置
        self.format_combo.setCurrentText(self.current_settings.format.value.upper())
        self.resolution_combo.setCurrentText(f"{self.current_settings.resolution[0]}×{self.current_settings.resolution[1]}")
        self.bitrate_slider.setValue(self.current_settings.bitrate)
        self.bitrate_spin.setValue(self.current_settings.bitrate)

        # 更新其他设置...
        self.estimate_file_size()
