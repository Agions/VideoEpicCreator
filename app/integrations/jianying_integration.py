#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
import shutil
import platform
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.video_manager import VideoClip
from app.ai.content_generator import GeneratedContent, ContentSegment


@dataclass
class JianYingClip:
    """剪映剪辑片段"""
    id: str
    type: str  # video, audio, text
    file_path: str
    start_time: float
    end_time: float
    duration: float
    track_index: int = 0
    volume: float = 1.0
    speed: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class JianYingTextClip:
    """剪映文本片段"""
    id: str
    text: str
    start_time: float
    end_time: float
    duration: float
    font_size: int = 24
    font_color: str = "#FFFFFF"
    background_color: str = "#000000"
    position_x: float = 0.5
    position_y: float = 0.8
    track_index: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class JianYingProject:
    """剪映项目"""
    name: str
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 0
    clips: List[JianYingClip] = None
    text_clips: List[JianYingTextClip] = None
    audio_clips: List[JianYingClip] = None

    def __post_init__(self):
        if self.clips is None:
            self.clips = []
        if self.text_clips is None:
            self.text_clips = []
        if self.audio_clips is None:
            self.audio_clips = []

    def add_video_clip(self, clip: JianYingClip):
        """添加视频片段"""
        self.clips.append(clip)
        self.duration = max(self.duration, clip.end_time)

    def add_text_clip(self, clip: JianYingTextClip):
        """添加文本片段"""
        self.text_clips.append(clip)
        self.duration = max(self.duration, clip.end_time)

    def add_audio_clip(self, clip: JianYingClip):
        """添加音频片段"""
        self.audio_clips.append(clip)
        self.duration = max(self.duration, clip.end_time)


class JianYingIntegration(QObject):
    """剪映集成"""

    # 信号
    project_created = pyqtSignal(str)  # 项目路径
    export_completed = pyqtSignal(str)  # 导出路径

    def __init__(self):
        super().__init__()

        # 剪映安装路径检测
        self.jianying_paths = self._detect_jianying_installation()
        self.is_installed = len(self.jianying_paths) > 0

        # 项目模板
        self.project_template = {
            "version": "3.0.0",
            "type": "draft_content",
            "draft_fold": "",
            "draft_id": "",
            "draft_name": "",
            "draft_root_fold": "",
            "duration": 0,
            "extra_info": {},
            "fps": 30,
            "height": 1080,
            "width": 1920,
            "materials": {
                "audios": [],
                "canvases": [],
                "effects": [],
                "images": [],
                "texts": [],
                "videos": []
            },
            "tracks": []
        }

    def _detect_jianying_installation(self) -> List[str]:
        """检测剪映安装路径"""
        paths = []
        system = platform.system().lower()

        if system == "windows":
            # Windows常见安装路径
            possible_paths = [
                os.path.expanduser("~/AppData/Local/JianyingPro"),
                "C:/Program Files/JianyingPro",
                "C:/Program Files (x86)/JianyingPro"
            ]
        elif system == "darwin":
            # macOS路径
            possible_paths = [
                "/Applications/JianyingPro.app",
                os.path.expanduser("~/Applications/JianyingPro.app")
            ]
        else:
            # Linux（如果有的话）
            possible_paths = []

        for path in possible_paths:
            if os.path.exists(path):
                paths.append(path)

        return paths

    def is_jianying_installed(self) -> bool:
        """检查剪映是否已安装"""
        return self.is_installed

    def get_installation_paths(self) -> List[str]:
        """获取剪映安装路径"""
        return self.jianying_paths

    def create_project_from_video(self, video: VideoClip, project_name: str = None) -> JianYingProject:
        """从视频创建剪映项目"""
        if not project_name:
            project_name = f"VideoEpic_{video.name}_{uuid.uuid4().hex[:8]}"

        project = JianYingProject(name=project_name)

        # 添加主视频片段
        main_clip = JianYingClip(
            id=str(uuid.uuid4()),
            type="video",
            file_path=video.file_path,
            start_time=0,
            end_time=video.duration,
            duration=video.duration,
            track_index=0
        )
        project.add_video_clip(main_clip)

        return project

    def create_project_from_content(self, content: GeneratedContent) -> JianYingProject:
        """从生成的内容创建剪映项目"""
        project_name = f"VideoEpic_{content.editing_mode}_{uuid.uuid4().hex[:8]}"
        project = JianYingProject(name=project_name)

        # 添加主视频
        main_clip = JianYingClip(
            id=str(uuid.uuid4()),
            type="video",
            file_path=content.video.file_path,
            start_time=0,
            end_time=content.video.duration,
            duration=content.video.duration,
            track_index=0
        )
        project.add_video_clip(main_clip)

        # 添加文本片段
        for segment in content.segments:
            if segment.text.strip():
                text_clip = JianYingTextClip(
                    id=str(uuid.uuid4()),
                    text=segment.text,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.end_time - segment.start_time,
                    track_index=1
                )
                project.add_text_clip(text_clip)

        return project

    def export_to_jianying(self, project: JianYingProject, output_dir: str = None) -> str:
        """导出到剪映项目文件"""
        if not output_dir:
            output_dir = os.path.expanduser("~/Desktop/CineAIStudio_Projects")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 创建项目文件夹
        project_dir = os.path.join(output_dir, project.name)
        os.makedirs(project_dir, exist_ok=True)

        # 生成剪映项目文件
        project_data = self._generate_jianying_project_data(project)

        # 写入项目文件
        project_file = os.path.join(project_dir, "draft_content.json")
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        # 复制媒体文件
        self._copy_media_files(project, project_dir)

        self.project_created.emit(project_dir)
        return project_dir

    def _generate_jianying_project_data(self, project: JianYingProject) -> Dict[str, Any]:
        """生成剪映项目数据"""
        data = self.project_template.copy()

        # 基本信息
        data["draft_name"] = project.name
        data["duration"] = int(project.duration * 1000000)  # 微秒
        data["fps"] = project.fps
        data["height"] = project.height
        data["width"] = project.width
        data["draft_id"] = str(uuid.uuid4())

        # 材料库
        materials = data["materials"]

        # 视频材料
        for clip in project.clips:
            if clip.type == "video":
                video_material = {
                    "id": clip.id,
                    "path": clip.file_path,
                    "type": "video",
                    "duration": int(clip.duration * 1000000),
                    "width": project.width,
                    "height": project.height,
                    "fps": project.fps
                }
                materials["videos"].append(video_material)

        # 文本材料
        for clip in project.text_clips:
            text_material = {
                "id": clip.id,
                "content": clip.text,
                "type": "text",
                "font_size": clip.font_size,
                "font_color": clip.font_color,
                "background_color": clip.background_color
            }
            materials["texts"].append(text_material)

        # 轨道
        tracks = []

        # 视频轨道
        video_track = {
            "id": str(uuid.uuid4()),
            "type": "video",
            "segments": []
        }

        for clip in project.clips:
            if clip.type == "video":
                segment = {
                    "id": str(uuid.uuid4()),
                    "material_id": clip.id,
                    "target_timerange": {
                        "start": int(clip.start_time * 1000000),
                        "duration": int(clip.duration * 1000000)
                    },
                    "source_timerange": {
                        "start": 0,
                        "duration": int(clip.duration * 1000000)
                    },
                    "speed": clip.speed,
                    "volume": clip.volume
                }
                video_track["segments"].append(segment)

        tracks.append(video_track)

        # 文本轨道
        if project.text_clips:
            text_track = {
                "id": str(uuid.uuid4()),
                "type": "text",
                "segments": []
            }

            for clip in project.text_clips:
                segment = {
                    "id": str(uuid.uuid4()),
                    "material_id": clip.id,
                    "target_timerange": {
                        "start": int(clip.start_time * 1000000),
                        "duration": int(clip.duration * 1000000)
                    },
                    "position": {
                        "x": clip.position_x,
                        "y": clip.position_y
                    }
                }
                text_track["segments"].append(segment)

            tracks.append(text_track)

        data["tracks"] = tracks
        return data

    def _copy_media_files(self, project: JianYingProject, project_dir: str):
        """复制媒体文件到项目目录"""
        media_dir = os.path.join(project_dir, "media")
        os.makedirs(media_dir, exist_ok=True)

        # 复制视频文件
        for clip in project.clips:
            if clip.type == "video" and os.path.exists(clip.file_path):
                filename = os.path.basename(clip.file_path)
                dest_path = os.path.join(media_dir, filename)

                if not os.path.exists(dest_path):
                    shutil.copy2(clip.file_path, dest_path)

                # 更新路径为相对路径
                clip.file_path = f"./media/{filename}"

    def open_in_jianying(self, project_path: str) -> bool:
        """在剪映中打开项目"""
        if not self.is_installed:
            return False

        try:
            system = platform.system().lower()

            if system == "windows":
                # Windows
                import subprocess
                subprocess.Popen([self.jianying_paths[0], project_path])
            elif system == "darwin":
                # macOS
                os.system(f'open -a "{self.jianying_paths[0]}" "{project_path}"')

            return True
        except Exception as e:
            print(f"打开剪映失败: {e}")
            return False

    def get_installation_guide(self) -> Dict[str, Any]:
        """获取剪映安装指南"""
        system = platform.system().lower()

        guides = {
            "windows": {
                "title": "Windows 剪映安装指南",
                "steps": [
                    "1. 访问剪映官网: https://lv.ulikecam.com/",
                    "2. 点击'免费下载'按钮",
                    "3. 下载Windows版本安装包",
                    "4. 运行安装程序并按照提示完成安装",
                    "5. 重启CineAIStudio以检测剪映"
                ],
                "download_url": "https://lv.ulikecam.com/"
            },
            "darwin": {
                "title": "macOS 剪映安装指南",
                "steps": [
                    "1. 访问剪映官网: https://lv.ulikecam.com/",
                    "2. 点击'免费下载'按钮",
                    "3. 下载macOS版本安装包",
                    "4. 打开DMG文件并拖拽到Applications文件夹",
                    "5. 重启CineAIStudio以检测剪映"
                ],
                "download_url": "https://lv.ulikecam.com/"
            }
        }

        return guides.get(system, guides["windows"])

    def create_compilation_project(self, scenes: List, style: str = "高能燃向") -> JianYingProject:
        """创建混剪项目"""
        project_name = f"Compilation_{style}_{uuid.uuid4().hex[:8]}"
        project = JianYingProject(name=project_name)

        current_time = 0
        for i, scene in enumerate(scenes):
            # 添加场景片段
            clip = JianYingClip(
                id=str(uuid.uuid4()),
                type="video",
                file_path=scene.scene_info.metadata.get("source_file", ""),
                start_time=current_time,
                end_time=current_time + (scene.end_time - scene.start_time),
                duration=scene.end_time - scene.start_time,
                track_index=0
            )
            project.add_video_clip(clip)

            # 添加转场效果（如果不是最后一个片段）
            if i < len(scenes) - 1:
                transition_duration = 0.5
                current_time += clip.duration - transition_duration
            else:
                current_time += clip.duration

        return project

    def get_supported_formats(self) -> List[str]:
        """获取支持的视频格式"""
        return [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v"]

    def validate_video_format(self, file_path: str) -> bool:
        """验证视频格式是否支持"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.get_supported_formats()
