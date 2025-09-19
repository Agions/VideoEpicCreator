#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映素材组织器
负责组织和管理项目中的媒体文件
"""

import os
import json
import shutil
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from .jianying_project_parser import JianYingProject, JianYingTrack, JianYingClip


@dataclass
class MediaFile:
    """媒体文件信息"""
    id: str
    original_path: str
    relative_path: str
    file_name: str
    file_size: int
    file_type: str
    duration: float = 0
    resolution: Tuple[int, int] = (0, 0)
    frame_rate: float = 0
    audio_channels: int = 0
    checksum: str = ""
    created_at: str = ""
    modified_at: str = ""


class JianYingMediaOrganizer:
    """剪映素材组织器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 支持的媒体格式
        self.supported_formats = {
            'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.webm'],
            'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'],
            'text': ['.txt', '.srt', '.ass', '.lrc', '.vtt']
        }
        
        # 文件组织结构
        self.directory_structure = {
            'video': 'media/videos',
            'audio': 'media/audio',
            'image': 'media/images',
            'text': 'media/texts',
            'effects': 'media/effects',
            'thumbnails': 'media/thumbnails',
            'proxies': 'media/proxies'
        }
        
        # 媒体文件数据库
        self.media_database = {}
    
    def organize_media_files(self, project: JianYingProject, output_dir: str) -> List[str]:
        """
        组织项目媒体文件
        
        Args:
            project: 剪映项目对象
            output_dir: 输出目录
            
        Returns:
            List[str]: 组织后的媒体文件路径列表
        """
        try:
            self.logger.info("开始组织媒体文件")
            
            organized_files = []
            media_info = {}
            
            # 创建媒体目录结构
            self._create_directory_structure(output_dir)
            
            # 收集所有媒体文件
            media_files = self._collect_media_files(project)
            
            # 复制和组织文件
            for media_file in media_files:
                try:
                    # 复制文件
                    dest_path = self._copy_media_file(media_file, output_dir)
                    
                    if dest_path:
                        organized_files.append(dest_path)
                        
                        # 生成缩略图
                        thumbnail_path = self._generate_thumbnail(media_file, output_dir)
                        
                        # 记录媒体信息
                        media_info[media_file.id] = {
                            'original_path': media_file.original_path,
                            'relative_path': self._get_relative_path(dest_path, output_dir),
                            'file_name': media_file.file_name,
                            'file_size': media_file.file_size,
                            'file_type': media_file.file_type,
                            'duration': media_file.duration,
                            'resolution': media_file.resolution,
                            'frame_rate': media_file.frame_rate,
                            'audio_channels': media_file.audio_channels,
                            'checksum': media_file.checksum,
                            'thumbnail_path': self._get_relative_path(thumbnail_path, output_dir) if thumbnail_path else None,
                            'created_at': media_file.created_at,
                            'modified_at': media_file.modified_at
                        }
                        
                except Exception as e:
                    self.logger.error(f"组织媒体文件失败: {media_file.original_path}, 错误: {e}")
            
            # 保存媒体信息数据库
            self._save_media_database(media_info, output_dir)
            
            # 生成媒体索引文件
            self._generate_media_index(media_info, output_dir)
            
            self.logger.info(f"媒体文件组织完成，共 {len(organized_files)} 个文件")
            return organized_files
            
        except Exception as e:
            self.logger.error(f"组织媒体文件失败: {e}")
            return []
    
    def _collect_media_files(self, project: JianYingProject) -> List[MediaFile]:
        """收集项目中的所有媒体文件"""
        media_files = []
        processed_paths = set()
        
        for track in project.tracks:
            for clip in track.clips:
                source_path = clip.source_path
                
                # 跳过已处理的文件
                if source_path in processed_paths:
                    continue
                
                if os.path.exists(source_path):
                    try:
                        media_file = self._create_media_file(source_path, clip.type)
                        if media_file:
                            media_files.append(media_file)
                            processed_paths.add(source_path)
                    except Exception as e:
                        self.logger.error(f"创建媒体文件对象失败: {source_path}, 错误: {e}")
                else:
                    self.logger.warning(f"媒体文件不存在: {source_path}")
        
        return media_files
    
    def _create_media_file(self, file_path: str, file_type: str) -> Optional[MediaFile]:
        """创建媒体文件对象"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            # 获取文件信息
            stat = path.stat()
            file_size = stat.st_size
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # 计算文件校验和
            checksum = self._calculate_checksum(file_path)
            
            # 获取媒体属性
            media_props = self._get_media_properties(file_path, file_type)
            
            media_file = MediaFile(
                id=self._generate_file_id(file_path),
                original_path=file_path,
                relative_path="",
                file_name=path.name,
                file_size=file_size,
                file_type=file_type,
                duration=media_props.get('duration', 0),
                resolution=media_props.get('resolution', (0, 0)),
                frame_rate=media_props.get('frame_rate', 0),
                audio_channels=media_props.get('audio_channels', 0),
                checksum=checksum,
                created_at=created_at,
                modified_at=modified_at
            )
            
            return media_file
            
        except Exception as e:
            self.logger.error(f"创建媒体文件对象失败: {file_path}, 错误: {e}")
            return None
    
    def _get_media_properties(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """获取媒体文件属性"""
        properties = {
            'duration': 0,
            'resolution': (0, 0),
            'frame_rate': 0,
            'audio_channels': 0
        }
        
        try:
            if file_type in ['video', 'audio']:
                # 这里可以使用 ffmpeg 或其他库获取媒体属性
                # 暂时返回默认值
                properties.update({
                    'duration': 0,
                    'resolution': (1920, 1080) if file_type == 'video' else (0, 0),
                    'frame_rate': 30.0 if file_type == 'video' else 0,
                    'audio_channels': 2 if file_type == 'audio' else 0
                })
            
        except Exception as e:
            self.logger.error(f"获取媒体属性失败: {file_path}, 错误: {e}")
        
        return properties
    
    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"计算校验和失败: {file_path}, 错误: {e}")
            return ""
    
    def _generate_file_id(self, file_path: str) -> str:
        """生成文件ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _create_directory_structure(self, output_dir: str):
        """创建目录结构"""
        try:
            base_dir = Path(output_dir)
            
            # 创建基础目录
            for dir_name, dir_path in self.directory_structure.items():
                full_path = base_dir / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                
                # 创建子目录
                if dir_name in ['video', 'audio', 'image']:
                    # 按日期组织
                    date_dir = full_path / datetime.now().strftime('%Y-%m-%d')
                    date_dir.mkdir(exist_ok=True)
        
        except Exception as e:
            self.logger.error(f"创建目录结构失败: {e}")
            raise
    
    def _copy_media_file(self, media_file: MediaFile, output_dir: str) -> Optional[str]:
        """复制媒体文件"""
        try:
            # 确定目标目录
            if media_file.file_type == 'video':
                target_dir = Path(output_dir) / self.directory_structure['video']
            elif media_file.file_type == 'audio':
                target_dir = Path(output_dir) / self.directory_structure['audio']
            elif media_file.file_type == 'image':
                target_dir = Path(output_dir) / self.directory_structure['image']
            elif media_file.file_type == 'text':
                target_dir = Path(output_dir) / self.directory_structure['text']
            else:
                target_dir = Path(output_dir) / 'media'
            
            # 按日期组织
            date_dir = target_dir / datetime.now().strftime('%Y-%m-%d')
            date_dir.mkdir(exist_ok=True)
            
            # 生成目标文件名
            target_name = self._generate_target_filename(media_file)
            target_path = date_dir / target_name
            
            # 复制文件
            shutil.copy2(media_file.original_path, target_path)
            
            self.logger.info(f"媒体文件复制成功: {media_file.original_path} -> {target_path}")
            return str(target_path)
            
        except Exception as e:
            self.logger.error(f"复制媒体文件失败: {media_file.original_path}, 错误: {e}")
            return None
    
    def _generate_target_filename(self, media_file: MediaFile) -> str:
        """生成目标文件名"""
        import re
        
        # 清理文件名
        clean_name = re.sub(r'[^\w\s-]', '', media_file.file_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name)
        
        # 添加时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成新文件名
        name_part = clean_name.rsplit('.', 1)[0]
        ext_part = clean_name.rsplit('.', 1)[1] if '.' in clean_name else ''
        
        new_filename = f"{name_part}_{timestamp}.{ext_part}"
        
        return new_filename
    
    def _generate_thumbnail(self, media_file: MediaFile, output_dir: str) -> Optional[str]:
        """生成缩略图"""
        try:
            if media_file.file_type not in ['video', 'image']:
                return None
            
            thumbnail_dir = Path(output_dir) / self.directory_structure['thumbnails']
            thumbnail_dir.mkdir(exist_ok=True)
            
            # 生成缩略图文件名
            thumbnail_name = f"{media_file.id}_thumbnail.jpg"
            thumbnail_path = thumbnail_dir / thumbnail_name
            
            # 这里可以使用 ffmpeg 或 PIL 生成缩略图
            # 暂时创建一个空文件
            with open(thumbnail_path, 'wb') as f:
                f.write(b'')
            
            return str(thumbnail_path)
            
        except Exception as e:
            self.logger.error(f"生成缩略图失败: {media_file.original_path}, 错误: {e}")
            return None
    
    def _get_relative_path(self, file_path: str, base_dir: str) -> str:
        """获取相对路径"""
        try:
            return os.path.relpath(file_path, base_dir)
        except Exception:
            return file_path
    
    def _save_media_database(self, media_info: Dict[str, Any], output_dir: str):
        """保存媒体数据库"""
        try:
            db_file = Path(output_dir) / 'media_database.json'
            
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(media_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"媒体数据库保存成功: {db_file}")
            
        except Exception as e:
            self.logger.error(f"保存媒体数据库失败: {e}")
    
    def _generate_media_index(self, media_info: Dict[str, Any], output_dir: str):
        """生成媒体索引文件"""
        try:
            index_file = Path(output_dir) / 'media_index.json'
            
            # 生成索引数据
            index_data = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'total_files': len(media_info),
                'total_size': sum(info['file_size'] for info in media_info.values()),
                'files_by_type': {},
                'files': media_info
            }
            
            # 按类型统计
            for info in media_info.values():
                file_type = info['file_type']
                if file_type not in index_data['files_by_type']:
                    index_data['files_by_type'][file_type] = 0
                index_data['files_by_type'][file_type] += 1
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"媒体索引文件生成成功: {index_file}")
            
        except Exception as e:
            self.logger.error(f"生成媒体索引文件失败: {e}")
    
    def validate_media_files(self, output_dir: str) -> Dict[str, Any]:
        """验证媒体文件"""
        validation_result = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'missing_files': 0,
            'corrupted_files': 0,
            'issues': []
        }
        
        try:
            # 加载媒体数据库
            db_file = Path(output_dir) / 'media_database.json'
            if not db_file.exists():
                validation_result['issues'].append('媒体数据库文件不存在')
                return validation_result
            
            with open(db_file, 'r', encoding='utf-8') as f:
                media_info = json.load(f)
            
            validation_result['total_files'] = len(media_info)
            
            # 验证每个文件
            for file_id, info in media_info.items():
                file_path = Path(output_dir) / info['relative_path']
                
                if not file_path.exists():
                    validation_result['missing_files'] += 1
                    validation_result['issues'].append(f'文件缺失: {info["file_name"]}')
                    continue
                
                # 检查文件大小
                current_size = file_path.stat().st_size
                if current_size != info['file_size']:
                    validation_result['corrupted_files'] += 1
                    validation_result['issues'].append(f'文件大小不匹配: {info["file_name"]}')
                    continue
                
                # 检查校验和
                current_checksum = self._calculate_checksum(str(file_path))
                if current_checksum != info['checksum']:
                    validation_result['corrupted_files'] += 1
                    validation_result['issues'].append(f'文件校验和不匹配: {info["file_name"]}')
                    continue
                
                validation_result['valid_files'] += 1
            
            validation_result['invalid_files'] = validation_result['total_files'] - validation_result['valid_files']
            
        except Exception as e:
            validation_result['issues'].append(f'验证过程出错: {e}')
        
        return validation_result
    
    def cleanup_unused_files(self, output_dir: str, used_files: List[str]):
        """清理未使用的文件"""
        try:
            media_dir = Path(output_dir) / 'media'
            if not media_dir.exists():
                return
            
            # 收集所有媒体文件
            all_files = []
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    all_files.append(os.path.join(root, file))
            
            # 找出未使用的文件
            used_files_set = set(used_files)
            unused_files = [f for f in all_files if f not in used_files_set]
            
            # 删除未使用的文件
            for unused_file in unused_files:
                try:
                    os.remove(unused_file)
                    self.logger.info(f"删除未使用文件: {unused_file}")
                except Exception as e:
                    self.logger.error(f"删除文件失败: {unused_file}, 错误: {e}")
            
            # 清理空目录
            self._cleanup_empty_dirs(media_dir)
            
            self.logger.info(f"清理完成，删除 {len(unused_files)} 个未使用文件")
            
        except Exception as e:
            self.logger.error(f"清理未使用文件失败: {e}")
    
    def _cleanup_empty_dirs(self, directory: Path):
        """清理空目录"""
        try:
            for root, dirs, files in os.walk(directory, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if dir_path.exists() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            self.logger.info(f"删除空目录: {dir_path}")
                    except Exception as e:
                        self.logger.error(f"删除目录失败: {dir_path}, 错误: {e}")
        except Exception as e:
            self.logger.error(f"清理空目录失败: {e}")
    
    def get_media_statistics(self, output_dir: str) -> Dict[str, Any]:
        """获取媒体统计信息"""
        try:
            # 加载媒体索引
            index_file = Path(output_dir) / 'media_index.json'
            if not index_file.exists():
                return {}
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            return index_data
            
        except Exception as e:
            self.logger.error(f"获取媒体统计信息失败: {e}")
            return {}