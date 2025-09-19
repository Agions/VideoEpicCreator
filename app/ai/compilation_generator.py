#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI混剪风格生成器 - 智能检测视频精彩片段并生成混剪
支持多种混剪风格和智能场景分析
"""

import asyncio
import json
import time
import logging
import random
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from .ai_manager import AIManager
from .models.base_model import AIResponse

logger = logging.getLogger(__name__)


class CompilationStyle(Enum):
    """混剪风格"""
    HIGHLIGHTS = "highlights"           # 精彩片段
    EMOTIONAL = "emotional"            # 情感高潮
    ACTION = "action"                  # 动作场景
    DIALOGUE = "dialogue"              # 对话精彩
    TRANSITION = "transition"          # 转场效果
    CINEMATIC = "cinematic"            # 电影级
    FAST_PACED = "fast_paced"          # 快节奏
    SLOW_MOTION = "slow_motion"        # 慢动作
    MUSIC_SYNC = "music_sync"          # 音乐同步


class SceneType(Enum):
    """场景类型"""
    OPENING = "opening"                # 开场
    ACTION = "action"                  # 动作
    EMOTIONAL = "emotional"            # 情感
    DIALOGUE = "dialogue"              # 对话
    TRANSITION = "transition"          # 转场
    CLIMAX = "climax"                  # 高潮
    ENDING = "ending"                  # 结尾


@dataclass
class VideoSegment:
    """视频片段"""
    start_time: float
    end_time: float
    duration: float
    scene_type: SceneType
    energy_score: float
    emotion_score: float
    visual_score: float
    audio_score: float
    description: str = ""
    keywords: List[str] = field(default_factory=list)


@dataclass
class CompilationPlan:
    """混剪计划"""
    segments: List[VideoSegment]
    total_duration: float
    style: CompilationStyle
    transitions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    music_suggestions: List[str] = field(default_factory=list)
    target_platform: str = "tiktok"


@dataclass
class CompilationRequest:
    """混剪请求"""
    request_id: str
    video_path: str
    style: CompilationStyle
    target_duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[callable] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class CompilationResult:
    """混剪结果"""
    request_id: str
    success: bool
    compilation_plan: Optional[CompilationPlan] = None
    segments: List[VideoSegment] = field(default_factory=list)
    error_message: str = ""
    processing_time: float = 0.0


class AICompilationGenerator(QObject):
    """AI混剪生成器"""
    
    # 信号定义
    analysis_started = pyqtSignal(str)  # 请求ID
    analysis_progress = pyqtSignal(str, float)  # 请求ID, 进度
    analysis_completed = pyqtSignal(str, object)  # 请求ID, 结果
    analysis_failed = pyqtSignal(str, str)  # 请求ID, 错误信息
    
    def __init__(self, ai_manager: AIManager):
        super().__init__()
        self.ai_manager = ai_manager
        
        # 活动请求
        self.active_requests: Dict[str, CompilationRequest] = {}
        self.request_results: Dict[str, CompilationResult] = {}
        
        # 配置
        self.max_concurrent_requests = 3
        self.default_timeout = 60.0
        
        # 风格配置
        self.style_configs = self._load_style_configs()
        
        # 定时器
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_requests)
        self.cleanup_timer.start(60000)  # 每分钟清理一次
        
        logger.info("AI混剪生成器初始化完成")
    
    def _load_style_configs(self) -> Dict[CompilationStyle, Dict[str, Any]]:
        """加载风格配置"""
        return {
            CompilationStyle.HIGHLIGHTS: {
                "name": "精彩片段",
                "description": "提取视频中最精彩的片段",
                "segment_length": (3, 8),
                "transition_types": ["cut", "fade"],
                "energy_threshold": 0.7,
                "emotion_weight": 0.3
            },
            CompilationStyle.EMOTIONAL: {
                "name": "情感高潮",
                "description": "专注于情感丰富的片段",
                "segment_length": (5, 12),
                "transition_types": ["fade", "dissolve"],
                "energy_threshold": 0.5,
                "emotion_weight": 0.8
            },
            CompilationStyle.ACTION: {
                "name": "动作场景",
                "description": "突出动作和运动片段",
                "segment_length": (2, 6),
                "transition_types": ["cut", "wipe"],
                "energy_threshold": 0.8,
                "emotion_weight": 0.2
            },
            CompilationStyle.DIALOGUE: {
                "name": "对话精彩",
                "description": "提取精彩对话片段",
                "segment_length": (4, 10),
                "transition_types": ["cut", "fade"],
                "energy_threshold": 0.4,
                "emotion_weight": 0.6
            },
            CompilationStyle.CINEMATIC: {
                "name": "电影级",
                "description": "电影感的混剪风格",
                "segment_length": (6, 15),
                "transition_types": ["fade", "dissolve", "wipe"],
                "energy_threshold": 0.6,
                "emotion_weight": 0.5
            },
            CompilationStyle.FAST_PACED: {
                "name": "快节奏",
                "description": "快速剪辑，高能量",
                "segment_length": (1, 3),
                "transition_types": ["cut", "flash"],
                "energy_threshold": 0.9,
                "emotion_weight": 0.3
            }
        }
    
    async def generate_compilation(self,
                                 video_path: str,
                                 style: CompilationStyle,
                                 target_duration: float = 60.0,
                                 **kwargs) -> CompilationResult:
        """生成混剪"""
        request_id = f"compilation_{int(time.time() * 1000)}"
        request = CompilationRequest(
            request_id=request_id,
            video_path=video_path,
            style=style,
            target_duration=target_duration,
            parameters=kwargs
        )
        
        return await self._generate_compilation(request)
    
    async def analyze_video_segments(self,
                                   video_path: str,
                                   analysis_type: str = "comprehensive") -> List[VideoSegment]:
        """分析视频片段"""
        try:
            # 构建分析提示
            prompt = f"""
请分析以下视频并识别关键片段：

视频路径：{video_path}
分析类型：{analysis_type}

要求：
1. 识别视频中的关键场景和片段
2. 为每个片段提供时间点和描述
3. 评估每个片段的能量、情感、视觉和音频质量
4. 标注场景类型（开场、动作、情感、对话、高潮、结尾等）
5. 提供片段关键词

请返回JSON格式的分析结果，包含以下字段：
- start_time: 开始时间（秒）
- end_time: 结束时间（秒）
- duration: 持续时间（秒）
- scene_type: 场景类型
- energy_score: 能量评分（0-1）
- emotion_score: 情感评分（0-1）
- visual_score: 视觉评分（0-1）
- audio_score: 音频评分（0-1）
- description: 片段描述
- keywords: 关键词列表

分析结果：
"""
            
            response = await self.ai_manager.generate_text_async(prompt)
            
            if response.success:
                # 解析JSON结果
                try:
                    segments_data = json.loads(response.content)
                    segments = []
                    
                    for segment_data in segments_data:
                        segment = VideoSegment(
                            start_time=float(segment_data.get("start_time", 0)),
                            end_time=float(segment_data.get("end_time", 0)),
                            duration=float(segment_data.get("duration", 0)),
                            scene_type=SceneType(segment_data.get("scene_type", "action")),
                            energy_score=float(segment_data.get("energy_score", 0.5)),
                            emotion_score=float(segment_data.get("emotion_score", 0.5)),
                            visual_score=float(segment_data.get("visual_score", 0.5)),
                            audio_score=float(segment_data.get("audio_score", 0.5)),
                            description=segment_data.get("description", ""),
                            keywords=segment_data.get("keywords", [])
                        )
                        segments.append(segment)
                    
                    return segments
                    
                except json.JSONDecodeError:
                    logger.error("解析视频片段分析结果失败")
                    return []
            else:
                logger.error(f"视频片段分析失败: {response.error_message}")
                return []
                
        except Exception as e:
            logger.error(f"分析视频片段时出错: {e}")
            return []
    
    async def _generate_compilation(self, request: CompilationRequest) -> CompilationResult:
        """生成混剪"""
        start_time = time.time()
        
        try:
            # 发射开始信号
            self.analysis_started.emit(request.request_id)
            
            # 分析视频片段
            self.analysis_progress.emit(request.request_id, 0.2)
            segments = await self.analyze_video_segments(request.video_path)
            
            if not segments:
                raise Exception("无法分析视频片段")
            
            # 根据风格筛选片段
            self.analysis_progress.emit(request.request_id, 0.4)
            filtered_segments = self._filter_segments_by_style(segments, request.style)
            
            # 生成混剪计划
            self.analysis_progress.emit(request.request_id, 0.6)
            compilation_plan = self._create_compilation_plan(
                filtered_segments, 
                request.style, 
                request.target_duration
            )
            
            # 优化混剪
            self.analysis_progress.emit(request.request_id, 0.8)
            optimized_plan = self._optimize_compilation(compilation_plan, request.parameters)
            
            # 生成建议
            self.analysis_progress.emit(request.request_id, 0.9)
            suggestions = await self._generate_suggestions(optimized_plan)
            
            # 创建结果
            result = CompilationResult(
                request_id=request.request_id,
                success=True,
                compilation_plan=optimized_plan,
                segments=optimized_plan.segments,
                processing_time=time.time() - start_time
            )
            
            # 保存结果
            self.request_results[request.request_id] = result
            
            # 发射完成信号
            self.analysis_completed.emit(request.request_id, result)
            
            # 执行回调
            if request.callback:
                request.callback(result)
            
            return result
            
        except Exception as e:
            error_msg = f"混剪生成失败: {str(e)}"
            logger.error(error_msg)
            
            result = CompilationResult(
                request_id=request.request_id,
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )
            
            self.analysis_failed.emit(request.request_id, error_msg)
            return result
    
    def _filter_segments_by_style(self, segments: List[VideoSegment], style: CompilationStyle) -> List[VideoSegment]:
        """根据风格筛选片段"""
        config = self.style_configs.get(style, self.style_configs[CompilationStyle.HIGHLIGHTS])
        
        filtered_segments = []
        
        for segment in segments:
            # 计算综合评分
            energy_weight = 0.5
            emotion_weight = config.get("emotion_weight", 0.5)
            
            # 根据风格调整权重
            if style == CompilationStyle.EMOTIONAL:
                emotion_weight = 0.8
                energy_weight = 0.2
            elif style == CompilationStyle.ACTION:
                energy_weight = 0.8
                emotion_weight = 0.2
            elif style == CompilationStyle.DIALOGUE:
                # 对话片段通常能量较低，情感适中
                if segment.scene_type == SceneType.DIALOGUE:
                    energy_weight = 0.3
                    emotion_weight = 0.7
            
            # 计算综合评分
            overall_score = (
                segment.energy_score * energy_weight +
                segment.emotion_score * emotion_weight +
                segment.visual_score * 0.2 +
                segment.audio_score * 0.1
            )
            
            # 检查是否符合阈值
            if overall_score >= config.get("energy_threshold", 0.5):
                segment_copy = VideoSegment(
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.duration,
                    scene_type=segment.scene_type,
                    energy_score=segment.energy_score,
                    emotion_score=segment.emotion_score,
                    visual_score=segment.visual_score,
                    audio_score=segment.audio_score,
                    description=segment.description,
                    keywords=segment.keywords.copy()
                )
                filtered_segments.append(segment_copy)
        
        # 按评分排序
        filtered_segments.sort(key=lambda x: (
            x.energy_score * 0.4 + x.emotion_score * 0.3 + x.visual_score * 0.3
        ), reverse=True)
        
        return filtered_segments
    
    def _create_compilation_plan(self, 
                               segments: List[VideoSegment], 
                               style: CompilationStyle,
                               target_duration: float) -> CompilationPlan:
        """创建混剪计划"""
        config = self.style_configs.get(style, self.style_configs[CompilationStyle.HIGHLIGHTS])
        
        # 计算目标片段数量
        avg_segment_length = sum(config["segment_length"]) / 2
        target_segment_count = int(target_duration / avg_segment_length)
        
        # 选择片段
        selected_segments = segments[:target_segment_count]
        
        # 调整时长
        total_duration = sum(s.duration for s in selected_segments)
        if total_duration > target_duration * 1.2:
            # 如果总时长过长，移除一些片段
            while total_duration > target_duration * 1.2 and len(selected_segments) > 1:
                removed = selected_segments.pop()
                total_duration -= removed.duration
        elif total_duration < target_duration * 0.8:
            # 如果总时长过短，添加更多片段
            additional_count = min(
                int((target_duration * 0.8 - total_duration) / avg_segment_length),
                len(segments) - len(selected_segments)
            )
            selected_segments.extend(segments[len(selected_segments):len(selected_segments) + additional_count])
        
        # 排序片段（按时间顺序）
        selected_segments.sort(key=lambda x: x.start_time)
        
        # 生成转场建议
        transitions = self._generate_transitions(selected_segments, config["transition_types"])
        
        # 生成特效建议
        effects = self._generate_effects(selected_segments, style)
        
        # 生成音乐建议
        music_suggestions = self._generate_music_suggestions(style, target_duration)
        
        return CompilationPlan(
            segments=selected_segments,
            total_duration=sum(s.duration for s in selected_segments),
            style=style,
            transitions=transitions,
            effects=effects,
            music_suggestions=music_suggestions
        )
    
    def _generate_transitions(self, segments: List[VideoSegment], transition_types: List[str]) -> List[str]:
        """生成转场建议"""
        transitions = []
        
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]
            
            # 根据场景类型选择转场
            if current_segment.scene_type == SceneType.ACTION and next_segment.scene_type == SceneType.ACTION:
                transitions.append("cut")  # 动作场景之间用硬切
            elif current_segment.scene_type == SceneType.EMOTIONAL or next_segment.scene_type == SceneType.EMOTIONAL:
                transitions.append("fade")  # 情感场景用淡入淡出
            else:
                transitions.append(random.choice(transition_types))
        
        return transitions
    
    def _generate_effects(self, segments: List[VideoSegment], style: CompilationStyle) -> List[str]:
        """生成特效建议"""
        effects = []
        
        if style == CompilationStyle.CINEMATIC:
            effects.extend(["color_grading", "film_grain", "vignette"])
        elif style == CompilationStyle.FAST_PACED:
            effects.extend(["speed_ramp", "flash", "glitch"])
        elif style == CompilationStyle.EMOTIONAL:
            effects.extend(["soft_focus", "warm_filter", "slow_motion"])
        elif style == CompilationStyle.ACTION:
            effects.extend(["motion_blur", "contrast_boost", "shake"])
        
        return effects
    
    def _generate_music_suggestions(self, style: CompilationStyle, duration: float) -> List[str]:
        """生成音乐建议"""
        music_suggestions = []
        
        if style == CompilationStyle.HIGHLIGHTS:
            music_suggestions.extend(["upbeat_electronic", "epic_orchestral"])
        elif style == CompilationStyle.EMOTIONAL:
            music_suggestions.extend(["emotional_piano", "ambient_strings"])
        elif style == CompilationStyle.ACTION:
            music_suggestions.extend(["intense_drum_bass", "rock_anthem"])
        elif style == CompilationStyle.CINEMATIC:
            music_suggestions.extend(["cinematic_orchestral", "dramatic_score"])
        
        return music_suggestions
    
    def _optimize_compilation(self, plan: CompilationPlan, parameters: Dict[str, Any]) -> CompilationPlan:
        """优化混剪计划"""
        # 根据参数优化
        if parameters.get("optimize_rhythm", True):
            # 优化节奏感
            plan = self._optimize_rhythm(plan)
        
        if parameters.get("add_variety", True):
            # 增加多样性
            plan = self._add_variety(plan)
        
        if parameters.get("smooth_transitions", True):
            # 平滑转场
            plan = self._smooth_transitions(plan)
        
        return plan
    
    def _optimize_rhythm(self, plan: CompilationPlan) -> CompilationPlan:
        """优化节奏感"""
        # 确保片段长度有变化，避免单调
        if len(plan.segments) > 2:
            # 交替使用不同长度的片段
            for i, segment in enumerate(plan.segments):
                if i % 2 == 0:
                    # 偶数位置使用较短的片段
                    if segment.duration > 6:
                        segment.duration = max(3, segment.duration * 0.7)
                        segment.end_time = segment.start_time + segment.duration
                else:
                    # 奇数位置使用较长的片段
                    if segment.duration < 4:
                        segment.duration = min(8, segment.duration * 1.3)
                        segment.end_time = segment.start_time + segment.duration
        
        plan.total_duration = sum(s.duration for s in plan.segments)
        return plan
    
    def _add_variety(self, plan: CompilationPlan) -> CompilationPlan:
        """增加多样性"""
        # 确保不同场景类型的混合
        scene_types = [s.scene_type for s in plan.segments]
        
        # 如果某种场景类型过多，尝试替换
        for scene_type in set(scene_types):
            if scene_types.count(scene_type) > len(plan.segments) * 0.6:
                # 寻找可以替换的片段
                for i, segment in enumerate(plan.segments):
                    if segment.scene_type == scene_type and random.random() < 0.3:
                        # 尝试改变场景类型（这里只是示例，实际应该基于内容分析）
                        if scene_type == SceneType.ACTION:
                            segment.scene_type = SceneType.TRANSITION
                        elif scene_type == SceneType.EMOTIONAL:
                            segment.scene_type = SceneType.DIALOGUE
        
        return plan
    
    def _smooth_transitions(self, plan: CompilationPlan) -> CompilationPlan:
        """平滑转场"""
        # 确保相邻片段之间的转场合理
        for i in range(len(plan.segments) - 1):
            current = plan.segments[i]
            next_segment = plan.segments[i + 1]
            
            # 如果相邻片段场景类型差异很大，使用渐变转场
            if current.scene_type != next_segment.scene_type:
                if i < len(plan.transitions):
                    plan.transitions[i] = "fade"
        
        return plan
    
    async def _generate_suggestions(self, plan: CompilationPlan) -> Dict[str, Any]:
        """生成建议"""
        try:
            prompt = f"""
请为以下混剪计划提供专业建议：

混剪风格：{plan.style.value}
总时长：{plan.total_duration:.1f}秒
片段数量：{len(plan.segments)}

片段信息：
{chr(10).join([f"- {s.description} ({s.duration:.1f}s, {s.scene_type.value})" for s in plan.segments[:5]])}

请提供以下建议：
1. 节奏优化建议
2. 转场效果建议
3. 音乐和音效建议
4. 色彩和滤镜建议
5. 发布平台优化建议

请以JSON格式返回建议：
"""
            
            response = await self.ai_manager.generate_text_async(prompt)
            
            if response.success:
                try:
                    suggestions = json.loads(response.content)
                    return suggestions
                except json.JSONDecodeError:
                    return {"error": "无法解析建议"}
            else:
                return {"error": response.error_message}
                
        except Exception as e:
            logger.error(f"生成建议时出错: {e}")
            return {"error": str(e)}
    
    def _cleanup_old_requests(self):
        """清理旧请求"""
        current_time = time.time()
        expired_requests = [
            request_id for request_id, request in self.active_requests.items()
            if current_time - request.created_at > 3600  # 1小时过期
        ]
        
        for request_id in expired_requests:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
        
        expired_results = [
            result_id for result_id, result in self.request_results.items()
            if current_time - result.processing_time > 3600
        ]
        
        for result_id in expired_results:
            if result_id in self.request_results:
                del self.request_results[result_id]
        
        if expired_requests or expired_results:
            logger.info(f"清理了 {len(expired_requests)} 个过期请求和 {len(expired_results)} 个过期结果")
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """获取请求状态"""
        if request_id in self.active_requests:
            request = self.active_requests[request_id]
            return {
                "request_id": request_id,
                "status": "processing",
                "style": request.style.value,
                "created_at": request.created_at
            }
        elif request_id in self.request_results:
            result = self.request_results[request_id]
            return {
                "request_id": request_id,
                "status": "completed" if result.success else "failed",
                "result": result
            }
        else:
            return {
                "request_id": request_id,
                "status": "not_found"
            }
    
    def get_style_configs(self) -> Dict[str, Any]:
        """获取风格配置"""
        return {
            style.value: config for style, config in self.style_configs.items()
        }
    
    def get_available_styles(self) -> List[str]:
        """获取可用风格列表"""
        return [style.value for style in CompilationStyle]
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理AI混剪生成器资源")
        
        # 停止定时器
        self.cleanup_timer.stop()
        
        # 清理请求和结果
        self.active_requests.clear()
        self.request_results.clear()
        
        logger.info("AI混剪生成器资源清理完成")


# 工厂函数
def create_compilation_generator(ai_manager: AIManager) -> AICompilationGenerator:
    """创建AI混剪生成器"""
    return AICompilationGenerator(ai_manager)