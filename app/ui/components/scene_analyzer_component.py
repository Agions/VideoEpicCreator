#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业AI场景分析组件 - 支持视频内容分析、场景分割、物体识别、情感分析等功能
集成计算机视觉和NLP技术，提供智能视频分析解决方案
"""

import asyncio
import json
import time
import cv2
import numpy as np
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
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsTextItem, QColorDialog, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QRectF, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QBrush, QImage

from app.ai.enhanced_ai_manager import EnhancedAIManager
from app.ai.cost_manager import ChineseLLMCostManager, CostTier
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class AnalysisType(Enum):
    """分析类型"""
    SCENE_SEGMENTATION = "scene_segmentation"      # 场景分割
    OBJECT_DETECTION = "object_detection"          # 物体识别
    FACE_RECOGNITION = "face_recognition"          # 人脸识别
    EMOTION_ANALYSIS = "emotion_analysis"          # 情感分析
    ACTION_RECOGNITION = "action_recognition"      # 动作识别
    COLOR_ANALYSIS = "color_analysis"              # 色彩分析
    COMPOSITION_ANALYSIS = "composition_analysis"  # 构图分析
    QUALITY_ASSESSMENT = "quality_assessment"      # 质量评估


class DetectionLevel(Enum):
    """检测级别"""
    BASIC = "基础"                        # 基础检测
    DETAILED = "详细"                     # 详细检测
    PROFESSIONAL = "专业"                  # 专业检测
    EXPERT = "专家"                       # 专家检测


@dataclass
class SceneSegment:
    """场景片段"""
    start_time: float
    end_time: float
    thumbnail: np.ndarray = None
    description: str = ""
    key_objects: List[str] = None
    emotions: List[str] = None
    actions: List[str] = None
    quality_score: float = 0.0
    
    def __post_init__(self):
        if self.key_objects is None:
            self.key_objects = []
        if self.emotions is None:
            self.emotions = []
        if self.actions is None:
            self.actions = []


@dataclass
class DetectedObject:
    """检测到的物体"""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_id: str
    video_file: str
    analysis_type: AnalysisType
    scene_segments: List[SceneSegment] = None
    detected_objects: List[DetectedObject] = None
    emotion_timeline: List[Dict[str, Any]] = None
    action_timeline: List[Dict[str, Any]] = None
    color_palette: List[str] = None
    composition_score: float = 0.0
    overall_quality: float = 0.0
    recommendations: List[str] = None
    processing_time: float = 0.0
    created_at: float = None
    
    def __post_init__(self):
        if self.scene_segments is None:
            self.scene_segments = []
        if self.detected_objects is None:
            self.detected_objects = []
        if self.emotion_timeline is None:
            self.emotion_timeline = []
        if self.action_timeline is None:
            self.action_timeline = []
        if self.color_palette is None:
            self.color_palette = []
        if self.recommendations is None:
            self.recommendations = []
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class AnalysisRequest:
    """分析请求"""
    request_id: str
    video_file: str
    analysis_type: AnalysisType
    detection_level: DetectionLevel = DetectionLevel.DETAILED
    enable_face_detection: bool = True
    enable_emotion_analysis: bool = True
    enable_action_recognition: bool = True
    enable_color_analysis: bool = True
    enable_quality_assessment: bool = True
    scene_threshold: float = 0.3
    min_segment_duration: float = 2.0
    max_segment_duration: float = 30.0
    selected_model: str = "auto"
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class AISceneAnalyzer(QWidget):
    """专业AI场景分析器"""
    
    # 信号定义
    analysis_started = pyqtSignal(str)                        # 分析开始
    analysis_progress = pyqtSignal(str, float, str)           # 分析进度 (request_id, progress, status)
    analysis_completed = pyqtSignal(str, object)       # 分析完成
    analysis_error = pyqtSignal(str, str)                     # 分析错误
    scene_detected = pyqtSignal(SceneSegment)                 # 场景检测到
    object_detected = pyqtSignal(DetectedObject)               # 物体检测到
    emotion_updated = pyqtSignal(float, str)                  # 情感更新 (time, emotion)
    export_ready = pyqtSignal(str, str)                       # 导出准备完成
    
    def __init__(self, ai_manager: EnhancedAIManager, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.settings_manager = settings_manager
        self.cost_manager = ai_manager.cost_manager
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # 分析状态
        self.current_analysis: AnalysisResult = None
        self.active_requests: Dict[str, AnalysisRequest] = {}
        self.request_counter = 0
        
        # 视频处理
        self.video_capture = None
        self.video_fps = 30
        self.video_frames = []
        
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
        
        # 分析设置标签页
        settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(settings_tab, "⚙️ 分析设置")
        
        # 场景分析标签页
        scene_tab = self._create_scene_tab()
        self.tab_widget.addTab(scene_tab, "🎬 场景分析")
        
        # 物体识别标签页
        object_tab = self._create_object_tab()
        self.tab_widget.addTab(object_tab, "🔍 物体识别")
        
        # 情感分析标签页
        emotion_tab = self._create_emotion_tab()
        self.tab_widget.addTab(emotion_tab, "😊 情感分析")
        
        # 质量评估标签页
        quality_tab = self._create_quality_tab()
        self.tab_widget.addTab(quality_tab, "📊 质量评估")
        
        main_layout.addWidget(self.tab_widget)
        
        # 控制按钮区域
        control_layout = QHBoxLayout()
        
        # 预览按钮
        preview_btn = QPushButton("👁️ 视频预览")
        preview_btn.clicked.connect(self.preview_video)
        control_layout.addWidget(preview_btn)
        
        control_layout.addStretch()
        
        # 分析按钮
        self.analyze_btn = QPushButton("🚀 开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.setMinimumHeight(50)
        control_layout.addWidget(self.analyze_btn)
        
        main_layout.addLayout(control_layout)
        
        # 进度显示
        self.progress_widget = self._create_progress_widget()
        self.progress_widget.setVisible(False)
        main_layout.addWidget(self.progress_widget)
        
    def _create_settings_tab(self) -> QWidget:
        """创建分析设置标签页"""
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
        
        # 分析类型选择
        type_group = QGroupBox("分析类型")
        type_layout = QVBoxLayout(type_group)
        
        # 分析类型网格
        type_grid = QGridLayout()
        
        analysis_types = [
            ("🎬", "场景分割", AnalysisType.SCENE_SEGMENTATION),
            ("🔍", "物体识别", AnalysisType.OBJECT_DETECTION),
            ("👤", "人脸识别", AnalysisType.FACE_RECOGNITION),
            ("😊", "情感分析", AnalysisType.EMOTION_ANALYSIS),
            ("🏃", "动作识别", AnalysisType.ACTION_RECOGNITION),
            ("🎨", "色彩分析", AnalysisType.COLOR_ANALYSIS),
            ("📐", "构图分析", AnalysisType.COMPOSITION_ANALYSIS),
            ("⭐", "质量评估", AnalysisType.QUALITY_ASSESSMENT)
        ]
        
        self.analysis_checkboxes = {}
        
        for i, (icon, name, analysis_type) in enumerate(analysis_types):
            checkbox = QCheckBox(f"{icon} {name}")
            checkbox.setProperty("analysis_type", analysis_type.value)
            self.analysis_checkboxes[analysis_type] = checkbox
            type_grid.addWidget(checkbox, i // 4, i % 4)
        
        # 默认选择基础分析类型
        self.analysis_checkboxes[AnalysisType.SCENE_SEGMENTATION].setChecked(True)
        self.analysis_checkboxes[AnalysisType.OBJECT_DETECTION].setChecked(True)
        self.analysis_checkboxes[AnalysisType.EMOTION_ANALYSIS].setChecked(True)
        
        type_layout.addLayout(type_grid)
        
        # 全选/取消全选
        select_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ 全选")
        select_all_btn.clicked.connect(self.select_all_analysis_types)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("❌ 取消全选")
        select_none_btn.clicked.connect(self.select_none_analysis_types)
        select_layout.addWidget(select_none_btn)
        
        select_layout.addStretch()
        
        type_layout.addLayout(select_layout)
        
        layout.addWidget(type_group)
        
        # 检测级别
        level_group = QGroupBox("检测级别")
        level_layout = QHBoxLayout(level_group)
        
        self.level_group = QButtonGroup()
        
        for level in DetectionLevel:
            radio = QRadioButton(level.value)
            radio.setProperty("detection_level", level.value)
            self.level_group.addButton(radio)
            level_layout.addWidget(radio)
        
        # 默认选择详细检测
        self.level_group.buttons()[1].setChecked(True)
        
        layout.addWidget(level_group)
        
        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)
        
        # 场景分割阈值
        self.scene_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.scene_threshold_slider.setRange(10, 90)
        self.scene_threshold_slider.setValue(30)
        self.scene_threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.scene_threshold_label = QLabel("0.3")
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(self.scene_threshold_slider)
        threshold_layout.addWidget(self.scene_threshold_label)
        advanced_layout.addRow("场景分割阈值:", threshold_layout)
        
        # 片段时长限制
        duration_layout = QHBoxLayout()
        
        self.min_duration_spin = QDoubleSpinBox()
        self.min_duration_spin.setRange(0.5, 10.0)
        self.min_duration_spin.setValue(2.0)
        self.min_duration_spin.setSuffix(" 秒")
        duration_layout.addWidget(self.min_duration_spin)
        
        duration_layout.addWidget(QLabel(" - "))
        
        self.max_duration_spin = QDoubleSpinBox()
        self.max_duration_spin.setRange(5.0, 120.0)
        self.max_duration_spin.setValue(30.0)
        self.max_duration_spin.setSuffix(" 秒")
        duration_layout.addWidget(self.max_duration_spin)
        
        advanced_layout.addRow("片段时长:", duration_layout)
        
        # AI模型选择
        self.analysis_model_combo = QComboBox()
        self._populate_analysis_models()
        advanced_layout.addRow("AI模型:", self.analysis_model_combo)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_scene_tab(self) -> QWidget:
        """创建场景分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 场景时间轴
        timeline_group = QGroupBox("场景时间轴")
        timeline_layout = QVBoxLayout(timeline_group)
        
        self.scene_timeline = QListWidget()
        self.scene_timeline.setMaximumHeight(200)
        self.scene_timeline.itemClicked.connect(self.on_scene_selected)
        timeline_layout.addWidget(self.scene_timeline)
        
        layout.addWidget(timeline_group)
        
        # 场景详情
        detail_group = QGroupBox("场景详情")
        detail_layout = QVBoxLayout(detail_group)
        
        self.scene_detail_browser = QTextBrowser()
        self.scene_detail_browser.setMaximumHeight(200)
        detail_layout.addWidget(self.scene_detail_browser)
        
        layout.addWidget(detail_group)
        
        # 场景缩略图
        thumbnail_group = QGroupBox("场景缩略图")
        thumbnail_layout = QHBoxLayout(thumbnail_group)
        
        self.prev_scene_btn = QPushButton("⬅️ 上一个")
        self.prev_scene_btn.clicked.connect(self.prev_scene)
        thumbnail_layout.addWidget(self.prev_scene_btn)
        
        self.scene_thumbnail = QLabel()
        self.scene_thumbnail.setMinimumSize(320, 180)
        self.scene_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scene_thumbnail.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        thumbnail_layout.addWidget(self.scene_thumbnail)
        
        self.next_scene_btn = QPushButton("下一个 ➡️")
        self.next_scene_btn.clicked.connect(self.next_scene)
        thumbnail_layout.addWidget(self.next_scene_btn)
        
        layout.addWidget(thumbnail_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_object_tab(self) -> QWidget:
        """创建物体识别标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 物体检测视图
        detection_group = QGroupBox("物体检测")
        detection_layout = QVBoxLayout(detection_group)
        
        # 图形视图
        self.detection_view = QGraphicsView()
        self.detection_scene = QGraphicsScene()
        self.detection_view.setScene(self.detection_scene)
        self.detection_view.setMinimumHeight(300)
        detection_layout.addWidget(self.detection_view)
        
        layout.addWidget(detection_group)
        
        # 检测结果列表
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout(result_group)
        
        self.object_list = QListWidget()
        self.object_list.setMaximumHeight(200)
        self.object_list.itemClicked.connect(self.on_object_selected)
        result_layout.addWidget(self.object_list)
        
        layout.addWidget(result_group)
        
        # 物体统计
        stats_group = QGroupBox("物体统计")
        stats_layout = QFormLayout(stats_group)
        
        self.total_objects_label = QLabel("0")
        stats_layout.addRow("检测到的物体总数:", self.total_objects_label)
        
        self.unique_objects_label = QLabel("0")
        stats_layout.addRow("物体类别数:", self.unique_objects_label)
        
        self.confidence_avg_label = QLabel("0%")
        stats_layout.addRow("平均置信度:", self.confidence_avg_label)
        
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_emotion_tab(self) -> QWidget:
        """创建情感分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 情感时间轴
        emotion_timeline_group = QGroupBox("情感时间轴")
        emotion_timeline_layout = QVBoxLayout(emotion_timeline_group)
        
        self.emotion_chart = QWidget()
        self.emotion_chart.setMinimumHeight(200)
        self.emotion_chart.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        emotion_timeline_layout.addWidget(self.emotion_chart)
        
        layout.addWidget(emotion_timeline_group)
        
        # 情感统计
        emotion_stats_group = QGroupBox("情感统计")
        emotion_stats_layout = QGridLayout(emotion_stats_group)
        
        # 情感类型
        emotions = ["开心", "悲伤", "愤怒", "惊讶", "恐惧", "厌恶", "中性"]
        self.emotion_bars = {}
        
        for i, emotion in enumerate(emotions):
            label = QLabel(f"{emotion}:")
            emotion_stats_layout.addWidget(label, i, 0)
            
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            emotion_stats_layout.addWidget(bar, i, 1)
            
            value_label = QLabel("0%")
            emotion_stats_layout.addWidget(value_label, i, 2)
            
            self.emotion_bars[emotion] = {"bar": bar, "label": value_label}
        
        layout.addWidget(emotion_stats_group)
        
        # 情感详情
        emotion_detail_group = QGroupBox("情感详情")
        emotion_detail_layout = QVBoxLayout(emotion_detail_group)
        
        self.emotion_detail_browser = QTextBrowser()
        self.emotion_detail_browser.setMaximumHeight(150)
        emotion_detail_layout.addWidget(self.emotion_detail_browser)
        
        layout.addWidget(emotion_detail_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_quality_tab(self) -> QWidget:
        """创建质量评估标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 整体质量评分
        overall_group = QGroupBox("整体质量评分")
        overall_layout = QVBoxLayout(overall_group)
        
        self.quality_score_display = QLabel("等待分析...")
        self.quality_score_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quality_score_display.setStyleSheet("font-size: 48px; font-weight: bold; color: #2196F3;")
        overall_layout.addWidget(self.quality_score_display)
        
        self.quality_description = QLabel("请先进行视频分析")
        self.quality_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quality_description.setWordWrap(True)
        overall_layout.addWidget(self.quality_description)
        
        layout.addWidget(overall_group)
        
        # 质量指标
        metrics_group = QGroupBox("质量指标")
        metrics_layout = QFormLayout(metrics_group)
        
        # 各种质量指标
        self.brightness_score = QProgressBar()
        self.brightness_score.setRange(0, 100)
        metrics_layout.addRow("亮度评分:", self.brightness_score)
        
        self.contrast_score = QProgressBar()
        self.contrast_score.setRange(0, 100)
        metrics_layout.addRow("对比度评分:", self.contrast_score)
        
        self.sharpness_score = QProgressBar()
        self.sharpness_score.setRange(0, 100)
        metrics_layout.addRow("清晰度评分:", self.sharpness_score)
        
        self.stability_score = QProgressBar()
        self.stability_score.setRange(0, 100)
        metrics_layout.addRow("稳定性评分:", self.stability_score)
        
        self.composition_score = QProgressBar()
        self.composition_score.setRange(0, 100)
        metrics_layout.addRow("构图评分:", self.composition_score)
        
        self.audio_quality_score = QProgressBar()
        self.audio_quality_score.setRange(0, 100)
        metrics_layout.addRow("音频质量:", self.audio_quality_score)
        
        layout.addWidget(metrics_group)
        
        # 改进建议
        recommendations_group = QGroupBox("改进建议")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QListWidget()
        self.recommendations_list.setMaximumHeight(200)
        recommendations_layout.addWidget(self.recommendations_list)
        
        layout.addWidget(recommendations_group)
        
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
        
        # 取消按钮
        cancel_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("❌ 取消分析")
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        cancel_layout.addWidget(self.cancel_btn)
        
        cancel_layout.addStretch()
        
        layout.addLayout(cancel_layout)
        
        return widget
    
    def _populate_analysis_models(self):
        """填充分析模型下拉框"""
        self.analysis_model_combo.clear()
        self.analysis_model_combo.addItem("🤖 自动选择", "auto")
        
        # 添加支持的分析模型
        analysis_models = [
            ("qianwen", "通义千问"),
            ("zhipu", "智谱AI"),
            ("hunyuan", "腾讯混元"),
            ("deepseek", "DeepSeek")
        ]
        
        for model_id, model_name in analysis_models:
            self.analysis_model_combo.addItem(model_name, model_id)
    
    def _connect_signals(self):
        """连接信号"""
        # 场景阈值滑块
        self.scene_threshold_slider.valueChanged.connect(self.on_scene_threshold_changed)
        
        # AI管理器信号
        self.ai_manager.model_response_ready.connect(self.on_ai_response)
        
        # 标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def on_scene_threshold_changed(self, value):
        """场景阈值变更"""
        threshold = value / 100.0
        self.scene_threshold_label.setText(f"{threshold:.1f}")
    
    def on_tab_changed(self, index):
        """标签页切换"""
        # 当切换到不同标签页时，更新相应的显示内容
        self.update_tab_content(index)
    
    def update_tab_content(self, tab_index):
        """更新标签页内容"""
        if not self.current_analysis:
            return
        
        if tab_index == 1:  # 场景分析
            self.update_scene_analysis()
        elif tab_index == 2:  # 物体识别
            self.update_object_detection()
        elif tab_index == 3:  # 情感分析
            self.update_emotion_analysis()
        elif tab_index == 4:  # 质量评估
            self.update_quality_assessment()
    
    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm)"
        )
        if file_path:
            self.video_file_input.setText(file_path)
            self.load_video_info(file_path)
    
    def load_video_info(self, file_path):
        """加载视频信息"""
        try:
            self.video_capture = cv2.VideoCapture(file_path)
            if self.video_capture.isOpened():
                self.video_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / self.video_fps
                
                QMessageBox.information(self, "视频信息", 
                                      f"文件: {file_path}\n"
                                      f"帧率: {self.video_fps:.2f} fps\n"
                                      f"总帧数: {total_frames}\n"
                                      f"时长: {duration:.2f} 秒")
            else:
                QMessageBox.warning(self, "警告", "无法打开视频文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载视频失败: {str(e)}")
    
    def select_all_analysis_types(self):
        """选择所有分析类型"""
        for checkbox in self.analysis_checkboxes.values():
            checkbox.setChecked(True)
    
    def select_none_analysis_types(self):
        """取消选择所有分析类型"""
        for checkbox in self.analysis_checkboxes.values():
            checkbox.setChecked(False)
    
    def start_analysis(self):
        """开始分析"""
        if not self.video_file_input.text():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return
        
        # 检查是否选择了分析类型
        selected_types = [analysis_type for analysis_type, checkbox in self.analysis_checkboxes.items() if checkbox.isChecked()]
        if not selected_types:
            QMessageBox.warning(self, "警告", "请至少选择一种分析类型")
            return
        
        # 创建分析请求
        request = self.create_analysis_request(selected_types)
        self.active_requests[request.request_id] = request
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在分析视频...")
        self.analyze_btn.setEnabled(False)
        
        # 发送信号
        self.analysis_started.emit(request.request_id)
        
        # 开始分析
        asyncio.create_task(self.execute_analysis(request))
    
    def create_analysis_request(self, selected_types: List[AnalysisType]) -> AnalysisRequest:
        """创建分析请求"""
        # 使用第一个选中的分析类型作为主要类型
        primary_type = selected_types[0]
        
        return AnalysisRequest(
            request_id=f"analysis_{self.request_counter}",
            video_file=self.video_file_input.text(),
            analysis_type=primary_type,
            detection_level=DetectionLevel(self.level_group.checkedButton().property("detection_level")),
            enable_face_detection=AnalysisType.FACE_RECOGNITION in selected_types,
            enable_emotion_analysis=AnalysisType.EMOTION_ANALYSIS in selected_types,
            enable_action_recognition=AnalysisType.ACTION_RECOGNITION in selected_types,
            enable_color_analysis=AnalysisType.COLOR_ANALYSIS in selected_types,
            enable_quality_assessment=AnalysisType.QUALITY_ASSESSMENT in selected_types,
            scene_threshold=self.scene_threshold_slider.value() / 100.0,
            min_segment_duration=self.min_duration_spin.value(),
            max_segment_duration=self.max_duration_spin.value(),
            selected_model=self.analysis_model_combo.currentData()
        )
    
    async def execute_analysis(self, request: AnalysisRequest):
        """执行分析"""
        try:
            start_time = time.time()
            
            # 创建分析结果
            self.current_analysis = AnalysisResult(
                analysis_id=request.request_id,
                video_file=request.video_file,
                analysis_type=request.analysis_type
            )
            
            # 场景分割分析
            if request.analysis_type == AnalysisType.SCENE_SEGMENTATION:
                await self.analyze_scene_segments(request)
            
            # 物体识别分析
            if request.enable_face_detection or request.analysis_type == AnalysisType.OBJECT_DETECTION:
                await self.analyze_objects(request)
            
            # 情感分析
            if request.enable_emotion_analysis:
                await self.analyze_emotions(request)
            
            # 动作识别
            if request.enable_action_recognition:
                await self.analyze_actions(request)
            
            # 色彩分析
            if request.enable_color_analysis:
                await self.analyze_colors(request)
            
            # 质量评估
            if request.enable_quality_assessment:
                await self.assess_quality(request)
            
            # 计算处理时间
            self.current_analysis.processing_time = time.time() - start_time
            
            # 更新UI
            self.update_analysis_results()
            
            self.progress_bar.setValue(100)
            self.status_label.setText("分析完成")
            
            # 发送信号
            self.analysis_completed.emit(request.request_id, self.current_analysis)
            
        except Exception as e:
            self.analysis_error.emit(request.request_id, str(e))
            self.status_label.setText(f"分析失败: {str(e)}")
            
        finally:
            # 清理请求
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            # 恢复按钮状态
            self.analyze_btn.setEnabled(True)
            
            # 隐藏进度条（延迟）
            QTimer.singleShot(3000, lambda: self.progress_widget.setVisible(False))
    
    async def analyze_scene_segments(self, request: AnalysisRequest):
        """分析场景片段"""
        self.analysis_progress.emit(request.request_id, 10.0, "正在分析场景片段...")
        
        # 模拟场景分割分析
        await asyncio.sleep(1)
        
        # 生成示例场景片段
        scene_segments = []
        
        # 假设视频时长为60秒
        video_duration = 60.0
        current_time = 0.0
        
        scene_descriptions = [
            "开场介绍，主持人出镜",
            "主要内容讲解，产品展示",
            "用户访谈，实际应用场景",
            "技术演示，功能介绍",
            "总结回顾，感谢观看"
        ]
        
        for i, description in enumerate(scene_descriptions):
            segment_duration = min(12.0, video_duration - current_time)
            
            segment = SceneSegment(
                start_time=current_time,
                end_time=current_time + segment_duration,
                description=description,
                key_objects=["人物", "背景"],
                emotions=["中性"],
                actions=["说话", "手势"],
                quality_score=0.8 + (i * 0.05)
            )
            
            scene_segments.append(segment)
            current_time += segment_duration
        
        self.current_analysis.scene_segments = scene_segments
        
        # 更新场景时间轴
        self.update_scene_timeline(scene_segments)
        
        self.analysis_progress.emit(request.request_id, 30.0, "场景片段分析完成")
    
    async def analyze_objects(self, request: AnalysisRequest):
        """分析物体识别"""
        self.analysis_progress.emit(request.request_id, 35.0, "正在识别物体...")
        
        await asyncio.sleep(1)
        
        # 生成示例物体检测结果
        detected_objects = [
            DetectedObject(
                label="人物",
                confidence=0.95,
                bbox=(100, 50, 200, 300),
                attributes={"gender": "未知", "age_range": "成人"}
            ),
            DetectedObject(
                label="桌子",
                confidence=0.88,
                bbox=(50, 250, 400, 100),
                attributes={"material": "木质", "color": "棕色"}
            ),
            DetectedObject(
                label="电脑",
                confidence=0.92,
                bbox=(150, 200, 150, 100),
                attributes={"type": "笔记本", "brand": "未知"}
            ),
            DetectedObject(
                label="书籍",
                confidence=0.76,
                bbox=(300, 220, 80, 60),
                attributes={"count": "3", "category": "技术"}
            )
        ]
        
        self.current_analysis.detected_objects = detected_objects
        
        # 更新物体检测显示
        self.update_object_detection_display(detected_objects)
        
        self.analysis_progress.emit(request.request_id, 50.0, "物体识别完成")
    
    async def analyze_emotions(self, request: AnalysisRequest):
        """分析情感"""
        self.analysis_progress.emit(request.request_id, 55.0, "正在分析情感...")
        
        await asyncio.sleep(1)
        
        # 生成示例情感分析结果
        emotion_timeline = []
        
        # 假设60秒视频，每5秒分析一次
        for i in range(0, 60, 5):
            emotions = {
                "开心": 0.6 + (i * 0.01),
                "中性": 0.3 - (i * 0.005),
                "惊讶": 0.1 + (i * 0.002)
            }
            
            emotion_timeline.append({
                "time": i,
                "emotions": emotions,
                "dominant_emotion": max(emotions, key=emotions.get)
            })
        
        self.current_analysis.emotion_timeline = emotion_timeline
        
        # 更新情感分析显示
        self.update_emotion_analysis_display(emotion_timeline)
        
        self.analysis_progress.emit(request.request_id, 70.0, "情感分析完成")
    
    async def analyze_actions(self, request: AnalysisRequest):
        """分析动作识别"""
        self.analysis_progress.emit(request.request_id, 75.0, "正在识别动作...")
        
        await asyncio.sleep(0.5)
        
        # 生成示例动作识别结果
        action_timeline = [
            {"time": 0, "action": "站立", "confidence": 0.9},
            {"time": 5, "action": "说话", "confidence": 0.95},
            {"time": 15, "action": "手势", "confidence": 0.88},
            {"time": 25, "action": "指向", "confidence": 0.82},
            {"time": 35, "action": "操作", "confidence": 0.91},
            {"time": 45, "action": "微笑", "confidence": 0.87}
        ]
        
        self.current_analysis.action_timeline = action_timeline
        
        self.analysis_progress.emit(request.request_id, 80.0, "动作识别完成")
    
    async def analyze_colors(self, request: AnalysisRequest):
        """分析色彩"""
        self.analysis_progress.emit(request.request_id, 85.0, "正在分析色彩...")
        
        await asyncio.sleep(0.5)
        
        # 生成示例色彩分析结果
        color_palette = [
            "#2C3E50",  # 深蓝灰
            "#3498DB",  # 蓝色
            "#E74C3C",  # 红色
            "#F39C12",  # 橙色
            "#27AE60"   # 绿色
        ]
        
        self.current_analysis.color_palette = color_palette
        
        self.analysis_progress.emit(request.request_id, 90.0, "色彩分析完成")
    
    async def assess_quality(self, request: AnalysisRequest):
        """评估质量"""
        self.analysis_progress.emit(request.request_id, 92.0, "正在评估质量...")
        
        await asyncio.sleep(0.8)
        
        # 生成示例质量评估结果
        quality_scores = {
            "brightness": 85,
            "contrast": 78,
            "sharpness": 82,
            "stability": 90,
            "composition": 75,
            "audio_quality": 88
        }
        
        overall_quality = sum(quality_scores.values()) / len(quality_scores)
        
        self.current_analysis.overall_quality = overall_quality
        
        # 生成改进建议
        recommendations = [
            "建议提高视频对比度，增强画面层次感",
            "可以优化构图，遵循三分法则",
            "建议使用更稳定的拍摄设备",
            "考虑增加背景音乐提升整体质量"
        ]
        
        self.current_analysis.recommendations = recommendations
        
        # 更新质量评估显示
        self.update_quality_assessment_display(quality_scores, overall_quality, recommendations)
        
        self.analysis_progress.emit(request.request_id, 100.0, "质量评估完成")
    
    def update_analysis_results(self):
        """更新分析结果显示"""
        if not self.current_analysis:
            return
        
        # 更新当前标签页的内容
        current_tab = self.tab_widget.currentIndex()
        self.update_tab_content(current_tab)
    
    def update_scene_timeline(self, scene_segments: List[SceneSegment]):
        """更新场景时间轴"""
        self.scene_timeline.clear()
        
        for i, segment in enumerate(scene_segments):
            start_time_str = self._format_time_for_display(segment.start_time)
            end_time_str = self._format_time_for_display(segment.end_time)
            duration = segment.end_time - segment.start_time
            
            item_text = f"{i+1:02d}. {start_time_str} - {end_time_str} ({duration:.1f}s) {segment.description}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, segment)
            self.scene_timeline.addItem(item)
    
    def update_object_detection_display(self, detected_objects: List[DetectedObject]):
        """更新物体检测显示"""
        # 清空场景
        self.detection_scene.clear()
        
        # 添加背景图片（示例）
        background_rect = QGraphicsRectItem(0, 0, 640, 480)
        background_rect.setBrush(QBrush(QColor(240, 240, 240)))
        self.detection_scene.addItem(background_rect)
        
        # 绘制检测框
        for obj in detected_objects:
            x, y, w, h = obj.bbox
            
            # 绘制边界框
            rect_item = QGraphicsRectItem(x, y, w, h)
            rect_item.setPen(QPen(QColor(255, 0, 0), 2))
            self.detection_scene.addItem(rect_item)
            
            # 添加标签
            label_text = f"{obj.label} ({obj.confidence:.0%})"
            label_item = QGraphicsTextItem(label_text)
            label_item.setPos(x, y - 20)
            label_item.setDefaultTextColor(QColor(255, 0, 0))
            self.detection_scene.addItem(label_item)
        
        # 更新物体列表
        self.object_list.clear()
        
        for obj in detected_objects:
            item_text = f"{obj.label} - 置信度: {obj.confidence:.0%}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, obj)
            self.object_list.addItem(item)
        
        # 更新统计信息
        self.total_objects_label.setText(str(len(detected_objects)))
        
        unique_objects = len(set(obj.label for obj in detected_objects))
        self.unique_objects_label.setText(str(unique_objects))
        
        avg_confidence = sum(obj.confidence for obj in detected_objects) / len(detected_objects)
        self.confidence_avg_label.setText(f"{avg_confidence:.0%}")
    
    def update_emotion_analysis_display(self, emotion_timeline: List[Dict[str, Any]]):
        """更新情感分析显示"""
        if not emotion_timeline:
            return
        
        # 计算情感统计
        emotion_totals = {}
        emotion_counts = {}
        
        for entry in emotion_timeline:
            emotions = entry["emotions"]
            for emotion, score in emotions.items():
                if emotion not in emotion_totals:
                    emotion_totals[emotion] = 0
                    emotion_counts[emotion] = 0
                emotion_totals[emotion] += score
                emotion_counts[emotion] += 1
        
        # 更新情感条形图
        for emotion, data in self.emotion_bars.items():
            if emotion in emotion_totals:
                avg_score = emotion_totals[emotion] / emotion_counts[emotion]
                percentage = avg_score * 100
                data["bar"].setValue(int(percentage))
                data["label"].setText(f"{percentage:.0f}%")
            else:
                data["bar"].setValue(0)
                data["label"].setText("0%")
        
        # 更新情感详情
        detail_text = "<h3>情感分析详情</h3>"
        for emotion, data in self.emotion_bars.items():
            if emotion in emotion_totals:
                avg_score = emotion_totals[emotion] / emotion_counts[emotion]
                detail_text += f"<p><b>{emotion}:</b> 平均强度 {avg_score:.2f}</p>"
        
        self.emotion_detail_browser.setHtml(detail_text)
    
    def update_quality_assessment_display(self, quality_scores: Dict[str, float], 
                                       overall_quality: float, recommendations: List[str]):
        """更新质量评估显示"""
        # 更新整体评分
        self.quality_score_display.setText(f"{overall_quality:.0f}")
        
        # 更新评分描述
        if overall_quality >= 90:
            description = "优秀 - 视频质量很高，建议保持当前标准"
        elif overall_quality >= 80:
            description = "良好 - 视频质量较好，有少量改进空间"
        elif overall_quality >= 70:
            description = "一般 - 视频质量中等，建议进行一些优化"
        elif overall_quality >= 60:
            description = "需改进 - 视频质量有待提升"
        else:
            description = "较差 - 视频质量需要大幅改进"
        
        self.quality_description.setText(description)
        
        # 更新各项指标
        self.brightness_score.setValue(int(quality_scores.get("brightness", 0)))
        self.contrast_score.setValue(int(quality_scores.get("contrast", 0)))
        self.sharpness_score.setValue(int(quality_scores.get("sharpness", 0)))
        self.stability_score.setValue(int(quality_scores.get("stability", 0)))
        self.composition_score.setValue(int(quality_scores.get("composition", 0)))
        self.audio_quality_score.setValue(int(quality_scores.get("audio_quality", 0)))
        
        # 更新改进建议
        self.recommendations_list.clear()
        for recommendation in recommendations:
            self.recommendations_list.addItem(recommendation)
    
    def on_scene_selected(self, item):
        """场景选择事件"""
        segment = item.data(Qt.ItemDataRole.UserRole)
        if segment:
            self.display_scene_details(segment)
    
    def display_scene_details(self, segment: SceneSegment):
        """显示场景详情"""
        detail_html = f"""
        <h3>场景详情</h3>
        <p><b>时间:</b> {self._format_time_for_display(segment.start_time)} - {self._format_time_for_display(segment.end_time)}</p>
        <p><b>时长:</b> {segment.end_time - segment.start_time:.1f} 秒</p>
        <p><b>描述:</b> {segment.description}</p>
        <p><b>关键物体:</b> {', '.join(segment.key_objects)}</p>
        <p><b>情感:</b> {', '.join(segment.emotions)}</p>
        <p><b>动作:</b> {', '.join(segment.actions)}</p>
        <p><b>质量评分:</b> {segment.quality_score:.2f}</p>
        """
        
        self.scene_detail_browser.setHtml(detail_html)
        
        # 显示缩略图（示例）
        self.scene_thumbnail.setText("场景缩略图\n(示例)")
    
    def on_object_selected(self, item):
        """物体选择事件"""
        obj = item.data(Qt.ItemDataRole.UserRole)
        if obj:
            self.highlight_object(obj)
    
    def highlight_object(self, obj: DetectedObject):
        """高亮显示物体"""
        # 在图形视图中高亮显示选中的物体
        for item in self.detection_scene.items():
            if isinstance(item, QGraphicsRectItem):
                x, y, w, h = obj.bbox
                if item.rect() == QRectF(x, y, w, h):
                    item.setPen(QPen(QColor(0, 255, 0), 3))
                else:
                    item.setPen(QPen(QColor(255, 0, 0), 2))
    
    def prev_scene(self):
        """上一个场景"""
        current_row = self.scene_timeline.currentRow()
        if current_row > 0:
            self.scene_timeline.setCurrentRow(current_row - 1)
    
    def next_scene(self):
        """下一个场景"""
        current_row = self.scene_timeline.currentRow()
        if current_row < self.scene_timeline.count() - 1:
            self.scene_timeline.setCurrentRow(current_row + 1)
    
    def preview_video(self):
        """预览视频"""
        if not self.video_file_input.text():
            QMessageBox.warning(self, "警告", "请先选择视频文件")
            return
        
        # 这里应该调用视频预览功能
        QMessageBox.information(self, "视频预览", "视频预览功能需要集成视频播放器")
    
    def cancel_analysis(self):
        """取消分析"""
        # 取消所有活跃的分析请求
        for request_id in list(self.active_requests.keys()):
            self.analysis_error.emit(request_id, "用户取消")
        
        self.active_requests.clear()
        self.progress_widget.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.status_label.setText("分析已取消")
    
    def export_analysis_results(self):
        """导出分析结果"""
        if not self.current_analysis:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果")
            return
        
        # 选择导出格式
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析结果", "", 
            "JSON文件 (*.json);;PDF报告 (*.pdf);;CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # 生成导出数据
            export_data = {
                "analysis_id": self.current_analysis.analysis_id,
                "video_file": self.current_analysis.video_file,
                "analysis_type": self.current_analysis.analysis_type.value,
                "created_at": self.current_analysis.created_at,
                "processing_time": self.current_analysis.processing_time,
                "overall_quality": self.current_analysis.overall_quality,
                "scene_segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "description": seg.description,
                        "quality_score": seg.quality_score
                    }
                    for seg in self.current_analysis.scene_segments
                ],
                "detected_objects": [
                    {
                        "label": obj.label,
                        "confidence": obj.confidence,
                        "bbox": obj.bbox
                    }
                    for obj in self.current_analysis.detected_objects
                ],
                "recommendations": self.current_analysis.recommendations
            }
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.export_ready.emit(file_path, "json")
            QMessageBox.information(self, "成功", f"分析结果已导出到：{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")
    
    def _format_time_for_display(self, seconds: float) -> str:
        """格式化时间用于显示"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def on_ai_response(self, model_provider, response):
        """AI响应处理"""
        if response.success:
            print(f"AI响应成功: {model_provider}")
        else:
            print(f"AI响应失败: {model_provider} - {response.error_message}")
    
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("scene_analyzer", {})
        
        # 应用设置
        if "default_detection_level" in settings:
            level = settings["default_detection_level"]
            for button in self.level_group.buttons():
                if button.property("detection_level") == level:
                    button.setChecked(True)
                    break
        
        if "scene_threshold" in settings:
            threshold = int(settings["scene_threshold"] * 100)
            self.scene_threshold_slider.setValue(threshold)
    
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_detection_level": self.level_group.checkedButton().property("detection_level"),
            "scene_threshold": self.scene_threshold_slider.value() / 100.0
        }
        
        self.settings_manager.set_setting("scene_analyzer", settings)
    
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        
        # 释放视频资源
        if self.video_capture:
            self.video_capture.release()
        
        super().closeEvent(event)