#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化版实时预览引擎 - 高性能、低延迟的视频预览系统
解决预览性能、缓存管理和硬件加速问题
"""

import os
import sys
import time
import logging
import threading
import queue
import weakref
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, deque
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor
import psutil

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, Qt, QMutex, QMutexLocker, QPointF, QRectF, QMimeData
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QPen, QFont, QTransform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QSlider
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

logger = logging.getLogger(__name__)


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


class RenderQuality(Enum):
    """渲染质量"""
    LOW = "low"        # 低质量，高性能
    MEDIUM = "medium"  # 中等质量
    HIGH = "high"      # 高质量
    ULTRA = "ultra"    # 超高质量


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
    max_cache_size: int = 500  # MB
    frame_skip_threshold: int = 3
    enable_filters: bool = True
    render_quality: RenderQuality = RenderQuality.MEDIUM
    max_fps: int = 60
    enable_real_time_effects: bool = True
    buffer_size: int = 10  # 帧缓冲大小


@dataclass
class VideoFrame:
    """视频帧数据"""
    timestamp: float
    frame_number: int
    data: np.ndarray
    width: int
    height: int
    format: str = "BGR"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SmartFrameCache:
    """智能帧缓存管理器"""
    
    def __init__(self, max_size_mb: int = 500):
        self.max_size_mb = max_size_mb
        self.cache = OrderedDict()
        self.access_order = deque()
        self.current_size = 0
        self.lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        
        # 智能预测
        self.prediction_cache = {}
        self.access_pattern = deque(maxlen=100)
        
        # 统计信息
        self.stats = {
            "total_accesses": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "avg_access_time": 0.0,
            "memory_efficiency": 0.0
        }
    
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
            
            # 更新访问模式
            self.access_pattern.append(frame_number)
            
            # 预测下一帧
            self._predict_next_frames()
            
            return True
    
    def get_frame(self, frame_number: int) -> Optional[VideoFrame]:
        """获取帧"""
        with self.lock:
            self.stats["total_accesses"] += 1
            
            if frame_number in self.cache:
                # 更新访问顺序
                self.access_order.remove(frame_number)
                self.access_order.append(frame_number)
                
                self.stats["cache_hits"] += 1
                self.hit_count += 1
                
                return self.cache[frame_number]
            
            self.stats["cache_misses"] += 1
            self.miss_count += 1
            
            return None
    
    def _evict_frames(self, required_size: int):
        """智能清理缓存"""
        evicted = 0
        while self.current_size > required_size and self.access_order:
            # 使用LRU策略
            oldest_frame = self.access_order.popleft()
            if oldest_frame in self.cache:
                frame = self.cache.pop(oldest_frame)
                self.current_size -= frame.data.nbytes
                evicted += 1
                self.eviction_count += 1
                self.stats["evictions"] += 1
        
        if evicted > 0:
            logger.debug(f"缓存清理: 清理了 {evicted} 帧, 释放 {self.current_size / (1024*1024):.2f}MB")
    
    def _predict_next_frames(self):
        """预测下一帧"""
        if len(self.access_pattern) < 3:
            return
        
        # 简单的线性预测
        recent_accesses = list(self.access_pattern)[-10:]
        if len(recent_accesses) >= 2:
            # 计算平均步长
            steps = [recent_accesses[i+1] - recent_accesses[i] for i in range(len(recent_accesses)-1)]
            if steps:
                avg_step = sum(steps) / len(steps)
                next_frame = int(recent_accesses[-1] + avg_step)
                
                # 预缓存下一帧
                if next_frame not in self.cache:
                    self.prediction_cache[next_frame] = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats["total_accesses"]
        hit_rate = self.stats["cache_hits"] / total if total > 0 else 0.0
        
        self.stats.update({
            "hit_rate": hit_rate,
            "cache_size_mb": self.current_size / (1024 * 1024),
            "cached_frames": len(self.cache),
            "efficiency": hit_rate * (1 - self.current_size / (self.max_size_mb * 1024 * 1024))
        })
        
        return self.stats.copy()
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size = 0
            self.prediction_cache.clear()
            self.stats = {
                "total_accesses": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "evictions": 0,
                "avg_access_time": 0.0,
                "memory_efficiency": 0.0
            }


class PreviewRenderEngine:
    """预览渲染引擎"""
    
    def __init__(self, config: PreviewConfig):
        self.config = config
        self.filter_pipeline = []
        self.render_stats = {
            "frames_rendered": 0,
            "average_render_time": 0.0,
            "dropped_frames": 0,
            "filter_processing_time": 0.0
        }
        
        # 初始化滤镜
        self._initialize_filters()
    
    def _initialize_filters(self):
        """初始化滤镜"""
        self.filter_pipeline = [
            {"name": "brightness", "enabled": False, "params": {"intensity": 0.0}},
            {"name": "contrast", "enabled": False, "params": {"intensity": 0.0}},
            {"name": "saturation", "enabled": False, "params": {"intensity": 0.0}},
            {"name": "blur", "enabled": False, "params": {"radius": 0}},
            {"name": "sharpen", "enabled": False, "params": {"intensity": 0.0}},
        ]
    
    def render_frame(self, frame: VideoFrame) -> VideoFrame:
        """渲染帧"""
        start_time = time.time()
        
        try:
            # 应用滤镜
            processed_frame = self._apply_filters(frame)
            
            # 质量调整
            if self.config.render_quality == RenderQuality.LOW:
                processed_frame = self._downscale_frame(processed_frame, 0.5)
            elif self.config.render_quality == RenderQuality.ULTRA:
                processed_frame = self._upscale_frame(processed_frame, 1.5)
            
            # 更新统计
            render_time = time.time() - start_time
            self.render_stats["frames_rendered"] += 1
            self.render_stats["average_render_time"] = (
                (self.render_stats["average_render_time"] * (self.render_stats["frames_rendered"] - 1) + render_time) /
                self.render_stats["frames_rendered"]
            )
            
            return processed_frame
            
        except Exception as e:
            logger.error(f"渲染帧失败: {e}")
            return frame
    
    def _apply_filters(self, frame: VideoFrame) -> VideoFrame:
        """应用滤镜"""
        start_time = time.time()
        processed_data = frame.data.copy()
        
        try:
            for filter_config in self.filter_pipeline:
                if filter_config["enabled"]:
                    processed_data = self._apply_single_filter(
                        processed_data, 
                        filter_config["name"], 
                        filter_config["params"]
                    )
            
            self.render_stats["filter_processing_time"] += time.time() - start_time
            
            return VideoFrame(
                timestamp=frame.timestamp,
                frame_number=frame.frame_number,
                data=processed_data,
                width=processed_data.shape[1],
                height=processed_data.shape[0],
                format=frame.format
            )
            
        except Exception as e:
            logger.error(f"应用滤镜失败: {e}")
            return frame
    
    def _apply_single_filter(self, data: np.ndarray, filter_name: str, params: Dict[str, Any]) -> np.ndarray:
        """应用单个滤镜"""
        if filter_name == "brightness":
            intensity = params.get("intensity", 0.0)
            hsv = cv2.cvtColor(data, cv2.COLOR_BGR2HSV)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] + intensity, 0, 255)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        elif filter_name == "contrast":
            intensity = params.get("intensity", 0.0)
            alpha = 1.0 + (intensity / 100.0)
            beta = 0
            return cv2.convertScaleAbs(data, alpha=alpha, beta=beta)
        
        elif filter_name == "saturation":
            intensity = params.get("intensity", 0.0)
            hsv = cv2.cvtColor(data, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] + intensity, 0, 255)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        elif filter_name == "blur":
            radius = int(params.get("radius", 0))
            if radius > 0:
                return cv2.GaussianBlur(data, (radius*2+1, radius*2+1), 0)
            return data
        
        elif filter_name == "sharpen":
            intensity = params.get("intensity", 0.0)
            if intensity > 0:
                kernel = np.array([[-1, -1, -1],
                                  [-1, 9, -1],
                                  [-1, -1, -1]]) * (intensity / 100.0)
                kernel[1, 1] = 9 - 8 * (intensity / 100.0)
                return cv2.filter2D(data, -1, kernel)
            return data
        
        return data
    
    def _downscale_frame(self, frame: VideoFrame, scale: float) -> VideoFrame:
        """降低帧质量"""
        new_width = int(frame.width * scale)
        new_height = int(frame.height * scale)
        
        resized_data = cv2.resize(frame.data, (new_width, new_height))
        
        return VideoFrame(
            timestamp=frame.timestamp,
            frame_number=frame.frame_number,
            data=resized_data,
            width=new_width,
            height=new_height,
            format=frame.format
        )
    
    def _upscale_frame(self, frame: VideoFrame, scale: float) -> VideoFrame:
        """提升帧质量"""
        new_width = int(frame.width * scale)
        new_height = int(frame.height * scale)
        
        # 使用高质量插值
        resized_data = cv2.resize(frame.data, (new_width, new_height), 
                                 interpolation=cv2.INTER_LANCZOS4)
        
        return VideoFrame(
            timestamp=frame.timestamp,
            frame_number=frame.frame_number,
            data=resized_data,
            width=new_width,
            height=new_height,
            format=frame.format
        )
    
    def set_filter(self, filter_name: str, enabled: bool, params: Dict[str, Any] = None):
        """设置滤镜"""
        for filter_config in self.filter_pipeline:
            if filter_config["name"] == filter_name:
                filter_config["enabled"] = enabled
                if params:
                    filter_config["params"].update(params)
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """获取渲染统计"""
        return self.render_stats.copy()


class OptimizedVideoPreviewEngine(QObject):
    """优化版视频预览引擎"""
    
    # 信号定义
    frame_ready = pyqtSignal(VideoFrame)           # 帧准备就绪
    preview_updated = pyqtSignal(QImage)         # 预览更新
    position_changed = pyqtSignal(float)           # 位置变化
    duration_changed = pyqtSignal(float)          # 时长变化
    playback_state_changed = pyqtSignal(str)      # 播放状态变化
    error_occurred = pyqtSignal(str)              # 错误发生
    filter_applied = pyqtSignal(FilterType, dict) # 滤镜应用
    zoom_changed = pyqtSignal(ZoomMode, float)     # 缩放变化
    performance_stats = pyqtSignal(dict)          # 性能统计
    
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
        
        # 智能缓存
        self.frame_cache = SmartFrameCache(self.config.max_cache_size)
        
        # 渲染引擎
        self.render_engine = PreviewRenderEngine(self.config)
        
        # 线程池
        self.max_workers = min(4, psutil.cpu_count())
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 预览线程
        self.preview_thread = None
        self.preview_queue = queue.Queue(maxsize=self.config.buffer_size)
        self.stop_preview = False
        
        # 帧缓冲区
        self.frame_buffer = deque(maxlen=self.config.buffer_size)
        self.buffer_lock = threading.Lock()
        
        # 滤镜
        self.current_filter = FilterType.NONE
        self.filter_params = {}
        
        # 性能监控
        self.stats = {
            "frames_processed": 0,
            "fps_actual": 0.0,
            "cache_hit_rate": 0.0,
            "processing_time": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "dropped_frames": 0,
            "render_quality": self.config.render_quality.value
        }
        
        # 监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_performance_stats)
        self.monitor_timer.start(1000)  # 每秒更新
        
        # 初始化定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.setInterval(16)  # ~60 FPS
        
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(1000)  # 每秒更新FPS
        
        self.frame_count_current = 0
        self.last_fps_time = time.time()
        self.last_frame_time = time.time()
        
        # 自适应质量
        self.adaptive_quality_enabled = True
        self.quality_adjustment_threshold = 0.1  # 10%性能变化阈值
    
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
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.duration = self.frame_count / self.fps if self.fps > 0 else 0
            
            # 初始化媒体播放器
            self._init_media_player()
            
            # 清空缓存
            self.frame_cache.clear()
            self.frame_buffer.clear()
            
            # 启动预览线程
            self._start_preview_thread()
            
            # 发射信号
            self.duration_changed.emit(self.duration)
            
            logger.info(f"视频加载成功: {video_path}, 分辨率: {self.width}x{self.height}, FPS: {self.fps}")
            return True
            
        except Exception as e:
            logger.error(f"加载视频失败: {e}")
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
        frame_processing_time = 0.0
        
        while not self.stop_preview:
            try:
                if self.is_playing and self.cap:
                    # 获取当前帧号
                    current_frame_number = int(self.current_position * self.fps)
                    
                    # 检查是否需要处理新帧
                    if current_frame_number != last_frame_number:
                        start_time = time.time()
                        
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
                            # 渲染帧
                            if self.config.enable_filters and self.current_filter != FilterType.NONE:
                                frame = self.render_engine.render_frame(frame)
                            
                            # 添加到缓冲区
                            with self.buffer_lock:
                                self.frame_buffer.append(frame)
                            
                            # 发射信号
                            self.frame_ready.emit(frame)
                            
                            last_frame_number = current_frame_number
                            self.frame_count_current += 1
                            
                            # 更新处理时间
                            processing_time = time.time() - start_time
                            frame_processing_time = (frame_processing_time * 0.9 + processing_time * 0.1)
                            
                            # 自适应质量调整
                            if self.adaptive_quality_enabled:
                                self._adjust_quality_based_on_performance(processing_time)
                
                # 控制帧率
                target_frame_time = 1.0 / self.fps
                actual_frame_time = time.time() - self.last_frame_time
                
                if actual_frame_time < target_frame_time:
                    sleep_time = target_frame_time - actual_frame_time
                    time.sleep(max(0, sleep_time))
                
                self.last_frame_time = time.time()
                
            except Exception as e:
                logger.error(f"预览线程错误: {e}")
                time.sleep(0.1)
    
    def _adjust_quality_based_on_performance(self, processing_time: float):
        """基于性能自适应调整质量"""
        target_frame_time = 1.0 / self.fps
        
        if processing_time > target_frame_time * 1.5:  # 处理时间超过目标时间的150%
            # 降低质量
            if self.config.render_quality == RenderQuality.ULTRA:
                self.config.render_quality = RenderQuality.HIGH
            elif self.config.render_quality == RenderQuality.HIGH:
                self.config.render_quality = RenderQuality.MEDIUM
            elif self.config.render_quality == RenderQuality.MEDIUM:
                self.config.render_quality = RenderQuality.LOW
            
            logger.debug(f"降低渲染质量至: {self.config.render_quality.value}")
            
        elif processing_time < target_frame_time * 0.5:  # 处理时间少于目标时间的50%
            # 提高质量
            if self.config.render_quality == RenderQuality.LOW:
                self.config.render_quality = RenderQuality.MEDIUM
            elif self.config.render_quality == RenderQuality.MEDIUM:
                self.config.render_quality = RenderQuality.HIGH
            elif self.config.render_quality == RenderQuality.HIGH:
                self.config.render_quality = RenderQuality.ULTRA
            
            logger.debug(f"提高渲染质量至: {self.config.render_quality.value}")
    
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
            logger.error(f"读取帧失败: {e}")
            return None
    
    def _update_preview(self):
        """更新预览显示"""
        try:
            # 从缓冲区获取最新帧
            with self.buffer_lock:
                if self.frame_buffer:
                    frame = self.frame_buffer[-1]
                    
                    # 转换为QImage
                    q_image = self._convert_to_qimage(frame)
                    
                    # 发射预览更新信号
                    self.preview_updated.emit(q_image)
                    
                    # 移除已处理的帧
                    self.frame_buffer.clear()
        except Exception as e:
            logger.error(f"更新预览失败: {e}")
    
    def _convert_to_qimage(self, frame: VideoFrame) -> QImage:
        """转换帧为QImage"""
        try:
            if frame.format == "BGR":
                height, width, channel = frame.data.shape
                bytes_per_line = 3 * width
                return QImage(frame.data.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            else:
                # 其他格式处理
                height, width = frame.data.shape[:2]
                return QImage(frame.data, width, height, QImage.Format.Format_RGB888)
        except Exception as e:
            logger.error(f"转换帧失败: {e}")
            return QImage()
    
    def _update_fps(self):
        """更新FPS统计"""
        current_time = time.time()
        time_diff = current_time - self.last_fps_time
        
        if time_diff > 0:
            self.stats["fps_actual"] = self.frame_count_current / time_diff
            self.frame_count_current = 0
            self.last_fps_time = current_time
    
    def _update_performance_stats(self):
        """更新性能统计"""
        try:
            # 获取内存使用
            process = psutil.Process()
            memory_info = process.memory_info()
            self.stats["memory_usage"] = memory_info.rss / (1024 * 1024)  # MB
            
            # 获取CPU使用
            cpu_percent = process.cpu_percent()
            self.stats["cpu_usage"] = cpu_percent
            
            # 获取缓存统计
            cache_stats = self.frame_cache.get_stats()
            self.stats["cache_hit_rate"] = cache_stats.get("hit_rate", 0.0)
            
            # 获取渲染统计
            render_stats = self.render_engine.get_stats()
            self.stats["dropped_frames"] = render_stats.get("dropped_frames", 0)
            
            # 更新渲染质量
            self.stats["render_quality"] = self.config.render_quality.value
            
            # 发射性能统计信号
            self.performance_stats.emit(self.stats.copy())
            
        except Exception as e:
            logger.error(f"更新性能统计失败: {e}")
    
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
        
        # 更新渲染引擎
        if filter_type != FilterType.NONE:
            self.render_engine.set_filter(filter_type.value.lower(), True, params)
        else:
            # 禁用所有滤镜
            for filter_config in self.render_engine.filter_pipeline:
                filter_config["enabled"] = False
        
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
        stats = self.stats.copy()
        
        # 添加缓存统计
        cache_stats = self.frame_cache.get_stats()
        stats.update(cache_stats)
        
        # 添加渲染统计
        render_stats = self.render_engine.get_stats()
        stats.update(render_stats)
        
        return stats
    
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
    
    def set_config(self, config: PreviewConfig):
        """设置预览配置"""
        self.config = config
        self.render_engine.config = config
        
        # 重新初始化缓存
        if hasattr(self, 'frame_cache'):
            self.frame_cache.max_size_mb = config.max_cache_size
    
    def enable_adaptive_quality(self, enabled: bool):
        """启用自适应质量"""
        self.adaptive_quality_enabled = enabled
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理优化版视频预览引擎资源")
        
        # 停止预览
        self.stop_preview = True
        
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.0)
        
        if self.cap:
            self.cap.release()
        
        if self.media_player:
            self.media_player.stop()
            self.media_player = None
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=False)
        
        # 清空缓存
        if hasattr(self, 'frame_cache'):
            self.frame_cache.clear()
        
        # 清空缓冲区
        with self.buffer_lock:
            self.frame_buffer.clear()
        
        logger.info("优化版视频预览引擎资源清理完成")


# 工厂函数
def create_optimized_video_preview_engine(config: PreviewConfig = None) -> OptimizedVideoPreviewEngine:
    """创建优化版视频预览引擎"""
    return OptimizedVideoPreviewEngine(config)


if __name__ == "__main__":
    # 测试代码
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel
    from PyQt6.QtCore import QTimer
    
    class PreviewTestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.init_ui()
            
        def init_ui(self):
            layout = QVBoxLayout(self)
            
            # 创建预览引擎
            config = PreviewConfig(
                render_quality=RenderQuality.MEDIUM,
                max_cache_size=200,
                max_fps=30
            )
            self.preview_engine = create_optimized_video_preview_engine(config)
            
            # 预览标签
            self.preview_label = QLabel()
            self.preview_label.setMinimumSize(640, 360)
            self.preview_label.setStyleSheet("background-color: black;")
            layout.addWidget(self.preview_label)
            
            # 状态标签
            self.status_label = QLabel("就绪")
            layout.addWidget(self.status_label)
            
            # 连接信号
            self.preview_engine.preview_updated.connect(self._on_preview_updated)
            self.preview_engine.performance_stats.connect(self._on_performance_stats)
            
            # 测试视频
            test_video = "test_video.mp4"
            if os.path.exists(test_video):
                self.preview_engine.load_video(test_video)
                self.preview_engine.play()
        
        def _on_preview_updated(self, q_image):
            """预览更新"""
            if not q_image.isNull():
                pixmap = QPixmap.fromImage(q_image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
        
        def _on_performance_stats(self, stats):
            """性能统计更新"""
            status_text = f"FPS: {stats.get('fps_actual', 0):.1f} | "
            status_text += f"缓存命中率: {stats.get('cache_hit_rate', 0):.2%} | "
            status_text += f"内存: {stats.get('memory_usage', 0):.1f}MB | "
            status_text += f"质量: {stats.get('render_quality', 'medium')}"
            self.status_label.setText(status_text)
    
    app = QApplication(sys.argv)
    
    widget = PreviewTestWidget()
    widget.setWindowTitle("优化版视频预览引擎测试")
    widget.resize(800, 600)
    widget.show()
    
    sys.exit(app.exec())