#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重构的统一AI管理器
集成优化的模型管理、成本管理、负载均衡和内容生成系统
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Type, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import PriorityQueue, Queue

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .optimized_model_manager import OptimizedModelManager, ModelCapability, ModelRequest
from .optimized_cost_manager import OptimizedCostManager, CostRecord, BudgetInfo
from .intelligent_load_balancer import IntelligentLoadBalancer, LoadBalancingStrategy, RequestPriority
from .intelligent_content_generator import (
    IntelligentContentGenerator, ContentGenerationRequest, 
    ContentGenerationType, ContentGenerationResult
)
from .models.base_model import BaseAIModel, AIModelConfig, AIResponse
from .models.qianwen_model import QianwenModel
from .models.wenxin_model import WenxinModel
from .models.zhipu_model import ZhipuModel
from .models.xunfei_model import XunfeiModel
from .models.hunyuan_model import HunyuanModel
from .models.deepseek_model import DeepSeekModel

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


@dataclass
class AITask:
    """AI任务"""
    task_id: str
    task_type: AITaskType
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.NORMAL
    provider: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3


class EnhancedAIManager(QObject):
    """增强的AI管理器"""
    
    # 信号定义
    task_completed = pyqtSignal(str, object)  # 任务ID, 结果
    task_failed = pyqtSignal(str, str)  # 任务ID, 错误信息
    task_progress = pyqtSignal(str, float)  # 任务ID, 进度
    model_health_updated = pyqtSignal(dict)  # 模型健康状态更新
    usage_stats_updated = pyqtSignal(dict)  # 使用统计更新
    cost_alert = pyqtSignal(object)  # 成本警报
    content_generated = pyqtSignal(object)  # 内容生成完成
    performance_metrics_updated = pyqtSignal(dict)  # 性能指标更新
    
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        
        self.settings_manager = settings_manager
        
        # 核心组件
        self.model_classes = {
            "qianwen": QianwenModel,
            "wenxin": WenxinModel,
            "zhipu": ZhipuModel,
            "xunfei": XunfeiModel,
            "hunyuan": HunyuanModel,
            "deepseek": DeepSeekModel
        }
        
        # 初始化管理器
        self.model_manager = OptimizedModelManager(self.model_classes)
        self.cost_manager = OptimizedCostManager()
        self.load_balancer = IntelligentLoadBalancer(self.model_manager, self.cost_manager)
        self.content_generator = IntelligentContentGenerator(self.model_manager, self.cost_manager)
        
        # 任务管理
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, AITask] = {}
        self.task_results: Dict[str, Any] = {}
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
        
        # 配置
        self.max_concurrent_tasks = 20
        self.default_timeout = 30.0
        self.enable_caching = True
        self.enable_content_moderation = True
        
        # 性能监控
        self.performance_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_response_time": 0.0,
            "total_cost": 0.0
        }
        
        # 定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_usage_stats)
        self.stats_timer.start(60000)  # 每分钟更新统计
        
        # 初始化
        self._initialize_system()
        
        logger.info("增强的AI管理器初始化完成")
    
    def _initialize_system(self):
        """初始化系统"""
        try:
            # 加载配置
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
            asyncio.create_task(self._initialize_models_async(model_configs))
            
            # 启动任务处理器
            self._start_task_processor()
            
            # 设置预算
            budget_amount = self.settings_manager.get_setting("ai_budget.monthly_limit", 1000.0)
            if budget_amount > 0:
                self.cost_manager.create_budget("月度预算", budget_amount, 30)
            
            # 连接信号
            self._connect_signals()
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
    
    async def _initialize_models_async(self, model_configs: Dict[str, AIModelConfig]):
        """异步初始化模型"""
        try:
            await self.model_manager.initialize_models(model_configs)
            logger.info(f"成功初始化 {len(model_configs)} 个模型")
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
    
    def _connect_signals(self):
        """连接信号"""
        # 模型管理器信号
        self.model_manager.model_health_updated.connect(self.model_health_updated)
        self.model_manager.model_performance_updated.connect(self.performance_metrics_updated)
        
        # 成本管理器信号
        self.cost_manager.cost_updated.connect(self._on_cost_updated)
        self.cost_manager.budget_alert.connect(self.cost_alert)
        self.cost_manager.cost_analysis_ready.connect(self._on_cost_analysis_ready)
        
        # 内容生成器信号
        self.content_generator.content_generated.connect(self.content_generated)
    
    def _start_task_processor(self):
        """启动任务处理器"""
        def process_tasks():
            while True:
                try:
                    if len(self.active_tasks) < self.max_concurrent_tasks:
                        priority, task = self.task_queue.get()
                        
                        # 检查超时
                        if task.timeout > 0 and time.time() - task.created_at > task.timeout:
                            self.task_failed.emit(task.task_id, "任务超时")
                            continue
                        
                        self.active_tasks[task.task_id] = task
                        
                        # 在线程池中执行任务
                        future = self.thread_pool.submit(self._execute_task, task)
                        future.add_done_callback(lambda f: self._task_completed(task.task_id, f))
                        
                    else:
                        time.sleep(0.01)
                        
                except Exception as e:
                    logger.error(f"处理任务时出错: {e}")
                    time.sleep(1)
        
        processor_thread = threading.Thread(target=process_tasks, daemon=True)
        processor_thread.start()
    
    def _execute_task(self, task: AITask) -> Any:
        """执行AI任务"""
        start_time = time.time()
        
        try:
            # 根据任务类型执行
            if task.task_type == AITaskType.TEXT_GENERATION:
                # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
                # result = asyncio.run(self._execute_text_generation(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.CONTENT_ANALYSIS:
                # result = asyncio.run(self._execute_content_analysis(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.COMMENTARY_GENERATION:
                # result = asyncio.run(self._execute_commentary_generation(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.MONOLOGUE_GENERATION:
                # result = asyncio.run(self._execute_monologue_generation(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.SCENE_ANALYSIS:
                # result = asyncio.run(self._execute_scene_analysis(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.SUBTITLE_GENERATION:
                # result = asyncio.run(self._execute_subtitle_generation(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.VIDEO_EDITING_SUGGESTION:
                # result = asyncio.run(self._execute_editing_suggestion(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            elif task.task_type == AITaskType.CONTENT_CLASSIFICATION:
                # result = asyncio.run(self._execute_content_classification(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            else:
                # result = asyncio.run(self._execute_text_generation(task))
                result = AIResponse(success=False, error_message="功能已迁移到新的AIService")
            
            # 更新性能统计
            response_time = time.time() - start_time
            self._update_performance_stats(result, response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "task_id": task.task_id
            }
    
    async def _execute_text_generation(self, task: AITask) -> AIResponse:
        """执行文本生成任务"""
        capability = ModelCapability.TEXT_GENERATION
        
        # 选择提供商
        if task.provider:
            provider = task.provider
        else:
            provider, _ = await self.load_balancer.select_provider(
                capability, task.content, task.priority
            )
        
        # 创建模型请求
        model_request = ModelRequest(
            request_id=task.task_id,
            provider=provider,
            prompt=task.content,
            capability=capability,
            parameters=task.parameters,
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 执行请求
        response = await self.model_manager.process_request(model_request)
        
        # 更新负载均衡器
        self.load_balancer.update_request_result(
            provider, response.success, 
            response.metadata.get("response_time", 0.0),
            self.cost_manager.calculate_cost(
                provider,
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0)
            )
        )
        
        # 记录成本
        if response.success:
            cost_record = CostRecord(
                timestamp=time.time(),
                provider=provider,
                request_id=task.task_id,
                capability=capability.value,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=self.cost_manager.calculate_cost(
                    provider,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0)
                ),
                success=response.success,
                response_time=response.metadata.get("response_time", 0.0),
                metadata={"task_type": task.task_type.value}
            )
            self.cost_manager.record_cost(cost_record)
        
        return response
    
    async def _execute_content_analysis(self, task: AITask) -> AIResponse:
        """执行内容分析任务"""
        capability = ModelCapability.CONTENT_ANALYSIS
        
        # 选择提供商
        if task.provider:
            provider = task.provider
        else:
            provider, _ = await self.load_balancer.select_provider(
                capability, task.content, task.priority
            )
        
        # 创建模型请求
        model_request = ModelRequest(
            request_id=task.task_id,
            provider=provider,
            prompt=task.content,
            capability=capability,
            parameters=task.parameters,
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 执行请求
        response = await self.model_manager.process_request(model_request)
        
        # 更新负载均衡器和成本
        self.load_balancer.update_request_result(
            provider, response.success,
            response.metadata.get("response_time", 0.0),
            self.cost_manager.calculate_cost(
                provider,
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0)
            )
        )
        
        if response.success:
            cost_record = CostRecord(
                timestamp=time.time(),
                provider=provider,
                request_id=task.task_id,
                capability=capability.value,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=self.cost_manager.calculate_cost(
                    provider,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0)
                ),
                success=response.success,
                response_time=response.metadata.get("response_time", 0.0),
                metadata={"task_type": task.task_type.value}
            )
            self.cost_manager.record_cost(cost_record)
        
        return response
    
    async def _execute_commentary_generation(self, task: AITask) -> ContentGenerationResult:
        """执行解说生成任务"""
        # 创建内容生成请求
        content_request = ContentGenerationRequest(
            request_id=task.task_id,
            content_type=ContentGenerationType.COMMENTARY,
            prompt=task.content,
            context=task.context,
            style=task.parameters.get("style", "humorous"),
            tone=task.parameters.get("tone", "casual"),
            target_audience=task.parameters.get("target_audience", "general"),
            max_length=task.parameters.get("max_length", 1000),
            requirements=task.parameters.get("requirements", []),
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 生成内容
        result = await self.content_generator.generate_content(content_request)
        
        return result
    
    async def _execute_monologue_generation(self, task: AITask) -> ContentGenerationResult:
        """执行独白生成任务"""
        content_request = ContentGenerationRequest(
            request_id=task.task_id,
            content_type=ContentGenerationType.MONOLOGUE,
            prompt=task.content,
            context=task.context,
            style=task.parameters.get("style", "emotional"),
            tone=task.parameters.get("tone", "dramatic"),
            target_audience=task.parameters.get("target_audience", "general"),
            max_length=task.parameters.get("max_length", 800),
            requirements=task.parameters.get("requirements", []),
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        result = await self.content_generator.generate_content(content_request)
        return result
    
    async def _execute_scene_analysis(self, task: AITask) -> AIResponse:
        """执行场景分析任务"""
        capability = ModelCapability.SCENE_ANALYSIS
        
        # 选择提供商
        if task.provider:
            provider = task.provider
        else:
            provider, _ = await self.load_balancer.select_provider(
                capability, task.content, task.priority
            )
        
        # 创建模型请求
        model_request = ModelRequest(
            request_id=task.task_id,
            provider=provider,
            prompt=task.content,
            capability=capability,
            parameters=task.parameters,
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 执行请求
        response = await self.model_manager.process_request(model_request)
        
        # 更新负载均衡器和成本
        self.load_balancer.update_request_result(
            provider, response.success,
            response.metadata.get("response_time", 0.0),
            self.cost_manager.calculate_cost(
                provider,
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0)
            )
        )
        
        if response.success:
            cost_record = CostRecord(
                timestamp=time.time(),
                provider=provider,
                request_id=task.task_id,
                capability=capability.value,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=self.cost_manager.calculate_cost(
                    provider,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0)
                ),
                success=response.success,
                response_time=response.metadata.get("response_time", 0.0),
                metadata={"task_type": task.task_type.value}
            )
            self.cost_manager.record_cost(cost_record)
        
        return response
    
    async def _execute_subtitle_generation(self, task: AITask) -> ContentGenerationResult:
        """执行字幕生成任务"""
        content_request = ContentGenerationRequest(
            request_id=task.task_id,
            content_type=ContentGenerationType.CAPTION,
            prompt=task.content,
            context=task.context,
            style="formal",
            tone="neutral",
            target_audience="general",
            max_length=task.parameters.get("max_length", 2000),
            requirements=["时间轴准确", "语言通顺", "符合视频节奏"],
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        result = await self.content_generator.generate_content(content_request)
        return result
    
    async def _execute_editing_suggestion(self, task: AITask) -> AIResponse:
        """执行编辑建议任务"""
        capability = ModelCapability.CONTENT_ANALYSIS
        
        # 选择提供商
        if task.provider:
            provider = task.provider
        else:
            provider, _ = await self.load_balancer.select_provider(
                capability, task.content, task.priority
            )
        
        # 创建模型请求
        model_request = ModelRequest(
            request_id=task.task_id,
            provider=provider,
            prompt=task.content,
            capability=capability,
            parameters=task.parameters,
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 执行请求
        response = await self.model_manager.process_request(model_request)
        
        # 更新负载均衡器和成本
        self.load_balancer.update_request_result(
            provider, response.success,
            response.metadata.get("response_time", 0.0),
            self.cost_manager.calculate_cost(
                provider,
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0)
            )
        )
        
        if response.success:
            cost_record = CostRecord(
                timestamp=time.time(),
                provider=provider,
                request_id=task.task_id,
                capability=capability.value,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=self.cost_manager.calculate_cost(
                    provider,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0)
                ),
                success=response.success,
                response_time=response.metadata.get("response_time", 0.0),
                metadata={"task_type": task.task_type.value}
            )
            self.cost_manager.record_cost(cost_record)
        
        return response
    
    async def _execute_content_classification(self, task: AITask) -> AIResponse:
        """执行内容分类任务"""
        capability = ModelCapability.CONTENT_ANALYSIS
        
        # 选择提供商
        if task.provider:
            provider = task.provider
        else:
            provider, _ = await self.load_balancer.select_provider(
                capability, task.content, task.priority
            )
        
        # 创建模型请求
        model_request = ModelRequest(
            request_id=task.task_id,
            provider=provider,
            prompt=task.content,
            capability=capability,
            parameters=task.parameters,
            priority=task.priority.value,
            timeout=task.timeout
        )
        
        # 执行请求
        response = await self.model_manager.process_request(model_request)
        
        # 更新负载均衡器和成本
        self.load_balancer.update_request_result(
            provider, response.success,
            response.metadata.get("response_time", 0.0),
            self.cost_manager.calculate_cost(
                provider,
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0)
            )
        )
        
        if response.success:
            cost_record = CostRecord(
                timestamp=time.time(),
                provider=provider,
                request_id=task.task_id,
                capability=capability.value,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=self.cost_manager.calculate_cost(
                    provider,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0)
                ),
                success=response.success,
                response_time=response.metadata.get("response_time", 0.0),
                metadata={"task_type": task.task_type.value}
            )
            self.cost_manager.record_cost(cost_record)
        
        return response
    
    def _task_completed(self, task_id: str, future):
        """任务完成处理"""
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                
                try:
                    result = future.result()
                    
                    if result.get("success", False):
                        self.task_completed.emit(task_id, result)
                        
                        # 执行回调
                        if task.callback:
                            task.callback(result)
                    else:
                        # 重试逻辑
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            task.created_at = time.time()
                            self.task_queue.put((task.priority.value, task))
                            logger.info(f"任务 {task_id} 重试第 {task.retry_count} 次")
                        else:
                            self.task_failed.emit(task_id, result.get("error_message", "任务失败"))
                    
                    self.task_results[task_id] = result
                    
                except Exception as e:
                    self.task_failed.emit(task_id, f"任务执行异常: {str(e)}")
                    
        except Exception as e:
            logger.error(f"处理任务完成时出错: {e}")
    
    def _update_performance_stats(self, result: Any, response_time: float):
        """更新性能统计"""
        self.performance_stats["total_tasks"] += 1
        
        if result.get("success", False):
            self.performance_stats["successful_tasks"] += 1
            
            # 更新成本
            if "cost" in result:
                self.performance_stats["total_cost"] += result["cost"]
        else:
            self.performance_stats["failed_tasks"] += 1
        
        # 更新平均响应时间
        if self.performance_stats["total_tasks"] > 0:
            total_time = self.performance_stats["average_response_time"] * (self.performance_stats["total_tasks"] - 1) + response_time
            self.performance_stats["average_response_time"] = total_time / self.performance_stats["total_tasks"]
    
    def _update_usage_stats(self):
        """更新使用统计"""
        stats = {
            "performance_stats": self.performance_stats,
            "load_balancing_stats": self.load_balancer.get_load_balancing_stats(),
            "cost_summary": self.cost_manager.get_cost_summary(),
            "model_health": self.model_manager.get_model_health_summary(),
            "generation_stats": self.content_generator.get_generation_stats()
        }
        
        self.usage_stats_updated.emit(stats)
    
    def _on_cost_updated(self, cost_summary: dict):
        """成本更新处理"""
        # 可以在这里添加成本更新后的处理逻辑
        pass
    
    def _on_cost_analysis_ready(self, analysis: dict):
        """成本分析完成处理"""
        # 可以在这里添加成本分析完成后的处理逻辑
        pass
    
    # 公共接口
    def generate_text(self, prompt: str, provider: str = None, **kwargs) -> str:
        """生成文本（同步接口）"""
        task_id = f"text_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.TEXT_GENERATION,
            content=prompt,
            provider=provider,
            parameters=kwargs
        )
        
        return self._execute_task_sync(task)
    
    def generate_text_async(self, prompt: str, provider: str = None, 
                          callback: Callable = None, **kwargs) -> str:
        """生成文本（异步接口）"""
        task_id = f"text_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.TEXT_GENERATION,
            content=prompt,
            provider=provider,
            callback=callback,
            parameters=kwargs
        )
        
        self.task_queue.put((task.priority.value, task))
        return task_id
    
    def generate_commentary(self, video_info: Dict[str, Any], style: str = "幽默风趣", 
                          provider: str = None, **kwargs) -> ContentGenerationResult:
        """生成视频解说"""
        task_id = f"commentary_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.COMMENTARY_GENERATION,
            content=f"为视频生成{style}的解说",
            context=video_info,
            provider=provider,
            parameters={"style": style, **kwargs}
        )
        
        return self._execute_task_sync(task)
    
    def generate_monologue(self, video_info: Dict[str, Any], character: str = "主角", 
                          emotion: str = "平静", provider: str = None, **kwargs) -> ContentGenerationResult:
        """生成第一人称独白"""
        task_id = f"monologue_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.MONOLOGUE_GENERATION,
            content=f"为角色生成{emotion}的独白",
            context=video_info,
            provider=provider,
            parameters={"character": character, "emotion": emotion, **kwargs}
        )
        
        return self._execute_task_sync(task)
    
    def analyze_content(self, content: str, analysis_type: str = "general", 
                       provider: str = None) -> AIResponse:
        """分析内容"""
        task_id = f"analysis_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.CONTENT_ANALYSIS,
            content=content,
            provider=provider,
            parameters={"analysis_type": analysis_type}
        )
        
        return self._execute_task_sync(task)
    
    def generate_subtitle(self, video_content: str, language: str = "zh", 
                         provider: str = None) -> ContentGenerationResult:
        """生成字幕"""
        task_id = f"subtitle_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.SUBTITLE_GENERATION,
            content=video_content,
            provider=provider,
            parameters={"language": language}
        )
        
        return self._execute_task_sync(task)
    
    def analyze_video_scene(self, video_description: str, provider: str = None) -> AIResponse:
        """分析视频场景"""
        task_id = f"scene_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.SCENE_ANALYSIS,
            content=video_description,
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
        """
        
        task_id = f"editing_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.VIDEO_EDITING_SUGGESTION,
            content=prompt,
            provider=provider,
            parameters={"video_info": video_info}
        )
        
        return self._execute_task_sync(task)
    
    def classify_content(self, content: str, provider: str = None) -> AIResponse:
        """内容分类"""
        task_id = f"classify_{int(time.time() * 1000)}"
        task = AITask(
            task_id=task_id,
            task_type=AITaskType.CONTENT_CLASSIFICATION,
            content=content,
            provider=provider
        )
        
        return self._execute_task_sync(task)
    
    def _execute_task_sync(self, task: AITask) -> Any:
        """同步执行任务"""
        self.task_queue.put((task.priority.value, task))
        
        # 等待任务完成
        start_time = time.time()
        timeout = task.timeout or self.default_timeout
        
        while time.time() - start_time < timeout:
            if task.task_id in self.task_results:
                result = self.task_results.pop(task.task_id)
                return result
            
            time.sleep(0.01)
        
        # 超时处理
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        return {
            "success": False,
            "error_message": "任务执行超时"
        }
    
    def get_model_status(self) -> Dict[str, Any]:
        """获取模型状态"""
        return self.model_manager.get_model_health_summary()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self.cost_manager.get_cost_summary()
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            provider for provider, metrics in self.model_manager.model_metrics.items()
            if metrics.health_status.value in ["healthy", "degraded"]
        ]
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        self.load_balancer.set_strategy(strategy)
    
    def set_cost_budget(self, budget: float, duration_days: int = 30):
        """设置成本预算"""
        self.cost_manager.create_budget("自定义预算", budget, duration_days)
    
    def get_provider_recommendations(self, capability: ModelCapability) -> List[Dict[str, Any]]:
        """获取提供商推荐"""
        return self.load_balancer.get_provider_recommendations(capability)
    
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
        logger.info("清理增强AI管理器资源")
        
        # 停止定时器
        self.stats_timer.stop()
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        # 清理各个管理器
        # TODO: 移除asyncio.run - 这个文件即将被ai_service.py替代
        # asyncio.run(self.model_manager.cleanup())
        try:
            # 尝试同步清理
            if hasattr(self.model_manager, 'cleanup_sync'):
                self.model_manager.cleanup_sync()
        except Exception as e:
            logger.warning(f"模型管理器清理失败: {e}")
        
        logger.info("增强AI管理器资源清理完成")


# 工厂函数
def create_enhanced_ai_manager(settings_manager: SettingsManager) -> EnhancedAIManager:
    """创建增强的AI管理器"""
    return EnhancedAIManager(settings_manager)