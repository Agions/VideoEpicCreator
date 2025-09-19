#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕生成页面 - 提供AI驱动的字幕生成和编辑功能
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap

from app.ui.professional_ui_system import ProfessionalCard, ProfessionalButton


class SubtitlePage(QWidget):
    """字幕生成页面"""
    
    # 信号
    subtitle_generated = pyqtSignal(dict)  # 字幕生成完成信号
    
    def __init__(self, ai_manager=None, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.current_video = None
        self.is_dark_theme = False
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 页面标题
        title_label = QLabel("字幕生成")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧 - 视频和字幕编辑
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # 右侧 - AI生成和设置
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例
        main_splitter.setSizes([700, 500])
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 视频上传区域
        upload_card = ProfessionalCard("视频上传")
        upload_content = QWidget()
        upload_layout = QVBoxLayout(upload_content)
        upload_layout.setContentsMargins(0, 0, 0, 0)
        
        # 上传按钮和预览
        upload_btn_layout = QHBoxLayout()
        
        self.upload_btn = ProfessionalButton("📁 选择视频文件", "primary")
        self.video_info_label = QLabel("未选择视频")
        
        upload_btn_layout.addWidget(self.upload_btn)
        upload_btn_layout.addWidget(self.video_info_label)
        upload_btn_layout.addStretch()
        
        upload_layout.addLayout(upload_btn_layout)
        
        # 视频预览
        self.video_preview = QLabel("🎬 视频预览区域")
        self.video_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px dashed #ddd;
                border-radius: 8px;
                padding: 40px;
                font-size: 24px;
                min-height: 200px;
            }
        """)
        upload_layout.addWidget(self.video_preview)
        
        upload_card.add_content(upload_content)
        layout.addWidget(upload_card)
        
        # 字幕编辑区域
        subtitle_card = ProfessionalCard("字幕编辑")
        subtitle_content = QWidget()
        subtitle_layout = QVBoxLayout(subtitle_content)
        subtitle_layout.setContentsMargins(0, 0, 0, 0)
        
        # 字幕表格
        self.subtitle_table = QTableWidget()
        self.subtitle_table.setColumnCount(4)
        self.subtitle_table.setHorizontalHeaderLabels(["时间码", "开始时间", "结束时间", "字幕内容"])
        self.subtitle_table.horizontalHeader().setStretchLastSection(True)
        self.subtitle_table.setMaximumHeight(300)
        
        # 设置列宽
        self.subtitle_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.subtitle_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.subtitle_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.subtitle_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        subtitle_layout.addWidget(self.subtitle_table)
        
        # 字幕编辑工具
        edit_tools_layout = QHBoxLayout()
        
        self.add_subtitle_btn = ProfessionalButton("➕ 添加", "default")
        self.edit_subtitle_btn = ProfessionalButton("✏️ 编辑", "default")
        self.delete_subtitle_btn = ProfessionalButton("🗑️ 删除", "default")
        self.sync_subtitle_btn = ProfessionalButton("🔄 同步", "default")
        
        edit_tools_layout.addWidget(self.add_subtitle_btn)
        edit_tools_layout.addWidget(self.edit_subtitle_btn)
        edit_tools_layout.addWidget(self.delete_subtitle_btn)
        edit_tools_layout.addWidget(self.sync_subtitle_btn)
        edit_tools_layout.addStretch()
        
        subtitle_layout.addLayout(edit_tools_layout)
        
        subtitle_card.add_content(subtitle_content)
        layout.addWidget(subtitle_card)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # AI字幕生成设置
        ai_settings_card = ProfessionalCard("AI字幕生成设置")
        ai_settings_content = QWidget()
        ai_settings_layout = QVBoxLayout(ai_settings_content)
        ai_settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # 语言选择
        language_layout = QHBoxLayout()
        language_label = QLabel("目标语言:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "英文", "日文", "韩文", "法文", "德文"])
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        
        ai_settings_layout.addLayout(language_layout)
        
        # 字幕样式
        style_layout = QHBoxLayout()
        style_label = QLabel("字幕样式:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["简洁", "优雅", "活泼", "专业", "复古"])
        
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        style_layout.addStretch()
        
        ai_settings_layout.addLayout(style_layout)
        
        # 高级选项
        options_group = QGroupBox("高级选项")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_timestamp_checkbox = QCheckBox("自动时间轴同步")
        self.auto_timestamp_checkbox.setChecked(True)
        
        self.speech_recognition_checkbox = QCheckBox("语音识别增强")
        self.speech_recognition_checkbox.setChecked(True)
        
        self.translation_checkbox = QCheckBox("多语言翻译")
        
        options_layout.addWidget(self.auto_timestamp_checkbox)
        options_layout.addWidget(self.speech_recognition_checkbox)
        options_layout.addWidget(self.translation_checkbox)
        
        ai_settings_layout.addWidget(options_group)
        
        # 生成按钮
        self.generate_btn = ProfessionalButton("🤖 生成AI字幕", "primary")
        ai_settings_layout.addWidget(self.generate_btn)
        
        ai_settings_card.add_content(ai_settings_content)
        layout.addWidget(ai_settings_card)
        
        # 处理进度
        progress_card = ProfessionalCard("处理进度")
        progress_content = QWidget()
        progress_layout = QVBoxLayout(progress_content)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("就绪")
        progress_layout.addWidget(self.progress_label)
        
        progress_card.add_content(progress_content)
        layout.addWidget(progress_card)
        
        # 字幕预览
        preview_card = ProfessionalCard("字幕预览")
        preview_content = QWidget()
        preview_layout = QVBoxLayout(preview_content)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.subtitle_preview = QTextEdit()
        self.subtitle_preview.setPlaceholderText("生成的字幕内容将在这里显示...")
        self.subtitle_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.subtitle_preview)
        
        preview_card.add_content(preview_content)
        layout.addWidget(preview_card)
        
        # 导出选项
        export_card = ProfessionalCard("导出选项")
        export_content = QWidget()
        export_layout = QVBoxLayout(export_content)
        export_layout.setContentsMargins(0, 0, 0, 0)
        
        export_buttons_layout = QHBoxLayout()
        
        self.export_srt_btn = ProfessionalButton("📄 导出SRT", "default")
        self.export_ass_btn = ProfessionalButton("📝 导出ASS", "default")
        self.export_vtt_btn = ProfessionalButton("🌐 导出VTT", "default")
        self.burn_in_btn = ProfessionalButton("🔥 烧录字幕", "primary")
        
        export_buttons_layout.addWidget(self.export_srt_btn)
        export_buttons_layout.addWidget(self.export_ass_btn)
        export_buttons_layout.addWidget(self.export_vtt_btn)
        export_buttons_layout.addWidget(self.burn_in_btn)
        
        export_layout.addLayout(export_buttons_layout)
        
        export_card.add_content(export_content)
        layout.addWidget(export_card)
        
        layout.addStretch()
        
        return panel
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                SubtitlePage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #177ddc;
                }
            """)
        else:
            self.setStyleSheet("""
                SubtitlePage {
                    background-color: #ffffff;
                    color: #262626;
                }
                QLabel {
                    color: #262626;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid #ddd;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #1890ff;
                }
            """)
    
    def _connect_signals(self):
        """连接信号"""
        # 上传按钮
        self.upload_btn.clicked.connect(self._upload_video)
        
        # AI生成按钮
        self.generate_btn.clicked.connect(self._generate_subtitles)
        
        # 字幕编辑按钮
        self.add_subtitle_btn.clicked.connect(self._add_subtitle)
        self.edit_subtitle_btn.clicked.connect(self._edit_subtitle)
        self.delete_subtitle_btn.clicked.connect(self._delete_subtitle)
        self.sync_subtitle_btn.clicked.connect(self._sync_subtitles)
        
        # 导出按钮
        self.export_srt_btn.clicked.connect(lambda: self._export_subtitle("srt"))
        self.export_ass_btn.clicked.connect(lambda: self._export_subtitle("ass"))
        self.export_vtt_btn.clicked.connect(lambda: self._export_subtitle("vtt"))
        self.burn_in_btn.clicked.connect(self._burn_in_subtitles)
    
    def _upload_video(self):
        """上传视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
        )
        
        if file_path:
            self.current_video = file_path
            self.video_info_label.setText(f"已选择: {file_path.split('/')[-1]}")
            self.video_preview.setText("🎬 视频已加载")
            self.video_preview.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e8;
                    border: 2px solid #4caf50;
                    border-radius: 8px;
                    padding: 40px;
                    font-size: 24px;
                    min-height: 200px;
                }
            """)
    
    def _generate_subtitles(self):
        """生成AI字幕"""
        if not self.current_video:
            QMessageBox.warning(self, "提示", "请先上传视频文件")
            return
        
        if not self.ai_manager:
            QMessageBox.warning(self, "提示", "AI管理器未初始化")
            return
        
        try:
            self.progress_bar.setValue(0)
            self.progress_label.setText("正在分析视频...")
            
            # 模拟AI字幕生成过程
            QTimer.singleShot(1000, lambda: self._update_progress(20, "语音识别中..."))
            QTimer.singleShot(2000, lambda: self._update_progress(40, "文本生成中..."))
            QTimer.singleShot(3000, lambda: self._update_progress(60, "时间轴同步中..."))
            QTimer.singleShot(4000, lambda: self._update_progress(80, "字幕优化中..."))
            QTimer.singleShot(5000, lambda: self._complete_subtitle_generation())
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成字幕失败: {str(e)}")
    
    def _update_progress(self, value: int, text: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def _complete_subtitle_generation(self):
        """完成字幕生成"""
        self.progress_bar.setValue(100)
        self.progress_label.setText("字幕生成完成")
        
        # 模拟生成的字幕数据
        sample_subtitles = [
            ["00:00:01", "00:00:01", "00:00:04", "欢迎来到CineAIStudio"],
            ["00:00:05", "00:00:05", "00:00:08", "今天我们将学习如何使用AI生成字幕"],
            ["00:00:09", "00:00:09", "00:00:12", "这是一个强大的视频编辑工具"],
            ["00:00:13", "00:00:13", "00:00:16", "让您的视频内容更加专业"],
            ["00:00:17", "00:00:17", "00:00:20", "感谢您的观看"]
        ]
        
        # 填充字幕表格
        self.subtitle_table.setRowCount(len(sample_subtitles))
        for row, subtitle in enumerate(sample_subtitles):
            for col, text in enumerate(subtitle):
                item = QTableWidgetItem(text)
                self.subtitle_table.setItem(row, col, item)
        
        # 更新预览
        preview_text = "\n".join([f"[{sub[0]}] {sub[3]}" for sub in sample_subtitles])
        self.subtitle_preview.setPlainText(preview_text)
        
        QMessageBox.information(self, "成功", "AI字幕生成完成！")
        
        # 重置进度条
        QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
        QTimer.singleShot(2000, lambda: self.progress_label.setText("就绪"))
    
    def _add_subtitle(self):
        """添加字幕"""
        QMessageBox.information(self, "添加字幕", "添加字幕功能正在开发中")
    
    def _edit_subtitle(self):
        """编辑字幕"""
        current_row = self.subtitle_table.currentRow()
        if current_row >= 0:
            QMessageBox.information(self, "编辑字幕", f"编辑第 {current_row + 1} 条字幕")
        else:
            QMessageBox.warning(self, "提示", "请先选择要编辑的字幕")
    
    def _delete_subtitle(self):
        """删除字幕"""
        current_row = self.subtitle_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "删除字幕", 
                f"确定要删除第 {current_row + 1} 条字幕吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.subtitle_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "提示", "请先选择要删除的字幕")
    
    def _sync_subtitles(self):
        """同步字幕"""
        QMessageBox.information(self, "同步字幕", "字幕同步功能正在开发中")
    
    def _export_subtitle(self, format_type: str):
        """导出字幕"""
        if self.subtitle_table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "没有可导出的字幕")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"导出{format_type.upper()}字幕", 
            f"subtitles.{format_type}",
            f"{format_type.upper()}文件 (*.{format_type})"
        )
        
        if file_path:
            QMessageBox.information(self, "导出成功", f"字幕已导出到: {file_path}")
    
    def _burn_in_subtitles(self):
        """烧录字幕"""
        QMessageBox.information(self, "烧录字幕", "字幕烧录功能正在开发中")
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = SubtitlePage()
    window.show()
    sys.exit(app.exec())