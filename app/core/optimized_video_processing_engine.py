#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化版视频处理引擎 - 高性能、低延迟的视频处理核心
解决内存管理、线程同步和硬件加速问题
"""

import os
import sys
import json
import time
import logging
import threading
import subprocess
import gc
import psutil
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import tempfile
import shutil
import multiprocessing as mp
from contextlib import contextmanager
import weakref

from .hardware_acceleration import HardwareAccelerationManager, HardwareType
from .effects_engine import EffectsEngine, EffectType
from .batch_processor import BatchProcessor, BatchTask, BatchTaskType
from .video_codec_manager import VideoCodecManager
from .video_optimizer import VideoOptimizer

logger = logging.getLogger(__name__)


class ProcessingPriority(Enum):
    """处理优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MemoryMode(Enum):
    """内存模式"""
    CONSERVATIVE = "conservative"  # 保守模式，低内存使用
    BALANCED = "balanced"        # 平衡模式
    AGGRESSIVE = "aggressive"    # 激进模式，高性能


@dataclass
class ProcessingTask:
    """处理任务"""
    task_id: str
    task_type: str
    input_path: str
    output_path: str
    config: Any
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    progress_callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """性能指标"""
    tasks_processed: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    memory_usage_peak: int = 0  # MB
    cpu_usage_avg: float = 0.0
    gpu_usage_avg: float = 0.0
    cache_hit_rate: float = 0.0
    success_rate: float = 0.0


class MemoryManager:
    """内存管理器 - 优化内存使用"""
    
    def __init__(self, max_memory_mb: int = 2048, mode: MemoryMode = MemoryMode.BALANCED):
        self.max_memory_mb = max_memory_mb
        self.mode = mode
        self.current_usage = 0
        self.cache_objects = weakref.WeakValueDictionary()
        self.allocation_lock = threading.Lock()
        self.cleanup_threshold = 0.8  # 80%时开始清理
        
        # 监控线程
        self.monitor_thread = None
        self.monitor_running = False
        
        # 启动监控
        self._start_monitoring()
    
    def _start_monitoring(self):
        """启动内存监控"""
        self.monitor_running = True
        
        def monitor_loop():
            while self.monitor_running:
                try:
                    self._check_memory_usage()
                    self._cleanup_if_needed()
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"内存监控错误: {e}")
                    time.sleep(10)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _check_memory_usage(self):
        """检查内存使用"""
        process = psutil.Process()
        memory_info = process.memory_info()
        self.current_usage = memory_info.rss / (1024 * 1024)  # MB
    
    def _cleanup_if_needed(self):
        """需要时清理内存"""
        if self.current_usage > self.max_memory_mb * self.cleanup_threshold:
            self._force_cleanup()
    
    def _force_cleanup(self):
        """强制清理内存"""
        logger.info(f"触发内存清理，当前使用: {self.current_usage:.1f}MB")
        
        # 强制垃圾回收
        gc.collect()
        
        # 清理缓存
        self.cache_objects.clear()
        
        # 如果仍然超过限制，通知系统
        self._check_memory_usage()
        if self.current_usage > self.max_memory_mb * 0.9:
            logger.warning(f"内存使用过高: {self.current_usage:.1f}MB / {self.max_memory_mb}MB")
    
    def allocate_memory(self, size_mb: int) -> bool:
        """分配内存"""
        with self.allocation_lock:
            if self.current_usage + size_mb <= self.max_memory_mb:
                self.current_usage += size_mb
                return True
            else:
                # 尝试清理
                self._force_cleanup()
                if self.current_usage + size_mb <= self.max_memory_mb:
                    self.current_usage += size_mb
                    return True
                return False
    
    def release_memory(self, size_mb: int):
        """释放内存"""
        with self.allocation_lock:
            self.current_usage = max(0, self.current_usage - size_mb)
    
    def get_memory_usage(self) -> float:
        """获取当前内存使用"""
        return self.current_usage
    
    def cleanup(self):
        """清理资源"""
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)


class OptimizedVideoProcessingEngine:
    """优化版视频处理引擎"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # 内存管理
        self.memory_manager = MemoryManager(max_memory_mb=4096)
        
        # 初始化组件
        self.hardware_manager = HardwareAccelerationManager(ffmpeg_path)
        self.effects_engine = EffectsEngine()
        self.batch_processor = BatchProcessor()
        self.codec_manager = VideoCodecManager(ffmpeg_path, ffprobe_path)
        self.video_optimizer = VideoOptimizer(ffmpeg_path, ffprobe_path)
        
        # 任务管理
        self.task_queue = PriorityQueue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.task_lock = threading.Lock()
        
        # 线程池优化
        self.max_workers = min(8, mp.cpu_count())
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=4)
        
        # 处理状态
        self.is_processing = False
        self.processing_cancel_flag = False
        
        # 性能监控
        self.performance_metrics = PerformanceMetrics()
        self.start_time = time.time()
        
        # 缓存优化
        self.video_cache: Dict[str, Any] = {}
        self.proxy_cache: Dict[str, str] = {}
        self.frame_cache: Dict[str, np.ndarray] = {}
        self.cache_lock = threading.RLock()
        
        # 事件系统
        self.processing_complete = threading.Event()
        self.error_occurred = threading.Event()
        
        # 启动工作线程
        self._start_worker_threads()
        
        logger.info("优化版视频处理引擎初始化完成")
    
    def _start_worker_threads(self):
        """启动工作线程"""
        # 任务分发线程
        self.task_dispatcher = threading.Thread(target=self._task_dispatcher_loop, daemon=True)
        self.task_dispatcher.start()
        
        # 性能监控线程
        self.performance_monitor = threading.Thread(target=self._performance_monitor_loop, daemon=True)
        self.performance_monitor.start()
        
        logger.info("工作线程已启动")
    
    def _task_dispatcher_loop(self):
        """任务分发循环"""
        while True:
            try:
                if not self.task_queue.empty():
                    # 获取最高优先级任务
                    _, task = self.task_queue.get()
                    
                    # 检查资源
                    if self._can_process_task(task):
                        # 分配线程处理
                        self.thread_pool.submit(self._process_task, task)
                    else:
                        # 资源不足，重新排队
                        self.task_queue.put((task.priority.value, task))
                        time.sleep(1)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"任务分发错误: {e}")
                time.sleep(5)
    
    def _performance_monitor_loop(self):
        """性能监控循环"""
        while True:
            try:
                self._update_performance_metrics()
                time.sleep(30)  # 30秒更新一次
            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(60)
    
    def _can_process_task(self, task: ProcessingTask) -> bool:
        """检查是否可以处理任务"""
        # 检查内存
        if not self.memory_manager.allocate_memory(512):  # 预分配512MB
            return False
        
        # 检查硬件资源
        recommended_hw = self.hardware_manager.recommend_hardware(
            task.task_type, 
            {"codecs": [getattr(task.config, 'video_codec', 'h264')]}
        )
        
        if not self.hardware_manager.is_hardware_available(recommended_hw):
            self.memory_manager.release_memory(512)
            return False
        
        return True
    
    def _process_task(self, task: ProcessingTask):
        """处理任务"""
        try:
            task.started_at = time.time()
            
            with self.task_lock:
                self.active_tasks[task.task_id] = task
            
            # 获取最优硬件配置
            recommended_hw = self.hardware_manager.recommend_hardware(
                task.task_type, 
                {"codecs": [getattr(task.config, 'video_codec', 'h264')]}
            )
            
            # 获取加速参数
            accel_params = self.hardware_manager.get_acceleration_params(
                recommended_hw, 
                getattr(task.config, 'video_codec', 'h264')
            )
            
            # 处理任务
            if task.task_type == "video_process":
                result = self._process_video_optimized(task, accel_params)
            elif task.task_type == "timeline_process":
                result = self._process_timeline_optimized(task, accel_params)
            else:
                result = self._process_generic_task(task, accel_params)
            
            task.completed_at = time.time()
            
            # 记录结果
            with self.task_lock:
                self.completed_tasks[task.task_id] = task
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            # 释放内存
            self.memory_manager.release_memory(512)
            
            # 调用回调
            if result and task.callback:
                task.callback(result)
            elif not result and task.error_callback:
                task.error_callback(Exception("处理失败"))
            
            # 记录性能
            self._record_task_performance(task, result)
            
        except Exception as e:
            logger.error(f"任务处理失败: {task.task_id}, 错误: {e}")
            task.completed_at = time.time()
            
            with self.task_lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            # 释放内存
            self.memory_manager.release_memory(512)
            
            # 调用错误回调
            if task.error_callback:
                task.error_callback(e)
    
    def _process_video_optimized(self, task: ProcessingTask, accel_params: Dict[str, Any]) -> bool:
        """优化版视频处理"""
        try:
            start_time = time.time()
            
            # 检查缓存
            cache_key = self._get_cache_key(task.input_path, task.config)
            if cache_key in self.video_cache:
                logger.info(f"使用缓存结果: {task.input_path}")
                return True
            
            # 构建优化命令
            cmd = self._build_optimized_command(task, accel_params)
            
            # 使用优化的子进程执行
            result = self._execute_optimized_process(cmd, task)
            
            if result:
                processing_time = time.time() - start_time
                self._record_hardware_performance(accel_params.get('hardware_type'), processing_time, True)
                
                # 缓存结果
                self._cache_result(cache_key, result)
                
                logger.info(f"视频处理完成: {task.input_path} -> {task.output_path}, 耗时: {processing_time:.2f}s")
                return True
            else:
                self._record_hardware_performance(accel_params.get('hardware_type'), time.time() - start_time, False)
                return False
                
        except Exception as e:
            logger.error(f"视频处理失败: {task.input_path}, 错误: {e}")
            return False
    
    def _build_optimized_command(self, task: ProcessingTask, accel_params: Dict[str, Any]) -> List[str]:
        """构建优化命令"""
        cmd = [self.ffmpeg_path]
        
        # 硬件加速输入
        if accel_params.get("hardware_acceleration"):
            cmd.extend(["-hwaccel", accel_params.get("hwaccel", "auto")])
        
        # 输入文件
        cmd.extend(["-i", task.input_path])
        
        # 多线程优化
        cmd.extend(["-threads", str(self.max_workers)])
        
        # 内存优化
        cmd.extend(["-thread_queue_size", "1024"])
        
        # 编码参数
        video_codec = getattr(task.config, 'video_codec', 'h264')
        if video_codec == 'h264':
            cmd.extend(["-c:v", "libx264"])
        elif video_codec == 'h265':
            cmd.extend(["-c:v", "libx265"])
        
        # 质量参数
        quality = getattr(task.config, 'quality', 'medium')
        if quality == 'high':
            cmd.extend(["-crf", "20", "-preset", "slow"])
        elif quality == 'medium':
            cmd.extend(["-crf", "23", "-preset", "medium"])
        else:
            cmd.extend(["-crf", "28", "-preset", "fast"])
        
        # 硬件加速参数
        if "extra_params" in accel_params:
            cmd.extend(accel_params["extra_params"])
        
        # 音频参数
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        
        # 输出文件
        cmd.extend(["-y", task.output_path])
        
        return cmd
    
    def _execute_optimized_process(self, cmd: List[str], task: ProcessingTask) -> bool:
        """执行优化进程"""
        try:
            # 使用subprocess.run的优化配置
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                check=False
            )
            
            if result.returncode == 0:
                return True
            else:
                logger.error(f"进程执行失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("进程执行超时")
            return False
        except Exception as e:
            logger.error(f"进程执行错误: {e}")
            return False
    
    def _get_cache_key(self, input_path: str, config: Any) -> str:
        """生成缓存键"""
        # 基于文件路径、修改时间和配置生成唯一键
        file_stat = os.stat(input_path)
        config_str = str(getattr(config, '__dict__', config))
        return f"{input_path}_{file_stat.st_mtime}_{hash(config_str)}"
    
    def _cache_result(self, cache_key: str, result: Any):
        """缓存结果"""
        with self.cache_lock:
            if len(self.video_cache) < 100:  # 限制缓存大小
                self.video_cache[cache_key] = result
    
    def _record_task_performance(self, task: ProcessingTask, success: bool):
        """记录任务性能"""
        if task.started_at and task.completed_at:
            processing_time = task.completed_at - task.started_at
            
            with self.task_lock:
                self.performance_metrics.tasks_processed += 1
                self.performance_metrics.total_processing_time += processing_time
                
                if success:
                    self.performance_metrics.success_rate = (
                        (self.performance_metrics.tasks_processed - 1) * self.performance_metrics.success_rate + 1
                    ) / self.performance_metrics.tasks_processed
                else:
                    self.performance_metrics.success_rate = (
                        (self.performance_metrics.tasks_processed - 1) * self.performance_metrics.success_rate
                    ) / self.performance_metrics.tasks_processed
    
    def _record_hardware_performance(self, hardware_type: Optional[HardwareType], 
                                   processing_time: float, success: bool):
        """记录硬件性能"""
        if hardware_type:
            speedup = 1.0  # 简化的加速比计算
            self.hardware_manager.record_acceleration(hardware_type, success, processing_time, speedup)
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        try:
            process = psutil.Process()
            
            # 内存使用
            memory_info = process.memory_info()
            self.performance_metrics.memory_usage_peak = max(
                self.performance_metrics.memory_usage_peak,
                memory_info.rss / (1024 * 1024)
            )
            
            # CPU使用率
            cpu_percent = process.cpu_percent()
            self.performance_metrics.cpu_usage_avg = (
                self.performance_metrics.cpu_usage_avg * 0.9 + cpu_percent * 0.1
            )
            
            # 平均处理时间
            if self.performance_metrics.tasks_processed > 0:
                self.performance_metrics.average_processing_time = (
                    self.performance_metrics.total_processing_time / self.performance_metrics.tasks_processed
                )
            
            # 缓存命中率
            with self.cache_lock:
                total_accesses = len(self.video_cache)
                if total_accesses > 0:
                    self.performance_metrics.cache_hit_rate = min(1.0, total_accesses / 1000)
            
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")
    
    def add_task(self, task: ProcessingTask):
        """添加任务"""
        self.task_queue.put((task.priority.value, task))
        logger.info(f"任务已添加: {task.task_id}, 优先级: {task.priority.name}")
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        with self.task_lock:
            if task_id in self.active_tasks:
                # 标记为取消
                task = self.active_tasks[task_id]
                self.processing_cancel_flag = True
                logger.info(f"任务已取消: {task_id}")
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        with self.task_lock:
            if task_id in self.active_tasks:
                return "processing"
            elif task_id in self.completed_tasks:
                return "completed"
            else:
                return "not_found"
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """获取性能指标"""
        return self.performance_metrics
    
    def optimize_for_batch_processing(self, tasks: List[ProcessingTask]):
        """批量处理优化"""
        # 按优先级和类型分组
        grouped_tasks = {}
        for task in tasks:
            key = (task.priority, task.task_type)
            if key not in grouped_tasks:
                grouped_tasks[key] = []
            grouped_tasks[key].append(task)
        
        # 按组处理
        for (priority, task_type), task_group in grouped_tasks.items():
            logger.info(f"批量处理组: 优先级={priority.name}, 类型={task_type}, 数量={len(task_group)}")
            
            for task in task_group:
                self.add_task(task)
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理优化版视频处理引擎资源")
        
        # 停止处理
        self.processing_cancel_flag = True
        
        # 清理线程池
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        # 清理组件
        self.hardware_manager.cleanup()
        self.effects_engine.cancel_render()
        self.batch_processor.cleanup()
        self.memory_manager.cleanup()
        
        # 清理缓存
        with self.cache_lock:
            self.video_cache.clear()
            self.proxy_cache.clear()
            self.frame_cache.clear()
        
        logger.info("优化版视频处理引擎资源清理完成")
    
    # 兼容原有API的方法
    def get_video_info(self, file_path: str):
        """获取视频信息（兼容方法）"""
        # 这里可以复用原有逻辑或调用新的优化方法
        from .video_processing_engine import VideoProcessingEngine
        temp_engine = VideoProcessingEngine(self.ffmpeg_path, self.ffprobe_path)
        return temp_engine.get_video_info(file_path)
    
    def process_video(self, input_path: str, output_path: str, config):
        """处理视频（兼容方法）"""
        task = ProcessingTask(
            task_id=f"task_{int(time.time() * 1000)}",
            task_type="video_process",
            input_path=input_path,
            output_path=output_path,
            config=config
        )
        self.add_task(task)
        return True


# 工厂函数
def create_optimized_video_processing_engine(ffmpeg_path: str = "ffmpeg", 
                                         ffprobe_path: str = "ffprobe") -> OptimizedVideoProcessingEngine:
    """创建优化版视频处理引擎"""
    return OptimizedVideoProcessingEngine(ffmpeg_path, ffprobe_path)


if __name__ == "__main__":
    # 测试代码
    engine = create_optimized_video_processing_engine()
    
    # 测试性能
    import time
    start_time = time.time()
    
    # 模拟任务
    from dataclasses import dataclass
    
    @dataclass
    class TestConfig:
        video_codec: str = "h264"
        quality: str = "medium"
    
    config = TestConfig()
    
    # 添加测试任务
    task = ProcessingTask(
        task_id="test_task",
        task_type="video_process",
        input_path="test_input.mp4",
        output_path="test_output.mp4",
        config=config
    )
    
    engine.add_task(task)
    
    # 等待处理完成
    time.sleep(5)
    
    # 获取性能指标
    metrics = engine.get_performance_metrics()
    print(f"性能指标: {metrics}")
    
    engine.cleanup()