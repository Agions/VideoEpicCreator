#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI视频处理面板 - 提供智能视频处理功能的用户界面
集成AI场景分析、自动剪辑、智能优化等功能
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QProgressBar, QGroupBox, QTabWidget,
    QSplitter, QScrollArea, QFrame, QToolButton, QMessageBox,
    QDialog, QFileDialog, QListWidget, QListWidgetItem, QSlider
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui import QIcon, QFont, QPixmap

from ..core.intelligent_video_processing_engine import (
    IntelligentVideoProcessingEngine, AIProcessingConfig, AIProcessingMode,
    AIProcessingTask, AISceneType, AISceneAnalysis, AIEditDecision
)
from ..core.service_container import get_service
from ..ai.interfaces import IAIService

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """处理状态"""
    IDLE = "空闲"
    ANALYZING = "分析中"
    PROCESSING = "处理中"
    COMPLETED = "完成"
    FAILED = "失败"
    CANCELLED = "已取消"


@dataclass
class ProcessingJob:
    """处理任务"""
    job_id: str
    input_path: str
    output_path: str
    config: AIProcessingConfig
    status: ProcessingStatus = ProcessingStatus.IDLE
    progress: float = 0.0
    message: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    scene_analysis: List[AISceneAnalysis] = field(default_factory=list)
    edit_decisions: List[AIEditDecision] = field(default_factory=list)


class AISceneAnalysisWidget(QWidget):
    """AI场景分析组件"""

    scene_selected = pyqtSignal(object)  # 场景选中信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_scenes: List[AISceneAnalysis] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 场景列表
        self.scene_list = QListWidget()
        self.scene_list.itemClicked.connect(self._on_scene_selected)
        layout.addWidget(QLabel("场景列表:"))
        layout.addWidget(self.scene_list)

        # 场景详情
        details_group = QGroupBox("场景详情")
        details_layout = QFormLayout(details_group)

        self.scene_type_label = QLabel("-")
        self.confidence_label = QLabel("-")
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(100)
        self.quality_label = QLabel("-")
        self.action_label = QLabel("-")
        self.lighting_label = QLabel("-")

        details_layout.addRow("场景类型:", self.scene_type_label)
        details_layout.addRow("置信度:", self.confidence_label)
        details_layout.addRow("描述:", self.description_text)
        details_layout.addRow("质量评分:", self.quality_label)
        details_layout.addRow("动作强度:", self.action_label)
        details_layout.addRow("光线条件:", self.lighting_label)

        layout.addWidget(details_group)

    def update_scenes(self, scenes: List[AISceneAnalysis]):
        """更新场景列表"""
        self.current_scenes = scenes
        self.scene_list.clear()

        for scene in scenes:
            time_str = f"{scene.timestamp:.1f}s - {scene.timestamp + scene.duration:.1f}s"
            item_text = f"{time_str} | {scene.scene_type.value} | 置信度: {scene.confidence:.2f}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, scene)

            # 根据质量设置颜色
            if scene.quality_score > 0.8:
                item.setBackground(Qt.GlobalColor.green)
            elif scene.quality_score > 0.6:
                item.setBackground(Qt.GlobalColor.yellow)
            else:
                item.setBackground(Qt.GlobalColor.red)

            self.scene_list.addItem(item)

    def _on_scene_selected(self, item: QListWidgetItem):
        """场景选中事件"""
        scene = item.data(Qt.ItemDataRole.UserRole)
        if scene:
            self._display_scene_details(scene)
            self.scene_selected.emit(scene)

    def _display_scene_details(self, scene: AISceneAnalysis):
        """显示场景详情"""
        self.scene_type_label.setText(scene.scene_type.value)
        self.confidence_label.setText(f"{scene.confidence:.2f}")
        self.description_text.setText(scene.description)
        self.quality_label.setText(f"{scene.quality_score:.2f}")
        self.action_label.setText(f"{scene.action_intensity:.2f}")
        self.lighting_label.setText(scene.lighting_condition)


class AIEditDecisionWidget(QWidget):
    """AI剪辑决策组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_decisions: List[AIEditDecision] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 决策列表
        self.decision_list = QListWidget()
        layout.addWidget(QLabel("剪辑建议:"))
        layout.addWidget(self.decision_list)

        # 决策详情
        details_group = QGroupBox("决策详情")
        details_layout = QFormLayout(details_group)

        self.decision_type_label = QLabel("-")
        self.confidence_label = QLabel("-")
        self.reason_label = QLabel("-")
        self.duration_label = QLabel("-")
        self.transition_label = QLabel("-")

        details_layout.addRow("决策类型:", self.decision_type_label)
        details_layout.addRow("置信度:", self.confidence_label)
        details_layout.addRow("原因:", self.reason_label)
        details_layout.addRow("建议时长:", self.duration_label)
        details_layout.addRow("建议转场:", self.transition_label)

        layout.addWidget(details_group)

    def update_decisions(self, decisions: List[AIEditDecision]):
        """更新剪辑决策"""
        self.current_decisions = decisions
        self.decision_list.clear()

        for decision in decisions:
            time_str = f"{decision.timestamp:.1f}s"
            item_text = f"{time_str} | {decision.decision_type} | 置信度: {decision.confidence:.2f}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, decision)

            # 根据决策类型设置颜色
            if decision.decision_type == "highlight":
                item.setBackground(Qt.GlobalColor.green)
            elif decision.decision_type == "remove":
                item.setBackground(Qt.GlobalColor.red)
            else:
                item.setBackground(Qt.GlobalColor.blue)

            self.decision_list.addItem(item)

    def _on_decision_selected(self, item: QListWidgetItem):
        """决策选中事件"""
        decision = item.data(Qt.ItemDataRole.UserRole)
        if decision:
            self._display_decision_details(decision)

    def _display_decision_details(self, decision: AIEditDecision):
        """显示决策详情"""
        self.decision_type_label.setText(decision.decision_type)
        self.confidence_label.setText(f"{decision.confidence:.2f}")
        self.reason_label.setText(decision.reason)
        self.duration_label.setText(f"{decision.suggested_duration:.1f}s")
        self.transition_label.setText(decision.suggested_transition)


class AIVideoProcessingPanel(QWidget):
    """AI视频处理面板"""

    processing_started = pyqtSignal(str)    # 处理开始信号
    processing_progress = pyqtSignal(str, float, str)  # 处理进度信号
    processing_completed = pyqtSignal(str, object)  # 处理完成信号
    processing_failed = pyqtSignal(str, str)  # 处理失败信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_engine: Optional[IntelligentVideoProcessingEngine] = None
        self.ai_service: Optional[IAIService] = None
        self.current_job: Optional[ProcessingJob] = None
        self.processing_jobs: List[ProcessingJob] = []

        self._init_ui()
        self._init_services()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 主标签页
        main_tabs = QTabWidget()
        layout.addWidget(main_tabs)

        # 基本设置标签页
        basic_tab = self._create_basic_settings_tab()
        main_tabs.addTab(basic_tab, "基本设置")

        # 高级设置标签页
        advanced_tab = self._create_advanced_settings_tab()
        main_tabs.addTab(advanced_tab, "高级设置")

        # 预览标签页
        preview_tab = self._create_preview_tab()
        main_tabs.addTab(preview_tab, "处理预览")

        # 结果标签页
        results_tab = self._create_results_tab()
        main_tabs.addTab(results_tab, "分析结果")

        # 控制按钮
        control_layout = QHBoxLayout()

        self.preview_button = QPushButton("预览效果")
        self.preview_button.clicked.connect(self._preview_processing)
        control_layout.addWidget(self.preview_button)

        self.start_button = QPushButton("开始处理")
        self.start_button.clicked.connect(self._start_processing)
        control_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("取消处理")
        self.cancel_button.clicked.connect(self._cancel_processing)
        self.cancel_button.setEnabled(False)
        control_layout.addWidget(self.cancel_button)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(QLabel("进度:"))
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # 设置定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # 每秒更新一次

    def _create_basic_settings_tab(self) -> QWidget:
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 文件选择
        file_group = QGroupBox("文件设置")
        file_layout = QFormLayout(file_group)

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("选择输入视频文件")
        self.input_browse_button = QPushButton("浏览...")
        self.input_browse_button.clicked.connect(self._browse_input_file)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_button)
        file_layout.addRow("输入文件:", input_layout)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出视频文件")
        self.output_browse_button = QPushButton("浏览...")
        self.output_browse_button.clicked.connect(self._browse_output_file)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_button)
        file_layout.addRow("输出文件:", output_layout)

        layout.addWidget(file_group)

        # 处理模式
        mode_group = QGroupBox("处理模式")
        mode_layout = QFormLayout(mode_group)

        self.mode_combo = QComboBox()
        for mode in AIProcessingMode:
            self.mode_combo.addItem(mode.value, mode)
        self.mode_combo.setCurrentText(AIProcessingMode.SMART_OPTIMIZATION.value)
        mode_layout.addRow("AI处理模式:", self.mode_combo)

        layout.addWidget(mode_group)

        # 功能开关
        features_group = QGroupBox("功能开关")
        features_layout = QVBoxLayout(features_group)

        self.enable_scene_analysis = QCheckBox("启用场景分析")
        self.enable_scene_analysis.setChecked(True)
        features_layout.addWidget(self.enable_scene_analysis)

        self.enable_auto_editing = QCheckBox("启用自动剪辑")
        self.enable_auto_editing.setChecked(True)
        features_layout.addWidget(self.enable_auto_editing)

        self.enable_content_optimization = QCheckBox("启用内容优化")
        self.enable_content_optimization.setChecked(True)
        features_layout.addWidget(self.enable_content_optimization)

        self.enable_quality_enhancement = QCheckBox("启用质量增强")
        self.enable_quality_enhancement.setChecked(True)
        features_layout.addWidget(self.enable_quality_enhancement)

        layout.addWidget(features_group)

        layout.addStretch()

        return widget

    def _create_advanced_settings_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 分析参数
        analysis_group = QGroupBox("分析参数")
        analysis_layout = QFormLayout(analysis_group)

        self.analysis_interval_spin = QDoubleSpinBox()
        self.analysis_interval_spin.setRange(1.0, 30.0)
        self.analysis_interval_spin.setValue(5.0)
        self.analysis_interval_spin.setSuffix(" 秒")
        analysis_layout.addRow("分析间隔:", self.analysis_interval_spin)

        self.min_scene_duration_spin = QDoubleSpinBox()
        self.min_scene_duration_spin.setRange(0.5, 10.0)
        self.min_scene_duration_spin.setValue(2.0)
        self.min_scene_duration_spin.setSuffix(" 秒")
        analysis_layout.addRow("最小场景时长:", self.min_scene_duration_spin)

        self.confidence_threshold_spin = QDoubleSpinBox()
        self.confidence_threshold_spin.setRange(0.1, 1.0)
        self.confidence_threshold_spin.setValue(0.7)
        self.confidence_threshold_spin.setSingleStep(0.05)
        analysis_layout.addRow("置信度阈值:", self.confidence_threshold_spin)

        layout.addWidget(analysis_group)

        # 输出选项
        output_group = QGroupBox("输出选项")
        output_layout = QVBoxLayout(output_group)

        self.generate_edit_suggestions = QCheckBox("生成剪辑建议")
        self.generate_edit_suggestions.setChecked(True)
        output_layout.addWidget(self.generate_edit_suggestions)

        self.generate_scene_markers = QCheckBox("生成场景标记")
        self.generate_scene_markers.setChecked(True)
        output_layout.addWidget(self.generate_scene_markers)

        self.generate_quality_report = QCheckBox("生成质量报告")
        self.generate_quality_report.setChecked(True)
        output_layout.addWidget(self.generate_quality_report)

        layout.addWidget(output_group)

        # 模型选择
        model_group = QGroupBox("AI模型选择")
        model_layout = QFormLayout(model_group)

        self.scene_analysis_model = QComboBox()
        self.scene_analysis_model.addItems(["default", "vision-large", "vision-base"])
        self.scene_analysis_model.setCurrentText("default")
        model_layout.addRow("场景分析模型:", self.scene_analysis_model)

        self.content_analysis_model = QComboBox()
        self.content_analysis_model.addItems(["default", "gpt-4", "gpt-3.5"])
        self.content_analysis_model.setCurrentText("default")
        model_layout.addRow("内容分析模型:", self.content_analysis_model)

        self.editing_assistant_model = QComboBox()
        self.editing_assistant_model.addItems(["default", "claude-3", "gpt-4"])
        self.editing_assistant_model.setCurrentText("default")
        model_layout.addRow("剪辑助手模型:", self.editing_assistant_model)

        layout.addWidget(model_group)

        layout.addStretch()

        return widget

    def _create_preview_tab(self) -> QWidget:
        """创建预览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预览信息
        self.preview_info = QTextEdit()
        self.preview_info.setReadOnly(True)
        self.preview_info.setPlaceholderText("点击"预览效果"按钮查看AI处理预览...")
        layout.addWidget(QLabel("处理预览:"))
        layout.addWidget(self.preview_info)

        return widget

    def _create_results_tab(self) -> QWidget:
        """创建结果标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 场景分析
        self.scene_widget = AISceneAnalysisWidget()
        splitter.addWidget(self.scene_widget)

        # 剪辑决策
        self.decision_widget = AIEditDecisionWidget()
        splitter.addWidget(self.decision_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(QLabel("AI分析结果:"))
        layout.addWidget(splitter)

        return widget

    def _init_services(self):
        """初始化服务"""
        try:
            # 获取智能视频处理引擎
            self.processing_engine = get_service(IntelligentVideoProcessingEngine)

            # 获取AI服务
            self.ai_service = get_service(IAIService)

            # 连接AI服务到视频处理引擎
            if self.processing_engine and self.ai_service:
                self.processing_engine.set_ai_service(self.ai_service)

            logger.info("AI视频处理服务初始化成功")

        except Exception as e:
            logger.error(f"初始化AI视频处理服务失败: {e}")
            QMessageBox.warning(self, "服务初始化失败", f"无法初始化AI服务: {e}")

    def _load_settings(self):
        """加载设置"""
        settings = QSettings("Agions", "CineAIStudio")

        # 加载文件路径
        last_input_dir = settings.value("ai_video/last_input_dir", "")
        last_output_dir = settings.value("ai_video/last_output_dir", "")

        if last_input_dir:
            self.input_path_edit.setText(last_input_dir)
        if last_output_dir:
            self.output_path_edit.setText(last_output_dir)

    def _save_settings(self):
        """保存设置"""
        settings = QSettings("Agions", "CineAIStudio")

        # 保存文件路径
        settings.setValue("ai_video/last_input_dir", self.input_path_edit.text())
        settings.setValue("ai_video/last_output_dir", self.output_path_edit.text())

    def _browse_input_file(self):
        """浏览输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择输入视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv);;所有文件 (*)"
        )

        if file_path:
            self.input_path_edit.setText(file_path)

            # 自动生成输出路径
            if not self.output_path_edit.text():
                input_path = Path(file_path)
                output_path = input_path.parent / f"{input_path.stem}_ai_processed{input_path.suffix}"
                self.output_path_edit.setText(str(output_path))

    def _browse_output_file(self):
        """浏览输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm);;所有文件 (*)"
        )

        if file_path:
            self.output_path_edit.setText(file_path)

    def _create_processing_config(self) -> AIProcessingConfig:
        """创建处理配置"""
        return AIProcessingConfig(
            processing_mode=self.mode_combo.currentData(),
            enable_scene_analysis=self.enable_scene_analysis.isChecked(),
            enable_auto_editing=self.enable_auto_editing.isChecked(),
            enable_content_optimization=self.enable_content_optimization.isChecked(),
            enable_quality_enhancement=self.enable_quality_enhancement.isChecked(),

            analysis_interval=self.analysis_interval_spin.value(),
            min_scene_duration=self.min_scene_duration_spin.value(),
            confidence_threshold=self.confidence_threshold_spin.value(),

            generate_edit_suggestions=self.generate_edit_suggestions.isChecked(),
            generate_scene_markers=self.generate_scene_markers.isChecked(),
            generate_quality_report=self.generate_quality_report.isChecked(),

            scene_analysis_model=self.scene_analysis_model.currentText(),
            content_analysis_model=self.content_analysis_model.currentText(),
            editing_assistant_model=self.editing_assistant_model.currentText()
        )

    def _preview_processing(self):
        """预览处理效果"""
        if not self._validate_inputs():
            return

        try:
            input_path = self.input_path_edit.text()
            config = self._create_processing_config()

            if not self.processing_engine:
                QMessageBox.warning(self, "服务不可用", "智能视频处理引擎未初始化")
                return

            # 显示预览信息
            self.preview_info.clear()
            self.preview_info.append("正在分析视频...")

            # 获取预览结果
            preview_result = self.processing_engine.preview_ai_processing(input_path, config)

            # 显示预览信息
            self._display_preview_info(preview_result)

        except Exception as e:
            logger.error(f"预览处理失败: {e}")
            QMessageBox.critical(self, "预览失败", f"预览处理失败: {e}")

    def _display_preview_info(self, preview_result: Dict[str, Any]):
        """显示预览信息"""
        self.preview_info.clear()

        if "error" in preview_result:
            self.preview_info.append(f"❌ 预览失败: {preview_result['error']}")
            return

        self.preview_info.append("🎬 AI视频处理预览\n")
        self.preview_info.append(f"⏱️  预估处理时间: {preview_result.get('estimated_processing_time', 0):.1f} 秒")
        self.preview_info.append(f"🎭 场景数量: {preview_result.get('scene_count', 0)}")
        self.preview_info.append(f"🏷️  主导场景类型: {preview_result.get('dominant_scene_type', '未知')}")
        self.preview_info.append(f"📈 预估质量改进: {preview_result.get('estimated_quality_improvement', 0):.2f}")
        self.preview_info.append(f"✂️  建议剪辑点: {preview_result.get('suggested_edit_points', 0)}")
        self.preview_info.append(f"⚙️  处理模式: {preview_result.get('processing_mode', '未知')}")

    def _start_processing(self):
        """开始处理"""
        if not self._validate_inputs():
            return

        try:
            input_path = self.input_path_edit.text()
            output_path = self.output_path_edit.text()
            config = self._create_processing_config()

            if not self.processing_engine:
                QMessageBox.warning(self, "服务不可用", "智能视频处理引擎未初始化")
                return

            # 创建处理任务
            import uuid
            task_id = str(uuid.uuid4())

            task = AIProcessingTask(
                task_id=task_id,
                input_path=input_path,
                output_path=output_path,
                config=config,
                progress_callback=self._on_progress,
                scene_analysis_callback=self._on_scene_analysis,
                edit_decision_callback=self._on_edit_decision,
                completion_callback=self._on_completion,
                error_callback=self._on_error
            )

            # 创建任务记录
            self.current_job = ProcessingJob(
                job_id=task_id,
                input_path=input_path,
                output_path=output_path,
                config=config
            )

            # 提交任务
            self.processing_engine.add_ai_processing_task(task)

            # 更新UI状态
            self._set_processing_state(True)
            self.processing_started.emit(task_id)

            self.status_label.setText("处理中...")
            self.progress_bar.setValue(0)

            # 保存设置
            self._save_settings()

            logger.info(f"AI视频处理任务已启动: {task_id}")

        except Exception as e:
            logger.error(f"启动处理失败: {e}")
            QMessageBox.critical(self, "启动失败", f"启动AI视频处理失败: {e}")

    def _cancel_processing(self):
        """取消处理"""
        if self.current_job and self.processing_engine:
            try:
                success = self.processing_engine.cancel_ai_processing(self.current_job.job_id)

                if success:
                    self.current_job.status = ProcessingStatus.CANCELLED
                    self._set_processing_state(False)
                    self.status_label.setText("已取消")
                    self.processing_failed.emit(self.current_job.job_id, "用户取消")

                    logger.info("AI视频处理已取消")
                else:
                    QMessageBox.warning(self, "取消失败", "无法取消处理任务")

            except Exception as e:
                logger.error(f"取消处理失败: {e}")
                QMessageBox.critical(self, "取消失败", f"取消处理失败: {e}")

    def _validate_inputs(self) -> bool:
        """验证输入"""
        input_path = self.input_path_edit.text().strip()
        output_path = self.output_path_edit.text().strip()

        if not input_path:
            QMessageBox.warning(self, "输入错误", "请选择输入视频文件")
            return False

        if not os.path.exists(input_path):
            QMessageBox.warning(self, "输入错误", "输入文件不存在")
            return False

        if not output_path:
            QMessageBox.warning(self, "输入错误", "请选择输出视频文件")
            return False

        # 检查输出目录是否存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.warning(self, "输出错误", f"无法创建输出目录: {e}")
                return False

        return True

    def _set_processing_state(self, is_processing: bool):
        """设置处理状态"""
        self.start_button.setEnabled(not is_processing)
        self.cancel_button.setEnabled(is_processing)
        self.preview_button.setEnabled(not is_processing)

        # 禁用设置控件
        self.input_path_edit.setEnabled(not is_processing)
        self.input_browse_button.setEnabled(not is_processing)
        self.output_path_edit.setEnabled(not is_processing)
        self.output_browse_button.setEnabled(not is_processing)

        self.mode_combo.setEnabled(not is_processing)
        self.enable_scene_analysis.setEnabled(not is_processing)
        self.enable_auto_editing.setEnabled(not is_processing)
        self.enable_content_optimization.setEnabled(not is_processing)
        self.enable_quality_enhancement.setEnabled(not is_processing)

    def _update_status(self):
        """更新状态"""
        if self.current_job and self.current_job.status in [ProcessingStatus.PROCESSING, ProcessingStatus.ANALYZING]:
            # 获取当前状态
            status = self.processing_engine.get_ai_processing_status(self.current_job.job_id)
            if status:
                self.status_label.setText(f"处理中... ({status})")

    # 回调函数
    def _on_progress(self, progress: float, message: str):
        """进度回调"""
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(message)
        self.processing_progress.emit(self.current_job.job_id, progress, message)

    def _on_scene_analysis(self, scene_analysis: List[AISceneAnalysis]):
        """场景分析回调"""
        if self.current_job:
            self.current_job.scene_analysis = scene_analysis
            self.current_job.status = ProcessingStatus.ANALYZING

            # 更新场景显示
            self.scene_widget.update_scenes(scene_analysis)

            logger.info(f"收到场景分析结果: {len(scene_analysis)} 个场景")

    def _on_edit_decision(self, edit_decisions: List[AIEditDecision]):
        """剪辑决策回调"""
        if self.current_job:
            self.current_job.edit_decisions = edit_decisions

            # 更新决策显示
            self.decision_widget.update_decisions(edit_decisions)

            logger.info(f"收到剪辑决策: {len(edit_decisions)} 个决策")

    def _on_completion(self, task: AIProcessingTask):
        """完成回调"""
        if self.current_job:
            self.current_job.status = ProcessingStatus.COMPLETED
            self.current_job.completed_at = time.time()

            self._set_processing_state(False)
            self.status_label.setText("处理完成")
            self.progress_bar.setValue(100)

            self.processing_completed.emit(self.current_job.job_id, task)

            # 显示完成消息
            QMessageBox.information(self, "处理完成",
                f"AI视频处理完成！\n\n"
                f"场景分析: {len(task.scene_analysis)} 个场景\n"
                f"剪辑建议: {len(task.edit_decisions)} 个建议\n"
                f"输出文件: {task.output_path}")

            logger.info(f"AI视频处理完成: {task.task_id}")

    def _on_error(self, error: Exception):
        """错误回调"""
        if self.current_job:
            self.current_job.status = ProcessingStatus.FAILED
            self.current_job.completed_at = time.time()

            self._set_processing_state(False)
            self.status_label.setText("处理失败")

            self.processing_failed.emit(self.current_job.job_id, str(error))

            QMessageBox.critical(self, "处理失败", f"AI视频处理失败: {error}")

            logger.error(f"AI视频处理失败: {error}")

    def get_current_job(self) -> Optional[ProcessingJob]:
        """获取当前任务"""
        return self.current_job

    def is_processing(self) -> bool:
        """是否正在处理"""
        return self.current_job and self.current_job.status in [ProcessingStatus.PROCESSING, ProcessingStatus.ANALYZING]

    def cleanup(self):
        """清理资源"""
        if self.processing_engine:
            self.processing_engine.cleanup()

        if self.update_timer:
            self.update_timer.stop()


if __name__ == "__main__":
    # 测试代码
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    panel = AIVideoProcessingPanel()
    panel.setWindowTitle("AI视频处理面板测试")
    panel.resize(800, 600)
    panel.show()

    sys.exit(app.exec())