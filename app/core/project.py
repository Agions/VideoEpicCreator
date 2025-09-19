#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目模型类
定义项目的基本数据结构和操作方法
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import logging


@dataclass
class ProjectSettings:
    """项目设置"""
    video_quality: str = "high"  # low, medium, high
    export_format: str = "mp4"  # mp4, mov, avi
    resolution: str = "1920x1080"  # 视频分辨率
    frame_rate: int = 30  # 帧率
    audio_sample_rate: int = 48000  # 音频采样率
    auto_save_interval: int = 300  # 自动保存间隔（秒）
    backup_enabled: bool = True  # 启用备份
    backup_count: int = 5  # 备份数量
    theme: str = "professional"  # 主题风格
    language: str = "zh-CN"  # 语言
    ai_model: str = "qwen-max"  # 默认AI模型

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectSettings':
        return cls(**data)


@dataclass
class ProjectMetadata:
    """项目元数据"""
    created_by: str = ""
    created_with: str = "CineAIStudio v2.0"
    project_version: str = "2.0"
    template_used: str = ""
    last_backup: str = ""
    total_editing_time: int = 0  # 总编辑时间（秒）
    auto_save_count: int = 0
    export_count: int = 0
    crash_recovery_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectMetadata':
        return cls(**data)


@dataclass
class ProjectInfo:
    """项目信息"""
    id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = ""
    modified_at: str = ""
    file_path: str = ""
    project_dir: str = ""
    thumbnail_path: str = ""
    video_count: int = 0
    audio_count: int = 0
    subtitle_count: int = 0
    duration: float = 0.0  # 总时长（秒）
    file_size: int = 0  # 项目文件大小（字节）
    editing_mode: str = "commentary"  # commentary, compilation, monologue
    status: str = "draft"  # draft, editing, processing, completed, exported
    progress: float = 0.0  # 编辑进度 0.0-1.0
    last_edited_feature: str = ""
    tags: List[str] = field(default_factory=list)
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at
        if not self.metadata.created_with:
            self.metadata.created_with = "CineAIStudio v2.0"
        if not self.metadata.project_version:
            self.metadata.project_version = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['settings'] = self.settings.to_dict()
        data['metadata'] = self.metadata.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectInfo':
        """从字典创建"""
        if 'settings' in data:
            data['settings'] = ProjectSettings.from_dict(data['settings'])
        if 'metadata' in data:
            data['metadata'] = ProjectMetadata.from_dict(data['metadata'])
        return cls(**data)

    def update_timestamp(self):
        """更新修改时间"""
        self.modified_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()

    def remove_tag(self, tag: str):
        """移除标签"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()

    def get_file_size_mb(self) -> float:
        """获取文件大小（MB）"""
        return self.file_size / (1024 * 1024) if self.file_size > 0 else 0.0

    def get_duration_formatted(self) -> str:
        """获取格式化的时长"""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class Project(QObject):
    """项目模型类"""

    # 信号
    modified = pyqtSignal()  # 项目被修改
    saved = pyqtSignal(str)  # 项目保存
    loaded = pyqtSignal(str)  # 项目加载
    backup_created = pyqtSignal(str)  # 备份创建
    error_occurred = pyqtSignal(str)  # 错误发生

    def __init__(self, project_info: ProjectInfo = None):
        super().__init__()
        self._logger = logging.getLogger(__name__)

        self.project_info = project_info or ProjectInfo()
        self.is_modified = False
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)

        # 项目数据
        self.videos = []
        self.audios = []
        self.subtitles = []
        self.timeline = []
        self.effects = []
        self.transitions = []
        self.ai_settings = {}
        self.export_settings = {}

        # 临时文件和缓存
        self.temp_files = []
        self.cache_dir = ""

        # 错误恢复信息
        self.crash_recovery_info = {}

    def create_new(self, name: str, description: str = "", project_dir: str = "") -> bool:
        """创建新项目"""
        try:
            self.project_info = ProjectInfo(
                name=name,
                description=description,
                project_dir=project_dir or self._get_default_project_dir(name)
            )

            # 创建项目目录
            os.makedirs(self.project_info.project_dir, exist_ok=True)

            # 创建子目录
            self._create_project_structure()

            # 设置项目文件路径
            project_file = os.path.join(self.project_info.project_dir, f"{name}.vecp")
            self.project_info.file_path = project_file

            # 初始化自动保存
            self._init_auto_save()

            self.is_modified = True
            self.modified.emit()

            return True

        except Exception as e:
            self.error_occurred.emit(f"创建项目失败: {str(e)}")
            return False

    def load_from_file(self, file_path: str) -> bool:
        """从文件加载项目"""
        try:
            if not os.path.exists(file_path):
                self.error_occurred.emit("项目文件不存在")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载项目信息
            self.project_info = ProjectInfo.from_dict(data.get('project_info', {}))
            self.project_info.file_path = file_path

            # 加载项目数据
            self.videos = data.get('videos', [])
            self.audios = data.get('audios', [])
            self.subtitles = data.get('subtitles', [])
            self.timeline = data.get('timeline', [])
            self.effects = data.get('effects', [])
            self.transitions = data.get('transitions', [])
            self.ai_settings = data.get('ai_settings', {})
            self.export_settings = data.get('export_settings', {})

            # 初始化自动保存
            self._init_auto_save()

            self.is_modified = False
            self.loaded.emit(file_path)

            return True

        except Exception as e:
            self.error_occurred.emit(f"加载项目失败: {str(e)}")
            return False

    def save_to_file(self, file_path: str = None) -> bool:
        """保存项目到文件"""
        try:
            if not self.project_info:
                return False

            # 确定保存路径
            save_path = file_path or self.project_info.file_path
            if not save_path:
                self.error_occurred.emit("未指定保存路径")
                return False

            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 更新项目信息
            self.project_info.update_timestamp()
            self.project_info.video_count = len(self.videos)
            self.project_info.audio_count = len(self.audios)
            self.project_info.subtitle_count = len(self.subtitles)
            self.project_info.metadata.auto_save_count += 1

            # 计算总时长
            total_duration = sum(video.get('duration', 0) for video in self.videos)
            self.project_info.duration = total_duration

            # 准备保存数据
            data = {
                'version': '2.0',
                'project_info': self.project_info.to_dict(),
                'videos': self.videos,
                'audios': self.audios,
                'subtitles': self.subtitles,
                'timeline': self.timeline,
                'effects': self.effects,
                'transitions': self.transitions,
                'ai_settings': self.ai_settings,
                'export_settings': self.export_settings
            }

            # 保存到文件
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 更新文件大小
            if os.path.exists(save_path):
                self.project_info.file_size = os.path.getsize(save_path)

            self.is_modified = False
            self.saved.emit(save_path)

            return True

        except Exception as e:
            self.error_occurred.emit(f"保存项目失败: {str(e)}")
            return False

    def auto_save(self):
        """自动保存"""
        if self.is_modified and self.project_info.file_path:
            # 创建自动保存文件
            auto_save_path = self.project_info.file_path.replace('.vecp', '_autosave.vecp')
            if self.save_to_file(auto_save_path):
                self.project_info.metadata.last_backup = datetime.now().isoformat()
                self.backup_created.emit(auto_save_path)

    def create_backup(self) -> str:
        """创建项目备份"""
        try:
            if not self.project_info.file_path:
                return ""

            # 创建备份目录
            backup_dir = os.path.join(self.project_info.project_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"{self.project_info.name}_{timestamp}.vecp")

            # 复制项目文件
            shutil.copy2(self.project_info.file_path, backup_file)

            # 清理旧备份
            self._cleanup_old_backups(backup_dir)

            self.project_info.metadata.last_backup = datetime.now().isoformat()
            self.backup_created.emit(backup_file)

            return backup_file

        except Exception as e:
            self.error_occurred.emit(f"创建备份失败: {str(e)}")
            return ""

    def restore_from_backup(self, backup_file: str) -> bool:
        """从备份恢复项目"""
        try:
            if not os.path.exists(backup_file):
                self.error_occurred.emit("备份文件不存在")
                return False

            # 恢复项目文件
            shutil.copy2(backup_file, self.project_info.file_path)

            # 重新加载项目
            return self.load_from_file(self.project_info.file_path)

        except Exception as e:
            self.error_occurred.emit(f"恢复备份失败: {str(e)}")
            return False

    def export_project(self, export_path: str, format_type: str = "json") -> bool:
        """导出项目"""
        try:
            export_data = {
                'project_info': self.project_info.to_dict(),
                'videos': self.videos,
                'audios': self.audios,
                'subtitles': self.subtitles,
                'timeline': self.timeline,
                'export_settings': self.export_settings
            }

            if format_type == "json":
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                self.error_occurred.emit(f"不支持的导出格式: {format_type}")
                return False

            self.project_info.metadata.export_count += 1
            self.project_info.update_timestamp()

            return True

        except Exception as e:
            self.error_occurred.emit(f"导出项目失败: {str(e)}")
            return False

    def import_project(self, import_path: str) -> bool:
        """导入项目"""
        try:
            if not os.path.exists(import_path):
                self.error_occurred.emit("导入文件不存在")
                return False

            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 创建新项目
            project_name = os.path.splitext(os.path.basename(import_path))[0]
            if self.create_new(project_name, f"导入的项目: {project_name}"):
                # 导入数据
                self.videos = data.get('videos', [])
                self.audios = data.get('audios', [])
                self.subtitles = data.get('subtitles', [])
                self.timeline = data.get('timeline', [])
                self.export_settings = data.get('export_settings', {})

                self.is_modified = True
                self.modified.emit()

                return True

            return False

        except Exception as e:
            self.error_occurred.emit(f"导入项目失败: {str(e)}")
            return False

    def _get_default_project_dir(self, project_name: str) -> str:
        """获取默认项目目录"""
        base_dir = os.path.expanduser("~/CineAIStudio/Projects")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return os.path.join(base_dir, safe_name)

    def _create_project_structure(self):
        """创建项目目录结构"""
        structure = [
            'videos',
            'audios',
            'subtitles',
            'effects',
            'exports',
            'backups',
            'cache',
            'temp'
        ]

        for dir_name in structure:
            dir_path = os.path.join(self.project_info.project_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)

    def _init_auto_save(self):
        """初始化自动保存"""
        if self.project_info.settings.auto_save_interval > 0:
            self.auto_save_timer.setInterval(self.project_info.settings.auto_save_interval * 1000)
            self.auto_save_timer.start()

    def _cleanup_old_backups(self, backup_dir: str):
        """清理旧备份"""
        try:
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.endswith('.vecp'):
                    file_path = os.path.join(backup_dir, file)
                    backup_files.append((file_path, os.path.getmtime(file_path)))

            # 按修改时间排序
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # 删除超过数量的备份
            max_backups = self.project_info.settings.backup_count
            for file_path, _ in backup_files[max_backups:]:
                os.remove(file_path)

        except Exception as e:
            print(f"清理备份失败: {e}")

    def cleanup(self):
        """清理项目资源"""
        # 停止自动保存
        self.auto_save_timer.stop()

        # 清理临时文件
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

        # 清理缓存目录
        if self.cache_dir and os.path.exists(self.cache_dir):
            try:
                shutil.rmtree(self.cache_dir)
            except:
                pass

    def get_crash_recovery_info(self) -> Dict[str, Any]:
        """获取崩溃恢复信息"""
        return {
            'project_id': self.project_info.id,
            'project_name': self.project_info.name,
            'file_path': self.project_info.file_path,
            'last_modified': self.project_info.modified_at,
            'auto_save_path': self.project_info.file_path.replace('.vecp', '_autosave.vecp'),
            'backup_files': self._get_backup_files()
        }

    def _get_backup_files(self) -> List[str]:
        """获取备份文件列表"""
        backup_files = []
        if self.project_info.project_dir:
            backup_dir = os.path.join(self.project_info.project_dir, 'backups')
            if os.path.exists(backup_dir):
                for file in os.listdir(backup_dir):
                    if file.endswith('.vecp'):
                        backup_files.append(os.path.join(backup_dir, file))
        return backup_files

    def __del__(self):
        """析构函数"""
        self.cleanup()
