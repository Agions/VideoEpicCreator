#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映导出模块
提供完整的剪映草稿导出功能
"""

from .jianying_exporter import (
    JianYingExporter,
    JianYingExportConfig,
    JianYingExportResult,
    create_jianying_exporter
)

from .jianying_project_parser import (
    JianYingProjectParser,
    JianYingProject,
    JianYingTrack,
    JianYingClip
)

from .jianying_draft_generator import JianYingDraftGenerator

from .jianying_media_organizer import (
    JianYingMediaOrganizer,
    MediaFile
)

__version__ = "2.0.0"
__author__ = "CineAIStudio Team"
__description__ = "剪映草稿导出系统"

# 导出的主要类和函数
__all__ = [
    # 主导出器
    "JianYingExporter",
    "JianYingExportConfig",
    "JianYingExportResult",
    "create_jianying_exporter",

    # 项目解析器
    "JianYingProjectParser",
    "JianYingProject",
    "JianYingTrack",
    "JianYingClip",

    # 草稿生成器
    "JianYingDraftGenerator",

    # 媒体组织器
    "JianYingMediaOrganizer",
    "MediaFile",
]

# 模块信息
MODULE_INFO = {
    "name": "剪映导出模块",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "supported_jianying_versions": ["4.0.0", "3.8.0", "3.7.0"],
    "supported_formats": {
        "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v", ".3gp"],
        "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
        "image": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
        "text": [".txt", ".srt", ".ass", ".lrc"]
    },
    "features": [
        "完整的项目解析",
        "剪映草稿生成",
        "素材文件组织",
        "元数据同步",
        "兼容性检查",
        "错误处理",
        "进度反馈",
        "统计信息"
    ]
}

def get_module_info():
    """获取模块信息"""
    return MODULE_INFO.copy()

def check_jianying_compatibility():
    """检查剪映兼容性"""
    exporter = create_jianying_exporter()
    return exporter.validate_jianying_compatibility()

def get_supported_formats():
    """获取支持的格式"""
    return MODULE_INFO["supported_formats"].copy()

def quick_export(project_data, output_path=None, **kwargs):
    """快速导出功能"""
    exporter = create_jianying_exporter()

    config = JianYingExportConfig(
        project_name=kwargs.get("project_name", "快速导出项目"),
        output_dir=output_path or kwargs.get("output_dir"),
        include_audio=kwargs.get("include_audio", True),
        include_subtitles=kwargs.get("include_subtitles", True),
        include_effects=kwargs.get("include_effects", True),
        include_transitions=kwargs.get("include_transitions", True),
        copy_media_files=kwargs.get("copy_media_files", True),
        create_backup=kwargs.get("create_backup", False),
        open_in_jianying=kwargs.get("open_in_jianying", False),
        compression_level=kwargs.get("compression_level", 5)
    )

    return exporter.export_project(project_data, config)

# 使用示例
def usage_example():
    """使用示例"""
    # 创建导出器
    exporter = create_jianying_exporter()

    # 检查兼容性
    compatibility = check_jianying_compatibility()
    print(f"兼容性: {compatibility}")

    # 获取支持的格式
    formats = get_supported_formats()
    print(f"支持的视频格式: {formats['video']}")

    # 快速导出
    # result = quick_export(project_data, "/path/to/output")

    return True

# 模块初始化
def _init_module():
    """模块初始化"""
    import logging

    # 设置日志
    logger = logging.getLogger(__name__)
    logger.info(f"剪映导出模块 v{__version__} 初始化完成")

# 自动初始化
_init_module()
