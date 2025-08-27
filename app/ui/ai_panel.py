#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QTextEdit, QScrollArea,
    QFrame, QSpinBox, QCheckBox, QToolButton, QTabWidget,
    QFileDialog, QDialog, QRadioButton, QButtonGroup, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTimeEdit,
    QMessageBox, QSplitter, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from PyQt6.QtGui import QIcon, QFont, QColor
import os
import time

class SubtitleExportDialog(QDialog):
    """字幕导出选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出字幕")
        self.setMinimumWidth(300)
        
        # 设置布局
        layout = QVBoxLayout(self)
        
        # 格式选择
        format_group = QGroupBox("选择格式")
        format_layout = QVBoxLayout(format_group)
        
        self.format_group = QButtonGroup(self)
        
        self.srt_radio = QRadioButton("SRT格式")
        self.srt_radio.setChecked(True)
        self.format_group.addButton(self.srt_radio)
        format_layout.addWidget(self.srt_radio)
        
        self.ass_radio = QRadioButton("ASS格式")
        self.format_group.addButton(self.ass_radio)
        format_layout.addWidget(self.ass_radio)
        
        self.txt_radio = QRadioButton("TXT纯文本")
        self.format_group.addButton(self.txt_radio)
        format_layout.addWidget(self.txt_radio)
        
        layout.addWidget(format_group)
        
        # 选项区域
        options_group = QGroupBox("导出选项")
        options_layout = QVBoxLayout(options_group)
        
        self.include_timecodes = QCheckBox("包含时间代码")
        self.include_timecodes.setChecked(True)
        options_layout.addWidget(self.include_timecodes)
        
        self.merge_lines = QCheckBox("合并相近的行")
        self.merge_lines.setChecked(True)
        options_layout.addWidget(self.merge_lines)
        
        layout.addWidget(options_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.export_button = QPushButton("导出")
        self.export_button.clicked.connect(self.accept)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
    
    def get_selected_format(self):
        """获取选中的格式"""
        if self.srt_radio.isChecked():
            return "srt"
        elif self.ass_radio.isChecked():
            return "ass"
        else:
            return "txt"
    
    def get_options(self):
        """获取导出选项"""
        return {
            "include_timecodes": self.include_timecodes.isChecked(),
            "merge_lines": self.merge_lines.isChecked()
        }


class SubtitleStyleDialog(QDialog):
    """字幕样式设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("字幕样式设置")
        self.setMinimumWidth(400)
        
        # 设置布局
        layout = QVBoxLayout(self)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QVBoxLayout(font_group)
        
        # 字体选择
        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("字体:"))
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["Arial", "微软雅黑", "宋体", "黑体"])
        font_family_layout.addWidget(self.font_family_combo)
        
        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 72)
        self.font_size_spin.setValue(20)
        font_size_layout.addWidget(self.font_size_spin)
        
        # 粗体
        self.bold_check = QCheckBox("粗体")
        self.bold_check.setChecked(False)
        
        # 斜体
        self.italic_check = QCheckBox("斜体")
        self.italic_check.setChecked(False)
        
        font_layout.addLayout(font_family_layout)
        font_layout.addLayout(font_size_layout)
        font_layout.addWidget(self.bold_check)
        font_layout.addWidget(self.italic_check)
        layout.addWidget(font_group)
        
        # 颜色设置
        color_group = QGroupBox("颜色设置")
        color_layout = QVBoxLayout(color_group)
        
        # 文字颜色
        text_color_layout = QHBoxLayout()
        text_color_layout.addWidget(QLabel("文字颜色:"))
        self.text_color_button = QPushButton("选择颜色")
        self.text_color_button.setStyleSheet("background-color: white;")
        self.text_color_button.clicked.connect(self._choose_text_color)
        text_color_layout.addWidget(self.text_color_button)
        
        # 描边颜色
        stroke_color_layout = QHBoxLayout()
        stroke_color_layout.addWidget(QLabel("描边颜色:"))
        self.stroke_color_button = QPushButton("选择颜色")
        self.stroke_color_button.setStyleSheet("background-color: black;")
        self.stroke_color_button.clicked.connect(self._choose_stroke_color)
        stroke_color_layout.addWidget(self.stroke_color_button)
        
        # 描边宽度
        stroke_width_layout = QHBoxLayout()
        stroke_width_layout.addWidget(QLabel("描边宽度:"))
        self.stroke_width_spin = QSpinBox()
        self.stroke_width_spin.setRange(0, 10)
        self.stroke_width_spin.setValue(2)
        stroke_width_layout.addWidget(self.stroke_width_spin)
        
        color_layout.addLayout(text_color_layout)
        color_layout.addLayout(stroke_color_layout)
        color_layout.addLayout(stroke_width_layout)
        layout.addWidget(color_group)
        
        # 位置设置
        position_group = QGroupBox("位置设置")
        position_layout = QVBoxLayout(position_group)
        
        # 水平位置
        h_position_layout = QHBoxLayout()
        h_position_layout.addWidget(QLabel("水平位置:"))
        self.h_position_combo = QComboBox()
        self.h_position_combo.addItems(["左对齐", "居中", "右对齐"])
        h_position_layout.addWidget(self.h_position_combo)
        
        # 垂直位置
        v_position_layout = QHBoxLayout()
        v_position_layout.addWidget(QLabel("垂直位置:"))
        self.v_position_combo = QComboBox()
        self.v_position_combo.addItems(["顶部", "中间", "底部"])
        v_position_layout.addWidget(self.v_position_combo)
        
        position_layout.addLayout(h_position_layout)
        position_layout.addLayout(v_position_layout)
        layout.addWidget(position_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.apply_button = QPushButton("应用")
        self.apply_button.clicked.connect(self.accept)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        
        # 保存颜色值
        self.text_color = "#FFFFFF"
        self.stroke_color = "#000000"
    
    def _choose_text_color(self):
        """选择文字颜色"""
        color = QColorDialog.getColor(QColor(self.text_color), self)
        if color.isValid():
            self.text_color = color.name()
            self.text_color_button.setStyleSheet(f"background-color: {self.text_color};")
    
    def _choose_stroke_color(self):
        """选择描边颜色"""
        color = QColorDialog.getColor(QColor(self.stroke_color), self)
        if color.isValid():
            self.stroke_color = color.name()
            self.stroke_color_button.setStyleSheet(f"background-color: {self.stroke_color};")
    
    def get_style(self):
        """获取样式设置"""
        return {
            "font_family": self.font_family_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "bold": self.bold_check.isChecked(),
            "italic": self.italic_check.isChecked(),
            "text_color": self.text_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width_spin.value(),
            "h_position": self.h_position_combo.currentText(),
            "v_position": self.v_position_combo.currentText()
        }


class TimelineWidget(QWidget):
    """时间轴编辑组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.subtitle_style = {}  # 保存字幕样式
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建时间轴表格
        self.timeline_table = QTableWidget()
        self.timeline_table.setColumnCount(4)
        self.timeline_table.setHorizontalHeaderLabels(["序号", "开始时间", "结束时间", "字幕内容"])
        self.timeline_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.timeline_table)
        
        # 创建编辑区域
        edit_layout = QHBoxLayout()
        
        # 时间编辑
        time_group = QGroupBox("时间编辑")
        time_layout = QVBoxLayout(time_group)
        
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(QLabel("开始时间:"))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm:ss.zzz")
        start_time_layout.addWidget(self.start_time_edit)
        
        end_time_layout = QHBoxLayout()
        end_time_layout.addWidget(QLabel("结束时间:"))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm:ss.zzz")
        end_time_layout.addWidget(self.end_time_edit)
        
        time_layout.addLayout(start_time_layout)
        time_layout.addLayout(end_time_layout)
        edit_layout.addWidget(time_group)
        
        # 字幕编辑
        text_group = QGroupBox("字幕编辑")
        text_layout = QVBoxLayout(text_group)
        
        self.subtitle_edit = QTextEdit()
        self.subtitle_edit.setMaximumHeight(100)
        text_layout.addWidget(self.subtitle_edit)
        
        # 编辑按钮
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用更改")
        self.apply_button.clicked.connect(self.apply_changes)
        button_layout.addWidget(self.apply_button)
        
        self.delete_button = QPushButton("删除字幕")
        self.delete_button.clicked.connect(self.delete_subtitle)
        button_layout.addWidget(self.delete_button)
        
        self.style_button = QPushButton("样式设置")
        self.style_button.clicked.connect(self.show_style_dialog)
        button_layout.addWidget(self.style_button)
        
        text_layout.addLayout(button_layout)
        edit_layout.addWidget(text_group)
        
        layout.addLayout(edit_layout)
        
        # 连接信号
        self.timeline_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def load_subtitles(self, subtitles):
        """加载字幕数据到时间轴"""
        self.timeline_table.setRowCount(len(subtitles))
        
        for i, sub in enumerate(subtitles):
            # 设置序号
            self.timeline_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # 设置时间
            self.timeline_table.setItem(i, 1, QTableWidgetItem(sub['start']))
            self.timeline_table.setItem(i, 2, QTableWidgetItem(sub['end']))
            
            # 设置字幕内容
            item = QTableWidgetItem(sub['text'])
            if 'style' in sub:
                item.setData(Qt.ItemDataRole.UserRole, sub['style'])
            self.timeline_table.setItem(i, 3, item)
        
        # 调整列宽
        self.timeline_table.resizeColumnsToContents()
        self.timeline_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    
    def show_style_dialog(self):
        """显示样式设置对话框"""
        dialog = SubtitleStyleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.subtitle_style = dialog.get_style()
            self.apply_style()
    
    def apply_style(self):
        """应用字幕样式"""
        # 更新当前选中行的样式
        current_row = self.timeline_table.currentRow()
        if current_row >= 0:
            # 创建样式表
            style = f"""
                QTableWidgetItem {{
                    font-family: {self.subtitle_style['font_family']};
                    font-size: {self.subtitle_style['font_size']}px;
                    color: {self.subtitle_style['text_color']};
                    background-color: transparent;
                }}
            """
            
            # 应用样式到字幕内容单元格
            item = self.timeline_table.item(current_row, 3)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, self.subtitle_style)
                self.timeline_table.setItem(current_row, 3, item)
    
    def on_selection_changed(self):
        """选择改变时更新编辑区域"""
        current_row = self.timeline_table.currentRow()
        if current_row >= 0:
            start_time = self.timeline_table.item(current_row, 1).text()
            end_time = self.timeline_table.item(current_row, 2).text()
            text = self.timeline_table.item(current_row, 3).text()
            
            self.start_time_edit.setTime(QTime.fromString(start_time, "HH:mm:ss"))
            self.end_time_edit.setTime(QTime.fromString(end_time, "HH:mm:ss"))
            self.subtitle_edit.setText(text)
    
    def apply_changes(self):
        """应用更改"""
        current_row = self.timeline_table.currentRow()
        if current_row >= 0:
            # 更新时间
            start_time = self.start_time_edit.time().toString("HH:mm:ss")
            end_time = self.end_time_edit.time().toString("HH:mm:ss")
            
            self.timeline_table.setItem(current_row, 1, QTableWidgetItem(start_time))
            self.timeline_table.setItem(current_row, 2, QTableWidgetItem(end_time))
            self.timeline_table.setItem(current_row, 3, QTableWidgetItem(self.subtitle_edit.toPlainText()))
    
    def delete_subtitle(self):
        """删除选中的字幕"""
        current_row = self.timeline_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                "确定要删除这条字幕吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.timeline_table.removeRow(current_row)
                # 更新序号
                for i in range(current_row, self.timeline_table.rowCount()):
                    self.timeline_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
    
    def get_subtitles(self):
        """获取所有字幕数据"""
        subtitles = []
        for row in range(self.timeline_table.rowCount()):
            item = self.timeline_table.item(row, 3)
            style = item.data(Qt.ItemDataRole.UserRole) if item else {}
            
            subtitles.append({
                "start": self.timeline_table.item(row, 1).text(),
                "end": self.timeline_table.item(row, 2).text(),
                "text": self.timeline_table.item(row, 3).text(),
                "style": style
            })
        return subtitles


class AIPanel(QWidget):
    """AI功能面板类"""
    
    # 自定义信号
    ai_result_ready = pyqtSignal(str, dict)  # 结果类型, 结果数据
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 当前选择的AI模型
        self.current_model = "通义千问"
        
        # AI模型配置
        self.ai_models = {
            "通义千问": {
                "enabled": True,
                "api_key": "",
                "max_tokens": 4096
            },
            "文心一言": {
                "enabled": False,
                "api_key": "",
                "max_tokens": 4096
            },
            "ChatGPT": {
                "enabled": False,
                "api_key": "",
                "max_tokens": 4096
            },
            "DeepSeek": {
                "enabled": False,
                "api_key": "",
                "max_tokens": 8192
            }
        }
        
        # 字幕内容
        self.subtitles = []
        
        # 初始化UI（确保在设置完AI模型后调用）
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建标题
        title_label = QLabel("AI 助手面板")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 字幕识别面板
        caption_panel = self._create_caption_panel()
        tab_widget.addTab(caption_panel, "字幕识别")
        
        # 智能剪辑面板
        edit_panel = self._create_edit_panel()
        tab_widget.addTab(edit_panel, "智能剪辑")
        
        # 特效生成面板
        effects_panel = self._create_effects_panel()
        tab_widget.addTab(effects_panel, "特效生成")
        
        # 创建状态区域
        status_label = QLabel("AI助手就绪")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(status_label)
        
        # 保存引用
        self.status_label = status_label
    
    def _create_caption_panel(self):
        """创建字幕识别面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 创建模型选择部分
        layout.addWidget(QLabel("选择AI模型:"))
        
        model_combo = QComboBox()
        model_combo.addItems(list(self.ai_models.keys()))
        model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(model_combo)
        
        # 创建识别选项部分
        layout.addWidget(QLabel("识别选项:"))
        
        # 字幕语言
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("语言:"))
        
        lang_combo = QComboBox()
        lang_combo.addItems(["自动检测", "中文", "英文", "其他"])
        lang_layout.addWidget(lang_combo)
        
        layout.addLayout(lang_layout)
        
        # 时间戳精度
        accuracy_layout = QHBoxLayout()
        accuracy_layout.addWidget(QLabel("时间戳精度:"))
        
        accuracy_spin = QSpinBox()
        accuracy_spin.setRange(1, 5)
        accuracy_spin.setValue(3)
        accuracy_spin.setSuffix(" (高)")
        accuracy_layout.addWidget(accuracy_spin)
        
        layout.addLayout(accuracy_layout)
        
        # 是否过滤语气词
        filter_layout = QHBoxLayout()
        filter_check = QCheckBox("过滤语气词和停顿")
        filter_check.setChecked(True)
        filter_layout.addWidget(filter_check)
        
        layout.addLayout(filter_layout)
        
        # 创建按钮
        button_layout = QHBoxLayout()
        
        start_button = QPushButton("开始识别")
        start_button.setIcon(QIcon())
        start_button.clicked.connect(self._on_start_caption)
        button_layout.addWidget(start_button)
        
        export_button = QPushButton("导出字幕")
        export_button.setEnabled(False)
        export_button.clicked.connect(self._on_export_caption)
        button_layout.addWidget(export_button)
        
        layout.addLayout(button_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 创建字幕编辑区域
        self.timeline_widget = TimelineWidget()
        splitter.addWidget(self.timeline_widget)
        
        # 创建结果显示区域
        self.caption_result_edit = QTextEdit()
        self.caption_result_edit.setReadOnly(True)
        self.caption_result_edit.setPlaceholderText("字幕将显示在这里...")
        splitter.addWidget(self.caption_result_edit)
        
        layout.addWidget(splitter)
        
        # 保存引用
        self.export_caption_button = export_button
        
        return panel
    
    def _on_model_changed(self, model_name):
        """AI模型变更回调"""
        self.current_model = model_name
        self.status_label.setText(f"已选择模型: {model_name}")
    
    def _on_start_caption(self):
        """开始字幕识别"""
        # TODO: 实现字幕识别功能
        self.status_label.setText("字幕识别中...")
        
        # 模拟识别结果
        self.caption_result_edit.setText("00:00:05 - 00:00:08  大家好，欢迎观看视频\n00:00:09 - 00:00:12  今天我们将介绍一个新产品")
        self.export_caption_button.setEnabled(True)
        
        # 加载字幕到时间轴
        self._parse_subtitles()
        self.timeline_widget.load_subtitles(self.subtitles)
    
    def _on_export_caption(self):
        """导出字幕"""
        # 如果没有字幕内容，显示提示
        if not self.caption_result_edit.toPlainText().strip():
            self.status_label.setText("没有可导出的字幕内容")
            return
            
        # 从时间轴获取最新的字幕数据
        self.subtitles = self.timeline_widget.get_subtitles()
        
        # 显示字幕导出对话框
        export_dialog = SubtitleExportDialog(self)
        if export_dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # 获取选中的格式和选项
        subtitle_format = export_dialog.get_selected_format()
        options = export_dialog.get_options()
        
        # 打开文件保存对话框
        file_filter = ""
        if subtitle_format == "srt":
            file_filter = "SRT字幕文件 (*.srt)"
        elif subtitle_format == "ass":
            file_filter = "ASS字幕文件 (*.ass)"
        else:
            file_filter = "文本文件 (*.txt)"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "保存字幕",
            os.path.expanduser("~/Desktop/subtitle." + subtitle_format),
            file_filter
        )
        
        # 如果用户取消了保存，返回
        if not file_path:
            return
            
        # 根据格式导出字幕
        success = self._export_subtitles(file_path, subtitle_format, options)
        
        if success:
            self.status_label.setText(f"字幕已导出到: {os.path.basename(file_path)}")
        else:
            self.status_label.setText("字幕导出失败")
    
    def _parse_subtitles(self):
        """解析字幕内容"""
        text = self.caption_result_edit.toPlainText()
        lines = text.strip().split("\n")
        self.subtitles = []
        
        for line in lines:
            # 尝试解析字幕行
            try:
                # 格式应该是 "00:00:05 - 00:00:08  大家好，欢迎观看视频"
                time_part, text_part = line.split("  ", 1)
                start_time, end_time = time_part.split(" - ")
                
                # 将时间转换为秒
                start_seconds = self._timecode_to_seconds(start_time)
                end_seconds = self._timecode_to_seconds(end_time)
                
                self.subtitles.append({
                    "start": start_time,
                    "start_seconds": start_seconds,
                    "end": end_time,
                    "end_seconds": end_seconds,
                    "text": text_part.strip()
                })
            except Exception as e:
                print(f"解析字幕行失败: {line} - {str(e)}")
    
    def _timecode_to_seconds(self, timecode):
        """将时间码转换为秒数"""
        h, m, s = timecode.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    
    def _seconds_to_timecode(self, seconds, format="srt"):
        """将秒数转换为时间码"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        
        if format == "srt":
            # SRT格式: 00:00:00,000
            milliseconds = int((seconds - int(seconds)) * 1000)
            return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
        else:
            # 普通格式: 00:00:00
            return f"{hours:02d}:{minutes:02d}:{seconds:.2f}"
    
    def _export_subtitles(self, file_path, format, options):
        """导出字幕"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if format == "srt":
                    self._write_srt(f)
                elif format == "ass":
                    self._write_ass(f)
                else:
                    self._write_txt(f, options)
            return True
        except Exception as e:
            print(f"导出字幕失败: {str(e)}")
            return False
    
    def _write_srt(self, file):
        """写入SRT格式字幕"""
        for i, sub in enumerate(self.subtitles):
            file.write(f"{i+1}\n")
            file.write(f"{self._seconds_to_timecode(sub['start_seconds'], 'srt')} --> {self._seconds_to_timecode(sub['end_seconds'], 'srt')}\n")
            file.write(f"{sub['text']}\n\n")
    
    def _write_ass(self, file):
        """写入ASS格式字幕"""
        # 写入ASS头部信息
        file.write("[Script Info]\n")
        file.write("Title: 由VideoEpicCreator生成的字幕\n")
        file.write("ScriptType: v4.00+\n")
        file.write("WrapStyle: 0\n")
        file.write("ScaledBorderAndShadow: yes\n")
        file.write("YCbCr Matrix: None\n\n")
        
        file.write("[V4+ Styles]\n")
        file.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        file.write("Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n")
        
        file.write("[Events]\n")
        file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        for sub in self.subtitles:
            start = self._seconds_to_timecode(sub['start_seconds']).replace('.', ':')
            end = self._seconds_to_timecode(sub['end_seconds']).replace('.', ':')
            file.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{sub['text']}\n")
    
    def _write_txt(self, file, options):
        """写入TXT格式字幕"""
        for sub in self.subtitles:
            if options["include_timecodes"]:
                file.write(f"{sub['start']} - {sub['end']} {sub['text']}\n")
            else:
                file.write(f"{sub['text']}\n")
    
    def update_status(self, message):
        """更新状态信息"""
        self.status_label.setText(message)
    
    def set_api_key(self, model, api_key):
        """设置API密钥"""
        if model in self.ai_models:
            self.ai_models[model]["api_key"] = api_key
            self.ai_models[model]["enabled"] = bool(api_key)
    
    def get_enabled_models(self):
        """获取已启用的模型列表"""
        return [name for name, config in self.ai_models.items() if config["enabled"]]

    def _create_edit_panel(self):
        """创建智能剪辑面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title_label = QLabel("智能剪辑助手")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 分析选项
        options_group = QGroupBox("分析选项")
        options_layout = QVBoxLayout(options_group)
        
        # 分析类型
        analysis_layout = QHBoxLayout()
        analysis_layout.addWidget(QLabel("分析类型:"))
        
        analysis_combo = QComboBox()
        analysis_combo.addItems(["内容分析", "情感分析", "节奏分析", "镜头分析"])
        analysis_layout.addWidget(analysis_combo)
        
        options_layout.addLayout(analysis_layout)
        
        # 场景检测
        scene_check = QCheckBox("自动场景检测")
        scene_check.setChecked(True)
        options_layout.addWidget(scene_check)
        
        # 亮点检测
        highlight_check = QCheckBox("亮点时刻检测")
        highlight_check.setChecked(True)
        options_layout.addWidget(highlight_check)
        
        layout.addWidget(options_group)
        
        # 分析按钮
        button_layout = QHBoxLayout()
        
        analyze_button = QPushButton("开始分析")
        analyze_button.clicked.connect(self._on_analyze_video)
        button_layout.addWidget(analyze_button)
        
        layout.addLayout(button_layout)
        
        # 结果区域
        result_label = QLabel("分析结果:")
        layout.addWidget(result_label)
        
        result_edit = QTextEdit()
        result_edit.setReadOnly(True)
        result_edit.setPlaceholderText("分析结果将显示在这里...")
        layout.addWidget(result_edit)
        
        # 保存引用
        self.analysis_result_edit = result_edit
        
        return panel
    
    def _create_effects_panel(self):
        """创建特效生成面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title_label = QLabel("特效生成助手")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 特效类型
        type_group = QGroupBox("特效类型")
        type_layout = QVBoxLayout(type_group)
        
        # 特效类型选择
        effects_layout = QHBoxLayout()
        effects_layout.addWidget(QLabel("选择特效:"))
        
        effects_combo = QComboBox()
        effects_combo.addItems(["转场特效", "文字特效", "滤镜效果", "动画效果"])
        effects_layout.addWidget(effects_combo)
        
        type_layout.addLayout(effects_layout)
        
        # 特效风格
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("特效风格:"))
        
        style_combo = QComboBox()
        style_combo.addItems(["现代简约", "复古风格", "动感活力", "电影级"])
        style_layout.addWidget(style_combo)
        
        type_layout.addLayout(style_layout)
        
        layout.addWidget(type_group)
        
        # 生成选项
        option_group = QGroupBox("生成选项")
        option_layout = QVBoxLayout(option_group)
        
        # 复杂度
        complexity_layout = QHBoxLayout()
        complexity_layout.addWidget(QLabel("复杂度:"))
        
        complexity_slider = QSpinBox()
        complexity_slider.setRange(1, 10)
        complexity_slider.setValue(5)
        complexity_layout.addWidget(complexity_slider)
        
        option_layout.addLayout(complexity_layout)
        
        # AI辅助
        ai_check = QCheckBox("使用AI优化特效参数")
        ai_check.setChecked(True)
        option_layout.addWidget(ai_check)
        
        layout.addWidget(option_group)
        
        # 生成按钮
        button_layout = QHBoxLayout()
        
        generate_button = QPushButton("生成特效")
        generate_button.clicked.connect(self._on_generate_effects)
        button_layout.addWidget(generate_button)
        
        layout.addLayout(button_layout)
        
        # 预览区域
        preview_label = QLabel("特效预览:")
        layout.addWidget(preview_label)
        
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.Box)
        preview_frame.setMinimumHeight(150)
        preview_frame.setStyleSheet("background-color: #222;")
        layout.addWidget(preview_frame)
        
        # 保存引用
        self.effects_preview_frame = preview_frame
        
        return panel
    
    def _on_analyze_video(self):
        """分析视频内容"""
        self.status_label.setText("正在分析视频...")
        
        # 模拟分析结果
        result = """
视频分析报告:
- 发现5个主要场景
- 检测到3个亮点时刻 (00:45, 02:10, 05:30)
- 建议剪辑点: 00:30, 01:15, 03:45, 06:20
- 节奏评分: 7/10
        """
        
        self.analysis_result_edit.setText(result.strip())
        self.status_label.setText("视频分析完成")
    
    def _on_generate_effects(self):
        """生成特效"""
        self.status_label.setText("正在生成特效...")
        
        # 模拟生成过程
        time.sleep(0.5)
        
        # 更新预览（此处应显示真实预览）
        self.effects_preview_frame.setStyleSheet("background-color: #222; border: 2px solid #0a84ff;")
        
        self.status_label.setText("特效生成完成，可以应用到视频中") 