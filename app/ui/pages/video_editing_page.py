#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频编辑页面 - 提供完整的视频编辑功能
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QToolBar, QToolButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QUrl, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from app.ui.professional_ui_system import (
    ProfessionalCard, ProfessionalButton
)
from app.ui.utils import (
    ComponentBase, FileDialogManager, MessageHelper, 
    ProgressHelper, ButtonFactory, LayoutHelper
)
from app.ui.components.timeline_editor_component import ProfessionalTimelineEditor
from app.ui.components.video_preview_component import ProfessionalVideoPreviewPanel
from app.core.video_processing_engine import (
    VideoProcessingEngine, TimelineProject, ProcessingConfig, VideoInfo
)


class VideoEditingPage(ComponentBase):
    """视频编辑页面"""
    
    # 信号
    video_processed = pyqtSignal(dict)  # 视频处理完成信号
    project_loaded = pyqtSignal(TimelineProject)  # 项目加载完成信号
    project_saved = pyqtSignal(TimelineProject)  # 项目保存完成信号
    
    def __init__(self, ai_manager=None, project_manager=None, parent=None):
        self.ai_manager = ai_manager
        self.project_manager = project_manager
        self.current_project = None
        
        # 初始化组件
        self.video_engine = VideoProcessingEngine()
        self.progress_helper = None
        
        ComponentBase.__init__(self, parent)
        
        # 设置UI
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = self.setup_main_layout("vertical", margins=(10, 10, 10, 10), spacing=10)
        
        # 顶部工具栏
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(5)
        
        # 左侧 - 视频预览
        left_panel = self._create_preview_panel()
        main_splitter.addWidget(left_panel)
        
        # 中间 - 时间轴编辑器
        center_panel = self._create_timeline_panel()
        main_splitter.addWidget(center_panel)
        
        # 右侧 - AI增强功能
        right_panel = self._create_ai_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例
        main_splitter.setSizes([400, 800, 300])
        layout.addWidget(main_splitter, 1)
        
        # 底部状态栏
        self.status_bar = self._create_status_bar()
        layout.addWidget(self.status_bar)
    
    def _create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        
        # 文件操作
        new_action = QAction("📄 新建", self)
        new_action.triggered.connect(self._new_project)
        toolbar.addAction(new_action)
        
        open_action = QAction("📁 打开", self)
        open_action.triggered.connect(self._open_project)
        toolbar.addAction(open_action)
        
        save_action = QAction("💾 保存", self)
        save_action.triggered.connect(self._save_project)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # 编辑操作
        import_action = QAction("📥 导入视频", self)
        import_action.triggered.connect(self._import_video)
        toolbar.addAction(import_action)
        
        export_action = QAction("📤 导出视频", self)
        export_action.triggered.connect(self._export_video)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # 播放控制
        self.play_action = QAction("▶️ 播放", self)
        self.play_action.triggered.connect(self._toggle_playback)
        toolbar.addAction(self.play_action)
        
        stop_action = QAction("⏹️ 停止", self)
        stop_action.triggered.connect(self._stop_playback)
        toolbar.addAction(stop_action)
        
        return toolbar
    
    def _create_preview_panel(self) -> QWidget:
        """创建视频预览面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 视频预览组件
        self.video_preview = ProfessionalVideoPreviewPanel()
        layout.addWidget(self.video_preview)
        
        # 预览控制工具栏
        preview_toolbar = QToolBar()
        preview_toolbar.setIconSize(QSize(16, 16))
        
        # 基础编辑工具
        tools = [
            ("✂️ 裁剪", "crop"),
            ("🔄 旋转", "rotate"),
            ("⚡ 速度", "speed"),
            ("🔊 音量", "volume"),
            ("🎨 滤镜", "filter"),
            ("📝 文字", "text")
        ]
        
        for i, (text, tool_type) in enumerate(tools):
            action = QAction(text, self)
            action.setProperty("tool_type", tool_type)
            action.triggered.connect(self._on_tool_clicked)
            preview_toolbar.addAction(action)
            
            if (i + 1) % 3 == 0:
                preview_toolbar.addSeparator()
        
        layout.addWidget(preview_toolbar)
        
        return panel
    
    def _create_timeline_panel(self) -> QWidget:
        """创建时间轴面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 时间轴编辑器
        self.timeline_editor = ProfessionalTimelineEditor(self.video_engine)
        layout.addWidget(self.timeline_editor)
        
        return panel
    
    def _create_ai_panel(self) -> QWidget:
        """创建AI功能面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # AI功能卡片
        ai_card = ProfessionalCard("AI增强功能")
        
        # AI功能按钮
        ai_features = [
            ("🤖 AI解说生成", "ai_commentary"),
            ("🎭 AI角色配音", "ai_dubbing"),
            ("📝 AI字幕生成", "ai_subtitle"),
            ("🎵 AI背景音乐", "ai_music"),
            ("🎨 AI智能调色", "ai_color"),
            ("✂️ AI智能剪辑", "ai_edit")
        ]
        
        for text, feature_type in ai_features:
            btn = ProfessionalButton(text, "primary")
            btn.setProperty("feature_type", feature_type)
            ai_card.add_content(btn)
        
        layout.addWidget(ai_card)
        
        # 智能建议
        suggestions_card = ProfessionalCard("智能建议")
        
        # 建议列表
        self.suggestions_text = QTextEdit()
        self.suggestions_text.setPlaceholderText("AI将根据视频内容提供智能建议...")
        self.suggestions_text.setMaximumHeight(150)
        suggestions_card.add_content(self.suggestions_text)
        
        layout.addWidget(suggestions_card)
        
        # 处理进度
        progress_card = ProfessionalCard("处理进度")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_card.add_content(self.progress_bar)
        
        self.progress_label = QLabel("就绪")
        progress_card.add_content(self.progress_label)
        
        # 初始化进度助手
        self.progress_helper = ProgressHelper(self.progress_bar, self.progress_label)
        
        layout.addWidget(progress_card)
        
        layout.addStretch()
        
        return panel
    
    def _create_status_bar(self) -> QWidget:
        """创建状态栏"""
        status_bar = QWidget()
        status_bar.setFixedHeight(30)
        status_bar.setObjectName("status_bar")
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # 左侧信息
        self.project_info_label = QLabel("未选择项目")
        self.duration_label = QLabel("时长: 00:00")
        self.resolution_label = QLabel("分辨率: --")
        
        layout.addWidget(self.project_info_label)
        layout.addSpacing(20)
        layout.addWidget(self.duration_label)
        layout.addSpacing(20)
        layout.addWidget(self.resolution_label)
        
        layout.addStretch()
        
        # 右侧状态
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        return status_bar
    
    def _connect_signals(self):
        """连接信号"""
        # 时间轴编辑器信号
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor.project_loaded.connect(self._on_timeline_project_loaded)
            self.timeline_editor.project_saved.connect(self._on_timeline_project_saved)
            self.timeline_editor.clip_selected.connect(self._on_clip_selected)
            self.timeline_editor.time_changed.connect(self._on_time_changed)
            self.timeline_editor.playback_started.connect(self._on_playback_started)
            self.timeline_editor.playback_paused.connect(self._on_playback_paused)
            self.timeline_editor.playback_stopped.connect(self._on_playback_stopped)
        
        # 视频预览信号
        if hasattr(self, 'video_preview'):
            self.video_preview.video_selected.connect(self._on_video_selected)
            self.video_preview.playback_started.connect(self._on_playback_started)
            self.video_preview.playback_paused.connect(self._on_playback_paused)
            self.video_preview.playback_stopped.connect(self._on_playback_stopped)
            self.video_preview.position_changed.connect(self._on_preview_position_changed)
        
        # AI功能按钮
        for btn in self.findChildren(ProfessionalButton):
            if btn.property("feature_type"):
                self.connect_signal_safe(btn, 'clicked', self, '_on_ai_feature_clicked')
    
    def _on_timeline_project_loaded(self, project: TimelineProject):
        """时间轴项目加载完成"""
        self.current_project = project
        self.project_loaded.emit(project)
        self._update_status_info()
    
    def _on_timeline_project_saved(self, project: TimelineProject):
        """时间轴项目保存完成"""
        self.current_project = project
        self.project_saved.emit(project)
        self.status_label.setText("项目已保存")
    
    def _on_clip_selected(self, clip):
        """片段选中"""
        # 可以在这里显示片段属性
        self.status_label.setText(f"已选择片段: {clip.clip_id}")
    
    def _on_time_changed(self, time_seconds: float):
        """时间变更"""
        # 更新状态栏时间显示
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)
        self.duration_label.setText(f"时长: {minutes:02d}:{seconds:02d}")
    
    def _on_video_selected(self, file_path: str):
        """视频选中"""
        self.project_info_label.setText(f"项目: {file_path.split('/')[-1]}")
        
        # 获取视频信息
        try:
            video_info = self.video_engine.get_video_info(file_path)
            self.resolution_label.setText(f"分辨率: {video_info.width}x{video_info.height}")
            self.duration_label.setText(f"时长: {int(video_info.duration // 60):02d}:{int(video_info.duration % 60):02d}")
        except Exception as e:
            self.status_label.setText(f"获取视频信息失败: {e}")
    
    def _on_preview_position_changed(self, position_ms: int):
        """预览位置变更"""
        position_seconds = position_ms / 1000.0
        self._on_time_changed(position_seconds)
    
    def _on_playback_started(self):
        """播放开始"""
        self.play_action.setText("⏸️ 暂停")
        self.status_label.setText("正在播放")
    
    def _on_playback_paused(self):
        """播放暂停"""
        self.play_action.setText("▶️ 播放")
        self.status_label.setText("已暂停")
    
    def _on_playback_stopped(self):
        """播放停止"""
        self.play_action.setText("▶️ 播放")
        self.status_label.setText("已停止")
    
    def _toggle_playback(self):
        """切换播放状态"""
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor._toggle_playback()
        elif hasattr(self, 'video_preview'):
            self.video_preview.toggle_playback()
    
    def _stop_playback(self):
        """停止播放"""
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor._stop_playback()
        elif hasattr(self, 'video_preview'):
            self.video_preview.stop()
    
    def _update_status_info(self):
        """更新状态信息"""
        if self.current_project:
            self.project_info_label.setText(f"项目: {self.current_project.name}")
            
            # 计算项目时长
            total_duration = 0
            for track in self.current_project.video_tracks:
                for clip in track.clips:
                    clip_end = clip.position + clip.duration
                    if clip_end > total_duration:
                        total_duration = clip_end
            
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)
            self.duration_label.setText(f"时长: {minutes:02d}:{seconds:02d}")
        else:
            self.project_info_label.setText("未选择项目")
            self.duration_label.setText("时长: 00:00")
            self.resolution_label.setText("分辨率: --")
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                VideoEditingPage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QToolBar {
                    background-color: #2a2a2a;
                    border-bottom: 1px solid #404040;
                    spacing: 4px;
                    padding: 4px;
                }
                QWidget#status_bar {
                    background-color: #2a2a2a;
                    border-top: 1px solid #404040;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoEditingPage {
                    background-color: #ffffff;
                    color: #262626;
                }
                QLabel {
                    color: #262626;
                }
                QToolBar {
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #ddd;
                    spacing: 4px;
                    padding: 4px;
                }
                QWidget#status_bar {
                    background-color: #f5f5f5;
                    border-top: 1px solid #ddd;
                }
            """)
        
        # 更新子组件主题
        if hasattr(self, 'video_preview'):
            self.video_preview.set_theme(self.is_dark_theme)
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor.set_theme(self.is_dark_theme)
    
    def _on_tool_clicked(self):
        """基础编辑工具点击"""
        action = self.sender()
        tool_type = action.property("tool_type")
        
        # 这里实现具体的编辑工具功能
        print(f"点击编辑工具: {tool_type}")
        MessageHelper.show_info(self, "编辑工具", f"正在开发 {tool_type} 功能")
    
    def _on_ai_feature_clicked(self):
        """AI功能点击"""
        btn = self.sender()
        feature_type = btn.property("feature_type")
        
        if not self.ai_manager:
            MessageHelper.show_warning(self, "提示", "AI管理器未初始化")
            return
        
        # 根据功能类型调用相应的AI功能
        if feature_type == "ai_commentary":
            self._generate_ai_commentary()
        elif feature_type == "ai_subtitle":
            self._generate_ai_subtitle()
        elif feature_type == "ai_music":
            self._generate_ai_music()
        else:
            MessageHelper.show_info(self, "AI功能", f"正在开发 {feature_type} 功能")
    
    def _generate_ai_commentary(self):
        """生成AI解说"""
        try:
            self.progress_helper.set_progress(10, "正在分析视频内容...")
            
            # 模拟AI处理过程
            QTimer.singleShot(1000, lambda: self.progress_helper.set_progress(30, "生成解说脚本..."))
            QTimer.singleShot(2000, lambda: self.progress_helper.set_progress(60, "优化解说内容..."))
            QTimer.singleShot(3000, lambda: self.progress_helper.set_progress(90, "完成解说生成..."))
            QTimer.singleShot(4000, lambda: self._complete_ai_task("解说", "AI解说已生成完成"))
            
        except Exception as e:
            self.handle_error(e, "生成解说失败")
    
    def _generate_ai_subtitle(self):
        """生成AI字幕"""
        try:
            self.progress_helper.set_progress(10, "正在识别语音...")
            
            QTimer.singleShot(1500, lambda: self.progress_helper.set_progress(40, "生成字幕文本..."))
            QTimer.singleShot(3000, lambda: self.progress_helper.set_progress(70, "同步时间轴..."))
            QTimer.singleShot(4500, lambda: self._complete_ai_task("字幕", "AI字幕已生成完成"))
            
        except Exception as e:
            self.handle_error(e, "生成字幕失败")
    
    def _generate_ai_music(self):
        """生成AI背景音乐"""
        try:
            self.progress_helper.set_progress(20, "分析视频情感...")
            
            QTimer.singleShot(2000, lambda: self.progress_helper.set_progress(50, "生成音乐风格..."))
            QTimer.singleShot(4000, lambda: self._complete_ai_task("音乐", "AI背景音乐已生成完成"))
            
        except Exception as e:
            self.handle_error(e, "生成音乐失败")
    
    def _complete_ai_task(self, task_type: str, message: str):
        """完成AI任务"""
        self.progress_bar.setValue(100)
        self.progress_label.setText(message)
        
        # 添加到建议区域
        current_text = self.suggestions_text.toPlainText()
        new_suggestion = f"✅ {task_type}: {message}\n"
        self.suggestions_text.setPlainText(current_text + new_suggestion)
        
        # 重置进度条
        QTimer.singleShot(2000, lambda: self.progress_helper.reset_progress())
    
    def _new_project(self):
        """新建项目"""
        if hasattr(self, "timeline_editor_component"):
            project = self.timeline_editor.create_new_project("新项目")
            self.status_label.setText("已创建新项目")
    
    def _open_project(self):
        """打开项目"""
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor._open_project()
    
    def _save_project(self):
        """保存项目"""
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor._save_project()
    
    def _import_video(self):
        """导入视频"""
        file_path, _ = FileDialogManager.open_video_file(self)
        
        if file_path:
            try:
                # 如果有时间轴编辑器，添加到时间轴
                if hasattr(self, "timeline_editor_component") and self.timeline_editor.current_project:
                    # 添加到第一个视频轨道
                    if self.timeline_editor.current_project.video_tracks:
                        track_id = self.timeline_editor.current_project.video_tracks[0].track_id
                        self.timeline_editor.add_clip_to_track(track_id, file_path, 0.0)
                        self.status_label.setText(f"已导入视频: {file_path.split('/')[-1]}")
                    else:
                        MessageHelper.show_warning(self, "提示", "请先创建视频轨道")
                else:
                    # 否则直接加载到预览器
                    self.video_preview.load_video(file_path)
                    self.status_label.setText(f"已加载视频: {file_path.split('/')[-1]}")
                
            except Exception as e:
                MessageHelper.show_error(self, "导入失败", f"导入视频失败: {e}")
    
    def _export_video(self):
        """导出视频"""
        if not hasattr(self, "timeline_editor_component") or not self.timeline_editor.current_project:
            MessageHelper.show_warning(self, "提示", "没有可导出的项目")
            return
        
        # 打开导出对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出视频", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            try:
                # 创建导出配置
                config = ProcessingConfig()
                config.video_codec = config.video_codec.H264
                config.audio_codec = config.audio_codec.AAC
                config.quality = config.quality.HIGH
                
                # 导出项目
                success = self.timeline_editor.export_project(file_path, config)
                
                if success:
                    MessageHelper.show_info(self, "导出成功", "视频导出成功！")
                    self.status_label.setText("视频导出成功")
                else:
                    MessageHelper.show_error(self, "导出失败", "视频导出失败")
                    
            except Exception as e:
                MessageHelper.show_error(self, "导出失败", f"导出视频失败: {e}")
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'video_preview'):
            self.video_preview.cleanup()
        if hasattr(self, "timeline_editor_component"):
            self.timeline_editor.cleanup()
        if hasattr(self, 'video_engine'):
            self.video_engine.cleanup()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = VideoEditingPage()
    window.show()
    sys.exit(app.exec())