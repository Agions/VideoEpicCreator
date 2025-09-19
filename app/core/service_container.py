#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务容器实现
实现单例模式的依赖注入管理，管理所有核心服务的生命周期
"""

import logging
import threading
from typing import Dict, Any, Optional, Type, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"  # 单例模式
    TRANSIENT = "transient"  # 瞬态模式
    SCOPED = "scoped"       # 作用域模式


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    interface: Type
    implementation: Type
    lifetime: ServiceLifetime
    instance: Any = None
    factory: Optional[callable] = None
    dependencies: list = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ServiceContainer(QObject):
    """服务容器"""
    
    _instance = None
    _lock = threading.Lock()
    
    # 信号定义
    service_registered = pyqtSignal(str, object)  # service_name, service_instance
    service_resolved = pyqtSignal(str, object)    # service_name, service_instance
    container_built = pyqtSignal()                # 容器构建完成
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        super().__init__()
        
        # 服务注册表
        self._services: Dict[str, ServiceDescriptor] = {}
        self._instances: Dict[str, Any] = {}
        self._building = False
        self._built = False
        
        # 线程安全
        self._service_lock = threading.RLock()
        
        self._initialized = True
        
        logger.info("服务容器初始化完成")
    
    def register_singleton(self, interface, implementation = None, 
                          factory: callable = None) -> 'ServiceContainer':
        """注册单例服务"""
        return self._register_service(
            interface, implementation, ServiceLifetime.SINGLETON, factory
        )
    
    def register_transient(self, interface, implementation = None,
                          factory: callable = None) -> 'ServiceContainer':
        """注册瞬态服务"""
        return self._register_service(
            interface, implementation, ServiceLifetime.TRANSIENT, factory
        )
    
    def register_scoped(self, interface, implementation = None,
                       factory: callable = None) -> 'ServiceContainer':
        """注册作用域服务"""
        return self._register_service(
            interface, implementation, ServiceLifetime.SCOPED, factory
        )
    
    def register_instance(self, interface, instance) -> 'ServiceContainer':
        """注册服务实例"""
        with self._service_lock:
            service_name = self._get_service_name(interface)

            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=type(instance),
                lifetime=ServiceLifetime.SINGLETON,
                instance=instance
            )
            
            self._services[service_name] = descriptor
            self._instances[service_name] = instance
            
            self.service_registered.emit(service_name, instance)
            
            logger.info(f"已注册服务实例: {service_name}")
            
        return self

    def register(self, interface, implementation = None) -> 'ServiceContainer':
        """简单注册服务方法（兼容性）"""
        return self.register_singleton(interface, implementation)

    def _register_service(self, interface, implementation = None,
                         lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                         factory: callable = None) -> 'ServiceContainer':
        """注册服务"""
        with self._service_lock:
            if self._built:
                raise RuntimeError("容器已构建，无法注册新服务")
            
            service_name = self._get_service_name(interface)
            
            # 如果没有指定实现，使用接口本身
            if implementation is None and factory is None:
                implementation = interface
            
            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                lifetime=lifetime,
                factory=factory
            )
            
            self._services[service_name] = descriptor
            
            logger.info(f"已注册服务: {service_name} ({lifetime.value})")
            
        return self
    
    def get(self, interface):
        """获取服务实例"""
        with self._service_lock:
            service_name = self._get_service_name(interface)
            
            if service_name not in self._services:
                raise ValueError(f"服务未注册: {service_name}")
            
            descriptor = self._services[service_name]
            
            # 单例模式：返回已存在的实例
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_name in self._instances:
                    return self._instances[service_name]
                
                # 创建新实例
                instance = self._create_instance(descriptor)
                self._instances[service_name] = instance
                
                self.service_resolved.emit(service_name, instance)
                return instance
            
            # 瞬态模式：每次创建新实例
            elif descriptor.lifetime == ServiceLifetime.TRANSIENT:
                instance = self._create_instance(descriptor)
                self.service_resolved.emit(service_name, instance)
                return instance
            
            # 作用域模式：在当前作用域内单例
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                # 简化实现，当作单例处理
                if service_name in self._instances:
                    return self._instances[service_name]
                
                instance = self._create_instance(descriptor)
                self._instances[service_name] = instance
                
                self.service_resolved.emit(service_name, instance)
                return instance
    
    def try_get(self, interface):
        """尝试获取服务实例"""
        try:
            return self.get(interface)
        except ValueError:
            return None
    
    def has_service(self, interface) -> bool:
        """检查是否注册了服务"""
        service_name = self._get_service_name(interface)
        return service_name in self._services
    
    def build(self) -> 'ServiceContainer':
        """构建容器"""
        with self._service_lock:
            if self._built:
                return self
            
            if self._building:
                raise RuntimeError("容器正在构建中")
            
            self._building = True
            
            try:
                # 验证服务依赖
                self._validate_dependencies()
                
                # 预创建单例服务
                self._create_singletons()
                
                self._built = True
                
                self.container_built.emit()
                
                logger.info(f"服务容器构建完成，共注册 {len(self._services)} 个服务")
                
            except Exception as e:
                logger.error(f"服务容器构建失败: {e}")
                raise
            finally:
                self._building = False
        
        return self
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例"""
        try:
            # 使用工厂方法
            if descriptor.factory:
                return descriptor.factory(self)
            
            # 使用构造函数
            if descriptor.implementation:
                # 简单的依赖注入（可以扩展）
                try:
                    # 尝试使用无参构造函数
                    return descriptor.implementation()
                except TypeError:
                    # 尝试注入容器
                    try:
                        return descriptor.implementation(self)
                    except TypeError:
                        # 回退到默认构造
                        return descriptor.implementation()
            
            raise ValueError(f"无法创建服务实例: {descriptor.interface}")
            
        except Exception as e:
            logger.error(f"创建服务实例失败: {descriptor.interface} - {e}")
            raise
    
    def _validate_dependencies(self):
        """验证服务依赖"""
        # 简化实现，检查循环依赖
        for service_name, descriptor in self._services.items():
            if descriptor.dependencies:
                for dep in descriptor.dependencies:
                    dep_name = self._get_service_name(dep)
                    if dep_name not in self._services:
                        logger.warning(f"服务 {service_name} 的依赖 {dep_name} 未注册")
    
    def _create_singletons(self):
        """预创建单例服务"""
        for service_name, descriptor in self._services.items():
            if descriptor.lifetime == ServiceLifetime.SINGLETON and service_name not in self._instances:
                try:
                    instance = self._create_instance(descriptor)
                    self._instances[service_name] = instance
                    
                    self.service_resolved.emit(service_name, instance)
                    
                    logger.debug(f"预创建单例服务: {service_name}")
                except Exception as e:
                    logger.error(f"预创建单例服务失败: {service_name} - {e}")
    
    def _get_service_name(self, interface) -> str:
        """获取服务名称"""
        if hasattr(interface, '__name__'):
            return interface.__name__
        return str(interface)
    
    def get_registered_services(self) -> Dict[str, ServiceDescriptor]:
        """获取已注册的服务"""
        return self._services.copy()
    
    def get_service_instances(self) -> Dict[str, Any]:
        """获取服务实例"""
        return self._instances.copy()
    
    def clear_scoped_services(self):
        """清理作用域服务"""
        with self._service_lock:
            scoped_services = [
                name for name, descriptor in self._services.items()
                if descriptor.lifetime == ServiceLifetime.SCOPED
            ]
            
            for service_name in scoped_services:
                if service_name in self._instances:
                    del self._instances[service_name]
            
            logger.debug(f"清理了 {len(scoped_services)} 个作用域服务")
    
    def cleanup(self):
        """清理容器"""
        with self._service_lock:
            logger.info("清理服务容器")
            
            # 清理服务实例
            for service_name, instance in self._instances.items():
                try:
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                except Exception as e:
                    logger.error(f"清理服务 {service_name} 失败: {e}")
            
            self._instances.clear()
            self._services.clear()
            self._built = False
            
            logger.info("服务容器清理完成")
    
    @classmethod
    def reset(cls):
        """重置容器（用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.cleanup()
                cls._instance = None


# 便利函数
def get_container() -> ServiceContainer:
    """获取服务容器实例"""
    return ServiceContainer()


def configure_services(configure_func: callable) -> ServiceContainer:
    """配置服务"""
    container = get_container()
    configure_func(container)
    return container.build()


# 装饰器
def service(interface: Type = None, lifetime: ServiceLifetime = ServiceLifetime.SINGLETON):
    """服务装饰器"""
    def decorator(cls):
        container = get_container()
        service_interface = interface if interface else cls
        
        if lifetime == ServiceLifetime.SINGLETON:
            container.register_singleton(service_interface, cls)
        elif lifetime == ServiceLifetime.TRANSIENT:
            container.register_transient(service_interface, cls)
        elif lifetime == ServiceLifetime.SCOPED:
            container.register_scoped(service_interface, cls)
        
        return cls
    
    return decorator


# 示例用法
if __name__ == "__main__":
    # 创建服务容器
    container = ServiceContainer()
    
    # 注册服务
    class ILogger:
        def log(self, message: str):
            pass
    
    class ConsoleLogger(ILogger):
        def log(self, message: str):
            print(f"[LOG] {message}")
    
    container.register_singleton(ILogger, ConsoleLogger)
    
    # 构建容器
    container.build()
    
    # 获取服务
    logger_service = container.get(ILogger)
    logger_service.log("Hello, World!")
    
    # 清理
    container.cleanup()
