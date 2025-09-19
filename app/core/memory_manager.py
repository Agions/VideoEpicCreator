#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内存管理模块 - 专门针对视频处理的内存优化
提供智能内存分配、缓存管理和垃圾回收功能
"""

import os
import gc
import psutil
import logging
import threading
import time
import weakref
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from contextlib import contextmanager

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """内存优先级"""
    LOW = 1      # 低优先级，可以优先释放
    MEDIUM = 2   # 中等优先级
    HIGH = 3     # 高优先级，尽量保留
    CRITICAL = 4 # 关键优先级，不自动释放


class MemoryUnit(Enum):
    """内存单位"""
    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024


@dataclass
class MemoryBlock:
    """内存块信息"""
    id: str
    size: int
    priority: MemoryPriority
    data: Any
    created_time: float
    last_access_time: float
    access_count: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def touch(self):
        """更新访问时间"""
        self.last_access_time = time.time()
        self.access_count += 1


@dataclass
class MemoryPool:
    """内存池"""
    name: str
    total_size: int
    used_size: int = 0
    blocks: Dict[str, MemoryBlock] = field(default_factory=dict)
    priority_distribution: Dict[MemoryPriority, int] = field(default_factory=dict)

    def __post_init__(self):
        for priority in MemoryPriority:
            self.priority_distribution[priority] = 0


class MemoryManager(QObject):
    """内存管理器 - 专门针对视频处理优化"""

    # 信号定义
    memory_warning = pyqtSignal(str, int, int)  # 警告类型, 当前值, 阈值
    pool_overflow = pyqtSignal(str, int, int)  # 池名称, 当前大小, 最大大小
    memory_freed = pyqtSignal(int, str)  # 释放的内存量, 操作描述
    allocation_failed = pyqtSignal(str, int)  # 操作描述, 请求大小

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # 内存池
        self.pools: Dict[str, MemoryPool] = {}
        self._create_default_pools()

        # 全局设置
        self.global_memory_limit = 8 * MemoryUnit.GB.value  # 默认8GB
        self.warning_threshold = 0.8  # 80%警告阈值
        self.critical_threshold = 0.95  # 95%严重阈值

        # 监控设置
        self.monitoring_enabled = False
        self.auto_cleanup_enabled = True
        self.cleanup_interval = 60  # 秒

        # 统计信息
        self.allocation_history = deque(maxlen=1000)
        self.cleanup_history = deque(maxlen=100)
        self.peak_memory_usage = 0

        # 线程锁
        self._lock = threading.RLock()

        # 定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_memory)
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._auto_cleanup)

        # 弱引用缓存
        self.weak_refs = weakref.WeakValueDictionary()

    def _create_default_pools(self):
        """创建默认内存池"""
        # 视频帧池 - 高优先级，用于当前处理
        self.pools['video_frames'] = MemoryPool(
            name="video_frames",
            total_size=2 * MemoryUnit.GB.value
        )

        # 预览缓存池 - 中等优先级，用于预览
        self.pools['preview_cache'] = MemoryPool(
            name="preview_cache",
            total_size=1 * MemoryUnit.GB.value
        )

        # 特效处理池 - 中等优先级，用于特效处理
        self.pools['effects_processing'] = MemoryPool(
            name="effects_processing",
            total_size=1 * MemoryUnit.GB.value
        )

        # AI模型池 - 高优先级，用于AI模型
        self.pools['ai_models'] = MemoryPool(
            name="ai_models",
            total_size=2 * MemoryUnit.GB.value
        )

        # 临时数据池 - 低优先级，用于临时数据
        self.pools['temp_data'] = MemoryPool(
            name="temp_data",
            total_size=512 * MemoryUnit.MB.value
        )

        # 缩略图池 - 低优先级，用于缩略图
        self.pools['thumbnails'] = MemoryPool(
            name="thumbnails",
            total_size=256 * MemoryUnit.MB.value
        )

    def start_monitoring(self, interval_ms: int = 5000):
        """开始内存监控"""
        if self.monitoring_enabled:
            return

        self.monitor_timer.start(interval_ms)
        if self.auto_cleanup_enabled:
            self.cleanup_timer.start(self.cleanup_interval * 1000)
        self.monitoring_enabled = True
        logger.info("内存管理器监控已启动")

    def stop_monitoring(self):
        """停止内存监控"""
        self.monitor_timer.stop()
        self.cleanup_timer.stop()
        self.monitoring_enabled = False
        logger.info("内存管理器监控已停止")

    def allocate_memory(self, pool_name: str, size: int, data: Any,
                       priority: MemoryPriority = MemoryPriority.MEDIUM,
                       description: str = "", tags: List[str] = None) -> Optional[str]:
        """分配内存"""
        with self._lock:
            pool = self.pools.get(pool_name)
            if not pool:
                logger.error(f"未知的内存池: {pool_name}")
                return None

            # 检查池空间
            if pool.used_size + size > pool.total_size:
                # 尝试清理空间
                if not self._cleanup_pool(pool, size):
                    self.pool_overflow.emit(pool_name, pool.used_size, pool.total_size)
                    self.allocation_failed.emit(f"池 {pool_name} 空间不足", size)
                    return None

            # 检查全局限制
            total_used = sum(p.used_size for p in self.pools.values())
            if total_used + size > self.global_memory_limit:
                if not self._cleanup_global(size):
                    self.memory_warning.emit("global_limit", total_used, self.global_memory_limit)
                    self.allocation_failed.emit("全局内存限制", size)
                    return None

            # 创建内存块
            block_id = f"{pool_name}_{int(time.time() * 1000000)}_{len(pool.blocks)}"
            block = MemoryBlock(
                id=block_id,
                size=size,
                priority=priority,
                data=data,
                created_time=time.time(),
                last_access_time=time.time(),
                description=description,
                tags=tags or []
            )

            # 添加到池
            pool.blocks[block_id] = block
            pool.used_size += size
            pool.priority_distribution[priority] += 1

            # 记录分配历史
            self.allocation_history.append({
                'timestamp': time.time(),
                'pool': pool_name,
                'size': size,
                'block_id': block_id,
                'operation': 'allocate'
            })

            # 更新峰值内存
            if total_used + size > self.peak_memory_usage:
                self.peak_memory_usage = total_used + size

            logger.debug(f"内存分配成功: {block_id}, 大小: {size / MemoryUnit.MB.value:.2f} MB")
            return block_id

    def deallocate_memory(self, block_id: str) -> bool:
        """释放内存"""
        with self._lock:
            # 查找内存块
            pool_name, block = self._find_block(block_id)
            if not block:
                logger.warning(f"未找到内存块: {block_id}")
                return False

            # 从池中移除
            pool = self.pools[pool_name]
            del pool.blocks[block_id]
            pool.used_size -= block.size
            pool.priority_distribution[block.priority] -= 1

            # 记录释放历史
            self.allocation_history.append({
                'timestamp': time.time(),
                'pool': pool_name,
                'size': block.size,
                'block_id': block_id,
                'operation': 'deallocate'
            })

            # 清理数据
            if hasattr(block.data, 'close'):
                block.data.close()
            elif hasattr(block.data, 'release'):
                block.data.release()
            elif isinstance(block.data, np.ndarray):
                del block.data

            self.memory_freed.emit(block.size, f"释放块 {block_id}")
            logger.debug(f"内存释放成功: {block_id}, 大小: {block.size / MemoryUnit.MB.value:.2f} MB")
            return True

    def access_memory(self, block_id: str) -> Optional[Any]:
        """访问内存块"""
        with self._lock:
            pool_name, block = self._find_block(block_id)
            if not block:
                return None

            block.touch()
            return block.data

    def _find_block(self, block_id: str) -> Tuple[Optional[str], Optional[MemoryBlock]]:
        """查找内存块"""
        for pool_name, pool in self.pools.items():
            if block_id in pool.blocks:
                return pool_name, pool.blocks[block_id]
        return None, None

    def _cleanup_pool(self, pool: MemoryPool, required_size: int) -> bool:
        """清理池空间"""
        # 按优先级和LRU策略清理
        blocks_to_remove = []

        # 收集所有块并排序
        all_blocks = list(pool.blocks.values())
        all_blocks.sort(key=lambda b: (
            b.priority.value,  # 优先级低的先清理
            b.last_access_time,  # 最久未访问的先清理
            b.access_count  # 访问次数少的先清理
        ))

        # 选择要清理的块
        freed_size = 0
        for block in all_blocks:
            if freed_size >= required_size:
                break
            if block.priority != MemoryPriority.CRITICAL:  # 不清理关键块
                blocks_to_remove.append(block.id)
                freed_size += block.size

        # 执行清理
        for block_id in blocks_to_remove:
            self.deallocate_memory(block_id)

        return freed_size >= required_size

    def _cleanup_global(self, required_size: int) -> bool:
        """全局清理"""
        total_freed = 0

        # 按优先级从低到高清理各个池
        for pool_name in ['temp_data', 'thumbnails', 'preview_cache', 'effects_processing']:
            if total_freed >= required_size:
                break
            pool = self.pools.get(pool_name)
            if pool:
                # 清理该池的50%空间
                target_size = pool.used_size * 0.5
                self._cleanup_pool(pool, target_size)
                total_freed += pool.used_size - target_size

        return total_freed >= required_size

    def _monitor_memory(self):
        """监控内存使用"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # 检查警告阈值
            if memory_percent > self.warning_threshold * 100:
                self.memory_warning.emit(
                    "process_memory",
                    memory_info.rss,
                    int(self.warning_threshold * psutil.virtual_memory().total)
                )

            # 检查各个池的使用情况
            for pool_name, pool in self.pools.items():
                usage_percent = pool.used_size / pool.total_size
                if usage_percent > 0.9:  # 90%使用率
                    self.pool_overflow.emit(
                        pool_name,
                        pool.used_size,
                        pool.total_size
                    )

        except Exception as e:
            logger.error(f"内存监控错误: {e}")

    def _auto_cleanup(self):
        """自动清理"""
        if not self.auto_cleanup_enabled:
            return

        try:
            cleanup_results = self.perform_cleanup()
            self.cleanup_history.append({
                'timestamp': time.time(),
                'type': 'auto_cleanup',
                'results': cleanup_results
            })
        except Exception as e:
            logger.error(f"自动清理失败: {e}")

    def perform_cleanup(self) -> Dict[str, Any]:
        """执行清理操作"""
        results = {
            'memory_before': 0,
            'memory_after': 0,
            'blocks_freed': 0,
            'pools_cleaned': [],
            'time_taken': 0
        }

        start_time = time.time()

        # 获取进程内存信息
        process = psutil.Process()
        results['memory_before'] = process.memory_info().rss

        # 清理各个池
        for pool_name, pool in self.pools.items():
            if pool.used_size > pool.total_size * 0.7:  # 70%使用率时清理
                before_size = pool.used_size
                target_size = pool.total_size * 0.5
                self._cleanup_pool(pool, target_size)
                after_size = pool.used_size

                if before_size > after_size:
                    results['pools_cleaned'].append({
                        'pool': pool_name,
                        'freed': before_size - after_size
                    })

        # 强制垃圾回收
        collected = gc.collect()
        results['memory_after'] = process.memory_info().rss
        results['time_taken'] = time.time() - start_time

        # 计算释放的块数
        for pool_result in results['pools_cleaned']:
            results['blocks_freed'] += len([
                b for b in self.allocation_history[-100:]
                if b['operation'] == 'deallocate' and
                b['timestamp'] > start_time
            ])

        logger.info(f"内存清理完成: 释放 {(results['memory_before'] - results['memory_after']) / 1024 / 1024:.2f} MB, "
                   f"清理 {len(results['pools_cleaned'])} 个池, "
                   f"耗时 {results['time_taken']:.2f} 秒")

        return results

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        process = psutil.Process()
        memory_info = process.memory_info()

        # 池统计
        pool_stats = {}
        for pool_name, pool in self.pools.items():
            pool_stats[pool_name] = {
                'total_size_mb': pool.total_size / MemoryUnit.MB.value,
                'used_size_mb': pool.used_size / MemoryUnit.MB.value,
                'usage_percent': (pool.used_size / pool.total_size) * 100,
                'block_count': len(pool.blocks),
                'priority_distribution': {
                    priority.name: count
                    for priority, count in pool.priority_distribution.items()
                }
            }

        # 全局统计
        total_used = sum(p.used_size for p in self.pools.values())
        total_limit = sum(p.total_size for p in self.pools.values())

        return {
            'timestamp': time.time(),
            'process_memory_mb': memory_info.rss / MemoryUnit.MB.value,
            'process_memory_percent': process.memory_percent(),
            'peak_memory_usage_mb': self.peak_memory_usage / MemoryUnit.MB.value,
            'global_limit_mb': self.global_memory_limit / MemoryUnit.MB.value,
            'total_used_mb': total_used / MemoryUnit.MB.value,
            'total_limit_mb': total_limit / MemoryUnit.MB.value,
            'global_usage_percent': (total_used / total_limit) * 100,
            'pools': pool_stats,
            'monitoring_enabled': self.monitoring_enabled,
            'auto_cleanup_enabled': self.auto_cleanup_enabled
        }

    def optimize_for_video_processing(self):
        """为视频处理优化内存"""
        with self._lock:
            # 释放低优先级池的内存
            low_priority_pools = ['temp_data', 'thumbnails']
            for pool_name in low_priority_pools:
                pool = self.pools.get(pool_name)
                if pool:
                    # 释放80%的空间
                    target_size = pool.total_size * 0.2
                    self._cleanup_pool(pool, target_size)

            # 压缩预览缓存
            preview_pool = self.pools.get('preview_cache')
            if preview_pool and preview_pool.used_size > preview_pool.total_size * 0.8:
                target_size = preview_pool.total_size * 0.4
                self._cleanup_pool(preview_pool, target_size)

            logger.info("视频处理内存优化完成")

    def create_video_frame_buffer(self, width: int, height: int, channels: int = 3,
                                 frame_count: int = 1) -> Optional[str]:
        """创建视频帧缓冲区"""
        # 计算所需内存
        frame_size = width * height * channels * 4  # 假设4字节每像素
        total_size = frame_size * frame_count

        # 分配内存
        buffer_id = self.allocate_memory(
            'video_frames',
            total_size,
            np.zeros((frame_count, height, width, channels), dtype=np.uint8),
            priority=MemoryPriority.HIGH,
            description=f"视频帧缓冲区 {width}x{height}x{channels}x{frame_count}",
            tags=['video_frame', 'buffer']
        )

        return buffer_id

    def get_video_frame(self, buffer_id: str, frame_index: int = 0) -> Optional[np.ndarray]:
        """获取视频帧"""
        buffer = self.access_memory(buffer_id)
        if buffer is not None and isinstance(buffer, np.ndarray):
            if frame_index < len(buffer):
                return buffer[frame_index]
        return None

    def cleanup_old_frames(self, max_age_seconds: int = 300):
        """清理旧的帧数据"""
        current_time = time.time()
        blocks_to_remove = []

        for pool_name, pool in self.pools.items():
            for block_id, block in pool.blocks.items():
                if 'video_frame' in block.tags:
                    if current_time - block.last_access_time > max_age_seconds:
                        blocks_to_remove.append(block_id)

        for block_id in blocks_to_remove:
            self.deallocate_memory(block_id)

        logger.info(f"清理了 {len(blocks_to_remove)} 个旧帧")

    @contextmanager
    def memory_context(self, pool_name: str, size: int, priority: MemoryPriority = MemoryPriority.MEDIUM):
        """内存上下文管理器"""
        block_id = None
        try:
            # 分配内存
            block_id = self.allocate_memory(pool_name, size, None, priority)
            if block_id is None:
                raise MemoryError("内存分配失败")

            yield block_id

        finally:
            # 释放内存
            if block_id:
                self.deallocate_memory(block_id)

    def set_pool_size(self, pool_name: str, new_size: int):
        """设置池大小"""
        with self._lock:
            pool = self.pools.get(pool_name)
            if not pool:
                logger.error(f"未知的内存池: {pool_name}")
                return False

            if new_size < pool.used_size:
                # 需要先清理空间
                if not self._cleanup_pool(pool, pool.used_size - new_size):
                    logger.error(f"无法缩小池 {pool_name} 到 {new_size} 字节")
                    return False

            pool.total_size = new_size
            logger.info(f"池 {pool_name} 大小已设置为 {new_size / MemoryUnit.MB.value:.2f} MB")
            return True

    def get_pool_info(self, pool_name: str) -> Optional[Dict[str, Any]]:
        """获取池信息"""
        pool = self.pools.get(pool_name)
        if not pool:
            return None

        return {
            'name': pool.name,
            'total_size_mb': pool.total_size / MemoryUnit.MB.value,
            'used_size_mb': pool.used_size / MemoryUnit.MB.value,
            'usage_percent': (pool.used_size / pool.total_size) * 100,
            'block_count': len(pool.blocks),
            'priority_distribution': {
                priority.name: count
                for priority, count in pool.priority_distribution.items()
            }
        }

    def cleanup(self):
        """清理所有内存"""
        with self._lock:
            # 停止监控
            self.stop_monitoring()

            # 清理所有池
            for pool_name, pool in self.pools.items():
                block_ids = list(pool.blocks.keys())
                for block_id in block_ids:
                    self.deallocate_memory(block_id)

            # 清理历史记录
            self.allocation_history.clear()
            self.cleanup_history.clear()

            # 强制垃圾回收
            gc.collect()

            logger.info("内存管理器已完全清理")


# 全局内存管理器实例
global_memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """获取全局内存管理器"""
    return global_memory_manager


def start_memory_monitoring(interval_ms: int = 5000):
    """开始内存监控"""
    global_memory_manager.start_monitoring(interval_ms)


def stop_memory_monitoring():
    """停止内存监控"""
    global_memory_manager.stop_monitoring()