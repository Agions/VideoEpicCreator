#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业时间线片段组件
支持视频、音频、字幕、特效等多种片段类型
提供高级功能如关键帧编辑、特效应用、音频波形显示等
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QPushButton, QLabel, QSplitter, QFrame, QMenu,
    QToolButton, QSpinBox, QComboBox, QSlider, QGroupBox,
    QToolBar, QStatusBar, QDialog, QTabWidget, QStackedWidget,
    QMessageBox, QProgressBar, QCheckBox, QRadioButton,
    QDoubleSpinBox, QGridLayout, QWidgetAction, QSizePolicy,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QMimeData, pyqtSignal, 
    QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSlot,
    QPointF, QRectF, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, 
    QLinearGradient, QDrag, QPixmap, QAction, QIcon,
    QCursor, QKeySequence, QShortcut, QWheelEvent, QPainterPath,
    QLinearGradient, QRadialGradient, QConicalGradient, QTransform,
    QFontMetrics, QPolygonF, QBrush
)


class ClipType(Enum):
    """片段类型"""
    VIDEO = "video"           # 视频片段
    AUDIO = "audio"           # 音频片段
    IMAGE = "image"           # 图片片段
    TEXT = "text"            # 文本片段
    SUBTITLE = "subtitle"     # 字幕片段
    EFFECT = "effect"         # 特效片段
    TRANSITION = "transition" # 转场片段
    COLOR = "color"          # 颜色片段


class ClipEdge(Enum):
    """片段边缘"""
    NONE = "none"           # 无边缘
    LEFT = "left"           # 左边缘
    RIGHT = "right"         # 右边缘
    TOP = "top"             # 上边缘
    BOTTOM = "bottom"       # 下边缘


class ResizeMode(Enum):
    """调整大小模式"""
    FREE = "free"           # 自由调整
    SNAP = "snap"           # 吸附调整
    PROPORTIONAL = "proportional"  # 比例调整


@dataclass
class ClipData:
    """片段数据"""
    clip_id: str = None
    name: str = "未命名片段"
    clip_type: ClipType = ClipType.VIDEO
    file_path: str = None
    start_time: int = 0
    duration: int = 5000
    source_start: int = 0
    source_duration: int = 5000
    volume: float = 1.0
    speed: float = 1.0
    opacity: float = 1.0
    blend_mode: str = "normal"
    effects: List[Dict] = None
    keyframes: List[Dict] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.clip_id is None:
            self.clip_id = str(uuid.uuid4())
        if self.effects is None:
            self.effects = []
        if self.keyframes is None:
            self.keyframes = []
        if self.metadata is None:
            self.metadata = {}


class Keyframe:
    """关键帧类"""
    
    def __init__(self, time: int, value: float, easing: str = "linear"):
        self.time = time
        self.value = value
        self.easing = easing
        self.selected = False
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'time': self.time,
            'value': self.value,
            'easing': self.easing
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Keyframe':
        """从字典创建"""
        return cls(data['time'], data['value'], data['easing'])


class ClipHandle(QWidget):
    """片段拖拽手柄"""
    
    def __init__(self, edge: ClipEdge, parent=None):
        super().__init__(parent)
        self.edge = edge
        self.is_hovered = False
        self.is_active = False
        
        # 设置手柄大小
        if edge in [ClipEdge.LEFT, ClipEdge.RIGHT]:
            self.setFixedSize(6, 20)
        else:
            self.setFixedSize(20, 6)
        
        self.setMouseTracking(True)
    
    def paintEvent(self, event):
        """绘制手柄"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 手柄颜色
        if self.is_active:
            color = QColor(100, 150, 255)
        elif self.is_hovered:
            color = QColor(150, 200, 255)
        else:
            color = QColor(80, 80, 80)
        
        painter.fillRect(self.rect(), color)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.is_hovered = True
        self.update()
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.is_hovered = False
        self.update()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_active = True
            self.update()
            # 通知父组件
            if hasattr(self.parent(), '_on_handle_pressed'):
                self.parent()._on_handle_pressed(self.edge)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.is_active = False
        self.update()


class TimelineClip(QWidget):
    """专业时间线片段组件"""
    
    # 信号
    clip_selected = pyqtSignal(object)       # 片段选中
    clip_moved = pyqtSignal(object, int)      # 片段移动 (clip, new_position)
    clip_trimmed = pyqtSignal(object, int, int)  # 片段修剪 (clip, start_time, end_time)
    clip_resized = pyqtSignal(object, int)    # 片段调整大小 (clip, new_duration)
    clip_split = pyqtSignal(object, int)      # 片段分割 (clip, split_time)
    clip_deleted = pyqtSignal(object)         # 片段删除
    keyframe_added = pyqtSignal(object, int, float)  # 关键帧添加 (clip, time, value)
    keyframe_removed = pyqtSignal(object, int)       # 关键帧移除 (clip, time)
    keyframe_moved = pyqtSignal(object, int, float)  # 关键帧移动 (clip, time, value)
    
    def __init__(self, clip_data: Union[Dict, ClipData], parent=None):
        super().__init__(parent)
        
        # 初始化片段数据
        if isinstance(clip_data, dict):
            self.clip_data = ClipData(**clip_data)
        else:
            self.clip_data = clip_data
        
        # 片段属性
        self.selected = False
        self.dragging = False
        self.resizing = False
        self.resize_edge = ClipEdge.NONE
        self.resize_mode = ResizeMode.SNAP
        
        # 时间相关
        self.start_time = self.clip_data.start_time
        self.duration = self.clip_data.duration
        
        # 缩放相关
        self.pixels_per_second = 100
        
        # 关键帧
        self.keyframes = []
        self.show_keyframes = True
        
        # 效果
        self.effects = self.clip_data.effects.copy()
        
        # UI元素
        self.handles = {}
        self.thumbnail = None
        self.waveform = None
        
        # 设置对象属性
        self.setObjectName(f"timeline_clip_{self.clip_data.clip_id}")
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        
        # 设置外观
        self.setMinimumHeight(50)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        # 计算初始宽度
        self._update_width()
        
        # 创建UI
        self._setup_ui()
        self._setup_handles()
        
        # 加载关键帧
        self._load_keyframes()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主内容区域
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(0)
        
        # 片段信息标签
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: white; font-size: 9px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.content_layout.addWidget(self.info_label)
        
        # 添加弹性空间
        self.content_layout.addStretch()
        
        layout.addWidget(self.content_widget)
        
        # 更新信息显示
        self._update_info_display()
    
    def _setup_handles(self):
        """设置拖拽手柄"""
        # 左边缘手柄
        self.handles[ClipEdge.LEFT] = ClipHandle(ClipEdge.LEFT, self)
        self.handles[ClipEdge.LEFT].move(0, (self.height() - 20) // 2)
        self.handles[ClipEdge.LEFT].show()
        
        # 右边缘手柄
        self.handles[ClipEdge.RIGHT] = ClipHandle(ClipEdge.RIGHT, self)
        self.handles[ClipEdge.RIGHT].move(self.width() - 6, (self.height() - 20) // 2)
        self.handles[ClipEdge.RIGHT].show()
    
    def _load_keyframes(self):
        """加载关键帧"""
        for kf_data in self.clip_data.keyframes:
            keyframe = Keyframe.from_dict(kf_data)
            self.keyframes.append(keyframe)
    
    def _update_width(self):
        """更新片段宽度"""
        width = int((self.duration / 1000) * self.pixels_per_second)
        self.setFixedWidth(max(50, width))
    
    def _update_info_display(self):
        """更新信息显示"""
        # 片段名称
        name = self.clip_data.name
        if len(name) > 20:
            name = name[:17] + "..."
        
        # 时间信息
        duration_sec = self.duration / 1000
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        time_text = f"{minutes}:{seconds:02d}"
        
        # 音量信息
        volume_text = f"🔊 {int(self.clip_data.volume * 100)}%"
        
        # 速度信息
        if self.clip_data.speed != 1.0:
            speed_text = f"⚡ {self.clip_data.speed:.1f}x"
        else:
            speed_text = ""
        
        # 组合显示文本
        display_text = f"{name}\n{time_text} {volume_text} {speed_text}".strip()
        self.info_label.setText(display_text)
    
    def _get_clip_color(self) -> QColor:
        """获取片段颜色"""
        colors = {
            ClipType.VIDEO: QColor(100, 150, 255),
            ClipType.AUDIO: QColor(100, 255, 100),
            ClipType.IMAGE: QColor(255, 200, 100),
            ClipType.TEXT: QColor(255, 255, 100),
            ClipType.SUBTITLE: QColor(255, 150, 100),
            ClipType.EFFECT: QColor(255, 100, 255),
            ClipType.TRANSITION: QColor(150, 150, 255),
            ClipType.COLOR: QColor(200, 200, 200)
        }
        return colors.get(self.clip_data.clip_type, QColor(150, 150, 150))
    
    def _draw_waveform(self, painter: QPainter, rect: QRect):
        """绘制音频波形"""
        if self.clip_data.clip_type != ClipType.AUDIO:
            return
        
        # 简单的波形绘制
        painter.setPen(QPen(QColor(100, 255, 100), 1))
        
        # 生成模拟波形数据
        width = rect.width()
        height = rect.height()
        center_y = height // 2
        
        # 绘制波形
        for x in range(0, width, 2):
            # 模拟波形数据
            amplitude = height * 0.3 * (0.5 + 0.5 * (x % 20) / 20)
            y1 = center_y - amplitude
            y2 = center_y + amplitude
            
            painter.drawLine(x, y1, x, y2)
    
    def _draw_keyframes(self, painter: QPainter, rect: QRect):
        """绘制关键帧"""
        if not self.show_keyframes or not self.keyframes:
            return
        
        painter.setPen(QPen(QColor(255, 255, 100), 2))
        painter.setBrush(QBrush(QColor(255, 255, 100)))
        
        for keyframe in self.keyframes:
            # 计算关键帧位置
            x = int((keyframe.time / 1000) * self.pixels_per_second)
            if 0 <= x <= rect.width():
                # 绘制关键帧
                size = 6
                painter.drawDiamond(x - size//2, rect.height() - size, size, size)
    
    def _draw_effects(self, painter: QPainter, rect: QRect):
        """绘制效果指示器"""
        if not self.effects:
            return
        
        # 在片段顶部绘制效果条
        effect_height = 4
        effect_rect = QRect(rect.left(), rect.top(), rect.width(), effect_height)
        
        # 渐变效果条
        gradient = QLinearGradient(effect_rect.topLeft(), effect_rect.topRight())
        gradient.setColorAt(0, QColor(255, 100, 255, 100))
        gradient.setColorAt(1, QColor(100, 100, 255, 100))
        
        painter.fillRect(effect_rect, gradient)
    
    def _get_resize_cursor(self, edge: ClipEdge) -> Qt.CursorShape:
        """获取调整大小的鼠标样式"""
        if edge in [ClipEdge.LEFT, ClipEdge.RIGHT]:
            return Qt.CursorShape.SizeHorCursor
        elif edge in [ClipEdge.TOP, ClipEdge.BOTTOM]:
            return Qt.CursorShape.SizeVerCursor
        else:
            return Qt.CursorShape.ArrowCursor
    
    def _get_edge_at_position(self, pos: QPoint) -> ClipEdge:
        """获取指定位置的边缘"""
        edge_threshold = 6
        
        if pos.x() <= edge_threshold:
            return ClipEdge.LEFT
        elif pos.x() >= self.width() - edge_threshold:
            return ClipEdge.RIGHT
        elif pos.y() <= edge_threshold:
            return ClipEdge.TOP
        elif pos.y() >= self.height() - edge_threshold:
            return ClipEdge.BOTTOM
        else:
            return ClipEdge.NONE
    
    def _on_handle_pressed(self, edge: ClipEdge):
        """手柄按下事件"""
        self.resizing = True
        self.resize_edge = edge
        self.setCursor(self._get_resize_cursor(edge))
    
    def _start_drag(self):
        """开始拖拽"""
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 设置拖拽数据
        mime_data.setText("timeline_clip")
        mime_data.setData("application/x-timeline-clip", json.dumps({
            'clip_id': self.clip_data.clip_id,
            'clip_type': self.clip_data.clip_type.value,
            'name': self.clip_data.name,
            'duration': self.duration
        }).encode())
        
        # 设置拖拽图像
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))
        
        # 执行拖拽
        drag.exec(Qt.DropAction.MoveAction)
    
    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 基本操作
        split_action = menu.addAction("分割片段")
        split_action.triggered.connect(lambda: self.clip_split.emit(self, self.start_time + self.duration // 2))
        
        menu.addSeparator()
        
        # 复制/剪切/删除
        copy_action = menu.addAction("复制")
        copy_action.triggered.connect(self._copy_clip)
        
        cut_action = menu.addAction("剪切")
        cut_action.triggered.connect(self._cut_clip)
        
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.clip_deleted.emit(self))
        
        menu.addSeparator()
        
        # 属性
        properties_action = menu.addAction("属性")
        properties_action.triggered.connect(self._show_properties)
        
        # 效果
        if self.clip_data.clip_type in [ClipType.VIDEO, ClipType.AUDIO]:
            effects_menu = menu.addMenu("效果")
            add_effect_action = effects_menu.addAction("添加效果")
            add_effect_action.triggered.connect(self._add_effect)
            
            if self.effects:
                remove_effect_action = effects_menu.addAction("移除效果")
                remove_effect_action.triggered.connect(self._remove_effect)
        
        # 关键帧
        keyframes_menu = menu.addMenu("关键帧")
        show_keyframes_action = keyframes_menu.addAction("显示关键帧")
        show_keyframes_action.setCheckable(True)
        show_keyframes_action.setChecked(self.show_keyframes)
        show_keyframes_action.toggled.connect(self._toggle_keyframes)
        
        add_keyframe_action = keyframes_menu.addAction("添加关键帧")
        add_keyframe_action.triggered.connect(self._add_keyframe)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _copy_clip(self):
        """复制片段"""
        # TODO: 实现复制功能
        pass
    
    def _cut_clip(self):
        """剪切片段"""
        # TODO: 实现剪切功能
        pass
    
    def _show_properties(self):
        """显示属性对话框"""
        # TODO: 实现属性对话框
        pass
    
    def _add_effect(self):
        """添加效果"""
        # TODO: 实现添加效果功能
        pass
    
    def _remove_effect(self):
        """移除效果"""
        # TODO: 实现移除效果功能
        pass
    
    def _toggle_keyframes(self, show: bool):
        """切换关键帧显示"""
        self.show_keyframes = show
        self.update()
    
    def _add_keyframe(self):
        """添加关键帧"""
        # 在片段中心添加关键帧
        time = self.start_time + self.duration // 2
        value = 1.0  # 默认值
        self.keyframes.append(Keyframe(time, value))
        self.keyframe_added.emit(self, time, value)
        self.update()
    
    def paintEvent(self, event):
        """绘制片段"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # 获取片段颜色
        base_color = self._get_clip_color()
        
        # 创建渐变背景
        gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomLeft()))
        
        if self.selected:
            gradient.setColorAt(0, base_color.lighter(120))
            gradient.setColorAt(1, base_color.darker(120))
            border_color = base_color.lighter(150)
        else:
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(1, base_color.darker(150))
            border_color = base_color
        
        # 绘制主体
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 4, 4)
        
        # 绘制效果
        self._draw_effects(painter, rect)
        
        # 绘制波形
        self._draw_waveform(painter, rect)
        
        # 绘制关键帧
        self._draw_keyframes(painter, rect)
        
        # 绘制选中状态
        if self.selected:
            painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)
        
        # 更新手柄位置
        if self.handles.get(ClipEdge.RIGHT):
            self.handles[ClipEdge.RIGHT].move(self.width() - 6, (self.height() - 20) // 2)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在边缘
            edge = self._get_edge_at_position(event.position().toPoint())
            if edge != ClipEdge.NONE:
                self.resizing = True
                self.resize_edge = edge
                self.setCursor(self._get_resize_cursor(edge))
            else:
                self.dragging = True
                self.drag_start_pos = event.position().toPoint()
            
            # 选中当前片段
            self.selected = True
            self.clip_selected.emit(self)
            self.update()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.resizing and event.buttons() == Qt.MouseButton.LeftButton:
            # 处理调整大小
            if self.resize_edge == ClipEdge.RIGHT:
                new_width = max(50, event.position().x())
                new_duration = int((new_width / self.pixels_per_second) * 1000)
                self.duration = new_duration
                self.clip_data.duration = new_duration
                self._update_width()
                self._update_info_display()
                self.clip_resized.emit(self, new_duration)
            
            self.update()
        elif self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # 处理拖动
            if (event.position() - QPointF(self.drag_start_pos)).manhattanLength() > 10:
                self._start_drag()
                self.dragging = False
        else:
            # 更新鼠标样式
            edge = self._get_edge_at_position(event.position().toPoint())
            if edge != ClipEdge.NONE:
                self.setCursor(self._get_resize_cursor(edge))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_edge = ClipEdge.NONE
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        # TODO: 实现双击预览
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        self._show_context_menu(event.position().toPoint())
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.selected = selected
        self.update()
    
    def update_scale(self, pixels_per_second: int):
        """更新时间尺度"""
        self.pixels_per_second = pixels_per_second
        self._update_width()
    
    def get_clip_state(self) -> Dict[str, Any]:
        """获取片段状态"""
        return {
            'clip_id': self.clip_data.clip_id,
            'name': self.clip_data.name,
            'clip_type': self.clip_data.clip_type.value,
            'start_time': self.start_time,
            'duration': self.duration,
            'source_start': self.clip_data.source_start,
            'source_duration': self.clip_data.source_duration,
            'volume': self.clip_data.volume,
            'speed': self.clip_data.speed,
            'opacity': self.clip_data.opacity,
            'blend_mode': self.clip_data.blend_mode,
            'effects': self.effects,
            'keyframes': [kf.to_dict() for kf in self.keyframes],
            'metadata': self.clip_data.metadata
        }
    
    def add_keyframe(self, time: int, value: float, easing: str = "linear"):
        """添加关键帧"""
        keyframe = Keyframe(time, value, easing)
        self.keyframes.append(keyframe)
        self.keyframe_added.emit(self, time, value)
        self.update()
    
    def remove_keyframe(self, time: int):
        """移除关键帧"""
        self.keyframes = [kf for kf in self.keyframes if kf.time != time]
        self.keyframe_removed.emit(self, time)
        self.update()
    
    def get_keyframe_at_time(self, time: int) -> Optional[Keyframe]:
        """获取指定时间的关键帧"""
        for keyframe in self.keyframes:
            if keyframe.time == time:
                return keyframe
        return None
    
    def get_keyframes_in_range(self, start_time: int, end_time: int) -> List[Keyframe]:
        """获取时间范围内的关键帧"""
        return [kf for kf in self.keyframes if start_time <= kf.time <= end_time]


# 工厂函数
def create_timeline_clip(clip_data: Union[Dict, ClipData]) -> TimelineClip:
    """创建时间线片段实例"""
    return TimelineClip(clip_data)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试片段
    clip_data = ClipData(
        name="测试视频片段",
        clip_type=ClipType.VIDEO,
        duration=10000,
        volume=0.8
    )
    
    clip = create_timeline_clip(clip_data)
    clip.setWindowTitle("时间线片段测试")
    clip.resize(200, 60)
    clip.show()
    
    sys.exit(app.exec())