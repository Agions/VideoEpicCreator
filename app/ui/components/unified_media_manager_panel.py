#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一媒体管理面板
提供媒体文件导入、组织、搜索和管理功能
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QProgressBar, QMessageBox, QMenu,
    QInputDialog, QDialog, QFormLayout, QDialogButtonBox,
    QFrame, QScrollArea, QStackedWidget, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt6.QtGui import QIcon, QPixmap, QImage, QAction

from ..core.unified_media_manager import (
    UnifiedMediaManager, MediaFile, MediaFolder, MediaCollection,
    MediaMetadata, MediaType, MediaStatus, MediaImportOptions
)
from ..utils.ui_helpers import show_info_message, show_error_message, show_warning_message
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class MediaImportWorker(QThread):
    """媒体导入工作线程"""

    progress_updated = pyqtSignal(int, str)  # progress, message
    import_completed = pyqtSignal(list)  # List[MediaFile]
    import_failed = pyqtSignal(str)

    def __init__(self, media_manager: UnifiedMediaManager, file_paths: List[str], options: MediaImportOptions):
        super().__init__()
        self.media_manager = media_manager
        self.file_paths = file_paths
        self.options = options

    def run(self):
        try:
            imported_files = []
            total_files = len(self.file_paths)

            for i, file_path in enumerate(self.file_paths):
                if self.isInterruptionRequested():
                    break

                self.progress_updated.emit(
                    int((i / total_files) * 100),
                    f"正在导入: {os.path.basename(file_path)}"
                )

                media_file = self.media_manager.import_media_file(file_path, self.options)
                if media_file:
                    imported_files.append(media_file)

            self.import_completed.emit(imported_files)

        except Exception as e:
            logger.error(f"媒体导入失败: {e}")
            self.import_failed.emit(str(e))


class MediaListWidget(QListWidget):
    """媒体文件列表组件"""

    media_selected = pyqtSignal(MediaFile)
    media_double_clicked = pyqtSignal(MediaFile)

    def __init__(self, media_manager: UnifiedMediaManager, parent=None):
        super().__init__(parent)
        self.media_manager = media_manager
        self.media_files: List[MediaFile] = []
        self.current_media: Optional[MediaFile] = None

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(120, 80))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(10)

        # 启用拖拽
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        # 连接信号
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def load_media_files(self, media_files: List[MediaFile]):
        """加载媒体文件列表"""
        self.clear()
        self.media_files = media_files

        for media_file in media_files:
            item = self._create_media_item(media_file)
            self.addItem(item)

    def _create_media_item(self, media_file: MediaFile) -> QListWidgetItem:
        """创建媒体文件项"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, media_file)

        # 设置图标（使用缩略图或默认图标）
        thumbnail_path = media_file.thumbnail_path
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            icon = QIcon(pixmap.scaled(QSize(120, 80), Qt.AspectRatioMode.KeepAspectRatio))
        else:
            icon = self._get_default_icon(media_file.media_type)

        item.setIcon(icon)

        # 设置文本
        item.setText(media_file.display_name)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 设置工具提示
        tooltip = f"""
        <b>{media_file.display_name}</b><br>
        类型: {media_file.media_type.value}<br>
        大小: {self._format_file_size(media_file.file_size)}<br>
        时长: {self._format_duration(media_file.duration)}<br>
        分辨率: {media_file.resolution}<br>
        导入时间: {media_file.import_time.strftime('%Y-%m-%d %H:%M:%S')}
        """
        item.setToolTip(tooltip)

        return item

    def _get_default_icon(self, media_type: MediaType) -> QIcon:
        """获取默认图标"""
        # 这里可以根据媒体类型返回不同的默认图标
        # 暂时使用空白图标
        return QIcon()

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _format_duration(self, duration_seconds: float) -> str:
        """格式化时长"""
        if duration_seconds <= 0:
            return "未知"

        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _on_item_clicked(self, item: QListWidgetItem):
        """点击项事件"""
        media_file = item.data(Qt.ItemDataRole.UserRole)
        self.current_media = media_file
        self.media_selected.emit(media_file)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击项事件"""
        media_file = item.data(Qt.ItemDataRole.UserRole)
        self.media_double_clicked.emit(media_file)


class MediaFolderTreeWidget(QTreeWidget):
    """媒体文件夹树组件"""

    folder_selected = pyqtSignal(MediaFolder)
    folder_double_clicked = pyqtSignal(MediaFolder)

    def __init__(self, media_manager: UnifiedMediaManager, parent=None):
        super().__init__(parent)
        self.media_manager = media_manager
        self.current_folder: Optional[MediaFolder] = None

        self.setup_ui()
        self.load_folders()

    def setup_ui(self):
        """设置UI"""
        self.setHeaderLabels(["文件夹", "媒体数量"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 100)

        # 启用右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 连接信号
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def load_folders(self):
        """加载文件夹列表"""
        self.clear()

        # 添加根文件夹
        root_folders = self.media_manager.get_root_folders()
        for folder in root_folders:
            item = self._create_folder_item(folder)
            self.addTopLevelItem(item)

    def _create_folder_item(self, folder: MediaFolder) -> QTreeWidgetItem:
        """创建文件夹项"""
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, folder)

        # 设置文本
        item.setText(0, folder.name)
        item.setText(1, str(len(folder.media_files)))

        # 设置图标
        item.setIcon(0, self._get_folder_icon(folder))

        # 添加子文件夹
        for child_folder in folder.subfolders:
            child_item = self._create_folder_item(child_folder)
            item.addChild(child_item)

        return item

    def _get_folder_icon(self, folder: MediaFolder) -> QIcon:
        """获取文件夹图标"""
        # 根据文件夹类型返回不同的图标
        # 暂时使用默认图标
        return QIcon()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击项事件"""
        folder = item.data(0, Qt.ItemDataRole.UserRole)
        self.current_folder = folder
        self.folder_selected.emit(folder)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击项事件"""
        folder = item.data(0, Qt.ItemDataRole.UserRole)
        self.folder_double_clicked.emit(folder)

    def _show_context_menu(self, position):
        """显示右键菜单"""
        item = self.itemAt(position)
        if not item:
            return

        folder = item.data(0, Qt.ItemDataRole.UserRole)

        menu = QMenu()
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        menu.addSeparator()
        create_folder_action = menu.addAction("新建文件夹")

        action = menu.exec(self.mapToGlobal(position))

        if action == rename_action:
            self._rename_folder(folder)
        elif action == delete_action:
            self._delete_folder(folder)
        elif action == create_folder_action:
            self._create_folder(folder)

    def _rename_folder(self, folder: MediaFolder):
        """重命名文件夹"""
        new_name, ok = QInputDialog.getText(
            self, "重命名文件夹", "请输入新名称:",
            text=folder.name
        )

        if ok and new_name and new_name != folder.name:
            try:
                self.media_manager.rename_folder(folder.id, new_name)
                self.load_folders()
            except Exception as e:
                show_error_message(self, f"重命名失败: {e}")

    def _delete_folder(self, folder: MediaFolder):
        """删除文件夹"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件夹 '{folder.name}' 吗？\n此操作将删除文件夹及其所有内容。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.media_manager.delete_folder(folder.id)
                self.load_folders()
            except Exception as e:
                show_error_message(self, f"删除失败: {e}")

    def _create_folder(self, parent_folder: MediaFolder):
        """创建子文件夹"""
        name, ok = QInputDialog.getText(
            self, "新建文件夹", "请输入文件夹名称:"
        )

        if ok and name:
            try:
                self.media_manager.create_folder(name, parent_folder.id)
                self.load_folders()
            except Exception as e:
                show_error_message(self, f"创建文件夹失败: {e}")


class UnifiedMediaManagerPanel(BaseComponent):
    """统一媒体管理面板"""

    # 信号定义
    media_imported = pyqtSignal(list)  # List[MediaFile]
    media_selected = pyqtSignal(MediaFile)
    folder_selected = pyqtSignal(MediaFolder)
    collection_selected = pyqtSignal(MediaCollection)

    def __init__(self, media_manager: UnifiedMediaManager, parent=None):
        super().__init__(parent)
        self.media_manager = media_manager

        self.current_folder: Optional[MediaFolder] = None
        self.current_collection: Optional[MediaCollection] = None
        self.current_media: Optional[MediaFile] = None

        self.setup_ui()
        self.load_initial_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        # 导入按钮
        self.import_btn = QPushButton("导入媒体")
        self.import_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton))
        self.import_btn.clicked.connect(self._import_media)

        # 新建文件夹按钮
        self.new_folder_btn = QPushButton("新建文件夹")
        self.new_folder_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
        self.new_folder_btn.clicked.connect(self._create_root_folder)

        # 新建收藏夹按钮
        self.new_collection_btn = QPushButton("新建收藏夹")
        self.new_collection_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
        self.new_collection_btn.clicked.connect(self._create_collection)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.refresh_all)

        toolbar_layout.addWidget(self.import_btn)
        toolbar_layout.addWidget(self.new_folder_btn)
        toolbar_layout.addWidget(self.new_collection_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_btn)

        layout.addLayout(toolbar_layout)

        # 主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧面板（文件夹和收藏夹）
        left_panel = QStackedWidget()

        # 文件夹树
        self.folder_tree = MediaFolderTreeWidget(self.media_manager)
        self.folder_tree.folder_selected.connect(self._on_folder_selected)

        # 收藏夹列表
        self.collection_list = QListWidget()
        self.collection_list.itemClicked.connect(self._on_collection_clicked)
        self.load_collections()

        # 标签页选择器
        tab_layout = QHBoxLayout()
        self.folder_tab_btn = QPushButton("文件夹")
        self.folder_tab_btn.setCheckable(True)
        self.folder_tab_btn.setChecked(True)
        self.folder_tab_btn.clicked.connect(lambda: left_panel.setCurrentIndex(0))

        self.collection_tab_btn = QPushButton("收藏夹")
        self.collection_tab_btn.setCheckable(True)
        self.collection_tab_btn.clicked.connect(lambda: left_panel.setCurrentIndex(1))

        tab_layout.addWidget(self.folder_tab_btn)
        tab_layout.addWidget(self.collection_tab_btn)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addLayout(tab_layout)
        left_panel.addWidget(self.folder_tree)
        left_panel.addWidget(self.collection_list)
        left_layout.addWidget(left_panel)

        # 右侧面板（媒体列表）
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 搜索和过滤
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索媒体文件...")
        self.search_input.textChanged.connect(self._on_search_changed)

        self.media_type_filter = QComboBox()
        self.media_type_filter.addItems(["全部", "视频", "音频", "图像"])
        self.media_type_filter.currentTextChanged.connect(self._on_filter_changed)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.media_type_filter)

        right_layout.addLayout(search_layout)

        # 媒体列表
        self.media_list = MediaListWidget(self.media_manager)
        self.media_list.media_selected.connect(self._on_media_selected)
        self.media_list.media_double_clicked.connect(self._on_media_double_clicked)

        right_layout.addWidget(self.media_list)

        # 状态栏
        self.status_bar = QStatusBar()
        right_layout.addWidget(self.status_bar)

        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([200, 600])

        layout.addWidget(main_splitter)

        # 导入进度条
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        layout.addWidget(self.import_progress)

    def load_initial_data(self):
        """加载初始数据"""
        try:
            # 加载根文件夹的媒体文件
            root_folders = self.media_manager.get_root_folders()
            if root_folders:
                self._on_folder_selected(root_folders[0])
            else:
                # 如果没有文件夹，加载所有媒体文件
                all_media = self.media_manager.get_all_media_files()
                self.media_list.load_media_files(all_media)
                self._update_status(f"共 {len(all_media)} 个媒体文件")

        except Exception as e:
            logger.error(f"加载初始数据失败: {e}")
            show_error_message(self, f"加载数据失败: {e}")

    def load_collections(self):
        """加载收藏夹列表"""
        self.collection_list.clear()

        collections = self.media_manager.get_all_collections()
        for collection in collections:
            item = QListWidgetItem(collection.name)
            item.setData(Qt.ItemDataRole.UserRole, collection)
            self.collection_list.addItem(item)

    def _import_media(self):
        """导入媒体文件"""
        # 这里需要实现文件对话框来选择媒体文件
        # 暂时显示一个提示消息
        show_info_message(self, "导入媒体文件功能待实现")

    def _create_root_folder(self):
        """创建根文件夹"""
        name, ok = QInputDialog.getText(
            self, "新建文件夹", "请输入文件夹名称:"
        )

        if ok and name:
            try:
                self.media_manager.create_folder(name)
                self.folder_tree.load_folders()
            except Exception as e:
                show_error_message(self, f"创建文件夹失败: {e}")

    def _create_collection(self):
        """创建收藏夹"""
        name, ok = QInputDialog.getText(
            self, "新建收藏夹", "请输入收藏夹名称:"
        )

        if ok and name:
            try:
                self.media_manager.create_collection(name)
                self.load_collections()
            except Exception as e:
                show_error_message(self, f"创建收藏夹失败: {e}")

    def _on_folder_selected(self, folder: MediaFolder):
        """文件夹选择事件"""
        self.current_folder = folder
        self.current_collection = None

        # 加载文件夹中的媒体文件
        media_files = self.media_manager.get_folder_media_files(folder.id)
        self.media_list.load_media_files(media_files)
        self._update_status(f"文件夹 '{folder.name}' - 共 {len(media_files)} 个媒体文件")

        self.folder_selected.emit(folder)

    def _on_collection_clicked(self, item: QListWidgetItem):
        """收藏夹点击事件"""
        collection = item.data(Qt.ItemDataRole.UserRole)
        self.current_collection = collection
        self.current_folder = None

        # 加载收藏夹中的媒体文件
        media_files = self.media_manager.get_collection_media_files(collection.id)
        self.media_list.load_media_files(media_files)
        self._update_status(f"收藏夹 '{collection.name}' - 共 {len(media_files)} 个媒体文件")

        self.collection_selected.emit(collection)

    def _on_media_selected(self, media_file: MediaFile):
        """媒体文件选择事件"""
        self.current_media = media_file
        self._update_status(f"已选择: {media_file.display_name}")
        self.media_selected.emit(media_file)

    def _on_media_double_clicked(self, media_file: MediaFile):
        """媒体文件双击事件"""
        # 这里可以添加预览或编辑功能
        show_info_message(self, f"打开媒体文件: {media_file.display_name}")

    def _on_search_changed(self, text: str):
        """搜索文本改变事件"""
        self._apply_filters()

    def _on_filter_changed(self, text: str):
        """过滤器改变事件"""
        self._apply_filters()

    def _apply_filters(self):
        """应用搜索和过滤"""
        search_text = self.search_input.text().strip()
        filter_type = self.media_type_filter.currentText()

        try:
            if search_text:
                # 执行搜索
                results = self.media_manager.search_media_files(search_text)

                # 应用类型过滤
                if filter_type != "全部":
                    media_type_map = {
                        "视频": MediaType.VIDEO,
                        "音频": MediaType.AUDIO,
                        "图像": MediaType.IMAGE
                    }
                    target_type = media_type_map.get(filter_type)
                    if target_type:
                        results = [m for m in results if m.media_type == target_type]

                self.media_list.load_media_files(results)
                self._update_status(f"搜索结果: {len(results)} 个媒体文件")
            else:
                # 重新加载当前文件夹或收藏夹
                if self.current_folder:
                    self._on_folder_selected(self.current_folder)
                elif self.current_collection:
                    self._on_collection_clicked(self.collection_list.currentItem())
                else:
                    all_media = self.media_manager.get_all_media_files()
                    self.media_list.load_media_files(all_media)
                    self._update_status(f"共 {len(all_media)} 个媒体文件")

        except Exception as e:
            logger.error(f"应用过滤失败: {e}")

    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.showMessage(message)

    def refresh_all(self):
        """刷新所有数据"""
        try:
            self.folder_tree.load_folders()
            self.load_collections()
            self.load_initial_data()
            show_info_message(self, "刷新完成")
        except Exception as e:
            show_error_message(self, f"刷新失败: {e}")

    def get_selected_media(self) -> Optional[MediaFile]:
        """获取当前选中的媒体文件"""
        return self.current_media

    def get_selected_folder(self) -> Optional[MediaFolder]:
        """获取当前选中的文件夹"""
        return self.current_folder

    def get_selected_collection(self) -> Optional[MediaCollection]:
        """获取当前选中的收藏夹"""
        return self.current_collection