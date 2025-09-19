#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目模板对话框
提供项目模板管理功能
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QSlider, QGroupBox,
    QTabWidget, QWidget, QDialogButtonBox, QFormLayout,
    QPushButton, QMessageBox, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QSplitter, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap

from ...core.project_manager import ProjectManager, ProjectTemplate
from ...core.project import ProjectSettings


class TemplateItemWidget(QListWidgetItem):
    """模板列表项"""
    
    def __init__(self, template: ProjectTemplate):
        super().__init__()
        self.template = template
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        # 创建自定义widget
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 模板名称
        name_label = QLabel(self.template.name)
        name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        # 模板描述
        desc_label = QLabel(self.template.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888;")
        layout.addWidget(desc_label)
        
        # 模板信息
        info_layout = QHBoxLayout()
        
        category_label = QLabel(f"分类: {self.template.category}")
        category_label.setStyleSheet("background-color: #007bff; color: white; padding: 2px 6px; border-radius: 3px;")
        info_layout.addWidget(category_label)
        
        info_layout.addStretch()
        
        created_label = QLabel(f"创建: {datetime.fromisoformat(self.template.created_at).strftime('%Y-%m-%d')}")
        created_label.setStyleSheet("color: #666666; font-size: 10px;")
        info_layout.addWidget(created_label)
        
        layout.addLayout(info_layout)
        
        # 设置大小
        widget.setMinimumHeight(80)
        widget.setMaximumHeight(120)
        
        self.setSizeHint(widget.sizeHint())
        self.setData(Qt.ItemDataRole.UserRole, widget)


class ProjectTemplatesDialog(QDialog):
    """项目模板对话框"""
    
    template_selected = pyqtSignal(ProjectTemplate)
    template_created = pyqtSignal(ProjectTemplate)
    template_updated = pyqtSignal(ProjectTemplate)
    template_deleted = pyqtSignal(str)
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.current_template = None
        
        self.setWindowTitle("项目模板管理")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_templates()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QHBoxLayout(self)
        
        # 左侧模板列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.new_template_button = QPushButton("新建模板")
        self.new_template_button.clicked.connect(self._on_new_template)
        toolbar_layout.addWidget(self.new_template_button)
        
        self.edit_template_button = QPushButton("编辑模板")
        self.edit_template_button.clicked.connect(self._on_edit_template)
        self.edit_template_button.setEnabled(False)
        toolbar_layout.addWidget(self.edit_template_button)
        
        self.delete_template_button = QPushButton("删除模板")
        self.delete_template_button.clicked.connect(self._on_delete_template)
        self.delete_template_button.setEnabled(False)
        toolbar_layout.addWidget(self.delete_template_button)
        
        toolbar_layout.addStretch()
        
        left_layout.addLayout(toolbar_layout)
        
        # 模板列表
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self._on_template_selected)
        self.template_list.itemDoubleClicked.connect(self._on_template_double_clicked)
        left_layout.addWidget(self.template_list)
        
        # 右侧模板详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 模板预览
        self.template_preview = self._create_template_preview()
        right_layout.addWidget(self.template_preview)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.use_template_button = QPushButton("使用此模板")
        self.use_template_button.clicked.connect(self._on_use_template)
        self.use_template_button.setEnabled(False)
        button_layout.addWidget(self.use_template_button)
        
        self.export_template_button = QPushButton("导出模板")
        self.export_template_button.clicked.connect(self._on_export_template)
        self.export_template_button.setEnabled(False)
        button_layout.addWidget(self.export_template_button)
        
        self.import_template_button = QPushButton("导入模板")
        self.import_template_button.clicked.connect(self._on_import_template)
        button_layout.addWidget(self.import_template_button)
        
        right_layout.addLayout(button_layout)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _create_template_preview(self) -> QWidget:
        """创建模板预览区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 模板信息组
        info_group = QGroupBox("模板信息")
        info_layout = QFormLayout()
        
        self.template_name_label = QLabel()
        info_layout.addRow("名称:", self.template_name_label)
        
        self.template_description_label = QLabel()
        self.template_description_label.setWordWrap(True)
        info_layout.addRow("描述:", self.template_description_label)
        
        self.template_category_label = QLabel()
        info_layout.addRow("分类:", self.template_category_label)
        
        self.template_created_label = QLabel()
        info_layout.addRow("创建时间:", self.template_created_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 模板设置组
        settings_group = QGroupBox("模板设置")
        settings_layout = QFormLayout()
        
        self.template_resolution_label = QLabel()
        settings_layout.addRow("分辨率:", self.template_resolution_label)
        
        self.template_frame_rate_label = QLabel()
        settings_layout.addRow("帧率:", self.template_frame_rate_label)
        
        self.template_quality_label = QLabel()
        settings_layout.addRow("视频质量:", self.template_quality_label)
        
        self.template_ai_model_label = QLabel()
        settings_layout.addRow("AI模型:", self.template_ai_model_label)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 模板描述组
        desc_group = QGroupBox("模板描述")
        desc_layout = QVBoxLayout()
        
        self.template_details_text = QTextEdit()
        self.template_details_text.setReadOnly(True)
        desc_layout.addWidget(self.template_details_text)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        layout.addStretch()
        
        return widget
    
    def _load_templates(self):
        """加载模板列表"""
        self.template_list.clear()
        
        templates = self.project_manager.get_project_templates()
        
        for template in templates:
            item = TemplateItemWidget(template)
            self.template_list.addItem(item)
    
    def _update_template_preview(self, template: ProjectTemplate):
        """更新模板预览"""
        self.current_template = template
        
        # 基本信息
        self.template_name_label.setText(template.name)
        self.template_description_label.setText(template.description)
        self.template_category_label.setText(template.category)
        self.template_created_label.setText(
            datetime.fromisoformat(template.created_at).strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 设置信息
        self.template_resolution_label.setText(template.settings.resolution)
        self.template_frame_rate_label.setText(f"{template.settings.frame_rate} fps")
        
        quality_map = {
            "low": "低质量",
            "medium": "中等质量", 
            "high": "高质量",
            "ultra": "超高质量"
        }
        quality_text = quality_map.get(template.settings.video_quality, template.settings.video_quality)
        self.template_quality_label.setText(quality_text)
        
        # AI模型
        ai_model_map = {
            "qwen-max": "通义千问-Max",
            "qwen-turbo": "通义千问-Turbo",
            "wenxin": "文心一言",
            "zhipu": "智谱GLM",
            "ollama": "Ollama"
        }
        ai_model_text = ai_model_map.get(template.settings.ai_model, template.settings.ai_model)
        self.template_ai_model_label.setText(ai_model_text)
        
        # 详细描述
        details = f"""模板功能特点：
        
• 编辑模式：{template.category}
• 默认分辨率：{template.settings.resolution}
• 默认帧率：{template.settings.frame_rate} fps
• 视频质量：{quality_text}
• AI模型：{ai_model_text}
• 导出格式：{template.settings.export_format}

时间线配置：
{json.dumps(template.timeline_template, indent=2, ensure_ascii=False)}

AI设置：
{json.dumps(template.ai_settings, indent=2, ensure_ascii=False)}

导出设置：
{json.dumps(template.export_settings, indent=2, ensure_ascii=False)}
"""
        
        self.template_details_text.setText(details)
        
        # 启用按钮
        self.edit_template_button.setEnabled(True)
        self.delete_template_button.setEnabled(True)
        self.use_template_button.setEnabled(True)
        self.export_template_button.setEnabled(True)
    
    def _on_template_selected(self, item: QListWidgetItem):
        """模板被选中"""
        template = item.template
        self._update_template_preview(template)
    
    def _on_template_double_clicked(self, item: QListWidgetItem):
        """模板双击"""
        template = item.template
        self.template_selected.emit(template)
        self.accept()
    
    def _on_new_template(self):
        """新建模板"""
        dialog = TemplateEditDialog(self.project_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template = dialog.get_template()
            if template:
                self.template_created.emit(template)
                self._load_templates()
    
    def _on_edit_template(self):
        """编辑模板"""
        if not self.current_template:
            return
        
        dialog = TemplateEditDialog(self.project_manager, self, self.current_template)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template = dialog.get_template()
            if template:
                self.template_updated.emit(template)
                self._load_templates()
    
    def _on_delete_template(self):
        """删除模板"""
        if not self.current_template:
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{self.current_template.name}' 吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.template_deleted.emit(self.current_template.id)
            self._load_templates()
            
            # 清空预览
            self.current_template = None
            self.template_name_label.setText("")
            self.template_description_label.setText("")
            self.template_category_label.setText("")
            self.template_details_text.setText("")
            
            # 禁用按钮
            self.edit_template_button.setEnabled(False)
            self.delete_template_button.setEnabled(False)
            self.use_template_button.setEnabled(False)
            self.export_template_button.setEnabled(False)
    
    def _on_use_template(self):
        """使用模板"""
        if self.current_template:
            self.template_selected.emit(self.current_template)
            self.accept()
    
    def _on_export_template(self):
        """导出模板"""
        if not self.current_template:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出模板",
            f"{self.current_template.name}.json",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_template.to_dict(), f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "导出成功", f"模板已导出到：\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出模板时发生错误：{str(e)}")
    
    def _on_import_template(self):
        """导入模板"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入模板",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                template = ProjectTemplate.from_dict(template_data)
                self.template_created.emit(template)
                self._load_templates()
                
                QMessageBox.information(self, "导入成功", f"模板已导入：{template.name}")
                
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入模板时发生错误：{str(e)}")


class TemplateEditDialog(QDialog):
    """模板编辑对话框"""
    
    def __init__(self, project_manager: ProjectManager, parent=None, template: Optional[ProjectTemplate] = None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.editing_template = template
        
        self.setWindowTitle("编辑模板" if template else "新建模板")
        self.setModal(True)
        self.resize(500, 600)
        
        self._setup_ui()
        if template:
            self._load_template_data(template)
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入模板名称")
        basic_layout.addRow("模板名称:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("输入模板描述")
        self.description_input.setMaximumHeight(80)
        basic_layout.addRow("模板描述:", self.description_input)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("解说", "解说")
        self.category_combo.addItem("混剪", "混剪")
        self.category_combo.addItem("独白", "独白")
        basic_layout.addRow("模板分类:", self.category_combo)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 设置组
        settings_group = QGroupBox("默认设置")
        settings_layout = QFormLayout()
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("1920x1080 (Full HD)", "1920x1080")
        self.resolution_combo.addItem("1280x720 (HD)", "1280x720")
        self.resolution_combo.addItem("3840x2160 (4K)", "3840x2160")
        self.resolution_combo.addItem("2560x1440 (2K)", "2560x1440")
        settings_layout.addRow("分辨率:", self.resolution_combo)
        
        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(15, 120)
        self.frame_rate_spin.setValue(30)
        self.frame_rate_spin.setSuffix(" fps")
        settings_layout.addRow("帧率:", self.frame_rate_spin)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("低质量", "low")
        self.quality_combo.addItem("中等质量", "medium")
        self.quality_combo.addItem("高质量", "high")
        self.quality_combo.addItem("超高质量", "ultra")
        settings_layout.addRow("视频质量:", self.quality_combo)
        
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItem("MP4", "mp4")
        self.export_format_combo.addItem("MOV", "mov")
        self.export_format_combo.addItem("AVI", "avi")
        self.export_format_combo.addItem("MKV", "mkv")
        settings_layout.addRow("导出格式:", self.export_format_combo)
        
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItem("通义千问-Max", "qwen-max")
        self.ai_model_combo.addItem("通义千问-Turbo", "qwen-turbo")
        self.ai_model_combo.addItem("文心一言", "wenxin")
        self.ai_model_combo.addItem("智谱GLM", "zhipu")
        self.ai_model_combo.addItem("Ollama", "ollama")
        settings_layout.addRow("AI模型:", self.ai_model_combo)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QVBoxLayout()
        
        self.timeline_settings_text = QTextEdit()
        self.timeline_settings_text.setPlaceholderText("输入时间线设置（JSON格式）")
        self.timeline_settings_text.setMaximumHeight(100)
        advanced_layout.addWidget(QLabel("时间线设置:"))
        advanced_layout.addWidget(self.timeline_settings_text)
        
        self.ai_settings_text = QTextEdit()
        self.ai_settings_text.setPlaceholderText("输入AI设置（JSON格式）")
        self.ai_settings_text.setMaximumHeight(100)
        advanced_layout.addWidget(QLabel("AI设置:"))
        advanced_layout.addWidget(self.ai_settings_text)
        
        self.export_settings_text = QTextEdit()
        self.export_settings_text.setPlaceholderText("输入导出设置（JSON格式）")
        self.export_settings_text.setMaximumHeight(100)
        advanced_layout.addWidget(QLabel("导出设置:"))
        advanced_layout.addWidget(self.export_settings_text)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_template_data(self, template: ProjectTemplate):
        """加载模板数据"""
        self.name_input.setText(template.name)
        self.description_input.setText(template.description)
        
        category_index = self.category_combo.findData(template.category)
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)
        
        resolution_index = self.resolution_combo.findData(template.settings.resolution)
        if resolution_index >= 0:
            self.resolution_combo.setCurrentIndex(resolution_index)
        
        self.frame_rate_spin.setValue(template.settings.frame_rate)
        
        quality_index = self.quality_combo.findData(template.settings.video_quality)
        if quality_index >= 0:
            self.quality_combo.setCurrentIndex(quality_index)
        
        format_index = self.export_format_combo.findData(template.settings.export_format)
        if format_index >= 0:
            self.export_format_combo.setCurrentIndex(format_index)
        
        ai_model_index = self.ai_model_combo.findData(template.settings.ai_model)
        if ai_model_index >= 0:
            self.ai_model_combo.setCurrentIndex(ai_model_index)
        
        # 高级设置
        if template.timeline_template:
            self.timeline_settings_text.setText(json.dumps(template.timeline_template, indent=2, ensure_ascii=False))
        
        if template.ai_settings:
            self.ai_settings_text.setText(json.dumps(template.ai_settings, indent=2, ensure_ascii=False))
        
        if template.export_settings:
            self.export_settings_text.setText(json.dumps(template.export_settings, indent=2, ensure_ascii=False))
    
    def get_template(self) -> Optional[ProjectTemplate]:
        """获取模板数据"""
        try:
            # 基本信息
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "输入错误", "请输入模板名称！")
                return None
            
            description = self.description_input.toPlainText().strip()
            category = self.category_combo.currentData()
            
            # 设置
            settings = ProjectSettings(
                resolution=self.resolution_combo.currentData(),
                frame_rate=self.frame_rate_spin.value(),
                video_quality=self.quality_combo.currentData(),
                export_format=self.export_format_combo.currentData(),
                ai_model=self.ai_model_combo.currentData()
            )
            
            # 高级设置
            timeline_template = {}
            if self.timeline_settings_text.toPlainText().strip():
                try:
                    timeline_template = json.loads(self.timeline_settings_text.toPlainText())
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "格式错误", "时间线设置格式不正确！")
                    return None
            
            ai_settings = {}
            if self.ai_settings_text.toPlainText().strip():
                try:
                    ai_settings = json.loads(self.ai_settings_text.toPlainText())
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "格式错误", "AI设置格式不正确！")
                    return None
            
            export_settings = {}
            if self.export_settings_text.toPlainText().strip():
                try:
                    export_settings = json.loads(self.export_settings_text.toPlainText())
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "格式错误", "导出设置格式不正确！")
                    return None
            
            # 创建模板
            if self.editing_template:
                template = self.editing_template
                template.name = name
                template.description = description
                template.category = category
                template.settings = settings
                template.timeline_template = timeline_template
                template.ai_settings = ai_settings
                template.export_settings = export_settings
            else:
                template = ProjectTemplate(
                    id=f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    name=name,
                    description=description,
                    category=category,
                    settings=settings,
                    timeline_template=timeline_template,
                    ai_settings=ai_settings,
                    export_settings=export_settings
                )
            
            return template
            
        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"创建模板时发生错误：{str(e)}")
            return None
    
    def accept(self):
        """确认对话框"""
        template = self.get_template()
        if template:
            super().accept()