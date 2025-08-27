"""
Material Design 3 主题系统
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont
from typing import Dict, Any, Optional
import json

class ColorScheme:
    """颜色方案"""
    
    # Material Design 3 颜色
    PRIMARY = "#6750A4"
    ON_PRIMARY = "#FFFFFF"
    PRIMARY_CONTAINER = "#EADDFF"
    ON_PRIMARY_CONTAINER = "#21005D"
    
    SECONDARY = "#625B71"
    ON_SECONDARY = "#FFFFFF"
    SECONDARY_CONTAINER = "#E8DEF8"
    ON_SECONDARY_CONTAINER = "#1D192B"
    
    TERTIARY = "#7D5260"
    ON_TERTIARY = "#FFFFFF"
    TERTIARY_CONTAINER = "#FFD8E4"
    ON_TERTIARY_CONTAINER = "#31111D"
    
    ERROR = "#BA1A1A"
    ON_ERROR = "#FFFFFF"
    ERROR_CONTAINER = "#FFDAD6"
    ON_ERROR_CONTAINER = "#410002"
    
    OUTLINE = "#79747E"
    OUTLINE_VARIANT = "#C4C7D7"
    SURFACE = "#FFFBFE"
    ON_SURFACE = "#1C1B1F"
    ON_SURFACE_VARIANT = "#49454F"
    SURFACE_VARIANT = "#E7E0EC"
    BACKGROUND = "#FFFBFE"
    ON_BACKGROUND = "#1C1B1F"
    
    # 语义化颜色
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    INFO = "#2196F3"
    
class ThemeManager(QObject):
    """主题管理器"""
    
    theme_changed = pyqtSignal(str)  # 主题改变信号
    
    def __init__(self):
        super().__init__()
        self._current_theme = "light"
        self._themes = {
            "light": self._create_light_theme(),
            "dark": self._create_dark_theme()
        }
    
    def _create_light_theme(self) -> Dict[str, Any]:
        """创建浅色主题"""
        return {
            "name": "light",
            "colors": {
                "primary": ColorScheme.PRIMARY,
                "on_primary": ColorScheme.ON_PRIMARY,
                "primary_container": ColorScheme.PRIMARY_CONTAINER,
                "on_primary_container": ColorScheme.ON_PRIMARY_CONTAINER,
                "secondary": ColorScheme.SECONDARY,
                "on_secondary": ColorScheme.ON_SECONDARY,
                "secondary_container": ColorScheme.SECONDARY_CONTAINER,
                "on_secondary_container": ColorScheme.ON_SECONDARY_CONTAINER,
                "tertiary": ColorScheme.TERTIARY,
                "on_tertiary": ColorScheme.ON_TERTIARY,
                "tertiary_container": ColorScheme.TERTIARY_CONTAINER,
                "on_tertiary_container": ColorScheme.ON_TERTIARY_CONTAINER,
                "error": ColorScheme.ERROR,
                "on_error": ColorScheme.ON_ERROR,
                "error_container": ColorScheme.ERROR_CONTAINER,
                "on_error_container": ColorScheme.ON_ERROR_CONTAINER,
                "outline": ColorScheme.OUTLINE,
                "outline_variant": ColorScheme.OUTLINE_VARIANT,
                "surface": ColorScheme.SURFACE,
                "on_surface": ColorScheme.ON_SURFACE,
                "on_surface_variant": ColorScheme.ON_SURFACE_VARIANT,
                "surface_variant": ColorScheme.SURFACE_VARIANT,
                "background": ColorScheme.BACKGROUND,
                "on_background": ColorScheme.ON_BACKGROUND,
                "success": ColorScheme.SUCCESS,
                "warning": ColorScheme.WARNING,
                "info": ColorScheme.INFO
            },
            "fonts": {
                "display_large": {"size": 57, "weight": 400},
                "display_medium": {"size": 45, "weight": 400},
                "display_small": {"size": 36, "weight": 400},
                "headline_large": {"size": 32, "weight": 400},
                "headline_medium": {"size": 28, "weight": 400},
                "headline_small": {"size": 24, "weight": 400},
                "title_large": {"size": 22, "weight": 400},
                "title_medium": {"size": 16, "weight": 500},
                "title_small": {"size": 14, "weight": 500},
                "body_large": {"size": 16, "weight": 400},
                "body_medium": {"size": 14, "weight": 400},
                "body_small": {"size": 12, "weight": 400},
                "label_large": {"size": 14, "weight": 500},
                "label_medium": {"size": 12, "weight": 500},
                "label_small": {"size": 11, "weight": 500}
            },
            "shapes": {
                "corner_none": 0,
                "corner_extra_small": 4,
                "corner_small": 8,
                "corner_medium": 12,
                "corner_large": 16,
                "corner_extra_large": 28,
                "corner_full": 9999
            },
            "elevation": {
                "level0": 0,
                "level1": 1,
                "level2": 3,
                "level3": 6,
                "level4": 8,
                "level5": 12
            }
        }
    
    def _create_dark_theme(self) -> Dict[str, Any]:
        """创建深色主题"""
        theme = self._create_light_theme().copy()
        theme["name"] = "dark"
        
        # 深色主题颜色调整
        theme["colors"].update({
            "primary": "#D0BCFF",
            "on_primary": "#381E72",
            "primary_container": "#4F378B",
            "on_primary_container": "#EADDFF",
            "secondary": "#CCC2DC",
            "on_secondary": "#332D41",
            "secondary_container": "#4A4458",
            "on_secondary_container": "#E8DEF8",
            "tertiary": "#EFB8C8",
            "on_tertiary": "#492532",
            "tertiary_container": "#633B48",
            "on_tertiary_container": "#FFD8E4",
            "error": "#FFB4AB",
            "on_error": "#690005",
            "error_container": "#93000A",
            "on_error_container": "#FFDAD6",
            "outline": "#938F99",
            "outline_variant": "#444746",
            "surface": "#1C1B1F",
            "on_surface": "#E6E1E5",
            "on_surface_variant": "#CAC4D0",
            "surface_variant": "#49454F",
            "background": "#1C1B1F",
            "on_background": "#E6E1E5"
        })
        
        return theme
    
    def get_current_theme(self) -> Dict[str, Any]:
        """获取当前主题"""
        return self._themes[self._current_theme]
    
    def set_theme(self, theme_name: str):
        """设置主题"""
        if theme_name in self._themes:
            self._current_theme = theme_name
            self.theme_changed.emit(theme_name)
    
    def get_color(self, color_name: str) -> str:
        """获取颜色"""
        return self._themes[self._current_theme]["colors"].get(color_name, "#000000")
    
    def get_font(self, font_name: str) -> QFont:
        """获取字体"""
        font_info = self._themes[self._current_theme]["fonts"].get(font_name, {"size": 12, "weight": 400})
        font = QFont()
        font.setPointSize(font_info["size"])
        font.setWeight(font_info["weight"])
        return font
    
    def apply_to_palette(self, palette: QPalette):
        """应用主题到调色板"""
        theme = self._themes[self._current_theme]
        colors = theme["colors"]
        
        # 基础颜色
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["on_background"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surface_variant"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["on_surface"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["primary_container"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["on_primary_container"]))
        
        # 高亮颜色
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["on_primary"]))
        
        # 链接颜色
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors["secondary"]))
        
        # 禁用状态
        palette.setColor(QPalette.ColorRole.Disabled, QPalette.ColorRole.WindowText, QColor(colors["outline"]))
        palette.setColor(QPalette.ColorRole.Disabled, QPalette.ColorRole.Button, QColor(colors["surface_variant"]))
        palette.setColor(QPalette.ColorRole.Disabled, QPalette.ColorRole.ButtonText, QColor(colors["on_surface_variant"]))
    
    def save_theme_config(self, config_path: str):
        """保存主题配置"""
        config = {
            "current_theme": self._current_theme,
            "custom_colors": {}
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def load_theme_config(self, config_path: str):
        """加载主题配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if "current_theme" in config:
                self.set_theme(config["current_theme"])
        except Exception as e:
            print(f"Failed to load theme config: {e}")

# 全局主题管理器
theme_manager = ThemeManager()