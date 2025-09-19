#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目模板管理器 - 提供专业项目模板管理功能
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal
import logging

from app.core.project_manager import ProjectTemplate


@dataclass
class TemplateCategory:
    """模板分类"""
    id: str
    name: str
    description: str = ""
    icon: str = ""
    color: str = "#1890ff"
    sort_order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateCategory':
        return cls(**data)


@dataclass
class TemplateVersion:
    """模板版本"""
    version: str
    release_date: str
    changelog: str = ""
    compatibility: str = "2.0+"
    is_latest: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateVersion':
        return cls(**data)


@dataclass
class EnhancedProjectTemplate(ProjectTemplate):
    """增强的项目模板"""
    versions: List[TemplateVersion] = field(default_factory=list)
    usage_count: int = 0
    rating: float = 0.0
    download_count: int = 0
    author: str = ""
    preview_url: str = ""
    dependencies: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['versions'] = [v.to_dict() for v in self.versions]
        data.update({
            'usage_count': self.usage_count,
            'rating': self.rating,
            'download_count': self.download_count,
            'author': self.author,
            'preview_url': self.preview_url,
            'dependencies': self.dependencies,
            'requirements': self.requirements,
            'custom_settings': self.custom_settings
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedProjectTemplate':
        if 'settings' in data:
            data['settings'] = ProjectSettings.from_dict(data['settings'])
        
        versions = []
        if 'versions' in data:
            versions = [TemplateVersion.from_dict(v) for v in data['versions']]
        
        # 提取增强字段
        enhanced_fields = {
            'versions': versions,
            'usage_count': data.get('usage_count', 0),
            'rating': data.get('rating', 0.0),
            'download_count': data.get('download_count', 0),
            'author': data.get('author', ''),
            'preview_url': data.get('preview_url', ''),
            'dependencies': data.get('dependencies', []),
            'requirements': data.get('requirements', {}),
            'custom_settings': data.get('custom_settings', {})
        }
        
        return cls(**{**data, **enhanced_fields})


class ProjectTemplateManager(QObject):
    """项目模板管理器"""
    
    # 信号定义
    template_added = pyqtSignal(EnhancedProjectTemplate)      # 模板添加信号
    template_updated = pyqtSignal(EnhancedProjectTemplate)    # 模板更新信号
    template_deleted = pyqtSignal(str)                       # 模板删除信号
    template_imported = pyqtSignal(EnhancedProjectTemplate)    # 模板导入信号
    template_exported = pyqtSignal(str)                       # 模板导出信号
    categories_updated = pyqtSignal(list)                      # 分类更新信号
    error_occurred = pyqtSignal(str)                          # 错误信号
    
    def __init__(self, templates_dir: str = None):
        super().__init__()
        
        self.templates_dir = Path(templates_dir or Path.home() / "CineAIStudio" / "Templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 模板和分类数据
        self._templates: Dict[str, EnhancedProjectTemplate] = {}
        self._categories: Dict[str, TemplateCategory] = {}
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 初始化
        self._init_categories()
        self._load_templates()
    
    def _init_categories(self):
        """初始化模板分类"""
        default_categories = [
            TemplateCategory(
                id="commentary",
                name="解说视频",
                description="适用于电影解说、游戏解说等",
                icon="🎬",
                color="#1890ff",
                sort_order=1
            ),
            TemplateCategory(
                id="compilation",
                name="混剪视频",
                description="适用于素材混剪、精彩集锦等",
                icon="🎞️",
                color="#52c41a",
                sort_order=2
            ),
            TemplateCategory(
                id="monologue",
                name="独白视频",
                description="适用于口播、演讲、独白等",
                icon="🎤",
                color="#faad14",
                sort_order=3
            ),
            TemplateCategory(
                id="tutorial",
                name="教程视频",
                description="适用于软件教程、知识分享等",
                icon="📚",
                color="#722ed1",
                sort_order=4
            ),
            TemplateCategory(
                id="vlog",
                name="Vlog视频",
                description="适用于生活记录、旅行vlog等",
                icon="📹",
                color="#eb2f96",
                sort_order=5
            ),
            TemplateCategory(
                id="promotion",
                name="宣传视频",
                description="适用于产品推广、广告宣传等",
                icon="📢",
                color="#f5222d",
                sort_order=6
            )
        ]
        
        for category in default_categories:
            self._categories[category.id] = category
    
    def _load_templates(self):
        """加载所有模板"""
        try:
            # 加载内置模板
            self._load_builtin_templates()
            
            # 加载用户自定义模板
            self._load_user_templates()
            
        except Exception as e:
            self._logger.error(f"加载模板失败: {e}")
            self.error_occurred.emit(f"加载模板失败: {e}")
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        builtin_templates = [
            # 电影解说模板
            EnhancedProjectTemplate(
                id="movie_commentary_pro",
                name="专业电影解说",
                description="适用于专业电影解说视频制作，包含字幕、配音、特效等完整流程",
                category="commentary",
                author="CineAIStudio",
                versions=[
                    TemplateVersion(
                        version="2.0",
                        release_date="2024-01-01",
                        changelog="新增AI字幕生成功能",
                        compatibility="2.0+"
                    )
                ],
                requirements={
                    "min_resolution": "1280x720",
                    "recommended_duration": "300-1800",
                    "ai_features": ["subtitle_generation", "voice_synthesis"]
                },
                custom_settings={
                    "subtitle_style": "professional",
                    "voice_type": "male_profound",
                    "background_music": true,
                    "intro_outro": true
                }
            ),
            
            # 游戏解说模板
            EnhancedProjectTemplate(
                id="game_commentary_esports",
                name="电竞游戏解说",
                description="专为电竞游戏解说设计，支持实时录制、精彩时刻标记",
                category="commentary",
                author="CineAIStudio",
                versions=[
                    TemplateVersion(
                        version="1.5",
                        release_date="2024-01-05",
                        changelog="优化游戏录制性能",
                        compatibility="2.0+"
                    )
                ],
                requirements={
                    "min_resolution": "1920x1080",
                    "recommended_duration": "600-3600",
                    "ai_features": ["highlight_detection", "game_analysis"]
                },
                custom_settings={
                    "recording_mode": "game_capture",
                    "highlight_detection": true,
                    "performance_overlay": true,
                    "watermark": true
                }
            ),
            
            # 短视频混剪模板
            EnhancedProjectTemplate(
                id="short_video_trending",
                name="热门短视频混剪",
                description="快速制作热门短视频合集，支持多种转场特效",
                category="compilation",
                author="CineAIStudio",
                versions=[
                    TemplateVersion(
                        version="2.1",
                        release_date="2024-01-10",
                        changelog="新增智能配乐功能",
                        compatibility="2.0+"
                    )
                ],
                requirements={
                    "min_resolution": "1080x1920",
                    "recommended_duration": "15-60",
                    "ai_features": ["auto_cut", "music_matching", "trend_analysis"]
                },
                custom_settings={
                    "aspect_ratio": "9:16",
                    "auto_transition": true,
                    "trending_effects": true,
                    "auto_caption": true
                }
            ),
            
            # 教程模板
            EnhancedProjectTemplate(
                id="tutorial_software_demo",
                name="软件演示教程",
                description="专业的软件演示和教程制作模板",
                category="tutorial",
                author="CineAIStudio",
                versions=[
                    TemplateVersion(
                        version="1.8",
                        release_date="2024-01-08",
                        changelog="增强屏幕录制功能",
                        compatibility="2.0+"
                    )
                ],
                requirements={
                    "min_resolution": "1920x1080",
                    "recommended_duration": "300-3600",
                    "ai_features": ["screen_recording", "step_highlighting"]
                },
                custom_settings={
                    "recording_mode": "screen_capture",
                    "zoom_pan": true,
                    "mouse_highlight": true,
                    "chapter_markers": true
                }
            ),
            
            # Vlog模板
            EnhancedProjectTemplate(
                id="vlog_life_style",
                name="生活方式Vlog",
                description="记录日常生活，分享美好时光",
                category="vlog",
                author="CineAIStudio",
                versions=[
                    TemplateVersion(
                        version="1.2",
                        release_date="2024-01-12",
                        changelog="新增滤镜和调色功能",
                        compatibility="2.0+"
                    )
                ],
                requirements={
                    "min_resolution": "1920x1080",
                    "recommended_duration": "180-600",
                    "ai_features": ["auto_color_grading", "scene_detection"]
                },
                custom_settings={
                    "color_filter": "warm",
                    "background_music": true,
                    "text_overlay": true,
                    "location_tags": true
                }
            )
        ]
        
        for template in builtin_templates:
            self._templates[template.id] = template
    
    def _load_user_templates(self):
        """加载用户自定义模板"""
        template_file = self.templates_dir / "user_templates.json"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                for data in template_data:
                    template = EnhancedProjectTemplate.from_dict(data)
                    self._templates[template.id] = template
                
            except Exception as e:
                self._logger.error(f"加载用户模板失败: {e}")
    
    def get_all_templates(self) -> List[EnhancedProjectTemplate]:
        """获取所有模板"""
        return list(self._templates.values())
    
    def get_template_by_id(self, template_id: str) -> Optional[EnhancedProjectTemplate]:
        """根据ID获取模板"""
        return self._templates.get(template_id)
    
    def get_templates_by_category(self, category_id: str) -> List[EnhancedProjectTemplate]:
        """根据分类获取模板"""
        return [t for t in self._templates.values() if t.category == category_id]
    
    def get_categories(self) -> List[TemplateCategory]:
        """获取所有分类"""
        return sorted(self._categories.values(), key=lambda x: x.sort_order)
    
    def get_category_by_id(self, category_id: str) -> Optional[TemplateCategory]:
        """根据ID获取分类"""
        return self._categories.get(category_id)
    
    def add_template(self, template: EnhancedProjectTemplate) -> bool:
        """添加模板"""
        try:
            template.created_at = datetime.now().isoformat()
            self._templates[template.id] = template
            
            # 保存到用户模板文件
            self._save_user_templates()
            
            # 增加使用计数
            template.usage_count += 1
            
            self.template_added.emit(template)
            self._logger.info(f"添加模板: {template.name}")
            
            return True
            
        except Exception as e:
            error_msg = f"添加模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def update_template(self, template_id: str, updated_data: Dict[str, Any]) -> bool:
        """更新模板"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return False
            
            # 更新模板数据
            for key, value in updated_data.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            # 保存到用户模板文件
            self._save_user_templates()
            
            self.template_updated.emit(template)
            self._logger.info(f"更新模板: {template.name}")
            
            return True
            
        except Exception as e:
            error_msg = f"更新模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return False
            
            # 不能删除内置模板
            if template.author == "CineAIStudio":
                self.error_occurred.emit("不能删除内置模板")
                return False
            
            del self._templates[template_id]
            
            # 保存到用户模板文件
            self._save_user_templates()
            
            self.template_deleted.emit(template_id)
            self._logger.info(f"删除模板: {template.name}")
            
            return True
            
        except Exception as e:
            error_msg = f"删除模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def import_template(self, file_path: str) -> bool:
        """导入模板"""
        try:
            if not os.path.exists(file_path):
                self.error_occurred.emit("模板文件不存在")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            template = EnhancedProjectTemplate.from_dict(template_data)
            
            # 检查ID冲突
            if template.id in self._templates:
                # 生成新的ID
                template.id = f"{template.id}_{uuid.uuid4().hex[:8]}"
            
            template.author = "用户导入"
            template.usage_count = 0
            template.download_count = 0
            
            self._templates[template.id] = template
            self._save_user_templates()
            
            self.template_imported.emit(template)
            self._logger.info(f"导入模板: {template.name}")
            
            return True
            
        except Exception as e:
            error_msg = f"导入模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def export_template(self, template_id: str, export_path: str) -> bool:
        """导出模板"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return False
            
            # 准备导出数据
            export_data = template.to_dict()
            
            # 导出模板
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # 增加下载计数
            template.download_count += 1
            
            self.template_exported.emit(export_path)
            self._logger.info(f"导出模板: {template.name}")
            
            return True
            
        except Exception as e:
            error_msg = f"导出模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def rate_template(self, template_id: str, rating: float) -> bool:
        """评分模板"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return False
            
            # 更新评分（简单平均）
            if template.rating > 0:
                template.rating = (template.rating + rating) / 2
            else:
                template.rating = rating
            
            self._save_user_templates()
            self.template_updated.emit(template)
            
            return True
            
        except Exception as e:
            error_msg = f"评分模板失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def search_templates(self, query: str) -> List[EnhancedProjectTemplate]:
        """搜索模板"""
        query = query.lower()
        results = []
        
        for template in self._templates.values():
            if (query in template.name.lower() or 
                query in template.description.lower() or
                any(query in tag.lower() for tag in template.custom_settings.get('tags', []))):
                results.append(template)
        
        return results
    
    def get_popular_templates(self, limit: int = 10) -> List[EnhancedProjectTemplate]:
        """获取热门模板"""
        return sorted(
            self._templates.values(),
            key=lambda x: (x.usage_count, x.download_count, x.rating),
            reverse=True
        )[:limit]
    
    def get_recent_templates(self, limit: int = 10) -> List[EnhancedProjectTemplate]:
        """获取最新模板"""
        return sorted(
            self._templates.values(),
            key=lambda x: x.versions[0].release_date if x.versions else x.created_at,
            reverse=True
        )[:limit]
    
    def _save_user_templates(self):
        """保存用户模板"""
        try:
            user_templates = []
            for template in self._templates.values():
                if template.author != "CineAIStudio":
                    user_templates.append(template.to_dict())
            
            template_file = self.templates_dir / "user_templates.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(user_templates, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self._logger.error(f"保存用户模板失败: {e}")
    
    def create_template_from_project(self, project_data: Dict[str, Any], 
                                    template_info: Dict[str, Any]) -> EnhancedProjectTemplate:
        """从项目创建模板"""
        try:
            template_id = f"template_{uuid.uuid4().hex[:8]}"
            
            template = EnhancedProjectTemplate(
                id=template_id,
                name=template_info.get('name', '自定义模板'),
                description=template_info.get('description', '从项目创建的模板'),
                category=template_info.get('category', 'custom'),
                author=template_info.get('author', '用户'),
                thumbnail_path=template_info.get('thumbnail_path', ''),
                preview_url=template_info.get('preview_url', ''),
                custom_settings=template_info.get('custom_settings', {})
            )
            
            # 从项目数据中提取设置
            if 'project_info' in project_data:
                project_info = project_data['project_info']
                if 'settings' in project_info:
                    template.settings = project_info['settings']
            
            # 提取AI设置
            if 'ai_settings' in project_data:
                template.ai_settings = project_data['ai_settings']
            
            # 提取导出设置
            if 'export_settings' in project_data:
                template.export_settings = project_data['export_settings']
            
            # 提取时间线模板
            if 'timeline' in project_data:
                template.timeline_template = project_data['timeline']
            
            return template
            
        except Exception as e:
            self._logger.error(f"从项目创建模板失败: {e}")
            raise
    
    def validate_template(self, template: EnhancedProjectTemplate) -> List[str]:
        """验证模板数据"""
        errors = []
        
        # 检查必需字段
        if not template.name:
            errors.append("模板名称不能为空")
        
        if not template.category:
            errors.append("模板分类不能为空")
        
        if template.category not in self._categories:
            errors.append(f"无效的分类: {template.category}")
        
        # 检查设置
        if not template.settings:
            errors.append("模板设置不能为空")
        
        # 检查版本信息
        if not template.versions:
            errors.append("模板版本信息不能为空")
        
        return errors
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        stats = {
            'total_templates': len(self._templates),
            'builtin_templates': len([t for t in self._templates.values() if t.author == "CineAIStudio"]),
            'user_templates': len([t for t in self._templates.values() if t.author != "CineAIStudio"]),
            'total_usage': sum(t.usage_count for t in self._templates.values()),
            'total_downloads': sum(t.download_count for t in self._templates.values()),
            'average_rating': sum(t.rating for t in self._templates.values()) / len(self._templates) if self._templates else 0,
            'categories': len(self._categories)
        }
        
        return stats