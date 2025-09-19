#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业时间线控制组件
提供完整的播放控制、时间定位、缩放控制等功能
支持高级功能如标记点、循环播放、节拍器等
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
    QDoubleSpinBox, QGridLayout, QWidgetAction, QSizePolicy,
    QLineEdit, QTimeEdit, QDial
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QMimeData, pyqtSignal, 
    QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSlot,
    QPointF, QRectF, QTime, QElapsedTimer
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, 
    QLinearGradient, QDrag, QPixmap, QAction, QIcon,
    QCursor, QKeySequence, QShortcut, QWheelEvent, QPainterPath,
    QLinearGradient, QRadialGradient, QConicalGradient, QTransform,
    QFontMetrics, QPolygonF, QBrush, QIconEngine
)
from PyQt6.QtWidgets import QStyle


class PlaybackState(Enum):
    """播放状态"""
    STOPPED = "stopped"       # 停止
    PLAYING = "playing"       # 播放
    PAUSED = "paused"         # 暂停
    RECORDING = "recording"   # 录制


class LoopMode(Enum):
    """循环模式"""
    NONE = "none"            # 无循环
    SINGLE = "single"        # 单段循环
    ALL = "all"              # 全部循环
    MARKER = "marker"        # 标记点循环


class SnapMode(Enum):
    """吸附模式"""
    NONE = "none"           # 无吸附
    CLIP = "clip"           # 片段吸附
    MARKER = "marker"       # 标记点吸附
    GRID = "grid"           # 网格吸附
    KEYFRAME = "keyframe"   # 关键帧吸附


@dataclass
class PlaybackSettings:
    """播放设置"""
    fps: int = 30                    # 帧率
    playback_speed: float = 1.0      # 播放速度
    loop_mode: LoopMode = LoopMode.NONE
    snap_mode: SnapMode = SnapMode.CLIP
    snap_threshold: int = 10         # 吸附阈值（像素）
    auto_scroll: bool = True         # 自动滚动
    show_safe_areas: bool = True      # 显示安全区域
    show_grid: bool = True           # 显示网格
    metronome_enabled: bool = False  # 节拍器
    metronome_bpm: int = 120         # 节拍器BPM


class TimeDisplay(QWidget):
    """时间显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_time = 0
        self.total_time = 0
        self.fps = 30
        
        self.setFixedSize(120, 30)
        self.setObjectName("time_display")
    
    def set_time(self, current: int, total: int):
        """设置时间"""
        self.current_time = current
        self.total_time = total
        self.update()
    
    def set_fps(self, fps: int):
        """设置帧率"""
        self.fps = fps
        self.update()
    
    def _format_time(self, milliseconds: int) -> str:
        """格式化时间"""
        total_seconds = milliseconds // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        frames = (milliseconds % 1000) * self.fps // 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    def paintEvent(self, event):
        """绘制时间显示"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # 边框
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # 时间文本
        current_text = self._format_time(self.current_time)
        total_text = self._format_time(self.total_time)
        display_text = f"{current_text} / {total_text}"
        
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        painter.drawText(self.rect().adjusted(5, 2, -5, -2), 
                        Qt.AlignmentFlag.AlignCenter, display_text)


class PlaybackControls(QWidget):
    """播放控制组件"""
    
    # 信号
    play_clicked = pyqtSignal()           # 播放按钮点击
    pause_clicked = pyqtSignal()          # 暂停按钮点击
    stop_clicked = pyqtSignal()           # 停止按钮点击
    previous_clicked = pyqtSignal()       # 上一个按钮点击
    next_clicked = pyqtSignal()           # 下一个按钮点击
    record_clicked = pyqtSignal()         # 录制按钮点击
    seek_requested = pyqtSignal(int)      # 跳转请求
    speed_changed = pyqtSignal(float)     # 速度变化
    loop_changed = pyqtSignal(LoopMode)  # 循环模式变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.playback_state = PlaybackState.STOPPED
        self.playback_speed = 1.0
        self.loop_mode = LoopMode.NONE
        
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 播放控制按钮组
        controls_group = QGroupBox()
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(2)
        
        # 上一个按钮
        self.previous_btn = QToolButton()
        self.previous_btn.setText("⏮")
        self.previous_btn.setFixedSize(32, 32)
        self.previous_btn.setToolTip("上一个片段 (Shift+←)")
        controls_layout.addWidget(self.previous_btn)
        
        # 停止按钮
        self.stop_btn = QToolButton()
        self.stop_btn.setText("⏹")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setToolTip("停止 (S)")
        controls_layout.addWidget(self.stop_btn)
        
        # 播放/暂停按钮
        self.play_pause_btn = QToolButton()
        self.play_pause_btn.setText("▶")
        self.play_pause_btn.setFixedSize(40, 40)
        self.play_pause_btn.setToolTip("播放/暂停 (Space)")
        controls_layout.addWidget(self.play_pause_btn)
        
        # 下一个按钮
        self.next_btn = QToolButton()
        self.next_btn.setText("⏭")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setToolTip("下一个片段 (Shift+→)")
        controls_layout.addWidget(self.next_btn)
        
        # 录制按钮
        self.record_btn = QToolButton()
        self.record_btn.setText("●")
        self.record_btn.setStyleSheet("color: red; font-weight: bold;")
        self.record_btn.setFixedSize(32, 32)
        self.record_btn.setCheckable(True)
        self.record_btn.setToolTip("录制 (R)")
        controls_layout.addWidget(self.record_btn)
        
        layout.addWidget(controls_group)
        
        # 速度控制
        speed_group = QGroupBox("速度")
        speed_layout = QHBoxLayout(speed_group)
        speed_layout.setContentsMargins(5, 5, 5, 5)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 200)  # 0.25x - 2.0x
        self.speed_slider.setValue(100)
        self.speed_slider.setFixedWidth(100)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        self.speed_label.setFixedWidth(40)
        speed_layout.addWidget(self.speed_label)
        
        layout.addWidget(speed_group)
        
        # 循环控制
        loop_group = QGroupBox("循环")
        loop_layout = QHBoxLayout(loop_group)
        loop_layout.setContentsMargins(5, 5, 5, 5)
        
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["无循环", "单段循环", "全部循环", "标记点循环"])
        self.loop_combo.setCurrentIndex(0)
        loop_layout.addWidget(self.loop_combo)
        
        layout.addWidget(loop_group)
        
        # 添加弹性空间
        layout.addStretch()
    
    def _connect_signals(self):
        """连接信号"""
        # 播放控制
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.previous_btn.clicked.connect(self.previous_clicked.emit)
        self.next_btn.clicked.connect(self.next_clicked.emit)
        self.record_btn.toggled.connect(self._on_record_toggled)
        
        # 速度控制
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # 循环控制
        self.loop_combo.currentIndexChanged.connect(self._on_loop_changed)
    
    def _on_play_pause_clicked(self):
        """播放/暂停按钮点击"""
        if self.playback_state == PlaybackState.PLAYING:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()
    
    def _on_stop_clicked(self):
        """停止按钮点击"""
        self.stop_clicked.emit()
    
    def _on_record_toggled(self, checked: bool):
        """录制按钮切换"""
        if checked:
            self.playback_state = PlaybackState.RECORDING
        else:
            self.playback_state = PlaybackState.STOPPED
        self._update_ui_state()
        self.record_clicked.emit()
    
    def _on_speed_changed(self, value: int):
        """速度变化"""
        self.playback_speed = value / 100.0
        self.speed_label.setText(f"{self.playback_speed:.1f}x")
        self.speed_changed.emit(self.playback_speed)
    
    def _on_loop_changed(self, index: int):
        """循环模式变化"""
        loop_modes = [
            LoopMode.NONE,
            LoopMode.SINGLE,
            LoopMode.ALL,
            LoopMode.MARKER
        ]
        self.loop_mode = loop_modes[index]
        self.loop_changed.emit(self.loop_mode)
    
    def _update_ui_state(self):
        """更新UI状态"""
        # 播放/暂停按钮
        if self.playback_state == PlaybackState.PLAYING:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("暂停 (Space)")
        elif self.playback_state == PlaybackState.RECORDING:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("暂停录制 (Space)")
            self.record_btn.setChecked(True)
        else:
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("播放 (Space)")
            self.record_btn.setChecked(False)
        
        # 按钮状态
        is_playing = self.playback_state in [PlaybackState.PLAYING, PlaybackState.RECORDING]
        self.previous_btn.setEnabled(not is_playing)
        self.next_btn.setEnabled(not is_playing)
    
    def set_playback_state(self, state: PlaybackState):
        """设置播放状态"""
        self.playback_state = state
        self._update_ui_state()
    
    def set_playback_speed(self, speed: float):
        """设置播放速度"""
        self.playback_speed = speed
        self.speed_slider.setValue(int(speed * 100))
        self.speed_label.setText(f"{speed:.1f}x")
    
    def set_loop_mode(self, mode: LoopMode):
        """设置循环模式"""
        self.loop_mode = mode
        mode_index = {
            LoopMode.NONE: 0,
            LoopMode.SINGLE: 1,
            LoopMode.ALL: 2,
            LoopMode.MARKER: 3
        }
        self.loop_combo.setCurrentIndex(mode_index.get(mode, 0))


class ZoomControls(QWidget):
    """缩放控制组件"""
    
    # 信号
    zoom_in_requested = pyqtSignal()      # 放大请求
    zoom_out_requested = pyqtSignal()     # 缩小请求
    zoom_reset_requested = pyqtSignal()   # 重置缩放请求
    zoom_changed = pyqtSignal(int)        # 缩放级别变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.min_zoom = 10
        self.max_zoom = 500
        self.current_zoom = 100
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 缩小按钮
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("−")
        self.zoom_out_btn.setFixedSize(24, 24)
        self.zoom_out_btn.setToolTip("缩小 (Ctrl+-)")
        layout.addWidget(self.zoom_out_btn)
        
        # 缩放滑块
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(self.min_zoom, self.max_zoom)
        self.zoom_slider.setValue(self.current_zoom)
        self.zoom_slider.setFixedWidth(150)
        layout.addWidget(self.zoom_slider)
        
        # 放大按钮
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("+")
        self.zoom_in_btn.setFixedSize(24, 24)
        self.zoom_in_btn.setToolTip("放大 (Ctrl++)")
        layout.addWidget(self.zoom_in_btn)
        
        # 缩放级别显示
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.zoom_label)
        
        # 重置按钮
        self.reset_btn = QToolButton()
        self.reset_btn.setText("重置")
        self.reset_btn.setFixedSize(50, 24)
        self.reset_btn.setToolTip("重置缩放 (Ctrl+0)")
        layout.addWidget(self.reset_btn)
        
        # 预设缩放按钮
        layout.addWidget(QLabel("预设:"))
        
        presets = [("25%", 25), ("50%", 50), ("100%", 100), ("200%", 200)]
        for text, value in presets:
            btn = QToolButton()
            btn.setText(text)
            btn.setFixedSize(40, 24)
            btn.clicked.connect(lambda checked, v=value: self.set_zoom(v))
            layout.addWidget(btn)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """连接信号"""
        self.zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        self.zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        self.reset_btn.clicked.connect(self.zoom_reset_requested.emit)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
    
    def _on_zoom_changed(self, value: int):
        """缩放变化"""
        self.current_zoom = value
        self.zoom_label.setText(f"{value}%")
        self.zoom_changed.emit(value)
    
    def set_zoom(self, zoom: int):
        """设置缩放级别"""
        self.current_zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        self.zoom_slider.setValue(self.current_zoom)
    
    def zoom_in(self):
        """放大"""
        new_zoom = min(self.current_zoom + 10, self.max_zoom)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        """缩小"""
        new_zoom = max(self.current_zoom - 10, self.min_zoom)
        self.set_zoom(new_zoom)
    
    def reset_zoom(self):
        """重置缩放"""
        self.set_zoom(100)


class SnapControls(QWidget):
    """吸附控制组件"""
    
    # 信号
    snap_mode_changed = pyqtSignal(SnapMode)  # 吸附模式变化
    snap_threshold_changed = pyqtSignal(int)  # 吸附阈值变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.snap_mode = SnapMode.CLIP
        self.snap_threshold = 10
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 吸附模式
        layout.addWidget(QLabel("吸附:"))
        
        self.snap_combo = QComboBox()
        self.snap_combo.addItems([
            "无吸附", "片段吸附", "标记点吸附", "网格吸附", "关键帧吸附"
        ])
        self.snap_combo.setCurrentIndex(1)  # 默认片段吸附
        layout.addWidget(self.snap_combo)
        
        # 吸附阈值
        layout.addWidget(QLabel("阈值:"))
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 50)
        self.threshold_spin.setValue(self.snap_threshold)
        self.threshold_spin.setSuffix("px")
        self.threshold_spin.setFixedWidth(60)
        layout.addWidget(self.threshold_spin)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """连接信号"""
        self.snap_combo.currentIndexChanged.connect(self._on_snap_mode_changed)
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
    
    def _on_snap_mode_changed(self, index: int):
        """吸附模式变化"""
        modes = [
            SnapMode.NONE,
            SnapMode.CLIP,
            SnapMode.MARKER,
            SnapMode.GRID,
            SnapMode.KEYFRAME
        ]
        self.snap_mode = modes[index]
        self.snap_mode_changed.emit(self.snap_mode)
    
    def _on_threshold_changed(self, value: int):
        """吸附阈值变化"""
        self.snap_threshold = value
        self.snap_threshold_changed.emit(value)
    
    def set_snap_mode(self, mode: SnapMode):
        """设置吸附模式"""
        self.snap_mode = mode
        mode_index = {
            SnapMode.NONE: 0,
            SnapMode.CLIP: 1,
            SnapMode.MARKER: 2,
            SnapMode.GRID: 3,
            SnapMode.KEYFRAME: 4
        }
        self.snap_combo.setCurrentIndex(mode_index.get(mode, 1))
    
    def set_snap_threshold(self, threshold: int):
        """设置吸附阈值"""
        self.snap_threshold = threshold
        self.threshold_spin.setValue(threshold)


class TimelineControls(QWidget):
    """专业时间线控制组件"""
    
    # 信号
    play_clicked = pyqtSignal()           # 播放
    pause_clicked = pyqtSignal()          # 暂停
    stop_clicked = pyqtSignal()           # 停止
    previous_clicked = pyqtSignal()       # 上一个
    next_clicked = pyqtSignal()           # 下一个
    record_clicked = pyqtSignal()         # 录制
    seek_requested = pyqtSignal(int)      # 跳转
    speed_changed = pyqtSignal(float)     # 速度变化
    loop_changed = pyqtSignal(LoopMode)  # 循环模式变化
    zoom_in_requested = pyqtSignal()      # 放大
    zoom_out_requested = pyqtSignal()     # 缩小
    zoom_reset_requested = pyqtSignal()   # 重置缩放
    zoom_changed = pyqtSignal(int)        # 缩放变化
    snap_mode_changed = pyqtSignal(SnapMode)  # 吸附模式变化
    snap_threshold_changed = pyqtSignal(int)  # 吸附阈值变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.settings = PlaybackSettings()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 时间显示
        self.time_display = TimeDisplay()
        layout.addWidget(self.time_display)
        
        # 主控制区域
        main_controls = QWidget()
        main_layout = QHBoxLayout(main_controls)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 播放控制
        self.playback_controls = PlaybackControls()
        main_layout.addWidget(self.playback_controls)
        
        main_layout.addStretch()
        
        # 缩放控制
        self.zoom_controls = ZoomControls()
        main_layout.addWidget(self.zoom_controls)
        
        main_layout.addStretch()
        
        # 吸附控制
        self.snap_controls = SnapControls()
        main_layout.addWidget(self.snap_controls)
        
        layout.addWidget(main_controls)
    
    def _connect_signals(self):
        """连接信号"""
        # 播放控制
        self.playback_controls.play_clicked.connect(self.play_clicked.emit)
        self.playback_controls.pause_clicked.connect(self.pause_clicked.emit)
        self.playback_controls.stop_clicked.connect(self.stop_clicked.emit)
        self.playback_controls.previous_clicked.connect(self.previous_clicked.emit)
        self.playback_controls.next_clicked.connect(self.next_clicked.emit)
        self.playback_controls.record_clicked.connect(self.record_clicked.emit)
        self.playback_controls.speed_changed.connect(self.speed_changed.emit)
        self.playback_controls.loop_changed.connect(self.loop_changed.emit)
        
        # 缩放控制
        self.zoom_controls.zoom_in_requested.connect(self.zoom_in_requested.emit)
        self.zoom_controls.zoom_out_requested.connect(self.zoom_out_requested.emit)
        self.zoom_controls.zoom_reset_requested.connect(self.zoom_reset_requested.emit)
        self.zoom_controls.zoom_changed.connect(self.zoom_changed.emit)
        
        # 吸附控制
        self.snap_controls.snap_mode_changed.connect(self.snap_mode_changed.emit)
        self.snap_controls.snap_threshold_changed.connect(self.snap_threshold_changed.emit)
    
    def set_time(self, current: int, total: int):
        """设置时间"""
        self.time_display.set_time(current, total)
    
    def set_fps(self, fps: int):
        """设置帧率"""
        self.time_display.set_fps(fps)
    
    def set_playback_state(self, state: PlaybackState):
        """设置播放状态"""
        self.playback_controls.set_playback_state(state)
    
    def set_playback_speed(self, speed: float):
        """设置播放速度"""
        self.playback_controls.set_playback_speed(speed)
    
    def set_loop_mode(self, mode: LoopMode):
        """设置循环模式"""
        self.playback_controls.set_loop_mode(mode)
    
    def set_zoom(self, zoom: int):
        """设置缩放级别"""
        self.zoom_controls.set_zoom(zoom)
    
    def set_snap_mode(self, mode: SnapMode):
        """设置吸附模式"""
        self.snap_controls.set_snap_mode(mode)
    
    def set_snap_threshold(self, threshold: int):
        """设置吸附阈值"""
        self.snap_controls.set_snap_threshold(threshold)
    
    def get_settings(self) -> PlaybackSettings:
        """获取播放设置"""
        return PlaybackSettings(
            fps=self.settings.fps,
            playback_speed=self.playback_controls.playback_speed,
            loop_mode=self.playback_controls.loop_mode,
            snap_mode=self.snap_controls.snap_mode,
            snap_threshold=self.snap_controls.snap_threshold,
            auto_scroll=self.settings.auto_scroll,
            show_safe_areas=self.settings.show_safe_areas,
            show_grid=self.settings.show_grid,
            metronome_enabled=self.settings.metronome_enabled,
            metronome_bpm=self.settings.metronome_bpm
        )


# 工厂函数
def create_timeline_controls() -> TimelineControls:
    """创建时间线控制组件实例"""
    return TimelineControls()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试控件
    controls = create_timeline_controls()
    controls.setWindowTitle("时间线控制测试")
    controls.resize(800, 100)
    controls.show()
    
    sys.exit(app.exec())