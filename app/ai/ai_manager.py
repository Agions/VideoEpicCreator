#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一AI管理器 - CineAIStudio AI功能统一管理系统
集成所有AI功能，包括模型管理、负载均衡、成本控制、内容审核等
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Type, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import PriorityQueue, Queue
import aiohttp
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from .models.base_model import BaseAIModel, AIModelConfig, AIResponse
from .models.qianwen_model import QianwenModel
from .models.wenxin_model import WenxinModel
from .models.zhipu_model import ZhipuModel
from .models.xunfei_model import XunfeiModel
from .models.hunyuan_model import HunyuanModel
from .models.deepseek_model import DeepSeekModel
from .optimized_ai_manager import OptimizedAIManager
# 成本管理器类（内联实现）
class ChineseLLMCostManager:
    """中文大模型成本管理器"""
    def __init__(self):
        self.budget_limit = 1000.0
        self.current_cost = 0.0
        
    def calculate_cost(self, provider: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算成本"""
        # 简化的成本计算
        rates = {
            'qianwen': 0.001,
            'wenxin': 0.002,
            'zhipu': 0.0015,
            'xunfei': 0.001,
            'hunyuan': 0.001,
            'deepseek': 0.001
        }
        rate = rates.get(provider, 0.001)
        return (prompt_tokens + completion_tokens) * rate
        
    def set_budget_limit(self, limit: float):
        """设置预算限制"""
        self.budget_limit = limit

class CostTier:
    """成本等级"""
    pass

# 负载均衡器类（内联实现）
class ChineseLLMLoadBalancer:
    """中文大模型负载均衡器"""
    def __init__(self, ai_manager, cost_manager):
        self.ai_manager = ai_manager
        self.cost_manager = cost_manager
        
    async def get_best_model(self, prompt: str, task_type: str):
        """获取最佳模型"""
        # 简化的负载均衡逻辑
        available_models = self.ai_manager.get_available_models()
        if available_models:
            return available_models[0], self.ai_manager.models[available_models[0]]
        return None, None
        
    def set_strategy(self, strategy):
        """设置策略"""
        pass

class LoadBalancingStrategy:
    """负载均衡策略"""
    pass

# 内容审核器类（内联实现）
class ChineseContentModerator:
    """中文内容审核器"""
    def filter_response(self, response):
        """过滤响应"""
        return response

class ModerationAction:
    """审核动作"""
    pass
from app.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


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


@dataclass
class AITask:
    """AI任务"""
    task_id: str
    task_type: AITaskType
    prompt: str
    provider: Optional[str] = None
    priority: AIPriority = AIPriority.NORMAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class AIModelStatus:
    """AI模型状态"""
    provider: str
    model: str
    is_healthy: bool
    response_time: float
    error_rate: float
    success_count: int
    total_requests: int
    last_used: float
    consecutive_failures: int
    health_score: float = 1.0


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


class AIManager(QObject):
    """统一AI管理器"""
    
    # 信号定义
    task_completed = pyqtSignal(str, AIResponse)  # 任务ID, 响应结果
    task_failed = pyqtSignal(str, str)  # 任务ID, 错误信息
    task_progress = pyqtSignal(str, float)  # 任务ID, 进度
    model_health_updated = pyqtSignal(dict)  # 模型健康状态更新
    usage_stats_updated = pyqtSignal(dict)  # 使用统计更新
    cost_alert = pyqtSignal(str, float)  # 成本告警
    content_moderation_result = pyqtSignal(str, dict)  # 内容审核结果
    
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        
        self.settings_manager = settings_manager
        
        # 核心组件
        self.cost_manager = ChineseLLMCostManager()
        self.load_balancer = None  # 延迟初始化
        self.content_moderator = ChineseContentModerator()
        
        # 模型管理
        self.models: Dict[str, BaseAIModel] = {}
        self.model_classes: Dict[str, Type[BaseAIModel]] = {
            "qianwen": QianwenModel,
            "wenxin": WenxinModel,
            "zhipu": ZhipuModel,
            "xunfei": XunfeiModel,
            "hunyuan": HunyuanModel,
            "deepseek": DeepSeekModel
        }
        
        # 任务管理
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, AITask] = {}
        self.task_results: Dict[str, AIResponse] = {}
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 统计信息
        self.usage_stats = AIUsageStats()
        self.model_status: Dict[str, AIModelStatus] = {}
        
        # 配置
        self.max_concurrent_tasks = 10
        self.default_timeout = 30.0
        self.cost_budget = 1000.0  # 月度预算
        self.enable_content_moderation = True
        self.enable_cost_optimization = True
        
        # 定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_usage_stats)
        self.stats_timer.start(60000)  # 每分钟更新统计
        
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self._health_check)
        self.health_check_timer.start(300000)  # 每5分钟健康检查
        
        # 初始化
        self._initialize_models()
        self._start_task_processor()
        
        logger.info("统一AI管理器初始化完成")
    
    def _initialize_models(self):
        """初始化所有配置的模型"""
        try:
            ai_config = self.settings_manager.get_setting("ai_models", {})
            
            for provider, config in ai_config.items():
                if provider in self.model_classes and config.get("enabled", False):
                    self._create_model(provider, config)
            
            # 初始化负载均衡器
            self.load_balancer = ChineseLLMLoadBalancer(self, self.cost_manager)
            
            logger.info(f"初始化了 {len(self.models)} 个AI模型")
            
        except Exception as e:
            logger.error(f"初始化AI模型失败: {e}")
    
    def _create_model(self, provider: str, config: Dict[str, Any]):
        """创建AI模型实例"""
        try:
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
            
            model_class = self.model_classes[provider]
            model = model_class(model_config)
            
            self.models[provider] = model
            
            # 初始化模型状态
            self.model_status[provider] = AIModelStatus(
                provider=provider,
                model=model_config.name,
                is_healthy=False,
                response_time=0.0,
                error_rate=0.0,
                success_count=0,
                total_requests=0,
                last_used=0.0,
                consecutive_failures=0
            )
            
            # 异步初始化模型
            asyncio.create_task(self._initialize_model_async(provider, model))
            
        except Exception as e:
            logger.error(f"创建模型 {provider} 失败: {e}")
    
    async def _initialize_model_async(self, provider: str, model: BaseAIModel):
        """异步初始化模型"""
        try:
            success = await model.initialize()
            
            if success:
                self.model_status[provider].is_healthy = True
                logger.info(f"模型 {provider} 初始化成功")
            else:
                self.model_status[provider].is_healthy = False
                logger.warning(f"模型 {provider} 初始化失败")
                
            self.model_health_updated.emit(self.get_model_status())
            
        except Exception as e:
            logger.error(f"初始化模型 {provider} 失败: {e}")
            self.model_status[provider].is_healthy = False
    
    def _start_task_processor(self):
        """启动任务处理器"""
        def process_tasks():
            while True:
                try:
                    if len(self.active_tasks) < self.max_concurrent_tasks:
                        priority, task = self.task_queue.get()
                        
                        if task.timeout > 0 and time.time() - task.created_at > task.timeout:
                            self.task_failed.emit(task.task_id, "任务超时")
                            continue
                        
                        self.active_tasks[task.task_id] = task
                        
                        # 在线程池中执行任务
                        future = self.thread_pool.submit(self._execute_task, task)
                        future.add_done_callback(lambda f: self._task_completed(task.task_id, f))
                        
                    else:
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"处理任务时出错: {e}")
                    time.sleep(1)
        
        processor_thread = threading.Thread(target=process_tasks, daemon=True)
        processor_thread.start()
    
    def _execute_task(self, task: AITask) -> AIResponse:
        """执行AI任务"""
        start_time = time.time()
        
        try:
            # 选择最佳模型
            if task.provider:
                model = self.models.get(task.provider)
                if not model or not model.is_available():
                    raise Exception(f"指定的模型 {task.provider} 不可用")
            else:
                # 使用负载均衡器选择最佳模型
                if self.load_balancer:
                    # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
                    # model_name, model = asyncio.run(
                    #     self.load_balancer.get_best_model(task.prompt, task.task_type.value)
                    # )
                    # 临时同步实现
                    model_name, model = list(self.models.items())[0]
                    task.provider = model_name
                else:
                    # 回退到第一个可用模型
                    available_models = [m for m in self.models.values() if m.is_available()]
                    if not available_models:
                        raise Exception("没有可用的AI模型")
                    model = available_models[0]
            
            # 执行任务
            if task.task_type == AITaskType.TEXT_GENERATION:
                # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
                # response = asyncio.run(model.generate_text(task.prompt, **task.parameters))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.CONTENT_ANALYSIS:
                # response = asyncio.run(model.analyze_content(task.prompt, **task.parameters))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.COMMENTARY_GENERATION:
                # response = asyncio.run(model.generate_commentary(task.parameters.get("video_info", {}), task.parameters.get("style", "幽默风趣")))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.MONOLOGUE_GENERATION:
                # response = asyncio.run(model.generate_monologue(task.parameters.get("video_info", {}), task.parameters.get("character", "主角"), task.parameters.get("emotion", "平静")))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            else:
                # 默认使用文本生成
                # response = asyncio.run(model.generate_text(task.prompt, **task.parameters))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            
            # 更新统计信息
            response_time = time.time() - start_time
            self._update_model_stats(task.provider, response, response_time, True)
            
            # 内容审核
            if self.enable_content_moderation and response.success:
                response = self.content_moderator.filter_response(response)
                
                # 发送审核结果信号
                moderation_result = {
                    "task_id": task.task_id,
                    "action": response.metadata.get("moderation_status", "allowed"),
                    "risk_score": response.metadata.get("moderation_score", 0.0),
                    "categories": response.metadata.get("moderation_categories", [])
                }
                self.content_moderation_result.emit(task.task_id, moderation_result)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            error_response = AIResponse(
                success=False,
                error_message=str(e)
            )
            
            if task.provider:
                self._update_model_stats(task.provider, error_response, response_time, False)
            
            return error_response
    
    def _task_completed(self, task_id: str, future):
        """任务完成处理"""
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                
                try:
                    response = future.result()
                    
                    if response.success:
                        self.task_completed.emit(task_id, response)
                        
                        # 执行回调
                        if task.callback:
                            task.callback(response)
                    else:
                        # 重试逻辑
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            task.created_at = time.time()  # 重置时间
                            self.task_queue.put((task.priority.value, task))
                            logger.info(f"任务 {task_id} 重试第 {task.retry_count} 次")
                        else:
                            self.task_failed.emit(task_id, response.error_message)
                    
                    self.task_results[task_id] = response
                    
                except Exception as e:
                    self.task_failed.emit(task_id, f"任务执行异常: {str(e)}")
                    
        except Exception as e:
            logger.error(f"处理任务完成时出错: {e}")
    
    def _update_model_stats(self, provider: str, response: AIResponse, response_time: float, success: bool):
        """更新模型统计信息"""
        if provider not in self.model_status:
            return
        
        status = self.model_status[provider]
        status.total_requests += 1
        status.last_used = time.time()
        
        if success:
            status.success_count += 1
            status.consecutive_failures = 0
            status.response_time = (status.response_time * 0.9) + (response_time * 0.1)
            status.health_score = min(1.0, status.health_score + 0.05)
        else:
            status.consecutive_failures += 1
            status.health_score = max(0.0, status.health_score - 0.1)
        
        status.error_rate = (status.total_requests - status.success_count) / status.total_requests
        
        # 更新使用统计
        self.usage_stats.total_requests += 1
        
        if success:
            self.usage_stats.successful_requests += 1
            
            # 更新token统计
            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                self.usage_stats.total_tokens += tokens
                self.usage_stats.tokens_by_provider[provider] = self.usage_stats.tokens_by_provider.get(provider, 0) + tokens
                
                # 更新成本统计
                if response.usage.get("prompt_tokens") and response.usage.get("completion_tokens"):
                    cost = self.cost_manager.calculate_cost(
                        provider,
                        response.usage["prompt_tokens"],
                        response.usage["completion_tokens"]
                    )
                    self.usage_stats.total_cost += cost
                    self.usage_stats.cost_by_provider[provider] = self.usage_stats.cost_by_provider.get(provider, 0.0) + cost
                    
                    # 检查成本告警
                    if self.usage_stats.total_cost > self.cost_budget * 0.8:
                        self.cost_alert.emit("成本告警", self.usage_stats.total_cost)
        else:
            self.usage_stats.failed_requests += 1
        
        self.usage_stats.requests_by_provider[provider] = self.usage_stats.requests_by_provider.get(provider, 0) + 1
        
        # 更新平均响应时间
        if self.usage_stats.total_requests > 0:
            total_time = self.usage_stats.average_response_time * (self.usage_stats.total_requests - 1) + response_time
            self.usage_stats.average_response_time = total_time / self.usage_stats.total_requests
    
    def _update_usage_stats(self):
        """更新使用统计"""
        stats_data = {
            "total_requests": self.usage_stats.total_requests,
            "successful_requests": self.usage_stats.successful_requests,
            "failed_requests": self.usage_stats.failed_requests,
            "total_tokens": self.usage_stats.total_tokens,
            "total_cost": self.usage_stats.total_cost,
            "average_response_time": self.usage_stats.average_response_time,
            "requests_by_provider": self.usage_stats.requests_by_provider,
            "cost_by_provider": self.usage_stats.cost_by_provider,
            "tokens_by_provider": self.usage_stats.tokens_by_provider,
            "success_rate": self.usage_stats.successful_requests / max(self.usage_stats.total_requests, 1)
        }
        
        self.usage_stats_updated.emit(stats_data)
    
    def _health_check(self):
        """健康检查"""
        for provider, model in self.models.items():
            try:
                start_time = time.time()
                # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
                # response = asyncio.run(model.generate_text("你好", max_tokens=10))
                response = AIResponse(success=False, error_message="功能已迁移到新的AIService")
                response_time = time.time() - start_time
                
                if response.success:
                    self._update_model_stats(provider, response, response_time, True)
                else:
                    self._update_model_stats(provider, response, response_time, False)
                    
            except Exception as e:
                logger.error(f"健康检查 {provider} 失败: {e}")
                self._update_model_stats(provider, AIResponse(success=False, error_message=str(e)), 30.0, False)
        
        self.model_health_updated.emit(self.get_model_status())
    
    # 公共接口
    def generate_text(self, prompt: str, provider: str = None, **kwargs) -> str:
        """生成文本（同步接口）"""
        task_id = f"text_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.TEXT_GENERATION,
            prompt=prompt,
            provider=provider,
            parameters=kwargs
        )
        
        return self._execute_task_sync(task)
    
    def generate_text_async(self, prompt: str, provider: str = None, callback: Callable = None, **kwargs) -> str:
        """生成文本（异步接口）"""
        task_id = f"text_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.TEXT_GENERATION,
            prompt=prompt,
            provider=provider,
            callback=callback,
            parameters=kwargs
        )
        
        self.task_queue.put((task.priority.value, task))
        return task_id
    
    def analyze_content(self, content: str, analysis_type: str = "general", provider: str = None) -> AIResponse:
        """分析内容"""
        task_id = f"analysis_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.CONTENT_ANALYSIS,
            prompt=content,
            provider=provider,
            parameters={"analysis_type": analysis_type}
        )
        
        return self._execute_task_sync(task)
    
    def generate_commentary(self, video_info: Dict[str, Any], style: str = "幽默风趣", provider: str = None) -> AIResponse:
        """生成视频解说"""
        task_id = f"commentary_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.COMMENTARY_GENERATION,
            prompt=f"为视频生成{style}的解说",
            provider=provider,
            parameters={"video_info": video_info, "style": style}
        )
        
        return self._execute_task_sync(task)
    
    def generate_monologue(self, video_info: Dict[str, Any], character: str = "主角", emotion: str = "平静", provider: str = None) -> AIResponse:
        """生成第一人称独白"""
        task_id = f"monologue_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.MONOLOGUE_GENERATION,
            prompt=f"为角色生成{emotion}的独白",
            provider=provider,
            parameters={"video_info": video_info, "character": character, "emotion": emotion}
        )
        
        return self._execute_task_sync(task)
    
    def generate_subtitle(self, video_content: str, language: str = "zh", provider: str = None) -> AIResponse:
        """生成字幕"""
        prompt = f"""
        请为以下视频内容生成{language}字幕：
        
        视频内容：
        {video_content}
        
        要求：
        1. 字幕要简洁明了
        2. 时间轴准确
        3. 语言通顺自然
        4. 符合视频节奏
        
        请生成字幕内容：
        """
        
        task_id = f"subtitle_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.SUBTITLE_GENERATION,
            prompt=prompt,
            provider=provider,
            parameters={"language": language}
        )
        
        return self._execute_task_sync(task)
    
    def analyze_video_scene(self, video_description: str, provider: str = None) -> AIResponse:
        """分析视频场景"""
        prompt = f"""
        请分析以下视频场景：
        
        视频描述：
        {video_description}
        
        请提供：
        1. 场景类型
        2. 视觉元素
        3. 情感基调
        4. 关键时刻
        5. 编辑建议
        
        请进行分析：
        """
        
        task_id = f"scene_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.SCENE_ANALYSIS,
            prompt=prompt,
            provider=provider
        )
        
        return self._execute_task_sync(task)
    
    def get_editing_suggestions(self, video_info: Dict[str, Any], provider: str = None) -> AIResponse:
        """获取视频编辑建议"""
        prompt = f"""
        请为以下视频提供编辑建议：
        
        视频信息：
        - 时长：{video_info.get('duration', '未知')}
        - 类型：{video_info.get('type', '未知')}
        - 内容：{video_info.get('content', '未知')}
        
        请提供：
        1. 节奏调整建议
        2. 转场效果建议
        3. 音效处理建议
        4. 色彩调整建议
        5. 整体优化建议
        
        请生成建议：
        """
        
        task_id = f"editing_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.VIDEO_EDITING_SUGGESTION,
            prompt=prompt,
            provider=provider,
            parameters={"video_info": video_info}
        )
        
        return self._execute_task_sync(task)
    
    def classify_content(self, content: str, provider: str = None) -> AIResponse:
        """内容分类"""
        prompt = f"""
        请对以下内容进行分类：
        
        内容：
        {content}
        
        请提供：
        1. 内容类型
        2. 目标受众
        3. 风格特征
        4. 适用平台
        5. 标签建议
        
        请进行分类：
        """
        
        task_id = f"classify_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.CONTENT_CLASSIFICATION,
            prompt=prompt,
            provider=provider
        )
        
        return self._execute_task_sync(task)
    
    def _execute_task_sync(self, task: AITask) -> AIResponse:
        """同步执行任务"""
        self.task_queue.put((task.priority.value, task))
        
        # 等待任务完成
        start_time = time.time()
        timeout = task.timeout or self.default_timeout
        
        while time.time() - start_time < timeout:
            if task.task_id in self.task_results:
                result = self.task_results.pop(task.task_id)
                return result
            
            time.sleep(0.1)
        
        # 超时处理
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        return AIResponse(
            success=False,
            error_message="任务执行超时"
        )
    
    def get_model_status(self) -> Dict[str, Any]:
        """获取模型状态"""
        return {
            provider: {
                "provider": status.provider,
                "model": status.model,
                "is_healthy": status.is_healthy,
                "response_time": status.response_time,
                "error_rate": status.error_rate,
                "success_count": status.success_count,
                "total_requests": status.total_requests,
                "health_score": status.health_score,
                "consecutive_failures": status.consecutive_failures
            }
            for provider, status in self.model_status.items()
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "total_requests": self.usage_stats.total_requests,
            "successful_requests": self.usage_stats.successful_requests,
            "failed_requests": self.usage_stats.failed_requests,
            "total_tokens": self.usage_stats.total_tokens,
            "total_cost": self.usage_stats.total_cost,
            "average_response_time": self.usage_stats.average_response_time,
            "requests_by_provider": self.usage_stats.requests_by_provider,
            "cost_by_provider": self.usage_stats.cost_by_provider,
            "tokens_by_provider": self.usage_stats.tokens_by_provider,
            "success_rate": self.usage_stats.successful_requests / max(self.usage_stats.total_requests, 1)
        }
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            provider for provider, model in self.models.items()
            if model.is_available() and self.model_status[provider].is_healthy
        ]
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        if self.load_balancer:
            self.load_balancer.set_strategy(strategy)
    
    def set_cost_budget(self, budget: float):
        """设置成本预算"""
        self.cost_budget = budget
        self.cost_manager.set_budget_limit(budget)
    
    def enable_content_moderation(self, enabled: bool):
        """启用/禁用内容审核"""
        self.enable_content_moderation = enabled
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "processing",
                "task_type": task.task_type.value,
                "provider": task.provider,
                "created_at": task.created_at,
                "retry_count": task.retry_count
            }
        elif task_id in self.task_results:
            return {
                "task_id": task_id,
                "status": "completed",
                "result": self.task_results[task_id]
            }
        else:
            return {
                "task_id": task_id,
                "status": "not_found"
            }
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理统一AI管理器资源")
        
        # 停止定时器
        self.stats_timer.stop()
        self.health_check_timer.stop()
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        # 关闭模型连接
        for model in self.models.values():
            if hasattr(model, 'close'):
                # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
                # asyncio.run(model.close())
                try:
                    # 尝试同步关闭
                    if hasattr(model, 'close_sync'):
                        model.close_sync()
                except Exception as e:
                    logger.warning(f"模型关闭失败: {e}")
        
        logger.info("统一AI管理器资源清理完成")


# 工厂函数
def create_ai_manager(settings_manager: SettingsManager) -> OptimizedAIManager:
    """创建AI管理器 - 使用优化版本"""
    return OptimizedAIManager(settings_manager)


# 为了向后兼容，保留原有的AIManager类，但推荐使用OptimizedAIManager
class AIManager(OptimizedAIManager):
    """向后兼容的AI管理器类"""
    
    def __init__(self, settings_manager):
        super().__init__(settings_manager)
        logging.info("使用向后兼容的AIManager（内部使用OptimizedAIManager）")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt6.QtWidgets import QApplication
    from app.config.settings_manager import SettingsManager
    
    app = QApplication(sys.argv)
    
    # 创建设置管理器
    settings_manager = SettingsManager()
    
    # 创建AI管理器
    ai_manager = create_ai_manager(settings_manager)
    
    # 测试文本生成
    try:
        result = ai_manager.generate_text("你好，请介绍一下人工智能")
        print(f"生成结果: {result.content}")
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 清理资源
    ai_manager.cleanup()
    
    sys.exit(app.exec())