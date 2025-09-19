#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业特效引擎核心类
基于PyQt6、OpenGL、FFmpeg和OpenCV的高性能特效处理系统
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
import threading
import time
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional OpenGL imports for GPU acceleration
try:
    import OpenGL.GL as gl
    import OpenGL.GLU as glu
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    gl = None
    glu = None

class EffectType(Enum):
    """特效类型枚举"""
    FILTER = "filter"              # 滤镜效果
    TRANSITION = "transition"      # 转场效果
    ANIMATION = "animation"        # 动画效果
    TEXT_EFFECT = "text_effect"    # 文字效果
    COLOR_CORRECTION = "color_correction"  # 调色效果
    AUDIO_EFFECT = "audio_effect"  # 音频效果
    STABILIZATION = "stabilization"  # 防抖效果

class RenderMode(Enum):
    """渲染模式"""
    CPU = "cpu"
    GPU_OPENGL = "gpu_opengl"
    GPU_CUDA = "gpu_cuda"

@dataclass
class EffectParameter:
    """特效参数"""
    name: str
    value: Any
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    description: str = ""
    keyframe_support: bool = True

@dataclass
class Keyframe:
    """关键帧"""
    time: float  # 时间位置（秒）
    parameters: Dict[str, float]  # 参数值
    easing: str = "linear"  # 缓动函数

class EffectsEngine(QObject):
    """专业特效引擎"""
    
    # 信号定义
    effect_applied = pyqtSignal(str, bool)  # 特效应用完成信号
    render_progress = pyqtSignal(int)  # 渲染进度信号
    preview_updated = pyqtSignal(object)  # 预览更新信号
    
    def __init__(self):
        super().__init__()
        self.effect_registry = {}
        self.active_effects = {}
        self.render_mode = RenderMode.CPU
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.is_rendering = False
        self.render_cancel_flag = False
        
        # OpenGL上下文
        self.gl_context = None
        self.gl_programs = {}
        
        # 初始化特效系统
        self._initialize_effects()
        self._initialize_opengl()
    
    def _initialize_effects(self):
        """初始化特效系统"""
        # 注册内置特效
        # 滤镜效果
        self.register_effect("brightness", self._apply_brightness, EffectType.FILTER)
        self.register_effect("contrast", self._apply_contrast, EffectType.FILTER)
        self.register_effect("saturation", self._apply_saturation, EffectType.FILTER)
        self.register_effect("blur", self._apply_blur, EffectType.FILTER)
        self.register_effect("sharpen", self._apply_sharpen, EffectType.FILTER)
        self.register_effect("grayscale", self._apply_grayscale, EffectType.FILTER)
        self.register_effect("sepia", self._apply_sepia, EffectType.FILTER)
        self.register_effect("vintage", self._apply_vintage, EffectType.FILTER)
        self.register_effect("cool", self._apply_cool, EffectType.FILTER)
        self.register_effect("warm", self._apply_warm, EffectType.FILTER)
        self.register_effect("dramatic", self._apply_dramatic, EffectType.FILTER)
        
        # 转场效果
        self.register_effect("fade", self._apply_fade, EffectType.TRANSITION)
        self.register_effect("slide", self._apply_slide, EffectType.TRANSITION)
        self.register_effect("dissolve", self._apply_dissolve, EffectType.TRANSITION)
        self.register_effect("wipe", self._apply_wipe, EffectType.TRANSITION)
        self.register_effect("circle", self._apply_circle, EffectType.TRANSITION)
        
        # 动画效果
        self.register_effect("zoom", self._apply_zoom, EffectType.ANIMATION)
        self.register_effect("rotate", self._apply_rotate, EffectType.ANIMATION)
        self.register_effect("pan", self._apply_pan, EffectType.ANIMATION)
        self.register_effect("bounce", self._apply_bounce, EffectType.ANIMATION)
        
        # 调色效果
        self.register_effect("white_balance", self._apply_white_balance, EffectType.COLOR_CORRECTION)
        self.register_effect("exposure", self._apply_exposure, EffectType.COLOR_CORRECTION)
        self.register_effect("gamma", self._apply_gamma, EffectType.COLOR_CORRECTION)
        self.register_effect("hue_shift", self._apply_hue_shift, EffectType.COLOR_CORRECTION)
        self.register_effect("color_grading", self._apply_color_grading, EffectType.COLOR_CORRECTION)
        
        # 文字效果
        self.register_effect("text_fade", self._apply_text_fade, EffectType.TEXT_EFFECT)
        self.register_effect("text_slide", self._apply_text_slide, EffectType.TEXT_EFFECT)
        self.register_effect("text_zoom", self._apply_text_zoom, EffectType.TEXT_EFFECT)
        self.register_effect("text_typewriter", self._apply_text_typewriter, EffectType.TEXT_EFFECT)
    
    def _initialize_opengl(self):
        """初始化OpenGL"""
        if not OPENGL_AVAILABLE:
            print("OpenGL不可用，使用CPU渲染模式")
            self.render_mode = RenderMode.CPU
            return
            
        try:
            # 创建着色器程序
            self._create_shader_programs()
            self.render_mode = RenderMode.GPU_OPENGL
        except Exception as e:
            print(f"OpenGL初始化失败: {e}")
            self.render_mode = RenderMode.CPU
    
    def _create_shader_programs(self):
        """创建OpenGL着色器程序"""
        if not OPENGL_AVAILABLE:
            return
            
        # 基础顶点着色器
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec2 aPos;
        layout (location = 1) in vec2 aTexCoord;
        out vec2 TexCoord;
        
        void main() {
            gl_Position = vec4(aPos, 0.0, 1.0);
            TexCoord = aTexCoord;
        }
        """
        
        # 基础片段着色器
        fragment_shader_source = """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        uniform sampler2D screenTexture;
        
        void main() {
            FragColor = texture(screenTexture, TexCoord);
        }
        """
        
        # 编译着色器
        vertex_shader = self._compile_shader(gl.GL_VERTEX_SHADER, vertex_shader_source)
        fragment_shader = self._compile_shader(gl.GL_FRAGMENT_SHADER, fragment_shader_source)
        
        # 创建程序
        program = gl.glCreateProgram()
        gl.glAttachShader(program, vertex_shader)
        gl.glAttachShader(program, fragment_shader)
        gl.glLinkProgram(program)
        
        self.gl_programs['basic'] = program
    
    def _compile_shader(self, shader_type: int, source: str) -> int:
        """编译着色器"""
        if not OPENGL_AVAILABLE:
            raise Exception("OpenGL不可用")
            
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        
        # 检查编译状态
        if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
            info_log = gl.glGetShaderInfoLog(shader)
            raise Exception(f"着色器编译失败: {info_log}")
        
        return shader
    
    def register_effect(self, name: str, effect_func: Callable, effect_type: EffectType):
        """注册特效"""
        self.effect_registry[name] = {
            'function': effect_func,
            'type': effect_type,
            'parameters': self._get_default_parameters(name, effect_type)
        }
    
    def _get_default_parameters(self, name: str, effect_type: EffectType) -> List[EffectParameter]:
        """获取默认参数"""
        parameters = []
        
        if effect_type == EffectType.FILTER:
            if name == "brightness":
                parameters.append(EffectParameter("intensity", 0.0, -100.0, 100.0, 1.0, "亮度调整"))
            elif name == "contrast":
                parameters.append(EffectParameter("intensity", 0.0, -100.0, 100.0, 1.0, "对比度调整"))
            elif name == "saturation":
                parameters.append(EffectParameter("intensity", 0.0, -100.0, 100.0, 1.0, "饱和度调整"))
            elif name == "blur":
                parameters.append(EffectParameter("radius", 5.0, 0.0, 50.0, 1.0, "模糊半径"))
            elif name == "sharpen":
                parameters.append(EffectParameter("intensity", 0.0, 0.0, 100.0, 1.0, "锐化强度"))
        
        elif effect_type == EffectType.TRANSITION:
            if name == "fade":
                parameters.append(EffectParameter("duration", 1.0, 0.1, 5.0, 0.1, "持续时间"))
            elif name == "slide":
                parameters.append(EffectParameter("direction", 0, 0, 3, 1, "滑动方向"))
                parameters.append(EffectParameter("duration", 1.0, 0.1, 5.0, 0.1, "持续时间"))
        
        elif effect_type == EffectType.ANIMATION:
            if name == "zoom":
                parameters.append(EffectParameter("scale", 1.0, 0.1, 5.0, 0.1, "缩放比例"))
                parameters.append(EffectParameter("duration", 2.0, 0.1, 10.0, 0.1, "持续时间"))
            elif name == "rotate":
                parameters.append(EffectParameter("angle", 0.0, -360.0, 360.0, 1.0, "旋转角度"))
                parameters.append(EffectParameter("duration", 2.0, 0.1, 10.0, 0.1, "持续时间"))
        
        return parameters
    
    def apply_effect(self, effect_name: str, frame: np.ndarray, 
                    parameters: Dict[str, Any] = None, 
                    keyframes: List[Keyframe] = None) -> np.ndarray:
        """应用特效到单帧"""
        if effect_name not in self.effect_registry:
            raise ValueError(f"未知的特效: {effect_name}")
        
        effect_data = self.effect_registry[effect_name]
        effect_func = effect_data['function']
        
        # 处理关键帧
        if keyframes and parameters:
            parameters = self._interpolate_keyframes(keyframes, parameters)
        
        # 应用特效
        if self.render_mode == RenderMode.GPU_OPENGL:
            result = self._apply_effect_gpu(effect_func, frame, parameters)
        else:
            result = effect_func(frame, parameters or {})
        
        return result
    
    def _apply_effect_gpu(self, effect_func: Callable, frame: np.ndarray, 
                         parameters: Dict[str, Any]) -> np.ndarray:
        """GPU加速特效处理"""
        # 这里实现GPU加速处理逻辑
        # 由于OpenGL需要特定的上下文，这里简化实现
        return effect_func(frame, parameters)
    
    def _interpolate_keyframes(self, keyframes: List[Keyframe], 
                             current_params: Dict[str, Any]) -> Dict[str, Any]:
        """关键帧插值"""
        # 简化的关键帧插值实现
        return current_params
    
    def render_effects(self, video_path: str, output_path: str, 
                      effects_config: List[Dict[str, Any]]) -> bool:
        """渲染特效到完整视频"""
        self.is_rendering = True
        self.render_cancel_flag = False
        
        try:
            # 使用线程池并行处理
            futures = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                future = executor.submit(self._render_video_thread, 
                                       video_path, output_path, effects_config)
                futures.append(future)
                
                # 等待完成
                for future in as_completed(futures):
                    if self.render_cancel_flag:
                        break
                    result = future.result()
                    if result:
                        self.effect_applied.emit(output_path, True)
                        return True
            
            return False
            
        except Exception as e:
            print(f"渲染失败: {e}")
            self.effect_applied.emit(output_path, False)
            return False
        finally:
            self.is_rendering = False
    
    def _render_video_thread(self, video_path: str, output_path: str, 
                           effects_config: List[Dict[str, Any]]) -> bool:
        """视频渲染线程"""
        try:
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 创建输出视频
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            processed_frames = 0
            while True:
                if self.render_cancel_flag:
                    break
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 应用特效
                for effect_config in effects_config:
                    effect_name = effect_config['name']
                    parameters = effect_config.get('parameters', {})
                    keyframes = effect_config.get('keyframes', [])
                    
                    frame = self.apply_effect(effect_name, frame, parameters, keyframes)
                
                # 写入输出
                out.write(frame)
                processed_frames += 1
                
                # 更新进度
                progress = int((processed_frames / frame_count) * 100)
                self.render_progress.emit(progress)
                
                # 发送预览更新
                if processed_frames % 30 == 0:  # 每30帧更新一次预览
                    self.preview_updated.emit(frame.copy())
            
            # 清理
            cap.release()
            out.release()
            
            return True
            
        except Exception as e:
            print(f"渲染线程错误: {e}")
            return False
    
    def cancel_render(self):
        """取消渲染"""
        self.render_cancel_flag = True
    
    def get_effect_parameters(self, effect_name: str) -> List[EffectParameter]:
        """获取特效参数"""
        if effect_name not in self.effect_registry:
            return []
        return self.effect_registry[effect_name]['parameters']
    
    def preview_effect(self, effect_name: str, frame: np.ndarray, 
                      parameters: Dict[str, Any]) -> np.ndarray:
        """预览特效"""
        return self.apply_effect(effect_name, frame, parameters)
    
    def create_effect_template(self, name: str, effects_config: List[Dict[str, Any]]) -> bool:
        """创建特效模板"""
        try:
            # 这里实现模板保存逻辑
            return True
        except Exception as e:
            print(f"创建模板失败: {e}")
            return False
    
    def load_effect_template(self, template_name: str) -> List[Dict[str, Any]]:
        """加载特效模板"""
        try:
            # 这里实现模板加载逻辑
            return []
        except Exception as e:
            print(f"加载模板失败: {e}")
            return []
    
    # 特效实现函数
    def _apply_brightness(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用亮度调整"""
        intensity = params.get('intensity', 0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + intensity, 0, 255)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def _apply_contrast(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用对比度调整"""
        intensity = params.get('intensity', 0)
        alpha = 1.0 + (intensity / 100.0)
        beta = 0
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
    
    def _apply_saturation(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用饱和度调整"""
        intensity = params.get('intensity', 0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + intensity, 0, 255)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def _apply_blur(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用模糊效果"""
        radius = int(params.get('radius', 5))
        if radius <= 0:
            return frame
        return cv2.GaussianBlur(frame, (radius*2+1, radius*2+1), 0)
    
    def _apply_sharpen(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用锐化效果"""
        intensity = params.get('intensity', 0)
        if intensity <= 0:
            return frame
        
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1],
                          [-1, -1, -1]]) * (intensity / 100.0)
        kernel[1, 1] = 9 - 8 * (intensity / 100.0)
        
        return cv2.filter2D(frame, -1, kernel)
    
    def _apply_fade(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用淡入淡出效果"""
        # 简化的淡入淡出实现
        alpha = params.get('alpha', 1.0)
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
    
    def _apply_slide(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用滑动效果"""
        # 简化的滑动实现
        return frame
    
    def _apply_zoom(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用缩放效果"""
        scale = params.get('scale', 1.0)
        if scale == 1.0:
            return frame
        
        height, width = frame.shape[:2]
        new_size = (int(width * scale), int(height * scale))
        
        if scale > 1.0:
            # 放大后裁剪
            zoomed = cv2.resize(frame, new_size)
            start_x = (zoomed.shape[1] - width) // 2
            start_y = (zoomed.shape[0] - height) // 2
            return zoomed[start_y:start_y+height, start_x:start_x+width]
        else:
            # 缩小后填充
            zoomed = cv2.resize(frame, new_size)
            result = np.zeros((height, width, 3), dtype=np.uint8)
            start_x = (width - zoomed.shape[1]) // 2
            start_y = (height - zoomed.shape[0]) // 2
            result[start_y:start_y+zoomed.shape[0], start_x:start_x+zoomed.shape[1]] = zoomed
            return result
    
    def _apply_rotate(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用旋转效果"""
        angle = params.get('angle', 0)
        if angle == 0:
            return frame
        
        height, width = frame.shape[:2]
        center = (width // 2, height // 2)
        
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(frame, rotation_matrix, (width, height))
        
        return rotated
    
    # 新增滤镜效果
    def _apply_grayscale(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用灰度效果"""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    def _apply_sepia(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用复古褐色效果"""
        kernel = np.array([[0.272, 0.534, 0.131],
                          [0.349, 0.686, 0.168],
                          [0.393, 0.769, 0.189]])
        sepia_frame = cv2.transform(frame, kernel)
        return np.clip(sepia_frame, 0, 255).astype(np.uint8)
    
    def _apply_vintage(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用复古效果"""
        # 降低饱和度
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.6
        vintage_frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # 添加轻微的褐色调
        vintage_frame = self._apply_sepia(vintage_frame, {})
        
        # 添加噪点
        noise = np.random.normal(0, 10, vintage_frame.shape)
        vintage_frame = np.clip(vintage_frame + noise, 0, 255).astype(np.uint8)
        
        return vintage_frame
    
    def _apply_cool(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用冷色调"""
        # 增加蓝色通道，减少红色通道
        cool_frame = frame.copy()
        cool_frame[:, :, 0] = np.clip(cool_frame[:, :, 0] * 1.2, 0, 255)  # 蓝色
        cool_frame[:, :, 2] = np.clip(cool_frame[:, :, 2] * 0.8, 0, 255)  # 红色
        return cool_frame
    
    def _apply_warm(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用暖色调"""
        # 增加红色通道，减少蓝色通道
        warm_frame = frame.copy()
        warm_frame[:, :, 2] = np.clip(warm_frame[:, :, 2] * 1.2, 0, 255)  # 红色
        warm_frame[:, :, 0] = np.clip(warm_frame[:, :, 0] * 0.8, 0, 255)  # 蓝色
        return warm_frame
    
    def _apply_dramatic(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用戏剧化效果"""
        # 高对比度 + 低饱和度
        dramatic_frame = self._apply_contrast(frame, {'intensity': 50})
        hsv = cv2.cvtColor(dramatic_frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.7
        dramatic_frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return dramatic_frame
    
    # 新增转场效果
    def _apply_dissolve(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用溶解效果"""
        alpha = params.get('alpha', 0.5)
        # 简化的溶解实现
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
    
    def _apply_wipe(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用擦除效果"""
        progress = params.get('progress', 0.5)
        direction = params.get('direction', 'left')
        
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if direction == 'left':
            wipe_x = int(width * progress)
            mask[:, :wipe_x] = 255
        elif direction == 'right':
            wipe_x = int(width * (1 - progress))
            mask[:, wipe_x:] = 255
        elif direction == 'up':
            wipe_y = int(height * progress)
            mask[:wipe_y, :] = 255
        elif direction == 'down':
            wipe_y = int(height * (1 - progress))
            mask[wipe_y:, :] = 255
        
        # 应用遮罩
        result = frame.copy()
        result[mask == 0] = 0
        
        return result
    
    def _apply_circle(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用圆形转场效果"""
        progress = params.get('progress', 0.5)
        
        height, width = frame.shape[:2]
        center = (width // 2, height // 2)
        max_radius = int(min(width, height) / 2)
        current_radius = int(max_radius * progress)
        
        # 创建圆形遮罩
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, center, current_radius, 255, -1)
        
        # 应用遮罩
        result = frame.copy()
        result[mask == 0] = 0
        
        return result
    
    # 新增动画效果
    def _apply_pan(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用平移效果"""
        offset_x = params.get('offset_x', 0)
        offset_y = params.get('offset_y', 0)
        
        height, width = frame.shape[:2]
        
        # 创建平移矩阵
        translation_matrix = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
        panned = cv2.warpAffine(frame, translation_matrix, (width, height))
        
        return panned
    
    def _apply_bounce(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用弹跳效果"""
        time = params.get('time', 0.0)
        amplitude = params.get('amplitude', 50)
        frequency = params.get('frequency', 2.0)
        
        # 计算弹跳偏移
        offset_y = int(amplitude * abs(np.sin(frequency * time * np.pi)))
        
        return self._apply_pan(frame, {'offset_x': 0, 'offset_y': offset_y})
    
    # 新增调色效果
    def _apply_white_balance(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用白平衡调整"""
        temperature = params.get('temperature', 0)  # -100 到 100
        
        # 简化的白平衡实现
        balanced_frame = frame.copy().astype(np.float32)
        
        if temperature > 0:  # 暖色
            balanced_frame[:, :, 2] *= 1.0 + temperature / 200.0  # 增加红色
            balanced_frame[:, :, 0] *= 1.0 - temperature / 400.0  # 减少蓝色
        else:  # 冷色
            balanced_frame[:, :, 0] *= 1.0 + abs(temperature) / 200.0  # 增加蓝色
            balanced_frame[:, :, 2] *= 1.0 - abs(temperature) / 400.0  # 减少红色
        
        return np.clip(balanced_frame, 0, 255).astype(np.uint8)
    
    def _apply_exposure(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用曝光调整"""
        exposure = params.get('exposure', 0.0)  # -2.0 到 2.0
        
        # 转换为浮点数进行调整
        frame_float = frame.astype(np.float32)
        frame_float = frame_float * (2 ** exposure)
        
        return np.clip(frame_float, 0, 255).astype(np.uint8)
    
    def _apply_gamma(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用伽马调整"""
        gamma = params.get('gamma', 1.0)  # 0.1 到 3.0
        
        # 归一化到0-1
        normalized = frame.astype(np.float32) / 255.0
        
        # 应用伽马校正
        corrected = np.power(normalized, 1.0 / gamma)
        
        # 转换回0-255
        return (corrected * 255).astype(np.uint8)
    
    def _apply_hue_shift(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用色相偏移"""
        hue_shift = params.get('hue_shift', 0)  # -180 到 180
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    def _apply_color_grading(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用调色分级"""
        shadows = params.get('shadows', [0, 0, 0])  # 阴影RGB调整
        midtones = params.get('midtones', [0, 0, 0])  # 中间调RGB调整
        highlights = params.get('highlights', [0, 0, 0])  # 高光RGB调整
        
        # 简化的调色分级实现
        graded_frame = frame.copy().astype(np.float32)
        
        # 应用不同亮度区域的调整
        luminance = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        shadow_mask = luminance < 85
        midtone_mask = (luminance >= 85) & (luminance < 170)
        highlight_mask = luminance >= 170
        
        for i in range(3):  # RGB通道
            graded_frame[:, :, i][shadow_mask] += shadows[i]
            graded_frame[:, :, i][midtone_mask] += midtones[i]
            graded_frame[:, :, i][highlight_mask] += highlights[i]
        
        return np.clip(graded_frame, 0, 255).astype(np.uint8)
    
    # 新增文字效果
    def _apply_text_fade(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用文字淡入淡出效果"""
        text = params.get('text', 'Sample Text')
        position = params.get('position', (50, 50))
        alpha = params.get('alpha', 1.0)
        font = params.get('font', cv2.FONT_HERSHEY_SIMPLEX)
        font_scale = params.get('font_scale', 1.0)
        color = params.get('color', (255, 255, 255))
        
        result = frame.copy()
        # 应用透明度
        overlay = result.copy()
        cv2.putText(overlay, text, position, font, font_scale, color, 2)
        
        # 混合原图和文字层
        result = cv2.addWeighted(result, 1.0 - alpha, overlay, alpha, 0)
        
        return result
    
    def _apply_text_slide(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用文字滑动效果"""
        text = params.get('text', 'Sample Text')
        start_pos = params.get('start_pos', (50, 50))
        end_pos = params.get('end_pos', (400, 50))
        progress = params.get('progress', 0.5)
        
        # 计算当前位置
        current_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * progress)
        current_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * progress)
        
        result = frame.copy()
        cv2.putText(result, text, (current_x, current_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        return result
    
    def _apply_text_zoom(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用文字缩放效果"""
        text = params.get('text', 'Sample Text')
        position = params.get('position', (50, 50))
        scale = params.get('scale', 1.0)
        
        result = frame.copy()
        cv2.putText(result, text, position, 
                   cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2)
        
        return result
    
    def _apply_text_typewriter(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """应用打字机效果"""
        text = params.get('text', 'Sample Text')
        position = params.get('position', (50, 50))
        progress = params.get('progress', 0.5)
        
        # 计算显示的文字长度
        display_length = int(len(text) * progress)
        display_text = text[:display_length]
        
        result = frame.copy()
        cv2.putText(result, display_text, position, 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        return result