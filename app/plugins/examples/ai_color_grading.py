#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI智能调色插件
使用AI分析视频内容并自动应用专业的色彩分级
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtGui import QImage

from app.plugins.plugin_system import EffectPlugin, PluginMetadata, PluginContext
from app.effects.effects_system import BaseEffect, EffectMetadata, EffectType, EffectCategory

logger = logging.getLogger(__name__)


class ColorGradingStyle(Enum):
    """调色风格枚举"""
    CINEMATIC = "cinematic"          # 电影风格
    VIBRANT = "vibrant"             # 鲜艳风格
    MOODY = "moody"                # 忧郁风格
    WARM = "warm"                  # 温暖风格
    COOL = "cool"                  # 冷静风格
    VINTAGE = "vintage"            # 复古风格
    BLACK_AND_WHITE = "bw"         # 黑白风格
    HIGH_CONTRAST = "high_contrast" # 高对比度


@dataclass
class AIColorGradingConfig:
    """AI调色配置"""
    style: str = ColorGradingStyle.CINEMATIC.value
    intensity: float = 1.0
    preserve_skin_tones: bool = True
    adaptive_lighting: bool = True
    color_accuracy: float = 0.8
    smoothing: float = 0.5
    analyze_scene: bool = True
    custom_lut: Optional[str] = None


@dataclass
class SceneAnalysis:
    """场景分析结果"""
    brightness: float
    contrast: float
    saturation: float
    dominant_colors: List[Tuple[int, int, int]]
    color_temperature: float
    has_people: bool
    scene_type: str


class ColorGradingWorker(QObject):
    """调色工作线程"""

    progress_updated = pyqtSignal(int)
    effect_completed = pyqtSignal(object, object)  # result, error

    def __init__(self, config: AIColorGradingConfig):
        super().__init__()
        self.config = config
        self._running = False

    def apply_color_grading(self, frame_data: np.ndarray):
        """应用AI调色"""
        try:
            self._running = True
            self.progress_updated.emit(10)

            # 转换颜色空间
            frame_rgb = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            frame_hsv = cv2.cvtColor(frame_data, cv2.COLOR_BGR2HSV)

            self.progress_updated.emit(20)

            # 场景分析
            if self.config.analyze_scene:
                analysis = self._analyze_scene(frame_rgb)
                self.progress_updated.emit(40)
            else:
                analysis = None

            self.progress_updated.emit(50)

            # 应用风格化调色
            graded_frame = self._apply_style_grading(frame_rgb, analysis)

            self.progress_updated.emit(80)

            # 后处理
            final_frame = self._post_process(graded_frame)

            self.progress_updated.emit(90)

            # 转回BGR格式
            result_bgr = cv2.cvtColor(final_frame, cv2.COLOR_RGB2BGR)

            self.progress_updated.emit(100)
            self.effect_completed.emit(result_bgr, None)

        except Exception as e:
            self.effect_completed.emit(None, {"error": str(e)})
        finally:
            self._running = False

    def _analyze_scene(self, frame_rgb: np.ndarray) -> SceneAnalysis:
        """分析场景特征"""
        # 计算亮度
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        brightness = np.mean(gray)

        # 计算对比度
        contrast = np.std(gray)

        # 计算饱和度
        hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
        saturation = np.mean(hsv[:, :, 1]) / 255.0

        # 获取主色调
        pixels = frame_rgb.reshape(-1, 3)
        kmeans = cv2.kmeans(
            np.float32(pixels), 3, None,
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0
        )
        dominant_colors = kmeans[2].astype(int).tolist()

        # 估算色温
        avg_b = np.mean(frame_rgb[:, :, 0])
        avg_r = np.mean(frame_rgb[:, :, 2])
        color_temperature = avg_r / (avg_b + 1e-6)

        # 简单的人体检测
        has_people = self._detect_people(frame_rgb)

        # 场景类型识别（简化版）
        scene_type = self._classify_scene(brightness, saturation, has_people)

        return SceneAnalysis(
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            dominant_colors=dominant_colors,
            color_temperature=color_temperature,
            has_people=has_people,
            scene_type=scene_type
        )

    def _apply_style_grading(self, frame_rgb: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用风格化调色"""
        style = self.config.style
        intensity = self.config.intensity

        # 复制原始帧
        result = frame_rgb.copy()

        if style == ColorGradingStyle.CINEMATIC.value:
            result = self._apply_cinematic_style(result, analysis)
        elif style == ColorGradingStyle.VIBRANT.value:
            result = self._apply_vibrant_style(result, analysis)
        elif style == ColorGradingStyle.MOODY.value:
            result = self._apply_moody_style(result, analysis)
        elif style == ColorGradingStyle.WARM.value:
            result = self._apply_warm_style(result, analysis)
        elif style == ColorGradingStyle.COOL.value:
            result = self._apply_cool_style(result, analysis)
        elif style == ColorGradingStyle.VINTAGE.value:
            result = self._apply_vintage_style(result, analysis)
        elif style == ColorGradingStyle.BLACK_AND_WHITE.value:
            result = self._apply_bw_style(result, analysis)
        elif style == ColorGradingStyle.HIGH_CONTRAST.value:
            result = self._apply_high_contrast_style(result, analysis)

        # 混合原始图像和调色结果
        if intensity < 1.0:
            result = cv2.addWeighted(frame_rgb, 1.0 - intensity, result, intensity, 0)

        return result

    def _apply_cinematic_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用电影风格调色"""
        # 降低饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.85
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # 添加橙蓝色调
        frame[:, :, 0] = np.clip(frame[:, :, 0] * 0.95, 0, 255)  # 减少蓝色
        frame[:, :, 1] = np.clip(frame[:, :, 1] * 0.98, 0, 255)  # 略微减少绿色
        frame[:, :, 2] = np.clip(frame[:, :, 2] * 1.05, 0, 255)  # 增加红色

        # S形曲线调整对比度
        frame = self._apply_s_curve(frame, 0.8)

        return frame

    def _apply_vibrant_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用鲜艳风格调色"""
        # 增加饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.1, 0, 255)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # 增强对比度
        frame = self._apply_contrast(frame, 1.2)

        return frame

    def _apply_moody_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用忧郁风格调色"""
        # 降低亮度和饱和度
        frame = frame * 0.8
        hsv = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.7
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # 添加青色调
        frame[:, :, 0] = np.clip(frame[:, :, 0] * 1.1, 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * 0.9, 0, 255)

        return frame

    def _apply_warm_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用温暖风格调色"""
        # 增加红色和黄色
        frame[:, :, 0] = np.clip(frame[:, :, 0] * 0.9, 0, 255)  # 减少蓝色
        frame[:, :, 2] = np.clip(frame[:, :, 2] * 1.15, 0, 255)  # 增加红色

        # 轻微增加饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.1, 0, 255)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        return frame

    def _apply_cool_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用冷静风格调色"""
        # 增加蓝色调
        frame[:, :, 0] = np.clip(frame[:, :, 0] * 1.15, 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * 0.9, 0, 255)  # 减少红色

        # 降低饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.9
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        return frame

    def _apply_vintage_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用复古风格调色"""
        # 添加暗角
        frame = self._add_vignette(frame, intensity=0.6)

        # 添加颗粒感
        noise = np.random.normal(0, 15, frame.shape).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # 褐色调
        frame[:, :, 0] = np.clip(frame[:, :, 0] * 0.8, 0, 255)
        frame[:, :, 1] = np.clip(frame[:, :, 1] * 0.85, 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * 1.1, 0, 255)

        return frame

    def _apply_bw_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用黑白风格调色"""
        # 转换为灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # 增强对比度
        gray = cv2.equalizeHist(gray)

        # 添加胶片颗粒
        noise = np.random.normal(0, 10, gray.shape).astype(np.int16)
        gray = np.clip(gray.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # 转回RGB
        result = np.stack([gray, gray, gray], axis=2)

        return result

    def _apply_high_contrast_style(self, frame: np.ndarray, analysis: Optional[SceneAnalysis]) -> np.ndarray:
        """应用高对比度风格调色"""
        # 增强对比度
        frame = self._apply_contrast(frame, 1.5)

        # 增加饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        return frame

    def _post_process(self, frame: np.ndarray) -> np.ndarray:
        """后处理"""
        # 皮肤色调保护
        if self.config.preserve_skin_tones:
            frame = self._protect_skin_tones(frame)

        # 平滑处理
        if self.config.smoothing > 0:
            frame = self._apply_smoothing(frame, self.config.smoothing)

        # 自适应光照
        if self.config.adaptive_lighting:
            frame = self._adaptive_lighting_correction(frame)

        return frame

    def _protect_skin_tones(self, frame: np.ndarray) -> np.ndarray:
        """保护皮肤色调"""
        # 简单的皮肤检测（YCbCr色彩空间）
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_RGB2YCrCb)

        # 皮肤色调范围
        lower = np.array([0, 133, 77], dtype=np.uint8)
        upper = np.array([255, 173, 127], dtype=np.uint8)

        mask = cv2.inRange(ycrcb, lower, upper)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        # 在皮肤区域降低效果强度
        return frame  # 简化实现，实际需要更复杂的保护逻辑

    def _apply_smoothing(self, frame: np.ndarray, intensity: float) -> np.ndarray:
        """应用平滑处理"""
        # 双边滤波
        smooth = cv2.bilateralFilter(frame, 9, 75, 75)
        return cv2.addWeighted(frame, 1.0 - intensity, smooth, intensity, 0)

    def _adaptive_lighting_correction(self, frame: np.ndarray) -> np.ndarray:
        """自适应光照校正"""
        # CLAHE（对比度受限自适应直方图均衡化）
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def _apply_s_curve(self, frame: np.ndarray, strength: float) -> np.ndarray:
        """应用S形曲线"""
        # 创建查找表
        lut = np.arange(256, dtype=np.uint8)

        # S形曲线
        for i in range(256):
            normalized = i / 255.0
            if normalized < 0.5:
                adjusted = 0.5 * (2 * normalized) ** strength
            else:
                adjusted = 1 - 0.5 * (2 * (1 - normalized)) ** strength
            lut[i] = int(adjusted * 255)

        return cv2.LUT(frame, lut)

    def _apply_contrast(self, frame: np.ndarray, factor: float) -> np.ndarray:
        """应用对比度调整"""
        mean = np.mean(frame)
        return np.clip((frame - mean) * factor + mean, 0, 255).astype(np.uint8)

    def _add_vignette(self, frame: np.ndarray, intensity: float) -> np.ndarray:
        """添加暗角效果"""
        height, width = frame.shape[:2]

        # 创建径向渐变
        center_x, center_y = width // 2, height // 2
        max_dist = np.sqrt(center_x**2 + center_y**2)

        y, x = np.ogrid[:height, :width]
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)

        # 创建暗角蒙版
        vignette = 1 - (dist_from_center / max_dist) * intensity
        vignette = np.clip(vignette, 0, 1)

        # 应用暗角
        return (frame * vignette[:, :, np.newaxis]).astype(np.uint8)

    def _detect_people(self, frame: np.ndarray) -> bool:
        """简单的人体检测（简化版）"""
        # 这里应该使用OpenCV的人体检测器
        # 为了简化，返回False
        return False

    def _classify_scene(self, brightness: float, saturation: float, has_people: bool) -> str:
        """场景分类"""
        if has_people:
            return "portrait"
        elif brightness > 180:
            return "bright_scene"
        elif brightness < 80:
            return "dark_scene"
        elif saturation > 120:
            return "colorful_scene"
        else:
            return "neutral_scene"


class AIColorGradingEffect(EffectPlugin):
    """AI智能调色效果插件"""

    def __init__(self):
        super().__init__()
        self._config = AIColorGradingConfig()
        self._worker = None
        self._thread = None

    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        return PluginMetadata(
            name="AI智能调色",
            version="1.0.0",
            description="使用AI分析视频内容并自动应用专业的色彩分级效果",
            author="CineAI Studio Team",
            email="support@cineaistudio.com",
            website="https://cineaistudio.com",
            plugin_type=PluginType.EFFECT,
            category="AI Effects",
            tags=["AI", "Color Grading", "Cinematic", "Professional"],
            dependencies=["opencv-python>=4.5.0", "numpy>=1.20.0"],
            min_app_version="2.0.0",
            api_version="1.0",
            priority=PluginPriority.HIGH,
            enabled=True,
            config_schema={
                "sections": [
                    {
                        "name": "style",
                        "label": "调色风格",
                        "description": "选择调色风格",
                        "fields": [
                            {
                                "name": "style",
                                "label": "风格",
                                "type": "select",
                                "description": "选择调色风格",
                                "default": "cinematic",
                                "options": [
                                    {"value": "cinematic", "label": "电影风格"},
                                    {"value": "vibrant", "label": "鲜艳风格"},
                                    {"value": "moody", "label": "忧郁风格"},
                                    {"value": "warm", "label": "温暖风格"},
                                    {"value": "cool", "label": "冷静风格"},
                                    {"value": "vintage", "label": "复古风格"},
                                    {"value": "bw", "label": "黑白风格"},
                                    {"value": "high_contrast", "label": "高对比度"}
                                ]
                            }
                        ]
                    },
                    {
                        "name": "parameters",
                        "label": "参数设置",
                        "description": "调色参数控制",
                        "fields": [
                            {
                                "name": "intensity",
                                "label": "强度",
                                "type": "float",
                                "description": "调色效果强度（0.0-2.0）",
                                "default": 1.0,
                                "min_value": 0.0,
                                "max_value": 2.0,
                                "step": 0.1
                            },
                            {
                                "name": "color_accuracy",
                                "label": "色彩准确度",
                                "type": "float",
                                "description": "AI色彩分析的准确度（0.0-1.0）",
                                "default": 0.8,
                                "min_value": 0.0,
                                "max_value": 1.0,
                                "step": 0.1
                            },
                            {
                                "name": "smoothing",
                                "label": "平滑度",
                                "type": "float",
                                "description": "画面平滑程度（0.0-1.0）",
                                "default": 0.5,
                                "min_value": 0.0,
                                "max_value": 1.0,
                                "step": 0.1
                            }
                        ]
                    },
                    {
                        "name": "advanced",
                        "label": "高级设置",
                        "description": "高级调色选项",
                        "fields": [
                            {
                                "name": "preserve_skin_tones",
                                "label": "保护皮肤色调",
                                "type": "boolean",
                                "description": "保持人物皮肤的自然色调",
                                "default": True
                            },
                            {
                                "name": "adaptive_lighting",
                                "label": "自适应光照",
                                "type": "boolean",
                                "description": "根据场景自动调整光照",
                                "default": True
                            },
                            {
                                "name": "analyze_scene",
                                "label": "场景分析",
                                "type": "boolean",
                                "description": "启用AI场景分析以优化调色",
                                "default": True
                            }
                        ]
                    }
                ]
            }
        )

    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        try:
            self._context = context
            logger.info("AI智能调色插件初始化成功")
            return True
        except Exception as e:
            logger.error(f"AI智能调色插件初始化失败: {e}")
            return False

    def cleanup(self):
        """清理插件资源"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        logger.info("AI智能调色插件已清理")

    def get_effect_types(self) -> List[str]:
        """获取特效类型"""
        return ["ai_color_grading"]

    def create_effect(self, effect_type: str, params: Dict[str, Any]) -> Any:
        """创建特效实例"""
        if effect_type == "ai_color_grading":
            # 创建效果实例
            effect_instance = {
                "type": effect_type,
                "params": params,
                "config": self._config
            }
            return effect_instance
        return None

    def get_effect_params(self, effect_type: str) -> Dict[str, Any]:
        """获取特效参数"""
        if effect_type == "ai_color_grading":
            return {
                "style": {
                    "type": "select",
                    "options": ["cinematic", "vibrant", "moody", "warm", "cool", "vintage", "bw", "high_contrast"],
                    "default": "cinematic",
                    "label": "调色风格"
                },
                "intensity": {
                    "type": "float",
                    "min": 0.0,
                    "max": 2.0,
                    "default": 1.0,
                    "step": 0.1,
                    "label": "强度"
                }
            }
        return {}

    def render_preview(self, effect: Any, params: Dict[str, Any]) -> Any:
        """渲染预览"""
        if effect["type"] == "ai_color_grading":
            # 创建测试图像
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

            # 设置工作线程
            self._setup_worker()

            # 更新配置
            self._update_config_from_params(params)

            # 应用效果
            self._worker.apply_color_grading(test_frame)

            # 返回预览结果
            return {
                "preview": "AI调色预览",
                "processing": True,
                "estimated_time": "2-5秒"
            }

        return None

    def _setup_worker(self):
        """设置工作线程"""
        if not self._thread:
            self._thread = QThread()
            self._worker = ColorGradingWorker(self._config)
            self._worker.moveToThread(self._thread)
            self._thread.start()

    def _update_config_from_params(self, params: Dict[str, Any]):
        """从参数更新配置"""
        for key, value in params.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def on_config_changed(self, new_config: Dict[str, Any]):
        """配置变化回调"""
        for key, value in new_config.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def get_status(self) -> Dict[str, Any]:
        """获取插件状态"""
        return {
            "state": self._state.value,
            "version": self.metadata.version,
            "enabled": self.metadata.enabled,
            "available_effects": len(self.get_effect_types())
        }


# 插件注册
plugin_class = AIColorGradingEffect