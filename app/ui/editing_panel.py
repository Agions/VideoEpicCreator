#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox, QScrollArea, QFrame, QProgressBar,
    QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QDragEnterEvent, QDropEvent

from app.core.project_manager import ProjectManager, ProjectInfo
from app.config.settings_manager import SettingsManager
from project_manager_component import ProjectInfoDialog
import os
from datetime import datetime


class VideoUploadWidget(QWidget):
    """视频上传控件"""
    
    videos_uploaded = pyqtSignal(list)  # 上传的视频文件路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setAcceptDrops(True)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 拖放区域
        self.drop_area = QFrame()
        self.drop_area.setFrameStyle(QFrame.Shape.Box)
        self.drop_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
                min-height: 150px;
            }
            QFrame:hover {
                border-color: #0a84ff;
                background-color: #f0f8ff;
            }
        """)
        
        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图标和提示文字
        icon_label = QLabel("📁")
        icon_label.setFont(QFont("Arial", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(icon_label)
        
        text_label = QLabel("拖放视频文件到此处\n或点击下方按钮选择文件")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("color: #666; font-size: 14px;")
        drop_layout.addWidget(text_label)
        
        layout.addWidget(self.drop_area)
        
        # 选择文件按钮
        button_layout = QHBoxLayout()
        
        self.select_files_btn = QPushButton("选择视频文件")
        self.select_files_btn.clicked.connect(self._select_files)
        button_layout.addWidget(self.select_files_btn)
        
        self.select_folder_btn = QPushButton("选择文件夹")
        self.select_folder_btn.clicked.connect(self._select_folder)
        button_layout.addWidget(self.select_folder_btn)
        
        layout.addLayout(button_layout)
        
        # 支持的格式提示
        format_label = QLabel("支持格式: MP4, AVI, MOV, MKV, WMV, FLV")
        format_label.setStyleSheet("color: #999; font-size: 12px;")
        format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(format_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self._is_video_file(file_path):
                files.append(file_path)
        
        if files:
            self.videos_uploaded.emit(files)
        else:
            QMessageBox.warning(self, "错误", "请选择有效的视频文件")
    
    def _select_files(self):
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件",
            "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
        )
        
        if files:
            self.videos_uploaded.emit(files)
    
    def _select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择包含视频的文件夹")
        
        if folder:
            video_files = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_video_file(file_path):
                        video_files.append(file_path)
            
            if video_files:
                self.videos_uploaded.emit(video_files)
            else:
                QMessageBox.information(self, "提示", "所选文件夹中没有找到视频文件")
    
    def _is_video_file(self, file_path: str) -> bool:
        """检查是否为视频文件"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.m4v', '.3gp'}
        return os.path.splitext(file_path.lower())[1] in video_extensions


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
        
        # 设置显示文本
        display_text = f"{project.name}\n"
        display_text += f"模式: {self._get_mode_display(project.editing_mode)} | "
        display_text += f"视频: {project.video_count} | "
        display_text += f"修改: {self._format_time(project.modified_at)}"
        
        item.setText(display_text)
        
        self.addItem(item)
    
    def _get_mode_display(self, mode: str) -> str:
        """获取模式显示名称"""
        mode_map = {
            "commentary": "解说",
            "compilation": "混剪",
            "monologue": "独白"
        }
        return mode_map.get(mode, "未知")
    
    def _format_time(self, time_str: str) -> str:
        """格式化时间显示"""
        try:
            dt = datetime.fromisoformat(time_str)
            return dt.strftime("%m-%d %H:%M")
        except:
            return "未知"
    
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


class EditingPanel(QWidget):
    """编辑面板 - 右侧面板"""
    
    edit_project_requested = pyqtSignal(ProjectInfo)
    new_project_requested = pyqtSignal(dict)  # project_info
    
    def __init__(self, project_manager: ProjectManager, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        
        self.project_manager = project_manager
        self.settings_manager = settings_manager
        self.current_project = None
        
        self._setup_ui()
        self._connect_signals()
        self.refresh_project_list()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 项目列表选项卡
        self.projects_tab = self._create_projects_tab()
        self.tab_widget.addTab(self.projects_tab, "项目列表")
        
        # 新建项目选项卡
        self.new_project_tab = self._create_new_project_tab()
        self.tab_widget.addTab(self.new_project_tab, "新建项目")
    
    def _create_projects_tab(self) -> QWidget:
        """创建项目列表选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_project_list)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addStretch()
        
        self.new_project_btn = QPushButton("新建项目")
        self.new_project_btn.clicked.connect(self._switch_to_new_project_tab)
        toolbar_layout.addWidget(self.new_project_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 项目列表
        self.project_list = ProjectListWidget()
        layout.addWidget(self.project_list)
        
        # 项目操作按钮
        action_layout = QHBoxLayout()
        
        self.edit_project_btn = QPushButton("编辑项目")
        self.edit_project_btn.setEnabled(False)
        self.edit_project_btn.clicked.connect(self._edit_selected_project)
        action_layout.addWidget(self.edit_project_btn)
        
        self.delete_project_btn = QPushButton("删除项目")
        self.delete_project_btn.setEnabled(False)
        self.delete_project_btn.clicked.connect(self._delete_selected_project)
        action_layout.addWidget(self.delete_project_btn)
        
        layout.addLayout(action_layout)
        
        return tab
    
    def _create_new_project_tab(self) -> QWidget:
        """创建新建项目选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("创建新项目")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 项目信息表单
        form_group = QGroupBox("项目信息")
        form_layout = QFormLayout(form_group)
        
        # 项目名称
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("输入项目名称")
        form_layout.addRow("项目名称:", self.project_name_edit)
        
        # 项目描述
        self.project_desc_edit = QTextEdit()
        self.project_desc_edit.setPlaceholderText("输入项目描述（可选）")
        self.project_desc_edit.setMaximumHeight(80)
        form_layout.addRow("项目描述:", self.project_desc_edit)
        
        # 编辑模式
        self.editing_mode_combo = QComboBox()
        self.editing_mode_combo.addItems([
            "短剧解说 (Commentary)",
            "短剧混剪 (Compilation)",
            "第一人称独白 (Monologue)"
        ])
        form_layout.addRow("编辑模式:", self.editing_mode_combo)
        
        layout.addWidget(form_group)
        
        # 视频上传区域
        upload_group = QGroupBox("上传视频")
        upload_layout = QVBoxLayout(upload_group)
        
        self.video_upload_widget = VideoUploadWidget()
        upload_layout.addWidget(self.video_upload_widget)
        
        # 已上传文件列表
        self.uploaded_files_list = QListWidget()
        self.uploaded_files_list.setMaximumHeight(100)
        upload_layout.addWidget(self.uploaded_files_list)
        
        layout.addWidget(upload_group)
        
        # 创建按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._cancel_new_project)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.create_project_btn = QPushButton("创建项目并开始编辑")
        self.create_project_btn.setEnabled(False)
        self.create_project_btn.clicked.connect(self._create_and_edit_project)
        button_layout.addWidget(self.create_project_btn)
        
        layout.addLayout(button_layout)
        
        return tab
    
    def _connect_signals(self):
        """连接信号"""
        # 项目列表信号
        self.project_list.project_selected.connect(self._on_project_selected)
        self.project_list.project_edit_requested.connect(self._on_project_edit_requested)
        self.project_list.project_delete_requested.connect(self._on_project_delete_requested)
        
        # 新建项目信号
        self.project_name_edit.textChanged.connect(self._check_create_button_state)
        self.video_upload_widget.videos_uploaded.connect(self._on_videos_uploaded)
        
        # 项目管理器信号
        self.project_manager.project_list_updated.connect(self.refresh_project_list)
    
    def _switch_to_new_project_tab(self):
        """切换到新建项目选项卡"""
        self.tab_widget.setCurrentIndex(1)
    
    def _check_create_button_state(self):
        """检查创建按钮状态"""
        has_name = bool(self.project_name_edit.text().strip())
        has_videos = self.uploaded_files_list.count() > 0
        self.create_project_btn.setEnabled(has_name and has_videos)
    
    def _on_videos_uploaded(self, file_paths: list):
        """视频上传回调"""
        for file_path in file_paths:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.uploaded_files_list.addItem(item)
        
        self._check_create_button_state()
    
    def _create_and_edit_project(self):
        """创建项目并开始编辑"""
        # 获取项目信息
        mode_map = {0: "commentary", 1: "compilation", 2: "monologue"}
        project_info = {
            "name": self.project_name_edit.text().strip(),
            "description": self.project_desc_edit.toPlainText().strip(),
            "editing_mode": mode_map[self.editing_mode_combo.currentIndex()]
        }
        
        # 创建项目
        project = self.project_manager.create_project(
            project_info["name"],
            project_info["description"],
            project_info["editing_mode"]
        )
        
        # 添加视频文件
        for i in range(self.uploaded_files_list.count()):
            item = self.uploaded_files_list.item(i)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            self.project_manager.video_manager.add_video(file_path)
        
        # 保存项目
        self.project_manager.save_project()
        
        # 清空表单
        self._clear_new_project_form()
        
        # 切换回项目列表
        self.tab_widget.setCurrentIndex(0)
        
        # 刷新项目列表
        self.refresh_project_list()
        
        # 开始编辑项目
        self.edit_project_requested.emit(project)
    
    def _cancel_new_project(self):
        """取消新建项目"""
        self._clear_new_project_form()
        self.tab_widget.setCurrentIndex(0)
    
    def _clear_new_project_form(self):
        """清空新建项目表单"""
        self.project_name_edit.clear()
        self.project_desc_edit.clear()
        self.editing_mode_combo.setCurrentIndex(0)
        self.uploaded_files_list.clear()
        self._check_create_button_state()
    
    def refresh_project_list(self):
        """刷新项目列表"""
        projects = self.project_manager.get_project_list()
        # 按修改时间排序
        projects.sort(key=lambda p: p.modified_at, reverse=True)
        self.project_list.refresh_projects(projects)
    
    def set_current_project(self, project: ProjectInfo):
        """设置当前项目"""
        self.current_project = project
    
    def show_new_project_dialog(self):
        """显示新建项目对话框"""
        self._switch_to_new_project_tab()
    
    def _on_project_selected(self, project: ProjectInfo):
        """项目选中"""
        self.current_project = project
        self.edit_project_btn.setEnabled(True)
        self.delete_project_btn.setEnabled(True)
    
    def _on_project_edit_requested(self, project: ProjectInfo):
        """编辑项目请求"""
        self.edit_project_requested.emit(project)
    
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
    
    def _edit_selected_project(self):
        """编辑选中的项目"""
        if self.current_project:
            self.edit_project_requested.emit(self.current_project)
    
    def _delete_selected_project(self):
        """删除选中的项目"""
        if self.current_project:
            self._on_project_delete_requested(self.current_project.id)
