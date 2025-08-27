#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QPushButton, QLabel, QSplitter, QFrame, QMenu,
    QToolButton, QSpinBox, QComboBox, QSlider
)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QMimeData, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, 
    QLinearGradient, QDrag, QPixmap, QAction
)


class TimelineClip(QWidget):
    """时间线片段类"""
    
    # 自定义信号
    clip_moved = pyqtSignal(object, int, int)  # clip, track_index, position
    clip_resized = pyqtSignal(object, int)  # clip, new_duration
    clip_selected = pyqtSignal(object)  # clip
    
    def __init__(self, clip, parent=None):
        super().__init__(parent)
        
        self.clip = clip
        self.selected = False
        self.dragging = False
        self.resizing = False
        self.resize_edge = None  # "left" or "right"
        
        # 设置外观
        self.setMinimumHeight(50)
        self.setMaximumHeight(50)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # 鼠标跟踪
        self.setMouseTracking(True)
        
        # 接受拖放
        self.setAcceptDrops(True)
    
    def paintEvent(self, event):
        """绘制片段"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        if self.selected:
            gradient.setColorAt(0, QColor(60, 120, 240))
            gradient.setColorAt(1, QColor(40, 80, 160))
            border_color = QColor(100, 160, 255)
        else:
            gradient.setColorAt(0, QColor(80, 80, 80))
            gradient.setColorAt(1, QColor(50, 50, 50))
            border_color = QColor(120, 120, 120)
        
        # 绘制主体
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(QRect(1, 1, self.width() - 2, self.height() - 2), 4, 4)
        
        # 绘制文本
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.setFont(QFont("Arial", 9))
        clip_name = self.clip.name
        if len(clip_name) > 20:
            clip_name = clip_name[:17] + "..."
        
        # 计算时间
        duration_seconds = self.clip.duration / 1000
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        time_text = f"{minutes}:{seconds:02d}"
        
        # 绘制名称和时长
        padding = 5
        painter.drawText(
            QRect(padding, 5, self.width() - 2 * padding, 20),
            Qt.AlignmentFlag.AlignLeft, 
            clip_name
        )
        painter.drawText(
            QRect(padding, 25, self.width() - 2 * padding, 20),
            Qt.AlignmentFlag.AlignLeft, 
            time_text
        )
        
        # 绘制边缘拖拽线（如果选中）
        if self.selected:
            edge_width = 4
            painter.setPen(QPen(QColor(180, 180, 180, 180), 1))
            painter.setBrush(QBrush(QColor(180, 180, 180, 120)))
            
            # 左边缘
            painter.drawRect(0, 0, edge_width, self.height())
            
            # 右边缘
            painter.drawRect(self.width() - edge_width, 0, edge_width, self.height())
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在边缘
            edge_width = 4
            if event.position().x() <= edge_width:
                self.resizing = True
                self.resize_edge = "left"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif event.position().x() >= self.width() - edge_width:
                self.resizing = True
                self.resize_edge = "right"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.dragging = True
                self.drag_start_pos = event.position().toPoint()
            
            # 选中当前片段
            self.selected = True
            self.clip_selected.emit(self.clip)
            self.update()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.resizing and event.buttons() == Qt.MouseButton.LeftButton:
            # 处理调整大小
            if self.resize_edge == "right":
                new_width = max(50, event.position().x())
                self.resize(new_width, self.height())
                # 发射片段调整大小信号
                new_duration = (new_width / self.parent().pixels_per_second) * 1000
                self.clip_resized.emit(self.clip, int(new_duration))
            elif self.resize_edge == "left":
                # TODO: 实现左侧调整大小
                pass
        elif self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # 处理拖动
            if (event.position() - QPoint(self.drag_start_pos)).manhattanLength() > 10:
                # 启动拖放操作
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText("timeline_clip")
                mime_data.setProperty("clip_id", self.clip.clip_id)
                drag.setMimeData(mime_data)
                
                # 创建拖放缩略图
                pixmap = QPixmap(self.size())
                self.render(pixmap)
                drag.setPixmap(pixmap)
                drag.setHotSpot(self.drag_start_pos)
                
                # 执行拖放
                drop_action = drag.exec(Qt.DropAction.MoveAction)
                self.dragging = False
        else:
            # 更新鼠标样式
            edge_width = 4
            if event.position().x() <= edge_width or event.position().x() >= self.width() - edge_width:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_edge = None
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        # TODO: 实现双击预览
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        
        # 分割操作
        split_action = menu.addAction("在此位置分割")
        split_action.triggered.connect(lambda: self.split_at_position(event.position().x()))
        
        # 删除操作
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self.delete_clip)
        
        # 显示菜单
        menu.exec(event.globalPosition().toPoint())
    
    def split_at_position(self, x_pos):
        """在指定位置分割片段"""
        # TODO: 实现分割功能
        pass
    
    def delete_clip(self):
        """删除当前片段"""
        # TODO: 实现删除功能
        parent = self.parent()
        if hasattr(parent, 'remove_clip'):
            parent.remove_clip(self)


class TimelineTrack(QWidget):
    """时间线轨道类"""
    
    def __init__(self, index, parent=None):
        super().__init__(parent)
        
        self.track_index = index
        self.clips = []
        self.pixels_per_second = 100  # 每秒像素数
        
        # 设置外观
        self.setMinimumHeight(60)
        self.setAcceptDrops(True)
        
        # 布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addStretch()
    
    def add_clip(self, clip, position=0):
        """添加片段到轨道"""
        # 创建片段组件
        clip_widget = TimelineClip(clip, self)
        
        # 计算宽度（基于时长）
        width = int((clip.duration / 1000) * self.pixels_per_second)
        clip_widget.setFixedWidth(max(50, width))
        
        # 连接信号
        clip_widget.clip_moved.connect(self.handle_clip_moved)
        clip_widget.clip_resized.connect(self.handle_clip_resized)
        clip_widget.clip_selected.connect(self.handle_clip_selected)
        
        # 添加到布局
        # 移除弹性空间
        if self.layout.count() > 0:
            stretch_item = self.layout.takeAt(self.layout.count() - 1)
            
        # 计算位置
        position_px = int(position * self.pixels_per_second / 1000)
        
        # 添加空白间隔（如果需要）
        if position_px > 0:
            spacer = QWidget()
            spacer.setFixedWidth(position_px)
            self.layout.addWidget(spacer)
        
        # 添加片段
        self.layout.addWidget(clip_widget)
        self.clips.append(clip_widget)
        
        # 添加弹性空间
        self.layout.addStretch()
        
        return clip_widget
    
    def remove_clip(self, clip_widget):
        """从轨道移除片段"""
        if clip_widget in self.clips:
            self.layout.removeWidget(clip_widget)
            clip_widget.setParent(None)
            self.clips.remove(clip_widget)
    
    def clear(self):
        """清空轨道"""
        # 移除所有片段
        for clip in self.clips[:]:
            self.remove_clip(clip)
        
        # 重置布局
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        self.layout.addStretch()
    
    def handle_clip_moved(self, clip, track_index, position):
        """处理片段移动"""
        # TODO: 实现片段移动
        pass
    
    def handle_clip_resized(self, clip, new_duration):
        """处理片段大小调整"""
        # TODO: 实现片段大小调整
        pass
    
    def handle_clip_selected(self, clip):
        """处理片段选中"""
        # 取消其他片段选中状态
        for clip_widget in self.clips:
            if clip_widget.clip != clip:
                clip_widget.selected = False
                clip_widget.update()
    
    def update_scale(self, pixels_per_second):
        """更新时间尺度"""
        self.pixels_per_second = pixels_per_second
        
        # 更新所有片段的宽度
        for clip_widget in self.clips:
            width = int((clip_widget.clip.duration / 1000) * self.pixels_per_second)
            clip_widget.setFixedWidth(max(50, width))
    
    def paintEvent(self, event):
        """绘制轨道背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 轨道背景
        painter.fillRect(event.rect(), QColor(40, 40, 40))
        
        # 绘制时间刻度线
        painter.setPen(QPen(QColor(70, 70, 70)))
        
        # 每秒一条线
        seconds_visible = self.width() // self.pixels_per_second
        for i in range(seconds_visible + 1):
            x = i * self.pixels_per_second
            if x <= self.width():
                painter.drawLine(x, 0, x, self.height())
    
    def dragEnterEvent(self, event):
        """拖放进入事件"""
        if event.mimeData().hasText() and event.mimeData().text() == "timeline_clip":
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """拖放事件"""
        if event.mimeData().hasText() and event.mimeData().text() == "timeline_clip":
            # 获取片段ID
            clip_id = event.mimeData().property("clip_id")
            
            # 查找源片段
            source_clip = None
            for clip_widget in self.clips:
                if clip_widget.clip.clip_id == clip_id:
                    source_clip = clip_widget
                    break
            
            if source_clip:
                # 计算新位置
                new_position = event.position().x()
                new_position_ms = int(new_position * 1000 / self.pixels_per_second)
                
                # 移动片段
                # TODO: 处理片段移动逻辑
                
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class TimelineRuler(QWidget):
    """时间线刻度尺"""
    
    position_changed = pyqtSignal(int)  # 当前位置（毫秒）
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.pixels_per_second = 100  # 每秒像素数
        self.current_position = 0  # 当前位置（毫秒）
        self.dragging = False
        
        # 设置外观
        self.setFixedHeight(30)
        self.setMouseTracking(True)
    
    def paintEvent(self, event):
        """绘制刻度尺"""
        painter = QPainter(self)
        
        # 刻度尺背景
        painter.fillRect(event.rect(), QColor(25, 25, 25))
        
        # 主要刻度线（每秒）和次要刻度线（每100毫秒）
        painter.setPen(QPen(QColor(200, 200, 200)))
        
        # 计算可见时间范围
        visible_range = int(self.width() / self.pixels_per_second) + 1
        
        # 绘制刻度线和时间标签
        for i in range(visible_range + 1):
            # 每秒一条主要刻度线
            x = i * self.pixels_per_second
            if x <= self.width():
                painter.drawLine(x, 15, x, 30)
                
                # 绘制时间标签
                minutes = i // 60
                seconds = i % 60
                time_text = f"{minutes}:{seconds:02d}"
                painter.drawText(x + 2, 12, time_text)
            
            # 每100毫秒一条次要刻度线
            for j in range(1, 10):
                x = i * self.pixels_per_second + j * (self.pixels_per_second / 10)
                if x <= self.width():
                    painter.drawLine(x, 25, x, 30)
        
        # 绘制当前位置指针
        current_x = int(self.current_position * self.pixels_per_second / 1000)
        painter.setPen(QPen(QColor(255, 100, 100), 2))
        painter.drawLine(current_x, 0, current_x, self.height())
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.set_position(event.position().x())
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.set_position(event.position().x())
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def set_position(self, x):
        """设置当前位置"""
        # 确保位置在有效范围内
        x = max(0, min(self.width(), x))
        
        # 转换为毫秒
        position_ms = int(x * 1000 / self.pixels_per_second)
        
        # 更新位置
        self.current_position = position_ms
        self.position_changed.emit(position_ms)
        self.update()
    
    def update_position(self, position_ms):
        """更新当前位置（从外部调用）"""
        self.current_position = position_ms
        self.update()
    
    def update_scale(self, pixels_per_second):
        """更新时间尺度"""
        self.pixels_per_second = pixels_per_second
        self.update()


class TimelineWidget(QWidget):
    """时间线组件"""
    
    # 自定义信号
    position_changed = pyqtSignal(int)  # 当前位置（毫秒）
    clip_selected = pyqtSignal(object)  # 选中的片段
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
        
        # 设置初始状态
        self.current_position = 0
        self.pixels_per_second = 100
        self.tracks = []
        
        # 创建默认轨道
        self.add_track()
        self.add_track()
        self.add_track()
    
    def init_ui(self):
        """初始化UI"""
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(0)
        
        # 创建顶部控制栏
        controls_layout = QHBoxLayout()
        
        # 添加轨道按钮
        self.add_track_button = QToolButton()
        self.add_track_button.setText("+轨道")
        self.add_track_button.clicked.connect(self.add_track)
        controls_layout.addWidget(self.add_track_button)
        
        # 缩放控制
        controls_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        controls_layout.addWidget(self.zoom_slider)
        
        # 播放控制
        self.play_button = QToolButton()
        self.play_button.setText("播放")
        self.play_button.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_button)
        
        controls_layout.addStretch()
        
        self.layout.addLayout(controls_layout)
        
        # 创建刻度尺
        self.ruler = TimelineRuler()
        self.ruler.position_changed.connect(self.set_position)
        self.layout.addWidget(self.ruler)
        
        # 创建轨道容器
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(2)
        
        # 添加滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.tracks_container)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.layout.addWidget(scroll_area)
    
    def add_track(self):
        """添加轨道"""
        track_index = len(self.tracks)
        track = TimelineTrack(track_index)
        
        # 设置初始缩放
        track.update_scale(self.pixels_per_second)
        
        # 添加到布局
        self.tracks_layout.addWidget(track)
        self.tracks.append(track)
        
        return track
    
    def remove_track(self, track_index):
        """移除轨道"""
        if 0 <= track_index < len(self.tracks):
            track = self.tracks[track_index]
            self.tracks_layout.removeWidget(track)
            track.setParent(None)
            self.tracks.pop(track_index)
            
            # 更新剩余轨道的索引
            for i, track in enumerate(self.tracks):
                track.track_index = i
    
    def update_zoom(self, value):
        """更新缩放级别"""
        self.pixels_per_second = value
        
        # 更新刻度尺
        self.ruler.update_scale(value)
        
        # 更新所有轨道
        for track in self.tracks:
            track.update_scale(value)
    
    def add_clip(self, clip, track_index=0, position=0):
        """添加片段到时间线"""
        # 确保轨道索引有效
        while track_index >= len(self.tracks):
            self.add_track()
        
        # 添加到指定轨道
        return self.tracks[track_index].add_clip(clip, position)
    
    def clear(self):
        """清空所有轨道"""
        for track in self.tracks:
            track.clear()
    
    def set_position(self, position_ms):
        """设置当前位置"""
        self.current_position = position_ms
        self.ruler.update_position(position_ms)
        self.position_changed.emit(position_ms)
    
    def toggle_play(self):
        """播放/暂停切换"""
        # TODO: 实现播放功能
        pass 