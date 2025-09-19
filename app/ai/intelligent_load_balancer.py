#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能负载均衡器
实现多策略负载均衡、故障转移、性能优化和自适应调度
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import random

from .optimized_model_manager import OptimizedModelManager, ModelMetrics, ModelCapability
from .optimized_cost_manager import OptimizedCostManager, ProviderCostConfig

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"
    COST_OPTIMIZED = "cost_optimized"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    ADAPTIVE = "adaptive"
    GEOGRAPHIC = "geographic"


class RequestPriority(Enum):
    """请求优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class ProviderWeight:
    """提供商权重"""
    provider: str
    weight: float = 1.0
    current_connections: int = 0
    max_connections: int = 100
    response_time: float = 0.0
    error_rate: float = 0.0
    cost_efficiency: float = 1.0
    health_score: float = 1.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class LoadBalancingConfig:
    """负载均衡配置"""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE
    health_check_interval: int = 30
    failure_threshold: int = 3
    recovery_time: int = 60
    max_retries: int = 3
    timeout: float = 30.0
    enable_circuit_breaker: bool = True
    enable_rate_limiting: bool = True
    max_requests_per_second: int = 100
    enable_cache: bool = True
    cache_ttl: int = 300


class IntelligentLoadBalancer:
    """智能负载均衡器"""
    
    def __init__(self, model_manager: OptimizedModelManager, 
                 cost_manager: OptimizedCostManager,
                 config: LoadBalancingConfig = None):
        self.model_manager = model_manager
        self.cost_manager = cost_manager
        self.config = config or LoadBalancingConfig()
        
        # 提供商权重
        self.provider_weights: Dict[str, ProviderWeight] = {}
        
        # 请求统计
        self.request_stats = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "last_request_time": 0.0
        })
        
        # 连接管理
        self.active_connections: Dict[str, int] = defaultdict(int)
        self.connection_history = defaultdict(lambda: deque(maxlen=100))
        
        # 性能监控
        self.performance_metrics = defaultdict(lambda: deque(maxlen=1000))
        
        # 策略状态
        self.current_strategy = self.config.strategy
        self.strategy_performance = defaultdict(float)
        
        # 故障转移
        self.failure_counts = defaultdict(int)
        self.blacklisted_providers = set()
        self.recovery_timers = {}
        
        # 缓存
        self.response_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0}
        
        # 速率限制
        self.rate_limits = defaultdict(lambda: deque(maxlen=100))
        
        # 启动后台任务
        self._start_background_tasks()
        
        logger.info(f"智能负载均衡器初始化完成，策略: {self.config.strategy.value}")
    
    async def select_provider(self, capability: ModelCapability, 
                             prompt: str = "", 
                             priority: RequestPriority = RequestPriority.NORMAL,
                             **kwargs) -> Tuple[str, Dict[str, Any]]:
        """选择最佳提供商"""
        # 检查缓存
        if self.config.enable_cache:
            cached_result = self._check_cache(capability, prompt, kwargs)
            if cached_result:
                return cached_result
        
        # 获取可用提供商
        available_providers = self._get_available_providers(capability)
        
        if not available_providers:
            raise Exception("没有可用的AI提供商")
        
        # 根据策略选择提供商
        selected_provider = None
        selection_reason = ""
        
        try:
            if self.current_strategy == LoadBalancingStrategy.ROUND_ROBIN:
                selected_provider, selection_reason = self._round_robin_selection(available_providers)
            elif self.current_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                selected_provider, selection_reason = self._least_connections_selection(available_providers)
            elif self.current_strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
                selected_provider, selection_reason = self._fastest_response_selection(available_providers)
            elif self.current_strategy == LoadBalancingStrategy.COST_OPTIMIZED:
                selected_provider, selection_reason = self._cost_optimized_selection(available_providers)
            elif self.current_strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                selected_provider, selection_reason = self._weighted_round_robin_selection(available_providers)
            elif self.current_strategy == LoadBalancingStrategy.ADAPTIVE:
                selected_provider, selection_reason = self._adaptive_selection(available_providers, capability, prompt)
            else:
                # 默认使用自适应策略
                selected_provider, selection_reason = self._adaptive_selection(available_providers, capability, prompt)
            
            # 检查速率限制
            if not self._check_rate_limit(selected_provider):
                # 如果超过速率限制，选择下一个提供商
                available_providers.remove(selected_provider)
                if available_providers:
                    selected_provider, selection_reason = self._adaptive_selection(available_providers, capability, prompt)
                else:
                    raise Exception(f"提供商 {selected_provider} 超过速率限制且无备用提供商")
            
            # 更新连接计数
            self.active_connections[selected_provider] += 1
            
            # 记录请求
            self._record_request(selected_provider, priority)
            
            logger.info(f"选择提供商: {selected_provider} ({selection_reason})")
            
            return selected_provider, {
                "strategy": self.current_strategy.value,
                "reason": selection_reason,
                "priority": priority.value,
                "connections": self.active_connections[selected_provider]
            }
            
        except Exception as e:
            logger.error(f"选择提供商失败: {e}")
            raise e
    
    def _get_available_providers(self, capability: ModelCapability) -> List[str]:
        """获取可用提供商列表"""
        available = []
        
        for provider, metrics in self.model_manager.model_metrics.items():
            # 检查是否在黑名单中
            if provider in self.blacklisted_providers:
                continue
            
            # 检查是否支持所需能力
            if capability not in metrics.capabilities:
                continue
            
            # 检查健康状态
            if metrics.health_status.value in ["unhealthy", "unknown"]:
                continue
            
            # 检查连接数限制
            max_connections = self.provider_weights.get(provider, ProviderWeight(provider)).max_connections
            if self.active_connections[provider] >= max_connections:
                continue
            
            available.append(provider)
        
        return available
    
    def _round_robin_selection(self, providers: List[str]) -> Tuple[str, str]:
        """轮询选择"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        selected = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1
        
        return selected, "轮询选择"
    
    def _least_connections_selection(self, providers: List[str]) -> Tuple[str, str]:
        """最少连接选择"""
        selected = min(providers, key=lambda p: self.active_connections[p])
        return selected, f"最少连接 ({self.active_connections[selected]})"
    
    def _fastest_response_selection(self, providers: List[str]) -> Tuple[str, str]:
        """最快响应选择"""
        provider_times = {}
        for provider in providers:
            metrics = self.model_manager.model_metrics.get(provider)
            if metrics:
                provider_times[provider] = metrics.response_time
        
        if provider_times:
            selected = min(provider_times, key=provider_times.get)
            return selected, f"最快响应 ({provider_times[selected]:.2f}s)"
        else:
            return providers[0], "默认选择"
    
    def _cost_optimized_selection(self, providers: List[str]) -> Tuple[str, str]:
        """成本优化选择"""
        provider_costs = {}
        for provider in providers:
            cost_config = self.cost_manager.provider_configs.get(provider)
            if cost_config:
                # 计算平均成本
                avg_cost = (cost_config.input_token_cost + cost_config.output_token_cost) / 2
                provider_costs[provider] = avg_cost
        
        if provider_costs:
            selected = min(provider_costs, key=provider_costs.get)
            return selected, f"成本优化 (¥{provider_costs[selected]:.4f}/token)"
        else:
            return providers[0], "默认选择"
    
    def _weighted_round_robin_selection(self, providers: List[str]) -> Tuple[str, str]:
        """加权轮询选择"""
        # 更新权重
        self._update_provider_weights()
        
        # 计算总权重
        total_weight = sum(self.provider_weights[p].weight for p in providers)
        
        if total_weight == 0:
            return providers[0], "默认选择"
        
        # 生成随机数
        random_value = random.uniform(0, total_weight)
        
        # 选择提供商
        current_weight = 0
        for provider in providers:
            current_weight += self.provider_weights[provider].weight
            if random_value <= current_weight:
                return provider, f"加权轮询 (权重: {self.provider_weights[provider].weight:.2f})"
        
        return providers[-1], "加权轮询 (默认)"
    
    def _adaptive_selection(self, providers: List[str], 
                           capability: ModelCapability, 
                           prompt: str) -> Tuple[str, str]:
        """自适应选择"""
        # 更新策略性能评估
        self._update_strategy_performance()
        
        # 获取各提供商评分
        provider_scores = {}
        for provider in providers:
            score = self._calculate_provider_score(provider, capability, prompt)
            provider_scores[provider] = score
        
        # 选择评分最高的提供商
        selected = max(provider_scores, key=provider_scores.get)
        score = provider_scores[selected]
        
        # 根据评分选择策略
        if score["health_score"] < 0.5:
            self.current_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
            reason = "健康状态不佳，使用最少连接策略"
        elif score["cost_efficiency"] > 0.8:
            self.current_strategy = LoadBalancingStrategy.COST_OPTIMIZED
            reason = "成本效率高，使用成本优化策略"
        elif score["response_time"] < 1.0:
            self.current_strategy = LoadBalancingStrategy.FASTEST_RESPONSE
            reason = "响应速度快，使用最快响应策略"
        else:
            self.current_strategy = LoadBalancingStrategy.ADAPTIVE
            reason = f"自适应选择 (评分: {score['total_score']:.2f})"
        
        return selected, reason
    
    def _calculate_provider_score(self, provider: str, 
                                 capability: ModelCapability, 
                                 prompt: str) -> Dict[str, float]:
        """计算提供商评分"""
        metrics = self.model_manager.model_metrics.get(provider)
        if not metrics:
            return {"total_score": 0.0}
        
        # 健康评分 (40%)
        health_score = metrics.health_score
        
        # 响应时间评分 (25%)
        response_time_score = max(0, 1.0 - metrics.response_time / 10.0)
        
        # 成本效率评分 (20%)
        cost_config = self.cost_manager.provider_configs.get(provider)
        cost_efficiency = 1.0
        if cost_config:
            avg_cost = (cost_config.input_token_cost + cost_config.output_token_cost) / 2
            cost_efficiency = max(0, 1.0 - avg_cost * 100)  # 成本越低分数越高
        
        # 成功率评分 (15%)
        success_rate_score = 1.0 - metrics.error_rate
        
        # 计算总分
        total_score = (
            health_score * 0.4 +
            response_time_score * 0.25 +
            cost_efficiency * 0.2 +
            success_rate_score * 0.15
        )
        
        return {
            "total_score": total_score,
            "health_score": health_score,
            "response_time": response_time_score,
            "cost_efficiency": cost_efficiency,
            "success_rate": success_rate_score
        }
    
    def _update_provider_weights(self):
        """更新提供商权重"""
        current_time = time.time()
        
        for provider, metrics in self.model_manager.model_metrics.items():
            if provider not in self.provider_weights:
                self.provider_weights[provider] = ProviderWeight(provider)
            
            weight = self.provider_weights[provider]
            
            # 基于多个因素计算权重
            new_weight = 1.0
            
            # 健康状态权重
            new_weight *= metrics.health_score
            
            # 响应时间权重
            if metrics.response_time > 0:
                new_weight *= max(0.1, 1.0 - metrics.response_time / 10.0)
            
            # 成本效率权重
            cost_config = self.cost_manager.provider_configs.get(provider)
            if cost_config:
                avg_cost = (cost_config.input_token_cost + cost_config.output_token_cost) / 2
                new_weight *= max(0.1, 1.0 - avg_cost * 50)
            
            # 平滑更新权重
            weight.weight = weight.weight * 0.9 + new_weight * 0.1
            weight.current_connections = self.active_connections[provider]
            weight.response_time = metrics.response_time
            weight.error_rate = metrics.error_rate
            weight.health_score = metrics.health_score
            weight.last_updated = current_time
    
    def _update_strategy_performance(self):
        """更新策略性能"""
        # 简化的策略性能评估
        # 实际实现中应该基于历史表现数据
        pass
    
    def _check_rate_limit(self, provider: str) -> bool:
        """检查速率限制"""
        if not self.config.enable_rate_limiting:
            return True
        
        current_time = time.time()
        recent_requests = [
            req_time for req_time in self.rate_limits[provider]
            if current_time - req_time < 1.0  # 1秒内
        ]
        
        return len(recent_requests) < self.config.max_requests_per_second
    
    def _record_request(self, provider: str, priority: RequestPriority):
        """记录请求"""
        current_time = time.time()
        
        # 更新统计
        stats = self.request_stats[provider]
        stats["total_requests"] += 1
        stats["last_request_time"] = current_time
        
        # 更新速率限制记录
        self.rate_limits[provider].append(current_time)
        
        # 更新连接历史
        self.connection_history[provider].append({
            "timestamp": current_time,
            "connections": self.active_connections[provider]
        })
    
    def _check_cache(self, capability: ModelCapability, prompt: str, 
                    kwargs: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """检查缓存"""
        if not self.config.enable_cache:
            return None
        
        # 生成缓存键
        cache_key = self._generate_cache_key(capability, prompt, kwargs)
        
        # 检查缓存
        if cache_key in self.response_cache:
            cached_data = self.response_cache[cache_key]
            
            # 检查是否过期
            if time.time() - cached_data["timestamp"] < self.config.cache_ttl:
                self.cache_stats["hits"] += 1
                return cached_data["provider"], cached_data["metadata"]
            else:
                # 删除过期缓存
                del self.response_cache[cache_key]
        
        self.cache_stats["misses"] += 1
        return None
    
    def _generate_cache_key(self, capability: ModelCapability, 
                          prompt: str, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        
        # 组合所有参数
        content = f"{capability.value}:{prompt}:{sorted(kwargs.items())}"
        
        # 生成哈希
        return hashlib.md5(content.encode()).hexdigest()
    
    def update_request_result(self, provider: str, success: bool, 
                            response_time: float, cost: float = 0.0):
        """更新请求结果"""
        # 更新连接计数
        self.active_connections[provider] = max(0, self.active_connections[provider] - 1)
        
        # 更新统计
        stats = self.request_stats[provider]
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
        
        stats["total_response_time"] += response_time
        
        # 更新性能指标
        self.performance_metrics[provider].append({
            "timestamp": time.time(),
            "success": success,
            "response_time": response_time,
            "cost": cost
        })
        
        # 处理失败情况
        if not success:
            self._handle_failure(provider)
    
    def _handle_failure(self, provider: str):
        """处理失败"""
        self.failure_counts[provider] += 1
        
        # 检查是否需要加入黑名单
        if self.failure_counts[provider] >= self.config.failure_threshold:
            self.blacklisted_providers.add(provider)
            logger.warning(f"提供商 {provider} 已加入黑名单")
            
            # 启动恢复计时器
            if provider not in self.recovery_timers:
                self.recovery_timers[provider] = time.time() + self.config.recovery_time
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 定期检查黑名单恢复
        asyncio.create_task(self._check_blacklist_recovery())
        
        # 定期清理过期缓存
        asyncio.create_task(self._cleanup_cache())
        
        # 定期更新权重
        asyncio.create_task(self._periodic_weight_update())
    
    async def _check_blacklist_recovery(self):
        """检查黑名单恢复"""
        while True:
            try:
                current_time = time.time()
                
                # 检查每个被黑名单的提供商
                for provider in list(self.blacklisted_providers):
                    if provider in self.recovery_timers:
                        if current_time >= self.recovery_timers[provider]:
                            # 尝试恢复
                            if self._test_provider_recovery(provider):
                                self.blacklisted_providers.remove(provider)
                                del self.recovery_timers[provider]
                                self.failure_counts[provider] = 0
                                logger.info(f"提供商 {provider} 已从黑名单恢复")
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                logger.error(f"检查黑名单恢复失败: {e}")
                await asyncio.sleep(30)
    
    def _test_provider_recovery(self, provider: str) -> bool:
        """测试提供商恢复"""
        try:
            metrics = self.model_manager.model_metrics.get(provider)
            if metrics and metrics.health_score > 0.5:
                return True
        except:
            pass
        return False
    
    async def _cleanup_cache(self):
        """清理过期缓存"""
        while True:
            try:
                current_time = time.time()
                
                # 清理过期缓存
                expired_keys = [
                    key for key, data in self.response_cache.items()
                    if current_time - data["timestamp"] > self.config.cache_ttl
                ]
                
                for key in expired_keys:
                    del self.response_cache[key]
                
                await asyncio.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                logger.error(f"清理缓存失败: {e}")
                await asyncio.sleep(60)
    
    async def _periodic_weight_update(self):
        """定期更新权重"""
        while True:
            try:
                self._update_provider_weights()
                await asyncio.sleep(30)  # 每30秒更新一次
            except Exception as e:
                logger.error(f"更新权重失败: {e}")
                await asyncio.sleep(60)
    
    def get_load_balancing_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        return {
            "current_strategy": self.current_strategy.value,
            "active_connections": dict(self.active_connections),
            "blacklisted_providers": list(self.blacklisted_providers),
            "failure_counts": dict(self.failure_counts),
            "provider_weights": {
                provider: {
                    "weight": weight.weight,
                    "current_connections": weight.current_connections,
                    "max_connections": weight.max_connections,
                    "health_score": weight.health_score
                }
                for provider, weight in self.provider_weights.items()
            },
            "cache_stats": self.cache_stats,
            "request_stats": dict(self.request_stats)
        }
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        self.current_strategy = strategy
        logger.info(f"负载均衡策略已更改为: {strategy.value}")
    
    def add_provider_to_blacklist(self, provider: str, timeout: int = 60):
        """手动添加提供商到黑名单"""
        self.blacklisted_providers.add(provider)
        self.recovery_timers[provider] = time.time() + timeout
        logger.info(f"提供商 {provider} 已手动加入黑名单，{timeout}秒后恢复")
    
    def remove_provider_from_blacklist(self, provider: str):
        """从黑名单移除提供商"""
        if provider in self.blacklisted_providers:
            self.blacklisted_providers.remove(provider)
            if provider in self.recovery_timers:
                del self.recovery_timers[provider]
            self.failure_counts[provider] = 0
            logger.info(f"提供商 {provider} 已从黑名单移除")
    
    def get_provider_recommendations(self, capability: ModelCapability) -> List[Dict[str, Any]]:
        """获取提供商推荐"""
        recommendations = []
        
        for provider, metrics in self.model_manager.model_metrics.items():
            if capability not in metrics.capabilities:
                continue
            
            score = self._calculate_provider_score(provider, capability, "")
            
            recommendations.append({
                "provider": provider,
                "score": score["total_score"],
                "health_score": score["health_score"],
                "response_time": metrics.response_time,
                "error_rate": metrics.error_rate,
                "cost_efficiency": score["cost_efficiency"],
                "recommendation": self._get_recommendation_text(score["total_score"])
            })
        
        # 按评分排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations
    
    def _get_recommendation_text(self, score: float) -> str:
        """获取推荐文本"""
        if score >= 0.8:
            return "强烈推荐"
        elif score >= 0.6:
            return "推荐"
        elif score >= 0.4:
            return "可以考虑"
        else:
            return "不推荐"