#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业关键帧编辑器组件
支持多种关键帧类型、缓动曲线、贝塞尔曲线编辑
提供高级功能如关键帧复制、粘贴、批量操作等
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import json
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QPushButton, QLabel, QSplitter, QFrame, QMenu,
    QToolButton, QSpinBox, QComboBox, QSlider, QGroupBox,
    QToolBar, QStatusBar, QDialog, QTabWidget, QStackedWidget,
    QMessageBox, QProgressBar, QCheckBox, QRadioButton,
    QDoubleSpinBox, QGridLayout, QWidgetAction, QSizePolicy,
    QLineEdit, QTimeEdit, QDial, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsPathItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem
)
from PyQt6.QtCore import (
    Qt, QSize, QRect, QPoint, QMimeData, pyqtSignal, 
    QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSlot,
    QPointF, QRectF, QTime, QElapsedTimer, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, 
    QLinearGradient, QDrag, QPixmap, QAction, QIcon,
    QCursor, QKeySequence, QShortcut, QWheelEvent, QPainterPath,
    QLinearGradient, QRadialGradient, QConicalGradient, QTransform,
    QFontMetrics, QPolygonF, QBrush, QIconEngine, QPainterPathStroker
)


class KeyframeType(Enum):
    """关键帧类型"""
    POSITION = "position"       # 位置
    ROTATION = "rotation"       # 旋转
    SCALE = "scale"            # 缩放
    OPACITY = "opacity"        # 不透明度
    VOLUME = "volume"          # 音量
    COLOR = "color"            # 颜色
    EFFECT = "effect"          # 效果参数
    CUSTOM = "custom"          # 自定义参数


class EasingType(Enum):
    """缓动类型"""
    LINEAR = "linear"          # 线性
    EASE_IN = "ease_in"        # 缓入
    EASE_OUT = "ease_out"      # 缓出
    EASE_IN_OUT = "ease_in_out"  # 缓入缓出
    BOUNCE_IN = "bounce_in"    # 弹跳入
    BOUNCE_OUT = "bounce_out"  # 弹跳出
    ELASTIC_IN = "elastic_in"  # 弹性入
    ELASTIC_OUT = "elastic_out" # 弹性出
    BEZIER = "bezier"          # 贝塞尔曲线
    STEP = "step"              # 步进


class InterpolationMode(Enum):
    """插值模式"""
    LINEAR = "linear"          # 线性插值
    BEZIER = "bezier"          # 贝塞尔插值
    STEP = "step"              # 步进插值
    SPLINE = "spline"          # 样条插值


@dataclass
class KeyframeData:
    """关键帧数据"""
    keyframe_id: str = None
    time: float = 0.0
    value: float = 0.0
    keyframe_type: KeyframeType = KeyframeType.POSITION
    easing: EasingType = EasingType.LINEAR
    interpolation: InterpolationMode = InterpolationMode.LINEAR
    tension: float = 0.0      # 张力（用于样条插值）
    continuity: float = 0.0   # 连续性
    bias: float = 0.0          # 偏差
    bezier_control_left: QPointF = None  # 贝塞尔左控制点
    bezier_control_right: QPointF = None  # 贝塞尔右控制点
    selected: bool = False
    metadata: Dict = None
    
    def __post_init__(self):
        if self.keyframe_id is None:
            self.keyframe_id = str(uuid.uuid4())
        if self.bezier_control_left is None:
            self.bezier_control_left = QPointF(-20, 0)
        if self.bezier_control_right is None:
            self.bezier_control_right = QPointF(20, 0)
        if self.metadata is None:
            self.metadata = {}


class KeyframeCurveItem(QGraphicsPathItem):
    """关键帧曲线项"""
    
    def __init__(self, keyframes: List[KeyframeData], parent=None):
        super().__init__(parent)
        self.keyframes = keyframes
        self.setZValue(-1)
        self.update_curve()
    
    def update_curve(self):
        """更新曲线"""
        if len(self.keyframes) < 2:
            return
        
        # 创建路径
        path = QPainterPath()
        
        # 按时间排序关键帧
        sorted_keyframes = sorted(self.keyframes, key=lambda kf: kf.time)
        
        # 起始点
        first_kf = sorted_keyframes[0]
        path.moveTo(first_kf.time, first_kf.value)
        
        # 绘制曲线
        for i in range(len(sorted_keyframes) - 1):
            kf1 = sorted_keyframes[i]
            kf2 = sorted_keyframes[i + 1]
            
            if kf1.interpolation == InterpolationMode.LINEAR:
                # 线性插值
                path.lineTo(kf2.time, kf2.value)
            elif kf1.interpolation == InterpolationMode.BEZIER:
                # 贝塞尔插值
                cp1 = QPointF(kf1.time + kf1.bezier_control_right.x(), 
                           kf1.value + kf1.bezier_control_right.y())
                cp2 = QPointF(kf2.time + kf2.bezier_control_left.x(), 
                           kf2.value + kf2.bezier_control_left.y())
                path.cubicTo(cp1, cp2, QPointF(kf2.time, kf2.value))
            elif kf1.interpolation == InterpolationMode.STEP:
                # 步进插值
                path.lineTo(kf2.time, kf1.value)
                path.lineTo(kf2.time, kf2.value)
            elif kf1.interpolation == InterpolationMode.SPLINE:
                # 样条插值（简化版）
                path.lineTo(kf2.time, kf2.value)
        
        self.setPath(path)
        
        # 设置画笔
        pen = QPen(QColor(100, 200, 255), 2)
        self.setPen(pen)


class KeyframeHandleItem(QGraphicsEllipseItem):
    """关键帧手柄项"""
    
    def __init__(self, keyframe: KeyframeData, parent=None):
        super().__init__(-4, -4, 8, 8, parent)
        self.keyframe = keyframe
        self.setBrush(QBrush(QColor(255, 255, 100)))
        self.setPen(QPen(QColor(255, 255, 255), 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(1)
        
        # 控制点
        self.left_control = None
        self.right_control = None
        self.control_lines = []
        
        self._create_controls()
    
    def _create_controls(self):
        """创建控制点"""
        if self.keyframe.interpolation == InterpolationMode.BEZIER:
            # 左控制点
            self.left_control = QGraphicsEllipseItem(-3, -3, 6, 6, self)
            self.left_control.setBrush(QBrush(QColor(255, 150, 150)))
            self.left_control.setPen(QPen(QColor(255, 255, 255), 1))
            self.left_control.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.left_control.setZValue(2)
            
            # 右控制点
            self.right_control = QGraphicsEllipseItem(-3, -3, 6, 6, self)
            self.right_control.setBrush(QBrush(QColor(150, 150, 255)))
            self.right_control.setPen(QPen(QColor(255, 255, 255), 1))
            self.right_control.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.right_control.setZValue(2)
            
            # 控制线
            self._update_control_lines()
    
    def _update_control_lines(self):
        """更新控制线"""
        # 清除旧的控制线
        for line in self.control_lines:
            line.setParentItem(None)
            line.scene().removeItem(line)
        self.control_lines.clear()
        
        if self.left_control and self.right_control:
            # 左控制线
            left_line = QGraphicsLineItem(0, 0, 
                self.left_control.pos().x(), self.left_control.pos().y(), self)
            left_line.setPen(QPen(QColor(255, 150, 150), 1, Qt.PenStyle.DashLine))
            left_line.setZValue(0)
            self.control_lines.append(left_line)
            
            # 右控制线
            right_line = QGraphicsLineItem(0, 0,
                self.right_control.pos().x(), self.right_control.pos().y(), self)
            right_line.setPen(QPen(QColor(150, 150, 255), 1, Qt.PenStyle.DashLine))
            right_line.setZValue(0)
            self.control_lines.append(right_line)
    
    def update_position(self):
        """更新位置"""
        self.setPos(self.keyframe.time, self.keyframe.value)
        
        if self.left_control:
            self.left_control.setPos(self.keyframe.bezier_control_left)
        if self.right_control:
            self.right_control.setPos(self.keyframe.bezier_control_right)
        
        self._update_control_lines()
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.keyframe.selected = selected
        self.setSelected(selected)
        
        if selected:
            self.setBrush(QBrush(QColor(255, 200, 100)))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            self.setBrush(QBrush(QColor(255, 255, 100)))
            self.setPen(QPen(QColor(255, 255, 255), 1))


class KeyframeEditorView(QGraphicsView):
    """关键帧编辑器视图"""
    
    # 信号
    keyframe_moved = pyqtSignal(object, float, float)  # 关键帧移动 (keyframe, new_time, new_value)
    keyframe_added = pyqtSignal(object, float, float)  # 关键帧添加 (keyframe_type, time, value)
    keyframe_removed = pyqtSignal(object)             # 关键帧移除 (keyframe)
    keyframe_selected = pyqtSignal(object)             # 关键帧选中 (keyframe)
    control_point_moved = pyqtSignal(object, QPointF, QPointF)  # 控制点移动 (keyframe, left_control, right_control)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 场景设置
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 视图设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 缩放和平移
        self.scale_factor = 1.0
        self.time_scale = 100.0  # 像素/秒
        self.value_scale = 100.0  # 像素/单位
        
        # 关键帧管理
        self.keyframes = []
        self.keyframe_items = {}
        self.curve_item = None
        
        # 交互状态
        self.is_panning = False
        self.is_zooming = False
        self.last_pos = None
        self.selected_keyframes = []
        
        # 网格设置
        self.show_grid = True
        self.grid_size = 50
        
        self._setup_scene()
        self._setup_grid()
    
    def _setup_scene(self):
        """设置场景"""
        # 设置场景大小
        self.scene.setSceneRect(0, 0, 1000, 500)
        
        # 创建网格背景
        self._create_grid_background()
    
    def _create_grid_background(self):
        """创建网格背景"""
        # 创建网格项
        self.grid_item = QGraphicsRectItem(self.scene.sceneRect())
        self.grid_item.setBrush(QBrush(QColor(40, 40, 40)))
        self.grid_item.setPen(QPen(QColor(60, 60, 60), 1))
        self.scene.addItem(self.grid_item)
        
        # 创建网格线
        self._update_grid()
    
    def _update_grid(self):
        """更新网格"""
        if not self.show_grid:
            return
        
        # 清除旧网格线
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and item != self.grid_item:
                self.scene.removeItem(item)
        
        # 绘制垂直网格线（时间）
        rect = self.scene.sceneRect()
        for x in range(0, int(rect.width()), self.grid_size):
            line = QGraphicsLineItem(x, 0, x, rect.height())
            line.setPen(QPen(QColor(60, 60, 60), 1))
            self.scene.addItem(line)
        
        # 绘制水平网格线（值）
        for y in range(0, int(rect.height()), self.grid_size):
            line = QGraphicsLineItem(0, y, rect.width(), y)
            line.setPen(QPen(QColor(60, 60, 60), 1))
            self.scene.addItem(line)
    
    def set_keyframes(self, keyframes: List[KeyframeData]):
        """设置关键帧"""
        # 清除现有关键帧
        self.clear_keyframes()
        
        # 添加新关键帧
        self.keyframes = keyframes.copy()
        
        # 创建关键帧项
        for kf in self.keyframes:
            self._add_keyframe_item(kf)
        
        # 创建曲线
        self._update_curve()
    
    def clear_keyframes(self):
        """清除关键帧"""
        # 清除关键帧项
        for item in self.keyframe_items.values():
            self.scene.removeItem(item)
        self.keyframe_items.clear()
        
        # 清除曲线
        if self.curve_item:
            self.scene.removeItem(self.curve_item)
            self.curve_item = None
        
        self.keyframes.clear()
        self.selected_keyframes.clear()
    
    def _add_keyframe_item(self, keyframe: KeyframeData):
        """添加关键帧项"""
        item = KeyframeHandleItem(keyframe)
        item.update_position()
        self.scene.addItem(item)
        self.keyframe_items[keyframe.keyframe_id] = item
        
        # 连接信号
        item.positionChanged.connect(lambda pos: self._on_keyframe_moved(keyframe, pos))
    
    def _update_curve(self):
        """更新曲线"""
        if self.curve_item:
            self.scene.removeItem(self.curve_item)
        
        if len(self.keyframes) >= 2:
            self.curve_item = KeyframeCurveItem(self.keyframes)
            self.scene.addItem(self.curve_item)
    
    def _on_keyframe_moved(self, keyframe: KeyframeData, pos: QPointF):
        """关键帧移动"""
        # 更新关键帧数据
        keyframe.time = pos.x()
        keyframe.value = pos.y()
        
        # 更新曲线
        self._update_curve()
        
        # 发射信号
        self.keyframe_moved.emit(keyframe, keyframe.time, keyframe.value)
    
    def add_keyframe(self, keyframe_type: KeyframeType, time: float, value: float) -> KeyframeData:
        """添加关键帧"""
        keyframe = KeyframeData(
            keyframe_type=keyframe_type,
            time=time,
            value=value
        )
        
        self.keyframes.append(keyframe)
        self._add_keyframe_item(keyframe)
        self._update_curve()
        
        self.keyframe_added.emit(keyframe_type, time, value)
        return keyframe
    
    def remove_keyframe(self, keyframe: KeyframeData):
        """移除关键帧"""
        if keyframe in self.keyframes:
            self.keyframes.remove(keyframe)
            
            # 移除项
            if keyframe.keyframe_id in self.keyframe_items:
                item = self.keyframe_items[keyframe.keyframe_id]
                self.scene.removeItem(item)
                del self.keyframe_items[keyframe.keyframe_id]
            
            # 更新曲线
            self._update_curve()
            
            self.keyframe_removed.emit(keyframe)
    
    def get_keyframe_at_position(self, pos: QPointF) -> Optional[KeyframeData]:
        """获取指定位置的关键帧"""
        scene_pos = self.mapToScene(pos)
        
        for keyframe in self.keyframes:
            kf_pos = QPointF(keyframe.time, keyframe.value)
            if (scene_pos - kf_pos).manhattanLength() < 10:
                return keyframe
        
        return None
    
    def wheelEvent(self, event):
        """滚轮事件"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+滚轮进行缩放
            zoom_factor = 1.1
            if event.angleDelta().y() > 0:
                self.scale(zoom_factor, zoom_factor)
            else:
                self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
        else:
            super().wheelEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击了关键帧
            keyframe = self.get_keyframe_at_position(event.pos())
            
            if keyframe:
                # 选中关键帧
                self._select_keyframe(keyframe)
            else:
                # 在空白处添加新关键帧
                scene_pos = self.mapToScene(event.pos())
                self.add_keyframe(KeyframeType.POSITION, scene_pos.x(), scene_pos.y())
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            # 中键拖拽
            self.is_panning = True
            self.last_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键菜单
            keyframe = self.get_keyframe_at_position(event.pos())
            if keyframe:
                self._show_keyframe_menu(event.pos(), keyframe)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_panning and event.buttons() == Qt.MouseButton.MiddleButton:
            # 平移视图
            delta = event.pos() - self.last_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pos = event.pos()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseReleaseEvent(event)
    
    def _select_keyframe(self, keyframe: KeyframeData):
        """选中关键帧"""
        # 清除之前的选中
        for kf in self.selected_keyframes:
            if kf.keyframe_id in self.keyframe_items:
                self.keyframe_items[kf.keyframe_id].set_selected(False)
        
        # 选中新的关键帧
        self.selected_keyframes = [keyframe]
        if keyframe.keyframe_id in self.keyframe_items:
            self.keyframe_items[keyframe.keyframe_id].set_selected(True)
        
        self.keyframe_selected.emit(keyframe)
    
    def _show_keyframe_menu(self, pos: QPoint, keyframe: KeyframeData):
        """显示关键帧菜单"""
        menu = QMenu(self)
        
        # 删除关键帧
        delete_action = menu.addAction("删除关键帧")
        delete_action.triggered.connect(lambda: self.remove_keyframe(keyframe))
        
        # 插值模式
        interpolation_menu = menu.addMenu("插值模式")
        for mode in InterpolationMode:
            action = interpolation_menu.addAction(mode.value)
            action.setCheckable(True)
            action.setChecked(keyframe.interpolation == mode)
            action.triggered.connect(lambda checked, m=mode: self._set_interpolation(keyframe, m))
        
        # 缓动类型
        easing_menu = menu.addMenu("缓动类型")
        for easing in EasingType:
            action = easing_menu.addAction(easing.value)
            action.setCheckable(True)
            action.setChecked(keyframe.easing == easing)
            action.triggered.connect(lambda checked, e=easing: self._set_easing(keyframe, e))
        
        menu.exec(self.mapToGlobal(pos))
    
    def _set_interpolation(self, keyframe: KeyframeData, mode: InterpolationMode):
        """设置插值模式"""
        keyframe.interpolation = mode
        self._update_curve()
    
    def _set_easing(self, keyframe: KeyframeData, easing: EasingType):
        """设置缓动类型"""
        keyframe.easing = easing
        self._update_curve()
    
    def set_time_scale(self, scale: float):
        """设置时间缩放"""
        self.time_scale = scale
        self.update()
    
    def set_value_scale(self, scale: float):
        """设置值缩放"""
        self.value_scale = scale
        self.update()
    
    def set_grid_visible(self, visible: bool):
        """设置网格可见性"""
        self.show_grid = visible
        self._update_grid()
    
    def fit_to_content(self):
        """适应内容"""
        if self.keyframes:
            # 计算边界
            min_time = min(kf.time for kf in self.keyframes)
            max_time = max(kf.time for kf in self.keyframes)
            min_value = min(kf.value for kf in self.keyframes)
            max_value = max(kf.value for kf in self.keyframes)
            
            # 添加边距
            margin = 50
            rect = QRectF(min_time - margin, min_value - margin, 
                         max_time - min_time + 2 * margin, 
                         max_value - min_value + 2 * margin)
            
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)


class KeyframeEditor(QWidget):
    """专业关键帧编辑器组件"""
    
    # 信号
    keyframe_added = pyqtSignal(object, float, float)  # 关键帧添加
    keyframe_removed = pyqtSignal(object)             # 关键帧移除
    keyframe_moved = pyqtSignal(object, float, float)  # 关键帧移动
    keyframe_selected = pyqtSignal(object)             # 关键帧选中
    interpolation_changed = pyqtSignal(object, str)   # 插值模式变化
    easing_changed = pyqtSignal(object, str)          # 缓动类型变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_keyframe_type = KeyframeType.POSITION
        self.keyframes = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # 主编辑区域
        self.editor_view = KeyframeEditorView()
        layout.addWidget(self.editor_view)
        
        # 属性面板
        self._create_properties_panel()
        layout.addWidget(self.properties_panel)
    
    def _create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(20, 20))
        
        # 关键帧类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems([t.value for t in KeyframeType])
        self.type_combo.setCurrentText(KeyframeType.POSITION.value)
        self.toolbar.addWidget(QLabel("类型:"))
        self.toolbar.addWidget(self.type_combo)
        
        self.toolbar.addSeparator()
        
        # 插值模式
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems([m.value for m in InterpolationMode])
        self.interpolation_combo.setCurrentText(InterpolationMode.LINEAR.value)
        self.toolbar.addWidget(QLabel("插值:"))
        self.toolbar.addWidget(self.interpolation_combo)
        
        self.toolbar.addSeparator()
        
        # 缓动类型
        self.easing_combo = QComboBox()
        self.easing_combo.addItems([e.value for e in EasingType])
        self.easing_combo.setCurrentText(EasingType.LINEAR.value)
        self.toolbar.addWidget(QLabel("缓动:"))
        self.toolbar.addWidget(self.easing_combo)
        
        self.toolbar.addSeparator()
        
        # 操作按钮
        self.add_btn = QToolButton()
        self.add_btn.setText("添加")
        self.add_btn.setToolTip("添加关键帧")
        self.toolbar.addWidget(self.add_btn)
        
        self.remove_btn = QToolButton()
        self.remove_btn.setText("删除")
        self.remove_btn.setToolTip("删除选中关键帧")
        self.toolbar.addWidget(self.remove_btn)
        
        self.clear_btn = QToolButton()
        self.clear_btn.setText("清空")
        self.clear_btn.setToolTip("清空所有关键帧")
        self.toolbar.addWidget(self.clear_btn)
        
        self.toolbar.addSeparator()
        
        # 视图控制
        self.grid_btn = QToolButton()
        self.grid_btn.setText("网格")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.setToolTip("显示/隐藏网格")
        self.toolbar.addWidget(self.grid_btn)
        
        self.fit_btn = QToolButton()
        self.fit_btn.setText("适应")
        self.fit_btn.setToolTip("适应内容")
        self.toolbar.addWidget(self.fit_btn)
        
        self.toolbar.addStretch()
    
    def _create_properties_panel(self):
        """创建属性面板"""
        self.properties_panel = QGroupBox("关键帧属性")
        layout = QFormLayout(self.properties_panel)
        
        # 时间属性
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setSuffix("s")
        self.time_spin.setSingleStep(0.1)
        layout.addRow("时间:", self.time_spin)
        
        # 值属性
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000, 1000)
        self.value_spin.setSingleStep(0.1)
        layout.addRow("值:", self.value_spin)
        
        # 张力、连续性、偏差（用于样条插值）
        self.tension_spin = QDoubleSpinBox()
        self.tension_spin.setRange(-1, 1)
        self.tension_spin.setSingleStep(0.1)
        layout.addRow("张力:", self.tension_spin)
        
        self.continuity_spin = QDoubleSpinBox()
        self.continuity_spin.setRange(-1, 1)
        self.continuity_spin.setSingleStep(0.1)
        layout.addRow("连续性:", self.continuity_spin)
        
        self.bias_spin = QDoubleSpinBox()
        self.bias_spin.setRange(-1, 1)
        self.bias_spin.setSingleStep(0.1)
        layout.addRow("偏差:", self.bias_spin)
    
    def _connect_signals(self):
        """连接信号"""
        # 工具栏信号
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.interpolation_combo.currentTextChanged.connect(self._on_interpolation_changed)
        self.easing_combo.currentTextChanged.connect(self._on_easing_changed)
        
        self.add_btn.clicked.connect(self._add_keyframe)
        self.remove_btn.clicked.connect(self._remove_selected_keyframe)
        self.clear_btn.clicked.connect(self._clear_keyframes)
        
        self.grid_btn.toggled.connect(self._toggle_grid)
        self.fit_btn.clicked.connect(self._fit_to_content)
        
        # 编辑器视图信号
        self.editor_view.keyframe_added.connect(self.keyframe_added.emit)
        self.editor_view.keyframe_removed.connect(self.keyframe_removed.emit)
        self.editor_view.keyframe_moved.connect(self.keyframe_moved.emit)
        self.editor_view.keyframe_selected.connect(self._on_keyframe_selected)
        
        # 属性面板信号
        self.time_spin.valueChanged.connect(self._on_time_changed)
        self.value_spin.valueChanged.connect(self._on_value_changed)
        self.tension_spin.valueChanged.connect(self._on_tension_changed)
        self.continuity_spin.valueChanged.connect(self._on_continuity_changed)
        self.bias_spin.valueChanged.connect(self._on_bias_changed)
    
    def _on_type_changed(self, text: str):
        """关键帧类型变化"""
        self.current_keyframe_type = KeyframeType(text)
    
    def _on_interpolation_changed(self, text: str):
        """插值模式变化"""
        # 更新选中关键帧的插值模式
        selected = self.editor_view.selected_keyframes
        for kf in selected:
            kf.interpolation = InterpolationMode(text)
        
        self.editor_view._update_curve()
        self.interpolation_changed.emit(selected[0] if selected else None, text)
    
    def _on_easing_changed(self, text: str):
        """缓动类型变化"""
        # 更新选中关键帧的缓动类型
        selected = self.editor_view.selected_keyframes
        for kf in selected:
            kf.easing = EasingType(text)
        
        self.easing_changed.emit(selected[0] if selected else None, text)
    
    def _add_keyframe(self):
        """添加关键帧"""
        # 在中心位置添加关键帧
        time = 5.0  # 默认5秒
        value = 0.0  # 默认值
        
        keyframe = self.editor_view.add_keyframe(self.current_keyframe_type, time, value)
        self.keyframes.append(keyframe)
    
    def _remove_selected_keyframe(self):
        """删除选中的关键帧"""
        selected = self.editor_view.selected_keyframes.copy()
        for kf in selected:
            self.editor_view.remove_keyframe(kf)
            if kf in self.keyframes:
                self.keyframes.remove(kf)
    
    def _clear_keyframes(self):
        """清空关键帧"""
        self.editor_view.clear_keyframes()
        self.keyframes.clear()
    
    def _toggle_grid(self, visible: bool):
        """切换网格显示"""
        self.editor_view.set_grid_visible(visible)
    
    def _fit_to_content(self):
        """适应内容"""
        self.editor_view.fit_to_content()
    
    def _on_keyframe_selected(self, keyframe: KeyframeData):
        """关键帧选中"""
        self.keyframe_selected.emit(keyframe)
        
        # 更新属性面板
        self.time_spin.setValue(keyframe.time)
        self.value_spin.setValue(keyframe.value)
        self.tension_spin.setValue(keyframe.tension)
        self.continuity_spin.setValue(keyframe.continuity)
        self.bias_spin.setValue(keyframe.bias)
        
        # 更新工具栏
        self.interpolation_combo.setCurrentText(keyframe.interpolation.value)
        self.easing_combo.setCurrentText(keyframe.easing.value)
    
    def _on_time_changed(self, value: float):
        """时间变化"""
        selected = self.editor_view.selected_keyframes
        if selected:
            selected[0].time = value
            self.editor_view._update_curve()
    
    def _on_value_changed(self, value: float):
        """值变化"""
        selected = self.editor_view.selected_keyframes
        if selected:
            selected[0].value = value
            self.editor_view._update_curve()
    
    def _on_tension_changed(self, value: float):
        """张力变化"""
        selected = self.editor_view.selected_keyframes
        if selected:
            selected[0].tension = value
            self.editor_view._update_curve()
    
    def _on_continuity_changed(self, value: float):
        """连续性变化"""
        selected = self.editor_view.selected_keyframes
        if selected:
            selected[0].continuity = value
            self.editor_view._update_curve()
    
    def _on_bias_changed(self, value: float):
        """偏差变化"""
        selected = self.editor_view.selected_keyframes
        if selected:
            selected[0].bias = value
            self.editor_view._update_curve()
    
    def set_keyframes(self, keyframes: List[KeyframeData]):
        """设置关键帧"""
        self.keyframes = keyframes.copy()
        self.editor_view.set_keyframes(keyframes)
    
    def get_keyframes(self) -> List[KeyframeData]:
        """获取关键帧"""
        return self.keyframes.copy()
    
    def export_keyframes(self, file_path: str):
        """导出关键帧"""
        data = {
            'keyframes': [
                {
                    'time': kf.time,
                    'value': kf.value,
                    'type': kf.keyframe_type.value,
                    'easing': kf.easing.value,
                    'interpolation': kf.interpolation.value,
                    'tension': kf.tension,
                    'continuity': kf.continuity,
                    'bias': kf.bias
                }
                for kf in self.keyframes
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_keyframes(self, file_path: str):
        """导入关键帧"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keyframes = []
        for kf_data in data.get('keyframes', []):
            keyframe = KeyframeData(
                time=kf_data['time'],
                value=kf_data['value'],
                keyframe_type=KeyframeType(kf_data['type']),
                easing=EasingType(kf_data['easing']),
                interpolation=InterpolationMode(kf_data['interpolation']),
                tension=kf_data.get('tension', 0.0),
                continuity=kf_data.get('continuity', 0.0),
                bias=kf_data.get('bias', 0.0)
            )
            keyframes.append(keyframe)
        
        self.set_keyframes(keyframes)


# 工厂函数
def create_keyframe_editor() -> KeyframeEditor:
    """创建关键帧编辑器实例"""
    return KeyframeEditor()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试编辑器
    editor = create_keyframe_editor()
    editor.setWindowTitle("关键帧编辑器测试")
    editor.resize(800, 600)
    editor.show()
    
    sys.exit(app.exec())