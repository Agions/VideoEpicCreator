#!/usr/bin/env python3
"""
剪映到VideoEpicCreator项目转换器
将剪映项目转换为VideoEpicCreator项目格式
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import copy

from .jianying_parser import JianyingProject, JianyingTrack, JianyingClip
from .project_manager import Project
from .video_engine import VideoEngine
from ..utils.config import Config
from ..utils.file_utils import FileUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConversionMapping:
    """转换映射配置"""
    effect_mapping: Dict[str, str]
    transition_mapping: Dict[str, str]
    filter_mapping: Dict[str, str]
    text_style_mapping: Dict[str, str]
    audio_effect_mapping: Dict[str, str]

@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    project: Optional[Project] = None
    conversion_log: List[str] = None
    statistics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversion_log is None:
            self.conversion_log = []
        if self.statistics is None:
            self.statistics = {}

class JianyingProjectConverter:
    """剪映项目转换器"""
    
    def __init__(self, video_engine: VideoEngine):
        self.video_engine = video_engine
        self.config = Config()
        self.file_utils = FileUtils()
        
        # 初始化转换映射
        self.mapping = self._init_conversion_mapping()
        
        # 转换统计
        self.conversion_stats = {
            'total_clips': 0,
            'converted_clips': 0,
            'failed_clips': 0,
            'total_effects': 0,
            'converted_effects': 0,
            'failed_effects': 0,
            'total_transitions': 0,
            'converted_transitions': 0,
            'failed_transitions': 0
        }
    
    def convert_project(self, jianying_project: JianyingProject, base_project: Project) -> ConversionResult:
        """转换剪映项目为VideoEpicCreator项目"""
        result = ConversionResult(success=False)
        
        try:
            logger.info(f"开始转换项目: {jianying_project.name}")
            
            # 深拷贝基础项目
            converted_project = copy.deepcopy(base_project)
            
            # 转换项目基本信息
            self._convert_project_info(jianying_project, converted_project)
            
            # 转换时间轴
            timeline_result = self._convert_timeline(jianying_project, converted_project)
            if not timeline_result['success']:
                result.conversion_log.extend(timeline_result['errors'])
                return result
            
            # 转换媒体资源
            media_result = self._convert_media_assets(jianying_project, converted_project)
            if not media_result['success']:
                result.conversion_log.extend(media_result['errors'])
            
            # 转换效果
            effects_result = self._convert_effects(jianying_project, converted_project)
            if not effects_result['success']:
                result.conversion_log.extend(effects_result['errors'])
            
            # 转换音频
            audio_result = self._convert_audio(jianying_project, converted_project)
            if not audio_result['success']:
                result.conversion_log.extend(audio_result['errors'])
            
            # 优化时间轴
            if self.config.get('auto_optimize_timeline', True):
                self._optimize_timeline(converted_project)
            
            # 设置转换结果
            result.success = True
            result.project = converted_project
            result.conversion_log = self._get_conversion_log()
            result.statistics = self.conversion_stats.copy()
            
            logger.info(f"项目转换完成: {jianying_project.name}")
            return result
            
        except Exception as e:
            error_msg = f"转换项目时出错: {str(e)}"
            logger.error(error_msg)
            result.conversion_log.append(error_msg)
            return result
    
    def _init_conversion_mapping(self) -> ConversionMapping:
        """初始化转换映射"""
        return ConversionMapping(
            effect_mapping={
                # 视频效果映射
                'brightness': 'brightness',
                'contrast': 'contrast',
                'saturation': 'saturation',
                'hue': 'hue',
                'blur': 'gaussian_blur',
                'sharpen': 'sharpen',
                'vignette': 'vignette',
                'glitch': 'digital_glitch',
                'fade_in': 'fade_in',
                'fade_out': 'fade_out',
                'zoom_in': 'zoom_in',
                'zoom_out': 'zoom_out',
                'slide_left': 'slide_left',
                'slide_right': 'slide_right',
                'slide_up': 'slide_up',
                'slide_down': 'slide_down'
            },
            transition_mapping={
                # 转场效果映射
                'fade': 'fade',
                'dissolve': 'dissolve',
                'slide': 'slide',
                'wipe': 'wipe',
                'zoom': 'zoom',
                'rotate': 'rotate',
                'flip': 'flip',
                'circle': 'circle',
                'star': 'star',
                'heart': 'heart'
            },
            filter_mapping={
                # 滤镜映射
                'black_white': 'grayscale',
                'sepia': 'sepia',
                'vintage': 'vintage',
                'cold': 'cool',
                'warm': 'warm',
                'dramatic': 'dramatic',
                'cinematic': 'cinematic'
            },
            text_style_mapping={
                # 文本样式映射
                'title': 'title',
                'subtitle': 'subtitle',
                'body': 'body',
                'caption': 'caption',
                'highlight': 'highlight'
            },
            audio_effect_mapping={
                # 音频效果映射
                'fade_in': 'audio_fade_in',
                'fade_out': 'audio_fade_out',
                'echo': 'echo',
                'reverb': 'reverb',
                'pitch_shift': 'pitch_shift',
                'speed_up': 'speed_up',
                'slow_down': 'slow_down'
            }
        )
    
    def _convert_project_info(self, jianying_project: JianyingProject, converted_project: Project):
        """转换项目基本信息"""
        # 更新项目设置
        converted_project.settings.update({
            'fps': jianying_project.fps,
            'resolution': jianying_project.resolution,
            'duration': jianying_project.duration,
            'source_project': {
                'name': jianying_project.name,
                'version': jianying_project.version,
                'project_id': jianying_project.project_id
            }
        })
        
        # 更新元数据
        converted_project.metadata.update({
            'conversion_info': {
                'source_format': 'jianying',
                'conversion_time': self.file_utils.get_timestamp(),
                'converter_version': '1.0.0'
            },
            'original_metadata': jianying_project.metadata
        })
    
    def _convert_timeline(self, jianying_project: JianyingProject, converted_project: Project) -> Dict[str, Any]:
        """转换时间轴"""
        result = {'success': True, 'errors': []}
        
        try:
            timeline = {
                'tracks': [],
                'total_duration': jianying_project.duration,
                'fps': jianying_project.fps
            }
            
            # 转换每个轨道
            for jianying_track in jianying_project.tracks:
                track_result = self._convert_track(jianying_track)
                if track_result['success']:
                    timeline['tracks'].append(track_result['track'])
                else:
                    result['errors'].extend(track_result['errors'])
            
            converted_project.settings['timeline'] = timeline
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"转换时间轴时出错: {str(e)}")
        
        return result
    
    def _convert_track(self, jianying_track: JianyingTrack) -> Dict[str, Any]:
        """转换单个轨道"""
        result = {'success': True, 'errors': []}
        
        try:
            track = {
                'track_id': jianying_track.track_id,
                'track_type': jianying_track.track_type,
                'duration': jianying_track.duration,
                'start_time': jianying_track.start_time,
                'clips': []
            }
            
            # 转换轨道中的片段
            for clip_data in jianying_track.clips:
                clip_result = self._convert_clip(clip_data, jianying_track.track_type)
                if clip_result['success']:
                    track['clips'].append(clip_result['clip'])
                    self.conversion_stats['converted_clips'] += 1
                else:
                    result['errors'].append(f"转换片段失败: {clip_result['error']}")
                    self.conversion_stats['failed_clips'] += 1
                
                self.conversion_stats['total_clips'] += 1
            
            result['track'] = track
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"转换轨道时出错: {str(e)}")
        
        return result
    
    def _convert_clip(self, clip_data: Dict[str, Any], track_type: str) -> Dict[str, Any]:
        """转换单个片段"""
        result = {'success': True, 'clip': None, 'error': None}
        
        try:
            clip = {
                'clip_id': clip_data.get('clip_id', ''),
                'source_file': clip_data.get('source_file', ''),
                'start_time': clip_data.get('start_time', 0),
                'end_time': clip_data.get('end_time', 0),
                'duration': clip_data.get('duration', 0),
                'track_type': track_type,
                'position': clip_data.get('position', {}),
                'effects': [],
                'transitions': []
            }
            
            # 转换效果
            if 'effects' in clip_data:
                for effect_data in clip_data['effects']:
                    effect_result = self._convert_effect(effect_data, track_type)
                    if effect_result['success']:
                        clip['effects'].append(effect_result['effect'])
                        self.conversion_stats['converted_effects'] += 1
                    else:
                        logger.warning(f"转换效果失败: {effect_result['error']}")
                        self.conversion_stats['failed_effects'] += 1
                    
                    self.conversion_stats['total_effects'] += 1
            
            # 转换转场
            if 'transitions' in clip_data:
                for transition_data in clip_data['transitions']:
                    transition_result = self._convert_transition(transition_data)
                    if transition_result['success']:
                        clip['transitions'].append(transition_result['transition'])
                        self.conversion_stats['converted_transitions'] += 1
                    else:
                        logger.warning(f"转换转场失败: {transition_result['error']}")
                        self.conversion_stats['failed_transitions'] += 1
                    
                    self.conversion_stats['total_transitions'] += 1
            
            result['clip'] = clip
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _convert_effect(self, effect_data: Dict[str, Any], track_type: str) -> Dict[str, Any]:
        """转换单个效果"""
        result = {'success': True, 'effect': None, 'error': None}
        
        try:
            effect_type = effect_data.get('type', '')
            mapping_dict = self._get_effect_mapping(track_type)
            
            # 查找映射的效果类型
            mapped_type = mapping_dict.get(effect_type, effect_type)
            
            effect = {
                'type': mapped_type,
                'name': effect_data.get('name', mapped_type),
                'parameters': self._convert_effect_parameters(effect_data.get('parameters', {})),
                'start_time': effect_data.get('start_time', 0),
                'duration': effect_data.get('duration', 0),
                'original_type': effect_type
            }
            
            result['effect'] = effect
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _convert_transition(self, transition_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换单个转场"""
        result = {'success': True, 'transition': None, 'error': None}
        
        try:
            transition_type = transition_data.get('type', '')
            mapped_type = self.mapping.transition_mapping.get(transition_type, transition_type)
            
            transition = {
                'type': mapped_type,
                'name': transition_data.get('name', mapped_type),
                'parameters': self._convert_effect_parameters(transition_data.get('parameters', {})),
                'duration': transition_data.get('duration', 0),
                'original_type': transition_type
            }
            
            result['transition'] = transition
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _get_effect_mapping(self, track_type: str) -> Dict[str, str]:
        """根据轨道类型获取效果映射"""
        if track_type == 'video':
            return self.mapping.effect_mapping
        elif track_type == 'audio':
            return self.mapping.audio_effect_mapping
        elif track_type == 'text':
            return self.mapping.text_style_mapping
        else:
            return self.mapping.effect_mapping
    
    def _convert_effect_parameters(self, original_params: Dict[str, Any]) -> Dict[str, Any]:
        """转换效果参数"""
        converted_params = {}
        
        for key, value in original_params.items():
            # 参数名映射
            if key in ['intensity', 'strength']:
                converted_params['intensity'] = float(value)
            elif key in ['speed', 'rate']:
                converted_params['speed'] = float(value)
            elif key in ['angle', 'rotation']:
                converted_params['angle'] = float(value)
            elif key in ['scale', 'zoom']:
                converted_params['scale'] = float(value)
            elif key in ['opacity', 'alpha']:
                converted_params['opacity'] = float(value)
            elif key in ['color', 'colour']:
                converted_params['color'] = str(value)
            else:
                converted_params[key] = value
        
        return converted_params
    
    def _convert_media_assets(self, jianying_project: JianyingProject, converted_project: Project) -> Dict[str, Any]:
        """转换媒体资源"""
        result = {'success': True, 'errors': []}
        
        try:
            media_assets = []
            
            # 遍历所有轨道和片段，收集媒体文件
            for track in jianying_project.tracks:
                for clip in track.clips:
                    if 'source_file' in clip and clip['source_file']:
                        asset_info = self._create_media_asset_info(clip['source_file'])
                        if asset_info:
                            media_assets.append(asset_info)
            
            converted_project.settings['media_assets'] = media_assets
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"转换媒体资源时出错: {str(e)}")
        
        return result
    
    def _create_media_asset_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """创建媒体资源信息"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            return {
                'file_path': str(path),
                'file_name': path.name,
                'file_size': path.stat().st_size,
                'file_type': path.suffix.lower(),
                'media_type': self._get_media_type(path.suffix.lower())
            }
            
        except Exception as e:
            logger.error(f"创建媒体资源信息时出错: {e}")
            return None
    
    def _get_media_type(self, file_extension: str) -> str:
        """根据文件扩展名确定媒体类型"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        audio_extensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg']
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        if file_extension in video_extensions:
            return 'video'
        elif file_extension in audio_extensions:
            return 'audio'
        elif file_extension in image_extensions:
            return 'image'
        else:
            return 'unknown'
    
    def _convert_audio(self, jianying_project: JianyingProject, converted_project: Project) -> Dict[str, Any]:
        """转换音频设置"""
        result = {'success': True, 'errors': []}
        
        try:
            audio_settings = {
                'sample_rate': 44100,
                'channels': 2,
                'bitrate': 128,
                'tracks': []
            }
            
            # 转换音频轨道
            for track in jianying_project.tracks:
                if track.track_type == 'audio':
                    audio_track = {
                        'track_id': track.track_id,
                        'duration': track.duration,
                        'clips': []
                    }
                    
                    for clip in track.clips:
                        audio_clip = {
                            'clip_id': clip.get('clip_id', ''),
                            'source_file': clip.get('source_file', ''),
                            'start_time': clip.get('start_time', 0),
                            'duration': clip.get('duration', 0),
                            'volume': clip.get('volume', 1.0),
                            'effects': []
                        }
                        
                        # 转换音频效果
                        if 'effects' in clip:
                            for effect in clip['effects']:
                                audio_effect = self._convert_audio_effect(effect)
                                if audio_effect:
                                    audio_clip['effects'].append(audio_effect)
                        
                        audio_track['clips'].append(audio_clip)
                    
                    audio_settings['tracks'].append(audio_track)
            
            converted_project.settings['audio'] = audio_settings
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"转换音频设置时出错: {str(e)}")
        
        return result
    
    def _convert_audio_effect(self, effect_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换音频效果"""
        try:
            effect_type = effect_data.get('type', '')
            mapped_type = self.mapping.audio_effect_mapping.get(effect_type, effect_type)
            
            return {
                'type': mapped_type,
                'parameters': effect_data.get('parameters', {}),
                'start_time': effect_data.get('start_time', 0),
                'duration': effect_data.get('duration', 0)
            }
            
        except Exception as e:
            logger.error(f"转换音频效果时出错: {e}")
            return None
    
    def _optimize_timeline(self, project: Project):
        """优化时间轴"""
        try:
            timeline = project.settings.get('timeline', {})
            
            if not timeline or 'tracks' not in timeline:
                return
            
            # 计算实际的项目时长
            max_duration = 0
            for track in timeline['tracks']:
                if 'clips' in track:
                    for clip in track['clips']:
                        end_time = clip.get('start_time', 0) + clip.get('duration', 0)
                        max_duration = max(max_duration, end_time)
            
            # 更新项目时长
            timeline['total_duration'] = max_duration
            project.settings['duration'] = max_duration
            
            # 优化轨道顺序
            timeline['tracks'].sort(key=lambda x: x.get('start_time', 0))
            
            logger.info(f"时间轴优化完成，总时长: {max_duration}秒")
            
        except Exception as e:
            logger.error(f"优化时间轴时出错: {e}")
    
    def _get_conversion_log(self) -> List[str]:
        """获取转换日志"""
        log = []
        
        log.append(f"转换统计:")
        log.append(f"  总片段数: {self.conversion_stats['total_clips']}")
        log.append(f"  成功转换片段: {self.conversion_stats['converted_clips']}")
        log.append(f"  失败片段: {self.conversion_stats['failed_clips']}")
        log.append(f"  总效果数: {self.conversion_stats['total_effects']}")
        log.append(f"  成功转换效果: {self.conversion_stats['converted_effects']}")
        log.append(f"  失败效果: {self.conversion_stats['failed_effects']}")
        log.append(f"  总转场数: {self.conversion_stats['total_transitions']}")
        log.append(f"  成功转换转场: {self.conversion_stats['converted_transitions']}")
        log.append(f"  失败转场: {self.conversion_stats['failed_transitions']}")
        
        return log
    
    def get_conversion_summary(self, jianying_project: JianyingProject) -> Dict[str, Any]:
        """获取转换摘要"""
        return {
            'project_name': jianying_project.name,
            'total_tracks': len(jianying_project.tracks),
            'total_clips': sum(len(track.clips) for track in jianying_project.tracks),
            'estimated_conversion_time': self._estimate_conversion_time(jianying_project),
            'supported_features': self._get_supported_features(),
            'conversion_mapping': {
                'effects': len(self.mapping.effect_mapping),
                'transitions': len(self.mapping.transition_mapping),
                'filters': len(self.mapping.filter_mapping)
            }
        }
    
    def _estimate_conversion_time(self, jianying_project: JianyingProject) -> float:
        """估算转换时间"""
        base_time = 3.0  # 基础时间3秒
        
        # 根据复杂度计算
        complexity_score = 0
        
        # 轨道复杂度
        complexity_score += len(jianying_project.tracks) * 2
        
        # 片段复杂度
        total_clips = sum(len(track.clips) for track in jianying_project.tracks)
        complexity_score += total_clips * 1
        
        # 效果复杂度
        total_effects = 0
        for track in jianying_project.tracks:
            for clip in track.clips:
                total_effects += len(clip.get('effects', []))
                total_effects += len(clip.get('transitions', []))
        complexity_score += total_effects * 0.5
        
        estimated_time = base_time + complexity_score * 0.1
        
        return min(estimated_time, 30.0)  # 最多30秒
    
    def _get_supported_features(self) -> Dict[str, List[str]]:
        """获取支持的功能列表"""
        return {
            'video_effects': list(self.mapping.effect_mapping.keys()),
            'transitions': list(self.mapping.transition_mapping.keys()),
            'filters': list(self.mapping.filter_mapping.keys()),
            'audio_effects': list(self.mapping.audio_effect_mapping.keys()),
            'text_styles': list(self.mapping.text_style_mapping.keys())
        }

def main():
    """主函数"""
    # 测试转换功能
    from app.core.jianying_parser import JianyingDraftParser
    from app.core.project_manager import ProjectManager
    from app.core.video_engine import VideoEngine
    
    # 创建必要的组件
    parser = JianyingDraftParser()
    video_engine = VideoEngine()
    converter = JianyingProjectConverter(video_engine)
    
    # 测试文件
    test_file = "/Users/zfkc/Desktop/VideoEpicCreator/test_data/sample_draft.draft"
    
    if os.path.exists(test_file):
        print(f"开始转换测试文件: {test_file}")
        
        try:
            # 解析剪映项目
            jianying_project = parser.parse_draft(test_file)
            
            if jianying_project:
                # 获取转换摘要
                summary = converter.get_conversion_summary(jianying_project)
                print(f"转换摘要: {summary}")
                
                # 创建基础项目
                project_manager = ProjectManager()
                base_project = Project(
                    project_id=jianying_project.project_id,
                    name=jianying_project.name,
                    project_folder=f"/tmp/test_conversion/{jianying_project.name}",
                    settings={},
                    metadata={}
                )
                
                # 执行转换
                result = converter.convert_project(jianying_project, base_project)
                
                if result.success:
                    print(f"✅ 转换成功: {result.project.name}")
                    print(f"转换统计: {result.statistics}")
                    print(f"转换日志:")
                    for log_entry in result.conversion_log:
                        print(f"  {log_entry}")
                else:
                    print(f"❌ 转换失败")
                    print(f"错误日志:")
                    for log_entry in result.conversion_log:
                        print(f"  {log_entry}")
            else:
                print("❌ 无法解析剪映草稿文件")
                
        except Exception as e:
            print(f"❌ 转换过程中出错: {e}")
    else:
        print(f"❌ 测试文件不存在: {test_file}")

if __name__ == "__main__":
    main()