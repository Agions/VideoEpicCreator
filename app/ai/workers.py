#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI工作线程实现
在独立线程中运行asyncio事件循环，避免与Qt主线程的事件循环冲突
"""

import asyncio
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThread, QMutex, QWaitCondition

from .interfaces import AIRequest, AIResponse, AIRequestStatus

logger = logging.getLogger(__name__)


class AIWorkerSignals(QObject):
    """AI工作线程信号"""
    # 请求开始处理
    request_started = pyqtSignal(str)  # request_id
    
    # 请求进度更新
    request_progress = pyqtSignal(str, float)  # request_id, progress
    
    # 请求完成
    request_finished = pyqtSignal(str, object)  # request_id, AIResponse
    
    # 请求失败
    request_error = pyqtSignal(str, str)  # request_id, error_message
    
    # 请求取消
    request_cancelled = pyqtSignal(str)  # request_id


class AIWorker(QRunnable):
    """AI任务工作线程"""
    
    def __init__(self, request: AIRequest, model_manager, cost_manager=None):
        super().__init__()
        self.request = request
        self.model_manager = model_manager
        self.cost_manager = cost_manager
        self.signals = AIWorkerSignals()
        self._cancelled = False
        
        # 设置可中断
        self.setAutoDelete(True)
    
    def run(self):
        """在工作线程中执行AI任务"""
        try:
            # 创建独立的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 发射开始信号
                self.signals.request_started.emit(self.request.request_id)
                
                # 更新请求状态
                self.request.status = AIRequestStatus.PROCESSING
                
                # 执行AI任务
                result = loop.run_until_complete(self._execute_ai_task())
                
                # 检查是否被取消
                if self._cancelled:
                    self.signals.request_cancelled.emit(self.request.request_id)
                    return
                
                if result.success:
                    self.signals.request_finished.emit(self.request.request_id, result)
                else:
                    self.signals.request_error.emit(self.request.request_id, result.error_message)
                
            finally:
                # 清理事件循环
                try:
                    # 取消所有未完成的任务
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                except Exception as e:
                    logger.warning(f"清理事件循环时出错: {e}")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"AI工作线程执行失败: {e}")
            self.signals.request_error.emit(self.request.request_id, str(e))
    
    async def _execute_ai_task(self) -> AIResponse:
        """执行AI任务"""
        start_time = time.time()
        
        try:
            # 选择提供商
            provider = await self._select_provider()
            if not provider:
                raise Exception("没有可用的AI提供商")
            
            # 更新请求信息
            self.request.provider = provider
            
            # 发射进度信号
            self.signals.request_progress.emit(self.request.request_id, 0.2)
            
            # 执行具体的AI任务
            response = await self._execute_model_request(provider)
            
            # 发射进度信号
            self.signals.request_progress.emit(self.request.request_id, 0.9)
            
            # 计算处理时间和成本
            processing_time = time.time() - start_time
            response.processing_time = processing_time
            response.request_id = self.request.request_id
            response.provider = provider
            
            # 计算成本
            if self.cost_manager and response.usage:
                cost = self.cost_manager.calculate_cost(provider, response.usage)
                response.cost = cost
                
                # 记录使用情况
                self.cost_manager.record_usage(provider, response.usage, cost)
            
            # 发射完成进度信号
            self.signals.request_progress.emit(self.request.request_id, 1.0)
            
            return response
            
        except Exception as e:
            logger.error(f"执行AI任务失败: {e}")
            return AIResponse(
                request_id=self.request.request_id,
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _select_provider(self) -> Optional[str]:
        """选择AI提供商"""
        # 如果指定了提供商，直接使用
        if self.request.provider:
            if hasattr(self.model_manager, 'is_provider_available'):
                if await self.model_manager.is_provider_available(self.request.provider):
                    return self.request.provider
                else:
                    logger.warning(f"指定的提供商 {self.request.provider} 不可用")
            else:
                return self.request.provider
        
        # 使用负载均衡器选择
        if hasattr(self.model_manager, 'get_best_provider'):
            return await self.model_manager.get_best_provider(self.request)
        
        # 回退到第一个可用提供商
        if hasattr(self.model_manager, 'get_available_providers'):
            providers = self.model_manager.get_available_providers()
            return providers[0] if providers else None
        
        return None
    
    async def _execute_model_request(self, provider: str) -> AIResponse:
        """执行模型请求"""
        try:
            # 获取模型实例
            if hasattr(self.model_manager, 'get_model'):
                model = self.model_manager.get_model(provider)
            elif hasattr(self.model_manager, 'models'):
                model = self.model_manager.models.get(provider)
            else:
                raise Exception(f"无法获取模型实例: {provider}")
            
            if not model:
                raise Exception(f"模型 {provider} 不存在")
            
            # 根据任务类型执行相应的方法
            task_type = self.request.task_type
            
            if task_type.value == "text_generation":
                return await model.generate_text(
                    self.request.content, 
                    **self.request.parameters
                )
            elif task_type.value == "content_analysis":
                return await model.analyze_content(
                    self.request.content, 
                    **self.request.parameters
                )
            elif task_type.value == "commentary_generation":
                video_info = self.request.context.get("video_info", {})
                style = self.request.context.get("style", "专业解说")
                return await model.generate_commentary(video_info, style)
            elif task_type.value == "monologue_generation":
                video_info = self.request.context.get("video_info", {})
                character = self.request.context.get("character", "主角")
                emotion = self.request.context.get("emotion", "平静")
                return await model.generate_monologue(video_info, character, emotion)
            else:
                # 默认使用文本生成
                return await model.generate_text(
                    self.request.content, 
                    **self.request.parameters
                )
                
        except Exception as e:
            logger.error(f"执行模型请求失败: {e}")
            raise e
    
    def cancel(self):
        """取消任务"""
        self._cancelled = True
        self.request.status = AIRequestStatus.CANCELLED


class AIWorkerPool(QObject):
    """AI工作线程池管理器"""
    
    # 信号定义
    pool_status_changed = pyqtSignal(int, int)  # active_workers, max_workers
    worker_started = pyqtSignal(str)  # request_id
    worker_finished = pyqtSignal(str, object)  # request_id, result
    worker_error = pyqtSignal(str, str)  # request_id, error
    
    def __init__(self, max_workers: int = 4):
        super().__init__()
        
        # 线程池配置
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # 工作线程管理
        self.active_workers: Dict[str, AIWorker] = {}
        self.worker_results: Dict[str, AIResponse] = {}
        
        # 线程安全
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        
        logger.info(f"AI工作线程池初始化完成，最大工作线程数: {max_workers}")
    
    def submit_task(self, request: AIRequest, model_manager, cost_manager=None) -> bool:
        """提交AI任务"""
        try:
            self.mutex.lock()
            
            # 检查是否已经在处理中
            if request.request_id in self.active_workers:
                logger.warning(f"请求 {request.request_id} 已在处理中")
                return False
            
            # 检查线程池容量
            if len(self.active_workers) >= self.max_workers:
                logger.warning(f"工作线程池已满，当前活动工作线程: {len(self.active_workers)}")
                return False
            
            # 创建工作线程
            worker = AIWorker(request, model_manager, cost_manager)
            
            # 连接信号
            worker.signals.request_started.connect(self._on_worker_started)
            worker.signals.request_progress.connect(self._on_worker_progress)
            worker.signals.request_finished.connect(self._on_worker_finished)
            worker.signals.request_error.connect(self._on_worker_error)
            worker.signals.request_cancelled.connect(self._on_worker_cancelled)
            
            # 添加到活动工作线程
            self.active_workers[request.request_id] = worker
            
            # 提交到线程池
            future = self.thread_pool.submit(worker.run)
            
            # 更新状态
            self.pool_status_changed.emit(len(self.active_workers), self.max_workers)
            
            logger.info(f"已提交AI任务: {request.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"提交AI任务失败: {e}")
            return False
        finally:
            self.mutex.unlock()
    
    def cancel_task(self, request_id: str) -> bool:
        """取消AI任务"""
        try:
            self.mutex.lock()
            
            if request_id in self.active_workers:
                worker = self.active_workers[request_id]
                worker.cancel()
                
                logger.info(f"已取消AI任务: {request_id}")
                return True
            else:
                logger.warning(f"未找到要取消的任务: {request_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消AI任务失败: {e}")
            return False
        finally:
            self.mutex.unlock()
    
    def get_active_tasks(self) -> List[str]:
        """获取活动任务列表"""
        self.mutex.lock()
        try:
            return list(self.active_workers.keys())
        finally:
            self.mutex.unlock()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """获取线程池状态"""
        self.mutex.lock()
        try:
            return {
                "active_workers": len(self.active_workers),
                "max_workers": self.max_workers,
                "utilization": len(self.active_workers) / self.max_workers,
                "completed_tasks": len(self.worker_results)
            }
        finally:
            self.mutex.unlock()
    
    def _on_worker_started(self, request_id: str):
        """工作线程开始处理"""
        self.worker_started.emit(request_id)
        logger.debug(f"工作线程开始处理: {request_id}")
    
    def _on_worker_progress(self, request_id: str, progress: float):
        """工作线程进度更新"""
        # 可以在这里添加进度监控逻辑
        pass
    
    def _on_worker_finished(self, request_id: str, result: AIResponse):
        """工作线程完成处理"""
        try:
            self.mutex.lock()
            
            # 移除活动工作线程
            if request_id in self.active_workers:
                del self.active_workers[request_id]
            
            # 保存结果
            self.worker_results[request_id] = result
            
            # 更新状态
            self.pool_status_changed.emit(len(self.active_workers), self.max_workers)
            
            # 发射信号
            self.worker_finished.emit(request_id, result)
            
            logger.info(f"工作线程处理完成: {request_id}")
            
        except Exception as e:
            logger.error(f"处理工作线程完成事件失败: {e}")
        finally:
            self.mutex.unlock()
    
    def _on_worker_error(self, request_id: str, error_message: str):
        """工作线程处理错误"""
        try:
            self.mutex.lock()
            
            # 移除活动工作线程
            if request_id in self.active_workers:
                del self.active_workers[request_id]
            
            # 更新状态
            self.pool_status_changed.emit(len(self.active_workers), self.max_workers)
            
            # 发射信号
            self.worker_error.emit(request_id, error_message)
            
            logger.error(f"工作线程处理错误: {request_id} - {error_message}")
            
        except Exception as e:
            logger.error(f"处理工作线程错误事件失败: {e}")
        finally:
            self.mutex.unlock()
    
    def _on_worker_cancelled(self, request_id: str):
        """工作线程被取消"""
        try:
            self.mutex.lock()
            
            # 移除活动工作线程
            if request_id in self.active_workers:
                del self.active_workers[request_id]
            
            # 更新状态
            self.pool_status_changed.emit(len(self.active_workers), self.max_workers)
            
            logger.info(f"工作线程已取消: {request_id}")
            
        except Exception as e:
            logger.error(f"处理工作线程取消事件失败: {e}")
        finally:
            self.mutex.unlock()
    
    def cleanup(self):
        """清理线程池"""
        logger.info("清理AI工作线程池")
        
        try:
            self.mutex.lock()
            
            # 取消所有活动任务
            for request_id in list(self.active_workers.keys()):
                self.cancel_task(request_id)
            
            # 关闭线程池
            self.thread_pool.shutdown(wait=True, timeout=30)
            
            # 清理数据
            self.active_workers.clear()
            self.worker_results.clear()
            
            logger.info("AI工作线程池清理完成")
            
        except Exception as e:
            logger.error(f"清理AI工作线程池失败: {e}")
        finally:
            self.mutex.unlock()


# 工厂函数
def create_worker_pool(max_workers: int = 4) -> AIWorkerPool:
    """创建AI工作线程池"""
    return AIWorkerPool(max_workers)
