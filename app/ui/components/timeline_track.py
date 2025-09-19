#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业时间线轨道组件
支持视频、音频、字幕、特效等多种轨道类型
提供高级功能如轨道锁定、独奏、音量控制、效果处理等
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QPushButton, QLabel, QSplitter, QFrame, QMenu,
    QToolButton, QSpinBox, QComboBox, QSlider, QGroupBox,
    QToolBar, QStatusBar, QDialog, QTabWidget, QStackedWidget,
    QMessageBox, QProgressBar, QCheckBox, QRadioButton,
    QDoubleSpinBox, QGridLayout, QWidgetAction, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QMimeData, pyqtSignal, 
    QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSlot,
    QPointF, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, 
    QLinearGradient, QDrag, QPixmap, QAction, QIcon,
    QCursor, QKeySequence, QShortcut, QWheelEvent, QPainterPath,
    QLinearGradient, QRadialGradient, QConicalGradient, QTransform, QPolygon
)
from PyQt6.QtWidgets import QStyle

from .timeline_clip import TimelineClip, ClipType


class TrackType(Enum):
    """轨道类型"""
    VIDEO = "video"           # 视频轨道
    AUDIO = "audio"           # 音频轨道
    SUBTITLE = "subtitle"     # 字幕轨道
    EFFECT = "effect"         # 特效轨道
    TRANSITION = "transition" # 转场轨道
    MIX = "mix"              # 混音轨道


class TrackState(Enum):
    """轨道状态"""
    NORMAL = "normal"        # 正常状态
    LOCKED = "locked"        # 锁定状态
    SOLO = "solo"           # 独奏状态
    MUTE = "mute"           # 静音状态
    HIDDEN = "hidden"       # 隐藏状态


@dataclass
class TrackSettings:
    """轨道设置"""
    volume: float = 1.0              # 音量 (0.0 - 2.0)
    pan: float = 0.0                 # 声道平衡 (-1.0 - 1.0)
    height: int = 80                 # 轨道高度
    show_waveform: bool = True       # 显示波形
    show_thumbnails: bool = True     # 显示缩略图
    opacity: float = 1.0             # 不透明度 (0.0 - 1.0)
    blend_mode: str = "normal"       # 混合模式
    enabled: bool = True             # 轨道启用状态


class TrackHeader(QWidget):
    """轨道头部组件"""
    
    # 信号
    track_selected = pyqtSignal(object)      # 轨道选中
    track_locked = pyqtSignal(bool)         # 轨道锁定
    track_solo = pyqtSignal(bool)           # 轨道独奏
    track_mute = pyqtSignal(bool)           # 轨道静音
    settings_changed = pyqtSignal(dict)      # 设置变化
    
    def __init__(self, track_type: TrackType, track_name: str, parent=None):
        super().__init__(parent)
        
        self.track_type = track_type
        self.track_name = track_name
        self.is_selected = False
        self.is_locked = False
        self.is_solo = False
        self.is_mute = False
        self.settings = TrackSettings()
        
        self.setFixedWidth(120)
        self.setObjectName("track_header")
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 轨道类型图标和名称
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 类型图标
        self.type_icon = QLabel()
        self.type_icon.setFixedSize(16, 16)
        self._update_type_icon()
        header_layout.addWidget(self.type_icon)
        
        # 轨道名称
        self.name_label = QLabel(self.track_name)
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.name_label)
        
        layout.addLayout(header_layout)
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # 锁定按钮
        self.lock_btn = QToolButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setText("🔒" if self.is_locked else "🔓")
        self.lock_btn.setCheckable(True)
        self.lock_btn.toggled.connect(self._on_lock_toggled)
        controls_layout.addWidget(self.lock_btn)
        
        # 独奏按钮
        self.solo_btn = QToolButton()
        self.solo_btn.setFixedSize(20, 20)
        self.solo_btn.setText("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.toggled.connect(self._on_solo_toggled)
        controls_layout.addWidget(self.solo_btn)
        
        # 静音按钮
        self.mute_btn = QToolButton()
        self.mute_btn.setFixedSize(20, 20)
        self.mute_btn.setText("🔇" if self.is_mute else "🔊")
        self.mute_btn.setCheckable(True)
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        controls_layout.addWidget(self.mute_btn)
        
        layout.addLayout(controls_layout)
        
        # 音量控制（仅音频轨道）
        if self.track_type == TrackType.AUDIO:
            volume_layout = QHBoxLayout()
            volume_layout.setContentsMargins(0, 0, 0, 0)
            
            self.volume_slider = QSlider(Qt.Orientation.Vertical)
            self.volume_slider.setRange(0, 200)
            self.volume_slider.setValue(int(self.settings.volume * 100))
            self.volume_slider.setFixedHeight(40)
            self.volume_slider.valueChanged.connect(self._on_volume_changed)
            volume_layout.addWidget(self.volume_slider)
            
            layout.addLayout(volume_layout)
        
        # 不透明度控制（仅视频轨道）
        if self.track_type == TrackType.VIDEO:
            opacity_layout = QHBoxLayout()
            opacity_layout.setContentsMargins(0, 0, 0, 0)
            
            self.opacity_slider = QSlider(Qt.Orientation.Vertical)
            self.opacity_slider.setRange(0, 100)
            self.opacity_slider.setValue(int(self.settings.opacity * 100))
            self.opacity_slider.setFixedHeight(40)
            self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
            opacity_layout.addWidget(self.opacity_slider)
            
            layout.addLayout(opacity_layout)
    
    def _connect_signals(self):
        """连接信号"""
        pass
    
    def _update_type_icon(self):
        """更新类型图标"""
        # 根据轨道类型设置不同的图标
        icon_colors = {
            TrackType.VIDEO: QColor(100, 150, 255),
            TrackType.AUDIO: QColor(100, 255, 100),
            TrackType.SUBTITLE: QColor(255, 200, 100),
            TrackType.EFFECT: QColor(255, 100, 255),
            TrackType.TRANSITION: QColor(255, 150, 100),
            TrackType.MIX: QColor(150, 150, 150)
        }
        
        color = icon_colors.get(self.track_type, QColor(150, 150, 150))
        
        # 创建简单的图标
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.track_type == TrackType.VIDEO:
            # 视频图标
            painter.fillRect(QRect(2, 2, 12, 8), color)
            painter.setPen(QPen(color, 2))
            painter.drawPolygon(QPolygon([
                QPoint(8, 12), QPoint(4, 16), QPoint(12, 16)
            ]))
        elif self.track_type == TrackType.AUDIO:
            # 音频图标
            painter.setPen(QPen(color, 2))
            painter.drawLine(4, 8, 4, 16)
            painter.drawLine(8, 4, 8, 16)
            painter.drawLine(12, 6, 12, 16)
        elif self.track_type == TrackType.SUBTITLE:
            # 字幕图标
            painter.setPen(QPen(color, 2))
            painter.drawRect(2, 6, 12, 8)
            painter.drawLine(4, 10, 12, 10)
        else:
            # 其他图标
            painter.fillRect(QRect(2, 2, 12, 12), color)
        
        painter.end()
        self.type_icon.setPixmap(pixmap)
    
    def _on_lock_toggled(self, checked: bool):
        """锁定按钮切换"""
        self.is_locked = checked
        self.lock_btn.setText("🔒" if checked else "🔓")
        self.track_locked.emit(checked)
    
    def _on_solo_toggled(self, checked: bool):
        """独奏按钮切换"""
        self.is_solo = checked
        self.track_solo.emit(checked)
    
    def _on_mute_toggled(self, checked: bool):
        """静音按钮切换"""
        self.is_mute = checked
        self.mute_btn.setText("🔇" if checked else "🔊")
        self.track_mute.emit(checked)
    
    def _on_volume_changed(self, value: int):
        """音量变化"""
        self.settings.volume = value / 100.0
        self.settings_changed.emit({'volume': self.settings.volume})
    
    def _on_opacity_changed(self, value: int):
        """不透明度变化"""
        self.settings.opacity = value / 100.0
        self.settings_changed.emit({'opacity': self.settings.opacity})
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.update()
    
    def paintEvent(self, event):
        """绘制轨道头部"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        if self.is_selected:
            painter.fillRect(self.rect(), QColor(60, 60, 80))
        else:
            painter.fillRect(self.rect(), QColor(45, 45, 45))
        
        # 边框
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # 锁定状态指示
        if self.is_locked:
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(0, 0, self.width(), 0)
            painter.drawLine(0, self.height()-1, self.width(), self.height()-1)


class TimelineTrack(QWidget):
    """专业时间线轨道组件"""
    
    # 信号
    clip_selected = pyqtSignal(object)       # 片段选中
    clip_moved = pyqtSignal(object, int, int) # 片段移动 (clip, old_track, new_track)
    clip_trimmed = pyqtSignal(object, int, int)  # 片段修剪 (clip, start_time, end_time)
    track_selected = pyqtSignal(object)      # 轨道选中
    track_settings_changed = pyqtSignal(dict) # 轨道设置变化
    
    def __init__(self, track_type: TrackType, name: str, track_index: int, parent=None):
        super().__init__(parent)
        
        self.track_type = track_type
        self.track_name = name
        self.track_index = track_index
        self.clips = []
        self.settings = TrackSettings()
        
        # 时间相关
        self.pixels_per_second = 100
        self.start_time = 0
        self.duration = 0
        
        # 状态
        self.is_selected = False
        self.is_locked = False
        self.is_solo = False
        self.is_mute = False
        self.state = TrackState.NORMAL
        
        # 拖拽状态
        self.drag_start_pos = None
        self.drag_operation = None
        
        # 设置对象属性
        self.setObjectName(f"timeline_track_{track_index}")
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        # 设置最小高度
        self.setMinimumHeight(self.settings.height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 轨道头部
        self.header = TrackHeader(self.track_type, self.track_name)
        self.header.track_selected.connect(self._on_header_clicked)
        self.header.track_locked.connect(self._on_track_locked)
        self.header.track_solo.connect(self._on_track_solo)
        self.header.track_mute.connect(self._on_track_mute)
        self.header.settings_changed.connect(self._on_settings_changed)
        layout.addWidget(self.header)
        
        # 轨道内容区域
        self.content_area = QWidget()
        self.content_layout = QHBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # 添加弹性空间
        self.content_layout.addStretch()
        
        layout.addWidget(self.content_area)
    
    def _connect_signals(self):
        """连接信号"""
        pass
    
    def _on_header_clicked(self):
        """头部点击事件"""
        self.set_selected(True)
        self.track_selected.emit(self)
    
    def _on_track_locked(self, locked: bool):
        """轨道锁定事件"""
        self.is_locked = locked
        self.state = TrackState.LOCKED if locked else TrackState.NORMAL
        self.update()
    
    def _on_track_solo(self, solo: bool):
        """轨道独奏事件"""
        self.is_solo = solo
        self.state = TrackState.SOLO if solo else TrackState.NORMAL
        self.update()
    
    def _on_track_mute(self, mute: bool):
        """轨道静音事件"""
        self.is_mute = mute
        self.state = TrackState.MUTE if mute else TrackState.NORMAL
        self.update()
    
    def _on_settings_changed(self, settings: dict):
        """设置变化事件"""
        self.settings.__dict__.update(settings)
        self.track_settings_changed.emit(settings)
        self.update()
    
    def add_clip(self, clip_data: Dict[str, Any], position: int = 0) -> TimelineClip:
        """添加片段到轨道"""
        if self.is_locked:
            return None
        
        # 创建片段
        clip = TimelineClip(clip_data, self)
        
        # 设置位置
        clip.start_time = position
        
        # 计算宽度
        duration = clip_data.get('duration', 5000)  # 默认5秒
        width = int((duration / 1000) * self.pixels_per_second)
        clip.setFixedWidth(max(50, width))
        
        # 连接信号
        clip.clip_selected.connect(self._on_clip_selected)
        clip.clip_moved.connect(self._on_clip_moved)
        clip.clip_trimmed.connect(self._on_clip_trimmed)
        
        # 添加到布局
        self._insert_clip_at_position(clip, position)
        
        # 添加到列表
        self.clips.append(clip)
        
        # 更新轨道时长
        self._update_duration()
        
        return clip
    
    def remove_clip(self, clip: TimelineClip):
        """从轨道移除片段"""
        if clip in self.clips:
            # 从布局中移除
            self.content_layout.removeWidget(clip)
            clip.setParent(None)
            
            # 从列表中移除
            self.clips.remove(clip)
            
            # 重新布局剩余片段
            self._relayout_clips()
            
            # 更新轨道时长
            self._update_duration()
    
    def _insert_clip_at_position(self, clip: TimelineClip, position: int):
        """在指定位置插入片段"""
        # 计算像素位置
        position_px = int(position * self.pixels_per_second / 1000)
        
        # 移除弹性空间
        if self.content_layout.count() > 0:
            stretch_item = self.content_layout.takeAt(self.content_layout.count() - 1)
        
        # 添加空白间隔
        if position_px > 0:
            spacer = QWidget()
            spacer.setFixedWidth(position_px)
            spacer.setObjectName("clip_spacer")
            self.content_layout.addWidget(spacer)
        
        # 添加片段
        self.content_layout.addWidget(clip)
        
        # 重新添加弹性空间
        self.content_layout.addStretch()
    
    def _relayout_clips(self):
        """重新布局所有片段"""
        # 清空布局
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # 按时间排序片段
        self.clips.sort(key=lambda c: c.start_time)
        
        # 重新添加片段
        for clip in self.clips:
            self._insert_clip_at_position(clip, clip.start_time)
    
    def _update_duration(self):
        """更新轨道时长"""
        if self.clips:
            self.duration = max(clip.start_time + clip.duration for clip in self.clips)
        else:
            self.duration = 0
    
    def _on_clip_selected(self, clip: TimelineClip):
        """片段选中事件"""
        self.clip_selected.emit(clip)
    
    def _on_clip_moved(self, clip: TimelineClip, new_position: int):
        """片段移动事件"""
        # 更新片段位置
        clip.start_time = new_position
        
        # 重新布局
        self._relayout_clips()
        
        # 更新时长
        self._update_duration()
        
        # 发射信号
        self.clip_moved.emit(clip, self.track_index, self.track_index)
    
    def _on_clip_trimmed(self, clip: TimelineClip, start_time: int, end_time: int):
        """片段修剪事件"""
        # 更新片段
        clip.start_time = start_time
        clip.duration = end_time - start_time
        
        # 重新布局
        self._relayout_clips()
        
        # 更新时长
        self._update_duration()
        
        # 发射信号
        self.clip_trimmed.emit(clip, start_time, end_time)
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.header.set_selected(selected)
        self.update()
    
    def update_scale(self, pixels_per_second: int):
        """更新时间尺度"""
        self.pixels_per_second = pixels_per_second
        
        # 更新所有片段的宽度
        for clip in self.clips:
            width = int((clip.duration / 1000) * self.pixels_per_second)
            clip.setFixedWidth(max(50, width))
        
        # 重新布局
        self._relayout_clips()
    
    def get_duration(self) -> int:
        """获取轨道时长"""
        return self.duration
    
    def get_track_state(self) -> Dict[str, Any]:
        """获取轨道状态"""
        return {
            'track_type': self.track_type.value,
            'track_name': self.track_name,
            'track_index': self.track_index,
            'clips': [clip.get_clip_state() for clip in self.clips],
            'settings': self.settings.__dict__,
            'state': self.state.value,
            'duration': self.duration
        }
    
    def paintEvent(self, event):
        """绘制轨道"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 轨道背景
        if self.is_selected:
            painter.fillRect(self.rect(), QColor(50, 50, 70))
        else:
            painter.fillRect(self.rect(), QColor(35, 35, 35))
        
        # 根据轨道类型绘制不同的背景
        if self.track_type == TrackType.VIDEO:
            # 视频轨道：深蓝色背景
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(40, 40, 60))
            gradient.setColorAt(1, QColor(30, 30, 50))
            painter.fillRect(self.rect(), gradient)
        elif self.track_type == TrackType.AUDIO:
            # 音频轨道：深绿色背景
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(40, 60, 40))
            gradient.setColorAt(1, QColor(30, 50, 30))
            painter.fillRect(self.rect(), gradient)
        elif self.track_type == TrackType.SUBTITLE:
            # 字幕轨道：深橙色背景
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(60, 50, 30))
            gradient.setColorAt(1, QColor(50, 40, 20))
            painter.fillRect(self.rect(), gradient)
        
        # 绘制网格线
        if self.pixels_per_second > 50:
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            
            # 垂直网格线（每秒）
            for i in range(0, self.width(), self.pixels_per_second):
                painter.drawLine(i, 0, i, self.height())
        
        # 绘制状态指示
        if self.is_locked:
            # 锁定状态：红色边框
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        elif self.is_solo:
            # 独奏状态：黄色边框
            painter.setPen(QPen(QColor(255, 255, 100), 2))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        elif self.is_mute:
            # 静音状态：灰色边框
            painter.setPen(QPen(QColor(150, 150, 150), 2))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
    
    def dragEnterEvent(self, event):
        """拖放进入事件"""
        if not self.is_locked and event.mimeData().hasFormat("application/x-timeline-clip"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """拖放移动事件"""
        if not self.is_locked and event.mimeData().hasFormat("application/x-timeline-clip"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """拖放事件"""
        if not self.is_locked and event.mimeData().hasFormat("application/x-timeline-clip"):
            # 获取片段数据
            clip_data = event.mimeData().property("clip_data")
            if clip_data:
                # 计算放置位置
                position = int(event.position().x() * 1000 / self.pixels_per_second)
                
                # 添加片段
                self.add_clip(clip_data, position)
                
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        
        # 轨道操作
        if not self.is_locked:
            add_clip_action = menu.addAction("添加片段")
            add_clip_action.triggered.connect(self._add_clip_dialog)
        
        # 轨道设置
        menu.addSeparator()
        
        # 重命名
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(self._rename_track)
        
        # 轨道高度
        height_menu = menu.addMenu("轨道高度")
        for height in [60, 80, 100, 120, 150]:
            action = height_menu.addAction(f"{height}px")
            action.triggered.connect(lambda checked, h=height: self.set_height(h))
        
        # 删除轨道
        menu.addSeparator()
        delete_action = menu.addAction("删除轨道")
        delete_action.triggered.connect(self._delete_track)
        
        menu.exec(event.globalPosition().toPoint())
    
    def _add_clip_dialog(self):
        """添加片段对话框"""
        # TODO: 实现添加片段对话框
        pass
    
    def _rename_track(self):
        """重命名轨道"""
        # TODO: 实现重命名对话框
        pass
    
    def set_height(self, height: int):
        """设置轨道高度"""
        self.settings.height = height
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.update()
    
    def _delete_track(self):
        """删除轨道"""
        # TODO: 实现删除轨道功能
        pass


# 工厂函数
def create_timeline_track(track_type: TrackType, name: str, track_index: int) -> TimelineTrack:
    """创建时间线轨道实例"""
    return TimelineTrack(track_type, name, track_index)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试轨道
    track = create_timeline_track(TrackType.VIDEO, "视频轨道 1", 0)
    track.setWindowTitle("时间线轨道测试")
    track.resize(800, 100)
    track.show()
    
    sys.exit(app.exec())