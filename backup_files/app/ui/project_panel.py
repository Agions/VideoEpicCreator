#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

from app.core.project_manager import ProjectManager, ProjectInfo
import os
from datetime import datetime


class ProjectInfoDialog(QDialog):
    """项目信息对话框"""

    def __init__(self, parent=None, project_info=None):
        super().__init__(parent)
        self.setWindowTitle("项目信息")
        self.setMinimumSize(400, 300)

        self.project_info = project_info
        self.is_edit_mode = project_info is not None

        self._setup_ui()

        if self.is_edit_mode:
            self._load_project_info()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单区域
        form_group = QGroupBox("项目信息")
        form_layout = QFormLayout(form_group)

        # 项目名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入项目名称")
        form_layout.addRow("项目名称:", self.name_edit)

        # 项目描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("输入项目描述（可选）")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("项目描述:", self.description_edit)

        # 编辑模式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "短剧解说 (Commentary)",
            "短剧混剪 (Compilation)",
            "第一人称独白 (Monologue)"
        ])
        form_layout.addRow("编辑模式:", self.mode_combo)

        layout.addWidget(form_group)

        # 按钮区域
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_project_info(self):
        """加载项目信息"""
        if self.project_info:
            self.name_edit.setText(self.project_info.name)
            self.description_edit.setPlainText(self.project_info.description)

            # 设置编辑模式
            mode_map = {
                "commentary": 0,
                "compilation": 1,
                "monologue": 2
            }
            index = mode_map.get(self.project_info.editing_mode, 0)
            self.mode_combo.setCurrentIndex(index)

    def get_project_data(self):
        """获取项目数据"""
        mode_map = {
            0: "commentary",
            1: "compilation",
            2: "monologue"
        }

        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "editing_mode": mode_map[self.mode_combo.currentIndex()]
        }

    def accept(self):
        """确认"""
        data = self.get_project_data()
        if not data["name"]:
            QMessageBox.warning(self, "错误", "请输入项目名称")
            return

        super().accept()


class ProjectListWidget(QListWidget):
    """项目列表控件"""

    project_selected = pyqtSignal(ProjectInfo)
    project_edit_requested = pyqtSignal(ProjectInfo)
    project_delete_requested = pyqtSignal(str)  # project_id

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # 连接信号
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        # 设置上下文菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def add_project(self, project: ProjectInfo):
        """添加项目到列表"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, project)

        # 创建项目显示控件
        widget = self._create_project_widget(project)
        item.setSizeHint(widget.sizeHint())

        self.addItem(item)
        self.setItemWidget(item, widget)

    def _create_project_widget(self, project: ProjectInfo) -> QWidget:
        """创建项目显示控件"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)
        widget.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 5px; padding: 5px; }")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # 项目名称
        name_label = QLabel(project.name)
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(name_label)

        # 项目信息
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        # 编辑模式
        mode_map = {
            "commentary": "解说",
            "compilation": "混剪",
            "monologue": "独白"
        }
        mode_text = mode_map.get(project.editing_mode, "未知")
        mode_label = QLabel(f"模式: {mode_text}")
        mode_label.setStyleSheet("color: #666;")
        info_layout.addWidget(mode_label)

        # 视频数量
        video_label = QLabel(f"视频: {project.video_count}")
        video_label.setStyleSheet("color: #666;")
        info_layout.addWidget(video_label)

        # 时长
        duration_text = self._format_duration(project.duration)
        duration_label = QLabel(f"时长: {duration_text}")
        duration_label.setStyleSheet("color: #666;")
        info_layout.addWidget(duration_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 修改时间
        modified_time = datetime.fromisoformat(project.modified_at).strftime("%Y-%m-%d %H:%M")
        time_label = QLabel(f"修改: {modified_time}")
        time_label.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(time_label)

        return widget

    def _format_duration(self, duration: float) -> str:
        """格式化时长显示"""
        if duration < 60:
            return f"{duration:.1f}秒"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}时{minutes}分"

    def _on_item_clicked(self, item):
        """项目点击"""
        project = item.data(Qt.ItemDataRole.UserRole)
        if project:
            self.project_selected.emit(project)

    def _on_item_double_clicked(self, item):
        """项目双击"""
        project = item.data(Qt.ItemDataRole.UserRole)
        if project:
            self.project_edit_requested.emit(project)

    def _show_context_menu(self, position):
        """显示上下文菜单"""
        item = self.itemAt(position)
        if not item:
            return

        project = item.data(Qt.ItemDataRole.UserRole)
        if not project:
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        edit_action = menu.addAction("编辑项目")
        edit_action.triggered.connect(lambda: self.project_edit_requested.emit(project))

        delete_action = menu.addAction("删除项目")
        delete_action.triggered.connect(lambda: self.project_delete_requested.emit(project.id))

        menu.exec(self.mapToGlobal(position))

    def refresh_projects(self, projects):
        """刷新项目列表"""
        self.clear()
        for project in projects:
            self.add_project(project)


class ProjectPanel(QWidget):
    """项目管理面板"""

    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)

        self.project_manager = project_manager

        self._setup_ui()
        self._connect_signals()
        self._refresh_project_list()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("项目管理")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 快速操作按钮
        button_layout = QHBoxLayout()

        self.new_project_btn = QPushButton("新建项目")
        self.new_project_btn.clicked.connect(self._on_new_project)
        button_layout.addWidget(self.new_project_btn)

        self.import_project_btn = QPushButton("导入项目")
        self.import_project_btn.clicked.connect(self._on_import_project)
        button_layout.addWidget(self.import_project_btn)

        layout.addLayout(button_layout)

        # 项目列表
        list_group = QGroupBox("最近项目")
        list_layout = QVBoxLayout(list_group)

        self.project_list = ProjectListWidget()
        list_layout.addWidget(self.project_list)

        layout.addWidget(list_group)

        # 项目操作按钮
        action_layout = QHBoxLayout()

        self.edit_project_btn = QPushButton("编辑项目")
        self.edit_project_btn.setEnabled(False)
        self.edit_project_btn.clicked.connect(self._on_edit_project)
        action_layout.addWidget(self.edit_project_btn)

        self.delete_project_btn = QPushButton("删除项目")
        self.delete_project_btn.setEnabled(False)
        self.delete_project_btn.clicked.connect(self._on_delete_project)
        action_layout.addWidget(self.delete_project_btn)

        layout.addLayout(action_layout)

        # 当前选中的项目
        self.selected_project = None

    def _connect_signals(self):
        """连接信号"""
        self.project_list.project_selected.connect(self._on_project_selected)
        self.project_list.project_edit_requested.connect(self._on_project_edit_requested)
        self.project_list.project_delete_requested.connect(self._on_project_delete_requested)

        # 项目管理器信号
        self.project_manager.project_list_updated.connect(self._refresh_project_list)

    def _refresh_project_list(self):
        """刷新项目列表"""
        projects = self.project_manager.get_project_list()
        # 按修改时间排序
        projects.sort(key=lambda p: p.modified_at, reverse=True)
        self.project_list.refresh_projects(projects)

    def _on_new_project(self):
        """新建项目"""
        dialog = ProjectInfoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_project_data()
            project = self.project_manager.create_project(
                data["name"],
                data["description"],
                data["editing_mode"]
            )
            QMessageBox.information(self, "成功", f"项目 '{project.name}' 创建成功")

    def _on_import_project(self):
        """导入项目"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("CineAIStudio项目文件 (*.vecp)")

        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            if self.project_manager.load_project(file_path):
                QMessageBox.information(self, "成功", "项目导入成功")
            else:
                QMessageBox.warning(self, "失败", "项目导入失败")

    def _on_project_selected(self, project: ProjectInfo):
        """项目选中"""
        self.selected_project = project
        self.edit_project_btn.setEnabled(True)
        self.delete_project_btn.setEnabled(True)

    def _on_project_edit_requested(self, project: ProjectInfo):
        """编辑项目请求"""
        # 这里应该打开视频编辑界面
        # 暂时显示消息
        QMessageBox.information(self, "编辑项目", f"将打开项目 '{project.name}' 的编辑界面")

    def _on_project_delete_requested(self, project_id: str):
        """删除项目请求"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个项目吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.project_manager.delete_project(project_id):
                QMessageBox.information(self, "成功", "项目删除成功")
            else:
                QMessageBox.warning(self, "失败", "项目删除失败")

    def _on_edit_project(self):
        """编辑当前选中的项目"""
        if self.selected_project:
            self._on_project_edit_requested(self.selected_project)

    def _on_delete_project(self):
        """删除当前选中的项目"""
        if self.selected_project:
            self._on_project_delete_requested(self.selected_project.id)
