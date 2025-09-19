#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导出分享页面 - 提供视频导出和分享功能
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QThread
from PyQt6.QtGui import QFont, QPixmap

from app.ui.professional_ui_system import ProfessionalCard, ProfessionalButton
from app.core.video_processing_engine import (
    VideoProcessingEngine, ProcessingConfig, VideoCodec, AudioCodec, VideoQuality
)


class ExportWorker(QThread):
    """导出工作线程"""
    
    # 信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    export_finished = pyqtSignal(bool, str)  # 导出完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, project, output_path, config):
        super().__init__()
        self.project = project
        self.output_path = output_path
        self.config = config
        self.is_cancelled = False
    
    def run(self):
        """执行导出任务"""
        try:
            self.progress_updated.emit(0, "正在准备导出...")
            
            # 创建视频处理引擎
            engine = VideoProcessingEngine()
            
            # 模拟导出过程
            for i in range(1, 101, 5):
                if self.is_cancelled:
                    self.export_finished.emit(False, "导出已取消")
                    return
                
                if i <= 20:
                    status = "正在分析项目..."
                elif i <= 40:
                    status = "正在编码视频..."
                elif i <= 60:
                    status = "正在编码音频..."
                elif i <= 80:
                    status = "正在合成音视频..."
                else:
                    status = "正在完成导出..."
                
                self.progress_updated.emit(i, status)
                self.msleep(200)
            
            # 实际导出逻辑
            success = engine.export_project(self.project, self.output_path, self.config)
            
            if success:
                self.export_finished.emit(True, "导出完成")
            else:
                self.export_finished.emit(False, "导出失败")
                
        except Exception as e:
            self.error_occurred.emit(f"导出过程中发生错误: {str(e)}")
    
    def cancel(self):
        """取消导出"""
        self.is_cancelled = True


class ExportPage(QWidget):
    """导出分享页面"""
    
    # 信号
    export_completed = pyqtSignal(dict)  # 导出完成信号
    
    def __init__(self, project_manager=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.current_project = None
        self.is_dark_theme = False
        self.export_worker = None
        
        # 初始化视频处理引擎
        self.video_engine = VideoProcessingEngine()
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 页面标题
        title_label = QLabel("导出分享")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧 - 导出设置
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # 右侧 - 分享选项
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例
        main_splitter.setSizes([600, 400])
        
        # 导出控制按钮
        export_controls_layout = QHBoxLayout()
        
        self.export_btn = ProfessionalButton("📤 开始导出", "primary")
        self.export_btn.clicked.connect(self._start_export)
        
        self.cancel_btn = ProfessionalButton("⏹️ 取消导出", "default")
        self.cancel_btn.clicked.connect(self._cancel_export)
        self.cancel_btn.setEnabled(False)
        
        export_controls_layout.addWidget(self.export_btn)
        export_controls_layout.addWidget(self.cancel_btn)
        export_controls_layout.addStretch()
        
        layout.addLayout(export_controls_layout)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 项目选择
        project_card = ProfessionalCard("项目选择")
        project_content = QWidget()
        project_layout = QVBoxLayout(project_content)
        project_layout.setContentsMargins(0, 0, 0, 0)
        
        project_select_layout = QHBoxLayout()
        
        self.project_combo = QComboBox()
        self.project_combo.addItems(["示例项目1", "示例项目2", "新建项目"])
        
        self.refresh_btn = ProfessionalButton("🔄 刷新", "default")
        
        project_select_layout.addWidget(QLabel("选择项目:"))
        project_select_layout.addWidget(self.project_combo)
        project_select_layout.addWidget(self.refresh_btn)
        project_select_layout.addStretch()
        
        project_layout.addLayout(project_select_layout)
        
        project_card.add_content(project_content)
        layout.addWidget(project_card)
        
        # 导出设置
        settings_card = ProfessionalCard("导出设置")
        settings_content = QWidget()
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # 格式选择
        format_layout = QHBoxLayout()
        format_label = QLabel("视频格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "AVI", "MOV", "MKV", "WMV"])
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        
        settings_layout.addLayout(format_layout)
        
        # 质量设置
        quality_group = QGroupBox("视频质量")
        quality_layout = QVBoxLayout(quality_group)
        
        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItems(["低质量", "标准质量", "高质量", "超高质量"])
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["原始分辨率", "1080p", "720p", "480p", "360p"])
        
        quality_layout.addWidget(QLabel("质量预设:"))
        quality_layout.addWidget(self.quality_preset_combo)
        quality_layout.addWidget(QLabel("分辨率:"))
        quality_layout.addWidget(self.resolution_combo)
        
        settings_layout.addWidget(quality_group)
        
        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QGridLayout(advanced_group)
        
        # 比特率
        advanced_layout.addWidget(QLabel("视频比特率:"), 0, 0)
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1, 100)
        self.bitrate_spin.setValue(8)
        self.bitrate_spin.setSuffix(" Mbps")
        advanced_layout.addWidget(self.bitrate_spin, 0, 1)
        
        # 帧率
        advanced_layout.addWidget(QLabel("帧率:"), 1, 0)
        self.framerate_combo = QComboBox()
        self.framerate_combo.addItems(["24 fps", "25 fps", "30 fps", "60 fps"])
        advanced_layout.addWidget(self.framerate_combo, 1, 1)
        
        # 编码器
        advanced_layout.addWidget(QLabel("编码器:"), 2, 0)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264", "H.265", "VP9", "AV1"])
        advanced_layout.addWidget(self.codec_combo, 2, 1)
        
        settings_layout.addWidget(advanced_group)
        
        # 输出路径
        output_layout = QHBoxLayout()
        output_label = QLabel("输出路径:")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出文件路径...")
        self.browse_btn = ProfessionalButton("📁 浏览", "default")
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.browse_btn)
        
        settings_layout.addLayout(output_layout)
        
        settings_card.add_content(settings_content)
        layout.addWidget(settings_card)
        
        # 处理进度
        progress_card = ProfessionalCard("导出进度")
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
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 快速分享
        share_card = ProfessionalCard("快速分享")
        share_content = QWidget()
        share_layout = QVBoxLayout(share_content)
        share_layout.setContentsMargins(0, 0, 0, 0)
        
        # 平台选择
        platforms = [
            ("📱 抖音", "douyin"),
            ("📸 小红书", "xiaohongshu"),
            ("🎬 B站", "bilibili"),
            ("📺 YouTube", "youtube"),
            ("🐦 Twitter", "twitter"),
            ("📘 Facebook", "facebook"),
            ("📷 Instagram", "instagram"),
            ("🔗 其他", "other")
        ]
        
        platform_grid = QGridLayout()
        for i, (text, platform) in enumerate(platforms):
            btn = ProfessionalButton(text, "default")
            btn.setProperty("platform", platform)
            platform_grid.addWidget(btn, i // 2, i % 2)
        
        share_layout.addLayout(platform_grid)
        
        share_card.add_content(share_content)
        layout.addWidget(share_card)
        
        # 分享设置
        share_settings_card = ProfessionalCard("分享设置")
        share_settings_content = QWidget()
        share_settings_layout = QVBoxLayout(share_settings_content)
        share_settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分享选项
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入视频标题...")
        share_settings_layout.addWidget(QLabel("视频标题:"))
        share_settings_layout.addWidget(self.title_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("输入视频描述...")
        self.description_edit.setMaximumHeight(100)
        share_settings_layout.addWidget(QLabel("视频描述:"))
        share_settings_layout.addWidget(self.description_edit)
        
        # 标签
        tags_layout = QHBoxLayout()
        tags_label = QLabel("标签:")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("用逗号分隔标签...")
        
        tags_layout.addWidget(tags_label)
        tags_layout.addWidget(self.tags_edit)
        
        share_settings_layout.addLayout(tags_layout)
        
        # 隐私设置
        privacy_layout = QHBoxLayout()
        privacy_label = QLabel("隐私设置:")
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["公开", "仅好友", "私密"])
        
        privacy_layout.addWidget(privacy_label)
        privacy_layout.addWidget(self.privacy_combo)
        privacy_layout.addStretch()
        
        share_settings_layout.addLayout(privacy_layout)
        
        share_settings_card.add_content(share_settings_content)
        layout.addWidget(share_settings_card)
        
        # 导出历史
        history_card = ProfessionalCard("导出历史")
        history_content = QWidget()
        history_layout = QVBoxLayout(history_content)
        history_layout.setContentsMargins(0, 0, 0, 0)
        
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(200)
        
        # 添加示例历史记录
        sample_history = [
            "示例项目1 - MP4 1080p - 2024-01-15",
            "示例项目2 - MP4 720p - 2024-01-14",
            "测试项目 - MP4 480p - 2024-01-13"
        ]
        
        for item in sample_history:
            self.history_list.addItem(item)
        
        history_layout.addWidget(self.history_list)
        
        # 历史操作按钮
        history_buttons_layout = QHBoxLayout()
        
        self.open_file_btn = ProfessionalButton("📂 打开文件", "default")
        self.share_again_btn = ProfessionalButton("🔄 重新分享", "default")
        self.clear_history_btn = ProfessionalButton("🗑️ 清空历史", "default")
        
        history_buttons_layout.addWidget(self.open_file_btn)
        history_buttons_layout.addWidget(self.share_again_btn)
        history_buttons_layout.addWidget(self.clear_history_btn)
        
        history_layout.addLayout(history_buttons_layout)
        
        history_card.add_content(history_content)
        layout.addWidget(history_card)
        
        layout.addStretch()
        
        return panel
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                ExportPage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                }
                QListWidget::item:selected {
                    background-color: #177ddc;
                }
            """)
        else:
            self.setStyleSheet("""
                ExportPage {
                    background-color: #ffffff;
                    color: #262626;
                }
                QLabel {
                    color: #262626;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid #ddd;
                }
                QListWidget::item:selected {
                    background-color: #1890ff;
                }
            """)
    
    def _connect_signals(self):
        """连接信号"""
        # 导出设置
        self.refresh_btn.clicked.connect(self._refresh_projects)
        self.browse_btn.clicked.connect(self._browse_output_path)
        
        # 分享平台按钮
        for btn in self.findChildren(ProfessionalButton):
            if btn.property("platform"):
                btn.clicked.connect(self._on_platform_clicked)
        
        # 历史记录按钮
        self.open_file_btn.clicked.connect(self._open_file)
        self.share_again_btn.clicked.connect(self._share_again)
        self.clear_history_btn.clicked.connect(self._clear_history)
    
    def _refresh_projects(self):
        """刷新项目列表"""
        QMessageBox.information(self, "刷新项目", "项目列表已刷新")
    
    def _browse_output_path(self):
        """浏览输出路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.output_path_edit.setText(file_path)
    
    def _on_platform_clicked(self):
        """分享平台点击"""
        btn = self.sender()
        platform = btn.property("platform")
        
        platform_names = {
            "douyin": "抖音",
            "xiaohongshu": "小红书",
            "bilibili": "B站",
            "youtube": "YouTube",
            "twitter": "Twitter",
            "facebook": "Facebook",
            "instagram": "Instagram",
            "other": "其他平台"
        }
        
        platform_name = platform_names.get(platform, "未知平台")
        QMessageBox.information(self, "分享到" + platform_name, f"正在准备分享到{platform_name}...")
    
    def _start_export(self):
        """开始导出"""
        if not self.output_path_edit.text():
            QMessageBox.warning(self, "提示", "请选择输出路径")
            return
        
        if not self.current_project:
            QMessageBox.warning(self, "提示", "没有可导出的项目")
            return
        
        # 创建导出配置
        config = self._create_export_config()
        
        # 禁用导出按钮，启用取消按钮
        self.export_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 创建导出工作线程
        self.export_worker = ExportWorker(
            self.current_project, 
            self.output_path_edit.text(), 
            config
        )
        
        # 连接信号
        self.export_worker.progress_updated.connect(self._update_progress)
        self.export_worker.export_finished.connect(self._on_export_finished)
        self.export_worker.error_occurred.connect(self._on_export_error)
        
        # 启动导出线程
        self.export_worker.start()
    
    def _cancel_export(self):
        """取消导出"""
        if self.export_worker and self.export_worker.isRunning():
            reply = QMessageBox.question(
                self, "确认取消", 
                "确定要取消当前导出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.export_worker.cancel()
                self.progress_label.setText("正在取消导出...")
    
    def _create_export_config(self) -> ProcessingConfig:
        """创建导出配置"""
        config = ProcessingConfig()
        
        # 设置视频编码器
        codec_map = {
            "H.264": VideoCodec.H264,
            "H.265": VideoCodec.H265,
            "VP9": VideoCodec.VP9,
            "AV1": VideoCodec.AV1
        }
        config.video_codec = codec_map.get(self.codec_combo.currentText(), VideoCodec.H264)
        
        # 设置音频编码器
        config.audio_codec = AudioCodec.AAC
        
        # 设置质量级别
        quality_map = {
            "低质量": VideoQuality.LOW,
            "标准质量": VideoQuality.MEDIUM,
            "高质量": VideoQuality.HIGH,
            "超高质量": VideoQuality.ULTRA
        }
        config.quality = quality_map.get(self.quality_preset_combo.currentText(), VideoQuality.HIGH)
        
        # 设置分辨率
        resolution = self.resolution_combo.currentText()
        if resolution != "原始分辨率":
            if resolution == "1080p":
                config.width = 1920
                config.height = 1080
            elif resolution == "720p":
                config.width = 1280
                config.height = 720
            elif resolution == "480p":
                config.width = 854
                config.height = 480
            elif resolution == "360p":
                config.width = 640
                config.height = 360
        
        # 设置比特率
        config.bitrate = self.bitrate_spin.value() * 1000000  # 转换为bps
        
        # 设置帧率
        fps_text = self.framerate_combo.currentText()
        config.fps = int(fps_text.replace(" fps", ""))
        
        return config
    
    def _update_progress(self, value: int, text: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def _on_export_finished(self, success: bool, message: str):
        """导出完成处理"""
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            self.progress_label.setText(message)
            
            # 添加到历史记录
            self._add_to_history()
            
            QMessageBox.information(self, "导出完成", "视频导出成功！")
        else:
            QMessageBox.warning(self, "导出失败", message)
        
        # 清理工作线程
        self.export_worker.deleteLater()
        self.export_worker = None
    
    def _on_export_error(self, error_message: str):
        """导出错误处理"""
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        QMessageBox.critical(self, "导出错误", error_message)
        
        # 清理工作线程
        if self.export_worker:
            self.export_worker.deleteLater()
            self.export_worker = None
    
    def _add_to_history(self):
        """添加到历史记录"""
        project_name = self.project_combo.currentText()
        format_name = self.format_combo.currentText()
        resolution = self.resolution_combo.currentText()
        
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        history_item = f"{project_name} - {format_name} {resolution} - {date_str}"
        self.history_list.insertItem(0, history_item)
    
    def _open_file(self):
        """打开文件"""
        current_item = self.history_list.currentItem()
        if current_item:
            QMessageBox.information(self, "打开文件", "正在打开视频文件...")
        else:
            QMessageBox.warning(self, "提示", "请先选择一个历史记录")
    
    def _share_again(self):
        """重新分享"""
        current_item = self.history_list.currentItem()
        if current_item:
            QMessageBox.information(self, "重新分享", "正在准备重新分享...")
        else:
            QMessageBox.warning(self, "提示", "请先选择一个历史记录")
    
    def _clear_history(self):
        """清空历史"""
        reply = QMessageBox.question(
            self, "清空历史", 
            "确定要清空所有导出历史吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history_list.clear()
            QMessageBox.information(self, "成功", "导出历史已清空")
    
    def set_project(self, project):
        """设置要导出的项目"""
        self.current_project = project
        if project:
            self.project_combo.addItem(project.name)
            self.project_combo.setCurrentText(project.name)
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()
    
    def cleanup(self):
        """清理资源"""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.cancel()
            self.export_worker.wait()
        
        if hasattr(self, 'video_engine'):
            self.video_engine.cleanup()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ExportPage()
    window.show()
    sys.exit(app.exec())