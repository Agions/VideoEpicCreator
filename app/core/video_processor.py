#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频处理核心引擎
提供完整的视频分析、处理和导出功能
"""

import cv2
import numpy as np
import ffmpeg
import os
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import tempfile
import subprocess


@dataclass
class VideoInfo:
    """视频信息"""
    path: str
    duration: float
    fps: float
    width: int
    height: int
    frame_count: int
    audio_channels: int
    audio_sample_rate: int
    file_size: int


@dataclass
class SceneInfo:
    """场景信息"""
    start_time: float
    end_time: float
    duration: float
    scene_type: str  # "dialogue", "action", "transition", "emotional"
    confidence: float
    key_frames: List[int]
    audio_features: Dict[str, float]
    visual_features: Dict[str, float]


@dataclass
class HighlightSegment:
    """精彩片段"""
    start_time: float
    end_time: float
    score: float
    highlight_type: str  # "action", "emotional", "dialogue", "climax"
    description: str
    key_moments: List[float]


class VideoProcessor(QObject):
    """视频处理器"""

    # 信号
    progress_updated = pyqtSignal(int)  # 进度更新
    status_updated = pyqtSignal(str)    # 状态更新
    processing_completed = pyqtSignal(str)  # 处理完成
    error_occurred = pyqtSignal(str)    # 错误发生

    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp(prefix="CineAIStudio_")

    def analyze_video(self, video_path: str) -> VideoInfo:
        """分析视频基本信息"""
        try:
            self.status_updated.emit("正在分析视频信息...")

            # 使用OpenCV获取视频信息
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise Exception(f"无法打开视频文件: {video_path}")

            # 获取基本信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            # 使用ffprobe获取音频信息
            try:
                probe = ffmpeg.probe(video_path)
                audio_stream = next((stream for stream in probe['streams']
                                   if stream['codec_type'] == 'audio'), None)

                audio_channels = int(audio_stream['channels']) if audio_stream else 0
                audio_sample_rate = int(audio_stream['sample_rate']) if audio_stream else 0
            except:
                audio_channels = 0
                audio_sample_rate = 0

            # 获取文件大小
            file_size = os.path.getsize(video_path)

            video_info = VideoInfo(
                path=video_path,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                frame_count=frame_count,
                audio_channels=audio_channels,
                audio_sample_rate=audio_sample_rate,
                file_size=file_size
            )

            self.status_updated.emit("视频信息分析完成")
            return video_info

        except Exception as e:
            self.error_occurred.emit(f"视频分析失败: {str(e)}")
            raise

    def detect_scenes(self, video_path: str, threshold: float = 0.3) -> List[SceneInfo]:
        """检测视频场景"""
        try:
            self.status_updated.emit("正在检测视频场景...")
            scenes = []

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("无法打开视频文件")

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            prev_frame = None
            scene_start = 0
            current_frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 转换为灰度图
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_frame is not None:
                    # 计算帧差
                    diff = cv2.absdiff(prev_frame, gray)
                    diff_score = np.mean(diff) / 255.0

                    # 检测场景切换
                    if diff_score > threshold:
                        scene_end = current_frame_idx / fps

                        if scene_end - scene_start > 1.0:  # 最小场景长度1秒
                            scene = SceneInfo(
                                start_time=scene_start,
                                end_time=scene_end,
                                duration=scene_end - scene_start,
                                scene_type=self._classify_scene_type(diff_score),
                                confidence=min(diff_score, 1.0),
                                key_frames=[int(scene_start * fps), int(scene_end * fps)],
                                audio_features={},
                                visual_features={"diff_score": diff_score}
                            )
                            scenes.append(scene)

                        scene_start = scene_end

                prev_frame = gray
                current_frame_idx += 1

                # 更新进度
                progress = int((current_frame_idx / frame_count) * 100)
                self.progress_updated.emit(progress)

            cap.release()

            # 添加最后一个场景
            if scene_start < (frame_count / fps):
                scene = SceneInfo(
                    start_time=scene_start,
                    end_time=frame_count / fps,
                    duration=(frame_count / fps) - scene_start,
                    scene_type="normal",
                    confidence=0.5,
                    key_frames=[int(scene_start * fps), frame_count],
                    audio_features={},
                    visual_features={}
                )
                scenes.append(scene)

            self.status_updated.emit(f"场景检测完成，共检测到 {len(scenes)} 个场景")
            return scenes

        except Exception as e:
            self.error_occurred.emit(f"场景检测失败: {str(e)}")
            raise

    def detect_highlights(self, video_path: str, min_duration: float = 2.0) -> List[HighlightSegment]:
        """检测精彩片段"""
        try:
            self.status_updated.emit("正在检测精彩片段...")
            highlights = []

            # 分析音频能量
            audio_highlights = self._analyze_audio_energy(video_path)

            # 分析视觉变化
            visual_highlights = self._analyze_visual_changes(video_path)

            # 合并和评分
            combined_highlights = self._combine_highlights(audio_highlights, visual_highlights)

            # 过滤和排序
            for highlight in combined_highlights:
                if highlight.duration >= min_duration:
                    highlights.append(highlight)

            # 按分数排序
            highlights.sort(key=lambda x: x.score, reverse=True)

            self.status_updated.emit(f"精彩片段检测完成，共检测到 {len(highlights)} 个片段")
            return highlights

        except Exception as e:
            self.error_occurred.emit(f"精彩片段检测失败: {str(e)}")
            raise

    def extract_audio(self, video_path: str, output_path: str = None) -> str:
        """提取音频"""
        try:
            if output_path is None:
                output_path = os.path.join(self.temp_dir, "extracted_audio.wav")

            self.status_updated.emit("正在提取音频...")

            # 使用ffmpeg提取音频
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )

            self.status_updated.emit("音频提取完成")
            return output_path

        except Exception as e:
            self.error_occurred.emit(f"音频提取失败: {str(e)}")
            raise

    def merge_audio_video(self, video_path: str, audio_path: str, output_path: str) -> str:
        """合并音频和视频"""
        try:
            self.status_updated.emit("正在合并音频和视频...")

            # 使用ffmpeg合并
            video_input = ffmpeg.input(video_path)
            audio_input = ffmpeg.input(audio_path)

            (
                ffmpeg
                .output(video_input, audio_input, output_path, vcodec='copy', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )

            self.status_updated.emit("音频视频合并完成")
            return output_path

        except Exception as e:
            self.error_occurred.emit(f"音频视频合并失败: {str(e)}")
            raise

    def _classify_scene_type(self, diff_score: float) -> str:
        """分类场景类型"""
        if diff_score > 0.7:
            return "action"
        elif diff_score > 0.5:
            return "transition"
        elif diff_score > 0.3:
            return "dialogue"
        else:
            return "normal"

    def _analyze_audio_energy(self, video_path: str) -> List[HighlightSegment]:
        """分析音频能量"""
        # 简化实现，实际应该使用librosa等音频处理库
        highlights = []

        # 模拟音频能量分析结果
        duration = self.analyze_video(video_path).duration
        segment_duration = 10.0  # 10秒一个片段

        for i in range(int(duration // segment_duration)):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)

            # 模拟能量分数
            score = np.random.uniform(0.3, 0.9)

            highlight = HighlightSegment(
                start_time=start_time,
                end_time=end_time,
                score=score,
                highlight_type="audio_energy",
                description=f"音频高能片段 {i+1}",
                key_moments=[start_time + 2, start_time + 5, start_time + 8]
            )
            highlights.append(highlight)

        return highlights

    def _analyze_visual_changes(self, video_path: str) -> List[HighlightSegment]:
        """分析视觉变化"""
        highlights = []

        # 模拟视觉变化分析
        duration = self.analyze_video(video_path).duration

        # 随机生成一些视觉高光时刻
        for i in range(3):
            start_time = np.random.uniform(0, duration - 5)
            end_time = start_time + np.random.uniform(3, 8)
            score = np.random.uniform(0.4, 0.8)

            highlight = HighlightSegment(
                start_time=start_time,
                end_time=end_time,
                score=score,
                highlight_type="visual_change",
                description=f"视觉精彩片段 {i+1}",
                key_moments=[start_time + 1]
            )
            highlights.append(highlight)

        return highlights

    def _combine_highlights(self, audio_highlights: List[HighlightSegment],
                          visual_highlights: List[HighlightSegment]) -> List[HighlightSegment]:
        """合并音频和视觉高光"""
        all_highlights = audio_highlights + visual_highlights

        # 简单合并，实际应该有更复杂的算法
        combined = []
        for highlight in all_highlights:
            if highlight.score > 0.5:  # 只保留高分片段
                combined.append(highlight)

        return combined
