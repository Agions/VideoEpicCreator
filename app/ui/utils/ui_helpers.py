#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI工具类和混入类 - 提供通用的UI模式和功能
"""

from typing import Optional, Dict, Any, List, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox,
    QFrame, QSizePolicy, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon

from app.ui.professional_ui_system import ProfessionalTheme, ProfessionalButton


class UISetupMixin:
    """UI设置混入类 - 提供通用的UI设置模式"""
    
    def setup_main_layout(self, layout_type: str = "vertical", margins=None, spacing=None) -> QVBoxLayout:
        """设置主布局"""
        if layout_type == "vertical":
            layout = QVBoxLayout(self)
        elif layout_type == "horizontal":
            layout = QHBoxLayout(self)
        elif layout_type == "grid":
            layout = QGridLayout(self)
        elif layout_type == "form":
            layout = QFormLayout(self)
        else:
            layout = QVBoxLayout(self)
        
        # 设置边距
        if margins:
            layout.setContentsMargins(*margins)
        else:
            layout.setContentsMargins(20, 20, 20, 20)
        
        # 设置间距
        if spacing is not None:
            layout.setSpacing(spacing)
        
        return layout
    
    def create_title_label(self, text: str, font_size: int = 24, bold: bool = True) -> QLabel:
        """创建标题标签"""
        label = QLabel(text)
        font = QFont("Arial", font_size)
        if bold:
            font.setWeight(QFont.Weight.Bold)
        label.setFont(font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
    
    def create_section_title(self, text: str, font_size: int = 16) -> QLabel:
        """创建节标题"""
        label = QLabel(text)
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        label.setFont(font)
        return label
    
    def add_stretch(self, layout, stretch: int = 1) -> None:
        """添加伸缩空间"""
        if hasattr(layout, 'addStretch'):
            layout.addStretch(stretch)
    
    def add_spacing(self, layout, spacing: int) -> None:
        """添加间距"""
        if hasattr(layout, 'addSpacing'):
            layout.addSpacing(spacing)


class SignalConnectionMixin:
    """信号连接混入类 - 提供统一的信号连接模式"""
    
    def connect_signal_safe(self, sender, signal_name: str, receiver, slot_name: str = None) -> bool:
        """安全地连接信号"""
        try:
            signal = getattr(sender, signal_name)
            if slot_name:
                slot = getattr(receiver, slot_name)
                signal.connect(slot)
            else:
                signal.connect(receiver)
            return True
        except (AttributeError, TypeError) as e:
            print(f"信号连接失败: {signal_name} -> {slot_name or receiver}, 错误: {e}")
            return False
    
    def disconnect_signal_safe(self, sender, signal_name: str, receiver, slot_name: str = None) -> bool:
        """安全地断开信号连接"""
        try:
            signal = getattr(sender, signal_name)
            if slot_name:
                slot = getattr(receiver, slot_name)
                signal.disconnect(slot)
            else:
                signal.disconnect(receiver)
            return True
        except (AttributeError, TypeError) as e:
            print(f"信号断开失败: {signal_name} -> {slot_name or receiver}, 错误: {e}")
            return False


class ThemeMixin:
    """主题混入类 - 提供主题切换功能"""
    
    def __init__(self):
        self.is_dark_theme = False
    
    def apply_theme_styles(self, widget, theme_styles: Dict[str, str]) -> None:
        """应用主题样式"""
        styles = []
        for selector, style in theme_styles.items():
            styles.append(f"{selector} {{ {style} }}")
        
        if styles:
            widget.setStyleSheet("\n".join(styles))
    
    def get_theme_colors(self) -> Dict[str, str]:
        """获取主题颜色"""
        return ProfessionalTheme.get_colors(self.is_dark_theme)
    
    def set_theme(self, is_dark: bool) -> None:
        """设置主题"""
        self.is_dark_theme = is_dark
        self._update_theme_styles()
    
    def _update_theme_styles(self) -> None:
        """更新主题样式 - 子类应重写此方法"""
        pass


class FileDialogManager:
    """文件对话框管理器"""
    
    @staticmethod
    def open_video_file(parent: QWidget, title: str = "选择视频文件") -> tuple[str, str]:
        """打开视频文件对话框"""
        return QFileDialog.getOpenFileName(
            parent,
            title,
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm);;所有文件 (*.*)"
        )
    
    @staticmethod
    def open_audio_file(parent: QWidget, title: str = "选择音频文件") -> tuple[str, str]:
        """打开音频文件对话框"""
        return QFileDialog.getOpenFileName(
            parent,
            title,
            "",
            "音频文件 (*.mp3 *.wav *.aac *.flac *.ogg);;所有文件 (*.*)"
        )
    
    @staticmethod
    def open_image_file(parent: QWidget, title: str = "选择图片文件") -> tuple[str, str]:
        """打开图片文件对话框"""
        return QFileDialog.getOpenFileName(
            parent,
            title,
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff);;所有文件 (*.*)"
        )
    
    @staticmethod
    def save_video_file(parent: QWidget, title: str = "保存视频文件") -> tuple[str, str]:
        """保存视频文件对话框"""
        return QFileDialog.getSaveFileName(
            parent,
            title,
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"
        )
    
    @staticmethod
    def save_project_file(parent: QWidget, title: str = "保存项目文件") -> tuple[str, str]:
        """保存项目文件对话框"""
        return QFileDialog.getSaveFileName(
            parent,
            title,
            "",
            "项目文件 (*.cine *.json);;所有文件 (*.*)"
        )
    
    @staticmethod
    def select_directory(parent: QWidget, title: str = "选择目录") -> str:
        """选择目录对话框"""
        return QFileDialog.getExistingDirectory(
            parent,
            title,
            ""
        )


class ButtonFactory:
    """按钮工厂类"""
    
    @staticmethod
    def create_standard_button(
        text: str, 
        button_type: str = "default",
        icon: Optional[str] = None,
        tooltip: Optional[str] = None
    ) -> ProfessionalButton:
        """创建标准按钮"""
        button = ProfessionalButton(text, button_type)
        
        if icon:
            # 这里可以添加图标设置逻辑
            pass
        
        if tooltip:
            button.setToolTip(tooltip)
        
        return button
    
    @staticmethod
    def create_button_group(buttons_config: List[Dict[str, Any]]) -> List[ProfessionalButton]:
        """创建按钮组"""
        buttons = []
        for config in buttons_config:
            button = ButtonFactory.create_standard_button(
                text=config.get('text', ''),
                button_type=config.get('type', 'default'),
                icon=config.get('icon'),
                tooltip=config.get('tooltip')
            )
            buttons.append(button)
        return buttons


class LayoutHelper:
    """布局辅助类"""
    
    @staticmethod
    def create_card_layout(title: str = None, content_margins=None) -> QVBoxLayout:
        """创建卡片布局"""
        layout = QVBoxLayout()
        
        if content_margins:
            layout.setContentsMargins(*content_margins)
        else:
            layout.setContentsMargins(16, 16, 16, 16)
        
        layout.setSpacing(12)
        
        return layout
    
    @staticmethod
    def create_form_layout(label_width: int = 120) -> QFormLayout:
        """创建表单布局"""
        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return layout
    
    @staticmethod
    def create_grid_layout(spacing: int = 10) -> QGridLayout:
        """创建网格布局"""
        layout = QGridLayout()
        layout.setSpacing(spacing)
        return layout


class MessageHelper:
    """消息辅助类"""

    @staticmethod
    def show_info(parent: QWidget, title: str, message: str) -> None:
        """显示信息消息"""
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_warning(parent: QWidget, title: str, message: str) -> None:
        """显示警告消息"""
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def show_error(parent: QWidget, title: str, message: str) -> None:
        """显示错误消息"""
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_question(parent: QWidget, title: str, message: str) -> bool:
        """显示确认对话框"""
        reply = QMessageBox.question(
            parent, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes


# 便捷函数
def show_info_message(parent: QWidget, message: str, title: str = "信息") -> None:
    """显示信息消息的便捷函数"""
    MessageHelper.show_info(parent, title, message)


def show_warning_message(parent: QWidget, message: str, title: str = "警告") -> None:
    """显示警告消息的便捷函数"""
    MessageHelper.show_warning(parent, title, message)


def show_error_message(parent: QWidget, message: str, title: str = "错误") -> None:
    """显示错误消息的便捷函数"""
    MessageHelper.show_error(parent, title, message)


def show_question_message(parent: QWidget, message: str, title: str = "确认") -> bool:
    """显示确认对话框的便捷函数"""
    return MessageHelper.show_question(parent, title, message)


class ProgressHelper:
    """进度辅助类"""
    
    def __init__(self, progress_bar, progress_label=None):
        self.progress_bar = progress_bar
        self.progress_label = progress_label
    
    def set_progress(self, value: int, text: str = None) -> None:
        """设置进度"""
        if self.progress_bar:
            self.progress_bar.setValue(value)
        
        if self.progress_label and text:
            self.progress_label.setText(text)
    
    def reset_progress(self) -> None:
        """重置进度"""
        if self.progress_bar:
            self.progress_bar.setValue(0)
        
        if self.progress_label:
            self.progress_label.setText("就绪")
    
    def set_range(self, min_val: int, max_val: int) -> None:
        """设置进度范围"""
        if self.progress_bar:
            self.progress_bar.setRange(min_val, max_val)


class ValidationHelper:
    """验证辅助类"""
    
    @staticmethod
    def validate_file_path(file_path: str, extensions: List[str] = None) -> bool:
        """验证文件路径"""
        import os
        
        if not file_path or not os.path.exists(file_path):
            return False
        
        if extensions:
            file_ext = os.path.splitext(file_path)[1].lower()
            return file_ext in extensions
        
        return True
    
    @staticmethod
    def validate_directory_path(dir_path: str) -> bool:
        """验证目录路径"""
        import os
        return dir_path and os.path.isdir(dir_path)
    
    @staticmethod
    def validate_video_file(file_path: str) -> bool:
        """验证视频文件"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        return ValidationHelper.validate_file_path(file_path, video_extensions)
    
    @staticmethod
    def validate_audio_file(file_path: str) -> bool:
        """验证音频文件"""
        audio_extensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg']
        return ValidationHelper.validate_file_path(file_path, audio_extensions)


class ErrorHandlerMixin:
    """错误处理混入类"""
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """处理错误"""
        error_msg = f"错误: {str(error)}"
        if context:
            error_msg = f"{context} - {error_msg}"
        
        print(error_msg)
        
        # 如果有父窗口，显示错误对话框
        parent = getattr(self, 'parent', lambda: None)()
        if parent:
            MessageHelper.show_error(parent, "错误", error_msg)
    
    def safe_execute(self, func: Callable, *args, **kwargs) -> Any:
        """安全执行函数"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, f"执行 {func.__name__} 时")
            return None


class ComponentBase(QWidget, UISetupMixin, SignalConnectionMixin, ThemeMixin, ErrorHandlerMixin):
    """组件基类 - 集成所有混入功能"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        QWidget.__init__(self, parent)
        UISetupMixin.__init__(self)
        SignalConnectionMixin.__init__(self)
        ThemeMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """设置UI - 子类应重写此方法"""
        pass
    
    def _connect_signals(self) -> None:
        """连接信号 - 子类应重写此方法"""
        pass
    
    def cleanup(self) -> None:
        """清理资源 - 子类应重写此方法"""
        pass