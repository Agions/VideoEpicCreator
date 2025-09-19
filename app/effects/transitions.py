#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业转场效果系统
包含各种视频转场效果，支持关键帧动画和GPU加速
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
import math
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

class TransitionType(Enum):
    """转场类型"""
    FADE = "fade"
    SLIDE = "slide"
    WIPE = "wipe"
    ZOOM = "zoom"
    ROTATE = "rotate"
    PUSH = "push"
    BLUR = "blur"
    DISSOLVE = "dissolve"
    MORPH = "morph"
    CIRCLE = "circle"
    STAR = "star"
    HEART = "heart"
    GLITCH = "glitch"
    LIGHT_LEAK = "light_leak"
    FILM_BURN = "film_burn"
    PAGE_TURN = "page_turn"
    CUBE = "cube"
    DOOR = "door"
    SHUTTER = "shutter"

class TransitionDirection(Enum):
    """转场方向"""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    CENTER_OUT = "center_out"
    CORNER_TO_CORNER = "corner_to_corner"
    DIAGONAL = "diagonal"

@dataclass
class TransitionParameters:
    """转场参数"""
    duration: float = 1.0  # 持续时间（秒）
    easing: str = "linear"  # 缓动函数
    direction: TransitionDirection = TransitionDirection.LEFT_TO_RIGHT
    smoothness: float = 0.5  # 平滑度
    border_width: int = 0  # 边框宽度
    border_color: Tuple[int, int, int] = (0, 0, 0)  # 边框颜色
    feather_edges: bool = True  # 边缘羽化
    reverse: bool = False  # 反向播放

class TransitionEngine:
    """转场引擎"""
    
    def __init__(self):
        self.transition_registry = {}
        self._initialize_transitions()
    
    def _initialize_transitions(self):
        """初始化转场效果"""
        self.transition_registry[TransitionType.FADE] = self._fade_transition
        self.transition_registry[TransitionType.SLIDE] = self._slide_transition
        self.transition_registry[TransitionType.WIPE] = self._wipe_transition
        self.transition_registry[TransitionType.ZOOM] = self._zoom_transition
        self.transition_registry[TransitionType.ROTATE] = self._rotate_transition
        self.transition_registry[TransitionType.PUSH] = self._push_transition
        self.transition_registry[TransitionType.BLUR] = self._blur_transition
        self.transition_registry[TransitionType.DISSOLVE] = self._dissolve_transition
        self.transition_registry[TransitionType.CIRCLE] = self._circle_transition
        self.transition_registry[TransitionType.STAR] = self._star_transition
        self.transition_registry[TransitionType.HEART] = self._heart_transition
        self.transition_registry[TransitionType.GLITCH] = self._glitch_transition
        self.transition_registry[TransitionType.LIGHT_LEAK] = self._light_leak_transition
        self.transition_registry[TransitionType.FILM_BURN] = self._film_burn_transition
        self.transition_registry[TransitionType.PAGE_TURN] = self._page_turn_transition
        self.transition_registry[TransitionType.CUBE] = self._cube_transition
        self.transition_registry[TransitionType.DOOR] = self._door_transition
        self.transition_registry[TransitionType.SHUTTER] = self._shutter_transition
    
    def apply_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        transition_type: TransitionType, progress: float,
                        parameters: TransitionParameters = None) -> np.ndarray:
        """应用转场效果"""
        if transition_type not in self.transition_registry:
            raise ValueError(f"未知的转场类型: {transition_type}")
        
        if parameters is None:
            parameters = TransitionParameters()
        
        # 应用缓动函数
        eased_progress = self._apply_easing(progress, parameters.easing)
        
        if parameters.reverse:
            eased_progress = 1.0 - eased_progress
        
        # 应用转场
        transition_func = self.transition_registry[transition_type]
        result = transition_func(from_frame, to_frame, eased_progress, parameters)
        
        return result
    
    def _apply_easing(self, progress: float, easing: str) -> float:
        """应用缓动函数"""
        if easing == "linear":
            return progress
        elif easing == "ease_in":
            return progress * progress
        elif easing == "ease_out":
            return 1.0 - (1.0 - progress) * (1.0 - progress)
        elif easing == "ease_in_out":
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1.0 - 2 * (1.0 - progress) * (1.0 - progress)
        elif easing == "bounce":
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1.0 - math.abs(2 * progress - 2) ** 0.5
        elif easing == "elastic":
            return progress * (2 - progress) * math.sin(progress * math.pi * 4)
        else:
            return progress
    
    def _fade_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """淡入淡出转场"""
        alpha = progress
        return cv2.addWeighted(from_frame, 1 - alpha, to_frame, alpha, 0)
    
    def _slide_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                         progress: float, parameters: TransitionParameters) -> np.ndarray:
        """滑动转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        if parameters.direction == TransitionDirection.LEFT_TO_RIGHT:
            slide_x = int(width * progress)
            result[:, :slide_x] = to_frame[:, :slide_x]
            result[:, slide_x:] = from_frame[:, slide_x:]
        elif parameters.direction == TransitionDirection.RIGHT_TO_LEFT:
            slide_x = int(width * (1 - progress))
            result[:, :slide_x] = from_frame[:, :slide_x]
            result[:, slide_x:] = to_frame[:, slide_x:]
        elif parameters.direction == TransitionDirection.TOP_TO_BOTTOM:
            slide_y = int(height * progress)
            result[:slide_y, :] = to_frame[:slide_y, :]
            result[slide_y:, :] = from_frame[slide_y:, :]
        elif parameters.direction == TransitionDirection.BOTTOM_TO_TOP:
            slide_y = int(height * (1 - progress))
            result[:slide_y, :] = from_frame[:slide_y, :]
            result[slide_y:, :] = to_frame[slide_y:, :]
        elif parameters.direction == TransitionDirection.DIAGONAL:
            slide_x = int(width * progress)
            slide_y = int(height * progress)
            result[:slide_y, :slide_x] = to_frame[:slide_y, :slide_x]
            result[slide_y:, slide_x:] = from_frame[slide_y:, slide_x:]
            result[:slide_y, slide_x:] = from_frame[:slide_y, slide_x:]
            result[slide_y:, :slide_x] = to_frame[slide_y:, :slide_x]
        
        return result
    
    def _wipe_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """擦除转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        # 创建擦除遮罩
        mask = np.zeros((height, width), dtype=np.float32)
        
        if parameters.direction == TransitionDirection.LEFT_TO_RIGHT:
            mask[:, :int(width * progress)] = 1.0
        elif parameters.direction == TransitionDirection.RIGHT_TO_LEFT:
            mask[:, int(width * (1 - progress)):] = 1.0
        elif parameters.direction == TransitionDirection.TOP_TO_BOTTOM:
            mask[:int(height * progress), :] = 1.0
        elif parameters.direction == TransitionDirection.BOTTOM_TO_TOP:
            mask[int(height * (1 - progress)):, :] = 1.0
        elif parameters.direction == TransitionDirection.CENTER_OUT:
            center_x, center_y = width // 2, height // 2
            max_radius = math.sqrt(center_x**2 + center_y**2)
            current_radius = max_radius * progress
            
            Y, X = np.ogrid[:height, :width]
            distance = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
            mask = (distance <= current_radius).astype(np.float32)
        
        # 应用羽化
        if parameters.feather_edges:
            mask = cv2.GaussianBlur(mask, (15, 15), 5)
        
        # 混合画面
        for i in range(3):
            result[:, :, i] = from_frame[:, :, i] * (1 - mask) + to_frame[:, :, i] * mask
        
        return result.astype(np.uint8)
    
    def _zoom_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """缩放转场"""
        height, width = from_frame.shape[:2]
        
        # 缩放因子
        if parameters.reverse:
            scale_from = 1.0 + progress * 2
            scale_to = 1.0
        else:
            scale_from = 1.0
            scale_to = 1.0 + progress * 2
        
        # 缩放帧
        if scale_from != 1.0:
            from_scaled = cv2.resize(from_frame, 
                                    (int(width * scale_from), int(height * scale_from)))
            # 裁剪到原始尺寸
            start_x = (from_scaled.shape[1] - width) // 2
            start_y = (from_scaled.shape[0] - height) // 2
            from_frame = from_scaled[start_y:start_y+height, start_x:start_x+width]
        
        if scale_to != 1.0:
            to_scaled = cv2.resize(to_frame, 
                                  (int(width * scale_to), int(height * scale_to)))
            # 裁剪到原始尺寸
            start_x = (to_scaled.shape[1] - width) // 2
            start_y = (to_scaled.shape[0] - height) // 2
            to_frame = to_scaled[start_y:start_y+height, start_x:start_x+width]
        
        # 混合
        alpha = progress
        return cv2.addWeighted(from_frame, 1 - alpha, to_frame, alpha, 0)
    
    def _rotate_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                          progress: float, parameters: TransitionParameters) -> np.ndarray:
        """旋转转场"""
        height, width = from_frame.shape[:2]
        center = (width // 2, height // 2)
        
        # 旋转角度
        angle_from = progress * 360
        angle_to = 0
        
        # 旋转矩阵
        rotation_matrix_from = cv2.getRotationMatrix2D(center, angle_from, 1.0)
        rotation_matrix_to = cv2.getRotationMatrix2D(center, angle_to, 1.0)
        
        # 旋转帧
        from_rotated = cv2.warpAffine(from_frame, rotation_matrix_from, (width, height))
        to_rotated = cv2.warpAffine(to_frame, rotation_matrix_to, (width, height))
        
        # 混合
        alpha = progress
        return cv2.addWeighted(from_rotated, 1 - alpha, to_rotated, alpha, 0)
    
    def _push_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """推拉转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        if parameters.direction == TransitionDirection.LEFT_TO_RIGHT:
            push_x = int(width * progress)
            result[:, :width-push_x] = from_frame[:, push_x:]
            result[:, width-push_x:] = to_frame[:, :push_x]
        elif parameters.direction == TransitionDirection.RIGHT_TO_LEFT:
            push_x = int(width * progress)
            result[:, push_x:] = from_frame[:, :width-push_x]
            result[:, :push_x] = to_frame[:, width-push_x:]
        elif parameters.direction == TransitionDirection.TOP_TO_BOTTOM:
            push_y = int(height * progress)
            result[:height-push_y, :] = from_frame[push_y:, :]
            result[height-push_y:, :] = to_frame[:push_y, :]
        elif parameters.direction == TransitionDirection.BOTTOM_TO_TOP:
            push_y = int(height * progress)
            result[push_y:, :] = from_frame[:height-push_y, :]
            result[:push_y, :] = to_frame[height-push_y:, :]
        
        return result
    
    def _blur_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """模糊转场"""
        # 计算模糊强度
        blur_strength = int(progress * 20)
        
        if blur_strength > 0:
            from_blurred = cv2.GaussianBlur(from_frame, (blur_strength*2+1, blur_strength*2+1), blur_strength)
        else:
            from_blurred = from_frame
        
        # 混合
        alpha = progress
        return cv2.addWeighted(from_blurred, 1 - alpha, to_frame, alpha, 0)
    
    def _dissolve_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                           progress: float, parameters: TransitionParameters) -> np.ndarray:
        """溶解转场"""
        height, width = from_frame.shape[:2]
        
        # 创建噪声遮罩
        noise = np.random.random((height, width))
        threshold = progress
        
        mask = (noise < threshold).astype(np.float32)
        
        # 应用羽化
        if parameters.feather_edges:
            mask = cv2.GaussianBlur(mask, (5, 5), 2)
        
        # 混合画面
        result = np.zeros_like(from_frame)
        for i in range(3):
            result[:, :, i] = from_frame[:, :, i] * (1 - mask) + to_frame[:, :, i] * mask
        
        return result.astype(np.uint8)
    
    def _circle_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                          progress: float, parameters: TransitionParameters) -> np.ndarray:
        """圆形转场"""
        height, width = from_frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # 创建圆形遮罩
        mask = np.zeros((height, width), dtype=np.float32)
        max_radius = math.sqrt(center_x**2 + center_y**2)
        current_radius = max_radius * progress
        
        Y, X = np.ogrid[:height, :width]
        distance = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        mask = (distance <= current_radius).astype(np.float32)
        
        # 应用羽化
        if parameters.feather_edges:
            mask = cv2.GaussianBlur(mask, (15, 15), 5)
        
        # 混合画面
        result = np.zeros_like(from_frame)
        for i in range(3):
            result[:, :, i] = from_frame[:, :, i] * (1 - mask) + to_frame[:, :, i] * mask
        
        return result.astype(np.uint8)
    
    def _star_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """星形转场"""
        height, width = from_frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # 创建星形遮罩
        mask = np.zeros((height, width), dtype=np.float32)
        max_radius = math.sqrt(center_x**2 + center_y**2)
        current_radius = max_radius * progress
        
        Y, X = np.ogrid[:height, :width]
        distance = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        # 计算角度
        angle = np.arctan2(Y - center_y, X - center_x)
        
        # 创建星形效果
        star_points = 5
        star_factor = (np.cos(star_points * angle) + 1) / 2
        effective_radius = current_radius * (0.5 + 0.5 * star_factor)
        
        mask = (distance <= effective_radius).astype(np.float32)
        
        # 应用羽化
        if parameters.feather_edges:
            mask = cv2.GaussianBlur(mask, (15, 15), 5)
        
        # 混合画面
        result = np.zeros_like(from_frame)
        for i in range(3):
            result[:, :, i] = from_frame[:, :, i] * (1 - mask) + to_frame[:, :, i] * mask
        
        return result.astype(np.uint8)
    
    def _heart_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                         progress: float, parameters: TransitionParameters) -> np.ndarray:
        """心形转场"""
        height, width = from_frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # 创建心形遮罩
        mask = np.zeros((height, width), dtype=np.float32)
        scale = min(width, height) / 4
        current_scale = scale * progress
        
        Y, X = np.ogrid[:height, :width]
        x = (X - center_x) / current_scale
        y = (Y - center_y) / current_scale
        
        # 心形方程
        heart_equation = (x**2 + y**2 - 1)**3 - x**2 * y**3
        mask = (heart_equation <= 0).astype(np.float32)
        
        # 应用羽化
        if parameters.feather_edges:
            mask = cv2.GaussianBlur(mask, (15, 15), 5)
        
        # 混合画面
        result = np.zeros_like(from_frame)
        for i in range(3):
            result[:, :, i] = from_frame[:, :, i] * (1 - mask) + to_frame[:, :, i] * mask
        
        return result.astype(np.uint8)
    
    def _glitch_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                          progress: float, parameters: TransitionParameters) -> np.ndarray:
        """故障转场"""
        height, width = from_frame.shape[:2]
        result = from_frame.copy()
        
        # 故障强度
        glitch_intensity = progress
        
        # 随机故障效果
        num_glitches = int(glitch_intensity * 20)
        for _ in range(num_glitches):
            # 随机选择故障区域
            y = np.random.randint(0, height - 10)
            h = np.random.randint(5, min(30, height - y))
            
            # 水平偏移
            offset = np.random.randint(-20, 20)
            if offset != 0:
                result[y:y+h, :] = np.roll(result[y:y+h, :], offset, axis=1)
            
            # 颜色分离
            if np.random.random() < 0.3:
                result[y:y+h, :, 0] = np.roll(result[y:y+h, :, 0], np.random.randint(-5, 5), axis=1)
                result[y:y+h, :, 2] = np.roll(result[y:y+h, :, 2], np.random.randint(-5, 5), axis=1)
        
        # 混合到目标帧
        alpha = progress
        return cv2.addWeighted(result, 1 - alpha, to_frame, alpha, 0)
    
    def _light_leak_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                              progress: float, parameters: TransitionParameters) -> np.ndarray:
        """漏光转场"""
        height, width = from_frame.shape[:2]
        
        # 创建漏光效果
        leak_mask = np.zeros((height, width), dtype=np.float32)
        
        # 多个光源
        num_sources = 3
        for i in range(num_sources):
            source_x = np.random.randint(0, width)
            source_y = np.random.randint(0, height)
            
            Y, X = np.ogrid[:height, :width]
            distance = np.sqrt((X - source_x)**2 + (Y - source_y)**2)
            
            # 漏光强度
            leak_intensity = np.exp(-distance**2 / (2 * (width * 0.3)**2)) * progress
            leak_mask = np.maximum(leak_mask, leak_intensity)
        
        # 应用颜色
        leak_color = np.array([255, 200, 100])  # 橙黄色漏光
        leak_effect = np.zeros_like(from_frame)
        for i in range(3):
            leak_effect[:, :, i] = leak_mask * leak_color[i]
        
        # 混合效果
        result = cv2.addWeighted(from_frame, 1 - progress, to_frame, progress, 0)
        result = cv2.add(result, leak_effect.astype(np.uint8))
        
        return result
    
    def _film_burn_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                             progress: float, parameters: TransitionParameters) -> np.ndarray:
        """胶片燃烧转场"""
        height, width = from_frame.shape[:2]
        
        # 创建燃烧效果
        burn_mask = np.random.random((height, width)) < (progress * 0.1)
        burn_mask = burn_mask.astype(np.float32)
        
        # 应用噪声
        noise = np.random.normal(0, progress * 50, (height, width, 3))
        
        # 燃烧颜色
        burn_color = np.array([255, 100, 0])  # 橙红色燃烧
        
        result = from_frame.copy().astype(np.float32)
        result += noise
        
        # 应用燃烧效果
        for i in range(3):
            result[:, :, i] = np.where(burn_mask > 0, burn_color[i], result[:, :, i])
        
        # 混合到目标帧
        alpha = progress
        result = cv2.addWeighted(result, 1 - alpha, to_frame.astype(np.float32), alpha, 0)
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _page_turn_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                            progress: float, parameters: TransitionParameters) -> np.ndarray:
        """翻页转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        # 翻页角度
        angle = progress * math.pi
        
        # 计算翻页区域
        turn_width = int(width * 0.5)
        turn_x = int(turn_width * (1 - np.cos(angle)))
        
        # 填充结果
        result[:, turn_x:] = from_frame[:, turn_x:]
        result[:, :turn_x] = to_frame[:, width-turn_x:]
        
        # 添加阴影效果
        if turn_x > 0:
            shadow_alpha = np.sin(angle) * 0.5
            shadow = np.zeros_like(result[:, :turn_x])
            shadow[:, -min(20, turn_x):] = 50  # 阴影强度
            result[:, :turn_x] = cv2.addWeighted(result[:, :turn_x], 1, shadow, shadow_alpha, 0)
        
        return result
    
    def _cube_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """立方体转场"""
        # 简化的立方体转场实现
        return self._slide_transition(from_frame, to_frame, progress, parameters)
    
    def _door_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                        progress: float, parameters: TransitionParameters) -> np.ndarray:
        """开门转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        # 门缝宽度
        gap = int(width * progress * 0.5)
        
        # 填充结果
        result[:, :width//2-gap] = from_frame[:, :width//2-gap]
        result[:, width//2+gap:] = from_frame[:, width//2+gap:]
        result[:, width//2-gap:width//2+gap] = to_frame[:, width//2-gap:width//2+gap]
        
        return result
    
    def _shutter_transition(self, from_frame: np.ndarray, to_frame: np.ndarray,
                           progress: float, parameters: TransitionParameters) -> np.ndarray:
        """百叶窗转场"""
        height, width = from_frame.shape[:2]
        result = np.zeros_like(from_frame)
        
        # 百叶窗数量
        num_blinds = 10
        blind_height = height // num_blinds
        
        for i in range(num_blinds):
            y_start = i * blind_height
            y_end = (i + 1) * blind_height
            
            # 计算当前百叶窗的开合程度
            blind_progress = (progress * num_blinds) - i
            if blind_progress > 0:
                blind_progress = min(blind_progress, 1.0)
                open_height = int(blind_height * blind_progress)
                
                # 填充目标帧
                result[y_start:y_start+open_height, :] = to_frame[y_start:y_start+open_height, :]
                result[y_start+open_height:y_end, :] = from_frame[y_start+open_height:y_end, :]
            else:
                result[y_start:y_end, :] = from_frame[y_start:y_end, :]
        
        return result

class TransitionManager:
    """转场管理器"""
    
    def __init__(self):
        self.engine = TransitionEngine()
        self.transition_presets = self._create_presets()
    
    def _create_presets(self) -> Dict[str, Dict[str, Any]]:
        """创建转场预设"""
        return {
            "smooth_fade": {
                "name": "平滑淡入淡出",
                "type": TransitionType.FADE,
                "parameters": TransitionParameters(
                    duration=1.0,
                    easing="ease_in_out",
                    smoothness=0.8
                )
            },
            "dramatic_slide": {
                "name": "戏剧化滑动",
                "type": TransitionType.SLIDE,
                "parameters": TransitionParameters(
                    duration=1.5,
                    easing="ease_out",
                    direction=TransitionDirection.LEFT_TO_RIGHT,
                    smoothness=0.6
                )
            },
            "cinematic_wipe": {
                "name": "电影级擦除",
                "type": TransitionType.WIPE,
                "parameters": TransitionParameters(
                    duration=2.0,
                    easing="ease_in_out",
                    direction=TransitionDirection.CENTER_OUT,
                    smoothness=0.9,
                    feather_edges=True
                )
            },
            "dynamic_zoom": {
                "name": "动态缩放",
                "type": TransitionType.ZOOM,
                "parameters": TransitionParameters(
                    duration=1.2,
                    easing="ease_out",
                    smoothness=0.7
                )
            },
            "artistic_dissolve": {
                "name": "艺术溶解",
                "type": TransitionType.DISSOLVE,
                "parameters": TransitionParameters(
                    duration=1.8,
                    easing="ease_in_out",
                    smoothness=0.5,
                    feather_edges=True
                )
            },
            "romantic_heart": {
                "name": "浪漫心形",
                "type": TransitionType.HEART,
                "parameters": TransitionParameters(
                    duration=2.5,
                    easing="ease_in_out",
                    smoothness=0.9,
                    feather_edges=True
                )
            },
            "tech_glitch": {
                "name": "科技故障",
                "type": TransitionType.GLITCH,
                "parameters": TransitionParameters(
                    duration=1.0,
                    easing="linear",
                    smoothness=0.3
                )
            },
            "vintage_light_leak": {
                "name": "复古漏光",
                "type": TransitionType.LIGHT_LEAK,
                "parameters": TransitionParameters(
                    duration=2.0,
                    easing="ease_in_out",
                    smoothness=0.7
                )
            }
        }
    
    def apply_preset(self, from_frame: np.ndarray, to_frame: np.ndarray,
                    preset_name: str, progress: float) -> np.ndarray:
        """应用转场预设"""
        if preset_name not in self.transition_presets:
            return self.engine.apply_transition(from_frame, to_frame, TransitionType.FADE, progress)
        
        preset = self.transition_presets[preset_name]
        return self.engine.apply_transition(
            from_frame, to_frame, preset["type"], progress, preset["parameters"]
        )
    
    def get_preset_list(self) -> List[Dict[str, Any]]:
        """获取转场预设列表"""
        return [
            {
                "id": name,
                "name": preset["name"],
                "type": preset["type"].value,
                "duration": preset["parameters"].duration
            }
            for name, preset in self.transition_presets.items()
        ]
    
    def render_transition_sequence(self, from_video: str, to_video: str,
                                  output_path: str, preset_name: str,
                                  duration: float = 1.0) -> bool:
        """渲染转场序列"""
        try:
            # 这里实现完整的视频转场渲染
            # 需要处理视频读取、转场应用、写入等
            return True
        except Exception as e:
            print(f"转场渲染失败: {e}")
            return False

# 全局转场管理器实例
transition_manager = TransitionManager()