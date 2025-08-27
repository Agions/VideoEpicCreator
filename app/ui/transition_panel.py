#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSlider, QCheckBox, QGridLayout, QGroupBox,
    QProgressBar, QListWidget, QListWidgetItem, QFileDialog,
    QFrame, QScrollArea, QSpinBox, QRadioButton, QButtonGroup,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QIcon

import time
import os
import random
import math

class WaveformVisualizer(QWidget):
    """音频波形可视化组件"""
    
    selection_changed = pyqtSignal(int, int)  # 开始时间，结束时间
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform_data = []  # 波形数据
        self.beats = []          # 节拍点数据
        self.duration = 0        # 总时长(毫秒)
        self.selection_start = 0 # 选择开始位置
        self.selection_end = 0   # 选择结束位置
        self.drag_mode = 0       # 0:无拖拽 1:拖拽开始 2:拖拽结束
        self.setMinimumHeight(80)
        self.setMouseTracking(True)
    
    def set_waveform(self, data, beats, duration):
        """设置波形数据"""
        self.waveform_data = data
        self.beats = beats
        self.duration = duration
        self.selection_start = 0
        self.selection_end = 0
        self.update()
    
    def set_selection(self, start, end):
        """设置选择区域"""
        self.selection_start = max(0, min(start, self.duration))
        self.selection_end = max(0, min(end, self.duration))
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        if not self.waveform_data or self.duration == 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制背景
        painter.fillRect(0, 0, width, height, QColor("#1e1e1e"))
        
        # 绘制波形
        painter.setPen(QPen(QColor("#4a9eff"), 1))
        
        # 计算采样率，保证波形数据能够完整显示
        sample_rate = len(self.waveform_data) / width
        if sample_rate < 1:
            sample_rate = 1
        
        for i in range(width):
            # 计算当前位置对应的波形数据索引范围
            start_idx = int(i * sample_rate)
            end_idx = int((i + 1) * sample_rate)
            
            # 确保索引在范围内
            end_idx = min(end_idx, len(self.waveform_data) - 1)
            
            # 获取该范围内的最大振幅
            if start_idx <= end_idx:
                amplitude = max(self.waveform_data[start_idx:end_idx+1])
            else:
                amplitude = 0
                
            # 将振幅映射到像素高度
            y = int(height / 2 * (1 - amplitude))
            
            # 绘制波形线
            painter.drawLine(i, height // 2, i, y)
            painter.drawLine(i, height // 2, i, height - y)
        
        # 绘制节拍点
        painter.setPen(QPen(QColor("#ff6b6b"), 2))
        for beat in self.beats:
            x = int(beat / self.duration * width)
            painter.drawLine(x, 0, x, height)
        
        # 绘制选择区域
        if self.selection_end > self.selection_start:
            start_x = int(self.selection_start / self.duration * width)
            end_x = int(self.selection_end / self.duration * width)
            
            # 绘制半透明选择区域
            painter.fillRect(start_x, 0, end_x - start_x, height, QColor(74, 158, 255, 80))
            
            # 绘制选择边界
            painter.setPen(QPen(QColor("#4a9eff"), 2))
            painter.drawLine(start_x, 0, start_x, height)
            painter.drawLine(end_x, 0, end_x, height)
            
            # 绘制开始和结束时间
            start_time = self._format_time(self.selection_start)
            end_time = self._format_time(self.selection_end)
            
            painter.setPen(QColor("#ffffff"))
            painter.drawText(start_x + 4, 15, start_time)
            painter.drawText(end_x - 60, 15, end_time)
    
    def _format_time(self, time_ms):
        """格式化时间为分:秒.毫秒格式"""
        total_seconds = time_ms / 1000
        minutes = int(total_seconds / 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - int(total_seconds)) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self.waveform_data or self.duration == 0:
            return
        
        pos_time = int(event.position().x() / self.width() * self.duration)
        
        # 检查是否点击边界
        start_x = int(self.selection_start / self.duration * self.width())
        end_x = int(self.selection_end / self.duration * self.width())
        
        if abs(event.position().x() - start_x) < 5:
            # 拖拽开始位置
            self.drag_mode = 1
        elif abs(event.position().x() - end_x) < 5:
            # 拖拽结束位置
            self.drag_mode = 2
        else:
            # 新建选择
            self.selection_start = pos_time
            self.selection_end = pos_time
            self.drag_mode = 2  # 默认拖拽结束位置
            self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.waveform_data or self.duration ==.0 or self.drag_mode == 0:
            return
        
        pos_time = int(event.position().x() / self.width() * self.duration)
        pos_time = max(0, min(pos_time, self.duration))
        
        if self.drag_mode == 1:
            # 拖拽开始位置
            self.selection_start = pos_time
            if self.selection_start > self.selection_end:
                self.selection_start, self.selection_end = self.selection_end, self.selection_start
                self.drag_mode = 2
        else:
            # 拖拽结束位置
            self.selection_end = pos_time
            if self.selection_end < self.selection_start:
                self.selection_start, self.selection_end = self.selection_end, self.selection_start
                self.drag_mode = 1
        
        self.update()
        self.selection_changed.emit(self.selection_start, self.selection_end)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.drag_mode = 0


class TransitionItem(QWidget):
    """转场效果项UI组件"""
    
    selected = pyqtSignal(str)  # 传递转场类型
    
    def __init__(self, transition_type, title, description, parent=None):
        super().__init__(parent)
        self.transition_type = transition_type
        self.title = title
        self.description = description
        self.is_selected = False
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 预览图
        preview_frame = QFrame()
        preview_frame.setMinimumSize(120, 80)
        preview_frame.setMaximumSize(120, 80)
        preview_frame.setFrameShape(QFrame.Shape.Box)
        preview_frame.setStyleSheet(f"background-color: #{random.randint(0, 0xffffff):06x};")
        layout.addWidget(preview_frame)
        
        # 描述
        description_label = QLabel(self.description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #888;")
        layout.addWidget(description_label)
        
        # 设定最小尺寸
        self.setMinimumSize(150, 180)
        self.setMaximumSize(150, 180)
        
        # 更新样式
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        if self.is_selected:
            self.setStyleSheet("background-color: #2a5a8a; border-radius: 5px;")
        else:
            self.setStyleSheet("background-color: #2a2a2a; border-radius: 5px;")
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.is_selected = True
        self.update_style()
        self.selected.emit(self.transition_type)
        super().mousePressEvent(event)


class TransitionPanel(QWidget):
    """智能转场面板"""
    
    status_updated = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_path = ""
        self.video_path = ""
        self.transitions = []  # 转场列表
        self.current_transition = ""  # 当前选中的转场
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # 上半部分 - 分析设置和波形显示
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # 分析设置区
        analysis_group = QGroupBox("节奏分析设置")
        analysis_layout = QGridLayout(analysis_group)
        
        # 音频源
        analysis_layout.addWidget(QLabel("音频源："), 0, 0)
        self.audio_source_combo = QComboBox()
        self.audio_source_combo.addItems(["视频音频", "背景音乐", "语音检测"])
        analysis_layout.addWidget(self.audio_source_combo, 0, 1)
        
        # 背景音乐选择按钮
        self.select_audio_button = QPushButton("选择音频文件")
        self.select_audio_button.clicked.connect(self._select_audio_file)
        analysis_layout.addWidget(self.select_audio_button, 0, 2)
        
        # 分析模式
        analysis_layout.addWidget(QLabel("分析模式："), 1, 0)
        self.analysis_mode_combo = QComboBox()
        self.analysis_mode_combo.addItems(["节拍检测", "节奏感知", "语音停顿", "混合模式"])
        analysis_layout.addWidget(self.analysis_mode_combo, 1, 1)
        
        # 灵敏度
        analysis_layout.addWidget(QLabel("灵敏度："), 1, 2)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        analysis_layout.addWidget(self.sensitivity_slider, 1, 3)
        
        # 最小间隔
        analysis_layout.addWidget(QLabel("最小间隔(秒)："), 2, 0)
        self.min_interval_spin = QSpinBox()
        self.min_interval_spin.setRange(1, 10)
        self.min_interval_spin.setValue(2)
        analysis_layout.addWidget(self.min_interval_spin, 2, 1)
        
        # AI优化
        self.ai_optimize_check = QCheckBox("使用AI优化节奏点")
        self.ai_optimize_check.setChecked(True)
        analysis_layout.addWidget(self.ai_optimize_check, 2, 2, 1, 2)
        
        top_layout.addWidget(analysis_group)
        
        # 波形显示区
        waveform_group = QGroupBox("音频波形与节拍")
        waveform_layout = QVBoxLayout(waveform_group)
        
        # 波形可视化组件
        self.waveform_visualizer = WaveformVisualizer()
        self.waveform_visualizer.selection_changed.connect(self._on_selection_changed)
        waveform_layout.addWidget(self.waveform_visualizer)
        
        # 分析按钮区
        button_layout = QHBoxLayout()
        
        self.load_video_button = QPushButton("载入视频")
        self.load_video_button.clicked.connect(self._load_video)
        button_layout.addWidget(self.load_video_button)
        
        self.analyze_button = QPushButton("开始分析")
        self.analyze_button.clicked.connect(self._analyze_rhythm)
        button_layout.addWidget(self.analyze_button)
        
        self.apply_all_button = QPushButton("应用所有转场")
        self.apply_all_button.clicked.connect(self._apply_all_transitions)
        self.apply_all_button.setEnabled(False)
        button_layout.addWidget(self.apply_all_button)
        
        waveform_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        waveform_layout.addWidget(self.progress_bar)
        
        top_layout.addWidget(waveform_group)
        
        splitter.addWidget(top_widget)
        
        # 下半部分 - 转场效果选择
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # 转场设置区
        transition_group = QGroupBox("转场效果设置")
        transition_layout = QGridLayout(transition_group)
        
        # 生成模式
        transition_layout.addWidget(QLabel("生成模式："), 0, 0)
        self.mode_buttons = QButtonGroup(self)
        
        self.auto_mode_radio = QRadioButton("智能匹配")
        self.auto_mode_radio.setChecked(True)
        self.mode_buttons.addButton(self.auto_mode_radio)
        transition_layout.addWidget(self.auto_mode_radio, 0, 1)
        
        self.manual_mode_radio = QRadioButton("手动选择")
        self.mode_buttons.addButton(self.manual_mode_radio)
        transition_layout.addWidget(self.manual_mode_radio, 0, 2)
        
        # 转场风格
        transition_layout.addWidget(QLabel("转场风格："), 1, 0)
        self.style_combo = QComboBox()
        self.style_combo.addItems(["标准", "快节奏", "平滑", "创意", "混合"])
        transition_layout.addWidget(self.style_combo, 1, 1, 1, 2)
        
        # 时长设置
        transition_layout.addWidget(QLabel("转场时长(帧)："), 2, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(15)
        transition_layout.addWidget(self.duration_spin, 2, 1, 1, 2)
        
        bottom_layout.addWidget(transition_group)
        
        # 转场效果列表
        effects_group = QGroupBox("可用转场效果")
        effects_layout = QVBoxLayout(effects_group)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建放置转场项的容器
        self.transitions_container = QWidget()
        self.transitions_layout = QHBoxLayout(self.transitions_container)
        self.transitions_layout.setSpacing(10)
        self.transitions_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 添加转场效果项
        self._populate_transitions()
        
        scroll_area.setWidget(self.transitions_container)
        effects_layout.addWidget(scroll_area)
        
        bottom_layout.addWidget(effects_group)
        
        # 预览与应用
        preview_group = QGroupBox("预览与应用")
        preview_layout = QHBoxLayout(preview_group)
        
        # 预览按钮
        self.preview_button = QPushButton("预览选中转场")
        self.preview_button.clicked.connect(self._preview_transition)
        self.preview_button.setEnabled(False)
        preview_layout.addWidget(self.preview_button)
        
        # 应用按钮
        self.apply_button = QPushButton("应用到选中区域")
        self.apply_button.clicked.connect(self._apply_transition)
        self.apply_button.setEnabled(False)
        preview_layout.addWidget(self.apply_button)
        
        # 复制选项
        self.copy_check = QCheckBox("复制到所有相似节拍点")
        self.copy_check.setChecked(True)
        preview_layout.addWidget(self.copy_check)
        
        bottom_layout.addWidget(preview_group)
        
        splitter.addWidget(bottom_widget)
        
        # 设置分割器初始大小
        splitter.setSizes([int(self.height() * 0.6), int(self.height() * 0.4)])
        
        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
    
    def _populate_transitions(self):
        """填充转场效果列表"""
        transitions_data = [
            {
                "type": "fade",
                "title": "淡入淡出",
                "description": "平滑的淡入淡出效果，适合平缓过渡"
            },
            {
                "type": "wipe_left",
                "title": "左擦除",
                "description": "从右到左的擦除效果，适合快速转换"
            },
            {
                "type": "wipe_right",
                "title": "右擦除",
                "description": "从左到右的擦除效果，适合平滑转换"
            },
            {
                "type": "wipe_up",
                "title": "上擦除",
                "description": "从下到上的擦除效果，带来上升感"
            },
            {
                "type": "wipe_down",
                "title": "下擦除",
                "description": "从上到下的擦除效果，带来下降感"
            },
            {
                "type": "zoom_in",
                "title": "缩放进入",
                "description": "缩放放大过渡，增强视觉冲击力"
            },
            {
                "type": "zoom_out",
                "title": "缩放退出",
                "description": "缩放缩小过渡，适合场景推进"
            },
            {
                "type": "rotate",
                "title": "旋转",
                "description": "旋转过渡效果，适合动感场景"
            },
            {
                "type": "blur",
                "title": "模糊",
                "description": "通过模糊实现平滑过渡"
            },
            {
                "type": "flash",
                "title": "闪白",
                "description": "闪烁过渡，适合节奏强烈的场景"
            },
            {
                "type": "pixelate",
                "title": "像素化",
                "description": "像素化过渡，适合科技感场景"
            },
            {
                "type": "slide_left",
                "title": "左滑动",
                "description": "向左滑动过渡，适合连续场景"
            }
        ]
        
        # 清空现有项
        for i in reversed(range(self.transitions_layout.count())):
            self.transitions_layout.itemAt(i).widget().setParent(None)
        
        # 添加新项
        self.transitions = []
        for data in transitions_data:
            item = TransitionItem(data["type"], data["title"], data["description"])
            item.selected.connect(self._on_transition_selected)
            self.transitions_layout.addWidget(item)
            self.transitions.append(item)
    
    def _select_audio_file(self):
        """选择音频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.aac)"
        )
        
        if file_path:
            self.audio_path = file_path
            status_text = f"已加载音频: {os.path.basename(file_path)}"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
    
    def _load_video(self):
        """加载视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.mov *.avi)"
        )
        
        if file_path:
            self.video_path = file_path
            status_text = f"已加载视频: {os.path.basename(file_path)}"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
    
    def _analyze_rhythm(self):
        """分析节奏"""
        if not self.audio_path and (self.audio_source_combo.currentText() == "背景音乐" or 
                                    self.audio_source_combo.currentText() == "自动提取"):
            status_text = "请先选择音频文件"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
            return
            
        if not self.video_path and self.audio_source_combo.currentText() == "自动提取":
            status_text = "请先加载视频文件"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
            return
            
        # 开始分析
        status_text = "正在分析音频节奏..."
        self.status_label.setText(status_text)
        self.status_updated.emit(status_text)
        
        # 显示进度
        for i in range(1, 101):
            # 模拟分析过程
            time.sleep(0.02)
            
            status_text = f"正在分析音频节奏... {i}%"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
            
            # 实际应用中应该在后台线程中处理，并通过信号更新进度
        
        # 完成分析
        status_text = "节奏分析完成，已识别15个节拍点"
        self.status_label.setText(status_text)
        self.status_updated.emit(status_text)
        
        # 生成模拟波形数据
        self._generate_demo_waveform()
    
    def _generate_demo_waveform(self):
        """生成演示用的波形数据"""
        # 模拟总时长10秒的音频
        duration = 10000  # 毫秒
        
        # 生成随机波形数据
        waveform_data = []
        for i in range(1000):  # 采样1000个点
            # 生成随机振幅，中间部分振幅大，两端振幅小
            if i < 200:
                amplitude = random.uniform(0, 0.5) * (i / 200)
            elif i > 800:
                amplitude = random.uniform(0, 0.5) * ((1000 - i) / 200)
            else:
                amplitude = random.uniform(0.2, 0.9)
            
            # 添加周期性变化，模拟音乐波形
            amplitude *= (0.7 + 0.3 * abs(math.sin(i / 30)))
            
            waveform_data.append(amplitude)
        
        # 生成节拍点
        beats = []
        beat_interval = random.uniform(300, 700)  # 平均节拍间隔(毫秒)
        
        current_time = beat_interval / 2
        while current_time < duration:
            # 添加一些随机变化，使节拍看起来更自然
            jitter = random.uniform(-beat_interval * 0.1, beat_interval * 0.1)
            beats.append(current_time + jitter)
            current_time += beat_interval
        
        # 设置波形数据
        self.waveform_visualizer.set_waveform(waveform_data, beats, duration)
    
    def _on_selection_changed(self, start, end):
        """选择区域变更回调"""
        selection_duration = (end - start) / 1000  # 转换为秒
        self.status_label.setText(f"当前选择: {selection_duration:.2f}秒")
    
    def _on_transition_selected(self, transition_type):
        """转场选中回调"""
        # 更新当前转场
        self.current_transition = transition_type
        
        # 更新选中状态
        for item in self.transitions:
            if item.transition_type != transition_type:
                item.is_selected = False
                item.update_style()
        
        # 启用预览按钮
        self.preview_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        
        self.status_label.setText(f"已选择转场: {transition_type}")
    
    def _preview_transition(self):
        """预览转场效果"""
        if not self.current_transition:
            return
        
        # 获取转场参数
        duration_frames = self.duration_spin.value()
        self.status_label.setText(f"正在预览转场效果: {self.current_transition}, {duration_frames}帧")
        
        # 弹出预览窗口
        # TODO: 实现实际的预览窗口
    
    def _apply_transition(self):
        """应用转场效果到选中区域"""
        if not self.current_transition:
            return
        
        # 获取选中区域
        start = self.waveform_visualizer.selection_start
        end = self.waveform_visualizer.selection_end
        
        if end <= start:
            self.status_label.setText("请先选择有效的转场区域")
            return
        
        # 获取转场参数
        duration_frames = self.duration_spin.value()
        copy_to_all = self.copy_check.isChecked()
        
        # 应用转场效果
        self.status_label.setText(f"已应用转场: {self.current_transition}, 时长: {duration_frames}帧")
        
        if copy_to_all:
            # 同时应用到所有节拍点
            beat_count = len(self.waveform_visualizer.beats)
            self.status_label.setText(f"已应用转场到{beat_count}个节拍点")
    
    def _apply_all_transitions(self):
        """应用所有转场"""
        # 根据节拍点自动应用转场
        beat_count = len(self.waveform_visualizer.beats)
        
        if beat_count == 0:
            self.status_label.setText("未检测到节拍点")
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.status_label.setText("正在应用智能转场...")
        
        # 模拟应用过程
        for i in range(101):
            time.sleep(0.02)  # 模拟处理时间
            self.progress_bar.setValue(i)
            if i % 20 == 0:
                self.status_label.setText(f"正在应用智能转场... {i}%")
        
        # 更新状态
        self.status_label.setText(f"已自动应用{beat_count}个转场效果")
        self.progress_bar.setVisible(False) 