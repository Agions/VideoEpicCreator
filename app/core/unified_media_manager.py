#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一媒体管理系统 - CineAIStudio的核心媒体管理组件
统一管理视频、音频、图片等媒体文件的导入、组织、索引和访问
"""

import os
import sys
import json
import time
import logging
import threading
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import sqlite3
import shutil

from ..utils.thumbnail_generator import ThumbnailGenerator
from ..core.video_processing_engine import VideoInfo, VideoProcessingEngine
from .intelligent_video_processing_engine import AISceneAnalysis, AIEditDecision

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """媒体类型"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    SEQUENCE = "sequence"
    PROJECT = "project"
    FOLDER = "folder"


class MediaStatus(Enum):
    """媒体状态"""
    AVAILABLE = "available"
    PROCESSING = "processing"
    ARCHIVED = "archived"
    DELETED = "deleted"
    CORRUPTED = "corrupted"


class StorageLocation(Enum):
    """存储位置"""
    LOCAL = "local"
    EXTERNAL = "external"
    CLOUD = "cloud"
    ARCHIVE = "archive"


@dataclass
class MediaMetadata:
    """媒体元数据"""
    duration: Optional[float] = None  # 秒
    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    audio_codec: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    file_hash: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    rating: Optional[int] = None  # 1-5星评分
    description: str = ""
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaItem:
    """媒体项"""
    id: str
    name: str
    path: str
    type: MediaType
    status: MediaStatus = MediaStatus.AVAILABLE
    storage_location: StorageLocation = StorageLocation.LOCAL
    thumbnail_path: Optional[str] = None
    preview_path: Optional[str] = None
    metadata: MediaMetadata = field(default_factory=MediaMetadata)

    # AI分析数据
    scene_analysis: List[AISceneAnalysis] = field(default_factory=list)
    edit_decisions: List[AIEditDecision] = field(default_factory=list)
    ai_tags: List[str] = field(default_factory=list)

    # 组织信息
    collection_id: Optional[str] = None
    folder_id: Optional[str] = None

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'type': self.type.value,
            'status': self.status.value,
            'storage_location': self.storage_location.value,
            'thumbnail_path': self.thumbnail_path,
            'preview_path': self.preview_path,
            'metadata': {
                'duration': self.metadata.duration,
                'width': self.metadata.width,
                'height': self.metadata.height,
                'frame_rate': self.metadata.frame_rate,
                'bitrate': self.metadata.bitrate,
                'codec': self.metadata.codec,
                'audio_codec': self.metadata.audio_codec,
                'sample_rate': self.metadata.sample_rate,
                'channels': self.metadata.channels,
                'size_bytes': self.metadata.size_bytes,
                'created_at': self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                'modified_at': self.metadata.modified_at.isoformat() if self.metadata.modified_at else None,
                'accessed_at': self.metadata.accessed_at.isoformat() if self.metadata.accessed_at else None,
                'file_hash': self.metadata.file_hash,
                'tags': self.metadata.tags,
                'rating': self.metadata.rating,
                'description': self.metadata.description,
                'custom_fields': self.metadata.custom_fields
            },
            'scene_analysis': [scene.__dict__ for scene in self.scene_analysis],
            'edit_decisions': [decision.__dict__ for decision in self.edit_decisions],
            'ai_tags': self.ai_tags,
            'collection_id': self.collection_id,
            'folder_id': self.folder_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'accessed_at': self.accessed_at.isoformat() if self.accessed_at else None
        }


@dataclass
class MediaCollection:
    """媒体集合"""
    id: str
    name: str
    description: str = ""
    parent_id: Optional[str] = None
    items: List[str] = field(default_factory=list)  # MediaItem IDs
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MediaFolder:
    """媒体文件夹"""
    id: str
    name: str
    path: str
    parent_id: Optional[str] = None
    storage_location: StorageLocation = StorageLocation.LOCAL
    auto_scan: bool = True
    items: List[str] = field(default_factory=list)  # MediaItem IDs
    subfolders: List[str] = field(default_factory=list)  # MediaFolder IDs
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class UnifiedMediaManager:
    """统一媒体管理系统"""

    def __init__(self, db_path: str = None, cache_dir: str = None):
        self.db_path = db_path or os.path.join(os.path.expanduser("~"), ".cineai_studio", "media.db")
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".cineai_studio", "media_cache")

        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        # 初始化组件
        self.thumbnail_generator = ThumbnailGenerator(os.path.join(self.cache_dir, "thumbnails"))
        self.video_engine = VideoProcessingEngine()

        # 线程锁
        self.db_lock = threading.Lock()
        self.scan_lock = threading.Lock()

        # 回调函数
        self.media_added_callback: Optional[Callable] = None
        self.media_updated_callback: Optional[Callable] = None
        self.media_removed_callback: Optional[Callable] = None

        # 初始化数据库
        self._init_database()

        logger.info("统一媒体管理系统初始化完成")

    def _init_database(self):
        """初始化数据库"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建媒体项表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    storage_location TEXT NOT NULL,
                    thumbnail_path TEXT,
                    preview_path TEXT,
                    metadata TEXT,
                    scene_analysis TEXT,
                    edit_decisions TEXT,
                    ai_tags TEXT,
                    collection_id TEXT,
                    folder_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    accessed_at TEXT
                )
            ''')

            # 创建媒体集合表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_id TEXT,
                    items TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 创建媒体文件夹表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    parent_id TEXT,
                    storage_location TEXT NOT NULL,
                    auto_scan INTEGER DEFAULT 1,
                    items TEXT,
                    subfolders TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_items_status ON media_items(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_items_collection ON media_items(collection_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_items_folder ON media_items(folder_id)')

            conn.commit()
            conn.close()

    def import_media_file(self, file_path: str, copy_to_library: bool = False) -> Optional[MediaItem]:
        """导入媒体文件"""
        try:
            file_path = os.path.abspath(file_path)

            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None

            # 检查是否已存在
            existing_item = self.get_media_item_by_path(file_path)
            if existing_item:
                logger.info(f"媒体文件已存在: {file_path}")
                return existing_item

            # 获取文件基本信息
            file_stat = os.stat(file_path)
            media_type = self._detect_media_type(file_path)

            # 生成ID
            media_id = hashlib.md5(file_path.encode()).hexdigest()

            # 复制到媒体库（如果需要）
            if copy_to_library:
                library_path = self._get_library_path(file_path, media_type)
                if library_path:
                    shutil.copy2(file_path, library_path)
                    file_path = library_path

            # 生成缩略图
            thumbnail_path = self._generate_thumbnail(file_path, media_type)

            # 提取元数据
            metadata = self._extract_metadata(file_path, media_type)

            # 创建媒体项
            media_item = MediaItem(
                id=media_id,
                name=os.path.basename(file_path),
                path=file_path,
                type=media_type,
                thumbnail_path=thumbnail_path,
                metadata=metadata
            )

            # 保存到数据库
            self._save_media_item(media_item)

            # 调用回调
            if self.media_added_callback:
                self.media_added_callback(media_item)

            logger.info(f"媒体文件导入成功: {file_path}")
            return media_item

        except Exception as e:
            logger.error(f"导入媒体文件失败: {file_path}, 错误: {e}")
            return None

    def import_media_batch(self, file_paths: List[str], copy_to_library: bool = False) -> List[MediaItem]:
        """批量导入媒体文件"""
        imported_items = []

        for file_path in file_paths:
            media_item = self.import_media_file(file_path, copy_to_library)
            if media_item:
                imported_items.append(media_item)

        logger.info(f"批量导入完成: {len(imported_items)}/{len(file_paths)} 个文件")
        return imported_items

    def get_media_item(self, item_id: str) -> Optional[MediaItem]:
        """获取媒体项"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM media_items WHERE id = ?', (item_id,))
                row = cursor.fetchone()

                conn.close()

                if row:
                    return self._row_to_media_item(row)
                return None

        except Exception as e:
            logger.error(f"获取媒体项失败: {item_id}, 错误: {e}")
            return None

    def get_media_item_by_path(self, file_path: str) -> Optional[MediaItem]:
        """根据路径获取媒体项"""
        try:
            file_path = os.path.abspath(file_path)

            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM media_items WHERE path = ?', (file_path,))
                row = cursor.fetchone()

                conn.close()

                if row:
                    return self._row_to_media_item(row)
                return None

        except Exception as e:
            logger.error(f"根据路径获取媒体项失败: {file_path}, 错误: {e}")
            return None

    def search_media_items(self, query: str = "", media_type: Optional[MediaType] = None,
                        tags: List[str] = None, collection_id: Optional[str] = None,
                        folder_id: Optional[str] = None, limit: int = 100) -> List[MediaItem]:
        """搜索媒体项"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if query:
                    conditions.append("(name LIKE ? OR path LIKE ? OR ai_tags LIKE ?)")
                    params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

                if media_type:
                    conditions.append("type = ?")
                    params.append(media_type.value)

                if tags:
                    for tag in tags:
                        conditions.append("ai_tags LIKE ?")
                        params.append(f"%{tag}%")

                if collection_id:
                    conditions.append("collection_id = ?")
                    params.append(collection_id)

                if folder_id:
                    conditions.append("folder_id = ?")
                    params.append(folder_id)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                sql = f"SELECT * FROM media_items WHERE {where_clause} ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                conn.close()

                return [self._row_to_media_item(row) for row in rows]

        except Exception as e:
            logger.error(f"搜索媒体项失败: {e}")
            return []

    def get_all_media_items(self, media_type: Optional[MediaType] = None) -> List[MediaItem]:
        """获取所有媒体项"""
        return self.search_media_items(media_type=media_type, limit=10000)

    def update_media_item(self, media_item: MediaItem) -> bool:
        """更新媒体项"""
        try:
            media_item.updated_at = datetime.now()

            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE media_items SET
                        name = ?, path = ?, type = ?, status = ?, storage_location = ?,
                        thumbnail_path = ?, preview_path = ?, metadata = ?, scene_analysis = ?,
                        edit_decisions = ?, ai_tags = ?, collection_id = ?, folder_id = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    media_item.name, media_item.path, media_item.type.value, media_item.status.value,
                    media_item.storage_location.value, media_item.thumbnail_path, media_item.preview_path,
                    json.dumps(media_item.metadata.__dict__), json.dumps([scene.__dict__ for scene in media_item.scene_analysis]),
                    json.dumps([decision.__dict__ for decision in media_item.edit_decisions]), json.dumps(media_item.ai_tags),
                    media_item.collection_id, media_item.folder_id, media_item.updated_at.isoformat(), media_item.id
                ))

                conn.commit()
                conn.close()

            # 调用回调
            if self.media_updated_callback:
                self.media_updated_callback(media_item)

            logger.info(f"媒体项更新成功: {media_item.id}")
            return True

        except Exception as e:
            logger.error(f"更新媒体项失败: {media_item.id}, 错误: {e}")
            return False

    def remove_media_item(self, item_id: str, delete_file: bool = False) -> bool:
        """删除媒体项"""
        try:
            media_item = self.get_media_item(item_id)
            if not media_item:
                logger.warning(f"媒体项不存在: {item_id}")
                return False

            # 删除文件（如果需要）
            if delete_file and os.path.exists(media_item.path):
                try:
                    os.remove(media_item.path)
                except Exception as e:
                    logger.warning(f"删除文件失败: {media_item.path}, 错误: {e}")

            # 删除缩略图
            if media_item.thumbnail_path and os.path.exists(media_item.thumbnail_path):
                try:
                    os.remove(media_item.thumbnail_path)
                except Exception as e:
                    logger.warning(f"删除缩略图失败: {media_item.thumbnail_path}, 错误: {e}")

            # 从数据库删除
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('DELETE FROM media_items WHERE id = ?', (item_id,))
                conn.commit()
                conn.close()

            # 调用回调
            if self.media_removed_callback:
                self.media_removed_callback(media_item)

            logger.info(f"媒体项删除成功: {item_id}")
            return True

        except Exception as e:
            logger.error(f"删除媒体项失败: {item_id}, 错误: {e}")
            return False

    def create_collection(self, name: str, description: str = "", parent_id: Optional[str] = None) -> MediaCollection:
        """创建媒体集合"""
        try:
            import uuid
            collection_id = str(uuid.uuid4())

            collection = MediaCollection(
                id=collection_id,
                name=name,
                description=description,
                parent_id=parent_id
            )

            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO media_collections (id, name, description, parent_id, items, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    collection.id, collection.name, collection.description, collection.parent_id,
                    json.dumps(collection.items), json.dumps(collection.tags),
                    collection.created_at.isoformat(), collection.updated_at.isoformat()
                ))

                conn.commit()
                conn.close()

            logger.info(f"媒体集合创建成功: {collection.id}")
            return collection

        except Exception as e:
            logger.error(f"创建媒体集合失败: {e}")
            raise

    def get_collections(self, parent_id: Optional[str] = None) -> List[MediaCollection]:
        """获取媒体集合"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                if parent_id:
                    cursor.execute('SELECT * FROM media_collections WHERE parent_id = ? ORDER BY name', (parent_id,))
                else:
                    cursor.execute('SELECT * FROM media_collections ORDER BY name')

                rows = cursor.fetchall()
                conn.close()

                return [self._row_to_collection(row) for row in rows]

        except Exception as e:
            logger.error(f"获取媒体集合失败: {e}")
            return []

    def add_to_collection(self, item_id: str, collection_id: str) -> bool:
        """添加媒体项到集合"""
        try:
            collection = self.get_collection(collection_id)
            if not collection:
                logger.error(f"集合不存在: {collection_id}")
                return False

            if item_id not in collection.items:
                collection.items.append(item_id)
                collection.updated_at = datetime.now()

                self._save_collection(collection)

                # 更新媒体项的集合ID
                media_item = self.get_media_item(item_id)
                if media_item:
                    media_item.collection_id = collection_id
                    self.update_media_item(media_item)

                logger.info(f"媒体项已添加到集合: {item_id} -> {collection_id}")
                return True

            return True

        except Exception as e:
            logger.error(f"添加到集合失败: {e}")
            return False

    def scan_directory(self, directory_path: str, recursive: bool = True,
                      file_extensions: List[str] = None) -> List[MediaItem]:
        """扫描目录导入媒体文件"""
        try:
            directory_path = os.path.abspath(directory_path)

            if not os.path.exists(directory_path):
                logger.error(f"目录不存在: {directory_path}")
                return []

            with self.scan_lock:
                imported_items = []

                # 支持的文件扩展名
                if not file_extensions:
                    file_extensions = [
                        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm',  # 视频
                        '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a',       # 音频
                        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif',     # 图片
                        '.pdf', '.doc', '.docx', '.txt'                    # 文档
                    ]

                # 递归扫描
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        file_path = os.path.join(root, file)

                        # 检查文件扩展名
                        if any(file.lower().endswith(ext) for ext in file_extensions):
                            media_item = self.import_media_file(file_path)
                            if media_item:
                                imported_items.append(media_item)

                    # 如果不递归，只扫描当前目录
                    if not recursive:
                        break

                logger.info(f"目录扫描完成: {directory_path}, 导入 {len(imported_items)} 个文件")
                return imported_items

        except Exception as e:
            logger.error(f"扫描目录失败: {directory_path}, 错误: {e}")
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 总文件数
                cursor.execute('SELECT COUNT(*) FROM media_items WHERE status = ?', (MediaStatus.AVAILABLE.value,))
                total_files = cursor.fetchone()[0]

                # 按类型统计
                type_stats = {}
                for media_type in MediaType:
                    cursor.execute('SELECT COUNT(*) FROM media_items WHERE type = ? AND status = ?',
                                 (media_type.value, MediaStatus.AVAILABLE.value))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        type_stats[media_type.value] = count

                # 总大小
                cursor.execute('SELECT SUM(metadata->>"$.size_bytes") FROM media_items WHERE status = ?',
                             (MediaStatus.AVAILABLE.value,))
                total_size = cursor.fetchone()[0] or 0

                # 集合数量
                cursor.execute('SELECT COUNT(*) FROM media_collections')
                collection_count = cursor.fetchone()[0]

                conn.close()

                return {
                    'total_files': total_files,
                    'total_size_bytes': total_size,
                    'total_size_gb': total_size / (1024**3),
                    'by_type': type_stats,
                    'collection_count': collection_count,
                    'cache_size': self._get_cache_size()
                }

        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}

    def cleanup_cache(self, max_age_days: int = 30) -> bool:
        """清理缓存文件"""
        try:
            import time
            cutoff_time = time.time() - (max_age_days * 24 * 3600)

            cleaned_count = 0

            # 清理缩略图缓存
            thumbnail_dir = os.path.join(self.cache_dir, "thumbnails")
            if os.path.exists(thumbnail_dir):
                for filename in os.listdir(thumbnail_dir):
                    file_path = os.path.join(thumbnail_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"清理缓存文件失败: {file_path}, 错误: {e}")

            logger.info(f"缓存清理完成: 删除 {cleaned_count} 个文件")
            return True

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return False

    def set_callbacks(self, media_added: Optional[Callable] = None,
                    media_updated: Optional[Callable] = None,
                    media_removed: Optional[Callable] = None):
        """设置回调函数"""
        self.media_added_callback = media_added
        self.media_updated_callback = media_updated
        self.media_removed_callback = media_removed

    # 私有方法
    def _detect_media_type(self, file_path: str) -> MediaType:
        """检测媒体类型"""
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type:
            if mime_type.startswith('video/'):
                return MediaType.VIDEO
            elif mime_type.startswith('audio/'):
                return MediaType.AUDIO
            elif mime_type.startswith('image/'):
                return MediaType.IMAGE
            elif mime_type == 'application/pdf':
                return MediaType.DOCUMENT

        # 基于扩展名检测
        ext = os.path.splitext(file_path)[1].lower()
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        audio_exts = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        doc_exts = ['.pdf', '.doc', '.docx', '.txt']

        if ext in video_exts:
            return MediaType.VIDEO
        elif ext in audio_exts:
            return MediaType.AUDIO
        elif ext in image_exts:
            return MediaType.IMAGE
        elif ext in doc_exts:
            return MediaType.DOCUMENT

        return MediaType.DOCUMENT

    def _generate_thumbnail(self, file_path: str, media_type: MediaType) -> Optional[str]:
        """生成缩略图"""
        try:
            if media_type == MediaType.VIDEO:
                # 使用视频缩略图生成器
                thumbnail_path = self.thumbnail_generator.generate_thumbnail(file_path)
                return thumbnail_path
            elif media_type == MediaType.IMAGE:
                # 直接使用图片作为缩略图
                return file_path
            else:
                # 其他类型使用默认图标
                return None

        except Exception as e:
            logger.error(f"生成缩略图失败: {file_path}, 错误: {e}")
            return None

    def _extract_metadata(self, file_path: str, media_type: MediaType) -> MediaMetadata:
        """提取元数据"""
        metadata = MediaMetadata()

        try:
            file_stat = os.stat(file_path)
            metadata.size_bytes = file_stat.st_size
            metadata.created_at = datetime.fromtimestamp(file_stat.st_ctime)
            metadata.modified_at = datetime.fromtimestamp(file_stat.st_mtime)
            metadata.accessed_at = datetime.fromtimestamp(file_stat.st_atime)

            # 计算文件哈希
            metadata.file_hash = self._calculate_file_hash(file_path)

            # 根据媒体类型提取特定元数据
            if media_type == MediaType.VIDEO:
                video_info = self.video_engine.get_video_info(file_path)
                if video_info:
                    metadata.duration = video_info.duration
                    metadata.width = video_info.width
                    metadata.height = video_info.height
                    metadata.frame_rate = video_info.fps
                    metadata.bitrate = video_info.bitrate
                    metadata.codec = video_info.video_codec
                    metadata.audio_codec = video_info.audio_codec
                    metadata.sample_rate = video_info.audio_sample_rate
                    metadata.channels = video_info.audio_channels

            elif media_type == MediaType.IMAGE:
                # 提取图片元数据
                try:
                    from PIL import Image, ExifTags
                    with Image.open(file_path) as img:
                        metadata.width, metadata.height = img.size

                        # 提取EXIF数据
                        if hasattr(img, '_getexif'):
                            exif_data = img._getexif()
                            if exif_data:
                                for tag_id, value in exif_data.items():
                                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                                    metadata.custom_fields[tag] = str(value)
                except Exception as e:
                    logger.warning(f"提取图片元数据失败: {file_path}, 错误: {e}")

            elif media_type == MediaType.AUDIO:
                # 提取音频元数据
                try:
                    import mutagen
                    audio_file = mutagen.File(file_path)
                    if audio_file:
                        metadata.duration = audio_file.info.length
                        metadata.sample_rate = audio_file.info.sample_rate
                        metadata.channels = getattr(audio_file.info, 'channels', 2)
                        metadata.bitrate = getattr(audio_file.info, 'bitrate', 0)
                except Exception as e:
                    logger.warning(f"提取音频元数据失败: {file_path}, 错误: {e}")

        except Exception as e:
            logger.error(f"提取元数据失败: {file_path}, 错误: {e}")

        return metadata

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {file_path}, 错误: {e}")
            return ""

    def _get_library_path(self, file_path: str, media_type: MediaType) -> Optional[str]:
        """获取媒体库路径"""
        try:
            library_root = os.path.join(self.cache_dir, "library", media_type.value)
            os.makedirs(library_root, exist_ok=True)

            filename = os.path.basename(file_path)
            library_path = os.path.join(library_root, filename)

            # 避免文件名冲突
            counter = 1
            while os.path.exists(library_path):
                name, ext = os.path.splitext(filename)
                library_path = os.path.join(library_root, f"{name}_{counter}{ext}")
                counter += 1

            return library_path

        except Exception as e:
            logger.error(f"获取媒体库路径失败: {e}")
            return None

    def _save_media_item(self, media_item: MediaItem):
        """保存媒体项到数据库"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO media_items
                (id, name, path, type, status, storage_location, thumbnail_path, preview_path,
                 metadata, scene_analysis, edit_decisions, ai_tags, collection_id, folder_id,
                 created_at, updated_at, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                media_item.id, media_item.name, media_item.path, media_item.type.value, media_item.status.value,
                media_item.storage_location.value, media_item.thumbnail_path, media_item.preview_path,
                json.dumps(media_item.metadata.__dict__), json.dumps([scene.__dict__ for scene in media_item.scene_analysis]),
                json.dumps([decision.__dict__ for decision in media_item.edit_decisions]), json.dumps(media_item.ai_tags),
                media_item.collection_id, media_item.folder_id, media_item.created_at.isoformat(),
                media_item.updated_at.isoformat(), media_item.accessed_at.isoformat() if media_item.accessed_at else None
            ))

            conn.commit()
            conn.close()

    def _save_collection(self, collection: MediaCollection):
        """保存集合到数据库"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE media_collections SET
                    name = ?, description = ?, parent_id = ?, items = ?, tags = ?, updated_at = ?
                WHERE id = ?
            ''', (
                collection.name, collection.description, collection.parent_id,
                json.dumps(collection.items), json.dumps(collection.tags),
                collection.updated_at.isoformat(), collection.id
            ))

            conn.commit()
            conn.close()

    def _get_collection(self, collection_id: str) -> Optional[MediaCollection]:
        """获取集合"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM media_collections WHERE id = ?', (collection_id,))
                row = cursor.fetchone()

                conn.close()

                if row:
                    return self._row_to_collection(row)
                return None

        except Exception as e:
            logger.error(f"获取集合失败: {e}")
            return None

    def _get_cache_size(self) -> int:
        """获取缓存大小"""
        try:
            total_size = 0
            if os.path.exists(self.cache_dir):
                for root, dirs, files in os.walk(self.cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
            return 0

    def _row_to_media_item(self, row) -> MediaItem:
        """将数据库行转换为媒体项"""
        metadata_dict = json.loads(row[8]) if row[8] else {}
        scene_analysis_data = json.loads(row[9]) if row[9] else []
        edit_decisions_data = json.loads(row[10]) if row[10] else []

        metadata = MediaMetadata(**metadata_dict)
        scene_analysis = [AISceneAnalysis(**scene) for scene in scene_analysis_data]
        edit_decisions = [AIEditDecision(**decision) for decision in edit_decisions_data]

        return MediaItem(
            id=row[0],
            name=row[1],
            path=row[2],
            type=MediaType(row[3]),
            status=MediaStatus(row[4]),
            storage_location=StorageLocation(row[5]),
            thumbnail_path=row[6],
            preview_path=row[7],
            metadata=metadata,
            scene_analysis=scene_analysis,
            edit_decisions=edit_decisions,
            ai_tags=json.loads(row[11]) if row[11] else [],
            collection_id=row[12],
            folder_id=row[13],
            created_at=datetime.fromisoformat(row[14]),
            updated_at=datetime.fromisoformat(row[15]),
            accessed_at=datetime.fromisoformat(row[16]) if row[16] else None
        )

    def _row_to_collection(self, row) -> MediaCollection:
        """将数据库行转换为集合"""
        return MediaCollection(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            parent_id=row[3],
            items=json.loads(row[4]) if row[4] else [],
            tags=json.loads(row[5]) if row[5] else [],
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7])
        )

    def cleanup(self):
        """清理资源"""
        logger.info("清理统一媒体管理系统资源")

        # 清理缩略图生成器
        if hasattr(self, 'thumbnail_generator'):
            self.thumbnail_generator.stop_all()

        # 清理视频引擎
        if hasattr(self, 'video_engine'):
            self.video_engine.cleanup()

        logger.info("统一媒体管理系统资源清理完成")


# 工厂函数
def create_unified_media_manager(db_path: str = None, cache_dir: str = None) -> UnifiedMediaManager:
    """创建统一媒体管理器"""
    return UnifiedMediaManager(db_path, cache_dir)


if __name__ == "__main__":
    # 测试代码
    manager = create_unified_media_manager()

    # 测试导入文件
    test_files = ["test_video.mp4", "test_image.jpg", "test_audio.mp3"]

    for file_path in test_files:
        if os.path.exists(file_path):
            item = manager.import_media_file(file_path)
            if item:
                print(f"导入成功: {item.name}")

    # 测试搜索
    search_results = manager.search_media_items("test")
    print(f"搜索结果: {len(search_results)} 个项目")

    # 测试统计
    stats = manager.get_storage_stats()
    print(f"存储统计: {stats}")

    manager.cleanup()