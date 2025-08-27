"""
剪映草稿解析器
支持剪映和剪映专业版的草稿文件格式解析和转换
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import zipfile
import tempfile
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from app.core.base import BaseComponent
from app.core.events import Event, EventType
from app.core.utils import LoggerMixin


@dataclass
class MediaTrack:
    """媒体轨道数据结构"""
    id: str
    type: str  # video, audio, image, text
    source_path: str
    start_time: float
    end_time: float
    duration: float
    position: Dict[str, float]  # x, y, scale
    opacity: float = 1.0
    volume: float = 1.0
    effects: List[Dict] = None
    transitions: List[Dict] = None

    def __post_init__(self):
        if self.effects is None:
            self.effects = []
        if self.transitions is None:
            self.transitions = []


@dataclass
class JianyingDraft:
    """剪映草稿数据结构"""
    version: str
    created_at: datetime
    modified_at: datetime
    duration: float
    resolution: Dict[str, int]  # width, height
    fps: int
    tracks: List[MediaTrack]
    metadata: Dict[str, Any]
    project_settings: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['modified_at'] = self.modified_at.isoformat()
        return result


class JianyingDraftParser(BaseComponent, LoggerMixin):
    """剪映草稿解析器"""

    def __init__(self):
        super().__init__()
        self.supported_formats = ['.json', '.draft', '.zip']
        self.logger.info("剪映草稿解析器初始化完成")

    def parse_draft(self, file_path: Union[str, Path]) -> JianyingDraft:
        """解析剪映草稿文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"草稿文件不存在: {file_path}")

        # 根据文件扩展名选择解析方法
        if file_path.suffix.lower() == '.zip':
            return self._parse_zip_draft(file_path)
        elif file_path.suffix.lower() in ['.json', '.draft']:
            return self._parse_json_draft(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    def _parse_zip_draft(self, file_path: Path) -> JianyingDraft:
        """解析ZIP格式的剪映草稿"""
        self.logger.info(f"解析ZIP草稿文件: {file_path}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 解压ZIP文件
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # 查找主草稿文件
            draft_file = self._find_draft_file(temp_path)
            if not draft_file:
                raise ValueError("ZIP文件中未找到有效的草稿文件")
            
            return self._parse_json_draft(draft_file)

    def _parse_json_draft(self, file_path: Path) -> JianyingDraft:
        """解析JSON格式的剪映草稿"""
        self.logger.info(f"解析JSON草稿文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析不同版本的剪映格式
        if 'version' in data:
            return self._parse_modern_format(data)
        else:
            return self._parse_legacy_format(data)

    def _parse_modern_format(self, data: Dict[str, Any]) -> JianyingDraft:
        """解析现代剪映格式"""
        tracks = []
        
        # 解析轨道
        for track_data in data.get('tracks', []):
            track = MediaTrack(
                id=track_data.get('id', str(uuid.uuid4())),
                type=track_data.get('type', 'video'),
                source_path=track_data.get('source_path', ''),
                start_time=float(track_data.get('start_time', 0)),
                end_time=float(track_data.get('end_time', 0)),
                duration=float(track_data.get('duration', 0)),
                position=track_data.get('position', {'x': 0, 'y': 0, 'scale': 1.0}),
                opacity=float(track_data.get('opacity', 1.0)),
                volume=float(track_data.get('volume', 1.0)),
                effects=track_data.get('effects', []),
                transitions=track_data.get('transitions', [])
            )
            tracks.append(track)
        
        return JianyingDraft(
            version=data.get('version', '1.0'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            modified_at=datetime.fromisoformat(data.get('modified_at', datetime.now().isoformat())),
            duration=float(data.get('duration', 0)),
            resolution=data.get('resolution', {'width': 1920, 'height': 1080}),
            fps=int(data.get('fps', 30)),
            tracks=tracks,
            metadata=data.get('metadata', {}),
            project_settings=data.get('project_settings', {})
        )

    def _parse_legacy_format(self, data: Dict[str, Any]) -> JianyingDraft:
        """解析旧版剪映格式"""
        # 旧版格式转换逻辑
        tracks = []
        
        # 解析媒体资源
        materials = data.get('materials', {})
        for material_id, material in materials.items():
            track = MediaTrack(
                id=material_id,
                type=material.get('type', 'video'),
                source_path=material.get('path', ''),
                start_time=float(material.get('start_time', 0)),
                end_time=float(material.get('end_time', 0)),
                duration=float(material.get('duration', 0)),
                position=material.get('position', {'x': 0, 'y': 0, 'scale': 1.0}),
                opacity=float(material.get('opacity', 1.0)),
                volume=float(material.get('volume', 1.0)),
                effects=material.get('effects', []),
                transitions=material.get('transitions', [])
            )
            tracks.append(track)
        
        return JianyingDraft(
            version='legacy',
            created_at=datetime.now(),
            modified_at=datetime.now(),
            duration=float(data.get('duration', 0)),
            resolution=data.get('resolution', {'width': 1920, 'height': 1080}),
            fps=int(data.get('fps', 30)),
            tracks=tracks,
            metadata=data.get('metadata', {}),
            project_settings=data.get('settings', {})
        )

    def _find_draft_file(self, directory: Path) -> Optional[Path]:
        """在目录中查找草稿文件"""
        for file_path in directory.rglob('*'):
            if file_path.suffix.lower() in ['.json', '.draft']:
                # 检查文件内容是否为有效JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    return file_path
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        return None

    def convert_to_internal_format(self, draft: JianyingDraft) -> Dict[str, Any]:
        """将剪映草稿转换为内部格式"""
        self.logger.info("转换剪映草稿为内部格式")
        
        # 发送转换开始事件
        self.emit_event(Event(
            type=EventType.DRAFT_IMPORT_START,
            data={'draft_version': draft.version}
        ))
        
        try:
            # 转换为内部项目格式
            project_data = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'modified_at': datetime.now().isoformat(),
                'source_format': 'jianying',
                'source_version': draft.version,
                'settings': {
                    'resolution': draft.resolution,
                    'fps': draft.fps,
                    'duration': draft.duration
                },
                'tracks': [],
                'effects': [],
                'metadata': draft.metadata
            }
            
            # 转换轨道
            for track in draft.tracks:
                track_data = {
                    'id': track.id,
                    'type': track.type,
                    'source_path': track.source_path,
                    'timeline': {
                        'start': track.start_time,
                        'end': track.end_time,
                        'duration': track.duration
                    },
                    'transform': track.position,
                    'properties': {
                        'opacity': track.opacity,
                        'volume': track.volume
                    },
                    'effects': track.effects,
                    'transitions': track.transitions
                }
                project_data['tracks'].append(track_data)
            
            # 发送转换完成事件
            self.emit_event(Event(
                type=EventType.DRAFT_IMPORT_COMPLETE,
                data={'project_data': project_data}
            ))
            
            return project_data
            
        except Exception as e:
            self.logger.error(f"转换剪映草稿失败: {e}")
            self.emit_event(Event(
                type=EventType.DRAFT_IMPORT_ERROR,
                data={'error': str(e)}
            ))
            raise

    def validate_draft(self, draft: JianyingDraft) -> bool:
        """验证剪映草稿的有效性"""
        self.logger.info("验证剪映草稿有效性")
        
        # 检查必要字段
        if not draft.tracks:
            self.logger.warning("草稿中没有轨道数据")
            return False
        
        # 检查时间线一致性
        total_duration = 0
        for track in draft.tracks:
            if track.end_time <= track.start_time:
                self.logger.warning(f"轨道 {track.id} 时间线无效")
                return False
            total_duration = max(total_duration, track.end_time)
        
        # 检查分辨率
        if draft.resolution.get('width', 0) <= 0 or draft.resolution.get('height', 0) <= 0:
            self.logger.warning("草稿分辨率无效")
            return False
        
        # 检查帧率
        if draft.fps <= 0:
            self.logger.warning("草稿帧率无效")
            return False
        
        self.logger.info("剪映草稿验证通过")
        return True

    def get_draft_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """获取草稿文件基本信息"""
        try:
            draft = self.parse_draft(file_path)
            return {
                'version': draft.version,
                'duration': draft.duration,
                'resolution': draft.resolution,
                'fps': draft.fps,
                'track_count': len(draft.tracks),
                'created_at': draft.created_at.isoformat(),
                'modified_at': draft.modified_at.isoformat(),
                'is_valid': self.validate_draft(draft)
            }
        except Exception as e:
            return {
                'error': str(e),
                'is_valid': False
            }