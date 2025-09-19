#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件管理器组件
提供插件的安装、配置、启用/禁用等管理功能
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QGroupBox, QFormLayout, QLineEdit, QTextEdit,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QColorDialog,
    QDialog, QDialogButtonBox, QMessageBox, QProgressBar, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QScrollArea, QFrame,
    QToolButton, QMenu, QAction, QStatusBar, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont

from app.plugins.plugin_system import (
    PluginManager, PluginMetadata, PluginType, PluginState, PluginContext
)
from app.plugins.plugin_config import PluginConfigManager, PluginConfigWidget

logger = logging.getLogger(__name__)


class PluginItemWidget(QWidget):
    """插件项目组件"""

    toggle_plugin = pyqtSignal(str, bool)  # plugin_id, enabled
    configure_plugin = pyqtSignal(str)    # plugin_id
    uninstall_plugin = pyqtSignal(str)    # plugin_id
    show_plugin_details = pyqtSignal(str)  # plugin_id

    def __init__(self, plugin_id: str, metadata: PluginMetadata, state: str, enabled: bool, parent=None):
        super().__init__(parent)
        self.plugin_id = plugin_id
        self.metadata = metadata
        self.state = state
        self.enabled = enabled
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 插件图标
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        layout.addWidget(icon_label)

        # 插件信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 插件名称和状态
        name_layout = QHBoxLayout()
        name_label = QLabel(self.metadata.name)
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_layout.addWidget(name_label)

        # 状态标签
        status_label = QLabel(self._get_status_text())
        status_label.setStyleSheet(self._get_status_style())
        status_label.setFixedSize(60, 20)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_layout.addWidget(status_label)
        name_layout.addStretch()

        info_layout.addLayout(name_layout)

        # 插件描述
        desc_label = QLabel(self.metadata.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")
        info_layout.addWidget(desc_label)

        # 插件信息
        info_text = f"版本: {self.metadata.version} | 作者: {self.metadata.author}"
        if self.metadata.category:
            info_text += f" | 分类: {self.metadata.category}"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #888; font-size: 9px;")
        info_layout.addWidget(info_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 操作按钮
        button_layout = QVBoxLayout()
        button_layout.setSpacing(4)

        # 启用/禁用按钮
        self.toggle_btn = QPushButton("禁用" if self.enabled else "启用")
        self.toggle_btn.setFixedSize(60, 25)
        self.toggle_btn.clicked.connect(self._on_toggle)
        button_layout.addWidget(self.toggle_btn)

        # 配置按钮
        if self.metadata.config_schema:
            config_btn = QPushButton("配置")
            config_btn.setFixedSize(60, 25)
            config_btn.clicked.connect(self._on_configure)
            button_layout.addWidget(config_btn)

        # 详情按钮
        details_btn = QPushButton("详情")
        details_btn.setFixedSize(60, 25)
        details_btn.clicked.connect(self._on_details)
        button_layout.addWidget(details_btn)

        layout.addLayout(button_layout)

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            PluginState.LOADED.value: "已加载",
            PluginState.INITIALIZED.value: "已初始化",
            PluginState.RUNNING.value: "运行中",
            PluginState.PAUSED.value: "已暂停",
            PluginState.ERROR.value: "错误",
            PluginState.UNLOADED.value: "未加载"
        }
        return status_map.get(self.state, "未知")

    def _get_status_style(self) -> str:
        """获取状态样式"""
        style_map = {
            PluginState.LOADED.value: "background-color: #4CAF50; color: white;",
            PluginState.INITIALIZED.value: "background-color: #2196F3; color: white;",
            PluginState.RUNNING.value: "background-color: #FF9800; color: white;",
            PluginState.PAUSED.value: "background-color: #9E9E9E; color: white;",
            PluginState.ERROR.value: "background-color: #F44336; color: white;",
            PluginState.UNLOADED.value: "background-color: #9E9E9E; color: white;"
        }
        return style_map.get(self.state, "") + "border-radius: 10px; font-size: 9px;"

    def _on_toggle(self):
        """切换插件状态"""
        self.toggle_plugin.emit(self.plugin_id, not self.enabled)

    def _on_configure(self):
        """配置插件"""
        self.configure_plugin.emit(self.plugin_id)

    def _on_details(self):
        """显示插件详情"""
        self.show_plugin_details.emit(self.plugin_id)


class PluginDetailsDialog(QDialog):
    """插件详情对话框"""

    def __init__(self, plugin_id: str, metadata: PluginMetadata, status: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.plugin_id = plugin_id
        self.metadata = metadata
        self.status = status
        self.setWindowTitle(f"插件详情 - {metadata.name}")
        self.setFixedSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 基本信息组
        basic_group = QGroupBox("基本信息", self)
        basic_layout = QFormLayout(basic_group)

        basic_layout.addRow("插件名称:", QLabel(self.metadata.name))
        basic_layout.addRow("版本:", QLabel(self.metadata.version))
        basic_layout.addRow("描述:", QLabel(self.metadata.description))
        basic_layout.addRow("作者:", QLabel(self.metadata.author))
        if self.metadata.email:
            basic_layout.addRow("邮箱:", QLabel(self.metadata.email))
        if self.metadata.website:
            basic_layout.addRow("网站:", QLabel(self.metadata.website))

        # 插件类型
        type_text = self.metadata.plugin_type.value if self.metadata.plugin_type else "未知"
        basic_layout.addRow("类型:", QLabel(type_text))

        if self.metadata.category:
            basic_layout.addRow("分类:", QLabel(self.metadata.category))

        # 标签
        if self.metadata.tags:
            tags_text = ", ".join(self.metadata.tags)
            basic_layout.addRow("标签:", QLabel(tags_text))

        layout.addWidget(basic_group)

        # 状态信息组
        status_group = QGroupBox("状态信息", self)
        status_layout = QFormLayout(status_group)

        status_layout.addRow("状态:", QLabel(self.status.get("state", "未知")))
        status_layout.addRow("启用:", QLabel("是" if self.status.get("enabled", False) else "否"))
        status_layout.addRow("版本兼容性:", QLabel("兼容" if self.metadata.enabled else "检查中"))

        layout.addWidget(status_group)

        # 依赖信息组
        if self.metadata.dependencies:
            deps_group = QGroupBox("依赖信息", self)
            deps_layout = QVBoxLayout(deps_group)

            for dep in self.metadata.dependencies:
                deps_layout.addWidget(QLabel(f"• {dep}"))

            layout.addWidget(deps_group)

        # 配置信息组
        if self.metadata.config_schema:
            config_group = QGroupBox("配置信息", self)
            config_layout = QVBoxLayout(config_group)

            config_text = f"该插件支持 {len(self.metadata.config_schema.get('sections', []))} 个配置组"
            config_layout.addWidget(QLabel(config_text))

            layout.addWidget(config_group)

        # 能力信息组
        capabilities = self.status.get("capabilities", {})
        if capabilities:
            caps_group = QGroupBox("插件能力", self)
            caps_layout = QVBoxLayout(caps_group)

            for cap_name, cap_value in capabilities.items():
                caps_layout.addWidget(QLabel(f"• {cap_name}: {cap_value}"))

            layout.addWidget(caps_group)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)


class PluginInstallDialog(QDialog):
    """插件安装对话框"""

    plugin_installed = pyqtSignal(str)  # plugin_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安装插件")
        self.setFixedSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 安装方式选择
        method_group = QGroupBox("安装方式", self)
        method_layout = QVBoxLayout(method_group)

        # 文件安装
        file_btn = QPushButton("从文件安装 (.py, .zip)")
        file_btn.clicked.connect(self._install_from_file)
        method_layout.addWidget(file_btn)

        # 目录安装
        dir_btn = QPushButton("从目录安装")
        dir_btn.clicked.connect(self._install_from_directory)
        method_layout.addWidget(dir_btn)

        layout.addWidget(method_group)

        # 插件信息显示
        self.info_group = QGroupBox("插件信息", self)
        info_layout = QVBoxLayout(self.info_group)
        self.info_label = QLabel("请选择插件文件或目录")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        layout.addWidget(self.info_group)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _install_from_file(self):
        """从文件安装"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择插件文件", "",
            "插件文件 (*.py *.zip);;Python文件 (*.py);;ZIP文件 (*.zip);;所有文件 (*)"
        )

        if file_path:
            self._install_plugin(file_path)

    def _install_from_directory(self):
        """从目录安装"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择插件目录")
        if dir_path:
            self._install_plugin(dir_path)

    def _install_plugin(self, plugin_path: str):
        """安装插件"""
        try:
            # 分析插件路径
            path = Path(plugin_path)
            plugin_name = path.name

            # 显示插件信息
            info_text = f"插件名称: {plugin_name}\n"
            info_text += f"路径: {plugin_path}\n"
            info_text += f"类型: {'文件' if path.is_file() else '目录'}\n\n"
            info_text += "准备安装插件..."

            self.info_label.setText(info_text)

            # 发送安装信号
            QTimer.singleShot(1000, lambda: self.plugin_installed.emit(plugin_path))
            QTimer.singleShot(1500, self.accept)

        except Exception as e:
            self.info_label.setText(f"分析插件失败: {str(e)}")


class PluginManagerWidget(QWidget):
    """插件管理器主组件"""

    def __init__(self, plugin_manager: PluginManager, config_manager: PluginConfigManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.config_manager = config_manager
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_plugins)
        toolbar_layout.addWidget(refresh_btn)

        # 安装插件按钮
        install_btn = QPushButton("安装插件")
        install_btn.clicked.connect(self.install_plugin)
        toolbar_layout.addWidget(install_btn)

        # 搜索框
        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索插件...")
        self.search_box.textChanged.connect(self.filter_plugins)
        toolbar_layout.addWidget(self.search_box)

        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        # 插件分类标签
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 创建分类标签
        self.plugin_lists = {}
        categories = [
            ("all", "全部插件"),
            ("ai_provider", "AI服务"),
            ("effect", "特效效果"),
            ("export_format", "导出格式"),
            ("import_format", "导入格式"),
            ("filter", "滤镜效果"),
            ("animation", "动画效果"),
            ("theme", "主题样式"),
            ("tool", "工具插件"),
            ("utility", "实用工具")
        ]

        for category_key, category_name in categories:
            list_widget = QListWidget()
            list_widget.setAlternatingRowColors(True)
            self.tab_widget.addTab(list_widget, category_name)
            self.plugin_lists[category_key] = list_widget

        layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        # 刷新插件列表
        self.refresh_plugins()

    def connect_signals(self):
        """连接信号"""
        # 连接插件管理器信号
        self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.connect(self.on_plugin_unloaded)
        self.plugin_manager.plugin_error.connect(self.on_plugin_error)
        self.plugin_manager.plugin_state_changed.connect(self.on_plugin_state_changed)

    def refresh_plugins(self):
        """刷新插件列表"""
        self.status_bar.showMessage("正在刷新插件列表...")

        # 获取所有插件信息
        all_plugins = self.plugin_manager.get_all_plugins()

        # 清空所有列表
        for list_widget in self.plugin_lists.values():
            list_widget.clear()

        # 按类型分类插件
        categorized_plugins = {}
        for category_key in self.plugin_lists.keys():
            categorized_plugins[category_key] = []

        for plugin_id, plugin_info in all_plugins.items():
            metadata = plugin_info["metadata"]
            plugin_type = metadata.get("plugin_type")
            if plugin_type:
                type_key = plugin_type.value
            else:
                type_key = "utility"

            # 添加到对应分类
            if type_key in categorized_plugins:
                categorized_plugins[type_key].append((plugin_id, plugin_info))
            categorized_plugins["all"].append((plugin_id, plugin_info))

        # 填充列表
        for category_key, plugin_list in categorized_plugins.items():
            if category_key in self.plugin_lists:
                list_widget = self.plugin_lists[category_key]
                for plugin_id, plugin_info in plugin_list:
                    self.add_plugin_to_list(list_widget, plugin_id, plugin_info)

        plugin_count = len(all_plugins)
        enabled_count = sum(1 for p in all_plugins.values() if p["enabled"])
        self.status_bar.showMessage(f"共 {plugin_count} 个插件，已启用 {enabled_count} 个")

    def add_plugin_to_list(self, list_widget: QListWidget, plugin_id: str, plugin_info: Dict[str, Any]):
        """添加插件到列表"""
        metadata_dict = plugin_info["metadata"]
        metadata = PluginMetadata(**metadata_dict)
        state = plugin_info["state"]
        enabled = plugin_info["enabled"]

        # 创建插件项目组件
        item_widget = PluginItemWidget(plugin_id, metadata, state, enabled)

        # 连接信号
        item_widget.toggle_plugin.connect(self.toggle_plugin)
        item_widget.configure_plugin.connect(self.configure_plugin)
        item_widget.uninstall_plugin.connect(self.uninstall_plugin)
        item_widget.show_plugin_details.connect(self.show_plugin_details)

        # 创建列表项
        list_item = QListWidgetItem(list_widget)
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.ItemDataRole.UserRole, plugin_id)

        # 添加到列表
        list_widget.addItem(list_item)
        list_widget.setItemWidget(list_item, item_widget)

    def filter_plugins(self):
        """过滤插件"""
        search_text = self.search_box.text().lower()

        current_tab = self.tab_widget.currentWidget()
        if not current_tab:
            return

        for i in range(current_tab.count()):
            item = current_tab.item(i)
            widget = current_tab.itemWidget(item)

            if widget:
                # 搜索插件名称和描述
                name_match = search_text in widget.metadata.name.lower()
                desc_match = search_text in widget.metadata.description.lower()
                author_match = search_text in widget.metadata.author.lower()

                item.setHidden(not (name_match or desc_match or author_match))

    def install_plugin(self):
        """安装插件"""
        dialog = PluginInstallDialog(self)
        dialog.plugin_installed.connect(self.on_plugin_installed)
        dialog.exec()

    def toggle_plugin(self, plugin_id: str, enabled: bool):
        """切换插件状态"""
        if enabled:
            self.plugin_manager.enable_plugin(plugin_id)
        else:
            self.plugin_manager.disable_plugin(plugin_id)

        self.refresh_plugins()

    def configure_plugin(self, plugin_id: str):
        """配置插件"""
        # 创建配置界面
        config_widget = self.config_manager.create_config_widget(plugin_id)
        if not config_widget:
            QMessageBox.information(self, "配置", "该插件不支持配置")
            return

        # 创建配置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"配置插件 - {plugin_id}")
        dialog.setFixedSize(600, 500)

        layout = QVBoxLayout(dialog)
        layout.addWidget(config_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def uninstall_plugin(self, plugin_id: str):
        """卸载插件"""
        reply = QMessageBox.question(
            self, "卸载插件",
            f"确定要卸载插件 '{plugin_id}' 吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.plugin_manager.unload_plugin(plugin_id)
            if success:
                # 删除配置
                self.config_manager.delete_config(plugin_id)
                self.refresh_plugins()
                self.status_bar.showMessage(f"插件 '{plugin_id}' 已卸载")
            else:
                QMessageBox.warning(self, "卸载失败", f"无法卸载插件 '{plugin_id}'")

    def show_plugin_details(self, plugin_id: str):
        """显示插件详情"""
        all_plugins = self.plugin_manager.get_all_plugins()
        if plugin_id not in all_plugins:
            return

        plugin_info = all_plugins[plugin_id]
        metadata_dict = plugin_info["metadata"]
        metadata = PluginMetadata(**metadata_dict)
        status = plugin_info.get("status", {})

        dialog = PluginDetailsDialog(plugin_id, metadata, status, self)
        dialog.exec()

    def on_tab_changed(self, index: int):
        """标签页切换"""
        self.filter_plugins()

    def on_plugin_loaded(self, plugin_id: str):
        """插件加载完成"""
        self.status_bar.showMessage(f"插件 '{plugin_id}' 加载成功", 3000)
        self.refresh_plugins()

    def on_plugin_unloaded(self, plugin_id: str):
        """插件卸载完成"""
        self.status_bar.showMessage(f"插件 '{plugin_id}' 卸载成功", 3000)
        self.refresh_plugins()

    def on_plugin_error(self, plugin_id: str, error_message: str):
        """插件错误"""
        self.status_bar.showMessage(f"插件 '{plugin_id}' 错误: {error_message}", 5000)
        QMessageBox.critical(self, "插件错误", f"插件 '{plugin_id}' 发生错误:\n{error_message}")

    def on_plugin_state_changed(self, plugin_id: str, state: str):
        """插件状态变化"""
        self.refresh_plugins()

    def on_plugin_installed(self, plugin_path: str):
        """插件安装完成"""
        try:
            success = self.plugin_manager.load_plugin(plugin_path)
            if success:
                self.status_bar.showMessage("插件安装成功", 3000)
                self.refresh_plugins()
            else:
                QMessageBox.warning(self, "安装失败", "插件加载失败，请检查插件格式")
        except Exception as e:
            QMessageBox.critical(self, "安装失败", f"安装插件时发生错误:\n{str(e)}")


class PluginManagerWindow(QWidget):
    """插件管理器窗口"""

    def __init__(self, plugin_manager: PluginManager, config_manager: PluginConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插件管理器")
        self.setFixedSize(900, 700)
        self.setup_ui(plugin_manager, config_manager)

    def setup_ui(self, plugin_manager: PluginManager, config_manager: PluginConfigManager):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("插件管理器")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # 插件管理器组件
        self.plugin_manager_widget = PluginManagerWidget(plugin_manager, config_manager, self)
        layout.addWidget(self.plugin_manager_widget)

        # 底部信息
        info_label = QLabel("支持动态加载插件，扩展应用功能")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)