#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理器核心类
提供完整的项目生命周期管理功能
"""

import json
import os
import uuid
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings
from PyQt6.QtWidgets import QMessageBox, QApplication

from .project import Project, ProjectInfo, ProjectSettings, ProjectMetadata
from .video_manager import VideoManager


@dataclass
class ProjectTemplate:
    """项目模板"""
    id: str
    name: str
    description: str
    category: str
    thumbnail_path: str = ""
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    timeline_template: Dict[str, Any] = field(default_factory=dict)
    ai_settings: Dict[str, Any] = field(default_factory=dict)
    export_settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectTemplate':
        if 'settings' in data:
            data['settings'] = ProjectSettings.from_dict(data['settings'])
        return cls(**data)


@dataclass
class ProjectStatistics:
    """项目统计信息"""
    total_projects: int = 0
    active_projects: int = 0
    completed_projects: int = 0
    total_editing_time: int = 0  # 总编辑时间（小时）
    total_videos_processed: int = 0
    total_exports: int = 0
    disk_usage: int = 0  # 磁盘使用量（字节）
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class ProjectManager(QObject):
    """项目管理器"""

    # 信号定义
    project_created = pyqtSignal(ProjectInfo)           # 项目创建信号
    project_loaded = pyqtSignal(ProjectInfo)           # 项目加载信号
    project_saved = pyqtSignal(str)                     # 项目保存信号
    project_closed = pyqtSignal()                       # 项目关闭信号
    project_deleted = pyqtSignal(str)                   # 项目删除信号
    project_list_updated = pyqtSignal()                 # 项目列表更新信号
    project_modified = pyqtSignal()                     # 项目修改信号
    template_loaded = pyqtSignal(ProjectTemplate)       # 模板加载信号
    statistics_updated = pyqtSignal(ProjectStatistics) # 统计信息更新信号
    error_occurred = pyqtSignal(str)                    # 错误信号
    backup_created = pyqtSignal(str)                    # 备份创建信号

    def __init__(self, settings_manager=None):
        super().__init__()

        self.settings_manager = settings_manager
        self.video_manager = VideoManager()

        # 当前项目
        self.current_project: Optional[Project] = None
        self.is_modified = False

        # 项目列表缓存
        self._project_list: List[ProjectInfo] = []
        self._project_templates: List[ProjectTemplate] = []
        self._recent_projects: List[str] = []

        # 统计信息
        self._statistics = ProjectStatistics()

        # 设置和配置
        self._settings = QSettings("CineAIStudio", "ProjectManager")
        self._max_recent_projects = 10
        self._auto_save_enabled = True
        self._auto_save_interval = 300  # 5分钟

        # 定时器
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save_projects)

        # 日志记录
        self._logger = logging.getLogger(__name__)

        # 初始化
        self._init_directories()
        self._load_project_templates()
        self._load_recent_projects()
        self._start_auto_save()

        # 连接信号
        self._connect_signals()

    def _init_directories(self):
        """初始化目录结构"""
        self.projects_dir = Path.home() / "CineAIStudio" / "Projects"
        self.templates_dir = Path.home() / "CineAIStudio" / "Templates"
        self.cache_dir = Path.home() / "CineAIStudio" / "Cache"

        # 创建目录
        for directory in [self.projects_dir, self.templates_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _connect_signals(self):
        """连接信号"""
        if hasattr(self.video_manager, 'video_added'):
            self.video_manager.video_added.connect(self._on_project_modified)
        if hasattr(self.video_manager, 'video_removed'):
            self.video_manager.video_removed.connect(self._on_project_modified)

    def create_new_project(self, name: str, description: str = "",
                          template: Optional[ProjectTemplate] = None) -> bool:
        """创建新项目"""
        try:
            # 创建项目
            project = Project()

            # 应用模板设置
            if template:
                project.project_info.settings = template.settings
                project.ai_settings = template.ai_settings.copy()
                project.export_settings = template.export_settings.copy()
                project.project_info.metadata.template_used = template.name

            # 创建项目
            success = project.create_new(name, description)
            if success:
                self.current_project = project
                self.is_modified = True

                # 添加到项目列表
                self._add_project_to_list(project.project_info)

                # 添加到最近项目
                self._add_to_recent_projects(project.project_info.file_path)

                # 更新统计信息
                self._update_statistics()

                # 发射信号
                self.project_created.emit(project.project_info)
                self.project_modified.emit()

                self._logger.info(f"创建新项目: {name}")
                return True

            return False

        except Exception as e:
            error_msg = f"创建项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def load_project(self, file_path: str) -> bool:
        """加载项目"""
        try:
            if not os.path.exists(file_path):
                error_msg = f"项目文件不存在: {file_path}"
                self.error_occurred.emit(error_msg)
                return False

            # 关闭当前项目
            if self.current_project:
                self.close_current_project()

            # 创建项目实例
            project = Project()

            # 加载项目
            success = project.load_from_file(file_path)
            if success:
                self.current_project = project
                self.is_modified = False

                # 添加到项目列表
                self._add_project_to_list(project.project_info)

                # 添加到最近项目
                self._add_to_recent_projects(file_path)

                # 更新统计信息
                self._update_statistics()

                # 发射信号
                self.project_loaded.emit(project.project_info)

                self._logger.info(f"加载项目: {project.project_info.name}")
                return True

            return False

        except Exception as e:
            error_msg = f"加载项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def save_project(self, file_path: Optional[str] = None) -> bool:
        """保存项目"""
        try:
            if not self.current_project:
                return False

            # 保存项目
            success = self.current_project.save_to_file(file_path)
            if success:
                self.is_modified = False

                # 更新项目列表
                self._add_project_to_list(self.current_project.project_info)

                # 更新统计信息
                self._update_statistics()

                # 发射信号
                self.project_saved.emit(self.current_project.project_info.file_path)

                self._logger.info(f"保存项目: {self.current_project.project_info.name}")
                return True

            return False

        except Exception as e:
            error_msg = f"保存项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def save_project_as(self, file_path: str) -> bool:
        """项目另存为"""
        try:
            if not self.current_project:
                return False

            # 更新项目文件路径
            old_path = self.current_project.project_info.file_path
            self.current_project.project_info.file_path = file_path

            # 保存项目
            success = self.save_project()
            if success:
                # 添加到最近项目
                self._add_to_recent_projects(file_path)

                self._logger.info(f"项目另存为: {file_path}")
                return True
            else:
                # 恢复原路径
                self.current_project.project_info.file_path = old_path
                return False

        except Exception as e:
            error_msg = f"项目另存为失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def close_current_project(self) -> bool:
        """关闭当前项目"""
        try:
            if self.current_project:
                # 检查是否需要保存
                if self.is_modified:
                    reply = QMessageBox.question(
                        None,
                        "保存项目",
                        f"项目 '{self.current_project.project_info.name}' 已修改，是否保存？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        if not self.save_project():
                            return False
                    elif reply == QMessageBox.StandardButton.Cancel:
                        return False

                # 清理项目资源
                self.current_project.cleanup()
                self.current_project = None
                self.is_modified = False

                # 发射信号
                self.project_closed.emit()

                self._logger.info("关闭当前项目")
                return True

            return True

        except Exception as e:
            error_msg = f"关闭项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            # 查找项目
            project_info = None
            for p in self._project_list:
                if p.id == project_id:
                    project_info = p
                    break

            if not project_info:
                return False

            # 如果是当前项目，先关闭
            if self.current_project and self.current_project.project_info.id == project_id:
                self.close_current_project()

            # 删除项目文件和目录
            if project_info.project_dir and os.path.exists(project_info.project_dir):
                shutil.rmtree(project_info.project_dir)

            # 从项目列表中移除
            self._project_list = [p for p in self._project_list if p.id != project_id]

            # 从最近项目中移除
            if project_info.file_path in self._recent_projects:
                self._recent_projects.remove(project_info.file_path)
                self._save_recent_projects()

            # 更新统计信息
            self._update_statistics()

            # 发射信号
            self.project_deleted.emit(project_id)
            self.project_list_updated.emit()

            self._logger.info(f"删除项目: {project_info.name}")
            return True

        except Exception as e:
            error_msg = f"删除项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def get_project_list(self, filter_text: str = "", category: str = "") -> List[ProjectInfo]:
        """获取项目列表"""
        projects = self._project_list.copy()

        # 应用过滤
        if filter_text:
            filter_text = filter_text.lower()
            projects = [p for p in projects if
                       filter_text in p.name.lower() or
                       filter_text in p.description.lower() or
                       any(filter_text in tag.lower() for tag in p.tags)]

        if category:
            projects = [p for p in projects if category in p.tags]

        # 按修改时间排序
        projects.sort(key=lambda x: x.modified_at, reverse=True)

        return projects

    def get_recent_projects(self) -> List[ProjectInfo]:
        """获取最近项目列表"""
        recent_projects = []

        for file_path in self._recent_projects:
            for project_info in self._project_list:
                if project_info.file_path == file_path:
                    recent_projects.append(project_info)
                    break

        return recent_projects

    def get_project_templates(self, category: str = "") -> List[ProjectTemplate]:
        """获取项目模板"""
        if category:
            return [t for t in self._project_templates if t.category == category]
        return self._project_templates.copy()

    def create_project_from_template(self, template_id: str, name: str, description: str = "") -> bool:
        """从模板创建项目"""
        template = None
        for t in self._project_templates:
            if t.id == template_id:
                template = t
                break

        if not template:
            self.error_occurred.emit(f"模板不存在: {template_id}")
            return False

        return self.create_new_project(name, description, template)

    def export_project(self, export_path: str, format_type: str = "json") -> bool:
        """导出项目"""
        try:
            if not self.current_project:
                return False

            success = self.current_project.export_project(export_path, format_type)
            if success:
                self._logger.info(f"导出项目: {export_path}")
                return True

            return False

        except Exception as e:
            error_msg = f"导出项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def import_project(self, import_path: str) -> bool:
        """导入项目"""
        try:
            # 关闭当前项目
            if self.current_project:
                self.close_current_project()

            # 创建新项目
            project = Project()
            success = project.import_project(import_path)

            if success:
                self.current_project = project
                self.is_modified = True

                # 添加到项目列表
                self._add_project_to_list(project.project_info)

                # 添加到最近项目
                self._add_to_recent_projects(project.project_info.file_path)

                # 更新统计信息
                self._update_statistics()

                # 发射信号
                self.project_loaded.emit(project.project_info)

                self._logger.info(f"导入项目: {import_path}")
                return True

            return False

        except Exception as e:
            error_msg = f"导入项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def backup_project(self) -> str:
        """备份项目"""
        try:
            if not self.current_project:
                return ""

            backup_path = self.current_project.create_backup()
            if backup_path:
                self.backup_created.emit(backup_path)
                self._logger.info(f"创建项目备份: {backup_path}")

            return backup_path

        except Exception as e:
            error_msg = f"备份项目失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return ""

    def restore_project_from_backup(self, backup_path: str) -> bool:
        """从备份恢复项目"""
        try:
            if not self.current_project:
                return False

            success = self.current_project.restore_from_backup(backup_path)
            if success:
                self.is_modified = False
                self._logger.info(f"从备份恢复项目: {backup_path}")

            return success

        except Exception as e:
            error_msg = f"恢复备份失败: {str(e)}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def get_project_statistics(self) -> ProjectStatistics:
        """获取项目统计信息"""
        return self._statistics

    def search_projects(self, query: str, search_fields: List[str] = None) -> List[ProjectInfo]:
        """搜索项目"""
        if not search_fields:
            search_fields = ['name', 'description', 'tags']

        query = query.lower()
        results = []

        for project in self._project_list:
            match = False

            for field in search_fields:
                if field == 'name' and query in project.name.lower():
                    match = True
                    break
                elif field == 'description' and query in project.description.lower():
                    match = True
                    break
                elif field == 'tags':
                    if any(query in tag.lower() for tag in project.tags):
                        match = True
                        break

            if match:
                results.append(project)

        return results

    def _load_project_templates(self):
        """加载项目模板"""
        self._project_templates = []

        # 默认模板
        default_templates = [
            ProjectTemplate(
                id="commentary_template",
                name="解说视频",
                description="适用于游戏解说、教程视频制作",
                category="解说",
                settings=ProjectSettings(
                    resolution="1920x1080",
                    frame_rate=30,
                    video_quality="high"
                )
            ),
            ProjectTemplate(
                id="compilation_template",
                name="混剪视频",
                description="适用于素材混剪、精彩集锦制作",
                category="混剪",
                settings=ProjectSettings(
                    resolution="1920x1080",
                    frame_rate=60,
                    video_quality="high"
                )
            ),
            ProjectTemplate(
                id="monologue_template",
                name="独白视频",
                description="适用于口播、演讲视频制作",
                category="独白",
                settings=ProjectSettings(
                    resolution="1920x1080",
                    frame_rate=30,
                    video_quality="high"
                )
            )
        ]

        self._project_templates.extend(default_templates)

        # 加载自定义模板
        template_file = self.templates_dir / "templates.json"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                for data in template_data:
                    template = ProjectTemplate.from_dict(data)
                    self._project_templates.append(template)

            except Exception as e:
                self._logger.error(f"加载项目模板失败: {e}")

    def _load_recent_projects(self):
        """加载最近项目"""
        self._recent_projects = self._settings.value("recent_projects", [], str)

    def _save_recent_projects(self):
        """保存最近项目"""
        self._settings.setValue("recent_projects", self._recent_projects)

    def _add_to_recent_projects(self, file_path: str):
        """添加到最近项目"""
        if file_path in self._recent_projects:
            self._recent_projects.remove(file_path)

        self._recent_projects.insert(0, file_path)

        # 限制数量
        if len(self._recent_projects) > self._max_recent_projects:
            self._recent_projects = self._recent_projects[:self._max_recent_projects]

        self._save_recent_projects()

    def _add_project_to_list(self, project_info: ProjectInfo):
        """添加项目到列表"""
        # 检查是否已存在
        for i, p in enumerate(self._project_list):
            if p.id == project_info.id:
                self._project_list[i] = project_info
                break
        else:
            self._project_list.append(project_info)

        self.project_list_updated.emit()

    def _update_statistics(self):
        """更新统计信息"""
        try:
            self._statistics.total_projects = len(self._project_list)
            self._statistics.active_projects = len([p for p in self._project_list if p.status in ["draft", "editing"]])
            self._statistics.completed_projects = len([p for p in self._project_list if p.status == "completed"])

            # 计算总编辑时间
            total_time = sum(p.metadata.total_editing_time for p in self._project_list)
            self._statistics.total_editing_time = total_time // 3600  # 转换为小时

            # 计算磁盘使用量
            total_size = sum(p.file_size for p in self._project_list)
            self._statistics.disk_usage = total_size

            # 统计处理视频数
            total_videos = sum(p.video_count for p in self._project_list)
            self._statistics.total_videos_processed = total_videos

            # 统计导出次数
            total_exports = sum(p.metadata.export_count for p in self._project_list)
            self._statistics.total_exports = total_exports

            self._statistics.last_updated = datetime.now().isoformat()

            self.statistics_updated.emit(self._statistics)

        except Exception as e:
            self._logger.error(f"更新统计信息失败: {e}")

    def _start_auto_save(self):
        """启动自动保存"""
        if self._auto_save_enabled:
            self._auto_save_timer.start(self._auto_save_interval * 1000)

    def _auto_save_projects(self):
        """自动保存项目"""
        if self._auto_save_enabled and self.current_project and self.is_modified:
            self._logger.info("执行自动保存")
            self.save_project()

    def _on_project_modified(self):
        """项目修改回调"""
        if self.current_project:
            self.is_modified = True
            self.project_modified.emit()

    def get_current_project(self) -> Optional[Project]:
        """获取当前项目"""
        return self.current_project

    def is_project_modified(self) -> bool:
        """检查项目是否已修改"""
        return self.is_modified

    def cleanup(self):
        """清理资源"""
        # 停止自动保存
        self._auto_save_timer.stop()

        # 关闭当前项目
        if self.current_project:
            self.close_current_project()

        self._logger.info("项目管理器清理完成")

    def __del__(self):
        """析构函数"""
        self.cleanup()
