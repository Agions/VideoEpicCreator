#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一主题系统 - 整合所有主题管理功能
提供高性能、可扩展的主题管理解决方案
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from abc import abstractmethod

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QTimer
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QColor, QFont, QPalette

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """主题类型枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    HIGH_CONTRAST_LIGHT = "high_contrast_light"
    HIGH_CONTRAST_DARK = "high_contrast_dark"
    AMOLED_DARK = "amoled_dark"
    MINIMAL_LIGHT = "minimal_light"


class ThemeCategory(Enum):
    """主题分类"""
    SYSTEM = "system"  # 系统主题
    PROFESSIONAL = "professional"  # 专业主题
    ACCESSIBILITY = "accessibility"  # 无障碍主题
    CUSTOM = "custom"  # 自定义主题


@dataclass
class ColorScheme:
    """颜色方案"""
    primary: str = "#007AFF"
    secondary: str = "#5856D6"
    success: str = "#34C759"
    warning: str = "#FF9500"
    error: str = "#FF3B30"
    info: str = "#5AC8FA"

    # 背景色
    background: str = "#FFFFFF"
    surface: str = "#F2F2F7"
    card: str = "#FFFFFF"

    # 前景色
    text_primary: str = "#000000"
    text_secondary: str = "#8E8E93"
    text_disabled: str = "#C7C7CC"

    # 边框
    border: str = "#E5E5EA"
    divider: str = "#C6C6C8"


@dataclass
class FontScheme:
    """字体方案"""
    family: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    size_small: int = 12
    size_normal: int = 14
    size_large: int = 16
    size_title: int = 20
    size_heading: int = 24

    weight_normal: int = 400
    weight_medium: int = 500
    weight_bold: int = 700


@dataclass
class SpacingScheme:
    """间距方案"""
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass
class ThemeDefinition:
    """主题定义"""
    id: str
    name: str
    type: ThemeType
    category: ThemeCategory
    colors: ColorScheme
    fonts: FontScheme
    spacing: SpacingScheme
    description: str = ""
    author: str = "CineAIStudio"
    version: str = "1.0.0"
    is_builtin: bool = True
    stylesheet: str = ""


class IThemeManager:
    """主题管理器接口"""

    @abstractmethod
    def register_theme(self, theme: ThemeDefinition) -> bool:
        """注册主题"""
        pass

    @abstractmethod
    def unregister_theme(self, theme_id: str) -> bool:
        """注销主题"""
        pass

    @abstractmethod
    def set_theme(self, theme_id: str) -> bool:
        """设置当前主题"""
        pass

    @abstractmethod
    def get_current_theme(self) -> Optional[ThemeDefinition]:
        """获取当前主题"""
        pass

    @abstractmethod
    def get_available_themes(self) -> List[ThemeDefinition]:
        """获取可用主题列表"""
        pass

    @abstractmethod
    def get_theme_by_id(self, theme_id: str) -> Optional[ThemeDefinition]:
        """根据ID获取主题"""
        pass


class ThemeRegistry:
    """主题注册表"""

    def __init__(self):
        self._themes: Dict[str, ThemeDefinition] = {}
        self._categories: Dict[ThemeCategory, List[str]] = {
            category: [] for category in ThemeCategory
        }

    def register(self, theme: ThemeDefinition) -> bool:
        """注册主题"""
        if theme.id in self._themes:
            logger.warning(f"主题已存在: {theme.id}")
            return False

        self._themes[theme.id] = theme
        self._categories[theme.category].append(theme.id)
        logger.info(f"注册主题: {theme.name} ({theme.id})")
        return True

    def unregister(self, theme_id: str) -> bool:
        """注销主题"""
        if theme_id not in self._themes:
            return False

        theme = self._themes[theme_id]
        self._categories[theme.category].remove(theme_id)
        del self._themes[theme_id]
        logger.info(f"注销主题: {theme.name} ({theme_id})")
        return True

    def get_theme(self, theme_id: str) -> Optional[ThemeDefinition]:
        """获取主题"""
        return self._themes.get(theme_id)

    def get_all_themes(self) -> List[ThemeDefinition]:
        """获取所有主题"""
        return list(self._themes.values())

    def get_themes_by_category(self, category: ThemeCategory) -> List[ThemeDefinition]:
        """按分类获取主题"""
        theme_ids = self._categories.get(category, [])
        return [self._themes[tid] for tid in theme_ids if tid in self._themes]

    def find_themes_by_type(self, theme_type: ThemeType) -> List[ThemeDefinition]:
        """按类型查找主题"""
        return [theme for theme in self._themes.values() if theme.type == theme_type]


class StyleSheetGenerator:
    """样式表生成器"""

    @staticmethod
    def generate_stylesheet(theme: ThemeDefinition) -> str:
        """生成样式表"""
        colors = theme.colors
        fonts = theme.fonts
        spacing = theme.spacing

        # 定义颜色调整函数
        def _adjust_color(hex_color: str, amount: int) -> str:
            """调整颜色亮度"""
            # 转换十六进制颜色为RGB
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

            # 调整亮度
            r = max(0, min(255, r + amount))
            g = max(0, min(255, g + amount))
            b = max(0, min(255, b + amount))

            return f"#{r:02x}{g:02x}{b:02x}"

        stylesheet = f"""
/* CineAIStudio Theme: {theme.name} ({theme.id}) */
/* Author: {theme.author} | Version: {theme.version} */

/* ===== 全局变量 ===== */
:root {{
    /* 颜色变量 */
    --color-primary: {colors.primary};
    --color-secondary: {colors.secondary};
    --color-success: {colors.success};
    --color-warning: {colors.warning};
    --color-error: {colors.error};
    --color-info: {colors.info};

    /* 背景变量 */
    --color-background: {colors.background};
    --color-surface: {colors.surface};
    --color-card: {colors.card};

    /* 文本变量 */
    --color-text-primary: {colors.text_primary};
    --color-text-secondary: {colors.text_secondary};
    --color-text-disabled: {colors.text_disabled};

    /* 边框变量 */
    --color-border: {colors.border};
    --color-divider: {colors.divider};

    /* 字体变量 */
    --font-family: {fonts.family};
    --font-size-small: {fonts.size_small}px;
    --font-size-normal: {fonts.size_normal}px;
    --font-size-large: {fonts.size_large}px;
    --font-size-title: {fonts.size_title}px;
    --font-size-heading: {fonts.size_heading}px;

    /* 间距变量 */
    --spacing-xs: {spacing.xs}px;
    --spacing-sm: {spacing.sm}px;
    --spacing-md: {spacing.md}px;
    --spacing-lg: {spacing.lg}px;
    --spacing-xl: {spacing.xl}px;
    --spacing-xxl: {spacing.xxl}px;
}}

/* ===== 全局样式 ===== */
* {{
    font-family: var(--font-family);
    font-size: var(--font-size-normal);
    color: var(--color-text-primary);
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

QWidget {{
    background-color: var(--color-background);
    color: var(--color-text-primary);
    border: none;
}}

/* ===== 按钮样式 ===== */
QPushButton {{
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: 6px;
    padding: var(--spacing-sm) var(--spacing-md);
    font-weight: {fonts.weight_medium};
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: {_adjust_color(colors.primary, -20)};
}}

QPushButton:pressed {{
    background-color: {_adjust_color(colors.primary, -40)};
}}

QPushButton:disabled {{
    background-color: var(--color-text-disabled);
    color: var(--color-card);
}}

QPushButton#secondaryButton {{
    background-color: var(--color-surface);
    color: var(--color-text-primary);
    border: 1px solid var(--color-border);
}}

QPushButton#secondaryButton:hover {{
    background-color: var(--color-border);
}}

/* ===== 输入框样式 ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: var(--spacing-sm);
    color: var(--color-text-primary);
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid var(--color-primary);
    outline: none;
}}

/* ===== 下拉框样式 ===== */
QComboBox {{
    background-color: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: var(--spacing-sm);
    min-height: 36px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid var(--color-text-secondary);
}}

/* ===== 标签样式 ===== */
QLabel {{
    color: var(--color-text-primary);
}}

QLabel#headingLabel {{
    font-size: var(--font-size-heading);
    font-weight: {fonts.weight_bold};
    margin-bottom: var(--spacing-md);
}}

QLabel#titleLabel {{
    font-size: var(--font-size-title);
    font-weight: {fonts.weight_medium};
    margin-bottom: var(--spacing-sm);
}}

QLabel#subtitle {{
    color: var(--color-text-secondary);
    font-size: var(--font-size-small);
}}

/* ===== 面板样式 ===== */
QFrame, QGroupBox {{
    background-color: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    margin: var(--spacing-md);
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 var(--spacing-sm);
    color: var(--color-text-primary);
    font-weight: {fonts.weight_medium};
}}

/* ===== 表格样式 ===== */
QTableWidget {{
    background-color: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    gridline-color: var(--color-divider);
}}

QTableWidget::item {{
    padding: var(--spacing-sm);
    border-bottom: 1px solid var(--color-divider);
}}

QTableWidget::item:selected {{
    background-color: var(--color-primary);
    color: white;
}}

QHeaderView::section {{
    background-color: var(--color-surface);
    color: var(--color-text-primary);
    padding: var(--spacing-sm);
    border: none;
    border-right: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
    font-weight: {fonts.weight_medium};
}}

/* ===== 进度条样式 ===== */
QProgressBar {{
    background-color: var(--color-border);
    border: none;
    border-radius: 3px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: var(--color-primary);
    border-radius: 3px;
}}

/* ===== 滚动条样式 ===== */
QScrollBar:vertical {{
    background-color: var(--color-surface);
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: var(--color-text-disabled);
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: var(--color-text-secondary);
}}

QScrollBar:horizontal {{
    background-color: var(--color-surface);
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: var(--color-text-disabled);
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: var(--color-text-secondary);
}}

/* ===== 工具提示样式 ===== */
QToolTip {{
    background-color: var(--color-text-primary);
    color: var(--color-card);
    border: none;
    border-radius: 4px;
    padding: var(--spacing-sm) var(--spacing-md);
}}

/* ===== 菜单样式 ===== */
QMenuBar {{
    background-color: var(--color-surface);
    color: var(--color-text-primary);
    border-bottom: 1px solid var(--color-border);
}}

QMenuBar::item:selected {{
    background-color: var(--color-primary);
    color: white;
}}

QMenu {{
    background-color: var(--color-card);
    color: var(--color-text-primary);
    border: 1px solid var(--color-border);
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: var(--color-primary);
    color: white;
}}

/* ===== 状态栏样式 ===== */
QStatusBar {{
    background-color: var(--color-surface);
    color: var(--color-text-secondary);
    border-top: 1px solid var(--color-border);
}}

/* ===== 选项卡样式 ===== */
QTabWidget::pane {{
    border: 1px solid var(--color-border);
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: var(--color-surface);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: var(--spacing-sm) var(--spacing-md);
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: var(--color-card);
    color: var(--color-primary);
    border-color: var(--color-primary);
}}

QTabBar::tab:hover {{
    background-color: var(--color-border);
}}
"""
        return stylesheet

    @staticmethod
    def _adjust_color(hex_color: str, amount: int) -> str:
        """调整颜色亮度"""
        try:
            color = QColor(hex_color)
            h, s, v, a = color.getHsv()

            # 调整明度
            v = max(0, min(255, v + amount))

            adjusted_color = QColor()
            adjusted_color.setHsv(h, s, v, a)
            return adjusted_color.name()
        except:
            return hex_color


class UnifiedThemeManager(QObject, IThemeManager):
    """统一主题管理器"""

    # 信号定义
    theme_changed = pyqtSignal(ThemeDefinition)  # 主题变更信号
    theme_registered = pyqtSignal(ThemeDefinition)  # 主题注册信号
    theme_unregistered = pyqtSignal(str)  # 主题注销信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 核心组件
        self.registry = ThemeRegistry()
        self.stylesheet_generator = StyleSheetGenerator()
        self.settings = QSettings("CineAIStudio", "ThemeSystem")

        # 当前主题
        self._current_theme: Optional[ThemeDefinition] = None

        # 初始化
        self._init_builtin_themes()
        self._load_custom_themes()
        self._restore_last_theme()

        logger.info("统一主题系统初始化完成")

    def _init_builtin_themes(self):
        """初始化内置主题"""
        builtin_themes = [
            # 专业浅色主题
            ThemeDefinition(
                id="professional_light",
                name="专业浅色",
                type=ThemeType.LIGHT,
                category=ThemeCategory.PROFESSIONAL,
                colors=ColorScheme(
                    primary="#007AFF",
                    secondary="#5856D6",
                    success="#34C759",
                    warning="#FF9500",
                    error="#FF3B30",
                    info="#5AC8FA",
                    background="#FFFFFF",
                    surface="#F2F2F7",
                    card="#FFFFFF",
                    text_primary="#000000",
                    text_secondary="#8E8E93",
                    text_disabled="#C7C7CC",
                    border="#E5E5EA",
                    divider="#C6C6C8"
                ),
                fonts=FontScheme(),
                spacing=SpacingScheme(),
                description="适合日间使用的专业浅色主题",
                author="CineAIStudio"
            ),

            # 专业深色主题
            ThemeDefinition(
                id="professional_dark",
                name="专业深色",
                type=ThemeType.DARK,
                category=ThemeCategory.PROFESSIONAL,
                colors=ColorScheme(
                    primary="#0A84FF",
                    secondary="#BF5AF2",
                    success="#32D74B",
                    warning="#FF9F0A",
                    error="#FF453A",
                    info="#64D2FF",
                    background="#000000",
                    surface="#1C1C1E",
                    card="#2C2C2E",
                    text_primary="#FFFFFF",
                    text_secondary="#8E8E93",
                    text_disabled="#48484A",
                    border="#38383A",
                    divider="#48484A"
                ),
                fonts=FontScheme(),
                spacing=SpacingScheme(),
                description="适合夜间使用的专业深色主题",
                author="CineAIStudio"
            ),

            # 高对比度浅色
            ThemeDefinition(
                id="high_contrast_light",
                name="高对比度浅色",
                type=ThemeType.HIGH_CONTRAST_LIGHT,
                category=ThemeCategory.ACCESSIBILITY,
                colors=ColorScheme(
                    primary="#0000FF",
                    secondary="#800080",
                    success="#008000",
                    warning="#FF8C00",
                    error="#FF0000",
                    info="#008080",
                    background="#FFFFFF",
                    surface="#FFFFFF",
                    card="#FFFFFF",
                    text_primary="#000000",
                    text_secondary="#000000",
                    text_disabled="#666666",
                    border="#000000",
                    divider="#000000"
                ),
                fonts=FontScheme(
                    weight_normal=600,
                    weight_medium=700,
                    weight_bold=900
                ),
                spacing=SpacingScheme(),
                description="为视力障碍用户设计的高对比度浅色主题",
                author="CineAIStudio"
            ),

            # 高对比度深色
            ThemeDefinition(
                id="high_contrast_dark",
                name="高对比度深色",
                type=ThemeType.HIGH_CONTRAST_DARK,
                category=ThemeCategory.ACCESSIBILITY,
                colors=ColorScheme(
                    primary="#00BFFF",
                    secondary="#FF1493",
                    success="#00FF00",
                    warning="#FFD700",
                    error="#FF0000",
                    info="#00FFFF",
                    background="#000000",
                    surface="#000000",
                    card="#000000",
                    text_primary="#FFFFFF",
                    text_secondary="#FFFFFF",
                    text_disabled="#CCCCCC",
                    border="#FFFFFF",
                    divider="#FFFFFF"
                ),
                fonts=FontScheme(
                    weight_normal=600,
                    weight_medium=700,
                    weight_bold=900
                ),
                spacing=SpacingScheme(),
                description="为视力障碍用户设计的高对比度深色主题",
                author="CineAIStudio"
            ),

            # AMOLED深色
            ThemeDefinition(
                id="amoled_dark",
                name="AMOLED深色",
                type=ThemeType.AMOLED_DARK,
                category=ThemeCategory.SYSTEM,
                colors=ColorScheme(
                    primary="#BB86FC",
                    secondary="#03DAC5",
                    success="#4CAF50",
                    warning="#FF9800",
                    error="#F44336",
                    info="#2196F3",
                    background="#000000",
                    surface="#000000",
                    card="#000000",
                    text_primary="#FFFFFF",
                    text_secondary="#B0B0B0",
                    text_disabled="#808080",
                    border="#333333",
                    divider="#333333"
                ),
                fonts=FontScheme(),
                spacing=SpacingScheme(),
                description="专为AMOLED屏幕优化的纯黑主题",
                author="CineAIStudio"
            ),

            # 极简浅色
            ThemeDefinition(
                id="minimal_light",
                name="极简浅色",
                type=ThemeType.MINIMAL_LIGHT,
                category=ThemeCategory.SYSTEM,
                colors=ColorScheme(
                    primary="#2C3E50",
                    secondary="#34495E",
                    success="#27AE60",
                    warning="#F39C12",
                    error="#E74C3C",
                    info="#3498DB",
                    background="#FFFFFF",
                    surface="#FFFFFF",
                    card="#FFFFFF",
                    text_primary="#2C3E50",
                    text_secondary="#7F8C8D",
                    text_disabled="#BDC3C7",
                    border="#ECF0F1",
                    divider="#BDC3C7"
                ),
                fonts=FontScheme(
                    family="'Helvetica Neue', Arial, sans-serif"
                ),
                spacing=SpacingScheme(
                    xs=2, sm=4, md=8, lg=16, xl=24, xxl=32
                ),
                description="简洁清爽的极简设计风格",
                author="CineAIStudio"
            )
        ]

        # 注册内置主题
        for theme in builtin_themes:
            self.register_theme(theme)

    def _load_custom_themes(self):
        """加载自定义主题"""
        try:
            custom_themes_dir = Path.home() / ".config" / "CineAIStudio" / "themes"
            if custom_themes_dir.exists():
                for theme_file in custom_themes_dir.glob("*.json"):
                    self._load_theme_from_file(theme_file)
        except Exception as e:
            logger.warning(f"加载自定义主题失败: {e}")

    def _load_theme_from_file(self, file_path: Path):
        """从文件加载主题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)

            theme = ThemeDefinition(
                id=theme_data.get('id', file_path.stem),
                name=theme_data.get('name', file_path.stem),
                type=ThemeType(theme_data.get('type', 'custom')),
                category=ThemeCategory(theme_data.get('category', 'custom')),
                colors=ColorScheme(**theme_data.get('colors', {})),
                fonts=FontScheme(**theme_data.get('fonts', {})),
                spacing=SpacingScheme(**theme_data.get('spacing', {})),
                description=theme_data.get('description', ''),
                author=theme_data.get('author', 'Unknown'),
                version=theme_data.get('version', '1.0.0'),
                is_builtin=False
            )

            self.register_theme(theme)

        except Exception as e:
            logger.error(f"加载主题文件失败 {file_path}: {e}")

    def _restore_last_theme(self):
        """恢复上次使用的主题"""
        try:
            last_theme_id = self.settings.value("last_theme_id", "professional_dark")
            if last_theme_id:
                self.set_theme(last_theme_id)
        except Exception as e:
            logger.warning(f"恢复主题失败: {e}")
            # 使用默认主题
            self.set_theme("professional_dark")

    def register_theme(self, theme: ThemeDefinition) -> bool:
        """注册主题"""
        success = self.registry.register(theme)
        if success:
            # 生成样式表
            theme.stylesheet = self.stylesheet_generator.generate_stylesheet(theme)
            self.theme_registered.emit(theme)
        return success

    def unregister_theme(self, theme_id: str) -> bool:
        """注销主题"""
        theme = self.registry.get_theme(theme_id)
        if not theme:
            return False

        if theme.is_builtin:
            logger.warning("不能注销内置主题")
            return False

        success = self.registry.unregister(theme_id)
        if success:
            self.theme_unregistered.emit(theme_id)

            # 如果当前主题被注销，切换到默认主题
            if self._current_theme and self._current_theme.id == theme_id:
                self.set_theme("professional_dark")

        return success

    def set_theme(self, theme_id: str) -> bool:
        """设置当前主题"""
        theme = self.registry.get_theme(theme_id)
        if not theme:
            logger.error(f"主题不存在: {theme_id}")
            return False

        try:
            # 应用主题到应用程序
            app = QApplication.instance()
            app.setStyleSheet(theme.stylesheet)

            # 更新调色板
            self._update_palette(theme)

            # 更新当前主题
            self._current_theme = theme

            # 保存设置
            self.settings.setValue("last_theme_id", theme_id)

            # 发射信号
            self.theme_changed.emit(theme)

            logger.info(f"主题已切换: {theme.name}")
            return True

        except Exception as e:
            logger.error(f"应用主题失败: {e}")
            return False

    def get_current_theme(self) -> Optional[ThemeDefinition]:
        """获取当前主题"""
        return self._current_theme

    def get_available_themes(self) -> List[ThemeDefinition]:
        """获取可用主题列表"""
        return self.registry.get_all_themes()

    def get_theme_by_id(self, theme_id: str) -> Optional[ThemeDefinition]:
        """根据ID获取主题"""
        return self.registry.get_theme(theme_id)

    def get_themes_by_category(self, category: ThemeCategory) -> List[ThemeDefinition]:
        """按分类获取主题"""
        return self.registry.get_themes_by_category(category)

    def _update_palette(self, theme: ThemeDefinition):
        """更新应用程序调色板"""
        app = QApplication.instance()
        palette = QPalette()

        colors = theme.colors

        # 设置主要颜色
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.card))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.surface))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors.surface))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors.text_primary))

        # 设置链接颜色
        palette.setColor(QPalette.ColorRole.Link, QColor(colors.primary))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors.secondary))

        # 设置高亮颜色
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.primary))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.background))

        app.setPalette(palette)

    def save_custom_theme(self, theme: ThemeDefinition, file_path: Optional[str] = None) -> bool:
        """保存自定义主题"""
        try:
            if not file_path:
                custom_dir = Path.home() / ".config" / "CineAIStudio" / "themes"
                custom_dir.mkdir(parents=True, exist_ok=True)
                file_path = custom_dir / f"{theme.id}.json"

            theme_data = asdict(theme)
            # 移除运行时字段
            theme_data.pop('stylesheet', None)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            logger.info(f"主题已保存: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存主题失败: {e}")
            return False

    def export_theme_config(self, file_path: str) -> bool:
        """导出主题配置"""
        try:
            config = {
                "current_theme": self._current_theme.id if self._current_theme else None,
                "available_themes": [
                    {
                        "id": theme.id,
                        "name": theme.name,
                        "type": theme.type.value,
                        "category": theme.category.value
                    }
                    for theme in self.get_available_themes()
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"主题配置已导出: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出主题配置失败: {e}")
            return False

    def import_theme_config(self, file_path: str) -> bool:
        """导入主题配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 设置当前主题
            current_theme_id = config.get("current_theme")
            if current_theme_id:
                self.set_theme(current_theme_id)

            logger.info(f"主题配置已导入: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导入主题配置失败: {e}")
            return False