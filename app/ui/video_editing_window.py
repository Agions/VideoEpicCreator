#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QLabel, QPushButton, QTabWidget,
    QGroupBox, QFormLayout, QComboBox, QSlider, QTextEdit,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction, QIcon

from app.core.project_manager import ProjectInfo
from app.core.video_manager import VideoClip
from app.config.settings_manager import SettingsManager
from app.ai import AIManager
from .components.video_player import VideoPlayer
from .components.timeline_widget import TimelineWidget
from .scene_detection_panel import SceneDetectionPanel
from .content_generation_panel import ContentGenerationPanel
from .jianying_integration_panel import JianYingIntegrationPanel


class VideoEditingWindow(QMainWindow):
    """视频编辑窗口 - 三种编辑模式的主界面"""

    def __init__(self, video: VideoClip, settings_manager: SettingsManager, ai_manager: AIManager = None, parent=None):
        super().__init__(parent)

        self.video = video
        self.settings_manager = settings_manager
        self.ai_manager = ai_manager or AIManager(settings_manager)

        # 设置窗口属性
        self.setWindowTitle(f"CineAIStudio - 编辑视频: {video.name}")
        self.setGeometry(100, 100, 1600, 900)

        # 创建UI组件
        self._create_actions()
        self._create_toolbars()
        self._create_central_widget()
        self._create_statusbar()

        # 设置编辑界面
        self._setup_editing_interface()

        # 设置样式
        self._setup_styles()

    def _create_actions(self):
        """创建动作"""
        # 文件菜单动作
        self.save_action = QAction("保存", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_project)

        self.export_action = QAction("导出", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self._export_project)

        self.export_jianying_action = QAction("导出到剪映", self)
        self.export_jianying_action.triggered.connect(self._export_to_jianying)

        # 编辑菜单动作
        self.undo_action = QAction("撤销", self)
        self.undo_action.setShortcut("Ctrl+Z")

        self.redo_action = QAction("重做", self)
        self.redo_action.setShortcut("Ctrl+Y")

        # AI功能动作
        self.generate_commentary_action = QAction("生成解说", self)
        self.generate_commentary_action.triggered.connect(self._generate_commentary)

        self.generate_compilation_action = QAction("生成混剪", self)
        self.generate_compilation_action.triggered.connect(self._generate_compilation)

        self.generate_monologue_action = QAction("生成独白", self)
        self.generate_monologue_action.triggered.connect(self._generate_monologue)

    def _create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        self.main_toolbar = QToolBar("主工具栏")
        self.addToolBar(self.main_toolbar)

        # 添加动作到工具栏
        self.main_toolbar.addAction(self.save_action)
        self.main_toolbar.addAction(self.export_action)
        self.main_toolbar.addAction(self.export_jianying_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.undo_action)
        self.main_toolbar.addAction(self.redo_action)
        self.main_toolbar.addSeparator()

        # 添加AI功能按钮
        self.main_toolbar.addAction(self.generate_commentary_action)
        self.main_toolbar.addAction(self.generate_compilation_action)
        self.main_toolbar.addAction(self.generate_monologue_action)

    def _create_central_widget(self):
        """创建中央窗口部件"""
        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 创建上下分隔面板
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.main_splitter)

        # 创建上半部分的左右分隔面板
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.top_splitter)

        # 左侧区域 - 视频播放器
        self.video_player = VideoPlayer()
        self.top_splitter.addWidget(self.video_player)

        # 右侧区域 - AI控制面板
        self.ai_control_panel = self._create_ai_control_panel()
        self.top_splitter.addWidget(self.ai_control_panel)

        # 设置顶部分隔面板的初始大小比例
        self.top_splitter.setSizes([1000, 600])

        # 下半部分 - 时间线
        self.timeline = TimelineWidget()
        self.main_splitter.addWidget(self.timeline)

        # 设置主分隔面板的初始大小比例
        self.main_splitter.setSizes([600, 300])

    def _create_ai_control_panel(self) -> QWidget:
        """创建AI控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("AI视频编辑 - 控制面板")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 创建选项卡
        self.control_tabs = QTabWidget()
        layout.addWidget(self.control_tabs)

        # 创建所有AI控制选项卡
        self._create_commentary_controls()
        self._create_compilation_controls()
        self._create_monologue_controls()

        # 通用控制选项卡
        self._create_common_controls()

        # 场景检测选项卡
        self._create_scene_detection_tab()

        # 内容生成选项卡
        self._create_content_generation_tab()

        # 剪映集成选项卡
        self._create_jianying_integration_tab()

        return panel

    def _create_commentary_controls(self):
        """创建解说控制选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 解说设置
        settings_group = QGroupBox("解说设置")
        settings_layout = QFormLayout(settings_group)

        # 解说风格
        self.commentary_style_combo = QComboBox()
        self.commentary_style_combo.addItems([
            "幽默风趣", "专业分析", "情感解读", "剧情梳理", "角色分析"
        ])
        settings_layout.addRow("解说风格:", self.commentary_style_combo)

        # 解说长度
        self.commentary_length_combo = QComboBox()
        self.commentary_length_combo.addItems(["简短", "中等", "详细"])
        settings_layout.addRow("解说长度:", self.commentary_length_combo)

        layout.addWidget(settings_group)

        # 生成控制
        generate_group = QGroupBox("生成控制")
        generate_layout = QVBoxLayout(generate_group)

        self.generate_commentary_btn = QPushButton("生成AI解说")
        self.generate_commentary_btn.clicked.connect(self._generate_commentary)
        generate_layout.addWidget(self.generate_commentary_btn)

        # 进度条
        self.commentary_progress = QProgressBar()
        self.commentary_progress.setVisible(False)
        generate_layout.addWidget(self.commentary_progress)

        layout.addWidget(generate_group)

        # 结果预览
        preview_group = QGroupBox("解说预览")
        preview_layout = QVBoxLayout(preview_group)

        self.commentary_preview = QTextEdit()
        self.commentary_preview.setPlaceholderText("AI生成的解说内容将显示在这里...")
        preview_layout.addWidget(self.commentary_preview)

        layout.addWidget(preview_group)

        layout.addStretch()
        self.control_tabs.addTab(tab, "解说生成")

    def _create_compilation_controls(self):
        """创建混剪控制选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 混剪设置
        settings_group = QGroupBox("混剪设置")
        settings_layout = QFormLayout(settings_group)

        # 混剪风格
        self.compilation_style_combo = QComboBox()
        self.compilation_style_combo.addItems([
            "高能燃向", "情感向", "搞笑向", "悬疑向", "浪漫向"
        ])
        settings_layout.addRow("混剪风格:", self.compilation_style_combo)

        # 节奏设置
        self.rhythm_slider = QSlider(Qt.Orientation.Horizontal)
        self.rhythm_slider.setRange(1, 10)
        self.rhythm_slider.setValue(5)
        settings_layout.addRow("节奏强度:", self.rhythm_slider)

        layout.addWidget(settings_group)

        # 生成控制
        generate_group = QGroupBox("生成控制")
        generate_layout = QVBoxLayout(generate_group)

        self.generate_compilation_btn = QPushButton("生成AI混剪")
        self.generate_compilation_btn.clicked.connect(self._generate_compilation)
        generate_layout.addWidget(self.generate_compilation_btn)

        # 进度条
        self.compilation_progress = QProgressBar()
        self.compilation_progress.setVisible(False)
        generate_layout.addWidget(self.compilation_progress)

        layout.addWidget(generate_group)

        layout.addStretch()
        self.control_tabs.addTab(tab, "混剪生成")

    def _create_monologue_controls(self):
        """创建独白控制选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 独白设置
        settings_group = QGroupBox("独白设置")
        settings_layout = QFormLayout(settings_group)

        # 角色视角
        self.character_combo = QComboBox()
        self.character_combo.addItems([
            "主角视角", "配角视角", "旁观者视角", "反派视角"
        ])
        settings_layout.addRow("角色视角:", self.character_combo)

        # 情感基调
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems([
            "平静叙述", "激动兴奋", "忧郁沉思", "愤怒控诉", "温暖回忆"
        ])
        settings_layout.addRow("情感基调:", self.emotion_combo)

        layout.addWidget(settings_group)

        # 生成控制
        generate_group = QGroupBox("生成控制")
        generate_layout = QVBoxLayout(generate_group)

        self.generate_monologue_btn = QPushButton("生成AI独白")
        self.generate_monologue_btn.clicked.connect(self._generate_monologue)
        generate_layout.addWidget(self.generate_monologue_btn)

        # 进度条
        self.monologue_progress = QProgressBar()
        self.monologue_progress.setVisible(False)
        generate_layout.addWidget(self.monologue_progress)

        layout.addWidget(generate_group)

        # 结果预览
        preview_group = QGroupBox("独白预览")
        preview_layout = QVBoxLayout(preview_group)

        self.monologue_preview = QTextEdit()
        self.monologue_preview.setPlaceholderText("AI生成的独白内容将显示在这里...")
        preview_layout.addWidget(self.monologue_preview)

        layout.addWidget(preview_group)

        layout.addStretch()
        self.control_tabs.addTab(tab, "独白生成")

    def _create_common_controls(self):
        """创建通用控制选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 场景检测
        scene_group = QGroupBox("智能场景检测")
        scene_layout = QVBoxLayout(scene_group)

        self.detect_scenes_btn = QPushButton("检测精彩场景")
        self.detect_scenes_btn.clicked.connect(self._detect_scenes)
        scene_layout.addWidget(self.detect_scenes_btn)

        # 场景列表
        self.scenes_list = QTextEdit()
        self.scenes_list.setMaximumHeight(100)
        self.scenes_list.setPlaceholderText("检测到的场景将显示在这里...")
        scene_layout.addWidget(self.scenes_list)

        layout.addWidget(scene_group)

        # 语音合成
        voice_group = QGroupBox("语音合成")
        voice_layout = QFormLayout(voice_group)

        # 语音选择
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "标准女声", "标准男声", "温柔女声", "磁性男声", "童声"
        ])
        voice_layout.addRow("语音类型:", self.voice_combo)

        # 语速设置
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        voice_layout.addRow("语速:", self.speed_slider)

        layout.addWidget(voice_group)

        layout.addStretch()
        self.control_tabs.addTab(tab, "通用设置")

    def _create_scene_detection_tab(self):
        """创建场景检测选项卡"""
        self.scene_detection_panel = SceneDetectionPanel()

        # 设置当前视频
        self.scene_detection_panel.set_video(self.video)

        # 连接信号
        self.scene_detection_panel.scene_detected.connect(self._on_scene_detected)
        self.scene_detection_panel.detection_completed.connect(self._on_scene_detection_completed)

        self.control_tabs.addTab(self.scene_detection_panel, "场景检测")

    def _create_content_generation_tab(self):
        """创建内容生成选项卡"""
        self.content_generation_panel = ContentGenerationPanel(self.ai_manager)

        # 设置当前视频
        self.content_generation_panel.set_video(self.video)

        # 连接信号
        self.content_generation_panel.content_generated.connect(self._on_content_generated)

        self.control_tabs.addTab(self.content_generation_panel, "内容生成")

    def _create_jianying_integration_tab(self):
        """创建剪映集成选项卡"""
        self.jianying_integration_panel = JianYingIntegrationPanel()

        # 设置当前视频
        self.jianying_integration_panel.set_video(self.video)

        # 连接信号
        self.jianying_integration_panel.project_exported.connect(self._on_jianying_project_exported)

        # 如果有AI内容，也设置给剪映面板
        if hasattr(self, 'current_ai_content'):
            self.jianying_integration_panel.set_ai_content(self.current_ai_content)

        self.control_tabs.addTab(self.jianying_integration_panel, "剪映集成")

    def _create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)

        # 视频信息
        video_info = f"视频: {self.video.name} | 时长: {self._format_duration(self.video.duration)}"
        self.video_info_label = QLabel(video_info)
        self.statusbar.addPermanentWidget(self.video_info_label)

    def _setup_editing_interface(self):
        """设置编辑界面"""
        # 加载视频到播放器
        if self.video.file_path and os.path.exists(self.video.file_path):
            # 这里可以加载视频到播放器
            pass

    def _format_duration(self, duration: float) -> str:
        """格式化时长显示"""
        if duration <= 0:
            return "未知"

        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _setup_styles(self):
        """设置样式"""
        # 加载样式表
        try:
            style_path = "resources/styles/style.qss"
            if os.path.exists(style_path):
                with open(style_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"加载样式失败: {e}")

    # AI功能方法
    def _generate_commentary(self):
        """生成AI解说"""
        self.status_label.setText("正在生成AI解说...")
        self.generate_commentary_btn.setEnabled(False)
        self.commentary_progress.setVisible(True)
        self.commentary_progress.setRange(0, 0)  # 无限进度条

        # 异步调用AI生成
        asyncio.create_task(self._generate_commentary_async())

    def _generate_compilation(self):
        """生成AI混剪"""
        self.status_label.setText("正在生成AI混剪...")
        self.generate_compilation_btn.setEnabled(False)
        self.compilation_progress.setVisible(True)
        self.compilation_progress.setRange(0, 0)  # 无限进度条

        # 异步调用AI生成
        asyncio.create_task(self._generate_compilation_async())

    def _generate_monologue(self):
        """生成AI独白"""
        self.status_label.setText("正在生成AI独白...")
        self.generate_monologue_btn.setEnabled(False)
        self.monologue_progress.setVisible(True)
        self.monologue_progress.setRange(0, 0)  # 无限进度条

        # 异步调用AI生成
        asyncio.create_task(self._generate_monologue_async())

    async def _generate_commentary_async(self):
        """异步生成AI解说"""
        try:
            # 准备视频信息
            video_info = {
                "duration": "未知",
                "scenes": "短剧场景",
                "characters": "主要角色",
                "plot": "剧情概要"
            }

            # 获取解说风格
            style = self.commentary_style_combo.currentText()

            # 调用AI生成解说
            response = await self.ai_manager.generate_commentary(video_info, style)

            # 更新UI（需要在主线程中执行）
            QTimer.singleShot(0, lambda: self._on_commentary_generated(response))

        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_ai_error(f"生成解说失败: {str(e)}"))

    async def _generate_compilation_async(self):
        """异步生成AI混剪"""
        try:
            # 准备视频信息
            video_info = {
                "duration": "未知",
                "scenes": "短剧场景",
                "characters": "主要角色",
                "plot": "剧情概要"
            }

            # 获取混剪风格
            style = self.compilation_style_combo.currentText()

            # 调用AI生成混剪方案
            prompt = f"请为短剧视频生成{style}的混剪方案，包括剪辑点、转场效果和节奏控制建议。"
            response = await self.ai_manager.generate_text(prompt)

            # 更新UI
            QTimer.singleShot(0, lambda: self._on_compilation_generated(response))

        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_ai_error(f"生成混剪失败: {str(e)}"))

    async def _generate_monologue_async(self):
        """异步生成AI独白"""
        try:
            # 准备视频信息
            video_info = {
                "duration": "未知",
                "scenes": "短剧场景",
                "characters": "主要角色",
                "plot": "剧情概要"
            }

            # 获取角色和情感设置
            character = self.character_combo.currentText()
            emotion = self.emotion_combo.currentText()

            # 调用AI生成独白
            response = await self.ai_manager.generate_monologue(video_info, character, emotion)

            # 更新UI
            QTimer.singleShot(0, lambda: self._on_monologue_generated(response))

        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_ai_error(f"生成独白失败: {str(e)}"))

    def _on_commentary_generated(self, response):
        """解说生成完成回调"""
        self.generate_commentary_btn.setEnabled(True)
        self.commentary_progress.setVisible(False)

        if response.success:
            self.commentary_preview.setPlainText(response.content)
            self.status_label.setText("AI解说生成完成")
        else:
            self.status_label.setText(f"解说生成失败: {response.error_message}")
            QMessageBox.warning(self, "生成失败", response.error_message)

    def _on_compilation_generated(self, response):
        """混剪生成完成回调"""
        self.generate_compilation_btn.setEnabled(True)
        self.compilation_progress.setVisible(False)

        if response.success:
            self.status_label.setText("AI混剪方案生成完成")
            # 这里可以进一步处理混剪方案
            QMessageBox.information(self, "生成完成", "混剪方案已生成，请查看时间线")
        else:
            self.status_label.setText(f"混剪生成失败: {response.error_message}")
            QMessageBox.warning(self, "生成失败", response.error_message)

    def _on_monologue_generated(self, response):
        """独白生成完成回调"""
        self.generate_monologue_btn.setEnabled(True)
        self.monologue_progress.setVisible(False)

        if response.success:
            self.monologue_preview.setPlainText(response.content)
            self.status_label.setText("AI独白生成完成")
        else:
            self.status_label.setText(f"独白生成失败: {response.error_message}")
            QMessageBox.warning(self, "生成失败", response.error_message)

    def _on_ai_error(self, error_message: str):
        """AI错误处理"""
        # 重置所有按钮和进度条
        self.generate_commentary_btn.setEnabled(True)
        self.generate_compilation_btn.setEnabled(True)
        self.generate_monologue_btn.setEnabled(True)

        self.commentary_progress.setVisible(False)
        self.compilation_progress.setVisible(False)
        self.monologue_progress.setVisible(False)

        self.status_label.setText(error_message)
        QMessageBox.critical(self, "AI错误", error_message)

    def _on_scene_detected(self, scene):
        """场景检测回调"""
        self.status_label.setText(f"检测到场景: {scene.description}")

    def _on_scene_detection_completed(self, scenes):
        """场景检测完成回调"""
        self.status_label.setText(f"场景检测完成，共检测到 {len(scenes)} 个场景")

    def _on_content_generated(self, content):
        """内容生成完成回调"""
        self.status_label.setText(f"内容生成完成，模式: {content.editing_mode}，片段数: {len(content.segments)}")

        # 保存AI内容并传递给剪映集成面板
        self.current_ai_content = content
        if hasattr(self, 'jianying_integration_panel'):
            self.jianying_integration_panel.set_ai_content(content)

    def _on_jianying_project_exported(self, project_path: str):
        """剪映项目导出完成回调"""
        self.status_label.setText(f"剪映项目已导出到: {project_path}")

    def _detect_scenes(self):
        """检测精彩场景"""
        self.status_label.setText("正在检测精彩场景...")
        # TODO: 实现场景检测
        QTimer.singleShot(1500, lambda: self.status_label.setText("场景检测完成"))

    # 项目操作方法
    def _save_project(self):
        """保存项目"""
        # TODO: 实现项目保存
        self.status_label.setText("项目已保存")

    def _export_project(self):
        """导出项目"""
        # TODO: 实现项目导出
        QMessageBox.information(self, "导出", "项目导出功能正在开发中...")

    def _export_to_jianying(self):
        """导出到剪映"""
        # TODO: 实现剪映导出
        QMessageBox.information(self, "导出到剪映", "剪映导出功能正在开发中...")

    def closeEvent(self, event):
        """关闭事件"""
        # 检查是否有未保存的更改
        reply = QMessageBox.question(
            self, "确认关闭",
            "确定要关闭编辑窗口吗？未保存的更改将丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
