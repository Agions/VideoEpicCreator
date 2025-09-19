#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
特效系统核心模块
提供统一的特效管理、应用和渲染功能
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import numpy as np
from pathlib import Path

from ..ai.interfaces import IAIService
from ..core.video_processing_engine import OptimizedVideoProcessingEngine
from ..core.hardware_acceleration import HardwareAcceleration

logger = logging.getLogger(__name__)


class EffectType(Enum):
    """特效类型枚举"""
    FILTER = "filter"           # 滤镜效果
    TRANSITION = "transition"   # 转场效果
    ANIMATION = "animation"     # 动画效果
    TEXT = "text"              # 文字效果
    AUDIO = "audio"            # 音频效果
    COLOR = "color"            # 调色效果
    PARTICLE = "particle"      # 粒子效果
    MOTION = "motion"          # 运动效果


class EffectCategory(Enum):
    """特效分类枚举"""
    BASIC = "basic"           # 基础特效
    PROFESSIONAL = "professional"  # 专业特效
    AI_POWERED = "ai_powered"      # AI驱动特效
    TEMPLATE = "template"          # 模板特效
    CUSTOM = "custom"             # 自定义特效


class EffectPriority(Enum):
    """特效优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EffectParameter:
    """特效参数定义"""
    name: str
    display_name: str
    param_type: str  # "float", "int", "bool", "string", "color"
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    step: Optional[Any] = None
    description: str = ""
    required: bool = False


@dataclass
class EffectPreset:
    """特效预设"""
    name: str
    parameters: Dict[str, Any]
    description: str = ""
    thumbnail_path: Optional[str] = None


@dataclass
class EffectMetadata:
    """特效元数据"""
    id: str
    name: str
    description: str
    author: str = "CineAI Studio"
    version: str = "1.0.0"
    effect_type: EffectType = EffectType.FILTER
    category: EffectCategory = EffectCategory.BASIC
    priority: EffectPriority = EffectPriority.MEDIUM
    parameters: List[EffectParameter] = field(default_factory=list)
    presets: List[EffectPreset] = field(default_factory=list)
    thumbnail_path: Optional[str] = None
    preview_path: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    hardware_accelerated: bool = True
    gpu_required: bool = False
    processing_time_estimate: float = 0.0  # 预估处理时间（秒）
    ai_enhanced: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class EffectInstance:
    """特效实例"""
    effect_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    enabled: bool = True
    opacity: float = 1.0
    blend_mode: str = "normal"
    mask_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseEffect(ABC):
    """特效基类"""

    def __init__(self, metadata: EffectMetadata):
        self.metadata = metadata
        self.parameters = {}
        self.initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """初始化特效"""
        pass

    @abstractmethod
    def apply(self, frame: np.ndarray, time: float) -> np.ndarray:
        """应用特效到帧"""
        pass

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        pass

    def set_parameter(self, name: str, value: Any) -> bool:
        """设置参数值"""
        if name in self.parameters:
            # 验证参数值
            for param_def in self.metadata.parameters:
                if param_def.name == name:
                    if self._validate_parameter_value(param_def, value):
                        self.parameters[name] = value
                        return True
                    break
        return False

    def _validate_parameter_value(self, param_def: EffectParameter, value: Any) -> bool:
        """验证参数值"""
        try:
            if param_def.param_type == "float":
                value = float(value)
                if param_def.min_value is not None and value < param_def.min_value:
                    return False
                if param_def.max_value is not None and value > param_def.max_value:
                    return False
            elif param_def.param_type == "int":
                value = int(value)
                if param_def.min_value is not None and value < param_def.min_value:
                    return False
                if param_def.max_value is not None and value > param_def.max_value:
                    return False
            elif param_def.param_type == "bool":
                return isinstance(value, bool)
            elif param_def.param_type == "color":
                # 验证颜色格式 (RGB, HEX等)
                return True

            return True
        except (ValueError, TypeError):
            return False

    def get_parameter(self, name: str) -> Any:
        """获取参数值"""
        return self.parameters.get(name)

    def get_parameters_info(self) -> List[EffectParameter]:
        """获取参数信息"""
        return self.metadata.parameters


class FilterEffect(BaseEffect):
    """滤镜效果基类"""

    def apply_filter(self, frame: np.ndarray, filter_params: Dict[str, Any]) -> np.ndarray:
        """应用滤镜"""
        # 基础滤镜实现
        return frame


class TransitionEffect(BaseEffect):
    """转场效果基类"""

    def __init__(self, metadata: EffectMetadata):
        super().__init__(metadata)
        self.from_frame = None
        self.to_frame = None

    def set_frames(self, from_frame: np.ndarray, to_frame: np.ndarray):
        """设置转场帧"""
        self.from_frame = from_frame
        self.to_frame = to_frame

    def apply_transition(self, progress: float) -> np.ndarray:
        """应用转场效果"""
        if self.from_frame is None or self.to_frame is None:
            raise ValueError("转场帧未设置")

        # 基础转场实现（线性混合）
        alpha = progress
        result = (self.from_frame * (1 - alpha) + self.to_frame * alpha).astype(np.uint8)
        return result


class AnimationEffect(BaseEffect):
    """动画效果基类"""

    def apply_animation(self, frame: np.ndarray, time: float, duration: float) -> np.ndarray:
        """应用动画效果"""
        # 基础动画实现
        return frame


class AIEffect(BaseEffect):
    """AI驱动特效基类"""

    def __init__(self, metadata: EffectMetadata, ai_service: Optional[IAIService] = None):
        super().__init__(metadata)
        self.ai_service = ai_service
        self.ai_cache = {}

    async def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """AI分析帧内容"""
        if not self.ai_service:
            return {}

        # 生成帧的唯一标识
        frame_hash = hash(frame.tobytes())

        # 检查缓存
        if frame_hash in self.ai_cache:
            return self.ai_cache[frame_hash]

        # AI分析
        try:
            # 这里需要实现具体的AI分析逻辑
            analysis_result = {}
            self.ai_cache[frame_hash] = analysis_result
            return analysis_result
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return {}


class EffectsManager:
    """特效管理器"""

    def __init__(self, video_engine: OptimizedVideoProcessingEngine,
                 ai_service: Optional[IAIService] = None):
        self.video_engine = video_engine
        self.ai_service = ai_service
        self.effects: Dict[str, BaseEffect] = {}
        self.effect_metadata: Dict[str, EffectMetadata] = {}
        self.effect_instances: List[EffectInstance] = []
        self.templates: Dict[str, List[EffectInstance]] = {}

        self._load_builtin_effects()
        self._load_effect_templates()

    def _load_builtin_effects(self):
        """加载内置特效"""
        # 这里应该加载所有内置特效
        logger.info("加载内置特效...")

    def _load_effect_templates(self):
        """加载特效模板"""
        # 这里应该加载特效模板
        logger.info("加载特效模板...")

    def register_effect(self, effect_class: type, metadata: EffectMetadata) -> bool:
        """注册特效"""
        try:
            effect_instance = effect_class(metadata)
            if effect_instance.initialize():
                self.effects[metadata.id] = effect_instance
                self.effect_metadata[metadata.id] = metadata
                logger.info(f"特效注册成功: {metadata.name}")
                return True
            else:
                logger.error(f"特效初始化失败: {metadata.name}")
                return False
        except Exception as e:
            logger.error(f"特效注册失败 {metadata.name}: {e}")
            return False

    def get_effect_metadata(self, effect_id: str) -> Optional[EffectMetadata]:
        """获取特效元数据"""
        return self.effect_metadata.get(effect_id)

    def list_effects(self, effect_type: Optional[EffectType] = None,
                    category: Optional[EffectCategory] = None) -> List[EffectMetadata]:
        """列出特效"""
        effects = list(self.effect_metadata.values())

        if effect_type:
            effects = [e for e in effects if e.effect_type == effect_type]

        if category:
            effects = [e for e in effects if e.category == category]

        return sorted(effects, key=lambda x: x.priority.value, reverse=True)

    def create_effect_instance(self, effect_id: str, **parameters) -> Optional[EffectInstance]:
        """创建特效实例"""
        if effect_id not in self.effects:
            logger.error(f"特效不存在: {effect_id}")
            return None

        effect = self.effects[effect_id]

        # 验证参数
        if not effect.validate_parameters(parameters):
            logger.error(f"参数验证失败: {effect_id}")
            return None

        # 创建实例
        instance = EffectInstance(
            effect_id=effect_id,
            parameters=parameters
        )

        # 设置参数到特效对象
        for name, value in parameters.items():
            effect.set_parameter(name, value)

        self.effect_instances.append(instance)
        return instance

    def apply_effects_to_frame(self, frame: np.ndarray, time: float) -> np.ndarray:
        """应用所有特效到帧"""
        result_frame = frame.copy()

        # 按优先级排序特效实例
        active_instances = [
            inst for inst in self.effect_instances
            if inst.enabled and inst.start_time <= time <= inst.end_time
        ]

        # 按优先级排序
        active_instances.sort(
            key=lambda x: self.effect_metadata.get(x.effect_id, EffectPriority.MEDIUM).priority.value,
            reverse=True
        )

        # 应用特效
        for instance in active_instances:
            try:
                effect = self.effects.get(instance.effect_id)
                if effect:
                    # 临时设置特效参数
                    old_params = effect.parameters.copy()
                    effect.parameters = instance.parameters.copy()

                    # 应用特效
                    result_frame = effect.apply(result_frame, time)

                    # 恢复原参数
                    effect.parameters = old_params

                    # 应用透明度和混合模式
                    if instance.opacity < 1.0:
                        alpha = instance.opacity
                        result_frame = (frame * (1 - alpha) + result_frame * alpha).astype(np.uint8)

            except Exception as e:
                logger.error(f"应用特效失败 {instance.effect_id}: {e}")

        return result_frame

    def remove_effect_instance(self, instance: EffectInstance):
        """移除特效实例"""
        if instance in self.effect_instances:
            self.effect_instances.remove(instance)

    def clear_all_effects(self):
        """清除所有特效实例"""
        self.effect_instances.clear()

    def create_effect_template(self, name: str, instances: List[EffectInstance]) -> bool:
        """创建特效模板"""
        try:
            self.templates[name] = instances.copy()
            logger.info(f"特效模板创建成功: {name}")
            return True
        except Exception as e:
            logger.error(f"创建特效模板失败: {e}")
            return False

    def load_effect_template(self, name: str) -> Optional[List[EffectInstance]]:
        """加载特效模板"""
        return self.templates.get(name)

    def save_effects_config(self, file_path: str) -> bool:
        """保存特效配置"""
        try:
            config = {
                "instances": [
                    {
                        "effect_id": inst.effect_id,
                        "parameters": inst.parameters,
                        "start_time": inst.start_time,
                        "end_time": inst.end_time,
                        "enabled": inst.enabled,
                        "opacity": inst.opacity,
                        "blend_mode": inst.blend_mode,
                        "mask_path": inst.mask_path,
                        "metadata": inst.metadata
                    }
                    for inst in self.effect_instances
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"特效配置保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存特效配置失败: {e}")
            return False

    def load_effects_config(self, file_path: str) -> bool:
        """加载特效配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.effect_instances.clear()

            for inst_data in config.get("instances", []):
                instance = EffectInstance(
                    effect_id=inst_data["effect_id"],
                    parameters=inst_data.get("parameters", {}),
                    start_time=inst_data.get("start_time", 0.0),
                    end_time=inst_data.get("end_time", 0.0),
                    enabled=inst_data.get("enabled", True),
                    opacity=inst_data.get("opacity", 1.0),
                    blend_mode=inst_data.get("blend_mode", "normal"),
                    mask_path=inst_data.get("mask_path"),
                    metadata=inst_data.get("metadata", {})
                )
                self.effect_instances.append(instance)

            logger.info(f"特效配置加载成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"加载特效配置失败: {e}")
            return False

    def get_effect_suggestions(self, frame: np.ndarray,
                              content_type: str = "general") -> List[EffectMetadata]:
        """获取AI特效建议"""
        if not self.ai_service:
            return []

        try:
            # AI分析帧内容
            analysis = await self.ai_service.analyze_image(frame)

            # 基于分析结果推荐特效
            suggestions = []

            # 这里应该根据AI分析结果推荐合适的特效
            # 例如：检测到人脸推荐美容特效，检测到风景推荐调色特效等

            return suggestions
        except Exception as e:
            logger.error(f"获取特效建议失败: {e}")
            return []

    def optimize_effects_order(self) -> None:
        """优化特效应用顺序"""
        # 基于特效类型和优先级重新排序
        pass

    def get_system_requirements(self) -> Dict[str, Any]:
        """获取系统要求"""
        requirements = {
            "gpu_required": False,
            "memory_required": 0,
            "processing_power_required": "low"
        }

        for instance in self.effect_instances:
            metadata = self.effect_metadata.get(instance.effect_id)
            if metadata:
                if metadata.gpu_required:
                    requirements["gpu_required"] = True
                if metadata.processing_time_estimate > 0:
                    requirements["processing_power_required"] = "high"

        return requirements