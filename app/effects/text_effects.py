#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业文字效果系统
包含各种字幕样式、动画效果和模板应用
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
import math
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

class TextEffectType(Enum):
    """文字效果类型"""
    BASIC = "basic"
    OUTLINE = "outline"
    SHADOW = "shadow"
    GLOW = "glow"
    GRADIENT = "gradient"
    NEON = "neon"
    METALLIC = "metallic"
    FIRE = "fire"
    ICE = "ice"
    RAINBOW = "rainbow"
    HOLOGRAPHIC = "holographic"
    3D = "3d"
    TYPING = "typing"
    FADE_IN = "fade_in"
    SLIDE_IN = "slide_in"
    BOUNCE = "bounce"
    WAVE = "wave"
    PARTICLE = "particle"

class TextAlign(Enum):
    """文本对齐方式"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"

class TextAnimationType(Enum):
    """文字动画类型"""
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
    BOUNCE = "bounce"
    ROTATE = "rotate"
    SCALE = "scale"
    TYPING = "typing"
    WAVE = "wave"
    GLOW = "glow"
    RAINBOW = "rainbow"
    PARTICLE = "particle"
    MAGNETIC = "magnetic"
    ZOOM = "zoom"
    FLIP = "flip"

@dataclass
class TextStyle:
    """文字样式"""
    font_family: str = "Arial"
    font_size: int = 48
    font_color: Tuple[int, int, int] = (255, 255, 255)
    background_color: Tuple[int, int, int] = (0, 0, 0, 0)
    outline_color: Tuple[int, int, int] = (0, 0, 0)
    outline_width: int = 0
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_blur: int = 0
    glow_color: Tuple[int, int, int] = (255, 255, 255)
    glow_size: int = 0
    gradient_colors: List[Tuple[int, int, int]] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    letter_spacing: int = 0
    line_spacing: float = 1.0
    opacity: float = 1.0
    blend_mode: str = "normal"

@dataclass
class TextAnimation:
    """文字动画"""
    animation_type: TextAnimationType
    duration: float = 1.0
    delay: float = 0.0
    easing: str = "linear"
    loop: bool = False
    parameters: Dict[str, Any] = None

@dataclass
class TextLayer:
    """文字图层"""
    text: str
    style: TextStyle
    position: Tuple[int, int]
    rotation: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0
    animation: TextAnimation = None
    is_visible: bool = True
    blend_mode: str = "normal"

class TextEffectEngine:
    """文字效果引擎"""
    
    def __init__(self):
        self.font_cache = {}
        self.effect_presets = self._create_effect_presets()
        self.animation_presets = self._create_animation_presets()
        self.text_templates = self._create_text_templates()
    
    def _create_effect_presets(self) -> Dict[str, Dict[str, Any]]:
        """创建效果预设"""
        return {
            "basic_white": {
                "name": "基础白色",
                "style": TextStyle(
                    font_color=(255, 255, 255),
                    font_size=48
                )
            },
            "neon_blue": {
                "name": "霓虹蓝",
                "style": TextStyle(
                    font_color=(100, 200, 255),
                    glow_color=(100, 200, 255),
                    glow_size=10,
                    outline_color=(0, 100, 200),
                    outline_width=2
                )
            },
            "fire_text": {
                "name": "火焰文字",
                "style": TextStyle(
                    font_color=(255, 200, 0),
                    glow_color=(255, 100, 0),
                    glow_size=15,
                    outline_color=(255, 0, 0),
                    outline_width=3
                )
            },
            "ice_text": {
                "name": "冰霜文字",
                "style": TextStyle(
                    font_color=(200, 230, 255),
                    glow_color=(150, 200, 255),
                    glow_size=12,
                    outline_color=(100, 150, 255),
                    outline_width=2
                )
            },
            "gold_text": {
                "name": "金色文字",
                "style": TextStyle(
                    font_color=(255, 215, 0),
                    glow_color=(255, 200, 0),
                    glow_size=8,
                    outline_color=(200, 150, 0),
                    outline_width=2
                )
            },
            "rainbow_text": {
                "name": "彩虹文字",
                "style": TextStyle(
                    gradient_colors=[
                        (255, 0, 0), (255, 127, 0), (255, 255, 0),
                        (0, 255, 0), (0, 0, 255), (139, 0, 255)
                    ],
                    font_size=48
                )
            },
            "3d_text": {
                "name": "3D文字",
                "style": TextStyle(
                    font_color=(255, 255, 255),
                    shadow_color=(100, 100, 100),
                    shadow_offset=(5, 5),
                    shadow_blur=3,
                    outline_color=(50, 50, 50),
                    outline_width=2
                )
            },
            "vintage_text": {
                "name": "复古文字",
                "style": TextStyle(
                    font_color=(200, 180, 140),
                    outline_color=(100, 80, 40),
                    outline_width=1,
                    font_size=36
                )
            },
            "cyberpunk": {
                "name": "赛博朋克",
                "style": TextStyle(
                    font_color=(0, 255, 255),
                    glow_color=(255, 0, 255),
                    glow_size=20,
                    outline_color=(255, 0, 0),
                    outline_width=2
                )
            },
            "holographic": {
                "name": "全息文字",
                "style": TextStyle(
                    font_color=(200, 255, 200),
                    glow_color=(100, 255, 100),
                    glow_size=15,
                    opacity=0.8
                )
            }
        }
    
    def _create_animation_presets(self) -> Dict[str, Dict[str, Any]]:
        """创建动画预设"""
        return {
            "fade_in": {
                "name": "淡入",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.FADE,
                    duration=1.0,
                    easing="ease_in"
                )
            },
            "fade_out": {
                "name": "淡出",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.FADE,
                    duration=1.0,
                    easing="ease_out"
                )
            },
            "slide_in_left": {
                "name": "从左滑入",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.SLIDE,
                    duration=1.0,
                    parameters={"direction": "left"}
                )
            },
            "slide_in_right": {
                "name": "从右滑入",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.SLIDE,
                    duration=1.0,
                    parameters={"direction": "right"}
                )
            },
            "bounce": {
                "name": "弹跳",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.BOUNCE,
                    duration=1.5,
                    easing="bounce"
                )
            },
            "typing": {
                "name": "打字机",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.TYPING,
                    duration=2.0,
                    parameters={"speed": 0.1}
                )
            },
            "wave": {
                "name": "波浪",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.WAVE,
                    duration=2.0,
                    loop=True
                )
            },
            "glow_pulse": {
                "name": "光晕脉冲",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.GLOW,
                    duration=1.0,
                    loop=True
                )
            },
            "rotate": {
                "name": "旋转",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.ROTATE,
                    duration=2.0,
                    loop=True
                )
            },
            "scale": {
                "name": "缩放",
                "animation": TextAnimation(
                    animation_type=TextAnimationType.SCALE,
                    duration=1.0,
                    loop=True
                )
            }
        }
    
    def _create_text_templates(self) -> Dict[str, List[TextLayer]]:
        """创建文字模板"""
        return {
            "title_card": [
                TextLayer(
                    text="主标题",
                    style=TextStyle(
                        font_size=72,
                        font_color=(255, 255, 255),
                        glow_color=(255, 200, 0),
                        glow_size=10,
                        bold=True
                    ),
                    position=(50, 100),
                    animation=TextAnimation(
                        animation_type=TextAnimationType.FADE,
                        duration=1.0
                    )
                ),
                TextLayer(
                    text="副标题",
                    style=TextStyle(
                        font_size=36,
                        font_color=(200, 200, 200),
                        opacity=0.8
                    ),
                    position=(50, 180),
                    animation=TextAnimation(
                        animation_type=TextAnimationType.SLIDE,
                        duration=1.0,
                        delay=0.5,
                        parameters={"direction": "left"}
                    )
                )
            ],
            "subtitle": [
                TextLayer(
                    text="字幕内容",
                    style=TextStyle(
                        font_size=32,
                        font_color=(255, 255, 255),
                        outline_color=(0, 0, 0),
                        outline_width=2,
                        background_color=(0, 0, 0, 128)
                    ),
                    position=(50, 500)
                )
            ],
            "lower_third": [
                TextLayer(
                    text="人物名称",
                    style=TextStyle(
                        font_size=42,
                        font_color=(255, 255, 255),
                        bold=True
                    ),
                    position=(50, 450),
                    animation=TextAnimation(
                        animation_type=TextAnimationType.SLIDE,
                        duration=0.5,
                        parameters={"direction": "left"}
                    )
                ),
                TextLayer(
                    text="职位描述",
                    style=TextStyle(
                        font_size=28,
                        font_color=(200, 200, 200)
                    ),
                    position=(50, 500),
                    animation=TextAnimation(
                        animation_type=TextAnimationType.SLIDE,
                        duration=0.5,
                        delay=0.2,
                        parameters={"direction": "left"}
                    )
                )
            ],
            "end_credits": [
                TextLayer(
                    text="制作人员",
                    style=TextStyle(
                        font_size=48,
                        font_color=(255, 255, 255),
                        bold=True
                    ),
                    position=(50, 200)
                ),
                TextLayer(
                    text="导演：XXX",
                    style=TextStyle(
                        font_size=32,
                        font_color=(200, 200, 200)
                    ),
                    position=(50, 300)
                ),
                TextLayer(
                    text="摄影：XXX",
                    style=TextStyle(
                        font_size=32,
                        font_color=(200, 200, 200)
                    ),
                    position=(50, 350)
                ),
                TextLayer(
                    text="剪辑：XXX",
                    style=TextStyle(
                        font_size=32,
                        font_color=(200, 200, 200)
                    ),
                    position=(50, 400)
                )
            ]
        }
    
    def render_text(self, text: str, style: TextStyle, position: Tuple[int, int],
                   animation: TextAnimation = None, current_time: float = 0.0) -> np.ndarray:
        """渲染文字"""
        # 创建PIL图像
        img_size = (1920, 1080)  # 默认尺寸
        pil_image = Image.new('RGBA', img_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_image)
        
        # 获取字体
        font = self._get_font(style)
        
        # 计算文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 处理多行文本
        lines = text.split('\n')
        line_height = int(text_height * style.line_spacing)
        
        # 渲染每一行
        for i, line in enumerate(lines):
            y_offset = i * line_height
            line_position = (position[0], position[1] + y_offset)
            
            # 应用动画
            if animation:
                line = self._apply_text_animation(line, animation, current_time)
            
            # 渲染文字效果
            self._render_text_line(draw, line, font, line_position, style)
        
        # 转换为OpenCV格式
        return np.array(pil_image)
    
    def _render_text_line(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont,
                         position: Tuple[int, int], style: TextStyle):
        """渲染单行文字"""
        x, y = position
        
        # 渲染阴影
        if style.shadow_blur > 0 or style.shadow_offset != (0, 0):
            shadow_x = x + style.shadow_offset[0]
            shadow_y = y + style.shadow_offset[1]
            
            # 创建阴影层
            shadow_layer = Image.new('RGBA', (2000, 2000), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_draw.text((shadow_x, shadow_y), text, font=font, fill=style.shadow_color)
            
            # 应用模糊
            if style.shadow_blur > 0:
                shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(style.shadow_blur))
            
            # 合并阴影
            draw.bitmap((0, 0), shadow_layer.convert('1'), fill=style.shadow_color)
        
        # 渲染光晕
        if style.glow_size > 0:
            for i in range(style.glow_size, 0, -1):
                alpha = int(255 * (i / style.glow_size) * 0.3)
                glow_color = (*style.glow_color, alpha)
                
                # 创建光晕层
                glow_layer = Image.new('RGBA', (2000, 2000), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_layer)
                glow_draw.text((x-i, y-i), text, font=font, fill=glow_color)
                glow_draw.text((x+i, y-i), text, font=font, fill=glow_color)
                glow_draw.text((x-i, y+i), text, font=font, fill=glow_color)
                glow_draw.text((x+i, y+i), text, font=font, fill=glow_color)
                
                # 合并光晕
                draw.bitmap((0, 0), glow_layer.convert('1'), fill=glow_color)
        
        # 渲染轮廓
        if style.outline_width > 0:
            outline_positions = []
            for dx in range(-style.outline_width, style.outline_width + 1):
                for dy in range(-style.outline_width, style.outline_width + 1):
                    if dx == 0 and dy == 0:
                        continue
                    if dx*dx + dy*dy <= style.outline_width * style.outline_width:
                        outline_positions.append((x + dx, y + dy))
            
            for outline_pos in outline_positions:
                draw.text(outline_pos, text, font=font, fill=style.outline_color)
        
        # 渲染主文字
        if style.gradient_colors:
            # 渐变文字
            self._render_gradient_text(draw, text, font, (x, y), style)
        else:
            # 普通文字
            text_color = (*style.font_color, int(255 * style.opacity))
            draw.text((x, y), text, font=font, fill=text_color)
        
        # 渲染下划线
        if style.underline:
            bbox = draw.textbbox((x, y), text, font=font)
            underline_y = bbox[3] + 2
            draw.line([(x, underline_y), (bbox[2], underline_y)], 
                     fill=style.font_color, width=2)
        
        # 渲染删除线
        if style.strikethrough:
            bbox = draw.textbbox((x, y), text, font=font)
            strike_y = y + (bbox[3] - bbox[1]) // 2
            draw.line([(x, strike_y), (bbox[2], strike_y)], 
                     fill=style.font_color, width=2)
    
    def _render_gradient_text(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont,
                            position: Tuple[int, int], style: TextStyle):
        """渲染渐变文字"""
        x, y = position
        bbox = draw.textbbox((x, y), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        # 为每个字符创建渐变
        for i, char in enumerate(text):
            if char == ' ':
                continue
            
            # 计算字符位置
            char_bbox = draw.textbbox((x, y), char, font=font)
            char_x = char_bbox[0]
            char_width = char_bbox[2] - char_bbox[0]
            
            # 计算渐变颜色
            gradient_position = (char_x - x) / text_width
            color_index = int(gradient_position * (len(style.gradient_colors) - 1))
            color_index = max(0, min(color_index, len(style.gradient_colors) - 1))
            
            # 如果在两个颜色之间，进行插值
            if color_index < len(style.gradient_colors) - 1:
                local_position = (gradient_position * (len(style.gradient_colors) - 1)) - color_index
                color1 = style.gradient_colors[color_index]
                color2 = style.gradient_colors[color_index + 1]
                
                r = int(color1[0] + (color2[0] - color1[0]) * local_position)
                g = int(color1[1] + (color2[1] - color1[1]) * local_position)
                b = int(color1[2] + (color2[2] - color1[2]) * local_position)
                color = (r, g, b)
            else:
                color = style.gradient_colors[color_index]
            
            # 渲染字符
            char_color = (*color, int(255 * style.opacity))
            draw.text((char_x, y), char, font=font, fill=char_color)
    
    def _apply_text_animation(self, text: str, animation: TextAnimation, 
                           current_time: float) -> str:
        """应用文字动画"""
        if not animation or current_time < animation.delay:
            return text
        
        effective_time = current_time - animation.delay
        
        if animation.animation_type == TextAnimationType.TYPING:
            # 打字机效果
            speed = animation.parameters.get('speed', 0.1) if animation.parameters else 0.1
            char_count = int(effective_time / speed)
            return text[:char_count]
        
        return text
    
    def _get_font(self, style: TextStyle) -> ImageFont.ImageFont:
        """获取字体"""
        font_key = f"{style.font_family}_{style.font_size}_{style.bold}_{style.italic}"
        
        if font_key in self.font_cache:
            return self.font_cache[font_key]
        
        try:
            # 尝试加载字体
            font_path = self._find_font_file(style.font_family)
            if font_path:
                font = ImageFont.truetype(font_path, style.font_size)
            else:
                # 使用默认字体
                font = ImageFont.load_default()
            
            # 应用样式
            if style.bold and style.italic:
                # 这里可以尝试加载粗斜体字体
                pass
            elif style.bold:
                # 这里可以尝试加载粗体字体
                pass
            elif style.italic:
                # 这里可以尝试加载斜体字体
                pass
            
            self.font_cache[font_key] = font
            return font
            
        except Exception as e:
            print(f"加载字体失败: {e}")
            return ImageFont.load_default()
    
    def _find_font_file(self, font_family: str) -> Optional[str]:
        """查找字体文件"""
        # 常见字体路径
        font_paths = [
            "/System/Library/Fonts",  # macOS
            "/usr/share/fonts",       # Linux
            "C:/Windows/Fonts",       # Windows
            "./fonts"                 # 本地字体目录
        ]
        
        font_name_map = {
            "Arial": "Arial.ttf",
            "Times New Roman": "Times New Roman.ttf",
            "Helvetica": "Helvetica.ttf",
            "Georgia": "Georgia.ttf",
            "Verdana": "Verdana.ttf",
            "Courier New": "Courier New.ttf",
            "Impact": "Impact.ttf",
            "Comic Sans MS": "Comic Sans MS.ttf"
        }
        
        font_filename = font_name_map.get(font_family, font_family + ".ttf")
        
        for font_path in font_paths:
            full_path = os.path.join(font_path, font_filename)
            if os.path.exists(full_path):
                return full_path
        
        return None
    
    def create_text_layer(self, text: str, style: TextStyle, position: Tuple[int, int],
                        animation: TextAnimation = None) -> TextLayer:
        """创建文字图层"""
        return TextLayer(
            text=text,
            style=style,
            position=position,
            animation=animation
        )
    
    def apply_text_effect(self, frame: np.ndarray, text_layer: TextLayer,
                         current_time: float = 0.0) -> np.ndarray:
        """应用文字效果到帧"""
        if not text_layer.is_visible:
            return frame
        
        # 渲染文字
        text_image = self.render_text(
            text_layer.text,
            text_layer.style,
            text_layer.position,
            text_layer.animation,
            current_time
        )
        
        # 转换为OpenCV格式
        if text_image.shape[2] == 4:  # RGBA
            # 分离alpha通道
            rgb = text_image[:, :, :3]
            alpha = text_image[:, :, 3] / 255.0
            
            # 应用透明度
            for i in range(3):
                frame[:, :, i] = frame[:, :, i] * (1 - alpha) + rgb[:, :, i] * alpha
        else:
            # 直接叠加
            mask = np.any(text_image > 0, axis=2)
            frame[mask] = text_image[mask]
        
        return frame
    
    def create_text_template(self, name: str, text_layers: List[TextLayer]) -> bool:
        """创建文字模板"""
        try:
            self.text_templates[name] = text_layers
            return True
        except Exception as e:
            print(f"创建文字模板失败: {e}")
            return False
    
    def apply_text_template(self, frame: np.ndarray, template_name: str,
                          current_time: float = 0.0) -> np.ndarray:
        """应用文字模板"""
        if template_name not in self.text_templates:
            return frame
        
        template = self.text_templates[template_name]
        result = frame.copy()
        
        for layer in template:
            result = self.apply_text_effect(result, layer, current_time)
        
        return result
    
    def get_effect_presets(self) -> List[Dict[str, Any]]:
        """获取效果预设列表"""
        return [
            {
                "id": key,
                "name": preset["name"],
                "description": f"{preset['name']} 文字效果"
            }
            for key, preset in self.effect_presets.items()
        ]
    
    def get_animation_presets(self) -> List[Dict[str, Any]]:
        """获取动画预设列表"""
        return [
            {
                "id": key,
                "name": preset["name"],
                "description": f"{preset['name']} 动画效果",
                "duration": preset["animation"].duration
            }
            for key, preset in self.animation_presets.items()
        ]
    
    def get_text_templates(self) -> List[Dict[str, Any]]:
        """获取文字模板列表"""
        return [
            {
                "id": key,
                "name": key.replace("_", " ").title(),
                "description": f"{key.replace('_', ' ')} 文字模板",
                "layer_count": len(template)
            }
            for key, template in self.text_templates.items()
        ]
    
    def apply_neon_effect(self, text: str, position: Tuple[int, int], 
                         color: Tuple[int, int, int] = (0, 255, 255),
                         font_size: int = 48) -> np.ndarray:
        """应用霓虹效果"""
        style = TextStyle(
            font_color=color,
            glow_color=color,
            glow_size=15,
            outline_color=(255, 255, 255),
            outline_width=2,
            font_size=font_size
        )
        
        return self.render_text(text, style, position)
    
    def apply_fire_effect(self, text: str, position: Tuple[int, int],
                         font_size: int = 48) -> np.ndarray:
        """应用火焰效果"""
        style = TextStyle(
            font_color=(255, 200, 0),
            glow_color=(255, 100, 0),
            glow_size=20,
            outline_color=(255, 0, 0),
            outline_width=3,
            font_size=font_size
        )
        
        return self.render_text(text, style, position)
    
    def apply_ice_effect(self, text: str, position: Tuple[int, int],
                        font_size: int = 48) -> np.ndarray:
        """应用冰霜效果"""
        style = TextStyle(
            font_color=(200, 230, 255),
            glow_color=(150, 200, 255),
            glow_size=15,
            outline_color=(100, 150, 255),
            outline_width=2,
            font_size=font_size
        )
        
        return self.render_text(text, style, position)
    
    def apply_3d_effect(self, text: str, position: Tuple[int, int],
                       color: Tuple[int, int, int] = (255, 255, 255),
                       depth: int = 10, font_size: int = 48) -> np.ndarray:
        """应用3D效果"""
        style = TextStyle(
            font_color=color,
            shadow_color=(100, 100, 100),
            shadow_offset=(depth, depth),
            shadow_blur=2,
            outline_color=(50, 50, 50),
            outline_width=1,
            font_size=font_size
        )
        
        return self.render_text(text, style, position)
    
    def apply_rainbow_effect(self, text: str, position: Tuple[int, int],
                           font_size: int = 48) -> np.ndarray:
        """应用彩虹效果"""
        style = TextStyle(
            gradient_colors=[
                (255, 0, 0), (255, 127, 0), (255, 255, 0),
                (0, 255, 0), (0, 0, 255), (139, 0, 255)
            ],
            font_size=font_size
        )
        
        return self.render_text(text, style, position)
    
    def create_karaoke_text(self, text: str, position: Tuple[int, int],
                           current_time: float, total_duration: float,
                           font_size: int = 48) -> np.ndarray:
        """创建卡拉OK文字效果"""
        # 计算当前应该高亮的字符数
        progress = current_time / total_duration
        char_count = int(progress * len(text))
        
        # 创建样式
        normal_style = TextStyle(
            font_color=(200, 200, 200),
            font_size=font_size
        )
        
        highlight_style = TextStyle(
            font_color=(255, 255, 0),
            glow_color=(255, 255, 0),
            glow_size=5,
            font_size=font_size
        )
        
        # 分割文字
        normal_text = text[:char_count]
        highlight_text = text[char_count:]
        
        # 渲染
        result = np.zeros((1080, 1920, 4), dtype=np.uint8)
        
        if normal_text:
            normal_render = self.render_text(normal_text, normal_style, position)
            result = self._blend_images(result, normal_render)
        
        if highlight_text:
            highlight_position = (position[0] + len(normal_text) * font_size * 0.6, position[1])
            highlight_render = self.render_text(highlight_text, highlight_style, highlight_position)
            result = self._blend_images(result, highlight_render)
        
        return result
    
    def _blend_images(self, base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """混合图像"""
        if overlay.shape[2] == 4:  # RGBA
            alpha = overlay[:, :, 3] / 255.0
            for i in range(3):
                base[:, :, i] = base[:, :, i] * (1 - alpha) + overlay[:, :, i] * alpha
        else:
            mask = np.any(overlay > 0, axis=2)
            base[mask] = overlay[mask]
        
        return base

# 全局文字效果引擎实例
text_effect_engine = TextEffectEngine()