#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一AI服务接口定义
定义标准化的AI请求-响应流程和数据模型
"""

import time
import uuid
from abc import abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AITaskType(Enum):
    """AI任务类型"""
    TEXT_GENERATION = "text_generation"
    CONTENT_ANALYSIS = "content_analysis"
    COMMENTARY_GENERATION = "commentary_generation"
    MONOLOGUE_GENERATION = "monologue_generation"
    SCENE_ANALYSIS = "scene_analysis"
    SUBTITLE_GENERATION = "subtitle_generation"
    VIDEO_EDITING_SUGGESTION = "video_editing_suggestion"
    CONTENT_CLASSIFICATION = "content_classification"


class AIPriority(Enum):
    """AI任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class AIRequestStatus(Enum):
    """AI请求状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AIRequest:
    """AI请求数据模型"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: AITaskType = AITaskType.TEXT_GENERATION
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    provider: Optional[str] = None
    priority: AIPriority = AIPriority.NORMAL
    timeout: float = 30.0
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    status: AIRequestStatus = AIRequestStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """AI响应数据模型"""
    request_id: str
    success: bool
    content: str = ""
    error_message: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    processing_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    cost: float = 0.0
    status: AIRequestStatus = AIRequestStatus.COMPLETED


@dataclass
class StreamingChunk:
    """流式响应数据块"""
    request_id: str
    chunk_id: str
    content: str
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)




@dataclass
class AIModelHealth:
    """AI模型健康状态"""
    provider: str
    is_healthy: bool = True
    response_time: float = 0.0
    error_rate: float = 0.0
    success_count: int = 0
    total_requests: int = 0
    consecutive_failures: int = 0
    health_score: float = 1.0
    last_used: float = 0.0
    capabilities: List[str] = field(default_factory=list)


@dataclass
class TokenUsage:
    """令牌使用详情"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    estimated_tokens: int = 0

    def __add__(self, other):
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            estimated_tokens=self.estimated_tokens + other.estimated_tokens
        )


@dataclass
class TokenBudget:
    """令牌预算"""
    total_tokens: int
    used_tokens: int = 0
    reserved_tokens: int = 0
    period: str = "monthly"  # daily, weekly, monthly, yearly
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    alerts_enabled: bool = True
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.9, 1.0])


@dataclass
class TokenReservation:
    """令牌预留"""
    reservation_id: str
    tokens: int
    purpose: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    provider: Optional[str] = None
    priority: int = 0  # 0=低, 1=中, 2=高


@dataclass
class AIUsageStats:
    """AI使用统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    requests_by_provider: Dict[str, int] = field(default_factory=dict)
    cost_by_provider: Dict[str, float] = field(default_factory=dict)
    tokens_by_provider: Dict[str, int] = field(default_factory=dict)

    # 新增令牌管理字段
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    cached_tokens: int = 0
    reserved_tokens: int = 0
    cost_efficiency: float = 0.0  # 成本效率指标


class IAIService:
    """AI服务抽象接口"""
    
    @abstractmethod
    async def process_request(self, request: AIRequest) -> AIResponse:
        """处理AI请求"""
        pass
    
    @abstractmethod
    def submit_request(self, request: AIRequest) -> str:
        """提交AI请求（异步）"""
        pass
    
    @abstractmethod
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """获取请求状态"""
        pass
    
    @abstractmethod
    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, AIModelHealth]:
        """获取健康状态"""
        pass
    
    @abstractmethod
    def get_usage_stats(self) -> AIUsageStats:
        """获取使用统计"""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> List[str]:
        """获取可用提供商列表"""
        pass
    
    @abstractmethod
    def set_budget_limit(self, limit: float) -> None:
        """设置预算限制"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """清理资源"""
        pass


class IStreamingAIService(IAIService):
    """流式AI服务接口"""

    @abstractmethod
    async def stream_request(self, request: AIRequest) -> Any:
        """流式处理AI请求"""
        pass

    @abstractmethod
    def submit_streaming_request(self, request: AIRequest) -> str:
        """提交流式AI请求"""
        pass


class IAIModelProvider:
    """AI模型提供商接口"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化提供商"""
        pass
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本"""
        pass
    
    @abstractmethod
    async def analyze_content(self, content: str, **kwargs) -> AIResponse:
        """分析内容"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass


class IAILoadBalancer:
    """AI负载均衡器接口"""
    
    @abstractmethod
    async def select_provider(self, request: AIRequest) -> Optional[str]:
        """选择最佳提供商"""
        pass
    
    @abstractmethod
    def update_provider_metrics(self, provider: str, success: bool, 
                               response_time: float, cost: float) -> None:
        """更新提供商指标"""
        pass
    
    @abstractmethod
    def get_provider_recommendations(self, task_type: AITaskType) -> List[str]:
        """获取提供商推荐"""
        pass


class IAICostManager:
    """AI成本管理器接口"""

    @abstractmethod
    def calculate_cost(self, provider: str, usage: Dict[str, Any]) -> float:
        """计算成本"""
        pass

    @abstractmethod
    def record_usage(self, provider: str, usage: Dict[str, Any], cost: float) -> None:
        """记录使用情况"""
        pass

    @abstractmethod
    def get_budget_status(self) -> Dict[str, Any]:
        """获取预算状态"""
        pass

    @abstractmethod
    def check_budget_limit(self, estimated_cost: float) -> bool:
        """检查预算限制"""
        pass

    @abstractmethod
    def get_cost_breakdown(self, period: str = "today") -> Dict[str, Any]:
        """获取成本分解"""
        pass

    @abstractmethod
    def set_budget_alert(self, threshold: float, callback: Callable) -> None:
        """设置预算预警"""
        pass


class IAIEventHandler:
    """AI事件处理器接口"""

    @abstractmethod
    def on_request_started(self, request: AIRequest) -> None:
        """请求开始事件"""
        pass

    @abstractmethod
    def on_request_completed(self, request: AIRequest, response: AIResponse) -> None:
        """请求完成事件"""
        pass

    @abstractmethod
    def on_request_failed(self, request: AIRequest, error: str) -> None:
        """请求失败事件"""
        pass

    @abstractmethod
    def on_streaming_chunk(self, chunk: StreamingChunk) -> None:
        """流式数据块事件"""
        pass

    @abstractmethod
    def on_provider_health_changed(self, provider: str, health: AIModelHealth) -> None:
        """提供商健康状态变化事件"""
        pass


@dataclass
class AIServiceConfig:
    """AI服务配置"""
    max_concurrent_requests: int = 5
    request_timeout: float = 300.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_streaming: bool = True
    cost_budget: float = 100.0
    health_check_interval: float = 60.0
    enable_metrics: bool = True
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_ttl: float = 3600.0


class IAIModelCache:
    """AI模型缓存接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float = 3600.0) -> bool:
        """设置缓存"""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """失效缓存"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        pass


# 便利函数
def create_ai_request(task_type: AITaskType, content: str, 
                     provider: str = None, priority: AIPriority = AIPriority.NORMAL,
                     **kwargs) -> AIRequest:
    """创建AI请求"""
    return AIRequest(
        task_type=task_type,
        content=content,
        provider=provider,
        priority=priority,
        parameters=kwargs
    )


def create_text_generation_request(prompt: str, provider: str = None, **kwargs) -> AIRequest:
    """创建文本生成请求"""
    return create_ai_request(
        task_type=AITaskType.TEXT_GENERATION,
        content=prompt,
        provider=provider,
        **kwargs
    )


def create_content_analysis_request(content: str, provider: str = None, **kwargs) -> AIRequest:
    """创建内容分析请求"""
    return create_ai_request(
        task_type=AITaskType.CONTENT_ANALYSIS,
        content=content,
        provider=provider,
        **kwargs
    )


def create_commentary_request(video_info: Dict[str, Any], style: str = "专业解说", 
                            provider: str = None, **kwargs) -> AIRequest:
    """创建解说生成请求"""
    return create_ai_request(
        task_type=AITaskType.COMMENTARY_GENERATION,
        content=f"为视频生成{style}的解说",
        provider=provider,
        context={"video_info": video_info, "style": style},
        **kwargs
    )


def create_monologue_request(video_info: Dict[str, Any], character: str = "主角",
                           emotion: str = "平静", provider: str = None, **kwargs) -> AIRequest:
    """创建独白生成请求"""
    return create_ai_request(
        task_type=AITaskType.MONOLOGUE_GENERATION,
        content=f"为{character}生成{emotion}的独白",
        provider=provider,
        context={"video_info": video_info, "character": character, "emotion": emotion},
        **kwargs
    )


def create_subtitle_generation_request(video_info: Dict[str, Any], language: str = "中文",
                                     provider: str = None, **kwargs) -> AIRequest:
    """创建字幕生成请求"""
    return create_ai_request(
        task_type=AITaskType.SUBTITLE_GENERATION,
        content=f"为视频生成{language}字幕",
        provider=provider,
        context={"video_info": video_info, "language": language},
        **kwargs
    )


def create_scene_analysis_request(video_info: Dict[str, Any], analysis_type: str = "场景检测",
                                provider: str = None, **kwargs) -> AIRequest:
    """创建场景分析请求"""
    return create_ai_request(
        task_type=AITaskType.SCENE_ANALYSIS,
        content=f"对视频进行{analysis_type}",
        provider=provider,
        context={"video_info": video_info, "analysis_type": analysis_type},
        **kwargs
    )


class ITokenManager:
    """统一令牌管理接口"""

    @abstractmethod
    def create_budget(self, name: str, total_tokens: int, period: str = "monthly") -> TokenBudget:
        """创建令牌预算"""
        pass

    @abstractmethod
    def check_token_availability(self, estimated_tokens: int, provider: str = None) -> bool:
        """检查令牌可用性"""
        pass

    @abstractmethod
    def reserve_tokens(self, tokens: int, purpose: str, provider: str = None,
                      priority: int = 0, expires_in: int = 3600) -> TokenReservation:
        """预留令牌"""
        pass

    @abstractmethod
    def release_reservation(self, reservation_id: str) -> bool:
        """释放令牌预留"""
        pass

    @abstractmethod
    def consume_tokens(self, provider: str, token_usage: TokenUsage, cost: float = 0.0) -> None:
        """消费令牌"""
        pass

    @abstractmethod
    def get_token_budget_status(self) -> Dict[str, Any]:
        """获取令牌预算状态"""
        pass

    @abstractmethod
    def set_token_alert(self, threshold: float, callback: Callable) -> None:
        """设置令牌预警"""
        pass

    @abstractmethod
    def get_token_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取令牌优化建议"""
        pass

    @abstractmethod
    def get_provider_efficiency_ranking(self) -> List[Tuple[str, float]]:
        """获取提供商效率排名"""
        pass

    @abstractmethod
    def cache_tokens(self, key: str, tokens: List[str], ttl: float = 3600.0) -> bool:
        """缓存令牌结果"""
        pass

    @abstractmethod
    def get_cached_tokens(self, key: str) -> Optional[List[str]]:
        """获取缓存的令牌结果"""
        pass


class ITokenOptimizer:
    """令牌优化器接口"""

    @abstractmethod
    def optimize_request_tokens(self, request: AIRequest) -> AIRequest:
        """优化请求令牌"""
        pass

    @abstractmethod
    def suggest_best_provider(self, request: AIRequest) -> str:
        """建议最佳提供商"""
        pass

    @abstractmethod
    def batch_optimize_requests(self, requests: List[AIRequest]) -> List[AIRequest]:
        """批量优化请求"""
        pass

    @abstractmethod
    def calculate_token_savings(self, original: AIRequest, optimized: AIRequest) -> int:
        """计算令牌节省"""
        pass
