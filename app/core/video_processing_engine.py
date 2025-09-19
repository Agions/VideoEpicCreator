#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业视频处理引擎 - CineAIStudio核心视频处理系统
基于FFmpeg、OpenCV和硬件加速的高性能视频处理引擎
"""

import os
import sys
import json
import time
import logging
import threading
import subprocess
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import tempfile
import shutil

from .hardware_acceleration import HardwareAccelerationManager, HardwareType
from .effects_engine import EffectsEngine, EffectType
from .batch_processor import BatchProcessor, BatchTask, BatchTaskType
from .video_codec_manager import VideoCodecManager
from .video_optimizer import VideoOptimizer

logger = logging.getLogger(__name__)


class VideoFormat(Enum):
    """视频格式"""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"
    WMV = "wmv"


class VideoCodec(Enum):
    """视频编码器"""
    H264 = "h264"
    H265 = "hevc"
    VP9 = "vp9"
    AV1 = "av1"
    PRORES = "prores"
    DNxHD = "dnxhd"


class AudioCodec(Enum):
    """音频编码器"""
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    FLAC = "flac"
    WAV = "wav"


class VideoQuality(Enum):
    """视频质量预设"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    LOSSLESS = "lossless"


class ProcessingMode(Enum):
    """处理模式"""
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    CUSTOM = "custom"


@dataclass
class VideoInfo:
    """视频信息"""
    file_path: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate: int = 0
    format: str = ""
    video_codec: str = ""
    audio_codec: str = ""
    audio_channels: int = 0
    audio_sample_rate: int = 0
    audio_bitrate: int = 0
    size_bytes: int = 0
    has_audio: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingConfig:
    """处理配置"""
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.AAC
    quality: VideoQuality = VideoQuality.MEDIUM
    mode: ProcessingMode = ProcessingMode.BALANCED
    hardware_acceleration: bool = True
    multi_threading: bool = True
    proxy_enabled: bool = True
    proxy_resolution: Tuple[int, int] = (1280, 720)
    temp_dir: str = ""
    output_dir: str = ""
    
    # 编码参数
    crf: int = 23
    preset: str = "medium"
    bitrate: str = ""
    audio_bitrate: str = "128k"
    
    # 高级参数
    keyframe_interval: int = 250
    gop_size: int = 250
    b_frames: int = 3
    refs: int = 3
    tune: str = ""
    profile: str = ""
    level: str = ""


@dataclass
class TimelineClip:
    """时间轴片段"""
    clip_id: str
    file_path: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    track_index: int = 0
    position: float = 0.0
    effects: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    volume: float = 1.0
    opacity: float = 1.0
    speed: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineTrack:
    """时间轴轨道"""
    track_id: str
    track_type: str = "video"  # video, audio, subtitle
    clips: List[TimelineClip] = field(default_factory=list)
    is_enabled: bool = True
    is_locked: bool = False
    volume: float = 1.0
    opacity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineProject:
    """时间轴项目"""
    project_id: str
    name: str
    description: str = ""
    video_tracks: List[TimelineTrack] = field(default_factory=list)
    audio_tracks: List[TimelineTrack] = field(default_factory=list)
    subtitle_tracks: List[TimelineTrack] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)


class VideoProcessingEngine:
    """专业视频处理引擎"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # 初始化组件
        self.hardware_manager = HardwareAccelerationManager(ffmpeg_path)
        self.effects_engine = EffectsEngine()
        self.batch_processor = BatchProcessor()
        self.codec_manager = VideoCodecManager(ffmpeg_path, ffprobe_path)
        self.video_optimizer = VideoOptimizer(ffmpeg_path, ffprobe_path)
        
        # 处理状态
        self.is_processing = False
        self.processing_cancel_flag = False
        self.processing_progress = 0.0
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # 缓存和代理
        self.video_cache: Dict[str, VideoInfo] = {}
        self.proxy_cache: Dict[str, str] = {}
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successful_processes": 0,
            "failed_processes": 0,
            "total_processing_time": 0.0,
            "average_speedup": 1.0
        }
        
        logger.info("视频处理引擎初始化完成")
    
    def get_video_info(self, file_path: str) -> VideoInfo:
        """获取视频信息"""
        if file_path in self.video_cache:
            return self.video_cache[file_path]
        
        try:
            # 使用ffprobe获取视频信息
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise Exception(f"获取视频信息失败: {result.stderr}")
            
            data = json.loads(result.stdout)
            
            # 解析视频流
            video_stream = None
            audio_stream = None
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    audio_stream = stream
            
            # 创建视频信息对象
            format_info = data.get("format", {})
            video_info = VideoInfo(
                file_path=file_path,
                duration=float(format_info.get("duration", 0)),
                size_bytes=int(format_info.get("size", 0)),
                format=format_info.get("format_name", "")
            )
            
            if video_stream:
                video_info.width = int(video_stream.get("width", 0))
                video_info.height = int(video_stream.get("height", 0))
                video_info.fps = eval(video_stream.get("r_frame_rate", "30/1"))
                video_info.video_codec = video_stream.get("codec_name", "")
                video_info.bitrate = int(video_stream.get("bit_rate", 0))
                video_info.metadata = video_stream.get("tags", {})
            
            if audio_stream:
                video_info.has_audio = True
                video_info.audio_codec = audio_stream.get("codec_name", "")
                video_info.audio_channels = int(audio_stream.get("channels", 0))
                video_info.audio_sample_rate = int(audio_stream.get("sample_rate", 0))
                video_info.audio_bitrate = int(audio_stream.get("bit_rate", 0))
            
            # 缓存结果
            self.video_cache[file_path] = video_info
            
            logger.info(f"获取视频信息: {file_path}")
            return video_info
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {file_path}, 错误: {e}")
            raise
    
    def create_proxy_file(self, file_path: str, resolution: Tuple[int, int] = (1280, 720)) -> str:
        """创建代理文件"""
        if file_path in self.proxy_cache:
            return self.proxy_cache[file_path]
        
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="cineai_proxy_")
            proxy_path = os.path.join(temp_dir, f"proxy_{os.path.basename(file_path)}")
            
            # 构建代理文件生成命令
            cmd = [
                self.ffmpeg_path,
                "-i", file_path,
                "-vf", f"scale={resolution[0]}:{resolution[1]}",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "28",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y", proxy_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise Exception(f"创建代理文件失败: {result.stderr}")
            
            # 缓存代理文件路径
            self.proxy_cache[file_path] = proxy_path
            
            logger.info(f"创建代理文件: {file_path} -> {proxy_path}")
            return proxy_path
            
        except Exception as e:
            logger.error(f"创建代理文件失败: {file_path}, 错误: {e}")
            raise
    
    def process_video(self, input_path: str, output_path: str, config: ProcessingConfig) -> bool:
        """处理单个视频文件"""
        start_time = time.time()
        
        try:
            # 获取推荐硬件
            recommended_hw = self.hardware_manager.recommend_hardware(
                "video_encoding", 
                {"codecs": [config.video_codec.value]}
            )
            
            # 获取硬件加速参数
            accel_params = self.hardware_manager.get_acceleration_params(
                recommended_hw, 
                config.video_codec.value
            )
            
            # 构建处理命令
            cmd = self._build_processing_command(input_path, output_path, config, accel_params)
            
            # 执行处理
            self.is_processing = True
            self.processing_cancel_flag = False
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                processing_time = time.time() - start_time
                self._record_processing_success(recommended_hw, processing_time)
                
                logger.info(f"视频处理完成: {input_path} -> {output_path}")
                return True
            else:
                raise Exception(f"视频处理失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self._record_processing_failure()
            logger.error(f"视频处理超时: {input_path}")
            return False
        except Exception as e:
            self._record_processing_failure()
            logger.error(f"视频处理失败: {input_path}, 错误: {e}")
            return False
        finally:
            self.is_processing = False
    
    def _build_processing_command(self, input_path: str, output_path: str, 
                               config: ProcessingConfig, accel_params: Dict[str, Any]) -> List[str]:
        """构建处理命令"""
        cmd = [self.ffmpeg_path]
        
        # 硬件加速输入
        if config.hardware_acceleration and accel_params.get("hwaccel"):
            cmd.extend(["-hwaccel", accel_params["hwaccel"]])
        
        # 输入文件
        cmd.extend(["-i", input_path])
        
        # 视频编码参数
        if config.video_codec == VideoCodec.H264:
            video_codec = "libx264"
        elif config.video_codec == VideoCodec.H265:
            video_codec = "libx265"
        elif config.video_codec == VideoCodec.VP9:
            video_codec = "libvpx-vp9"
        elif config.video_codec == VideoCodec.AV1:
            video_codec = "libsvtav1"
        else:
            video_codec = config.video_codec.value
        
        cmd.extend(["-c:v", video_codec])
        
        # 质量参数
        if config.quality == VideoQuality.LOW:
            cmd.extend(["-crf", "28", "-preset", "fast"])
        elif config.quality == VideoQuality.MEDIUM:
            cmd.extend(["-crf", "23", "-preset", "medium"])
        elif config.quality == VideoQuality.HIGH:
            cmd.extend(["-crf", "20", "-preset", "slow"])
        elif config.quality == VideoQuality.ULTRA:
            cmd.extend(["-crf", "18", "-preset", "veryslow"])
        
        # 自定义参数
        if config.mode == ProcessingMode.CUSTOM:
            if config.crf:
                cmd.extend(["-crf", str(config.crf)])
            if config.preset:
                cmd.extend(["-preset", config.preset])
            if config.bitrate:
                cmd.extend(["-b:v", config.bitrate])
        
        # 硬件加速参数
        if config.hardware_acceleration and "extra_params" in accel_params:
            cmd.extend(accel_params["extra_params"])
        
        # 音频编码参数
        cmd.extend(["-c:a", config.audio_codec.value])
        if config.audio_bitrate:
            cmd.extend(["-b:a", config.audio_bitrate])
        
        # 多线程
        if config.multi_threading:
            cmd.extend(["-threads", "0"])
        
        # 输出文件
        cmd.extend(["-y", output_path])
        
        return cmd
    
    def process_timeline(self, project: TimelineProject, output_path: str, config: ProcessingConfig) -> bool:
        """处理时间轴项目"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="cineai_timeline_")
            
            # 处理每个轨道
            processed_tracks = []
            
            # 处理视频轨道
            for track in project.video_tracks:
                if not track.is_enabled:
                    continue
                
                track_output = os.path.join(temp_dir, f"video_track_{track.track_id}.mp4")
                if self._process_track(track, track_output, config):
                    processed_tracks.append(track_output)
            
            # 处理音频轨道
            for track in project.audio_tracks:
                if not track.is_enabled:
                    continue
                
                track_output = os.path.join(temp_dir, f"audio_track_{track.track_id}.wav")
                if self._process_track(track, track_output, config):
                    processed_tracks.append(track_output)
            
            # 合并轨道
            if len(processed_tracks) > 1:
                return self._merge_tracks(processed_tracks, output_path, config)
            elif len(processed_tracks) == 1:
                # 单个轨道直接复制
                shutil.copy2(processed_tracks[0], output_path)
                return True
            else:
                logger.warning("没有可处理的轨道")
                return False
                
        except Exception as e:
            logger.error(f"处理时间轴失败: {e}")
            return False
        finally:
            # 清理临时文件
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _process_track(self, track: TimelineTrack, output_path: str, config: ProcessingConfig) -> bool:
        """处理单个轨道"""
        try:
            if not track.clips:
                return False
            
            # 创建临时文件列表
            temp_dir = tempfile.mkdtemp(prefix="cineai_track_")
            file_list_path = os.path.join(temp_dir, "file_list.txt")
            
            processed_clips = []
            
            for clip in track.clips:
                # 处理单个片段
                clip_output = os.path.join(temp_dir, f"clip_{clip.clip_id}.mp4")
                
                if self._process_clip(clip, clip_output, config):
                    processed_clips.append(clip_output)
            
            # 创建文件列表
            with open(file_list_path, 'w') as f:
                for clip_path in processed_clips:
                    f.write(f"file '{clip_path}'\n")
            
            # 合并片段
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", file_list_path,
                "-c", "copy",
                "-y", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"处理轨道失败: {e}")
            return False
    
    def _process_clip(self, clip: TimelineClip, output_path: str, config: ProcessingConfig) -> bool:
        """处理单个片段"""
        try:
            # 获取视频信息
            video_info = self.get_video_info(clip.file_path)
            
            # 构建处理命令
            cmd = [self.ffmpeg_path]
            
            # 输入文件
            cmd.extend(["-i", clip.file_path])
            
            # 时间范围
            if clip.start_time > 0 or clip.end_time > 0:
                start_time = clip.start_time
                duration = clip.end_time - clip.start_time if clip.end_time > 0 else video_info.duration
                cmd.extend(["-ss", str(start_time), "-t", str(duration)])
            
            # 速度调整
            if clip.speed != 1.0:
                cmd.extend(["-filter:v", f"setpts={1.0/clip.speed}*PTS"])
                cmd.extend(["-filter:a", f"atempo={clip.speed}"])
            
            # 音量调整
            if clip.volume != 1.0:
                cmd.extend(["-filter:a", f"volume={clip.volume}"])
            
            # 输出文件
            cmd.extend(["-y", output_path])
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"处理片段失败: {e}")
            return False
    
    def _merge_tracks(self, track_files: List[str], output_path: str, config: ProcessingConfig) -> bool:
        """合并多个轨道"""
        try:
            if len(track_files) == 0:
                return False
            elif len(track_files) == 1:
                shutil.copy2(track_files[0], output_path)
                return True
            
            # 构建合并命令
            cmd = [self.ffmpeg_path]
            
            # 添加所有输入文件
            for track_file in track_files:
                cmd.extend(["-i", track_file])
            
            # 复杂过滤器
            filter_complex = []
            for i, track_file in enumerate(track_files):
                filter_complex.append(f"[{i}:v]copy[v{i}];[{i}:a]copy[a{i}]")
            
            # 合并视频和音频
            filter_complex.append(f"[{''.join([f'[v{i}]' for i in range(len(track_files))])}]concat=n={len(track_files)}:v=1[outv]")
            filter_complex.append(f"[{''.join([f'[a{i}]' for i in range(len(track_files))])}]concat=n={len(track_files)}:a=1[outa]")
            
            cmd.extend(["-filter_complex", "".join(filter_complex)])
            cmd.extend(["-map", "[outv]", "-map", "[outa]"])
            
            # 输出文件
            cmd.extend(["-y", output_path])
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"合并轨道失败: {e}")
            return False
    
    def apply_effects(self, input_path: str, output_path: str, effects: List[Dict[str, Any]]) -> bool:
        """应用特效"""
        try:
            # 使用特效引擎处理
            return self.effects_engine.render_effects(input_path, output_path, effects)
            
        except Exception as e:
            logger.error(f"应用特效失败: {e}")
            return False
    
    def add_watermark(self, input_path: str, watermark_path: str, output_path: str, 
                     position: str = "overlay=10:10", opacity: float = 1.0) -> bool:
        """添加水印"""
        try:
            # 构建水印命令
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-i", watermark_path,
                "-filter_complex", f"[1]format=rgba,colorchannelmixer=aa={opacity}[wm];[0][wm]{position}",
                "-c:a", "copy",
                "-y", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"添加水印失败: {e}")
            return False
    
    def stabilize_video(self, input_path: str, output_path: str) -> bool:
        """视频防抖"""
        try:
            # 第一步：分析视频运动
            temp_dir = tempfile.mkdtemp(prefix="cineai_stabilize_")
            transforms_file = os.path.join(temp_dir, "transforms.trf")
            
            cmd1 = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", "vidstabdetect=file=" + transforms_file,
                "-f", "null",
                "-"
            ]
            
            result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=600)
            if result1.returncode != 0:
                raise Exception(f"视频分析失败: {result1.stderr}")
            
            # 第二步：应用防抖
            cmd2 = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", "vidstabtransform=input=" + transforms_file + ":smoothing=30",
                "-c:a", "copy",
                "-y", output_path
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result2.returncode == 0
            
        except Exception as e:
            logger.error(f"视频防抖失败: {e}")
            return False
    
    def create_thumbnail(self, input_path: str, output_path: str, timestamp: float = 0.0, 
                        size: Tuple[int, int] = (320, 180)) -> bool:
        """创建缩略图"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-ss", str(timestamp),
                "-i", input_path,
                "-vframes", "1",
                "-vf", f"scale={size[0]}:{size[1]}",
                "-y", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")
            return False
    
    def extract_frames(self, input_path: str, output_dir: str, fps: float = 1.0, 
                      format: str = "jpg") -> bool:
        """提取视频帧"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", f"fps={fps}",
                os.path.join(output_dir, f"frame_%04d.{format}")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"提取视频帧失败: {e}")
            return False
    
    def optimize_video(self, input_path: str, output_path: str, config: ProcessingConfig) -> bool:
        """优化视频"""
        try:
            return self.video_optimizer.optimize_video(input_path, output_path, config)
            
        except Exception as e:
            logger.error(f"优化视频失败: {e}")
            return False
    
    def _record_processing_success(self, hardware_type: HardwareType, processing_time: float):
        """记录处理成功"""
        self.stats["total_processed"] += 1
        self.stats["successful_processes"] += 1
        self.stats["total_processing_time"] += processing_time
        
        # 记录硬件加速
        self.hardware_manager.record_acceleration(hardware_type, True, processing_time)
        
        logger.info(f"视频处理成功，耗时: {processing_time:.2f}s")
    
    def _record_processing_failure(self):
        """记录处理失败"""
        self.stats["total_processed"] += 1
        self.stats["failed_processes"] += 1
        
        logger.error("视频处理失败")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        # 计算成功率
        total = stats["total_processed"]
        if total > 0:
            stats["success_rate"] = stats["successful_processes"] / total
        else:
            stats["success_rate"] = 0.0
        
        # 计算平均处理时间
        if stats["successful_processes"] > 0:
            stats["average_processing_time"] = stats["total_processing_time"] / stats["successful_processes"]
        else:
            stats["average_processing_time"] = 0.0
        
        # 添加硬件统计
        stats["hardware_stats"] = self.hardware_manager.get_performance_stats()
        
        return stats
    
    def cancel_processing(self):
        """取消处理"""
        self.processing_cancel_flag = True
        self.is_processing = False
        
        # 取消特效处理
        self.effects_engine.cancel_render()
        
        # 取消批量处理
        self.batch_processor.pause_processing()
        
        logger.info("已取消视频处理")
    
    def set_callbacks(self, progress_callback=None, completion_callback=None, error_callback=None):
        """设置回调函数"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理视频处理引擎资源")
        
        # 取消所有处理
        self.cancel_processing()
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        # 清理组件
        self.hardware_manager.cleanup()
        self.effects_engine.cancel_render()
        self.batch_processor.cleanup()
        
        # 清理缓存
        self.video_cache.clear()
        self.proxy_cache.clear()
        
        logger.info("视频处理引擎资源清理完成")


# 工厂函数
def create_video_processing_engine(ffmpeg_path: str = "ffmpeg", 
                                ffprobe_path: str = "ffprobe") -> VideoProcessingEngine:
    """创建视频处理引擎"""
    return VideoProcessingEngine(ffmpeg_path, ffprobe_path)


if __name__ == "__main__":
    # 测试代码
    engine = create_video_processing_engine()
    
    # 测试获取视频信息
    test_video = "test_video.mp4"
    if os.path.exists(test_video):
        info = engine.get_video_info(test_video)
        print(f"视频信息: {info}")
        
        # 测试创建缩略图
        engine.create_thumbnail(test_video, "thumbnail.jpg")
        
        # 测试优化视频
        config = ProcessingConfig()
        engine.optimize_video(test_video, "optimized_video.mp4", config)
    
    engine.cleanup()