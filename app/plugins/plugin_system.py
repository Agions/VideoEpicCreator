#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件系统核心架构
提供可扩展的插件框架，支持AI提供商、特效、导出格式等扩展
"""

import os
import sys
import json
import logging
import importlib
import inspect
import traceback
from typing import Dict, Any, List, Optional, Type, Callable, Union
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pkg_resources

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# 设置日志
logger = logging.getLogger(__name__)


class PluginType(Enum):
    """插件类型枚举"""
    AI_PROVIDER = "ai_provider"           # AI服务提供商
    EFFECT = "effect"                     # 视频特效
    TRANSITION = "transition"             # 转场效果
    EXPORT_FORMAT = "export_format"       # 导出格式
    IMPORT_FORMAT = "import_format"       # 导入格式
    FILTER = "filter"                     # 滤镜效果
    ANIMATION = "animation"               # 动画效果
    THEME = "theme"                       # 主题插件
    TOOL = "tool"                         # 工具插件
    UTILITY = "utility"                   # 实用工具


class PluginState(Enum):
    """插件状态"""
    LOADED = "loaded"                     # 已加载
    INITIALIZED = "initialized"           # 已初始化
    RUNNING = "running"                   # 运行中
    PAUSED = "paused"                     # 已暂停
    ERROR = "error"                       # 错误状态
    UNLOADED = "unloaded"                 # 已卸载


class PluginPriority(Enum):
    """插件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str                           # 插件名称
    version: str                        # 版本号
    description: str                    # 描述
    author: str                         # 作者
    email: str = ""                     # 邮箱
    website: str = ""                   # 网站
    plugin_type: PluginType = None      # 插件类型
    category: str = ""                 # 分类
    tags: List[str] = field(default_factory=list)  # 标签
    dependencies: List[str] = field(default_factory=list)  # 依赖
    min_app_version: str = "2.0.0"     # 最低应用版本
    max_app_version: str = ""          # 最高应用版本
    api_version: str = "1.0"           # API版本
    priority: PluginPriority = PluginPriority.NORMAL  # 优先级
    enabled: bool = True                # 默认启用
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置架构


@dataclass
class PluginContext:
    """插件上下文"""
    app_version: str
    data_dir: Path
    config_dir: Path
    temp_dir: Path
    service_container: Any  # ServiceContainer instance
    settings_manager: Any  # SettingsManager instance
    theme_manager: Any     # ThemeManager instance


class PluginInterface:
    """插件基础接口"""

    def __init__(self):
        self._metadata = None
        self._context = None
        self._state = PluginState.LOADED
        self._config = {}

    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        if self._metadata is None:
            self._metadata = self.get_metadata()
        return self._metadata

    @property
    def context(self) -> PluginContext:
        """获取插件上下文"""
        return self._context

    @property
    def state(self) -> PluginState:
        """获取插件状态"""
        return self._state

    @property
    def config(self) -> Dict[str, Any]:
        """获取插件配置"""
        return self._config

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass

    @abstractmethod
    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def cleanup(self):
        """清理插件资源"""
        pass

    def get_config_ui(self) -> Optional[Any]:
        """获取配置界面（可选）"""
        return None

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        return True

    def on_config_changed(self, new_config: Dict[str, Any]):
        """配置变化回调"""
        self._config.update(new_config)

    def on_app_shutdown(self):
        """应用关闭回调"""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """获取插件能力描述"""
        return {}

    def get_status(self) -> Dict[str, Any]:
        """获取插件状态信息"""
        return {
            "state": self._state.value,
            "version": self.metadata.version,
            "enabled": self.metadata.enabled
        }


class AIProviderPlugin(PluginInterface):
    """AI服务提供商插件接口"""

    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        pass

    @abstractmethod
    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """估算成本"""
        pass


class EffectPlugin(PluginInterface):
    """特效插件接口"""

    @abstractmethod
    def get_effect_types(self) -> List[str]:
        """获取特效类型"""
        pass

    @abstractmethod
    def create_effect(self, effect_type: str, params: Dict[str, Any]) -> Any:
        """创建特效实例"""
        pass

    @abstractmethod
    def get_effect_params(self, effect_type: str) -> Dict[str, Any]:
        """获取特效参数"""
        pass

    @abstractmethod
    def render_preview(self, effect: Any, params: Dict[str, Any]) -> Any:
        """渲染预览"""
        pass


class ExportPlugin(PluginInterface):
    """导出插件接口"""

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的导出格式"""
        pass

    @abstractmethod
    def get_format_options(self, format_name: str) -> Dict[str, Any]:
        """获取格式选项"""
        pass

    @abstractmethod
    def export(self, project_data: Any, output_path: str, options: Dict[str, Any]) -> bool:
        """执行导出"""
        pass

    @abstractmethod
    def validate_export_options(self, options: Dict[str, Any]) -> bool:
        """验证导出选项"""
        pass


class PluginManager(QObject):
    """插件管理器"""

    # 信号定义
    plugin_loaded = pyqtSignal(str)  # plugin_id
    plugin_unloaded = pyqtSignal(str)  # plugin_id
    plugin_error = pyqtSignal(str, str)  # plugin_id, error_message
    plugin_state_changed = pyqtSignal(str, str)  # plugin_id, state

    def __init__(self, context: PluginContext):
        super().__init__()
        self.context = context
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.plugin_paths: List[Path] = []
        self.enabled_plugins: Dict[str, bool] = {}

        # 初始化插件路径
        self._init_plugin_paths()

    def _init_plugin_paths(self):
        """初始化插件路径"""
        # 系统插件目录
        system_plugin_dir = self.context.data_dir / "plugins"
        system_plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugin_paths.append(system_plugin_dir)

        # 用户插件目录
        user_plugin_dir = Path.home() / ".cineai_studio" / "plugins"
        user_plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugin_paths.append(user_plugin_dir)

        # 应用插件目录
        app_plugin_dir = Path(__file__).parent.parent / "plugins"
        if app_plugin_dir.exists():
            self.plugin_paths.append(app_plugin_dir)

        logger.info(f"插件搜索路径: {[str(p) for p in self.plugin_paths]}")

    def discover_plugins(self) -> List[str]:
        """发现可用插件"""
        discovered_plugins = []

        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue

            for item in plugin_path.iterdir():
                if item.is_dir():
                    # 目录插件
                    plugin_file = item / "plugin.py"
                    if plugin_file.exists():
                        discovered_plugins.append(str(item))
                elif item.suffix == '.py' and item.name != '__init__.py':
                    # 单文件插件
                    discovered_plugins.append(str(item))

        logger.info(f"发现插件: {discovered_plugins}")
        return discovered_plugins

    def load_plugin(self, plugin_path: str) -> bool:
        """加载插件"""
        try:
            plugin_path = Path(plugin_path)
            plugin_id = plugin_path.name

            # 检查是否已加载
            if plugin_id in self.plugins:
                logger.warning(f"插件已加载: {plugin_id}")
                return True

            # 动态导入插件模块
            if plugin_path.is_dir():
                sys.path.insert(0, str(plugin_path.parent))
                module = importlib.import_module(f"{plugin_path.name}.plugin")
            else:
                sys.path.insert(0, str(plugin_path.parent))
                module = importlib.import_module(plugin_path.stem)

            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and
                    obj != PluginInterface and
                    obj.__module__ == module.__name__):
                    plugin_class = obj
                    break

            if not plugin_class:
                logger.error(f"未找到插件类: {plugin_path}")
                return False

            # 创建插件实例
            plugin_instance = plugin_class()

            # 验证插件元数据
            metadata = plugin_instance.metadata
            if not self._validate_metadata(metadata):
                logger.error(f"插件元数据无效: {plugin_id}")
                return False

            # 检查版本兼容性
            if not self._check_version_compatibility(metadata):
                logger.error(f"插件版本不兼容: {plugin_id}")
                return False

            # 初始化插件
            if not plugin_instance.initialize(self.context):
                logger.error(f"插件初始化失败: {plugin_id}")
                return False

            # 注册插件
            self.plugins[plugin_id] = plugin_instance
            self.plugin_metadata[plugin_id] = metadata
            self.enabled_plugins[plugin_id] = metadata.enabled

            plugin_instance._state = PluginState.INITIALIZED

            logger.info(f"插件加载成功: {plugin_id} v{metadata.version}")
            self.plugin_loaded.emit(plugin_id)
            self.plugin_state_changed.emit(plugin_id, PluginState.INITIALIZED.value)

            return True

        except Exception as e:
            error_msg = f"加载插件失败: {plugin_path} - {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.plugin_error.emit(plugin_path, error_msg)
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        try:
            if plugin_id not in self.plugins:
                logger.warning(f"插件未加载: {plugin_id}")
                return False

            plugin = self.plugins[plugin_id]
            plugin.cleanup()
            plugin._state = PluginState.UNLOADED

            # 从注册表中移除
            del self.plugins[plugin_id]
            del self.plugin_metadata[plugin_id]
            del self.enabled_plugins[plugin_id]

            logger.info(f"插件卸载成功: {plugin_id}")
            self.plugin_unloaded.emit(plugin_id)
            self.plugin_state_changed.emit(plugin_id, PluginState.UNLOADED.value)

            return True

        except Exception as e:
            error_msg = f"卸载插件失败: {plugin_id} - {str(e)}"
            logger.error(error_msg)
            self.plugin_error.emit(plugin_id, error_msg)
            return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id not in self.plugins:
            return False

        self.enabled_plugins[plugin_id] = True
        logger.info(f"插件已启用: {plugin_id}")
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id not in self.plugins:
            return False

        self.enabled_plugins[plugin_id] = False
        logger.info(f"插件已禁用: {plugin_id}")
        return True

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        plugin = self.plugins.get(plugin_id)
        if plugin and self.enabled_plugins.get(plugin_id, False):
            return plugin
        return None

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInterface]:
        """按类型获取插件"""
        return [
            plugin for plugin_id, plugin in self.plugins.items()
            if (self.enabled_plugins.get(plugin_id, False) and
                plugin.metadata.plugin_type == plugin_type)
        ]

    def get_all_plugins(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件信息"""
        plugin_info = {}
        for plugin_id, plugin in self.plugins.items():
            plugin_info[plugin_id] = {
                "metadata": plugin.metadata.__dict__,
                "state": plugin.state.value,
                "enabled": self.enabled_plugins.get(plugin_id, False),
                "status": plugin.get_status()
            }
        return plugin_info

    def load_all_plugins(self):
        """加载所有可用插件"""
        discovered_plugins = self.discover_plugins()
        success_count = 0

        for plugin_path in discovered_plugins:
            if self.load_plugin(plugin_path):
                success_count += 1

        logger.info(f"插件加载完成: {success_count}/{len(discovered_plugins)}")
        return success_count

    def _validate_metadata(self, metadata: PluginMetadata) -> bool:
        """验证插件元数据"""
        required_fields = ['name', 'version', 'description', 'author', 'plugin_type']
        for field in required_fields:
            if not getattr(metadata, field):
                logger.error(f"缺少必需字段: {field}")
                return False
        return True

    def _check_version_compatibility(self, metadata: PluginMetadata) -> bool:
        """检查版本兼容性"""
        # 简单的版本检查
        app_version = self.context.app_version
        min_version = metadata.min_app_version
        max_version = metadata.max_app_version

        if max_version and app_version > max_version:
            logger.error(f"应用版本过高: {app_version} > {max_version}")
            return False

        if app_version < min_version:
            logger.error(f"应用版本过低: {app_version} < {min_version}")
            return False

        return True

    def save_plugin_config(self, plugin_id: str, config: Dict[str, Any]):
        """保存插件配置"""
        if plugin_id not in self.plugins:
            return False

        config_file = self.context.config_dir / f"plugin_{plugin_id}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存插件配置失败: {plugin_id} - {e}")
            return False

    def load_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """加载插件配置"""
        config_file = self.context.config_dir / f"plugin_{plugin_id}.json"
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载插件配置失败: {plugin_id} - {e}")
            return {}

    def cleanup_all(self):
        """清理所有插件"""
        for plugin_id in list(self.plugins.keys()):
            self.unload_plugin(plugin_id)

        logger.info("所有插件已清理")


# 插件注册装饰器
def plugin_class(plugin_type: PluginType):
    """插件类装饰器"""
    def decorator(cls):
        if not hasattr(cls, '_metadata'):
            cls._metadata = PluginMetadata(
                name=cls.__name__,
                version="1.0.0",
                description=cls.__doc__ or "",
                author="Unknown",
                plugin_type=plugin_type
            )
        return cls
    return decorator


def ai_provider_plugin(name: str, version: str = "1.0.0"):
    """AI提供商插件装饰器"""
    def decorator(cls):
        cls._metadata = PluginMetadata(
            name=name,
            version=version,
            description=cls.__doc__ or "",
            author="Unknown",
            plugin_type=PluginType.AI_PROVIDER
        )
        return cls
    return decorator


def effect_plugin(name: str, version: str = "1.0.0"):
    """特效插件装饰器"""
    def decorator(cls):
        cls._metadata = PluginMetadata(
            name=name,
            version=version,
            description=cls.__doc__ or "",
            author="Unknown",
            plugin_type=PluginType.EFFECT
        )
        return cls
    return decorator