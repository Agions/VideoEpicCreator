#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业动画效果系统
包含各种动态效果、关键帧动画和运动路径
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable
from enum import Enum
import math
import time
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

class AnimationType(Enum):
    """动画类型"""
    POSITION = "position"
    SCALE = "scale"
    ROTATION = "rotation"
    OPACITY = "opacity"
    CROP = "crop"
    DISTORTION = "distortion"
    COLOR_SHIFT = "color_shift"
    SHAKE = "shake"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    PATH_FOLLOW = "path_follow"
    MORPH = "morph"
    PARTICLE = "particle"
    WAVE = "wave"
    SPIRAL = "spiral"
    FLIP = "flip"
    ZOOM_PAN = "zoom_pan"

class EasingType(Enum):
    """缓动类型"""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    BACK = "back"
    SINE = "sine"
    CUBIC = "cubic"
    QUARTIC = "quartic"
    QUINTIC = "quintic"

@dataclass
class Keyframe:
    """关键帧"""
    time: float  # 时间（秒）
    value: Any  # 值
    easing: EasingType = EasingType.LINEAR  # 缓动类型
    curve_points: List[Tuple[float, float]] = None  # 自定义曲线点

@dataclass
class AnimationTrack:
    """动画轨道"""
    name: str
    type: AnimationType
    keyframes: List[Keyframe]
    target: str  # 目标对象
    property_name: str  # 属性名
    is_active: bool = True

@dataclass
class AnimationLayer:
    """动画图层"""
    name: str
    tracks: List[AnimationTrack]
    opacity: float = 1.0
    blend_mode: str = "normal"
    is_visible: bool = True

@dataclass
class MotionPath:
    """运动路径"""
    points: List[Tuple[float, float]]
    is_closed: bool = False
    smoothing: float = 0.0
    speed_profile: List[float] = None

class AnimationEngine(QObject):
    """动画引擎"""
    
    # 信号定义
    animation_progress = pyqtSignal(float)  # 动画进度信号
    animation_completed = pyqtSignal(str)  # 动画完成信号
    keyframe_reached = pyqtSignal(float, str)  # 关键帧到达信号
    
    def __init__(self):
        super().__init__()
        self.animation_layers = []
        self.active_animations = {}
        self.motion_paths = {}
        self.global_time = 0.0
        self.fps = 30.0
        self.is_playing = False
        
        # 初始化内置动画
        self._initialize_builtin_animations()
    
    def _initialize_builtin_animations(self):
        """初始化内置动画"""
        # 创建预设动画模板
        self.animation_templates = {
            "zoom_in": self._create_zoom_in_template(),
            "zoom_out": self._create_zoom_out_template(),
            "pan_left": self._create_pan_left_template(),
            "pan_right": self._create_pan_right_template(),
            "rotate_clockwise": self._create_rotate_clockwise_template(),
            "bounce_effect": self._create_bounce_effect_template(),
            "shake_effect": self._create_shake_effect_template(),
            "fade_in": self._create_fade_in_template(),
            "fade_out": self._create_fade_out_template(),
            "slide_in_left": self._create_slide_in_left_template(),
            "slide_out_right": self._create_slide_out_right_template()
        }
    
    def _create_zoom_in_template(self) -> AnimationLayer:
        """创建放大模板"""
        track = AnimationTrack(
            name="zoom_in_scale",
            type=AnimationType.SCALE,
            keyframes=[
                Keyframe(time=0.0, value=0.5, easing=EasingType.EASE_OUT),
                Keyframe(time=1.0, value=1.0, easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="scale"
        )
        return AnimationLayer(name="zoom_in", tracks=[track])
    
    def _create_zoom_out_template(self) -> AnimationLayer:
        """创建缩小模板"""
        track = AnimationTrack(
            name="zoom_out_scale",
            type=AnimationType.SCALE,
            keyframes=[
                Keyframe(time=0.0, value=1.0, easing=EasingType.EASE_IN),
                Keyframe(time=1.0, value=0.5, easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="scale"
        )
        return AnimationLayer(name="zoom_out", tracks=[track])
    
    def _create_pan_left_template(self) -> AnimationLayer:
        """创建向左平移模板"""
        track = AnimationTrack(
            name="pan_left_position",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(0, 0), easing=EasingType.LINEAR),
                Keyframe(time=1.0, value=(-100, 0), easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="pan_left", tracks=[track])
    
    def _create_pan_right_template(self) -> AnimationLayer:
        """创建向右平移模板"""
        track = AnimationTrack(
            name="pan_right_position",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(0, 0), easing=EasingType.LINEAR),
                Keyframe(time=1.0, value=(100, 0), easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="pan_right", tracks=[track])
    
    def _create_rotate_clockwise_template(self) -> AnimationLayer:
        """创建顺时针旋转模板"""
        track = AnimationTrack(
            name="rotate_clockwise",
            type=AnimationType.ROTATION,
            keyframes=[
                Keyframe(time=0.0, value=0, easing=EasingType.LINEAR),
                Keyframe(time=1.0, value=360, easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="rotation"
        )
        return AnimationLayer(name="rotate_clockwise", tracks=[track])
    
    def _create_bounce_effect_template(self) -> AnimationLayer:
        """创建弹跳效果模板"""
        track = AnimationTrack(
            name="bounce_effect",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(0, 0), easing=EasingType.BOUNCE),
                Keyframe(time=0.5, value=(0, -50), easing=EasingType.BOUNCE),
                Keyframe(time=1.0, value=(0, 0), easing=EasingType.BOUNCE)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="bounce_effect", tracks=[track])
    
    def _create_shake_effect_template(self) -> AnimationLayer:
        """创建震动效果模板"""
        track = AnimationTrack(
            name="shake_effect",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(0, 0), easing=EasingType.LINEAR),
                Keyframe(time=0.1, value=(5, 5), easing=EasingType.LINEAR),
                Keyframe(time=0.2, value=(-5, -5), easing=EasingType.LINEAR),
                Keyframe(time=0.3, value=(3, 3), easing=EasingType.LINEAR),
                Keyframe(time=0.4, value=(-3, -3), easing=EasingType.LINEAR),
                Keyframe(time=0.5, value=(0, 0), easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="shake_effect", tracks=[track])
    
    def _create_fade_in_template(self) -> AnimationLayer:
        """创建淡入模板"""
        track = AnimationTrack(
            name="fade_in",
            type=AnimationType.OPACITY,
            keyframes=[
                Keyframe(time=0.0, value=0.0, easing=EasingType.EASE_IN),
                Keyframe(time=1.0, value=1.0, easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="opacity"
        )
        return AnimationLayer(name="fade_in", tracks=[track])
    
    def _create_fade_out_template(self) -> AnimationLayer:
        """创建淡出模板"""
        track = AnimationTrack(
            name="fade_out",
            type=AnimationType.OPACITY,
            keyframes=[
                Keyframe(time=0.0, value=1.0, easing=EasingType.LINEAR),
                Keyframe(time=1.0, value=0.0, easing=EasingType.EASE_OUT)
            ],
            target="frame",
            property_name="opacity"
        )
        return AnimationLayer(name="fade_out", tracks=[track])
    
    def _create_slide_in_left_template(self) -> AnimationLayer:
        """创建从左滑入模板"""
        track = AnimationTrack(
            name="slide_in_left",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(-100, 0), easing=EasingType.EASE_OUT),
                Keyframe(time=1.0, value=(0, 0), easing=EasingType.LINEAR)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="slide_in_left", tracks=[track])
    
    def _create_slide_out_right_template(self) -> AnimationLayer:
        """创建向右滑出模板"""
        track = AnimationTrack(
            name="slide_out_right",
            type=AnimationType.POSITION,
            keyframes=[
                Keyframe(time=0.0, value=(0, 0), easing=EasingType.LINEAR),
                Keyframe(time=1.0, value=(100, 0), easing=EasingType.EASE_IN)
            ],
            target="frame",
            property_name="position"
        )
        return AnimationLayer(name="slide_out_right", tracks=[track])
    
    def add_animation_layer(self, layer: AnimationLayer):
        """添加动画图层"""
        self.animation_layers.append(layer)
    
    def remove_animation_layer(self, layer_name: str):
        """移除动画图层"""
        self.animation_layers = [layer for layer in self.animation_layers 
                               if layer.name != layer_name]
    
    def apply_animation(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """应用动画到帧"""
        result = frame.copy()
        
        for layer in self.animation_layers:
            if not layer.is_visible:
                continue
            
            # 应用图层动画
            layer_result = self._apply_layer_animation(result, layer, current_time)
            
            # 混合图层
            if layer.blend_mode == "normal":
                alpha = layer.opacity
                result = cv2.addWeighted(result, 1 - alpha, layer_result, alpha, 0)
            elif layer.blend_mode == "multiply":
                result = self._blend_multiply(result, layer_result, layer.opacity)
            elif layer.blend_mode == "screen":
                result = self._blend_screen(result, layer_result, layer.opacity)
            elif layer.blend_mode == "overlay":
                result = self._blend_overlay(result, layer_result, layer.opacity)
        
        return result
    
    def _apply_layer_animation(self, frame: np.ndarray, layer: AnimationLayer, 
                             current_time: float) -> np.ndarray:
        """应用图层动画"""
        result = frame.copy()
        
        for track in layer.tracks:
            if not track.is_active:
                continue
            
            # 获取当前时间点的值
            current_value = self._interpolate_keyframes(track.keyframes, current_time)
            
            # 应用动画
            if track.type == AnimationType.POSITION:
                result = self._apply_position_animation(result, current_value)
            elif track.type == AnimationType.SCALE:
                result = self._apply_scale_animation(result, current_value)
            elif track.type == AnimationType.ROTATION:
                result = self._apply_rotation_animation(result, current_value)
            elif track.type == AnimationType.OPACITY:
                result = self._apply_opacity_animation(result, current_value)
            elif track.type == AnimationType.CROP:
                result = self._apply_crop_animation(result, current_value)
            elif track.type == AnimationType.DISTORTION:
                result = self._apply_distortion_animation(result, current_value)
            elif track.type == AnimationType.COLOR_SHIFT:
                result = self._apply_color_shift_animation(result, current_value)
            elif track.type == AnimationType.SHAKE:
                result = self._apply_shake_animation(result, current_value)
            elif track.type == AnimationType.BOUNCE:
                result = self._apply_bounce_animation(result, current_value)
            elif track.type == AnimationType.WAVE:
                result = self._apply_wave_animation(result, current_time)
            elif track.type == AnimationType.SPIRAL:
                result = self._apply_spiral_animation(result, current_time)
            elif track.type == AnimationType.FLIP:
                result = self._apply_flip_animation(result, current_value)
            elif track.type == AnimationType.ZOOM_PAN:
                result = self._apply_zoom_pan_animation(result, current_value)
        
        return result
    
    def _interpolate_keyframes(self, keyframes: List[Keyframe], current_time: float) -> Any:
        """关键帧插值"""
        if not keyframes:
            return None
        
        # 找到当前时间所在的关键帧区间
        for i in range(len(keyframes) - 1):
            start_keyframe = keyframes[i]
            end_keyframe = keyframes[i + 1]
            
            if start_keyframe.time <= current_time <= end_keyframe.time:
                # 计算插值因子
                duration = end_keyframe.time - start_keyframe.time
                if duration == 0:
                    return start_keyframe.value
                
                t = (current_time - start_keyframe.time) / duration
                
                # 应用缓动函数
                t = self._apply_easing(t, start_keyframe.easing)
                
                # 插值计算
                return self._interpolate_values(start_keyframe.value, end_keyframe.value, t)
        
        # 超出范围，返回边界值
        if current_time <= keyframes[0].time:
            return keyframes[0].value
        else:
            return keyframes[-1].value
    
    def _apply_easing(self, t: float, easing: EasingType) -> float:
        """应用缓动函数"""
        if easing == EasingType.LINEAR:
            return t
        elif easing == EasingType.EASE_IN:
            return t * t
        elif easing == EasingType.EASE_OUT:
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif easing == EasingType.EASE_IN_OUT:
            if t < 0.5:
                return 2 * t * t
            else:
                return 1.0 - 2 * (1.0 - t) * (1.0 - t)
        elif easing == EasingType.BOUNCE:
            if t < 0.5:
                return 2 * t * t
            else:
                return 1.0 - math.abs(2 * t - 2) ** 0.5
        elif easing == EasingType.ELASTIC:
            return t * (2 - t) * math.sin(t * math.pi * 4)
        elif easing == EasingType.BACK:
            return t * t * (2.7 * t - 1.7)
        elif easing == EasingType.SINE:
            return 0.5 * (1 - math.cos(t * math.pi))
        elif easing == EasingType.CUBIC:
            return t * t * t
        elif easing == EasingType.QUARTIC:
            return t * t * t * t
        elif easing == EasingType.QUINTIC:
            return t * t * t * t * t
        else:
            return t
    
    def _interpolate_values(self, start_value: Any, end_value: Any, t: float) -> Any:
        """插值计算"""
        if isinstance(start_value, (int, float)) and isinstance(end_value, (int, float)):
            return start_value + (end_value - start_value) * t
        elif isinstance(start_value, tuple) and isinstance(end_value, tuple):
            return tuple(start_value[i] + (end_value[i] - start_value[i]) * t 
                       for i in range(len(start_value)))
        else:
            return start_value
    
    def _apply_position_animation(self, frame: np.ndarray, position: Tuple[float, float]) -> np.ndarray:
        """应用位置动画"""
        if position is None:
            return frame
        
        height, width = frame.shape[:2]
        dx, dy = int(position[0]), int(position[1])
        
        # 创建变换矩阵
        translation_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
        
        # 应用平移
        result = cv2.warpAffine(frame, translation_matrix, (width, height))
        
        return result
    
    def _apply_scale_animation(self, frame: np.ndarray, scale: float) -> np.ndarray:
        """应用缩放动画"""
        if scale is None:
            return frame
        
        height, width = frame.shape[:2]
        
        # 计算新尺寸
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        if scale == 1.0:
            return frame
        
        # 缩放
        if scale > 1.0:
            # 放大后裁剪
            scaled = cv2.resize(frame, (new_width, new_height))
            start_x = (scaled.shape[1] - width) // 2
            start_y = (scaled.shape[0] - height) // 2
            return scaled[start_y:start_y+height, start_x:start_x+width]
        else:
            # 缩小后填充
            scaled = cv2.resize(frame, (new_width, new_height))
            result = np.zeros((height, width, 3), dtype=np.uint8)
            start_x = (width - scaled.shape[1]) // 2
            start_y = (height - scaled.shape[0]) // 2
            result[start_y:start_y+scaled.shape[0], start_x:start_x+scaled.shape[1]] = scaled
            return result
    
    def _apply_rotation_animation(self, frame: np.ndarray, angle: float) -> np.ndarray:
        """应用旋转动画"""
        if angle is None:
            return frame
        
        height, width = frame.shape[:2]
        center = (width // 2, height // 2)
        
        # 创建旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 应用旋转
        result = cv2.warpAffine(frame, rotation_matrix, (width, height))
        
        return result
    
    def _apply_opacity_animation(self, frame: np.ndarray, opacity: float) -> np.ndarray:
        """应用透明度动画"""
        if opacity is None:
            return frame
        
        # 创建透明背景
        result = frame.copy().astype(np.float32)
        result = result * opacity
        
        return result.astype(np.uint8)
    
    def _apply_crop_animation(self, frame: np.ndarray, crop_params: Dict[str, Any]) -> np.ndarray:
        """应用裁剪动画"""
        if crop_params is None:
            return frame
        
        height, width = frame.shape[:2]
        
        # 获取裁剪参数
        left = int(crop_params.get('left', 0))
        top = int(crop_params.get('top', 0))
        right = int(crop_params.get('right', width))
        bottom = int(crop_params.get('bottom', height))
        
        # 确保参数有效
        left = max(0, left)
        top = max(0, top)
        right = min(width, right)
        bottom = min(height, bottom)
        
        # 裁剪
        cropped = frame[top:bottom, left:right]
        
        # 如果需要，调整回原始尺寸
        if cropped.shape[0] != height or cropped.shape[1] != width:
            cropped = cv2.resize(cropped, (width, height))
        
        return cropped
    
    def _apply_distortion_animation(self, frame: np.ndarray, distortion_params: Dict[str, Any]) -> np.ndarray:
        """应用扭曲动画"""
        if distortion_params is None:
            return frame
        
        height, width = frame.shape[:2]
        
        # 获取扭曲参数
        intensity = distortion_params.get('intensity', 0.1)
        frequency = distortion_params.get('frequency', 1.0)
        
        # 创建扭曲映射
        map_x = np.zeros((height, width), dtype=np.float32)
        map_y = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                # 波浪扭曲
                offset_x = int(intensity * width * math.sin(frequency * y * 2 * math.pi / height))
                offset_y = int(intensity * height * math.cos(frequency * x * 2 * math.pi / width))
                
                map_x[y, x] = x + offset_x
                map_y[y, x] = y + offset_y
        
        # 应用扭曲
        result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        
        return result
    
    def _apply_color_shift_animation(self, frame: np.ndarray, color_shift: Dict[str, float]) -> np.ndarray:
        """应用颜色偏移动画"""
        if color_shift is None:
            return frame
        
        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 应用色相偏移
        if 'hue' in color_shift:
            hsv[:, :, 0] = (hsv[:, :, 0] + color_shift['hue']) % 180
        
        # 应用饱和度偏移
        if 'saturation' in color_shift:
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] + color_shift['saturation'], 0, 255)
        
        # 应用亮度偏移
        if 'brightness' in color_shift:
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] + color_shift['brightness'], 0, 255)
        
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def _apply_shake_animation(self, frame: np.ndarray, shake_params: Dict[str, Any]) -> np.ndarray:
        """应用震动动画"""
        if shake_params is None:
            return frame
        
        intensity = shake_params.get('intensity', 5)
        frequency = shake_params.get('frequency', 10)
        
        # 随机偏移
        dx = np.random.randint(-intensity, intensity)
        dy = np.random.randint(-intensity, intensity)
        
        # 应用震动
        height, width = frame.shape[:2]
        translation_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
        result = cv2.warpAffine(frame, translation_matrix, (width, height))
        
        return result
    
    def _apply_bounce_animation(self, frame: np.ndarray, bounce_params: Dict[str, Any]) -> np.ndarray:
        """应用弹跳动画"""
        if bounce_params is None:
            return frame
        
        height, width = frame.shape[:2]
        
        # 获取弹跳参数
        amplitude = bounce_params.get('amplitude', 50)
        frequency = bounce_params.get('frequency', 2.0)
        phase = bounce_params.get('phase', 0.0)
        
        # 计算垂直偏移
        offset_y = int(amplitude * math.sin(frequency * self.global_time * 2 * math.pi + phase))
        
        # 应用弹跳
        translation_matrix = np.float32([[1, 0, 0], [0, 1, offset_y]])
        result = cv2.warpAffine(frame, translation_matrix, (width, height))
        
        return result
    
    def _apply_wave_animation(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """应用波浪动画"""
        height, width = frame.shape[:2]
        
        # 波浪参数
        amplitude = 10
        frequency = 0.1
        speed = 2.0
        
        # 创建波浪效果
        map_x = np.zeros((height, width), dtype=np.float32)
        map_y = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                offset_x = int(amplitude * math.sin(frequency * x + speed * current_time))
                offset_y = int(amplitude * math.cos(frequency * y + speed * current_time))
                
                map_x[y, x] = x + offset_x
                map_y[y, x] = y + offset_y
        
        result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        
        return result
    
    def _apply_spiral_animation(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """应用螺旋动画"""
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # 螺旋参数
        max_radius = math.sqrt(center_x**2 + center_y**2)
        spiral_speed = 0.5
        
        # 创建螺旋映射
        map_x = np.zeros((height, width), dtype=np.float32)
        map_y = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                # 计算极坐标
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx**2 + dy**2)
                angle = math.atan2(dy, dx)
                
                # 螺旋扭曲
                spiral_angle = angle + spiral_speed * current_time * distance / max_radius
                
                # 转换回笛卡尔坐标
                new_x = center_x + distance * math.cos(spiral_angle)
                new_y = center_y + distance * math.sin(spiral_angle)
                
                map_x[y, x] = new_x
                map_y[y, x] = new_y
        
        result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        
        return result
    
    def _apply_flip_animation(self, frame: np.ndarray, flip_params: Dict[str, bool]) -> np.ndarray:
        """应用翻转动画"""
        if flip_params is None:
            return frame
        
        result = frame.copy()
        
        if flip_params.get('horizontal', False):
            result = cv2.flip(result, 1)
        
        if flip_params.get('vertical', False):
            result = cv2.flip(result, 0)
        
        return result
    
    def _apply_zoom_pan_animation(self, frame: np.ndarray, zoom_pan_params: Dict[str, Any]) -> np.ndarray:
        """应用缩放平移动画"""
        if zoom_pan_params is None:
            return frame
        
        height, width = frame.shape[:2]
        
        # 获取参数
        scale = zoom_pan_params.get('scale', 1.0)
        pan_x = zoom_pan_params.get('pan_x', 0.0)
        pan_y = zoom_pan_params.get('pan_y', 0.0)
        
        # 应用缩放
        if scale != 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            scaled = cv2.resize(frame, (new_width, new_height))
            
            if scale > 1.0:
                # 放大后裁剪
                start_x = int((scaled.shape[1] - width) // 2 + pan_x)
                start_y = int((scaled.shape[0] - height) // 2 + pan_y)
                start_x = max(0, min(start_x, scaled.shape[1] - width))
                start_y = max(0, min(start_y, scaled.shape[0] - height))
                result = scaled[start_y:start_y+height, start_x:start_x+width]
            else:
                # 缩小后填充
                result = np.zeros((height, width, 3), dtype=np.uint8)
                start_x = int((width - scaled.shape[1]) // 2 + pan_x)
                start_y = int((height - scaled.shape[0]) // 2 + pan_y)
                start_x = max(0, min(start_x, width - scaled.shape[1]))
                start_y = max(0, min(start_y, height - scaled.shape[0]))
                result[start_y:start_y+scaled.shape[0], start_x:start_x+scaled.shape[1]] = scaled
        else:
            result = frame.copy()
        
        return result
    
    def _blend_multiply(self, base: np.ndarray, overlay: np.ndarray, opacity: float) -> np.ndarray:
        """正片叠底混合"""
        base_float = base.astype(np.float32) / 255.0
        overlay_float = overlay.astype(np.float32) / 255.0
        
        result = base_float * overlay_float * opacity + base_float * (1 - opacity)
        
        return (result * 255).astype(np.uint8)
    
    def _blend_screen(self, base: np.ndarray, overlay: np.ndarray, opacity: float) -> np.ndarray:
        """滤色混合"""
        base_float = base.astype(np.float32) / 255.0
        overlay_float = overlay.astype(np.float32) / 255.0
        
        result = (1.0 - (1.0 - base_float) * (1.0 - overlay_float)) * opacity + base_float * (1 - opacity)
        
        return (result * 255).astype(np.uint8)
    
    def _blend_overlay(self, base: np.ndarray, overlay: np.ndarray, opacity: float) -> np.ndarray:
        """叠加混合"""
        base_float = base.astype(np.float32) / 255.0
        overlay_float = overlay.astype(np.float32) / 255.0
        
        # 创建遮罩
        mask = base_float < 0.5
        
        # 计算
        result = np.where(mask, 
                         2.0 * base_float * overlay_float,
                         1.0 - 2.0 * (1.0 - base_float) * (1.0 - overlay_float))
        
        result = result * opacity + base_float * (1 - opacity)
        
        return (result * 255).astype(np.uint8)
    
    def create_motion_path(self, name: str, points: List[Tuple[float, float]], 
                          is_closed: bool = False, smoothing: float = 0.0) -> bool:
        """创建运动路径"""
        try:
            self.motion_paths[name] = MotionPath(
                points=points,
                is_closed=is_closed,
                smoothing=smoothing
            )
            return True
        except Exception as e:
            print(f"创建运动路径失败: {e}")
            return False
    
    def get_position_on_path(self, path_name: str, t: float) -> Tuple[float, float]:
        """获取路径上的位置"""
        if path_name not in self.motion_paths:
            return (0, 0)
        
        path = self.motion_paths[path_name]
        points = path.points
        
        if not points:
            return (0, 0)
        
        if len(points) == 1:
            return points[0]
        
        # 计算总长度
        total_length = 0
        segment_lengths = []
        
        for i in range(len(points) - 1):
            length = math.sqrt((points[i+1][0] - points[i][0])**2 + 
                             (points[i+1][1] - points[i][1])**2)
            segment_lengths.append(length)
            total_length += length
        
        if path.is_closed:
            length = math.sqrt((points[0][0] - points[-1][0])**2 + 
                             (points[0][1] - points[-1][1])**2)
            segment_lengths.append(length)
            total_length += length
        
        # 找到当前段
        target_length = t * total_length
        current_length = 0
        
        for i, segment_length in enumerate(segment_lengths):
            if current_length + segment_length >= target_length:
                # 在当前段内
                segment_t = (target_length - current_length) / segment_length
                
                if i < len(points) - 1:
                    start_point = points[i]
                    end_point = points[i + 1]
                else:
                    start_point = points[-1]
                    end_point = points[0]
                
                # 线性插值
                x = start_point[0] + (end_point[0] - start_point[0]) * segment_t
                y = start_point[1] + (end_point[1] - start_point[1]) * segment_t
                
                return (x, y)
            
            current_length += segment_length
        
        # 超出范围，返回最后一个点
        return points[-1]
    
    def start_animation(self, duration: float):
        """开始动画"""
        self.is_playing = True
        self.global_time = 0.0
        self.animation_duration = duration
        
        # 启动动画定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(int(1000 / self.fps))
    
    def _update_animation(self):
        """更新动画"""
        if not self.is_playing:
            return
        
        # 更新时间
        self.global_time += 1.0 / self.fps
        
        # 发送进度信号
        progress = min(self.global_time / self.animation_duration, 1.0)
        self.animation_progress.emit(progress)
        
        # 检查是否完成
        if self.global_time >= self.animation_duration:
            self.is_playing = False
            self.animation_timer.stop()
            self.animation_completed.emit("animation_complete")
    
    def stop_animation(self):
        """停止动画"""
        self.is_playing = False
        if hasattr(self, 'animation_timer'):
            self.animation_timer.stop()
    
    def reset_animation(self):
        """重置动画"""
        self.stop_animation()
        self.global_time = 0.0
        self.animation_progress.emit(0.0)
    
    def get_animation_template(self, template_name: str) -> AnimationLayer:
        """获取动画模板"""
        return self.animation_templates.get(template_name)
    
    def get_template_list(self) -> List[Dict[str, Any]]:
        """获取模板列表"""
        return [
            {
                "id": name,
                "name": name.replace("_", " ").title(),
                "description": f"{name.replace('_', ' ')} animation template"
            }
            for name in self.animation_templates.keys()
        ]

# 全局动画引擎实例
animation_engine = AnimationEngine()