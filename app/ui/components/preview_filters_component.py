#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
预览滤镜组件 - 专业视频滤镜和效果控制
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import queue

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QToolButton, QSlider, QComboBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QCheckBox, QFrame, QSpacerItem,
    QSizePolicy, QProgressBar, QMenu, QWidgetAction, QDialog,
    QDialogButtonBox, QScrollArea, QSplitter, QListWidget,
    QListWidgetItem, QTabWidget, QStackedWidget, QRadioButton,
    QButtonGroup, QSlider, QDial, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPointF, QRect, QThread
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont,
    QPalette, QLinearGradient, QRadialGradient, QPainterPath,
    QCursor, QFontMetrics, QWheelEvent, QMouseEvent, QPaintEvent,
    QTransform, QPolygonF
)


class FilterType(Enum):
    """滤镜类型"""
    # 基础滤镜
    NONE = "none"
    BLUR = "blur"
    SHARPEN = "sharpen"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    HUE = "hue"
    GAMMA = "gamma"
    
    # 颜色滤镜
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"
    VINTAGE = "vintage"
    COLD = "cold"
    WARM = "warm"
    BLACK_WHITE = "black_white"
    
    # 特效滤镜
    EDGE_DETECT = "edge_detect"
    EMBOSS = "emboss"
    OIL_PAINTING = "oil_painting"
    SKETCH = "sketch"
    CARTOON = "cartoon"
    NIGHT_VISION = "night_vision"
    THERMAL = "thermal"
    
    # 模糊效果
    GAUSSIAN_BLUR = "gaussian_blur"
    MOTION_BLUR = "motion_blur"
    RADIAL_BLUR = "radial_blur"
    BOX_BLUR = "box_blur"
    
    # 锐化效果
    UNSHARP_MASK = "unsharp_mask"
    HIGH_PASS = "high_pass"
    LAPLACIAN = "laplacian"
    
    # 噪点处理
    DENOISE = "denoise"
    ADD_NOISE = "add_noise"
    SALT_PEPPER = "salt_pepper"


class FilterPreset(Enum):
    """滤镜预设"""
    CINEMATIC = "cinematic"
    DRAMATIC = "dramatic"
    VIBRANT = "vibrant"
    NATURAL = "natural"
    SOFT = "soft"
    HARD = "hard"
    RETRO = "retro"
    FUTURISTIC = "futuristic"


@dataclass
class FilterParameters:
    """滤镜参数"""
    intensity: float = 1.0
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue: float = 0.0
    gamma: float = 1.0
    blur_radius: int = 5
    sharpen_amount: float = 1.0
    noise_level: float = 0.0
    custom_params: Dict[str, Any] = None


@dataclass
class FilterChain:
    """滤镜链"""
    name: str
    filters: List[Tuple[FilterType, FilterParameters]]
    enabled: bool = True


class RealTimeFilterProcessor(QThread):
    """实时滤镜处理器"""
    
    filter_processed = pyqtSignal(object, object)  # frame, filter_chain
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.input_queue = queue.Queue(maxsize=10)
        self.filter_chains = []
        self.processing_time = 0.0
    
    def add_filter_chain(self, chain: FilterChain):
        """添加滤镜链"""
        self.filter_chains.append(chain)
    
    def remove_filter_chain(self, chain_name: str):
        """移除滤镜链"""
        self.filter_chains = [c for c in self.filter_chains if c.name != chain_name]
    
    def process_frame(self, frame: np.ndarray):
        """处理帧"""
        try:
            self.input_queue.put_nowait(frame)
        except queue.Full:
            pass  # 丢弃帧以避免阻塞
    
    def run(self):
        """运行处理线程"""
        self.running = True
        
        while self.running:
            try:
                # 获取输入帧
                frame = self.input_queue.get(timeout=0.1)
                
                if frame is None:
                    break
                
                start_time = cv2.getTickCount()
                
                # 应用滤镜链
                processed_frame = frame.copy()
                for chain in self.filter_chains:
                    if chain.enabled:
                        processed_frame = self._apply_filter_chain(processed_frame, chain)
                
                # 计算处理时间
                self.processing_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
                
                # 发射处理结果
                self.filter_processed.emit(processed_frame, self.filter_chains)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"滤镜处理错误: {e}")
    
    def _apply_filter_chain(self, frame: np.ndarray, chain: FilterChain) -> np.ndarray:
        """应用滤镜链"""
        result = frame.copy()
        
        for filter_type, params in chain.filters:
            result = self._apply_single_filter(result, filter_type, params)
        
        return result
    
    def _apply_single_filter(self, frame: np.ndarray, filter_type: FilterType, params: FilterParameters) -> np.ndarray:
        """应用单个滤镜"""
        try:
            if filter_type == FilterType.NONE:
                return frame
            
            elif filter_type == FilterType.BLUR:
                return cv2.GaussianBlur(frame, (params.blur_radius*2+1, params.blur_radius*2+1), 0)
            
            elif filter_type == FilterType.SHARPEN:
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * params.sharpen_amount
                return cv2.filter2D(frame, -1, kernel)
            
            elif filter_type == FilterType.BRIGHTNESS:
                return cv2.convertScaleAbs(frame, alpha=params.brightness, beta=0)
            
            elif filter_type == FilterType.CONTRAST:
                return cv2.convertScaleAbs(frame, alpha=params.contrast, beta=0)
            
            elif filter_type == FilterType.SATURATION:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], params.saturation)
                return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            elif filter_type == FilterType.HUE:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hsv[:, :, 0] = cv2.add(hsv[:, :, 0], params.hue * 180)
                return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            elif filter_type == FilterType.GRAYSCALE:
                return cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            
            elif filter_type == FilterType.SEPIA:
                sepia_kernel = np.array([
                    [0.272, 0.534, 0.131],
                    [0.349, 0.686, 0.168],
                    [0.393, 0.769, 0.189]
                ])
                return cv2.transform(frame, sepia_kernel)
            
            elif filter_type == FilterType.INVERT:
                return cv2.bitwise_not(frame)
            
            elif filter_type == FilterType.EDGE_DETECT:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            
            elif filter_type == FilterType.EMBOSS:
                kernel = np.array([
                    [-2, -1, 0],
                    [-1, 1, 1],
                    [0, 1, 2]
                ])
                return cv2.filter2D(frame, -1, kernel)
            
            elif filter_type == FilterType.VINTAGE:
                # 复古效果
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, s, v = cv2.split(cv2.cvtColor(frame, cv2.COLOR_RGB2HSV))
                s = s * 0.8  # 降低饱和度
                v = v * 1.2  # 提高亮度
                frame = cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2RGB)
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            elif filter_type == FilterType.COLD:
                # 冷色调
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame[:, :, 0] = np.minimum(255, frame[:, :, 0] * 1.2)  # 增强蓝色
                frame[:, :, 1] = frame[:, :, 1] * 0.9  # 降低绿色
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            elif filter_type == FilterType.WARM:
                # 暖色调
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame[:, :, 0] = frame[:, :, 0] * 0.8  # 降低蓝色
                frame[:, :, 1] = np.minimum(255, frame[:, :, 1] * 1.1)  # 增强绿色
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            elif filter_type == FilterType.ADD_NOISE:
                noise = np.random.normal(0, params.noise_level * 255, frame.shape).astype(np.int16)
                noisy_frame = frame.astype(np.int16) + noise
                return np.clip(noisy_frame, 0, 255).astype(np.uint8)
            
            # 更多滤镜实现...
            
        except Exception as e:
            print(f"滤镜应用错误 {filter_type}: {e}")
            return frame
        
        return frame
    
    def stop(self):
        """停止处理"""
        self.running = False
        self.input_queue.put(None)  # 发送停止信号
        self.wait()


class FilterPreviewWidget(QWidget):
    """滤镜预览组件"""
    
    filter_selected = pyqtSignal(FilterType, FilterParameters)
    preset_selected = pyqtSignal(FilterPreset)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_filter = FilterType.NONE
        self.current_params = FilterParameters()
        self.preview_processor = RealTimeFilterProcessor()
        self.preview_processor.filter_processed.connect(self._on_filter_processed)
        self.preview_processor.start()
        
        self.init_ui()
        self.setup_presets()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滤镜选择面板
        filter_panel = self._create_filter_panel()
        main_layout.addWidget(filter_panel, 1)
        
        # 参数控制面板
        params_panel = self._create_params_panel()
        main_layout.addWidget(params_panel, 2)
        
        # 预设面板
        preset_panel = self._create_preset_panel()
        main_layout.addWidget(preset_panel, 1)
    
    def _create_filter_panel(self) -> QWidget:
        """创建滤镜选择面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 滤镜分类
        category_group = QGroupBox("滤镜分类")
        category_layout = QVBoxLayout(category_group)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "基础滤镜", "颜色滤镜", "特效滤镜", 
            "模糊效果", "锐化效果", "噪点处理"
        ])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        category_layout.addWidget(self.category_combo)
        
        layout.addWidget(category_group)
        
        # 滤镜列表
        filter_group = QGroupBox("滤镜列表")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_list = QListWidget()
        self.filter_list.itemDoubleClicked.connect(self._on_filter_selected)
        filter_layout.addWidget(self.filter_list)
        
        layout.addWidget(filter_group)
        
        # 搜索框
        search_group = QGroupBox("搜索")
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索滤镜...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_group)
        
        # 初始化滤镜列表
        self._update_filter_list()
        
        return panel
    
    def _create_params_panel(self) -> QWidget:
        """创建参数控制面板"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(10, 10, 10, 10)
        params_layout.setSpacing(15)
        
        # 当前滤镜信息
        info_group = QGroupBox("当前滤镜")
        info_layout = QVBoxLayout(info_group)
        
        self.filter_name_label = QLabel("未选择滤镜")
        self.filter_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.filter_name_label)
        
        self.filter_desc_label = QLabel("请选择一个滤镜")
        self.filter_desc_label.setWordWrap(True)
        info_layout.addWidget(self.filter_desc_label)
        
        params_layout.addWidget(info_group)
        
        # 基础参数
        self.basic_params_group = QGroupBox("基础参数")
        basic_params_layout = QGridLayout(self.basic_params_group)
        
        # 强度滑块
        basic_params_layout.addWidget(QLabel("强度:"), 0, 0)
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 200)
        self.intensity_slider.setValue(100)
        self.intensity_slider.valueChanged.connect(self._on_param_changed)
        basic_params_layout.addWidget(self.intensity_slider, 0, 1)
        
        self.intensity_label = QLabel("1.0")
        basic_params_layout.addWidget(self.intensity_label, 0, 2)
        
        # 亮度滑块
        basic_params_layout.addWidget(QLabel("亮度:"), 1, 0)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 200)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self._on_param_changed)
        basic_params_layout.addWidget(self.brightness_slider, 1, 1)
        
        self.brightness_label = QLabel("1.0")
        basic_params_layout.addWidget(self.brightness_label, 1, 2)
        
        # 对比度滑块
        basic_params_layout.addWidget(QLabel("对比度:"), 2, 0)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self._on_param_changed)
        basic_params_layout.addWidget(self.contrast_slider, 2, 1)
        
        self.contrast_label = QLabel("1.0")
        basic_params_layout.addWidget(self.contrast_label, 2, 2)
        
        # 饱和度滑块
        basic_params_layout.addWidget(QLabel("饱和度:"), 3, 0)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(100)
        self.saturation_slider.valueChanged.connect(self._on_param_changed)
        basic_params_layout.addWidget(self.saturation_slider, 3, 1)
        
        self.saturation_label = QLabel("1.0")
        basic_params_layout.addWidget(self.saturation_label, 3, 2)
        
        params_layout.addWidget(self.basic_params_group)
        
        # 高级参数
        self.advanced_params_group = QGroupBox("高级参数")
        advanced_params_layout = QGridLayout(self.advanced_params_group)
        
        # 色调滑块
        advanced_params_layout.addWidget(QLabel("色调:"), 0, 0)
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(-180, 180)
        self.hue_slider.setValue(0)
        self.hue_slider.valueChanged.connect(self._on_param_changed)
        advanced_params_layout.addWidget(self.hue_slider, 0, 1)
        
        self.hue_label = QLabel("0")
        advanced_params_layout.addWidget(self.hue_label, 0, 2)
        
        # 伽马滑块
        advanced_params_layout.addWidget(QLabel("伽马:"), 1, 0)
        self.gamma_slider = QSlider(Qt.Orientation.Horizontal)
        self.gamma_slider.setRange(10, 300)
        self.gamma_slider.setValue(100)
        self.gamma_slider.valueChanged.connect(self._on_param_changed)
        advanced_params_layout.addWidget(self.gamma_slider, 1, 1)
        
        self.gamma_label = QLabel("1.0")
        advanced_params_layout.addWidget(self.gamma_label, 1, 2)
        
        # 模糊半径
        advanced_params_layout.addWidget(QLabel("模糊半径:"), 2, 0)
        self.blur_radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_radius_slider.setRange(0, 20)
        self.blur_radius_slider.setValue(5)
        self.blur_radius_slider.valueChanged.connect(self._on_param_changed)
        advanced_params_layout.addWidget(self.blur_radius_slider, 2, 1)
        
        self.blur_radius_label = QLabel("5")
        advanced_params_layout.addWidget(self.blur_radius_label, 2, 2)
        
        params_layout.addWidget(self.advanced_params_group)
        
        # 预览控制
        preview_group = QGroupBox("预览控制")
        preview_layout = QHBoxLayout(preview_group)
        
        self.preview_button = QPushButton("实时预览")
        self.preview_button.setCheckable(True)
        self.preview_button.clicked.connect(self._toggle_preview)
        preview_layout.addWidget(self.preview_button)
        
        self.reset_button = QPushButton("重置参数")
        self.reset_button.clicked.connect(self._reset_params)
        preview_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("应用滤镜")
        self.apply_button.clicked.connect(self._apply_filter)
        preview_layout.addWidget(self.apply_button)
        
        params_layout.addWidget(preview_group)
        
        # 性能信息
        perf_group = QGroupBox("性能信息")
        perf_layout = QVBoxLayout(perf_group)
        
        self.perf_label = QLabel("处理时间: 0.00ms")
        perf_layout.addWidget(self.perf_label)
        
        self.fps_label = QLabel("FPS: 0")
        perf_layout.addWidget(self.fps_label)
        
        params_layout.addWidget(perf_group)
        
        params_layout.addStretch()
        
        panel.setWidget(params_widget)
        
        return panel
    
    def _create_preset_panel(self) -> QWidget:
        """创建预设面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 预设分类
        preset_category_group = QGroupBox("预设分类")
        preset_category_layout = QVBoxLayout(preset_category_group)
        
        self.preset_category_combo = QComboBox()
        self.preset_category_combo.addItems([
            "电影风格", "艺术效果", "色彩调整", "特殊效果"
        ])
        self.preset_category_combo.currentTextChanged.connect(self._on_preset_category_changed)
        preset_category_layout.addWidget(self.preset_category_combo)
        
        layout.addWidget(preset_category_group)
        
        # 预设列表
        preset_group = QGroupBox("滤镜预设")
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_list)
        
        layout.addWidget(preset_group)
        
        # 预设操作
        preset_ops_group = QGroupBox("预设操作")
        preset_ops_layout = QHBoxLayout(preset_ops_group)
        
        self.save_preset_button = QPushButton("保存预设")
        self.save_preset_button.clicked.connect(self._save_preset)
        preset_ops_layout.addWidget(self.save_preset_button)
        
        self.load_preset_button = QPushButton("加载预设")
        self.load_preset_button.clicked.connect(self._load_preset)
        preset_ops_layout.addWidget(self.load_preset_button)
        
        self.delete_preset_button = QPushButton("删除预设")
        self.delete_preset_button.clicked.connect(self._delete_preset)
        preset_ops_layout.addWidget(self.delete_preset_button)
        
        layout.addWidget(preset_ops_group)
        
        # 初始化预设列表
        self._update_preset_list()
        
        return panel
    
    def setup_presets(self):
        """设置预设"""
        self.presets = {
            "电影风格": [
                FilterPreset.CINEMATIC,
                FilterPreset.DRAMATIC,
                FilterPreset.RETRO
            ],
            "艺术效果": [
                FilterPreset.VIBRANT,
                FilterPreset.NATURAL,
                FilterPreset.SOFT
            ],
            "色彩调整": [
                FilterPreset.COLD,
                FilterPreset.WARM,
                FilterPreset.HARD
            ],
            "特殊效果": [
                FilterPreset.FUTURISTIC,
                FilterPreset.CARTOON
            ]
        }
        
        self.preset_definitions = {
            FilterPreset.CINEMATIC: FilterChain(
                "电影风格",
                [
                    (FilterType.CONTRAST, FilterParameters(contrast=1.2, intensity=0.8)),
                    (FilterType.SATURATION, FilterParameters(saturation=0.8, intensity=0.7)),
                    (FilterType.VINTAGE, FilterParameters(intensity=0.5))
                ]
            ),
            FilterPreset.DRAMATIC: FilterChain(
                "戏剧风格",
                [
                    (FilterType.CONTRAST, FilterParameters(contrast=1.5, intensity=1.0)),
                    (FilterType.SATURATION, FilterParameters(saturation=1.3, intensity=0.9)),
                    (FilterType.BRIGHTNESS, FilterParameters(brightness=0.9, intensity=0.8))
                ]
            ),
            FilterPreset.VIBRANT: FilterChain(
                "鲜艳色彩",
                [
                    (FilterType.SATURATION, FilterParameters(saturation=1.5, intensity=1.2)),
                    (FilterType.CONTRAST, FilterParameters(contrast=1.1, intensity=0.9)),
                    (FilterType.BRIGHTNESS, FilterParameters(brightness=1.1, intensity=0.8))
                ]
            ),
            # 更多预设...
        }
    
    def _update_filter_list(self):
        """更新滤镜列表"""
        category_filters = {
            "基础滤镜": [
                FilterType.NONE, FilterType.BLUR, FilterType.SHARPEN,
                FilterType.BRIGHTNESS, FilterType.CONTRAST, FilterType.SATURATION,
                FilterType.HUE, FilterType.GAMMA
            ],
            "颜色滤镜": [
                FilterType.GRAYSCALE, FilterType.SEPIA, FilterType.INVERT,
                FilterType.VINTAGE, FilterType.COLD, FilterType.WARM,
                FilterType.BLACK_WHITE
            ],
            "特效滤镜": [
                FilterType.EDGE_DETECT, FilterType.EMBOSS,
                FilterType.OIL_PAINTING, FilterType.SKETCH,
                FilterType.CARTOON, FilterType.NIGHT_VISION,
                FilterType.THERMAL
            ],
            "模糊效果": [
                FilterType.GAUSSIAN_BLUR, FilterType.MOTION_BLUR,
                FilterType.RADIAL_BLUR, FilterType.BOX_BLUR
            ],
            "锐化效果": [
                FilterType.UNSHARP_MASK, FilterType.HIGH_PASS,
                FilterType.LAPLACIAN
            ],
            "噪点处理": [
                FilterType.DENOISE, FilterType.ADD_NOISE,
                FilterType.SALT_PEPPER
            ]
        }
        
        current_category = self.category_combo.currentText()
        filters = category_filters.get(current_category, [])
        
        self.filter_list.clear()
        filter_names = {
            FilterType.NONE: "无滤镜",
            FilterType.BLUR: "模糊",
            FilterType.SHARPEN: "锐化",
            FilterType.BRIGHTNESS: "亮度",
            FilterType.CONTRAST: "对比度",
            FilterType.SATURATION: "饱和度",
            FilterType.HUE: "色调",
            FilterType.GAMMA: "伽马",
            FilterType.GRAYSCALE: "灰度",
            FilterType.SEPIA: "复古",
            FilterType.INVERT: "反色",
            FilterType.VINTAGE: "怀旧",
            FilterType.COLD: "冷色调",
            FilterType.WARM: "暖色调",
            FilterType.BLACK_WHITE: "黑白",
            FilterType.EDGE_DETECT: "边缘检测",
            FilterType.EMBOSS: "浮雕",
            FilterType.OIL_PAINTING: "油画",
            FilterType.SKETCH: "素描",
            FilterType.CARTOON: "卡通",
            FilterType.NIGHT_VISION: "夜视",
            FilterType.THERMAL: "热成像",
            FilterType.GAUSSIAN_BLUR: "高斯模糊",
            FilterType.MOTION_BLUR: "运动模糊",
            FilterType.RADIAL_BLUR: "径向模糊",
            FilterType.BOX_BLUR: "盒式模糊",
            FilterType.UNSHARP_MASK: "反锐化",
            FilterType.HIGH_PASS: "高通",
            FilterType.LAPLACIAN: "拉普拉斯",
            FilterType.DENOISE: "降噪",
            FilterType.ADD_NOISE: "添加噪点",
            FilterType.SALT_PEPPER: "椒盐噪点"
        }
        
        for filter_type in filters:
            item = QListWidgetItem(filter_names.get(filter_type, filter_type.value))
            item.setData(Qt.ItemDataRole.UserRole, filter_type)
            self.filter_list.addItem(item)
    
    def _update_preset_list(self):
        """更新预设列表"""
        current_category = self.preset_category_combo.currentText()
        presets = self.presets.get(current_category, [])
        
        self.preset_list.clear()
        preset_names = {
            FilterPreset.CINEMATIC: "电影风格",
            FilterPreset.DRAMATIC: "戏剧风格",
            FilterPreset.VIBRANT: "鲜艳色彩",
            FilterPreset.NATURAL: "自然",
            FilterPreset.SOFT: "柔和",
            FilterPreset.HARD: "硬朗",
            FilterPreset.RETRO: "复古",
            FilterPreset.FUTURISTIC: "未来感"
        }
        
        for preset in presets:
            item = QListWidgetItem(preset_names.get(preset, preset.value))
            item.setData(Qt.ItemDataRole.UserRole, preset)
            self.preset_list.addItem(item)
    
    def _on_category_changed(self, category: str):
        """分类变化处理"""
        self._update_filter_list()
    
    def _on_preset_category_changed(self, category: str):
        """预设分类变化处理"""
        self._update_preset_list()
    
    def _on_filter_selected(self, item: QListWidgetItem):
        """滤镜选择处理"""
        filter_type = item.data(Qt.ItemDataRole.UserRole)
        self.current_filter = filter_type
        self.current_params = FilterParameters()
        
        # 更新UI
        filter_descriptions = {
            FilterType.BLUR: "模糊效果，用于柔化图像细节",
            FilterType.SHARPEN: "锐化效果，增强图像边缘和细节",
            FilterType.BRIGHTNESS: "调整图像亮度",
            FilterType.CONTRAST: "调整图像对比度",
            FilterType.SATURATION: "调整图像饱和度",
            FilterType.HUE: "调整图像色调",
            FilterType.GAMMA: "调整图像伽马值",
            FilterType.GRAYSCALE: "转换为灰度图像",
            FilterType.SEPIA: "复古褐色调效果",
            FilterType.INVERT: "反色效果",
            FilterType.VINTAGE: "怀旧效果",
            FilterType.COLD: "冷色调效果",
            FilterType.WARM: "暖色调效果",
            FilterType.EDGE_DETECT: "边缘检测效果",
            FilterType.EMBOSS: "浮雕效果",
            FilterType.ADD_NOISE: "添加噪点效果"
        }
        
        self.filter_name_label.setText(item.text())
        self.filter_desc_label.setText(filter_descriptions.get(filter_type, "暂无描述"))
        
        # 更新参数控件的可见性
        self._update_param_controls_visibility(filter_type)
    
    def _on_preset_selected(self, item: QListWidgetItem):
        """预设选择处理"""
        preset = item.data(Qt.ItemDataRole.UserRole)
        self.preset_selected.emit(preset)
        
        # 应用预设
        if preset in self.preset_definitions:
            preset_chain = self.preset_definitions[preset]
            self.preview_processor.add_filter_chain(preset_chain)
    
    def _on_search_changed(self, text: str):
        """搜索变化处理"""
        # 实现搜索逻辑
        pass
    
    def _on_param_changed(self):
        """参数变化处理"""
        # 更新参数值
        self.current_params.intensity = self.intensity_slider.value() / 100.0
        self.current_params.brightness = self.brightness_slider.value() / 100.0
        self.current_params.contrast = self.contrast_slider.value() / 100.0
        self.current_params.saturation = self.saturation_slider.value() / 100.0
        self.current_params.hue = self.hue_slider.value()
        self.current_params.gamma = self.gamma_slider.value() / 100.0
        self.current_params.blur_radius = self.blur_radius_slider.value()
        
        # 更新标签
        self.intensity_label.setText(f"{self.current_params.intensity:.2f}")
        self.brightness_label.setText(f"{self.current_params.brightness:.2f}")
        self.contrast_label.setText(f"{self.current_params.contrast:.2f}")
        self.saturation_label.setText(f"{self.current_params.saturation:.2f}")
        self.hue_label.setText(f"{self.current_params.hue}")
        self.gamma_label.setText(f"{self.current_params.gamma:.2f}")
        self.blur_radius_label.setText(f"{self.current_params.blur_radius}")
        
        # 如果启用预览，实时更新
        if self.preview_button.isChecked():
            self._apply_current_filter()
    
    def _update_param_controls_visibility(self, filter_type: FilterType):
        """更新参数控件可见性"""
        # 根据滤镜类型显示/隐藏相关参数
        basic_visible = filter_type in [
            FilterType.BLUR, FilterType.SHARPEN, FilterType.BRIGHTNESS,
            FilterType.CONTRAST, FilterType.SATURATION, FilterType.VINTAGE,
            FilterType.COLD, FilterType.WARM
        ]
        
        advanced_visible = filter_type in [
            FilterType.HUE, FilterType.GAMMA, FilterType.ADD_NOISE
        ]
        
        self.basic_params_group.setVisible(basic_visible)
        self.advanced_params_group.setVisible(advanced_visible)
    
    def _toggle_preview(self):
        """切换预览"""
        if self.preview_button.isChecked():
            self.preview_button.setText("停止预览")
            self._apply_current_filter()
        else:
            self.preview_button.setText("实时预览")
    
    def _reset_params(self):
        """重置参数"""
        self.current_params = FilterParameters()
        
        # 重置滑块
        self.intensity_slider.setValue(100)
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.saturation_slider.setValue(100)
        self.hue_slider.setValue(0)
        self.gamma_slider.setValue(100)
        self.blur_radius_slider.setValue(5)
    
    def _apply_filter(self):
        """应用滤镜"""
        self.filter_selected.emit(self.current_filter, self.current_params)
    
    def _apply_current_filter(self):
        """应用当前滤镜"""
        filter_chain = FilterChain(
            "current_filter",
            [(self.current_filter, self.current_params)]
        )
        self.preview_processor.add_filter_chain(filter_chain)
    
    def _on_filter_processed(self, frame, filter_chains):
        """滤镜处理完成"""
        # 更新性能信息
        processing_time_ms = self.preview_processor.processing_time * 1000
        self.perf_label.setText(f"处理时间: {processing_time_ms:.2f}ms")
        
        if processing_time_ms > 0:
            fps = 1000.0 / processing_time_ms
            self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def _save_preset(self):
        """保存预设"""
        # 实现保存预设逻辑
        pass
    
    def _load_preset(self):
        """加载预设"""
        # 实现加载预设逻辑
        pass
    
    def _delete_preset(self):
        """删除预设"""
        # 实现删除预设逻辑
        pass
    
    def process_frame(self, frame: np.ndarray):
        """处理帧"""
        self.preview_processor.process_frame(frame)
    
    def cleanup(self):
        """清理资源"""
        self.preview_processor.stop()


class PreviewFiltersPanel(QWidget):
    """预览滤镜面板"""
    
    filter_applied = pyqtSignal(FilterType, FilterParameters)  # 滤镜应用
    preset_applied = pyqtSignal(FilterPreset)               # 预设应用
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建滤镜预览组件
        self.filter_preview = FilterPreviewWidget()
        self.filter_preview.filter_selected.connect(self._on_filter_selected)
        self.filter_preview.preset_selected.connect(self._on_preset_selected)
        
        main_layout.addWidget(self.filter_preview)
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            PreviewFiltersPanel {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 5px;
            }
            
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 3px;
                margin-top: 2px;
                padding-top: 2px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QListWidget {
                background-color: #333;
                border: 1px solid #555;
                color: white;
                selection-background-color: #4CAF50;
            }
            
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                color: white;
                padding: 3px;
            }
            
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            
            QSlider::groove:horizontal {
                height: 4px;
                background: #555;
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid white;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
            
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 2px;
            }
        """)
    
    def _on_filter_selected(self, filter_type: FilterType, params: FilterParameters):
        """滤镜选择处理"""
        self.filter_applied.emit(filter_type, params)
    
    def _on_preset_selected(self, preset: FilterPreset):
        """预设选择处理"""
        self.preset_applied.emit(preset)
    
    def process_frame(self, frame: np.ndarray):
        """处理帧"""
        self.filter_preview.process_frame(frame)
    
    def cleanup(self):
        """清理资源"""
        self.filter_preview.cleanup()