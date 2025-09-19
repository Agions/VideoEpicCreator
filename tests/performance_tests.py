#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能测试模块 - 测试系统性能和资源使用
"""

import os
import sys
import time
import psutil
import threading
import gc
import tracemalloc
import unittest
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock, patch

# 添加应用根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThreadPool, QRunnable

from app.core.performance_optimizer import get_enhanced_performance_optimizer
from app.core.memory_manager import get_memory_manager
from app.core.service_container import ServiceContainer
from app.config.settings_manager import SettingsManager


class PerformanceTestRunner:
    """性能测试运行器"""

    def __init__(self):
        self.results = {}
        self.process = psutil.Process()

    def measure_memory_usage(self, func, *args, **kwargs):
        """测量函数的内存使用"""
        # 启动内存跟踪
        tracemalloc.start()

        # 获取初始内存
        initial_memory = self.process.memory_info().rss

        # 执行函数
        result = func(*args, **kwargs)

        # 获取最终内存
        final_memory = self.process.memory_info().rss

        # 获取内存快照
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_usage = {
            'initial_memory_mb': initial_memory / 1024 / 1024,
            'final_memory_mb': final_memory / 1024 / 1024,
            'memory_delta_mb': (final_memory - initial_memory) / 1024 / 1024,
            'peak_memory_mb': peak / 1024 / 1024,
            'current_memory_mb': current / 1024 / 1024
        }

        return result, memory_usage

    def measure_execution_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time

        return result, execution_time

    def measure_cpu_usage(self, func, *args, **kwargs):
        """测量函数的CPU使用率"""
        # 获取初始CPU时间
        initial_cpu = self.process.cpu_times()

        # 执行函数
        result = func(*args, **kwargs)

        # 获取最终CPU时间
        final_cpu = self.process.cpu_times()

        cpu_usage = {
            'user_time': final_cpu.user - initial_cpu.user,
            'system_time': final_cpu.system - initial_cpu.system,
            'total_cpu_time': (final_cpu.user + final_cpu.system) - (initial_cpu.user + initial_cpu.system)
        }

        return result, cpu_usage

    def comprehensive_measure(self, func, *args, **kwargs):
        """综合测量函数性能"""
        # 测量执行时间
        result, execution_time = self.measure_execution_time(func, *args, **kwargs)

        # 测量内存使用
        _, memory_usage = self.measure_memory_usage(func, *args, **kwargs)

        # 测量CPU使用
        _, cpu_usage = self.measure_cpu_usage(func, *args, **kwargs)

        performance_data = {
            'execution_time': execution_time,
            'memory_usage': memory_usage,
            'cpu_usage': cpu_usage,
            'throughput': len(args) / execution_time if execution_time > 0 and args else 0
        }

        return result, performance_data


class ServiceContainerPerformanceTest(unittest.TestCase):
    """服务容器性能测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = PerformanceTestRunner()
        self.container = ServiceContainer()

    def test_01_service_registration_performance(self):
        """测试服务注册性能"""
        def register_services():
            for i in range(1000):
                service = Mock()
                self.container.register(f'service_{i}', service)

        result, performance_data = self.runner.comprehensive_measure(register_services)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 1.0)  # 应该在1秒内完成
        self.assertLess(performance_data['memory_usage']['memory_delta_mb'], 10)  # 内存增长应该小于10MB

        print(f"服务注册性能: {performance_data['execution_time']:.3f}s, "
              f"内存: {performance_data['memory_usage']['memory_delta_mb']:.2f}MB")

    def test_02_service_retrieval_performance(self):
        """测试服务检索性能"""
        # 预先注册服务
        for i in range(1000):
            service = Mock()
            self.container.register(f'service_{i}', service)

        def retrieve_services():
            for i in range(1000):
                service = self.container.get(f'service_{i}')
                self.assertIsNotNone(service)

        result, performance_data = self.runner.comprehensive_measure(retrieve_services)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 0.5)  # 应该在0.5秒内完成
        self.assertLess(performance_data['memory_usage']['memory_delta_mb'], 1)  # 内存增长应该很小

        print(f"服务检索性能: {performance_data['execution_time']:.3f}s, "
              f"内存: {performance_data['memory_usage']['memory_delta_mb']:.2f}MB")

    def test_03_concurrent_service_access(self):
        """测试并发服务访问性能"""
        # 注册一个服务
        test_service = Mock()
        self.container.register('concurrent_service', test_service)

        def access_service():
            for _ in range(100):
                service = self.container.get('concurrent_service')
                self.assertIsNotNone(service)

        def concurrent_access():
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(access_service) for _ in range(10)]
                for future in futures:
                    future.result()

        result, performance_data = self.runner.comprehensive_measure(concurrent_access)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 2.0)  # 应该在2秒内完成

        print(f"并发服务访问性能: {performance_data['execution_time']:.3f}s, "
              f"CPU时间: {performance_data['cpu_usage']['total_cpu_time']:.3f}s")


class MemoryManagerPerformanceTest(unittest.TestCase):
    """内存管理器性能测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = PerformanceTestRunner()
        self.memory_manager = get_memory_manager()

    def test_01_memory_allocation_performance(self):
        """测试内存分配性能"""
        def allocate_memory():
            block_ids = []
            for i in range(1000):
                test_data = f'test_data_{i}'.encode() * 100
                block_id = self.memory_manager.allocate_memory(
                    'temp_data',
                    len(test_data),
                    test_data,
                    description=f'性能测试{i}'
                )
                block_ids.append(block_id)
            return block_ids

        result, performance_data = self.runner.comprehensive_measure(allocate_memory)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 2.0)  # 应该在2秒内完成
        self.assertEqual(len(result), 1000)  # 应该分配1000个块

        print(f"内存分配性能: {performance_data['execution_time']:.3f}s, "
              f"内存: {performance_data['memory_usage']['memory_delta_mb']:.2f}MB")

        # 清理内存
        for block_id in result:
            self.memory_manager.deallocate_memory(block_id)

    def test_02_memory_cleanup_performance(self):
        """测试内存清理性能"""
        # 预先分配内存
        block_ids = []
        for i in range(500):
            test_data = f'test_data_{i}'.encode() * 100
            block_id = self.memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                description=f'清理测试{i}'
            )
            block_ids.append(block_id)

        def cleanup_memory():
            return self.memory_manager.perform_cleanup()

        result, performance_data = self.runner.comprehensive_measure(cleanup_memory)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 1.0)  # 应该在1秒内完成
        self.assertIn('memory_before', result)
        self.assertIn('memory_after', result)

        print(f"内存清理性能: {performance_data['execution_time']:.3f}s, "
              f"释放内存: {(result['memory_before'] - result['memory_after']) / 1024 / 1024:.2f}MB")

    def test_03_memory_access_performance(self):
        """测试内存访问性能"""
        # 预先分配内存
        block_ids = []
        for i in range(100):
            test_data = f'test_data_{i}'.encode() * 1000
            block_id = self.memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                description=f'访问测试{i}'
            )
            block_ids.append(block_id)

        def access_memory():
            for block_id in block_ids:
                data = self.memory_manager.access_memory(block_id)
                self.assertIsNotNone(data)

        result, performance_data = self.runner.comprehensive_measure(access_memory)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 0.1)  # 应该在0.1秒内完成

        print(f"内存访问性能: {performance_data['execution_time']:.3f}s")

        # 清理内存
        for block_id in block_ids:
            self.memory_manager.deallocate_memory(block_id)


class PerformanceOptimizerTest(unittest.TestCase):
    """性能优化器测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = PerformanceTestRunner()
        self.optimizer = get_enhanced_performance_optimizer()

    def test_01_profile_switching_performance(self):
        """测试配置文件切换性能"""
        def switch_profiles():
            profiles = ['power_saver', 'balanced', 'performance', 'maximum']
            for profile in profiles:
                self.optimizer.set_performance_profile(profile)

        result, performance_data = self.runner.comprehensive_measure(switch_profiles)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 0.1)  # 应该在0.1秒内完成

        print(f"配置文件切换性能: {performance_data['execution_time']:.3f}s")

    def test_02_cache_operations_performance(self):
        """测试缓存操作性能"""
        cache_manager = self.optimizer.get_cache_manager()

        def cache_operations():
            # 添加缓存
            for i in range(100):
                cache_data = {f'key_{j}': f'value_{j}' for j in range(10)}
                cache_manager.add_cache(f'cache_{i}', cache_data)

            # 访问缓存
            for i in range(100):
                cache = cache_manager.get_cache(f'cache_{i}')
                self.assertIsNotNone(cache)

        result, performance_data = self.runner.comprehensive_measure(cache_operations)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 1.0)  # 应该在1秒内完成

        print(f"缓存操作性能: {performance_data['execution_time']:.3f}s")

    def test_03_memory_tracking_performance(self):
        """测试内存跟踪性能"""
        memory_tracker = self.optimizer.get_memory_tracker()

        def memory_tracking():
            memory_tracker.start_tracking()

            # 拍摄快照
            for i in range(50):
                memory_tracker.take_snapshot(f'snapshot_{i}')

            # 比较快照
            for i in range(49):
                comparison = memory_tracker.compare_snapshots(f'snapshot_{i}', f'snapshot_{i+1}')
                self.assertIsInstance(comparison, dict)

            memory_tracker.stop_tracking()

        result, performance_data = self.runner.comprehensive_measure(memory_tracking)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 2.0)  # 应该在2秒内完成

        print(f"内存跟踪性能: {performance_data['execution_time']:.3f}s")


class ConcurrencyPerformanceTest(unittest.TestCase):
    """并发性能测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = PerformanceTestRunner()

    def test_01_thread_pool_performance(self):
        """测试线程池性能"""
        def cpu_task(x):
            # 模拟CPU密集型任务
            result = 0
            for i in range(1000):
                result += i * x
            return result

        def run_thread_pool():
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(cpu_task, i) for i in range(100)]
                results = [future.result() for future in futures]
            return results

        result, performance_data = self.runner.comprehensive_measure(run_thread_pool)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 2.0)  # 应该在2秒内完成
        self.assertEqual(len(result), 100)

        print(f"线程池性能: {performance_data['execution_time']:.3f}s, "
              f"CPU时间: {performance_data['cpu_usage']['total_cpu_time']:.3f}s")

    def test_02_process_pool_performance(self):
        """测试进程池性能"""
        def io_task(x):
            # 模拟IO密集型任务
            time.sleep(0.01)  # 模拟IO等待
            return x * 2

        def run_process_pool():
            with ProcessPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(io_task, i) for i in range(20)]
                results = [future.result() for future in futures]
            return results

        result, performance_data = self.runner.comprehensive_measure(run_process_pool)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 1.0)  # 应该在1秒内完成
        self.assertEqual(len(result), 20)

        print(f"进程池性能: {performance_data['execution_time']:.3f}s")

    def test_03_async_task_performance(self):
        """测试异步任务性能"""
        def async_task():
            results = []
            threads = []

            def worker(task_id):
                time.sleep(0.01)  # 模拟工作
                results.append(f'task_{task_id}_completed')

            # 创建并启动线程
            for i in range(50):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            return results

        result, performance_data = self.runner.comprehensive_measure(async_task)

        # 验证性能
        self.assertLess(performance_data['execution_time'], 1.0)  # 应该在1秒内完成
        self.assertEqual(len(result), 50)

        print(f"异步任务性能: {performance_data['execution_time']:.3f}s")


class MemoryLeakTest(unittest.TestCase):
    """内存泄漏测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = PerformanceTestRunner()
        self.initial_memory = psutil.Process().memory_info().rss

    def tearDown(self):
        """清理测试环境"""
        gc.collect()

    def test_01_service_container_memory_leak(self):
        """测试服务容器内存泄漏"""
        def repeated_operations():
            container = ServiceContainer()
            for i in range(1000):
                service = Mock()
                container.register(f'service_{i}', service)
                retrieved = container.get(f'service_{i}')
                self.assertIsNotNone(retrieved)

        # 多次执行操作
        for _ in range(10):
            repeated_operations()
            gc.collect()

        # 检查内存增长
        final_memory = psutil.Process().memory_info().rss
        memory_growth = (final_memory - self.initial_memory) / 1024 / 1024

        # 内存增长应该在合理范围内
        self.assertLess(memory_growth, 50)  # 应该小于50MB

        print(f"服务容器内存增长: {memory_growth:.2f}MB")

    def test_02_memory_manager_memory_leak(self):
        """测试内存管理器内存泄漏"""
        def repeated_memory_operations():
            memory_manager = get_memory_manager()
            block_ids = []

            # 分配内存
            for i in range(100):
                test_data = f'test_data_{i}'.encode() * 100
                block_id = memory_manager.allocate_memory(
                    'temp_data',
                    len(test_data),
                    test_data,
                    description=f'泄漏测试{i}'
                )
                block_ids.append(block_id)

            # 访问内存
            for block_id in block_ids:
                data = memory_manager.access_memory(block_id)
                self.assertIsNotNone(data)

            # 释放内存
            for block_id in block_ids:
                memory_manager.deallocate_memory(block_id)

        # 多次执行操作
        for _ in range(10):
            repeated_memory_operations()
            gc.collect()

        # 检查内存增长
        final_memory = psutil.Process().memory_info().rss
        memory_growth = (final_memory - self.initial_memory) / 1024 / 1024

        # 内存增长应该在合理范围内
        self.assertLess(memory_growth, 100)  # 应该小于100MB

        print(f"内存管理器内存增长: {memory_growth:.2f}MB")

    def test_03_gui_component_memory_leak(self):
        """测试GUI组件内存泄漏"""
        # 创建QApplication实例（如果还没有）
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()

        def create_gui_components():
            from PyQt6.QtWidgets import QLabel, QPushButton, QWidget, QVBoxLayout

            for i in range(100):
                widget = QWidget()
                layout = QVBoxLayout(widget)
                layout.addWidget(QLabel(f"Label {i}"))
                layout.addWidget(QPushButton(f"Button {i}"))

                # 组件使用后应该被垃圾回收
                widget.deleteLater()

        # 多次创建和销毁GUI组件
        for _ in range(5):
            create_gui_components()
            gc.collect()
            app.processEvents()

        # 检查内存增长
        final_memory = psutil.Process().memory_info().rss
        memory_growth = (final_memory - self.initial_memory) / 1024 / 1024

        # 内存增长应该在合理范围内
        self.assertLess(memory_growth, 20)  # 应该小于20MB

        print(f"GUI组件内存增长: {memory_growth:.2f}MB")


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("开始 CineAIStudio 性能测试")
    print("=" * 60)

    # 创建测试套件
    test_classes = [
        ServiceContainerPerformanceTest,
        MemoryManagerPerformanceTest,
        PerformanceOptimizerTest,
        ConcurrencyPerformanceTest,
        MemoryLeakTest
    ]

    test_suite = unittest.TestSuite()

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出结果
    print("\n" + "=" * 60)
    print("性能测试结果总结")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)