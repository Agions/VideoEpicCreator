#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一组件基类系统
为所有UI组件提供统一的基础功能和生命周期管理
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLayout
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui import QFont


class ComponentState(Enum):
    """组件状态枚举"""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class ComponentConfig:
    """组件配置数据类"""
    name: str
    version: str = "1.0.0"
    enabled: bool = True
    theme_support: bool = True
    auto_save: bool = True
    debug_mode: bool = False
    custom_settings: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_settings is None:
            self.custom_settings = {}


class ComponentError(Exception):
    """组件异常基类"""

    def __init__(self, message: str, error_code: str = "COMPONENT_ERROR",
                 component_name: str = "Unknown", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.component_name = component_name
        self.details = details or {}
        self.timestamp = None

    def __str__(self):
        return f"[{self.component_name}] {self.error_code}: {super().__str__()}"


class BaseComponent(QWidget):
    """统一组件基类

    所有UI组件都应该继承这个基类，以获得统一的功能：
    - 生命周期管理
    - 状态管理
    - 主题支持
    - 错误处理
    - 配置管理
    - 日志记录
    """

    # 信号定义
    state_changed = pyqtSignal(ComponentState)          # 状态变更信号
    error_occurred = pyqtSignal(str, str)             # 错误信号 (error_code, message)
    config_changed = pyqtSignal(dict)                 # 配置变更信号
    theme_changed = pyqtSignal(bool)                  # 主题变更信号
    component_initialized = pyqtSignal()               # 组件初始化完成信号

    def __init__(self, parent: Optional[QWidget] = None,
                 config: Optional[ComponentConfig] = None):
        """初始化组件基类

        Args:
            parent: 父窗口部件
            config: 组件配置对象

        Raises:
            ComponentError: 组件初始化失败时抛出
        """
        super().__init__(parent)

        # 组件基本信息
        self._component_name = self.__class__.__name__
        self._component_version = "1.0.0"

        # 状态管理
        self._state = ComponentState.INITIALIZING
        self._is_enabled = True
        self._is_visible = True

        # 配置管理
        self._config = config or ComponentConfig(name=self._component_name)
        self._settings = QSettings(f"CineAIStudio/{self._component_name}", "ComponentSettings")

        # 主题相关
        self._is_dark_theme = False
        self._theme_support = self._config.theme_support

        # 错误处理
        self._error_count = 0
        self._max_errors = 10

        # 日志记录
        self._logger = logging.getLogger(f"component.{self._component_name.lower()}")

        # 性能监控
        self._performance_timer = QTimer()
        self._performance_timer.timeout.connect(self._check_performance)

        # 自动保存
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)

        # 初始化组件
        try:
            self._initialize_component()
            self.state_changed.emit(ComponentState.READY)
            self.component_initialized.emit()
            self._logger.info(f"Component {self._component_name} initialized successfully")
        except Exception as e:
            self._handle_error(f"Failed to initialize component: {str(e)}", "INIT_ERROR")
            self._state = ComponentState.ERROR
            self.state_changed.emit(ComponentState.ERROR)
            raise ComponentError(
                message=f"Component initialization failed: {str(e)}",
                error_code="INIT_ERROR",
                component_name=self._component_name
            )

    @abstractmethod
    def _setup_ui(self) -> None:
        """设置UI界面 - 子类必须实现

        这个方法应该在子类中实现，用于创建和设置组件的UI界面。
        """
        raise NotImplementedError("Subclasses must implement _setup_ui()")

    def _connect_signals(self) -> None:
        """连接信号和槽 - 子类可选实现

        子类可以重写这个方法来连接特定的信号和槽。
        """
        pass

    def _apply_styles(self) -> None:
        """应用样式 - 子类可选实现

        子类可以重写这个方法来应用自定义样式。
        """
        pass

    def _initialize_component(self) -> None:
        """初始化组件

        这个方法负责组件的完整初始化流程。
        """
        # 设置UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

        # 应用样式
        if self._theme_support:
            self._apply_styles()

        # 加载配置
        self._load_config()

        # 启动定时器
        if self._config.auto_save:
            self._start_auto_save()

        # 性能监控
        if self._config.debug_mode:
            self._start_performance_monitoring()

    def _load_config(self) -> None:
        """加载组件配置"""
        try:
            # 从QSettings加载配置
            custom_settings = self._settings.value("custom_settings", {})
            if custom_settings:
                self._config.custom_settings.update(custom_settings)

            # 加载主题设置
            self._is_dark_theme = self._settings.value("dark_theme", False, bool)

            self._logger.debug(f"Configuration loaded for {self._component_name}")
        except Exception as e:
            self._handle_error(f"Failed to load configuration: {str(e)}", "CONFIG_ERROR")

    def _save_config(self) -> None:
        """保存组件配置"""
        try:
            self._settings.setValue("custom_settings", self._config.custom_settings)
            self._settings.setValue("dark_theme", self._is_dark_theme)
            self._settings.sync()

            self._logger.debug(f"Configuration saved for {self._component_name}")
        except Exception as e:
            self._handle_error(f"Failed to save configuration: {str(e)}", "CONFIG_ERROR")

    def _handle_error(self, message: str, error_code: str = "UNKNOWN_ERROR",
                     details: Optional[Dict[str, Any]] = None) -> None:
        """处理错误

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        self._error_count += 1

        # 记录错误日志
        self._logger.error(f"{error_code}: {message}", extra=details)

        # 发射错误信号
        self.error_occurred.emit(error_code, message)

        # 如果错误过多，禁用组件
        if self._error_count >= self._max_errors:
            self._disable_component()
            self._logger.warning(f"Component {self._component_name} disabled due to too many errors")

    def _disable_component(self) -> None:
        """禁用组件"""
        self._is_enabled = False
        self.setEnabled(False)
        self._state = ComponentState.ERROR
        self.state_changed.emit(ComponentState.ERROR)

    def _start_auto_save(self) -> None:
        """启动自动保存"""
        self._auto_save_timer.start(30000)  # 30秒

    def _auto_save(self) -> None:
        """自动保存配置"""
        if self._config.auto_save:
            self._save_config()

    def _start_performance_monitoring(self) -> None:
        """启动性能监控"""
        self._performance_timer.start(5000)  # 5秒

    def _check_performance(self) -> None:
        """检查性能"""
        # 子类可以实现具体的性能检查逻辑
        pass

    # 公共方法
    def set_theme(self, is_dark: bool) -> None:
        """设置主题

        Args:
            is_dark: 是否使用深色主题
        """
        if not self._theme_support:
            return

        self._is_dark_theme = is_dark
        self._apply_styles()
        self.theme_changed.emit(is_dark)

        # 保存主题设置
        self._settings.setValue("dark_theme", is_dark)

    def set_enabled(self, enabled: bool) -> None:
        """设置组件启用状态

        Args:
            enabled: 是否启用组件
        """
        self._is_enabled = enabled
        self.setEnabled(enabled)

        if enabled:
            self._state = ComponentState.READY
        else:
            self._state = ComponentState.INACTIVE

        self.state_changed.emit(self._state)

    def set_visible(self, visible: bool) -> None:
        """设置组件可见性

        Args:
            visible: 是否可见
        """
        self._is_visible = visible
        self.setVisible(visible)

    def get_config(self) -> ComponentConfig:
        """获取组件配置

        Returns:
            ComponentConfig: 组件配置对象
        """
        return self._config

    def update_config(self, **kwargs) -> None:
        """更新组件配置

        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        self._save_config()
        self.config_changed.emit(self._config.custom_settings)

    def get_state(self) -> ComponentState:
        """获取组件状态

        Returns:
            ComponentState: 当前状态
        """
        return self._state

    def is_enabled(self) -> bool:
        """检查组件是否启用

        Returns:
            bool: 是否启用
        """
        return self._is_enabled

    def is_visible(self) -> bool:
        """检查组件是否可见

        Returns:
            bool: 是否可见
        """
        return self._is_visible

    def get_error_count(self) -> int:
        """获取错误计数

        Returns:
            int: 错误数量
        """
        return self._error_count

    def reset_error_count(self) -> None:
        """重置错误计数"""
        self._error_count = 0

    def cleanup(self) -> None:
        """清理组件资源

        子类应该重写这个方法来清理特定的资源。
        """
        # 停止定时器
        self._auto_save_timer.stop()
        self._performance_timer.stop()

        # 保存配置
        self._save_config()

        # 更新状态
        self._state = ComponentState.DESTROYED
        self.state_changed.emit(ComponentState.DESTROYED)

        self._logger.info(f"Component {self._component_name} cleaned up")

    def closeEvent(self, event) -> None:
        """关闭事件处理"""
        self.cleanup()
        super().closeEvent(event)

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass  # 防止析构时出现异常


class ContainerComponent(BaseComponent):
    """容器组件基类

    用于包含其他组件的容器类组件。
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 config: Optional[ComponentConfig] = None,
                 layout_type: str = "vertical"):
        """初始化容器组件

        Args:
            parent: 父窗口部件
            config: 组件配置
            layout_type: 布局类型 ("vertical", "horizontal", "grid")
        """
        self._layout_type = layout_type
        self._child_components: List[BaseComponent] = []
        super().__init__(parent, config)

    def _setup_ui(self) -> None:
        """设置容器UI"""
        if self._layout_type == "vertical":
            self._main_layout = QVBoxLayout()
        elif self._layout_type == "horizontal":
            self._main_layout = QHBoxLayout()
        else:
            self._main_layout = QVBoxLayout()  # 默认垂直布局

        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.setLayout(self._main_layout)

    def add_component(self, component: BaseComponent,
                     stretch: int = 0, alignment: Optional[Qt.AlignmentFlag] = None) -> None:
        """添加子组件

        Args:
            component: 要添加的组件
            stretch: 拉伸因子
            alignment: 对齐方式
        """
        if not isinstance(component, BaseComponent):
            raise ComponentError("Child component must inherit from BaseComponent")

        self._child_components.append(component)

        if alignment:
            self._main_layout.addWidget(component, stretch, alignment)
        else:
            self._main_layout.addWidget(component, stretch)

        # 连接子组件信号
        component.error_occurred.connect(self._on_child_error)
        component.state_changed.connect(self._on_child_state_changed)

    def remove_component(self, component: BaseComponent) -> None:
        """移除子组件

        Args:
            component: 要移除的组件
        """
        if component in self._child_components:
            self._child_components.remove(component)
            self._main_layout.removeWidget(component)

            # 断开信号连接
            component.error_occurred.disconnect(self._on_child_error)
            component.state_changed.disconnect(self._on_child_state_changed)

            # 清理组件
            component.cleanup()

    def _on_child_error(self, error_code: str, message: str) -> None:
        """处理子组件错误"""
        self._handle_error(f"Child component error: {message}", f"CHILD_{error_code}")

    def _on_child_state_changed(self, state: ComponentState) -> None:
        """处理子组件状态变更"""
        # 可以在这里实现容器级别的状态管理逻辑
        pass

    def cleanup(self) -> None:
        """清理容器和所有子组件"""
        # 清理所有子组件
        for component in self._child_components[:]:  # 使用副本避免修改列表时的问题
            self.remove_component(component)

        super().cleanup()


# 工厂函数
def create_component(component_class: type, *args, **kwargs) -> BaseComponent:
    """创建组件实例的工厂函数

    Args:
        component_class: 组件类
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        BaseComponent: 组件实例

    Raises:
        ComponentError: 如果组件类无效
    """
    if not issubclass(component_class, BaseComponent):
        raise ComponentError("Component class must inherit from BaseComponent")

    try:
        return component_class(*args, **kwargs)
    except Exception as e:
        raise ComponentError(f"Failed to create component: {str(e)}", "CREATE_ERROR")


# 装饰器用于自动注册组件
def register_component(component_name: str):
    """组件注册装饰器

    Args:
        component_name: 组件名称
    """
    def decorator(cls):
        cls._component_name = component_name
        return cls
    return decorator


if __name__ == "__main__":
    # 示例用法
    class ExampleComponent(BaseComponent):
        """示例组件"""

        def _setup_ui(self):
            layout = QVBoxLayout(self)
            label = QLabel("Example Component")
            layout.addWidget(label)

        def _apply_styles(self):
            if self._is_dark_theme:
                self.setStyleSheet("background-color: #2b2b2b; color: white;")
            else:
                self.setStyleSheet("background-color: white; color: black;")

    # 创建示例组件
    example = ExampleComponent()
    print(f"Component created: {example._component_name}")
    print(f"Component state: {example.get_state()}")
