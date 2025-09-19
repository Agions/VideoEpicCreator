#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
响应式布局系统 - 支持多种屏幕尺寸和设备
提供灵活的布局管理、自适应组件和智能调整
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSizePolicy, QSpacerItem,
    QStackedWidget, QSplitter, QDockWidget, QMainWindow
)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer, pyqtSignal, QEvent, QObject
from PyQt6.QtGui import QResizeEvent, QScreen, QGuiApplication


class Breakpoint(Enum):
    """响应式断点"""
    XS = 0        # 超小屏幕 (< 576px)
    SM = 576      # 小屏幕 (≥ 576px)
    MD = 768      # 中等屏幕 (≥ 768px)
    LG = 992      # 大屏幕 (≥ 992px)
    XL = 1200     # 超大屏幕 (≥ 1200px)
    XXL = 1400    # 超超大屏幕 (≥ 1400px)


class LayoutType(Enum):
    """布局类型"""
    FLUID = "fluid"          # 流式布局
    FIXED = "fixed"          # 固定布局
    RESPONSIVE = "responsive" # 响应式布局
    GRID = "grid"           # 网格布局
    FLEX = "flex"           # 弹性布局


class Alignment(Enum):
    """对齐方式"""
    START = "start"          # 开始对齐
    CENTER = "center"        # 居中对齐
    END = "end"             # 结束对齐
    STRETCH = "stretch"     # 拉伸对齐
    BETWEEN = "between"     # 两端对齐
    AROUND = "around"        # 环绕对齐


class DeviceType(Enum):
    """设备类型"""
    MOBILE = "mobile"        # 移动设备
    TABLET = "tablet"        # 平板设备
    DESKTOP = "desktop"      # 桌面设备
    LARGE_DESKTOP = "large_desktop"  # 大屏桌面


@dataclass
class ResponsiveConfig:
    """响应式配置"""
    min_width: int = 0
    max_width: int = 9999
    layout_type: LayoutType = LayoutType.RESPONSIVE
    columns: int = 12
    gutter: int = 16
    margin: int = 16
    padding: int = 16
    hidden: bool = False
    order: Optional[int] = None
    alignment: Alignment = Alignment.START
    spacing: int = 8


class ResponsiveLayoutEngine(QObject):
    """响应式布局引擎"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.breakpoints = {
            Breakpoint.XS: ResponsiveConfig(max_width=575),
            Breakpoint.SM: ResponsiveConfig(min_width=576, max_width=767),
            Breakpoint.MD: ResponsiveConfig(min_width=768, max_width=991),
            Breakpoint.LG: ResponsiveConfig(min_width=992, max_width=1199),
            Breakpoint.XL: ResponsiveConfig(min_width=1200, max_width=1399),
            Breakpoint.XXL: ResponsiveConfig(min_width=1400)
        }
        
        self.current_breakpoint = Breakpoint.MD
        self.current_device_type = DeviceType.DESKTOP
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._handle_resize)
        
        # 注册的组件
        self.registered_widgets: Dict[QWidget, ResponsiveConfig] = {}
        self.layout_callbacks: List[Callable] = []
    
    def register_widget(self, widget: QWidget, config: ResponsiveConfig):
        """注册响应式组件"""
        self.registered_widgets[widget] = config
        
        # 监听组件大小变化
        widget.installEventFilter(self)
    
    def unregister_widget(self, widget: QWidget):
        """注销响应式组件"""
        if widget in self.registered_widgets:
            del self.registered_widgets[widget]
            widget.removeEventFilter(self)
    
    def add_layout_callback(self, callback: Callable[[Breakpoint, DeviceType], None]):
        """添加布局回调函数"""
        self.layout_callbacks.append(callback)
    
    def get_current_breakpoint(self) -> Breakpoint:
        """获取当前断点"""
        return self.current_breakpoint
    
    def get_current_device_type(self) -> DeviceType:
        """获取当前设备类型"""
        return self.current_device_type
    
    def get_breakpoint_for_width(self, width: int) -> Breakpoint:
        """根据宽度获取断点"""
        for breakpoint, config in self.breakpoints.items():
            if config.min_width <= width <= config.max_width:
                return breakpoint
        
        return Breakpoint.XS
    
    def get_device_type_for_breakpoint(self, breakpoint: Breakpoint) -> DeviceType:
        """根据断点获取设备类型"""
        if breakpoint in [Breakpoint.XS, Breakpoint.SM]:
            return DeviceType.MOBILE
        elif breakpoint == Breakpoint.MD:
            return DeviceType.TABLET
        elif breakpoint == Breakpoint.LG:
            return DeviceType.DESKTOP
        else:
            return DeviceType.LARGE_DESKTOP
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if event.type() == QEvent.Type.Resize:
            self.resize_timer.start(100)  # 延迟100ms处理
        
        return super().eventFilter(obj, event)
    
    def _handle_resize(self):
        """处理窗口大小变化"""
        # 获取主窗口大小
        main_window = None
        for widget in self.registered_widgets.keys():
            main_window = widget.window()
            if main_window:
                break
        
        if main_window:
            width = main_window.width()
            new_breakpoint = self.get_breakpoint_for_width(width)
            new_device_type = self.get_device_type_for_breakpoint(new_breakpoint)
            
            # 如果断点发生变化
            if new_breakpoint != self.current_breakpoint:
                self.current_breakpoint = new_breakpoint
                self.current_device_type = new_device_type
                
                # 更新所有注册的组件
                self._update_registered_widgets()
                
                # 调用布局回调
                for callback in self.layout_callbacks:
                    try:
                        callback(self.current_breakpoint, self.current_device_type)
                    except Exception as e:
                        print(f"布局回调执行失败: {e}")
    
    def _update_registered_widgets(self):
        """更新所有注册的组件"""
        config = self.breakpoints[self.current_breakpoint]
        
        for widget, widget_config in self.registered_widgets.items():
            try:
                self._update_widget_layout(widget, config, widget_config)
            except Exception as e:
                print(f"更新组件布局失败: {e}")
    
    def _update_widget_layout(self, widget: QWidget, breakpoint_config: ResponsiveConfig, widget_config: ResponsiveConfig):
        """更新单个组件的布局"""
        # 检查是否应该隐藏
        if widget_config.hidden:
            widget.hide()
            return
        else:
            widget.show()
        
        # 设置间距
        if widget.layout():
            widget.layout().setSpacing(widget_config.spacing)
            widget.layout().setContentsMargins(
                widget_config.margin,
                widget_config.margin,
                widget_config.margin,
                widget_config.margin
            )
        
        # 设置大小策略
        size_policy = widget.sizePolicy()
        if widget_config.alignment == Alignment.STRETCH:
            size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
            size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        else:
            size_policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
            size_policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        
        widget.setSizePolicy(size_policy)
        
        # 设置最小/最大尺寸
        if widget_config.min_width > 0:
            widget.setMinimumWidth(widget_config.min_width)
        
        if widget_config.max_width < 9999:
            widget.setMaximumWidth(widget_config.max_width)


class ResponsiveContainer(QWidget):
    """响应式容器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_engine = ResponsiveLayoutEngine()
        self.child_configs: Dict[QWidget, ResponsiveConfig] = {}
        
        # 设置默认布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(self, ResponsiveConfig())
        
        # 监听断点变化
        self.layout_engine.add_layout_callback(self._on_breakpoint_changed)
    
    def add_widget(self, widget: QWidget, config: Optional[ResponsiveConfig] = None):
        """添加响应式组件"""
        if config is None:
            config = ResponsiveConfig()
        
        self.child_configs[widget] = config
        self.main_layout.addWidget(widget)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(widget, config)
    
    def remove_widget(self, widget: QWidget):
        """移除响应式组件"""
        if widget in self.child_configs:
            del self.child_configs[widget]
            self.main_layout.removeWidget(widget)
            
            # 从布局引擎注销
            self.layout_engine.unregister_widget(widget)
    
    def _on_breakpoint_changed(self, breakpoint: Breakpoint, device_type: DeviceType):
        """断点变化处理"""
        # 可以在这里添加特定的断点处理逻辑
        self.breakpoint_changed.emit(breakpoint, device_type)
    
    # 信号
    breakpoint_changed = pyqtSignal(Breakpoint, DeviceType)


class ResponsiveGrid(QWidget):
    """响应式网格布局"""
    
    def __init__(self, parent=None, columns: int = 12):
        super().__init__(parent)
        self.columns = columns
        self.layout_engine = ResponsiveLayoutEngine()
        self.grid_items: List[Dict] = []
        
        # 设置网格布局
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(0)
        self.setLayout(self.grid_layout)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(self, ResponsiveConfig())
        self.layout_engine.add_layout_callback(self._on_breakpoint_changed)
    
    def add_widget(self, widget: QWidget, col_span: int = 1, row_span: int = 1, 
                   config: Optional[ResponsiveConfig] = None):
        """添加网格组件"""
        if config is None:
            config = ResponsiveConfig()
        
        # 计算位置
        row, col = self._find_next_position(col_span, row_span)
        
        # 添加到网格
        self.grid_layout.addWidget(widget, row, col, row_span, col_span)
        
        # 保存配置
        grid_item = {
            'widget': widget,
            'col_span': col_span,
            'row_span': row_span,
            'config': config,
            'row': row,
            'col': col
        }
        self.grid_items.append(grid_item)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(widget, config)
    
    def _find_next_position(self, col_span: int, row_span: int) -> Tuple[int, int]:
        """查找下一个可用位置"""
        # 简单的行优先布局
        current_row = 0
        current_col = 0
        
        for item in self.grid_items:
            if item['row'] == current_row:
                current_col += item['col_span']
                if current_col + col_span > self.columns:
                    current_row += 1
                    current_col = 0
        
        return current_row, current_col
    
    def _on_breakpoint_changed(self, breakpoint: Breakpoint, device_type: DeviceType):
        """断点变化处理"""
        # 根据断点调整网格布局
        self._adjust_grid_layout(breakpoint, device_type)
    
    def _adjust_grid_layout(self, breakpoint: Breakpoint, device_type: DeviceType):
        """调整网格布局"""
        # 根据设备类型调整列数
        if device_type == DeviceType.MOBILE:
            target_columns = 4
        elif device_type == DeviceType.TABLET:
            target_columns = 8
        else:
            target_columns = self.columns
        
        # 重新布局网格
        self._reorganize_grid(target_columns)
    
    def _reorganize_grid(self, target_columns: int):
        """重新组织网格"""
        # 清空当前布局
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # 重新添加组件
        current_row = 0
        current_col = 0
        
        for item in self.grid_items:
            widget = item['widget']
            col_span = min(item['col_span'], target_columns)
            row_span = item['row_span']
            
            # 检查是否需要换行
            if current_col + col_span > target_columns:
                current_row += 1
                current_col = 0
            
            # 添加到网格
            self.grid_layout.addWidget(widget, current_row, current_col, row_span, col_span)
            
            current_col += col_span


class ResponsiveStack(QWidget):
    """响应式堆栈布局"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_engine = ResponsiveLayoutEngine()
        self.stack_configs: Dict[QWidget, List[ResponsiveConfig]] = {}
        
        # 设置堆栈布局
        self.stacked_layout = QStackedWidget()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stacked_layout)
        self.setLayout(self.main_layout)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(self, ResponsiveConfig())
        self.layout_engine.add_layout_callback(self._on_breakpoint_changed)
    
    def add_widget(self, widget: QWidget, configs: List[ResponsiveConfig]):
        """添加堆栈组件"""
        self.stacked_layout.addWidget(widget)
        self.stack_configs[widget] = configs
        
        # 注册到布局引擎
        for config in configs:
            self.layout_engine.register_widget(widget, config)
    
    def _on_breakpoint_changed(self, breakpoint: Breakpoint, device_type: DeviceType):
        """断点变化处理"""
        # 查找适合当前断点的组件
        for i in range(self.stacked_layout.count()):
            widget = self.stacked_layout.widget(i)
            configs = self.stack_configs.get(widget, [])
            
            for config in configs:
                if self._is_config_suitable(config, breakpoint, device_type):
                    self.stacked_layout.setCurrentWidget(widget)
                    break
    
    def _is_config_suitable(self, config: ResponsiveConfig, breakpoint: Breakpoint, device_type: DeviceType) -> bool:
        """检查配置是否适合当前断点"""
        if config.hidden:
            return False
        
        # 检查设备类型
        if device_type == DeviceType.MOBILE and breakpoint in [Breakpoint.XS, Breakpoint.SM]:
            return True
        elif device_type == DeviceType.TABLET and breakpoint == Breakpoint.MD:
            return True
        elif device_type == DeviceType.DESKTOP and breakpoint == Breakpoint.LG:
            return True
        elif device_type == DeviceType.LARGE_DESKTOP and breakpoint in [Breakpoint.XL, Breakpoint.XXL]:
            return True
        
        return False


class ResponsiveSplitter(QSplitter):
    """响应式分割器"""
    
    def __init__(self, parent=None, orientation: Qt.Orientation = Qt.Orientation.Horizontal):
        super().__init__(orientation, parent)
        self.layout_engine = ResponsiveLayoutEngine()
        self.splitter_configs: Dict[QWidget, ResponsiveConfig] = {}
        
        # 注册到布局引擎
        self.layout_engine.register_widget(self, ResponsiveConfig())
        self.layout_engine.add_layout_callback(self._on_breakpoint_changed)
    
    def add_widget(self, widget: QWidget, config: Optional[ResponsiveConfig] = None):
        """添加分割器组件"""
        if config is None:
            config = ResponsiveConfig()
        
        self.addWidget(widget)
        self.splitter_configs[widget] = config
        
        # 注册到布局引擎
        self.layout_engine.register_widget(widget, config)
    
    def _on_breakpoint_changed(self, breakpoint: Breakpoint, device_type: DeviceType):
        """断点变化处理"""
        # 根据断点调整分割器比例
        self._adjust_splitter_sizes(breakpoint, device_type)
    
    def _adjust_splitter_sizes(self, breakpoint: Breakpoint, device_type: DeviceType):
        """调整分割器大小"""
        if device_type == DeviceType.MOBILE:
            # 移动设备上使用垂直布局
            self.setOrientation(Qt.Orientation.Vertical)
            sizes = [self.width() // 2, self.width() // 2]
        else:
            # 桌面设备上使用水平布局
            self.setOrientation(Qt.Orientation.Horizontal)
            sizes = [self.width() * 2 // 3, self.width() // 3]
        
        self.setSizes(sizes)


class ResponsiveMenuBar(QWidget):
    """响应式菜单栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_engine = ResponsiveLayoutEngine()
        self.menu_items: List[Dict] = []
        
        # 设置布局
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        
        # 创建菜单容器
        self.menu_container = QWidget()
        self.menu_layout = QHBoxLayout()
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(0)
        self.menu_container.setLayout(self.menu_layout)
        
        # 创建汉堡菜单
        self.hamburger_button = QPushButton("☰")
        self.hamburger_button.setFixedSize(40, 40)
        self.hamburger_button.hide()
        self.hamburger_button.clicked.connect(self._toggle_hamburger_menu)
        
        self.main_layout.addWidget(self.hamburger_button)
        self.main_layout.addWidget(self.menu_container)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(self, ResponsiveConfig())
        self.layout_engine.add_layout_callback(self._on_breakpoint_changed)
    
    def add_menu_item(self, text: str, callback: Callable, config: Optional[ResponsiveConfig] = None):
        """添加菜单项"""
        if config is None:
            config = ResponsiveConfig()
        
        button = QPushButton(text)
        button.clicked.connect(callback)
        
        self.menu_layout.addWidget(button)
        
        menu_item = {
            'button': button,
            'config': config,
            'callback': callback
        }
        self.menu_items.append(menu_item)
        
        # 注册到布局引擎
        self.layout_engine.register_widget(button, config)
    
    def _on_breakpoint_changed(self, breakpoint: Breakpoint, device_type: DeviceType):
        """断点变化处理"""
        # 根据断点调整菜单显示
        if device_type == DeviceType.MOBILE:
            self.hamburger_button.show()
            self.menu_container.hide()
        else:
            self.hamburger_button.hide()
            self.menu_container.show()
    
    def _toggle_hamburger_menu(self):
        """切换汉堡菜单"""
        # 这里可以实现汉堡菜单的显示/隐藏逻辑
        pass


# 工厂函数
def create_responsive_container(parent=None) -> ResponsiveContainer:
    """创建响应式容器"""
    return ResponsiveContainer(parent)


def create_responsive_grid(parent=None, columns: int = 12) -> ResponsiveGrid:
    """创建响应式网格"""
    return ResponsiveGrid(parent, columns)


def create_responsive_stack(parent=None) -> ResponsiveStack:
    """创建响应式堆栈"""
    return ResponsiveStack(parent)


def create_responsive_splitter(parent=None, orientation: Qt.Orientation = Qt.Orientation.Horizontal) -> ResponsiveSplitter:
    """创建响应式分割器"""
    return ResponsiveSplitter(parent, orientation)


def create_responsive_menu_bar(parent=None) -> ResponsiveMenuBar:
    """创建响应式菜单栏"""
    return ResponsiveMenuBar(parent)


# 便捷函数
def create_mobile_config() -> ResponsiveConfig:
    """创建移动设备配置"""
    return ResponsiveConfig(
        max_width=575,
        columns=4,
        gutter=8,
        margin=8,
        padding=8
    )


def create_tablet_config() -> ResponsiveConfig:
    """创建平板设备配置"""
    return ResponsiveConfig(
        min_width=576,
        max_width=991,
        columns=8,
        gutter=12,
        margin=12,
        padding=12
    )


def create_desktop_config() -> ResponsiveConfig:
    """创建桌面设备配置"""
    return ResponsiveConfig(
        min_width=992,
        columns=12,
        gutter=16,
        margin=16,
        padding=16
    )


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    
    app = QApplication(sys.argv)
    
    # 创建响应式容器
    container = create_responsive_container()
    container.setWindowTitle("响应式布局测试")
    container.resize(800, 600)
    
    # 添加测试组件
    label1 = QLabel("组件 1")
    label1.setStyleSheet("background-color: #ff6b6b; color: white; padding: 20px;")
    
    label2 = QLabel("组件 2")
    label2.setStyleSheet("background-color: #4ecdc4; color: white; padding: 20px;")
    
    button = QPushButton("点击测试")
    button.setStyleSheet("background-color: #45b7d1; color: white; padding: 20px;")
    
    # 添加响应式配置
    mobile_config = create_mobile_config()
    tablet_config = create_tablet_config()
    desktop_config = create_desktop_config()
    
    container.add_widget(label1, mobile_config)
    container.add_widget(label2, tablet_config)
    container.add_widget(button, desktop_config)
    
    container.show()
    sys.exit(app.exec())