#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映草稿生成器
负责生成剪映项目文件和草稿结构
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from .jianying_project_parser import JianYingProject, JianYingTrack, JianYingClip


class JianYingDraftGenerator:
    """剪映草稿生成器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 剪映草稿格式版本
        self.draft_version = "4.0.0"

        # 剪映项目模板
        self.project_template = {
            "version": "4.0.0",
            "type": "project",
            "created_at": "",
            "modified_at": "",
            "duration": 0,
            "frame_rate": 30,
            "resolution": {
                "width": 1920,
                "height": 1080
            },
            "tracks": [],
            "effects": [],
            "transitions": [],
            "audio_settings": {
                "sample_rate": 48000,
                "channels": 2,
                "bit_depth": 16
            },
            "video_settings": {
                "codec": "h264",
                "bitrate": 8000000,
                "profile": "high"
            },
            "metadata": {
                "title": "",
                "description": "",
                "tags": [],
                "creator": "CineAIStudio"
            }
        }

        # 剪映素材目录结构
        self.media_structure = {
            "videos": "video",
            "audio": "audio",
            "images": "image",
            "texts": "text",
            "effects": "effect",
            "transitions": "transition"
        }

    def generate_draft(self, project: JianYingProject, version: str = "4.0.0") -> Dict[str, Any]:
        """
        生成剪映草稿数据

        Args:
            project: 剪映项目对象
            version: 剪映版本

        Returns:
            Dict: 草稿数据
        """
        try:
            self.logger.info(f"开始生成剪映 {version} 草稿")

            # 设置版本
            self.draft_version = version

            # 创建项目数据
            draft_data = self._create_project_data(project)

            # 生成轨道数据
            draft_data["tracks"] = self._generate_tracks(project.tracks)

            # 生成特效数据
            draft_data["effects"] = self._generate_effects(project.effects)

            # 生成转场数据
            draft_data["transitions"] = self._generate_transitions(project.transitions)

            # 生成音频轨道
            draft_data["audio_tracks"] = self._generate_audio_tracks(project.audio_tracks)

            # 生成文本轨道
            draft_data["text_tracks"] = self._generate_text_tracks(project.text_tracks)

            # 生成素材引用
            draft_data["materials"] = self._generate_materials(project)

            # 生成时间轴数据
            draft_data["timeline"] = self._generate_timeline(project)

            # 添加项目元数据
            draft_data["metadata"] = self._generate_metadata(project)

            self.logger.info("剪映草稿生成完成")
            return draft_data

        except Exception as e:
            self.logger.error(f"草稿生成失败: {e}")
            raise

    def _create_project_data(self, project: JianYingProject) -> Dict[str, Any]:
        """创建项目基础数据"""
        project_data = self.project_template.copy()

        project_data.update({
            "version": self.draft_version,
            "created_at": project.create_time,
            "modified_at": project.modify_time,
            "duration": project.duration,
            "frame_rate": project.frame_rate,
            "resolution": project.resolution,
            "metadata": {
                "title": project.name,
                "description": f"由 CineAIStudio 创建的项目",
                "tags": ["CineAIStudio", "AI生成"],
                "creator": "CineAIStudio",
                "created_at": project.create_time
            }
        })

        return project_data

    def _generate_tracks(self, tracks: List[JianYingTrack]) -> List[Dict[str, Any]]:
        """生成轨道数据"""
        track_list = []

        for track in tracks:
            track_data = {
                "id": track.id,
                "type": track.type,
                "enabled": track.enabled,
                "locked": track.locked,
                "visible": track.visible,
                "volume": track.volume,
                "clips": self._generate_clips(track.clips)
            }

            track_list.append(track_data)

        return track_list

    def _generate_clips(self, clips: List[JianYingClip]) -> List[Dict[str, Any]]:
        """生成片段数据"""
        clip_list = []

        for clip in clips:
            clip_data = {
                "id": clip.id,
                "type": clip.type,
                "source_path": clip.source_path,
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "duration": clip.duration,
                "transform": {
                    "x": clip.x,
                    "y": clip.y,
                    "width": clip.width,
                    "height": clip.height,
                    "rotation": clip.rotation,
                    "scale_x": 1.0,
                    "scale_y": 1.0
                },
                "properties": {
                    "opacity": clip.opacity,
                    "volume": clip.volume,
                    "speed": clip.speed,
                    "blend_mode": "normal"
                },
                "effects": self._generate_clip_effects(clip.effects),
                "transitions": self._generate_clip_transitions(clip.transitions)
            }

            # 为文本片段添加特殊属性
            if clip.type == "text":
                clip_data["text_properties"] = {
                    "content": clip.source_path,
                    "font": "Arial",
                    "size": 24,
                    "color": "#FFFFFF",
                    "alignment": "center",
                    "background": {
                        "enabled": False,
                        "color": "#000000",
                        "opacity": 0.8
                    }
                }

            clip_list.append(clip_data)

        return clip_list

    def _generate_clip_effects(self, effects: List[Dict]) -> List[Dict[str, Any]]:
        """生成片段特效"""
        effect_list = []

        for effect in effects:
            effect_data = {
                "id": str(uuid.uuid4()),
                "type": effect.get("type", "basic"),
                "name": effect.get("name", "特效"),
                "start_time": effect.get("start_time", 0),
                "duration": effect.get("duration", 1.0),
                "properties": effect.get("properties", {}),
                "enabled": True
            }

            effect_list.append(effect_data)

        return effect_list

    def _generate_clip_transitions(self, transitions: List[Dict]) -> List[Dict[str, Any]]:
        """生成片段转场"""
        transition_list = []

        for transition in transitions:
            transition_data = {
                "id": str(uuid.uuid4()),
                "type": transition.get("type", "fade"),
                "name": transition.get("name", "转场"),
                "duration": transition.get("duration", 1.0),
                "properties": transition.get("properties", {}),
                "enabled": True
            }

            transition_list.append(transition_data)

        return transition_list

    def _generate_effects(self, effects: List[Dict]) -> List[Dict[str, Any]]:
        """生成全局特效"""
        return self._generate_clip_effects(effects)

    def _generate_transitions(self, transitions: List[Dict]) -> List[Dict[str, Any]]:
        """生成全局转场"""
        return self._generate_clip_transitions(transitions)

    def _generate_audio_tracks(self, audio_tracks: List[Dict]) -> List[Dict[str, Any]]:
        """生成音频轨道"""
        track_list = []

        for track in audio_tracks:
            track_data = {
                "id": track.get("id", str(uuid.uuid4())),
                "type": "audio",
                "name": track.get("name", "音频轨道"),
                "volume": track.get("volume", 1.0),
                "muted": track.get("muted", False),
                "solo": track.get("solo", False),
                "clips": self._generate_audio_clips(track.get("clips", []))
            }

            track_list.append(track_data)

        return track_list

    def _generate_audio_clips(self, audio_clips: List[Dict]) -> List[Dict[str, Any]]:
        """生成音频片段"""
        clip_list = []

        for clip in audio_clips:
            clip_data = {
                "id": clip.get("id", str(uuid.uuid4())),
                "source_path": clip.get("source_path", ""),
                "start_time": clip.get("start_time", 0),
                "duration": clip.get("duration", 0),
                "volume": clip.get("volume", 1.0),
                "fade_in": clip.get("fade_in", 0),
                "fade_out": clip.get("fade_out", 0),
                "properties": {
                    "pitch": 1.0,
                    "equalizer": {}
                }
            }

            clip_list.append(clip_data)

        return clip_list

    def _generate_text_tracks(self, text_tracks: List[Dict]) -> List[Dict[str, Any]]:
        """生成文本轨道"""
        track_list = []

        for track in text_tracks:
            track_data = {
                "id": track.get("id", str(uuid.uuid4())),
                "type": "text",
                "name": track.get("name", "文本轨道"),
                "visible": track.get("visible", True),
                "clips": self._generate_text_clips(track.get("clips", []))
            }

            track_list.append(track_data)

        return track_list

    def _generate_text_clips(self, text_clips: List[Dict]) -> List[Dict[str, Any]]:
        """生成文本片段"""
        clip_list = []

        for clip in text_clips:
            clip_data = {
                "id": clip.get("id", str(uuid.uuid4())),
                "content": clip.get("content", ""),
                "start_time": clip.get("start_time", 0),
                "duration": clip.get("duration", 0),
                "position": {
                    "x": clip.get("x", 960),
                    "y": clip.get("y", 900)
                },
                "style": {
                    "font": clip.get("font", "Arial"),
                    "size": clip.get("size", 24),
                    "color": clip.get("color", "#FFFFFF"),
                    "bold": clip.get("bold", False),
                    "italic": clip.get("italic", False),
                    "underline": clip.get("underline", False),
                    "alignment": clip.get("alignment", "center")
                },
                "background": {
                    "enabled": clip.get("background_enabled", False),
                    "color": clip.get("background_color", "#000000"),
                    "opacity": clip.get("background_opacity", 0.8),
                    "margin": clip.get("background_margin", 10)
                }
            }

            clip_list.append(clip_data)

        return clip_list

    def _generate_materials(self, project: JianYingProject) -> Dict[str, Any]:
        """生成素材引用"""
        materials = {
            "videos": [],
            "audio": [],
            "images": [],
            "texts": [],
            "effects": [],
            "transitions": []
        }

        # 收集所有素材
        for track in project.tracks:
            for clip in track.clips:
                material_path = clip.source_path
                if material_path:
                    if clip.type == "video":
                        materials["videos"].append({
                            "id": clip.id,
                            "path": material_path,
                            "name": os.path.basename(material_path)
                        })
                    elif clip.type == "audio":
                        materials["audio"].append({
                            "id": clip.id,
                            "path": material_path,
                            "name": os.path.basename(material_path)
                        })
                    elif clip.type == "image":
                        materials["images"].append({
                            "id": clip.id,
                            "path": material_path,
                            "name": os.path.basename(material_path)
                        })
                    elif clip.type == "text":
                        materials["texts"].append({
                            "id": clip.id,
                            "content": material_path,
                            "name": f"文本_{clip.id[:8]}"
                        })

        return materials

    def _generate_timeline(self, project: JianYingProject) -> Dict[str, Any]:
        """生成时间轴数据"""
        timeline = {
            "duration": project.duration,
            "markers": [],
            "chapters": [],
            "zoom_level": 1.0,
            "playhead_position": 0,
            "selection_range": {
                "start": 0,
                "end": project.duration
            }
        }

        # 生成章节标记
        chapters = self._generate_chapters(project)
        if chapters:
            timeline["chapters"] = chapters

        return timeline

    def _generate_chapters(self, project: JianYingProject) -> List[Dict[str, Any]]:
        """生成章节数据"""
        chapters = []

        # 基于视频片段生成章节
        video_tracks = [track for track in project.tracks if track.type == "video"]
        if video_tracks:
            current_time = 0
            for i, track in enumerate(video_tracks):
                for clip in track.clips:
                    chapter = {
                        "id": str(uuid.uuid4()),
                        "title": f"章节 {i+1}",
                        "start_time": current_time,
                        "end_time": current_time + clip.duration,
                        "description": f"视频片段: {os.path.basename(clip.source_path)}"
                    }
                    chapters.append(chapter)
                    current_time += clip.duration

        return chapters

    def _generate_metadata(self, project: JianYingProject) -> Dict[str, Any]:
        """生成项目元数据"""
        metadata = {
            "title": project.name,
            "description": f"由 CineAIStudio 创建的剪映项目",
            "tags": ["CineAIStudio", "AI生成", "视频编辑"],
            "creator": "CineAIStudio",
            "created_at": project.create_time,
            "modified_at": project.modify_time,
            "version": self.draft_version,
            "export_info": {
                "exporter": "CineAIStudio",
                "exporter_version": "2.0.0",
                "export_time": datetime.now().isoformat()
            },
            "statistics": {
                "total_clips": sum(len(track.clips) for track in project.tracks),
                "total_tracks": len(project.tracks),
                "total_duration": project.duration,
                "resolution": f"{project.resolution['width']}x{project.resolution['height']}",
                "frame_rate": project.frame_rate
            }
        }

        return metadata

    def save_draft_file(self, draft_data: Dict[str, Any], output_path: str) -> bool:
        """保存草稿文件"""
        try:
            # 确保输出目录存在
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 保存主草稿文件
            draft_file = output_dir / "draft_content.json"
            with open(draft_file, 'w', encoding='utf-8') as f:
                json.dump(draft_data, f, ensure_ascii=False, indent=2)

            # 保存项目信息文件
            project_info = {
                "version": self.draft_version,
                "created_at": datetime.now().isoformat(),
                "project_name": draft_data.get("metadata", {}).get("title", "未命名项目"),
                "exporter": "CineAIStudio",
                "notes": "此项目可在剪映中打开编辑"
            }

            info_file = output_dir / "project_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, ensure_ascii=False, indent=2)

            self.logger.info(f"草稿文件保存成功: {draft_file}")
            return True

        except Exception as e:
            self.logger.error(f"保存草稿文件失败: {e}")
            return False

    def validate_draft_structure(self, draft_data: Dict[str, Any]) -> List[str]:
        """验证草稿结构"""
        errors = []

        # 检查必要字段
        required_fields = ["version", "type", "duration", "tracks", "materials"]
        for field in required_fields:
            if field not in draft_data:
                errors.append(f"缺少必要字段: {field}")

        # 检查轨道结构
        tracks = draft_data.get("tracks", [])
        for i, track in enumerate(tracks):
            if "clips" not in track:
                errors.append(f"轨道 {i} 缺少 clips 字段")

            clips = track.get("clips", [])
            for j, clip in enumerate(clips):
                if "source_path" not in clip:
                    errors.append(f"轨道 {i} 片段 {j} 缺少 source_path 字段")

                if clip.get("duration", 0) <= 0:
                    errors.append(f"轨道 {i} 片段 {j} 时长无效")

        return errors

    def get_draft_summary(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取草稿摘要"""
        tracks = draft_data.get("tracks", [])
        materials = draft_data.get("materials", {})

        video_count = len(materials.get("videos", []))
        audio_count = len(materials.get("audio", []))
        image_count = len(materials.get("images", []))
        text_count = len(materials.get("texts", []))

        total_clips = sum(len(track.get("clips", [])) for track in tracks)

        return {
            "project_name": draft_data.get("metadata", {}).get("title", "未命名项目"),
            "version": draft_data.get("version", "未知版本"),
            "duration": draft_data.get("duration", 0),
            "total_tracks": len(tracks),
            "total_clips": total_clips,
            "video_clips": video_count,
            "audio_clips": audio_count,
            "image_clips": image_count,
            "text_clips": text_count,
            "resolution": f"{draft_data.get('resolution', {}).get('width', 0)}x{draft_data.get('resolution', {}).get('height', 0)}",
            "frame_rate": draft_data.get("frame_rate", 0)
        }
