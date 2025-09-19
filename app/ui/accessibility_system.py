#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
键盘快捷键和可访问性系统
提供完整的键盘导航、快捷键管理和无障碍支持
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QApplication, QToolTip, QStyle,
    QSizePolicy, QFocusFrame
)
from PyQt6.QtGui import QShortcut
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QObject, QTimer, QPoint, QSize
from PyQt6.QtGui import (
    QKeySequence, QKeyEvent, QMouseEvent, QHoverEvent, 
    QFont, QColor, QPainter, QPen, QBrush, QCursor
)

from .modern_ui_system import ModernUIStyleEngine, ModernUITheme


class KeyboardShortcut:
    """键盘快捷键"""
    
    def __init__(self, key_sequence: str, action_id: str, description: str,
                 category: str = "General", default_enabled: bool = True):
        self.key_sequence = QKeySequence(key_sequence)
        self.action_id = action_id
        self.description = description
        self.category = category
        self.default_enabled = default_enabled
        self.enabled = default_enabled
        self.custom_sequence = None
        self.callback: Optional[Callable] = None
    
    def get_current_sequence(self) -> QKeySequence:
        """获取当前快捷键序列"""
        return self.custom_sequence or self.key_sequence
    
    def set_custom_sequence(self, sequence: str):
        """设置自定义快捷键序列"""
        if sequence:
            self.custom_sequence = QKeySequence(sequence)
        else:
            self.custom_sequence = None
    
    def reset_to_default(self):
        """重置为默认快捷键"""
        self.custom_sequence = None


class ShortcutCategory(Enum):
    """快捷键类别"""
    FILE = "文件操作"
    EDIT = "编辑操作"
    VIEW = "视图操作"
    PLAYBACK = "播放控制"
    TIMELINE = "时间线操作"
    EFFECTS = "特效操作"
    TOOLS = "工具操作"
    WINDOW = "窗口操作"
    HELP = "帮助操作"
    CUSTOM = "自定义"


class AccessibilityLevel(Enum):
    """可访问性级别"""
    NONE = "none"              # 无可访问性支持
    BASIC = "basic"            # 基础可访问性
    STANDARD = "standard"      # 标准可访问性
    ENHANCED = "enhanced"      # 增强可访问性
    FULL = "full"             # 完全可访问性


@dataclass
class AccessibilitySettings:
    """可访问性设置"""
    level: AccessibilityLevel = AccessibilityLevel.STANDARD
    high_contrast: bool = False
    large_text: bool = False
    screen_reader: bool = False
    keyboard_navigation: bool = True
    focus_indicators: bool = True
    animation_reduction: bool = False
    color_blind_support: bool = False
    custom_text_scale: float = 1.0


class KeyboardShortcutManager:
    """键盘快捷键管理器"""
    
    def __init__(self):
        self.shortcuts: Dict[str, KeyboardShortcut] = {}
        self.active_shortcuts: Dict[str, QShortcut] = {}
        self.shortcut_conflicts: List[Tuple[str, str]] = []
        
        # 初始化默认快捷键
        self._initialize_default_shortcuts()
    
    def _initialize_default_shortcuts(self):
        """初始化默认快捷键"""
        default_shortcuts = [
            # 文件操作
            KeyboardShortcut("Ctrl+N", "new_project", "新建项目", ShortcutCategory.FILE.value),
            KeyboardShortcut("Ctrl+O", "open_project", "打开项目", ShortcutCategory.FILE.value),
            KeyboardShortcut("Ctrl+S", "save_project", "保存项目", ShortcutCategory.FILE.value),
            KeyboardShortcut("Ctrl+Shift+S", "save_as", "另存为", ShortcutCategory.FILE.value),
            KeyboardShortcut("Ctrl+W", "close_project", "关闭项目", ShortcutCategory.FILE.value),
            KeyboardShortcut("Ctrl+Q", "exit", "退出应用", ShortcutCategory.FILE.value),
            
            # 编辑操作
            KeyboardShortcut("Ctrl+Z", "undo", "撤销", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Ctrl+Y", "redo", "重做", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Ctrl+X", "cut", "剪切", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Ctrl+C", "copy", "复制", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Ctrl+V", "paste", "粘贴", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Delete", "delete", "删除", ShortcutCategory.EDIT.value),
            KeyboardShortcut("Ctrl+A", "select_all", "全选", ShortcutCategory.EDIT.value),
            
            # 视图操作
            KeyboardShortcut("F11", "fullscreen", "全屏切换", ShortcutCategory.VIEW.value),
            KeyboardShortcut("Ctrl++", "zoom_in", "放大", ShortcutCategory.VIEW.value),
            KeyboardShortcut("Ctrl+-", "zoom_out", "缩小", ShortcutCategory.VIEW.value),
            KeyboardShortcut("Ctrl+0", "zoom_reset", "重置缩放", ShortcutCategory.VIEW.value),
            KeyboardShortcut("Ctrl+R", "refresh", "刷新", ShortcutCategory.VIEW.value),
            
            # 播放控制
            KeyboardShortcut("Space", "play_pause", "播放/暂停", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("K", "play_pause", "播放/暂停", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("J", "rewind", "快退", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("L", "fast_forward", "快进", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("Left", "seek_backward", "向后跳转", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("Right", "seek_forward", "向前跳转", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("Home", "seek_start", "跳转到开始", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("End", "seek_end", "跳转到结束", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("M", "toggle_mute", "静音切换", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("Up", "volume_up", "增加音量", ShortcutCategory.PLAYBACK.value),
            KeyboardShortcut("Down", "volume_down", "减少音量", ShortcutCategory.PLAYBACK.value),
            
            # 时间线操作
            KeyboardShortcut("I", "mark_in", "标记入点", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("O", "mark_out", "标记出点", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("X", "cut_clip", "切割片段", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("C", "add_clip", "添加片段", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("V", "paste_clip", "粘贴片段", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("T", "add_text", "添加文本", ShortcutCategory.TIMELINE.value),
            KeyboardShortcut("B", "add_transition", "添加转场", ShortcutCategory.TIMELINE.value),
            
            # 特效操作
            KeyboardShortcut("Ctrl+E", "add_effect", "添加特效", ShortcutCategory.EFFECTS.value),
            KeyboardShortcut("Ctrl+Shift+E", "effect_settings", "特效设置", ShortcutCategory.EFFECTS.value),
            KeyboardShortcut("Ctrl+R", "remove_effect", "移除特效", ShortcutCategory.EFFECTS.value),
            
            # 工具操作
            KeyboardShortcut("V", "select_tool", "选择工具", ShortcutCategory.TOOLS.value),
            KeyboardShortcut("A", "arrow_tool", "箭头工具", ShortcutCategory.TOOLS.value),
            KeyboardShortcut("T", "text_tool", "文本工具", ShortcutCategory.TOOLS.value),
            KeyboardShortcut("C", "crop_tool", "裁剪工具", ShortcutCategory.TOOLS.value),
            KeyboardShortcut("R", "rotate_tool", "旋转工具", ShortcutCategory.TOOLS.value),
            
            # 窗口操作
            KeyboardShortcut("Ctrl+1", "window_project", "项目窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+2", "window_timeline", "时间线窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+3", "window_preview", "预览窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+4", "window_effects", "特效窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+5", "window_media", "媒体窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+Tab", "next_window", "下一个窗口", ShortcutCategory.WINDOW.value),
            KeyboardShortcut("Ctrl+Shift+Tab", "prev_window", "上一个窗口", ShortcutCategory.WINDOW.value),
            
            # 帮助操作
            KeyboardShortcut("F1", "help", "帮助", ShortcutCategory.HELP.value),
            KeyboardShortcut("F2", "shortcuts", "快捷键列表", ShortcutCategory.HELP.value),
            KeyboardShortcut("F3", "about", "关于", ShortcutCategory.HELP.value),
        ]
        
        for shortcut in default_shortcuts:
            self.shortcuts[shortcut.action_id] = shortcut
    
    def register_shortcut(self, shortcut: KeyboardShortcut):
        """注册快捷键"""
        self.shortcuts[shortcut.action_id] = shortcut
    
    def unregister_shortcut(self, action_id: str):
        """注销快捷键"""
        if action_id in self.shortcuts:
            del self.shortcuts[action_id]
    
    def activate_shortcut(self, action_id: str, callback: Callable, parent: QWidget = None):
        """激活快捷键"""
        if action_id not in self.shortcuts:
            return False
        
        shortcut = self.shortcuts[action_id]
        if not shortcut.enabled:
            return False
        
        # 创建快捷键对象
        qshortcut = QShortcut(shortcut.get_current_sequence(), parent or QApplication.instance())
        qshortcut.activated.connect(callback)
        
        self.active_shortcuts[action_id] = qshortcut
        shortcut.callback = callback
        
        return True
    
    def deactivate_shortcut(self, action_id: str):
        """停用快捷键"""
        if action_id in self.active_shortcuts:
            shortcut = self.active_shortcuts[action_id]
            shortcut.setEnabled(False)
            shortcut.deleteLater()
            del self.active_shortcuts[action_id]
        
        if action_id in self.shortcuts:
            self.shortcuts[action_id].callback = None
    
    def get_shortcut(self, action_id: str) -> Optional[KeyboardShortcut]:
        """获取快捷键"""
        return self.shortcuts.get(action_id)
    
    def get_all_shortcuts(self) -> List[KeyboardShortcut]:
        """获取所有快捷键"""
        return list(self.shortcuts.values())
    
    def get_shortcuts_by_category(self, category: str) -> List[KeyboardShortcut]:
        """根据类别获取快捷键"""
        return [s for s in self.shortcuts.values() if s.category == category]
    
    def check_conflicts(self) -> List[Tuple[str, str]]:
        """检查快捷键冲突"""
        conflicts = []
        
        for i, shortcut1 in enumerate(self.shortcuts.values()):
            for j, shortcut2 in enumerate(self.shortcuts.values()):
                if i >= j:
                    continue
                
                seq1 = shortcut1.get_current_sequence()
                seq2 = shortcut2.get_current_sequence()
                
                if seq1 == seq2 and seq1.toString():
                    conflicts.append((shortcut1.action_id, shortcut2.action_id))
        
        self.shortcut_conflicts = conflicts
        return conflicts
    
    def set_shortcut_enabled(self, action_id: str, enabled: bool):
        """设置快捷键启用状态"""
        if action_id in self.shortcuts:
            self.shortcuts[action_id].enabled = enabled
            
            if not enabled:
                self.deactivate_shortcut(action_id)
    
    def customize_shortcut(self, action_id: str, key_sequence: str):
        """自定义快捷键"""
        if action_id in self.shortcuts:
            self.shortcuts[action_id].set_custom_sequence(key_sequence)
            
            # 重新激活快捷键
            if action_id in self.active_shortcuts:
                callback = self.shortcuts[action_id].callback
                parent = self.active_shortcuts[action_id].parent()
                self.deactivate_shortcut(action_id)
                self.activate_shortcut(action_id, callback, parent)
    
    def reset_shortcut(self, action_id: str):
        """重置快捷键为默认"""
        if action_id in self.shortcuts:
            self.shortcuts[action_id].reset_to_default()
            
            # 重新激活快捷键
            if action_id in self.active_shortcuts:
                callback = self.shortcuts[action_id].callback
                parent = self.active_shortcuts[action_id].parent()
                self.deactivate_shortcut(action_id)
                self.activate_shortcut(action_id, callback, parent)
    
    def export_shortcuts(self, file_path: str):
        """导出快捷键配置"""
        import json
        
        shortcuts_data = {}
        for action_id, shortcut in self.shortcuts.items():
            shortcuts_data[action_id] = {
                'key_sequence': shortcut.key_sequence.toString(),
                'custom_sequence': shortcut.custom_sequence.toString() if shortcut.custom_sequence else None,
                'description': shortcut.description,
                'category': shortcut.category,
                'enabled': shortcut.enabled
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(shortcuts_data, f, ensure_ascii=False, indent=2)
    
    def import_shortcuts(self, file_path: str):
        """导入快捷键配置"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                shortcuts_data = json.load(f)
            
            for action_id, data in shortcuts_data.items():
                if action_id in self.shortcuts:
                    shortcut = self.shortcuts[action_id]
                    shortcut.enabled = data.get('enabled', True)
                    
                    if data.get('custom_sequence'):
                        shortcut.set_custom_sequence(data['custom_sequence'])
                    else:
                        shortcut.reset_to_default()
            
            return True
        except Exception as e:
            print(f"导入快捷键配置失败: {e}")
            return False


class KeyboardNavigator(QObject):
    """键盘导航器"""
    
    def __init__(self, parent: QWidget):
        super().__init__()
        self.parent = parent
        self.focus_order: List[QWidget] = []
        self.current_focus_index = -1
        self.tab_order_enabled = True
        self.arrow_key_navigation = True
        
        # 设置焦点框架
        self.focus_frame = QFocusFrame(parent)
        self.focus_frame.setWidget(None)
        self.focus_frame.hide()
        
        # 安装事件过滤器
        parent.installEventFilter(self)
    
    def set_focus_order(self, widgets: List[QWidget]):
        """设置焦点顺序"""
        self.focus_order = widgets
        
        # 为每个组件设置焦点策略
        for widget in widgets:
            if hasattr(widget, 'setFocusPolicy'):
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def add_focus_widget(self, widget: QWidget):
        """添加焦点组件"""
        if widget not in self.focus_order:
            self.focus_order.append(widget)
            
            if hasattr(widget, 'setFocusPolicy'):
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def remove_focus_widget(self, widget: QWidget):
        """移除焦点组件"""
        if widget in self.focus_order:
            self.focus_order.remove(widget)
    
    def focus_next(self):
        """聚焦下一个组件"""
        if not self.focus_order:
            return
        
        self.current_focus_index = (self.current_focus_index + 1) % len(self.focus_order)
        self.focus_order[self.current_focus_index].setFocus()
        self._update_focus_frame()
    
    def focus_previous(self):
        """聚焦上一个组件"""
        if not self.focus_order:
            return
        
        self.current_focus_index = (self.current_focus_index - 1) % len(self.focus_order)
        self.focus_order[self.current_focus_index].setFocus()
        self._update_focus_frame()
    
    def focus_first(self):
        """聚焦第一个组件"""
        if self.focus_order:
            self.current_focus_index = 0
            self.focus_order[0].setFocus()
            self._update_focus_frame()
    
    def focus_last(self):
        """聚焦最后一个组件"""
        if self.focus_order:
            self.current_focus_index = len(self.focus_order) - 1
            self.focus_order[-1].setFocus()
            self._update_focus_frame()
    
    def _update_focus_frame(self):
        """更新焦点框架"""
        if self.current_focus_index >= 0 and self.current_focus_index < len(self.focus_order):
            widget = self.focus_order[self.current_focus_index]
            self.focus_frame.setWidget(widget)
            self.focus_frame.show()
        else:
            self.focus_frame.setWidget(None)
            self.focus_frame.hide()
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            
            if self.tab_order_enabled and key_event.key() == Qt.Key.Key_Tab:
                if key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.focus_previous()
                else:
                    self.focus_next()
                return True
            
            elif self.arrow_key_navigation:
                if key_event.key() == Qt.Key.Key_Down:
                    self.focus_next()
                    return True
                elif key_event.key() == Qt.Key.Key_Up:
                    self.focus_previous()
                    return True
        
        elif event.type() == QEvent.Type.FocusIn:
            # 更新当前焦点索引
            widget = obj
            if widget in self.focus_order:
                self.current_focus_index = self.focus_order.index(widget)
                self._update_focus_frame()
        
        return super().eventFilter(obj, event)


class AccessibilityManager:
    """可访问性管理器"""
    
    def __init__(self):
        self.settings = AccessibilitySettings()
        self.shortcut_manager = KeyboardShortcutManager()
        self.ui_engine: Optional[ModernUIStyleEngine] = None
        
        # 可访问性信号
        self.settings_changed = None  # 可以设置信号
        
        # 初始化可访问性
        self._initialize_accessibility()
    
    def _initialize_accessibility(self):
        """初始化可访问性"""
        # 设置应用程序级别的可访问性
        app = QApplication.instance()
        
        # 设置焦点指示器
        self._setup_focus_indicators()
    
    def _setup_focus_indicators(self):
        """设置焦点指示器"""
        app = QApplication.instance()
        
        # 设置焦点样式
        focus_style = """
            QWidget:focus {
                outline: 2px solid #0061A4;
                outline-offset: 2px;
            }
            
            QPushButton:focus {
                outline: 2px solid #0061A4;
                outline-offset: 2px;
            }
            
            QLineEdit:focus {
                outline: 2px solid #0061A4;
                outline-offset: 2px;
            }
            
            QComboBox:focus {
                outline: 2px solid #0061A4;
                outline-offset: 2px;
            }
        """
        
        if self.settings.focus_indicators:
            app.setStyleSheet(focus_style)
    
    def set_accessibility_level(self, level: AccessibilityLevel):
        """设置可访问性级别"""
        self.settings.level = level
        self._apply_accessibility_settings()
    
    def set_high_contrast(self, enabled: bool):
        """设置高对比度"""
        self.settings.high_contrast = enabled
        self._apply_accessibility_settings()
    
    def set_large_text(self, enabled: bool):
        """设置大文本"""
        self.settings.large_text = enabled
        self._apply_accessibility_settings()
    
    def set_screen_reader(self, enabled: bool):
        """设置屏幕阅读器"""
        self.settings.screen_reader = enabled
        self._apply_accessibility_settings()
    
    def set_keyboard_navigation(self, enabled: bool):
        """设置键盘导航"""
        self.settings.keyboard_navigation = enabled
        self._apply_accessibility_settings()
    
    def set_focus_indicators(self, enabled: bool):
        """设置焦点指示器"""
        self.settings.focus_indicators = enabled
        self._apply_accessibility_settings()
    
    def set_animation_reduction(self, enabled: bool):
        """设置动画减少"""
        self.settings.animation_reduction = enabled
        self._apply_accessibility_settings()
    
    def set_color_blind_support(self, enabled: bool):
        """设置色盲支持"""
        self.settings.color_blind_support = enabled
        self._apply_accessibility_settings()
    
    def set_custom_text_scale(self, scale: float):
        """设置自定义文本缩放"""
        self.settings.custom_text_scale = max(0.5, min(3.0, scale))
        self._apply_accessibility_settings()
    
    def _apply_accessibility_settings(self):
        """应用可访问性设置"""
        app = QApplication.instance()
        
        # 应用高对比度
        if self.settings.high_contrast and self.ui_engine:
            # 切换到高对比度主题
            if self.settings.level in [AccessibilityLevel.STANDARD, AccessibilityLevel.ENHANCED, AccessibilityLevel.FULL]:
                # 这里可以根据需要切换到高对比度主题
                pass
        
        # 应用大文本
        if self.settings.large_text or self.settings.custom_text_scale != 1.0:
            font = app.font()
            base_size = font.pointSize()
            
            if self.settings.large_text:
                scale_factor = 1.2
            else:
                scale_factor = self.settings.custom_text_scale
            
            font.setPointSize(int(base_size * scale_factor))
            app.setFont(font)
        
        # 应用动画减少
        if self.settings.animation_reduction:
            # 减少或禁用动画
            app.style().setStyle(QStyleFactory.create("Fusion"))
        
        # 应用色盲支持
        if self.settings.color_blind_support:
            # 应用色盲友好的颜色方案
            self._apply_color_blind_colors()
        
        # 应用焦点指示器
        self._setup_focus_indicators()
        
        # 发送设置变更信号
        if self.settings_changed:
            self.settings_changed.emit(self.settings)
    
    def _apply_color_blind_colors(self):
        """应用色盲友好颜色"""
        if not self.ui_engine:
            return
        
        # 这里可以实现色盲友好的颜色方案
        # 例如，避免红绿色对比，使用蓝黄色对比等
        pass
    
    def set_ui_engine(self, ui_engine: ModernUIStyleEngine):
        """设置UI引擎"""
        self.ui_engine = ui_engine
        self._apply_accessibility_settings()
    
    def create_keyboard_navigator(self, parent: QWidget) -> KeyboardNavigator:
        """创建键盘导航器"""
        return KeyboardNavigator(parent)
    
    def get_shortcut_manager(self) -> KeyboardShortcutManager:
        """获取快捷键管理器"""
        return self.shortcut_manager
    
    def show_shortcuts_help(self, parent: QWidget = None):
        """显示快捷键帮助"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QTabWidget, QLabel
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("快捷键帮助")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 按类别显示快捷键
        categories = {}
        for shortcut in self.shortcut_manager.get_all_shortcuts():
            if shortcut.category not in categories:
                categories[shortcut.category] = []
            categories[shortcut.category].append(shortcut)
        
        for category, shortcuts in categories.items():
            # 创建类别页面
            page = QWidget()
            page_layout = QVBoxLayout(page)
            
            # 添加类别标题
            title = QLabel(category)
            title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
            page_layout.addWidget(title)
            
            # 添加快捷键列表
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            
            shortcuts_text = ""
            for shortcut in shortcuts:
                shortcuts_text += f"{shortcut.get_current_sequence().toString()}\t{shortcut.description}\n"
            
            text_edit.setPlainText(shortcuts_text)
            text_edit.setFont(QFont("Courier New", 10))
            page_layout.addWidget(text_edit)
            
            tab_widget.addTab(page, category)
        
        layout.addWidget(tab_widget)
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec()


# 全局可访问性管理器实例
_accessibility_manager = None


# 工厂函数
def get_accessibility_manager() -> AccessibilityManager:
    """获取可访问性管理器"""
    global _accessibility_manager
    if _accessibility_manager is None:
        _accessibility_manager = AccessibilityManager()
    return _accessibility_manager

def create_keyboard_navigator(parent: QWidget) -> KeyboardNavigator:
    """创建键盘导航器"""
    return get_accessibility_manager().create_keyboard_navigator(parent)


def register_shortcut(action_id: str, callback: Callable, parent: QWidget = None) -> bool:
    """注册快捷键"""
    return get_accessibility_manager().get_shortcut_manager().activate_shortcut(action_id, callback, parent)


def unregister_shortcut(action_id: str):
    """注销快捷键"""
    get_accessibility_manager().get_shortcut_manager().deactivate_shortcut(action_id)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
    
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = QWidget()
    window.setWindowTitle("键盘快捷键和可访问性测试")
    window.resize(600, 400)
    
    layout = QVBoxLayout()
    window.setLayout(layout)
    
    # 添加测试组件
    label = QLabel("按 F1 查看快捷键帮助")
    layout.addWidget(label)
    
    button1 = QPushButton("按钮 1")
    layout.addWidget(button1)
    
    button2 = QPushButton("按钮 2")
    layout.addWidget(button2)
    
    button3 = QPushButton("按钮 3")
    layout.addWidget(button3)
    
    # 创建键盘导航器
    navigator = create_keyboard_navigator(window)
    navigator.set_focus_order([button1, button2, button3])
    
    # 注册快捷键
    def show_help():
        get_accessibility_manager().show_shortcuts_help(window)
    
    register_shortcut("help", show_help, window)
    
    def test_shortcut():
        print("测试快捷键触发")
    
    register_shortcut("new_project", test_shortcut, window)
    
    window.show()
    sys.exit(app.exec())