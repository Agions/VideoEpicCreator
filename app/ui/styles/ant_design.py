"""
Ant Design 风格主题系统
"""

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any
import json
import os

class AntDesignTheme:
    """Ant Design 主题"""

    def __init__(self):
        # 品牌色
        self.primary_color = QColor("#1890ff")  # 主色
        self.primary_color_hover = QColor("#40a9ff")
        self.primary_color_active = QColor("#096dd9")
        self.primary_color_outline = QColor("#e6f7ff")

        # 成功色
        self.success_color = QColor("#52c41a")
        self.success_color_hover = QColor("#73d13d")
        self.success_color_active = QColor("#389e0d")

        # 警告色
        self.warning_color = QColor("#faad14")
        self.warning_color_hover = QColor("#ffc53d")
        self.warning_color_active = QColor("#d48806")

        # 错误色
        self.error_color = QColor("#ff4d4f")
        self.error_color_hover = QColor("#ff7875")
        self.error_color_active = QColor("#d9363e")

        # 信息色
        self.info_color = QColor("#1890ff")

        # 中性色
        self.heading_color = QColor("#000000e0")  # 标题色
        self.text_color = QColor("#000000d9")    # 文本色
        self.text_color_secondary = QColor("#00000073")  # 次要文本色
        self.disabled_color = QColor("#00000040")  # 禁用色
        self.border_color = QColor("#d9d9d9")    # 边框色
        self.border_color_split = QColor("#f0f0f0")  # 分割线色
        self.background_color = QColor("#ffffff")  # 背景色
        self.background_color_light = QColor("#fafafa")  # 轻背景色
        self.placeholder_color = QColor("#bfbfbf")  # 占位符色

        # 阴影
        self.shadow_1 = QColor(0, 0, 0, 20)   # 基础投影
        self.shadow_2 = QColor(0, 0, 0, 45)   # 下拉菜单、弹窗等投影
        self.shadow_3 = QColor(0, 0, 0, 80)   # 特殊场景投影

        # 圆角
        self.border_radius_base = 2  # 基础圆角
        self.border_radius_sm = 4    # 小圆角
        self.border_radius_lg = 8    # 大圆角
        self.border_radius_xl = 12   # 超大圆角

        # 间距
        self.padding_lg = 24  # 大间距
        self.padding_md = 16  # 中等间距
        self.padding_sm = 12  # 小间距
        self.padding_xs = 8   # 超小间距
        self.padding_xxs = 4  # 超超小间距

        # 字体
        self.font_size_base = 14
        self.font_size_lg = 16
        self.font_size_sm = 12
        self.line_height_base = 1.5

        # 动画
        self.animation_duration_slow = 0.3  # 慢速动画
        self.animation_duration_base = 0.2  # 基础动画
        self.animation_duration_fast = 0.1  # 快速动画

class AntDesignThemeManager(QObject):
    """Ant Design 主题管理器"""

    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_theme = AntDesignTheme()
        self._themes = {
            "default": self._current_theme
        }

    def get_current_theme(self) -> AntDesignTheme:
        """获取当前主题"""
        return self._current_theme

    def set_theme(self, theme_name: str):
        """设置主题"""
        if theme_name in self._themes:
            self._current_theme = self._themes[theme_name]
            self.theme_changed.emit()

    def get_color(self, color_name: str) -> QColor:
        """获取颜色"""
        theme = self._current_theme
        color_map = {
            "primary": theme.primary_color,
            "primary_hover": theme.primary_color_hover,
            "primary_active": theme.primary_color_active,
            "primary_outline": theme.primary_color_outline,
            "success": theme.success_color,
            "success_hover": theme.success_color_hover,
            "success_active": theme.success_color_active,
            "warning": theme.warning_color,
            "warning_hover": theme.warning_color_hover,
            "warning_active": theme.warning_color_active,
            "error": theme.error_color,
            "error_hover": theme.error_color_hover,
            "error_active": theme.error_color_active,
            "info": theme.info_color,
            "heading": theme.heading_color,
            "text": theme.text_color,
            "text_secondary": theme.text_color_secondary,
            "disabled": theme.disabled_color,
            "border": theme.border_color,
            "border_split": theme.border_color_split,
            "background": theme.background_color,
            "background_light": theme.background_color_light,
            "placeholder": theme.placeholder_color,
            "shadow_1": theme.shadow_1,
            "shadow_2": theme.shadow_2,
            "shadow_3": theme.shadow_3
        }
        return color_map.get(color_name, QColor("#000000"))

    def get_border_radius(self, size: str = "base") -> int:
        """获取圆角"""
        theme = self._current_theme
        radius_map = {
            "base": theme.border_radius_base,
            "sm": theme.border_radius_sm,
            "lg": theme.border_radius_lg,
            "xl": theme.border_radius_xl
        }
        return radius_map.get(size, theme.border_radius_base)

    def get_padding(self, size: str = "md") -> int:
        """获取间距"""
        theme = self._current_theme
        padding_map = {
            "lg": theme.padding_lg,
            "md": theme.padding_md,
            "sm": theme.padding_sm,
            "xs": theme.padding_xs,
            "xxs": theme.padding_xxs
        }
        return padding_map.get(size, theme.padding_md)

    def get_font(self, size: str = "base") -> QFont:
        """获取字体"""
        theme = self._current_theme
        font = QFont()
        font.setFamily("Segoe UI, sans-serif")

        size_map = {
            "base": theme.font_size_base,
            "lg": theme.font_size_lg,
            "sm": theme.font_size_sm
        }

        font.setPixelSize(size_map.get(size, theme.font_size_base))
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100)
        return font

    def get_animation_duration(self, speed: str = "base") -> float:
        """获取动画时长"""
        theme = self._current_theme
        duration_map = {
            "slow": theme.animation_duration_slow,
            "base": theme.animation_duration_base,
            "fast": theme.animation_duration_fast
        }
        return duration_map.get(speed, theme.animation_duration_base)

# 全局主题管理器实例
theme_manager = AntDesignThemeManager()
