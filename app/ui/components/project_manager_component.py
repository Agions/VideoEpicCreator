#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理面板
提供项目的创建、打开、管理等功能
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QGroupBox, QTabWidget, QScrollArea, QFrame,
    QSplitter, QFileDialog, QMessageBox, QProgressBar,
    QDialog, QDialogButtonBox, QFormLayout, QMenu,
    QTreeView, QFileSystemModel, QHeaderView
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QModelIndex, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QAction

from ...core.project_manager import ProjectManager, ProjectInfo, ProjectTemplate, ProjectStatistics
from ...core.project import ProjectSettings
from ..professional_ui_system import ProfessionalStyleEngine


class ProjectItemWidget(QWidget):
    """项目列表项组件"""

    project_selected = pyqtSignal(ProjectInfo)
    project_deleted = pyqtSignal(ProjectInfo)
    project_opened = pyqtSignal(ProjectInfo)

    def __init__(self, project_info: ProjectInfo, parent=None):
        super().__init__(parent)
        self.project_info = project_info
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 项目名称和状态
        header_layout = QHBoxLayout()

        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        self.status_label = QLabel()
        self.status_label.setFixedSize(60, 20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("border-radius: 10px; padding: 2px;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # 项目描述
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumHeight(40)
        layout.addWidget(self.description_label)

        # 项目信息
        info_layout = QGridLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)

        # 创建时间
        self.created_label = QLabel()
        info_layout.addWidget(QLabel("创建:"), 0, 0)
        info_layout.addWidget(self.created_label, 0, 1)

        # 修改时间
        self.modified_label = QLabel()
        info_layout.addWidget(QLabel("修改:"), 0, 2)
        info_layout.addWidget(self.modified_label, 0, 3)

        # 视频数量
        self.video_count_label = QLabel()
        info_layout.addWidget(QLabel("视频:"), 1, 0)
        info_layout.addWidget(self.video_count_label, 1, 1)

        # 项目时长
        self.duration_label = QLabel()
        info_layout.addWidget(QLabel("时长:"), 1, 2)
        info_layout.addWidget(self.duration_label, 1, 3)

        # 文件大小
        self.size_label = QLabel()
        info_layout.addWidget(QLabel("大小:"), 2, 0)
        info_layout.addWidget(self.size_label, 2, 1)

        # 进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        info_layout.addWidget(QLabel("进度:"), 2, 2)
        info_layout.addWidget(self.progress_bar, 2, 3)

        layout.addLayout(info_layout)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.open_button = QPushButton("打开")
        self.open_button.clicked.connect(self._on_open_clicked)
        button_layout.addWidget(self.open_button)

        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.delete_button.setStyleSheet("background-color: #dc3545; color: white;")
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        # 设置悬停效果
        self.setMouseTracking(True)
        self.setStyleSheet("""
            ProjectItemWidget {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 2px;
            }
            ProjectItemWidget:hover {
                background-color: #333333;
                border-color: #007acc;
            }
        """)

    def _update_display(self):
        """更新显示信息"""
        # 基本信息
        self.name_label.setText(self.project_info.name)
        self.description_label.setText(self.project_info.description or "无描述")

        # 状态标签
        status_colors = {
            "draft": "#6c757d",
            "editing": "#007bff",
            "processing": "#ffc107",
            "completed": "#28a745",
            "exported": "#17a2b8"
        }
        status_texts = {
            "draft": "草稿",
            "editing": "编辑中",
            "processing": "处理中",
            "completed": "已完成",
            "exported": "已导出"
        }

        status = self.project_info.status
        color = status_colors.get(status, "#6c757d")
        text = status_texts.get(status, status)

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"background-color: {color}; color: white; border-radius: 10px; padding: 2px;")

        # 时间信息
        created_date = datetime.fromisoformat(self.project_info.created_at)
        modified_date = datetime.fromisoformat(self.project_info.modified_at)

        self.created_label.setText(created_date.strftime("%Y-%m-%d"))
        self.modified_label.setText(modified_date.strftime("%Y-%m-%d"))

        # 项目统计
        self.video_count_label.setText(f"{self.project_info.video_count} 个")
        self.duration_label.setText(self.project_info.get_duration_formatted())
        self.size_label.setText(f"{self.project_info.get_file_size_mb():.1f} MB")

        # 进度条
        self.progress_bar.setValue(int(self.project_info.progress * 100))

        # 设置编辑模式标签
        mode_tags = {
            "commentary": "解说",
            "compilation": "混剪",
            "monologue": "独白"
        }
        mode_tag = mode_tags.get(self.project_info.editing_mode, self.project_info.editing_mode)
        if mode_tag not in self.project_info.tags:
            self.project_info.tags.append(mode_tag)

    def _on_open_clicked(self):
        """打开项目"""
        self.project_opened.emit(self.project_info)

    def _on_delete_clicked(self):
        """删除项目"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除项目 '{self.project_info.name}' 吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.project_deleted.emit(self.project_info)

    def mouseDoubleClickEvent(self, event):
        """双击打开项目"""
        self.project_opened.emit(self.project_info)


class ProjectTemplateItemWidget(QWidget):
    """项目模板项组件"""

    template_selected = pyqtSignal(ProjectTemplate)

    def __init__(self, template: ProjectTemplate, parent=None):
        super().__init__(parent)
        self.template = template
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 模板名称
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.name_label)

        # 模板描述
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.description_label)

        # 模板分类
        self.category_label = QLabel()
        self.category_label.setStyleSheet("background-color: #007bff; color: white; padding: 4px 8px; border-radius: 4px;")
        layout.addWidget(self.category_label)

        # 设置样式
        self.setStyleSheet("""
            ProjectTemplateItemWidget {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 12px;
                margin: 5px;
                min-height: 120px;
            }
            ProjectTemplateItemWidget:hover {
                background-color: #333333;
                border-color: #007acc;
            }
        """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_display(self):
        """更新显示信息"""
        self.name_label.setText(self.template.name)
        self.description_label.setText(self.template.description)
        self.category_label.setText(self.template.category)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.template_selected.emit(self.template)


class ProjectManagementPanel(QWidget):
    """项目管理面板"""

    # 信号定义
    project_created = pyqtSignal(ProjectInfo)
    project_loaded = pyqtSignal(ProjectInfo)
    project_saved = pyqtSignal(str)
    project_closed = pyqtSignal()
    project_deleted = pyqtSignal(str)
    template_selected = pyqtSignal(ProjectTemplate)
    settings_changed = pyqtSignal(dict)

    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.style_engine = ProfessionalStyleEngine()

        self._setup_ui()
        self._connect_signals()
        self._load_projects()

    def _setup_ui(self):
        """设置UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #404040;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
                border-color: #007acc;
            }
            QTabBar::tab:hover {
                background-color: #333333;
            }
        """)

        # 项目列表标签页
        self.projects_tab = self._create_projects_tab()
        self.tab_widget.addTab(self.projects_tab, "项目列表")

        # 项目模板标签页
        self.templates_tab = self._create_templates_tab()
        self.tab_widget.addTab(self.templates_tab, "项目模板")

        # 项目设置标签页
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "项目设置")

        # 项目统计标签页
        self.statistics_tab = self._create_statistics_tab()
        self.tab_widget.addTab(self.statistics_tab, "项目统计")

        main_layout.addWidget(self.tab_widget)

    def _create_projects_tab(self) -> QWidget:
        """创建项目列表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        # 新建项目按钮
        self.new_project_button = QPushButton("新建项目")
        self.new_project_button.setIcon(self.style_engine.get_icon("add"))
        self.new_project_button.clicked.connect(self._on_new_project)
        toolbar_layout.addWidget(self.new_project_button)

        # 打开项目按钮
        self.open_project_button = QPushButton("打开项目")
        self.open_project_button.setIcon(self.style_engine.get_icon("open"))
        self.open_project_button.clicked.connect(self._on_open_project)
        toolbar_layout.addWidget(self.open_project_button)

        # 导入项目按钮
        self.import_project_button = QPushButton("导入项目")
        self.import_project_button.setIcon(self.style_engine.get_icon("import"))
        self.import_project_button.clicked.connect(self._on_import_project)
        toolbar_layout.addWidget(self.import_project_button)

        toolbar_layout.addStretch()

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索项目...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self.search_input)

        layout.addLayout(toolbar_layout)

        # 过滤器
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("分类:"))

        self.category_filter = QComboBox()
        self.category_filter.addItem("全部", "")
        self.category_filter.addItem("解说", "解说")
        self.category_filter.addItem("混剪", "混剪")
        self.category_filter.addItem("独白", "独白")
        self.category_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.category_filter)

        filter_layout.addWidget(QLabel("状态:"))

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", "")
        self.status_filter.addItem("草稿", "draft")
        self.status_filter.addItem("编辑中", "editing")
        self.status_filter.addItem("处理中", "processing")
        self.status_filter.addItem("已完成", "completed")
        self.status_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # 项目列表
        self.projects_scroll = QScrollArea()
        self.projects_scroll.setWidgetResizable(True)
        self.projects_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_layout.setSpacing(10)

        self.projects_scroll.setWidget(self.projects_container)
        layout.addWidget(self.projects_scroll)

        return widget

    def _create_templates_tab(self) -> QWidget:
        """创建项目模板标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel("选择项目模板")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # 模板分类
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("分类:"))

        self.template_category_filter = QComboBox()
        self.template_category_filter.addItem("全部", "")
        self.template_category_filter.addItem("解说", "解说")
        self.template_category_filter.addItem("混剪", "混剪")
        self.template_category_filter.addItem("独白", "独白")
        self.template_category_filter.currentTextChanged.connect(self._on_template_filter_changed)
        category_layout.addWidget(self.template_category_filter)

        category_layout.addStretch()
        layout.addLayout(category_layout)

        # 模板网格
        self.templates_container = QWidget()
        self.templates_layout = QGridLayout(self.templates_container)
        self.templates_layout.setContentsMargins(0, 0, 0, 0)
        self.templates_layout.setSpacing(15)

        templates_scroll = QScrollArea()
        templates_scroll.setWidgetResizable(True)
        templates_scroll.setWidget(self.templates_container)
        layout.addWidget(templates_scroll)

        return widget

    def _create_settings_tab(self) -> QWidget:
        """创建项目设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 设置表单
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # 自动保存设置
        self.auto_save_checkbox = QCheckBox("启用自动保存")
        self.auto_save_checkbox.setChecked(True)
        form_layout.addRow("自动保存:", self.auto_save_checkbox)

        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(60, 3600)
        self.auto_save_interval.setValue(300)
        self.auto_save_interval.setSuffix(" 秒")
        form_layout.addRow("自动保存间隔:", self.auto_save_interval)

        # 备份设置
        self.backup_checkbox = QCheckBox("启用项目备份")
        self.backup_checkbox.setChecked(True)
        form_layout.addRow("项目备份:", self.backup_checkbox)

        self.backup_count = QSpinBox()
        self.backup_count.setRange(1, 50)
        self.backup_count.setValue(5)
        self.backup_count.setSuffix(" 个")
        form_layout.addRow("备份数量:", self.backup_count)

        # 最近项目设置
        self.recent_count = QSpinBox()
        self.recent_count.setRange(5, 20)
        self.recent_count.setValue(10)
        self.recent_count.setSuffix(" 个")
        form_layout.addRow("最近项目数量:", self.recent_count)

        layout.addLayout(form_layout)

        layout.addStretch()

        # 保存按钮
        self.save_settings_button = QPushButton("保存设置")
        self.save_settings_button.clicked.connect(self._on_save_settings)
        layout.addWidget(self.save_settings_button)

        return widget

    def _create_statistics_tab(self) -> QWidget:
        """创建项目统计标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 统计信息组
        stats_group = QGroupBox("项目统计")
        stats_layout = QGridLayout()

        # 总项目数
        self.total_projects_label = QLabel("0")
        self.total_projects_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.total_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("总项目数"), 0, 0)
        stats_layout.addWidget(self.total_projects_label, 1, 0)

        # 活跃项目数
        self.active_projects_label = QLabel("0")
        self.active_projects_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.active_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("活跃项目"), 0, 1)
        stats_layout.addWidget(self.active_projects_label, 1, 1)

        # 完成项目数
        self.completed_projects_label = QLabel("0")
        self.completed_projects_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.completed_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("完成项目"), 0, 2)
        stats_layout.addWidget(self.completed_projects_label, 1, 2)

        # 总编辑时间
        self.total_time_label = QLabel("0 小时")
        self.total_time_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("总编辑时间"), 2, 0)
        stats_layout.addWidget(self.total_time_label, 3, 0)

        # 处理视频数
        self.videos_processed_label = QLabel("0")
        self.videos_processed_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.videos_processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("处理视频"), 2, 1)
        stats_layout.addWidget(self.videos_processed_label, 3, 1)

        # 导出次数
        self.exports_count_label = QLabel("0")
        self.exports_count_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.exports_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("导出次数"), 2, 2)
        stats_layout.addWidget(self.exports_count_label, 3, 2)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 磁盘使用情况
        disk_group = QGroupBox("磁盘使用情况")
        disk_layout = QVBoxLayout()

        self.disk_usage_label = QLabel("0 MB")
        self.disk_usage_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        disk_layout.addWidget(self.disk_usage_label)

        self.disk_progress = QProgressBar()
        disk_layout.addWidget(self.disk_progress)

        disk_group.setLayout(disk_layout)
        layout.addWidget(disk_group)

        layout.addStretch()

        return widget

    def _connect_signals(self):
        """连接信号"""
        # 项目管理器信号
        self.project_manager.project_list_updated.connect(self._load_projects)
        self.project_manager.project_created.connect(self._on_project_created)
        self.project_manager.project_loaded.connect(self._on_project_loaded)
        self.project_manager.project_saved.connect(self._on_project_saved)
        self.project_manager.project_deleted.connect(self._on_project_deleted)
        self.project_manager.statistics_updated.connect(self._update_statistics)

    def _load_projects(self):
        """加载项目列表"""
        # 清空现有项目
        for i in reversed(range(self.projects_layout.count())):
            item = self.projects_layout.itemAt(i).widget()
            if item:
                item.deleteLater()

        # 获取过滤后的项目列表
        filter_text = self.search_input.text()
        category = self.category_filter.currentData()
        status = self.status_filter.currentData()

        projects = self.project_manager.get_project_list(filter_text, category)

        # 如果有状态过滤
        if status:
            projects = [p for p in projects if p.status == status]

        # 添加项目项
        for project in projects:
            project_item = ProjectItemWidget(project)
            project_item.project_opened.connect(self._on_project_opened)
            project_item.project_deleted.connect(self._on_project_item_deleted)
            self.projects_layout.addWidget(project_item)

        # 添加占位符
        if not projects:
            placeholder = QLabel("没有找到项目")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #888888; font-size: 14px;")
            self.projects_layout.addWidget(placeholder)

    def _load_templates(self):
        """加载项目模板"""
        # 清空现有模板
        for i in reversed(range(self.templates_layout.count())):
            item = self.templates_layout.itemAt(i).widget()
            if item:
                item.deleteLater()

        # 获取过滤后的模板列表
        category = self.template_category_filter.currentData()
        templates = self.project_manager.get_project_templates(category or "")

        # 添加模板项
        row, col = 0, 0
        max_cols = 3

        for template in templates:
            template_item = ProjectTemplateItemWidget(template)
            template_item.template_selected.connect(self._on_template_selected)
            self.templates_layout.addWidget(template_item, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _update_statistics(self, statistics: ProjectStatistics):
        """更新统计信息"""
        self.total_projects_label.setText(str(statistics.total_projects))
        self.active_projects_label.setText(str(statistics.active_projects))
        self.completed_projects_label.setText(str(statistics.completed_projects))
        self.total_time_label.setText(f"{statistics.total_editing_time} 小时")
        self.videos_processed_label.setText(str(statistics.total_videos_processed))
        self.exports_count_label.setText(str(statistics.total_exports))

        # 更新磁盘使用情况
        disk_usage_mb = statistics.disk_usage / (1024 * 1024)
        self.disk_usage_label.setText(f"{disk_usage_mb:.1f} MB")

        # 假设最大磁盘使用为 10GB
        max_disk = 10 * 1024 * 1024 * 1024  # 10GB
        disk_progress = min(100, int((statistics.disk_usage / max_disk) * 100))
        self.disk_progress.setValue(disk_progress)

    def _on_new_project(self):
        """新建项目"""
        dialog = ProjectCreateDialog(self.project_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_projects()

    def _on_open_project(self):
        """打开项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开项目",
            "",
            "CineAIStudio 项目 (*.vecp);;所有文件 (*.*)"
        )

        if file_path:
            if self.project_manager.load_project(file_path):
                self.project_loaded.emit(self.project_manager.get_current_project().project_info)

    def _on_import_project(self):
        """导入项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入项目",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )

        if file_path:
            if self.project_manager.import_project(file_path):
                self._load_projects()
                self.project_loaded.emit(self.project_manager.get_current_project().project_info)

    def _on_search_changed(self):
        """搜索内容改变"""
        self._load_projects()

    def _on_filter_changed(self):
        """过滤器改变"""
        self._load_projects()

    def _on_template_filter_changed(self):
        """模板过滤器改变"""
        self._load_templates()

    def _on_project_opened(self, project_info: ProjectInfo):
        """项目被打开"""
        if self.project_manager.load_project(project_info.file_path):
            self.project_loaded.emit(self.project_manager.get_current_project().project_info)

    def _on_project_item_deleted(self, project_info: ProjectInfo):
        """项目项被删除"""
        if self.project_manager.delete_project(project_info.id):
            self._load_projects()
            self.project_deleted.emit(project_info.id)

    def _on_project_created(self, project_info: ProjectInfo):
        """项目创建完成"""
        self.project_created.emit(project_info)

    def _on_project_loaded(self, project_info: ProjectInfo):
        """项目加载完成"""
        self.project_loaded.emit(project_info)

    def _on_project_saved(self, file_path: str):
        """项目保存完成"""
        self.project_saved.emit(file_path)

    def _on_project_deleted(self, project_id: str):
        """项目删除完成"""
        self.project_deleted.emit(project_id)

    def _on_template_selected(self, template: ProjectTemplate):
        """模板被选择"""
        self.template_selected.emit(template)

    def _on_save_settings(self):
        """保存设置"""
        settings = {
            'auto_save_enabled': self.auto_save_checkbox.isChecked(),
            'auto_save_interval': self.auto_save_interval.value(),
            'backup_enabled': self.backup_checkbox.isChecked(),
            'backup_count': self.backup_count.value(),
            'recent_projects_count': self.recent_count.value()
        }

        self.settings_changed.emit(settings)

        QMessageBox.information(self, "设置保存", "项目设置已保存成功！")

    def refresh(self):
        """刷新面板"""
        self._load_projects()
        self._load_templates()

        # 更新统计信息
        statistics = self.project_manager.get_project_statistics()
        self._update_statistics(statistics)


class ProjectCreateDialog(QDialog):
    """项目创建对话框"""

    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_template = None

        self.setWindowTitle("创建新项目")
        self.setModal(True)
        self.resize(500, 400)

        self._setup_ui()
        self._load_templates()

    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)

        # 项目信息组
        info_group = QGroupBox("项目信息")
        info_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入项目名称")
        info_layout.addRow("项目名称:", self.name_input)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("输入项目描述（可选）")
        self.description_input.setMaximumHeight(80)
        info_layout.addRow("项目描述:", self.description_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 模板选择组
        template_group = QGroupBox("选择模板")
        template_layout = QVBoxLayout()

        self.template_combo = QComboBox()
        self.template_combo.addItem("空白项目", None)
        template_layout.addWidget(self.template_combo)

        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_templates(self):
        """加载模板列表"""
        templates = self.project_manager.get_project_templates()

        for template in templates:
            self.template_combo.addItem(f"{template.name} - {template.description}", template)

    def accept(self):
        """确认创建项目"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入项目名称！")
            return

        description = self.description_input.toPlainText().strip()
        template = self.template_combo.currentData()

        # 创建项目
        if template:
            success = self.project_manager.create_project_from_template(template.id, name, description)
        else:
            success = self.project_manager.create_new_project(name, description)

        if success:
            super().accept()
        else:
            QMessageBox.critical(self, "创建失败", "项目创建失败，请重试！")
