"""
视频处理核心引擎
提供专业的视频编辑和处理功能
"""

import asyncio
import subprocess
import json
import os
import logging
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import numpy as np
import cv2

from .base import BaseModel
from .event_system import event_bus, Event, EventType

logger = logging.getLogger(__name__)


class VideoFormat(Enum):
    """视频格式枚举"""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"


class VideoQuality(Enum):
    """视频质量枚举"""
    LOW = "low"      # 480p
    MEDIUM = "medium" # 720p
    HIGH = "high"    # 1080p
    ULTRA = "ultra"  # 4K


class OperationType(Enum):
    """操作类型枚举"""
    TRIM = "trim"
    SCALE = "scale"
    CROP = "crop"
    ROTATE = "rotate"
    SPEED = "speed"
    FADE = "fade"
    MERGE = "merge"
    SPLIT = "split"
    ADD_AUDIO = "add_audio"
    ADD_SUBTITLE = "add_subtitle"
    ADD_FILTER = "add_filter"


@dataclass
class VideoInfo(BaseModel):
    """视频信息数据类"""
    id: str = ""
    path: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate: int = 0
    codec: str = ""
    audio_codec: str = ""
    size: int = 0
    has_audio: bool = True
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class ProcessingOptions(BaseModel):
    """处理选项数据类"""
    id: str = ""
    output_path: str = ""
    format: VideoFormat = VideoFormat.MP4
    quality: VideoQuality = VideoQuality.HIGH
    resolution: Optional[Tuple[int, int]] = None
    bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    preset: str = "medium"
    threads: int = 4
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class VideoOperation(BaseModel):
    """视频操作数据类"""
    id: str = ""
    type: OperationType = OperationType.TRIM
    parameters: Dict[str, Any] = None
    priority: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class TimelineClip(BaseModel):
    """时间线片段"""
    id: str = ""
    video_path: str = ""
    start_time: float = 0.0  # 在原视频中的开始时间
    end_time: float = 0.0    # 在原视频中的结束时间
    timeline_start: float = 0.0  # 在时间线上的开始时间
    timeline_end: float = 0.0    # 在时间线上的结束时间
    operations: List[VideoOperation] = None
    effects: List[Dict[str, Any]] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.operations is None:
            self.operations = []
        if self.effects is None:
            self.effects = []
        if self.metadata is None:
            self.metadata = {}


class VideoEngine:
    """视频处理引擎"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.temp_dir = tempfile.gettempdir()
        self._logger = logging.getLogger(__name__)
        self._processing = False
        self._current_task = None
        
    async def initialize(self):
        """初始化视频引擎"""
        # 检查FFmpeg是否可用
        try:
            await self._run_command([self.ffmpeg_path, "-version"])
            await self._run_command([self.ffprobe_path, "-version"])
            self._logger.info("Video engine initialized successfully")
        except Exception as e:
            self._logger.error(f"FFmpeg not found: {e}")
            raise RuntimeError("FFmpeg is required but not found")
    
    async def get_video_info(self, video_path: str) -> VideoInfo:
        """获取视频详细信息"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        try:
            result = await self._run_command(cmd)
            data = json.loads(result)
            
            # 解析视频流
            video_stream = None
            audio_stream = None
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    audio_stream = stream
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            format_info = data.get("format", {})
            
            # 计算FPS
            fps_str = video_stream.get("r_frame_rate", "30/1")
            fps = eval(fps_str) if "/" in fps_str else float(fps_str)
            
            return VideoInfo(
                id=f"video_{hash(video_path)}",
                path=video_path,
                duration=float(format_info.get("duration", 0)),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                fps=fps,
                bitrate=int(format_info.get("bit_rate", 0)),
                codec=video_stream.get("codec_name", "unknown"),
                audio_codec=audio_stream.get("codec_name", "unknown") if audio_stream else "none",
                size=int(format_info.get("size", 0)),
                has_audio=audio_stream is not None,
                audio_sample_rate=int(audio_stream.get("sample_rate", 44100)) if audio_stream else 44100,
                audio_channels=int(audio_stream.get("channels", 2)) if audio_stream else 2
            )
        except Exception as e:
            self._logger.error(f"Failed to get video info: {e}")
            raise
    
    async def process_video(self, 
                           input_path: str,
                           operations: List[VideoOperation],
                           options: ProcessingOptions) -> str:
        """处理视频"""
        if self._processing:
            raise RuntimeError("Another video is being processed")
        
        self._processing = True
        
        try:
            # 发布处理开始事件
            await event_bus.publish(Event(
                type=EventType.VIDEO_PROCESSED,
                source="video_engine",
                data={"status": "started", "input_path": input_path}
            ))
            
            # 构建FFmpeg命令
            cmd = [self.ffmpeg_path, "-i", input_path]
            
            # 按优先级排序操作
            sorted_operations = sorted(operations, key=lambda x: x.priority)
            
            # 添加处理操作
            for operation in sorted_operations:
                cmd.extend(self._build_operation_args(operation))
            
            # 添加输出选项
            cmd.extend(self._build_output_args(options))
            
            cmd.append(options.output_path)
            
            self._logger.info(f"Processing video with command: {' '.join(cmd)}")
            
            # 执行处理
            await self._run_command(cmd)
            
            # 验证输出文件
            if not os.path.exists(options.output_path):
                raise FileNotFoundError("Output video file not created")
            
            # 发布处理完成事件
            await event_bus.publish(Event(
                type=EventType.VIDEO_PROCESSED,
                source="video_engine",
                data={"status": "completed", "output_path": options.output_path}
            ))
            
            return options.output_path
            
        except Exception as e:
            self._logger.error(f"Video processing failed: {e}")
            
            # 发布错误事件
            await event_bus.publish(Event(
                type=EventType.ERROR_OCCURRED,
                source="video_engine",
                data={"error": str(e), "operation": "video_processing"}
            ))
            
            raise
        finally:
            self._processing = False
    
    async def process_timeline(self, 
                              timeline_clips: List[TimelineClip],
                              options: ProcessingOptions) -> str:
        """处理时间线视频"""
        if not timeline_clips:
            raise ValueError("No timeline clips provided")
        
        self._processing = True
        
        try:
            # 创建临时文件列表
            concat_file = os.path.join(self.temp_dir, "concat_list.txt")
            
            with open(concat_file, "w") as f:
                for clip in timeline_clips:
                    # 为每个片段创建处理后的临时文件
                    temp_clip_path = os.path.join(self.temp_dir, f"clip_{clip.id}.mp4")
                    
                    # 处理单个片段
                    if clip.operations:
                        await self.process_video(
                            clip.video_path,
                            clip.operations,
                            ProcessingOptions(
                                output_path=temp_clip_path,
                                format=options.format,
                                quality=options.quality
                            )
                        )
                    else:
                        # 直接复制片段
                        await self._run_command([
                            self.ffmpeg_path,
                            "-i", clip.video_path,
                            "-c", "copy",
                            temp_clip_path
                        ])
                    
                    # 添加到concat列表
                    f.write(f"file '{temp_clip_path}'\n")
                    f.write(f"duration {clip.timeline_end - clip.timeline_start}\n")
            
            # 使用concat demuxer合并视频
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                options.output_path
            ]
            
            await self._run_command(cmd)
            
            # 清理临时文件
            if os.path.exists(concat_file):
                os.remove(concat_file)
            
            return options.output_path
            
        except Exception as e:
            self._logger.error(f"Timeline processing failed: {e}")
            raise
        finally:
            self._processing = False
    
    async def extract_frames(self, 
                            video_path: str,
                            output_dir: str,
                            interval: float = 1.0,
                            max_frames: int = 100,
                            start_time: float = 0,
                            end_time: float = None) -> List[str]:
        """提取视频帧"""
        os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-ss", str(start_time),
            "-i", video_path
        ]
        
        if end_time:
            cmd.extend(["-t", str(end_time - start_time)])
        
        cmd.extend([
            "-vf", f"fps=1/{interval}",
            "-frames:v", str(max_frames),
            "-q:v", "2",  # 高质量
            f"{output_dir}/frame_%04d.jpg"
        ])
        
        try:
            await self._run_command(cmd)
            
            # 返回提取的帧文件列表
            frames = []
            for i in range(1, max_frames + 1):
                frame_path = f"{output_dir}/frame_{i:04d}.jpg"
                if os.path.exists(frame_path):
                    frames.append(frame_path)
                else:
                    break
            
            self._logger.info(f"Extracted {len(frames)} frames")
            return frames
            
        except Exception as e:
            self._logger.error(f"Frame extraction failed: {e}")
            raise
    
    async def extract_audio(self, 
                           video_path: str,
                           output_path: str,
                           format: str = "mp3",
                           bitrate: str = "128k") -> str:
        """提取音频"""
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vn",  # 忽略视频
            "-acodec", "libmp3lame" if format == "mp3" else "aac",
            "-ab", bitrate,
            output_path
        ]
        
        try:
            await self._run_command(cmd)
            return output_path
        except Exception as e:
            self._logger.error(f"Audio extraction failed: {e}")
            raise
    
    async def add_subtitles(self, 
                           video_path: str,
                           subtitle_path: str,
                           output_path: str,
                           style: Dict[str, Any] = None) -> str:
        """添加字幕"""
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-i", subtitle_path,
            "-c:v", "copy",
            "-c:a", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=chi",
            output_path
        ]
        
        try:
            await self._run_command(cmd)
            return output_path
        except Exception as e:
            self._logger.error(f"Subtitle addition failed: {e}")
            raise
    
    async def create_preview(self, 
                            video_path: str,
                            output_path: str,
                            duration: float = 10.0,
                            quality: VideoQuality = VideoQuality.MEDIUM) -> str:
        """创建预览视频"""
        # 获取视频信息
        video_info = await self.get_video_info(video_path)
        
        # 计算预览片段
        start_time = max(0, video_info.duration / 2 - duration / 2)
        
        cmd = [
            self.ffmpeg_path,
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "28",
            output_path
        ]
        
        try:
            await self._run_command(cmd)
            return output_path
        except Exception as e:
            self._logger.error(f"Preview creation failed: {e}")
            raise
    
    async def analyze_video_content(self, video_path: str) -> Dict[str, Any]:
        """分析视频内容"""
        try:
            # 获取视频信息
            video_info = await self.get_video_info(video_path)
            
            # 提取关键帧进行分析
            frames = await self.extract_frames(
                video_path,
                os.path.join(self.temp_dir, "analysis"),
                interval=2.0,
                max_frames=50
            )
            
            # 简单的内容分析
            content_analysis = {
                "video_info": asdict(video_info),
                "scene_changes": len(frames),
                "estimated_complexity": "medium",
                "recommended_operations": []
            }
            
            # 基于视频特征推荐操作
            if video_info.duration > 300:  # 5分钟以上
                content_analysis["recommended_operations"].append("highlight_extraction")
            
            if video_info.width > 1920 or video_info.height > 1080:
                content_analysis["recommended_operations"].append("resolution_optimization")
            
            if not video_info.has_audio:
                content_analysis["recommended_operations"].append("background_music")
            
            return content_analysis
            
        except Exception as e:
            self._logger.error(f"Video content analysis failed: {e}")
            raise
    
    async def cancel_processing(self):
        """取消当前处理"""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._processing = False
            self._logger.info("Video processing cancelled")
    
    async def _run_command(self, cmd: List[str]) -> str:
        """运行命令"""
        try:
            self._logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._current_task = process
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Command failed with return code {process.returncode}: {error_msg}")
            
            return stdout.decode() if stdout else ""
            
        except asyncio.CancelledError:
            self._logger.info("Command execution cancelled")
            raise
        except Exception as e:
            self._logger.error(f"Command execution failed: {e}")
            raise
        finally:
            self._current_task = None
    
    def _build_operation_args(self, operation: VideoOperation) -> List[str]:
        """构建操作参数"""
        args = []
        op_type = operation.type
        params = operation.parameters
        
        if op_type == OperationType.TRIM:
            start = params.get("start", 0)
            end = params.get("end")
            args.extend(["-ss", str(start)])
            if end:
                args.extend(["-t", str(end - start)])
        
        elif op_type == OperationType.SCALE:
            width = params.get("width")
            height = params.get("height")
            if width and height:
                args.extend(["-vf", f"scale={width}:{height}"])
        
        elif op_type == OperationType.CROP:
            x = params.get("x", 0)
            y = params.get("y", 0)
            width = params.get("width")
            height = params.get("height")
            args.extend(["-vf", f"crop={width}:{height}:{x}:{y}"])
        
        elif op_type == OperationType.ROTATE:
            angle = params.get("angle", 0)
            if angle == 90:
                args.extend(["-vf", "transpose=1"])
            elif angle == 180:
                args.extend(["-vf", "transpose=1,transpose=1"])
            elif angle == 270:
                args.extend(["-vf", "transpose=2"])
        
        elif op_type == OperationType.SPEED:
            speed = params.get("speed", 1.0)
            args.extend(["-vf", f"setpts={1.0/speed}*PTS"])
            args.extend(["-af", f"atempo={speed}"])
        
        elif op_type == OperationType.FADE:
            fade_type = params.get("type", "in")
            duration = params.get("duration", 1.0)
            if fade_type == "in":
                args.extend(["-vf", f"fade=in:0:{duration}"])
            else:
                args.extend(["-vf", f"fade=out:st={params.get('start_time', 0)}:d={duration}"])
        
        elif op_type == OperationType.ADD_FILTER:
            filter_name = params.get("filter")
            filter_params = params.get("params", {})
            filter_str = filter_name
            if filter_params:
                filter_str += "=" + ":".join([f"{k}={v}" for k, v in filter_params.items()])
            args.extend(["-vf", filter_str])
        
        return args
    
    def _build_output_args(self, options: ProcessingOptions) -> List[str]:
        """构建输出参数"""
        args = []
        
        # 设置编码器
        if options.format == VideoFormat.MP4:
            args.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif options.format == VideoFormat.WEBM:
            args.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
        
        # 设置预设
        args.extend(["-preset", options.preset])
        
        # 设置线程数
        args.extend(["-threads", str(options.threads)])
        
        # 设置质量和比特率
        if options.quality == VideoQuality.LOW:
            args.extend(["-crf", "28"])
            if not options.bitrate:
                args.extend(["-b:v", "1000k"])
        elif options.quality == VideoQuality.MEDIUM:
            args.extend(["-crf", "23"])
            if not options.bitrate:
                args.extend(["-b:v", "2000k"])
        elif options.quality == VideoQuality.HIGH:
            args.extend(["-crf", "20"])
            if not options.bitrate:
                args.extend(["-b:v", "4000k"])
        elif options.quality == VideoQuality.ULTRA:
            args.extend(["-crf", "18"])
            if not options.bitrate:
                args.extend(["-b:v", "8000k"])
        
        # 自定义比特率
        if options.bitrate:
            args.extend(["-b:v", f"{options.bitrate}k"])
        
        if options.audio_bitrate:
            args.extend(["-b:a", f"{options.audio_bitrate}k"])
        
        # 设置分辨率
        if options.resolution:
            width, height = options.resolution
            args.extend(["-vf", f"scale={width}:{height}"])
        
        return args
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的视频格式"""
        return [fmt.value for fmt in VideoFormat]
    
    def get_supported_operations(self) -> List[str]:
        """获取支持的操作类型"""
        return [op.value for op in OperationType]
    
    async def is_processing(self) -> bool:
        """检查是否正在处理视频"""
        return self._processing