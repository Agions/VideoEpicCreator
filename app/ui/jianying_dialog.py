"""
剪映草稿导入导出对话框
提供剪映草稿文件的导入和导出功能
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

from app.services.jianying_parser import JianyingDraftParser
from app.services.jianying_exporter import JianyingExporter


class JianyingImportDialog(QDialog):
    """剪映草稿导入对话框"""
    
    draft_imported = pyqtSignal(dict)  # 草稿导入成功信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = JianyingDraftParser()
        self.setup_ui()
        self.setWindowTitle("导入剪映草稿")
        self.setFixedSize(600, 400)
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 文件选择区域
        file_group = QGroupBox("选择草稿文件")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QTextEdit()
        self.file_path_edit.setPlaceholderText("点击选择剪映草稿文件...")
        self.file_path_edit.setMaximumHeight(60)
        self.file_path_edit.setReadOnly(True)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # 草稿信息显示区域
        info_group = QGroupBox("草稿信息")
        info_layout = QFormLayout(info_group)
        
        self.version_label = QLabel("-")
        self.duration_label = QLabel("-")
        self.resolution_label = QLabel("-")
        self.fps_label = QLabel("-")
        self.tracks_label = QLabel("-")
        self.status_label = QLabel("未选择文件")
        
        info_layout.addRow("版本:", self.version_label)
        info_layout.addRow("时长:", self.duration_label)
        info_layout.addRow("分辨率:", self.resolution_label)
        info_layout.addRow("帧率:", self.fps_label)
        info_layout.addRow("轨道数:", self.tracks_label)
        info_layout.addRow("状态:", self.status_label)
        
        layout.addWidget(info_group)
        
        # 导入选项
        options_group = QGroupBox("导入选项")
        options_layout = QVBoxLayout(options_group)
        
        self.copy_media_checkbox = QCheckBox("复制媒体文件到项目目录")
        self.copy_media_checkbox.setChecked(True)
        
        self.convert_effects_checkbox = QCheckBox("转换特效和转场")
        self.convert_effects_checkbox.setChecked(True)
        
        options_layout.addWidget(self.copy_media_checkbox)
        options_layout.addWidget(self.convert_effects_checkbox)
        
        layout.addWidget(options_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("导入")
        self.import_btn.clicked.connect(self.import_draft)
        self.import_btn.setEnabled(False)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def browse_file(self):
        """浏览选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择剪映草稿文件",
            "",
            "剪映草稿文件 (*.json *.draft *.zip);;所有文件 (*.*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.analyze_draft(file_path)
            
    def analyze_draft(self, file_path: str):
        """分析草稿文件"""
        try:
            info = self.parser.get_draft_info(file_path)
            
            if 'error' in info:
                self.status_label.setText(f"错误: {info['error']}")
                self.import_btn.setEnabled(False)
                return
            
            # 显示草稿信息
            self.version_label.setText(info.get('version', '-'))
            self.duration_label.setText(f"{info.get('duration', 0):.2f}秒")
            resolution = info.get('resolution', {})
            self.resolution_label.setText(f"{resolution.get('width', 0)}x{resolution.get('height', 0)}")
            self.fps_label.setText(f"{info.get('fps', 0)}fps")
            self.tracks_label.setText(str(info.get('track_count', 0)))
            
            if info.get('is_valid', False):
                self.status_label.setText("✓ 草稿文件有效")
                self.status_label.setStyleSheet("color: green;")
                self.import_btn.setEnabled(True)
            else:
                self.status_label.setText("✗ 草稿文件无效")
                self.status_label.setStyleSheet("color: red;")
                self.import_btn.setEnabled(False)
                
        except Exception as e:
            self.status_label.setText(f"分析失败: {str(e)}")
            self.import_btn.setEnabled(False)
            
    def import_draft(self):
        """导入草稿"""
        file_path = self.file_path_edit.toPlainText().strip()
        if not file_path:
            QMessageBox.warning(self, "警告", "请先选择草稿文件")
            return
            
        try:
            # 解析草稿
            draft = self.parser.parse_draft(file_path)
            
            # 转换为内部格式
            project_data = self.parser.convert_to_internal_format(draft)
            
            # 添加导入选项
            project_data['import_options'] = {
                'copy_media': self.copy_media_checkbox.isChecked(),
                'convert_effects': self.convert_effects_checkbox.isChecked(),
                'source_file': file_path
            }
            
            # 发送导入成功信号
            self.draft_imported.emit(project_data)
            
            QMessageBox.information(self, "成功", "剪映草稿导入成功！")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")


class JianyingExportDialog(QDialog):
    """剪映草稿导出对话框"""
    
    def __init__(self, project_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.exporter = JianyingExporter()
        self.setup_ui()
        self.setWindowTitle("导出为剪映草稿")
        self.setFixedSize(600, 500)
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = self.create_basic_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 高级选项选项卡
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "高级选项")
        
        layout.addWidget(tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self.export_draft)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def create_basic_tab(self):
        """创建基本设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 导出格式
        format_group = QGroupBox("导出格式")
        format_layout = QFormLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "剪映草稿 (.json)",
            "剪映专业版 (.zip)"
        ])
        
        format_layout.addRow("格式:", self.format_combo)
        layout.addWidget(format_group)
        
        # 文件位置
        file_group = QGroupBox("文件位置")
        file_layout = QFormLayout(file_group)
        
        self.output_path_edit = QTextEdit()
        self.output_path_edit.setPlaceholderText("点击选择输出位置...")
        self.output_path_edit.setMaximumHeight(60)
        self.output_path_edit.setReadOnly(True)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.output_path_edit)
        path_layout.addWidget(browse_btn)
        
        file_layout.addRow("输出位置:", path_layout)
        layout.addWidget(file_group)
        
        # 项目信息
        info_group = QGroupBox("项目信息")
        info_layout = QFormLayout(info_group)
        
        tracks_count = len(self.project_data.get('tracks', []))
        settings = self.project_data.get('settings', {})
        resolution = settings.get('resolution', {})
        
        info_layout.addRow("轨道数量:", QLabel(str(tracks_count)))
        info_layout.addRow("分辨率:", QLabel(f"{resolution.get('width', 0)}x{resolution.get('height', 0)}"))
        info_layout.addRow("帧率:", QLabel(f"{settings.get('fps', 0)}fps"))
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        return widget
        
    def create_advanced_tab(self):
        """创建高级选项选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 媒体文件选项
        media_group = QGroupBox("媒体文件")
        media_layout = QVBoxLayout(media_group)
        
        self.copy_media_checkbox = QCheckBox("复制媒体文件到项目目录")
        self.copy_media_checkbox.setChecked(True)
        
        self.convert_paths_checkbox = QCheckBox("转换为相对路径")
        self.convert_paths_checkbox.setChecked(True)
        
        media_layout.addWidget(self.copy_media_checkbox)
        media_layout.addWidget(self.convert_paths_checkbox)
        
        layout.addWidget(media_group)
        
        # 特效和转场
        effects_group = QGroupBox("特效和转场")
        effects_layout = QVBoxLayout(effects_group)
        
        self.include_effects_checkbox = QCheckBox("包含特效")
        self.include_effects_checkbox.setChecked(True)
        
        self.include_transitions_checkbox = QCheckBox("包含转场")
        self.include_transitions_checkbox.setChecked(True)
        
        effects_layout.addWidget(self.include_effects_checkbox)
        effects_layout.addWidget(self.include_transitions_checkbox)
        
        layout.addWidget(effects_group)
        
        # 模板选项
        template_group = QGroupBox("模板选项")
        template_layout = QVBoxLayout(template_group)
        
        self.save_as_template_checkbox = QCheckBox("保存为模板")
        
        self.template_name_edit = QTextEdit()
        self.template_name_edit.setPlaceholderText("输入模板名称...")
        self.template_name_edit.setMaximumHeight(40)
        self.template_name_edit.setEnabled(False)
        
        self.save_as_template_checkbox.stateChanged.connect(
            lambda state: self.template_name_edit.setEnabled(state == 2)
        )
        
        template_layout.addWidget(self.save_as_template_checkbox)
        template_layout.addWidget(self.template_name_edit)
        
        layout.addWidget(template_group)
        layout.addStretch()
        
        return widget
        
    def browse_output_path(self):
        """浏览输出路径"""
        format_index = self.format_combo.currentIndex()
        
        if format_index == 0:  # JSON格式
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择输出位置",
                "",
                "剪映草稿文件 (*.json);;所有文件 (*.*)"
            )
        else:  # ZIP格式
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择输出位置",
                "",
                "剪映专业版文件 (*.zip);;所有文件 (*.*)"
            )
        
        if file_path:
            self.output_path_edit.setText(file_path)
            
    def export_draft(self):
        """导出草稿"""
        output_path = self.output_path_edit.toPlainText().strip()
        if not output_path:
            QMessageBox.warning(self, "警告", "请选择输出位置")
            return
            
        try:
            format_type = 'jianying' if self.format_combo.currentIndex() == 0 else 'capcut'
            
            # 应用导出选项
            export_data = self.project_data.copy()
            
            if not self.include_effects_checkbox.isChecked():
                # 移除特效
                for track in export_data.get('tracks', []):
                    track['effects'] = []
                    
            if not self.include_transitions_checkbox.isChecked():
                # 移除转场
                for track in export_data.get('tracks', []):
                    track['transitions'] = []
            
            # 导出文件
            if self.save_as_template_checkbox.isChecked():
                template_name = self.template_name_edit.toPlainText().strip()
                if template_name:
                    exported_path = self.exporter.create_template(
                        export_data, template_name, output_path
                    )
                else:
                    QMessageBox.warning(self, "警告", "请输入模板名称")
                    return
            else:
                exported_path = self.exporter.export_to_jianying(
                    export_data, output_path, format_type
                )
            
            QMessageBox.information(self, "成功", f"导出成功！\n文件保存位置: {exported_path}")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class JianyingIntegrationDialog(QDialog):
    """剪映集成主对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setWindowTitle("剪映集成")
        self.setFixedSize(700, 500)
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 选项卡
        tab_widget = QTabWidget()
        
        # 导入选项卡
        import_tab = self.create_import_tab()
        tab_widget.addTab(import_tab, "导入剪映草稿")
        
        # 导出选项卡
        export_tab = self.create_export_tab()
        tab_widget.addTab(export_tab, "导出为剪映格式")
        
        # 帮助选项卡
        help_tab = self.create_help_tab()
        tab_widget.addTab(help_tab, "帮助")
        
        layout.addWidget(tab_widget)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def create_import_tab(self):
        """创建导入选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明文本
        info_label = QLabel(
            "导入剪映草稿文件，支持以下格式：\n"
            "• 剪映草稿文件 (.json)\n"
            "• 剪映专业版文件 (.zip)\n"
            "• 剪映旧版草稿 (.draft)"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        
        layout.addWidget(info_label)
        
        # 功能说明
        features_group = QGroupBox("功能特性")
        features_layout = QVBoxLayout(features_group)
        
        features = [
            "✓ 完美兼容剪映和剪映专业版",
            "✓ 自动解析时间线和轨道",
            "✓ 保持特效和转场效果",
            "✓ 智能转换媒体文件路径",
            "✓ 支持批量导入"
        ]
        
        for feature in features:
            label = QLabel(feature)
            layout.addWidget(label)
        
        features_layout.addWidget(QLabel("\n".join(features)))
        layout.addWidget(features_group)
        
        # 导入按钮
        import_btn = QPushButton("开始导入")
        import_btn.clicked.connect(self.show_import_dialog)
        import_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        
        layout.addWidget(import_btn)
        layout.addStretch()
        
        return widget
        
    def create_export_tab(self):
        """创建导出选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明文本
        info_label = QLabel(
            "将当前项目导出为剪映兼容格式：\n"
            "• 剪映草稿格式 (.json)\n"
            "• 剪映专业版格式 (.zip)\n"
            "• 支持创建可重用模板"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        
        layout.addWidget(info_label)
        
        # 功能说明
        features_group = QGroupBox("功能特性")
        features_layout = QVBoxLayout(features_group)
        
        features = [
            "✓ 导出为标准剪映格式",
            "✓ 包含完整的轨道和特效信息",
            "✓ 自动处理媒体文件",
            "✓ 支持批量导出",
            "✓ 创建可重用模板"
        ]
        
        features_layout.addWidget(QLabel("\n".join(features)))
        layout.addWidget(features_group)
        
        # 导出按钮
        export_btn = QPushButton("开始导出")
        export_btn.clicked.connect(self.show_export_dialog)
        export_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        
        layout.addWidget(export_btn)
        layout.addStretch()
        
        return widget
        
    def create_help_tab(self):
        """创建帮助选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 使用说明
        usage_group = QGroupBox("使用说明")
        usage_layout = QVBoxLayout(usage_group)
        
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setHtml("""
        <h3>工作流程</h3>
        <ol>
            <li><b>在剪映中编辑</b> - 使用剪映进行基础剪辑</li>
            <li><b>导入草稿</b> - 将剪映草稿导入到VideoEpicCreator</li>
            <li><b>AI增强</b> - 使用AI功能添加智能解说和剪辑</li>
            <li><b>导出草稿</b> - 将结果导出为剪映格式</li>
            <li><b>最终调整</b> - 在剪映中进行最终调整</li>
        </ol>
        
        <h3>支持的功能</h3>
        <ul>
            <li>多轨道视频和音频</li>
            <li>特效和转场效果</li>
            <li>文本和字幕</li>
            <li>关键帧动画</li>
            <li>音频处理</li>
        </ul>
        
        <h3>注意事项</h3>
        <ul>
            <li>确保媒体文件路径正确</li>
            <li>建议使用相对路径</li>
            <li>复杂特效可能需要手动调整</li>
        </ul>
        """)
        
        usage_layout.addWidget(usage_text)
        layout.addWidget(usage_group)
        
        return widget
        
    def show_import_dialog(self):
        """显示导入对话框"""
        dialog = JianyingImportDialog(self)
        dialog.exec()
        
    def show_export_dialog(self):
        """显示导出对话框"""
        # 这里需要传入当前项目数据
        # 临时使用空数据
        project_data = {
            'tracks': [],
            'settings': {'resolution': {'width': 1920, 'height': 1080}, 'fps': 30}
        }
        dialog = JianyingExportDialog(project_data, self)
        dialog.exec()