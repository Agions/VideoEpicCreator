#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能优化和内存管理模块 - 提供系统性能监控、内存优化和资源管理功能
"""

import os
import sys
import psutil
import time
import threading
import gc
import logging
import tracemalloc
import weakref
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque, defaultdict
from contextlib import contextmanager

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QThreadPool, QRunnable
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """性能级别"""
    LOW = 1      # 低性能模式（省电）
    MEDIUM = 2   # 中等性能模式
    HIGH = 3     # 高性能模式
    MAXIMUM = 4  # 最高性能模式


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    gpu_percent: Optional[float] = None
    gpu_memory_used: Optional[int] = None
    gpu_memory_total: Optional[int] = None
    disk_usage: Optional[float] = None
    network_io: Optional[Tuple[int, int]] = None


@dataclass
class ResourceUsage:
    """资源使用情况"""
    resource_type: ResourceType
    current_usage: float
    peak_usage: float
    average_usage: float
    limit: Optional[float] = None
    warning_threshold: float = 80.0
    critical_threshold: float = 95.0


@dataclass
class PerformanceProfile:
    """性能配置文件"""
    name: str
    level: PerformanceLevel
    max_memory_usage: int  # MB
    max_cpu_usage: float  # 百分比
    enable_gpu_acceleration: bool
    enable_multithreading: bool
    cache_size: int  # MB
    background_processing: bool
    auto_cleanup: bool
    cleanup_interval: int  # 秒
    description: str = ""


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    thread_count: int
    handle_count: int
    fps: Optional[float] = None
    ui_response_time: Optional[float] = None
    custom_metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'memory_total_mb': self.memory_total_mb,
            'thread_count': self.thread_count,
            'handle_count': self.handle_count,
            'fps': self.fps,
            'ui_response_time': self.ui_response_time,
            'custom_metrics': self.custom_metrics or {}
        }


class MemoryTracker:
    """内存跟踪器"""

    def __init__(self):
        self.snapshots = {}
        self.peak_memory = 0
        self.enabled = False

    def start_tracking(self):
        """开始跟踪内存使用"""
        tracemalloc.start()
        self.enabled = True
        logger.info("内存跟踪已启动")

    def take_snapshot(self, name: str):
        """拍摄内存快照"""
        if not self.enabled:
            return

        snapshot = tracemalloc.take_snapshot()
        self.snapshots[name] = snapshot

        # 更新峰值内存
        current, peak = tracemalloc.get_traced_memory()
        if peak > self.peak_memory:
            self.peak_memory = peak

        logger.debug(f"内存快照 '{name}': 当前 {current / 1024 / 1024:.2f} MB, 峰值 {peak / 1024 / 1024:.2f} MB")

    def compare_snapshots(self, snapshot1: str, snapshot2: str) -> Dict[str, Any]:
        """比较两个快照的差异"""
        if snapshot1 not in self.snapshots or snapshot2 not in self.snapshots:
            return {}

        snap1 = self.snapshots[snapshot1]
        snap2 = self.snapshots[snapshot2]

        stats = snap2.compare_to(snap1, 'lineno')

        result = {
            'total_diff': 0,
            'top_stats': []
        }

        for stat in stats[:10]:  # 前10个最大的差异
            result['top_stats'].append({
                'file': stat.traceback.format()[-1] if stat.traceback else 'unknown',
                'line': stat.lineno,
                'diff': stat.size_diff,
                'count_diff': stat.count_diff
            })
            result['total_diff'] += stat.size_diff

        return result

    def stop_tracking(self):
        """停止跟踪"""
        if self.enabled:
            tracemalloc.stop()
            self.enabled = False
            self.snapshots.clear()
            logger.info("内存跟踪已停止")


class CacheManager:
    """缓存管理器"""

    def __init__(self, max_size: int = 1024):  # MB
        self.max_size = max_size * 1024 * 1024  # 转换为字节
        self.caches = {}
        self.access_times = {}
        self.cache_sizes = {}
        self.lock = threading.Lock()

    def add_cache(self, name: str, cache: Dict[str, Any]):
        """添加缓存"""
        with self.lock:
            self.caches[name] = cache
            self.access_times[name] = time.time()
            self.cache_sizes[name] = self._estimate_cache_size(cache)
            self._enforce_size_limit()

    def get_cache(self, name: str) -> Optional[Dict[str, Any]]:
        """获取缓存"""
        with self.lock:
            if name in self.caches:
                self.access_times[name] = time.time()
                return self.caches[name]
            return None

    def remove_cache(self, name: str):
        """移除缓存"""
        with self.lock:
            if name in self.caches:
                del self.caches[name]
                del self.access_times[name]
                del self.cache_sizes[name]

    def clear_all(self):
        """清除所有缓存"""
        with self.lock:
            self.caches.clear()
            self.access_times.clear()
            self.cache_sizes.clear()

    def _estimate_cache_size(self, cache: Dict[str, Any]) -> int:
        """估算缓存大小"""
        try:
            import pickle
            return len(pickle.dumps(cache))
        except Exception:
            return 1024  # 默认1KB

    def _enforce_size_limit(self):
        """强制执行大小限制"""
        total_size = sum(self.cache_sizes.values())

        while total_size > self.max_size and self.caches:
            # 按LRU策略移除缓存
            oldest_cache = min(self.access_times.items(), key=lambda x: x[1])[0]
            self.remove_cache(oldest_cache)
            total_size = sum(self.cache_sizes.values())

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_size = sum(self.cache_sizes.values())
            return {
                'total_size_mb': total_size / 1024 / 1024,
                'max_size_mb': self.max_size / 1024 / 1024,
                'cache_count': len(self.caches),
                'usage_percent': (total_size / self.max_size) * 100
            }


class PerformanceMonitor(QObject):
    """性能监控器"""

    # 信号定义
    metrics_updated = pyqtSignal(PerformanceMetrics)  # 性能指标更新信号
    performance_warning = pyqtSignal(str)  # 性能警告信号
    memory_warning = pyqtSignal(float)  # 内存警告信号
    cpu_warning = pyqtSignal(float)  # CPU警告信号

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._monitoring = False
        self._metrics_history: deque = deque(maxlen=1000)
        self._warning_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'thread_count': 100,
            'ui_response_time': 100.0  # ms
        }

        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._collect_metrics)

        self._last_ui_response_time = time.time()
        self._fps_counter = 0
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._calculate_fps)

    def start_monitoring(self, interval_ms: int = 1000) -> None:
        """开始监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_timer.start(interval_ms)
        self._fps_timer.start(1000)  # 每秒计算一次FPS

    def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitoring = False
        self._monitor_timer.stop()
        self._fps_timer.stop()

    def _collect_metrics(self) -> None:
        """收集性能指标"""
        try:
            process = psutil.Process()

            # 获取基本指标
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_info.rss / 1024 / 1024,
                memory_total_mb=psutil.virtual_memory().total / 1024 / 1024,
                thread_count=process.num_threads(),
                handle_count=len(process.open_files()),
                fps=self._fps_counter,
                ui_response_time=self._calculate_ui_response_time()
            )

            # 添加到历史记录
            self._metrics_history.append(metrics)

            # 检查警告
            self._check_warnings(metrics)

            # 发射信号
            self.metrics_updated.emit(metrics)

        except Exception as e:
            print(f"性能监控错误: {e}")

    def _calculate_fps(self) -> None:
        """计算FPS"""
        self._fps_counter = 0

    def _calculate_ui_response_time(self) -> float:
        """计算UI响应时间"""
        current_time = time.time()
        response_time = (current_time - self._last_ui_response_time) * 1000
        self._last_ui_response_time = current_time
        return response_time

    def _check_warnings(self, metrics: PerformanceMetrics) -> None:
        """检查性能警告"""
        # CPU警告
        if metrics.cpu_percent > self._warning_thresholds['cpu_percent']:
            self.cpu_warning.emit(metrics.cpu_percent)
            self.performance_warning.emit(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")

        # 内存警告
        if metrics.memory_percent > self._warning_thresholds['memory_percent']:
            self.memory_warning.emit(metrics.memory_percent)
            self.performance_warning.emit(f"内存使用率过高: {metrics.memory_percent:.1f}%")

        # 线程数警告
        if metrics.thread_count > self._warning_thresholds['thread_count']:
            self.performance_warning.emit(f"线程数过多: {metrics.thread_count}")

        # UI响应时间警告
        if (metrics.ui_response_time and
            metrics.ui_response_time > self._warning_thresholds['ui_response_time']):
            self.performance_warning.emit(f"UI响应时间过长: {metrics.ui_response_time:.1f}ms")

    def get_metrics_history(self, limit: Optional[int] = None) -> List[PerformanceMetrics]:
        """获取性能历史"""
        history = list(self._metrics_history)
        if limit:
            history = history[-limit:]
        return history

    def get_average_metrics(self, duration_seconds: int = 60) -> Optional[PerformanceMetrics]:
        """获取平均性能指标"""
        cutoff_time = datetime.now().timestamp() - duration_seconds
        recent_metrics = [
            m for m in self._metrics_history
            if m.timestamp.timestamp() > cutoff_time
        ]

        if not recent_metrics:
            return None

        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            memory_percent=sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            memory_used_mb=sum(m.memory_used_mb for m in recent_metrics) / len(recent_metrics),
            memory_total_mb=recent_metrics[0].memory_total_mb,
            thread_count=sum(m.thread_count for m in recent_metrics) / len(recent_metrics),
            handle_count=sum(m.handle_count for m in recent_metrics) / len(recent_metrics),
            fps=sum(m.fps for m in recent_metrics if m.fps) / len([m for m in recent_metrics if m.fps]),
            ui_response_time=sum(m.ui_response_time for m in recent_metrics if m.ui_response_time) / len([m for m in recent_metrics if m.ui_response_time])
        )

    def set_warning_threshold(self, metric: str, threshold: float) -> None:
        """设置警告阈值"""
        self._warning_thresholds[metric] = threshold

    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标"""
        return self._metrics_history[-1] if self._metrics_history else None


class MemoryOptimizer(QObject):
    """内存优化器"""

    # 信号定义
    memory_optimized = pyqtSignal(int)  # 内存优化完成信号，参数为释放的MB数
    optimization_started = pyqtSignal()  # 优化开始信号

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._optimization_threshold = 80.0  # 内存使用率阈值
        self._auto_optimize = True

    def set_optimization_threshold(self, threshold: float) -> None:
        """设置优化阈值"""
        self._optimization_threshold = threshold

    def set_auto_optimize(self, enabled: bool) -> None:
        """设置自动优化"""
        self._auto_optimize = enabled

    def optimize_memory(self) -> int:
        """优化内存，返回释放的MB数"""
        self.optimization_started.emit()

        try:
            import gc

            # 获取优化前的内存使用
            process = psutil.Process()
            before_memory = process.memory_info().rss / 1024 / 1024

            # 强制垃圾回收
            gc.collect()

            # 清理PyQt缓存
            if QApplication.instance():
                QApplication.instance().processEvents()

            # 获取优化后的内存使用
            after_memory = process.memory_info().rss / 1024 / 1024
            freed_memory = before_memory - after_memory

            if freed_memory > 0:
                self.memory_optimized.emit(int(freed_memory))

            return int(freed_memory)

        except Exception as e:
            print(f"内存优化失败: {e}")
            return 0

    def should_optimize(self) -> bool:
        """判断是否需要优化"""
        if not self._auto_optimize:
            return False

        try:
            process = psutil.Process()
            memory_percent = process.memory_percent()
            return memory_percent > self._optimization_threshold
        except:
            return False


class ThreadManager:
    """线程管理器"""

    def __init__(self, max_threads: int = 8):
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(max_threads)
        self._active_threads = {}
        self._thread_counter = 0

    def execute_task(self, task: QRunnable, task_id: Optional[str] = None) -> None:
        """执行任务"""
        if not task_id:
            self._thread_counter += 1
            task_id = f"task_{self._thread_counter}"

        # 记录活动线程
        self._active_threads[task_id] = {
            'start_time': datetime.now(),
            'runnable': task
        }

        # 任务完成时清理
        def cleanup():
            self._active_threads.pop(task_id, None)

        if hasattr(task, 'finished'):
            task.finished.connect(cleanup)
        else:
            # 如果没有finished信号，使用定时器清理
            QTimer.singleShot(60000, cleanup)  # 60秒后清理

        self._thread_pool.start(task)

    def get_active_threads(self) -> Dict[str, Any]:
        """获取活动线程"""
        return self._active_threads.copy()

    def get_thread_count(self) -> int:
        """获取线程数"""
        return len(self._active_threads)

    def clear_completed_threads(self) -> None:
        """清理已完成的线程"""
        current_time = datetime.now()
        completed_threads = []

        for task_id, thread_info in self._active_threads.items():
            if (current_time - thread_info['start_time']).total_seconds() > 300:  # 5分钟
                completed_threads.append(task_id)

        for task_id in completed_threads:
            self._active_threads.pop(task_id, None)

    def set_max_threads(self, max_threads: int) -> None:
        """设置最大线程数"""
        self._thread_pool.setMaxThreadCount(max_threads)


class PerformanceOptimizer(QObject):
    """增强的性能优化器 - 整合所有优化功能"""

    # 信号定义
    optimization_complete = pyqtSignal(dict)  # 优化完成信号
    performance_report = pyqtSignal(dict)  # 性能报告信号
    performance_alert = pyqtSignal(str, float, float)  # 资源类型, 当前值, 限制值
    memory_warning = pyqtSignal(str, int)  # 警告信息, 内存使用量
    cleanup_completed = pyqtSignal()  # 清理完成

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # 初始化组件
        self._monitor = PerformanceMonitor(self)
        self._memory_optimizer = MemoryOptimizer(self)
        self._thread_manager = ThreadManager()
        self.memory_tracker = MemoryTracker()
        self.cache_manager = CacheManager()

        # 性能配置
        self.profiles = self._create_default_profiles()
        self.current_profile = self.profiles['balanced']

        # 性能统计
        self.performance_stats = defaultdict(list)
        self.optimization_history = []

        # 监控设置
        self.monitoring_enabled = False
        self.auto_cleanup_enabled = True

        # 连接信号
        self._monitor.performance_warning.connect(self._on_performance_warning)
        self._memory_optimizer.memory_optimized.connect(self._on_memory_optimized)

        # 定时器
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._periodic_cleanup)

        # 自动优化定时器
        self._auto_optimize_timer = QTimer()
        self._auto_optimize_timer.timeout.connect(self._auto_optimize)

    def _create_default_profiles(self) -> Dict[str, PerformanceProfile]:
        """创建默认性能配置文件"""
        return {
            'power_saver': PerformanceProfile(
                name="省电模式",
                level=PerformanceLevel.LOW,
                max_memory_usage=2048,  # 2GB
                max_cpu_usage=50.0,
                enable_gpu_acceleration=False,
                enable_multithreading=False,
                cache_size=256,  # 256MB
                background_processing=False,
                auto_cleanup=True,
                cleanup_interval=300,
                description="最低能耗模式，适合电池供电场景"
            ),
            'balanced': PerformanceProfile(
                name="平衡模式",
                level=PerformanceLevel.MEDIUM,
                max_memory_usage=4096,  # 4GB
                max_cpu_usage=75.0,
                enable_gpu_acceleration=True,
                enable_multithreading=True,
                cache_size=512,  # 512MB
                background_processing=True,
                auto_cleanup=True,
                cleanup_interval=180,
                description="平衡性能和能耗的默认模式"
            ),
            'performance': PerformanceProfile(
                name="高性能模式",
                level=PerformanceLevel.HIGH,
                max_memory_usage=8192,  # 8GB
                max_cpu_usage=90.0,
                enable_gpu_acceleration=True,
                enable_multithreading=True,
                cache_size=1024,  # 1GB
                background_processing=True,
                auto_cleanup=True,
                cleanup_interval=120,
                description="高性能模式，适合专业视频编辑"
            ),
            'maximum': PerformanceProfile(
                name="最高性能模式",
                level=PerformanceLevel.MAXIMUM,
                max_memory_usage=16384,  # 16GB
                max_cpu_usage=100.0,
                enable_gpu_acceleration=True,
                enable_multithreading=True,
                cache_size=2048,  # 2GB
                background_processing=True,
                auto_cleanup=False,
                cleanup_interval=60,
                description="最高性能模式，最大化资源利用"
            )
        }

    def set_performance_profile(self, profile_name: str):
        """设置性能配置文件"""
        if profile_name not in self.profiles:
            logger.error(f"未知的性能配置文件: {profile_name}")
            return False

        self.current_profile = self.profiles[profile_name]

        # 应用配置
        self._apply_profile_settings()

        logger.info(f"性能配置文件已切换到: {profile_name}")
        return True

    def _apply_profile_settings(self):
        """应用性能配置文件设置"""
        profile = self.current_profile

        # 设置缓存大小
        self.cache_manager.max_size = profile.cache_size * 1024 * 1024

        # 配置清理定时器
        if profile.auto_cleanup:
            self.cleanup_timer.start(profile.cleanup_interval * 1000)
        else:
            self.cleanup_timer.stop()

    def start_monitoring(self, interval_ms: int = 1000) -> None:
        """开始监控"""
        if self.monitoring_enabled:
            return

        # 启动内存跟踪
        self.memory_tracker.start_tracking()

        # 启动原有监控
        self._monitor.start_monitoring(interval_ms)
        self._auto_optimize_timer.start(30000)  # 每30秒检查一次

        self.monitoring_enabled = True
        logger.info("增强性能优化监控已启动")

    def stop_monitoring(self) -> None:
        """停止监控"""
        if not self.monitoring_enabled:
            return

        # 停止内存跟踪
        self.memory_tracker.stop_tracking()

        # 停止原有监控
        self._monitor.stop_monitoring()
        self._auto_optimize_timer.stop()
        self.cleanup_timer.stop()

        self.monitoring_enabled = False
        logger.info("增强性能优化监控已停止")

    def _periodic_cleanup(self):
        """定期清理"""
        if not self.auto_cleanup_enabled:
            return

        try:
            cleanup_results = self.perform_cleanup()
            self.optimization_history.append({
                'timestamp': time.time(),
                'type': 'periodic_cleanup',
                'results': cleanup_results
            })
            self.cleanup_completed.emit()
        except Exception as e:
            logger.error(f"定期清理失败: {e}")

    def perform_cleanup(self) -> Dict[str, Any]:
        """执行清理操作"""
        results = {
            'memory_before': 0,
            'memory_after': 0,
            'cache_cleared': 0,
            'objects_collected': 0,
            'time_taken': 0
        }

        start_time = time.time()

        # 记录清理前的内存使用
        process = psutil.Process()
        results['memory_before'] = process.memory_info().rss

        # 清理缓存
        cache_stats_before = self.cache_manager.get_cache_stats()
        self.cache_manager.clear_all()
        cache_stats_after = self.cache_manager.get_cache_stats()
        results['cache_cleared'] = cache_stats_before['total_size_mb'] - cache_stats_after['total_size_mb']

        # 强制垃圾回收
        collected = gc.collect()
        results['objects_collected'] = collected

        # 记录清理后的内存使用
        results['memory_after'] = process.memory_info().rss
        results['time_taken'] = time.time() - start_time

        logger.info(f"清理完成: 释放内存 {(results['memory_before'] - results['memory_after']) / 1024 / 1024:.2f} MB, "
                   f"清理缓存 {results['cache_cleared']:.2f} MB, "
                   f"回收对象 {results['objects_collected']} 个, "
                   f"耗时 {results['time_taken']:.2f} 秒")

        return results

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """优化内存使用"""
        optimization_results = {
            'actions_taken': [],
            'memory_saved': 0,
            'performance_impact': 'minimal'
        }

        try:
            # 拍摄内存快照
            self.memory_tracker.take_snapshot('before_optimization')

            # 执行清理
            cleanup_results = self.perform_cleanup()
            optimization_results['actions_taken'].append('cleanup')
            optimization_results['memory_saved'] += (cleanup_results['memory_before'] - cleanup_results['memory_after']) / 1024 / 1024

            # 优化缓存
            cache_stats = self.cache_manager.get_cache_stats()
            if cache_stats['usage_percent'] > 80:
                # 减少缓存大小
                self.cache_manager.max_size = int(self.cache_manager.max_size * 0.8)
                optimization_results['actions_taken'].append('cache_reduction')

            # 拍摄优化后快照
            self.memory_tracker.take_snapshot('after_optimization')

            # 比较快照
            comparison = self.memory_tracker.compare_snapshots('before_optimization', 'after_optimization')
            optimization_results['memory_analysis'] = comparison

            logger.info(f"内存优化完成: 节省 {optimization_results['memory_saved']:.2f} MB, "
                       f"执行操作: {optimization_results['actions_taken']}")

        except Exception as e:
            logger.error(f"内存优化失败: {e}")
            optimization_results['error'] = str(e)

        return optimization_results

    def get_enhanced_performance_report(self) -> Dict[str, Any]:
        """获取增强性能报告"""
        current_metrics = self._monitor.get_current_metrics()
        avg_metrics = self._monitor.get_average_metrics(300)  # 5分钟平均

        # 计算性能统计
        cpu_stats = self._calculate_stats(self.performance_stats['cpu'])
        memory_stats = self._calculate_stats(self.performance_stats['memory'])

        cache_stats = self.cache_manager.get_cache_stats()

        return {
            'current_profile': self.current_profile.name,
            'monitoring_enabled': self.monitoring_enabled,
            'current_metrics': {
                'cpu_percent': current_metrics.cpu_percent if current_metrics else 0,
                'memory_percent': current_metrics.memory_percent if current_metrics else 0,
                'memory_used_mb': current_metrics.memory_used_mb if current_metrics else 0,
            },
            'average_metrics': {
                'cpu_percent': avg_metrics.cpu_percent if avg_metrics else 0,
                'memory_percent': avg_metrics.memory_percent if avg_metrics else 0,
                'memory_used_mb': avg_metrics.memory_used_mb if avg_metrics else 0,
            },
            'cpu_stats': cpu_stats,
            'memory_stats': memory_stats,
            'cache_stats': cache_stats,
            'optimization_history': self.optimization_history[-10:],  # 最近10次优化
            'recommendations': self._generate_recommendations()
        }

    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """计算统计信息"""
        if not values:
            return {'avg': 0, 'min': 0, 'max': 0, 'std': 0}

        return {
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'std': (sum((x - sum(values) / len(values)) ** 2 for x in values) / len(values)) ** 0.5
        }

    def _generate_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        current_metrics = self._monitor.get_current_metrics()
        if not current_metrics:
            return recommendations

        # CPU建议
        if current_metrics.cpu_percent > 80:
            recommendations.append("CPU使用率过高，建议减少并行任务数量")

        # 内存建议
        if current_metrics.memory_percent > 80:
            recommendations.append("内存使用率过高，建议执行内存清理或关闭其他应用")

        # 缓存建议
        cache_stats = self.cache_manager.get_cache_stats()
        if cache_stats['usage_percent'] > 90:
            recommendations.append("缓存使用率过高，建议清理缓存或增加缓存大小")

        # 性能配置建议
        if self.current_profile.level == PerformanceLevel.LOW and current_metrics.cpu_percent < 30:
            recommendations.append("系统负载较低，可以切换到更高性能模式")

        return recommendations

    @contextmanager
    def performance_context(self, operation_name: str):
        """性能上下文管理器"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            # 记录性能数据
            self.performance_stats[f'operation_{operation_name}'].append({
                'execution_time': execution_time,
                'memory_delta': memory_delta,
                'timestamp': time.time()
            })

            logger.debug(f"操作 '{operation_name}' 耗时: {execution_time:.3f}s, "
                        f"内存变化: {memory_delta / 1024 / 1024:.2f} MB")

    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        self.memory_tracker.stop_tracking()
        self.cache_manager.clear_all()
        logger.info("增强性能优化器已清理")

    def _on_performance_warning(self, message: str) -> None:
        """处理性能警告"""
        logger.warning(f"性能警告: {message}")

        # 自动优化
        if "内存" in message and self._memory_optimizer.should_optimize():
            self._memory_optimizer.optimize_memory()

    def _on_memory_optimized(self, freed_mb: int) -> None:
        """处理内存优化完成"""
        logger.info(f"内存优化完成，释放了 {freed_mb} MB")

    def _auto_optimize(self) -> None:
        """自动优化"""
        # 内存优化
        if self._memory_optimizer.should_optimize():
            self._memory_optimizer.optimize_memory()

        # 清理线程
        self._thread_manager.clear_completed_threads()

    def get_monitor(self) -> PerformanceMonitor:
        """获取性能监控器"""
        return self._monitor

    def get_memory_optimizer(self) -> MemoryOptimizer:
        """获取内存优化器"""
        return self._memory_optimizer

    def get_thread_manager(self) -> ThreadManager:
        """获取线程管理器"""
        return self._thread_manager

    def get_memory_tracker(self) -> MemoryTracker:
        """获取内存跟踪器"""
        return self.memory_tracker

    def get_cache_manager(self) -> CacheManager:
        """获取缓存管理器"""
        return self.cache_manager


# 全局增强性能优化器实例
global_enhanced_performance_optimizer = PerformanceOptimizer()


def get_enhanced_performance_optimizer() -> PerformanceOptimizer:
    """获取全局增强性能优化器"""
    return global_enhanced_performance_optimizer


def start_enhanced_performance_monitoring(interval_ms: int = 1000) -> None:
    """开始增强性能监控"""
    global_enhanced_performance_optimizer.start_monitoring(interval_ms)


def stop_enhanced_performance_monitoring() -> None:
    """停止增强性能监控"""
    global_enhanced_performance_optimizer.stop_monitoring()


# 保持向后兼容的全局实例和函数
global_performance_optimizer = global_enhanced_performance_optimizer


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器"""
    return global_enhanced_performance_optimizer


def start_performance_monitoring(interval_ms: int = 1000) -> None:
    """开始性能监控"""
    global_enhanced_performance_optimizer.start_monitoring(interval_ms)


def stop_performance_monitoring() -> None:
    """停止性能监控"""
    global_enhanced_performance_optimizer.stop_monitoring()