#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目设置对话框
提供项目详细设置功能
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QSlider, QGroupBox,
    QTabWidget, QWidget, QDialogButtonBox, QFormLayout,
    QPushButton, QMessageBox, QScrollArea, QFrame,
    QColorDialog, QFontDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ...core.project import ProjectInfo, ProjectSettings, ProjectMetadata
from ...core.project_manager import ProjectManager


class ProjectSettingsDialog(QDialog):
    """项目设置对话框"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.current_project = project_manager.get_current_project()
        
        self.setWindowTitle("项目设置")
        self.setModal(True)
        self.resize(600, 500)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 基本设置标签页
        self.basic_tab = self._create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "基本设置")
        
        # 视频设置标签页
        self.video_tab = self._create_video_tab()
        self.tab_widget.addTab(self.video_tab, "视频设置")
        
        # AI设置标签页
        self.ai_tab = self._create_ai_tab()
        self.tab_widget.addTab(self.ai_tab, "AI设置")
        
        # 导出设置标签页
        self.export_tab = self._create_export_tab()
        self.tab_widget.addTab(self.export_tab, "导出设置")
        
        # 高级设置标签页
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级设置")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        layout.addWidget(button_box)
    
    def _create_basic_tab(self) -> QWidget:
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 项目信息组
        info_group = QGroupBox("项目信息")
        info_layout = QFormLayout()
        
        self.project_name_input = QLineEdit()
        info_layout.addRow("项目名称:", self.project_name_input)
        
        self.project_description_input = QTextEdit()
        self.project_description_input.setMaximumHeight(80)
        info_layout.addRow("项目描述:", self.project_description_input)
        
        # 编辑模式
        self.editing_mode_combo = QComboBox()
        self.editing_mode_combo.addItem("解说模式", "commentary")
        self.editing_mode_combo.addItem("混剪模式", "compilation")
        self.editing_mode_combo.addItem("独白模式", "monologue")
        info_layout.addRow("编辑模式:", self.editing_mode_combo)
        
        # 项目状态
        self.status_combo = QComboBox()
        self.status_combo.addItem("草稿", "draft")
        self.status_combo.addItem("编辑中", "editing")
        self.status_combo.addItem("处理中", "processing")
        self.status_combo.addItem("已完成", "completed")
        self.status_combo.addItem("已导出", "exported")
        info_layout.addRow("项目状态:", self.status_combo)
        
        # 项目标签
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("输入标签，用逗号分隔")
        info_layout.addRow("项目标签:", self.tags_input)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 创建信息组
        creation_group = QGroupBox("创建信息")
        creation_layout = QFormLayout()
        
        self.created_by_label = QLabel()
        creation_layout.addRow("创建者:", self.created_by_label)
        
        self.created_at_label = QLabel()
        creation_layout.addRow("创建时间:", self.created_at_label)
        
        self.modified_at_label = QLabel()
        creation_layout.addRow("修改时间:", self.modified_at_label)
        
        self.project_version_label = QLabel()
        creation_layout.addRow("项目版本:", self.project_version_label)
        
        creation_group.setLayout(creation_layout)
        layout.addWidget(creation_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_video_tab(self) -> QWidget:
        """创建视频设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 视频质量组
        quality_group = QGroupBox("视频质量")
        quality_layout = QFormLayout()
        
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItem("低质量", "low")
        self.video_quality_combo.addItem("中等质量", "medium")
        self.video_quality_combo.addItem("高质量", "high")
        self.video_quality_combo.addItem("超高质量", "ultra")
        quality_layout.addRow("视频质量:", self.video_quality_combo)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("1920x1080 (Full HD)", "1920x1080")
        self.resolution_combo.addItem("1280x720 (HD)", "1280x720")
        self.resolution_combo.addItem("3840x2160 (4K)", "3840x2160")
        self.resolution_combo.addItem("2560x1440 (2K)", "2560x1440")
        quality_layout.addRow("分辨率:", self.resolution_combo)
        
        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(15, 120)
        self.frame_rate_spin.setValue(30)
        self.frame_rate_spin.setSuffix(" fps")
        quality_layout.addRow("帧率:", self.frame_rate_spin)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # 音频设置组
        audio_group = QGroupBox("音频设置")
        audio_layout = QFormLayout()
        
        self.audio_sample_rate_combo = QComboBox()
        self.audio_sample_rate_combo.addItem("44100 Hz", 44100)
        self.audio_sample_rate_combo.addItem("48000 Hz", 48000)
        self.audio_sample_rate_combo.addItem("96000 Hz", 96000)
        audio_layout.addRow("采样率:", self.audio_sample_rate_combo)
        
        self.audio_bitrate_spin = QSpinBox()
        self.audio_bitrate_spin.setRange(64, 320)
        self.audio_bitrate_spin.setValue(128)
        self.audio_bitrate_spin.setSuffix(" kbps")
        audio_layout.addRow("比特率:", self.audio_bitrate_spin)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_ai_tab(self) -> QWidget:
        """创建AI设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # AI模型设置组
        model_group = QGroupBox("AI模型设置")
        model_layout = QFormLayout()
        
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItem("通义千问-Max", "qwen-max")
        self.ai_model_combo.addItem("通义千问-Turbo", "qwen-turbo")
        self.ai_model_combo.addItem("文心一言", "wenxin")
        self.ai_model_combo.addItem("智谱GLM", "zhipu")
        self.ai_model_combo.addItem("Ollama", "ollama")
        model_layout.addRow("默认AI模型:", self.ai_model_combo)
        
        self.ai_temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.ai_temperature_slider.setRange(0, 100)
        self.ai_temperature_slider.setValue(70)
        self.ai_temperature_label = QLabel("0.7")
        self.ai_temperature_slider.valueChanged.connect(
            lambda v: self.ai_temperature_label.setText(f"{v/100:.2f}")
        )
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.ai_temperature_slider)
        temp_layout.addWidget(self.ai_temperature_label)
        model_layout.addRow("创造性:", temp_layout)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # AI功能设置组
        features_group = QGroupBox("AI功能设置")
        features_layout = QVBoxLayout()
        
        self.auto_subtitle_checkbox = QCheckBox("自动生成字幕")
        self.auto_subtitle_checkbox.setChecked(True)
        features_layout.addWidget(self.auto_subtitle_checkbox)
        
        self.smart_cut_checkbox = QCheckBox("智能剪辑")
        self.smart_cut_checkbox.setChecked(True)
        features_layout.addWidget(self.smart_cut_checkbox)
        
        self.auto_music_checkbox = QCheckBox("自动配乐")
        self.auto_music_checkbox.setChecked(False)
        features_layout.addWidget(self.auto_music_checkbox)
        
        self.content_filter_checkbox = QCheckBox("内容过滤")
        self.content_filter_checkbox.setChecked(True)
        features_layout.addWidget(self.content_filter_checkbox)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_export_tab(self) -> QWidget:
        """创建导出设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 导出格式组
        format_group = QGroupBox("导出格式")
        format_layout = QFormLayout()
        
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItem("MP4", "mp4")
        self.export_format_combo.addItem("MOV", "mov")
        self.export_format_combo.addItem("AVI", "avi")
        self.export_format_combo.addItem("MKV", "mkv")
        format_layout.addRow("默认格式:", self.export_format_combo)
        
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.addItem("H.264", "h264")
        self.video_codec_combo.addItem("H.265", "h265")
        self.video_codec_combo.addItem("VP9", "vp9")
        self.video_codec_combo.addItem("AV1", "av1")
        format_layout.addRow("视频编码:", self.video_codec_combo)
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItem("AAC", "aac")
        self.audio_codec_combo.addItem("MP3", "mp3")
        self.audio_codec_combo.addItem("Opus", "opus")
        format_layout.addRow("音频编码:", self.audio_codec_combo)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # 导出质量组
        quality_group = QGroupBox("导出质量")
        quality_layout = QFormLayout()
        
        self.export_bitrate_spin = QSpinBox()
        self.export_bitrate_spin.setRange(1000, 50000)
        self.export_bitrate_spin.setValue(8000)
        self.export_bitrate_spin.setSuffix(" kbps")
        quality_layout.addRow("视频比特率:", self.export_bitrate_spin)
        
        self.export_quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.export_quality_slider.setRange(1, 100)
        self.export_quality_slider.setValue(80)
        self.export_quality_label = QLabel("80%")
        self.export_quality_slider.valueChanged.connect(
            lambda v: self.export_quality_label.setText(f"{v}%")
        )
        
        quality_layout.addRow("导出质量:", self.export_quality_slider)
        quality_layout.addRow("", self.export_quality_label)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 自动保存组
        autosave_group = QGroupBox("自动保存")
        autosave_layout = QFormLayout()
        
        self.auto_save_checkbox = QCheckBox("启用自动保存")
        autosave_layout.addRow("自动保存:", self.auto_save_checkbox)
        
        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(30, 3600)
        self.auto_save_interval_spin.setValue(300)
        self.auto_save_interval_spin.setSuffix(" 秒")
        autosave_layout.addRow("保存间隔:", self.auto_save_interval_spin)
        
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        # 备份设置组
        backup_group = QGroupBox("备份设置")
        backup_layout = QFormLayout()
        
        self.backup_enabled_checkbox = QCheckBox("启用项目备份")
        backup_layout.addRow("项目备份:", self.backup_enabled_checkbox)
        
        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setRange(1, 50)
        self.backup_count_spin.setValue(5)
        backup_layout.addRow("备份数量:", self.backup_count_spin)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # 性能设置组
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout()
        
        self.hardware_acceleration_checkbox = QCheckBox("启用硬件加速")
        self.hardware_acceleration_checkbox.setChecked(True)
        performance_layout.addRow("硬件加速:", self.hardware_acceleration_checkbox)
        
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10240)
        self.cache_size_spin.setValue(1024)
        self.cache_size_spin.setSuffix(" MB")
        performance_layout.addRow("缓存大小:", self.cache_size_spin)
        
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 16)
        self.max_threads_spin.setValue(4)
        performance_layout.addRow("最大线程数:", self.max_threads_spin)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        layout.addStretch()
        
        return widget
    
    def _load_settings(self):
        """加载项目设置"""
        if not self.current_project:
            return
        
        project_info = self.current_project.project_info
        settings = project_info.settings
        metadata = project_info.metadata
        
        # 基本设置
        self.project_name_input.setText(project_info.name)
        self.project_description_input.setText(project_info.description)
        
        # 编辑模式
        mode_index = self.editing_mode_combo.findData(project_info.editing_mode)
        if mode_index >= 0:
            self.editing_mode_combo.setCurrentIndex(mode_index)
        
        # 项目状态
        status_index = self.status_combo.findData(project_info.status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
        
        # 项目标签
        self.tags_input.setText(", ".join(project_info.tags))
        
        # 创建信息
        self.created_by_label.setText(metadata.created_by)
        self.created_at_label.setText(datetime.fromisoformat(project_info.created_at).strftime("%Y-%m-%d %H:%M:%S"))
        self.modified_at_label.setText(datetime.fromisoformat(project_info.modified_at).strftime("%Y-%m-%d %H:%M:%S"))
        self.project_version_label.setText(metadata.project_version)
        
        # 视频设置
        quality_index = self.video_quality_combo.findData(settings.video_quality)
        if quality_index >= 0:
            self.video_quality_combo.setCurrentIndex(quality_index)
        
        resolution_index = self.resolution_combo.findData(settings.resolution)
        if resolution_index >= 0:
            self.resolution_combo.setCurrentIndex(resolution_index)
        
        self.frame_rate_spin.setValue(settings.frame_rate)
        
        sample_rate_index = self.audio_sample_rate_combo.findData(settings.audio_sample_rate)
        if sample_rate_index >= 0:
            self.audio_sample_rate_combo.setCurrentIndex(sample_rate_index)
        
        # AI设置
        ai_model_index = self.ai_model_combo.findData(settings.ai_model)
        if ai_model_index >= 0:
            self.ai_model_combo.setCurrentIndex(ai_model_index)
        
        # 导出设置
        format_index = self.export_format_combo.findData(settings.export_format)
        if format_index >= 0:
            self.export_format_combo.setCurrentIndex(format_index)
        
        # 自动保存设置
        self.auto_save_checkbox.setChecked(settings.auto_save_interval > 0)
        self.auto_save_interval_spin.setValue(settings.auto_save_interval)
        self.backup_enabled_checkbox.setChecked(settings.backup_enabled)
        self.backup_count_spin.setValue(settings.backup_count)
    
    def _apply_settings(self):
        """应用设置"""
        if not self.current_project:
            return
        
        try:
            # 获取设置
            settings = self._get_settings()
            
            # 更新项目设置
            project_info = self.current_project.project_info
            project_info.settings = ProjectSettings.from_dict(settings['settings'])
            
            # 更新项目信息
            project_info.name = settings['project_name']
            project_info.description = settings['project_description']
            project_info.editing_mode = settings['editing_mode']
            project_info.status = settings['status']
            project_info.tags = settings['tags']
            
            # 更新元数据
            project_info.metadata.created_by = settings['created_by']
            
            # 标记项目已修改
            self.project_manager.is_modified = True
            
            # 发射信号
            self.settings_changed.emit(settings)
            
            QMessageBox.information(self, "设置应用", "项目设置已应用成功！")
            
        except Exception as e:
            QMessageBox.critical(self, "设置应用失败", f"应用设置时发生错误：{str(e)}")
    
    def _get_settings(self) -> Dict[str, Any]:
        """获取设置数据"""
        return {
            'project_name': self.project_name_input.text(),
            'project_description': self.project_description_input.toPlainText(),
            'editing_mode': self.editing_mode_combo.currentData(),
            'status': self.status_combo.currentData(),
            'tags': [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()],
            'created_by': self.created_by_label.text(),
            'settings': {
                'video_quality': self.video_quality_combo.currentData(),
                'export_format': self.export_format_combo.currentData(),
                'resolution': self.resolution_combo.currentData(),
                'frame_rate': self.frame_rate_spin.value(),
                'audio_sample_rate': self.audio_sample_rate_combo.currentData(),
                'auto_save_interval': self.auto_save_interval_spin.value() if self.auto_save_checkbox.isChecked() else 0,
                'backup_enabled': self.backup_enabled_checkbox.isChecked(),
                'backup_count': self.backup_count_spin.value(),
                'ai_model': self.ai_model_combo.currentData(),
                'ai_temperature': self.ai_temperature_slider.value() / 100,
                'auto_subtitle': self.auto_subtitle_checkbox.isChecked(),
                'smart_cut': self.smart_cut_checkbox.isChecked(),
                'auto_music': self.auto_music_checkbox.isChecked(),
                'content_filter': self.content_filter_checkbox.isChecked(),
                'video_codec': self.video_codec_combo.currentData(),
                'audio_codec': self.audio_codec_combo.currentData(),
                'export_bitrate': self.export_bitrate_spin.value(),
                'export_quality': self.export_quality_slider.value(),
                'hardware_acceleration': self.hardware_acceleration_checkbox.isChecked(),
                'cache_size': self.cache_size_spin.value(),
                'max_threads': self.max_threads_spin.value()
            }
        }
    
    def accept(self):
        """确认对话框"""
        self._apply_settings()
        super().accept()