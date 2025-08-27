#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QStyle, QSizePolicy,
    QToolButton, QFrame, QComboBox, QFileDialog,
    QGraphicsDropShadowEffect, QMenu, QListWidget,
    QDialog, QLineEdit, QDialogButtonBox, QScrollArea,
    QWidgetAction
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, pyqtSignal, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor, QImage, QKeySequence, QShortcut
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class VideoPlayer(QWidget):
    """视频播放器组件"""
    
    # 信号
    keyframeDetected = pyqtSignal(int, str)  # 检测到关键帧时发射(位置, 描述)
    markerAdded = pyqtSignal(int, str)       # 添加标记时发射(位置, 描述)
    snapshotTaken = pyqtSignal(str)          # 截图保存时发射(路径)
    clipCreated = pyqtSignal(str, int, int)  # 创建片段时发射(文件路径, 开始时间, 结束时间)
    positionChanged = pyqtSignal(int)        # 播放位置变化时发射(位置)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 连接播放器信号
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status_changed)
        self.media_player.playbackStateChanged.connect(self.handle_playback_state_changed)
        self.media_player.errorOccurred.connect(self.handle_error)
        
        # 视频处理相关
        self.video_file_path = ""
        self.video_cap = None
        self.keyframes = []
        self.keyframe_threshold = 0.6  # 关键帧检测阈值
        
        # 创建UI组件
        self.init_ui()
        
        # 设置定时器用于帧进帧退
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.go_to_next_frame)
        self.frame_step_size = 33  # 默认约为30fps (1000ms / 30 ≈ 33ms)
        
        # 初始播放速度为1.0倍速
        self.playback_speed = 1.0
        
        # 添加标记列表
        self.markers = []
        
        # 实时预览效果
        self.preview_effects = []
        self.current_effect = None
        
        # 片段选择
        self.in_point = -1
        self.out_point = -1
        
        # 快捷键设置
        self.setup_shortcuts()
        
        # 预览定时器
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.setInterval(100)  # 每100ms更新预览
    
    def init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)  # 减少空间间隔
        
        # 视频显示区域
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # 添加视频效果预览层
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setVisible(False)
        
        # 视频控制区域 - 使用简化的悬浮控制栏样式
        controls_container = QWidget()
        controls_container.setMaximumHeight(60)  # 控制高度
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(5, 2, 5, 2)
        controls_layout.setSpacing(2)
        
        # 播放进度条
        position_layout = QHBoxLayout()
        position_layout.setSpacing(2)
        
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.sliderPressed.connect(self.on_slider_pressed)
        self.position_slider.sliderReleased.connect(self.on_slider_released)
        self.position_slider.setFixedHeight(15)  # 减小滑块高度
        
        self.position_label = QLabel("00:00 / 00:00")
        self.position_label.setMinimumWidth(80)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        position_layout.addWidget(self.position_slider)
        position_layout.addWidget(self.position_label)
        
        # 播放控制按钮 - 只保留最核心的控制按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)
        
        # 核心控制按钮组
        # 播放/暂停按钮
        self.play_button = QToolButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setToolTip("播放/暂停 (空格)")
        self.play_button.clicked.connect(self.toggle_play)
        
        # 帧进/帧退按钮合并为一组
        frame_buttons = QHBoxLayout()
        frame_buttons.setSpacing(0)
        
        # 帧退按钮
        self.frame_back_button = QToolButton()
        self.frame_back_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.frame_back_button.setToolTip("帧退 (左箭头)")
        self.frame_back_button.clicked.connect(self.go_to_previous_frame)
        frame_buttons.addWidget(self.frame_back_button)
        
        # 帧进按钮
        self.frame_forward_button = QToolButton()
        self.frame_forward_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.frame_forward_button.setToolTip("帧进 (右箭头)")
        self.frame_forward_button.clicked.connect(self.go_to_next_frame)
        frame_buttons.addWidget(self.frame_forward_button)
        
        # 设置按钮大小
        for button in [self.play_button, self.frame_back_button, self.frame_forward_button]:
            button.setFixedSize(28, 28)
        
        # 音量控制按钮
        self.volume_button = QToolButton()
        self.volume_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.volume_button.setToolTip("音量控制")
        
        # 创建音量控制弹出菜单
        volume_menu = QMenu(self)
        volume_widget = QWidget()
        volume_layout = QVBoxLayout(volume_widget)
        
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)  # 默认音量50%
        self.volume_slider.setFixedHeight(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        
        volume_layout.addWidget(self.volume_slider)
        volume_widget.setLayout(volume_layout)
        
        volume_action = QWidgetAction(volume_menu)
        volume_action.setDefaultWidget(volume_widget)
        volume_menu.addAction(volume_action)
        
        self.volume_button.setMenu(volume_menu)
        self.volume_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # 更多选项按钮 (替代原来的多个功能按钮)
        self.more_options_button = QToolButton()
        self.more_options_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton))
        self.more_options_button.setToolTip("更多选项")
        self.more_options_button.clicked.connect(self.show_options_menu)
        
        # 时间线入点/出点按钮
        # 设置入点按钮
        self.set_in_button = QToolButton()
        self.set_in_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.set_in_button.setToolTip("设置入点 (I)")
        self.set_in_button.clicked.connect(self.set_in_point)
        
        # 设置出点按钮
        self.set_out_button = QToolButton()
        self.set_out_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.set_out_button.setToolTip("设置出点 (O)")
        self.set_out_button.clicked.connect(self.set_out_point)
        
        # 添加按钮到布局
        buttons_layout.addLayout(frame_buttons)
        buttons_layout.addWidget(self.play_button)
        buttons_layout.addWidget(self.set_in_button)
        buttons_layout.addWidget(self.set_out_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.volume_button)
        buttons_layout.addWidget(self.more_options_button)
        
        # 添加到控制布局
        controls_layout.addLayout(position_layout)
        controls_layout.addLayout(buttons_layout)
        
        # 创建视频信息标签
        self.info_label = QLabel("未加载视频")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("background-color: #222; color: #eee; padding: 4px; font-size: 11px;")
        self.info_label.setMaximumHeight(20)
        
        # 设置视频区域
        video_container = QVBoxLayout()
        video_container.setSpacing(0)
        video_container.addWidget(self.video_widget)
        video_container.addWidget(self.preview_label, 1)
        video_container.addWidget(self.info_label)
        
        # 确保视频和预览叠加
        video_container.setAlignment(self.preview_label, Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(self.video_widget.minimumSize())
        
        main_layout.addLayout(video_container)
        main_layout.addWidget(controls_container)
        
        # 设置视频区域和控制区域的比例
        main_layout.setStretch(0, 10)  # 视频区域占比较大
        main_layout.setStretch(1, 0)   # 控制区域占比较小
        
        # 隐藏部分控件但保留引用
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self.change_playback_speed)
        self.speed_combo.setFixedWidth(70)
        self.speed_combo.hide()
        
        # 关键帧按钮（在上下文菜单中使用）
        self.prev_keyframe_button = QToolButton()
        self.prev_keyframe_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.prev_keyframe_button.setToolTip("上一关键帧 (K+左箭头)")
        self.prev_keyframe_button.clicked.connect(self.go_to_previous_keyframe)
        self.prev_keyframe_button.hide()
        
        self.next_keyframe_button = QToolButton()
        self.next_keyframe_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.next_keyframe_button.setToolTip("下一关键帧 (K+右箭头)")
        self.next_keyframe_button.clicked.connect(self.go_to_next_keyframe)
        self.next_keyframe_button.hide()
        
        # 其他功能按钮（将在上下文菜单中使用）
        self.mark_button = QToolButton()
        self.mark_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.mark_button.setToolTip("添加标记 (M)")
        self.mark_button.clicked.connect(self.add_marker)
        self.mark_button.hide()
        
        self.snapshot_button = QToolButton()
        self.snapshot_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.snapshot_button.setToolTip("截图 (S)")
        self.snapshot_button.clicked.connect(self.take_snapshot)
        self.snapshot_button.hide()
        
        self.detect_keyframes_button = QToolButton()
        self.detect_keyframes_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.detect_keyframes_button.setToolTip("检测关键帧 (D)")
        self.detect_keyframes_button.clicked.connect(self.detect_keyframes)
        self.detect_keyframes_button.hide()
        
        self.marker_list_button = QToolButton()
        self.marker_list_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.marker_list_button.setToolTip("标记列表 (L)")
        self.marker_list_button.clicked.connect(self.show_marker_list)
        self.marker_list_button.hide()
        
        self.effect_preview_button = QToolButton()
        self.effect_preview_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton))
        self.effect_preview_button.setToolTip("效果预览 (E)")
        self.effect_preview_button.setCheckable(True)
        self.effect_preview_button.clicked.connect(self.show_effect_menu)
        self.effect_preview_button.hide()
        
        self.create_clip_button = QToolButton()
        self.create_clip_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.create_clip_button.setToolTip("创建片段 (C)")
        self.create_clip_button.clicked.connect(self.create_clip)
        self.create_clip_button.hide()
        
        # 设置初始状态
        self.change_volume(50)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 空格播放/暂停已在keyPressEvent中处理
        
        # 关键帧导航快捷键
        self.shortcut_prev_keyframe = QShortcut(QKeySequence("K+Left"), self)
        self.shortcut_prev_keyframe.activated.connect(self.go_to_previous_keyframe)
        
        self.shortcut_next_keyframe = QShortcut(QKeySequence("K+Right"), self)
        self.shortcut_next_keyframe.activated.connect(self.go_to_next_keyframe)
        
        # 标记快捷键
        self.shortcut_add_marker = QShortcut(QKeySequence("M"), self)
        self.shortcut_add_marker.activated.connect(self.add_marker)
        
        self.shortcut_marker_list = QShortcut(QKeySequence("L"), self)
        self.shortcut_marker_list.activated.connect(self.show_marker_list)
        
        # 检测关键帧快捷键
        self.shortcut_detect_keyframes = QShortcut(QKeySequence("D"), self)
        self.shortcut_detect_keyframes.activated.connect(self.detect_keyframes)
        
        # 效果预览快捷键
        self.shortcut_effect_preview = QShortcut(QKeySequence("E"), self)
        self.shortcut_effect_preview.activated.connect(self.show_effect_menu)
        
        # 调整播放速度快捷键
        self.shortcut_speed_up = QShortcut(QKeySequence("]"), self)
        self.shortcut_speed_up.activated.connect(lambda: self.adjust_speed(0.25))
        
        self.shortcut_speed_down = QShortcut(QKeySequence("["), self)
        self.shortcut_speed_down.activated.connect(lambda: self.adjust_speed(-0.25))
        
        self.shortcut_normal_speed = QShortcut(QKeySequence("\\"), self)
        self.shortcut_normal_speed.activated.connect(lambda: self.speed_combo.setCurrentText("1.0x"))
        
        # 时间线编辑快捷键
        self.shortcut_set_in = QShortcut(QKeySequence("I"), self)
        self.shortcut_set_in.activated.connect(self.set_in_point)
        
        self.shortcut_set_out = QShortcut(QKeySequence("O"), self)
        self.shortcut_set_out.activated.connect(self.set_out_point)
        
        self.shortcut_create_clip = QShortcut(QKeySequence("C"), self)
        self.shortcut_create_clip.activated.connect(self.create_clip)
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key.Key_Left:
            self.go_to_previous_frame()
        elif event.key() == Qt.Key.Key_Right:
            self.go_to_next_frame()
        elif event.key() == Qt.Key.Key_M:
            self.add_marker()
        elif event.key() == Qt.Key.Key_S:
            self.take_snapshot()
        elif event.key() == Qt.Key.Key_Up:
            self.change_volume(self.volume_slider.value() + 5)
        elif event.key() == Qt.Key.Key_Down:
            self.change_volume(self.volume_slider.value() - 5)
        else:
            super().keyPressEvent(event)
    
    def load_video(self, file_path):
        """加载视频文件"""
        if not os.path.exists(file_path):
            self.info_label.setText(f"错误: 文件不存在 - {file_path}")
            return False
        
        # 设置媒体源
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        
        # 更新UI
        self.video_file_path = file_path
        self.video_filename = os.path.basename(file_path)
        self.info_label.setText(f"已加载: {self.video_filename}")
        
        # 初始化OpenCV视频捕获
        self.video_cap = cv2.VideoCapture(file_path)
        if not self.video_cap.isOpened():
            self.info_label.setText(f"错误: 无法使用OpenCV打开视频 - {file_path}")
            return False
        
        # 获取视频信息
        fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self.frame_step_size = int(1000 / fps)
        
        # 重置播放速度
        self.speed_combo.setCurrentText("1.0x")
        self.playback_speed = 1.0
        
        # 清空标记和关键帧
        self.markers = []
        self.keyframes = []
        
        return True
    
    def play(self):
        """播放视频"""
        if self.media_player.source().isEmpty():
            return
        
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
            
        self.media_player.play()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
    
    def pause(self):
        """暂停视频"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            return
            
        self.media_player.pause()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
    
    def toggle_play(self):
        """播放/暂停切换"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()
    
    def stop(self):
        """停止视频播放"""
        self.media_player.stop()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
    
    def set_position(self, position):
        """设置视频位置"""
        self.media_player.setPosition(position)
        
        # 发射位置变化信号
        self.positionChanged.emit(position)
    
    def update_position(self, position):
        """更新当前位置"""
        # 更新滑块位置
        self.position_slider.setValue(position)
        
        # 更新时间标签
        self.update_position_label(position)
    
    def update_duration(self, duration):
        """更新视频总时长"""
        self.position_slider.setRange(0, duration)
        self.update_position_label(self.media_player.position())
    
    def update_position_label(self, position):
        """更新时间标签"""
        duration = self.media_player.duration()
        
        # 更新Label
        self.position_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
    
    def on_slider_pressed(self):
        """滑块被按下时的处理"""
        # 暂停视频更新定时器
        if self.preview_timer.isActive():
            self.preview_timer.stop()
        
        # 记录当前播放状态
        self.was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        # 暂停播放
        if self.was_playing:
            self.pause()
    
    def on_slider_released(self):
        """滑块释放时的处理"""
        # 如果之前是播放状态，恢复播放
        if hasattr(self, 'was_playing') and self.was_playing:
            self.play()
        
        # 恢复预览定时器
        if self.effect_preview_button.isChecked():
            self.preview_timer.start()
    
    def change_volume(self, volume):
        """修改音量"""
        self.audio_output.setVolume(volume / 100.0)
        self.volume_slider.setValue(volume)
    
    def change_playback_speed(self, speed_text):
        """修改播放速度"""
        speed = float(speed_text.replace('x', ''))
        self.playback_speed = speed
        
        # 设置新的播放速率
        self.media_player.setPlaybackRate(speed)
        
        # 更新信息
        self.info_label.setText(f"播放速度: {speed_text} - {self.video_filename}")
    
    def go_to_previous_frame(self):
        """帧退一帧"""
        if self.media_player.source().isEmpty():
            return
            
        # 暂停播放
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if was_playing:
            self.pause()
        
        # 获取当前位置和帧步长
        current_position = self.media_player.position()
        
        # 计算上一帧的位置
        prev_position = max(0, current_position - self.frame_step_size)
        
        # 设置到上一帧
        self.media_player.setPosition(prev_position)
        
        # 如果开启了预览，更新预览
        if self.preview_label.isVisible():
            self.update_preview()
    
    def go_to_next_frame(self):
        """帧进一帧"""
        if self.media_player.source().isEmpty():
            return
            
        # 暂停播放
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if was_playing:
            self.pause()
        
        # 获取当前位置和帧步长
        current_position = self.media_player.position()
        
        # 计算下一帧的位置
        next_position = min(self.media_player.duration(), current_position + self.frame_step_size)
        
        # 设置到下一帧
        self.media_player.setPosition(next_position)
        
        # 如果开启了预览，更新预览
        if self.preview_label.isVisible():
            self.update_preview()
    
    def go_to_previous_keyframe(self):
        """跳转到前一个关键帧"""
        if not self.keyframes:
            self.info_label.setText("提示: 请先检测关键帧")
            return
            
        current_position = self.media_player.position()
        
        # 寻找前一个关键帧
        prev_keyframe = None
        for keyframe in reversed(self.keyframes):
            if keyframe < current_position:
                prev_keyframe = keyframe
                break
        
        if prev_keyframe is not None:
            self.media_player.setPosition(prev_keyframe)
            self.info_label.setText(f"已跳转到关键帧: {self.format_time(prev_keyframe)}")
        else:
            # 如果没有前一个关键帧，跳转到第一个关键帧
            self.media_player.setPosition(self.keyframes[0])
            self.info_label.setText(f"已跳转到首个关键帧: {self.format_time(self.keyframes[0])}")
    
    def go_to_next_keyframe(self):
        """跳转到下一个关键帧"""
        if not self.keyframes:
            self.info_label.setText("提示: 请先检测关键帧")
            return
            
        current_position = self.media_player.position()
        
        # 寻找下一个关键帧
        next_keyframe = None
        for keyframe in self.keyframes:
            if keyframe > current_position:
                next_keyframe = keyframe
                break
        
        if next_keyframe is not None:
            self.media_player.setPosition(next_keyframe)
            self.info_label.setText(f"已跳转到关键帧: {self.format_time(next_keyframe)}")
        else:
            # 如果没有下一个关键帧，跳转到最后一个关键帧
            self.media_player.setPosition(self.keyframes[-1])
            self.info_label.setText(f"已跳转到末尾关键帧: {self.format_time(self.keyframes[-1])}")
    
    def add_marker(self):
        """添加当前位置标记"""
        # 如果未加载视频，退出
        if self.media_player.source().isEmpty():
            return
            
        # 获取当前位置
        position = self.media_player.position()
        
        # 创建标记对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加标记")
        dialog_layout = QVBoxLayout(dialog)
        
        # 标记描述输入框
        label = QLabel("标记描述:")
        dialog_layout.addWidget(label)
        
        marker_desc = QLineEdit()
        marker_desc.setPlaceholderText("输入标记描述...")
        marker_desc.setText(f"标记 {len(self.markers) + 1} - {self.format_time(position)}")
        dialog_layout.addWidget(marker_desc)
        
        # 对话框按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = marker_desc.text()
            if not description:
                description = f"标记 {len(self.markers) + 1}"
                
            # 添加标记
            self.markers.append((position, description))
            
            # 发射信号
            self.markerAdded.emit(position, description)
            
            # 更新信息
            self.info_label.setText(f"已添加标记: {description} 在 {self.format_time(position)}")
    
    def show_marker_list(self):
        """显示标记列表"""
        if not self.markers:
            self.info_label.setText("暂无标记")
            return
            
        # 创建标记列表对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("标记列表")
        dialog.resize(400, 300)
        dialog_layout = QVBoxLayout(dialog)
        
        # 标记列表
        list_widget = QListWidget()
        for position, description in self.markers:
            list_widget.addItem(f"{description} - {self.format_time(position)}")
        
        dialog_layout.addWidget(list_widget)
        
        # 添加双击跳转功能
        def jump_to_marker(item):
            index = list_widget.row(item)
            position = self.markers[index][0]
            self.media_player.setPosition(position)
            dialog.close()
            
        list_widget.itemDoubleClicked.connect(jump_to_marker)
        
        # 添加右键菜单
        def show_context_menu(pos):
            global_pos = list_widget.mapToGlobal(pos)
            
            menu = QMenu()
            jump_action = menu.addAction("跳转到此标记")
            delete_action = menu.addAction("删除此标记")
            
            action = menu.exec(global_pos)
            
            if action == jump_action:
                jump_to_marker(list_widget.currentItem())
            elif action == delete_action:
                index = list_widget.currentRow()
                if index >= 0:
                    del self.markers[index]
                    list_widget.takeItem(index)
        
        list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(show_context_menu)
        
        # 对话框按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        # 显示对话框
        dialog.exec()
    
    def toggle_effect_preview(self, enabled):
        """切换特效预览模式"""
        if enabled:
            # 开启预览模式
            if self.video_cap and self.video_cap.isOpened():
                # 暂停播放器，使用预览层
                was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                if was_playing:
                    self.pause()
                
                # 设置预览效果
                self.current_effect = "模糊效果"  # 默认效果
                
                # 显示预览层
                self.preview_label.setVisible(True)
                self.preview_timer.start()
                
                # 更新信息
                self.info_label.setText(f"预览效果: {self.current_effect}")
            else:
                self.info_label.setText("错误: 未加载视频或视频无法处理")
                self.effect_preview_button.setChecked(False)
        else:
            # 关闭预览模式
            self.preview_timer.stop()
            self.preview_label.setVisible(False)
            self.info_label.setText(f"已加载: {self.video_filename}")
    
    def update_preview(self):
        """更新预览效果"""
        if not self.video_cap or not self.video_cap.isOpened():
            return
            
        # 获取当前帧
        position = self.media_player.position()
        self.video_cap.set(cv2.CAP_PROP_POS_MSEC, position)
        success, frame = self.video_cap.read()
        
        if not success:
            return
            
        # 应用效果
        if self.current_effect == "模糊效果":
            frame = cv2.GaussianBlur(frame, (15, 15), 0)
        elif self.current_effect == "边缘检测":
            frame = cv2.Canny(frame, 100, 200)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif self.current_effect == "怀旧风格":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.array(frame, dtype=np.float64)
            frame = frame * np.array([0.393, 0.769, 0.189]).reshape((1, 1, 3))
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif self.current_effect == "黑白效果":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif self.current_effect == "锐化效果":
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            frame = cv2.filter2D(frame, -1, kernel)
        # 原始画面或未知效果，不做处理
        
        # 转换为QImage并显示
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        self.preview_label.setPixmap(QPixmap.fromImage(q_image).scaled(
            self.video_widget.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
    
    def take_snapshot(self):
        """截取当前帧"""
        if not self.video_cap or not self.video_cap.isOpened():
            self.info_label.setText("错误: 未加载视频或视频无法处理")
            return
            
        # 获取当前帧
        position = self.media_player.position()
        self.video_cap.set(cv2.CAP_PROP_POS_MSEC, position)
        success, frame = self.video_cap.read()
        
        if not success:
            self.info_label.setText("错误: 无法获取当前帧")
            return
            
        # 创建保存对话框
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("图片文件 (*.png *.jpg)")
        file_dialog.setDefaultSuffix("png")
        
        video_name = os.path.splitext(self.video_filename)[0]
        default_name = f"{video_name}_snapshot_{self.format_time(position).replace(':', '_')}.png"
        file_dialog.selectFile(default_name)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            
            # 保存图片
            cv2.imwrite(file_path, frame)
            
            # 发射信号
            self.snapshotTaken.emit(file_path)
            
            # 更新信息
            self.info_label.setText(f"截图已保存: {os.path.basename(file_path)}")
    
    def adjust_speed(self, delta):
        """调整播放速度"""
        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        current_speed = float(self.speed_combo.currentText().replace('x', ''))
        
        new_speed = current_speed + delta
        
        # 找到最接近的预设速度
        closest_speed = min(speeds, key=lambda x: abs(x - new_speed))
        
        self.speed_combo.setCurrentText(f"{closest_speed}x")
    
    def detect_keyframes(self):
        """检测视频关键帧"""
        if not self.video_cap or not self.video_cap.isOpened():
            self.info_label.setText("错误: 未加载视频或视频无法处理")
            return
        
        # 暂停播放
        self.pause()
        
        # 保存当前位置
        current_position = self.media_player.position()
        
        # 重置关键帧列表
        self.keyframes = []
        
        # 获取视频信息
        total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # 默认值
        
        # 更新信息
        self.info_label.setText("正在检测关键帧...")
        
        # 初始化变量
        prev_frame = None
        
        # 设置采样间隔 (每秒检查5帧)
        sample_interval = max(1, int(fps / 5))
        
        # 提前计算好每一帧的时间点（毫秒）
        frame_times = [int(i * 1000 / fps) for i in range(0, total_frames, sample_interval)]
        
        # 检测关键帧
        for i, frame_time in enumerate(frame_times):
            # 设置帧位置
            self.video_cap.set(cv2.CAP_PROP_POS_MSEC, frame_time)
            success, frame = self.video_cap.read()
            
            if not success:
                continue
                
            # 调整帧大小以加快处理速度
            small_frame = cv2.resize(frame, (320, 180))
            gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # 计算帧差异
                diff = cv2.absdiff(gray_frame, prev_frame)
                non_zero_count = np.count_nonzero(diff)
                
                # 判断是否是关键帧
                if non_zero_count > (gray_frame.size * self.keyframe_threshold):
                    # 添加关键帧
                    self.keyframes.append(frame_time)
                    self.keyframeDetected.emit(frame_time, f"关键帧 {len(self.keyframes)}")
            
            # 更新上一帧
            prev_frame = gray_frame
            
            # 更新进度
            progress = int((i / len(frame_times)) * 100)
            self.info_label.setText(f"正在检测关键帧... {progress}%")
        
        # 恢复原始位置
        self.media_player.setPosition(current_position)
        
        # 更新信息
        self.info_label.setText(f"已加载: {self.video_filename} (检测到 {len(self.keyframes)} 个关键帧)")
    
    def handle_media_status_changed(self, status):
        """处理媒体状态变化"""
        status_map = {
            QMediaPlayer.MediaStatus.NoMedia: "无媒体",
            QMediaPlayer.MediaStatus.LoadingMedia: "加载中",
            QMediaPlayer.MediaStatus.LoadedMedia: "已加载",
            QMediaPlayer.MediaStatus.BufferingMedia: "缓冲中",
            QMediaPlayer.MediaStatus.BufferedMedia: "已缓冲",
            QMediaPlayer.MediaStatus.EndOfMedia: "播放结束",
            QMediaPlayer.MediaStatus.InvalidMedia: "无效媒体"
        }
        
        status_text = status_map.get(status, "未知状态")
        
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # 视频加载完成，更新信息
            video_info = self.get_video_info()
            if video_info:
                self.info_label.setText(f"已加载: {self.video_filename} {video_info}")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.info_label.setText(f"错误: 无法播放视频 - {self.video_filename}")
    
    def handle_playback_state_changed(self, state):
        """处理播放状态变化"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
    
    def handle_error(self, error, error_string):
        """处理错误"""
        self.info_label.setText(f"错误: {error_string}")
    
    def get_video_info(self):
        """获取视频信息"""
        if not self.video_cap or not self.video_cap.isOpened():
            return None
            
        width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = round(self.video_cap.get(cv2.CAP_PROP_FPS), 1)
        
        return f"({width}x{height}, {fps}fps)"
    
    def format_time(self, ms):
        """格式化时间为 HH:MM:SS 格式"""
        s = ms // 1000
        m = s // 60
        h = m // 60
        s = s % 60
        m = m % 60
        
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    def show_effect_menu(self):
        """显示效果菜单"""
        if not self.video_cap or not self.video_cap.isOpened():
            self.info_label.setText("错误: 未加载视频或视频无法处理")
            return
            
        menu = QMenu(self)
        effects = ["原始画面", "模糊效果", "边缘检测", "怀旧风格", "黑白效果", "锐化效果"]
        
        for effect in effects:
            action = menu.addAction(effect)
            action.triggered.connect(lambda checked, e=effect: self.apply_effect(e))
        
        # 显示菜单
        pos = self.effect_preview_button.mapToGlobal(
            QPointF(0, -menu.sizeHint().height()).toPoint()
        )
        action = menu.exec(pos)
        
        # 如果用户选择了效果，启用预览模式
        if action:
            if not self.effect_preview_button.isChecked():
                self.effect_preview_button.setChecked(True)
                self.toggle_effect_preview(True)
    
    def apply_effect(self, effect):
        """应用特效"""
        self.current_effect = effect
        
        # 检查是否需要启用预览模式
        if not self.preview_label.isVisible():
            self.toggle_effect_preview(True)
        
        # 更新信息
        self.info_label.setText(f"预览效果: {effect}")
        
        # 更新预览
        self.update_preview()
    
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 更新预览层大小
        if self.preview_label.isVisible():
            self.update_preview()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止视频播放
        self.media_player.stop()
        
        # 关闭视频文件
        if self.video_cap and self.video_cap.isOpened():
            self.video_cap.release()
        
        super().closeEvent(event)
    
    def set_in_point(self):
        """设置入点"""
        if self.media_player.source().isEmpty():
            return
            
        self.in_point = self.media_player.position()
        
        # 更新信息
        self.info_label.setText(f"已设置入点: {self.format_time(self.in_point)}")
        
        # 更新出点信息
        if self.out_point >= 0 and self.out_point > self.in_point:
            duration = self.out_point - self.in_point
            self.info_label.setText(f"已设置入点: {self.format_time(self.in_point)} - 片段长度: {self.format_time(duration)}")
    
    def set_out_point(self):
        """设置出点"""
        if self.media_player.source().isEmpty():
            return
            
        self.out_point = self.media_player.position()
        
        # 确保出点在入点之后
        if self.in_point >= 0 and self.out_point <= self.in_point:
            self.info_label.setText("错误: 出点必须在入点之后")
            return
            
        # 更新信息
        self.info_label.setText(f"已设置出点: {self.format_time(self.out_point)}")
        
        # 更新入点信息
        if self.in_point >= 0:
            duration = self.out_point - self.in_point
            self.info_label.setText(f"已设置出点: {self.format_time(self.out_point)} - 片段长度: {self.format_time(duration)}")
    
    def create_clip(self):
        """创建片段"""
        if self.media_player.source().isEmpty():
            return
            
        # 检查入点和出点
        if self.in_point < 0:
            self.info_label.setText("错误: 请先设置入点")
            return
            
        if self.out_point < 0 or self.out_point <= self.in_point:
            self.info_label.setText("错误: 请设置有效的出点 (必须在入点之后)")
            return
            
        # 创建片段
        duration = self.out_point - self.in_point
        
        # 发射信号
        self.clipCreated.emit(self.video_file_path, self.in_point, self.out_point)
        
        # 更新信息
        self.info_label.setText(f"已创建片段: {self.format_time(self.in_point)} 到 {self.format_time(self.out_point)} (长度: {self.format_time(duration)})")
        
        # 重置入点和出点
        self.in_point = -1
        self.out_point = -1
    
    def play_clip(self, start_time, end_time):
        """播放指定时间段的片段"""
        if self.media_player.source().isEmpty():
            return
            
        # 设置位置到起始时间
        self.media_player.setPosition(start_time)
        
        # 开始播放
        self.play()
        
        # 设置结束检测定时器
        def check_end():
            current_pos = self.media_player.position()
            if current_pos >= end_time:
                self.pause()
                self.media_player.setPosition(end_time)
                self.clip_end_timer.stop()
                
        self.clip_end_timer = QTimer(self)
        self.clip_end_timer.timeout.connect(check_end)
        self.clip_end_timer.start(100)  # 每100ms检查一次
    
    def show_context_menu(self, pos):
        """显示视频播放器上下文菜单"""
        if self.media_player.source().isEmpty():
            return
            
        menu = QMenu(self)
        
        # 添加播放控制
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            menu.addAction("暂停", self.pause)
        else:
            menu.addAction("播放", self.play)
            
        # 添加帧控制
        frame_menu = menu.addMenu("帧控制")
        frame_menu.addAction("帧进", self.go_to_next_frame)
        frame_menu.addAction("帧退", self.go_to_previous_frame)
        
        # 添加关键帧控制
        keyframe_menu = menu.addMenu("关键帧")
        keyframe_menu.addAction("上一关键帧", self.go_to_previous_keyframe)
        keyframe_menu.addAction("下一关键帧", self.go_to_next_keyframe)
        keyframe_menu.addAction("检测关键帧", self.detect_keyframes)
        
        # 添加标记控制
        marker_menu = menu.addMenu("标记")
        marker_menu.addAction("添加标记", self.add_marker)
        marker_menu.addAction("查看标记列表", self.show_marker_list)
        
        # 添加截图功能
        menu.addAction("截图", self.take_snapshot)
        
        # 添加效果预览
        menu.addAction("效果预览", self.show_effect_menu)
        
        # 添加播放速度控制
        speed_menu = menu.addMenu("播放速度")
        for speed in ["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]:
            action = speed_menu.addAction(speed)
            action.setCheckable(True)
            action.setChecked(self.speed_combo.currentText() == speed)
            speed_text = speed
            action.triggered.connect(lambda checked, s=speed: self.speed_combo.setCurrentText(s))
        
        # 添加片段控制
        clip_menu = menu.addMenu("片段")
        clip_menu.addAction("设置入点", self.set_in_point)
        clip_menu.addAction("设置出点", self.set_out_point)
        clip_menu.addAction("创建片段", self.create_clip)
        
        # 显示菜单
        menu.exec(self.video_widget.mapToGlobal(pos))
    
    def show_options_menu(self):
        """显示更多选项菜单"""
        menu = QMenu(self)
        
        # 添加常用功能
        menu.addAction("添加标记", self.add_marker)
        menu.addAction("截图", self.take_snapshot)
        menu.addAction("检测关键帧", self.detect_keyframes)
        menu.addAction("标记列表", self.show_marker_list)
        menu.addAction("效果预览", self.show_effect_menu)
        
        # 添加播放速度控制
        speed_menu = menu.addMenu("播放速度")
        for speed in ["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]:
            action = speed_menu.addAction(speed)
            action.setCheckable(True)
            action.setChecked(self.speed_combo.currentText() == speed)
            speed_text = speed
            action.triggered.connect(lambda checked, s=speed: self.speed_combo.setCurrentText(s))
        
        # 显示菜单
        menu.exec(self.more_options_button.mapToGlobal(QPointF(0, -menu.sizeHint().height()).toPoint())) 