#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一令牌管理器 - 实现ITokenManager接口
提供令牌预算管理、预留、消费和优化功能
"""

import json
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .interfaces import (
    ITokenManager, ITokenOptimizer, TokenUsage, TokenBudget,
    TokenReservation, AIRequest, AIResponse, AITaskType
)
from .optimized_cost_manager import OptimizedCostManager

logger = logging.getLogger(__name__)


class TokenAlertLevel(Enum):
    """令牌告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TokenReservationStatus(Enum):
    """令牌预留状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    CONSUMED = "consumed"


@dataclass
class TokenAlert:
    """令牌告警信息"""
    level: TokenAlertLevel
    message: str
    current_usage: int
    budget_limit: int
    threshold: float
    timestamp: datetime


class UnifiedTokenManager(QObject, ITokenManager):
    """统一令牌管理器"""

    # 信号定义
    token_alert = pyqtSignal(TokenAlert)  # 令牌告警
    reservation_created = pyqtSignal(TokenReservation)  # 预留创建
    reservation_released = pyqtSignal(str)  # 预留释放
    tokens_consumed = pyqtSignal(str, TokenUsage, float)  # 令牌消费
    budget_exceeded = pyqtSignal(str, int)  # 预算超限

    def __init__(self, cost_manager: Optional[OptimizedCostManager] = None):
        super().__init__()

        self.cost_manager = cost_manager
        self.budgets: Dict[str, TokenBudget] = {}
        self.reservations: Dict[str, TokenReservation] = {}
        self.token_cache: Dict[str, Tuple[List[str], float]] = {}
        self.usage_history: deque = deque(maxlen=10000)

        # 统计数据
        self.total_consumed_tokens = 0
        self.total_cached_tokens = 0
        self.total_saved_tokens = 0

        # 配置
        self.default_budget_tokens = 1000000  # 1M tokens默认预算
        self.reservation_timeout = 3600  # 1小时预留超时
        self.cache_ttl = 3600  # 1小时缓存

        # 线程安全
        self._lock = threading.RLock()

        # 初始化定时器
        self._init_timers()

    def _init_timers(self):
        """初始化定时器"""
        # 预留清理定时器
        self.reservation_cleanup_timer = QTimer()
        self.reservation_cleanup_timer.timeout.connect(self._cleanup_expired_reservations)
        self.reservation_cleanup_timer.start(300000)  # 5分钟

        # 缓存清理定时器
        self.cache_cleanup_timer = QTimer()
        self.cache_cleanup_timer.timeout.connect(self._cleanup_expired_cache)
        self.cache_cleanup_timer.start(600000)  # 10分钟

    def create_budget(self, name: str, total_tokens: int, period: str = "monthly") -> TokenBudget:
        """创建令牌预算"""
        with self._lock:
            now = datetime.now()

            # 计算预算周期
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif period == "weekly":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = start_date - timedelta(days=start_date.weekday())
                end_date = start_date + timedelta(days=7)
            elif period == "monthly":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
            elif period == "yearly":
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                start_date = now
                end_date = now + timedelta(days=30)

            budget = TokenBudget(
                total_tokens=total_tokens,
                period=period,
                start_date=start_date,
                end_date=end_date
            )

            self.budgets[name] = budget
            logger.info(f"创建令牌预算: {name}, 总令牌: {total_tokens}, 周期: {period}")

            return budget

    def check_token_availability(self, estimated_tokens: int, provider: str = None) -> bool:
        """检查令牌可用性"""
        with self._lock:
            # 检查总预算
            total_available = 0
            total_reserved = 0

            for budget in self.budgets.values():
                if budget.used_tokens + budget.reserved_tokens < budget.total_tokens:
                    total_available += budget.total_tokens - budget.used_tokens - budget.reserved_tokens
                total_reserved += budget.reserved_tokens

            # 检查预留
            available_tokens = total_available + total_reserved

            # 考虑成本管理器的预算限制
            if self.cost_manager:
                # 估算成本并检查预算
                estimated_cost = self._estimate_cost_from_tokens(estimated_tokens, provider)
                if not self.cost_manager.check_budget_limit(estimated_cost):
                    logger.warning(f"成本预算限制，无法分配 {estimated_tokens} 令牌")
                    return False

            return available_tokens >= estimated_tokens

    def reserve_tokens(self, tokens: int, purpose: str, provider: str = None,
                      priority: int = 0, expires_in: int = 3600) -> TokenReservation:
        """预留令牌"""
        with self._lock:
            # 检查可用性
            if not self.check_token_availability(tokens, provider):
                raise ValueError(f"没有足够的可用令牌来预留 {tokens} 个令牌")

            # 创建预留
            reservation_id = str(uuid.uuid4())
            now = datetime.now()
            expires_at = now + timedelta(seconds=expires_in) if expires_in > 0 else None

            reservation = TokenReservation(
                reservation_id=reservation_id,
                tokens=tokens,
                purpose=purpose,
                created_at=now,
                expires_at=expires_at,
                provider=provider,
                priority=priority
            )

            self.reservations[reservation_id] = reservation

            # 更新预算预留
            for budget in self.budgets.values():
                if budget.used_tokens + budget.reserved_tokens <= budget.total_tokens:
                    budget.reserved_tokens += tokens
                    break

            logger.info(f"预留令牌: {tokens}, 用途: {purpose}, 预留ID: {reservation_id}")
            self.reservation_created.emit(reservation)

            return reservation

    def release_reservation(self, reservation_id: str) -> bool:
        """释放令牌预留"""
        with self._lock:
            if reservation_id not in self.reservations:
                return False

            reservation = self.reservations[reservation_id]

            # 更新预算预留
            for budget in self.budgets.values():
                budget.reserved_tokens = max(0, budget.reserved_tokens - reservation.tokens)

            # 标记为已释放
            reservation.status = TokenReservationStatus.RELEASED
            del self.reservations[reservation_id]

            logger.info(f"释放令牌预留: {reservation_id}")
            self.reservation_released.emit(reservation_id)

            return True

    def consume_tokens(self, provider: str, token_usage: TokenUsage, cost: float = 0.0) -> None:
        """消费令牌"""
        with self._lock:
            # 更新统计
            self.total_consumed_tokens += token_usage.total_tokens
            self.total_cached_tokens += token_usage.cached_tokens

            # 记录使用历史
            self.usage_history.append({
                'timestamp': datetime.now(),
                'provider': provider,
                'token_usage': asdict(token_usage),
                'cost': cost
            })

            # 更新预算使用
            for budget in self.budgets.values():
                if budget.used_tokens < budget.total_tokens:
                    actual_consumed = min(token_usage.total_tokens, budget.total_tokens - budget.used_tokens)
                    budget.used_tokens += actual_consumed
                    break

            # 检查告警
            self._check_budget_alerts()

            # 通知成本管理器
            if self.cost_manager:
                usage_data = {
                    'prompt_tokens': token_usage.prompt_tokens,
                    'completion_tokens': token_usage.completion_tokens,
                    'total_tokens': token_usage.total_tokens,
                    'cached_tokens': token_usage.cached_tokens
                }
                self.cost_manager.record_usage(provider, usage_data, cost)

            logger.debug(f"消费令牌: {provider}, {token_usage.total_tokens} tokens, 成本: {cost}")
            self.tokens_consumed.emit(provider, token_usage, cost)

    def get_token_budget_status(self) -> Dict[str, Any]:
        """获取令牌预算状态"""
        with self._lock:
            total_budget = sum(b.total_tokens for b in self.budgets.values())
            total_used = sum(b.used_tokens for b in self.budgets.values())
            total_reserved = sum(b.reserved_tokens for b in self.budgets.values())

            active_reservations = [
                asdict(r) for r in self.reservations.values()
                if r.expires_at is None or r.expires_at > datetime.now()
            ]

            return {
                'total_budget': total_budget,
                'total_used': total_used,
                'total_reserved': total_reserved,
                'total_available': total_budget - total_used - total_reserved,
                'usage_percentage': (total_used / total_budget * 100) if total_budget > 0 else 0,
                'budgets': {name: asdict(budget) for name, budget in self.budgets.items()},
                'active_reservations': active_reservations,
                'total_consumed_tokens': self.total_consumed_tokens,
                'total_cached_tokens': self.total_cached_tokens,
                'total_saved_tokens': self.total_saved_tokens
            }

    def set_token_alert(self, threshold: float, callback: Callable) -> None:
        """设置令牌预警"""
        # 这里可以实现更复杂的告警逻辑
        logger.info(f"设置令牌预警阈值: {threshold}")

    def get_token_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取令牌优化建议"""
        suggestions = []

        # 分析使用模式
        if self.usage_history:
            recent_usage = list(self.usage_history)[-100:]  # 最近100条记录

            # 检查高成本提供商
            provider_costs = defaultdict(float)
            provider_tokens = defaultdict(int)

            for record in recent_usage:
                provider = record['provider']
                cost = record.get('cost', 0)
                tokens = record['token_usage'].get('total_tokens', 0)

                provider_costs[provider] += cost
                provider_tokens[provider] += tokens

            # 计算成本效率
            for provider in provider_costs:
                if provider_tokens[provider] > 0:
                    cost_per_token = provider_costs[provider] / provider_tokens[provider]
                    if cost_per_token > 0.002:  # 高于平均成本
                        suggestions.append({
                            'type': 'provider_efficiency',
                            'provider': provider,
                            'message': f"提供商 {provider} 的成本较高，考虑更换更经济的提供商",
                            'priority': 'medium',
                            'potential_savings': provider_tokens[provider] * (cost_per_token - 0.001)
                        })

            # 检查缓存命中率
            total_tokens = sum(record['token_usage'].get('total_tokens', 0) for record in recent_usage)
            cached_tokens = sum(record['token_usage'].get('cached_tokens', 0) for record in recent_usage)

            if total_tokens > 0:
                cache_hit_rate = cached_tokens / total_tokens
                if cache_hit_rate < 0.1:  # 缓存命中率低于10%
                    suggestions.append({
                        'type': 'cache_optimization',
                        'message': f"缓存命中率较低 ({cache_hit_rate:.1%})，建议增加缓存使用",
                        'priority': 'low',
                        'current_hit_rate': cache_hit_rate
                    })

        return suggestions

    def get_provider_efficiency_ranking(self) -> List[Tuple[str, float]]:
        """获取提供商效率排名"""
        if not self.usage_history:
            return []

        provider_stats = defaultdict(lambda: {'total_cost': 0.0, 'total_tokens': 0})

        for record in self.usage_history:
            provider = record['provider']
            cost = record.get('cost', 0)
            tokens = record['token_usage'].get('total_tokens', 0)

            provider_stats[provider]['total_cost'] += cost
            provider_stats[provider]['total_tokens'] += tokens

        # 计算效率 (tokens per cost unit)
        efficiencies = []
        for provider, stats in provider_stats.items():
            if stats['total_cost'] > 0:
                efficiency = stats['total_tokens'] / stats['total_cost']
                efficiencies.append((provider, efficiency))

        # 按效率排序
        efficiencies.sort(key=lambda x: x[1], reverse=True)

        return efficiencies

    def cache_tokens(self, key: str, tokens: List[str], ttl: float = 3600.0) -> bool:
        """缓存令牌结果"""
        with self._lock:
            expire_time = time.time() + ttl
            self.token_cache[key] = (tokens, expire_time)

            # 估算缓存的令牌数量
            estimated_cached_tokens = sum(len(token.split()) for token in tokens)
            self.total_cached_tokens += estimated_cached_tokens

            logger.debug(f"缓存令牌结果: {key}, 估算 {estimated_cached_tokens} tokens")
            return True

    def get_cached_tokens(self, key: str) -> Optional[List[str]]:
        """获取缓存的令牌结果"""
        with self._lock:
            if key in self.token_cache:
                tokens, expire_time = self.token_cache[key]

                if time.time() < expire_time:
                    logger.debug(f"获取缓存的令牌结果: {key}")
                    return tokens
                else:
                    # 清理过期缓存
                    del self.token_cache[key]

            return None

    def _cleanup_expired_reservations(self):
        """清理过期的预留"""
        with self._lock:
            now = datetime.now()
            expired_reservations = []

            for reservation_id, reservation in self.reservations.items():
                if (reservation.expires_at and reservation.expires_at < now and
                    reservation.status == TokenReservationStatus.ACTIVE):
                    expired_reservations.append(reservation_id)

            for reservation_id in expired_reservations:
                self.release_reservation(reservation_id)

    def _cleanup_expired_cache(self):
        """清理过期的缓存"""
        with self._lock:
            now = time.time()
            expired_keys = []

            for key, (_, expire_time) in self.token_cache.items():
                if expire_time < now:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.token_cache[key]

    def _check_budget_alerts(self):
        """检查预算告警"""
        for budget_name, budget in self.budgets.items():
            if budget.total_tokens > 0:
                usage_ratio = budget.used_tokens / budget.total_tokens

                for threshold in budget.alert_thresholds:
                    if usage_ratio >= threshold and usage_ratio < threshold + 0.05:  # 避免重复告警
                        alert = TokenAlert(
                            level=self._get_alert_level(threshold),
                            message=f"预算 {budget_name} 使用率达到 {usage_ratio:.1%}",
                            current_usage=budget.used_tokens,
                            budget_limit=budget.total_tokens,
                            threshold=threshold,
                            timestamp=datetime.now()
                        )

                        self.token_alert.emit(alert)
                        logger.warning(f"令牌预算告警: {alert.message}")

                        if usage_ratio >= 1.0:
                            self.budget_exceeded.emit(budget_name, budget.used_tokens)

    def _get_alert_level(self, threshold: float) -> TokenAlertLevel:
        """获取告警级别"""
        if threshold >= 1.0:
            return TokenAlertLevel.CRITICAL
        elif threshold >= 0.9:
            return TokenAlertLevel.WARNING
        else:
            return TokenAlertLevel.INFO

    def _estimate_cost_from_tokens(self, tokens: int, provider: str = None) -> float:
        """根据令牌数估算成本"""
        if not self.cost_manager:
            return tokens * 0.001  # 默认成本估算

        # 这里可以使用成本管理器的定价信息
        # 简化实现，实际应该根据提供商的定价模型计算
        return tokens * 0.001

    def get_usage_summary(self) -> Dict[str, Any]:
        """获取使用摘要"""
        with self._lock:
            if not self.usage_history:
                return {'total_requests': 0}

            total_requests = len(self.usage_history)
            total_tokens = sum(record['token_usage'].get('total_tokens', 0) for record in self.usage_history)
            total_cost = sum(record.get('cost', 0) for record in self.usage_history)

            # 按提供商统计
            provider_stats = defaultdict(lambda: {'requests': 0, 'tokens': 0, 'cost': 0})
            for record in self.usage_history:
                provider = record['provider']
                provider_stats[provider]['requests'] += 1
                provider_stats[provider]['tokens'] += record['token_usage'].get('total_tokens', 0)
                provider_stats[provider]['cost'] += record.get('cost', 0)

            return {
                'total_requests': total_requests,
                'total_tokens': total_tokens,
                'total_cost': total_cost,
                'average_cost_per_request': total_cost / total_requests if total_requests > 0 else 0,
                'average_tokens_per_request': total_tokens / total_requests if total_requests > 0 else 0,
                'provider_stats': dict(provider_stats),
                'cache_hit_rate': self.total_cached_tokens / max(total_tokens, 1)
            }