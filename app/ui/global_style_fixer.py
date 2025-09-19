#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局样式修复工具
解决所有UI组件的样式问题，确保文字清晰可见，布局完整
"""

from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QTextEdit, QComboBox, QProgressBar, QTabWidget
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QFont

from .professional_ui_system import ProfessionalTheme


class GlobalStyleFixer(QObject):
    """全局样式修复器"""
    
    def __init__(self):
        super().__init__()
        self.is_dark_theme = False
    
    def fix_all_styles(self, root_widget: QWidget, is_dark: bool = False):
        """修复所有样式问题"""
        self.is_dark_theme = is_dark
        colors = ProfessionalTheme.get_colors(is_dark)
        
        # 修复根组件
        self._fix_widget_style(root_widget, colors)
        
        # 递归修复所有子组件
        self._fix_children_styles(root_widget, colors)
    
    def _fix_widget_style(self, widget: QWidget, colors: dict):
        """修复单个组件样式"""
        widget_class = widget.__class__.__name__
        
        # 基础样式修复
        base_style = f"""
            background-color: {colors['background']};
            color: {colors['text']};
            font-family: Arial, sans-serif;
            font-size: 14px;
        """
        
        # 根据组件类型应用特定样式
        if widget_class == "QLabel":
            self._fix_label_style(widget, colors)
        elif widget_class == "QPushButton":
            self._fix_button_style(widget, colors)
        elif widget_class == "QTabWidget":
            self._fix_tab_widget_style(widget, colors)
        elif widget_class == "QTextEdit":
            self._fix_text_edit_style(widget, colors)
        elif widget_class == "QComboBox":
            self._fix_combo_box_style(widget, colors)
        elif widget_class == "QProgressBar":
            self._fix_progress_bar_style(widget, colors)
        elif "Panel" in widget_class or "Card" in widget_class:
            self._fix_panel_style(widget, colors)
    
    def _fix_label_style(self, label, colors):
        """修复标签样式"""
        # 确保文字清晰可见
        font = label.font()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Normal)
        label.setFont(font)

        # 确保标签有足够的空间显示文字
        label.setWordWrap(True)
        label.adjustSize()
        label.setMinimumHeight(28)

        # 设置内容边距确保文字不被截断
        label.setContentsMargins(8, 6, 8, 6)

        # 确保文字垂直居中，但保持原有的水平对齐
        current_alignment = label.alignment()
        # 清除垂直对齐标志，然后添加垂直居中
        horizontal_alignment = current_alignment & (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignJustify)
        label.setAlignment(horizontal_alignment | Qt.AlignmentFlag.AlignVCenter)

        style = f"""
            QLabel {{
                color: {colors['text']};
                background-color: transparent;
                padding: 6px 8px;
                border: none;
                font-family: Arial, sans-serif;
                font-size: 12px;
                font-weight: normal;
                line-height: 1.5;
            }}
        """
        label.setStyleSheet(style)
    
    def _fix_button_style(self, button, colors):
        """修复按钮样式"""
        # 确保按钮文字清晰
        font = button.font()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Medium)
        button.setFont(font)

        # 确保按钮有足够的尺寸
        button.adjustSize()
        if button.height() < 36:
            button.setMinimumHeight(40)
        if button.width() < 100:
            button.setMinimumWidth(120)

        # 设置内容边距
        button.setContentsMargins(12, 8, 12, 8)
        
        # 检查按钮类型
        object_name = button.objectName()
        
        if "primary" in object_name.lower():
            style = f"""
                QPushButton {{
                    background-color: {colors['primary']};
                    color: white;
                    border: 1px solid {colors['primary']};
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                    min-height: 36px;
                    min-width: 100px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {colors['primary_hover']};
                    border-color: {colors['primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['primary_active']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['text_disabled']};
                    color: white;
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                    min-height: 36px;
                    min-width: 100px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    border-color: {colors['primary']};
                    color: {colors['primary']};
                }}
                QPushButton:pressed {{
                    border-color: {colors['primary_active']};
                    color: {colors['primary_active']};
                }}
            """
        
        button.setStyleSheet(style)
    
    def _fix_tab_widget_style(self, tab_widget, colors):
        """修复选项卡样式"""
        style = f"""
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['background']};
                border-radius: 6px;
            }}
            
            QTabBar::tab {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 12px 20px;
                margin-right: 2px;
                color: {colors['text_secondary']};
                font-weight: 500;
                font-size: 14px;
                min-width: 100px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {colors['background']};
                color: {colors['primary']};
                border-color: {colors['primary']};
                border-bottom: 2px solid {colors['primary']};
                font-weight: 600;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {colors['surface']};
                color: {colors['text_primary']};
            }}
        """
        tab_widget.setStyleSheet(style)
    
    def _fix_text_edit_style(self, text_edit, colors):
        """修复文本编辑器样式"""
        # 确保文字清晰
        font = text_edit.font()
        font.setPointSize(12)
        text_edit.setFont(font)
        
        style = f"""
            QTextEdit {{
                background-color: {colors['background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {colors['primary']};
            }}
        """
        text_edit.setStyleSheet(style)
    
    def _fix_combo_box_style(self, combo_box, colors):
        """修复下拉框样式"""
        style = f"""
            QComboBox {{
                background-color: {colors['background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 24px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {colors['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: 2px solid {colors['text_secondary']};
                border-top: none;
                border-right: none;
                width: 6px;
                height: 6px;
                margin-right: 8px;
            }}
        """
        combo_box.setStyleSheet(style)
    
    def _fix_progress_bar_style(self, progress_bar, colors):
        """修复进度条样式"""
        style = f"""
            QProgressBar {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                text-align: center;
                color: {colors['text']};
                font-weight: 500;
            }}
            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: 5px;
            }}
        """
        progress_bar.setStyleSheet(style)
    
    def _fix_panel_style(self, panel, colors):
        """修复面板样式"""
        style = f"""
            QWidget {{
                background-color: {colors['background']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
        """
        panel.setStyleSheet(style)
    
    def _fix_children_styles(self, parent_widget: QWidget, colors: dict):
        """递归修复所有子组件样式"""
        for child in parent_widget.findChildren(QWidget):
            self._fix_widget_style(child, colors)
    
    def apply_global_fixes(self, app: QApplication, is_dark: bool = False):
        """应用全局修复"""
        self.is_dark_theme = is_dark
        colors = ProfessionalTheme.get_colors(is_dark)
        
        # 应用全局应用程序样式
        global_style = f"""
            * {{
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}
            
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
            }}
            
            QMainWindow {{
                background-color: {colors['surface']};
            }}
            
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['text_disabled']};
            }}
        """
        
        app.setStyleSheet(global_style)


# 全局样式修复器实例
global_style_fixer = GlobalStyleFixer()


def fix_widget_styles(widget: QWidget, is_dark: bool = False):
    """修复组件样式的便捷函数"""
    global_style_fixer.fix_all_styles(widget, is_dark)


def apply_global_style_fixes(app: QApplication, is_dark: bool = False):
    """应用全局样式修复的便捷函数"""
    global_style_fixer.apply_global_fixes(app, is_dark)
