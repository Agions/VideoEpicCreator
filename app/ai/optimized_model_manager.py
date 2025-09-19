#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化的AI模型管理器
实现智能模型选择、异步初始化、性能监控和故障恢复
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import numpy as np
from collections import defaultdict, deque

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .models.base_model import BaseAIModel, AIModelConfig, AIResponse

logger = logging.getLogger(__name__)


class ModelHealthStatus(Enum):
    """模型健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ModelCapability(Enum):
    """模型能力"""
    TEXT_GENERATION = "text_generation"
    CONTENT_ANALYSIS = "content_analysis"
    COMMENTARY_GENERATION = "commentary_generation"
    MONOLOGUE_GENERATION = "monologue_generation"
    SCENE_ANALYSIS = "scene_analysis"
    SUBTITLE_GENERATION = "subtitle_generation"
    CODE_GENERATION = "code_generation"
    TRANSLATION = "translation"


@dataclass
class ModelMetrics:
    """模型性能指标"""
    provider: str
    model_name: str
    response_time: float = 0.0
    error_rate: float = 0.0
    success_count: int = 0
    total_requests: int = 0
    consecutive_failures: int = 0
    health_score: float = 1.0
    last_used: float = 0.0
    average_tokens_per_second: float = 0.0
    cost_per_1k_tokens: float = 0.0
    capabilities: List[ModelCapability] = field(default_factory=list)
    
    def update_success(self, response_time: float, tokens: int = 0):
        """更新成功指标"""
        self.success_count += 1
        self.total_requests += 1
        self.last_used = time.time()
        self.consecutive_failures = 0
        
        # 指数移动平均更新响应时间
        if self.response_time == 0:
            self.response_time = response_time
        else:
            self.response_time = self.response_time * 0.9 + response_time * 0.1
        
        # 更新健康分数
        self.health_score = min(1.0, self.health_score + 0.05)
        
        # 更新token处理速度
        if tokens > 0 and response_time > 0:
            tokens_per_second = tokens / response_time
            if self.average_tokens_per_second == 0:
                self.average_tokens_per_second = tokens_per_second
            else:
                self.average_tokens_per_second = (
                    self.average_tokens_per_second * 0.9 + tokens_per_second * 0.1
                )
        
        # 更新错误率
        self.error_rate = (self.total_requests - self.success_count) / self.total_requests
    
    def update_failure(self):
        """更新失败指标"""
        self.total_requests += 1
        self.consecutive_failures += 1
        self.health_score = max(0.0, self.health_score - 0.1)
        self.error_rate = (self.total_requests - self.success_count) / self.total_requests
    
    @property
    def health_status(self) -> ModelHealthStatus:
        """获取健康状态"""
        if self.health_score >= 0.8:
            return ModelHealthStatus.HEALTHY
        elif self.health_score >= 0.5:
            return ModelHealthStatus.DEGRADED
        elif self.health_score > 0:
            return ModelHealthStatus.UNHEALTHY
        else:
            return ModelHealthStatus.UNKNOWN


@dataclass
class ModelRequest:
    """模型请求"""
    request_id: str
    provider: str
    prompt: str
    capability: ModelCapability
    parameters: Dict[str, Any]
    priority: int = 1
    timeout: float = 30.0
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3


class OptimizedModelManager(QObject):
    """优化的模型管理器"""
    
    # 信号
    model_health_updated = pyqtSignal(dict)  # 模型健康状态更新
    model_performance_updated = pyqtSignal(dict)  # 模型性能更新
    request_completed = pyqtSignal(str, object)  # 请求完成
    request_failed = pyqtSignal(str, str)  # 请求失败
    
    def __init__(self, model_classes: Dict[str, Type[BaseAIModel]]):
        super().__init__()
        
        self.model_classes = model_classes
        self.models: Dict[str, BaseAIModel] = {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        
        # 请求管理
        self.request_queue = asyncio.Queue()
        self.active_requests: Dict[str, ModelRequest] = {}
        self.request_results: Dict[str, AIResponse] = {}
        
        # 性能监控
        self.performance_history = defaultdict(lambda: deque(maxlen=100))
        self.circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
        
        # 配置
        self.max_concurrent_requests = 20
        self.health_check_interval = 300  # 5分钟
        self.metrics_update_interval = 60  # 1分钟
        
        # 启动后台任务
        self._start_background_tasks()
        
        logger.info("优化的模型管理器初始化完成")
    
    async def initialize_models(self, configs: Dict[str, AIModelConfig]):
        """异步初始化所有模型"""
        logger.info(f"开始初始化 {len(configs)} 个模型")
        
        # 并行初始化模型
        init_tasks = []
        for provider, config in configs.items():
            if provider in self.model_classes:
                task = self._initialize_single_model(provider, config)
                init_tasks.append(task)
        
        # 等待所有初始化完成
        results = await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # 统计初始化结果
        success_count = sum(1 for result in results if result is True)
        logger.info(f"模型初始化完成: {success_count}/{len(configs)} 成功")
        
        # 初始化熔断器
        for provider in self.models.keys():
            self.circuit_breakers[provider] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=Exception
            )
    
    async def _initialize_single_model(self, provider: str, config: AIModelConfig) -> bool:
        """初始化单个模型"""
        try:
            logger.info(f"初始化模型: {provider}")
            
            model_class = self.model_classes[provider]
            model = model_class(config)
            
            # 异步初始化
            success = await model.initialize()
            
            if success:
                self.models[provider] = model
                
                # 初始化指标
                self.model_metrics[provider] = ModelMetrics(
                    provider=provider,
                    model_name=config.name,
                    capabilities=self._get_model_capabilities(provider)
                )
                
                logger.info(f"模型 {provider} 初始化成功")
                return True
            else:
                logger.warning(f"模型 {provider} 初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"初始化模型 {provider} 失败: {e}")
            return False
    
    def _get_model_capabilities(self, provider: str) -> List[ModelCapability]:
        """获取模型能力"""
        # 根据模型类型定义能力
        capabilities = [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CONTENT_ANALYSIS
        ]
        
        # 特定模型的能力
        if provider in ["qianwen", "wenxin", "zhipu"]:
            capabilities.extend([
                ModelCapability.COMMENTARY_GENERATION,
                ModelCapability.MONOLOGUE_GENERATION,
                ModelCapability.SCENE_ANALYSIS,
                ModelCapability.SUBTITLE_GENERATION
            ])
        
        return capabilities
    
    async def process_request(self, request: ModelRequest) -> AIResponse:
        """处理模型请求"""
        try:
            # 检查熔断器状态
            circuit_breaker = self.circuit_breakers.get(request.provider)
            if circuit_breaker and circuit_breaker.is_open():
                raise Exception(f"模型 {request.provider} 熔断器开启")
            
            # 获取模型
            model = self.models.get(request.provider)
            if not model:
                raise Exception(f"模型 {request.provider} 不存在")
            
            # 记录开始时间
            start_time = time.time()
            
            # 执行请求
            response = await self._execute_model_request(model, request)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 更新指标
            if response.success:
                tokens = response.usage.get("total_tokens", 0)
                self.model_metrics[request.provider].update_success(response_time, tokens)
                
                # 记录成功
                if circuit_breaker:
                    circuit_breaker.success()
            else:
                self.model_metrics[request.provider].update_failure()
                
                # 记录失败
                if circuit_breaker:
                    circuit_breaker.failure()
            
            # 更新性能历史
            self.performance_history[request.provider].append({
                "timestamp": start_time,
                "response_time": response_time,
                "success": response.success,
                "tokens": response.usage.get("total_tokens", 0)
            })
            
            return response
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return AIResponse(
                success=False,
                error_message=str(e)
            )
    
    async def _execute_model_request(self, model: BaseAIModel, request: ModelRequest) -> AIResponse:
        """执行模型请求"""
        try:
            if request.capability == ModelCapability.TEXT_GENERATION:
                return await model.generate_text(request.prompt, **request.parameters)
            elif request.capability == ModelCapability.CONTENT_ANALYSIS:
                return await model.analyze_content(request.prompt, **request.parameters)
            elif request.capability == ModelCapability.COMMENTARY_GENERATION:
                return await model.generate_commentary(**request.parameters)
            elif request.capability == ModelCapability.MONOLOGUE_GENERATION:
                return await model.generate_monologue(**request.parameters)
            else:
                # 默认使用文本生成
                return await model.generate_text(request.prompt, **request.parameters)
                
        except Exception as e:
            logger.error(f"模型请求执行失败: {e}")
            return AIResponse(
                success=False,
                error_message=str(e)
            )
    
    def get_best_model_for_task(self, capability: ModelCapability, 
                               prompt_length: int = 0) -> Optional[str]:
        """为任务选择最佳模型"""
        available_models = []
        
        for provider, metrics in self.model_metrics.items():
            # 检查模型是否支持该能力
            if capability not in metrics.capabilities:
                continue
            
            # 检查模型健康状态
            if metrics.health_status in [ModelHealthStatus.UNHEALTHY, ModelHealthStatus.UNKNOWN]:
                continue
            
            # 检查熔断器状态
            circuit_breaker = self.circuit_breakers.get(provider)
            if circuit_breaker and circuit_breaker.is_open():
                continue
            
            # 计算模型评分
            score = self._calculate_model_score(metrics, capability, prompt_length)
            available_models.append((provider, score))
        
        # 按评分排序
        available_models.sort(key=lambda x: x[1], reverse=True)
        
        return available_models[0][0] if available_models else None
    
    def _calculate_model_score(self, metrics: ModelMetrics, 
                              capability: ModelCapability, prompt_length: int) -> float:
        """计算模型评分"""
        # 基础分数
        score = metrics.health_score * 100
        
        # 响应时间权重（响应时间越短分数越高）
        response_time_score = max(0, 100 - metrics.response_time * 10)
        score += response_time_score * 0.3
        
        # 成功率权重
        success_rate_score = (1 - metrics.error_rate) * 100
        score += success_rate_score * 0.2
        
        # 成本权重（成本越低分数越高）
        if metrics.cost_per_1k_tokens > 0:
            cost_score = max(0, 100 - metrics.cost_per_1k_tokens * 50)
            score += cost_score * 0.2
        
        # 处理速度权重
        if metrics.average_tokens_per_second > 0:
            speed_score = min(100, metrics.average_tokens_per_second * 10)
            score += speed_score * 0.3
        
        return score
    
    def get_model_health_summary(self) -> Dict[str, Any]:
        """获取模型健康状态摘要"""
        summary = {}
        
        for provider, metrics in self.model_metrics.items():
            summary[provider] = {
                "provider": metrics.provider,
                "model_name": metrics.model_name,
                "health_status": metrics.health_status.value,
                "health_score": metrics.health_score,
                "response_time": metrics.response_time,
                "error_rate": metrics.error_rate,
                "success_count": metrics.success_count,
                "total_requests": metrics.total_requests,
                "consecutive_failures": metrics.consecutive_failures,
                "average_tokens_per_second": metrics.average_tokens_per_second,
                "cost_per_1k_tokens": metrics.cost_per_1k_tokens,
                "capabilities": [cap.value for cap in metrics.capabilities],
                "last_used": datetime.fromtimestamp(metrics.last_used).isoformat()
            }
        
        return summary
    
    def get_performance_metrics(self, provider: str, time_range: int = 3600) -> Dict[str, Any]:
        """获取性能指标"""
        if provider not in self.performance_history:
            return {}
        
        # 获取指定时间范围内的数据
        current_time = time.time()
        history = [
            entry for entry in self.performance_history[provider]
            if current_time - entry["timestamp"] <= time_range
        ]
        
        if not history:
            return {}
        
        # 计算指标
        response_times = [entry["response_time"] for entry in history]
        success_entries = [entry for entry in history if entry["success"]]
        
        return {
            "provider": provider,
            "time_range": time_range,
            "total_requests": len(history),
            "successful_requests": len(success_entries),
            "success_rate": len(success_entries) / len(history) if history else 0,
            "average_response_time": np.mean(response_times) if response_times else 0,
            "min_response_time": np.min(response_times) if response_times else 0,
            "max_response_time": np.max(response_times) if response_times else 0,
            "p95_response_time": np.percentile(response_times, 95) if response_times else 0,
            "total_tokens": sum(entry["tokens"] for entry in history),
            "average_tokens_per_second": np.mean([
                entry["tokens"] / entry["response_time"] 
                for entry in history if entry["response_time"] > 0
            ]) if history else 0
        }
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 健康检查任务
        QTimer.singleShot(self.health_check_interval * 1000, self._perform_health_check)
        
        # 性能指标更新任务
        QTimer.singleShot(self.metrics_update_interval * 1000, self._update_metrics)
    
    def _perform_health_check(self):
        """执行健康检查"""
        async def health_check():
            for provider, model in self.models.items():
                try:
                    start_time = time.time()
                    response = await model.generate_text("你好", max_tokens=10)
                    response_time = time.time() - start_time
                    
                    if response.success:
                        self.model_metrics[provider].update_success(response_time)
                    else:
                        self.model_metrics[provider].update_failure()
                        
                except Exception as e:
                    logger.error(f"健康检查 {provider} 失败: {e}")
                    self.model_metrics[provider].update_failure()
            
            # 发送更新信号
            self.model_health_updated.emit(self.get_model_health_summary())
            
            # 安排下次检查
            QTimer.singleShot(self.health_check_interval * 1000, self._perform_health_check)
        
        # 在异步循环中执行
        asyncio.create_task(health_check())
    
    def _update_metrics(self):
        """更新性能指标"""
        # 发送性能更新信号
        metrics_summary = {}
        for provider in self.models.keys():
            metrics_summary[provider] = self.get_performance_metrics(provider)
        
        self.model_performance_updated.emit(metrics_summary)
        
        # 安排下次更新
        QTimer.singleShot(self.metrics_update_interval * 1000, self._update_metrics)
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理模型管理器资源")
        
        # 关闭所有模型连接
        for model in self.models.values():
            if hasattr(model, 'close'):
                await model.close()
        
        # 清理数据
        self.models.clear()
        self.model_metrics.clear()
        self.performance_history.clear()
        
        logger.info("模型管理器资源清理完成")


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()
    
    def call(self, func: Callable, *args, **kwargs):
        """调用函数并处理熔断逻辑"""
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("熔断器开启")
        
        try:
            result = func(*args, **kwargs)
            self.success()
            return result
        except self.expected_exception as e:
            self.failure()
            raise e
    
    def success(self):
        """成功调用"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
    
    def failure(self):
        """失败调用"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
    
    def is_open(self) -> bool:
        """检查熔断器是否开启"""
        return self.state == "OPEN"
    
    def get_state(self) -> str:
        """获取熔断器状态"""
        return self.state