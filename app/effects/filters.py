#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业滤镜效果系统
包含各种色彩调整、光影效果和艺术滤镜
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from enum import Enum
import math

class FilterType(Enum):
    """滤镜类型"""
    COLOR_ADJUSTMENT = "color_adjustment"
    LIGHT_EFFECT = "light_effect"
    ARTISTIC = "artistic"
    VINTAGE = "vintage"
    DRAMATIC = "dramatic"

class FilterPreset(Enum):
    """滤镜预设"""
    ORIGINAL = "original"
    VIVID = "vivid"
    DRAMATIC = "dramatic"
    SOFT = "soft"
    COLD = "cold"
    WARM = "warm"
    BLACK_WHITE = "black_white"
    SEPIA = "sepia"
    VINTAGE = "vintage"
    NOIR = "noir"
    CINEMATIC = "cinematic"

class ColorGradingFilter:
    """色彩分级滤镜"""
    
    @staticmethod
    def lift_gamma_gain(frame: np.ndarray, lift: Tuple[float, float, float] = (0, 0, 0),
                       gamma: Tuple[float, float, float] = (1, 1, 1),
                       gain: Tuple[float, float, float] = (1, 1, 1)) -> np.ndarray:
        """Lift-Gamma-Gain色彩分级"""
        # 转换为float32进行精确计算
        frame_float = frame.astype(np.float32) / 255.0
        
        # 应用Lift (阴影)
        frame_float = frame_float * (1 - np.array(lift)) + np.array(lift)
        
        # 应用Gamma (中间调)
        frame_float = np.power(frame_float, 1.0 / np.array(gamma))
        
        # 应用Gain (高光)
        frame_float = frame_float * np.array(gain)
        
        # 限制范围并转换回uint8
        result = np.clip(frame_float * 255, 0, 255).astype(np.uint8)
        return result
    
    @staticmethod
    def color_wheel_adjustment(frame: np.ndarray, hue_shift: float = 0,
                             saturation_adjust: float = 0, 
                             brightness_adjust: float = 0) -> np.ndarray:
        """色彩轮调整"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 色相调整
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
        
        # 饱和度调整
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + saturation_adjust, 0, 255)
        
        # 亮度调整
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + brightness_adjust, 0, 255)
        
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    @staticmethod
    def hsl_curves(frame: np.ndarray, hue_curve: List[Tuple[float, float]] = None,
                  saturation_curve: List[Tuple[float, float]] = None,
                  lightness_curve: List[Tuple[float, float]] = None) -> np.ndarray:
        """HSL曲线调整"""
        # 转换为HSL色彩空间
        hsl = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hsl)
        
        # 应用曲线调整
        if hue_curve:
            h = ColorGradingFilter._apply_curve(h, hue_curve, 180)
        if lightness_curve:
            l = ColorGradingFilter._apply_curve(l, lightness_curve, 255)
        if saturation_curve:
            s = ColorGradingFilter._apply_curve(s, saturation_curve, 255)
        
        # 合并通道
        hsl = cv2.merge([h, l, s])
        return cv2.cvtColor(hsl, cv2.COLOR_HLS2BGR)
    
    @staticmethod
    def _apply_curve(channel: np.ndarray, curve_points: List[Tuple[float, float]], 
                    max_value: int) -> np.ndarray:
        """应用曲线调整"""
        if not curve_points:
            return channel
        
        # 创建曲线查找表
        lut = np.zeros(256, dtype=np.float32)
        
        # 线性插值曲线点
        for i in range(256):
            normalized_value = i / 255.0 * max_value
            lut[i] = ColorGradingFilter._interpolate_curve(curve_points, normalized_value)
        
        # 应用曲线
        normalized_channel = channel.astype(np.float32) / max_value * 255
        adjusted_channel = np.take(lut, normalized_channel.astype(np.int32))
        return np.clip(adjusted_channel / 255.0 * max_value, 0, max_value).astype(np.uint8)
    
    @staticmethod
    def _interpolate_curve(curve_points: List[Tuple[float, float]], value: float) -> float:
        """曲线插值"""
        if len(curve_points) < 2:
            return value
        
        # 找到合适的区间
        for i in range(len(curve_points) - 1):
            x1, y1 = curve_points[i]
            x2, y2 = curve_points[i + 1]
            
            if x1 <= value <= x2:
                # 线性插值
                t = (value - x1) / (x2 - x1) if x2 != x1 else 0
                return y1 + t * (y2 - y1)
        
        # 超出范围时返回边界值
        if value < curve_points[0][0]:
            return curve_points[0][1]
        else:
            return curve_points[-1][1]

class LightEffectsFilter:
    """光影效果滤镜"""
    
    @staticmethod
    def vignette(frame: np.ndarray, intensity: float = 0.5, 
                radius: float = 0.5, center: Tuple[float, float] = (0.5, 0.5)) -> np.ndarray:
        """暗角效果"""
        height, width = frame.shape[:2]
        
        # 创建渐变遮罩
        center_x = int(width * center[0])
        center_y = int(height * center[1])
        
        # 计算每个像素到中心的距离
        Y, X = np.ogrid[:height, :width]
        distance = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        # 归一化距离
        max_distance = np.sqrt(center_x**2 + center_y**2)
        normalized_distance = distance / max_distance
        
        # 创建暗角遮罩
        mask = 1.0 - intensity * np.clip((normalized_distance - radius) / (1 - radius), 0, 1)
        
        # 应用遮罩
        result = frame.astype(np.float32)
        for i in range(3):  # RGB通道
            result[:, :, i] *= mask
        
        return result.astype(np.uint8)
    
    @staticmethod
    def lens_flare(frame: np.ndarray, position: Tuple[float, float] = (0.5, 0.5),
                   intensity: float = 0.5, color: Tuple[int, int, int] = (255, 255, 255)) -> np.ndarray:
        """镜头光晕效果"""
        height, width = frame.shape[:2]
        center_x = int(width * position[0])
        center_y = int(height * position[1])
        
        # 创建光晕遮罩
        Y, X = np.ogrid[:height, :width]
        distance = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        # 多层光晕效果
        flare_mask = np.zeros((height, width), dtype=np.float32)
        
        # 主光晕
        main_radius = min(width, height) * 0.3
        main_flare = np.exp(-distance**2 / (2 * main_radius**2))
        flare_mask += main_flare * intensity
        
        # 次光晕
        for i in range(3):
            offset_radius = main_radius * (1.5 + i * 0.5)
            offset_flare = np.exp(-distance**2 / (2 * offset_radius**2))
            flare_mask += offset_flare * intensity * 0.3
        
        # 应用颜色
        result = frame.astype(np.float32)
        for i, color_channel in enumerate(color):
            result[:, :, i] += flare_mask * color_channel * intensity
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def bloom(frame: np.ndarray, intensity: float = 0.5, threshold: float = 0.7,
              radius: float = 15.0) -> np.ndarray:
        """辉光效果"""
        # 提取高光区域
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        high_pass_mask = (gray.astype(np.float32) / 255.0) > threshold
        
        # 创建辉光层
        bloom_layer = frame.astype(np.float32) / 255.0
        bloom_layer[~high_pass_mask] = 0
        
        # 模糊处理
        bloom_layer = cv2.GaussianBlur(bloom_layer, (int(radius*2+1), int(radius*2+1)), radius)
        
        # 混合原图和辉光层
        result = frame.astype(np.float32) / 255.0
        result = result * (1 - intensity) + bloom_layer * intensity
        
        return (result * 255).astype(np.uint8)
    
    @staticmethod
    def god_rays(frame: np.ndarray, source: Tuple[float, float] = (0.5, 0.5),
                intensity: float = 0.5, num_rays: int = 12) -> np.ndarray:
        """神圣光束效果"""
        height, width = frame.shape[:2]
        center_x = int(width * source[0])
        center_y = int(height * source[1])
        
        # 创建光束遮罩
        rays_mask = np.zeros((height, width), dtype=np.float32)
        
        for i in range(num_rays):
            angle = (i / num_rays) * 2 * np.pi
            
            # 光束终点
            end_x = int(center_x + width * np.cos(angle))
            end_y = int(center_y + height * np.sin(angle))
            
            # 绘制光束
            for j in range(10):
                alpha = (10 - j) / 10.0
                thickness = j * 3 + 1
                temp_mask = np.zeros((height, width), dtype=np.float32)
                cv2.line(temp_mask, (center_x, center_y), (end_x, end_y), alpha, thickness)
                rays_mask = np.maximum(rays_mask, temp_mask)
        
        # 模糊光束
        rays_mask = cv2.GaussianBlur(rays_mask, (21, 21), 5)
        
        # 应用效果
        result = frame.astype(np.float32)
        for i in range(3):
            result[:, :, i] = np.clip(result[:, :, i] + rays_mask * intensity * 255, 0, 255)
        
        return result.astype(np.uint8)

class ArtisticFilter:
    """艺术滤镜"""
    
    @staticmethod
    def oil_painting(frame: np.ndarray, intensity: int = 7, 
                     size: int = 3) -> np.ndarray:
        """油画效果"""
        return cv2.xphoto.oilPainting(frame, size, intensity)
    
    @staticmethod
    def watercolor(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """水彩效果"""
        # 双边滤波
        smooth = cv2.bilateralFilter(frame, 15, 25, 25)
        
        # 边缘检测
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                    cv2.THRESH_BINARY, 9, 9)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # 混合
        result = cv2.addWeighted(smooth, intensity, edges, 1 - intensity, 0)
        return result
    
    @staticmethod
    def cartoon(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """卡通效果"""
        # 双边滤波
        smooth = cv2.bilateralFilter(frame, 15, 25, 25)
        
        # 创建边缘遮罩
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                    cv2.THRESH_BINARY, 9, 9)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # 量化颜色
        quantized = smooth.copy()
        for i in range(3):
            quantized[:, :, i] = quantized[:, :, i] // 32 * 32
        
        # 混合
        result = cv2.addWeighted(quantized, intensity, edges, 1 - intensity, 0)
        return result
    
    @staticmethod
    def sketch(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """素描效果"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 创建素描效果
        gray_blur = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                     cv2.THRESH_BINARY, 9, 9)
        
        # 反转并混合
        sketch = cv2.bitwise_not(edges)
        result = cv2.addWeighted(gray, 1 - intensity, sketch, intensity, 0)
        return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

class VintageFilter:
    """复古滤镜"""
    
    @staticmethod
    def sepia(frame: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """棕褐色效果"""
        # 棕褐色转换矩阵
        sepia_matrix = np.array([[0.272, 0.534, 0.131],
                                [0.349, 0.686, 0.168],
                                [0.393, 0.769, 0.189]])
        
        sepia_frame = cv2.transform(frame, sepia_matrix)
        sepia_frame = np.clip(sepia_frame, 0, 255).astype(np.uint8)
        
        # 混合原图
        result = cv2.addWeighted(frame, 1 - intensity, sepia_frame, intensity, 0)
        return result
    
    @staticmethod
    def film_grain(frame: np.ndarray, intensity: float = 0.3) -> np.ndarray:
        """胶片颗粒效果"""
        height, width = frame.shape[:2]
        
        # 生成噪声
        noise = np.random.normal(0, intensity * 255, (height, width, 3))
        
        # 添加噪声
        result = frame.astype(np.float32) + noise
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    @staticmethod
    def aged_film(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """老电影效果"""
        # 棕褐色效果
        sepia = VintageFilter.sepia(frame, intensity)
        
        # 添加颗粒
        grain = VintageFilter.film_grain(sepia, intensity * 0.3)
        
        # 添加暗角
        vignette = LightEffectsFilter.vignette(grain, intensity * 0.5)
        
        # 降低对比度
        alpha = 1.0 - intensity * 0.3
        beta = intensity * 20
        result = cv2.convertScaleAbs(vignette, alpha=alpha, beta=beta)
        
        return result
    
    @staticmethod
    def cross_process(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """交叉冲洗效果"""
        # 转换为LAB色彩空间
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 调整曲线
        l = cv2.addWeighted(l, 1.2, np.zeros_like(l), 0, -20)
        a = cv2.addWeighted(a, 1.5, np.zeros_like(a), 0, -30)
        b = cv2.addWeighted(b, 0.8, np.zeros_like(b), 0, 20)
        
        # 合并通道
        lab = cv2.merge([l, a, b])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 混合原图
        return cv2.addWeighted(frame, 1 - intensity, result, intensity, 0)

class FilterManager:
    """滤镜管理器"""
    
    def __init__(self):
        self.presets = self._create_presets()
        self.custom_filters = {}
    
    def _create_presets(self) -> Dict[str, Dict[str, Any]]:
        """创建滤镜预设"""
        presets = {
            FilterPreset.ORIGINAL: {
                'name': '原图',
                'description': '原始画面',
                'parameters': {}
            },
            FilterPreset.VIVID: {
                'name': '鲜艳',
                'description': '增强色彩饱和度和对比度',
                'parameters': {
                    'saturation': 30,
                    'contrast': 20,
                    'brightness': 10
                }
            },
            FilterPreset.DRAMATIC: {
                'name': '戏剧化',
                'description': '高对比度戏剧效果',
                'parameters': {
                    'contrast': 50,
                    'vignette_intensity': 0.3,
                    'shadows': -20,
                    'highlights': 30
                }
            },
            FilterPreset.SOFT: {
                'name': '柔和',
                'description': '柔和梦幻效果',
                'parameters': {
                    'blur': 3,
                    'brightness': 10,
                    'contrast': -10
                }
            },
            FilterPreset.COLD: {
                'name': '冷色调',
                'description': '蓝色调冷色效果',
                'parameters': {
                    'temperature': -20,
                    'tint': -10,
                    'saturation': -10
                }
            },
            FilterPreset.WARM: {
                'name': '暖色调',
                'description': '橙黄色调暖色效果',
                'parameters': {
                    'temperature': 20,
                    'tint': 10,
                    'saturation': 10
                }
            },
            FilterPreset.BLACK_WHITE: {
                'name': '黑白',
                'description': '经典黑白效果',
                'parameters': {
                    'desaturate': 100,
                    'contrast': 20,
                    'clarity': 30
                }
            },
            FilterPreset.SEPIA: {
                'name': '棕褐色',
                'description': '复古棕褐色效果',
                'parameters': {
                    'sepia_intensity': 100,
                    'vignette_intensity': 0.2,
                    'grain_intensity': 0.1
                }
            },
            FilterPreset.VINTAGE: {
                'name': '复古',
                'description': '老电影复古效果',
                'parameters': {
                    'aged_film_intensity': 0.8,
                    'vignette_intensity': 0.4,
                    'grain_intensity': 0.3
                }
            },
            FilterPreset.NOIR: {
                'name': '黑色电影',
                'description': '高对比度黑白电影效果',
                'parameters': {
                    'desaturate': 100,
                    'contrast': 60,
                    'vignette_intensity': 0.5,
                    'clarity': 40
                }
            },
            FilterPreset.CINEMATIC: {
                'name': '电影感',
                'description': '电影级调色效果',
                'parameters': {
                    'contrast': 25,
                    'saturation': -15,
                    'vignette_intensity': 0.3,
                    'film_grain': 0.15,
                    'color_grading': {
                        'lift': (0.02, 0.01, 0.03),
                        'gamma': (0.95, 1.05, 1.1),
                        'gain': (1.1, 1.05, 0.95)
                    }
                }
            }
        }
        return presets
    
    def apply_preset(self, frame: np.ndarray, preset_name: str) -> np.ndarray:
        """应用滤镜预设"""
        if preset_name not in self.presets:
            return frame
        
        preset = self.presets[preset_name]
        parameters = preset['parameters']
        
        result = frame.copy()
        
        # 应用基本调整
        if 'brightness' in parameters:
            result = self._adjust_brightness(result, parameters['brightness'])
        if 'contrast' in parameters:
            result = self._adjust_contrast(result, parameters['contrast'])
        if 'saturation' in parameters:
            result = self._adjust_saturation(result, parameters['saturation'])
        if 'desaturate' in parameters:
            result = self._adjust_saturation(result, -parameters['desaturate'])
        
        # 应用特效
        if 'vignette_intensity' in parameters:
            result = LightEffectsFilter.vignette(result, parameters['vignette_intensity'])
        if 'sepia_intensity' in parameters:
            result = VintageFilter.sepia(result, parameters['sepia_intensity'] / 100.0)
        if 'grain_intensity' in parameters:
            result = VintageFilter.film_grain(result, parameters['grain_intensity'])
        if 'aged_film_intensity' in parameters:
            result = VintageFilter.aged_film(result, parameters['aged_film_intensity'])
        
        # 应用色彩分级
        if 'color_grading' in parameters:
            color_params = parameters['color_grading']
            result = ColorGradingFilter.lift_gamma_gain(
                result, 
                color_params['lift'],
                color_params['gamma'],
                color_params['gain']
            )
        
        return result
    
    def _adjust_brightness(self, frame: np.ndarray, value: int) -> np.ndarray:
        """调整亮度"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + value, 0, 255)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def _adjust_contrast(self, frame: np.ndarray, value: int) -> np.ndarray:
        """调整对比度"""
        alpha = 1.0 + (value / 100.0)
        beta = 0
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
    
    def _adjust_saturation(self, frame: np.ndarray, value: int) -> np.ndarray:
        """调整饱和度"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + value, 0, 255)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def create_custom_filter(self, name: str, parameters: Dict[str, Any]) -> bool:
        """创建自定义滤镜"""
        try:
            self.custom_filters[name] = {
                'name': name,
                'parameters': parameters,
                'created_at': time.time()
            }
            return True
        except Exception as e:
            print(f"创建自定义滤镜失败: {e}")
            return False
    
    def get_preset_list(self) -> List[Dict[str, Any]]:
        """获取滤镜预设列表"""
        preset_list = []
        for preset_enum, preset_data in self.presets.items():
            preset_list.append({
                'id': preset_enum.value,
                'name': preset_data['name'],
                'description': preset_data['description']
            })
        return preset_list
    
    def get_custom_filter_list(self) -> List[Dict[str, Any]]:
        """获取自定义滤镜列表"""
        filter_list = []
        for name, filter_data in self.custom_filters.items():
            filter_list.append({
                'id': name,
                'name': filter_data['name'],
                'created_at': filter_data['created_at']
            })
        return filter_list

# 全局滤镜管理器实例
filter_manager = FilterManager()