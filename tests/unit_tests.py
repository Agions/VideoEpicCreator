#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试模块 - 测试各个组件的独立功能
"""

import os
import sys
import unittest
import time
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# 添加应用根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtTest import QSignalSpy

# 导入要测试的模块
from app.config.settings_manager import SettingsManager
from app.core.service_container import ServiceContainer
from app.core.performance_optimizer import (
    PerformanceLevel, PerformanceProfile, get_enhanced_performance_optimizer
)
from app.core.memory_manager import MemoryManager, MemoryPriority
from app.ai.interfaces import IAIService, IAIModelProvider
from app.core.project import Project
from app.ui.unified_theme_system import UnifiedThemeManager, ThemeType


class TestSettingsManager(unittest.TestCase):
    """设置管理器单元测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = os.path.join(self.temp_dir, "test_settings.json")

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def test_01_settings_manager_creation(self):
        """测试设置管理器创建"""
        settings_manager = SettingsManager(self.settings_file)
        self.assertIsNotNone(settings_manager)

    def test_02_save_and_load_settings(self):
        """测试保存和加载设置"""
        settings_manager = SettingsManager(self.settings_file)

        # 保存设置
        test_settings = {
            "ui.theme": "dark",
            "performance.memory_limit": 8192,
            "ai.default_model": "gpt-4"
        }

        for key, value in test_settings.items():
            settings_manager.set_setting(key, value)

        # 创建新的设置管理器实例
        new_settings_manager = SettingsManager(self.settings_file)

        # 验证设置是否正确加载
        for key, expected_value in test_settings.items():
            actual_value = new_settings_manager.get_setting(key)
            self.assertEqual(actual_value, expected_value)

    def test_03_default_values(self):
        """测试默认值"""
        settings_manager = SettingsManager(self.settings_file)

        # 测试不存在的键返回默认值
        default_value = settings_manager.get_setting("nonexistent.key", "default")
        self.assertEqual(default_value, "default")

        # 测试不存在的键返回None
        none_value = settings_manager.get_setting("nonexistent.key")
        self.assertIsNone(none_value)


class TestServiceContainer(unittest.TestCase):
    """服务容器单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.container = ServiceContainer()

    def test_01_register_and_get_service(self):
        """测试注册和获取服务"""
        # 创建测试服务
        test_service = Mock()

        # 注册服务
        self.container.register('test_service', test_service)

        # 获取服务
        retrieved_service = self.container.get('test_service')

        # 验证服务是否正确
        self.assertEqual(retrieved_service, test_service)

    def test_02_service_not_found(self):
        """测试服务不存在的情况"""
        # 获取不存在的服务
        service = self.container.get('nonexistent_service')
        self.assertIsNone(service)

    def test_03_duplicate_registration(self):
        """测试重复注册服务"""
        # 创建两个测试服务
        service1 = Mock()
        service2 = Mock()

        # 注册第一个服务
        self.container.register('test_service', service1)

        # 注册第二个服务（应该覆盖第一个）
        self.container.register('test_service', service2)

        # 获取服务应该返回第二个服务
        retrieved_service = self.container.get('test_service')
        self.assertEqual(retrieved_service, service2)

    def test_04_list_services(self):
        """测试列出所有服务"""
        # 注册多个服务
        services = {
            'service1': Mock(),
            'service2': Mock(),
            'service3': Mock()
        }

        for name, service in services.items():
            self.container.register(name, service)

        # 列出所有服务
        service_list = self.container.list_services()

        # 验证服务列表
        self.assertEqual(len(service_list), 3)
        for name in services.keys():
            self.assertIn(name, service_list)


class TestPerformanceOptimizer(unittest.TestCase):
    """性能优化器单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.optimizer = get_enhanced_performance_optimizer()

    def test_01_performance_levels(self):
        """测试性能级别"""
        # 验证性能级别枚举
        self.assertEqual(PerformanceLevel.LOW.value, 1)
        self.assertEqual(PerformanceLevel.MEDIUM.value, 2)
        self.assertEqual(PerformanceLevel.HIGH.value, 3)
        self.assertEqual(PerformanceLevel.MAXIMUM.value, 4)

    def test_02_performance_profiles(self):
        """测试性能配置文件"""
        # 验证默认配置文件
        profiles = self.optimizer.profiles
        self.assertIn('balanced', profiles)
        self.assertIn('power_saver', profiles)
        self.assertIn('performance', profiles)
        self.assertIn('maximum', profiles)

        # 验证平衡模式配置
        balanced_profile = profiles['balanced']
        self.assertEqual(balanced_profile.level, PerformanceLevel.MEDIUM)
        self.assertEqual(balanced_profile.name, '平衡模式')
        self.assertTrue(balanced_profile.enable_gpu_acceleration)

    def test_03_set_performance_profile(self):
        """测试设置性能配置文件"""
        # 切换到省电模式
        success = self.optimizer.set_performance_profile('power_saver')
        self.assertTrue(success)

        # 验证当前配置文件
        current_profile = self.optimizer.current_profile
        self.assertEqual(current_profile.name, '省电模式')
        self.assertEqual(current_profile.level, PerformanceLevel.LOW)
        self.assertFalse(current_profile.enable_gpu_acceleration)

    def test_04_invalid_profile(self):
        """测试无效配置文件"""
        # 尝试设置不存在的配置文件
        success = self.optimizer.set_performance_profile('invalid_profile')
        self.assertFalse(success)

    def test_05_memory_tracker(self):
        """测试内存跟踪器"""
        memory_tracker = self.optimizer.get_memory_tracker()

        # 启动跟踪
        memory_tracker.start_tracking()
        self.assertTrue(memory_tracker.enabled)

        # 拍摄快照
        memory_tracker.take_snapshot('test_snapshot')
        self.assertIn('test_snapshot', memory_tracker.snapshots)

        # 停止跟踪
        memory_tracker.stop_tracking()
        self.assertFalse(memory_tracker.enabled)
        self.assertEqual(len(memory_tracker.snapshots), 0)

    def test_06_cache_manager(self):
        """测试缓存管理器"""
        cache_manager = self.optimizer.get_cache_manager()

        # 添加缓存
        test_cache = {'key1': 'value1', 'key2': 'value2'}
        cache_manager.add_cache('test_cache', test_cache)

        # 获取缓存
        retrieved_cache = cache_manager.get_cache('test_cache')
        self.assertEqual(retrieved_cache, test_cache)

        # 获取缓存统计
        stats = cache_manager.get_cache_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_size_mb', stats)
        self.assertIn('cache_count', stats)

        # 清理缓存
        cache_manager.clear_all()
        stats = cache_manager.get_cache_stats()
        self.assertEqual(stats['cache_count'], 0)


class TestMemoryManager(unittest.TestCase):
    """内存管理器单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.memory_manager = MemoryManager()

    def test_01_memory_pools_creation(self):
        """测试内存池创建"""
        # 验证默认内存池
        pools = self.memory_manager.pools
        self.assertIn('video_frames', pools)
        self.assertIn('preview_cache', pools)
        self.assertIn('effects_processing', pools)
        self.assertIn('ai_models', pools)
        self.assertIn('temp_data', pools)
        self.assertIn('thumbnails', pools)

    def test_02_memory_allocation(self):
        """测试内存分配"""
        # 分配内存
        test_data = b'test_data' * 100
        block_id = self.memory_manager.allocate_memory(
            'temp_data',
            len(test_data),
            test_data,
            MemoryPriority.MEDIUM,
            '测试数据'
        )

        # 验证分配成功
        self.assertIsNotNone(block_id)

        # 验证数据正确存储
        retrieved_data = self.memory_manager.access_memory(block_id)
        self.assertEqual(retrieved_data, test_data)

    def test_03_memory_deallocation(self):
        """测试内存释放"""
        # 分配内存
        test_data = b'test_data' * 100
        block_id = self.memory_manager.allocate_memory(
            'temp_data',
            len(test_data),
            test_data,
            MemoryPriority.MEDIUM,
            '测试数据'
        )

        # 释放内存
        success = self.memory_manager.deallocate_memory(block_id)
        self.assertTrue(success)

        # 验证内存已释放
        retrieved_data = self.memory_manager.access_memory(block_id)
        self.assertIsNone(retrieved_data)

    def test_04_memory_statistics(self):
        """测试内存统计"""
        # 获取初始统计
        stats = self.memory_manager.get_memory_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('pools', stats)
        self.assertIn('global_limit_mb', stats)
        self.assertIn('total_used_mb', stats)

        # 分配一些内存
        test_data = b'test_data' * 1000
        self.memory_manager.allocate_memory(
            'temp_data',
            len(test_data),
            test_data,
            MemoryPriority.MEDIUM,
            '测试数据'
        )

        # 获取更新后的统计
        updated_stats = self.memory_manager.get_memory_stats()
        self.assertGreater(updated_stats['total_used_mb'], stats['total_used_mb'])

    def test_05_memory_cleanup(self):
        """测试内存清理"""
        # 分配多个内存块
        block_ids = []
        for i in range(5):
            test_data = f'test_data_{i}'.encode() * 100
            block_id = self.memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                MemoryPriority.LOW,
                f'测试数据{i}'
            )
            block_ids.append(block_id)

        # 执行清理
        cleanup_results = self.memory_manager.perform_cleanup()
        self.assertIsInstance(cleanup_results, dict)
        self.assertIn('memory_before', cleanup_results)
        self.assertIn('memory_after', cleanup_results)


class TestAIService(unittest.TestCase):
    """AI服务单元测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建模拟的AI服务
        self.ai_service = Mock(spec=IAIService)

    def test_01_ai_service_interface(self):
        """测试AI服务接口"""
        # 设置模拟方法
        self.ai_service.process_video.return_value = {"result": "success"}
        self.ai_service.generate_subtitles.return_value = ["字幕1", "字幕2"]
        self.ai_service.get_available_models.return_value = ["model1", "model2"]

        # 测试视频处理
        video_result = self.ai_service.process_video("test_video.mp4", {})
        self.assertEqual(video_result, {"result": "success"})

        # 测试字幕生成
        subtitle_result = self.ai_service.generate_subtitles("test_video.mp4", {})
        self.assertEqual(subtitle_result, ["字幕1", "字幕2"])

        # 测试获取模型列表
        models = self.ai_service.get_available_models()
        self.assertEqual(models, ["model1", "model2"])

    def test_02_ai_model_interface(self):
        """测试AI模型接口"""
        # 创建模拟的AI模型
        ai_model = Mock(spec=IAIModelProvider)

        # 设置模拟方法
        ai_model.generate_text.return_value = Mock(success=True, content="generated_text")
        ai_model.get_model_health.return_value = Mock(provider="test_provider", is_healthy=True)

        # 测试文本生成
        result = ai_model.generate_text("test_prompt")
        self.assertIsNotNone(result)

        # 测试获取模型健康状态
        health = ai_model.get_model_health()
        self.assertEqual(health.provider, "test_provider")
        self.assertTrue(health.is_healthy)


class TestProject(unittest.TestCase):
    """项目单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.project = Project("测试项目", "/test/path")

    def test_01_project_creation(self):
        """测试项目创建"""
        self.assertEqual(self.project.name, "测试项目")
        self.assertEqual(self.project.path, "/test/path")
        self.assertIsNotNone(self.project.created_at)
        self.assertIsNotNone(self.project.id)

    def test_02_project_modification(self):
        """测试项目修改"""
        # 修改项目名称
        self.project.name = "修改后的项目"
        self.assertEqual(self.project.name, "修改后的项目")

        # 修改项目路径
        self.project.path = "/new/test/path"
        self.assertEqual(self.project.path, "/new/test/path")

        # 验证修改时间已更新
        self.assertIsNotNone(self.project.modified_at)

    def test_03_project_metadata(self):
        """测试项目元数据"""
        # 添加元数据
        self.project.set_metadata("author", "test_author")
        self.project.set_metadata("description", "测试项目描述")
        self.project.set_metadata("version", "1.0")

        # 验证元数据
        self.assertEqual(self.project.get_metadata("author"), "test_author")
        self.assertEqual(self.project.get_metadata("description"), "测试项目描述")
        self.assertEqual(self.project.get_metadata("version"), "1.0")

        # 测试不存在的元数据
        nonexistent = self.project.get_metadata("nonexistent", "default")
        self.assertEqual(nonexistent, "default")


class TestThemeSystem(unittest.TestCase):
    """主题系统单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.theme_manager = UnifiedThemeManager()

    def test_01_theme_types(self):
        """测试主题类型"""
        # 验证主题类型枚举
        self.assertEqual(ThemeType.LIGHT.value, "light")
        self.assertEqual(ThemeType.DARK.value, "dark")
        self.assertEqual(ThemeType.AUTO.value, "auto")

    def test_02_theme_switching(self):
        """测试主题切换"""
        # 切换到浅色主题
        self.theme_manager.set_theme(ThemeType.LIGHT)
        colors = self.theme_manager.get_theme_colors()
        self.assertEqual(colors['theme_type'], 'light')

        # 切换到深色主题
        self.theme_manager.set_theme(ThemeType.DARK)
        colors = self.theme_manager.get_theme_colors()
        self.assertEqual(colors['theme_type'], 'dark')

    def test_03_theme_colors(self):
        """测试主题颜色"""
        # 设置深色主题
        self.theme_manager.set_theme(ThemeType.DARK)
        colors = self.theme_manager.get_theme_colors()

        # 验证必要的颜色属性
        required_colors = [
            'background', 'surface', 'primary', 'secondary',
            'text', 'text_secondary', 'border', 'accent',
            'success', 'warning', 'error', 'theme_type'
        ]

        for color_name in required_colors:
            self.assertIn(color_name, colors)
            self.assertIsInstance(colors[color_name], str)

    def test_04_invalid_theme(self):
        """测试无效主题"""
        # 尝试设置无效主题
        with self.assertRaises(Exception):
            self.theme_manager.set_theme("invalid_theme")


class TestSignalEmission(unittest.TestCase):
    """信号发射单元测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建QApplication实例（如果还没有）
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_01_signal_spy_creation(self):
        """测试信号间谍创建"""
        # 创建测试对象
        test_object = QObject()

        # 创建信号
        test_object.test_signal = pyqtSignal(str)

        # 创建信号间谍
        spy = QSignalSpy(test_object.test_signal)

        # 发射信号
        test_object.test_signal.emit("test")

        # 验证信号被捕获
        self.assertEqual(len(spy), 1)
        self.assertEqual(spy[0][0], "test")

    def test_02_signal_arguments(self):
        """测试信号参数"""
        # 创建测试对象
        test_object = QObject()

        # 创建多参数信号
        test_object.multi_signal = pyqtSignal(str, int, float)

        # 创建信号间谍
        spy = QSignalSpy(test_object.multi_signal)

        # 发射信号
        test_object.multi_signal.emit("test", 42, 3.14)

        # 验证信号参数
        self.assertEqual(len(spy), 1)
        self.assertEqual(spy[0][0], "test")
        self.assertEqual(spy[0][1], 42)
        self.assertEqual(spy[0][2], 3.14)


class TestErrorHandling(unittest.TestCase):
    """错误处理单元测试"""

    def test_01_exception_handling(self):
        """测试异常处理"""
        # 测试基本的异常处理
        def function_that_raises():
            raise ValueError("测试错误")

        with self.assertRaises(ValueError):
            function_that_raises()

    def test_02_mock_exception_handling(self):
        """测试模拟异常处理"""
        # 创建模拟对象
        mock_object = Mock()

        # 设置模拟对象抛出异常
        mock_object.method_that_raises.side_effect = RuntimeError("模拟错误")

        # 验证异常被正确抛出
        with self.assertRaises(RuntimeError):
            mock_object.method_that_raises()

    def test_03_exception_context(self):
        """测试异常上下文"""
        # 测试异常上下文信息
        try:
            raise ValueError("测试错误", {"additional": "info"})
        except ValueError as e:
            self.assertEqual(str(e), "测试错误")


class TestPerformanceBenchmark(unittest.TestCase):
    """性能基准测试"""

    def test_01_memory_allocation_speed(self):
        """测试内存分配速度"""
        memory_manager = MemoryManager()

        # 测试大量内存分配
        start_time = time.time()
        block_ids = []

        for i in range(100):
            test_data = f'test_data_{i}'.encode() * 1000
            block_id = memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                MemoryPriority.MEDIUM,
                f'基准测试{i}'
            )
            block_ids.append(block_id)

        end_time = time.time()
        allocation_time = end_time - start_time

        # 清理内存
        for block_id in block_ids:
            memory_manager.deallocate_memory(block_id)

        # 验证分配速度（应该在合理时间内完成）
        self.assertLess(allocation_time, 1.0)  # 应该在1秒内完成

    def test_02_service_access_speed(self):
        """测试服务访问速度"""
        container = ServiceContainer()

        # 注册服务
        test_service = Mock()
        container.register('benchmark_service', test_service)

        # 测试服务访问速度
        start_time = time.time()

        for _ in range(1000):
            service = container.get('benchmark_service')
            self.assertEqual(service, test_service)

        end_time = time.time()
        access_time = end_time - start_time

        # 验证访问速度（应该在合理时间内完成）
        self.assertLess(access_time, 0.1)  # 应该在0.1秒内完成


def run_unit_tests():
    """运行单元测试"""
    print("=" * 60)
    print("开始 CineAIStudio 单元测试")
    print("=" * 60)

    # 创建测试套件
    test_classes = [
        TestSettingsManager,
        TestServiceContainer,
        TestPerformanceOptimizer,
        TestMemoryManager,
        TestAIService,
        TestProject,
        TestThemeSystem,
        TestSignalEmission,
        TestErrorHandling,
        TestPerformanceBenchmark
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
    print("单元测试结果总结")
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
    success = run_unit_tests()
    sys.exit(0 if success else 1)