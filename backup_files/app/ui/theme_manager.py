#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⚠️ DEPRECATED: 此文件已被统一主题系统替代
请使用 app.ui.unified_theme_system.UnifiedThemeManager

保留此文件仅用于向后兼容，新代码不应使用此模块
计划于下一版本中移除
"""

import os
from enum import Enum
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

import warnings
warnings.warn(
    "ThemeManager is deprecated. Use UnifiedThemeManager from app.ui.unified_theme_system instead.",
    DeprecationWarning,
    stacklevel=2
)


class ThemeType(Enum):
    """主题类型枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ThemeManager(QObject):
    """主题管理器 - 统一管理应用程序主题"""
    
    # 信号
    theme_changed = pyqtSignal(str)  # 主题变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_theme = ThemeType.LIGHT
        self._theme_stylesheets = {}
        self._load_theme_stylesheets()
    
    def _load_theme_stylesheets(self):
        """加载主题样式表"""
        theme_files = {
            ThemeType.LIGHT: "resources/styles/light_theme.qss",
            ThemeType.DARK: "resources/styles/dark_theme.qss"
        }
        
        for theme_type, file_path in theme_files.items():
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._theme_stylesheets[theme_type] = f.read()
                    print(f"✅ 加载主题样式: {theme_type.value}")
                else:
                    print(f"⚠️ 主题文件不存在: {file_path}")
                    # 使用备用样式
                    self._theme_stylesheets[theme_type] = self._get_fallback_stylesheet(theme_type)
            except Exception as e:
                print(f"❌ 加载主题失败 {file_path}: {e}")
                self._theme_stylesheets[theme_type] = self._get_fallback_stylesheet(theme_type)
    
    def _get_fallback_stylesheet(self, theme_type: ThemeType) -> str:
        """获取备用样式表"""
        if theme_type == ThemeType.DARK:
            return """
            QWidget {
                background-color: #1f1f1f;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
            }
            QMainWindow {
                background-color: #141414;
            }
            QPushButton {
                background-color: #177ddc;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 16px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #3c9ae8;
            }
            """
        else:  # Light theme
            return """
            QWidget {
                background-color: #ffffff;
                color: #262626;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
            }
            QMainWindow {
                background-color: #f0f2f5;
            }
            QPushButton {
                background-color: #1890ff;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 16px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            """
    
    def set_theme(self, theme: str):
        """设置主题"""
        try:
            if isinstance(theme, str):
                # 处理字符串主题名称
                theme_map = {
                    "light": ThemeType.LIGHT,
                    "浅色主题": ThemeType.LIGHT,
                    "dark": ThemeType.DARK,
                    "深色主题": ThemeType.DARK,
                    "auto": ThemeType.AUTO,
                    "自动": ThemeType.AUTO
                }
                theme_type = theme_map.get(theme.lower(), ThemeType.LIGHT)
            else:
                theme_type = theme
            
            # 如果是自动主题，根据系统设置选择
            if theme_type == ThemeType.AUTO:
                theme_type = self._detect_system_theme()
            
            if theme_type != self.current_theme:
                self.current_theme = theme_type
                self._apply_theme(theme_type)
                self.theme_changed.emit(theme_type.value)
                print(f"🎨 主题已切换到: {theme_type.value}")
        
        except Exception as e:
            print(f"❌ 设置主题失败: {e}")
    
    def _detect_system_theme(self) -> ThemeType:
        """检测系统主题（简化实现）"""
        # 这里可以添加系统主题检测逻辑
        # 目前默认返回浅色主题
        return ThemeType.LIGHT
    
    def _apply_theme(self, theme_type: ThemeType):
        """应用主题"""
        app = QApplication.instance()
        if app and theme_type in self._theme_stylesheets:
            stylesheet = self._theme_stylesheets[theme_type]
            app.setStyleSheet(stylesheet)
    
    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self.current_theme
    
    def get_theme_colors(self, theme_type: Optional[ThemeType] = None) -> Dict[str, str]:
        """获取主题颜色配置"""
        if theme_type is None:
            theme_type = self.current_theme
        
        if theme_type == ThemeType.DARK:
            return {
                'primary': '#177ddc',
                'primary_hover': '#3c9ae8',
                'primary_active': '#0958d9',
                'background': '#141414',
                'surface': '#1f1f1f',
                'border': '#434343',
                'text': '#ffffff',
                'text_secondary': '#a6a6a6',
                'text_disabled': '#595959',
                'success': '#49aa19',
                'warning': '#d89614',
                'error': '#dc4446'
            }
        else:  # Light theme
            return {
                'primary': '#1890ff',
                'primary_hover': '#40a9ff',
                'primary_active': '#096dd9',
                'background': '#ffffff',
                'surface': '#fafafa',
                'border': '#d9d9d9',
                'text': '#262626',
                'text_secondary': '#595959',
                'text_disabled': '#bfbfbf',
                'success': '#52c41a',
                'warning': '#faad14',
                'error': '#ff4d4f'
            }
    
    def reload_themes(self):
        """重新加载主题文件"""
        self._load_theme_stylesheets()
        self._apply_theme(self.current_theme)
        print("🔄 主题文件已重新加载")


# 全局主题管理器实例
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器实例"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def apply_theme_to_widget(widget, theme_type: Optional[ThemeType] = None):
    """为特定控件应用主题样式"""
    theme_manager = get_theme_manager()
    colors = theme_manager.get_theme_colors(theme_type)
    
    # 应用基本样式
    widget.setStyleSheet(f"""
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text']};
        }}
        QPushButton {{
            background-color: {colors['primary']};
            border: none;
            border-radius: 6px;
            color: #ffffff;
            padding: 8px 16px;
            min-height: 32px;
        }}
        QPushButton:hover {{
            background-color: {colors['primary_hover']};
        }}
    """)
