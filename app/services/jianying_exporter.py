"""
剪映格式导出器
支持将项目导出为剪映兼容的草稿格式
"""

import json
import zipfile
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import uuid

from app.core.base import BaseComponent
from app.core.events import Event, EventType
from app.core.utils import LoggerMixin
from app.services.jianying_parser import JianyingDraft, MediaTrack


class JianyingExporter(BaseComponent, LoggerMixin):
    """剪映格式导出器"""

    def __init__(self):
        super().__init__()
        self.supported_formats = ['jianying', 'capcut', 'draft']
        self.logger.info("剪映格式导出器初始化完成")

    def export_to_jianying(self, project_data: Dict[str, Any], output_path: Union[str, Path], 
                          format_type: str = 'jianying') -> str:
        """导出项目为剪映格式"""
        output_path = Path(output_path)
        self.logger.info(f"导出项目到剪映格式: {output_path}")
        
        # 发送导出开始事件
        self.emit_event(Event(
            type=EventType.EXPORT_START,
            data={'format': format_type, 'output_path': str(output_path)}
        ))
        
        try:
            # 转换项目数据为剪映格式
            jianying_draft = self._convert_to_jianying_format(project_data)
            
            # 根据格式类型导出
            if format_type == 'jianying':
                return self._export_as_json(jianying_draft, output_path)
            elif format_type == 'capcut':
                return self._export_as_zip(jianying_draft, output_path)
            else:
                raise ValueError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            self.logger.error(f"导出剪映格式失败: {e}")
            self.emit_event(Event(
                type=EventType.EXPORT_ERROR,
                data={'error': str(e)}
            ))
            raise

    def _convert_to_jianying_format(self, project_data: Dict[str, Any]) -> JianyingDraft:
        """将项目数据转换为剪映格式"""
        self.logger.info("转换项目数据为剪映格式")
        
        tracks = []
        
        # 转换轨道数据
        for track_data in project_data.get('tracks', []):
            timeline = track_data.get('timeline', {})
            track = MediaTrack(
                id=track_data.get('id', str(uuid.uuid4())),
                type=track_data.get('type', 'video'),
                source_path=track_data.get('source_path', ''),
                start_time=float(timeline.get('start', 0)),
                end_time=float(timeline.get('end', 0)),
                duration=float(timeline.get('duration', 0)),
                position=track_data.get('transform', {'x': 0, 'y': 0, 'scale': 1.0}),
                opacity=float(track_data.get('properties', {}).get('opacity', 1.0)),
                volume=float(track_data.get('properties', {}).get('volume', 1.0)),
                effects=track_data.get('effects', []),
                transitions=track_data.get('transitions', [])
            )
            tracks.append(track)
        
        # 获取项目设置
        settings = project_data.get('settings', {})
        
        return JianyingDraft(
            version='2.0',  # 剪映专业版格式版本
            created_at=datetime.fromisoformat(project_data.get('created_at', datetime.now().isoformat())),
            modified_at=datetime.now(),
            duration=float(settings.get('duration', 0)),
            resolution=settings.get('resolution', {'width': 1920, 'height': 1080}),
            fps=int(settings.get('fps', 30)),
            tracks=tracks,
            metadata=project_data.get('metadata', {}),
            project_settings=project_data.get('project_settings', {})
        )

    def _export_as_json(self, draft: JianyingDraft, output_path: Path) -> str:
        """导出为JSON格式"""
        self.logger.info("导出为JSON格式")
        
        # 转换为剪映JSON格式
        jianying_data = {
            'version': draft.version,
            'created_at': draft.created_at.isoformat(),
            'modified_at': draft.modified_at.isoformat(),
            'duration': draft.duration,
            'resolution': draft.resolution,
            'fps': draft.fps,
            'tracks': [],
            'metadata': draft.metadata,
            'project_settings': draft.project_settings
        }
        
        # 转换轨道数据
        for track in draft.tracks:
            track_data = {
                'id': track.id,
                'type': track.type,
                'source_path': track.source_path,
                'start_time': track.start_time,
                'end_time': track.end_time,
                'duration': track.duration,
                'position': track.position,
                'opacity': track.opacity,
                'volume': track.volume,
                'effects': track.effects,
                'transitions': track.transitions
            }
            jianying_data['tracks'].append(track_data)
        
        # 写入JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(jianying_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON导出完成: {output_path}")
        return str(output_path)

    def _export_as_zip(self, draft: JianyingDraft, output_path: Path) -> str:
        """导出为ZIP格式（剪映专业版）"""
        self.logger.info("导出为ZIP格式")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建项目文件结构
            project_dir = temp_path / 'project'
            project_dir.mkdir(parents=True)
            
            # 创建主草稿文件
            draft_file = project_dir / 'draft.json'
            self._export_as_json(draft, draft_file)
            
            # 创建媒体文件目录
            media_dir = project_dir / 'media'
            media_dir.mkdir()
            
            # 复制媒体文件（如果存在）
            self._copy_media_files(draft, media_dir)
            
            # 创建项目配置文件
            config_file = project_dir / 'config.json'
            self._create_config_file(draft, config_file)
            
            # 创建ZIP文件
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_path)
                        zipf.write(file_path, arcname)
        
        self.logger.info(f"ZIP导出完成: {output_path}")
        return str(output_path)

    def _copy_media_files(self, draft: JianyingDraft, media_dir: Path):
        """复制媒体文件到项目目录"""
        self.logger.info("复制媒体文件")
        
        copied_files = set()
        
        for track in draft.tracks:
            source_path = Path(track.source_path)
            if source_path.exists() and source_path.is_file():
                # 生成唯一文件名
                file_name = f"{track.id}_{source_path.name}"
                dest_path = media_dir / file_name
                
                # 避免重复复制
                if file_name not in copied_files:
                    shutil.copy2(source_path, dest_path)
                    copied_files.add(file_name)
                    
                    # 更新轨道中的源路径
                    track.source_path = f"media/{file_name}"

    def _create_config_file(self, draft: JianyingDraft, config_path: Path):
        """创建项目配置文件"""
        config_data = {
            'project_version': '2.0',
            'app_version': '剪映专业版',
            'created_at': draft.created_at.isoformat(),
            'modified_at': draft.modified_at.isoformat(),
            'settings': {
                'resolution': draft.resolution,
                'fps': draft.fps,
                'duration': draft.duration,
                'audio_sample_rate': 48000,
                'audio_bitrate': 128000,
                'video_bitrate': 8000000
            },
            'effects': [],
            'transitions': [],
            'templates': []
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def create_template(self, project_data: Dict[str, Any], template_name: str, 
                       template_path: Union[str, Path]) -> str:
        """创建剪映模板"""
        template_path = Path(template_path)
        self.logger.info(f"创建剪映模板: {template_name}")
        
        # 添加模板元数据
        template_data = project_data.copy()
        template_data['metadata'] = template_data.get('metadata', {})
        template_data['metadata']['template'] = {
            'name': template_name,
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'description': f'VideoEpicCreator生成的模板: {template_name}',
            'tags': ['AI生成', '自动剪辑', '智能解说']
        }
        
        # 导出为模板格式
        return self.export_to_jianying(template_data, template_path, 'capcut')

    def batch_export(self, projects: List[Dict[str, Any]], output_dir: Union[str, Path], 
                    format_type: str = 'jianying') -> List[str]:
        """批量导出项目"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"批量导出 {len(projects)} 个项目")
        
        exported_files = []
        
        for i, project in enumerate(projects):
            try:
                project_name = project.get('metadata', {}).get('name', f'project_{i}')
                output_path = output_dir / f"{project_name}.{format_type}"
                
                exported_file = self.export_to_jianying(project, output_path, format_type)
                exported_files.append(exported_file)
                
                self.logger.info(f"项目 {i+1}/{len(projects)} 导出完成")
                
            except Exception as e:
                self.logger.error(f"导出项目 {i+1} 失败: {e}")
                continue
        
        return exported_files

    def get_export_formats(self) -> List[Dict[str, Any]]:
        """获取支持的导出格式信息"""
        return [
            {
                'id': 'jianying',
                'name': '剪映草稿',
                'extension': '.json',
                'description': '剪映标准草稿格式',
                'compatibility': '剪映、剪映专业版'
            },
            {
                'id': 'capcut',
                'name': '剪映专业版',
                'extension': '.zip',
                'description': '剪映专业版完整项目格式',
                'compatibility': '剪映专业版'
            }
        ]

    def validate_export_data(self, project_data: Dict[str, Any]) -> bool:
        """验证导出数据的有效性"""
        self.logger.info("验证导出数据")
        
        # 检查必要字段
        if 'tracks' not in project_data:
            self.logger.warning("项目数据中缺少轨道信息")
            return False
        
        # 检查轨道数据
        for track in project_data['tracks']:
            if 'source_path' not in track or not track['source_path']:
                self.logger.warning("轨道缺少源文件路径")
                return False
        
        # 检查项目设置
        settings = project_data.get('settings', {})
        if 'resolution' not in settings:
            self.logger.warning("项目设置中缺少分辨率信息")
            return False
        
        self.logger.info("导出数据验证通过")
        return True