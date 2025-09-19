#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⚠️ DEPRECATED: 此文件已被新的统一主题系统替代
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
    "UnifiedThemeManager in design_theme_system.py is deprecated. "
    "Use UnifiedThemeManager from app.ui.unified_theme_system instead.",
    DeprecationWarning,
    stacklevel=2
)


class ThemeType(Enum):
    """主题类型枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class UnifiedThemeManager(QObject):
    """统一主题管理器 - 解决所有可见性问题"""
    
    # 信号
    theme_changed = pyqtSignal(str)  # 主题变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_theme = ThemeType.LIGHT
        self._theme_stylesheets = {}
        self._load_theme_stylesheets()
    
    def _load_theme_stylesheets(self):
        """加载高质量的主题样式表"""
        self._theme_stylesheets[ThemeType.LIGHT] = self._get_light_theme()
        self._theme_stylesheets[ThemeType.DARK] = self._get_dark_theme()
        print(f"✅ 统一主题系统加载完成")
    
    def _get_light_theme(self) -> str:
        """获取高质量的浅色主题"""
        return """
        /* CineAIStudio - 高对比度浅色主题 */
        
        /* 全局样式 - 确保最高可读性 */
        * {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            font-size: 14px;
        }
        
        QWidget {
            background-color: #ffffff;
            color: #000000;
            selection-background-color: #007acc;
            selection-color: #ffffff;
        }
        
        QMainWindow {
            background-color: #f8f9fa;
        }
        
        QLabel {
            color: #000000;
            font-weight: 500;
        }
        
        /* 按钮样式 - 高对比度 */
        QPushButton {
            background-color: #007acc;
            color: #ffffff;
            border: 2px solid #007acc;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 14px;
            min-height: 44px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #0056b3;
            border-color: #0056b3;
        }
        
        QPushButton:pressed {
            background-color: #004085;
            border-color: #004085;
        }
        
        QPushButton:disabled {
            background-color: #e9ecef;
            color: #6c757d;
            border-color: #dee2e6;
        }
        
        /* 次要按钮 */
        QPushButton[flat="true"] {
            background-color: transparent;
            color: #007acc;
            border: 2px solid #007acc;
        }
        
        QPushButton[flat="true"]:hover {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 危险按钮 */
        QPushButton[objectName="danger_button"] {
            background-color: #dc3545;
            border-color: #dc3545;
        }
        
        QPushButton[objectName="danger_button"]:hover {
            background-color: #c82333;
            border-color: #bd2130;
        }
        
        /* 输入框样式 - 高对比度 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 6px;
            padding: 10px 15px;
            font-size: 14px;
            min-height: 44px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #007acc;
            outline: none;
        }
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background-color: #f8f9fa;
            color: #6c757d;
            border-color: #dee2e6;
        }
        
        /* 下拉框样式 */
        QComboBox {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 6px;
            padding: 10px 15px;
            font-size: 14px;
            min-height: 44px;
        }
        
        QComboBox:hover {
            border-color: #007acc;
        }
        
        QComboBox:focus {
            border-color: #007acc;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        
        QComboBox::down-arrow {
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0iIzAwMDAwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNC41TDYgNy41TDkgNC41IiBzdHJva2U9IiMwMDAwMDAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            selection-background-color: #007acc;
            selection-color: #ffffff;
        }
        
        /* 复选框和单选框 */
        QCheckBox, QRadioButton {
            color: #000000;
            font-size: 14px;
            font-weight: 500;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #000000;
            background-color: #ffffff;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007acc;
            border-color: #007acc;
        }
        
        QRadioButton::indicator:checked {
            background-color: #007acc;
            border-color: #007acc;
        }
        
        /* 选项卡 */
        QTabWidget::pane {
            background-color: #ffffff;
            border: 2px solid #000000;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #f8f9fa;
            color: #000000;
            border: 2px solid #000000;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            padding: 12px 24px;
            margin-right: 2px;
            font-weight: bold;
        }
        
        QTabBar::tab:selected {
            background-color: #007acc;
            color: #ffffff;
            border-color: #007acc;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e9ecef;
        }
        
        /* 列表和树形控件 */
        QListWidget, QTreeWidget {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 8px;
        }
        
        QListWidget::item, QTreeWidget::item {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
            font-size: 14px;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 进度条 */
        QProgressBar {
            background-color: #e9ecef;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            height: 24px;
        }
        
        QProgressBar::chunk {
            background-color: #007acc;
            border-radius: 4px;
        }
        
        /* 滑块 */
        QSlider::groove:horizontal {
            background-color: #dee2e6;
            height: 8px;
            border-radius: 4px;
            border: 1px solid #000000;
        }
        
        QSlider::handle:horizontal {
            background-color: #007acc;
            border: 2px solid #ffffff;
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            background-color: #f8f9fa;
            width: 16px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #000000;
            border-radius: 8px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #007acc;
        }
        
        QScrollBar:horizontal {
            background-color: #f8f9fa;
            height: 16px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #000000;
            border-radius: 8px;
            min-width: 30px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #007acc;
        }
        
        /* 分组框 */
        QGroupBox {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
            font-size: 16px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            background-color: #ffffff;
        }
        
        /* 工具提示 */
        QToolTip {
            background-color: rgba(0, 0, 0, 0.9);
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: #f8f9fa;
            color: #000000;
            border-top: 2px solid #000000;
            font-weight: 500;
        }
        
        /* 菜单栏 */
        QMenuBar {
            background-color: #f8f9fa;
            color: #000000;
            border-bottom: 2px solid #000000;
        }
        
        QMenuBar::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 6px;
        }
        
        QMenu::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 卡片和面板 */
        QFrame[objectName="card"], QFrame[objectName="panel"] {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 12px;
            padding: 16px;
        }
        
        /* 专业卡片 */
        #professionalCard {
            background-color: #ffffff;
            color: #000000;
            border: 2px solid #000000;
            border-radius: 12px;
            padding: 20px;
        }
        
        /* 导航面板 */
        QWidget[objectName="left_panel"] {
            background-color: #ffffff;
            color: #000000;
            border-right: 2px solid #000000;
        }
        
        /* 导航按钮 */
        QPushButton[objectName="nav_button"] {
            background-color: transparent;
            color: #000000;
            border: none;
            border-radius: 6px;
            padding: 12px 16px;
            text-align: left;
            font-weight: 500;
            font-size: 14px;
        }
        
        QPushButton[objectName="nav_button"]:hover {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QPushButton[objectName="nav_button"]:checked {
            background-color: #007acc;
            color: #ffffff;
            font-weight: bold;
        }
        
        /* 应用标题 */
        QLabel[objectName="app_title"] {
            color: #007acc;
            font-size: 20px;
            font-weight: bold;
            padding: 16px;
        }
        """
    
    def _get_dark_theme(self) -> str:
        """获取高质量的深色主题"""
        return """
        /* CineAIStudio - 高对比度深色主题 */
        
        /* 全局样式 - 确保最高可读性 */
        * {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            font-size: 14px;
        }
        
        QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
            selection-background-color: #007acc;
            selection-color: #ffffff;
        }
        
        QMainWindow {
            background-color: #000000;
        }
        
        QLabel {
            color: #ffffff;
            font-weight: 500;
        }
        
        /* 按钮样式 - 高对比度 */
        QPushButton {
            background-color: #007acc;
            color: #ffffff;
            border: 2px solid #007acc;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 14px;
            min-height: 44px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #0056b3;
            border-color: #0056b3;
        }
        
        QPushButton:pressed {
            background-color: #004085;
            border-color: #004085;
        }
        
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #6c757d;
            border-color: #404040;
        }
        
        /* 次要按钮 */
        QPushButton[flat="true"] {
            background-color: transparent;
            color: #007acc;
            border: 2px solid #007acc;
        }
        
        QPushButton[flat="true"]:hover {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 危险按钮 */
        QPushButton[objectName="danger_button"] {
            background-color: #dc3545;
            border-color: #dc3545;
        }
        
        QPushButton[objectName="danger_button"]:hover {
            background-color: #c82333;
            border-color: #bd2130;
        }
        
        /* 输入框样式 - 高对比度 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 6px;
            padding: 10px 15px;
            font-size: 14px;
            min-height: 44px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #007acc;
            outline: none;
        }
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background-color: #1a1a1a;
            color: #6c757d;
            border-color: #404040;
        }
        
        /* 下拉框样式 */
        QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 6px;
            padding: 10px 15px;
            font-size: 14px;
            min-height: 44px;
        }
        
        QComboBox:hover {
            border-color: #007acc;
        }
        
        QComboBox:focus {
            border-color: #007acc;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        
        QComboBox::down-arrow {
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNC41TDYgNy41TDkgNC41IiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            selection-background-color: #007acc;
            selection-color: #ffffff;
        }
        
        /* 复选框和单选框 */
        QCheckBox, QRadioButton {
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #ffffff;
            background-color: #2d2d2d;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007acc;
            border-color: #007acc;
        }
        
        QRadioButton::indicator:checked {
            background-color: #007acc;
            border-color: #007acc;
        }
        
        /* 选项卡 */
        QTabWidget::pane {
            background-color: #1a1a1a;
            border: 2px solid #ffffff;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            padding: 12px 24px;
            margin-right: 2px;
            font-weight: bold;
        }
        
        QTabBar::tab:selected {
            background-color: #007acc;
            color: #ffffff;
            border-color: #007acc;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #404040;
        }
        
        /* 列表和树形控件 */
        QListWidget, QTreeWidget {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 8px;
        }
        
        QListWidget::item, QTreeWidget::item {
            padding: 12px;
            border-bottom: 1px solid #404040;
            font-size: 14px;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 进度条 */
        QProgressBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            height: 24px;
        }
        
        QProgressBar::chunk {
            background-color: #007acc;
            border-radius: 4px;
        }
        
        /* 滑块 */
        QSlider::groove:horizontal {
            background-color: #404040;
            height: 8px;
            border-radius: 4px;
            border: 1px solid #ffffff;
        }
        
        QSlider::handle:horizontal {
            background-color: #007acc;
            border: 2px solid #ffffff;
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 16px;
            border: 1px solid #404040;
            border-radius: 8px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #ffffff;
            border-radius: 8px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #007acc;
        }
        
        QScrollBar:horizontal {
            background-color: #2d2d2d;
            height: 16px;
            border: 1px solid #404040;
            border-radius: 8px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #ffffff;
            border-radius: 8px;
            min-width: 30px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #007acc;
        }
        
        /* 分组框 */
        QGroupBox {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
            font-size: 16px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            background-color: #1a1a1a;
        }
        
        /* 工具提示 */
        QToolTip {
            background-color: rgba(0, 0, 0, 0.95);
            color: #ffffff;
            border: 2px solid #007acc;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-top: 2px solid #ffffff;
            font-weight: 500;
        }
        
        /* 菜单栏 */
        QMenuBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-bottom: 2px solid #ffffff;
        }
        
        QMenuBar::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 6px;
        }
        
        QMenu::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* 卡片和面板 */
        QFrame[objectName="card"], QFrame[objectName="panel"] {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 12px;
            padding: 16px;
        }
        
        /* 专业卡片 */
        #professionalCard {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 12px;
            padding: 20px;
        }
        
        /* 导航面板 */
        QWidget[objectName="left_panel"] {
            background-color: #2d2d2d;
            color: #ffffff;
            border-right: 2px solid #ffffff;
        }
        
        /* 导航按钮 */
        QPushButton[objectName="nav_button"] {
            background-color: transparent;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 12px 16px;
            text-align: left;
            font-weight: 500;
            font-size: 14px;
        }
        
        QPushButton[objectName="nav_button"]:hover {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QPushButton[objectName="nav_button"]:checked {
            background-color: #007acc;
            color: #ffffff;
            font-weight: bold;
        }
        
        /* 应用标题 */
        QLabel[objectName="app_title"] {
            color: #007acc;
            font-size: 20px;
            font-weight: bold;
            padding: 16px;
        }
        """
    
    def set_theme(self, theme: str):
        """设置主题"""
        try:
            if isinstance(theme, str):
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
                print(f"🎨 统一主题已切换到: {theme_type.value}")
        
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
                'primary': '#007acc',
                'primary_hover': '#0056b3',
                'primary_active': '#004085',
                'background': '#1a1a1a',
                'surface': '#2d2d2d',
                'border': '#ffffff',
                'text': '#ffffff',
                'text_secondary': '#b0b0b0',
                'text_disabled': '#6c757d',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'card': '#2d2d2d',
                'hover': '#404040'
            }
        else:  # Light theme
            return {
                'primary': '#007acc',
                'primary_hover': '#0056b3',
                'primary_active': '#004085',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'border': '#000000',
                'text': '#000000',
                'text_secondary': '#6c757d',
                'text_disabled': '#999999',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'card': '#ffffff',
                'hover': '#e9ecef'
            }
    
    def reload_themes(self):
        """重新加载主题文件"""
        self._load_theme_stylesheets()
        self._apply_theme(self.current_theme)
        print("🔄 统一主题文件已重新加载")


# 全局统一主题管理器实例
_unified_theme_manager = None


def get_unified_theme_manager() -> UnifiedThemeManager:
    """获取全局统一主题管理器实例"""
    global _unified_theme_manager
    if _unified_theme_manager is None:
        _unified_theme_manager = UnifiedThemeManager()
    return _unified_theme_manager


def apply_unified_theme_to_widget(widget, theme_type: Optional[ThemeType] = None):
    """为特定控件应用统一主题样式"""
    theme_manager = get_unified_theme_manager()
    colors = theme_manager.get_theme_colors(theme_type)
    
    # 应用基本样式
    widget.setStyleSheet(f"""
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text']};
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton {{
            background-color: {colors['primary']};
            color: #ffffff;
            border: 2px solid {colors['primary']};
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
            min-height: 44px;
        }}
        QPushButton:hover {{
            background-color: {colors['primary_hover']};
            border-color: {colors['primary_hover']};
        }}
        QLineEdit, QTextEdit {{
            background-color: {colors['surface']};
            color: {colors['text']};
            border: 2px solid {colors['border']};
            border-radius: 6px;
            padding: 10px 15px;
            min-height: 44px;
        }}
    """)