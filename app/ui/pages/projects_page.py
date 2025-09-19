#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理页面 - 提供项目创建、管理和编辑功能
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QDialogButtonBox, QMenu, QToolButton, QSpacerItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QPen, QBrush, QAction

from app.ui.professional_ui_system import ProfessionalCard, ProfessionalButton
from app.ui.components.loading_component import LoadingOverlay
from app.core.error_handler import ErrorHandler
from app.ui.components.error_handler import MessageType
from app.ui.components.shortcut_manager_component import ShortcutManager


class ProfessionalProjectsPage(QWidget):
    """专业项目管理页面"""
    
    # 信号定义
    project_selected = pyqtSignal(object)  # 项目选择信号
    project_edited = pyqtSignal(object)    # 项目编辑信号
    project_deleted = pyqtSignal(object)   # 项目删除信号
    project_created = pyqtSignal(object)   # 项目创建信号
    video_editing_requested = pyqtSignal(dict)  # 视频编辑请求信号
    project_duplicated = pyqtSignal(object)  # 项目复制信号
    
    def __init__(self, project_manager=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.current_project = None
        self.is_dark_theme = False
        self.projects_data = []
        self.filtered_projects = []
        self.current_view_mode = "grid"
        
        # 组件初始化
        self.loading_overlay = LoadingOverlay(self)
        self.error_handler = ErrorHandler(self)
        self.shortcut_manager = ShortcutManager(self)
        
        # 初始化项目数据
        self._init_sample_projects()
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        self._setup_shortcuts()
    
    def _init_sample_projects(self):
        """初始化示例项目数据"""
        self.projects_data = [
            {
                "id": "001",
                "name": "电影解说项目",
                "date": "2024-01-15",
                "status": "进行中",
                "description": "经典电影解说视频系列",
                "type": "电影解说",
                "duration": "00:45:30",
                "size": "2.3 GB",
                "thumbnail": None,
                "tags": ["电影", "解说", "经典"],
                "last_modified": "2024-01-15 14:30"
            },
            {
                "id": "002", 
                "name": "短视频合集",
                "date": "2024-01-14",
                "status": "已完成",
                "description": "热门短视频剪辑合集",
                "type": "短视频",
                "duration": "00:15:20",
                "size": "856 MB",
                "thumbnail": None,
                "tags": ["短视频", "热门", "合集"],
                "last_modified": "2024-01-14 16:45"
            },
            {
                "id": "003",
                "name": "教程系列", 
                "date": "2024-01-13",
                "status": "计划中",
                "description": "软件使用教程系列",
                "type": "教程",
                "duration": "00:00:00",
                "size": "0 MB",
                "thumbnail": None,
                "tags": ["教程", "软件", "学习"],
                "last_modified": "2024-01-13 09:15"
            },
            {
                "id": "004",
                "name": "产品演示",
                "date": "2024-01-12", 
                "status": "进行中",
                "description": "新产品功能演示视频",
                "type": "演示",
                "duration": "00:08:45",
                "size": "324 MB",
                "thumbnail": None,
                "tags": ["产品", "演示", "功能"],
                "last_modified": "2024-01-12 11:20"
            }
        ]
        self.filtered_projects = self.projects_data.copy()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题区域
        header_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("项目管理")
        title_label.setProperty("class", "section-title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("🔄")
        self.refresh_btn.setToolTip("刷新项目列表")
        self.refresh_btn.setProperty("class", "tool-btn")
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 左侧按钮组
        left_toolbar = QHBoxLayout()
        
        # 新建项目按钮
        self.new_project_btn = ProfessionalButton("📁 新建项目", "primary")
        left_toolbar.addWidget(self.new_project_btn)
        
        # 导入项目按钮
        self.import_project_btn = ProfessionalButton("📂 导入项目", "default")
        left_toolbar.addWidget(self.import_project_btn)
        
        # 批量操作按钮
        self.batch_actions_btn = ProfessionalButton("📋 批量操作", "default")
        batch_menu = QMenu(self)
        batch_menu.addAction("删除选中", self._batch_delete)
        batch_menu.addAction("导出选中", self._batch_export)
        batch_menu.addAction("复制选中", self._batch_duplicate)
        self.batch_actions_btn.setMenu(batch_menu)
        left_toolbar.addWidget(self.batch_actions_btn)
        
        toolbar.addLayout(left_toolbar)
        toolbar.addStretch()
        
        # 右侧搜索和筛选
        right_toolbar = QHBoxLayout()
        
        # 筛选器
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "进行中", "已完成", "计划中"])
        self.filter_combo.setMaximumWidth(100)
        self.filter_combo.setToolTip("按状态筛选")
        right_toolbar.addWidget(self.filter_combo)
        
        # 类型筛选
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["全部类型", "电影解说", "短视频", "教程", "演示"])
        self.type_filter_combo.setMaximumWidth(100)
        self.type_filter_combo.setToolTip("按类型筛选")
        right_toolbar.addWidget(self.type_filter_combo)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索项目名称、标签或描述...")
        self.search_input.setProperty("class", "search-input")
        self.search_input.setMaximumWidth(250)
        right_toolbar.addWidget(self.search_input)
        
        toolbar.addLayout(right_toolbar)
        layout.addLayout(toolbar)
        
        # 项目视图区域
        view_container = QFrame()
        view_container.setProperty("class", "view-container")
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用QStackedWidget支持不同视图模式
        self.view_stack = QStackedWidget()
        view_layout.addWidget(self.view_stack)
        
        # 网格视图
        self._setup_grid_view()
        
        # 列表视图
        self._setup_list_view()
        
        # 设置默认视图
        self.view_stack.setCurrentWidget(self.grid_view)
        
        layout.addWidget(view_container)
        
        # 状态栏
        status_bar = QHBoxLayout()
        
        # 项目统计
        self.stats_label = QLabel(f"共 {len(self.projects_data)} 个项目")
        status_bar.addWidget(self.stats_label)
        
        # 选中统计
        self.selected_label = QLabel("已选中: 0")
        status_bar.addWidget(self.selected_label)
        
        status_bar.addStretch()
        
        # 视图切换按钮组
        view_group = QFrame()
        view_group.setProperty("class", "view-toggle-group")
        view_group_layout = QHBoxLayout(view_group)
        view_group_layout.setContentsMargins(5, 5, 5, 5)
        
        self.grid_view_btn = QToolButton()
        self.grid_view_btn.setText("⊞")
        self.grid_view_btn.setToolTip("网格视图")
        self.grid_view_btn.setProperty("class", "view-toggle-btn active")
        self.grid_view_btn.setCheckable(True)
        self.grid_view_btn.setChecked(True)
        
        self.list_view_btn = QToolButton()
        self.list_view_btn.setText("☰")
        self.list_view_btn.setToolTip("列表视图")
        self.list_view_btn.setProperty("class", "view-toggle-btn")
        self.list_view_btn.setCheckable(True)
        
        view_group_layout.addWidget(self.grid_view_btn)
        view_group_layout.addWidget(self.list_view_btn)
        
        status_bar.addWidget(view_group)
        
        layout.addLayout(status_bar)
        
        # 添加加载遮罩
        self.loading_overlay.hide()

    def _setup_grid_view(self):
        """设置网格视图"""
        self.grid_view = QWidget()
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidget(self.grid_view)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_layout = QGridLayout(self.grid_view)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self._refresh_grid_view()
        self.view_stack.addWidget(self.grid_scroll)

    def _setup_list_view(self):
        """设置列表视图"""
        self.list_view = QWidget()
        list_layout = QVBoxLayout(self.list_view)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(8)
        self.project_table.setHorizontalHeaderLabels([
            "项目名称", "类型", "状态", "时长", "大小", 
            "创建时间", "最后修改", "操作"
        ])
        
        # 设置列宽
        header = self.project_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        self.project_table.setAlternatingRowColors(True)
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self._refresh_table_view()
        list_layout.addWidget(self.project_table)
        self.view_stack.addWidget(self.list_view)

    def _refresh_grid_view(self):
        """刷新网格视图"""
        # 清除现有卡片
        for i in reversed(range(self.grid_layout.count())):
            child = self.grid_layout.itemAt(i).widget()
            if child is not None:
                child.deleteLater()
        
        # 添加项目卡片
        for i, project in enumerate(self.filtered_projects):
            card = self._create_project_card(project)
            self.grid_layout.addWidget(card, i // 3, i % 3)
        
        # 添加空白区域
        if len(self.filtered_projects) == 0:
            empty_label = QLabel("📂 暂无项目")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setProperty("class", "empty-state")
            self.grid_layout.addWidget(empty_label, 0, 0, 1, 3)

    def _refresh_table_view(self):
        """刷新表格视图"""
        self.project_table.setRowCount(len(self.filtered_projects))
        
        for i, project in enumerate(self.filtered_projects):
            # 项目名称
            name_item = QTableWidgetItem(project["name"])
            name_item.setToolTip(project["description"])
            self.project_table.setItem(i, 0, name_item)
            
            # 类型
            type_item = QTableWidgetItem(project["type"])
            self.project_table.setItem(i, 1, type_item)
            
            # 状态
            status_item = QTableWidgetItem(project["status"])
            self.project_table.setItem(i, 2, status_item)
            
            # 时长
            duration_item = QTableWidgetItem(project["duration"])
            self.project_table.setItem(i, 3, duration_item)
            
            # 大小
            size_item = QTableWidgetItem(project["size"])
            self.project_table.setItem(i, 4, size_item)
            
            # 创建时间
            date_item = QTableWidgetItem(project["date"])
            self.project_table.setItem(i, 5, date_item)
            
            # 最后修改
            modified_item = QTableWidgetItem(project["last_modified"])
            self.project_table.setItem(i, 6, modified_item)
            
            # 操作按钮
            actions_widget = self._create_table_actions(project)
            self.project_table.setCellWidget(i, 7, actions_widget)

    def _create_table_actions(self, project_data: Dict[str, Any]) -> QWidget:
        """创建表格操作按钮"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 5, 5, 5)
        
        # 编辑按钮
        edit_btn = QToolButton()
        edit_btn.setText("✏️")
        edit_btn.setToolTip("编辑项目")
        edit_btn.setProperty("class", "table-action-btn")
        edit_btn.clicked.connect(lambda: self._on_edit_project(project_data))
        actions_layout.addWidget(edit_btn)
        
        # 打开按钮
        open_btn = QToolButton()
        open_btn.setText("📂")
        open_btn.setToolTip("打开项目")
        open_btn.setProperty("class", "table-action-btn")
        open_btn.clicked.connect(lambda: self._on_open_project(project_data))
        actions_layout.addWidget(open_btn)
        
        # 复制按钮
        duplicate_btn = QToolButton()
        duplicate_btn.setText("📋")
        duplicate_btn.setToolTip("复制项目")
        duplicate_btn.setProperty("class", "table-action-btn")
        duplicate_btn.clicked.connect(lambda: self._on_duplicate_project(project_data))
        actions_layout.addWidget(duplicate_btn)
        
        # 删除按钮
        delete_btn = QToolButton()
        delete_btn.setText("🗑️")
        delete_btn.setToolTip("删除项目")
        delete_btn.setProperty("class", "table-action-btn delete")
        delete_btn.clicked.connect(lambda: self._on_delete_project(project_data))
        actions_layout.addWidget(delete_btn)
        
        return actions_widget
    
    def _create_project_card(self, project_data: Dict[str, Any]) -> ProfessionalCard:
        """创建项目卡片"""
        card = ProfessionalCard()
        card.setProperty("class", "project-card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 卡片头部（图标和类型标签）
        header_layout = QHBoxLayout()
        
        # 类型图标
        type_icon = self._get_project_type_icon(project_data["type"])
        icon_label = QLabel(type_icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setProperty("class", "project-icon")
        header_layout.addWidget(icon_label)
        
        header_layout.addStretch()
        
        # 状态标签
        status_label = QLabel(project_data["status"])
        status_label.setProperty("class", f"project-status status-{project_data['status']}")
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)
        
        # 项目名称
        name_label = QLabel(project_data["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setProperty("class", "project-name")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # 项目描述
        if project_data.get("description"):
            desc_label = QLabel(project_data["description"])
            desc_label.setWordWrap(True)
            desc_label.setProperty("class", "project-desc")
            desc_label.setMaximumHeight(40)
            layout.addWidget(desc_label)
        
        # 项目详细信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # 时长和大小
        details_layout = QHBoxLayout()
        
        duration_label = QLabel(f"⏱️ {project_data['duration']}")
        duration_label.setProperty("class", "project-detail")
        details_layout.addWidget(duration_label)
        
        size_label = QLabel(f"💾 {project_data['size']}")
        size_label.setProperty("class", "project-detail")
        details_layout.addWidget(size_label)
        
        info_layout.addLayout(details_layout)
        
        # 标签
        if project_data.get("tags"):
            tags_label = QLabel(f"🏷️ {', '.join(project_data['tags'][:3])}")
            tags_label.setProperty("class", "project-tags")
            tags_label.setWordWrap(True)
            info_layout.addWidget(tags_label)
        
        # 修改时间
        modified_label = QLabel(f"📅 {project_data['last_modified']}")
        modified_label.setProperty("class", "project-date")
        info_layout.addWidget(modified_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 操作按钮
        actions_layout = QHBoxLayout()
        
        # 右键菜单按钮
        menu_btn = QToolButton()
        menu_btn.setText("⋮")
        menu_btn.setToolTip("更多操作")
        menu_btn.setProperty("class", "card-menu-btn")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # 创建菜单
        card_menu = QMenu(menu_btn)
        card_menu.addAction("📂 打开项目", lambda: self._on_open_project(project_data))
        card_menu.addAction("✏️ 编辑项目", lambda: self._on_edit_project(project_data))
        card_menu.addAction("📋 复制项目", lambda: self._on_duplicate_project(project_data))
        card_menu.addSeparator()
        card_menu.addAction("📤 导出项目", lambda: self._on_export_project(project_data))
        card_menu.addAction("🗑️ 删除项目", lambda: self._on_delete_project(project_data))
        
        menu_btn.setMenu(card_menu)
        actions_layout.addWidget(menu_btn)
        
        actions_layout.addStretch()
        
        # 快速打开按钮
        open_btn = ProfessionalButton("打开", "primary")
        open_btn.setProperty("class", "btn-small")
        open_btn.clicked.connect(lambda: self._on_open_project(project_data))
        actions_layout.addWidget(open_btn)
        
        layout.addLayout(actions_layout)
        
        # 添加内容到卡片
        card.add_content(content)
        
        # 卡片双击事件
        card.mouseDoubleClickEvent = lambda event: self._on_open_project(project_data)
        
        # 添加悬停效果
        card.enterEvent = lambda event: self._on_card_enter(card)
        card.leaveEvent = lambda event: self._on_card_leave(card)
        
        return card

    def _get_project_type_icon(self, project_type: str) -> str:
        """根据项目类型获取图标"""
        type_icons = {
            "电影解说": "🎬",
            "短视频": "📱",
            "教程": "📚",
            "演示": "💼",
            "vlog": "📹",
            "音乐": "🎵",
            "游戏": "🎮",
            "其他": "📁"
        }
        return type_icons.get(project_type, "📁")

    def _on_card_enter(self, card):
        """卡片悬停进入"""
        card.setProperty("class", "project-card hover")
        card.setStyleSheet(card.styleSheet())

    def _on_card_leave(self, card):
        """卡片悬停离开"""
        card.setProperty("class", "project-card")
        card.setStyleSheet(card.styleSheet())
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                ProfessionalProjectsPage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                
                .section-title {
                    font-size: 28px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 20px;
                }
                
                .view-container {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 12px;
                }
                
                .search-input {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                    padding: 10px 12px;
                    color: #ffffff;
                    font-size: 14px;
                }
                
                .search-input:focus {
                    border: 2px solid #177ddc;
                    background-color: #1f1f1f;
                }
                
                QComboBox {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 8px;
                    color: #ffffff;
                    min-width: 80px;
                }
                
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #ffffff;
                }
                
                .tool-btn {
                    background-color: transparent;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 8px;
                    color: #ffffff;
                    font-size: 16px;
                    min-width: 36px;
                }
                
                .tool-btn:hover {
                    background-color: #177ddc;
                    border-color: #177ddc;
                }
                
                .project-card {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 12px;
                    min-height: 240px;
                    transition: all 0.3s ease;
                }
                
                .project-card.hover {
                    border: 2px solid #177ddc;
                    background-color: #1f1f1f;
                    transform: translateY(-2px);
                }
                
                .project-icon {
                    font-size: 36px;
                }
                
                .project-name {
                    font-size: 16px;
                    font-weight: bold;
                    color: #ffffff;
                }
                
                .project-desc {
                    font-size: 12px;
                    color: #cccccc;
                    line-height: 1.4;
                }
                
                .project-detail {
                    font-size: 11px;
                    color: #999999;
                }
                
                .project-tags {
                    font-size: 11px;
                    color: #177ddc;
                }
                
                .project-date {
                    font-size: 11px;
                    color: #666666;
                }
                
                .project-status {
                    font-size: 11px;
                    padding: 4px 8px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                
                .status-进行中 {
                    background-color: #177ddc;
                    color: white;
                }
                
                .status-已完成 {
                    background-color: #52c41a;
                    color: white;
                }
                
                .status-计划中 {
                    background-color: #faad14;
                    color: white;
                }
                
                .card-menu-btn {
                    background-color: transparent;
                    border: 1px solid #444;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 14px;
                    min-width: 24px;
                }
                
                .card-menu-btn:hover {
                    background-color: #444;
                }
                
                .btn-small {
                    padding: 6px 12px;
                    font-size: 12px;
                    min-width: 60px;
                    border-radius: 6px;
                }
                
                .table-action-btn {
                    background-color: transparent;
                    border: 1px solid #444;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 14px;
                    min-width: 28px;
                    padding: 4px;
                }
                
                .table-action-btn:hover {
                    background-color: #177ddc;
                    border-color: #177ddc;
                }
                
                .table-action-btn.delete:hover {
                    background-color: #ff4d4f;
                    border-color: #ff4d4f;
                }
                
                QTableWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: none;
                    gridline-color: #444;
                    alternate-background-color: #1f1f1f;
                }
                
                QTableWidget::item {
                    padding: 12px 8px;
                    border-bottom: 1px solid #444;
                }
                
                QTableWidget::item:selected {
                    background-color: #177ddc;
                    color: #ffffff;
                }
                
                QHeaderView::section {
                    background-color: #1f1f1f;
                    color: #ffffff;
                    padding: 12px 8px;
                    border: none;
                    border-bottom: 2px solid #444;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                .view-toggle-group {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                }
                
                .view-toggle-btn {
                    background-color: transparent;
                    border: none;
                    color: #999999;
                    font-size: 14px;
                    min-width: 32px;
                    padding: 6px;
                }
                
                .view-toggle-btn.active {
                    background-color: #177ddc;
                    color: #ffffff;
                    border-radius: 4px;
                }
                
                .view-toggle-btn:hover {
                    color: #ffffff;
                }
                
                .empty-state {
                    font-size: 48px;
                    color: #666666;
                    padding: 60px 20px;
                }
            """)
        else:
            self.setStyleSheet("""
                ProfessionalProjectsPage {
                    background-color: #f5f5f5;
                    color: #262626;
                }
                
                .section-title {
                    font-size: 28px;
                    font-weight: bold;
                    color: #262626;
                    margin-bottom: 20px;
                }
                
                .view-container {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 12px;
                }
                
                .search-input {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px 12px;
                    color: #262626;
                    font-size: 14px;
                }
                
                .search-input:focus {
                    border: 2px solid #1890ff;
                    background-color: #ffffff;
                }
                
                QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 8px;
                    color: #262626;
                    min-width: 80px;
                }
                
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #262626;
                }
                
                .tool-btn {
                    background-color: transparent;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 8px;
                    color: #262626;
                    font-size: 16px;
                    min-width: 36px;
                }
                
                .tool-btn:hover {
                    background-color: #1890ff;
                    border-color: #1890ff;
                    color: white;
                }
                
                .project-card {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 12px;
                    min-height: 240px;
                    /* transition: all 0.3s ease; */
                    /* box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); */
                }
                
                .project-card.hover {
                    border: 2px solid #1890ff;
                    background-color: #f0f8ff;
                    /* transform: translateY(-2px); */
                    /* box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15); */
                }
                
                .project-icon {
                    font-size: 36px;
                }
                
                .project-name {
                    font-size: 16px;
                    font-weight: bold;
                    color: #262626;
                }
                
                .project-desc {
                    font-size: 12px;
                    color: #666666;
                    line-height: 1.4;
                }
                
                .project-detail {
                    font-size: 11px;
                    color: #999999;
                }
                
                .project-tags {
                    font-size: 11px;
                    color: #1890ff;
                }
                
                .project-date {
                    font-size: 11px;
                    color: #666666;
                }
                
                .project-status {
                    font-size: 11px;
                    padding: 4px 8px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                
                .status-进行中 {
                    background-color: #1890ff;
                    color: white;
                }
                
                .status-已完成 {
                    background-color: #52c41a;
                    color: white;
                }
                
                .status-计划中 {
                    background-color: #faad14;
                    color: white;
                }
                
                .card-menu-btn {
                    background-color: transparent;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    color: #262626;
                    font-size: 14px;
                    min-width: 24px;
                }
                
                .card-menu-btn:hover {
                    background-color: #f0f0f0;
                }
                
                .btn-small {
                    padding: 6px 12px;
                    font-size: 12px;
                    min-width: 60px;
                    border-radius: 6px;
                }
                
                .table-action-btn {
                    background-color: transparent;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    color: #262626;
                    font-size: 14px;
                    min-width: 28px;
                    padding: 4px;
                }
                
                .table-action-btn:hover {
                    background-color: #1890ff;
                    border-color: #1890ff;
                    color: white;
                }
                
                .table-action-btn.delete:hover {
                    background-color: #ff4d4f;
                    border-color: #ff4d4f;
                    color: white;
                }
                
                QTableWidget {
                    background-color: #ffffff;
                    color: #262626;
                    border: none;
                    gridline-color: #f0f0f0;
                    alternate-background-color: #fafafa;
                }
                
                QTableWidget::item {
                    padding: 12px 8px;
                    border-bottom: 1px solid #f0f0f0;
                }
                
                QTableWidget::item:selected {
                    background-color: #1890ff;
                    color: #ffffff;
                }
                
                QHeaderView::section {
                    background-color: #fafafa;
                    color: #262626;
                    padding: 12px 8px;
                    border: none;
                    border-bottom: 2px solid #f0f0f0;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                .view-toggle-group {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
                
                .view-toggle-btn {
                    background-color: transparent;
                    border: none;
                    color: #999999;
                    font-size: 14px;
                    min-width: 32px;
                    padding: 6px;
                }
                
                .view-toggle-btn.active {
                    background-color: #1890ff;
                    color: #ffffff;
                    border-radius: 4px;
                }
                
                .view-toggle-btn:hover {
                    color: #262626;
                }
                
                .empty-state {
                    font-size: 48px;
                    color: #999999;
                    padding: 60px 20px;
                }
            """)
    
    def _connect_signals(self):
        """连接信号"""
        # 主要按钮信号
        self.new_project_btn.clicked.connect(self._create_new_project)
        self.import_project_btn.clicked.connect(self._import_project)
        self.refresh_btn.clicked.connect(self._refresh_projects)
        
        # 搜索和筛选信号
        self.search_input.textChanged.connect(self._filter_projects)
        self.filter_combo.currentTextChanged.connect(self._filter_projects)
        self.type_filter_combo.currentTextChanged.connect(self._filter_projects)
        
        # 视图切换信号
        self.grid_view_btn.clicked.connect(lambda: self._switch_view("grid"))
        self.list_view_btn.clicked.connect(lambda: self._switch_view("list"))
        
        # 表格选择信号
        self.project_table.itemSelectionChanged.connect(self._update_selection_stats)
        
        # 加载完成信号
        self.loading_overlay.indicator.loading_complete.connect(self._on_loading_complete)

    def _setup_shortcuts(self):
        """设置快捷键"""
        shortcuts = [
            ("Ctrl+N", "新建项目", self._create_new_project),
            ("Ctrl+O", "打开项目", self._show_open_dialog),
            ("Ctrl+I", "导入项目", self._import_project),
            ("F5", "刷新列表", self._refresh_projects),
            ("Ctrl+F", "搜索项目", lambda: self.search_input.setFocus()),
            ("Delete", "删除选中项目", self._delete_selected_projects),
            ("Ctrl+A", "全选项目", self._select_all_projects),
            ("Escape", "取消选择", self._clear_selection)
        ]
        
        for key_seq, description, callback in shortcuts:
            self.shortcut_manager.add_shortcut(key_seq, description, callback)

    def _filter_projects(self):
        """过滤项目"""
        search_text = self.search_input.text().lower().strip()
        status_filter = self.filter_combo.currentText()
        type_filter = self.type_filter_combo.currentText()
        
        self.filtered_projects = []
        
        for project in self.projects_data:
            # 搜索过滤
            if search_text:
                search_match = (
                    search_text in project["name"].lower() or
                    search_text in project["description"].lower() or
                    any(search_text in tag.lower() for tag in project.get("tags", []))
                )
                if not search_match:
                    continue
            
            # 状态过滤
            if status_filter != "全部" and project["status"] != status_filter:
                continue
            
            # 类型过滤
            if type_filter != "全部类型" and project["type"] != type_filter:
                continue
            
            self.filtered_projects.append(project)
        
        # 更新视图
        self._refresh_grid_view()
        self._refresh_table_view()
        
        # 更新统计
        self._update_stats()

    def _switch_view(self, view_mode: str):
        """切换视图"""
        self.current_view_mode = view_mode
        
        # 更新按钮状态
        self.grid_view_btn.setChecked(view_mode == "grid")
        self.list_view_btn.setChecked(view_mode == "list")
        
        # 切换视图
        if view_mode == "grid":
            self.view_stack.setCurrentWidget(self.grid_scroll)
        else:
            self.view_stack.setCurrentWidget(self.list_view)

    def _update_selection_stats(self):
        """更新选择统计"""
        if self.current_view_mode == "list":
            selected_count = len(self.project_table.selectedItems())
            self.selected_label.setText(f"已选中: {selected_count // 8}")  # 8列
        else:
            self.selected_label.setText("已选中: 0")

    def _update_stats(self):
        """更新统计信息"""
        total_count = len(self.projects_data)
        filtered_count = len(self.filtered_projects)
        
        if total_count == filtered_count:
            self.stats_label.setText(f"共 {total_count} 个项目")
        else:
            self.stats_label.setText(f"共 {total_count} 个项目 (显示 {filtered_count})")

    def _refresh_projects(self):
        """刷新项目列表"""
        self.loading_overlay.show_loading("正在刷新项目列表...")
        
        # 模拟异步刷新
        QTimer.singleShot(1000, self._on_refresh_complete)

    def _on_refresh_complete(self):
        """刷新完成"""
        self.loading_overlay.complete_loading()
        self.error_handler.show_toast("刷新完成", "项目列表已更新", MessageType.SUCCESS)

    def _on_loading_complete(self):
        """加载完成处理"""
        self._refresh_grid_view()
        self._refresh_table_view()
        self._update_stats()

    def _batch_delete(self):
        """批量删除"""
        selected_projects = self._get_selected_projects()
        if not selected_projects:
            self.error_handler.show_toast("提示", "请先选择要删除的项目", MessageType.WARNING)
            return
        
        count = len(selected_projects)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {count} 个项目吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 执行删除
            for project in selected_projects:
                if project in self.projects_data:
                    self.projects_data.remove(project)
            
            self._filter_projects()
            self.error_handler.show_toast("删除成功", f"已删除 {count} 个项目", MessageType.SUCCESS)

    def _batch_export(self):
        """批量导出"""
        selected_projects = self._get_selected_projects()
        if not selected_projects:
            self.error_handler.show_toast("提示", "请先选择要导出的项目", MessageType.WARNING)
            return
        
        self.error_handler.show_toast("导出中", f"正在导出 {len(selected_projects)} 个项目...", MessageType.INFO)
        # 实际导出逻辑

    def _batch_duplicate(self):
        """批量复制"""
        selected_projects = self._get_selected_projects()
        if not selected_projects:
            self.error_handler.show_toast("提示", "请先选择要复制的项目", MessageType.WARNING)
            return
        
        count = len(selected_projects)
        for project in selected_projects:
            self._duplicate_project_data(project)
        
        self._filter_projects()
        self.error_handler.show_toast("复制成功", f"已复制 {count} 个项目", MessageType.SUCCESS)

    def _get_selected_projects(self) -> List[Dict[str, Any]]:
        """获取选中的项目"""
        if self.current_view_mode == "list":
            selected_rows = set()
            for item in self.project_table.selectedItems():
                selected_rows.add(item.row())
            
            selected_projects = []
            for row in selected_rows:
                if row < len(self.filtered_projects):
                    selected_projects.append(self.filtered_projects[row])
            
            return selected_projects
        
        return []

    def _select_all_projects(self):
        """全选项目"""
        if self.current_view_mode == "list":
            self.project_table.selectAll()

    def _clear_selection(self):
        """清除选择"""
        if self.current_view_mode == "list":
            self.project_table.clearSelection()

    def _delete_selected_projects(self):
        """删除选中的项目"""
        self._batch_delete()

    def _show_open_dialog(self):
        """显示打开项目对话框"""
        # 实现打开项目对话框
        pass
    
    def _create_new_project(self):
        """创建新项目"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新建项目")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 标题
        title_label = QLabel("创建新项目")
        title_label.setProperty("class", "dialog-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 项目名称
        name_layout = QVBoxLayout()
        name_label = QLabel("项目名称 *")
        name_label.setProperty("class", "field-label")
        name_layout.addWidget(name_label)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("输入项目名称...")
        name_input.setProperty("class", "input-field")
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # 项目描述
        desc_layout = QVBoxLayout()
        desc_label = QLabel("项目描述")
        desc_label.setProperty("class", "field-label")
        desc_layout.addWidget(desc_label)
        
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("输入项目描述...")
        desc_input.setMaximumHeight(80)
        desc_input.setProperty("class", "input-field")
        desc_layout.addWidget(desc_input)
        layout.addLayout(desc_layout)
        
        # 项目类型
        type_layout = QVBoxLayout()
        type_label = QLabel("项目类型 *")
        type_label.setProperty("class", "field-label")
        type_layout.addWidget(type_label)
        
        type_combo = QComboBox()
        type_combo.addItems(["电影解说", "短视频", "教程", "演示", "vlog", "音乐", "游戏", "其他"])
        type_combo.setProperty("class", "input-field")
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # 项目模板
        template_layout = QVBoxLayout()
        template_label = QLabel("项目模板")
        template_label.setProperty("class", "field-label")
        template_layout.addWidget(template_label)
        
        template_combo = QComboBox()
        template_combo.addItems(["空白项目", "电影解说模板", "短视频模板", "教程模板", "演示模板"])
        template_combo.setProperty("class", "input-field")
        template_layout.addWidget(template_combo)
        layout.addLayout(template_layout)
        
        # 标签
        tags_layout = QVBoxLayout()
        tags_label = QLabel("标签")
        tags_label.setProperty("class", "field-label")
        tags_layout.addWidget(tags_label)
        
        tags_input = QLineEdit()
        tags_input.setPlaceholderText("输入标签，用逗号分隔...")
        tags_input.setProperty("class", "input-field")
        tags_layout.addWidget(tags_input)
        layout.addLayout(tags_layout)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "btn-secondary")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(dialog.reject)
        
        create_btn = QPushButton("创建项目")
        create_btn.setProperty("class", "btn-primary")
        create_btn.setMinimumWidth(100)
        create_btn.clicked.connect(lambda: self._validate_and_create_project(
            dialog, name_input, desc_input, type_combo, template_combo, tags_input
        ))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # 设置样式
        if self.is_dark_theme:
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                .dialog-title {
                    font-size: 20px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 10px;
                }
                .field-label {
                    font-size: 14px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 5px;
                }
                .input-field {
                    background-color: #1f1f1f;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 8px;
                    color: #ffffff;
                    font-size: 13px;
                }
                .input-field:focus {
                    border: 2px solid #177ddc;
                }
                .btn-primary {
                    background-color: #177ddc;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                .btn-primary:hover {
                    background-color: #4096ff;
                }
                .btn-secondary {
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 10px 20px;
                }
                .btn-secondary:hover {
                    background-color: #444;
                }
            """)
        else:
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #262626;
                }
                .dialog-title {
                    font-size: 20px;
                    font-weight: bold;
                    color: #262626;
                    margin-bottom: 10px;
                }
                .field-label {
                    font-size: 14px;
                    font-weight: bold;
                    color: #262626;
                    margin-bottom: 5px;
                }
                .input-field {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 8px;
                    color: #262626;
                    font-size: 13px;
                }
                .input-field:focus {
                    border: 2px solid #1890ff;
                }
                .btn-primary {
                    background-color: #1890ff;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                .btn-primary:hover {
                    background-color: #4096ff;
                }
                .btn-secondary {
                    background-color: transparent;
                    color: #262626;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 10px 20px;
                }
                .btn-secondary:hover {
                    background-color: #f0f0f0;
                }
            """)
        
        # 显示对话框
        dialog.exec()

    def _validate_and_create_project(self, dialog, name_input, desc_input, type_combo, template_combo, tags_input):
        """验证并创建项目"""
        project_name = name_input.text().strip()
        project_type = type_combo.currentText()
        
        # 验证必填字段
        if not project_name:
            self.error_handler.show_toast("错误", "项目名称不能为空", MessageType.ERROR)
            return
        
        if not project_type:
            self.error_handler.show_toast("错误", "请选择项目类型", MessageType.ERROR)
            return
        
        # 创建项目
        now = datetime.now()
        project_data = {
            "id": f"{now.strftime('%Y%m%d%H%M%S')}",
            "name": project_name,
            "description": desc_input.toPlainText().strip(),
            "type": project_type,
            "template": template_combo.currentText(),
            "date": now.strftime("%Y-%m-%d"),
            "status": "计划中",
            "duration": "00:00:00",
            "size": "0 MB",
            "thumbnail": None,
            "tags": [tag.strip() for tag in tags_input.text().split(',') if tag.strip()],
            "last_modified": now.strftime("%Y-%m-%d %H:%M")
        }
        
        self.projects_data.append(project_data)
        self._filter_projects()
        
        self.project_created.emit(project_data)
        self.error_handler.show_toast("创建成功", f"项目 '{project_name}' 创建成功！", MessageType.SUCCESS)
        
        dialog.accept()
    
    def _import_project(self):
        """导入项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入项目", "", 
            "项目文件 (*.json *.zip *.vecp *.cine);;所有文件 (*)"
        )
        
        if file_path:
            self.loading_overlay.show_loading("正在导入项目...")
            
            # 模拟导入过程
            QTimer.singleShot(1500, lambda: self._complete_import(file_path))

    def _complete_import(self, file_path: str):
        """完成导入"""
        # 这里应该有实际的导入逻辑
        now = datetime.now()
        project_name = f"导入项目_{now.strftime('%H%M%S')}"
        
        project_data = {
            "id": f"{now.strftime('%Y%m%d%H%M%S')}",
            "name": project_name,
            "description": f"从文件导入的项目: {file_path}",
            "type": "其他",
            "template": "空白项目",
            "date": now.strftime("%Y-%m-%d"),
            "status": "计划中",
            "duration": "00:00:00",
            "size": "0 MB",
            "thumbnail": None,
            "tags": ["导入"],
            "last_modified": now.strftime("%Y-%m-%d %H:%M")
        }
        
        self.projects_data.append(project_data)
        self._filter_projects()
        
        self.loading_overlay.complete_loading()
        self.error_handler.show_toast("导入成功", f"项目 '{project_name}' 导入成功！", MessageType.SUCCESS)

    def _on_edit_project(self, project_data: Dict[str, Any]):
        """编辑项目"""
        self.current_project = project_data
        self.project_edited.emit(project_data)
        self.error_handler.show_toast("编辑项目", f"正在编辑项目: {project_data['name']}", MessageType.INFO)

    def _on_open_project(self, project_data: Dict[str, Any]):
        """打开项目"""
        self.current_project = project_data
        self.project_selected.emit(project_data)
        self.video_editing_requested.emit(project_data)
        self.error_handler.show_toast("打开项目", f"正在打开项目: {project_data['name']}", MessageType.INFO)

    def _on_duplicate_project(self, project_data: Dict[str, Any]):
        """复制项目"""
        self._duplicate_project_data(project_data)
        self.project_duplicated.emit(project_data)
        self.error_handler.show_toast("复制成功", f"项目 '{project_data['name']}' 已复制", MessageType.SUCCESS)

    def _duplicate_project_data(self, original_project: Dict[str, Any]):
        """复制项目数据"""
        now = datetime.now()
        duplicate_project = original_project.copy()
        duplicate_project["id"] = f"{now.strftime('%Y%m%d%H%M%S')}"
        duplicate_project["name"] = f"{original_project['name']}_副本"
        duplicate_project["date"] = now.strftime("%Y-%m-%d")
        duplicate_project["last_modified"] = now.strftime("%Y-%m-%d %H:%M")
        
        self.projects_data.append(duplicate_project)

    def _on_delete_project(self, project_data: Dict[str, Any]):
        """删除项目"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 '{project_data['name']}' 吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if project_data in self.projects_data:
                self.projects_data.remove(project_data)
                self._filter_projects()
                self.project_deleted.emit(project_data)
                self.error_handler.show_toast("删除成功", f"项目 '{project_data['name']}' 已删除", MessageType.SUCCESS)

    def _on_export_project(self, project_data: Dict[str, Any]):
        """导出项目"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出项目", f"{project_data['name']}.cine",
            "项目文件 (*.cine);;JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            self.loading_overlay.show_loading("正在导出项目...")
            
            # 模拟导出过程
            QTimer.singleShot(1000, lambda: self._complete_export(project_data, file_path))

    def _complete_export(self, project_data: Dict[str, Any], file_path: str):
        """完成导出"""
        self.loading_overlay.complete_loading()
        self.error_handler.show_toast("导出成功", f"项目 '{project_data['name']}' 已导出到 {file_path}", MessageType.SUCCESS)

    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()
        
        # 更新所有子组件主题
        for card in self.findChildren(ProfessionalCard):
            card.set_theme(is_dark_theme)
        for button in self.findChildren(ProfessionalButton):
            button.set_theme(is_dark_theme)
        
        # 更新加载遮罩主题
        self.loading_overlay._apply_styles()
        
        # 更新错误处理器主题
        self.error_handler.is_dark_theme = is_dark_theme

    def refresh_projects(self):
        """刷新项目列表"""
        self._refresh_projects()

    def get_project_count(self) -> int:
        """获取项目总数"""
        return len(self.projects_data)

    def get_filtered_project_count(self) -> int:
        """获取过滤后的项目数量"""
        return len(self.filtered_projects)

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取项目"""
        for project in self.projects_data:
            if project["id"] == project_id:
                return project
        return None

    def update_project(self, project_id: str, updated_data: Dict[str, Any]):
        """更新项目信息"""
        for i, project in enumerate(self.projects_data):
            if project["id"] == project_id:
                self.projects_data[i].update(updated_data)
                self.projects_data[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self._filter_projects()
                break

    def add_project(self, project_data: Dict[str, Any]):
        """添加项目"""
        self.projects_data.append(project_data)
        self._filter_projects()

    def remove_project(self, project_id: str):
        """移除项目"""
        self.projects_data = [p for p in self.projects_data if p["id"] != project_id]
        self._filter_projects()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ProfessionalProjectsPage()
    window.show()
    sys.exit(app.exec())