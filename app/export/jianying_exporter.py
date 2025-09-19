#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
剪映导出器主类
提供完整的剪映草稿导出功能，支持最新版本的剪映项目文件格式
"""

import os
import json
import uuid
import shutil
import logging
import platform
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from app.core.video_manager import VideoClip
# from app.ai.content_generator import GeneratedContent, ContentSegment

# 占位类定义
class GeneratedContent:
    """AI生成内容占位类"""
    def __init__(self, title, video=None, audio=None, segments=None):
        self.title = title
        self.video = video
        self.audio = audio
        self.segments = segments or []

class ContentSegment:
    """内容片段占位类"""
    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
from app.export.jianying_project_parser import JianYingProjectParser
from app.export.jianying_draft_generator import JianYingDraftGenerator
from app.export.jianying_media_organizer import JianYingMediaOrganizer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class JianYingExportConfig:
    """剪映导出配置"""
    project_name: str = ""
    output_dir: str = ""
    include_audio: bool = True
    include_subtitles: bool = True
    include_effects: bool = True
    include_transitions: bool = True
    copy_media_files: bool = True
    create_backup: bool = True
    open_in_jianying: bool = False
    compression_level: int = 5  # 1-10, 10为最高压缩


@dataclass
class JianYingExportResult:
    """剪映导出结果"""
    success: bool
    project_path: str = ""
    draft_file_path: str = ""
    media_files: List[str] = None
    error_message: str = ""
    export_time: float = 0.0
    file_size: int = 0

    def __post_init__(self):
        if self.media_files is None:
            self.media_files = []


class JianYingExporter(QObject):
    """剪映导出器主类"""

    # 信号定义
    export_started = pyqtSignal(str)  # 项目名称
    export_progress = pyqtSignal(int, str)  # 进度百分比, 状态信息
    export_completed = pyqtSignal(JianYingExportResult)  # 导出结果
    export_error = pyqtSignal(str)  # 错误信息
    project_opened = pyqtSignal(str)  # 项目路径

    def __init__(self):
        super().__init__()

        # 初始化组件
        self.project_parser = JianYingProjectParser()
        self.draft_generator = JianYingDraftGenerator()
        self.media_organizer = JianYingMediaOrganizer()

        # 剪映安装路径检测
        self.jianying_paths = self._detect_jianying_installation()
        self.is_installed = len(self.jianying_paths) > 0

        # 支持的剪映版本
        self.supported_versions = ["3.0.0", "3.1.0", "3.2.0", "3.3.0", "4.0.0"]
        self.current_version = "4.0.0"  # 最新版本

        # 导出统计
        self.export_stats = {
            "total_exports": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "last_export_time": None
        }

        logger.info("剪映导出器初始化完成")

    def _detect_jianying_installation(self) -> List[str]:
        """检测剪映安装路径"""
        paths = []
        system = platform.system().lower()

        if system == "windows":
            # Windows常见安装路径
            possible_paths = [
                os.path.expanduser("~/AppData/Local/JianyingPro"),
                "C:/Program Files/JianyingPro",
                "C:/Program Files (x86)/JianyingPro",
                os.path.expanduser("~/AppData/Local/Programs/JianyingPro"),
                "C:/Users/Default/AppData/Local/JianyingPro"
            ]
        elif system == "darwin":
            # macOS路径
            possible_paths = [
                "/Applications/JianyingPro.app",
                os.path.expanduser("~/Applications/JianyingPro.app"),
                "/Applications/剪映专业版.app",
                os.path.expanduser("~/Applications/剪映专业版.app")
            ]
        else:
            # Linux（如果有的话）
            possible_paths = []

        for path in possible_paths:
            if os.path.exists(path):
                paths.append(path)
                logger.info(f"检测到剪映安装路径: {path}")

        return paths

    def is_jianying_installed(self) -> bool:
        """检查剪映是否已安装"""
        return self.is_installed

    def get_installation_info(self) -> Dict[str, Any]:
        """获取剪映安装信息"""
        return {
            "installed": self.is_installed,
            "paths": self.jianying_paths,
            "system": platform.system(),
            "supported_versions": self.supported_versions,
            "current_version": self.current_version
        }

    def export_project(self,
                      project_data: Union[VideoClip, GeneratedContent, Dict[str, Any]],
                      config: JianYingExportConfig = None) -> JianYingExportResult:
        """导出项目到剪映格式"""
        start_time = datetime.now()

        if config is None:
            config = JianYingExportConfig()

        try:
            self.export_started.emit(config.project_name or "未命名项目")

            # 验证项目数据
            if not self._validate_project_data(project_data):
                error_msg = "项目数据格式无效"
                self.export_error.emit(error_msg)
                return JianYingExportResult(success=False, error_message=error_msg)

            # 解析项目数据
            self.export_progress.emit(10, "解析项目数据...")
            parsed_project = self.project_parser.parse_project(project_data)

            # 设置输出目录
            output_dir = self._prepare_output_directory(config)

            # 生成剪映草稿
            self.export_progress.emit(30, "生成剪映草稿...")
            draft_data = self.draft_generator.generate_draft(
                parsed_project,
                self.current_version
            )

            # 组织媒体文件
            self.export_progress.emit(50, "组织媒体文件...")
            media_files = []
            if config.copy_media_files:
                media_files = self.media_organizer.organize_media_files(
                    parsed_project,
                    output_dir
                )
                self.export_progress.emit(70, "媒体文件组织完成")

            # 写入项目文件
            self.export_progress.emit(80, "写入项目文件...")
            project_path = self._write_project_files(draft_data, output_dir, config)

            # 创建备份
            if config.create_backup:
                self._create_backup(project_path, config)

            # 在剪映中打开
            if config.open_in_jianying and self.is_installed:
                self._open_in_jianying(project_path)

            # 计算文件大小
            file_size = self._calculate_project_size(project_path)

            # 计算导出时间
            export_time = (datetime.now() - start_time).total_seconds()

            # 更新统计信息
            self._update_export_stats(True, export_time)

            # 创建结果对象
            result = JianYingExportResult(
                success=True,
                project_path=project_path,
                draft_file_path=os.path.join(project_path, "draft_content.json"),
                media_files=media_files,
                export_time=export_time,
                file_size=file_size
            )

            self.export_completed.emit(result)
            logger.info(f"项目导出成功: {project_path}")

            return result

        except Exception as e:
            export_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"导出失败: {str(e)}"
            self.export_error.emit(error_msg)
            self._update_export_stats(False, export_time)

            logger.error(f"项目导出失败: {error_msg}")
            return JianYingExportResult(
                success=False,
                error_message=error_msg,
                export_time=export_time
            )

    def _validate_project_data(self, project_data: Union[VideoClip, GeneratedContent, Dict[str, Any]]) -> bool:
        """验证项目数据格式"""
        try:
            if isinstance(project_data, VideoClip):
                return os.path.exists(project_data.file_path)
            elif isinstance(project_data, GeneratedContent):
                return project_data.video is not None and os.path.exists(project_data.video.file_path)
            elif isinstance(project_data, dict):
                # 检查必要字段
                required_fields = ["name", "clips"]
                return all(field in project_data for field in required_fields)
            else:
                return False
        except Exception as e:
            logger.error(f"项目数据验证失败: {e}")
            return False

    def _prepare_output_directory(self, config: JianYingExportConfig) -> str:
        """准备输出目录"""
        if not config.output_dir:
            config.output_dir = os.path.expanduser("~/Desktop/CineAIStudio_Projects")

        # 创建项目目录
        project_name = config.project_name or f"VideoEpic_{uuid.uuid4().hex[:8]}"
        project_dir = os.path.join(config.output_dir, project_name)

        os.makedirs(project_dir, exist_ok=True)

        # 创建子目录
        subdirs = ["media", "audio", "images", "texts", "effects"]
        for subdir in subdirs:
            os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)

        return project_dir

    def _write_project_files(self, draft_data: Dict[str, Any], output_dir: str, config: JianYingExportConfig) -> str:
        """写入项目文件"""
        # 主项目文件
        project_file = os.path.join(output_dir, "draft_content.json")

        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)

        # 项目信息文件
        project_info = {
            "exporter": "CineAIStudio",
            "version": "2.0.0",
            "export_time": datetime.now().isoformat(),
            "jianying_version": self.current_version,
            "config": asdict(config)
        }

        info_file = os.path.join(output_dir, "project_info.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)

        # 生成项目预览图
        self._generate_preview_image(output_dir)

        return output_dir

    def _generate_preview_image(self, output_dir: str):
        """生成项目预览图"""
        # 这里可以生成项目预览图
        preview_file = os.path.join(output_dir, "preview.jpg")
        # 创建一个空的预览文件
        with open(preview_file, 'wb') as f:
            f.write(b'')

    def _create_backup(self, project_path: str, config: JianYingExportConfig):
        """创建项目备份"""
        try:
            backup_dir = os.path.join(config.output_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_name)

            shutil.copytree(project_path, backup_path)
            logger.info(f"项目备份创建成功: {backup_path}")

        except Exception as e:
            logger.warning(f"创建备份失败: {e}")

    def _open_in_jianying(self, project_path: str) -> bool:
        """在剪映中打开项目"""
        if not self.is_installed:
            logger.warning("剪映未安装，无法打开项目")
            return False

        try:
            system = platform.system().lower()

            if system == "windows":
                import subprocess
                subprocess.Popen([self.jianying_paths[0], project_path])
            elif system == "darwin":
                os.system(f'open -a "{self.jianying_paths[0]}" "{project_path}"')

            self.project_opened.emit(project_path)
            logger.info(f"在剪映中打开项目: {project_path}")
            return True

        except Exception as e:
            logger.error(f"打开剪映失败: {e}")
            return False

    def _calculate_project_size(self, project_path: str) -> int:
        """计算项目文件大小"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.warning(f"计算项目大小失败: {e}")

        return total_size

    def _update_export_stats(self, success: bool, export_time: float):
        """更新导出统计信息"""
        self.export_stats["total_exports"] += 1
        if success:
            self.export_stats["successful_exports"] += 1
        else:
            self.export_stats["failed_exports"] += 1

        self.export_stats["last_export_time"] = datetime.now().isoformat()

    def get_export_stats(self) -> Dict[str, Any]:
        """获取导出统计信息"""
        return self.export_stats.copy()

    def get_installation_guide(self) -> Dict[str, Any]:
        """获取剪映安装指南"""
        system = platform.system().lower()

        guides = {
            "windows": {
                "title": "Windows 剪映专业版安装指南",
                "steps": [
                    "1. 访问剪映官网: https://lv.ulikecam.com/",
                    "2. 点击'免费下载'按钮",
                    "3. 下载Windows版本安装包",
                    "4. 运行安装程序并按照提示完成安装",
                    "5. 重启CineAIStudio以检测剪映"
                ],
                "download_url": "https://lv.ulikecam.com/",
                "system_requirements": [
                    "操作系统: Windows 10/11 (64位)",
                    "处理器: Intel i5/AMD Ryzen 5 或更高",
                    "内存: 8GB RAM (推荐16GB)",
                    "显卡: 支持DirectX 11",
                    "存储空间: 10GB 可用空间"
                ]
            },
            "darwin": {
                "title": "macOS 剪映专业版安装指南",
                "steps": [
                    "1. 访问剪映官网: https://lv.ulikecam.com/",
                    "2. 点击'免费下载'按钮",
                    "3. 下载macOS版本安装包",
                    "4. 打开DMG文件并拖拽到Applications文件夹",
                    "5. 重启CineAIStudio以检测剪映"
                ],
                "download_url": "https://lv.ulikecam.com/",
                "system_requirements": [
                    "操作系统: macOS 10.15+ (推荐11.0+)",
                    "处理器: Intel Core i5 或 Apple M1",
                    "内存: 8GB RAM (推荐16GB)",
                    "显卡: 支持Metal",
                    "存储空间: 10GB 可用空间"
                ]
            }
        }

        return guides.get(system, guides["windows"])

    def validate_jianying_compatibility(self) -> Dict[str, Any]:
        """验证剪映兼容性"""
        compatibility = {
            "compatible": False,
            "version": self.current_version,
            "issues": [],
            "recommendations": []
        }

        if not self.is_installed:
            compatibility["issues"].append("剪映未安装")
            compatibility["recommendations"].append("请安装剪映专业版")
        else:
            compatibility["compatible"] = True
            compatibility["recommendations"].append("剪映版本兼容性良好")

        # 检查系统要求
        system = platform.system().lower()
        if system == "windows":
            if platform.release() < "10":
                compatibility["issues"].append("Windows版本过低，推荐Windows 10/11")
        elif system == "darwin":
            if platform.mac_ver()[0] < "10.15":
                compatibility["issues"].append("macOS版本过低，推荐10.15+")

        return compatibility

    def cleanup_temp_files(self, project_path: str):
        """清理临时文件"""
        try:
            temp_files = []
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    if file.startswith(".tmp") or file.startswith("~"):
                        temp_files.append(os.path.join(root, file))

            for temp_file in temp_files:
                os.remove(temp_file)
                logger.info(f"清理临时文件: {temp_file}")

        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式"""
        return {
            "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v", ".3gp"],
            "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
            "image": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
            "text": [".txt", ".srt", ".ass", ".lrc"]
        }

    def validate_media_format(self, file_path: str) -> bool:
        """验证媒体文件格式"""
        _, ext = os.path.splitext(file_path.lower())
        supported_formats = self.get_supported_formats()

        for format_list in supported_formats.values():
            if ext in format_list:
                return True

        return False


def create_jianying_exporter() -> JianYingExporter:
    """创建剪映导出器实例"""
    return JianYingExporter()
