#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级视频编解码管理器 - 专业的视频编解码和格式转换管理
"""

import os
import subprocess
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil

logger = logging.getLogger(__name__)


class CodecType(Enum):
    """编解码器类型"""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


class CodecProfile(Enum):
    """编解码器配置文件"""
    HIGH = "high"
    MAIN = "main"
    BASELINE = "baseline"
    HIGH10 = "high10"
    HIGH422 = "high422"
    HIGH444 = "high444"


class VideoPreset(Enum):
    """视频编码预设"""
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"


@dataclass
class CodecInfo:
    """编解码器信息"""
    name: str
    type: CodecType
    description: str
    capabilities: List[str]
    profiles: List[CodecProfile]
    hardware_acceleration: bool = False
    max_resolution: str = "8K"
    max_fps: int = 120
    max_bitrate: int = 100000000  # 100 Mbps
    supported_formats: List[str] = field(default_factory=list)


@dataclass
class EncodingParams:
    """编码参数"""
    codec: str
    profile: CodecProfile = CodecProfile.HIGH
    preset: VideoPreset = VideoPreset.MEDIUM
    crf: int = 23
    bitrate: Optional[int] = None
    max_bitrate: Optional[int] = None
    bufsize: Optional[int] = None
    keyframe_interval: int = 250
    threads: int = 0  # 0 = auto
    hardware_acceleration: bool = True
    pixel_format: str = "yuv420p"
    color_space: str = "bt709"
    color_range: str = "tv"
    tune: Optional[str] = None  # film, animation, grain, stillimage, fastdecode, zerolatency


@dataclass
class DecodingParams:
    """解码参数"""
    codec: str
    hardware_acceleration: bool = True
    threads: int = 0  # 0 = auto
    skip_frame: int = 0  # 0 = no skip
    lowres: int = 0  # 0 = full resolution
    fast: bool = False
    correct_ts: bool = True


class VideoCodecManager:
    """视频编解码管理器"""
    
    def __init__(self, ffmpeg_path: str, ffprobe_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # 编解码器信息缓存
        self.codec_cache: Dict[str, CodecInfo] = {}
        self.hardware_codecs: List[str] = []
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 编码会话管理
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = threading.Lock()
        
        # 性能统计
        self.encoding_stats = {
            "total_encodes": 0,
            "successful_encodes": 0,
            "failed_encodes": 0,
            "total_encoding_time": 0.0,
            "average_encoding_speed": 0.0,
            "hardware_acceleration_usage": 0
        }
        
        # 初始化编解码器信息
        self._initialize_codecs()
        
        logger.info("视频编解码管理器初始化完成")
    
    def _initialize_codecs(self):
        """初始化编解码器信息"""
        try:
            # 获取所有编码器
            encoders_result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True, text=True, timeout=30
            )
            
            # 获取所有解码器
            decoders_result = subprocess.run(
                [self.ffmpeg_path, "-decoders"],
                capture_output=True, text=True, timeout=30
            )
            
            # 解析编码器信息
            self._parse_codec_info(encoders_result.stdout, decoders_result.stdout)
            
            # 识别硬件加速编解码器
            self._identify_hardware_codecs()
            
        except Exception as e:
            logger.error(f"初始化编解码器信息失败: {e}")
    
    def _parse_codec_info(self, encoders_output: str, decoders_output: str):
        """解析编解码器信息"""
        # 视频编解码器定义
        video_codecs = {
            "libx264": CodecInfo(
                name="libx264",
                type=CodecType.VIDEO,
                description="H.264/AVC 编码器",
                capabilities=["encoding", "high_quality", "wide_range"],
                profiles=[CodecProfile.BASELINE, CodecProfile.MAIN, CodecProfile.HIGH],
                max_resolution="4K",
                max_fps=60,
                supported_formats=["mp4", "mov", "mkv", "flv"]
            ),
            "libx265": CodecInfo(
                name="libx265",
                type=CodecType.VIDEO,
                description="H.265/HEVC 编码器",
                capabilities=["encoding", "high_quality", "high_efficiency"],
                profiles=[CodecProfile.MAIN, CodecProfile.HIGH10, CodecProfile.HIGH422],
                max_resolution="8K",
                max_fps=120,
                supported_formats=["mp4", "mkv", "hevc"]
            ),
            "h264_nvenc": CodecInfo(
                name="h264_nvenc",
                type=CodecType.VIDEO,
                description="NVIDIA H.264 硬件编码器",
                capabilities=["encoding", "hardware_acceleration", "real_time"],
                profiles=[CodecProfile.BASELINE, CodecProfile.MAIN, CodecProfile.HIGH],
                hardware_acceleration=True,
                max_resolution="4K",
                max_fps=120,
                supported_formats=["mp4", "mov", "mkv"]
            ),
            "hevc_nvenc": CodecInfo(
                name="hevc_nvenc",
                type=CodecType.VIDEO,
                description="NVIDIA H.265 硬件编码器",
                capabilities=["encoding", "hardware_acceleration", "high_efficiency"],
                profiles=[CodecProfile.MAIN, CodecProfile.HIGH10],
                hardware_acceleration=True,
                max_resolution="8K",
                max_fps=60,
                supported_formats=["mp4", "mkv", "hevc"]
            ),
            "h264_qsv": CodecInfo(
                name="h264_qsv",
                type=CodecType.VIDEO,
                description="Intel Quick Sync H.264 硬件编码器",
                capabilities=["encoding", "hardware_acceleration", "low_power"],
                profiles=[CodecProfile.BASELINE, CodecProfile.MAIN, CodecProfile.HIGH],
                hardware_acceleration=True,
                max_resolution="4K",
                max_fps=60,
                supported_formats=["mp4", "mov", "mkv"]
            ),
            "libvpx": CodecInfo(
                name="libvpx",
                type=CodecType.VIDEO,
                description="VP8 编码器",
                capabilities=["encoding", "web_optimized", "royalty_free"],
                profiles=[CodecProfile.BASELINE],
                max_resolution="4K",
                max_fps=60,
                supported_formats=["webm", "mkv"]
            ),
            "libvpx-vp9": CodecInfo(
                name="libvpx-vp9",
                type=CodecType.VIDEO,
                description="VP9 编码器",
                capabilities=["encoding", "web_optimized", "high_efficiency"],
                profiles=[CodecProfile.MAIN],
                max_resolution="8K",
                max_fps=60,
                supported_formats=["webm", "mkv"]
            )
        }
        
        # 音频编解码器定义
        audio_codecs = {
            "aac": CodecInfo(
                name="aac",
                type=CodecType.AUDIO,
                description="AAC 音频编码器",
                capabilities=["encoding", "high_quality", "wide_compatibility"],
                profiles=[CodecProfile.MAIN],
                max_bitrate=256000,  # 256 kbps
                supported_formats=["mp4", "mov", "mkv", "flv"]
            ),
            "libmp3lame": CodecInfo(
                name="libmp3lame",
                type=CodecType.AUDIO,
                description="MP3 音频编码器",
                capabilities=["encoding", "wide_compatibility", "variable_bitrate"],
                profiles=[CodecProfile.MAIN],
                max_bitrate=320000,  # 320 kbps
                supported_formats=["mp3", "mp4", "mkv", "avi"]
            ),
            "libopus": CodecInfo(
                name="libopus",
                type=CodecType.AUDIO,
                description="Opus 音频编码器",
                capabilities=["encoding", "high_quality", "low_latency"],
                profiles=[CodecProfile.MAIN],
                max_bitrate=510000,  # 510 kbps
                supported_formats=["webm", "mkv", "opus"]
            )
        }
        
        # 合并所有编解码器
        self.codec_cache.update(video_codecs)
        self.codec_cache.update(audio_codecs)
        
        logger.info(f"加载了 {len(self.codec_cache)} 个编解码器信息")
    
    def _identify_hardware_codecs(self):
        """识别硬件加速编解码器"""
        hardware_indicators = ["nvenc", "qsv", "amf", "vaapi", "videotoolbox"]
        
        for codec_name, codec_info in self.codec_cache.items():
            if any(indicator in codec_name.lower() for indicator in hardware_indicators):
                self.hardware_codecs.append(codec_name)
                codec_info.hardware_acceleration = True
        
        logger.info(f"识别到 {len(self.hardware_codecs)} 个硬件加速编解码器")
    
    def get_codec_info(self, codec_name: str) -> Optional[CodecInfo]:
        """获取编解码器信息"""
        return self.codec_cache.get(codec_name)
    
    def list_available_codecs(self, codec_type: Optional[CodecType] = None) -> List[CodecInfo]:
        """列出可用的编解码器"""
        if codec_type:
            return [info for info in self.codec_cache.values() if info.type == codec_type]
        return list(self.codec_cache.values())
    
    def get_hardware_codecs(self) -> List[str]:
        """获取硬件加速编解码器列表"""
        return self.hardware_codecs.copy()
    
    def recommend_codec(self, requirements: Dict[str, Any]) -> Optional[str]:
        """根据需求推荐编解码器"""
        target_format = requirements.get("format", "mp4")
        hardware_acceleration = requirements.get("hardware_acceleration", True)
        quality = requirements.get("quality", "high")
        max_resolution = requirements.get("max_resolution", "4K")
        
        # 根据格式推荐
        if target_format == "webm":
            return "libvpx-vp9"
        elif target_format == "mp4":
            if hardware_acceleration and "hevc_nvenc" in self.hardware_codecs:
                return "hevc_nvenc"
            elif hardware_acceleration and "h264_nvenc" in self.hardware_codecs:
                return "h264_nvenc"
            elif max_resolution == "8K":
                return "libx265"
            else:
                return "libx264"
        elif target_format == "mkv":
            return "libx265"
        
        return None
    
    def build_encoding_command(self, input_path: str, output_path: str, 
                            params: EncodingParams) -> List[str]:
        """构建编码命令"""
        cmd = [self.ffmpeg_path, "-i", input_path]
        
        # 添加硬件加速
        if params.hardware_acceleration and params.codec in self.hardware_codecs:
            if "nvenc" in params.codec:
                cmd.extend(["-hwaccel", "cuda"])
            elif "qsv" in params.codec:
                cmd.extend(["-hwaccel", "qsv"])
        
        # 视频编码参数
        video_params = []
        
        # 编码器
        video_params.extend(["-c:v", params.codec])
        
        # 预设
        if params.preset and "nvenc" not in params.codec:
            video_params.extend(["-preset", params.preset.value])
        
        # 配置文件
        if params.profile:
            video_params.extend(["-profile:v", params.profile.value])
        
        # CRF 或比特率
        if params.bitrate:
            video_params.extend(["-b:v", f"{params.bitrate}k"])
            if params.max_bitrate:
                video_params.extend(["-maxrate:v", f"{params.max_bitrate}k"])
            if params.bufsize:
                video_params.extend(["-bufsize:v", f"{params.bufsize}k"])
        else:
            video_params.extend(["-crf", str(params.crf)])
        
        # 关键帧间隔
        video_params.extend(["-g", str(params.keyframe_interval)])
        
        # 线程数
        if params.threads > 0:
            video_params.extend(["-threads", str(params.threads)])
        
        # 像素格式
        video_params.extend(["-pix_fmt", params.pixel_format])
        
        # 色彩空间
        if params.color_space:
            video_params.extend(["-colorspace", params.color_space])
        
        # 调优参数
        if params.tune:
            video_params.extend(["-tune", params.tune])
        
        # 添加视频参数到命令
        cmd.extend(video_params)
        
        # 音频参数（默认使用AAC）
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        
        # 输出文件
        cmd.extend(["-y", output_path])
        
        return cmd
    
    def build_decoding_command(self, input_path: str, params: DecodingParams) -> List[str]:
        """构建解码命令"""
        cmd = [self.ffmpeg_path]
        
        # 硬件加速
        if params.hardware_acceleration:
            cmd.extend(["-hwaccel", "auto"])
        
        # 解码参数
        if params.threads > 0:
            cmd.extend(["-threads", str(params.threads)])
        
        if params.skip_frame > 0:
            cmd.extend(["-skip_frame", str(params.skip_frame)])
        
        if params.lowres > 0:
            cmd.extend(["-lowres", str(params.lowres)])
        
        if params.fast:
            cmd.extend(["-fast"])
        
        if not params.correct_ts:
            cmd.extend(["-correct_ts", "0"])
        
        # 输入文件
        cmd.extend(["-i", input_path])
        
        # 输出到null（仅解码）
        cmd.extend(["-f", "null", "-"])
        
        return cmd
    
    def encode_video(self, input_path: str, output_path: str, params: EncodingParams, 
                   progress_callback=None) -> Dict[str, Any]:
        """编码视频"""
        start_time = time.time()
        session_id = f"encode_{int(time.time() * 1000)}"
        
        try:
            # 创建编码会话
            with self.session_lock:
                self.active_sessions[session_id] = {
                    "input_path": input_path,
                    "output_path": output_path,
                    "params": params,
                    "start_time": start_time,
                    "status": "encoding"
                }
            
            # 构建编码命令
            cmd = self.build_encoding_command(input_path, output_path, params)
            
            logger.info(f"开始编码: {input_path} -> {output_path}")
            logger.debug(f"编码命令: {' '.join(cmd)}")
            
            # 执行编码
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            # 更新统计
            self.encoding_stats["total_encodes"] += 1
            processing_time = time.time() - start_time
            self.encoding_stats["total_encoding_time"] += processing_time
            
            if result.returncode == 0:
                # 编码成功
                self.encoding_stats["successful_encodes"] += 1
                
                if params.hardware_acceleration:
                    self.encoding_stats["hardware_acceleration_usage"] += 1
                
                # 计算编码速度
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    encoding_speed = file_size / (processing_time * 1024 * 1024)  # MB/s
                    self.encoding_stats["average_encoding_speed"] = (
                        (self.encoding_stats["average_encoding_speed"] * (self.encoding_stats["successful_encodes"] - 1) + encoding_speed) 
                        / self.encoding_stats["successful_encodes"]
                    )
                
                logger.info(f"编码完成: {output_path}, 耗时: {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "processing_time": processing_time,
                    "session_id": session_id
                }
            else:
                # 编码失败
                self.encoding_stats["failed_encodes"] += 1
                logger.error(f"编码失败: {result.stderr}")
                
                return {
                    "success": False,
                    "error": result.stderr,
                    "session_id": session_id
                }
        
        except subprocess.TimeoutExpired:
            self.encoding_stats["failed_encodes"] += 1
            logger.error(f"编码超时: {input_path}")
            
            return {
                "success": False,
                "error": "编码超时",
                "session_id": session_id
            }
        
        except Exception as e:
            self.encoding_stats["failed_encodes"] += 1
            logger.error(f"编码异常: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
        
        finally:
            # 清理会话
            with self.session_lock:
                self.active_sessions.pop(session_id, None)
    
    def decode_video(self, input_path: str, params: DecodingParams) -> Dict[str, Any]:
        """解码视频"""
        start_time = time.time()
        
        try:
            # 构建解码命令
            cmd = self.build_decoding_command(input_path, params)
            
            logger.info(f"开始解码: {input_path}")
            logger.debug(f"解码命令: {' '.join(cmd)}")
            
            # 执行解码
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            processing_time = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"解码完成: {input_path}, 耗时: {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "processing_time": processing_time
                }
            else:
                logger.error(f"解码失败: {result.stderr}")
                
                return {
                    "success": False,
                    "error": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            logger.error(f"解码超时: {input_path}")
            
            return {
                "success": False,
                "error": "解码超时"
            }
        
        except Exception as e:
            logger.error(f"解码异常: {e}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def transcode_video(self, input_path: str, output_path: str, 
                       input_params: DecodingParams, output_params: EncodingParams) -> Dict[str, Any]:
        """转码视频"""
        start_time = time.time()
        
        try:
            # 构建转码命令
            cmd = [self.ffmpeg_path]
            
            # 解码参数
            if input_params.hardware_acceleration:
                cmd.extend(["-hwaccel", "auto"])
            
            # 输入文件
            cmd.extend(["-i", input_path])
            
            # 编码参数
            video_params = []
            video_params.extend(["-c:v", output_params.codec])
            
            if output_params.bitrate:
                video_params.extend(["-b:v", f"{output_params.bitrate}k"])
            else:
                video_params.extend(["-crf", str(output_params.crf)])
            
            if output_params.preset and "nvenc" not in output_params.codec:
                video_params.extend(["-preset", output_params.preset.value])
            
            cmd.extend(video_params)
            
            # 音频参数
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
            
            # 输出文件
            cmd.extend(["-y", output_path])
            
            logger.info(f"开始转码: {input_path} -> {output_path}")
            logger.debug(f"转码命令: {' '.join(cmd)}")
            
            # 执行转码
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            processing_time = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"转码完成: {output_path}, 耗时: {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "processing_time": processing_time
                }
            else:
                logger.error(f"转码失败: {result.stderr}")
                
                return {
                    "success": False,
                    "error": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            logger.error(f"转码超时: {input_path}")
            
            return {
                "success": False,
                "error": "转码超时"
            }
        
        except Exception as e:
            logger.error(f"转码异常: {e}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_encoding_stats(self) -> Dict[str, Any]:
        """获取编码统计信息"""
        stats = self.encoding_stats.copy()
        
        # 计算成功率
        if stats["total_encodes"] > 0:
            stats["success_rate"] = stats["successful_encodes"] / stats["total_encodes"]
        else:
            stats["success_rate"] = 0.0
        
        # 计算硬件加速使用率
        if stats["successful_encodes"] > 0:
            stats["hardware_acceleration_rate"] = stats["hardware_acceleration_usage"] / stats["successful_encodes"]
        else:
            stats["hardware_acceleration_rate"] = 0.0
        
        return stats
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """获取活跃的编码会话"""
        with self.session_lock:
            return self.active_sessions.copy()
    
    def cancel_session(self, session_id: str) -> bool:
        """取消编码会话"""
        with self.session_lock:
            if session_id in self.active_sessions:
                # 注意：这里需要实现更复杂的取消机制
                # 当前只是标记为取消
                self.active_sessions[session_id]["status"] = "cancelled"
                logger.info(f"已取消会话: {session_id}")
                return True
            return False
    
    def optimize_encoding_params(self, video_info: Dict[str, Any], 
                               requirements: Dict[str, Any]) -> EncodingParams:
        """优化编码参数"""
        # 根据视频信息和需求优化参数
        width = video_info.get("width", 1920)
        height = video_info.get("height", 1080)
        duration = video_info.get("duration", 60)
        
        # 计算目标比特率
        target_bitrate = self._calculate_target_bitrate(width, height, requirements)
        
        # 选择编解码器
        codec = self.recommend_codec(requirements)
        
        # 选择预设
        preset = self._select_preset(requirements.get("speed", "medium"))
        
        # 选择CRF值
        crf = self._select_crf(requirements.get("quality", "medium"))
        
        return EncodingParams(
            codec=codec,
            preset=preset,
            crf=crf,
            bitrate=target_bitrate,
            hardware_acceleration=requirements.get("hardware_acceleration", True)
        )
    
    def _calculate_target_bitrate(self, width: int, height: int, 
                                 requirements: Dict[str, Any]) -> int:
        """计算目标比特率"""
        quality = requirements.get("quality", "medium")
        pixels = width * height
        
        # 基础比特率计算
        if quality == "low":
            bitrate_per_pixel = 0.05
        elif quality == "medium":
            bitrate_per_pixel = 0.1
        elif quality == "high":
            bitrate_per_pixel = 0.2
        else:
            bitrate_per_pixel = 0.1
        
        target_bitrate = int(pixels * bitrate_per_pixel / 1000)  # kbps
        
        # 限制比特率范围
        return max(500, min(target_bitrate, 50000))  # 500 kbps - 50 Mbps
    
    def _select_preset(self, speed: str) -> VideoPreset:
        """选择编码预设"""
        speed_map = {
            "ultrafast": VideoPreset.ULTRAFAST,
            "superfast": VideoPreset.SUPERFAST,
            "veryfast": VideoPreset.VERYFAST,
            "faster": VideoPreset.FASTER,
            "fast": VideoPreset.FAST,
            "medium": VideoPreset.MEDIUM,
            "slow": VideoPreset.SLOW,
            "slower": VideoPreset.SLOWER,
            "veryslow": VideoPreset.VERYSLOW
        }
        
        return speed_map.get(speed, VideoPreset.MEDIUM)
    
    def _select_crf(self, quality: str) -> int:
        """选择CRF值"""
        quality_map = {
            "low": 28,
            "medium": 23,
            "high": 20,
            "ultra": 18
        }
        
        return quality_map.get(quality, 23)
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理编解码管理器资源")
        
        # 取消所有活跃会话
        with self.session_lock:
            for session_id in list(self.active_sessions.keys()):
                self.cancel_session(session_id)
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        logger.info("编解码管理器资源清理完成")