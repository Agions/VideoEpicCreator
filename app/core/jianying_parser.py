#!/usr/bin/env python3
"""
剪映草稿解析器
用于解析剪映草稿文件并提取视频编辑信息
"""

import json
import xml.etree.ElementTree as ET
import zipfile
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import struct

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class JianyingTrack:
    """剪映轨道信息"""
    track_id: str
    track_type: str  # video, audio, text, etc.
    duration: float
    start_time: float
    clips: List[Dict[str, Any]]

@dataclass
class JianyingClip:
    """剪映片段信息"""
    clip_id: str
    source_file: str
    start_time: float
    end_time: float
    duration: float
    position: Dict[str, float]  # x, y, scale, rotation
    effects: List[Dict[str, Any]]
    transitions: List[Dict[str, Any]]

@dataclass
class JianyingProject:
    """剪映项目信息"""
    project_id: str
    name: str
    version: str
    fps: float
    resolution: Dict[str, int]  # width, height
    duration: float
    tracks: List[JianyingTrack]
    metadata: Dict[str, Any]

class JianyingDraftParser:
    """剪映草稿解析器"""
    
    def __init__(self):
        self.supported_formats = ['.draft', '.json', '.xml']
        self.project_data = None
        
    def parse_draft(self, file_path: str) -> Optional[JianyingProject]:
        """解析剪映草稿文件"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None
                
            file_ext = file_path.suffix.lower()
            
            if file_ext == '.draft':
                return self._parse_draft_file(file_path)
            elif file_ext == '.json':
                return self._parse_json_file(file_path)
            elif file_ext == '.xml':
                return self._parse_xml_file(file_path)
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                return None
                
        except Exception as e:
            logger.error(f"解析草稿文件时出错: {e}")
            return None
    
    def _parse_draft_file(self, file_path: Path) -> Optional[JianyingProject]:
        """解析.draft文件（剪映草稿格式）"""
        try:
            # 剪映草稿文件通常是zip格式
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # 解析项目信息文件
                project_info = self._extract_project_info(zip_file)
                if not project_info:
                    return None
                
                # 解析轨道信息
                tracks = self._extract_tracks(zip_file)
                
                # 解析片段信息
                clips = self._extract_clips(zip_file)
                
                # 构建项目对象
                project = JianyingProject(
                    project_id=project_info.get('project_id', ''),
                    name=project_info.get('name', ''),
                    version=project_info.get('version', '1.0'),
                    fps=project_info.get('fps', 30.0),
                    resolution=project_info.get('resolution', {'width': 1920, 'height': 1080}),
                    duration=project_info.get('duration', 0.0),
                    tracks=tracks,
                    metadata=project_info.get('metadata', {})
                )
                
                logger.info(f"成功解析剪映草稿: {project.name}")
                return project
                
        except Exception as e:
            logger.error(f"解析.draft文件时出错: {e}")
            return None
    
    def _parse_json_file(self, file_path: Path) -> Optional[JianyingProject]:
        """解析JSON格式的剪映草稿"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return self._parse_project_data(data)
            
        except Exception as e:
            logger.error(f"解析JSON文件时出错: {e}")
            return None
    
    def _parse_xml_file(self, file_path: Path) -> Optional[JianyingProject]:
        """解析XML格式的剪映草稿"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 转换XML为字典
            data = self._xml_to_dict(root)
            
            return self._parse_project_data(data)
            
        except Exception as e:
            logger.error(f"解析XML文件时出错: {e}")
            return None
    
    def _extract_project_info(self, zip_file: zipfile.ZipFile) -> Optional[Dict[str, Any]]:
        """从zip文件中提取项目信息"""
        try:
            # 查找项目信息文件
            info_files = [f for f in zip_file.namelist() if 'project' in f.lower()]
            
            if not info_files:
                logger.error("未找到项目信息文件")
                return None
            
            # 读取项目信息
            with zip_file.open(info_files[0]) as f:
                content = f.read().decode('utf-8')
                
                # 尝试解析JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试解析XML
                    try:
                        root = ET.fromstring(content)
                        return self._xml_to_dict(root)
                    except ET.ParseError:
                        logger.error("无法解析项目信息文件格式")
                        return None
                        
        except Exception as e:
            logger.error(f"提取项目信息时出错: {e}")
            return None
    
    def _extract_tracks(self, zip_file: zipfile.ZipFile) -> List[JianyingTrack]:
        """从zip文件中提取轨道信息"""
        tracks = []
        
        try:
            # 查找轨道文件
            track_files = [f for f in zip_file.namelist() if 'track' in f.lower()]
            
            for track_file in track_files:
                with zip_file.open(track_file) as f:
                    content = f.read().decode('utf-8')
                    
                    # 解析轨道数据
                    try:
                        track_data = json.loads(content)
                        track = JianyingTrack(
                            track_id=track_data.get('track_id', ''),
                            track_type=track_data.get('type', 'video'),
                            duration=track_data.get('duration', 0.0),
                            start_time=track_data.get('start_time', 0.0),
                            clips=track_data.get('clips', [])
                        )
                        tracks.append(track)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"提取轨道信息时出错: {e}")
        
        return tracks
    
    def _extract_clips(self, zip_file: zipfile.ZipFile) -> List[JianyingClip]:
        """从zip文件中提取片段信息"""
        clips = []
        
        try:
            # 查找片段文件
            clip_files = [f for f in zip_file.namelist() if 'clip' in f.lower()]
            
            for clip_file in clip_files:
                with zip_file.open(clip_file) as f:
                    content = f.read().decode('utf-8')
                    
                    # 解析片段数据
                    try:
                        clip_data = json.loads(content)
                        clip = JianyingClip(
                            clip_id=clip_data.get('clip_id', ''),
                            source_file=clip_data.get('source_file', ''),
                            start_time=clip_data.get('start_time', 0.0),
                            end_time=clip_data.get('end_time', 0.0),
                            duration=clip_data.get('duration', 0.0),
                            position=clip_data.get('position', {}),
                            effects=clip_data.get('effects', []),
                            transitions=clip_data.get('transitions', [])
                        )
                        clips.append(clip)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"提取片段信息时出错: {e}")
        
        return clips
    
    def _parse_project_data(self, data: Dict[str, Any]) -> Optional[JianyingProject]:
        """解析项目数据"""
        try:
            # 解析轨道信息
            tracks = []
            for track_data in data.get('tracks', []):
                track = JianyingTrack(
                    track_id=track_data.get('track_id', ''),
                    track_type=track_data.get('type', 'video'),
                    duration=track_data.get('duration', 0.0),
                    start_time=track_data.get('start_time', 0.0),
                    clips=track_data.get('clips', [])
                )
                tracks.append(track)
            
            # 构建项目对象
            project = JianyingProject(
                project_id=data.get('project_id', ''),
                name=data.get('name', ''),
                version=data.get('version', '1.0'),
                fps=data.get('fps', 30.0),
                resolution=data.get('resolution', {'width': 1920, 'height': 1080}),
                duration=data.get('duration', 0.0),
                tracks=tracks,
                metadata=data.get('metadata', {})
            )
            
            logger.info(f"成功解析项目: {project.name}")
            return project
            
        except Exception as e:
            logger.error(f"解析项目数据时出错: {e}")
            return None
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """将XML元素转换为字典"""
        result = {}
        
        # 添加元素属性
        if element.attrib:
            result.update(element.attrib)
        
        # 添加子元素
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # 如果已存在，转换为列表
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        # 添加文本内容
        if element.text and element.text.strip():
            if result:
                result['text'] = element.text.strip()
            else:
                result = element.text.strip()
        
        return result
    
    def get_project_summary(self, project: JianyingProject) -> Dict[str, Any]:
        """获取项目摘要信息"""
        return {
            'project_id': project.project_id,
            'name': project.name,
            'version': project.version,
            'duration': project.duration,
            'fps': project.fps,
            'resolution': project.resolution,
            'track_count': len(project.tracks),
            'video_tracks': len([t for t in project.tracks if t.track_type == 'video']),
            'audio_tracks': len([t for t in project.tracks if t.track_type == 'audio']),
            'text_tracks': len([t for t in project.tracks if t.track_type == 'text']),
            'total_clips': sum(len(t.clips) for t in project.tracks)
        }
    
    def validate_project(self, project: JianyingProject) -> List[str]:
        """验证项目数据完整性"""
        errors = []
        
        if not project.project_id:
            errors.append("项目ID缺失")
        
        if not project.name:
            errors.append("项目名称缺失")
        
        if project.duration <= 0:
            errors.append("项目时长无效")
        
        if project.fps <= 0:
            errors.append("帧率无效")
        
        if not project.tracks:
            errors.append("没有轨道信息")
        
        # 验证轨道数据
        for i, track in enumerate(project.tracks):
            if not track.track_id:
                errors.append(f"轨道 {i+1} 缺少ID")
            
            if track.duration <= 0:
                errors.append(f"轨道 {i+1} 时长无效")
        
        return errors

def main():
    """主函数"""
    # 创建解析器实例
    parser = JianyingDraftParser()
    
    # 测试解析
    test_file = "/Users/zfkc/Desktop/VideoEpicCreator/test_data/sample_draft.draft"
    
    if os.path.exists(test_file):
        project = parser.parse_draft(test_file)
        
        if project:
            print(f"项目名称: {project.name}")
            print(f"项目ID: {project.project_id}")
            print(f"时长: {project.duration}秒")
            print(f"分辨率: {project.resolution['width']}x{project.resolution['height']}")
            print(f"帧率: {project.fps}")
            print(f"轨道数量: {len(project.tracks)}")
            
            # 显示项目摘要
            summary = parser.get_project_summary(project)
            print(f"\n项目摘要: {summary}")
            
            # 验证项目
            errors = parser.validate_project(project)
            if errors:
                print(f"\n验证错误: {errors}")
            else:
                print("\n项目验证通过")
        else:
            print("解析失败")
    else:
        print(f"测试文件不存在: {test_file}")

if __name__ == "__main__":
    main()