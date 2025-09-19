#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业时间轴编辑器 - 视频编辑器的核心组件
基于PyQt6的专业时间轴编辑系统，支持多轨道编辑、关键帧动画等高级功能
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QProgressBar, QSlider, QSpinBox,
    QComboBox, QCheckBox, QRadioButton, QButtonGroup, QGroupBox,
    QLineEdit, QTextEdit, QTabWidget, QSplitter, QStackedWidget,
    QToolButton, QMenuBar, QStatusBar, QToolBar, QDockWidget,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem,
    QApplication, QStyleFactory, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QMenu, QInputDialog, QMessageBox, QFileDialog
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QTimer, pyqtSignal, QObject,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QThread, QMutex, QMutexLocker,
    QBuffer, QIODevice, QByteArray, QPointF, QRectF, QMargins,
    QUrl, QMimeData, QSettings, QStandardPaths
)
from PyQt6.QtGui import (
    QPainter, QColor, QPalette, QFont, QFontMetrics, QIcon,
    QPixmap, QImage, QBrush, QPen, QLinearGradient, QRadialGradient,
    QConicalGradient, QPainterPath, QTransform, QPolygon,
    QKeySequence, QCursor, QFontDatabase, QTextCharFormat,
    QTextFormat, QDrag, QPixmap, QDragEnterEvent, QDropEvent,
    QWheelEvent, QMouseEvent, QPaintEvent, QResizeEvent,
    QIntValidator, QDoubleValidator, QRegularExpressionValidator
)

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme, 
    FontScheme, SpacingScheme, get_color, create_font
)
from ...core.video_processing_engine import (
    VideoProcessingEngine, TimelineProject, TimelineClip, TimelineTrack, 
    ProcessingConfig, VideoInfo
)


class TrackType(Enum):
    """轨道类型"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    TRANSITION = "transition"


class ClipType(Enum):
    """片段类型"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    TRANSITION = "transition"


class TimelineState(Enum):
    """时间轴状态"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"
    RENDERING = "rendering"


@dataclass
class TimeScale:
    """时间刻度"""
    pixels_per_second: float = 100.0
    minor_tick_interval: float = 0.1  # 秒
    major_tick_interval: float = 1.0  # 秒
    format: str = "mm:ss"


@dataclass
class SelectionInfo:
    """选择信息"""
    selected_clips: List[str] = field(default_factory=list)
    selected_tracks: List[str] = field(default_factory=list)
    selection_start: float = 0.0
    selection_end: float = 0.0


class TimelineCanvas(QWidget):
    """时间轴画布"""
    
    # 信号
    clip_selected = pyqtSignal(object)  # 片段选中信号
    clip_moved = pyqtSignal(str, float)  # 片段移动信号
    clip_resized = pyqtSignal(str, float, float)  # 片段调整大小信号
    time_clicked = pyqtSignal(float)  # 时间点击信号
    selection_changed = pyqtSignal(SelectionInfo)  # 选择变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化变量
        self.is_dark_theme = False
        self.project = None
        self.time_scale = TimeScale()
        self.current_time = 0.0
        self.playhead_time = 0.0
        self.selection_info = SelectionInfo()
        
        # 交互状态
        self.dragging_clip = None
        self.resizing_clip = None
        self.drag_start_pos = None
        self.drag_start_time = 0.0
        self.resize_edge = None  # 'left' or 'right'
        
        # 设置UI属性
        self._setup_ui_properties()
        self._setup_timers()
        
        # 设置拖放支持
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
    
    def _setup_ui_properties(self):
        """设置UI属性"""
        self.setMinimumSize(800, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _setup_timers(self):
        """设置定时器"""
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(50)  # 20fps
        self.playback_timer.timeout.connect(self._update_playback)
    
    def set_project(self, project: TimelineProject):
        """设置项目"""
        self.project = project
        self.update()
    
    def set_time_scale(self, scale: TimeScale):
        """设置时间刻度"""
        self.time_scale = scale
        self.update()
    
    def set_current_time(self, time: float):
        """设置当前时间"""
        self.current_time = time
        self.playhead_time = time
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        self._draw_background(painter)
        
        # 绘制时间刻度
        self._draw_time_ruler(painter)
        
        # 绘制轨道
        self._draw_tracks(painter)
        
        # 绘制片段
        self._draw_clips(painter)
        
        # 绘制播放头
        self._draw_playhead(painter)
        
        # 绘制选择区域
        self._draw_selection(painter)
    
    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        if self.is_dark_theme:
            painter.fillRect(self.rect(), QColor(30, 30, 30))
        else:
            painter.fillRect(self.rect(), QColor(245, 245, 245))
    
    def _draw_time_ruler(self, painter: QPainter):
        """绘制时间刻度"""
        ruler_height = 30
        ruler_rect = QRect(0, 0, self.width(), ruler_height)
        
        # 绘制刻度背景
        if self.is_dark_theme:
            painter.fillRect(ruler_rect, QColor(50, 50, 50))
        else:
            painter.fillRect(ruler_rect, QColor(220, 220, 220))
        
        # 绘制刻度线
        painter.setPen(QPen(QColor(100, 100, 100) if self.is_dark_theme else QColor(150, 150, 150), 1))
        
        start_time = 0
        end_time = self.width() / self.time_scale.pixels_per_second
        
        # 主刻度
        current_time = start_time
        while current_time <= end_time:
            x = int(current_time * self.time_scale.pixels_per_second)
            
            # 主刻度线
            painter.drawLine(x, ruler_height - 10, x, ruler_height)
            
            # 时间标签
            time_text = self._format_time(current_time)
            painter.drawText(x + 2, ruler_height - 12, time_text)
            
            current_time += self.time_scale.major_tick_interval
        
        # 次刻度
        current_time = start_time
        while current_time <= end_time:
            x = int(current_time * self.time_scale.pixels_per_second)
            
            # 次刻度线
            painter.drawLine(x, ruler_height - 5, x, ruler_height)
            
            current_time += self.time_scale.minor_tick_interval
    
    def _draw_tracks(self, painter: QPainter):
        """绘制轨道"""
        if not self.project:
            return
        
        track_y = 30  # 时间刻度高度
        track_height = 60
        
        for track in self.project.video_tracks + self.project.audio_tracks:
            # 轨道背景
            track_rect = QRect(0, track_y, self.width(), track_height)
            
            if track.track_id in self.selection_info.selected_tracks:
                # 选中的轨道
                painter.fillRect(track_rect, QColor(70, 130, 180, 100))
            else:
                # 普通轨道
                if self.is_dark_theme:
                    painter.fillRect(track_rect, QColor(40, 40, 40))
                else:
                    painter.fillRect(track_rect, QColor(230, 230, 230))
            
            # 轨道边框
            painter.setPen(QPen(QColor(80, 80, 80) if self.is_dark_theme else QColor(180, 180, 180), 1))
            painter.drawRect(track_rect)
            
            # 轨道标签
            painter.setPen(QPen(QColor(255, 255, 255) if self.is_dark_theme else QColor(0, 0, 0), 1))
            painter.drawText(5, track_y + 20, f"{track.name} ({track.track_type})")
            
            track_y += track_height + 5
    
    def _draw_clips(self, painter: QPainter):
        """绘制片段"""
        if not self.project:
            return
        
        track_y = 30  # 时间刻度高度
        track_height = 60
        
        # 绘制视频轨道片段
        for track in self.project.video_tracks:
            for clip in track.clips:
                self._draw_clip(painter, clip, track_y, track_height)
            
            track_y += track_height + 5
        
        # 绘制音频轨道片段
        for track in self.project.audio_tracks:
            for clip in track.clips:
                self._draw_clip(painter, clip, track_y, track_height)
            
            track_y += track_height + 5
    
    def _draw_clip(self, painter: QPainter, clip, track_y: int, track_height: int):
        """绘制单个片段"""
        x = int(clip.position * self.time_scale.pixels_per_second)
        width = int(clip.duration * self.time_scale.pixels_per_second)
        clip_rect = QRect(x, track_y + 5, width, track_height - 10)
        
        # 片段颜色
        if clip.clip_id in self.selection_info.selected_clips:
            color = QColor(70, 130, 180)
        else:
            color = QColor(100, 150, 200)
        
        # 绘制片段
        painter.fillRect(clip_rect, color)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawRect(clip_rect)
        
        # 绘制片段标签
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        text_rect = QRect(x + 5, track_y + 10, width - 10, track_height - 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, clip.name)
        
        # 绘制持续时间
        duration_text = self._format_time(clip.duration)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, duration_text)
    
    def _draw_playhead(self, painter: QPainter):
        """绘制播放头"""
        x = int(self.playhead_time * self.time_scale.pixels_per_second)
        
        # 播放头线
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawLine(x, 0, x, self.height())
        
        # 播放头三角形
        triangle_points = [
            QPoint(x - 5, 0),
            QPoint(x + 5, 0),
            QPoint(x, 10)
        ]
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        painter.drawPolygon(QPolygon(triangle_points))
    
    def _draw_selection(self, painter: QPainter):
        """绘制选择区域"""
        if (self.selection_info.selection_start < self.selection_info.selection_end and
            self.selection_info.selection_end > 0):
            
            start_x = int(self.selection_info.selection_start * self.time_scale.pixels_per_second)
            end_x = int(self.selection_info.selection_end * self.time_scale.pixels_per_second)
            selection_rect = QRect(start_x, 0, end_x - start_x, self.height())
            
            painter.fillRect(selection_rect, QColor(70, 130, 180, 50))
            painter.setPen(QPen(QColor(70, 130, 180), 1))
            painter.drawRect(selection_rect)
    
    def _format_time(self, time_seconds: float) -> str:
        """格式化时间"""
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)
        milliseconds = int((time_seconds % 1) * 100)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
    
    def _time_to_x(self, time: float) -> int:
        """时间转换为X坐标"""
        return int(time * self.time_scale.pixels_per_second)
    
    def _x_to_time(self, x: int) -> float:
        """X坐标转换为时间"""
        return x / self.time_scale.pixels_per_second
    
    def _get_clip_at_position(self, x: int, y: int) -> Tuple[Optional[object], Optional[str], Optional[float]]:
        """获取指定位置的片段"""
        if not self.project:
            return None, None, None
        
        time = self._x_to_time(x)
        track_y = 30
        track_height = 60
        
        # 检查视频轨道
        for track in self.project.video_tracks:
            if track_y <= y <= track_y + track_height:
                for clip in track.clips:
                    if (clip.position <= time <= clip.position + clip.duration):
                        return clip, track.track_id, clip.position
            
            track_y += track_height + 5
        
        # 检查音频轨道
        for track in self.project.audio_tracks:
            if track_y <= y <= track_y + track_height:
                for clip in track.clips:
                    if (clip.position <= time <= clip.position + clip.duration):
                        return clip, track.track_id, clip.position
            
            track_y += track_height + 5
        
        return None, None, None
    
    def _get_clip_edge(self, clip, x: int) -> Optional[str]:
        """获取片段边缘"""
        clip_x = int(clip.position * self.time_scale.pixels_per_second)
        clip_width = int(clip.duration * self.time_scale.pixels_per_second)
        
        edge_tolerance = 5
        
        if abs(x - clip_x) <= edge_tolerance:
            return 'left'
        elif abs(x - (clip_x + clip_width)) <= edge_tolerance:
            return 'right'
        
        return None
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.position().x(), event.position().y()
            
            # 检查是否点击了片段
            clip, track_id, clip_time = self._get_clip_at_position(int(x), int(y))
            
            if clip:
                # 检查是否点击了片段边缘（调整大小）
                edge = self._get_clip_edge(clip, int(x))
                if edge:
                    self.resizing_clip = clip
                    self.resize_edge = edge
                    self.drag_start_pos = event.position()
                    self.drag_start_time = clip.duration if edge == 'right' else 0
                else:
                    # 选择片段
                    self.dragging_clip = clip
                    self.drag_start_pos = event.position()
                    self.drag_start_time = clip.position
                
                # 更新选择
                if clip.clip_id not in self.selection_info.selected_clips:
                    self.selection_info.selected_clips = [clip.clip_id]
                    self.selection_changed.emit(self.selection_info)
                
                self.clip_selected.emit(clip)
            else:
                # 点击空白区域，清除选择
                self.selection_info.selected_clips = []
                self.selection_changed.emit(self.selection_info)
                
                # 设置播放头位置
                time = self._x_to_time(int(x))
                self.set_current_time(time)
                self.time_clicked.emit(time)
        
        self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        x, y = event.position().x(), event.position().y()
        
        if self.dragging_clip and event.buttons() & Qt.MouseButton.LeftButton:
            # 拖动片段
            delta_x = x - self.drag_start_pos.x()
            delta_time = self._x_to_time(int(delta_x))
            new_time = max(0, self.drag_start_time + delta_time)
            
            self.dragging_clip.position = new_time
            self.clip_moved.emit(self.dragging_clip.clip_id, new_time)
            self.update()
        
        elif self.resizing_clip and event.buttons() & Qt.MouseButton.LeftButton:
            # 调整片段大小
            delta_x = x - self.drag_start_pos.x()
            delta_time = self._x_to_time(int(delta_x))
            
            if self.resize_edge == 'right':
                new_duration = max(0.1, self.drag_start_time + delta_time)
                self.resizing_clip.duration = new_duration
                self.clip_resized.emit(self.resizing_clip.clip_id, self.resizing_clip.position, new_duration)
            elif self.resize_edge == 'left':
                new_duration = max(0.1, self.drag_start_time - delta_time)
                new_position = self.resizing_clip.position + delta_time
                if new_position >= 0:
                    self.resizing_clip.position = new_position
                    self.resizing_clip.duration = new_duration
                    self.clip_resized.emit(self.resizing_clip.clip_id, new_position, new_duration)
            
            self.update()
        else:
            # 更新鼠标样式
            clip, _, _ = self._get_clip_at_position(int(x), int(y))
            if clip:
                edge = self._get_clip_edge(clip, int(x))
                if edge == 'left':
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif edge == 'right':
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.dragging_clip = None
        self.resizing_clip = None
        self.resize_edge = None
        self.drag_start_pos = None
        self.drag_start_time = 0.0
    
    def mouseDoubleClickEvent(self, event):
        """双击事件"""
        x, y = event.position().x(), event.position().y()
        clip, _, _ = self._get_clip_at_position(int(x), int(y))
        
        if clip:
            # 双击片段，可以打开片段属性编辑器
            self.clip_selected.emit(clip)
    
    def wheelEvent(self, event):
        """滚轮事件"""
        # 缩放时间轴
        delta = event.angleDelta().y()
        if delta > 0:
            # 放大
            self.time_scale.pixels_per_second *= 1.1
        else:
            # 缩小
            self.time_scale.pixels_per_second *= 0.9
        
        self.time_scale.pixels_per_second = max(10, min(1000, self.time_scale.pixels_per_second))
        self.update()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete:
            # 删除选中的片段
            if self.selection_info.selected_clips and self.project:
                for clip_id in self.selection_info.selected_clips:
                    self._remove_clip(clip_id)
                
                self.selection_info.selected_clips = []
                self.selection_changed.emit(self.selection_info)
                self.update()
        
        elif event.key() == Qt.Key.Key_Space:
            # 空格键播放/暂停
            if self.playback_timer.isActive():
                self.playback_timer.stop()
            else:
                self.playback_timer.start()
    
    def _remove_clip(self, clip_id: str):
        """移除片段"""
        if not self.project:
            return
        
        # 从视频轨道中移除
        for track in self.project.video_tracks:
            track.clips = [clip for clip in track.clips if clip.clip_id != clip_id]
        
        # 从音频轨道中移除
        for track in self.project.audio_tracks:
            track.clips = [clip for clip in track.clips if clip.clip_id != clip_id]
    
    def _update_playback(self):
        """更新播放"""
        self.playhead_time += 0.05  # 50ms
        self.update()
        
        # 检查是否到达项目末尾
        if self.project:
            project_duration = self._get_project_duration()
            if self.playhead_time >= project_duration:
                self.playback_timer.stop()
                self.playhead_time = project_duration
                self.update()
    
    def _get_project_duration(self) -> float:
        """获取项目时长"""
        if not self.project:
            return 0.0
        
        max_duration = 0.0
        
        for track in self.project.video_tracks + self.project.audio_tracks:
            for clip in track.clips:
                clip_end = clip.position + clip.duration
                if clip_end > max_duration:
                    max_duration = clip_end
        
        return max_duration
    
    def start_playback(self):
        """开始播放"""
        self.playback_timer.start()
    
    def pause_playback(self):
        """暂停播放"""
        self.playback_timer.stop()
    
    def stop_playback(self):
        """停止播放"""
        self.playback_timer.stop()
        self.playhead_time = 0.0
        self.update()
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self.update()


class ProfessionalTimelineEditor(QWidget):
    """专业时间轴编辑器"""
    
    # 信号定义
    project_loaded = pyqtSignal(TimelineProject)  # 项目加载完成信号
    project_saved = pyqtSignal(TimelineProject)  # 项目保存完成信号
    clip_selected = pyqtSignal(object)  # 片段选中信号
    time_changed = pyqtSignal(float)  # 时间变更信号
    playback_started = pyqtSignal()  # 播放开始信号
    playback_paused = pyqtSignal()  # 播放暂停信号
    playback_stopped = pyqtSignal()  # 播放停止信号
    
    def __init__(self, video_engine: VideoProcessingEngine = None, parent=None):
        super().__init__(parent)
        
        self.is_dark_theme = False
        self.video_engine = video_engine or VideoProcessingEngine()
        self.current_project = None
        self.state = TimelineState.IDLE
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # 时间轴画布
        self.canvas = TimelineCanvas()
        layout.addWidget(self.canvas, 1)
        
        # 时间控制
        self.time_controls = self._create_time_controls()
        layout.addWidget(self.time_controls)
    
    def _create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        
        # 文件操作
        new_action = toolbar.addAction("📄 新建")
        new_action.triggered.connect(self.create_new_project)
        
        open_action = toolbar.addAction("📁 打开")
        open_action.triggered.connect(self._open_project)
        
        save_action = toolbar.addAction("💾 保存")
        save_action.triggered.connect(self._save_project)
        
        toolbar.addSeparator()
        
        # 编辑操作
        add_video_action = toolbar.addAction("🎥 添加视频")
        add_video_action.triggered.connect(self._add_video_clip)
        
        add_audio_action = toolbar.addAction("🎵 添加音频")
        add_audio_action.triggered.connect(self._add_audio_clip)
        
        add_text_action = toolbar.addAction("📝 添加文字")
        add_text_action.triggered.connect(self._add_text_clip)
        
        toolbar.addSeparator()
        
        # 播放控制
        self.play_action = toolbar.addAction("▶️ 播放")
        self.play_action.triggered.connect(self._toggle_playback)
        
        stop_action = toolbar.addAction("⏹️ 停止")
        stop_action.triggered.connect(self._stop_playback)
        
        toolbar.addSeparator()
        
        # 缩放控制
        zoom_in_action = toolbar.addAction("🔍 放大")
        zoom_in_action.triggered.connect(self._zoom_in)
        
        zoom_out_action = toolbar.addAction("🔍 缩小")
        zoom_out_action.triggered.connect(self._zoom_out)
        
        zoom_fit_action = toolbar.addAction("📏 适应")
        zoom_fit_action.triggered.connect(self._zoom_fit)
        
        return toolbar
    
    def _create_time_controls(self) -> QWidget:
        """创建时间控制"""
        controls = QWidget()
        controls.setFixedHeight(60)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 当前时间显示
        self.time_label = QLabel("00:00:00")
        self.time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.time_label)
        
        layout.addSpacing(20)
        
        # 时间滑块
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 1000)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self._on_time_slider_changed)
        layout.addWidget(self.time_slider, 1)
        
        layout.addSpacing(20)
        
        # 总时长显示
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.duration_label)
        
        return controls
    
    def _apply_styles(self):
        """应用样式"""
        colors = ColorScheme.DARK_THEME if self.is_dark_theme else ColorScheme.LIGHT_THEME
        
        self.setStyleSheet(f"""
            ProfessionalTimelineEditor {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_MD}px;
            }}
            
            QToolBar {{
                background-color: {colors['surface_variant']};
                border: none;
                border-bottom: 1px solid {colors['border']};
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
                min-width: 80px;
            }}
            
            QToolButton:hover {{
                background: {colors['highlight']};
            }}
            
            QToolButton:pressed {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
        """)
        
        # 更新画布主题
        self.canvas.set_theme(self.is_dark_theme)
    
    def _connect_signals(self):
        """连接信号"""
        self.canvas.clip_selected.connect(self._on_clip_selected)
        self.canvas.clip_moved.connect(self._on_clip_moved)
        self.canvas.clip_resized.connect(self._on_clip_resized)
        self.canvas.time_clicked.connect(self._on_time_clicked)
        self.canvas.selection_changed.connect(self._on_selection_changed)
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self._apply_styles()
    
    def create_new_project(self, name: str = "新项目") -> TimelineProject:
        """创建新项目"""
        project = TimelineProject(name=name)
        self.current_project = project
        self.canvas.set_project(project)
        self.project_loaded.emit(project)
        return project
    
    def _open_project(self):
        """打开项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", 
            "项目文件 (*.json *.cineai)"
        )
        
        if file_path:
            try:
                project = self.video_engine.load_project(file_path)
                self.current_project = project
                self.canvas.set_project(project)
                self.project_loaded.emit(project)
                
                # 更新时长显示
                self._update_duration_display()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开项目失败: {e}")
    
    def _save_project(self):
        """保存项目"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "没有可保存的项目")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "", 
            "项目文件 (*.json *.cineai)"
        )
        
        if file_path:
            try:
                self.video_engine.save_project(self.current_project, file_path)
                self.project_saved.emit(self.current_project)
                QMessageBox.information(self, "成功", "项目保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存项目失败: {e}")
    
    def _add_video_clip(self):
        """添加视频片段"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先创建项目")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )
        
        if file_path:
            self.add_clip_to_track("video_1", file_path, self.canvas.current_time)
    
    def _add_audio_clip(self):
        """添加音频片段"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先创建项目")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", 
            "音频文件 (*.mp3 *.wav *.aac *.flac)"
        )
        
        if file_path:
            self.add_clip_to_track("audio_1", file_path, self.canvas.current_time)
    
    def _add_text_clip(self):
        """添加文字片段"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先创建项目")
            return
        
        text, ok = QInputDialog.getText(self, "添加文字", "请输入文字内容:")
        if ok and text:
            self.add_text_clip_to_track("text_1", text, self.canvas.current_time, 5.0)
    
    def add_clip_to_track(self, track_id: str, file_path: str, position: float) -> bool:
        """添加片段到轨道"""
        if not self.current_project:
            return False
        
        try:
            # 获取视频信息
            video_info = self.video_engine.get_video_info(file_path)
            
            # 创建视频片段
            clip = TimelineClip(
                clip_id=str(uuid.uuid4()),
                name=os.path.basename(file_path),
                file_path=file_path,
                position=position,
                duration=video_info.duration,
                width=video_info.width,
                height=video_info.height
            )
            
            # 添加到轨道
            for track in self.current_project.video_tracks:
                if track.track_id == track_id:
                    track.clips.append(clip)
                    self.canvas.update()
                    return True
            
            # 如果轨道不存在，创建新轨道
            new_track = TimelineTrack(
                track_id=track_id,
                name=f"视频轨道 {len(self.current_project.video_tracks) + 1}",
                clips=[clip]
            )
            self.current_project.video_tracks.append(new_track)
            self.canvas.update()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加片段失败: {e}")
            return False
    
    def add_text_clip_to_track(self, track_id: str, text: str, position: float, duration: float) -> bool:
        """添加文字片段到轨道"""
        if not self.current_project:
            return False
        
        try:
            # 创建文字片段
            clip = TimelineClip(
                clip_id=str(uuid.uuid4()),
                name=f"文字: {text[:20]}...",
                text=text,
                position=position,
                duration=duration
            )
            
            # 添加到轨道
            for track in self.current_project.text_tracks:
                if track.track_id == track_id:
                    track.clips.append(clip)
                    self.canvas.update()
                    return True
            
            # 如果轨道不存在，创建新轨道
            new_track = Track(
                track_id=track_id,
                name=f"文字轨道 {len(self.current_project.text_tracks) + 1}",
                track_type="text",
                clips=[clip]
            )
            self.current_project.text_tracks.append(new_track)
            self.canvas.update()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加文字片段失败: {e}")
            return False
    
    def _toggle_playback(self):
        """切换播放状态"""
        if self.canvas.playback_timer.isActive():
            self.canvas.pause_playback()
            self.play_action.setText("▶️ 播放")
            self.playback_paused.emit()
        else:
            self.canvas.start_playback()
            self.play_action.setText("⏸️ 暂停")
            self.playback_started.emit()
    
    def _stop_playback(self):
        """停止播放"""
        self.canvas.stop_playback()
        self.play_action.setText("▶️ 播放")
        self.playback_stopped.emit()
    
    def _zoom_in(self):
        """放大"""
        self.canvas.time_scale.pixels_per_second *= 1.2
        self.canvas.update()
    
    def _zoom_out(self):
        """缩小"""
        self.canvas.time_scale.pixels_per_second *= 0.8
        self.canvas.update()
    
    def _zoom_fit(self):
        """适应窗口"""
        if self.current_project:
            project_duration = self.canvas._get_project_duration()
            if project_duration > 0:
                self.canvas.time_scale.pixels_per_second = self.canvas.width() / project_duration
                self.canvas.update()
    
    def _on_clip_selected(self, clip):
        """片段选中处理"""
        self.clip_selected.emit(clip)
    
    def _on_clip_moved(self, clip_id: str, position: float):
        """片段移动处理"""
        # 这里可以添加片段移动后的处理逻辑
        pass
    
    def _on_clip_resized(self, clip_id: str, position: float, duration: float):
        """片段调整大小处理"""
        # 这里可以添加片段调整大小后的处理逻辑
        pass
    
    def _on_time_clicked(self, time: float):
        """时间点击处理"""
        self.time_changed.emit(time)
        self._update_time_display(time)
    
    def _on_selection_changed(self, selection_info: SelectionInfo):
        """选择变更处理"""
        # 这里可以添加选择变更后的处理逻辑
        pass
    
    def _on_time_slider_changed(self, value: int):
        """时间滑块变更处理"""
        if self.current_project:
            project_duration = self.canvas._get_project_duration()
            time = (value / 1000.0) * project_duration
            self.canvas.set_current_time(time)
            self._update_time_display(time)
    
    def _update_time_display(self, time: float):
        """更新时间显示"""
        hours = int(time // 3600)
        minutes = int((time % 3600) // 60)
        seconds = int(time % 60)
        self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _update_duration_display(self):
        """更新时长显示"""
        if self.current_project:
            duration = self.canvas._get_project_duration()
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # 更新滑块范围
            self.time_slider.setRange(0, 1000)
    
    def export_project(self, output_path: str, config: ProcessingConfig) -> bool:
        """导出项目"""
        if not self.current_project:
            return False
        
        try:
            return self.video_engine.export_project(self.current_project, output_path, config)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出项目失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'canvas'):
            self.canvas.playback_timer.stop()


# 工厂函数
def create_timeline_editor(video_engine: VideoProcessingEngine = None, parent=None) -> ProfessionalTimelineEditor:
    """创建时间轴编辑器"""
    return ProfessionalTimelineEditor(video_engine, parent)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建时间轴编辑器
    editor = create_timeline_editor()
    editor.setWindowTitle("时间轴编辑器测试")
    editor.resize(1200, 600)
    editor.show()
    
    # 创建测试项目
    project = editor.create_new_project("测试项目")
    
    sys.exit(app.exec())