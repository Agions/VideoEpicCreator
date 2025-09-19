#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映导出面板UI组件
提供剪映项目导出的用户界面
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QProgressBar, QTextEdit, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPixmap, QIcon

from app.export.jianying_exporter import JianYingExporter, JianYingExportConfig, JianYingExportResult


class JianYingExportWorker(QThread):
    """剪映导出工作线程"""

    progress_updated = pyqtSignal(int, str)
    export_completed = pyqtSignal(object)
    export_error = pyqtSignal(str)

    def __init__(self, exporter: JianYingExporter, project_data: Any, config: JianYingExportConfig):
        super().__init__()
        self.exporter = exporter
        self.project_data = project_data
        self.config = config

        # 连接信号
        self.exporter.export_progress.connect(self.progress_updated.emit)
        self.exporter.export_completed.connect(self._on_export_completed)
        self.exporter.export_error.connect(self.export_error.emit)

    def run(self):
        """执行导出任务"""
        try:
            result = self.exporter.export_project(self.project_data, self.config)
            self.export_completed.emit(result)
        except Exception as e:
            self.export_error.emit(str(e))

    @pyqtSlot(object)
    def _on_export_completed(self, result: JianYingExportResult):
        """导出完成处理"""
        self.export_completed.emit(result)


class JianYingExportPanel(QWidget):
    """剪映导出面板"""

    # 信号定义
    export_started = pyqtSignal(str)
    export_progress = pyqtSignal(int, str)
    export_completed = pyqtSignal(object)
    export_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化组件
        self.exporter = JianYingExporter()
        self.export_worker = None
        self.current_project_data = None

        # UI状态
        self.is_exporting = False

        # 初始化UI
        self.init_ui()

        # 连接信号
        self.connect_signals()

        # 加载配置
        self.load_settings()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建标题
        title_label = QLabel("剪映项目导出")
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 创建主标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 导出设置标签页
        export_tab = self.create_export_tab()
        tab_widget.addTab(export_tab, "导出设置")

        # 项目信息标签页
        project_tab = self.create_project_tab()
        tab_widget.addTab(project_tab, "项目信息")

        # 剪映信息标签页
        jianying_tab = self.create_jianying_tab()
        tab_widget.addTab(jianying_tab, "剪映信息")

        # 历史记录标签页
        history_tab = self.create_history_tab()
        tab_widget.addTab(history_tab, "历史记录")

        # 创建进度区域
        progress_group = self.create_progress_group()
        layout.addWidget(progress_group)

        # 创建按钮区域
        button_layout = self.create_button_layout()
        layout.addLayout(button_layout)

    def create_export_tab(self) -> QWidget:
        """创建导出设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)

        # 项目名称
        self.project_name_edit = QLineEdit("未命名项目")
        basic_layout.addRow("项目名称:", self.project_name_edit)

        # 输出目录
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录...")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_btn)
        basic_layout.addRow("输出目录:", output_layout)

        # 剪映版本
        self.version_combo = QComboBox()
        self.version_combo.addItems(["4.0.0", "3.8.0", "3.7.0"])
        self.version_combo.setCurrentText("4.0.0")
        basic_layout.addRow("剪映版本:", self.version_combo)

        layout.addWidget(basic_group)

        # 内容设置组
        content_group = QGroupBox("内容设置")
        content_layout = QVBoxLayout(content_group)

        # 包含选项
        self.include_audio_check = QCheckBox("包含音频")
        self.include_audio_check.setChecked(True)
        content_layout.addWidget(self.include_audio_check)

        self.include_subtitles_check = QCheckBox("包含字幕")
        self.include_subtitles_check.setChecked(True)
        content_layout.addWidget(self.include_subtitles_check)

        self.include_effects_check = QCheckBox("包含特效")
        self.include_effects_check.setChecked(True)
        content_layout.addWidget(self.include_effects_check)

        self.include_transitions_check = QCheckBox("包含转场")
        self.include_transitions_check.setChecked(True)
        content_layout.addWidget(self.include_transitions_check)

        layout.addWidget(content_group)

        # 文件设置组
        file_group = QGroupBox("文件设置")
        file_layout = QFormLayout(file_group)

        # 复制媒体文件
        self.copy_media_check = QCheckBox("复制媒体文件")
        self.copy_media_check.setChecked(True)
        file_layout.addRow("", self.copy_media_check)

        # 创建备份
        self.create_backup_check = QCheckBox("创建备份")
        self.create_backup_check.setChecked(True)
        file_layout.addRow("", self.create_backup_check)

        # 压缩级别
        self.compression_spin = QSpinBox()
        self.compression_spin.setRange(1, 10)
        self.compression_spin.setValue(5)
        self.compression_spin.setSuffix(" (1-10)")
        file_layout.addRow("压缩级别:", self.compression_spin)

        layout.addWidget(file_group)

        # 导出后操作组
        action_group = QGroupBox("导出后操作")
        action_layout = QVBoxLayout(action_group)

        self.open_in_jianying_check = QCheckBox("导出后在剪映中打开")
        action_layout.addWidget(self.open_in_jianying_check)

        layout.addWidget(action_group)

        layout.addStretch()

        return widget

    def create_project_tab(self) -> QWidget:
        """创建项目信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 项目信息表格
        self.project_info_table = QTableWidget()
        self.project_info_table.setColumnCount(2)
        self.project_info_table.setHorizontalHeaderLabels(["属性", "值"])
        self.project_info_table.horizontalHeader().setStretchLastSection(True)
        self.project_info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.project_info_table)

        # 预览区域
        preview_group = QGroupBox("项目预览")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        return widget

    def create_jianying_tab(self) -> QWidget:
        """创建剪映信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 剪映安装状态
        install_group = QGroupBox("剪映安装状态")
        install_layout = QVBoxLayout(install_group)

        self.install_status_label = QLabel("检测中...")
        install_layout.addWidget(self.install_status_label)

        self.install_details_text = QTextEdit()
        self.install_details_text.setReadOnly(True)
        self.install_details_text.setMaximumHeight(150)
        install_layout.addWidget(self.install_details_text)

        layout.addWidget(install_group)

        # 兼容性信息
        compatibility_group = QGroupBox("兼容性信息")
        compatibility_layout = QVBoxLayout(compatibility_group)

        self.compatibility_text = QTextEdit()
        self.compatibility_text.setReadOnly(True)
        self.compatibility_text.setMaximumHeight(150)
        compatibility_layout.addWidget(self.compatibility_text)

        layout.addWidget(compatibility_group)

        # 支持的格式
        format_group = QGroupBox("支持的格式")
        format_layout = QVBoxLayout(format_group)

        self.format_text = QTextEdit()
        self.format_text.setReadOnly(True)
        self.format_text.setMaximumHeight(150)
        format_layout.addWidget(self.format_text)

        layout.addWidget(format_group)

        # 刷新按钮
        refresh_btn = QPushButton("刷新信息")
        refresh_btn.clicked.connect(self.refresh_jianying_info)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        # 初始化信息
        self.refresh_jianying_info()

        return widget

    def create_history_tab(self) -> QWidget:
        """创建历史记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "项目名称", "导出时间", "文件大小", "状态", "路径", "操作"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.history_table)

        # 操作按钮
        button_layout = QHBoxLayout()

        clear_history_btn = QPushButton("清除历史")
        clear_history_btn.clicked.connect(self.clear_history)
        button_layout.addWidget(clear_history_btn)

        export_selected_btn = QPushButton("重新导出选中")
        export_selected_btn.clicked.connect(self.export_selected)
        button_layout.addWidget(export_selected_btn)

        layout.addLayout(button_layout)

        # 加载历史记录
        self.load_history()

        return widget

    def create_progress_group(self) -> QGroupBox:
        """创建进度显示组"""
        group = QGroupBox("导出进度")
        layout = QVBoxLayout(group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)

        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        group.setVisible(False)

        return group

    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()

        # 导出按钮
        self.export_btn = QPushButton("开始导出")
        self.export_btn.clicked.connect(self.start_export)
        self.export_btn.setMinimumHeight(40)
        layout.addWidget(self.export_btn)

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_export)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setVisible(False)
        layout.addWidget(self.cancel_btn)

        return layout

    def connect_signals(self):
        """连接信号"""
        # 导出器信号
        self.exporter.export_progress.connect(self.update_progress)
        self.exporter.export_completed.connect(self.on_export_completed)
        self.exporter.export_error.connect(self.on_export_error)

    def set_project_data(self, project_data: Any):
        """设置项目数据"""
        self.current_project_data = project_data
        self.update_project_info()

    def update_project_info(self):
        """更新项目信息显示"""
        if not self.current_project_data:
            return

        try:
            # 获取项目摘要
            if hasattr(self.current_project_data, 'name'):
                project_name = self.current_project_data.name
            elif isinstance(self.current_project_data, dict):
                project_name = self.current_project_data.get('name', '未命名项目')
            else:
                project_name = '未命名项目'

            # 更新项目名称输入框
            self.project_name_edit.setText(project_name)

            # 更新项目信息表格
            self.project_info_table.setRowCount(0)

            info_items = [
                ("项目名称", project_name),
                ("创建时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ("导出工具", "CineAIStudio"),
                ("导出版本", "2.0.0")
            ]

            row = 0
            for key, value in info_items:
                self.project_info_table.insertRow(row)
                self.project_info_table.setItem(row, 0, QTableWidgetItem(key))
                self.project_info_table.setItem(row, 1, QTableWidgetItem(str(value)))
                row += 1

            # 更新预览文本
            preview_text = f"""
项目名称: {project_name}
创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
导出工具: CineAIStudio v2.0.0
目标格式: 剪映 {self.version_combo.currentText()}
预计状态: 准备导出
            """
            self.preview_text.setPlainText(preview_text.strip())

        except Exception as e:
            self.log_error(f"更新项目信息失败: {e}")

    def browse_output_directory(self):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir_edit.text()
        )

        if directory:
            self.output_dir_edit.setText(directory)

    def start_export(self):
        """开始导出"""
        if not self.current_project_data:
            QMessageBox.warning(self, "警告", "请先设置项目数据")
            return

        if self.is_exporting:
            QMessageBox.warning(self, "警告", "正在导出中，请等待完成")
            return

        # 创建导出配置
        config = self.create_export_config()

        # 验证配置
        if not self.validate_config(config):
            return

        # 开始导出
        self.is_exporting = True
        self.update_ui_for_exporting()

        # 创建工作线程
        self.export_worker = JianYingExportWorker(self.exporter, self.current_project_data, config)
        self.export_worker.progress_updated.connect(self.update_progress)
        self.export_worker.export_completed.connect(self.on_export_completed)
        self.export_worker.export_error.connect(self.on_export_error)

        self.export_worker.start()

        self.log_message("开始导出项目...")
        self.export_started.emit(config.project_name)

    def create_export_config(self) -> JianYingExportConfig:
        """创建导出配置"""
        return JianYingExportConfig(
            project_name=self.project_name_edit.text(),
            output_dir=self.output_dir_edit.text(),
            include_audio=self.include_audio_check.isChecked(),
            include_subtitles=self.include_subtitles_check.isChecked(),
            include_effects=self.include_effects_check.isChecked(),
            include_transitions=self.include_transitions_check.isChecked(),
            copy_media_files=self.copy_media_check.isChecked(),
            create_backup=self.create_backup_check.isChecked(),
            open_in_jianying=self.open_in_jianying_check.isChecked(),
            compression_level=self.compression_spin.value()
        )

    def validate_config(self, config: JianYingExportConfig) -> bool:
        """验证导出配置"""
        if not config.project_name:
            QMessageBox.warning(self, "警告", "请输入项目名称")
            return False

        if not config.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return False

        if not os.path.exists(config.output_dir):
            try:
                os.makedirs(config.output_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建输出目录失败: {e}")
                return False

        return True

    def cancel_export(self):
        """取消导出"""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.terminate()
            self.export_worker.wait()

        self.is_exporting = False
        self.update_ui_for_idle()
        self.log_message("导出已取消")

    def update_progress(self, progress: int, status: str):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        self.log_message(status)
        self.export_progress.emit(progress, status)

    def on_export_completed(self, result: JianYingExportResult):
        """导出完成处理"""
        self.is_exporting = False
        self.update_ui_for_idle()

        if result.success:
            self.log_message(f"导出成功！文件保存在: {result.project_path}")
            self.add_to_history(result)
            QMessageBox.information(self, "成功", "项目导出成功！")
        else:
            self.log_message(f"导出失败: {result.error_message}")
            QMessageBox.critical(self, "错误", f"导出失败: {result.error_message}")

        self.export_completed.emit(result)

    def on_export_error(self, error_message: str):
        """导出错误处理"""
        self.is_exporting = False
        self.update_ui_for_idle()
        self.log_message(f"导出错误: {error_message}")
        QMessageBox.critical(self, "错误", f"导出错误: {error_message}")
        self.export_error.emit(error_message)

    def update_ui_for_exporting(self):
        """更新UI为导出状态"""
        self.export_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在导出...")

        # 禁用设置控件
        self.project_name_edit.setEnabled(False)
        self.output_dir_edit.setEnabled(False)
        self.version_combo.setEnabled(False)
        self.include_audio_check.setEnabled(False)
        self.include_subtitles_check.setEnabled(False)
        self.include_effects_check.setEnabled(False)
        self.include_transitions_check.setEnabled(False)
        self.copy_media_check.setEnabled(False)
        self.create_backup_check.setEnabled(False)
        self.compression_spin.setEnabled(False)
        self.open_in_jianying_check.setEnabled(False)

    def update_ui_for_idle(self):
        """更新UI为空闲状态"""
        self.export_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.status_label.setText("准备就绪")

        # 启用设置控件
        self.project_name_edit.setEnabled(True)
        self.output_dir_edit.setEnabled(True)
        self.version_combo.setEnabled(True)
        self.include_audio_check.setEnabled(True)
        self.include_subtitles_check.setEnabled(True)
        self.include_effects_check.setEnabled(True)
        self.include_transitions_check.setEnabled(True)
        self.copy_media_check.setEnabled(True)
        self.create_backup_check.setEnabled(True)
        self.compression_spin.setEnabled(True)
        self.open_in_jianying_check.setEnabled(True)

    def refresh_jianying_info(self):
        """刷新剪映信息"""
        try:
            # 获取安装信息
            install_info = self.exporter.get_installation_info()

            if install_info["installed"]:
                self.install_status_label.setText("✓ 剪映已安装")
                self.install_status_label.setStyleSheet("color: green;")
            else:
                self.install_status_label.setText("✗ 剪映未安装")
                self.install_status_label.setStyleSheet("color: red;")

            # 显示安装详情
            details_text = f"""
系统: {install_info['system']}
安装路径: {', '.join(install_info['paths']) if install_info['paths'] else '未找到'}
支持版本: {', '.join(install_info['supported_versions'])}
当前版本: {install_info['current_version']}
            """
            self.install_details_text.setPlainText(details_text.strip())

            # 获取兼容性信息
            compatibility = self.exporter.validate_jianying_compatibility()

            compatibility_text = f"""
兼容状态: {'✓ 兼容' if compatibility['compatible'] else '✗ 不兼容'}
版本: {compatibility['version']}
问题: {'; '.join(compatibility['issues']) if compatibility['issues'] else '无'}
建议: {'; '.join(compatibility['recommendations']) if compatibility['recommendations'] else '无'}
            """
            self.compatibility_text.setPlainText(compatibility_text.strip())

            # 获取支持的格式
            formats = self.exporter.get_supported_formats()

            format_text = ""
            for format_type, extensions in formats.items():
                format_text += f"{format_type.upper()}: {', '.join(extensions)}\n"

            self.format_text.setPlainText(format_text.strip())

        except Exception as e:
            self.log_error(f"刷新剪映信息失败: {e}")

    def add_to_history(self, result: JianYingExportResult):
        """添加到历史记录"""
        try:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            # 项目名称
            self.history_table.setItem(row, 0, QTableWidgetItem(
                os.path.basename(result.project_path)
            ))

            # 导出时间
            self.history_table.setItem(row, 1, QTableWidgetItem(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            # 文件大小
            size_mb = result.file_size / (1024 * 1024)
            self.history_table.setItem(row, 2, QTableWidgetItem(
                f"{size_mb:.2f} MB"
            ))

            # 状态
            status_item = QTableWidgetItem("成功" if result.success else "失败")
            status_item.setForeground(
                Qt.GlobalColor.green if result.success else Qt.GlobalColor.red
            )
            self.history_table.setItem(row, 3, status_item)

            # 路径
            self.history_table.setItem(row, 4, QTableWidgetItem(result.project_path))

            # 操作按钮
            open_btn = QPushButton("打开")
            open_btn.clicked.connect(lambda: self.open_project_location(result.project_path))
            self.history_table.setCellWidget(row, 5, open_btn)

            # 保存历史记录
            self.save_history()

        except Exception as e:
            self.log_error(f"添加历史记录失败: {e}")

    def load_history(self):
        """加载历史记录"""
        try:
            # 这里可以从配置文件加载历史记录
            pass
        except Exception as e:
            self.log_error(f"加载历史记录失败: {e}")

    def save_history(self):
        """保存历史记录"""
        try:
            # 这里可以保存历史记录到配置文件
            pass
        except Exception as e:
            self.log_error(f"保存历史记录失败: {e}")

    def clear_history(self):
        """清除历史记录"""
        reply = QMessageBox.question(
            self, "确认", "确定要清除所有历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.history_table.setRowCount(0)
            self.save_history()

    def export_selected(self):
        """重新导出选中的项目"""
        selected_rows = self.history_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要重新导出的项目")
            return

        # 这里可以实现重新导出功能
        QMessageBox.information(self, "提示", "重新导出功能开发中...")

    def open_project_location(self, project_path: str):
        """打开项目位置"""
        try:
            import subprocess
            import platform

            system = platform.system().lower()

            if system == "windows":
                subprocess.Popen(['explorer', '/select,', project_path])
            elif system == "darwin":
                subprocess.Popen(['open', project_path])
            else:
                subprocess.Popen(['xdg-open', project_path])

        except Exception as e:
            self.log_error(f"打开项目位置失败: {e}")

    def log_message(self, message: str):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def log_error(self, error_message: str):
        """记录错误消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] ❌ {error_message}")

        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def load_settings(self):
        """加载设置"""
        try:
            # 这里可以从配置文件加载设置
            default_output_dir = os.path.expanduser("~/Desktop/CineAIStudio_Projects")
            self.output_dir_edit.setText(default_output_dir)

        except Exception as e:
            self.log_error(f"加载设置失败: {e}")

    def save_settings(self):
        """保存设置"""
        try:
            # 这里可以保存设置到配置文件
            pass
        except Exception as e:
            self.log_error(f"保存设置失败: {e}")

    def closeEvent(self, event):
        """关闭事件处理"""
        # 取消正在进行的导出
        if self.is_exporting:
            reply = QMessageBox.question(
                self, "确认", "导出正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.cancel_export()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()
