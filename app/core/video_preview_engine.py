#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级视频预览引擎 - 高性能视频预览和处理核心
"""

import os
import cv2
import numpy as np
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import subprocess
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, Qt
from PyQt6.QtGui import QImage, QPixmap, QPixelFormat
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class PreviewMode(Enum):
    """预览模式"""
    SINGLE = "single"          # 单画面预览
    SPLIT = "split"           # 分屏对比
    GRID = "grid"             # 网格多画面
    PIP = "pip"               # 画中画


class ZoomMode(Enum):
    """缩放模式"""
    FIT = "fit"               # 适应窗口
    FILL = "fill"             # 填充窗口
    ORIGINAL = "original"     # 原始尺寸
    CUSTOM = "custom"         # 自定义缩放


class FilterType(Enum):
    """滤镜类型"""
    NONE = "none"
    BLUR = "blur"
    SHARPEN = "sharpen"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    HUE = "hue"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    EDGE_DETECT = "edge_detect"
    EMBOSS = "emboss"
    VINTAGE = "vintage"
    COLD = "cold"
    WARM = "warm"


@dataclass
class PreviewConfig:
    """预览配置"""
    mode: PreviewMode = PreviewMode.SINGLE
    zoom_mode: ZoomMode = ZoomMode.FIT
    zoom_level: float = 1.0
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue: float = 0.0
    hardware_acceleration: bool = True
    max_cache_size: int = 100  # MB
    frame_skip_threshold: int = 3
    enable_filters: bool = True


@dataclass
class VideoFrame:
    """视频帧数据"""
    timestamp: float
    frame_number: int
    data: np.ndarray
    width: int
    height: int
    format: str = "BGR"


class FrameCache:
    """帧缓存管理器"""
    
    def __init__(self, max_size_mb: int = 100):
        self.max_size_mb = max_size_mb
        self.cache = {}
        self.access_order = []
        self.current_size = 0
        self.lock = threading.Lock()
    
    def add_frame(self, frame_number: int, frame: VideoFrame) -> bool:
        """添加帧到缓存"""
        with self.lock:
            # 计算帧大小
            frame_size = frame.data.nbytes
            
            # 检查是否超过缓存大小
            if self.current_size + frame_size > self.max_size_mb * 1024 * 1024:
                self._evict_frames(frame_size)
            
            # 添加帧
            self.cache[frame_number] = frame
            self.access_order.append(frame_number)
            self.current_size += frame_size
            
            return True
    
    def get_frame(self, frame_number: int) -> Optional[VideoFrame]:
        """获取帧"""
        with self.lock:
            if frame_number in self.cache:
                # 更新访问顺序
                self.access_order.remove(frame_number)
                self.access_order.append(frame_number)
                return self.cache[frame_number]
            return None
    
    def _evict_frames(self, required_size: int):
        """清理缓存"""
        while self.current_size > required_size and self.access_order:
            oldest_frame = self.access_order.pop(0)
            if oldest_frame in self.cache:
                frame = self.cache.pop(oldest_frame)
                self.current_size -= frame.data.nbytes
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size = 0


class VideoPreviewEngine(QObject):
    """企业级视频预览引擎"""
    
    # 信号
    frame_ready = pyqtSignal(VideoFrame)           # 帧准备就绪
    preview_updated = pyqtSignal(QImage)         # 预览更新
    position_changed = pyqtSignal(float)           # 位置变化
    duration_changed = pyqtSignal(float)          # 时长变化
    playback_state_changed = pyqtSignal(str)      # 播放状态变化
    error_occurred = pyqtSignal(str)              # 错误发生
    filter_applied = pyqtSignal(FilterType, dict) # 滤镜应用
    zoom_changed = pyqtSignal(ZoomMode, float)     # 缩放变化
    
    def __init__(self, config: PreviewConfig = None):
        super().__init__()
        
        self.config = config or PreviewConfig()
        self.video_path = ""
        self.cap = None
        self.media_player = None
        self.audio_output = None
        
        # 预览状态
        self.is_playing = False
        self.current_position = 0.0
        self.duration = 0.0
        self.fps = 30.0
        self.frame_count = 0
        self.width = 0
        self.height = 0
        
        # 帧缓存
        self.frame_cache = FrameCache(self.config.max_cache_size)
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 预览线程
        self.preview_thread = None
        self.preview_queue = queue.Queue()
        self.stop_preview = False
        
        # 滤镜
        self.current_filter = FilterType.NONE
        self.filter_params = {}
        
        # 性能统计
        self.stats = {
            "frames_processed": 0,
            "fps_actual": 0.0,
            "cache_hit_rate": 0.0,
            "processing_time": 0.0
        }
        
        # 初始化定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.setInterval(33)  # ~30fps
        
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(1000)  # 每秒更新FPS
        
        self.frame_count_current = 0
        self.last_fps_time = time.time()
    
    def load_video(self, video_path: str) -> bool:
        """加载视频文件"""
        try:
            if not os.path.exists(video_path):
                self.error_occurred.emit(f"文件不存在: {video_path}")
                return False
            
            self.video_path = video_path
            
            # 使用OpenCV打开视频
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                self.error_occurred.emit("无法打开视频文件")
                return False
            
            # 获取视频信息
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = self.frame_count / self.fps if self.fps > 0 else 0
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 初始化媒体播放器
            self._init_media_player()
            
            # 清空缓存
            self.frame_cache.clear()
            
            # 启动预览线程
            self._start_preview_thread()
            
            # 发射信号
            self.duration_changed.emit(self.duration)
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"加载视频失败: {str(e)}")
            return False
    
    def _init_media_player(self):
        """初始化媒体播放器"""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 连接信号
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.errorOccurred.connect(self._on_media_error)
        
        # 设置视频源
        self.media_player.setSource(QUrl.fromLocalFile(self.video_path))
    
    def _start_preview_thread(self):
        """启动预览线程"""
        self.stop_preview = False
        self.preview_thread = threading.Thread(target=self._preview_worker, daemon=True)
        self.preview_thread.start()
    
    def _preview_worker(self):
        """预览工作线程"""
        last_frame_number = -1
        
        while not self.stop_preview:
            try:
                if self.is_playing and self.cap:
                    # 获取当前帧号
                    current_frame_number = int(self.current_position * self.fps)
                    
                    # 检查是否需要处理新帧
                    if current_frame_number != last_frame_number:
                        # 尝试从缓存获取
                        frame = self.frame_cache.get_frame(current_frame_number)
                        
                        if frame is None:
                            # 从视频读取帧
                            frame = self._read_frame(current_frame_number)
                            if frame:
                                # 添加到缓存
                                self.frame_cache.add_frame(current_frame_number, frame)
                                self.stats["frames_processed"] += 1
                        
                        if frame:
                            # 应用滤镜
                            if self.config.enable_filters and self.current_filter != FilterType.NONE:
                                frame = self._apply_filter_to_frame(frame)
                            
                            # 发射信号
                            self.frame_ready.emit(frame)
                            
                            last_frame_number = current_frame_number
                            self.frame_count_current += 1
                
                # 控制帧率
                time.sleep(1.0 / (self.fps * 2))  # 以两倍帧率处理以确保流畅
                
            except Exception as e:
                self.error_occurred.emit(f"预览线程错误: {str(e)}")
                time.sleep(0.1)
    
    def _read_frame(self, frame_number: int) -> Optional[VideoFrame]:
        """读取指定帧"""
        try:
            # 设置帧位置
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # 读取帧
            ret, frame_data = self.cap.read()
            if not ret:
                return None
            
            # 创建帧对象
            frame = VideoFrame(
                timestamp=frame_number / self.fps,
                frame_number=frame_number,
                data=frame_data,
                width=self.width,
                height=self.height
            )
            
            return frame
            
        except Exception as e:
            print(f"读取帧失败: {e}")
            return None
    
    def _apply_filter_to_frame(self, frame: VideoFrame) -> VideoFrame:
        """对帧应用滤镜"""
        try:
            filtered_data = frame.data.copy()
            
            if self.current_filter == FilterType.BLUR:
                filtered_data = cv2.GaussianBlur(filtered_data, (15, 15), 0)
            
            elif self.current_filter == FilterType.SHARPEN:
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
                filtered_data = cv2.filter2D(filtered_data, -1, kernel)
            
            elif self.current_filter == FilterType.BRIGHTNESS:
                brightness_factor = self.filter_params.get("brightness", 1.0)
                filtered_data = cv2.convertScaleAbs(filtered_data, alpha=brightness_factor, beta=0)
            
            elif self.current_filter == FilterType.CONTRAST:
                contrast_factor = self.filter_params.get("contrast", 1.0)
                filtered_data = cv2.convertScaleAbs(filtered_data, alpha=contrast_factor, beta=0)
            
            elif self.current_filter == FilterType.GRAYSCALE:
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_BGR2GRAY)
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_GRAY2BGR)
            
            elif self.current_filter == FilterType.SEPIA:
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_BGR2RGB)
                filtered_data = np.array(filtered_data, dtype=np.float64)
                filtered_data = filtered_data * np.array([0.393, 0.769, 0.189]).reshape((1, 1, 3))
                filtered_data = np.clip(filtered_data, 0, 255).astype(np.uint8)
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_RGB2BGR)
            
            elif self.current_filter == FilterType.EDGE_DETECT:
                filtered_data = cv2.Canny(filtered_data, 100, 200)
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_GRAY2BGR)
            
            elif self.current_filter == FilterType.VINTAGE:
                # 复古效果
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_BGR2RGB)
                h, s, v = cv2.split(cv2.cvtColor(filtered_data, cv2.COLOR_RGB2HSV))
                s = s * 0.8  # 降低饱和度
                v = v * 1.2  # 提高亮度
                filtered_data = cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2RGB)
                filtered_data = cv2.cvtColor(filtered_data, cv2.COLOR_RGB2BGR)
            
            # 创建新帧对象
            return VideoFrame(
                timestamp=frame.timestamp,
                frame_number=frame.frame_number,
                data=filtered_data,
                width=frame.width,
                height=frame.height
            )
            
        except Exception as e:
            print(f"应用滤镜失败: {e}")
            return frame
    
    def _update_preview(self):
        """更新预览显示"""
        # 这个方法由子类实现具体的显示逻辑
        pass
    
    def _update_fps(self):
        """更新FPS统计"""
        current_time = time.time()
        time_diff = current_time - self.last_fps_time
        
        if time_diff > 0:
            self.stats["fps_actual"] = self.frame_count_current / time_diff
            self.frame_count_current = 0
            self.last_fps_time = current_time
    
    def play(self):
        """开始播放"""
        if self.media_player:
            self.media_player.play()
        self.is_playing = True
        self.playback_state_changed.emit("playing")
        self.update_timer.start()
    
    def pause(self):
        """暂停播放"""
        if self.media_player:
            self.media_player.pause()
        self.is_playing = False
        self.playback_state_changed.emit("paused")
        self.update_timer.stop()
    
    def stop(self):
        """停止播放"""
        if self.media_player:
            self.media_player.stop()
        self.is_playing = False
        self.current_position = 0.0
        self.playback_state_changed.emit("stopped")
        self.update_timer.stop()
    
    def seek(self, position: float):
        """跳转到指定位置"""
        if self.media_player:
            self.media_player.setPosition(int(position * 1000))
        self.current_position = position
        self.position_changed.emit(position)
    
    def set_playback_rate(self, rate: float):
        """设置播放速率"""
        if self.media_player:
            self.media_player.setPlaybackRate(rate)
    
    def set_volume(self, volume: float):
        """设置音量"""
        if self.audio_output:
            self.audio_output.setVolume(volume)
    
    def apply_filter(self, filter_type: FilterType, params: dict = None):
        """应用滤镜"""
        self.current_filter = filter_type
        self.filter_params = params or {}
        
        # 发射信号
        self.filter_applied.emit(filter_type, self.filter_params)
    
    def set_zoom_mode(self, mode: ZoomMode, level: float = 1.0):
        """设置缩放模式"""
        self.config.zoom_mode = mode
        self.config.zoom_level = level
        
        # 发射信号
        self.zoom_changed.emit(mode, level)
    
    def get_frame_at_time(self, timestamp: float) -> Optional[VideoFrame]:
        """获取指定时间的帧"""
        frame_number = int(timestamp * self.fps)
        return self.frame_cache.get_frame(frame_number)
    
    def get_video_info(self) -> dict:
        """获取视频信息"""
        return {
            "path": self.video_path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "format": os.path.splitext(self.video_path)[1][1:].upper()
        }
    
    def get_stats(self) -> dict:
        """获取性能统计"""
        cache_hit_rate = 0.0
        if self.stats["frames_processed"] > 0:
            cache_hit_rate = (self.stats["frames_processed"] - len(self.frame_cache.cache)) / self.stats["frames_processed"]
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size_mb": self.frame_cache.current_size / (1024 * 1024),
            "cache_frames": len(self.frame_cache.cache)
        }
    
    def _on_position_changed(self, position: int):
        """媒体播放器位置变化"""
        self.current_position = position / 1000.0
        self.position_changed.emit(self.current_position)
    
    def _on_duration_changed(self, duration: int):
        """媒体播放器时长变化"""
        self.duration = duration / 1000.0
        self.duration_changed.emit(self.duration)
    
    def _on_playback_state_changed(self, state):
        """媒体播放器状态变化"""
        state_map = {
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
            QMediaPlayer.PlaybackState.StoppedState: "stopped"
        }
        state_str = state_map.get(state, "unknown")
        self.is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.playback_state_changed.emit(state_str)
    
    def _on_media_error(self, error, error_string):
        """媒体播放器错误"""
        self.error_occurred.emit(f"媒体播放器错误: {error_string}")
    
    def cleanup(self):
        """清理资源"""
        self.stop_preview = True
        
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.0)
        
        if self.cap:
            self.cap.release()
        
        if self.media_player:
            self.media_player.stop()
            self.media_player = None
        
        self.thread_pool.shutdown(wait=False)
        
        # 清空缓存
        self.frame_cache.clear()