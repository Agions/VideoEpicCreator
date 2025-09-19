#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化版时间轴编辑器 - 高性能、流畅的多轨道编辑体验
解决UI重绘、事件处理和数据结构性能问题
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref
import threading
from collections import OrderedDict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSlider, QSpinBox, QComboBox,
    QCheckBox, QToolBar, QToolButton, QStackedWidget,
    QScrollArea, QSizePolicy, QSpacerItem, QGroupBox, QRadioButton,
    QButtonGroup, QDialog, QFileDialog, QMessageBox, QApplication,
    QSplitter, QMenu, QInputDialog, QProgressBar, QLineEdit,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsProxyWidget, QStyleOptionGraphicsItem
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker, QPointF, QRectF, QMimeData, \
    QRect, QPoint, QObject, pyqtSlot, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPixmap, QImage, QBrush, QPen,
    QLinearGradient, QRadialGradient, QPainterPath, QTransform,
    QCursor, QFontMetrics, QDragEnterEvent, QDropEvent, QWheelEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QIcon, QPalette,
    QDrag, QAction, QKeySequence, QContextMenuEvent, QDoubleValidator,
    QIntValidator, QFontDatabase, QGraphicsSceneHoverEvent
)

from app.core.optimized_video_processing_engine import OptimizedVideoProcessingEngine
from app.core.video_processing_engine import TimelineProject, TimelineTrack, TimelineClip, ProcessingConfig, VideoInfo
from app.ui.professional_ui_system import ProfessionalStyleEngine, UITheme, ColorScheme, FontScheme, SpacingScheme
from .timeline_widget import TimelineRuler

logger = logging.getLogger(__name__)


class TimelineZoom(Enum):
    """时间轴缩放级别"""
    FRAME = "frame"        # 帧级别
    SECOND = "second"      # 秒级别
    MINUTE = "minute"      # 分钟级别
    HOUR = "hour"          # 小时级别


class ClipState(Enum):
    """片段状态"""
    NORMAL = "normal"
    SELECTED = "selected"
    HOVERED = "hovered"
    DRAGGING = "dragging"
    RESIZING = "resizing"


class RenderMode(Enum):
    """渲染模式"""
    CPU = "cpu"                    # CPU渲染
    OPENGL = "opengl"              # OpenGL加速
    HARDWARE_ACCELERATED = "hardware"  # 硬件加速


@dataclass
class TimelineCache:
    """时间轴缓存"""
    clip_cache: Dict[str, Any] = field(default_factory=dict)
    track_cache: Dict[str, Any] = field(default_factory=dict)
    render_cache: Dict[str, QPixmap] = field(default_factory=dict)
    max_cache_size: int = 1000
    
    def add_clip(self, clip_id: str, clip_data: Any):
        """添加片段到缓存"""
        if len(self.clip_cache) >= self.max_cache_size:
            # 删除最旧的项
            oldest_key = next(iter(self.clip_cache))
            del self.clip_cache[oldest_key]
        self.clip_cache[clip_id] = clip_data
    
    def get_clip(self, clip_id: str) -> Optional[Any]:
        """获取片段缓存"""
        return self.clip_cache.get(clip_id)
    
    def clear(self):
        """清空缓存"""
        self.clip_cache.clear()
        self.track_cache.clear()
        self.render_cache.clear()


@dataclass
class PerformanceConfig:
    """性能配置"""
    render_mode: RenderMode = RenderMode.CPU
    enable_caching: bool = True
    cache_size: int = 1000
    enable_virtualization: bool = True
    virtualization_threshold: int = 100  # 虚拟化阈值
    enable_animations: bool = True
    animation_duration: int = 200  # 毫秒
    enable_precise_rendering: bool = True
    max_fps: int = 60


class OptimizedTimelineClip(QGraphicsRectItem):
    """优化版时间轴片段"""
    
    # 信号定义
    clip_selected = pyqtSignal(str)
    clip_moved = pyqtSignal(str, float)
    clip_resized = pyqtSignal(str, float, float)
    clip_double_clicked = pyqtSignal(str)
    
    def __init__(self, clip: TimelineClip, timeline_ruler, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.timeline_ruler = timeline_ruler
        self.state = ClipState.NORMAL
        self.drag_start_pos = None
        self.resize_handle = None
        self.thumbnail = None
        self.cache_key = f"clip_{clip.clip_id}"
        
        # 性能优化
        self.needs_update = True
        self.last_render_time = 0
        self.render_count = 0
        
        # 设置属性
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # 初始化
        self._initialize_clip()
        self._load_thumbnail_async()
    
    def _initialize_clip(self):
        """初始化片段"""
        # 计算尺寸
        width = self.clip.duration * self.timeline_ruler.pixels_per_second
        height = 80
        
        # 设置矩形
        self.setRect(0, 0, width, height)
        
        # 设置位置
        x = self.clip.position * self.timeline_ruler.pixels_per_second
        self.setPos(x, 0)
        
        # 设置Z值
        self.setZValue(1)
    
    def _load_thumbnail_async(self):
        """异步加载缩略图"""
        def load_thumbnail():
            try:
                # 这里应该从视频文件中提取缩略图
                # 目前使用占位符
                self.thumbnail = QPixmap(100, 60)
                self.thumbnail.fill(QColor(100, 100, 100))
                self.update()
            except Exception as e:
                logger.error(f"加载缩略图失败: {e}")
        
        # 在后台线程加载
        threading.Thread(target=load_thumbnail, daemon=True).start()
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        """优化的绘制方法"""
        start_time = time.time()
        
        # 检查是否需要更新
        if not self.needs_update and self.last_render_time > 0:
            return
        
        # 启用抗锯齿
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 绘制背景
        self._draw_background(painter)
        
        # 绘制缩略图
        if self.thumbnail:
            self._draw_thumbnail(painter)
        
        # 绘制边框
        self._draw_border(painter)
        
        # 绘制文本
        self._draw_text(painter)
        
        # 绘制调整手柄
        if self.state == ClipState.SELECTED:
            self._draw_resize_handles(painter)
        
        # 更新性能统计
        self.render_count += 1
        self.last_render_time = time.time() - start_time
        self.needs_update = False
    
    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        rect = self.rect()
        
        if self.state == ClipState.SELECTED:
            color = QColor(70, 130, 180)  # 钢蓝色
        elif self.state == ClipState.HOVERED:
            color = QColor(100, 149, 237)  # 矢车菊蓝
        else:
            color = QColor(60, 60, 60)  # 深灰色
        
        painter.fillRect(rect, color)
        
        # 绘制渐变效果
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor(255, 255, 255, 30))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 30))
        painter.fillRect(rect, gradient)
    
    def _draw_thumbnail(self, painter: QPainter):
        """绘制缩略图"""
        if not self.thumbnail or self.thumbnail.isNull():
            return
        
        rect = self.rect()
        thumbnail_rect = QRectF(4, 4, rect.width() - 8, rect.height() - 20)
        
        # 缩放缩略图以适应区域
        scaled_thumbnail = self.thumbnail.scaled(
            thumbnail_rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 居中绘制
        x = thumbnail_rect.x() + (thumbnail_rect.width() - scaled_thumbnail.width()) // 2
        y = thumbnail_rect.y() + (thumbnail_rect.height() - scaled_thumbnail.height()) // 2
        
        painter.drawPixmap(x, y, scaled_thumbnail)
    
    def _draw_border(self, painter: QPainter):
        """绘制边框"""
        rect = self.rect()
        
        if self.state == ClipState.SELECTED:
            pen = QPen(QColor(255, 215, 0), 2)  # 金色边框
        else:
            pen = QPen(QColor(100, 100, 100), 1)
        
        painter.setPen(pen)
        painter.drawRect(rect)
    
    def _draw_text(self, painter: QPainter):
        """绘制文本"""
        rect = self.rect()
        
        # 设置字体
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # 设置文本颜色
        painter.setPen(QColor(255, 255, 255))
        
        # 绘制文件名
        file_name = os.path.basename(self.clip.file_path)
        if len(file_name) > 20:
            file_name = file_name[:17] + "..."
        
        text_rect = QRectF(4, rect.height() - 16, rect.width() - 8, 12)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, file_name)
        
        # 绘制时长
        duration_text = self._format_duration(self.clip.duration)
        duration_rect = QRectF(rect.width() - 40, rect.height() - 16, 36, 12)
        painter.drawText(duration_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, duration_text)
    
    def _draw_resize_handles(self, painter: QPainter):
        """绘制调整手柄"""
        rect = self.rect()
        
        # 左侧手柄
        left_handle = QRectF(0, 0, 6, rect.height())
        painter.fillRect(left_handle, QColor(255, 215, 0, 180))
        
        # 右侧手柄
        right_handle = QRectF(rect.width() - 6, 0, 6, rect.height())
        painter.fillRect(right_handle, QColor(255, 215, 0, 180))
    
    def _format_duration(self, duration: float) -> str:
        """格式化时长"""
        if duration < 60:
            return f"{duration:.1f}s"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = duration % 60
            return f"{minutes}:{seconds:04.1f}"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60
            return f"{hours}:{minutes:02d}:{seconds:04.1f}"
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            
            # 检查是否点击了调整手柄
            if self.state == ClipState.SELECTED:
                if event.pos().x() <= 6:
                    self.resize_handle = 'left'
                    self.state = ClipState.RESIZING
                elif event.pos().x() >= self.rect().width() - 6:
                    self.resize_handle = 'right'
                    self.state = ClipState.RESIZING
                else:
                    self.state = ClipState.DRAGGING
            else:
                self.state = ClipState.DRAGGING
            
            # 发送选中信号
            self.clip_selected.emit(self.clip.clip_id)
            
            self.needs_update = True
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if self.state == ClipState.DRAGGING and self.drag_start_pos:
            # 计算移动距离
            delta = event.pos() - self.drag_start_pos
            time_delta = delta.x() / self.timeline_ruler.pixels_per_second
            
            # 限制移动范围
            new_position = max(0, self.clip.position + time_delta)
            
            # 发送移动信号
            self.clip_moved.emit(self.clip.clip_id, new_position)
            
        elif self.state == ClipState.RESIZING and self.drag_start_pos:
            # 计算调整大小
            delta = event.pos() - self.drag_start_pos
            time_delta = delta.x() / self.timeline_ruler.pixels_per_second
            
            if self.resize_handle == 'left':
                new_start = max(0, self.clip.position + time_delta)
                new_duration = self.clip.duration - time_delta
            else:
                new_start = self.clip.position
                new_duration = max(0.1, self.clip.duration + time_delta)
            
            # 发送调整大小信号
            self.clip_resized.emit(self.clip.clip_id, new_start, new_duration)
        
        # 更新鼠标样式
        self._update_cursor(event.pos())
        
        self.needs_update = True
        self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.state = ClipState.SELECTED
            self.drag_start_pos = None
            self.resize_handle = None
            
            self.needs_update = True
            self.update()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """鼠标双击事件"""
        self.clip_double_clicked.emit(self.clip.clip_id)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent):
        """鼠标进入事件"""
        if self.state == ClipState.NORMAL:
            self.state = ClipState.HOVERED
            self.needs_update = True
            self.update()
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        """鼠标离开事件"""
        if self.state == ClipState.HOVERED:
            self.state = ClipState.NORMAL
            self.needs_update = True
            self.update()
    
    def _update_cursor(self, pos: QPointF):
        """更新鼠标样式"""
        if self.state == ClipState.SELECTED:
            if pos.x() <= 6 or pos.x() >= self.rect().width() - 6:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """项目变更处理"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 更新片段位置
            new_pos = value
            new_time = new_pos.x() / self.timeline_ruler.pixels_per_second
            self.clip.position = max(0, new_time)
        
        return super().itemChange(change, value)
    
    def update_position(self):
        """更新片段位置"""
        x = self.clip.position * self.timeline_ruler.pixels_per_second
        self.setPos(x, 0)
        self.needs_update = True
        self.update()


class OptimizedTimelineTrack(QGraphicsItem):
    """优化版时间轴轨道"""
    
    # 信号定义
    track_selected = pyqtSignal(str)
    track_visibility_changed = pyqtSignal(str, bool)
    track_lock_changed = pyqtSignal(str, bool)
    
    def __init__(self, track: TimelineTrack, timeline_ruler, parent=None):
        super().__init__(parent)
        self.track = track
        self.timeline_ruler = timeline_ruler
        self.clips = {}
        self.is_selected = False
        self.cache = TimelineCache()
        
        # 性能优化
        self.visible_items = set()
        self.last_viewport = QRectF()
        self.needs_update = True
        
        # 设置属性
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemHasNoContents, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # 初始化
        self._initialize_track()
        self._create_clips()
    
    def _initialize_track(self):
        """初始化轨道"""
        # 设置轨道尺寸
        self.track_width = self.timeline_ruler.pixels_per_second * 60  # 60秒默认
        self.track_height = 100
        
        # 设置Z值
        self.setZValue(0)
    
    def _create_clips(self):
        """创建片段"""
        for clip in self.track.clips:
            clip_item = OptimizedTimelineClip(clip, self.timeline_ruler, self)
            clip_item.clip_selected.connect(self._on_clip_selected)
            clip_item.clip_moved.connect(self._on_clip_moved)
            clip_item.clip_resized.connect(self._on_clip_resized)
            clip_item.clip_double_clicked.connect(self._on_clip_double_clicked)
            
            self.clips[clip.clip_id] = clip_item
            self.cache.add_clip(clip.clip_id, clip)
    
    def boundingRect(self) -> QRectF:
        """获取边界矩形"""
        return QRectF(0, 0, self.track_width, self.track_height)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        """绘制轨道"""
        if not self.needs_update:
            return
        
        # 启用抗锯齿
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制轨道背景
        self._draw_background(painter)
        
        # 绘制轨道头部
        self._draw_track_header(painter)
        
        # 绘制时间刻度
        self._draw_time_scale(painter)
        
        self.needs_update = False
    
    def _draw_background(self, painter: QPainter):
        """绘制背景"""
        rect = self.boundingRect()
        
        # 轨道背景
        if self.is_selected:
            painter.fillRect(rect, QColor(50, 50, 70))
        else:
            painter.fillRect(rect, QColor(40, 40, 40))
        
        # 绘制网格线
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        
        # 每秒一条线
        for i in range(0, int(self.track_width), int(self.timeline_ruler.pixels_per_second)):
            painter.drawLine(i, 0, i, self.track_height)
    
    def _draw_track_header(self, painter: QPainter):
        """绘制轨道头部"""
        header_rect = QRectF(0, 0, 150, self.track_height)
        
        # 轨道头部背景
        painter.fillRect(header_rect, QColor(30, 30, 30))
        
        # 轨道名称
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        track_type_names = {
            "video": "视频轨道",
            "audio": "音频轨道",
            "subtitle": "字幕轨道"
        }
        
        name = track_type_names.get(self.track.track_type, self.track.track_type)
        painter.drawText(header_rect.adjusted(10, 10, -10, -10), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, name)
    
    def _draw_time_scale(self, painter: QPainter):
        """绘制时间刻度"""
        scale_rect = QRectF(150, 0, self.track_width - 150, 20)
        
        # 刻度背景
        painter.fillRect(scale_rect, QColor(25, 25, 25))
        
        # 绘制刻度
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 8))
        
        # 每秒一个刻度
        for i in range(0, int(self.track_width), int(self.timeline_ruler.pixels_per_second)):
            x = 150 + i
            painter.drawLine(x, 0, x, 10)
            
            # 时间标签
            time_text = f"{i // self.timeline_ruler.pixels_per_second}s"
            painter.drawText(x + 2, 15, time_text)
    
    def _on_clip_selected(self, clip_id: str):
        """片段选中处理"""
        # 更新选中状态
        for clip_item in self.clips.values():
            if clip_item.clip.clip_id == clip_id:
                clip_item.state = ClipState.SELECTED
            else:
                clip_item.state = ClipState.NORMAL
            clip_item.needs_update = True
            clip_item.update()
    
    def _on_clip_moved(self, clip_id: str, new_position: float):
        """片段移动处理"""
        # 更新片段位置
        for clip in self.track.clips:
            if clip.clip_id == clip_id:
                clip.position = new_position
                break
        
        # 重新排序片段
        self.track.clips.sort(key=lambda x: x.position)
        
        # 更新片段组件位置
        if clip_id in self.clips:
            self.clips[clip_id].update_position()
    
    def _on_clip_resized(self, clip_id: str, new_start: float, new_duration: float):
        """片段调整大小处理"""
        # 更新片段
        for clip in self.track.clips:
            if clip.clip_id == clip_id:
                clip.position = new_start
                clip.duration = new_duration
                break
        
        # 更新片段组件
        if clip_id in self.clips:
            clip_item = self.clips[clip_id]
            clip_item.clip = clip
            clip_item.update_position()
    
    def _on_clip_double_clicked(self, clip_id: str):
        """片段双击处理"""
        # 可以在这里打开片段属性对话框
        pass
    
    def add_clip(self, clip: TimelineClip):
        """添加片段"""
        self.track.clips.append(clip)
        
        clip_item = OptimizedTimelineClip(clip, self.timeline_ruler, self)
        clip_item.clip_selected.connect(self._on_clip_selected)
        clip_item.clip_moved.connect(self._on_clip_moved)
        clip_item.clip_resized.connect(self._on_clip_resized)
        clip_item.clip_double_clicked.connect(self._on_clip_double_clicked)
        
        self.clips[clip.clip_id] = clip_item
        self.cache.add_clip(clip.clip_id, clip_item)
        
        self.needs_update = True
        self.update()
    
    def remove_clip(self, clip_id: str):
        """移除片段"""
        # 从轨道中移除
        self.track.clips = [clip for clip in self.track.clips if clip.clip_id != clip_id]
        
        # 移除组件
        if clip_id in self.clips:
            clip_item = self.clips[clip_id]
            scene = clip_item.scene()
            if scene:
                scene.removeItem(clip_item)
            del self.clips[clip_id]
        
        self.needs_update = True
        self.update()
    
    def update_zoom(self, new_pixels_per_second: float):
        """更新缩放"""
        self.timeline_ruler.pixels_per_second = new_pixels_per_second
        
        # 更新所有片段组件的位置
        for clip_item in self.clips.values():
            clip_item.update_position()
        
        self.needs_update = True
        self.update()


class OptimizedTimelineRuler(QGraphicsItem):
    """优化版时间轴标尺"""
    
    # 信号定义
    time_changed = pyqtSignal(float)
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, timeline_ruler, parent=None):
        super().__init__(parent)
        self.timeline_ruler = timeline_ruler
        self.current_time = 0.0
        self.drag_start_time = None
        
        # 性能优化
        self.needs_update = True
        self.cached_pixmap = None
        
        # 设置属性
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemHasNoContents, False)
        self.setZValue(2)
    
    def boundingRect(self) -> QRectF:
        """获取边界矩形"""
        return QRectF(0, 0, self.timeline_ruler.pixels_per_second * 60, 40)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        """绘制标尺"""
        if not self.needs_update and self.cached_pixmap:
            painter.drawPixmap(0, 0, self.cached_pixmap)
            return
        
        # 启用抗锯齿
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        rect = self.boundingRect()
        painter.fillRect(rect, QColor(26, 26, 26))
        
        # 绘制刻度
        self._draw_ticks(painter)
        
        # 绘制时间标签
        self._draw_time_labels(painter)
        
        # 绘制当前时间线
        self._draw_current_time_line(painter)
        
        # 缓存结果
        self.cached_pixmap = QPixmap(rect.size().toSize())
        self.cached_pixmap.fill(Qt.GlobalColor.transparent)
        
        cache_painter = QPainter(self.cached_pixmap)
        self.paint(cache_painter, option, widget)
        cache_painter.end()
        
        self.needs_update = False
    
    def _draw_ticks(self, painter: QPainter):
        """绘制刻度"""
        rect = self.boundingRect()
        width = rect.width()
        height = rect.height()
        
        # 设置画笔
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        
        # 计算刻度间隔
        pixels_per_second = self.timeline_ruler.pixels_per_second
        major_interval = self.timeline_ruler.major_tick_interval
        minor_interval = self.timeline_ruler.minor_tick_interval
        
        # 绘制主刻度
        for i in range(int(self.timeline_ruler.start_time), int(self.timeline_ruler.end_time) + 1, int(major_interval)):
            x = i * pixels_per_second
            if 0 <= x <= width:
                painter.drawLine(int(x), height - 15, int(x), height)
        
        # 绘制次刻度
        for i in range(int(self.timeline_ruler.start_time), int(self.timeline_ruler.end_time) + 1, int(minor_interval)):
            x = i * pixels_per_second
            if 0 <= x <= width and i % int(major_interval) != 0:
                painter.drawLine(int(x), height - 8, int(x), height)
    
    def _draw_time_labels(self, painter: QPainter):
        """绘制时间标签"""
        rect = self.boundingRect()
        width = rect.width()
        
        # 设置字体
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QColor(200, 200, 200))
        
        # 计算标签间隔
        pixels_per_second = self.timeline_ruler.pixels_per_second
        label_interval = self.timeline_ruler.major_tick_interval
        
        # 绘制时间标签
        for i in range(int(self.timeline_ruler.start_time), int(self.timeline_ruler.end_time) + 1, int(label_interval)):
            x = i * pixels_per_second
            if 0 <= x <= width:
                time_text = self._format_time(i)
                text_rect = QRectF(x - 20, 2, 40, 12)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, time_text)
    
    def _draw_current_time_line(self, painter: QPainter):
        """绘制当前时间线"""
        rect = self.boundingRect()
        height = rect.height()
        
        x = self.current_time * self.timeline_ruler.pixels_per_second
        
        # 绘制时间线
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawLine(int(x), 0, int(x), height)
        
        # 绘制时间标签背景
        time_text = self._format_time(self.current_time)
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        text_rect = QRectF(x - 30, height - 20, 60, 16)
        painter.fillRect(text_rect, QColor(255, 0, 0))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, time_text)
    
    def _format_time(self, time_seconds: float) -> str:
        """格式化时间"""
        if time_seconds < 60:
            return f"{time_seconds:.1f}s"
        elif time_seconds < 3600:
            minutes = int(time_seconds // 60)
            seconds = time_seconds % 60
            return f"{minutes}:{seconds:04.1f}"
        else:
            hours = int(time_seconds // 3600)
            minutes = int((time_seconds % 3600) // 60)
            seconds = time_seconds % 60
            return f"{hours}:{minutes:02d}:{seconds:04.1f}"
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_time = self.current_time
            
            # 更新当前时间
            new_time = event.pos().x() / self.timeline_ruler.pixels_per_second
            self.set_current_time(new_time)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # 更新当前时间
            new_time = event.pos().x() / self.timeline_ruler.pixels_per_second
            self.set_current_time(new_time)
    
    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件"""
        # 缩放时间轴
        delta = event.angleDelta().y()
        if delta > 0:
            # 放大
            new_pixels_per_second = self.timeline_ruler.pixels_per_second * 1.2
        else:
            # 缩小
            new_pixels_per_second = self.timeline_ruler.pixels_per_second / 1.2
        
        # 限制缩放范围
        new_pixels_per_second = max(10, min(1000, new_pixels_per_second))
        
        self.timeline_ruler.pixels_per_second = new_pixels_per_second
        self.zoom_changed.emit(new_pixels_per_second)
        
        self.needs_update = True
        self.update()
    
    def set_current_time(self, time_seconds: float):
        """设置当前时间"""
        self.current_time = max(0, time_seconds)
        self.time_changed.emit(self.current_time)
        self.needs_update = True
        self.update()


class OptimizedTimelineScene(QGraphicsScene):
    """优化版时间轴场景"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = {}
        self.ruler = None
        self.performance_config = PerformanceConfig()
        
        # 性能优化
        self.visible_items = set()
        self.last_viewport = QRectF()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._batch_update)
        self.update_timer.setInterval(16)  # 60 FPS
        
        # 启动更新定时器
        self.update_timer.start()
    
    def add_track(self, track: TimelineTrack, timeline_ruler):
        """添加轨道"""
        track_item = OptimizedTimelineTrack(track, timeline_ruler)
        self.addItem(track_item)
        self.tracks[track.track_id] = track_item
        return track_item
    
    def remove_track(self, track_id: str):
        """移除轨道"""
        if track_id in self.tracks:
            track_item = self.tracks[track_id]
            self.removeItem(track_item)
            del self.tracks[track_id]
    
    def set_ruler(self, ruler: OptimizedTimelineRuler):
        """设置标尺"""
        self.ruler = ruler
        self.addItem(ruler)
    
    def _batch_update(self):
        """批量更新"""
        # 只更新可见区域的项目
        viewport = self.views()[0].mapToScene(self.views()[0].viewport().rect()).boundingRect()
        
        if viewport != self.last_viewport:
            self.last_viewport = viewport
            self._update_visible_items(viewport)
    
    def _update_visible_items(self, viewport: QRectF):
        """更新可见项目"""
        new_visible_items = set()
        
        for track_item in self.tracks.values():
            if track_item.boundingRect().intersects(viewport):
                new_visible_items.add(track_item)
                
                for clip_item in track_item.clips.values():
                    if clip_item.boundingRect().translated(clip_item.pos()).intersects(viewport):
                        new_visible_items.add(clip_item)
        
        # 更新可见项目
        for item in new_visible_items - self.visible_items:
            item.update()
        
        self.visible_items = new_visible_items


class OptimizedTimelineView(QGraphicsView):
    """优化版时间轴视图"""
    
    def __init__(self, scene: OptimizedTimelineScene, parent=None):
        super().__init__(scene, parent)
        self.scene = scene
        self.performance_config = PerformanceConfig()
        
        # 性能优化设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        
        # 设置拖拽模式
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        # 设置缓存背景
        self.setCacheMode(QGraphicsView.CacheMode.CacheBackground)
        
        # 连接信号
        self.scene.ruler.time_changed.connect(self._on_time_changed)
        self.scene.ruler.zoom_changed.connect(self._on_zoom_changed)
    
    def _on_time_changed(self, time_seconds: float):
        """时间变更处理"""
        # 可以在这里更新外部UI
        pass
    
    def _on_zoom_changed(self, pixels_per_second: float):
        """缩放变更处理"""
        # 更新所有轨道的缩放
        for track_item in self.scene.tracks.values():
            track_item.update_zoom(pixels_per_second)
        
        # 更新标尺
        self.scene.ruler.needs_update = True
        self.scene.ruler.update()
    
    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件"""
        # 传递给标尺处理
        self.scene.ruler.wheelEvent(event)
    
    def resizeEvent(self, event: QResizeEvent):
        """调整大小事件"""
        super().resizeEvent(event)
        # 触发可见性更新
        self.scene._batch_update()


class OptimizedTimelineEditor(QWidget):
    """优化版时间轴编辑器"""
    
    # 信号定义
    project_loaded = pyqtSignal(TimelineProject)
    project_saved = pyqtSignal(TimelineProject)
    clip_selected = pyqtSignal(TimelineClip)
    time_changed = pyqtSignal(float)
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    
    def __init__(self, video_engine: OptimizedVideoProcessingEngine, parent=None):
        super().__init__(parent)
        self.video_engine = video_engine
        self.current_project = None
        self.selected_clip = None
        self.is_playing = False
        self.is_dark_theme = True
        
        # 时间轴标尺
        self.timeline_ruler = TimelineRuler()
        
        # 性能配置
        self.performance_config = PerformanceConfig()
        
        # 轨道组件
        self.tracks = {}
        
        # 设置UI
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        
        # 创建工具栏
        self._create_toolbar()
        
        # 初始化场景
        self._initialize_scene()
        
        # 更新UI
        self._update_ui()
        
        logger.info("优化版时间轴编辑器初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setMovable(False)
        layout.addWidget(self.toolbar)
        
        # 创建图形视图和场景
        self.scene = OptimizedTimelineScene()
        self.view = OptimizedTimelineView(self.scene)
        
        # 创建标尺
        self.ruler = OptimizedTimelineRuler(self.timeline_ruler)
        self.scene.set_ruler(self.ruler)
        
        layout.addWidget(self.view, 1)
        
        # 状态栏
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(30)
        self.status_bar.setObjectName("status_bar")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.zoom_label = QLabel("缩放: 100%")
        status_layout.addWidget(self.zoom_label)
        
        layout.addWidget(self.status_bar)
    
    def _initialize_scene(self):
        """初始化场景"""
        # 设置场景大小
        self.scene.setSceneRect(0, 0, 2000, 1000)
        
        # 添加默认轨道
        if self.current_project:
            self._load_project_to_scene(self.current_project)
    
    def _load_project_to_scene(self, project: TimelineProject):
        """加载项目到场景"""
        # 清除现有轨道
        self._clear_tracks()
        
        # 加载视频轨道
        for track in project.video_tracks:
            track_item = self.scene.add_track(track, self.timeline_ruler)
            self.tracks[track.track_id] = track_item
        
        # 加载音频轨道
        for track in project.audio_tracks:
            track_item = self.scene.add_track(track, self.timeline_ruler)
            self.tracks[track.track_id] = track_item
        
        # 加载字幕轨道
        for track in project.subtitle_tracks:
            track_item = self.scene.add_track(track, self.timeline_ruler)
            self.tracks[track.track_id] = track_item
    
    def _clear_tracks(self):
        """清除轨道"""
        for track_id in list(self.tracks.keys()):
            self.scene.remove_track(track_id)
        self.tracks.clear()
    
    def create_new_project(self, name: str, description: str = "") -> TimelineProject:
        """创建新项目"""
        project = TimelineProject(
            project_id=f"project_{int(time.time() * 1000)}",
            name=name,
            description=description
        )
        
        # 添加默认轨道
        video_track = TimelineTrack(
            track_id=f"video_track_{int(time.time() * 1000)}",
            track_type="video"
        )
        project.video_tracks.append(video_track)
        
        audio_track = TimelineTrack(
            track_id=f"audio_track_{int(time.time() * 1000)}",
            track_type="audio"
        )
        project.audio_tracks.append(audio_track)
        
        self.current_project = project
        self._load_project_to_scene(project)
        
        self.project_loaded.emit(project)
        self._update_ui()
        
        return project
    
    def add_clip_to_track(self, track_id: str, file_path: str, position: float = 0.0) -> bool:
        """添加片段到轨道"""
        try:
            # 获取视频信息
            video_info = self.video_engine.get_video_info(file_path)
            
            # 创建片段
            clip_id = f"clip_{int(time.time() * 1000)}"
            clip = TimelineClip(
                clip_id=clip_id,
                file_path=file_path,
                start_time=0.0,
                end_time=video_info.duration,
                duration=video_info.duration,
                position=position
            )
            
            # 添加到轨道
            if track_id in self.tracks:
                track_item = self.tracks[track_id]
                track_item.add_clip(clip)
                
                # 更新项目
                if self.current_project:
                    for track in self.current_project.video_tracks:
                        if track.track_id == track_id:
                            track.clips.append(clip)
                            break
                    for track in self.current_project.audio_tracks:
                        if track.track_id == track_id:
                            track.clips.append(clip)
                            break
                    for track in self.current_project.subtitle_tracks:
                        if track.track_id == track_id:
                            track.clips.append(clip)
                            break
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"添加片段失败: {e}")
            return False
    
    def _create_toolbar(self):
        """创建工具栏"""
        # 文件操作
        new_action = QAction("📄 新建", self)
        new_action.triggered.connect(self._new_project)
        self.toolbar.addAction(new_action)
        
        open_action = QAction("📁 打开", self)
        open_action.triggered.connect(self._open_project)
        self.toolbar.addAction(open_action)
        
        save_action = QAction("💾 保存", self)
        save_action.triggered.connect(self._save_project)
        self.toolbar.addAction(save_action)
        
        self.toolbar.addSeparator()
        
        # 编辑操作
        add_video_action = QAction("🎥 添加视频", self)
        add_video_action.triggered.connect(self._add_video_track)
        self.toolbar.addAction(add_video_action)
        
        add_audio_action = QAction("🎵 添加音频", self)
        add_audio_action.triggered.connect(self._add_audio_track)
        self.toolbar.addAction(add_audio_action)
        
        add_subtitle_action = QAction("📝 添加字幕", self)
        add_subtitle_action.triggered.connect(self._add_subtitle_track)
        self.toolbar.addAction(add_subtitle_action)
        
        self.toolbar.addSeparator()
        
        # 播放控制
        self.play_action = QAction("▶️ 播放", self)
        self.play_action.triggered.connect(self._toggle_playback)
        self.toolbar.addAction(self.play_action)
        
        stop_action = QAction("⏹️ 停止", self)
        stop_action.triggered.connect(self._stop_playback)
        self.toolbar.addAction(stop_action)
        
        self.toolbar.addSeparator()
        
        # 缩放控制
        zoom_in_action = QAction("🔍 放大", self)
        zoom_in_action.triggered.connect(self._zoom_in)
        self.toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("🔍 缩小", self)
        zoom_out_action.triggered.connect(self._zoom_out)
        self.toolbar.addAction(zoom_out_action)
        
        zoom_fit_action = QAction("📏 适应", self)
        zoom_fit_action.triggered.connect(self._zoom_fit)
        self.toolbar.addAction(zoom_fit_action)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            OptimizedTimelineEditor {
                background-color: #1a1a1a;
                color: white;
            }
            
            QToolBar {
                background-color: #2a2a2a;
                border-bottom: 1px solid #404040;
                spacing: 4px;
                padding: 4px;
            }
            
            QToolButton {
                background-color: transparent;
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
            }
            
            QToolButton:hover {
                background-color: #404040;
            }
            
            QToolButton:pressed {
                background-color: #505050;
            }
            
            QWidget#status_bar {
                background-color: #2a2a2a;
                border-top: 1px solid #404040;
            }
            
            QLabel {
                color: white;
                font-size: 12px;
            }
        """)
    
    def _connect_signals(self):
        """连接信号"""
        self.ruler.time_changed.connect(self._on_time_changed)
        self.ruler.zoom_changed.connect(self._on_zoom_changed)
    
    def _update_ui(self):
        """更新UI"""
        # 更新状态栏
        if self.current_project:
            self.status_label.setText(f"项目: {self.current_project.name}")
        else:
            self.status_label.setText("就绪")
        
        # 更新缩放标签
        zoom_percent = int(self.timeline_ruler.pixels_per_second)
        self.zoom_label.setText(f"缩放: {zoom_percent}%")
    
    def _new_project(self):
        """新建项目"""
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称:")
        if ok and name:
            self.create_new_project(name)
    
    def _open_project(self):
        """打开项目"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("项目文件 (*.json)")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                try:
                    with open(file_paths[0], 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                    
                    # 创建项目对象
                    project = TimelineProject(
                        project_id=project_data.get("project_id", ""),
                        name=project_data.get("name", ""),
                        description=project_data.get("description", "")
                    )
                    
                    # 加载轨道数据
                    # 这里需要根据实际的数据结构来加载
                    
                    self.load_project(project)
                    
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"打开项目失败: {e}")
    
    def _save_project(self):
        """保存项目"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "没有打开的项目")
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("项目文件 (*.json)")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                try:
                    project_data = {
                        "project_id": self.current_project.project_id,
                        "name": self.current_project.name,
                        "description": self.current_project.description,
                        "created_at": self.current_project.created_at,
                        "modified_at": self.current_project.modified_at,
                        "video_tracks": [],
                        "audio_tracks": [],
                        "subtitle_tracks": []
                    }
                    
                    # 转换轨道数据
                    # 这里需要根据实际的数据结构来保存
                    
                    with open(file_paths[0], 'w', encoding='utf-8') as f:
                        json.dump(project_data, f, indent=2, ensure_ascii=False)
                    
                    self.save_project()
                    QMessageBox.information(self, "成功", "项目保存成功")
                    
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存项目失败: {e}")
    
    def _add_video_track(self):
        """添加视频轨道"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先创建项目")
            return
        
        track_id = f"video_track_{int(time.time() * 1000)}"
        track = TimelineTrack(track_id=track_id, track_type="video")
        
        self.current_project.video_tracks.append(track)
        
        track_item = self.scene.add_track(track, self.timeline_ruler)
        self.tracks[track_id] = track_item
    
    def _add_audio_track(self):
        """添加音频轨道"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先创建项目")
            return
        
        track_id = f"audio_track_{int(time.time() * 1000)}"
        track = TimelineTrack(track_id=track_id, track_type="audio")
        
        self.current_project.audio_tracks.append(track)
        
        track_item = self.scene.add_track(track, self.timeline_ruler)
        self.tracks[track_id] = track_item
    
    def _add_subtitle_track(self):
        """添加字幕轨道"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先创建项目")
            return
        
        track_id = f"subtitle_track_{int(time.time() * 1000)}"
        track = TimelineTrack(track_id=track_id, track_type="subtitle")
        
        self.current_project.subtitle_tracks.append(track)
        
        track_item = self.scene.add_track(track, self.timeline_ruler)
        self.tracks[track_id] = track_item
    
    def _toggle_playback(self):
        """切换播放状态"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """开始播放"""
        self.is_playing = True
        self.play_action.setText("⏸️ 暂停")
        self.playback_started.emit()
        
        # 开始播放定时器
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._update_playback)
        self.playback_timer.start(50)  # 20 FPS
    
    def pause_playback(self):
        """暂停播放"""
        self.is_playing = False
        self.play_action.setText("▶️ 播放")
        self.playback_paused.emit()
        
        if hasattr(self, 'playback_timer'):
            self.playback_timer.stop()
    
    def _stop_playback(self):
        """停止播放"""
        self.is_playing = False
        self.play_action.setText("▶️ 播放")
        self.playback_stopped.emit()
        
        if hasattr(self, 'playback_timer'):
            self.playback_timer.stop()
        
        # 重置时间
        self.ruler.set_current_time(0.0)
    
    def _update_playback(self):
        """更新播放"""
        if self.is_playing:
            current_time = self.ruler.current_time
            new_time = current_time + 0.05  # 50ms步进
            
            # 检查是否到达项目结尾
            if self.current_project:
                max_duration = self._get_project_duration()
                if new_time >= max_duration:
                    self._stop_playback()
                    return
            
            self.ruler.set_current_time(new_time)
    
    def _get_project_duration(self) -> float:
        """获取项目时长"""
        if not self.current_project:
            return 0.0
        
        max_duration = 0.0
        
        for track in self.current_project.video_tracks:
            for clip in track.clips:
                end_time = clip.position + clip.duration
                if end_time > max_duration:
                    max_duration = end_time
        
        for track in self.current_project.audio_tracks:
            for clip in track.clips:
                end_time = clip.position + clip.duration
                if end_time > max_duration:
                    max_duration = end_time
        
        return max_duration
    
    def _zoom_in(self):
        """放大"""
        new_pixels_per_second = self.timeline_ruler.pixels_per_second * 1.2
        new_pixels_per_second = min(1000, new_pixels_per_second)
        
        self.timeline_ruler.pixels_per_second = new_pixels_per_second
        self._update_track_zoom()
        self._update_ui()
    
    def _zoom_out(self):
        """缩小"""
        new_pixels_per_second = self.timeline_ruler.pixels_per_second / 1.2
        new_pixels_per_second = max(10, new_pixels_per_second)
        
        self.timeline_ruler.pixels_per_second = new_pixels_per_second
        self._update_track_zoom()
        self._update_ui()
    
    def _zoom_fit(self):
        """适应窗口"""
        if not self.current_project:
            return
        
        project_duration = self._get_project_duration()
        if project_duration <= 0:
            return
        
        available_width = self.view.viewport().width()
        new_pixels_per_second = available_width / project_duration
        
        self.timeline_ruler.pixels_per_second = new_pixels_per_second
        self._update_track_zoom()
        self._update_ui()
    
    def _update_track_zoom(self):
        """更新轨道缩放"""
        for track_item in self.tracks.values():
            track_item.update_zoom(self.timeline_ruler.pixels_per_second)
    
    def _on_time_changed(self, time_seconds: float):
        """时间变更处理"""
        self.time_changed.emit(time_seconds)
    
    def _on_zoom_changed(self, pixels_per_second: float):
        """缩放变更处理"""
        self._update_track_zoom()
        self._update_ui()
    
    def load_project(self, project: TimelineProject):
        """加载项目"""
        self.current_project = project
        self._load_project_to_scene(project)
        
        self.project_loaded.emit(project)
        self._update_ui()
    
    def save_project(self) -> TimelineProject:
        """保存项目"""
        if self.current_project:
            self.current_project.modified_at = time.time()
            self.project_saved.emit(self.current_project)
            return self.current_project
        return None
    
    def set_performance_config(self, config: PerformanceConfig):
        """设置性能配置"""
        self.performance_config = config
        self.scene.performance_config = config
        self.view.performance_config = config
        
        # 应用性能设置
        if config.render_mode == RenderMode.CPU:
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        elif config.render_mode == RenderMode.OPENGL:
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        elif config.render_mode == RenderMode.HARDWARE_ACCELERATED:
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    def export_project(self, output_path: str, config: ProcessingConfig) -> bool:
        """导出项目"""
        if not self.current_project:
            return False
        
        try:
            # 使用视频引擎处理时间轴
            return self.video_engine.process_timeline(self.current_project, output_path, config)
            
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        # 停止播放
        self._stop_playback()
        
        # 清理轨道
        self._clear_tracks()
        
        logger.info("优化版时间轴编辑器资源清理完成")


# 工厂函数
def create_optimized_timeline_editor(video_engine: OptimizedVideoProcessingEngine, parent=None) -> OptimizedTimelineEditor:
    """创建优化版时间轴编辑器"""
    return OptimizedTimelineEditor(video_engine, parent)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建视频引擎
    video_engine = OptimizedVideoProcessingEngine()
    
    # 创建时间轴编辑器
    editor = create_optimized_timeline_editor(video_engine)
    editor.setWindowTitle("优化版时间轴编辑器测试")
    editor.resize(1200, 800)
    editor.show()
    
    # 创建测试项目
    project = editor.create_new_project("测试项目")
    
    sys.exit(app.exec())