#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映项目文件解析器
负责解析和转换项目数据到剪映格式
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from app.core.video_manager import VideoClip
# from app.ai.content_generator import GeneratedContent, ContentSegment

# 占位类定义
class GeneratedContent:
    """AI生成内容占位类"""
    def __init__(self, title, video=None, audio=None, segments=None):
        self.title = title
        self.video = video
        self.audio = audio
        self.segments = segments or []

class ContentSegment:
    """内容片段占位类"""
    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time


@dataclass
class JianYingClip:
    """剪映片段数据结构"""
    id: str
    type: str  # video, audio, image, text
    source_path: str
    start_time: float
    end_time: float
    duration: float
    x: float = 0
    y: float = 0
    width: float = 1920
    height: float = 1080
    rotation: float = 0
    opacity: float = 1.0
    volume: float = 1.0
    speed: float = 1.0
    effects: List[Dict] = None
    transitions: List[Dict] = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []
        if self.transitions is None:
            self.transitions = []


@dataclass
class JianYingTrack:
    """剪映轨道数据结构"""
    id: str
    type: str  # video, audio, text
    clips: List[JianYingClip]
    enabled: bool = True
    locked: bool = False
    visible: bool = True
    volume: float = 1.0
    
    def __post_init__(self):
        if self.clips is None:
            self.clips = []


@dataclass
class JianYingProject:
    """剪映项目数据结构"""
    id: str
    name: str
    version: str
    create_time: str
    modify_time: str
    duration: float
    resolution: Dict[str, int]
    frame_rate: float
    tracks: List[JianYingTrack]
    effects: List[Dict] = None
    transitions: List[Dict] = None
    audio_tracks: List[Dict] = None
    text_tracks: List[Dict] = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []
        if self.transitions is None:
            self.transitions = []
        if self.audio_tracks is None:
            self.audio_tracks = []
        if self.text_tracks is None:
            self.text_tracks = []


class JianYingProjectParser:
    """剪映项目文件解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_formats = {
            'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp'],
            'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
            'text': ['.txt', '.srt', '.ass', '.lrc']
        }
        
        # 剪映特效映射
        self.effect_mapping = {
            'fade_in': {'type': 'fade', 'direction': 'in'},
            'fade_out': {'type': 'fade', 'direction': 'out'},
            'zoom_in': {'type': 'scale', 'direction': 'in'},
            'zoom_out': {'type': 'scale', 'direction': 'out'},
            'slide_left': {'type': 'slide', 'direction': 'left'},
            'slide_right': {'type': 'slide', 'direction': 'right'},
            'slide_up': {'type': 'slide', 'direction': 'up'},
            'slide_down': {'type': 'slide', 'direction': 'down'}
        }
        
        # 剪映转场映射
        self.transition_mapping = {
            'fade': {'type': 'fade', 'duration': 1.0},
            'dissolve': {'type': 'dissolve', 'duration': 1.0},
            'slide': {'type': 'slide', 'duration': 1.0},
            'zoom': {'type': 'zoom', 'duration': 1.0},
            'wipe': {'type': 'wipe', 'duration': 1.0}
        }
    
    def parse_project(self, project_data: Union[VideoClip, GeneratedContent, Dict[str, Any], Any]) -> JianYingProject:
        """
        解析项目数据到剪映格式
        
        Args:
            project_data: 项目数据
            
        Returns:
            JianYingProject: 剪映项目对象
        """
        try:
            self.logger.info("开始解析项目数据")
            
            # 生成项目ID
            project_id = str(uuid.uuid4())
            
            # 解析基本信息
            if isinstance(project_data, VideoClip):
                return self._parse_video_clip(project_data, project_id)
            elif isinstance(project_data, GeneratedContent):
                return self._parse_generated_content(project_data, project_id)
            elif isinstance(project_data, dict):
                return self._parse_dict_project(project_data, project_id)
            elif hasattr(project_data, 'file_path') and hasattr(project_data, 'duration'):
                # 支持类似VideoClip的对象
                return self._parse_video_clip_like(project_data, project_id)
            else:
                raise ValueError(f"不支持的项目数据类型: {type(project_data)}")
                
        except Exception as e:
            self.logger.error(f"项目解析失败: {e}")
            raise
    
    def _parse_video_clip(self, video_clip: VideoClip, project_id: str) -> JianYingProject:
        """解析视频片段项目"""
        # 创建视频轨道
        video_track = JianYingTrack(
            id=str(uuid.uuid4()),
            type='video',
            clips=[self._create_video_clip(video_clip)]
        )
        
        # 创建项目
        project = JianYingProject(
            id=project_id,
            name=video_clip.name or "未命名项目",
            version="4.0.0",
            create_time=datetime.now().isoformat(),
            modify_time=datetime.now().isoformat(),
            duration=video_clip.duration,
            resolution={'width': 1920, 'height': 1080},
            frame_rate=30.0,
            tracks=[video_track]
        )
        
        return project
    
    def _parse_video_clip_like(self, video_clip, project_id: str) -> JianYingProject:
        """解析类似VideoClip的对象"""
        # 创建视频轨道
        video_track = JianYingTrack(
            id=str(uuid.uuid4()),
            type='video',
            clips=[self._create_video_clip_like(video_clip)]
        )
        
        # 创建项目
        project = JianYingProject(
            id=project_id,
            name=getattr(video_clip, 'name', '未命名项目'),
            version="4.0.0",
            create_time=datetime.now().isoformat(),
            modify_time=datetime.now().isoformat(),
            duration=getattr(video_clip, 'duration', 0),
            resolution={'width': 1920, 'height': 1080},
            frame_rate=30.0,
            tracks=[video_track]
        )
        
        return project
    
    def _parse_generated_content(self, content: GeneratedContent, project_id: str) -> JianYingProject:
        """解析AI生成内容项目"""
        tracks = []
        
        # 主视频轨道
        if content.video:
            video_track = JianYingTrack(
                id=str(uuid.uuid4()),
                type='video',
                clips=[self._create_video_clip(content.video)]
            )
            tracks.append(video_track)
        
        # 音频轨道
        if content.audio:
            audio_track = JianYingTrack(
                id=str(uuid.uuid4()),
                type='audio',
                clips=[self._create_audio_clip(content.audio)]
            )
            tracks.append(audio_track)
        
        # 字幕轨道
        if content.segments:
            text_clips = []
            for segment in content.segments:
                text_clip = self._create_text_clip(segment)
                if text_clip:
                    text_clips.append(text_clip)
            
            if text_clips:
                text_track = JianYingTrack(
                    id=str(uuid.uuid4()),
                    type='text',
                    clips=text_clips
                )
                tracks.append(text_track)
        
        # 计算总时长
        total_duration = content.video.duration if content.video else 0
        
        project = JianYingProject(
            id=project_id,
            name=content.title or "AI生成项目",
            version="4.0.0",
            create_time=datetime.now().isoformat(),
            modify_time=datetime.now().isoformat(),
            duration=total_duration,
            resolution={'width': 1920, 'height': 1080},
            frame_rate=30.0,
            tracks=tracks
        )
        
        return project
    
    def _parse_dict_project(self, project_dict: Dict[str, Any], project_id: str) -> JianYingProject:
        """解析字典格式项目"""
        tracks = []
        
        # 解析视频片段
        clips = project_dict.get('clips', [])
        video_clips = []
        for clip_data in clips:
            if clip_data.get('type') == 'video':
                video_clip = self._parse_dict_clip(clip_data)
                if video_clip:
                    video_clips.append(video_clip)
        
        if video_clips:
            video_track = JianYingTrack(
                id=str(uuid.uuid4()),
                type='video',
                clips=video_clips
            )
            tracks.append(video_track)
        
        # 解析音频片段
        audio_clips = []
        for clip_data in clips:
            if clip_data.get('type') == 'audio':
                audio_clip = self._parse_dict_clip(clip_data)
                if audio_clip:
                    audio_clips.append(audio_clip)
        
        if audio_clips:
            audio_track = JianYingTrack(
                id=str(uuid.uuid4()),
                type='audio',
                clips=audio_clips
            )
            tracks.append(audio_track)
        
        # 解析文本片段
        text_clips = []
        for clip_data in clips:
            if clip_data.get('type') == 'text':
                text_clip = self._parse_dict_clip(clip_data)
                if text_clip:
                    text_clips.append(text_clip)
        
        if text_clips:
            text_track = JianYingTrack(
                id=str(uuid.uuid4()),
                type='text',
                clips=text_clips
            )
            tracks.append(text_track)
        
        # 解析项目信息
        project = JianYingProject(
            id=project_id,
            name=project_dict.get('name', '未命名项目'),
            version="4.0.0",
            create_time=datetime.now().isoformat(),
            modify_time=datetime.now().isoformat(),
            duration=project_dict.get('duration', 0),
            resolution=project_dict.get('resolution', {'width': 1920, 'height': 1080}),
            frame_rate=project_dict.get('frame_rate', 30.0),
            tracks=tracks
        )
        
        return project
    
    def _parse_dict_clip(self, clip_data: Dict[str, Any]) -> Optional[JianYingClip]:
        """解析字典格式片段"""
        try:
            clip = JianYingClip(
                id=clip_data.get('id', str(uuid.uuid4())),
                type=clip_data.get('type', 'video'),
                source_path=clip_data.get('source_path', ''),
                start_time=clip_data.get('start_time', 0),
                end_time=clip_data.get('end_time', 0),
                duration=clip_data.get('duration', 0),
                x=clip_data.get('x', 0),
                y=clip_data.get('y', 0),
                width=clip_data.get('width', 1920),
                height=clip_data.get('height', 1080),
                rotation=clip_data.get('rotation', 0),
                opacity=clip_data.get('opacity', 1.0),
                volume=clip_data.get('volume', 1.0),
                speed=clip_data.get('speed', 1.0),
                effects=clip_data.get('effects', []),
                transitions=clip_data.get('transitions', [])
            )
            return clip
        except Exception as e:
            self.logger.error(f"解析片段失败: {e}")
            return None
    
    def _create_video_clip(self, video_clip: VideoClip) -> JianYingClip:
        """创建视频片段"""
        return JianYingClip(
            id=str(uuid.uuid4()),
            type='video',
            source_path=video_clip.file_path,
            start_time=0,
            end_time=video_clip.duration,
            duration=video_clip.duration,
            width=1920,
            height=1080,
            volume=1.0,
            speed=1.0
        )
    
    def _create_video_clip_like(self, video_clip) -> JianYingClip:
        """创建类似VideoClip的片段"""
        return JianYingClip(
            id=getattr(video_clip, 'id', str(uuid.uuid4())),
            type='video',
            source_path=getattr(video_clip, 'file_path', ''),
            start_time=getattr(video_clip, 'start_time', 0),
            end_time=getattr(video_clip, 'end_time', getattr(video_clip, 'duration', 0)),
            duration=getattr(video_clip, 'duration', 0),
            width=1920,
            height=1080,
            volume=1.0,
            speed=1.0
        )
    
    def _create_audio_clip(self, audio_clip) -> JianYingClip:
        """创建音频片段"""
        return JianYingClip(
            id=str(uuid.uuid4()),
            type='audio',
            source_path=audio_clip.file_path,
            start_time=0,
            end_time=audio_clip.duration,
            duration=audio_clip.duration,
            volume=1.0
        )
    
    def _create_text_clip(self, segment: ContentSegment) -> Optional[JianYingClip]:
        """创建文本片段"""
        if not segment.text:
            return None
        
        return JianYingClip(
            id=str(uuid.uuid4()),
            type='text',
            source_path=segment.text,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration=segment.end_time - segment.start_time,
            x=960,  # 居中
            y=900,  # 底部
            width=800,
            height=100
        )
    
    def map_effects(self, effects: List[Dict]) -> List[Dict]:
        """映射特效到剪映格式"""
        mapped_effects = []
        
        for effect in effects:
            effect_type = effect.get('type', '')
            if effect_type in self.effect_mapping:
                mapped_effect = {
                    **self.effect_mapping[effect_type],
                    **effect
                }
                mapped_effects.append(mapped_effect)
            else:
                # 未知特效，直接添加
                mapped_effects.append(effect)
        
        return mapped_effects
    
    def map_transitions(self, transitions: List[Dict]) -> List[Dict]:
        """映射转场到剪映格式"""
        mapped_transitions = []
        
        for transition in transitions:
            transition_type = transition.get('type', '')
            if transition_type in self.transition_mapping:
                mapped_transition = {
                    **self.transition_mapping[transition_type],
                    **transition
                }
                mapped_transitions.append(mapped_transition)
            else:
                # 未知转场，直接添加
                mapped_transitions.append(transition)
        
        return mapped_transitions
    
    def validate_project_structure(self, project: JianYingProject) -> List[str]:
        """验证项目结构"""
        errors = []
        
        if not project.tracks:
            errors.append("项目没有轨道")
        
        for track in project.tracks:
            if not track.clips:
                errors.append(f"轨道 {track.id} 没有片段")
            
            for clip in track.clips:
                if not os.path.exists(clip.source_path):
                    errors.append(f"片段 {clip.id} 源文件不存在: {clip.source_path}")
                
                if clip.duration <= 0:
                    errors.append(f"片段 {clip.id} 时长无效: {clip.duration}")
                
                if clip.start_time < 0:
                    errors.append(f"片段 {clip.id} 开始时间无效: {clip.start_time}")
        
        return errors
    
    def get_project_summary(self, project: JianYingProject) -> Dict[str, Any]:
        """获取项目摘要"""
        video_count = 0
        audio_count = 0
        text_count = 0
        total_duration = 0
        
        for track in project.tracks:
            if track.type == 'video':
                video_count += len(track.clips)
            elif track.type == 'audio':
                audio_count += len(track.clips)
            elif track.type == 'text':
                text_count += len(track.clips)
            
            for clip in track.clips:
                total_duration = max(total_duration, clip.end_time)
        
        return {
            'project_name': project.name,
            'total_duration': total_duration,
            'video_clips': video_count,
            'audio_clips': audio_count,
            'text_clips': text_count,
            'total_tracks': len(project.tracks),
            'resolution': f"{project.resolution['width']}x{project.resolution['height']}",
            'frame_rate': project.frame_rate
        }
    
    def export_project_data(self, project: JianYingProject) -> Dict[str, Any]:
        """导出项目数据为字典"""
        return asdict(project)
    
    def import_project_data(self, project_data: Dict[str, Any]) -> JianYingProject:
        """从字典导入项目数据"""
        try:
            # 转换轨道数据
            tracks = []
            for track_data in project_data.get('tracks', []):
                clips = []
                for clip_data in track_data.get('clips', []):
                    clip = JianYingClip(**clip_data)
                    clips.append(clip)
                
                track_data['clips'] = clips
                track = JianYingTrack(**track_data)
                tracks.append(track)
            
            project_data['tracks'] = tracks
            
            return JianYingProject(**project_data)
            
        except Exception as e:
            self.logger.error(f"导入项目数据失败: {e}")
            raise