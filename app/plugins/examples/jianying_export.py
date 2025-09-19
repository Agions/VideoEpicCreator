#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
剪映草稿导出插件
支持将项目导出为剪映草稿格式，便于在剪映APP中继续编辑
"""

import json
import os
import uuid
import logging
import shutil
import zipfile
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QProgressDialog

from app.plugins.plugin_system import ExportPlugin, PluginMetadata, PluginContext

logger = logging.getLogger(__name__)


class JianyingExportFormat(Enum):
    """剪映导出格式枚举"""
    DRAFT_JSON = "draft_json"          # 草稿JSON格式
    DRAFT_PACKAGE = "draft_package"      # 草稿包格式
    PROJECT_BACKUP = "project_backup"   # 项目备份格式


class VideoQuality(Enum):
    """视频质量枚举"""
    ORIGINAL = "original"      # 原始质量
    HIGH = "high"              # 高质量
    MEDIUM = "medium"          # 中等质量
    LOW = "low"               # 低质量


class AudioQuality(Enum):
    """音频质量枚举"""
    ORIGINAL = "original"      # 原始质量
    HIGH = "high"              # 高质量 (320kbps)
    MEDIUM = "medium"          # 中等质量 (192kbps)
    LOW = "low"               # 低质量 (128kbps)


@dataclass
class JianyingExportConfig:
    """剪映导出配置"""
    export_format: str = JianyingExportFormat.DRAFT_PACKAGE.value
    video_quality: str = VideoQuality.HIGH.value
    audio_quality: str = AudioQuality.HIGH.value
    include_effects: bool = True
    include_transitions: bool = True
    include_audio: bool = True
    include_thumbnails: bool = True
    compress_media: bool = True
    generate_preview: bool = True
    export_path: str = ""
    draft_name: str = ""
    description: str = ""
    tags: List[str] = None
    cover_image: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class MediaClip:
    """媒体片段"""
    id: str
    type: str  # "video", "audio", "image"
    path: str
    duration: float
    start_time: float
    end_time: float
    position: float
    x: float = 0
    y: float = 0
    width: float = 1920
    height: float = 1080
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
class JianyingDraft:
    """剪映草稿结构"""
    version: str = "1.0"
    draft_id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = ""
    modified_at: str = ""
    duration: float = 0.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    media_clips: List[MediaClip] = None
    audio_tracks: List[MediaClip] = None
    effects: List[Dict] = None
    tags: List[str] = None
    cover_image: str = ""
    settings: Dict = None

    def __post_init__(self):
        if self.media_clips is None:
            self.media_clips = []
        if self.audio_tracks is None:
            self.audio_tracks = []
        if self.effects is None:
            self.effects = []
        if self.tags is None:
            self.tags = []
        if self.settings is None:
            self.settings = {}


class JianyingExportWorker(QObject):
    """剪映导出工作线程"""

    progress_updated = pyqtSignal(int, str)  # progress, message
    export_completed = pyqtSignal(str, object)  # output_path, error
    log_message = pyqtSignal(str)

    def __init__(self, config: JianyingExportConfig):
        super().__init__()
        self.config = config
        self._running = False

    def export_project(self, project_data: Dict[str, Any], output_path: str):
        """导出项目"""
        try:
            self._running = True
            self.progress_updated.emit(5, "开始解析项目数据...")

            # 解析项目数据
            draft = self._parse_project_data(project_data)
            self.progress_updated.emit(15, "项目数据解析完成")

            # 根据导出格式选择导出方式
            if self.config.export_format == JianyingExportFormat.DRAFT_JSON.value:
                self._export_as_json(draft, output_path)
            elif self.config.export_format == JianyingExportFormat.DRAFT_PACKAGE.value:
                self._export_as_package(draft, output_path)
            elif self.config.export_format == JianyingExportFormat.PROJECT_BACKUP.value:
                self._export_as_backup(draft, output_path)

            self.progress_updated.emit(100, "导出完成")
            self.export_completed.emit(output_path, None)

        except Exception as e:
            self.log_message.emit(f"导出失败: {str(e)}")
            self.export_completed.emit("", {"error": str(e)})
        finally:
            self._running = False

    def _parse_project_data(self, project_data: Dict[str, Any]) -> JianyingDraft:
        """解析项目数据"""
        draft = JianyingDraft(
            draft_id=str(uuid.uuid4()),
            name=self.config.draft_name or project_data.get("name", "未命名项目"),
            description=self.config.description or project_data.get("description", ""),
            created_at=project_data.get("created_at", ""),
            modified_at=project_data.get("modified_at", ""),
            duration=project_data.get("duration", 0.0),
            fps=project_data.get("fps", 30),
            width=project_data.get("width", 1920),
            height=project_data.get("height", 1080),
            tags=self.config.tags
        )

        # 解析媒体片段
        if "media_clips" in project_data:
            for clip_data in project_data["media_clips"]:
                clip = MediaClip(
                    id=str(uuid.uuid4()),
                    type=clip_data.get("type", "video"),
                    path=clip_data.get("path", ""),
                    duration=clip_data.get("duration", 0.0),
                    start_time=clip_data.get("start_time", 0.0),
                    end_time=clip_data.get("end_time", 0.0),
                    position=clip_data.get("position", 0.0),
                    x=clip_data.get("x", 0),
                    y=clip_data.get("y", 0),
                    width=clip_data.get("width", 1920),
                    height=clip_data.get("height", 1080),
                    opacity=clip_data.get("opacity", 1.0),
                    volume=clip_data.get("volume", 1.0),
                    speed=clip_data.get("speed", 1.0),
                    effects=clip_data.get("effects", []),
                    transitions=clip_data.get("transitions", [])
                )
                draft.media_clips.append(clip)

        # 解析音轨
        if "audio_tracks" in project_data:
            for audio_data in project_data["audio_tracks"]:
                audio_clip = MediaClip(
                    id=str(uuid.uuid4()),
                    type="audio",
                    path=audio_data.get("path", ""),
                    duration=audio_data.get("duration", 0.0),
                    start_time=audio_data.get("start_time", 0.0),
                    end_time=audio_data.get("end_time", 0.0),
                    position=audio_data.get("position", 0.0),
                    volume=audio_data.get("volume", 1.0),
                    effects=audio_data.get("effects", [])
                )
                draft.audio_tracks.append(audio_clip)

        # 解析效果
        if "effects" in project_data:
            draft.effects = project_data["effects"]

        return draft

    def _export_as_json(self, draft: JianyingDraft, output_path: str):
        """导出为JSON格式"""
        self.progress_updated.emit(20, "生成JSON数据...")

        # 转换为字典
        draft_dict = asdict(draft)

        # 转换MediaClip对象
        draft_dict["media_clips"] = [asdict(clip) for clip in draft.media_clips]
        draft_dict["audio_tracks"] = [asdict(clip) for clip in draft.audio_tracks]

        # 添加导出信息
        draft_dict["export_info"] = {
            "export_format": "json",
            "exported_by": "CineAI Studio",
            "export_time": self._get_current_time(),
            "version": "1.0"
        }

        # 保存JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(draft_dict, f, ensure_ascii=False, indent=2)

        self.progress_updated.emit(90, "JSON文件保存完成")

    def _export_as_package(self, draft: JianyingDraft, output_path: str):
        """导出为草稿包格式"""
        self.progress_updated.emit(20, "创建草稿包目录...")

        # 创建临时目录
        temp_dir = output_path.replace('.zip', '_temp')
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 创建草稿包结构
            self._create_package_structure(temp_dir, draft)

            # 复制媒体文件
            if self.config.include_thumbnails:
                self._copy_media_files(temp_dir, draft)

            # 生成缩略图
            if self.config.generate_preview:
                self._generate_thumbnails(temp_dir, draft)

            # 打包为ZIP
            self.progress_updated.emit(70, "创建ZIP压缩包...")
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)

            self.progress_updated.emit(90, "草稿包创建完成")

        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _export_as_backup(self, draft: JianyingDraft, output_path: str):
        """导出为项目备份格式"""
        self.progress_updated.emit(20, "创建备份文件...")

        # 创建备份目录结构
        backup_dir = output_path.replace('.zip', '')
        os.makedirs(backup_dir, exist_ok=True)

        try:
            # 保存项目数据
            project_file = os.path.join(backup_dir, 'project.json')
            self._export_as_json(draft, project_file)

            # 复制所有媒体文件
            media_dir = os.path.join(backup_dir, 'media')
            os.makedirs(media_dir, exist_ok=True)

            if self.config.include_thumbnails:
                self._copy_media_files(media_dir, draft)

            # 生成备份信息文件
            backup_info = {
                "backup_version": "1.0",
                "created_by": "CineAI Studio",
                "created_time": self._get_current_time(),
                "draft_info": asdict(draft)
            }

            info_file = os.path.join(backup_dir, 'backup_info.json')
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            # 打包备份
            self.progress_updated.emit(80, "创建备份压缩包...")
            shutil.make_archive(backup_dir, 'zip', backup_dir)

            self.progress_updated.emit(90, "备份文件创建完成")

        finally:
            # 清理临时目录
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

    def _create_package_structure(self, package_dir: str, draft: JianyingDraft):
        """创建草稿包结构"""
        self.progress_updated.emit(25, "创建草稿包文件结构...")

        # 创建必要目录
        os.makedirs(os.path.join(package_dir, 'media'), exist_ok=True)
        os.makedirs(os.path.join(package_dir, 'thumbnails'), exist_ok=True)
        os.makedirs(os.path.join(package_dir, 'effects'), exist_ok=True)
        os.makedirs(os.path.join(package_dir, 'audio'), exist_ok=True)

        # 创建草稿信息文件
        draft_info = {
            "draft_id": draft.draft_id,
            "name": draft.name,
            "description": draft.description,
            "created_at": draft.created_at,
            "modified_at": draft.modified_at,
            "duration": draft.duration,
            "fps": draft.fps,
            "resolution": f"{draft.width}x{draft.height}",
            "tags": draft.tags,
            "version": "1.0"
        }

        info_file = os.path.join(package_dir, 'draft_info.json')
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(draft_info, f, ensure_ascii=False, indent=2)

        # 创建时间线数据文件
        timeline_data = {
            "tracks": {
                "main": [asdict(clip) for clip in draft.media_clips],
                "audio": [asdict(clip) for clip in draft.audio_tracks]
            },
            "effects": draft.effects,
            "total_duration": draft.duration
        }

        timeline_file = os.path.join(package_dir, 'timeline.json')
        with open(timeline_file, 'w', encoding='utf-8') as f:
            json.dump(timeline_data, f, ensure_ascii=False, indent=2)

        self.progress_updated.emit(40, "草稿包结构创建完成")

    def _copy_media_files(self, media_dir: str, draft: JianyingDraft):
        """复制媒体文件"""
        self.progress_updated.emit(45, "复制媒体文件...")

        copied_files = 0
        total_files = len(draft.media_clips) + len(draft.audio_tracks)

        for clip in draft.media_clips + draft.audio_tracks:
            if os.path.exists(clip.path):
                try:
                    # 创建媒体文件名
                    file_name = f"{clip.id}_{os.path.basename(clip.path)}"
                    dest_path = os.path.join(media_dir, file_name)

                    # 复制文件
                    if self.config.compress_media:
                        # 这里应该实现媒体压缩逻辑
                        shutil.copy2(clip.path, dest_path)
                    else:
                        shutil.copy2(clip.path, dest_path)

                    copied_files += 1
                    self.progress_updated.emit(
                        45 + int(15 * copied_files / total_files),
                        f"复制媒体文件 {copied_files}/{total_files}"
                    )

                except Exception as e:
                    self.log_message.emit(f"复制媒体文件失败: {clip.path} - {e}")

    def _generate_thumbnails(self, thumbnails_dir: str, draft: JianyingDraft):
        """生成缩略图"""
        self.progress_updated.emit(65, "生成缩略图...")

        # 这里应该实现缩略图生成逻辑
        # 简化实现，创建占位符文件
        for clip in draft.media_clips:
            if clip.type == "video":
                thumb_path = os.path.join(thumbnails_dir, f"{clip.id}_thumb.jpg")
                # 创建空文件作为占位符
                with open(thumb_path, 'w') as f:
                    f.write("")

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().isoformat()


class JianyingExportPlugin(ExportPlugin):
    """剪映导出插件"""

    def __init__(self):
        super().__init__()
        self._config = JianyingExportConfig()
        self._worker = None
        self._thread = None

    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        return PluginMetadata(
            name="剪映导出器",
            version="1.0.0",
            description="将项目导出为剪映草稿格式，支持在剪映APP中继续编辑",
            author="CineAI Studio Team",
            email="support@cineaistudio.com",
            website="https://cineaistudio.com",
            plugin_type=PluginType.EXPORT_FORMAT,
            category="Export Formats",
            tags=["剪映", "Jianying", "Export", "Mobile", "Draft"],
            dependencies=["PyQt6>=6.0.0"],
            min_app_version="2.0.0",
            api_version="1.0",
            priority=PluginPriority.HIGH,
            enabled=True,
            config_schema={
                "sections": [
                    {
                        "name": "basic",
                        "label": "基本设置",
                        "description": "导出基本选项",
                        "fields": [
                            {
                                "name": "export_format",
                                "label": "导出格式",
                                "type": "select",
                                "description": "选择导出格式",
                                "default": "draft_package",
                                "options": [
                                    {"value": "draft_json", "label": "草稿JSON"},
                                    {"value": "draft_package", "label": "草稿包（推荐）"},
                                    {"value": "project_backup", "label": "项目备份"}
                                ]
                            },
                            {
                                "name": "draft_name",
                                "label": "草稿名称",
                                "type": "string",
                                "description": "导出的草稿名称",
                                "required": True,
                                "placeholder": "输入草稿名称"
                            },
                            {
                                "name": "description",
                                "label": "描述",
                                "type": "text",
                                "description": "草稿描述信息",
                                "required": False,
                                "placeholder": "输入项目描述"
                            },
                            {
                                "name": "tags",
                                "label": "标签",
                                "type": "string",
                                "description": "草稿标签，用逗号分隔",
                                "required": False,
                                "placeholder": "Vlog,教程,生活"
                            }
                        ]
                    },
                    {
                        "name": "quality",
                        "label": "质量设置",
                        "description": "媒体质量选项",
                        "fields": [
                            {
                                "name": "video_quality",
                                "label": "视频质量",
                                "type": "select",
                                "description": "导出视频质量",
                                "default": "high",
                                "options": [
                                    {"value": "original", "label": "原始质量"},
                                    {"value": "high", "label": "高质量"},
                                    {"value": "medium", "label": "中等质量"},
                                    {"value": "low", "label": "低质量"}
                                ]
                            },
                            {
                                "name": "audio_quality",
                                "label": "音频质量",
                                "type": "select",
                                "description": "导出音频质量",
                                "default": "high",
                                "options": [
                                    {"value": "original", "label": "原始质量"},
                                    {"value": "high", "label": "高质量 (320kbps)"},
                                    {"value": "medium", "label": "中等质量 (192kbps)"},
                                    {"value": "low", "label": "低质量 (128kbps)"}
                                ]
                            }
                        ]
                    },
                    {
                        "name": "content",
                        "label": "内容设置",
                        "description": "导出内容选项",
                        "fields": [
                            {
                                "name": "include_effects",
                                "label": "包含特效",
                                "type": "boolean",
                                "description": "是否包含视频特效",
                                "default": True
                            },
                            {
                                "name": "include_transitions",
                                "label": "包含转场",
                                "type": "boolean",
                                "description": "是否包含转场效果",
                                "default": True
                            },
                            {
                                "name": "include_audio",
                                "label": "包含音频",
                                "type": "boolean",
                                "description": "是否包含音轨",
                                "default": True
                            },
                            {
                                "name": "include_thumbnails",
                                "label": "包含缩略图",
                                "type": "boolean",
                                "description": "是否生成缩略图",
                                "default": True
                            }
                        ]
                    },
                    {
                        "name": "advanced",
                        "label": "高级设置",
                        "description": "高级导出选项",
                        "fields": [
                            {
                                "name": "compress_media",
                                "label": "压缩媒体",
                                "type": "boolean",
                                "description": "是否压缩媒体文件以减小文件大小",
                                "default": True
                            },
                            {
                                "name": "generate_preview",
                                "label": "生成预览",
                                "type": "boolean",
                                "description": "是否生成项目预览",
                                "default": True
                            },
                            {
                                "name": "export_path",
                                "label": "导出路径",
                                "type": "directory",
                                "description": "导出文件保存路径",
                                "required": True,
                                "placeholder": "选择导出路径"
                            }
                        ]
                    }
                ]
            }
        )

    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        try:
            self._context = context
            logger.info("剪映导出插件初始化成功")
            return True
        except Exception as e:
            logger.error(f"剪映导出插件初始化失败: {e}")
            return False

    def cleanup(self):
        """清理插件资源"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        logger.info("剪映导出插件已清理")

    def get_supported_formats(self) -> List[str]:
        """获取支持的导出格式"""
        return [
            "剪映草稿包 (.zip)",
            "剪映草稿 (.json)",
            "项目备份 (.zip)"
        ]

    def get_format_options(self, format_name: str) -> Dict[str, Any]:
        """获取格式选项"""
        options = {
            "剪映草稿包 (.zip)": {
                "description": "包含媒体文件的完整草稿包，推荐使用",
                "file_extension": ".zip",
                "supports_media": True,
                "supports_effects": True,
                "file_size": "较大",
                "compatibility": "剪映APP"
            },
            "剪映草稿 (.json)": {
                "description": "仅包含项目数据的JSON文件",
                "file_extension": ".json",
                "supports_media": False,
                "supports_effects": True,
                "file_size": "很小",
                "compatibility": "剪映专业版"
            },
            "项目备份 (.zip)": {
                "description": "完整的项目备份文件",
                "file_extension": ".zip",
                "supports_media": True,
                "supports_effects": True,
                "file_size": "很大",
                "compatibility": "CineAI Studio"
            }
        }
        return options.get(format_name, {})

    def export(self, project_data: Any, output_path: str, options: Dict[str, Any]) -> bool:
        """执行导出"""
        try:
            # 更新配置
            self._update_config_from_options(options)

            # 设置工作线程
            self._setup_worker()

            # 执行导出
            self._worker.export_project(project_data, output_path)

            return True

        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False

    def validate_export_options(self, options: Dict[str, Any]) -> bool:
        """验证导出选项"""
        required_fields = ["export_format", "draft_name", "export_path"]

        for field in required_fields:
            if field not in options or not options[field]:
                logger.error(f"缺少必需字段: {field}")
                return False

        # 验证导出路径
        export_path = options["export_path"]
        if not os.path.exists(os.path.dirname(export_path)):
            logger.error("导出路径不存在")
            return False

        # 验证导出格式
        valid_formats = [fmt.value for fmt in JianyingExportFormat]
        if options["export_format"] not in valid_formats:
            logger.error(f"无效的导出格式: {options['export_format']}")
            return False

        return True

    def _setup_worker(self):
        """设置工作线程"""
        if not self._thread:
            self._thread = QThread()
            self._worker = JianyingExportWorker(self._config)
            self._worker.moveToThread(self._thread)
            self._thread.start()

    def _update_config_from_options(self, options: Dict[str, Any]):
        """从选项更新配置"""
        for key, value in options.items():
            if hasattr(self._config, key):
                if key == "tags" and isinstance(value, str):
                    # 处理标签字符串
                    self._config.tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                else:
                    setattr(self._config, key, value)

    def on_config_changed(self, new_config: Dict[str, Any]):
        """配置变化回调"""
        for key, value in new_config.items():
            if hasattr(self._config, key):
                if key == "tags" and isinstance(value, str):
                    self._config.tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                else:
                    setattr(self._config, key, value)

    def get_status(self) -> Dict[str, Any]:
        """获取插件状态"""
        return {
            "state": self._state.value,
            "version": self.metadata.version,
            "enabled": self.metadata.enabled,
            "supported_formats": len(self.get_supported_formats())
        }


# 插件注册
plugin_class = JianyingExportPlugin