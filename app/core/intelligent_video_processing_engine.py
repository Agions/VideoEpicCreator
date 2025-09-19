#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能视频处理引擎 - 集成AI能力的视频处理核心
结合AI场景分析、内容理解、智能剪辑和自动化视频优化
"""

import os
import sys
import json
import time
import logging
import threading
import asyncio
import subprocess
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import tempfile
import shutil
from datetime import datetime

from .optimized_video_processing_engine import OptimizedVideoProcessingEngine, ProcessingTask, ProcessingPriority
from .video_preview_engine import VideoPreviewEngine
from .hardware_acceleration import HardwareAccelerationManager, HardwareType
from .effects_engine import EffectsEngine, EffectType
from .batch_processor import BatchProcessor
from .video_codec_manager import VideoCodecManager
from .video_optimizer import VideoOptimizer

from ..ai.interfaces import (
    IAIService, AIRequest, AIResponse, AITaskType, AIPriority,
    AIRequestStatus, StreamingChunk, AIModelHealth, TokenUsage,
    IAIModelProvider, IAILoadBalancer, IAICostManager, IAIEventHandler,
    create_ai_request, create_content_analysis_request, create_scene_analysis_request
)

logger = logging.getLogger(__name__)


class AISceneType(Enum):
    """AI场景类型"""
    NATURE = "自然风景"
    URBAN = "城市景观"
    INDOOR = "室内场景"
    ACTION = "动作场景"
    DIALOGUE = "对话场景"
    EMOTIONAL = "情感场景"
    TRANSITION = "转场场景"
    MUSIC = "音乐场景"
    SPORTS = "运动场景"
    DOCUMENTARY = "纪录片风格"
    COMMERCIAL = "商业广告"
    EDUCATIONAL = "教育内容"


class AIProcessingMode(Enum):
    """AI处理模式"""
    ANALYSIS_ONLY = "analysis_only"        # 仅分析
    AUTO_EDIT = "auto_edit"              # 自动剪辑
    SMART_OPTIMIZATION = "smart_opt"     # 智能优化
    CONTENT_AWARE = "content_aware"      # 内容感知
    REAL_TIME = "real_time"              # 实时处理
    BATCH_AI = "batch_ai"                # 批量AI处理


@dataclass
class AISceneAnalysis:
    """AI场景分析结果"""
    scene_id: str
    timestamp: float
    duration: float
    scene_type: AISceneType
    confidence: float
    description: str = ""
    tags: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    action_intensity: float = 0.0
    lighting_condition: str = ""
    camera_movement: str = ""
    suggested_transitions: List[str] = field(default_factory=list)
    suggested_effects: List[str] = field(default_factory=list)


@dataclass
class AIEditDecision:
    """AI剪辑决策"""
    decision_id: str
    timestamp: float
    decision_type: str  # cut, keep, highlight, remove
    confidence: float
    reason: str = ""
    suggested_duration: float = 0.0
    suggested_transition: str = ""
    suggested_effects: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class AIProcessingConfig:
    """AI处理配置"""
    processing_mode: AIProcessingMode = AIProcessingMode.SMART_OPTIMIZATION
    enable_scene_analysis: bool = True
    enable_auto_editing: bool = True
    enable_content_optimization: bool = True
    enable_quality_enhancement: bool = True

    # AI模型参数
    scene_analysis_model: str = "default"
    content_analysis_model: str = "default"
    editing_assistant_model: str = "default"

    # 处理参数
    analysis_interval: float = 5.0  # 分析间隔（秒）
    min_scene_duration: float = 2.0  # 最小场景时长
    confidence_threshold: float = 0.7  # 置信度阈值

    # 输出参数
    generate_edit_suggestions: bool = True
    generate_scene_markers: bool = True
    generate_quality_report: bool = True

    # 高级参数
    custom_prompts: Dict[str, str] = field(default_factory=dict)
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    target_audience: str = "general"
    content_category: str = "general"


@dataclass
class AIProcessingTask:
    """AI处理任务"""
    task_id: str
    input_path: str
    output_path: str
    config: AIProcessingConfig
    priority: ProcessingPriority = ProcessingPriority.NORMAL

    # 回调函数
    progress_callback: Optional[Callable] = None
    scene_analysis_callback: Optional[Callable] = None
    edit_decision_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None

    # 元数据
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "pending"

    # 处理结果
    scene_analysis: List[AISceneAnalysis] = field(default_factory=list)
    edit_decisions: List[AIEditDecision] = field(default_factory=list)
    quality_report: Dict[str, Any] = field(default_factory=dict)


class IntelligentVideoProcessingEngine:
    """智能视频处理引擎"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

        # 初始化基础视频处理引擎
        self.video_engine = OptimizedVideoProcessingEngine(ffmpeg_path, ffprobe_path)

        # 创建预览配置
        from app.core.video_preview_engine import PreviewConfig
        preview_config = PreviewConfig()
        preview_config.ffmpeg_path = ffmpeg_path
        preview_config.ffprobe_path = ffprobe_path
        self.preview_engine = VideoPreviewEngine(preview_config)

        # AI服务
        self.ai_service: Optional[IAIService] = None
        self.ai_available = False

        # 处理状态
        self.is_processing = False
        self.processing_cancel_flag = False

        # 任务管理
        self.ai_task_queue = PriorityQueue()
        self.active_ai_tasks: Dict[str, AIProcessingTask] = {}
        self.task_lock = threading.Lock()

        # 线程池
        self.ai_thread_pool = ThreadPoolExecutor(max_workers=3)
        self.analysis_thread_pool = ThreadPoolExecutor(max_workers=2)

        # 缓存
        self.scene_analysis_cache: Dict[str, List[AISceneAnalysis]] = {}
        self.edit_decision_cache: Dict[str, List[AIEditDecision]] = {}

        # 统计信息
        self.stats = {
            "total_ai_processed": 0,
            "successful_ai_processes": 0,
            "failed_ai_processes": 0,
            "total_ai_time": 0.0,
            "scenes_analyzed": 0,
            "auto_edits_suggested": 0
        }

        # 启动工作线程
        self._start_worker_threads()

        logger.info("智能视频处理引擎初始化完成")

    def set_ai_service(self, ai_service: IAIService):
        """设置AI服务"""
        self.ai_service = ai_service
        self.ai_available = True
        logger.info("AI服务已连接")

    def _start_worker_threads(self):
        """启动工作线程"""
        # AI任务分发线程
        self.ai_task_dispatcher = threading.Thread(target=self._ai_task_dispatcher_loop, daemon=True)
        self.ai_task_dispatcher.start()

        # 场景分析线程
        self.scene_analyzer = threading.Thread(target=self._scene_analysis_loop, daemon=True)
        self.scene_analyzer.start()

        logger.info("AI工作线程已启动")

    def _ai_task_dispatcher_loop(self):
        """AI任务分发循环"""
        while True:
            try:
                if not self.ai_task_queue.empty() and self.ai_available:
                    # 获取任务
                    _, task = self.ai_task_queue.get()

                    # 分配AI线程处理
                    self.ai_thread_pool.submit(self._process_ai_task, task)
                else:
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"AI任务分发错误: {e}")
                time.sleep(5)

    def _scene_analysis_loop(self):
        """场景分析循环"""
        while True:
            try:
                # 处理待分析的视频
                self._process_pending_analysis()
                time.sleep(1)

            except Exception as e:
                logger.error(f"场景分析错误: {e}")
                time.sleep(10)

    def _process_pending_analysis(self):
        """处理待分析的视频"""
        # 这里可以添加需要自动分析的逻辑
        pass

    def add_ai_processing_task(self, task: AIProcessingTask) -> bool:
        """添加AI处理任务"""
        try:
            if not self.ai_available:
                logger.warning("AI服务不可用，无法处理AI任务")
                return False

            with self.task_lock:
                self.active_ai_tasks[task.task_id] = task

            self.ai_task_queue.put((task.priority.value, task))

            logger.info(f"AI处理任务已添加: {task.task_id}")
            return True

        except Exception as e:
            logger.error(f"添加AI处理任务失败: {e}")
            return False

    def _process_ai_task(self, task: AIProcessingTask):
        """处理AI任务"""
        try:
            task.started_at = time.time()
            task.status = "processing"

            # 分析视频
            if task.config.enable_scene_analysis:
                scene_analysis = self._analyze_video_scenes(task.input_path, task.config)
                task.scene_analysis = scene_analysis

                # 调用回调
                if task.scene_analysis_callback:
                    task.scene_analysis_callback(scene_analysis)

            # 生成剪辑建议
            if task.config.enable_auto_editing:
                edit_decisions = self._generate_edit_suggestions(task.scene_analysis, task.config)
                task.edit_decisions = edit_decisions

                # 调用回调
                if task.edit_decision_callback:
                    task.edit_decision_callback(edit_decisions)

            # 应用智能优化
            if task.config.enable_content_optimization:
                self._apply_intelligent_optimization(task)

            # 生成质量报告
            if task.config.generate_quality_report:
                task.quality_report = self._generate_quality_report(task)

            # 执行实际视频处理
            self._execute_video_processing(task)

            task.completed_at = time.time()
            task.status = "completed"

            # 记录统计
            self._record_ai_processing_success(task)

            # 调用完成回调
            if task.completion_callback:
                task.completion_callback(task)

            logger.info(f"AI处理任务完成: {task.task_id}")

        except Exception as e:
            task.status = "failed"
            task.completed_at = time.time()

            logger.error(f"AI处理任务失败: {task.task_id}, 错误: {e}")

            # 调用错误回调
            if task.error_callback:
                task.error_callback(e)

            # 记录失败
            self._record_ai_processing_failure()

        finally:
            with self.task_lock:
                if task.task_id in self.active_ai_tasks:
                    del self.active_ai_tasks[task.task_id]

    def _analyze_video_scenes(self, video_path: str, config: AIProcessingConfig) -> List[AISceneAnalysis]:
        """分析视频场景"""
        try:
            # 获取视频信息
            video_info = self.video_engine.get_video_info(video_path)
            duration = video_info.duration

            scene_analysis = []
            current_time = 0.0

            while current_time < duration:
                try:
                    # 提取当前时间段的帧
                    frames = self._extract_frames_for_analysis(video_path, current_time, config.analysis_interval)

                    # 使用AI分析场景
                    scene_info = self._ai_analyze_scene(frames, current_time, config)

                    if scene_info:
                        scene_analysis.append(scene_info)
                        self.stats["scenes_analyzed"] += 1

                        # 调用进度回调
                        progress = (current_time / duration) * 100
                        self._notify_progress(progress, f"分析场景: {scene_info.scene_type.value}")

                    current_time += config.analysis_interval

                except Exception as e:
                    logger.error(f"场景分析失败 at {current_time}s: {e}")
                    current_time += config.analysis_interval

            # 缓存结果
            self.scene_analysis_cache[video_path] = scene_analysis

            return scene_analysis

        except Exception as e:
            logger.error(f"视频场景分析失败: {e}")
            return []

    def _extract_frames_for_analysis(self, video_path: str, start_time: float, duration: float) -> List[np.ndarray]:
        """提取用于分析的帧"""
        try:
            frames = []

            # 使用OpenCV提取帧
            cap = cv2.VideoCapture(video_path)

            # 设置起始时间
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)

            # 提取关键帧
            frame_count = 0
            while frame_count < 5:  # 每个时间段提取5帧
                ret, frame = cap.read()
                if not ret:
                    break

                frames.append(frame)
                frame_count += 1

                # 跳过一些帧
                for _ in range(10):
                    cap.read()

            cap.release()
            return frames

        except Exception as e:
            logger.error(f"提取分析帧失败: {e}")
            return []

    def _ai_analyze_scene(self, frames: List[np.ndarray], timestamp: float, config: AIProcessingConfig) -> Optional[AISceneAnalysis]:
        """使用AI分析场景"""
        try:
            if not self.ai_service or not frames:
                return None

            # 构建分析请求
            analysis_prompt = self._build_scene_analysis_prompt(frames, config)

            ai_request = create_ai_request(
                task_type=AITaskType.SCENE_ANALYSIS,
                content=analysis_prompt,
                priority=AIPriority.NORMAL,
                context={"timestamp": timestamp, "config": config.__dict__}
            )

            # 发送AI请求
            response = self.ai_service.submit_request(ai_request)

            # 解析AI响应
            return self._parse_scene_analysis_response(response, timestamp)

        except Exception as e:
            logger.error(f"AI场景分析失败: {e}")
            return None

    def _build_scene_analysis_prompt(self, frames: List[np.ndarray], config: AIProcessingConfig) -> str:
        """构建场景分析提示"""
        # 将帧转换为base64编码的图片描述
        frame_descriptions = []
        for i, frame in enumerate(frames[:3]):  # 最多使用3帧
            # 这里可以添加图像描述生成逻辑
            frame_descriptions.append(f"Frame {i+1}: RGB image {frame.shape}")

        prompt = f"""
        分析以下视频帧，提供详细的场景分析：

        帧信息：
        {chr(10).join(frame_descriptions)}

        请提供：
        1. 场景类型（自然风景、城市景观、室内场景等）
        2. 场景描述
        3. 检测到的物体
        4. 情感分析
        5. 动作强度（0-1）
        6. 光线条件
        7. 摄像机运动
        8. 质量评分（0-1）
        9. 建议的转场效果
        10. 建议的特效

        以JSON格式返回分析结果。
        """

        return prompt

    def _parse_scene_analysis_response(self, response: str, timestamp: float) -> AISceneAnalysis:
        """解析场景分析响应"""
        try:
            # 这里应该解析AI返回的JSON响应
            # 简化实现，返回默认分析结果

            return AISceneAnalysis(
                scene_id=f"scene_{timestamp:.1f}",
                timestamp=timestamp,
                duration=5.0,
                scene_type=AISceneType.INDOOR,
                confidence=0.8,
                description="分析结果",
                tags=["室内", "对话"],
                objects=["人物", "家具"],
                emotions=["平静"],
                quality_score=0.8,
                action_intensity=0.2,
                lighting_condition="良好",
                camera_movement="固定",
                suggested_transitions=["淡入淡出"],
                suggested_effects=["色彩增强"]
            )

        except Exception as e:
            logger.error(f"解析场景分析响应失败: {e}")
            return AISceneAnalysis(
                scene_id=f"scene_{timestamp:.1f}",
                timestamp=timestamp,
                duration=5.0,
                scene_type=AISceneType.INDOOR,
                confidence=0.5,
                description="分析失败"
            )

    def _generate_edit_suggestions(self, scene_analysis: List[AISceneAnalysis],
                                config: AIProcessingConfig) -> List[AIEditDecision]:
        """生成剪辑建议"""
        try:
            edit_decisions = []

            for i, scene in enumerate(scene_analysis):
                # 基于场景分析生成剪辑决策
                decision = self._create_edit_decision(scene, i, len(scene_analysis))
                if decision:
                    edit_decisions.append(decision)

            self.stats["auto_edits_suggested"] += len(edit_decisions)
            return edit_decisions

        except Exception as e:
            logger.error(f"生成剪辑建议失败: {e}")
            return []

    def _create_edit_decision(self, scene: AISceneAnalysis, index: int, total_scenes: int) -> Optional[AIEditDecision]:
        """创建剪辑决策"""
        try:
            # 基于场景质量、动作强度等因素做决策
            if scene.quality_score > 0.7 and scene.action_intensity > 0.5:
                decision_type = "highlight"
                reason = "高质量动作场景"
            elif scene.quality_score < 0.4:
                decision_type = "remove"
                reason = "质量较低"
            else:
                decision_type = "keep"
                reason = "常规场景"

            return AIEditDecision(
                decision_id=f"edit_{scene.scene_id}",
                timestamp=scene.timestamp,
                decision_type=decision_type,
                confidence=min(scene.confidence, 0.9),
                reason=reason,
                suggested_duration=scene.duration,
                suggested_transition=scene.suggested_transitions[0] if scene.suggested_transitions else "",
                suggested_effects=scene.suggested_effects,
                priority=2 if decision_type == "highlight" else 1
            )

        except Exception as e:
            logger.error(f"创建剪辑决策失败: {e}")
            return None

    def _apply_intelligent_optimization(self, task: AIProcessingTask):
        """应用智能优化"""
        try:
            # 基于场景分析结果应用优化
            if not task.scene_analysis:
                return

            # 分析整体视频特征
            avg_quality = sum(scene.quality_score for scene in task.scene_analysis) / len(task.scene_analysis)
            dominant_scene_type = self._get_dominant_scene_type(task.scene_analysis)

            # 应用相应的优化策略
            optimization_settings = self._get_optimization_settings(avg_quality, dominant_scene_type)

            # 更新视频处理配置
            self._update_processing_config(task, optimization_settings)

        except Exception as e:
            logger.error(f"应用智能优化失败: {e}")

    def _get_dominant_scene_type(self, scene_analysis: List[AISceneAnalysis]) -> AISceneType:
        """获取主导场景类型"""
        scene_counts = {}
        for scene in scene_analysis:
            scene_type = scene.scene_type
            scene_counts[scene_type] = scene_counts.get(scene_type, 0) + 1

        return max(scene_counts, key=scene_counts.get) if scene_counts else AISceneType.INDOOR

    def _get_optimization_settings(self, avg_quality: float, scene_type: AISceneType) -> Dict[str, Any]:
        """获取优化设置"""
        settings = {
            "brightness": 0.0,
            "contrast": 0.0,
            "saturation": 0.0,
            "sharpness": 0.0,
            "noise_reduction": 0.0
        }

        # 基于质量评分调整
        if avg_quality < 0.5:
            settings["brightness"] = 0.1
            settings["contrast"] = 0.15
            settings["sharpness"] = 0.2
            settings["noise_reduction"] = 0.3
        elif avg_quality < 0.7:
            settings["contrast"] = 0.1
            settings["sharpness"] = 0.1

        # 基于场景类型调整
        if scene_type == AISceneType.NATURE:
            settings["saturation"] = 0.2
        elif scene_type == AISceneType.ACTION:
            settings["sharpness"] = 0.3
            settings["contrast"] = 0.2

        return settings

    def _update_processing_config(self, task: AIProcessingTask, settings: Dict[str, Any]):
        """更新处理配置"""
        # 这里可以更新视频处理引擎的配置
        pass

    def _generate_quality_report(self, task: AIProcessingTask) -> Dict[str, Any]:
        """生成质量报告"""
        try:
            if not task.scene_analysis:
                return {"error": "No scene analysis available"}

            # 计算质量指标
            avg_quality = sum(scene.quality_score for scene in task.scene_analysis) / len(task.scene_analysis)
            quality_variance = sum((scene.quality_score - avg_quality) ** 2 for scene in task.scene_analysis) / len(task.scene_analysis)

            # 分析场景分布
            scene_types = {}
            for scene in task.scene_analysis:
                scene_type = scene.scene_type.value
                scene_types[scene_type] = scene_types.get(scene_type, 0) + 1

            report = {
                "overall_quality": avg_quality,
                "quality_variance": quality_variance,
                "quality_stability": 1.0 - min(quality_variance * 2, 1.0),
                "scene_count": len(task.scene_analysis),
                "scene_distribution": scene_types,
                "total_duration": sum(scene.duration for scene in task.scene_analysis),
                "analysis_timestamp": datetime.now().isoformat(),
                "recommendations": self._generate_quality_recommendations(avg_quality, quality_variance)
            }

            return report

        except Exception as e:
            logger.error(f"生成质量报告失败: {e}")
            return {"error": str(e)}

    def _generate_quality_recommendations(self, avg_quality: float, variance: float) -> List[str]:
        """生成质量建议"""
        recommendations = []

        if avg_quality < 0.5:
            recommendations.append("建议进行色彩校正和亮度调整")
            recommendations.append("考虑应用降噪处理")

        if variance > 0.3:
            recommendations.append("视频质量不稳定，建议统一处理风格")

        if avg_quality < 0.7:
            recommendations.append("建议应用锐化增强细节")

        return recommendations

    def _execute_video_processing(self, task: AIProcessingTask):
        """执行视频处理"""
        try:
            # 构建视频处理任务
            video_task = ProcessingTask(
                task_id=task.task_id + "_video",
                task_type="ai_enhanced_process",
                input_path=task.input_path,
                output_path=task.output_path,
                config=task.config,
                priority=task.priority
            )

            # 添加到视频处理队列
            self.video_engine.add_task(video_task)

        except Exception as e:
            logger.error(f"执行视频处理失败: {e}")
            raise

    def _notify_progress(self, progress: float, message: str):
        """通知进度更新"""
        # 这里可以实现进度通知机制
        logger.info(f"AI处理进度: {progress:.1f}% - {message}")

    def _record_ai_processing_success(self, task: AIProcessingTask):
        """记录AI处理成功"""
        self.stats["total_ai_processed"] += 1
        self.stats["successful_ai_processes"] += 1

        if task.started_at and task.completed_at:
            processing_time = task.completed_at - task.started_at
            self.stats["total_ai_time"] += processing_time

    def _record_ai_processing_failure(self):
        """记录AI处理失败"""
        self.stats["total_ai_processed"] += 1
        self.stats["failed_ai_processes"] += 1

    def get_ai_processing_status(self, task_id: str) -> Optional[str]:
        """获取AI处理状态"""
        with self.task_lock:
            if task_id in self.active_ai_tasks:
                return self.active_ai_tasks[task_id].status
        return None

    def get_scene_analysis(self, video_path: str) -> List[AISceneAnalysis]:
        """获取场景分析结果"""
        return self.scene_analysis_cache.get(video_path, [])

    def get_edit_suggestions(self, video_path: str) -> List[AIEditDecision]:
        """获取剪辑建议"""
        return self.edit_decision_cache.get(video_path, [])

    def get_ai_stats(self) -> Dict[str, Any]:
        """获取AI处理统计"""
        stats = self.stats.copy()

        # 计算成功率
        total = stats["total_ai_processed"]
        if total > 0:
            stats["success_rate"] = stats["successful_ai_processes"] / total
        else:
            stats["success_rate"] = 0.0

        # 计算平均处理时间
        if stats["successful_ai_processes"] > 0:
            stats["average_ai_time"] = stats["total_ai_time"] / stats["successful_ai_processes"]
        else:
            stats["average_ai_time"] = 0.0

        return stats

    def cancel_ai_processing(self, task_id: str) -> bool:
        """取消AI处理"""
        try:
            with self.task_lock:
                if task_id in self.active_ai_tasks:
                    task = self.active_ai_tasks[task_id]
                    task.status = "cancelled"
                    del self.active_ai_tasks[task_id]
                    logger.info(f"AI处理任务已取消: {task_id}")
                    return True
            return False

        except Exception as e:
            logger.error(f"取消AI处理失败: {e}")
            return False

    def preview_ai_processing(self, video_path: str, config: AIProcessingConfig) -> Dict[str, Any]:
        """预览AI处理效果"""
        try:
            # 快速分析视频样本
            sample_analysis = self._quick_scene_analysis(video_path, config)

            # 生成处理预览
            preview_result = {
                "estimated_processing_time": self._estimate_processing_time(video_path, config),
                "scene_count": len(sample_analysis),
                "dominant_scene_type": self._get_dominant_scene_type(sample_analysis),
                "estimated_quality_improvement": self._estimate_quality_improvement(sample_analysis),
                "suggested_edit_points": len([s for s in sample_analysis if s.quality_score > 0.7]),
                "processing_mode": config.processing_mode.value
            }

            return preview_result

        except Exception as e:
            logger.error(f"AI处理预览失败: {e}")
            return {"error": str(e)}

    def _quick_scene_analysis(self, video_path: str, config: AIProcessingConfig) -> List[AISceneAnalysis]:
        """快速场景分析"""
        try:
            # 获取视频信息
            video_info = self.video_engine.get_video_info(video_path)
            duration = video_info.duration

            # 采样分析
            sample_points = [0.0, duration * 0.25, duration * 0.5, duration * 0.75, duration * 0.9]
            sample_analysis = []

            for timestamp in sample_points:
                frames = self._extract_frames_for_analysis(video_path, timestamp, 1.0)
                if frames:
                    scene_info = self._ai_analyze_scene(frames, timestamp, config)
                    if scene_info:
                        sample_analysis.append(scene_info)

            return sample_analysis

        except Exception as e:
            logger.error(f"快速场景分析失败: {e}")
            return []

    def _estimate_processing_time(self, video_path: str, config: AIProcessingConfig) -> float:
        """估算处理时间"""
        try:
            video_info = self.video_engine.get_video_info(video_path)
            base_time = video_info.duration * 0.5  # 基础处理时间

            # 基于配置调整
            if config.enable_scene_analysis:
                base_time *= 1.5
            if config.enable_auto_editing:
                base_time *= 1.3
            if config.enable_content_optimization:
                base_time *= 1.2

            return base_time

        except Exception as e:
            logger.error(f"估算处理时间失败: {e}")
            return 0.0

    def _estimate_quality_improvement(self, scene_analysis: List[AISceneAnalysis]) -> float:
        """估算质量改进"""
        if not scene_analysis:
            return 0.0

        current_quality = sum(scene.quality_score for scene in scene_analysis) / len(scene_analysis)
        potential_quality = min(current_quality * 1.2, 1.0)  # 假设最多改进20%

        return potential_quality - current_quality

    def batch_process_ai_tasks(self, tasks: List[AIProcessingTask]):
        """批量处理AI任务"""
        for task in tasks:
            self.add_ai_processing_task(task)

        logger.info(f"批量AI处理任务已添加: {len(tasks)} 个任务")

    def cleanup(self):
        """清理资源"""
        logger.info("清理智能视频处理引擎资源")

        # 取消所有处理
        self.processing_cancel_flag = True

        # 清理线程池
        self.ai_thread_pool.shutdown(wait=True)
        self.analysis_thread_pool.shutdown(wait=True)

        # 清理视频引擎
        self.video_engine.cleanup()
        self.preview_engine.cleanup()

        # 清理缓存
        self.scene_analysis_cache.clear()
        self.edit_decision_cache.clear()

        logger.info("智能视频处理引擎资源清理完成")


# 工厂函数
def create_intelligent_video_processing_engine(ffmpeg_path: str = "ffmpeg",
                                             ffprobe_path: str = "ffprobe") -> IntelligentVideoProcessingEngine:
    """创建智能视频处理引擎"""
    return IntelligentVideoProcessingEngine(ffmpeg_path, ffprobe_path)


# 便利函数
def create_ai_processing_task(input_path: str, output_path: str,
                            config: AIProcessingConfig, **kwargs) -> AIProcessingTask:
    """创建AI处理任务"""
    import uuid

    return AIProcessingTask(
        task_id=str(uuid.uuid4()),
        input_path=input_path,
        output_path=output_path,
        config=config,
        **kwargs
    )


if __name__ == "__main__":
    # 测试代码
    engine = create_intelligent_video_processing_engine()

    # 测试配置
    config = AIProcessingConfig(
        processing_mode=AIProcessingMode.SMART_OPTIMIZATION,
        enable_scene_analysis=True,
        enable_auto_editing=True,
        enable_content_optimization=True
    )

    # 创建测试任务
    test_video = "test_video.mp4"
    if os.path.exists(test_video):
        task = create_ai_processing_task(
            input_path=test_video,
            output_path="output_video.mp4",
            config=config
        )

        # 预览处理
        preview = engine.preview_ai_processing(test_video, config)
        print(f"AI处理预览: {preview}")

        # 添加任务
        engine.add_ai_processing_task(task)

        # 等待处理
        time.sleep(10)

        # 获取统计
        stats = engine.get_ai_stats()
        print(f"AI处理统计: {stats}")

    engine.cleanup()