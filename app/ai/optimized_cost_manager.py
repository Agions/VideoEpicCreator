#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化的AI成本管理系统
实现精确的成本跟踪、预算控制、成本优化和智能分析
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class CostAlertSeverity(Enum):
    """成本警报严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CostAlertType(Enum):
    """成本警报类型"""
    BUDGET_THRESHOLD = "budget_threshold"
    BUDGET_EXCEEDED = "budget_exceeded"
    COST_SPIKE = "cost_spike"
    UNUSUAL_PATTERN = "unusual_pattern"
    RATE_LIMIT = "rate_limit"


@dataclass
class ProviderCostConfig:
    """提供商成本配置"""
    provider: str
    input_token_cost: float  # 每1k token成本
    output_token_cost: float  # 每1k token成本
    currency: str = "CNY"
    min_cost_per_request: float = 0.001
    rate_limit_requests: int = 1000  # 每小时请求限制
    rate_limit_tokens: int = 100000  # 每小时token限制


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: float
    provider: str
    request_id: str
    capability: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    success: bool
    response_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetInfo:
    """预算信息"""
    budget_id: str
    name: str
    total_amount: float
    used_amount: float = 0.0
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default=lambda: datetime.now() + timedelta(days=30))
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.9, 1.0])
    is_active: bool = True
    
    @property
    def remaining_amount(self) -> float:
        """剩余金额"""
        return max(0.0, self.total_amount - self.used_amount)
    
    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        return min(100.0, (self.used_amount / self.total_amount) * 100)
    
    @property
    def is_over_budget(self) -> bool:
        """是否超预算"""
        return self.used_amount > self.total_amount
    
    @property
    def days_remaining(self) -> int:
        """剩余天数"""
        return max(0, (self.end_date - datetime.now()).days)


@dataclass
class CostAlert:
    """成本警报"""
    alert_id: str
    alert_type: CostAlertType
    severity: CostAlertSeverity
    message: str
    timestamp: datetime
    provider: Optional[str] = None
    budget_id: Optional[str] = None
    amount: float = 0.0
    threshold: float = 0.0
    acknowledged: bool = False
    resolved: bool = False


class OptimizedCostManager(QObject):
    """优化的成本管理器"""
    
    # 信号
    cost_updated = pyqtSignal(dict)  # 成本更新
    budget_alert = pyqtSignal(object)  # 预算警报
    cost_analysis_ready = pyqtSignal(dict)  # 成本分析完成
    optimization_suggestion = pyqtSignal(dict)  # 优化建议
    
    def __init__(self):
        super().__init__()
        
        # 成本配置
        self.provider_configs: Dict[str, ProviderCostConfig] = self._load_provider_configs()
        
        # 成本记录
        self.cost_records: deque = deque(maxlen=10000)
        self.daily_costs: Dict[str, float] = defaultdict(float)
        self.monthly_costs: Dict[str, float] = defaultdict(float)
        
        # 预算管理
        self.budgets: Dict[str, BudgetInfo] = {}
        self.active_budget: Optional[BudgetInfo] = None
        
        # 警报管理
        self.alerts: List[CostAlert] = []
        self.alert_rules: List[Dict] = self._load_alert_rules()
        
        # 成本分析
        self.cost_history = defaultdict(lambda: deque(maxlen=1000))
        self.anomaly_detector = CostAnomalyDetector()
        
        # 缓存
        self.cost_cache: Dict[str, float] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 定时器
        self.analytics_timer = QTimer()
        self.analytics_timer.timeout.connect(self._perform_cost_analysis)
        self.analytics_timer.start(3600000)  # 每小时分析
        
        self.alert_check_timer = QTimer()
        self.alert_check_timer.timeout.connect(self._check_alerts)
        self.alert_check_timer.start(60000)  # 每分钟检查
        
        logger.info("优化的成本管理器初始化完成")
    
    def _load_provider_configs(self) -> Dict[str, ProviderCostConfig]:
        """加载提供商成本配置"""
        configs = {
            "qianwen": ProviderCostConfig(
                provider="qianwen",
                input_token_cost=0.0005,
                output_token_cost=0.002,
                currency="CNY"
            ),
            "wenxin": ProviderCostConfig(
                provider="wenxin",
                input_token_cost=0.001,
                output_token_cost=0.002,
                currency="CNY"
            ),
            "zhipu": ProviderCostConfig(
                provider="zhipu",
                input_token_cost=0.001,
                output_token_cost=0.0015,
                currency="CNY"
            ),
            "xunfei": ProviderCostConfig(
                provider="xunfei",
                input_token_cost=0.0008,
                output_token_cost=0.0018,
                currency="CNY"
            ),
            "hunyuan": ProviderCostConfig(
                provider="hunyuan",
                input_token_cost=0.0006,
                output_token_cost=0.0016,
                currency="CNY"
            ),
            "deepseek": ProviderCostConfig(
                provider="deepseek",
                input_token_cost=0.0004,
                output_token_cost=0.001,
                currency="CNY"
            )
        }
        return configs
    
    def _load_alert_rules(self) -> List[Dict]:
        """加载警报规则"""
        return [
            {
                "type": "budget_threshold",
                "thresholds": [0.5, 0.8, 0.9, 1.0],
                "severity": [CostAlertSeverity.LOW, CostAlertSeverity.MEDIUM, 
                           CostAlertSeverity.HIGH, CostAlertSeverity.CRITICAL]
            },
            {
                "type": "cost_spike",
                "threshold_multiplier": 3.0,
                "time_window": 3600,
                "severity": CostAlertSeverity.HIGH
            },
            {
                "type": "unusual_pattern",
                "deviation_threshold": 2.0,
                "severity": CostAlertSeverity.MEDIUM
            }
        ]
    
    def calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        config = self.provider_configs.get(provider)
        if not config:
            return 0.0
        
        # 计算基础成本
        input_cost = (input_tokens / 1000) * config.input_token_cost
        output_cost = (output_tokens / 1000) * config.output_token_cost
        total_cost = input_cost + output_cost
        
        # 应用最低消费限制
        return max(config.min_cost_per_request, total_cost)
    
    def record_cost(self, record: CostRecord):
        """记录成本"""
        # 添加到记录
        self.cost_records.append(record)
        
        # 更新统计
        date_key = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d")
        month_key = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m")
        
        self.daily_costs[date_key] += record.cost
        self.monthly_costs[month_key] += record.cost
        
        # 更新历史数据
        self.cost_history[record.provider].append({
            "timestamp": record.timestamp,
            "cost": record.cost,
            "tokens": record.total_tokens,
            "success": record.success
        })
        
        # 更新预算
        if self.active_budget:
            self.active_budget.used_amount += record.cost
        
        # 检查缓存
        cache_key = f"{record.provider}_{date_key}"
        self.cost_cache[cache_key] = self.daily_costs[date_key]
        
        # 发送更新信号
        self.cost_updated.emit(self.get_cost_summary())
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        today = datetime.now().strftime("%Y-%m-%d")
        this_month = datetime.now().strftime("%Y-%m")
        
        # 计算今日成本
        today_cost = self.daily_costs.get(today, 0.0)
        
        # 计算本月成本
        month_cost = self.monthly_costs.get(this_month, 0.0)
        
        # 计算提供商分布
        provider_costs = defaultdict(float)
        provider_requests = defaultdict(int)
        
        for record in self.cost_records:
            provider_costs[record.provider] += record.cost
            provider_requests[record.provider] += 1
        
        # 计算平均成本
        total_requests = len(self.cost_records)
        avg_cost_per_request = sum(r.cost for r in self.cost_records) / max(total_requests, 1)
        
        return {
            "today_cost": today_cost,
            "month_cost": month_cost,
            "total_requests": total_requests,
            "avg_cost_per_request": avg_cost_per_request,
            "provider_costs": dict(provider_costs),
            "provider_requests": dict(provider_requests),
            "active_budget": self.active_budget.asdict() if self.active_budget else None,
            "alert_count": len([a for a in self.alerts if not a.acknowledged])
        }
    
    def create_budget(self, name: str, amount: float, duration_days: int = 30) -> str:
        """创建预算"""
        budget_id = f"budget_{int(time.time())}"
        
        budget = BudgetInfo(
            budget_id=budget_id,
            name=name,
            total_amount=amount,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days)
        )
        
        self.budgets[budget_id] = budget
        self.active_budget = budget
        
        logger.info(f"创建预算: {name} - ¥{amount}")
        return budget_id
    
    def get_cost_analysis(self, time_range: int = 86400) -> Dict[str, Any]:
        """获取成本分析"""
        current_time = time.time()
        cutoff_time = current_time - time_range
        
        # 筛选时间范围内的记录
        relevant_records = [
            record for record in self.cost_records
            if record.timestamp >= cutoff_time
        ]
        
        if not relevant_records:
            return {"error": "没有足够的数据进行分析"}
        
        # 按提供商分组
        provider_stats = defaultdict(lambda: {
            "total_cost": 0.0,
            "total_tokens": 0,
            "request_count": 0,
            "success_count": 0,
            "avg_response_time": 0.0,
            "cost_per_token": 0.0
        })
        
        for record in relevant_records:
            stats = provider_stats[record.provider]
            stats["total_cost"] += record.cost
            stats["total_tokens"] += record.total_tokens
            stats["request_count"] += 1
            if record.success:
                stats["success_count"] += 1
        
        # 计算衍生指标
        for provider, stats in provider_stats.items():
            if stats["total_tokens"] > 0:
                stats["cost_per_token"] = stats["total_cost"] / stats["total_tokens"]
            if stats["request_count"] > 0:
                stats["success_rate"] = stats["success_count"] / stats["request_count"]
        
        # 成本趋势分析
        hourly_costs = defaultdict(float)
        for record in relevant_records:
            hour_key = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d %H:00")
            hourly_costs[hour_key] += record.cost
        
        # 异常检测
        anomalies = self.anomaly_detector.detect_anomalies(relevant_records)
        
        return {
            "time_range": time_range,
            "total_cost": sum(r.cost for r in relevant_records),
            "total_tokens": sum(r.total_tokens for r in relevant_records),
            "total_requests": len(relevant_records),
            "provider_stats": dict(provider_stats),
            "hourly_costs": dict(hourly_costs),
            "anomalies": anomalies,
            "cost_efficiency": self._calculate_cost_efficiency(provider_stats)
        }
    
    def _calculate_cost_efficiency(self, provider_stats: Dict[str, Dict]) -> Dict[str, float]:
        """计算成本效率"""
        efficiency_scores = {}
        
        for provider, stats in provider_stats.items():
            if stats["request_count"] == 0:
                continue
            
            # 成本效率分数 (越低越好，这里用倒数)
            cost_efficiency = 1.0 / max(stats["cost_per_token"], 0.001)
            
            # 成功率权重
            success_rate = stats.get("success_rate", 0.0)
            
            # 综合效率分数
            efficiency_scores[provider] = cost_efficiency * success_rate
        
        return efficiency_scores
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        suggestions = []
        
        # 分析成本效率
        analysis = self.get_cost_analysis()
        if "provider_stats" in analysis:
            provider_stats = analysis["provider_stats"]
            
            # 找出成本最高的提供商
            most_expensive = max(provider_stats.items(), 
                               key=lambda x: x[1]["cost_per_token"], 
                               default=None)
            
            if most_expensive:
                suggestions.append({
                    "type": "cost_optimization",
                    "title": "成本优化建议",
                    "description": f"{most_expensive[0]} 的成本最高 (¥{most_expensive[1]['cost_per_token']:.4f}/token)，建议考虑使用更经济的模型",
                    "priority": "medium",
                    "potential_savings": "15-30%"
                })
            
            # 找出成功率低的提供商
            low_success = [
                (provider, stats) for provider, stats in provider_stats.items()
                if stats.get("success_rate", 0.0) < 0.8
            ]
            
            for provider, stats in low_success:
                suggestions.append({
                    "type": "reliability",
                    "title": "可靠性问题",
                    "description": f"{provider} 的成功率较低 ({stats.get('success_rate', 0.0):.1%})，建议检查API配置",
                    "priority": "high"
                })
        
        # 预算相关建议
        if self.active_budget:
            usage_percentage = self.active_budget.usage_percentage
            days_remaining = self.active_budget.days_remaining
            
            if usage_percentage > 80 and days_remaining > 7:
                suggestions.append({
                    "type": "budget_management",
                    "title": "预算管理建议",
                    "description": f"预算已使用 {usage_percentage:.1f}%，但还有 {days_remaining} 天，建议控制使用频率",
                    "priority": "medium"
                })
        
        return suggestions
    
    def _perform_cost_analysis(self):
        """执行成本分析"""
        try:
            analysis = self.get_cost_analysis()
            self.cost_analysis_ready.emit(analysis)
            
            # 生成优化建议
            suggestions = self.get_optimization_suggestions()
            for suggestion in suggestions:
                self.optimization_suggestion.emit(suggestion)
                
        except Exception as e:
            logger.error(f"成本分析失败: {e}")
    
    def _check_alerts(self):
        """检查警报"""
        try:
            # 检查预算警报
            if self.active_budget:
                self._check_budget_alerts()
            
            # 检查成本异常警报
            self._check_cost_anomaly_alerts()
            
            # 检查速率限制警报
            self._check_rate_limit_alerts()
            
        except Exception as e:
            logger.error(f"检查警报失败: {e}")
    
    def _check_budget_alerts(self):
        """检查预算警报"""
        if not self.active_budget:
            return
        
        usage_percentage = self.active_budget.usage_percentage
        
        # 检查阈值警报
        for i, threshold in enumerate(self.active_budget.alert_thresholds):
            if usage_percentage >= threshold * 100:
                # 检查是否已经发送过类似警报
                existing_alert = any(
                    a for a in self.alerts
                    if (a.alert_type == CostAlertType.BUDGET_THRESHOLD and
                        a.budget_id == self.active_budget.budget_id and
                        abs(a.threshold - threshold) < 0.01 and
                        not a.acknowledged)
                )
                
                if not existing_alert:
                    severity = [CostAlertSeverity.LOW, CostAlertSeverity.MEDIUM, 
                               CostAlertSeverity.HIGH, CostAlertSeverity.CRITICAL][min(i, 3)]
                    
                    alert = CostAlert(
                        alert_id=f"budget_{int(time.time())}",
                        alert_type=CostAlertType.BUDGET_THRESHOLD,
                        severity=severity,
                        message=f"预算使用已达到 {threshold:.0%} (¥{self.active_budget.used_amount:.2f}/¥{self.active_budget.total_amount:.2f})",
                        timestamp=datetime.now(),
                        budget_id=self.active_budget.budget_id,
                        amount=self.active_budget.used_amount,
                        threshold=threshold
                    )
                    
                    self.alerts.append(alert)
                    self.budget_alert.emit(alert)
        
        # 检查超支警报
        if self.active_budget.is_over_budget:
            existing_alert = any(
                a for a in self.alerts
                if (a.alert_type == CostAlertType.BUDGET_EXCEEDED and
                    a.budget_id == self.active_budget.budget_id and
                    not a.acknowledged)
            )
            
            if not existing_alert:
                alert = CostAlert(
                    alert_id=f"budget_exceeded_{int(time.time())}",
                    alert_type=CostAlertType.BUDGET_EXCEEDED,
                    severity=CostAlertSeverity.CRITICAL,
                    message=f"预算已超支 ¥{self.active_budget.used_amount - self.active_budget.total_amount:.2f}",
                    timestamp=datetime.now(),
                    budget_id=self.active_budget.budget_id,
                    amount=self.active_budget.used_amount,
                    threshold=self.active_budget.total_amount
                )
                
                self.alerts.append(alert)
                self.budget_alert.emit(alert)
    
    def _check_cost_anomaly_alerts(self):
        """检查成本异常警报"""
        # 获取最近一小时的成本记录
        current_time = time.time()
        recent_records = [
            record for record in self.cost_records
            if current_time - record.timestamp <= 3600
        ]
        
        if len(recent_records) < 10:
            return
        
        # 使用异常检测器
        anomalies = self.anomaly_detector.detect_anomalies(recent_records)
        
        for anomaly in anomalies:
            # 检查是否已经发送过类似警报
            existing_alert = any(
                a for a in self.alerts
                if (a.alert_type == CostAlertType.COST_SPIKE and
                    a.provider == anomaly.get("provider") and
                    not a.acknowledged)
            )
            
            if not existing_alert:
                alert = CostAlert(
                    alert_id=f"anomaly_{int(time.time())}",
                    alert_type=CostAlertType.COST_SPIKE,
                    severity=CostAlertSeverity.HIGH,
                    message=f"检测到成本异常: {anomaly.get('description', '未知异常')}",
                    timestamp=datetime.now(),
                    provider=anomaly.get("provider"),
                    amount=anomaly.get("cost", 0.0)
                )
                
                self.alerts.append(alert)
                self.budget_alert.emit(alert)
    
    def _check_rate_limit_alerts(self):
        """检查速率限制警报"""
        current_time = time.time()
        hour_start = current_time - 3600
        
        # 统计每小时的请求数
        provider_requests = defaultdict(int)
        provider_tokens = defaultdict(int)
        
        for record in self.cost_records:
            if record.timestamp >= hour_start:
                provider_requests[record.provider] += 1
                provider_tokens[record.provider] += record.total_tokens
        
        # 检查速率限制
        for provider, config in self.provider_configs.items():
            if provider_requests[provider] > config.rate_limit_requests:
                alert = CostAlert(
                    alert_id=f"rate_limit_{int(time.time())}",
                    alert_type=CostAlertType.RATE_LIMIT,
                    severity=CostAlertSeverity.MEDIUM,
                    message=f"{provider} 请求频率过高 ({provider_requests[provider]}/小时)",
                    timestamp=datetime.now(),
                    provider=provider
                )
                
                self.alerts.append(alert)
                self.budget_alert.emit(alert)
            
            if provider_tokens[provider] > config.rate_limit_tokens:
                alert = CostAlert(
                    alert_id=f"token_limit_{int(time.time())}",
                    alert_type=CostAlertType.RATE_LIMIT,
                    severity=CostAlertSeverity.MEDIUM,
                    message=f"{provider} Token使用量过高 ({provider_tokens[provider]}/小时)",
                    timestamp=datetime.now(),
                    provider=provider
                )
                
                self.alerts.append(alert)
                self.budget_alert.emit(alert)
    
    def acknowledge_alert(self, alert_id: str):
        """确认警报"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break
    
    def export_cost_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """导出成本数据"""
        filtered_records = [
            record for record in self.cost_records
            if start_date <= datetime.fromtimestamp(record.timestamp) <= end_date
        ]
        
        return {
            "export_time": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_records": len(filtered_records),
            "total_cost": sum(r.cost for r in filtered_records),
            "records": [asdict(record) for record in filtered_records],
            "daily_summary": self._get_daily_summary(filtered_records),
            "provider_summary": self._get_provider_summary(filtered_records)
        }
    
    def _get_daily_summary(self, records: List[CostRecord]) -> Dict[str, Dict]:
        """获取每日摘要"""
        daily_summary = defaultdict(lambda: {
            "total_cost": 0.0,
            "total_tokens": 0,
            "request_count": 0
        })
        
        for record in records:
            date_key = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d")
            daily_summary[date_key]["total_cost"] += record.cost
            daily_summary[date_key]["total_tokens"] += record.total_tokens
            daily_summary[date_key]["request_count"] += 1
        
        return dict(daily_summary)
    
    def _get_provider_summary(self, records: List[CostRecord]) -> Dict[str, Dict]:
        """获取提供商摘要"""
        provider_summary = defaultdict(lambda: {
            "total_cost": 0.0,
            "total_tokens": 0,
            "request_count": 0,
            "success_count": 0
        })
        
        for record in records:
            provider_summary[record.provider]["total_cost"] += record.cost
            provider_summary[record.provider]["total_tokens"] += record.total_tokens
            provider_summary[record.provider]["request_count"] += 1
            if record.success:
                provider_summary[record.provider]["success_count"] += 1
        
        return dict(provider_summary)


class CostAnomalyDetector:
    """成本异常检测器"""
    
    def __init__(self):
        self.window_size = 20
        self.threshold_multiplier = 2.5
        
    def detect_anomalies(self, records: List[CostRecord]) -> List[Dict[str, Any]]:
        """检测异常"""
        if len(records) < self.window_size:
            return []
        
        anomalies = []
        
        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)
        
        # 计算移动平均和标准差
        costs = [record.cost for record in sorted_records]
        
        for i in range(self.window_size, len(costs)):
            window = costs[i - self.window_size:i]
            mean = np.mean(window)
            std = np.std(window)
            
            # 检查是否异常
            if std > 0 and abs(costs[i] - mean) > self.threshold_multiplier * std:
                anomalies.append({
                    "timestamp": sorted_records[i].timestamp,
                    "cost": costs[i],
                    "expected_range": (mean - std, mean + std),
                    "deviation": abs(costs[i] - mean) / std,
                    "description": f"成本异常: ¥{costs[i]:.4f} (预期: ¥{mean:.4f} ± ¥{std:.4f})",
                    "provider": sorted_records[i].provider
                })
        
        return anomalies