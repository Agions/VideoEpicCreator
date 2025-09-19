#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
令牌优化器 - 实现ITokenOptimizer接口
提供智能令牌使用优化、提供商选择和请求压缩功能
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import threading

from .interfaces import ITokenOptimizer, AIRequest, AIResponse, AITaskType, TokenUsage
from .unified_token_manager import UnifiedTokenManager

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """优化策略"""
    AGGRESSIVE = "aggressive"  # 激进优化 - 可能影响质量
    BALANCED = "balanced"  # 平衡优化 - 质量和效率平衡
    CONSERVATIVE = "conservative"  # 保守优化 - 保持质量


@dataclass
class OptimizationRule:
    """优化规则"""
    name: str
    pattern: str
    replacement: str
    description: str
    risk_level: str = "low"  # low, medium, high
    estimated_savings: int = 0


class TokenOptimizer(ITokenOptimizer):
    """令牌优化器"""

    def __init__(self, token_manager: UnifiedTokenManager):
        self.token_manager = token_manager
        self.strategy = OptimizationStrategy.BALANCED

        # 优化规则
        self.optimization_rules = self._init_optimization_rules()

        # 提供商性能缓存
        self.provider_performance_cache = {}
        self._lock = threading.RLock()

        # 统计
        self.optimization_stats = {
            'total_optimized': 0,
            'total_saved_tokens': 0,
            'rule_usage': Counter()
        }

    def _init_optimization_rules(self) -> List[OptimizationRule]:
        """初始化优化规则"""
        rules = [
            # 文本压缩规则
            OptimizationRule(
                name="多余空格压缩",
                pattern=r'\s+',
                replacement=' ',
                description="压缩多个空格为单个空格",
                risk_level="low",
                estimated_savings=50
            ),
            OptimizationRule(
                name="多余换行符移除",
                pattern=r'\n\s*\n',
                replacement='\n',
                description="移除多余的空行",
                risk_level="low",
                estimated_savings=30
            ),
            OptimizationRule(
                name="重复词组压缩",
                pattern=r'(\b\w+\b)\s+\1',
                replacement=r'\1',
                description="压缩重复的词组",
                risk_level="medium",
                estimated_savings=100
            ),
            OptimizationRule(
                name="冗余标点清理",
                pattern=r'[.]{2,}',
                replacement='.',
                description="清理冗余的标点符号",
                risk_level="low",
                estimated_savings=20
            ),
            # AI特定优化
            OptimizationRule(
                name="提示词标准化",
                pattern=r'(请|请你|麻烦你)',
                replacement='请',
                description="标准化提示词开头",
                risk_level="low",
                estimated_savings=25
            ),
            OptimizationRule(
                name="冗余礼貌用语移除",
                pattern=r'(谢谢|感谢|多谢)',
                replacement='',
                description="移除冗余的礼貌用语",
                risk_level="low",
                estimated_savings=40
            ),
            OptimizationRule(
                name="重复说明压缩",
                pattern=r'(也就是说|换句话说|即)',
                replacement='',
                description="压缩重复的说明",
                risk_level="medium",
                estimated_savings=80
            )
        ]
        return rules

    def optimize_request_tokens(self, request: AIRequest) -> AIRequest:
        """优化请求令牌"""
        with self._lock:
            original_content = request.content
            optimized_content = self._optimize_text(original_content)

            # 根据策略调整优化强度
            if self.strategy == OptimizationStrategy.AGGRESSIVE:
                optimized_content = self._aggressive_optimize(optimized_content)
            elif self.strategy == OptimizationStrategy.CONSERVATIVE:
                optimized_content = self._conservative_optimize(optimized_content)

            # 计算节省的令牌
            saved_tokens = self._estimate_token_count(original_content) - self._estimate_token_count(optimized_content)

            # 更新统计
            self.optimization_stats['total_optimized'] += 1
            self.optimization_stats['total_saved_tokens'] += max(0, saved_tokens)

            # 创建优化后的请求
            optimized_request = AIRequest(
                id=request.id,
                task_type=request.task_type,
                content=optimized_content,
                provider=request.provider,
                context=request.context.copy() if request.context else {},
                parameters=request.parameters.copy() if request.parameters else {},
                created_at=request.created_at,
                priority=request.priority
            )

            # 添加优化信息
            optimized_request.metadata = {
                **(request.metadata or {}),
                'optimized': True,
                'original_token_count': self._estimate_token_count(original_content),
                'optimized_token_count': self._estimate_token_count(optimized_content),
                'saved_tokens': max(0, saved_tokens),
                'optimization_strategy': self.strategy.value
            }

            logger.debug(f"优化请求: 保存 {max(0, saved_tokens)} tokens (策略: {self.strategy.value})")
            return optimized_request

    def suggest_best_provider(self, request: AIRequest) -> str:
        """建议最佳提供商"""
        with self._lock:
            # 获取提供商效率排名
            provider_rankings = self.token_manager.get_provider_efficiency_ranking()

            if not provider_rankings:
                # 如果没有历史数据，使用默认提供商
                return "openai"  # 或者根据任务类型选择

            # 根据任务类型和内容特征选择最佳提供商
            task_type = request.task_type
            content_length = len(request.content)
            estimated_tokens = self._estimate_token_count(request.content)

            # 权重计算
            best_provider = None
            best_score = 0

            for provider, efficiency in provider_rankings:
                score = efficiency  # 基础效率分数

                # 根据任务类型调整权重
                if task_type == AITaskType.TEXT_GENERATION:
                    # 文本生成任务更注重效率
                    score *= 1.2
                elif task_type == AITaskType.CONTENT_ANALYSIS:
                    # 内容分析任务更注重准确性
                    score *= 0.9
                elif task_type == AITaskType.SCENE_ANALYSIS:
                    # 场景分析可能需要特定能力
                    score *= 1.0

                # 考虑请求大小
                if estimated_tokens > 1000:  # 大请求
                    score *= 1.1  # 效率更重要
                elif estimated_tokens < 100:  # 小请求
                    score *= 0.95  # 准确性更重要

                if score > best_score:
                    best_score = score
                    best_provider = provider

            logger.debug(f"为任务类型 {task_type.value} 选择提供商: {best_provider} (分数: {best_score:.2f})")
            return best_provider or provider_rankings[0][0]

    def batch_optimize_requests(self, requests: List[AIRequest]) -> List[AIRequest]:
        """批量优化请求"""
        optimized_requests = []

        for request in requests:
            try:
                optimized_request = self.optimize_request_tokens(request)
                optimized_requests.append(optimized_request)
            except Exception as e:
                logger.warning(f"优化请求失败: {e}")
                optimized_requests.append(request)  # 使用原始请求

        # 批量优化后，可能需要重新分配提供商
        if len(optimized_requests) > 1:
            optimized_requests = self._rebalance_providers(optimized_requests)

        return optimized_requests

    def calculate_token_savings(self, original: AIRequest, optimized: AIRequest) -> int:
        """计算令牌节省"""
        original_tokens = self._estimate_token_count(original.content)
        optimized_tokens = self._estimate_token_count(optimized.content)
        return original_tokens - optimized_tokens

    def _optimize_text(self, text: str) -> str:
        """优化文本内容"""
        optimized_text = text

        for rule in self.optimization_rules:
            # 根据策略选择规则
            if self._should_apply_rule(rule):
                try:
                    old_length = len(optimized_text)
                    optimized_text = re.sub(rule.pattern, rule.replacement, optimized_text)
                    new_length = len(optimized_text)

                    if old_length != new_length:
                        self.optimization_stats['rule_usage'][rule.name] += 1
                        logger.debug(f"应用优化规则 '{rule.name}': {old_length} -> {new_length} 字符")

                except Exception as e:
                    logger.warning(f"应用优化规则 '{rule.name}' 失败: {e}")

        return optimized_text

    def _should_apply_rule(self, rule: OptimizationRule) -> bool:
        """判断是否应该应用优化规则"""
        if self.strategy == OptimizationStrategy.AGGRESSIVE:
            return rule.risk_level in ["low", "medium", "high"]
        elif self.strategy == OptimizationStrategy.BALANCED:
            return rule.risk_level in ["low", "medium"]
        elif self.strategy == OptimizationStrategy.CONSERVATIVE:
            return rule.risk_level == "low"
        return False

    def _aggressive_optimize(self, text: str) -> str:
        """激进优化"""
        # 移除不必要的修饰词
        text = re.sub(r'(非常|特别|极其|相当)', '', text)
        # 压缩长句
        text = re.sub(r'，\s*，', '，', text)
        # 移除重复的形容词
        text = re.sub(r'(\b\w+\b)\s+\1', r'\1', text)

        return text

    def _conservative_optimize(self, text: str) -> str:
        """保守优化"""
        # 只进行非常安全的优化
        text = re.sub(r'\s+', ' ', text)  # 压缩空格
        text = re.sub(r'\n\s*\n', '\n', text)  # 移除空行

        return text

    def _estimate_token_count(self, text: str) -> int:
        """估算令牌数量"""
        # 简单估算：通常1个token约等于0.75个英文单词或1.5个中文字符
        if not text:
            return 0

        # 中文字符统计
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 英文单词统计
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        # 标点符号统计
        punctuation = len(re.findall(r'[^\w\s]', text))

        # 估算公式
        estimated_tokens = int(chinese_chars * 0.6 + english_words * 0.75 + punctuation * 0.25)
        return max(1, estimated_tokens)

    def _rebalance_providers(self, requests: List[AIRequest]) -> List[AIRequest]:
        """重新平衡提供商分配"""
        provider_counts = Counter()

        # 统计当前提供商分配
        for request in requests:
            if request.provider:
                provider_counts[request.provider] += 1

        # 如果只有一个提供商或分布已平衡，直接返回
        if len(provider_counts) <= 1:
            return requests

        # 获取推荐的提供商
        recommended_providers = [p[0] for p in self.token_manager.get_provider_efficiency_ranking()]

        # 重新分配一些请求到更高效的提供商
        rebalanced_requests = []
        for request in requests:
            # 如果当前提供商不是最高效的，且该提供商已有较多请求
            if (request.provider and
                len(recommended_providers) > 1 and
                recommended_providers[0] != request.provider and
                provider_counts[request.provider] > len(requests) // len(provider_counts)):

                # 考虑重新分配到更高效的提供商
                new_provider = recommended_providers[0]
                if new_provider:
                    request.provider = new_provider
                    provider_counts[request.provider] -= 1
                    provider_counts[new_provider] += 1

            rebalanced_requests.append(request)

        return rebalanced_requests

    def set_optimization_strategy(self, strategy: OptimizationStrategy):
        """设置优化策略"""
        self.strategy = strategy
        logger.info(f"设置优化策略: {strategy.value}")

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            **self.optimization_stats,
            'strategy': self.strategy.value,
            'available_rules': len(self.optimization_rules),
            'rule_usage': dict(self.optimization_stats['rule_usage'])
        }

    def add_custom_rule(self, rule: OptimizationRule):
        """添加自定义优化规则"""
        self.optimization_rules.append(rule)
        logger.info(f"添加自定义优化规则: {rule.name}")

    def remove_rule(self, rule_name: str):
        """移除优化规则"""
        self.optimization_rules = [r for r in self.optimization_rules if r.name != rule_name]
        logger.info(f"移除优化规则: {rule_name}")

    def analyze_text_patterns(self, text: str) -> Dict[str, Any]:
        """分析文本模式，提供优化建议"""
        patterns = {
            'whitespace_ratio': len(re.findall(r'\s+', text)) / max(len(text), 1),
            'duplicate_words': len(re.findall(r'(\b\w+\b)\s+\1', text)),
            'long_sentences': len([s for s in text.split('.') if len(s.split()) > 30]),
            'redundant_phrases': len(re.findall(r'(也就是说|换句话说|即)', text)),
            'politeness_markers': len(re.findall(r'(请|麻烦你|谢谢你)', text)),
            'repeated_punctuation': len(re.findall(r'[.]{2,}', text))
        }

        suggestions = []
        if patterns['whitespace_ratio'] > 0.2:
            suggestions.append("空格比例较高，建议压缩空白字符")
        if patterns['duplicate_words'] > 5:
            suggestions.append("发现重复词汇，建议合并")
        if patterns['long_sentences'] > 3:
            suggestions.append("长句较多，建议拆分或简化")
        if patterns['redundant_phrases'] > 2:
            suggestions.append("存在冗余表达，建议精简")
        if patterns['repeated_punctuation'] > 2:
            suggestions.append("标点符号重复，建议清理")

        return {
            'patterns': patterns,
            'suggestions': suggestions,
            'optimization_potential': self._estimate_optimization_potential(patterns)
        }

    def _estimate_optimization_potential(self, patterns: Dict[str, float]) -> int:
        """估算优化潜力"""
        potential = 0
        potential += patterns['whitespace_ratio'] * 50
        potential += patterns['duplicate_words'] * 10
        potential += patterns['long_sentences'] * 20
        potential += patterns['redundant_phrases'] * 15
        potential += patterns['repeated_punctuation'] * 5

        return int(potential)