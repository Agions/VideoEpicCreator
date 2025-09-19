#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
应用服务配置
统一配置所有应用服务的依赖注入和生命周期管理
"""

import logging
from typing import Optional

from .service_container import ServiceContainer, ServiceLifetime, configure_services
from .settings_manager import SettingsManager
from ..ai.ai_service import AIService
from ..ai.interfaces import (
    AIServiceConfig, IAICostManager, IAILoadBalancer, ITokenManager, ITokenOptimizer
)
from ..ai.cost_manager import ChineseLLMCostManager
from ..ai.load_balancer import ChineseLLMLoadBalancer, LoadBalancingStrategy
from ..ai.workers import AIWorkerPool
from ..ai.unified_token_manager import UnifiedTokenManager
from ..ai.token_optimizer import TokenOptimizer
from ..ui.unified_theme_system import UnifiedThemeManager
from ..project_manager import ProjectManager
from ..video_processor import VideoProcessor
from .intelligent_video_processing_engine import IntelligentVideoProcessingEngine
from .unified_media_manager import UnifiedMediaManager

logger = logging.getLogger(__name__)


class ServiceConfig:
    """服务配置类"""

    @staticmethod
    def configure_aiservices(container: ServiceContainer) -> None:
        """配置AI相关服务"""
        logger.info("配置AI服务...")

        # 配置AI服务设置
        ai_config = AIServiceConfig(
            max_concurrent_requests=5,
            request_timeout=300.0,
            retry_attempts=3,
            retry_delay=1.0,
            enable_streaming=True,
            cost_budget=1000.0,
            health_check_interval=60.0,
            enable_metrics=True,
            log_level="INFO",
            cache_enabled=True,
            cache_ttl=3600.0
        )

        # 注册AI配置
        container.register_instance(AIServiceConfig, ai_config)

        # 注册成本管理器（单例）
        container.register_singleton(
            IAICostManager,
            ChineseLLMCostManager,
            factory=lambda c: ChineseLLMCostManager(c.get(SettingsManager))
        )

        # 注册负载均衡器（单例）
        container.register_singleton(
            IAILoadBalancer,
            ChineseLLMLoadBalancer,
            factory=lambda c: ChineseLLMLoadBalancer(
                LoadBalancingStrategy.ROUND_ROBIN,
                c.get(SettingsManager),
                c.get(IAICostManager)
            )
        )

        # 注册AI工作线程池（单例）
        container.register_singleton(
            AIWorkerPool,
            factory=lambda c: AIWorkerPool(max_workers=4)
        )

        # 注册统一令牌管理器（单例）
        container.register_singleton(
            ITokenManager,
            UnifiedTokenManager,
            factory=lambda c: UnifiedTokenManager(c.get(IAICostManager))
        )

        # 注册令牌优化器（单例）
        container.register_singleton(
            ITokenOptimizer,
            TokenOptimizer,
            factory=lambda c: TokenOptimizer(c.get(ITokenManager))
        )

        # 注册主AI服务（单例）
        container.register_singleton(
            AIService,
            factory=lambda c: AIService(
                config=c.get(AIServiceConfig),
                model_manager=c.get(IAILoadBalancer),
                cost_manager=c.get(IAICostManager),
                worker_pool=c.get(AIWorkerPool),
                settings_manager=c.get(SettingsManager)
            )
        )

        logger.info("AI服务配置完成")

    @staticmethod
    def configure_core_services(container: ServiceContainer) -> None:
        """配置核心服务"""
        logger.info("配置核心服务...")

        # 注册设置管理器（单例）
        container.register_singleton(SettingsManager)

        # 注册统一主题管理器（单例）
        container.register_singleton(UnifiedThemeManager)

        # 注册项目管理器（单例）
        container.register_singleton(ProjectManager)

        # 注册视频处理器（单例）
        container.register_singleton(
            VideoProcessor,
            factory=lambda c: VideoProcessor(c.get(SettingsManager))
        )

        # 注册智能视频处理引擎（单例）
        container.register_singleton(
            IntelligentVideoProcessingEngine,
            factory=lambda c: IntelligentVideoProcessingEngine()
        )

        # 注册统一媒体管理器（单例）
        container.register_singleton(
            UnifiedMediaManager,
            factory=lambda c: UnifiedMediaManager()
        )

        logger.info("核心服务配置完成")

    @staticmethod
    def configure_ui_services(container: ServiceContainer) -> None:
        """配置UI相关服务"""
        logger.info("配置UI服务...")

        # UI服务可以在这里注册
        # 例如：状态栏服务、通知服务等

        logger.info("UI服务配置完成")

    @staticmethod
    def configure_all_services(container: Optional[ServiceContainer] = None) -> ServiceContainer:
        """配置所有服务"""
        if container is None:
            container = ServiceContainer()

        logger.info("开始配置所有应用服务...")

        try:
            # 按依赖顺序配置服务
            ServiceConfig.configure_core_services(container)
            ServiceConfig.configure_aiservices(container)
            ServiceConfig.configure_ui_services(container)

            logger.info("所有服务配置完成")
            return container

        except Exception as e:
            logger.error(f"服务配置失败: {e}")
            raise


def create_service_container() -> ServiceContainer:
    """创建并构建服务容器"""
    return ServiceConfig.configure_all_services()


def get_ai_service() -> AIService:
    """获取AI服务实例"""
    container = ServiceContainer()
    if not container.has_service(AIService):
        raise RuntimeError("AI服务未配置，请先调用create_service_container()")
    return container.get(AIService)


def get_settings_manager() -> SettingsManager:
    """获取设置管理器实例"""
    container = ServiceContainer()
    if not container.has_service(SettingsManager):
        raise RuntimeError("设置管理器未配置，请先调用create_service_container()")
    return container.get(SettingsManager)


# 便利函数
def initialize_services() -> ServiceContainer:
    """初始化所有服务"""
    logger.info("初始化应用服务...")

    container = create_service_container()
    container.build()

    logger.info("应用服务初始化完成")
    return container


# 装饰器
def inject_service(service_interface):
    """服务注入装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = ServiceContainer()
            service_instance = container.get(service_interface)
            return func(service_instance, *args, **kwargs)
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 配置服务
    container = initialize_services()

    # 获取服务
    ai_service = get_ai_service()
    settings = get_settings_manager()

    print(f"AI服务: {ai_service}")
    print(f"设置管理器: {settings}")

    # 清理
    container.cleanup()