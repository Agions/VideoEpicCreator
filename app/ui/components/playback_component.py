#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业播放控制组件 - 高级视频播放控制界面
"""

import os
import math
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QToolButton, QSlider, QComboBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QCheckBox, QFrame, QSpacerItem,
    QSizePolicy, QProgressBar, QMenu, QWidgetAction, QDialog,
    QDialogButtonBox, QScrollArea, QSplitter, QStyle, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPointF, QRect
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QFont,
    QPalette, QLinearGradient, QRadialGradient, QPainterPath,
    QCursor, QFontMetrics, QWheelEvent, QMouseEvent, QPaintEvent
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


class PlaybackState(Enum):
    """播放状态"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    SEEKING = "seeking"


class PlaybackMode(Enum):
    """播放模式"""
    NORMAL = "normal"        # 正常播放
    LOOP = "loop"           # 循环播放
    SINGLE_LOOP = "single_loop"  # 单曲循环
    SHUFFLE = "shuffle"     # 随机播放


class PrecisionMode(Enum):
    """精度模式"""
    FRAME = "frame"         # 帧精度
    TIME = "time"           # 时间精度
    SAMPLE = "sample"       # 采样精度


@dataclass
class PlaybackConfig:
    """播放配置"""
    state: PlaybackState = PlaybackState.STOPPED
    mode: PlaybackMode = PlaybackMode.NORMAL
    precision: PrecisionMode = PrecisionMode.TIME
    speed: float = 1.0
    volume: float = 1.0
    is_muted: bool = False
    position: float = 0.0
    duration: float = 0.0
    frame_rate: float = 30.0
    hardware_acceleration: bool = True
    buffer_size: int = 1024  # KB


class AdvancedSlider(QSlider):
    """高级滑块组件"""
    
    valueChangedPrecise = pyqtSignal(float)  # 精确值变化信号
    
    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        
        self.min_value = 0.0
        self.max_value = 100.0
        self.current_value = 0.0
        self.step_size = 0.1
        self.is_dragging = False
        
        # 设置基本属性
        self.setMinimum(0)
        self.setMaximum(1000)
        self.setValue(0)
        self.setSingleStep(1)
        
        # 连接信号
        self.valueChanged.connect(self._on_value_changed)
        self.sliderPressed.connect(self._on_slider_pressed)
        self.sliderReleased.connect(self._on_slider_released)
    
    def setRangeFloat(self, min_val: float, max_val: float):
        """设置浮点数范围"""
        self.min_value = min_val
        self.max_value = max_val
    
    def setValueFloat(self, value: float):
        """设置浮点数值"""
        self.current_value = max(self.min_value, min(self.max_value, value))
        
        # 转换为整数设置
        if self.max_value > self.min_value:
            int_value = int(((self.current_value - self.min_value) / 
                           (self.max_value - self.min_value)) * 1000)
            super().setValue(int_value)
    
    def valueFloat(self) -> float:
        """获取浮点数值"""
        return self.current_value
    
    def _on_value_changed(self, int_value: int):
        """整数值变化处理"""
        if self.max_value > self.min_value:
            self.current_value = self.min_value + (int_value / 1000.0) * (self.max_value - self.min_value)
            self.valueChangedPrecise.emit(self.current_value)
    
    def _on_slider_pressed(self):
        """滑块按下处理"""
        self.is_dragging = True
    
    def _on_slider_released(self):
        """滑块释放处理"""
        self.is_dragging = False


class PlaybackControls(QWidget):
    """专业播放控制组件"""
    
    # 信号定义
    state_changed = pyqtSignal(PlaybackState)  # 播放状态变化
    position_changed = pyqtSignal(float)      # 播放位置变化
    duration_changed = pyqtSignal(float)       # 时长变化
    speed_changed = pyqtSignal(float)          # 播放速度变化
    volume_changed = pyqtSignal(float)          # 音量变化
    mute_changed = pyqtSignal(bool)             # 静音状态变化
    mode_changed = pyqtSignal(PlaybackMode)    # 播放模式变化
    precision_changed = pyqtSignal(PrecisionMode)  # 精度模式变化
    
    # 操作信号
    play_requested = pyqtSignal()              # 请求播放
    pause_requested = pyqtSignal()             # 请求暂停
    stop_requested = pyqtSignal()              # 请求停止
    seek_requested = pyqtSignal(float)         # 请求跳转
    frame_step_requested = pyqtSignal(int)     # 请求帧步进
    snapshot_requested = pyqtSignal()          # 请求截图
    fullscreen_requested = pyqtSignal()        # 请求全屏
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化配置
        self.config = PlaybackConfig()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化定时器
        self.init_timers()
        
        # 应用样式
        self.apply_styles()
        
        # 设置快捷键
        self.setup_shortcuts()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建控制面板
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 创建信息面板
        info_panel = self._create_info_panel()
        main_layout.addWidget(info_panel)
        
        # 创建高级控制面板
        advanced_panel = self._create_advanced_panel()
        main_layout.addWidget(advanced_panel)
    
    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setObjectName("control_panel")
        panel.setFixedHeight(80)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # 进度条区域
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(5)
        
        # 时间显示
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: white; font-size: 12px; min-width: 80px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.time_label)
        
        # 进度滑块
        self.progress_slider = AdvancedSlider(Qt.Orientation.Horizontal)
        self.progress_slider.valueChangedPrecise.connect(self._on_position_changed)
        progress_layout.addWidget(self.progress_slider)
        
        # 时长显示
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setStyleSheet("color: white; font-size: 12px; min-width: 80px;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.duration_label)
        
        layout.addLayout(progress_layout)
        
        # 控制按钮区域
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        # 播放控制组
        playback_group = self._create_playback_group()
        control_layout.addWidget(playback_group)
        
        control_layout.addSpacing(15)
        
        # 时间控制组
        time_group = self._create_time_control_group()
        control_layout.addWidget(time_group)
        
        control_layout.addSpacing(15)
        
        # 音量控制组
        volume_group = self._create_volume_control_group()
        control_layout.addWidget(volume_group)
        
        control_layout.addStretch()
        
        # 视图控制组
        view_group = self._create_view_control_group()
        control_layout.addWidget(view_group)
        
        layout.addLayout(control_layout)
        
        return panel
    
    def _create_playback_group(self) -> QWidget:
        """创建播放控制组"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 播放/暂停按钮
        self.play_button = QToolButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setToolTip("播放/暂停 (空格)")
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setFixedSize(40, 40)
        layout.addWidget(self.play_button)
        
        # 停止按钮
        self.stop_button = QToolButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setToolTip("停止")
        self.stop_button.clicked.connect(self.stop_playback)
        self.stop_button.setFixedSize(35, 35)
        layout.addWidget(self.stop_button)
        
        # 上一帧按钮
        self.prev_frame_button = QToolButton()
        self.prev_frame_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_frame_button.setToolTip("上一帧 (左箭头)")
        self.prev_frame_button.clicked.connect(lambda: self.step_frame(-1))
        self.prev_frame_button.setFixedSize(35, 35)
        layout.addWidget(self.prev_frame_button)
        
        # 下一帧按钮
        self.next_frame_button = QToolButton()
        self.next_frame_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_frame_button.setToolTip("下一帧 (右箭头)")
        self.next_frame_button.clicked.connect(lambda: self.step_frame(1))
        self.next_frame_button.setFixedSize(35, 35)
        layout.addWidget(self.next_frame_button)
        
        return group
    
    def _create_time_control_group(self) -> QWidget:
        """创建时间控制组"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 播放速度
        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "0.25x", "0.5x", "0.75x", "1.0x", "1.25x", 
            "1.5x", "2.0x", "4.0x", "8.0x"
        ])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        self.speed_combo.setMaximumWidth(80)
        layout.addWidget(QLabel("速度:"))
        layout.addWidget(self.speed_combo)
        
        # 精度模式
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["时间精度", "帧精度", "采样精度"])
        self.precision_combo.setCurrentText("时间精度")
        self.precision_combo.currentTextChanged.connect(self._on_precision_changed)
        self.precision_combo.setMaximumWidth(100)
        layout.addWidget(QLabel("精度:"))
        layout.addWidget(self.precision_combo)
        
        return group
    
    def _create_volume_control_group(self) -> QWidget:
        """创建音量控制组"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 静音按钮
        self.mute_button = QToolButton()
        self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.mute_button.setToolTip("静音 (M)")
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setFixedSize(30, 30)
        layout.addWidget(self.mute_button)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.volume_slider)
        
        # 音量显示
        self.volume_label = QLabel("70%")
        self.volume_label.setStyleSheet("color: white; font-size: 11px; min-width: 35px;")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.volume_label)
        
        return group
    
    def _create_view_control_group(self) -> QWidget:
        """创建视图控制组"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 播放模式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["正常", "循环", "单曲循环", "随机"])
        self.mode_combo.setCurrentText("正常")
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.mode_combo.setMaximumWidth(80)
        layout.addWidget(QLabel("模式:"))
        layout.addWidget(self.mode_combo)
        
        # 全屏按钮
        self.fullscreen_button = QToolButton()
        self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.fullscreen_button.setToolTip("全屏 (F)")
        self.fullscreen_button.clicked.connect(self.request_fullscreen)
        self.fullscreen_button.setFixedSize(30, 30)
        layout.addWidget(self.fullscreen_button)
        
        return group
    
    def _create_info_panel(self) -> QWidget:
        """创建信息面板"""
        panel = QWidget()
        panel.setObjectName("info_panel")
        panel.setFixedHeight(40)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(20)
        
        # 文件名
        self.filename_label = QLabel("未加载视频")
        self.filename_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.filename_label)
        
        layout.addStretch()
        
        # 分辨率
        self.resolution_label = QLabel("--")
        self.resolution_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.resolution_label)
        
        # 帧率
        self.fps_label = QLabel("-- FPS")
        self.fps_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.fps_label)
        
        # 比特率
        self.bitrate_label = QLabel("--")
        self.bitrate_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.bitrate_label)
        
        # 缓冲状态
        self.buffer_label = QLabel("缓冲: 0%")
        self.buffer_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.buffer_label)
        
        return panel
    
    def _create_advanced_panel(self) -> QWidget:
        """创建高级控制面板"""
        panel = QWidget()
        panel.setObjectName("advanced_panel")
        panel.setMaximumHeight(60)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # 标记控制
        marker_group = QGroupBox("标记")
        marker_layout = QHBoxLayout(marker_group)
        marker_layout.setContentsMargins(5, 2, 5, 2)
        
        self.add_marker_button = QToolButton()
        self.add_marker_button.setText("添加")
        self.add_marker_button.setToolTip("添加标记 (M)")
        self.add_marker_button.setFixedSize(50, 25)
        marker_layout.addWidget(self.add_marker_button)
        
        self.clear_markers_button = QToolButton()
        self.clear_markers_button.setText("清除")
        self.clear_markers_button.setToolTip("清除所有标记")
        self.clear_markers_button.setFixedSize(50, 25)
        marker_layout.addWidget(self.clear_markers_button)
        
        layout.addWidget(marker_group)
        
        # 片段控制
        clip_group = QGroupBox("片段")
        clip_layout = QHBoxLayout(clip_group)
        clip_layout.setContentsMargins(5, 2, 5, 2)
        
        self.set_in_button = QToolButton()
        self.set_in_button.setText("入点")
        self.set_in_button.setToolTip("设置入点 (I)")
        self.set_in_button.setFixedSize(50, 25)
        clip_layout.addWidget(self.set_in_button)
        
        self.set_out_button = QToolButton()
        self.set_out_button.setText("出点")
        self.set_out_button.setToolTip("设置出点 (O)")
        self.set_out_button.setFixedSize(50, 25)
        clip_layout.addWidget(self.set_out_button)
        
        self.create_clip_button = QToolButton()
        self.create_clip_button.setText("创建")
        self.create_clip_button.setToolTip("创建片段")
        self.create_clip_button.setFixedSize(50, 25)
        clip_layout.addWidget(self.create_clip_button)
        
        layout.addWidget(clip_group)
        
        # 快捷操作
        quick_group = QGroupBox("快捷")
        quick_layout = QHBoxLayout(quick_group)
        quick_layout.setContentsMargins(5, 2, 5, 2)
        
        self.snapshot_button = QToolButton()
        self.snapshot_button.setText("截图")
        self.snapshot_button.setToolTip("截图 (S)")
        self.snapshot_button.setFixedSize(50, 25)
        quick_layout.addWidget(self.snapshot_button)
        
        self.loop_button = QToolButton()
        self.loop_button.setText("循环")
        self.loop_button.setToolTip("循环播放")
        self.loop_button.setCheckable(True)
        self.loop_button.setFixedSize(50, 25)
        quick_layout.addWidget(self.loop_button)
        
        layout.addWidget(quick_group)
        
        layout.addStretch()
        
        return panel
    
    def init_timers(self):
        """初始化定时器"""
        # 位置更新定时器
        self.position_timer = QTimer()
        self.position_timer.setInterval(100)  # 100ms更新一次
        self.position_timer.timeout.connect(self._update_position_display)
        
        # 缓冲状态定时器
        self.buffer_timer = QTimer()
        self.buffer_timer.setInterval(500)  # 500ms更新一次
        self.buffer_timer.timeout.connect(self._update_buffer_status)
    
    def apply_styles(self):
        """应用样式"""
        # 控制面板样式
        self.setStyleSheet("""
            QWidget#control_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 40, 40, 0.95), stop:1 rgba(20, 20, 20, 0.98));
                border: none;
            }
            
            QWidget#info_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 30, 30, 0.9), stop:1 rgba(15, 15, 15, 0.95));
                border: none;
            }
            
            QWidget#advanced_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(35, 35, 35, 0.9), stop:1 rgba(20, 20, 20, 0.95));
                border: none;
            }
            
            QToolButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: #4CAF50;
            }
            
            QToolButton:pressed {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            
            QToolButton:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                color: white;
                padding: 2px 6px;
                font-size: 11px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 12px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid white;
                margin-right: 3px;
            }
            
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
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
            
            QGroupBox {
                color: white;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                margin-top: 2px;
                padding-top: 2px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # 空格键 - 播放/暂停
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_playback)
        
        # 左箭头 - 上一帧
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(lambda: self.step_frame(-1))
        
        # 右箭头 - 下一帧
        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(lambda: self.step_frame(1))
        
        # M键 - 添加标记
        self.m_shortcut = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.m_shortcut.activated.connect(self.add_marker_button.click)
        
        # S键 - 截图
        self.s_shortcut = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        self.s_shortcut.activated.connect(self.snapshot_button.click)
        
        # I键 - 设置入点
        self.i_shortcut = QShortcut(QKeySequence(Qt.Key.Key_I), self)
        self.i_shortcut.activated.connect(self.set_in_button.click)
        
        # O键 - 设置出点
        self.o_shortcut = QShortcut(QKeySequence(Qt.Key.Key_O), self)
        self.o_shortcut.activated.connect(self.set_out_button.click)
        
        # F键 - 全屏
        self.f_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F), self)
        self.f_shortcut.activated.connect(self.request_fullscreen)
    
    def set_state(self, state: PlaybackState):
        """设置播放状态"""
        self.config.state = state
        
        # 更新按钮图标
        if state == PlaybackState.PLAYING:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.position_timer.start()
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.position_timer.stop()
        
        # 发射信号
        self.state_changed.emit(state)
    
    def set_position(self, position: float):
        """设置播放位置"""
        self.config.position = position
        self.progress_slider.setValueFloat(position)
        self._update_time_display(position)
    
    def set_duration(self, duration: float):
        """设置时长"""
        self.config.duration = duration
        self.progress_slider.setRangeFloat(0, duration)
        self._update_time_display(duration, is_duration=True)
    
    def set_speed(self, speed: float):
        """设置播放速度"""
        self.config.speed = speed
        speed_text = f"{speed:.2f}x"
        
        # 更新下拉框
        index = self.speed_combo.findText(speed_text)
        if index >= 0:
            self.speed_combo.setCurrentIndex(index)
        else:
            self.speed_combo.addItem(speed_text)
            self.speed_combo.setCurrentText(speed_text)
        
        # 发射信号
        self.speed_changed.emit(speed)
    
    def set_volume(self, volume: float):
        """设置音量"""
        self.config.volume = max(0.0, min(1.0, volume))
        self.volume_slider.setValue(int(self.config.volume * 100))
        self.volume_label.setText(f"{int(self.config.volume * 100)}%")
        
        # 更新静音按钮图标
        if self.config.is_muted:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        
        # 发射信号
        self.volume_changed.emit(self.config.volume)
    
    def set_muted(self, muted: bool):
        """设置静音状态"""
        self.config.is_muted = muted
        
        # 更新按钮图标
        if muted:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        
        # 发射信号
        self.mute_changed.emit(muted)
    
    def set_video_info(self, info: Dict[str, Any]):
        """设置视频信息"""
        # 更新文件名
        filename = info.get('name', '未知视频')
        self.filename_label.setText(filename)
        
        # 更新分辨率
        width = info.get('width', 0)
        height = info.get('height', 0)
        if width > 0 and height > 0:
            self.resolution_label.setText(f"{width}x{height}")
        
        # 更新帧率
        fps = info.get('frame_rate', 0.0)
        if fps > 0:
            self.fps_label.setText(f"{fps:.1f} FPS")
            self.config.frame_rate = fps
        
        # 更新比特率
        bitrate = info.get('bitrate', 0)
        if bitrate > 0:
            self.bitrate_label.setText(self._format_bitrate(bitrate))
        
        # 更新时长
        duration = info.get('duration_ms', 0) / 1000.0
        if duration > 0:
            self.set_duration(duration)
    
    def toggle_playback(self):
        """切换播放状态"""
        if self.config.state == PlaybackState.PLAYING:
            self.pause_requested.emit()
        else:
            self.play_requested.emit()
    
    def stop_playback(self):
        """停止播放"""
        self.stop_requested.emit()
    
    def step_frame(self, frames: int):
        """帧步进"""
        self.frame_step_requested.emit(frames)
    
    def toggle_mute(self):
        """切换静音"""
        self.set_muted(not self.config.is_muted)
    
    def request_fullscreen(self):
        """请求全屏"""
        self.fullscreen_requested.emit()
    
    def _on_position_changed(self, position: float):
        """位置变化处理"""
        self.set_position(position)
        self.seek_requested.emit(position)
    
    def _on_speed_changed(self, speed_text: str):
        """速度变化处理"""
        speed = float(speed_text.replace('x', ''))
        self.set_speed(speed)
    
    def _on_volume_changed(self, volume: int):
        """音量变化处理"""
        self.set_volume(volume / 100.0)
    
    def _on_mode_changed(self, mode_text: str):
        """模式变化处理"""
        mode_map = {
            "正常": PlaybackMode.NORMAL,
            "循环": PlaybackMode.LOOP,
            "单曲循环": PlaybackMode.SINGLE_LOOP,
            "随机": PlaybackMode.SHUFFLE
        }
        mode = mode_map.get(mode_text, PlaybackMode.NORMAL)
        self.config.mode = mode
        self.mode_changed.emit(mode)
    
    def _on_precision_changed(self, precision_text: str):
        """精度变化处理"""
        precision_map = {
            "时间精度": PrecisionMode.TIME,
            "帧精度": PrecisionMode.FRAME,
            "采样精度": PrecisionMode.SAMPLE
        }
        precision = precision_map.get(precision_text, PrecisionMode.TIME)
        self.config.precision = precision
        self.precision_changed.emit(precision)
    
    def _update_position_display(self):
        """更新位置显示"""
        self._update_time_display(self.config.position)
    
    def _update_time_display(self, time_seconds: float, is_duration: bool = False):
        """更新时间显示"""
        if is_duration:
            self.duration_label.setText(self._format_time(time_seconds))
        else:
            self.time_label.setText(self._format_time(time_seconds))
    
    def _update_buffer_status(self):
        """更新缓冲状态"""
        # 这里可以根据实际缓冲状态更新
        buffer_percent = 100  # 假设已完全缓冲
        self.buffer_label.setText(f"缓冲: {buffer_percent}%")
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if not seconds or seconds < 0:
            return "00:00:00"
        
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _format_bitrate(self, bitrate_bps: int) -> str:
        """格式化比特率"""
        if bitrate_bps < 1000:
            return f"{bitrate_bps} bps"
        elif bitrate_bps < 1000000:
            return f"{bitrate_bps / 1000:.1f} Kbps"
        else:
            return f"{bitrate_bps / 1000000:.1f} Mbps"
    
    def get_config(self) -> PlaybackConfig:
        """获取配置"""
        return self.config
    
    def cleanup(self):
        """清理资源"""
        self.position_timer.stop()
        self.buffer_timer.stop()