#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
媒体库面板 - 专业视频编辑器的媒体管理组件
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QComboBox, QGroupBox, QTabWidget, QToolBar, QToolButton,
    QScrollArea, QFrame, QSizePolicy, QProgressBar, QMenu, QMessageBox,
    QApplication, QStyleFactory, QFileDialog, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QMimeData, QPoint, QRect, QUrl
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QFont, QCursor, QDrag, QPainter, QColor,
    QPen, QBrush, QLinearGradient, QFontMetrics, QStandardItemModel, QStandardItem
)

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme, 
    FontScheme, SpacingScheme, get_color, create_font
)


class MediaType(Enum):
    """媒体类型"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    SEQUENCE = "sequence"
    FOLDER = "folder"


class ViewMode(Enum):
    """视图模式"""
    LIST = "list"          # 列表视图
    GRID = "grid"          # 网格视图
    TREE = "tree"          # 树形视图
    DETAILS = "details"    # 详细信息视图


class SortMode(Enum):
    """排序模式"""
    NAME = "name"          # 按名称排序
    DATE = "date"          # 按日期排序
    SIZE = "size"          # 按大小排序
    DURATION = "duration"  # 按时长排序
    TYPE = "type"          # 按类型排序


@dataclass
class MediaItem:
    """媒体项数据类"""
    id: str
    name: str
    path: str
    type: MediaType
    thumbnail_path: Optional[str] = None
    duration: Optional[int] = None  # 毫秒
    size: Optional[int] = None    # 字节
    resolution: Optional[Tuple[int, int]] = None
    frame_rate: Optional[float] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'type': self.type.value,
            'thumbnail_path': self.thumbnail_path,
            'duration': self.duration,
            'size': self.size,
            'resolution': self.resolution,
            'frame_rate': self.frame_rate,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaItem':
        """从字典创建"""
        return cls(
            id=data['id'],
            name=data['name'],
            path=data['path'],
            type=MediaType(data['type']),
            thumbnail_path=data.get('thumbnail_path'),
            duration=data.get('duration'),
            size=data.get('size'),
            resolution=tuple(data['resolution']) if data.get('resolution') else None,
            frame_rate=data.get('frame_rate'),
            created_at=data.get('created_at'),
            modified_at=data.get('modified_at'),
            metadata=data.get('metadata', {})
        )


class MediaItemDelegate(QStyledItemDelegate):
    """媒体项代理 - 自定义绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark_theme = False
        self.thumbnail_size = QSize(120, 80)
    
    def paint(self, painter, option, index):
        """绘制媒体项"""
        # 获取媒体项数据
        media_item = index.data(Qt.ItemDataRole.UserRole)
        if not media_item:
            super().paint(painter, option, index)
            return
        
        # 设置绘制参数
        painter.save()
        
        # 绘制背景
        if option.state & QStyleFactory.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(get_color('selection', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        elif option.state & QStyleFactory.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor(get_color('hover', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        # 绘制缩略图
        thumbnail_rect = QRect(option.rect.x() + 10, option.rect.y() + 10, 
                             self.thumbnail_size.width(), self.thumbnail_size.height())
        
        if media_item.thumbnail_path and os.path.exists(media_item.thumbnail_path):
            pixmap = QPixmap(media_item.thumbnail_path)
            painter.drawPixmap(thumbnail_rect, pixmap.scaled(self.thumbnail_size, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            # 绘制默认图标
            painter.fillRect(thumbnail_rect, QColor(get_color('surface', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.setPen(QColor(get_color('border', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.drawRect(thumbnail_rect)
            
            # 绘制媒体类型图标
            icon_text = {
                MediaType.VIDEO: "🎬",
                MediaType.AUDIO: "🎵",
                MediaType.IMAGE: "🖼️",
                MediaType.SEQUENCE: "🎞️",
                MediaType.FOLDER: "📁"
            }
            
            icon = icon_text.get(media_item.type, "📄")
            painter.setFont(QFont("Arial", 24))
            painter.drawText(thumbnail_rect, Qt.AlignmentFlag.AlignCenter, icon)
        
        # 绘制文本信息
        text_rect = QRect(thumbnail_rect.right() + 10, option.rect.y() + 10,
                         option.rect.width() - thumbnail_rect.width() - 30, option.rect.height() - 20)
        
        # 设置字体
        title_font = create_font(FontScheme.FONT_SIZE_MD, FontScheme.WEIGHT_SEMI_BOLD)
        info_font = create_font(FontScheme.FONT_SIZE_SM, FontScheme.WEIGHT_REGULAR)
        
        # 绘制标题
        painter.setFont(title_font)
        painter.setPen(QColor(get_color('text_primary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        # 文本省略处理
        title_text = media_item.name
        title_metrics = QFontMetrics(title_font)
        if title_metrics.horizontalAdvance(title_text) > text_rect.width():
            title_text = title_metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, text_rect.width())
        
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, title_text)
        
        # 绘制详细信息
        info_text = self._get_info_text(media_item)
        painter.setFont(info_font)
        painter.setPen(QColor(get_color('text_secondary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        info_metrics = QFontMetrics(info_font)
        if info_metrics.horizontalAdvance(info_text) > text_rect.width():
            info_text = info_metrics.elidedText(info_text, Qt.TextElideMode.ElideRight, text_rect.width())
        
        info_rect = QRect(text_rect.x(), text_rect.y() + 25, text_rect.width(), text_rect.height() - 25)
        painter.drawText(info_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, info_text)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """返回项目大小"""
        return QSize(300, 100)
    
    def _get_info_text(self, media_item: MediaItem) -> str:
        """获取信息文本"""
        info_parts = []
        
        if media_item.duration:
            duration_str = self._format_duration(media_item.duration)
            info_parts.append(f"时长: {duration_str}")
        
        if media_item.size:
            size_str = self._format_size(media_item.size)
            info_parts.append(f"大小: {size_str}")
        
        if media_item.resolution:
            resolution_str = f"{media_item.resolution[0]}x{media_item.resolution[1]}"
            info_parts.append(f"分辨率: {resolution_str}")
        
        if media_item.frame_rate:
            info_parts.append(f"帧率: {media_item.frame_rate:.1f}fps")
        
        return " | ".join(info_parts)
    
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
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if not size_bytes:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"


class MediaLibraryPanel(QWidget):
    """媒体库面板"""
    
    # 信号定义
    video_selected = pyqtSignal(MediaItem)  # 视频选中信号
    video_double_clicked = pyqtSignal(MediaItem)  # 视频双击信号
    media_imported = pyqtSignal(str)  # 媒体导入信号
    media_removed = pyqtSignal(str)  # 媒体移除信号
    
    def __init__(self, video_manager, parent=None):
        super().__init__(parent)
        
        self.video_manager = video_manager
        self.is_dark_theme = False
        self.current_view_mode = ViewMode.GRID
        self.current_sort_mode = SortMode.NAME
        self.media_items: List[MediaItem] = []
        self.selected_items: List[MediaItem] = []
        
        # 连接视频管理器信号
        self.video_manager.video_added.connect(self._on_video_added)
        self.video_manager.video_removed.connect(self._on_video_removed)
        self.video_manager.thumbnail_generated.connect(self._on_thumbnail_updated)
        self.video_manager.metadata_updated.connect(self._on_metadata_updated)
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建工具栏
        self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # 创建搜索和过滤区域
        self._create_search_area()
        layout.addWidget(self.search_widget)
        
        # 创建主要内容区域
        self._create_content_area()
        layout.addWidget(self.content_widget)
        
        # 创建状态栏
        self._create_status_bar()
        layout.addWidget(self.status_widget)
    
    def _create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setMovable(False)
        
        # 导入按钮
        import_action = self.toolbar.addAction("📥 导入")
        import_action.setToolTip("导入媒体文件")
        import_action.triggered.connect(self._on_import_media)
        
        self.toolbar.addSeparator()
        
        # 视图模式按钮
        self.list_view_action = self.toolbar.addAction("📋 列表")
        self.list_view_action.setToolTip("列表视图")
        self.list_view_action.setCheckable(True)
        self.list_view_action.triggered.connect(lambda: self._change_view_mode(ViewMode.LIST))
        
        self.grid_view_action = self.toolbar.addAction("⊞ 网格")
        self.grid_view_action.setToolTip("网格视图")
        self.grid_view_action.setCheckable(True)
        self.grid_view_action.setChecked(True)
        self.grid_view_action.triggered.connect(lambda: self._change_view_mode(ViewMode.GRID))
        
        self.tree_view_action = self.toolbar.addAction("🌳 树形")
        self.tree_view_action.setToolTip("树形视图")
        self.tree_view_action.setCheckable(True)
        self.tree_view_action.triggered.connect(lambda: self._change_view_mode(ViewMode.TREE))
        
        self.toolbar.addSeparator()
        
        # 排序按钮
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "按名称排序", "按日期排序", "按大小排序", "按时长排序", "按类型排序"
        ])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.toolbar.addWidget(self.sort_combo)
        
        # 排序方向
        self.sort_asc_action = self.toolbar.addAction("↑ 升序")
        self.sort_asc_action.setToolTip("升序排列")
        self.sort_asc_action.setCheckable(True)
        self.sort_asc_action.setChecked(True)
        
        self.sort_desc_action = self.toolbar.addAction("↓ 降序")
        self.sort_desc_action.setToolTip("降序排列")
        self.sort_desc_action.setCheckable(True)
        self.sort_desc_action.triggered.connect(self._on_sort_order_changed)
        
        self.toolbar.addSeparator()
        
        # 刷新按钮
        refresh_action = self.toolbar.addAction("🔄 刷新")
        refresh_action.setToolTip("刷新媒体库")
        refresh_action.triggered.connect(self._refresh_library)
    
    def _create_search_area(self):
        """创建搜索区域"""
        self.search_widget = QWidget()
        search_layout = QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(SpacingScheme.PADDING_MD, SpacingScheme.PADDING_SM, 
                                       SpacingScheme.PADDING_MD, SpacingScheme.PADDING_SM)
        search_layout.setSpacing(SpacingScheme.GAP_MD)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索媒体文件...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)
        
        # 过滤器
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "视频", "音频", "图片", "序列"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.filter_combo)
        
        # 清除搜索按钮
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_btn)
    
    def _create_content_area(self):
        """创建内容区域"""
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 媒体库选项卡
        self.media_tab = self._create_media_tab()
        self.tab_widget.addTab(self.media_tab, "媒体库")
        
        # 项目文件选项卡
        self.project_tab = self._create_project_tab()
        self.tab_widget.addTab(self.project_tab, "项目文件")
        
        # 特效库选项卡
        self.effects_tab = self._create_effects_tab()
        self.tab_widget.addTab(self.effects_tab, "特效库")
        
        content_layout.addWidget(self.tab_widget)
    
    def _create_media_tab(self) -> QWidget:
        """创建媒体库选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建堆叠窗口部件用于不同视图
        self.view_stack = QStackedWidget()
        
        # 列表视图
        self.list_view = QListWidget()
        self.list_view.setDragEnabled(True)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        self.list_view.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_view.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.view_stack.addWidget(self.list_view)
        
        # 网格视图
        self.grid_view = QListWidget()
        self.grid_view.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid_view.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid_view.setDragEnabled(True)
        self.grid_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid_view.customContextMenuRequested.connect(self._show_context_menu)
        self.grid_view.itemSelectionChanged.connect(self._on_selection_changed)
        self.grid_view.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.view_stack.addWidget(self.grid_view)
        
        # 树形视图
        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderLabels(["名称", "类型", "大小", "时长", "修改时间"])
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_view.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree_view.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.view_stack.addWidget(self.tree_view)
        
        layout.addWidget(self.view_stack)
        
        # 设置当前视图
        self.view_stack.setCurrentIndex(1)  # 网格视图
        
        return widget
    
    def _create_project_tab(self) -> QWidget:
        """创建项目文件选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SpacingScheme.PADDING_MD, SpacingScheme.PADDING_MD, 
                               SpacingScheme.PADDING_MD, SpacingScheme.PADDING_MD)
        layout.setSpacing(SpacingScheme.GAP_MD)
        
        # 项目文件列表
        self.project_list = QListWidget()
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_project_context_menu)
        
        layout.addWidget(self.project_list)
        
        return widget
    
    def _create_effects_tab(self) -> QWidget:
        """创建特效库选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SpacingScheme.PADDING_MD, SpacingScheme.PADDING_MD, 
                               SpacingScheme.PADDING_MD, SpacingScheme.PADDING_MD)
        layout.setSpacing(SpacingScheme.GAP_MD)
        
        # 特效分类
        effects_label = QLabel("特效分类")
        effects_label.setFont(create_font(FontScheme.FONT_SIZE_LG, FontScheme.WEIGHT_SEMI_BOLD))
        layout.addWidget(effects_label)
        
        # 特效网格
        self.effects_grid = QGridLayout()
        self.effects_grid.setSpacing(SpacingScheme.GAP_MD)
        
        # 添加特效类别
        effect_categories = [
            ("转场", "🎭"),
            ("滤镜", "🎨"),
            ("字幕", "📝"),
            ("音频", "🎵"),
            ("动画", "✨"),
            ("调色", "🌈")
        ]
        
        for i, (name, icon) in enumerate(effect_categories):
            btn = QPushButton(f"{icon}\n{name}")
            btn.setMinimumSize(100, 80)
            btn.clicked.connect(lambda checked, n=name: self._on_effect_category_clicked(n))
            self.effects_grid.addWidget(btn, i // 3, i % 3)
        
        layout.addLayout(self.effects_grid)
        layout.addStretch()
        
        return widget
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_widget = QWidget()
        status_layout = QHBoxLayout(self.status_widget)
        status_layout.setContentsMargins(SpacingScheme.PADDING_MD, SpacingScheme.PADDING_SM, 
                                        SpacingScheme.PADDING_MD, SpacingScheme.PADDING_SM)
        status_layout.setSpacing(SpacingScheme.GAP_MD)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 项目信息
        self.item_count_label = QLabel("0 个项目")
        status_layout.addWidget(self.item_count_label)
        
        # 总大小
        self.total_size_label = QLabel("总大小: 0 B")
        status_layout.addWidget(self.total_size_label)
    
    def _apply_styles(self):
        """应用样式"""
        colors = ColorScheme.DARK_THEME if self.is_dark_theme else ColorScheme.LIGHT_THEME
        
        # 面板样式
        self.setStyleSheet(f"""
            MediaLibraryPanel {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_MD}px;
            }}
        """)
        
        # 工具栏样式
        self.toolbar.setStyleSheet(f"""
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
                min-width: 60px;
            }}
            
            QToolButton:hover {{
                background: {colors['highlight']};
            }}
            
            QToolButton:pressed {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
            
            QToolButton:checked {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
            
            QComboBox {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_SM}px;
                min-width: 100px;
            }}
            
            QComboBox:hover {{
                border-color: {colors['primary']};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {colors['text_secondary']};
            }}
        """)
        
        # 搜索区域样式
        self.search_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['surface_variant']};
                border: none;
            }}
            
            QLineEdit {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
            }}
            
            QLineEdit:focus {{
                border-color: {colors['primary']};
            }}
            
            QPushButton {{
                background-color: {colors['primary']};
                border: none;
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px {SpacingScheme.PADDING_MD}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
                font-weight: {FontScheme.WEIGHT_MEDIUM};
            }}
            
            QPushButton:hover {{
                background-color: {colors['primary_dark']};
            }}
        """)
        
        # 状态栏样式
        self.status_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['surface_variant']};
                border: none;
                border-top: 1px solid {colors['border']};
            }}
            
            QLabel {{
                color: {colors['text_secondary']};
                font-size: {FontScheme.FONT_SIZE_SM}px;
            }}
        """)
        
        # 列表视图样式
        list_style = f"""
            QListWidget {{
                background-color: {colors['surface']};
                border: none;
                outline: none;
                font-size: {FontScheme.FONT_SIZE_MD}px;
            }}
            
            QListWidget::item {{
                background-color: transparent;
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                margin: {SpacingScheme.GAP_SM}px;
                padding: {SpacingScheme.PADDING_MD}px;
                color: {colors['text_primary']};
            }}
            
            QListWidget::item:selected {{
                background-color: {colors['selection']};
                border-color: {colors['primary']};
            }}
            
            QListWidget::item:hover {{
                background-color: {colors['hover']};
            }}
        """
        
        self.list_view.setStyleSheet(list_style)
        self.grid_view.setStyleSheet(list_style)
        
        # 树形视图样式
        self.tree_view.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {colors['surface']};
                border: none;
                outline: none;
                font-size: {FontScheme.FONT_SIZE_MD}px;
                color: {colors['text_primary']};
            }}
            
            QTreeWidget::item {{
                padding: {SpacingScheme.PADDING_SM}px;
                border: none;
            }}
            
            QTreeWidget::item:selected {{
                background-color: {colors['selection']};
                color: {colors['text_primary']};
            }}
            
            QTreeWidget::item:hover {{
                background-color: {colors['hover']};
            }}
            
            QTreeWidget::header {{
                background-color: {colors['surface_variant']};
                border: none;
                border-bottom: 1px solid {colors['border']};
                padding: {SpacingScheme.PADDING_SM}px;
            }}
            
            QTreeWidget::header::section {{
                background-color: transparent;
                border: none;
                padding: {SpacingScheme.PADDING_SM}px;
                font-weight: {FontScheme.WEIGHT_MEDIUM};
                color: {colors['text_primary']};
            }}
        """)
        
        # 项目列表样式
        self.project_list.setStyleSheet(list_style)
        
        # 特效按钮样式
        for i in range(self.effects_grid.count()):
            widget = self.effects_grid.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {colors['surface']};
                        border: 1px solid {colors['border']};
                        border-radius: {SpacingScheme.RADIUS_MD}px;
                        color: {colors['text_primary']};
                        font-size: {FontScheme.FONT_SIZE_MD}px;
                        font-weight: {FontScheme.WEIGHT_MEDIUM};
                        text-align: center;
                    }}
                    
                    QPushButton:hover {{
                        background-color: {colors['surface_variant']};
                        border-color: {colors['primary']};
                    }}
                    
                    QPushButton:pressed {{
                        background-color: {colors['primary']};
                        color: {colors['text_primary']};
                    }}
                """)
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self._apply_styles()
        
        # 更新代理主题
        if hasattr(self, 'item_delegate'):
            self.item_delegate.is_dark_theme = is_dark
    
    def _change_view_mode(self, mode: ViewMode):
        """切换视图模式"""
        self.current_view_mode = mode
        
        # 更新按钮状态
        self.list_view_action.setChecked(mode == ViewMode.LIST)
        self.grid_view_action.setChecked(mode == ViewMode.GRID)
        self.tree_view_action.setChecked(mode == ViewMode.TREE)
        
        # 切换视图
        if mode == ViewMode.LIST:
            self.view_stack.setCurrentIndex(0)
            self._update_list_view()
        elif mode == ViewMode.GRID:
            self.view_stack.setCurrentIndex(1)
            self._update_grid_view()
        elif mode == ViewMode.TREE:
            self.view_stack.setCurrentIndex(2)
            self._update_tree_view()
    
    def _on_sort_changed(self, index: int):
        """排序变更处理"""
        sort_modes = [SortMode.NAME, SortMode.DATE, SortMode.SIZE, SortMode.DURATION, SortMode.TYPE]
        self.current_sort_mode = sort_modes[index]
        self._refresh_current_view()
    
    def _on_sort_order_changed(self):
        """排序方向变更处理"""
        self.sort_asc_action.setChecked(not self.sort_desc_action.isChecked())
        self._refresh_current_view()
    
    def _on_search_changed(self, text: str):
        """搜索文本变更处理"""
        self._filter_media_items(text, self.filter_combo.currentText())
    
    def _on_filter_changed(self, filter_text: str):
        """过滤器变更处理"""
        self._filter_media_items(self.search_edit.text(), filter_text)
    
    def _clear_search(self):
        """清除搜索"""
        self.search_edit.clear()
        self.filter_combo.setCurrentIndex(0)
        self._refresh_current_view()
    
    def _filter_media_items(self, search_text: str, filter_type: str):
        """过滤媒体项"""
        filtered_items = []
        
        for item in self.media_items:
            # 搜索过滤
            if search_text:
                if search_text.lower() not in item.name.lower():
                    continue
            
            # 类型过滤
            if filter_type != "全部":
                type_map = {
                    "视频": MediaType.VIDEO,
                    "音频": MediaType.AUDIO,
                    "图片": MediaType.IMAGE,
                    "序列": MediaType.SEQUENCE
                }
                if item.type != type_map.get(filter_type):
                    continue
            
            filtered_items.append(item)
        
        self._display_filtered_items(filtered_items)
    
    def _display_filtered_items(self, items: List[MediaItem]):
        """显示过滤后的项目"""
        # 根据当前视图模式显示项目
        if self.current_view_mode == ViewMode.LIST:
            self._update_list_view_with_items(items)
        elif self.current_view_mode == ViewMode.GRID:
            self._update_grid_view_with_items(items)
        elif self.current_view_mode == ViewMode.TREE:
            self._update_tree_view_with_items(items)
    
    def _refresh_current_view(self):
        """刷新当前视图"""
        if self.current_view_mode == ViewMode.LIST:
            self._update_list_view()
        elif self.current_view_mode == ViewMode.GRID:
            self._update_grid_view()
        elif self.current_view_mode == ViewMode.TREE:
            self._update_tree_view()
    
    def _update_list_view(self):
        """更新列表视图"""
        self._update_list_view_with_items(self.media_items)
    
    def _update_list_view_with_items(self, items: List[MediaItem]):
        """使用指定项目更新列表视图"""
        self.list_view.clear()
        
        for item in items:
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            
            # 设置文本
            text = f"{item.name}"
            if item.duration:
                text += f" ({self._format_duration(item.duration)})"
            
            list_item.setText(text)
            
            # 设置图标
            if item.thumbnail_path and os.path.exists(item.thumbnail_path):
                list_item.setIcon(QIcon(item.thumbnail_path))
            else:
                # 使用默认图标
                icon_map = {
                    MediaType.VIDEO: "🎬",
                    MediaType.AUDIO: "🎵",
                    MediaType.IMAGE: "🖼️",
                    MediaType.SEQUENCE: "🎞️",
                    MediaType.FOLDER: "📁"
                }
                icon = icon_map.get(item.type, "📄")
                list_item.setText(f"{icon} {text}")
            
            self.list_view.addItem(list_item)
    
    def _update_grid_view(self):
        """更新网格视图"""
        self._update_grid_view_with_items(self.media_items)
    
    def _update_grid_view_with_items(self, items: List[MediaItem]):
        """使用指定项目更新网格视图"""
        self.grid_view.clear()
        
        for item in items:
            grid_item = QListWidgetItem()
            grid_item.setData(Qt.ItemDataRole.UserRole, item)
            
            # 设置图标
            if item.thumbnail_path and os.path.exists(item.thumbnail_path):
                pixmap = QPixmap(item.thumbnail_path)
                grid_item.setIcon(QIcon(pixmap))
            else:
                # 使用默认图标
                icon_map = {
                    MediaType.VIDEO: "🎬",
                    MediaType.AUDIO: "🎵",
                    MediaType.IMAGE: "🖼️",
                    MediaType.SEQUENCE: "🎞️",
                    MediaType.FOLDER: "📁"
                }
                icon = icon_map.get(item.type, "📄")
                grid_item.setText(icon)
            
            # 设置文本
            grid_item.setText(item.name)
            grid_item.setToolTip(self._get_item_tooltip(item))
            
            self.grid_view.addItem(grid_item)
        
        # 设置网格大小
        self.grid_view.setGridSize(QSize(150, 150))
    
    def _update_tree_view(self):
        """更新树形视图"""
        self._update_tree_view_with_items(self.media_items)
    
    def _update_tree_view_with_items(self, items: List[MediaItem]):
        """使用指定项目更新树形视图"""
        self.tree_view.clear()
        
        # 按类型分组
        type_groups = {}
        for item in items:
            if item.type not in type_groups:
                type_groups[item.type] = []
            type_groups[item.type].append(item)
        
        # 创建树形结构
        for media_type, type_items in type_groups.items():
            # 创建类型节点
            type_names = {
                MediaType.VIDEO: "视频文件",
                MediaType.AUDIO: "音频文件",
                MediaType.IMAGE: "图片文件",
                MediaType.SEQUENCE: "序列文件",
                MediaType.FOLDER: "文件夹"
            }
            
            type_item = QTreeWidgetItem(self.tree_view)
            type_item.setText(0, type_names.get(media_type, media_type.value))
            type_item.setExpanded(True)
            
            # 添加该类型的文件
            for item in type_items:
                file_item = QTreeWidgetItem(type_item)
                file_item.setText(0, item.name)
                file_item.setText(1, item.type.value)
                file_item.setText(2, self._format_size(item.size) if item.size else "-")
                file_item.setText(3, self._format_duration(item.duration) if item.duration else "-")
                file_item.setText(4, item.modified_at or "-")
                file_item.setData(0, Qt.ItemDataRole.UserRole, item)
    
    def _get_item_tooltip(self, item: MediaItem) -> str:
        """获取项目工具提示"""
        tooltip_lines = [f"名称: {item.name}"]
        tooltip_lines.append(f"类型: {item.type.value}")
        tooltip_lines.append(f"路径: {item.path}")
        
        if item.duration:
            tooltip_lines.append(f"时长: {self._format_duration(item.duration)}")
        
        if item.size:
            tooltip_lines.append(f"大小: {self._format_size(item.size)}")
        
        if item.resolution:
            tooltip_lines.append(f"分辨率: {item.resolution[0]}x{item.resolution[1]}")
        
        if item.frame_rate:
            tooltip_lines.append(f"帧率: {item.frame_rate:.1f}fps")
        
        if item.created_at:
            tooltip_lines.append(f"创建时间: {item.created_at}")
        
        if item.modified_at:
            tooltip_lines.append(f"修改时间: {item.modified_at}")
        
        return "\n".join(tooltip_lines)
    
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
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if not size_bytes:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    def _on_import_media(self):
        """导入媒体文件"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("媒体文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.mp3 *.wav *.aac *.flac *.jpg *.png *.bmp *.tiff)")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            self._import_media_files(file_paths)
    
    def _import_media_files(self, file_paths: List[str]):
        """导入媒体文件"""
        # 通过视频管理器导入文件
        added_clips = self.video_manager.add_videos_batch(file_paths)
        
        if added_clips:
            self.status_label.setText(f"已导入 {len(added_clips)} 个文件")
            self._refresh_library()
            
            for clip in added_clips:
                self.media_imported.emit(clip.file_path)
        else:
            self.status_label.setText("导入失败")
    
    def _refresh_library(self):
        """刷新媒体库"""
        # 从视频管理器获取最新的媒体项
        self.media_items.clear()
        
        for clip in self.video_manager.videos:
            media_item = MediaItem(
                id=clip.clip_id,
                name=clip.name,
                path=clip.file_path,
                type=MediaType.VIDEO,
                thumbnail_path=clip.thumbnail,
                duration=clip.duration,
                size=clip.metadata.get('size') if clip.metadata else None,
                resolution=(
                    clip.metadata.get('width'), 
                    clip.metadata.get('height')
                ) if clip.metadata and 'width' in clip.metadata and 'height' in clip.metadata else None,
                frame_rate=clip.metadata.get('frame_rate') if clip.metadata else None,
                created_at=clip.metadata.get('created_at') if clip.metadata else None,
                modified_at=clip.metadata.get('modified_at') if clip.metadata else None,
                metadata=clip.metadata
            )
            self.media_items.append(media_item)
        
        # 更新状态信息
        self._update_status_info()
        
        # 刷新当前视图
        self._refresh_current_view()
    
    def _update_status_info(self):
        """更新状态信息"""
        item_count = len(self.media_items)
        total_size = sum(item.size for item in self.media_items if item.size)
        
        self.item_count_label.setText(f"{item_count} 个项目")
        self.total_size_label.setText(f"总大小: {self._format_size(total_size)}")
    
    def _on_selection_changed(self):
        """选择变更处理"""
        self.selected_items.clear()
        
        current_view = self.view_stack.currentWidget()
        if isinstance(current_view, QListWidget):
            for item in current_view.selectedItems():
                media_item = item.data(Qt.ItemDataRole.UserRole)
                if media_item:
                    self.selected_items.append(media_item)
        
        # 如果只选择了一个项目，发射选中信号
        if len(self.selected_items) == 1:
            self.video_selected.emit(self.selected_items[0])
    
    def _on_tree_selection_changed(self):
        """树形视图选择变更处理"""
        self.selected_items.clear()
        
        for item in self.tree_view.selectedItems():
            media_item = item.data(0, Qt.ItemDataRole.UserRole)
            if media_item:
                self.selected_items.append(media_item)
        
        # 如果只选择了一个项目，发射选中信号
        if len(self.selected_items) == 1:
            self.video_selected.emit(self.selected_items[0])
    
    def _on_item_double_clicked(self, item):
        """项目双击处理"""
        media_item = item.data(Qt.ItemDataRole.UserRole)
        if media_item:
            self.video_double_clicked.emit(media_item)
    
    def _on_tree_item_double_clicked(self, item, column):
        """树形项目双击处理"""
        media_item = item.data(0, Qt.ItemDataRole.UserRole)
        if media_item:
            self.video_double_clicked.emit(media_item)
    
    def _show_context_menu(self, position):
        """显示上下文菜单"""
        if not self.selected_items:
            return
        
        menu = QMenu(self)
        
        # 基本操作
        play_action = menu.addAction("播放")
        play_action.triggered.connect(self._play_selected_items)
        
        menu.addSeparator()
        
        # 编辑操作
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(self._rename_selected_items)
        
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self._delete_selected_items)
        
        menu.addSeparator()
        
        # 导出操作
        export_action = menu.addAction("导出")
        export_action.triggered.connect(self._export_selected_items)
        
        # 显示菜单
        menu.exec(self.sender().mapToGlobal(position))
    
    def _show_project_context_menu(self, position):
        """显示项目上下文菜单"""
        menu = QMenu(self)
        
        # 项目操作
        open_action = menu.addAction("打开项目")
        open_action.triggered.connect(self._open_selected_project)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("删除项目")
        delete_action.triggered.connect(self._delete_selected_project)
        
        # 显示菜单
        menu.exec(self.sender().mapToGlobal(position))
    
    def _play_selected_items(self):
        """播放选中的项目"""
        if self.selected_items:
            # 播放第一个选中的项目
            self.video_double_clicked.emit(self.selected_items[0])
    
    def _rename_selected_items(self):
        """重命名选中的项目"""
        if len(self.selected_items) == 1:
            item = self.selected_items[0]
            # TODO: 实现重命名逻辑
            self.status_label.setText(f"重命名: {item.name}")
    
    def _delete_selected_items(self):
        """删除选中的项目"""
        if not self.selected_items:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(self.selected_items)} 个项目吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in self.selected_items:
                # 从视频管理器中移除
                for i, clip in enumerate(self.video_manager.videos):
                    if clip.clip_id == item.id:
                        self.video_manager.remove_video(i)
                        break
                
                self.media_removed.emit(item.path)
            
            self._refresh_library()
            self.status_label.setText(f"已删除 {len(self.selected_items)} 个项目")
    
    def _export_selected_items(self):
        """导出选中的项目"""
        if not self.selected_items:
            return
        
        # 选择导出位置
        folder_dialog = QFileDialog(self)
        folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        folder_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if folder_dialog.exec():
            export_dir = folder_dialog.selectedFiles()[0]
            # TODO: 实现导出逻辑
            self.status_label.setText(f"导出到: {export_dir}")
    
    def _open_selected_project(self):
        """打开选中的项目"""
        # TODO: 实现打开项目逻辑
        self.status_label.setText("打开项目功能开发中...")
    
    def _delete_selected_project(self):
        """删除选中的项目"""
        # TODO: 实现删除项目逻辑
        self.status_label.setText("删除项目功能开发中...")
    
    def _on_effect_category_clicked(self, category: str):
        """特效分类点击处理"""
        self.status_label.setText(f"选择特效类别: {category}")
        # TODO: 实现特效选择逻辑
    
    # 视频管理器回调方法
    def _on_video_added(self, clip):
        """视频添加回调"""
        self._refresh_library()
    
    def _on_video_removed(self, index):
        """视频移除回调"""
        self._refresh_library()
    
    def _on_thumbnail_updated(self, clip):
        """缩略图更新回调"""
        self._refresh_library()
    
    def _on_metadata_updated(self, clip):
        """元数据更新回调"""
        self._refresh_library()