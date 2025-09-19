#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化AI管理器 - 集成所有优化功能的AI管理器
包含智能负载均衡、成本管理、内容审核等优化功能
"""

import asyncio
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Type, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import PriorityQueue, Queue

from PyQt6.QtCore import QEventLoop, QTimer
import aiohttp
import numpy as np
from collections import defaultdict, deque

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from .models.base_model import BaseAIModel, AIModelConfig, AIResponse
from .models.qianwen_model import QianwenModel
from .models.wenxin_model import WenxinModel
from .models.zhipu_model import ZhipuModel
from .models.xunfei_model import XunfeiModel
from .models.hunyuan_model import HunyuanModel
from .models.deepseek_model import DeepSeekModel


@dataclass
class ProviderMetrics:
    """提供商性能指标"""
    provider: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    last_used: datetime = field(default_factory=datetime.now)
    health_score: float = 1.0
    consecutive_failures: int = 0
    
    def update_success(self, response_time: float, tokens: int, cost: float):
        """更新成功指标"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_used = datetime.now()
        
        # 更新平均响应时间
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (self.average_response_time * 0.9) + (response_time * 0.1)
        
        self.total_tokens += tokens
        self.total_cost += cost
        self.health_score = min(1.0, self.health_score + 0.05)
    
    def update_failure(self):
        """更新失败指标"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.health_score = max(0.0, self.health_score - 0.1)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"
    COST_OPTIMIZED = "cost_optimized"
    ADAPTIVE = "adaptive"


class OptimizedAIManager(QObject):
    """优化AI管理器"""
    
    # 信号定义
    request_started = pyqtSignal(str, str)  # provider, request_id
    request_completed = pyqtSignal(str, str, float)  # provider, request_id, response_time
    request_failed = pyqtSignal(str, str, str)  # provider, request_id, error_message
    cost_updated = pyqtSignal(float, float)  # current_cost, budget_limit
    provider_health_changed = pyqtSignal(str, float)  # provider, health_score
    task_queue_updated = pyqtSignal(int, int)  # queue_size, max_queue_size
    performance_metrics_updated = pyqtSignal(dict)  # 性能指标更新
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        
        # 模型映射
        self.model_map = {
            'qianwen': QianwenModel,
            'wenxin': WenxinModel,
            'zhipu': ZhipuModel,
            'xunfei': XunfeiModel,
            'hunyuan': HunyuanModel,
            'deepseek': DeepSeekModel
        }
        
        # 模型实例
        self.models: Dict[str, BaseAIModel] = {}
        
        # 性能指标
        self.metrics: Dict[str, ProviderMetrics] = {}
        
        # 负载均衡
        self.load_balancing_strategy = LoadBalancingStrategy.ADAPTIVE
        self.current_index = 0
        self.request_queue = PriorityQueue()
        self.max_queue_size = 100
        
        # 成本管理
        self.budget_limit = 1000.0
        self.current_cost = 0.0
        self.daily_budget = 100.0
        self.daily_cost = 0.0
        self.cost_alert_threshold = 0.8  # 80%预算告警
        
        # 缓存系统
        self.response_cache = {}
        self.cache_ttl = 3600  # 1小时
        self.max_cache_size = 1000
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # 会话管理
        self.session = None
        
        # 任务队列管理
        self.active_tasks: Dict[str, dict] = {}
        self.task_results: Dict[str, Any] = {}
        self.max_concurrent_tasks = 5
        
        # 性能监控
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'cache_hit_rate': 0.0,
            'cost_efficiency': 0.0
        }
        
        # 统计数据
        self.usage_stats = defaultdict(int)
        
        # 初始化
        self._initialize_metrics()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _initialize_metrics(self):
        """初始化性能指标"""
        for provider in self.model_map.keys():
            self.metrics[provider] = ProviderMetrics(provider=provider)
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 健康检查定时器
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self._perform_health_check)
        self.health_check_timer.start(30000)  # 30秒
        
        # 成本统计定时器
        self.cost_timer = QTimer()
        self.cost_timer.timeout.connect(self._update_cost_stats)
        self.cost_timer.start(60000)  # 1分钟
        
        # 缓存清理定时器
        self.cache_timer = QTimer()
        self.cache_timer.timeout.connect(self._cleanup_cache)
        self.cache_timer.start(3600000)  # 1小时
        
        # 性能监控定时器
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_metrics)
        self.performance_timer.start(30000)  # 30秒
        
        # 任务队列监控定时器
        self.queue_monitor_timer = QTimer()
        self.queue_monitor_timer.timeout.connect(self._monitor_task_queue)
        self.queue_monitor_timer.start(10000)  # 10秒
    
    async def initialize(self):
        """初始化AI管理器"""
        try:
            # 创建HTTP会话
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=10)
            )
            
            # 加载配置
            config = self.settings_manager.get_ai_config()
            
            # 初始化模型
            for provider_name, provider_config in config.get('providers', {}).items():
                if provider_config.get('enabled', False):
                    await self._initialize_provider(provider_name, provider_config)
            
            logging.info(f"优化AI管理器初始化完成，已加载 {len(self.models)} 个模型")
            
        except Exception as e:
            logging.error(f"优化AI管理器初始化失败: {e}")
    
    async def _initialize_provider(self, provider_name: str, config: Dict[str, Any]):
        """初始化提供商"""
        try:
            if provider_name not in self.model_map:
                logging.warning(f"未知的提供商: {provider_name}")
                return
            
            # 创建模型配置
            model_config = AIModelConfig(
                name=provider_name,
                api_key=config.get('api_key', ''),
                api_url=config.get('api_url', ''),
                model=config.get('model', ''),
                enabled=config.get('enabled', True),
                max_tokens=config.get('max_tokens', 4096),
                temperature=config.get('temperature', 0.7),
                api_secret=config.get('api_secret', ''),
                app_id=config.get('app_id', ''),
                timeout=config.get('timeout', 30)
            )
            
            # 创建模型实例
            model_class = self.model_map[provider_name]
            model = model_class(model_config)
            
            # 初始化模型
            if await model.initialize():
                self.models[provider_name] = model
                logging.info(f"✅ {provider_name} 模型初始化成功")
            else:
                logging.warning(f"❌ {provider_name} 模型初始化失败")
                
        except Exception as e:
            logging.error(f"初始化提供商 {provider_name} 失败: {e}")
    
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本（智能负载均衡）"""
        try:
            # 检查缓存
            cache_key = self._get_cache_key(prompt, kwargs)
            if cache_key in self.response_cache:
                cached_response = self.response_cache[cache_key]
                if time.time() - cached_response['timestamp'] < self.cache_ttl:
                    return cached_response['response']
            
            # 选择最佳提供商
            provider = self._select_best_provider()
            if not provider:
                return AIResponse(
                    success=False,
                    error_message="没有可用的AI模型"
                )
            
            # 生成请求ID
            request_id = f"{provider}_{int(time.time() * 1000)}"
            
            # 发射信号
            self.request_started.emit(provider, request_id)
            
            # 记录开始时间
            start_time = time.time()
            
            # 发送请求
            model = self.models[provider]
            response = await model.generate_text(prompt, **kwargs)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            if response.success:
                # 更新指标
                tokens = response.usage.get('total_tokens', 0)
                cost = self._calculate_cost(provider, tokens)
                
                self.metrics[provider].update_success(response_time, tokens, cost)
                self.current_cost += cost
                self.daily_cost += cost
                
                # 缓存响应
                self.response_cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }
                
                # 发射信号
                self.request_completed.emit(provider, request_id, response_time)
                self.cost_updated.emit(self.current_cost, self.budget_limit)
                
                logging.info(f"✅ {provider} 生成文本成功，耗时 {response_time:.2f}s")
                
            else:
                self.metrics[provider].update_failure()
                self.request_failed.emit(provider, request_id, response.error_message)
                logging.warning(f"❌ {provider} 生成文本失败: {response.error_message}")
            
            return response
            
        except Exception as e:
            logging.error(f"生成文本失败: {e}")
            return AIResponse(
                success=False,
                error_message=str(e)
            )
    
    def _select_best_provider(self) -> Optional[str]:
        """选择最佳提供商"""
        available_providers = [
            provider for provider, model in self.models.items()
            if model.is_available() and self.metrics[provider].health_score > 0.3
        ]
        
        if not available_providers:
            return None
        
        if self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_providers)
        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(available_providers)
        elif self.load_balancing_strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
            return self._fastest_response_selection(available_providers)
        elif self.load_balancing_strategy == LoadBalancingStrategy.COST_OPTIMIZED:
            return self._cost_optimized_selection(available_providers)
        else:  # ADAPTIVE
            return self._adaptive_selection(available_providers)
    
    def _round_robin_selection(self, providers: List[str]) -> str:
        """轮询选择"""
        provider = providers[self.current_index % len(providers)]
        self.current_index += 1
        return provider
    
    def _least_connections_selection(self, providers: List[str]) -> str:
        """最少连接选择"""
        return min(providers, key=lambda p: self.metrics[p].total_requests)
    
    def _fastest_response_selection(self, providers: List[str]) -> str:
        """最快响应选择"""
        return min(providers, key=lambda p: self.metrics[p].average_response_time)
    
    def _cost_optimized_selection(self, providers: List[str]) -> str:
        """成本优化选择"""
        cost_rates = {
            'qianwen': 0.001,
            'wenxin': 0.002,
            'zhipu': 0.0015,
            'xunfei': 0.001,
            'hunyuan': 0.001,
            'deepseek': 0.001
        }
        return min(providers, key=lambda p: cost_rates.get(p, 0.002))
    
    def _adaptive_selection(self, providers: List[str]) -> str:
        """自适应选择"""
        def score(provider):
            metrics = self.metrics[provider]
            health_score = metrics.health_score
            response_time_score = 1.0 / (metrics.average_response_time + 0.1)
            success_rate_score = metrics.success_rate
            
            return health_score * 0.4 + response_time_score * 0.3 + success_rate_score * 0.3
        
        return max(providers, key=score)
    
    def _calculate_cost(self, provider: str, tokens: int) -> float:
        """计算成本"""
        rates = {
            'qianwen': 0.001,
            'wenxin': 0.002,
            'zhipu': 0.0015,
            'xunfei': 0.001,
            'hunyuan': 0.001,
            'deepseek': 0.001
        }
        rate = rates.get(provider, 0.002)
        return (tokens / 1000) * rate
    
    def _get_cache_key(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{prompt}_{sorted(kwargs.items())}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _perform_health_check(self):
        """执行健康检查"""
        for provider, model in self.models.items():
            try:
                # 简单的健康检查
                if model.is_available():
                    self.metrics[provider].health_score = min(1.0, self.metrics[provider].health_score + 0.02)
                else:
                    self.metrics[provider].health_score = max(0.0, self.metrics[provider].health_score - 0.1)
                
                self.provider_health_changed.emit(provider, self.metrics[provider].health_score)
                
            except Exception as e:
                logging.error(f"健康检查失败 {provider}: {e}")
                self.metrics[provider].health_score = max(0.0, self.metrics[provider].health_score - 0.2)
    
    def _update_cost_stats(self):
        """更新成本统计"""
        # 检查预算限制
        if self.current_cost > self.budget_limit:
            logging.warning(f"已超出预算限制: {self.current_cost} > {self.budget_limit}")
        
        # 重置每日成本
        if datetime.now().hour == 0 and datetime.now().minute < 5:
            self.daily_cost = 0.0
        
        self.cost_updated.emit(self.current_cost, self.budget_limit)
    
    def _cleanup_cache(self):
        """清理缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.response_cache.items()
            if current_time - value['timestamp'] > self.cache_ttl
        ]
        
        # 如果缓存超过最大大小，删除最旧的项
        if len(self.response_cache) > self.max_cache_size:
            sorted_items = sorted(self.response_cache.items(), key=lambda x: x[1]['timestamp'])
            overflow_count = len(self.response_cache) - self.max_cache_size
            expired_keys.extend([item[0] for item in sorted_items[:overflow_count]])
        
        for key in expired_keys:
            if key in self.response_cache:
                del self.response_cache[key]
        
        if expired_keys:
            logging.info(f"清理了 {len(expired_keys)} 个过期缓存项")
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        try:
            # 计算缓存命中率
            total_requests = self.performance_metrics['total_requests']
            if total_requests > 0:
                cache_hits = sum(1 for m in self.metrics.values() if m.total_requests > 0)
                self.performance_metrics['cache_hit_rate'] = cache_hits / total_requests
            
            # 计算成本效率
            if self.performance_metrics['total_cost'] > 0:
                self.performance_metrics['cost_efficiency'] = (
                    self.performance_metrics['successful_requests'] / self.performance_metrics['total_cost']
                )
            
            # 计算平均响应时间
            total_response_time = sum(m.average_response_time * m.total_requests for m in self.metrics.values())
            total_requests = sum(m.total_requests for m in self.metrics.values())
            if total_requests > 0:
                self.performance_metrics['average_response_time'] = total_response_time / total_requests
            
            # 发射性能指标更新信号
            self.performance_metrics_updated.emit(self.performance_metrics.copy())
            
        except Exception as e:
            logging.error(f"更新性能指标失败: {e}")
    
    def _monitor_task_queue(self):
        """监控任务队列"""
        try:
            queue_size = len(self.active_tasks)
            self.task_queue_updated.emit(queue_size, self.max_concurrent_tasks)
            
            # 如果队列过长，发出警告
            if queue_size > self.max_concurrent_tasks * 0.8:
                logging.warning(f"任务队列过长: {queue_size}/{self.max_concurrent_tasks}")
            
        except Exception as e:
            logging.error(f"监控任务队列失败: {e}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        stats = {
            'total_requests': sum(m.total_requests for m in self.metrics.values()),
            'successful_requests': sum(m.successful_requests for m in self.metrics.values()),
            'failed_requests': sum(m.failed_requests for m in self.metrics.values()),
            'total_cost': self.current_cost,
            'daily_cost': self.daily_cost,
            'average_response_time': np.mean([m.average_response_time for m in self.metrics.values() if m.average_response_time > 0]),
            'providers': {}
        }
        
        for provider, metrics in self.metrics.items():
            stats['providers'][provider] = {
                'total_requests': metrics.total_requests,
                'success_rate': metrics.success_rate,
                'average_response_time': metrics.average_response_time,
                'health_score': metrics.health_score,
                'total_cost': metrics.total_cost
            }
        
        return stats
    
    def get_provider_recommendations(self, capability: str) -> List[Dict[str, Any]]:
        """获取提供商推荐"""
        recommendations = []
        
        for provider, metrics in self.metrics.items():
            if metrics.health_score > 0.5:
                recommendations.append({
                    'provider': provider,
                    'health_score': metrics.health_score,
                    'success_rate': metrics.success_rate,
                    'average_response_time': metrics.average_response_time,
                    'cost_efficiency': 1.0 / (metrics.total_cost + 0.01)
                })
        
        # 按综合评分排序
        recommendations.sort(key=lambda x: x['health_score'] * 0.4 + x['success_rate'] * 0.3 + x['cost_efficiency'] * 0.3, reverse=True)
        
        return recommendations[:3]  # 返回前3个推荐
    
    async def generate_commentary(self, video_info: Dict[str, Any], style: str = "专业解说") -> AIResponse:
        """生成视频解说"""
        try:
            # 构建提示词
            prompt = f"""
请为以下视频生成{style}风格的解说词：

视频信息：
- 时长：{video_info.get('duration', '未知')}秒
- 类型：{video_info.get('type', '未知')}
- 内容：{video_info.get('content', '未知')}

要求：
1. 语言生动有趣，符合短视频特点
2. 解说词时长与视频时长匹配
3. 突出视频亮点和关键信息
4. 风格统一，节奏感强

请生成完整的解说词：
"""
            
            return await self.generate_text(prompt)
            
        except Exception as e:
            logging.error(f"生成解说失败: {e}")
            return AIResponse(
                success=False,
                error_message=str(e)
            )
    
    async def analyze_content(self, content: str, analysis_type: str = "general") -> AIResponse:
        """分析内容"""
        try:
            # 选择最佳提供商
            provider = self._select_best_provider()
            if not provider:
                return AIResponse(
                    success=False,
                    error_message="没有可用的AI模型"
                )
            
            model = self.models[provider]
            return await model.analyze_content(content, analysis_type)
            
        except Exception as e:
            logging.error(f"内容分析失败: {e}")
            return AIResponse(
                success=False,
                error_message=str(e)
            )
    
    def set_budget_limit(self, limit: float):
        """设置预算限制"""
        self.budget_limit = limit
        self.cost_updated.emit(self.current_cost, self.budget_limit)
    
    def set_daily_budget(self, budget: float):
        """设置每日预算"""
        self.daily_budget = budget
    
    def cleanup(self):
        """清理资源"""
        try:
            # 关闭线程池
            self.thread_pool.shutdown(wait=True)
            
            # 关闭HTTP会话
            if self.session:
                try:
                    # 尝试同步关闭
                    if hasattr(self.session, 'close_sync'):
                        self.session.close_sync()
                    else:
                        # 使用Qt的工作线程来处理异步关闭
                        loop = QEventLoop()
                        task = loop.create_task(self.session.close())
                        QTimer.singleShot(0, lambda: task)
                        loop.exec()
                except Exception as e:
                    logger.warning(f"HTTP会话关闭失败: {e}")
            
            # 清理缓存
            self.response_cache.clear()
            
            logging.info("优化AI管理器资源清理完成")
            
        except Exception as e:
            logging.error(f"清理资源失败: {e}")


# 为了保持向后兼容，创建一个工厂函数
def create_optimized_ai_manager(settings_manager) -> OptimizedAIManager:
    """创建优化AI管理器"""
    return OptimizedAIManager(settings_manager)