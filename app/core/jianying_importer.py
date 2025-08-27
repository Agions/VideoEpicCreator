#!/usr/bin/env python3
"""
剪映项目导入器
将剪映草稿文件导入到VideoEpicCreator项目中
"""

import os
import shutil
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import json

from .jianying_parser import JianyingDraftParser, JianyingProject
from .project_manager import ProjectManager, Project
from .video_engine import VideoEngine
from ..utils.file_utils import FileUtils
from ..utils.config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    project: Optional[Project] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class JianyingImporter:
    """剪映项目导入器"""
    
    def __init__(self, project_manager: ProjectManager, video_engine: VideoEngine):
        self.project_manager = project_manager
        self.video_engine = video_engine
        self.parser = JianyingDraftParser()
        self.config = Config()
        self.file_utils = FileUtils()
        
        # 支持的文件格式
        self.supported_extensions = ['.draft', '.json', '.xml']
        
        # 导入设置
        self.import_settings = {
            'copy_media_files': True,
            'convert_effects': True,
            'preserve_transitions': True,
            'auto_adjust_timeline': True,
            'create_backup': True
        }
    
    def import_project(self, draft_file_path: str, target_folder: Optional[str] = None) -> ImportResult:
        """导入剪映项目"""
        result = ImportResult(success=False)
        
        try:
            # 验证文件
            validation_result = self._validate_import_file(draft_file_path)
            if not validation_result['valid']:
                result.errors.extend(validation_result['errors'])
                return result
            
            # 解析剪映草稿
            logger.info(f"开始解析剪映草稿: {draft_file_path}")
            jianying_project = self.parser.parse_draft(draft_file_path)
            
            if not jianying_project:
                result.errors.append("无法解析剪映草稿文件")
                return result
            
            # 验证项目数据
            validation_errors = self.parser.validate_project(jianying_project)
            if validation_errors:
                result.errors.extend(validation_errors)
                return result
            
            # 创建VideoEpicCreator项目
            logger.info(f"创建VideoEpicCreator项目: {jianying_project.name}")
            project = self._create_project_from_jianying(jianying_project, target_folder)
            
            if not project:
                result.errors.append("无法创建项目")
                return result
            
            # 处理媒体文件
            if self.import_settings['copy_media_files']:
                media_result = self._process_media_files(jianying_project, project)
                if not media_result['success']:
                    result.errors.extend(media_result['errors'])
                result.warnings.extend(media_result['warnings'])
            
            # 转换效果和转场
            if self.import_settings['convert_effects']:
                effects_result = self._convert_effects(jianying_project, project)
                if not effects_result['success']:
                    result.errors.extend(effects_result['errors'])
                result.warnings.extend(effects_result['warnings'])
            
            # 保存项目
            save_result = self.project_manager.save_project(project)
            if not save_result:
                result.errors.append("无法保存项目")
                return result
            
            result.success = True
            result.project = project
            
            logger.info(f"成功导入项目: {project.name}")
            return result
            
        except Exception as e:
            error_msg = f"导入项目时出错: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return result
    
    def _validate_import_file(self, file_path: str) -> Dict[str, Any]:
        """验证导入文件"""
        errors = []
        
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                errors.append("文件不存在")
                return {'valid': False, 'errors': errors}
            
            # 检查文件扩展名
            if path.suffix.lower() not in self.supported_extensions:
                errors.append(f"不支持的文件格式: {path.suffix}")
                return {'valid': False, 'errors': errors}
            
            # 检查文件大小
            if path.stat().st_size > 100 * 1024 * 1024:  # 100MB
                errors.append("文件过大，可能不是有效的剪映草稿文件")
                return {'valid': False, 'errors': errors}
            
            return {'valid': True, 'errors': []}
            
        except Exception as e:
            errors.append(f"验证文件时出错: {str(e)}")
            return {'valid': False, 'errors': errors}
    
    def _create_project_from_jianying(self, jianying_project: JianyingProject, target_folder: Optional[str] = None) -> Optional[Project]:
        """从剪映项目创建VideoEpicCreator项目"""
        try:
            # 确定项目文件夹
            if not target_folder:
                projects_dir = Path(self.config.get('projects_dir', 'projects'))
                projects_dir.mkdir(exist_ok=True)
                target_folder = projects_dir / jianying_project.name
            else:
                target_folder = Path(target_folder)
            
            # 创建项目文件夹
            project_folder = target_folder / jianying_project.name
            project_folder.mkdir(parents=True, exist_ok=True)
            
            # 创建子文件夹
            (project_folder / 'media').mkdir(exist_ok=True)
            (project_folder / 'assets').mkdir(exist_ok=True)
            (project_folder / 'exports').mkdir(exist_ok=True)
            
            # 创建项目对象
            project = Project(
                project_id=jianying_project.project_id,
                name=jianying_project.name,
                project_folder=str(project_folder),
                settings={
                    'fps': jianying_project.fps,
                    'resolution': jianying_project.resolution,
                    'duration': jianying_project.duration,
                    'version': jianying_project.version,
                    'source_format': 'jianying',
                    'import_timestamp': self.file_utils.get_timestamp()
                },
                metadata={
                    'original_project': jianying_project.metadata,
                    'import_settings': self.import_settings,
                    'conversion_log': []
                }
            )
            
            return project
            
        except Exception as e:
            logger.error(f"创建项目时出错: {e}")
            return None
    
    def _process_media_files(self, jianying_project: JianyingProject, project: Project) -> Dict[str, Any]:
        """处理媒体文件"""
        result = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            media_folder = Path(project.project_folder) / 'media'
            media_folder.mkdir(exist_ok=True)
            
            processed_files = []
            
            # 遍历所有轨道和片段
            for track in jianying_project.tracks:
                for clip in track.clips:
                    if 'source_file' in clip and clip['source_file']:
                        file_result = self._process_single_media_file(clip['source_file'], media_folder)
                        if file_result['success']:
                            processed_files.append(file_result['file_info'])
                        else:
                            result['warnings'].append(f"无法处理媒体文件: {clip['source_file']}")
            
            # 更新项目媒体文件列表
            project.settings['media_files'] = processed_files
            
            logger.info(f"处理了 {len(processed_files)} 个媒体文件")
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"处理媒体文件时出错: {str(e)}")
        
        return result
    
    def _process_single_media_file(self, source_path: str, target_folder: Path) -> Dict[str, Any]:
        """处理单个媒体文件"""
        try:
            source_file = Path(source_path)
            
            # 检查源文件是否存在
            if not source_file.exists():
                return {'success': False, 'error': '源文件不存在'}
            
            # 生成目标文件名
            target_file = target_folder / source_file.name
            
            # 如果文件已存在，添加序号
            counter = 1
            while target_file.exists():
                stem = source_file.stem
                suffix = source_file.suffix
                target_file = target_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # 复制文件
            shutil.copy2(source_file, target_file)
            
            # 获取文件信息
            file_info = {
                'original_path': str(source_file),
                'project_path': str(target_file),
                'file_name': target_file.name,
                'file_size': target_file.stat().st_size,
                'file_type': source_file.suffix.lower(),
                'import_timestamp': self.file_utils.get_timestamp()
            }
            
            return {'success': True, 'file_info': file_info}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _convert_effects(self, jianying_project: JianyingProject, project: Project) -> Dict[str, Any]:
        """转换效果和转场"""
        result = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            converted_effects = []
            
            # 遍历所有轨道和片段
            for track in jianying_project.tracks:
                for clip in track.clips:
                    # 转换片段效果
                    if 'effects' in clip:
                        for effect in clip['effects']:
                            converted = self._convert_single_effect(effect)
                            if converted:
                                converted_effects.append(converted)
                            else:
                                result['warnings'].append(f"无法转换效果: {effect}")
                    
                    # 转换片段转场
                    if 'transitions' in clip:
                        for transition in clip['transitions']:
                            converted = self._convert_single_transition(transition)
                            if converted:
                                converted_effects.append(converted)
                            else:
                                result['warnings'].append(f"无法转换转场: {transition}")
            
            # 更新项目效果列表
            project.settings['effects'] = converted_effects
            
            logger.info(f"转换了 {len(converted_effects)} 个效果和转场")
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"转换效果时出错: {str(e)}")
        
        return result
    
    def _convert_single_effect(self, effect: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换单个效果"""
        try:
            # 这里实现效果转换逻辑
            # 根据剪映效果类型映射到VideoEpicCreator效果类型
            
            converted = {
                'type': effect.get('type', 'unknown'),
                'name': effect.get('name', 'Unknown Effect'),
                'parameters': effect.get('parameters', {}),
                'start_time': effect.get('start_time', 0),
                'duration': effect.get('duration', 0),
                'converted': True
            }
            
            return converted
            
        except Exception as e:
            logger.error(f"转换效果时出错: {e}")
            return None
    
    def _convert_single_transition(self, transition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换单个转场"""
        try:
            # 这里实现转场转换逻辑
            # 根据剪映转场类型映射到VideoEpicCreator转场类型
            
            converted = {
                'type': 'transition',
                'name': transition.get('name', 'Unknown Transition'),
                'parameters': transition.get('parameters', {}),
                'duration': transition.get('duration', 0),
                'converted': True
            }
            
            return converted
            
        except Exception as e:
            logger.error(f"转换转场时出错: {e}")
            return None
    
    def get_import_summary(self, jianying_project: JianyingProject) -> Dict[str, Any]:
        """获取导入摘要信息"""
        summary = self.parser.get_project_summary(jianying_project)
        
        # 添加导入相关信息
        summary.update({
            'supported_formats': self.supported_extensions,
            'import_settings': self.import_settings,
            'estimated_processing_time': self._estimate_processing_time(jianying_project)
        })
        
        return summary
    
    def _estimate_processing_time(self, jianying_project: JianyingProject) -> float:
        """估算处理时间"""
        # 基于项目复杂度估算处理时间
        base_time = 5.0  # 基础时间5秒
        
        # 根据轨道数量增加时间
        track_time = len(jianying_project.tracks) * 2.0
        
        # 根据片段数量增加时间
        clip_time = sum(len(track.clips) for track in jianying_project.tracks) * 1.0
        
        total_time = base_time + track_time + clip_time
        
        return min(total_time, 60.0)  # 最多60秒
    
    def set_import_settings(self, settings: Dict[str, Any]):
        """设置导入选项"""
        self.import_settings.update(settings)
        logger.info(f"导入设置已更新: {settings}")
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return self.supported_formats

def main():
    """主函数"""
    # 测试导入功能
    from app.core.project_manager import ProjectManager
    from app.core.video_engine import VideoEngine
    
    # 创建必要的组件
    project_manager = ProjectManager()
    video_engine = VideoEngine()
    
    # 创建导入器
    importer = JianyingImporter(project_manager, video_engine)
    
    # 测试文件
    test_file = "/Users/zfkc/Desktop/VideoEpicCreator/test_data/sample_draft.draft"
    
    if os.path.exists(test_file):
        print(f"开始导入测试文件: {test_file}")
        
        # 获取导入摘要
        try:
            # 先解析项目获取摘要
            jianying_project = importer.parser.parse_draft(test_file)
            if jianying_project:
                summary = importer.get_import_summary(jianying_project)
                print(f"导入摘要: {summary}")
                
                # 执行导入
                result = importer.import_project(test_file)
                
                if result.success:
                    print(f"✅ 导入成功: {result.project.name}")
                    print(f"项目文件夹: {result.project.project_folder}")
                else:
                    print(f"❌ 导入失败: {result.errors}")
                    
                if result.warnings:
                    print(f"⚠️  警告: {result.warnings}")
            else:
                print("❌ 无法解析剪映草稿文件")
                
        except Exception as e:
            print(f"❌ 导入过程中出错: {e}")
    else:
        print(f"❌ 测试文件不存在: {test_file}")

if __name__ == "__main__":
    main()