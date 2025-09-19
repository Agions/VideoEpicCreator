#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多画面预览面板 - 专业多视图对比和监控组件
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import queue
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QToolButton, QSlider, QComboBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QCheckBox, QFrame, QSpacerItem,
    QSizePolicy, QProgressBar, QMenu, QWidgetAction, QDialog,
    QDialogButtonBox, QScrollArea, QSplitter, QListWidget,
    QListWidgetItem, QTabWidget, QStackedWidget, QRadioButton,
    QButtonGroup, QSlider, QDial, QMdiArea, QMdiSubWindow,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsProxyWidget
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPointF, QRect, QThread, QRectF
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont,
    QPalette, QLinearGradient, QRadialGradient, QPainterPath,
    QCursor, QFontMetrics, QWheelEvent, QMouseEvent, QPaintEvent,
    QTransform, QPolygonF, QBrush, QPixmapCache, QGuiApplication
)

from app.core.video_preview_engine import VideoFrame, ZoomMode
from video_preview_component import VideoPreviewWidget


class ViewLayout(Enum):
    """视图布局"""
    SINGLE = "single"           # 单视图
    DUAL_HORIZONTAL = "dual_horizontal"  # 双视图水平
    DUAL_VERTICAL = "dual_vertical"      # 双视图垂直
    TRIPLE = "triple"          # 三视图
    QUAD = "quad"              # 四视图
    GRID_2X2 = "grid_2x2"       # 2x2网格
    GRID_3X3 = "grid_3x3"       # 3x3网格
    GRID_4X4 = "grid_4x4"       # 4x4网格
    CUSTOM = "custom"          # 自定义布局


class SyncMode(Enum):
    """同步模式"""
    NONE = "none"              # 无同步
    POSITION = "position"      # 位置同步
    ZOOM = "zoom"             # 缩放同步
    PLAYBACK = "playback"      # 播放同步
    FULL = "full"              # 完全同步


class DisplayMode(Enum):
    """显示模式"""
    NORMAL = "normal"          # 正常显示
    SPLIT = "split"            # 分屏对比
    OVERLAY = "overlay"        # 叠加显示
    DIFFERENCE = "difference"   # 差异显示
    BLEND = "blend"            # 混合显示


@dataclass
class ViewWindow:
    """视图窗口"""
    id: str
    title: str
    video_path: str
    position: float = 0.0
    zoom_mode: ZoomMode = ZoomMode.FIT
    zoom_level: float = 1.0
    is_active: bool = True
    is_synced: bool = True
    filter_chain: List[Any] = None
    custom_params: Dict[str, Any] = None


class VideoViewWidget(VideoPreviewWidget):
    """视频视图组件"""
    
    view_activated = pyqtSignal(str)     # 视图激活
    view_closed = pyqtSignal(str)         # 视图关闭
    position_changed = pyqtSignal(str, float)  # 位置变化
    zoom_changed = pyqtSignal(str, ZoomMode, float)  # 缩放变化
    
    def __init__(self, window_id: str, title: str, parent=None):
        super().__init__(parent)
        
        self.window_id = window_id
        self.title = title
        self.is_active = False
        self.is_synced = True
        
        # 设置标题栏
        self._create_title_bar()
        
        # 设置焦点策略
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _create_title_bar(self):
        """创建标题栏"""
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 0.7);
            padding: 2px 8px;
            font-size: 12px;
            font-weight: bold;
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 在绘制事件中绘制标题栏
        self.title_rect = QRect(0, 0, self.width(), 25)
    
    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制标题栏背景
        if self.is_active:
            title_color = QColor(76, 175, 80, 180)  # 绿色
        else:
            title_color = QColor(100, 100, 100, 180)  # 灰色
        
        painter.fillRect(self.title_rect, title_color)
        
        # 绘制标题文本
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(self.title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        # 绘制同步指示器
        if self.is_synced:
            sync_indicator = QRect(self.width() - 20, 5, 15, 15)
            painter.setBrush(QBrush(QColor(76, 175, 80)))
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.drawEllipse(sync_indicator)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        super().mousePressEvent(event)
        
        # 检查是否点击了标题栏
        if self.title_rect.contains(event.position().toPoint()):
            self.view_activated.emit(self.window_id)
    
    def set_active(self, active: bool):
        """设置激活状态"""
        self.is_active = active
        self.update()
    
    def set_synced(self, synced: bool):
        """设置同步状态"""
        self.is_synced = synced
        self.update()


class MultiViewPanel(QWidget):
    """多画面预览面板"""
    
    # 信号定义
    view_activated = pyqtSignal(str)                    # 视图激活
    view_closed = pyqtSignal(str)                      # 视图关闭
    layout_changed = pyqtSignal(ViewLayout)             # 布局变化
    sync_mode_changed = pyqtSignal(SyncMode)            # 同步模式变化
    display_mode_changed = pyqtSignal(DisplayMode)       # 显示模式变化
    
    # 操作信号
    add_view_requested = pyqtSignal()                   # 请求添加视图
    remove_view_requested = pyqtSignal(str)             # 请求移除视图
    sync_views_requested = pyqtSignal()                  # 请求同步视图
    export_layout_requested = pyqtSignal()               # 请求导出布局
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化属性
        self.current_layout = ViewLayout.QUAD
        self.sync_mode = SyncMode.POSITION
        self.display_mode = DisplayMode.NORMAL
        self.views: Dict[str, VideoViewWidget] = {}
        self.active_view_id = None
        
        # 初始化UI
        self.init_ui()
        
        # 初始化定时器
        self.init_timers()
        
        # 应用样式
        self.apply_styles()
        
        # 创建默认视图
        self.create_default_views()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 工具栏
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 视图区域
        self.view_area = self._create_view_area()
        main_layout.addWidget(self.view_area)
        
        # 控制面板
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 状态栏
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
    
    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background-color: #333; border-bottom: 1px solid #555;")
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # 布局选择
        layout.addWidget(QLabel("布局:"))
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "单视图", "双视图(水平)", "双视图(垂直)", "三视图", 
            "四视图", "2x2网格", "3x3网格", "4x4网格", "自定义"
        ])
        self.layout_combo.setCurrentText("四视图")
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        layout.addWidget(self.layout_combo)
        
        layout.addSpacing(20)
        
        # 同步模式
        layout.addWidget(QLabel("同步:"))
        
        self.sync_combo = QComboBox()
        self.sync_combo.addItems([
            "无同步", "位置同步", "缩放同步", "播放同步", "完全同步"
        ])
        self.sync_combo.setCurrentText("位置同步")
        self.sync_combo.currentTextChanged.connect(self._on_sync_mode_changed)
        layout.addWidget(self.sync_combo)
        
        layout.addSpacing(20)
        
        # 显示模式
        layout.addWidget(QLabel("显示:"))
        
        self.display_combo = QComboBox()
        self.display_combo.addItems([
            "正常", "分屏对比", "叠加显示", "差异显示", "混合显示"
        ])
        self.display_combo.setCurrentText("正常")
        self.display_combo.currentTextChanged.connect(self._on_display_mode_changed)
        layout.addWidget(self.display_combo)
        
        layout.addSpacing(20)
        
        # 操作按钮
        self.add_view_button = QToolButton()
        self.add_view_button.setText("添加视图")
        self.add_view_button.setToolTip("添加新视图")
        self.add_view_button.clicked.connect(self.add_view_requested.emit)
        layout.addWidget(self.add_view_button)
        
        self.sync_views_button = QToolButton()
        self.sync_views_button.setText("同步所有")
        self.sync_views_button.setToolTip("同步所有视图")
        self.sync_views_button.clicked.connect(self.sync_views_requested.emit)
        layout.addWidget(self.sync_views_button)
        
        self.export_button = QToolButton()
        self.export_button.setText("导出布局")
        self.export_button.setToolTip("导出当前布局")
        self.export_button.clicked.connect(self.export_layout_requested.emit)
        layout.addWidget(self.export_button)
        
        layout.addStretch()
        
        return toolbar
    
    def _create_view_area(self) -> QWidget:
        """创建视图区域"""
        area = QWidget()
        area.setObjectName("view_area")
        
        self.view_layout = QGridLayout(area)
        self.view_layout.setContentsMargins(5, 5, 5, 5)
        self.view_layout.setSpacing(2)
        
        return area
    
    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setObjectName("control_panel")
        panel.setFixedHeight(60)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # 视图信息
        self.view_info_label = QLabel("活动视图: 无")
        layout.addWidget(self.view_info_label)
        
        layout.addStretch()
        
        # 性能信息
        self.fps_label = QLabel("FPS: 0")
        layout.addWidget(self.fps_label)
        
        self.memory_label = QLabel("内存: 0MB")
        layout.addWidget(self.memory_label)
        
        self.sync_status_label = QLabel("同步: 关闭")
        layout.addWidget(self.sync_status_label)
        
        return panel
    
    def _create_status_bar(self) -> QWidget:
        """创建状态栏"""
        status_bar = QWidget()
        status_bar.setObjectName("status_bar")
        status_bar.setFixedHeight(25)
        status_bar.setStyleSheet("background-color: #222; color: white;")
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(10, 2, 10, 2)
        
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        return status_bar
    
    def init_timers(self):
        """初始化定时器"""
        # 性能监控定时器
        self.performance_timer = QTimer()
        self.performance_timer.setInterval(1000)  # 1秒更新一次
        self.performance_timer.timeout.connect(self._update_performance_stats)
        self.performance_timer.start()
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            MultiViewPanel {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 5px;
            }
            
            QWidget#view_area {
                background-color: #2b2b2b;
                border: none;
            }
            
            QWidget#control_panel {
                background-color: #333;
                border-top: 1px solid #555;
            }
            
            QComboBox {
                background-color: #444;
                border: 1px solid #666;
                color: white;
                padding: 2px 6px;
                min-width: 80px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid white;
                margin-right: 3px;
            }
            
            QToolButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                min-width: 60px;
            }
            
            QToolButton:hover {
                background-color: #45a049;
            }
            
            QToolButton:pressed {
                background-color: #3d8b40;
            }
            
            QLabel {
                color: white;
                font-size: 11px;
            }
        """)
    
    def create_default_views(self):
        """创建默认视图"""
        default_views = [
            ("view_1", "主视图"),
            ("view_2", "对比视图 1"),
            ("view_3", "对比视图 2"),
            ("view_4", "对比视图 3")
        ]
        
        for view_id, title in default_views:
            view_widget = VideoViewWidget(view_id, title)
            view_widget.view_activated.connect(self._on_view_activated)
            view_widget.view_closed.connect(self._on_view_closed)
            view_widget.position_changed.connect(self._on_position_changed)
            view_widget.zoom_changed.connect(self._on_zoom_changed)
            
            self.views[view_id] = view_widget
        
        # 应用布局
        self._apply_layout()
    
    def add_view(self, view_id: str, title: str, video_path: str = ""):
        """添加视图"""
        if view_id in self.views:
            return False
        
        view_widget = VideoViewWidget(view_id, title)
        view_widget.view_activated.connect(self._on_view_activated)
        view_widget.view_closed.connect(self._on_view_closed)
        view_widget.position_changed.connect(self._on_position_changed)
        view_widget.zoom_changed.connect(self._on_zoom_changed)
        
        self.views[view_id] = view_widget
        
        # 重新应用布局
        self._apply_layout()
        
        self.status_label.setText(f"已添加视图: {title}")
        return True
    
    def remove_view(self, view_id: str):
        """移除视图"""
        if view_id not in self.views:
            return False
        
        view_widget = self.views[view_id]
        
        # 从布局中移除
        self.view_layout.removeWidget(view_widget)
        
        # 删除视图
        del self.views[view_id]
        view_widget.deleteLater()
        
        # 重新应用布局
        self._apply_layout()
        
        self.status_label.setText(f"已移除视图: {view_id}")
        return True
    
    def set_active_view(self, view_id: str):
        """设置活动视图"""
        if view_id not in self.views:
            return False
        
        # 取消其他视图的激活状态
        for vid, view in self.views.items():
            view.set_active(vid == view_id)
        
        self.active_view_id = view_id
        
        # 更新信息
        active_view = self.views[view_id]
        self.view_info_label.setText(f"活动视图: {active_view.title}")
        
        # 发射信号
        self.view_activated.emit(view_id)
        
        return True
    
    def _apply_layout(self):
        """应用布局"""
        # 清空现有布局
        while self.view_layout.count():
            item = self.view_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # 根据布局类型添加视图
        visible_views = list(self.views.values())
        
        if self.current_layout == ViewLayout.SINGLE:
            if visible_views:
                self.view_layout.addWidget(visible_views[0], 0, 0)
        
        elif self.current_layout == ViewLayout.DUAL_HORIZONTAL:
            for i, view in enumerate(visible_views[:2]):
                self.view_layout.addWidget(view, 0, i)
        
        elif self.current_layout == ViewLayout.DUAL_VERTICAL:
            for i, view in enumerate(visible_views[:2]):
                self.view_layout.addWidget(view, i, 0)
        
        elif self.current_layout == ViewLayout.TRIPLE:
            positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
            for i, view in enumerate(visible_views[:3]):
                row, col = positions[i]
                self.view_layout.addWidget(view, row, col)
        
        elif self.current_layout == ViewLayout.QUAD:
            positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
            for i, view in enumerate(visible_views[:4]):
                row, col = positions[i]
                self.view_layout.addWidget(view, row, col)
        
        elif self.current_layout == ViewLayout.GRID_2X2:
            for i, view in enumerate(visible_views[:4]):
                row = i // 2
                col = i % 2
                self.view_layout.addWidget(view, row, col)
        
        elif self.current_layout == ViewLayout.GRID_3X3:
            for i, view in enumerate(visible_views[:9]):
                row = i // 3
                col = i % 3
                self.view_layout.addWidget(view, row, col)
        
        elif self.current_layout == ViewLayout.GRID_4X4:
            for i, view in enumerate(visible_views[:16]):
                row = i // 4
                col = i % 4
                self.view_layout.addWidget(view, row, col)
        
        # 设置行列拉伸
        if self.current_layout in [ViewLayout.GRID_2X2, ViewLayout.QUAD]:
            self.view_layout.setRowStretch(0, 1)
            self.view_layout.setRowStretch(1, 1)
            self.view_layout.setColumnStretch(0, 1)
            self.view_layout.setColumnStretch(1, 1)
        elif self.current_layout == ViewLayout.GRID_3X3:
            for i in range(3):
                self.view_layout.setRowStretch(i, 1)
                self.view_layout.setColumnStretch(i, 1)
        elif self.current_layout == ViewLayout.GRID_4X4:
            for i in range(4):
                self.view_layout.setRowStretch(i, 1)
                self.view_layout.setColumnStretch(i, 1)
    
    def _on_layout_changed(self, layout_text: str):
        """布局变化处理"""
        layout_map = {
            "单视图": ViewLayout.SINGLE,
            "双视图(水平)": ViewLayout.DUAL_HORIZONTAL,
            "双视图(垂直)": ViewLayout.DUAL_VERTICAL,
            "三视图": ViewLayout.TRIPLE,
            "四视图": ViewLayout.QUAD,
            "2x2网格": ViewLayout.GRID_2X2,
            "3x3网格": ViewLayout.GRID_3X3,
            "4x4网格": ViewLayout.GRID_4X4,
            "自定义": ViewLayout.CUSTOM
        }
        
        self.current_layout = layout_map.get(layout_text, ViewLayout.QUAD)
        self._apply_layout()
        
        # 发射信号
        self.layout_changed.emit(self.current_layout)
    
    def _on_sync_mode_changed(self, sync_text: str):
        """同步模式变化处理"""
        sync_map = {
            "无同步": SyncMode.NONE,
            "位置同步": SyncMode.POSITION,
            "缩放同步": SyncMode.ZOOM,
            "播放同步": SyncMode.PLAYBACK,
            "完全同步": SyncMode.FULL
        }
        
        self.sync_mode = sync_map.get(sync_text, SyncMode.POSITION)
        
        # 更新同步状态
        for view in self.views.values():
            view.set_synced(self.sync_mode != SyncMode.NONE)
        
        # 更新状态标签
        sync_status = "开启" if self.sync_mode != SyncMode.NONE else "关闭"
        self.sync_status_label.setText(f"同步: {sync_status}")
        
        # 发射信号
        self.sync_mode_changed.emit(self.sync_mode)
    
    def _on_display_mode_changed(self, display_text: str):
        """显示模式变化处理"""
        display_map = {
            "正常": DisplayMode.NORMAL,
            "分屏对比": DisplayMode.SPLIT,
            "叠加显示": DisplayMode.OVERLAY,
            "差异显示": DisplayMode.DIFFERENCE,
            "混合显示": DisplayMode.BLEND
        }
        
        self.display_mode = display_map.get(display_text, DisplayMode.NORMAL)
        
        # 发射信号
        self.display_mode_changed.emit(self.display_mode)
    
    def _on_view_activated(self, view_id: str):
        """视图激活处理"""
        self.set_active_view(view_id)
    
    def _on_view_closed(self, view_id: str):
        """视图关闭处理"""
        self.remove_view(view_id)
        self.view_closed.emit(view_id)
    
    def _on_position_changed(self, view_id: str, position: float):
        """位置变化处理"""
        if self.sync_mode in [SyncMode.POSITION, SyncMode.FULL] and view_id == self.active_view_id:
            # 同步其他视图的位置
            for vid, view in self.views.items():
                if vid != view_id and view.is_synced:
                    # 这里应该调用视图的跳转方法
                    pass
    
    def _on_zoom_changed(self, view_id: str, mode: ZoomMode, level: float):
        """缩放变化处理"""
        if self.sync_mode in [SyncMode.ZOOM, SyncMode.FULL] and view_id == self.active_view_id:
            # 同步其他视图的缩放
            for vid, view in self.views.items():
                if vid != view_id and view.is_synced:
                    view.set_zoom_mode(mode, level)
    
    def _update_performance_stats(self):
        """更新性能统计"""
        # 这里可以获取实际的性能数据
        fps = 30.0  # 假设30fps
        memory = 128.0  # 假设128MB内存
        
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.memory_label.setText(f"内存: {memory:.1f}MB")
    
    def sync_all_views(self):
        """同步所有视图"""
        if not self.active_view_id or self.active_view_id not in self.views:
            return
        
        active_view = self.views[self.active_view_id]
        
        for view in self.views.values():
            if view != active_view:
                # 同步缩放
                view.set_zoom_mode(active_view.zoom_mode, active_view.zoom_level)
                
                # 可以添加更多同步逻辑
                # 如位置同步、播放状态同步等
        
        self.status_label.setText("已同步所有视图")
    
    def get_view_config(self) -> Dict[str, Any]:
        """获取视图配置"""
        config = {
            "layout": self.current_layout.value,
            "sync_mode": self.sync_mode.value,
            "display_mode": self.display_mode.value,
            "views": []
        }
        
        for view_id, view in self.views.items():
            view_config = {
                "id": view_id,
                "title": view.title,
                "zoom_mode": view.zoom_mode.value,
                "zoom_level": view.zoom_level,
                "is_active": view.is_active,
                "is_synced": view.is_synced
            }
            config["views"].append(view_config)
        
        return config
    
    def set_view_config(self, config: Dict[str, Any]):
        """设置视图配置"""
        # 恢复布局
        layout_map = {v.value: v for v in ViewLayout}
        self.current_layout = layout_map.get(config.get("layout"), ViewLayout.QUAD)
        self.layout_combo.setCurrentText(config.get("layout", "四视图"))
        
        # 恢复同步模式
        sync_map = {v.value: v for v in SyncMode}
        self.sync_mode = sync_map.get(config.get("sync_mode"), SyncMode.POSITION)
        self.sync_combo.setCurrentText(config.get("sync_mode", "位置同步"))
        
        # 恢复显示模式
        display_map = {v.value: v for v in DisplayMode}
        self.display_mode = display_map.get(config.get("display_mode"), DisplayMode.NORMAL)
        self.display_combo.setCurrentText(config.get("display_mode", "正常"))
        
        # 恢复视图
        for view_config in config.get("views", []):
            view_id = view_config.get("id")
            if view_id in self.views:
                view = self.views[view_id]
                view.title = view_config.get("title", view.title)
                
                # 恢复缩放
                zoom_mode_map = {v.value: v for v in ZoomMode}
                zoom_mode = zoom_mode_map.get(view_config.get("zoom_mode"), ZoomMode.FIT)
                zoom_level = view_config.get("zoom_level", 1.0)
                view.set_zoom_mode(zoom_mode, zoom_level)
                
                view.is_active = view_config.get("is_active", False)
                view.is_synced = view_config.get("is_synced", True)
        
        # 应用布局
        self._apply_layout()
    
    def export_layout(self, file_path: str):
        """导出布局"""
        import json
        
        config = self.get_view_config()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.status_label.setText(f"布局已导出: {file_path}")
            return True
        except Exception as e:
            self.status_label.setText(f"导出失败: {str(e)}")
            return False
    
    def import_layout(self, file_path: str):
        """导入布局"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.set_view_config(config)
            self.status_label.setText(f"布局已导入: {file_path}")
            return True
        except Exception as e:
            self.status_label.setText(f"导入失败: {str(e)}")
            return False
    
    def cleanup(self):
        """清理资源"""
        self.performance_timer.stop()
        
        # 清理视图
        for view in self.views.values():
            view.deleteLater()
        
        self.views.clear()