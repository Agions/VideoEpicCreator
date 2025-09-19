#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件市场UI界面
提供插件浏览、搜索、安装、更新等功能
"""

import asyncio
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
    QToolButton, QMenu, QAction, QStatusBar, QLineEdit, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle, QApplication, QSpacerItem, QSizePolicy,
    QRadioButton, QButtonGroup, QGroupBox, QTextBrowser, QRatingWidget,
    QGraphicsDropShadowEffect, QGraphicsEffect, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, QUrl, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QBrush, QPen, QCursor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from app.plugins.marketplace import (
    PluginMarketplace, PluginPackage, PluginSource, PluginSourceType,
    PluginReleaseChannel, MarketplaceConfig
)
from app.plugins.plugin_system import PluginType, PluginManager

logger = logging.getLogger(__name__)


class PluginPackageWidget(QWidget):
    """插件包显示组件"""

    install_requested = pyqtSignal(PluginPackage)
    details_requested = pyqtSignal(PluginPackage)

    def __init__(self, package: PluginPackage, parent=None):
        super().__init__(parent)
        self.package = package
        self.setFixedSize(300, 120)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 设置圆角边框
        self.setStyleSheet("""
            PluginPackageWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 2px;
            }
            PluginPackageWidget:hover {
                border: 2px solid #2196F3;
                margin: 1px;
            }
        """)

        # 标题行
        title_layout = QHBoxLayout()

        # 插件名称
        name_label = QLabel(self.package.name)
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #333;")
        title_layout.addWidget(name_label)

        # 版本标签
        version_label = QLabel(f"v{self.package.version}")
        version_label.setStyleSheet("color: #666; font-size: 9px;")
        title_layout.addWidget(version_label)

        # 发布渠道标签
        channel_color = {
            PluginReleaseChannel.STABLE: "#4CAF50",
            PluginReleaseChannel.BETA: "#FF9800",
            PluginReleaseChannel.ALPHA: "#F44336",
            PluginReleaseChannel.NIGHTLY: "#9C27B0"
        }
        channel_text = self.package.release_channel.value.upper()
        channel_label = QLabel(channel_text)
        channel_label.setStyleSheet(f"background-color: {channel_color.get(self.package.release_channel, '#666')}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 8px;")
        title_layout.addWidget(channel_label)

        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 描述
        desc_label = QLabel(self.package.description[:60] + "..." if len(self.package.description) > 60 else self.package.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(desc_label)

        # 信息行
        info_layout = QHBoxLayout()

        # 作者
        author_label = QLabel(f"作者: {self.package.author}")
        author_label.setStyleSheet("color: #888; font-size: 8px;")
        info_layout.addWidget(author_label)

        # 下载量
        downloads_text = self._format_number(self.package.download_count)
        downloads_label = QLabel(f"下载: {downloads_text}")
        downloads_label.setStyleSheet("color: #888; font-size: 8px;")
        info_layout.addWidget(downloads_label)

        # 评分
        if self.package.rating_count > 0:
            rating_text = f"★{self.package.rating:.1f}"
        else:
            rating_text = "新插件"
        rating_label = QLabel(rating_text)
        rating_label.setStyleSheet("color: #888; font-size: 8px;")
        info_layout.addWidget(rating_label)

        layout.addLayout(info_layout)

        # 标签
        if self.package.tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            for tag in self.package.tags[:3]:  # 最多显示3个标签
                tag_label = QLabel(tag)
                tag_label.setStyleSheet("background-color: #f0f0f0; color: #666; padding: 1px 4px; border-radius: 3px; font-size: 7px;")
                tags_layout.addWidget(tag_label)
            layout.addLayout(tags_layout)

        layout.addStretch()

        # 按钮行
        button_layout = QHBoxLayout()

        # 详情按钮
        details_btn = QPushButton("详情")
        details_btn.setFixedSize(50, 25)
        details_btn.clicked.connect(lambda: self.details_requested.emit(self.package))
        button_layout.addWidget(details_btn)

        # 安装按钮
        install_btn = QPushButton("安装")
        install_btn.setFixedSize(50, 25)
        install_btn.clicked.connect(lambda: self.install_requested.emit(self.package))
        button_layout.addWidget(install_btn)

        layout.addLayout(button_layout)

    def _format_number(self, num: int) -> str:
        """格式化数字"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().leaveEvent(event)


class PluginDetailsDialog(QDialog):
    """插件详情对话框"""

    install_requested = pyqtSignal(PluginPackage)

    def __init__(self, package: PluginPackage, parent=None):
        super().__init__(parent)
        self.package = package
        self.setWindowTitle(f"插件详情 - {package.name}")
        self.setFixedSize(700, 600)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 标题区域
        title_group = QGroupBox()
        title_layout = QHBoxLayout(title_group)

        # 插件图标（占位）
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")
        title_layout.addWidget(icon_label)

        # 插件信息
        info_layout = QVBoxLayout()

        # 名称和版本
        name_layout = QHBoxLayout()
        name_label = QLabel(self.package.name)
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        name_layout.addWidget(name_label)

        version_label = QLabel(f"v{self.package.version}")
        version_label.setStyleSheet("color: #666; font-size: 12px;")
        name_layout.addWidget(version_label)

        # 发布渠道
        channel_color = {
            PluginReleaseChannel.STABLE: "#4CAF50",
            PluginReleaseChannel.BETA: "#FF9800",
            PluginReleaseChannel.ALPHA: "#F44336",
            PluginReleaseChannel.NIGHTLY: "#9C27B0"
        }
        channel_text = self.package.release_channel.value.upper()
        channel_label = QLabel(channel_text)
        channel_label.setStyleSheet(f"background-color: {channel_color.get(self.package.release_channel, '#666')}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;")
        name_layout.addWidget(channel_label)

        name_layout.addStretch()
        info_layout.addLayout(name_layout)

        # 作者和来源
        author_label = QLabel(f"作者: {self.package.author}")
        author_label.setStyleSheet("color: #666;")
        info_layout.addWidget(author_label)

        source_label = QLabel(f"来源: {self.package.source}")
        source_label.setStyleSheet("color: #666;")
        info_layout.addWidget(source_label)

        # 发布日期
        publish_label = QLabel(f"发布时间: {self.package.publish_date}")
        publish_label.setStyleSheet("color: #666;")
        info_layout.addWidget(publish_label)

        title_layout.addLayout(info_layout)
        title_layout.addStretch()

        layout.addWidget(title_group)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout(stats_group)

        # 下载量
        downloads_widget = self._create_stat_widget("下载量", self._format_number(self.package.download_count))
        stats_layout.addWidget(downloads_widget)

        # 评分
        rating_text = f"{self.package.rating:.1f}" if self.package.rating_count > 0 else "新插件"
        rating_widget = self._create_stat_widget("评分", rating_text)
        stats_layout.addWidget(rating_widget)

        # 评分次数
        votes_text = str(self.package.rating_count) if self.package.rating_count > 0 else "暂无"
        votes_widget = self._create_stat_widget("评价", votes_text)
        stats_layout.addWidget(votes_widget)

        # 文件大小
        size_text = self._format_file_size(self.package.file_size)
        size_widget = self._create_stat_widget("文件大小", size_text)
        stats_layout.addWidget(size_widget)

        layout.addWidget(stats_group)

        # 选项卡
        tab_widget = QTabWidget()

        # 描述标签页
        desc_widget = QTextBrowser()
        desc_widget.setHtml(self._format_description())
        tab_widget.addTab(desc_widget, "描述")

        # 更新日志标签页
        if self.package.changelog:
            changelog_widget = QTextBrowser()
            changelog_widget.setPlainText(self.package.changelog)
            tab_widget.addTab(changelog_widget, "更新日志")

        # 依赖标签页
        if self.package.dependencies:
            deps_widget = QTextBrowser()
            deps_text = "<ul>"
            for dep in self.package.dependencies:
                deps_text += f"<li>{dep}</li>"
            deps_text += "</ul>"
            deps_widget.setHtml(deps_text)
            tab_widget.addTab(deps_widget, "依赖")
        else:
            deps_widget = QTextBrowser()
            deps_widget.setHtml("<p>无依赖</p>")
            tab_widget.addTab(deps_widget, "依赖")

        # 兼容性标签页
        compat_widget = QTextBrowser()
        compat_text = "<ul>"
        for key, value in self.package.compatibility.items():
            compat_text += f"<li><b>{key}</b>: {value}</li>"
        if not self.package.compatibility:
            compat_text += "<li>暂无兼容性信息</li>"
        compat_text += "</ul>"
        compat_widget.setHtml(compat_text)
        tab_widget.addTab(compat_widget, "兼容性")

        layout.addWidget(tab_widget)

        # 标签
        if self.package.tags:
            tags_group = QGroupBox("标签")
            tags_layout = QHBoxLayout(tags_group)
            for tag in self.package.tags:
                tag_label = QLabel(tag)
                tag_label.setStyleSheet("background-color: #e0e0e0; color: #333; padding: 4px 8px; border-radius: 12px; margin: 2px;")
                tags_layout.addWidget(tag_label)
            layout.addWidget(tags_group)

        # 按钮
        button_layout = QHBoxLayout()

        # 取消按钮
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        # 安装按钮
        install_btn = QPushButton("安装插件")
        install_btn.setFixedSize(100, 30)
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        install_btn.clicked.connect(lambda: self.install_requested.emit(self.package))
        button_layout.addWidget(install_btn)

        layout.addLayout(button_layout)

    def _create_stat_widget(self, label: str, value: str) -> QWidget:
        """创建统计信息组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(value_label)

        label_label = QLabel(label)
        label_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(label_label)

        return widget

    def _format_description(self) -> str:
        """格式化描述"""
        desc = self.package.description.replace('\n', '<br>')
        return f"<p style='line-height: 1.6;'>{desc}</p>"

    def _format_number(self, num: int) -> str:
        """格式化数字"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)

    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        if size >= 1024 * 1024:
            return f"{size/(1024*1024):.1f}MB"
        elif size >= 1024:
            return f"{size/1024:.1f}KB"
        else:
            return f"{size}B"


class PluginMarketplaceUI(QWidget):
    """插件市场主界面"""

    def __init__(self, marketplace: PluginMarketplace, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.marketplace = marketplace
        self.plugin_manager = plugin_manager
        self.current_packages = []
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
        refresh_btn.clicked.connect(self.refresh_marketplace)
        toolbar_layout.addWidget(refresh_btn)

        # 搜索框
        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索插件...")
        self.search_box.setFixedSize(200, 25)
        self.search_box.textChanged.connect(self.search_plugins)
        toolbar_layout.addWidget(self.search_box)

        # 类型过滤
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部类型", "AI服务", "特效效果", "导出格式", "导入格式", "滤镜效果", "动画效果", "主题样式", "工具插件", "实用工具"])
        self.type_filter.currentTextChanged.connect(self.filter_by_type)
        toolbar_layout.addWidget(self.type_filter)

        # 排序方式
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["默认排序", "下载量", "评分", "最新发布"])
        self.sort_combo.currentTextChanged.connect(self.sort_packages)
        toolbar_layout.addWidget(self.sort_combo)

        toolbar_layout.addStretch()

        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.show_settings)
        toolbar_layout.addWidget(settings_btn)

        layout.addLayout(toolbar_layout)

        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧分类列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 分类标题
        category_label = QLabel("插件分类")
        category_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(category_label)

        # 分类列表
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(150)
        categories = [
            ("全部", "all"),
            ("推荐", "featured"),
            ("AI服务", "ai_provider"),
            ("特效效果", "effect"),
            ("导出格式", "export_format"),
            ("导入格式", "import_format"),
            ("滤镜效果", "filter"),
            ("动画效果", "animation"),
            ("主题样式", "theme"),
            ("工具插件", "tool"),
            ("实用工具", "utility"),
            ("最新发布", "newest"),
            ("热门下载", "popular")
        ]

        for display_name, key in categories:
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.category_list.addItem(item)

        self.category_list.currentItemChanged.connect(self.on_category_changed)
        left_layout.addWidget(self.category_list)

        # 更新信息
        update_group = QGroupBox("更新信息")
        update_layout = QVBoxLayout(update_group)

        self.update_label = QLabel("检查更新中...")
        update_layout.addWidget(self.update_label)

        self.check_updates_btn = QPushButton("检查更新")
        self.check_updates_btn.clicked.connect(self.check_updates)
        update_layout.addWidget(self.check_updates_btn)

        left_layout.addWidget(update_group)
        left_layout.addStretch()

        content_splitter.addWidget(left_widget)

        # 右侧插件列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.loading_progress)
        right_layout.addLayout(status_layout)

        # 插件网格
        self.plugins_scroll = QScrollArea()
        self.plugins_scroll.setWidgetResizable(True)
        self.plugins_content = QWidget()
        self.plugins_layout = QVBoxLayout(self.plugins_content)
        self.plugins_layout.setSpacing(10)
        self.plugins_scroll.setWidget(self.plugins_content)
        right_layout.addWidget(self.plugins_scroll)

        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([200, 700])
        layout.addWidget(content_splitter)

        # 初始加载
        QTimer.singleShot(100, self.load_initial_plugins)

    def connect_signals(self):
        """连接信号"""
        # 连接市场信号
        self.marketplace.api.repository_updated.connect(self.on_repository_updated)
        self.marketplace.api.download_progress.connect(self.on_download_progress)
        self.marketplace.api.download_completed.connect(self.on_download_completed)
        self.marketplace.api.download_failed.connect(self.on_download_failed)
        self.marketplace.installer.install_progress.connect(self.on_install_progress)
        self.marketplace.installer.install_completed.connect(self.on_install_completed)
        self.marketplace.installer.install_failed.connect(self.on_install_failed)

    async def load_initial_plugins(self):
        """加载初始插件"""
        self.set_loading(True)
        self.status_label.setText("正在加载插件数据...")

        try:
            # 刷新市场数据
            await self.marketplace.refresh_sources()

            # 加载推荐插件
            packages = await self.marketplace.search_plugins("", None)
            self.display_packages(packages)

            self.status_label.setText(f"共找到 {len(packages)} 个插件")
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载插件市场失败: {str(e)}")
        finally:
            self.set_loading(False)

    def refresh_marketplace(self):
        """刷新市场"""
        asyncio.create_task(self.load_initial_plugins())

    def search_plugins(self):
        """搜索插件"""
        query = self.search_box.text().strip()
        if query:
            asyncio.create_task(self._search_and_display(query))

    def filter_by_type(self, type_text: str):
        """按类型过滤"""
        if type_text != "全部类型":
            # 获取对应的插件类型
            type_map = {
                "AI服务": PluginType.AI_PROVIDER,
                "特效效果": PluginType.EFFECT,
                "导出格式": PluginType.EXPORT_FORMAT,
                "导入格式": PluginType.IMPORT_FORMAT,
                "滤镜效果": PluginType.FILTER,
                "动画效果": PluginType.ANIMATION,
                "主题样式": PluginType.THEME,
                "工具插件": PluginType.TOOL,
                "实用工具": PluginType.UTILITY
            }
            plugin_type = type_map.get(type_text)
            if plugin_type:
                asyncio.create_task(self._search_and_display("", plugin_type))

    def sort_packages(self, sort_text: str):
        """排序插件"""
        if not self.current_packages:
            return

        if sort_text == "下载量":
            self.current_packages.sort(key=lambda p: p.download_count, reverse=True)
        elif sort_text == "评分":
            self.current_packages.sort(key=lambda p: p.rating, reverse=True)
        elif sort_text == "最新发布":
            self.current_packages.sort(key=lambda p: p.publish_date, reverse=True)
        else:
            # 默认排序
            self.current_packages.sort(key=lambda p: (p.download_count, p.rating), reverse=True)

        self.display_packages(self.current_packages)

    def on_category_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """分类变化"""
        if current:
            category = current.data(Qt.ItemDataRole.UserRole)
            # 这里可以根据分类进行过滤
            # 简化处理，重新搜索
            self.search_plugins()

    async def _search_and_display(self, query: str, plugin_type: Optional[PluginType] = None):
        """搜索并显示插件"""
        self.set_loading(True)
        self.status_label.setText("搜索中...")

        try:
            packages = await self.marketplace.search_plugins(query, plugin_type)
            self.current_packages = packages
            self.display_packages(packages)
            self.status_label.setText(f"找到 {len(packages)} 个插件")
        except Exception as e:
            self.status_label.setText(f"搜索失败: {str(e)}")
        finally:
            self.set_loading(False)

    def display_packages(self, packages: List[PluginPackage]):
        """显示插件包"""
        # 清空现有内容
        for i in reversed(range(self.plugins_layout.count())):
            item = self.plugins_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        if not packages:
            no_results_label = QLabel("没有找到匹配的插件")
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_results_label.setStyleSheet("color: #666; font-size: 14px; padding: 50px;")
            self.plugins_layout.addWidget(no_results_label)
            return

        # 创建网格布局
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setSpacing(15)

        # 每行显示3个插件
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(15)

        for i, package in enumerate(packages):
            # 创建插件组件
            package_widget = PluginPackageWidget(package)
            package_widget.install_requested.connect(self.install_plugin)
            package_widget.details_requested.connect(self.show_plugin_details)
            row_layout.addWidget(package_widget)

            # 每3个插件换行
            if (i + 1) % 3 == 0:
                grid_layout.addWidget(row_widget)
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setSpacing(15)

        # 添加最后一行
        if row_layout.count() > 0:
            grid_layout.addWidget(row_widget)

        self.plugins_layout.addWidget(grid_widget)

    async def install_plugin(self, package: PluginPackage):
        """安装插件"""
        reply = QMessageBox.question(
            self, "安装插件",
            f"确定要安装插件 '{package.name}' v{package.version} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.set_loading(True)
            self.status_label.setText(f"正在安装 {package.name}...")

            try:
                success = await self.marketplace.install_plugin(package)
                if success:
                    QMessageBox.information(self, "安装成功", f"插件 '{package.name}' 安装成功！")
                    self.status_label.setText(f"插件 '{package.name}' 安装成功")
                else:
                    QMessageBox.warning(self, "安装失败", f"插件 '{package.name}' 安装失败")
                    self.status_label.setText("安装失败")
            except Exception as e:
                QMessageBox.critical(self, "安装错误", f"安装插件时发生错误:\n{str(e)}")
                self.status_label.setText("安装错误")
            finally:
                self.set_loading(False)

    def show_plugin_details(self, package: PluginPackage):
        """显示插件详情"""
        dialog = PluginDetailsDialog(package, self)
        dialog.install_requested.connect(self.install_plugin)
        dialog.exec()

    async def check_updates(self):
        """检查更新"""
        self.set_loading(True)
        self.update_label.setText("正在检查更新...")

        try:
            updates = await self.marketplace.check_updates()
            if updates:
                self.update_label.setText(f"发现 {len(updates)} 个更新")
                self.show_update_dialog(updates)
            else:
                self.update_label.setText("所有插件都是最新版本")
        except Exception as e:
            self.update_label.setText(f"检查更新失败: {str(e)}")
        finally:
            self.set_loading(False)

    def show_update_dialog(self, updates: List[tuple]):
        """显示更新对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("可用更新")
        dialog.setFixedSize(500, 400)

        layout = QVBoxLayout(dialog)

        # 标题
        title_label = QLabel(f"发现 {len(updates)} 个插件更新")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # 更新列表
        updates_widget = QTableWidget()
        updates_widget.setColumnCount(3)
        updates_widget.setHorizontalHeaderLabels(["插件名称", "当前版本", "新版本"])
        updates_widget.horizontalHeader().setStretchLastSection(True)
        updates_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for row, (plugin_id, new_package) in enumerate(updates):
            updates_widget.insertRow(row)
            updates_widget.setItem(row, 0, QTableWidgetItem(new_package.name))
            updates_widget.setItem(row, 1, QTableWidgetItem("v" + plugin_id.split("-")[-1]))  # 简化显示
            updates_widget.setItem(row, 2, QTableWidgetItem(f"v{new_package.version}"))

        layout.addWidget(updates_widget)

        # 按钮
        button_layout = QHBoxLayout()

        update_all_btn = QPushButton("全部更新")
        update_all_btn.clicked.connect(lambda: self.update_all_plugins(updates))
        button_layout.addWidget(update_all_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.exec()

    async def update_all_plugins(self, updates: List[tuple]):
        """更新所有插件"""
        success_count = 0
        for plugin_id, new_package in updates:
            try:
                success = await self.marketplace.update_plugin(plugin_id, new_package)
                if success:
                    success_count += 1
            except Exception:
                pass

        QMessageBox.information(self, "更新完成", f"成功更新 {success_count}/{len(updates)} 个插件")

    def show_settings(self):
        """显示设置对话框"""
        QMessageBox.information(self, "设置", "插件市场设置功能开发中...")

    def set_loading(self, loading: bool):
        """设置加载状态"""
        self.loading_progress.setVisible(loading)
        if loading:
            self.loading_progress.setRange(0, 0)  # 无限进度

    # 事件处理方法
    def on_repository_updated(self, source_name: str):
        """仓库更新完成"""
        self.status_label.setText(f"仓库 '{source_name}' 更新完成")

    def on_download_progress(self, package_id: str, downloaded: int, total: int):
        """下载进度"""
        progress = int((downloaded / total) * 100) if total > 0 else 0
        self.status_label.setText(f"下载进度: {progress}%")

    def on_download_completed(self, package_id: str, file_path: str):
        """下载完成"""
        self.status_label.setText("下载完成，正在安装...")

    def on_download_failed(self, package_id: str, error: str):
        """下载失败"""
        self.status_label.setText(f"下载失败: {error}")

    def on_install_progress(self, package_id: str, progress: int):
        """安装进度"""
        self.status_label.setText(f"安装进度: {progress}%")

    def on_install_completed(self, package_id: str, success: bool):
        """安装完成"""
        if success:
            self.status_label.setText("安装成功")
        else:
            self.status_label.setText("安装失败")


class PluginMarketplaceWindow(QWidget):
    """插件市场窗口"""

    def __init__(self, marketplace: PluginMarketplace, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插件市场")
        self.setFixedSize(1000, 700)
        self.setup_ui(marketplace, plugin_manager)

    def setup_ui(self, marketplace: PluginMarketplace, plugin_manager: PluginManager):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("插件市场")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # 插件市场UI
        self.marketplace_ui = PluginMarketplaceUI(marketplace, plugin_manager, self)
        layout.addWidget(self.marketplace_ui)

        # 底部信息
        info_label = QLabel("发现并安装各种插件来扩展CineAI Studio的功能")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)