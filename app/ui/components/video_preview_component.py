#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频预览面板 - 专业视频编辑器的预览组件
基于Material Design，提供高质量的视频预览体验
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QProgressBar, QSlider, QSpinBox,
    QComboBox, QCheckBox, QToolBar, QToolButton, QStackedWidget,
    QScrollArea, QSizePolicy, QSpacerItem, QGroupBox, QRadioButton,
    QButtonGroup, QDialog, QFileDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPixmap, QImage, QBrush, QPen,
    QLinearGradient, QRadialGradient, QPainterPath, QTransform,
    QCursor, QFontMetrics, QDragEnterEvent, QDropEvent, QWheelEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QIcon, QPalette
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme, 
    FontScheme, SpacingScheme, get_color, create_font
)


class PlaybackState(Enum):
    """播放状态"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"


class ZoomMode(Enum):
    """缩放模式"""
    FIT = "fit"           # 适应窗口
    FILL = "fill"         # 填充窗口
    ACTUAL = "actual"     # 实际大小
    CUSTOM = "custom"     # 自定义缩放


@dataclass
class VideoInfo:
    """视频信息"""
    file_path: str
    name: str
    duration_ms: int = 0
    width: int = 0
    height: int = 0
    frame_rate: float = 0.0
    bitrate: int = 0
    format: str = ""
    size_bytes: int = 0
    has_audio: bool = False
    audio_channels: int = 0
    audio_sample_rate: int = 0


class VideoPreviewWidget(QVideoWidget):
    """视频预览组件"""
    
    # 信号定义
    playback_state_changed = pyqtSignal(PlaybackState)  # 播放状态变更
    position_changed = pyqtSignal(int)  # 播放位置变更
    duration_changed = pyqtSignal(int)  # 时长变更
    video_loaded = pyqtSignal(VideoInfo)  # 视频加载完成
    video_error = pyqtSignal(str)  # 视频错误
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化变量
        self.is_dark_theme = False
        self.current_video_path = None
        self.current_video_info = None
        self.playback_state = PlaybackState.STOPPED
        self.zoom_mode = ZoomMode.FIT
        self.custom_zoom = 1.0
        self.volume = 1.0
        self.is_muted = False
        
        # 媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 设置视频输出
        self.media_player.setVideoOutput(self)
        
        # 连接信号
        self._connect_media_signals()
        
        # 设置UI属性
        self._setup_ui_properties()
        
        # 创建控制界面
        self._create_controls()
        
        # 应用样式
        self._apply_styles()
        
        # 初始化定时器
        self.position_update_timer = QTimer()
        self.position_update_timer.setInterval(100)  # 100ms更新一次
        self.position_update_timer.timeout.connect(self._update_position)
        
        # 设置拖放支持
        self.setAcceptDrops(True)
    
    def _setup_ui_properties(self):
        """设置UI属性"""
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #000000;")
        
        # 设置鼠标样式
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _connect_media_signals(self):
        """连接媒体播放器信号"""
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.errorOccurred.connect(self._on_media_error)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
    
    def _create_controls(self):
        """创建控制界面"""
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 视频显示区域（由QVideoWidget提供）
        
        # 控制面板
        self.control_panel = self._create_control_panel()
        self.main_layout.addWidget(self.control_panel)
        
        # 信息面板
        self.info_panel = self._create_info_panel()
        self.main_layout.addWidget(self.info_panel)
        
        # 默认隐藏控制面板
        self.control_panel.hide()
        self.info_panel.hide()
    
    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setObjectName("control_panel")
        panel.setFixedHeight(80)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # 进度条
        progress_layout = QHBoxLayout()
        self.position_label = QLabel("00:00")
        self.position_label.setStyleSheet("color: white; font-size: 12px;")
        progress_layout.addWidget(self.position_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.valueChanged.connect(self._on_slider_changed)
        progress_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: white; font-size: 12px;")
        progress_layout.addWidget(self.duration_label)
        
        layout.addLayout(progress_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        # 播放控制
        self.play_btn = QPushButton("▶️")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.clicked.connect(self.toggle_playback)
        control_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.clicked.connect(self.stop)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addSpacing(10)
        
        # 时间控制
        self.prev_frame_btn = QPushButton("⏮️")
        self.prev_frame_btn.setFixedSize(35, 35)
        self.prev_frame_btn.setToolTip("上一帧")
        self.prev_frame_btn.clicked.connect(self._previous_frame)
        control_layout.addWidget(self.prev_frame_btn)
        
        self.next_frame_btn = QPushButton("⏭️")
        self.next_frame_btn.setFixedSize(35, 35)
        self.next_frame_btn.setToolTip("下一帧")
        self.next_frame_btn.clicked.connect(self._next_frame)
        control_layout.addWidget(self.next_frame_btn)
        
        control_layout.addSpacing(10)
        
        # 音量控制
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setFixedSize(35, 35)
        self.volume_btn.setToolTip("静音")
        self.volume_btn.clicked.connect(self.toggle_mute)
        control_layout.addWidget(self.volume_btn)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        control_layout.addWidget(self.volume_slider)
        
        control_layout.addStretch()
        
        # 缩放控制
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["适应窗口", "填充窗口", "实际大小", "50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom_combo.setCurrentText("适应窗口")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        control_layout.addWidget(self.zoom_combo)
        
        # 全屏按钮
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(35, 35)
        self.fullscreen_btn.setToolTip("全屏")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        control_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(control_layout)
        
        return panel
    
    def _create_info_panel(self) -> QWidget:
        """创建信息面板"""
        panel = QWidget()
        panel.setObjectName("info_panel")
        panel.setFixedHeight(60)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # 视频信息
        self.video_name_label = QLabel("未加载视频")
        self.video_name_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.video_name_label)
        
        layout.addStretch()
        
        # 分辨率信息
        self.resolution_label = QLabel("--")
        self.resolution_label.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(self.resolution_label)
        
        # 帧率信息
        self.fps_label = QLabel("-- FPS")
        self.fps_label.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(self.fps_label)
        
        # 比特率信息
        self.bitrate_label = QLabel("--")
        self.bitrate_label.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(self.bitrate_label)
        
        return panel
    
    def _apply_styles(self):
        """应用样式"""
        colors = ColorScheme.DARK_THEME if self.is_dark_theme else ColorScheme.LIGHT_THEME
        
        # 控制面板样式
        self.control_panel.setStyleSheet(f"""
            QWidget#control_panel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0.8), stop:1 rgba(0, 0, 0, 0.9));
                border: none;
            }}
            
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: {SpacingScheme.RADIUS_MD}px;
                color: white;
                font-size: 16px;
                text-align: center;
            }}
            
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                border-color: {colors['primary']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['primary']};
                border-color: {colors['primary']};
            }}
            
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }}
            
            QSlider::handle:horizontal {{
                background: {colors['primary']};
                border: 2px solid white;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }}
            
            QSlider::sub-page:horizontal {{
                background: {colors['primary']};
                border-radius: 2px;
            }}
            
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: {SpacingScheme.RADIUS_SM}px;
                color: white;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 16px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid white;
                margin-right: 4px;
            }}
        """)
        
        # 信息面板样式
        self.info_panel.setStyleSheet(f"""
            QWidget#info_panel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0.6), stop:1 rgba(0, 0, 0, 0.7));
                border: none;
            }}
        """)
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self._apply_styles()
    
    def load_video(self, file_path: str):
        """加载视频文件"""
        if not os.path.exists(file_path):
            self.video_error.emit(f"文件不存在: {file_path}")
            return
        
        try:
            self.current_video_path = file_path
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            
            # 显示控制面板和信息面板
            self.control_panel.show()
            self.info_panel.show()
            
            # 更新视频名称
            video_name = os.path.basename(file_path)
            self.video_name_label.setText(video_name)
            
            # 获取视频信息
            self._extract_video_info(file_path)
            
        except Exception as e:
            self.video_error.emit(f"加载视频失败: {str(e)}")
    
    def _extract_video_info(self, file_path: str):
        """提取视频信息"""
        try:
            # 这里可以使用FFmpeg或其他库获取视频信息
            # 目前使用基本文件信息
            import os
            
            video_info = VideoInfo(
                file_path=file_path,
                name=os.path.basename(file_path),
                size_bytes=os.path.getsize(file_path)
            )
            
            # 等待媒体播放器加载完成后再获取详细信息
            QTimer.singleShot(500, lambda: self._complete_video_info(video_info))
            
        except Exception as e:
            print(f"提取视频信息失败: {e}")
    
    def _complete_video_info(self, video_info: VideoInfo):
        """完成视频信息获取"""
        # 从媒体播放器获取信息
        duration_ms = self.media_player.duration()
        if duration_ms > 0:
            video_info.duration_ms = duration_ms
        
        # 更新显示
        self._update_info_display(video_info)
        self.current_video_info = video_info
        
        # 发射信号
        self.video_loaded.emit(video_info)
    
    def _update_info_display(self, video_info: VideoInfo):
        """更新信息显示"""
        # 更新时长显示
        duration_str = self._format_duration(video_info.duration_ms)
        self.duration_label.setText(duration_str)
        
        # 更新分辨率显示
        if video_info.width > 0 and video_info.height > 0:
            self.resolution_label.setText(f"{video_info.width}x{video_info.height}")
        
        # 更新帧率显示
        if video_info.frame_rate > 0:
            self.fps_label.setText(f"{video_info.frame_rate:.1f} FPS")
        
        # 更新比特率显示
        if video_info.bitrate > 0:
            bitrate_str = self._format_bitrate(video_info.bitrate)
            self.bitrate_label.setText(bitrate_str)
    
    def _format_duration(self, duration_ms: int) -> str:
        """格式化时长"""
        if not duration_ms:
            return "00:00"
        
        total_seconds = int(duration_ms / 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _format_bitrate(self, bitrate_bps: int) -> str:
        """格式化比特率"""
        if bitrate_bps < 1000:
            return f"{bitrate_bps} bps"
        elif bitrate_bps < 1000000:
            return f"{bitrate_bps / 1000:.1f} Kbps"
        else:
            return f"{bitrate_bps / 1000000:.1f} Mbps"
    
    def play(self):
        """播放视频"""
        if self.current_video_path:
            self.media_player.play()
    
    def pause(self):
        """暂停视频"""
        self.media_player.pause()
    
    def stop(self):
        """停止视频"""
        self.media_player.stop()
        self.position_update_timer.stop()
    
    def toggle_playback(self):
        """切换播放状态"""
        if self.playback_state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()
    
    def set_position(self, position_ms: int):
        """设置播放位置"""
        if self.media_player.duration() > 0:
            self.media_player.setPosition(position_ms)
    
    def set_volume(self, volume: float):
        """设置音量 (0.0 - 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(self.volume)
        self.volume_slider.setValue(int(self.volume * 100))
    
    def toggle_mute(self):
        """切换静音"""
        self.is_muted = not self.is_muted
        self.audio_output.setMuted(self.is_muted)
        
        # 更新按钮图标
        if self.is_muted:
            self.volume_btn.setText("🔇")
        else:
            self.volume_btn.setText("🔊")
    
    def toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("⛶")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛶")
    
    def _on_playback_state_changed(self, state):
        """播放状态变更处理"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_state = PlaybackState.PLAYING
            self.play_btn.setText("⏸️")
            self.position_update_timer.start()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.playback_state = PlaybackState.PAUSED
            self.play_btn.setText("▶️")
            self.position_update_timer.stop()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.playback_state = PlaybackState.STOPPED
            self.play_btn.setText("▶️")
            self.position_update_timer.stop()
        
        self.playback_state_changed.emit(self.playback_state)
    
    def _on_position_changed(self, position):
        """播放位置变更处理"""
        if not self.progress_slider.isSliderDown():
            duration = self.media_player.duration()
            if duration > 0:
                progress = int((position / duration) * 100)
                self.progress_slider.setValue(progress)
            
            # 更新位置显示
            self.position_label.setText(self._format_duration(position))
        
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration):
        """时长变更处理"""
        self.duration_label.setText(self._format_duration(duration))
        self.duration_changed.emit(duration)
        
        # 如果当前有视频信息，更新它
        if self.current_video_info:
            self.current_video_info.duration_ms = duration
            self._update_info_display(self.current_video_info)
    
    def _on_media_error(self, error, error_string):
        """媒体错误处理"""
        self.video_error.emit(error_string)
    
    def _on_media_status_changed(self, status):
        """媒体状态变更处理"""
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # 媒体加载完成
            pass
        elif status == QMediaPlayer.MediaStatus.BufferingMedia:
            # 正在缓冲
            self.playback_state = PlaybackState.BUFFERING
            self.playback_state_changed.emit(self.playback_state)
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            # 缓冲完成
            if self.playback_state == PlaybackState.PLAYING:
                self.play()
    
    def _update_position(self):
        """更新播放位置"""
        if self.media_player.duration() > 0:
            position = self.media_player.position()
            self.position_label.setText(self._format_duration(position))
    
    def _on_slider_pressed(self):
        """滑块按下处理"""
        # 暂停更新
        pass
    
    def _on_slider_released(self):
        """滑块释放处理"""
        # 设置播放位置
        duration = self.media_player.duration()
        if duration > 0:
            progress = self.progress_slider.value()
            position = int((progress / 100) * duration)
            self.set_position(position)
    
    def _on_slider_changed(self, value):
        """滑块值变更处理"""
        # 只在拖动时更新显示
        if self.progress_slider.isSliderDown():
            duration = self.media_player.duration()
            if duration > 0:
                position = int((value / 100) * duration)
                self.position_label.setText(self._format_duration(position))
    
    def _on_volume_changed(self, value):
        """音量变更处理"""
        self.set_volume(value / 100.0)
    
    def _on_zoom_changed(self, text):
        """缩放变更处理"""
        zoom_map = {
            "适应窗口": ZoomMode.FIT,
            "填充窗口": ZoomMode.FILL,
            "实际大小": ZoomMode.ACTUAL,
            "50%": ZoomMode.CUSTOM,
            "75%": ZoomMode.CUSTOM,
            "100%": ZoomMode.CUSTOM,
            "125%": ZoomMode.CUSTOM,
            "150%": ZoomMode.CUSTOM,
            "200%": ZoomMode.CUSTOM
        }
        
        self.zoom_mode = zoom_map.get(text, ZoomMode.FIT)
        
        if self.zoom_mode == ZoomMode.CUSTOM:
            zoom_value = float(text.replace("%", "")) / 100.0
            self.custom_zoom = zoom_value
        
        self._apply_zoom()
    
    def _apply_zoom(self):
        """应用缩放"""
        # 这里可以实现具体的缩放逻辑
        pass
    
    def _previous_frame(self):
        """上一帧"""
        current_position = self.media_player.position()
        # 假设30fps，每帧约33ms
        new_position = max(0, current_position - 33)
        self.set_position(new_position)
    
    def _next_frame(self):
        """下一帧"""
        current_position = self.media_player.position()
        duration = self.media_player.duration()
        # 假设30fps，每帧约33ms
        new_position = min(duration, current_position + 33)
        self.set_position(new_position)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件处理"""
        self.toggle_fullscreen()
    
    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        super().mousePressEvent(event)
        
        # 显示/隐藏控制面板
        if event.button() == Qt.MouseButton.LeftButton:
            if self.control_panel.isVisible():
                self.control_panel.hide()
                self.info_panel.hide()
            else:
                self.control_panel.show()
                self.info_panel.show()
    
    def wheelEvent(self, event):
        """滚轮事件处理"""
        # 使用滚轮调节音量
        delta = event.angleDelta().y()
        if delta > 0:
            # 向上滚动，增加音量
            self.set_volume(self.volume + 0.05)
        else:
            # 向下滚动，减少音量
            self.set_volume(self.volume - 0.05)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为视频文件
            video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]
            
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext in video_extensions:
                    event.acceptProposedAction()
                    return
        
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放置事件"""
        if event.mimeData().hasUrls():
            video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]
            
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext in video_extensions:
                    self.load_video(file_path)
                    event.acceptProposedAction()
                    return
        
        event.ignore()
    
    def cleanup(self):
        """清理资源"""
        self.stop()
        self.media_player.setVideoOutput(None)
        self.media_player.deleteLater()
        self.audio_output.deleteLater()


class ProfessionalVideoPreviewPanel(QWidget):
    """专业视频预览面板"""
    
    # 信号定义
    video_selected = pyqtSignal(str)  # 视频选中信号
    playback_started = pyqtSignal()  # 播放开始信号
    playback_paused = pyqtSignal()  # 播放暂停信号
    playback_stopped = pyqtSignal()  # 播放停止信号
    position_changed = pyqtSignal(int)  # 播放位置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_dark_theme = False
        self.video_manager = None
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 视频预览组件
        self.video_preview = VideoPreviewWidget()
        layout.addWidget(self.video_preview)
        
        # 工具栏
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
    
    def _create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        
        # 文件操作
        open_action = toolbar.addAction("📁 打开")
        open_action.setToolTip("打开视频文件")
        open_action.triggered.connect(self._open_video)
        
        toolbar.addSeparator()
        
        # 播放控制
        play_action = toolbar.addAction("▶️ 播放")
        play_action.setToolTip("播放/暂停")
        play_action.triggered.connect(self.video_preview.toggle_playback)
        
        stop_action = toolbar.addAction("⏹️ 停止")
        stop_action.setToolTip("停止播放")
        stop_action.triggered.connect(self.video_preview.stop)
        
        toolbar.addSeparator()
        
        # 编辑工具
        snapshot_action = toolbar.addAction("📸 截图")
        snapshot_action.setToolTip("截图")
        snapshot_action.triggered.connect(self._take_snapshot)
        
        toolbar.addSeparator()
        
        # 视图控制
        fullscreen_action = toolbar.addAction("⛶ 全屏")
        fullscreen_action.setToolTip("全屏播放")
        fullscreen_action.triggered.connect(self.video_preview.toggle_fullscreen)
        
        return toolbar
    
    def _apply_styles(self):
        """应用样式"""
        colors = ColorScheme.DARK_THEME if self.is_dark_theme else ColorScheme.LIGHT_THEME
        
        # 面板样式
        self.setStyleSheet(f"""
            ProfessionalVideoPreviewPanel {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_MD}px;
            }}
            
            QToolBar {{
                background-color: {colors['surface_variant']};
                border: none;
                border-top: 1px solid {colors['border']};
                border-radius: 0px;
                spacing: {SpacingScheme.GAP_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
            }}
            
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
                min-width: 60px;
            }}
            
            QToolButton:hover {{
                background: {colors['highlight']};
            }}
            
            QToolButton:pressed {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
        """)
    
    def _connect_signals(self):
        """连接信号"""
        self.video_preview.video_loaded.connect(self._on_video_loaded)
        self.video_preview.playback_state_changed.connect(self._on_playback_state_changed)
        self.video_preview.position_changed.connect(self._on_position_changed)
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self.video_preview.set_theme(is_dark)
        self._apply_styles()
    
    def set_video_manager(self, video_manager):
        """设置视频管理器"""
        self.video_manager = video_manager
    
    def load_video(self, file_path: str):
        """加载视频"""
        self.video_preview.load_video(file_path)
    
    def _open_video(self):
        """打开视频文件"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm)")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self.load_video(file_paths[0])
    
    def _take_snapshot(self):
        """截图"""
        # TODO: 实现截图功能
        pass
    
    def _on_video_loaded(self, video_info: VideoInfo):
        """视频加载完成处理"""
        self.video_selected.emit(video_info.file_path)
    
    def _on_playback_state_changed(self, state: PlaybackState):
        """播放状态变更处理"""
        if state == PlaybackState.PLAYING:
            self.playback_started.emit()
        elif state == PlaybackState.PAUSED:
            self.playback_paused.emit()
        elif state == PlaybackState.STOPPED:
            self.playback_stopped.emit()
    
    def _on_position_changed(self, position: int):
        """播放位置变更处理"""
        self.position_changed.emit(position)
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'video_preview'):
            self.video_preview.cleanup()


# 工厂函数
def create_video_preview_panel(parent=None) -> ProfessionalVideoPreviewPanel:
    """创建视频预览面板"""
    return ProfessionalVideoPreviewPanel(parent)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建视频预览面板
    panel = create_video_preview_panel()
    panel.setWindowTitle("视频预览面板测试")
    panel.resize(800, 600)
    panel.show()
    
    sys.exit(app.exec())