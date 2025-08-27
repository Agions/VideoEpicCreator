#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from PyQt6.QtCore import QObject, pyqtSignal

from app.utils.thumbnail_generator import ThumbnailGenerator
from app.utils.ffmpeg_utils import FFmpegUtils


class VideoClip:
    """视频片段类"""
    
    def __init__(self, file_path, start_time=0, end_time=None, clip_id=None):
        self.file_path = file_path
        self.start_time = start_time  # 开始时间（毫秒）
        self.end_time = end_time  # 结束时间（毫秒），None表示到文件结尾
        self.clip_id = clip_id or self._generate_id()
        self.name = os.path.basename(file_path)
        self.duration = 0  # 时长（毫秒）
        self.thumbnail = None  # 缩略图路径
        self.metadata = {}  # 视频元数据
        
    def _generate_id(self):
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())
    
    def set_duration(self, duration):
        """设置视频时长"""
        self.duration = duration
        if self.end_time is None:
            self.end_time = duration
    
    def set_metadata(self, metadata):
        """设置视频元数据"""
        self.metadata = metadata
        
        # 从元数据中提取时长（如果有）
        if "duration" in metadata:
            self.set_duration(metadata["duration"])
    
    def set_thumbnail(self, thumbnail_path):
        """设置缩略图路径"""
        self.thumbnail = thumbnail_path
    
    def to_dict(self):
        """转换为字典，用于保存"""
        return {
            "file_path": self.file_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "clip_id": self.clip_id,
            "name": self.name,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        clip = cls(
            file_path=data["file_path"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            clip_id=data["clip_id"]
        )
        clip.name = data["name"]
        clip.duration = data["duration"]
        clip.thumbnail = data["thumbnail"]
        clip.metadata = data["metadata"]
        return clip


class VideoManager(QObject):
    """视频管理器类"""
    
    # 自定义信号
    video_added = pyqtSignal(VideoClip)  # 添加视频信号
    video_removed = pyqtSignal(int)  # 移除视频信号
    video_updated = pyqtSignal(int, VideoClip)  # 更新视频信号
    thumbnail_generated = pyqtSignal(VideoClip)  # 缩略图生成完成信号
    metadata_updated = pyqtSignal(VideoClip)  # 元数据更新信号
    
    def __init__(self, thumbnail_cache_dir=None, ffmpeg_path="ffmpeg"):
        super().__init__()
        self.videos = []  # 视频列表
        self.timeline_clips = []  # 时间线上的片段
        self.project_path = None  # 项目保存路径
        
        # 创建缩略图生成器
        self.thumbnail_generator = ThumbnailGenerator(thumbnail_cache_dir)
        self.thumbnail_generator.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumbnail_generator.thumbnail_error.connect(self._on_thumbnail_error)
        
        # 创建FFmpeg工具
        self.ffmpeg_utils = FFmpegUtils(ffmpeg_path)
        self.ffmpeg_utils.metadata_ready.connect(self._on_metadata_ready)
        self.ffmpeg_utils.metadata_error.connect(self._on_metadata_error)
        
    def add_video(self, file_path):
        """添加视频到视频库"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None
            
        # 创建视频片段
        clip = VideoClip(file_path)
        
        # 提取视频元数据
        self._extract_video_info(clip)
        
        # 生成缩略图
        self._generate_thumbnail(clip)
        
        # 添加到视频列表
        self.videos.append(clip)
        
        # 发射信号
        self.video_added.emit(clip)
        
        return clip
    
    def add_videos_batch(self, file_paths):
        """批量添加视频到视频库"""
        added_clips = []
        
        for file_path in file_paths:
            clip = self.add_video(file_path)
            if clip:
                added_clips.append(clip)
            
        return added_clips
    
    def remove_video(self, index):
        """从视频库中移除视频"""
        if 0 <= index < len(self.videos):
            self.videos.pop(index)
            self.video_removed.emit(index)
            return True
        return False
    
    def get_video(self, index):
        """获取指定索引的视频"""
        if 0 <= index < len(self.videos):
            return self.videos[index]
        return None
    
    def find_video_by_path(self, file_path):
        """通过文件路径查找视频"""
        for clip in self.videos:
            if clip.file_path == file_path:
                return clip
        return None
    
    def find_video_by_id(self, clip_id):
        """通过ID查找视频"""
        for clip in self.videos:
            if clip.clip_id == clip_id:
                return clip
        return None
    
    def add_to_timeline(self, clip, track_index=0, position=0):
        """添加片段到时间线"""
        timeline_clip = {
            "clip": clip,
            "track_index": track_index,
            "position": position
        }
        self.timeline_clips.append(timeline_clip)
        return timeline_clip
    
    def remove_from_timeline(self, clip_id):
        """从时间线移除片段"""
        for i, timeline_clip in enumerate(self.timeline_clips):
            if timeline_clip["clip"].clip_id == clip_id:
                self.timeline_clips.pop(i)
                return True
        return False
    
    def save_project(self, path):
        """保存项目"""
        project_data = {
            "videos": [clip.to_dict() for clip in self.videos],
            "timeline_clips": [
                {
                    "clip": clip["clip"].to_dict(),
                    "track_index": clip["track_index"],
                    "position": clip["position"]
                }
                for clip in self.timeline_clips
            ]
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)
            
        self.project_path = path
        return True
    
    def load_project(self, path):
        """加载项目"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                project_data = json.load(f)
                
            # 清空当前数据
            self.videos = []
            self.timeline_clips = []
            
            # 加载视频库
            for video_data in project_data["videos"]:
                clip = VideoClip.from_dict(video_data)
                self.videos.append(clip)
                self.video_added.emit(clip)
            
            # 加载时间线片段
            for timeline_data in project_data["timeline_clips"]:
                clip_data = timeline_data["clip"]
                clip = VideoClip.from_dict(clip_data)
                
                # 找到对应的原始视频
                for video in self.videos:
                    if video.clip_id == clip.clip_id:
                        clip = video
                        break
                
                timeline_clip = {
                    "clip": clip,
                    "track_index": timeline_data["track_index"],
                    "position": timeline_data["position"]
                }
                self.timeline_clips.append(timeline_clip)
                
            self.project_path = path
            return True
        except Exception as e:
            print(f"加载项目失败: {e}")
            return False
    
    def export_to_jianying(self, output_path):
        """导出到剪映格式"""
        # TODO: 实现导出到剪映格式
        return False
    
    def generate_missing_thumbnails(self):
        """为没有缩略图的视频生成缩略图"""
        for clip in self.videos:
            if not clip.thumbnail or not os.path.exists(clip.thumbnail):
                self._generate_thumbnail(clip)
    
    def refresh_thumbnails(self):
        """刷新所有视频的缩略图"""
        for clip in self.videos:
            self._generate_thumbnail(clip)
            
    def refresh_metadata(self, clip):
        """刷新视频元数据"""
        self._extract_video_info(clip)
    
    def _generate_thumbnail(self, clip):
        """为指定视频生成缩略图"""
        # 使用视频30%位置的帧作为缩略图
        time_pos = None
        if clip.duration > 0:
            time_pos = (clip.duration / 1000) * 0.3  # 转换为秒
        
        # 生成缩略图
        self.thumbnail_generator.generate_thumbnail(clip.file_path, time_pos)
    
    def _on_thumbnail_ready(self, video_path, thumbnail_path):
        """缩略图生成完成回调"""
        # 查找对应的视频
        clip = self.find_video_by_path(video_path)
        if clip:
            clip.set_thumbnail(thumbnail_path)
            # 发射缩略图生成完成信号
            self.thumbnail_generated.emit(clip)
    
    def _on_thumbnail_error(self, video_path, error_msg):
        """缩略图生成错误回调"""
        print(f"生成缩略图失败，视频: {video_path}, 错误: {error_msg}")
    
    def _on_metadata_ready(self, video_path, metadata):
        """元数据提取完成回调"""
        # 查找对应的视频
        clip = self.find_video_by_path(video_path)
        if clip:
            clip.set_metadata(metadata)
            # 发射元数据更新信号
            self.metadata_updated.emit(clip)
    
    def _on_metadata_error(self, video_path, error_msg):
        """元数据提取错误回调"""
        print(f"提取元数据失败，视频: {video_path}, 错误: {error_msg}")
    
    def _extract_video_info(self, clip):
        """提取视频信息（时长、元数据等）"""
        # 尝试使用FFmpeg提取视频信息
        if self.ffmpeg_utils.ffmpeg_available:
            # 启动异步提取
            self.ffmpeg_utils.extract_metadata(clip.file_path)
        else:
            # FFmpeg不可用，使用模拟数据
            self._use_mock_data(clip)
    
    def _use_mock_data(self, clip):
        """使用模拟数据（FFmpeg不可用时）"""
        import random
        mock_metadata = {
            "duration": random.randint(10000, 60000),  # 10-60秒
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "codec": "h264",
            "bit_rate": 5000000,  # 5Mbps
            "size": random.randint(10000000, 100000000)  # 10-100MB
        }
        clip.set_metadata(mock_metadata)
        self.metadata_updated.emit(clip) 