#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一AI服务实现
重构自EnhancedAIManager，实现IAIService接口
使用QThreadPool替代直接asyncio调用，解决并发冲突
"""

import time
import logging
import asyncio
import uuid
import re
from typing import Dict, List, Optional, Any, Union, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThreadPool, QRunnable, pyqtSlot

from .interfaces import (
    IAIService, IStreamingAIService, IAIEventHandler, IAIModelCache,
    AIRequest, AIResponse, StreamingChunk, AIModelHealth, AIUsageStats,
    AIServiceConfig, AITaskType, AIPriority, AIRequestStatus, AIRequestStatus,
    ITokenManager, ITokenOptimizer, TokenUsage
)
from .workers import AIWorkerPool
from .models.base_model import BaseAIModel, AIModelConfig
from .models.qianwen_model import QianwenModel
from .models.wenxin_model import WenxinModel
from .models.zhipu_model import ZhipuModel
from .models.xunfei_model import XunfeiModel
from .models.hunyuan_model import HunyuanModel
from .models.deepseek_model import DeepSeekModel

# 可选导入
try:
    from .optimized_model_manager import OptimizedModelManager
except ImportError:
    OptimizedModelManager = None

try:
    from .optimized_cost_manager import OptimizedCostManager
except ImportError:
    OptimizedCostManager = None

try:
    from .intelligent_load_balancer import IntelligentLoadBalancer
except ImportError:
    IntelligentLoadBalancer = None

from app.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class AIService(QObject, IStreamingAIService, IAIEventHandler):
    """统一AI服务"""

    # 信号定义
    request_started = pyqtSignal(str)  # request_id
    request_progress = pyqtSignal(str, float)  # request_id, progress
    request_completed = pyqtSignal(str, object)  # request_id, AIResponse
    request_failed = pyqtSignal(str, str)  # request_id, error_message
    request_cancelled = pyqtSignal(str)  # request_id

    # 流式响应信号
    streaming_started = pyqtSignal(str)        # request_id
    streaming_chunk = pyqtSignal(str, str)    # request_id, chunk
    streaming_completed = pyqtSignal(str, object)  # request_id, result

    # 健康和统计信号
    health_status_updated = pyqtSignal(dict)  # 健康状态更新
    usage_stats_updated = pyqtSignal(object)  # 使用统计更新
    cost_alert = pyqtSignal(str, float, float)  # 成本告警: message, current, limit
    budget_exceeded = pyqtSignal(float, float)  # 预算超限: current, limit
    
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        
        self.settings_manager = settings_manager
        
        # 模型类映射
        self.model_classes = {
            "qianwen": QianwenModel,
            "wenxin": WenxinModel,
            "zhipu": ZhipuModel,
            "xunfei": XunfeiModel,
            "hunyuan": HunyuanModel,
            "deepseek": DeepSeekModel
        }
        
        # 核心组件
        self.model_manager = None
        self.cost_manager = None
        self.load_balancer = None
        self.token_manager = None
        self.token_optimizer = None
        
        # 工作线程池
        self.worker_pool = AIWorkerPool(max_workers=8)
        
        # 请求管理
        self.active_requests: Dict[str, AIRequest] = {}
        self.request_results: Dict[str, AIResponse] = {}
        self.request_history = deque(maxlen=1000)
        
        # 统计信息
        self.usage_stats = AIUsageStats()
        self.model_health: Dict[str, AIModelHealth] = {}
        
        # 配置
        self.max_concurrent_requests = 20
        self.default_timeout = 30.0
        self.budget_limit = 1000.0
        self.cost_alert_threshold = 0.8
        
        # 定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(60000)  # 每分钟更新统计
        
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._health_check)
        self.health_timer.start(300000)  # 每5分钟健康检查
        
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_data)
        self.cleanup_timer.start(3600000)  # 每小时清理数据
        
        # 连接工作线程池信号
        self._connect_worker_signals()
        
        # 异步初始化
        QTimer.singleShot(100, self._initialize_async)
        
        logger.info("统一AI服务初始化完成")
    
    def _connect_worker_signals(self):
        """连接工作线程池信号"""
        self.worker_pool.worker_started.connect(self._on_request_started)
        self.worker_pool.worker_finished.connect(self._on_request_finished)
        self.worker_pool.worker_error.connect(self._on_request_error)
        self.worker_pool.pool_status_changed.connect(self._on_pool_status_changed)
    
    def _initialize_async(self):
        """异步初始化组件"""
        try:
            # 初始化模型管理器
            if OptimizedModelManager:
                self.model_manager = OptimizedModelManager(self.model_classes)
            
            # 初始化成本管理器
            if OptimizedCostManager:
                self.cost_manager = OptimizedCostManager()
            
            # 初始化负载均衡器
            if IntelligentLoadBalancer and self.model_manager and self.cost_manager:
                self.load_balancer = IntelligentLoadBalancer(
                    self.model_manager, self.cost_manager
                )

            # 初始化令牌管理器
            from .unified_token_manager import UnifiedTokenManager
            self.token_manager = UnifiedTokenManager(self.cost_manager)

            # 初始化令牌优化器
            from .token_optimizer import TokenOptimizer
            self.token_optimizer = TokenOptimizer(self.token_manager)

            # 创建默认令牌预算
            self.token_manager.create_budget("默认预算", 1000000, "monthly")

            # 加载AI配置
            self._load_ai_config()
            
            # 连接组件信号
            self._connect_component_signals()
            
            logger.info("AI服务组件初始化完成")
            
        except Exception as e:
            logger.error(f"AI服务初始化失败: {e}")
    
    def _load_ai_config(self):
        """加载AI配置"""
        try:
            ai_config = self.settings_manager.get_setting("ai_models", {})
            
            # 创建模型配置
            model_configs = {}
            for provider, config in ai_config.items():
                if provider in self.model_classes and config.get("enabled", False):
                    api_key = self.settings_manager.get_api_key(provider)
                    
                    model_config = AIModelConfig(
                        name=config.get("model", provider),
                        api_key=api_key,
                        api_url=config.get("api_url", ""),
                        max_tokens=config.get("max_tokens", 4096),
                        temperature=config.get("temperature", 0.7),
                        top_p=config.get("top_p", 0.9),
                        frequency_penalty=config.get("frequency_penalty", 0.0),
                        presence_penalty=config.get("presence_penalty", 0.0),
                        enabled=config.get("enabled", False),
                        use_proxy=config.get("use_proxy", False),
                        proxy_url=config.get("proxy_url", ""),
                        custom_headers=config.get("custom_headers", {})
                    )
                    
                    model_configs[provider] = model_config
            
            # 异步初始化模型
            if model_configs and self.model_manager:
                QTimer.singleShot(500, lambda: self._initialize_models_async(model_configs))
            
            # 设置预算
            budget_amount = self.settings_manager.get_setting("ai_budget.monthly_limit", 1000.0)
            self.set_budget_limit(budget_amount)
            
        except Exception as e:
            logger.error(f"加载AI配置失败: {e}")
    
    def _connect_component_signals(self):
        """连接组件信号"""
        if self.model_manager:
            self.model_manager.model_health_updated.connect(self._on_model_health_updated)
            self.model_manager.model_performance_updated.connect(self._on_model_performance_updated)
        
        if self.cost_manager:
            self.cost_manager.cost_updated.connect(self._on_cost_updated)
            self.cost_manager.budget_alert.connect(self._on_budget_alert)
    
    # IAIService接口实现
    async def process_request(self, request: AIRequest) -> AIResponse:
        """处理AI请求（异步接口）"""
        try:
            # 验证请求
            if not self._validate_request(request):
                return AIResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message="请求验证失败"
                )

            # 优化请求
            optimized_request = self.token_optimizer.optimize_request_tokens(request)

            # 检查令牌可用性
            estimated_tokens = self._estimate_request_tokens(optimized_request)
            if not self.token_manager.check_token_availability(estimated_tokens):
                return AIResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message="令牌预算不足"
                )

            # 预留令牌
            try:
                reservation = self.token_manager.reserve_tokens(
                    estimated_tokens,
                    f"AI请求: {request.task_type.value}",
                    request.provider
                )
            except Exception as e:
                return AIResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message=f"令牌预留失败: {e}"
                )

            # 检查成本预算
            if not self._check_budget(optimized_request):
                self.token_manager.release_reservation(reservation.reservation_id)
                return AIResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message="成本预算不足"
                )

            # 更新请求状态
            request.status = AIRequestStatus.PROCESSING
            self.active_requests[request.request_id] = request
            self.on_request_started(request)

            # 执行AI请求
            result = await self._execute_ai_request(optimized_request)

            # 处理令牌消费
            if result.success and result.usage:
                token_usage = TokenUsage(
                    prompt_tokens=result.usage.get('prompt_tokens', 0),
                    completion_tokens=result.usage.get('completion_tokens', 0),
                    total_tokens=result.usage.get('total_tokens', 0),
                    cached_tokens=getattr(result, 'cached_tokens', 0)
                )

                # 消费令牌
                self.token_manager.consume_tokens(
                    result.provider or request.provider,
                    token_usage,
                    result.cost or 0.0
                )

                # 释放预留的令牌（实际消费可能不同）
                self.token_manager.release_reservation(reservation.reservation_id)

                # 更新响应中的优化信息
                if hasattr(optimized_request, 'metadata'):
                    result.metadata = {
                        **(result.metadata or {}),
                        'token_optimization': optimized_request.metadata,
                        'token_usage': asdict(token_usage)
                    }
            else:
                # 请求失败，释放预留令牌
                self.token_manager.release_reservation(reservation.reservation_id)

            # 更新统计
            self._update_request_stats(result)
            self.on_request_completed(optimized_request, result)

            return result

        except Exception as e:
            logger.error(f"处理AI请求失败: {e}")
            # 释放预留令牌
            if 'reservation' in locals():
                self.token_manager.release_reservation(reservation.reservation_id)

            error_response = AIResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e)
            )
            self.on_request_failed(request, str(e))
            return error_response

        finally:
            # 清理活动请求
            self.active_requests.pop(request.request_id, None)

    def submit_request(self, request: AIRequest) -> str:
        """提交AI请求（非阻塞）"""
        try:
            # 验证请求
            if not self._validate_request(request):
                self.request_failed.emit(request.request_id, "请求验证失败")
                return request.request_id

            # 检查预算
            if not self._check_budget(request):
                self.request_failed.emit(request.request_id, "预算不足")
                return request.request_id

            # 添加到活动请求
            self.active_requests[request.request_id] = request

            # 提交到工作线程池
            success = self.worker_pool.submit_task(
                request, self.model_manager, self.cost_manager
            )

            if not success:
                self.active_requests.pop(request.request_id, None)
                self.request_failed.emit(request.request_id, "无法提交请求到工作线程池")

            return request.request_id

        except Exception as e:
            logger.error(f"提交AI请求失败: {e}")
            self.request_failed.emit(request.request_id, str(e))
            return request.request_id

    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        try:
            # 从活动请求中移除
            if request_id in self.active_requests:
                del self.active_requests[request_id]

            # 取消工作线程
            success = self.worker_pool.cancel_task(request_id)

            if success:
                self.request_cancelled.emit(request_id)
                logger.info(f"已取消请求: {request_id}")

            return success

        except Exception as e:
            logger.error(f"取消请求失败: {e}")
            return False

    def get_request_status(self, request_id: str) -> Optional[AIRequestStatus]:
        """获取请求状态"""
        if request_id in self.active_requests:
            return AIRequestStatus.PROCESSING
        elif request_id in self.request_results:
            response = self.request_results[request_id]
            return AIRequestStatus.COMPLETED if response.success else AIRequestStatus.FAILED
        return None

    def get_available_providers(self) -> List[str]:
        """获取可用提供商列表"""
        if self.model_manager:
            return [
                provider for provider, metrics in self.model_manager.model_metrics.items()
                if metrics.health_status.value in ["healthy", "degraded"]
            ]
        return []

    def get_provider_models(self, provider: str) -> List[Any]:
        """获取提供商模型信息"""
        if self.model_manager and provider in self.model_manager.model_metrics:
            return [{
                "provider": provider,
                "model_name": provider,
                "display_name": provider.title(),
                "capabilities": ["text_generation"],
                "max_tokens": 4096,
                "cost_per_1k_tokens": 0.001,
                "supports_streaming": True
            }]
        return []

    def get_health_status(self) -> Dict[str, AIModelHealth]:
        """获取健康状态"""
        return self.model_health.copy()

    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """更新设置"""
        try:
            for key, value in settings.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            logger.error(f"更新设置失败: {e}")
            return False

    def get_cost_estimate(self, request: AIRequest) -> float:
        """获取成本估算"""
        return self._estimate_request_cost(request)

    def set_budget_limit(self, limit: float) -> None:
        """设置预算限制"""
        self.budget_limit = limit
        if self.cost_manager:
            self.cost_manager.create_budget("主要预算", limit, 30)

    # IStreamingAIService接口实现
    async def stream_request(self, request: AIRequest) -> Any:
        """流式处理AI请求"""
        # 简化实现：返回普通响应
        return await self.process_request(request)

    def submit_streaming_request(self, request: AIRequest) -> str:
        """提交流式AI请求"""
        # 发送开始信号
        self.streaming_started.emit(request.request_id)

        # 使用普通请求处理（简化实现）
        request_id = self.submit_request(request)

        # 模拟流式响应
        if request_id in self.active_requests:
            # 在实际实现中，这里应该连接到真正的流式处理
            QTimer.singleShot(100, lambda: self._simulate_streaming_response(request))

        return request_id

    def _simulate_streaming_response(self, request: AIRequest):
        """模拟流式响应（仅用于演示）"""
        # 这里简化了流式响应的模拟
        # 在实际实现中，应该连接到真正的流式API
        pass

    # IAIEventHandler接口实现
    def on_request_started(self, request: AIRequest) -> None:
        """请求开始事件"""
        self.request_started.emit(request.request_id)

    def on_request_completed(self, request: AIRequest, response: AIResponse) -> None:
        """请求完成事件"""
        self.request_completed.emit(request.request_id, response)

    def on_request_failed(self, request: AIRequest, error: str) -> None:
        """请求失败事件"""
        self.request_failed.emit(request.request_id, error)

    def on_streaming_chunk(self, chunk: StreamingChunk) -> None:
        """流式数据块事件"""
        self.streaming_chunk.emit(chunk.request_id, chunk.content)

    def on_provider_health_changed(self, provider: str, health: AIModelHealth) -> None:
        """提供商健康状态变化事件"""
        self.model_health[provider] = health
        self.health_status_updated.emit({provider: health})

    # 内部方法
    async def _execute_ai_request(self, request: AIRequest) -> AIResponse:
        """执行AI请求"""
        start_time = time.time()

        try:
            # 这里简化了实际的AI处理逻辑
            # 在实际实现中，应该调用相应的model_manager

            # 模拟处理延迟
            await asyncio.sleep(0.1)

            # 模拟响应
            response = AIResponse(
                request_id=request.request_id,
                success=True,
                content=f"处理完成: {request.content[:100]}...",
                processing_time=time.time() - start_time,
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                provider=request.provider or "default",
                cost=0.001
            )

            return response

        except Exception as e:
            return AIResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    # 便利方法
    def generate_text_sync(self, prompt: str, provider: str = None, **kwargs) -> str:
        """生成文本（已弃用，请使用generate_text_async）"""
        logger.warning("generate_text_sync已弃用，请使用generate_text_async")
        request = AIRequest(
            task_type=AITaskType.TEXT_GENERATION,
            content=prompt,
            provider=provider,
            parameters=kwargs
        )
        
        request_id = self.submit_request(request)
        return f"请求已提交: {request_id}"
    
    def generate_text_async(self, prompt: str, provider: str = None, 
                           callback: callable = None, **kwargs) -> str:
        """生成文本（异步接口）"""
        request = AIRequest(
            task_type=AITaskType.TEXT_GENERATION,
            content=prompt,
            provider=provider,
            callback=callback,
            parameters=kwargs
        )
        
        return self.submit_request(request)
    
    def generate_commentary(self, video_info: Dict[str, Any], style: str = "专业解说", 
                          provider: str = None, **kwargs) -> str:
        """生成视频解说"""
        request = AIRequest(
            task_type=AITaskType.COMMENTARY_GENERATION,
            content=f"为视频生成{style}的解说",
            context={"video_info": video_info, "style": style},
            provider=provider,
            parameters=kwargs
        )
        
        return self.submit_request(request)
    
    def analyze_content(self, content: str, analysis_type: str = "general", 
                       provider: str = None) -> str:
        """分析内容"""
        request = AIRequest(
            task_type=AITaskType.CONTENT_ANALYSIS,
            content=content,
            provider=provider,
            parameters={"analysis_type": analysis_type}
        )
        
        return self.submit_request(request)
    
    # 内部方法
    def _validate_request(self, request: AIRequest) -> bool:
        """验证请求"""
        if not request.content and request.task_type != AITaskType.TEXT_GENERATION:
            return False
        
        if not self.model_manager:
            return False
        
        return True
    
    def _check_budget(self, request: AIRequest) -> bool:
        """检查预算"""
        if not self.cost_manager:
            return True
        
        # 估算成本
        estimated_cost = self._estimate_request_cost(request)
        
        # 检查预算限制
        return self.cost_manager.check_budget_limit(estimated_cost)
    
    def _estimate_request_cost(self, request: AIRequest) -> float:
        """估算请求成本"""
        # 简单的成本估算逻辑
        base_cost = 0.01  # 基础成本
        content_length = len(request.content)
        estimated_tokens = content_length // 4  # 粗略估算
        
        return base_cost + (estimated_tokens * 0.001)
    
    def _on_request_started(self, request_id: str):
        """请求开始处理"""
        self.request_started.emit(request_id)
        
        # 更新请求状态
        if request_id in self.active_requests:
            self.active_requests[request_id].status = AIRequestStatus.PROCESSING
    
    def _on_request_finished(self, request_id: str, result: AIResponse):
        """请求完成处理"""
        try:
            # 移除活动请求
            request = self.active_requests.pop(request_id, None)
            
            # 保存结果
            self.request_results[request_id] = result
            
            # 更新统计
            self._update_request_stats(result)
            
            # 添加到历史记录
            if request:
                self.request_history.append({
                    "request": request,
                    "result": result,
                    "completed_at": time.time()
                })
            
            # 执行回调
            if request and request.callback:
                try:
                    request.callback(result)
                except Exception as e:
                    logger.error(f"执行请求回调失败: {e}")
            
            # 发射信号
            self.request_completed.emit(request_id, result)
            
        except Exception as e:
            logger.error(f"处理请求完成事件失败: {e}")
    
    def _on_request_error(self, request_id: str, error_message: str):
        """请求错误处理"""
        try:
            # 移除活动请求
            request = self.active_requests.pop(request_id, None)
            
            # 创建错误结果
            result = AIResponse(
                request_id=request_id,
                success=False,
                error_message=error_message
            )
            
            # 保存结果
            self.request_results[request_id] = result
            
            # 更新统计
            self._update_request_stats(result)
            
            # 检查重试
            if request and request.retry_count < request.max_retries:
                request.retry_count += 1
                request.created_at = time.time()
                
                # 重新提交
                QTimer.singleShot(1000 * (2 ** request.retry_count), 
                                lambda: self.submit_request(request))
                
                logger.info(f"请求 {request_id} 重试第 {request.retry_count} 次")
            else:
                # 发射失败信号
                self.request_failed.emit(request_id, error_message)
            
        except Exception as e:
            logger.error(f"处理请求错误事件失败: {e}")
    
    def _on_pool_status_changed(self, active_workers: int, max_workers: int):
        """工作线程池状态变化"""
        # 可以在这里添加负载监控逻辑
        pass
    
    def _on_model_health_updated(self, health_data: dict):
        """模型健康状态更新"""
        # 更新本地健康状态
        for provider, health_info in health_data.items():
            self.model_health[provider] = AIModelHealth(
                provider=provider,
                is_healthy=health_info.get("is_healthy", False),
                response_time=health_info.get("response_time", 0.0),
                error_rate=health_info.get("error_rate", 0.0),
                success_count=health_info.get("success_count", 0),
                total_requests=health_info.get("total_requests", 0),
                consecutive_failures=health_info.get("consecutive_failures", 0),
                health_score=health_info.get("health_score", 0.0),
                last_used=health_info.get("last_used", 0.0),
                capabilities=health_info.get("capabilities", [])
            )
        
        # 发射更新信号
        self.health_status_updated.emit(health_data)
    
    def _on_model_performance_updated(self, performance_data: dict):
        """模型性能更新"""
        # 可以在这里添加性能监控逻辑
        pass
    
    def _on_cost_updated(self, cost_summary: dict):
        """成本更新"""
        current_cost = cost_summary.get("total_cost", 0.0)
        
        # 检查成本告警
        if current_cost > self.budget_limit * self.cost_alert_threshold:
            self.cost_alert.emit(
                f"成本已达到预算的{self.cost_alert_threshold*100:.0f}%",
                current_cost,
                self.budget_limit
            )
        
        # 检查预算超限
        if current_cost > self.budget_limit:
            self.budget_exceeded.emit(current_cost, self.budget_limit)
    
    def _on_budget_alert(self, alert_info: dict):
        """预算告警"""
        message = alert_info.get("message", "预算告警")
        current = alert_info.get("current_cost", 0.0)
        limit = alert_info.get("budget_limit", 0.0)
        
        self.cost_alert.emit(message, current, limit)
    
    def _update_request_stats(self, result: AIResponse):
        """更新请求统计"""
        self.usage_stats.total_requests += 1
        
        if result.success:
            self.usage_stats.successful_requests += 1
            
            # 更新token和成本统计
            if result.usage:
                tokens = result.usage.get("total_tokens", 0)
                self.usage_stats.total_tokens += tokens
                
                if result.provider:
                    self.usage_stats.tokens_by_provider[result.provider] = (
                        self.usage_stats.tokens_by_provider.get(result.provider, 0) + tokens
                    )
                    
                    self.usage_stats.cost_by_provider[result.provider] = (
                        self.usage_stats.cost_by_provider.get(result.provider, 0.0) + result.cost
                    )
            
            self.usage_stats.total_cost += result.cost
        else:
            self.usage_stats.failed_requests += 1
        
        if result.provider:
            self.usage_stats.requests_by_provider[result.provider] = (
                self.usage_stats.requests_by_provider.get(result.provider, 0) + 1
            )
        
        # 更新平均响应时间
        if self.usage_stats.total_requests > 0:
            total_time = (
                self.usage_stats.average_response_time * (self.usage_stats.total_requests - 1) + 
                result.processing_time
            )
            self.usage_stats.average_response_time = total_time / self.usage_stats.total_requests
    
    def _update_stats(self):
        """更新统计信息"""
        # 发射统计更新信号
        self.usage_stats_updated.emit(self.usage_stats)
    
    def _health_check(self):
        """健康检查"""
        if self.model_manager:
            # 触发模型管理器的健康检查
            QTimer.singleShot(100, self.model_manager._perform_health_check)
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            current_time = time.time()
            
            # 清理旧的请求结果（保留1小时）
            expired_results = [
                request_id for request_id, result in self.request_results.items()
                if current_time - result.created_at > 3600
            ]
            
            for request_id in expired_results:
                del self.request_results[request_id]
            
            if expired_results:
                logger.info(f"清理了 {len(expired_results)} 个过期请求结果")
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
    
    def cleanup(self) -> None:
        """清理资源"""
        logger.info("清理统一AI服务资源")
        
        try:
            # 停止定时器
            self.stats_timer.stop()
            self.health_timer.stop()
            self.cleanup_timer.stop()
            
            # 清理工作线程池
            self.worker_pool.cleanup()
            
            # 清理组件
            if self.model_manager:
                # 使用Qt的信号槽机制或QThreadPool来处理异步清理
                try:
                    # 如果model_manager有同步的cleanup方法，使用它
                    if hasattr(self.model_manager, 'cleanup_sync'):
                        self.model_manager.cleanup_sync()
                    else:
                        # 否则创建一个工作任务来执行异步清理
                        from app.ai.workers import AIWorker
                        cleanup_worker = AIWorker(self.model_manager.cleanup, None)
                        cleanup_worker.run()  # 同步执行
                except Exception as e:
                    logger.warning(f"模型管理器清理失败: {e}")
            
            # 清理数据
            self.active_requests.clear()
            self.request_results.clear()
            self.request_history.clear()
            self.model_health.clear()
            
            logger.info("统一AI服务资源清理完成")
            
        except Exception as e:
            logger.error(f"清理统一AI服务资源失败: {e}")
    
    def _initialize_models_async(self, model_configs: Dict[str, AIModelConfig]):
        """异步初始化模型"""
        try:
            if self.model_manager:
                # 使用QTimer延迟执行，确保主循环运行
                def init_models():
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.model_manager.initialize_models(model_configs))
                        loop.close()
                        logger.info("模型初始化完成")
                    except Exception as e:
                        logger.error(f"模型初始化失败: {e}")
                
                # 在后台线程中执行
                import threading
                init_thread = threading.Thread(target=init_models, daemon=True)
                init_thread.start()
                
        except Exception as e:
            logger.error(f"启动模型初始化失败: {e}")


    def _estimate_request_tokens(self, request: AIRequest) -> int:
        """估算请求需要的令牌数量"""
        # 基础令牌估算
        content_tokens = self._estimate_token_count(request.content)

        # 上下文令牌
        context_tokens = 0
        if request.context:
            context_text = json.dumps(request.context, ensure_ascii=False)
            context_tokens = self._estimate_token_count(context_text)

        # 参数令牌
        params_tokens = 0
        if request.parameters:
            params_text = json.dumps(request.parameters, ensure_ascii=False)
            params_tokens = self._estimate_token_count(params_text)

        # 任务类型基础开销
        task_overhead = {
            AITaskType.TEXT_GENERATION: 10,
            AITaskType.CONTENT_ANALYSIS: 20,
            AITaskType.COMMENTARY_GENERATION: 30,
            AITaskType.MONOLOGUE_GENERATION: 25,
            AITaskType.SCENE_ANALYSIS: 40,
            AITaskType.SUBTITLE_GENERATION: 15,
            AITaskType.VIDEO_EDITING_SUGGESTION: 35,
            AITaskType.CONTENT_CLASSIFICATION: 25
        }

        overhead = task_overhead.get(request.task_type, 15)

        total_tokens = content_tokens + context_tokens + params_tokens + overhead
        return max(1, total_tokens)

    def _estimate_token_count(self, text: str) -> int:
        """估算文本的令牌数量"""
        if not text:
            return 0

        # 简单估算：中文字符 + 英文单词 + 标点符号
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        punctuation = len(re.findall(r'[^\w\s]', text))

        # 估算公式
        estimated_tokens = int(chinese_chars * 0.6 + english_words * 0.75 + punctuation * 0.25)
        return max(1, estimated_tokens)

    def get_token_management_stats(self) -> Dict[str, Any]:
        """获取令牌管理统计信息"""
        if not self.token_manager:
            return {'error': '令牌管理器未初始化'}

        stats = self.token_manager.get_token_budget_status()
        if self.token_optimizer:
            stats['optimization'] = self.token_optimizer.get_optimization_stats()

        return stats

    def get_token_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取令牌优化建议"""
        if not self.token_optimizer:
            return []

        return self.token_optimizer.get_token_optimization_suggestions()

    def set_optimization_strategy(self, strategy: str) -> bool:
        """设置优化策略"""
        if not self.token_optimizer:
            return False

        try:
            from .token_optimizer import OptimizationStrategy
            strategy_enum = OptimizationStrategy(strategy)
            self.token_optimizer.set_optimization_strategy(strategy_enum)
            return True
        except ValueError:
            logger.error(f"无效的优化策略: {strategy}")
            return False


# 工厂函数
def create_ai_service(settings_manager: SettingsManager) -> AIService:
    """创建统一AI服务"""
    return AIService(settings_manager)
