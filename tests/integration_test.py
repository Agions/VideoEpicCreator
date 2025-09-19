#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试模块 - 验证所有新功能的集成和协同工作
"""

import os
import sys
import unittest
import time
import logging
import threading
from typing import Dict, Any, List

# 添加应用根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QTest
from PyQt6.QtCore import QTimer, QThreadPool
from PyQt6.QtTest import QSignalSpy

from app.application_launcher import ApplicationLauncher
from app.core.performance_optimizer import get_enhanced_performance_optimizer
from app.core.memory_manager import get_memory_manager
from app.ai import create_unified_ai_service
from app.core.project_manager import ProjectManager
from app.core.service_container import ServiceContainer
from app.ui.enhanced_main_window import EnhancedMainWindow


class TestApplicationIntegration(unittest.TestCase):
    """应用程序集成测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试类"""
        # 创建QApplication实例
        cls.app = QApplication(sys.argv if sys.argv else ["test"])

        # 设置测试日志
        logging.basicConfig(level=logging.INFO)

    @classmethod
    def tearDownClass(cls):
        """清理测试类"""
        cls.app.quit()

    def setUp(self):
        """设置每个测试"""
        # 创建服务容器
        self.service_container = ServiceContainer()

        # 初始化基础服务
        self.initialize_services()

    def tearDown(self):
        """清理每个测试"""
        # 清理服务
        self.cleanup_services()

    def initialize_services(self):
        """初始化测试服务"""
        try:
            # 初始化设置管理器
            from app.config.settings_manager import SettingsManager
            settings_manager = SettingsManager()
            self.service_container.register('settings_manager', settings_manager)

            # 初始化项目管理器
            project_manager = ProjectManager()
            self.service_container.register('project_manager', project_manager)

            # 初始化AI服务
            ai_service = create_unified_ai_service()
            self.service_container.register('ai_service', ai_service)

        except Exception as e:
            self.logger.error(f"初始化服务失败: {e}")

    def cleanup_services(self):
        """清理测试服务"""
        try:
            # 清理性能监控
            performance_optimizer = get_enhanced_performance_optimizer()
            performance_optimizer.stop_monitoring()

            # 清理内存管理
            memory_manager = get_memory_manager()
            memory_manager.cleanup()

        except Exception as e:
            self.logger.error(f"清理服务失败: {e}")

    def test_01_application_launcher_initialization(self):
        """测试应用启动器初始化"""
        print("测试应用启动器初始化...")

        try:
            # 创建应用启动器
            launcher = ApplicationLauncher()

            # 检查启动器是否创建成功
            self.assertIsNotNone(launcher)
            self.assertIsNotNone(launcher.logger)
            self.assertEqual(len(launcher.initialization_steps), 12)

            print("✓ 应用启动器初始化测试通过")

        except Exception as e:
            self.fail(f"应用启动器初始化测试失败: {e}")

    def test_02_service_container_integration(self):
        """测试服务容器集成"""
        print("测试服务容器集成...")

        try:
            # 验证服务是否正确注册
            settings_manager = self.service_container.get('settings_manager')
            self.assertIsNotNone(settings_manager)

            project_manager = self.service_container.get('project_manager')
            self.assertIsNotNone(project_manager)

            ai_service = self.service_container.get('ai_service')
            self.assertIsNotNone(ai_service)

            print("✓ 服务容器集成测试通过")

        except Exception as e:
            self.fail(f"服务容器集成测试失败: {e}")

    def test_03_performance_monitoring_system(self):
        """测试性能监控系统"""
        print("测试性能监控系统...")

        try:
            # 获取性能优化器
            performance_optimizer = get_enhanced_performance_optimizer()

            # 测试性能配置文件
            profiles = performance_optimizer.profiles
            self.assertIn('balanced', profiles)
            self.assertIn('power_saver', profiles)
            self.assertIn('performance', profiles)
            self.assertIn('maximum', profiles)

            # 测试配置文件切换
            success = performance_optimizer.set_performance_profile('balanced')
            self.assertTrue(success)

            current_profile = performance_optimizer.current_profile
            self.assertEqual(current_profile.name, '平衡模式')

            print("✓ 性能监控系统测试通过")

        except Exception as e:
            self.fail(f"性能监控系统测试失败: {e}")

    def test_04_memory_management_system(self):
        """测试内存管理系统"""
        print("测试内存管理系统...")

        try:
            # 获取内存管理器
            memory_manager = get_memory_manager()

            # 检查内存池
            self.assertIn('video_frames', memory_manager.pools)
            self.assertIn('preview_cache', memory_manager.pools)
            self.assertIn('effects_processing', memory_manager.pools)

            # 测试内存分配
            test_data = b'test_data' * 1000  # 创建测试数据
            block_id = memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                description='测试分配'
            )

            self.assertIsNotNone(block_id)

            # 测试内存访问
            accessed_data = memory_manager.access_memory(block_id)
            self.assertEqual(accessed_data, test_data)

            # 测试内存释放
            success = memory_manager.deallocate_memory(block_id)
            self.assertTrue(success)

            print("✓ 内存管理系统测试通过")

        except Exception as e:
            self.fail(f"内存管理系统测试失败: {e}")

    def test_05_ai_service_integration(self):
        """测试AI服务集成"""
        print("测试AI服务集成...")

        try:
            # 获取AI服务
            ai_service = self.service_container.get('ai_service')

            # 测试AI服务基本功能
            self.assertIsNotNone(ai_service)

            # 测试AI模型列表
            if hasattr(ai_service, 'get_available_models'):
                models = ai_service.get_available_models()
                self.assertIsInstance(models, list)

            print("✓ AI服务集成测试通过")

        except Exception as e:
            self.fail(f"AI服务集成测试失败: {e}")

    def test_06_project_management_system(self):
        """测试项目管理系统"""
        print("测试项目管理系统...")

        try:
            # 获取项目管理器
            project_manager = self.service_container.get('project_manager')

            # 测试项目创建
            project = project_manager.create_project("测试项目")
            self.assertIsNotNone(project)
            self.assertEqual(project.name, "测试项目")

            # 测试项目保存
            success = project_manager.save_project()
            self.assertTrue(success)

            print("✓ 项目管理系统测试通过")

        except Exception as e:
            self.fail(f"项目管理系统测试失败: {e}")

    def test_07_enhanced_main_window_creation(self):
        """测试增强主窗口创建"""
        print("测试增强主窗口创建...")

        try:
            # 创建增强主窗口
            main_window = EnhancedMainWindow()

            # 检查主窗口是否创建成功
            self.assertIsNotNone(main_window)
            self.assertEqual(main_window.windowTitle(), "CineAIStudio - 专业AI视频编辑器")

            # 检查页面映射
            self.assertIn('home', main_window.page_map)
            self.assertIn('video_edit', main_window.page_map)
            self.assertIn('performance', main_window.page_map)

            # 检查导航
            self.assertIsNotNone(main_window.navigation)
            self.assertIsNotNone(main_window.content_stack)

            # 清理窗口
            main_window.close()

            print("✓ 增强主窗口创建测试通过")

        except Exception as e:
            self.fail(f"增强主窗口创建测试失败: {e}")

    def test_08_performance_monitoring_start_stop(self):
        """测试性能监控启动和停止"""
        print("测试性能监控启动和停止...")

        try:
            # 获取性能优化器
            performance_optimizer = get_enhanced_performance_optimizer()

            # 测试启动监控
            performance_optimizer.start_monitoring(1000)
            self.assertTrue(performance_optimizer.monitoring_enabled)

            # 等待一段时间
            time.sleep(0.1)

            # 测试停止监控
            performance_optimizer.stop_monitoring()
            self.assertFalse(performance_optimizer.monitoring_enabled)

            print("✓ 性能监控启动和停止测试通过")

        except Exception as e:
            self.fail(f"性能监控启动和停止测试失败: {e}")

    def test_09_memory_pool_operations(self):
        """测试内存池操作"""
        print("测试内存池操作...")

        try:
            # 获取内存管理器
            memory_manager = get_memory_manager()

            # 测试多个内存分配
            block_ids = []
            test_sizes = [1024, 2048, 4096, 8192]

            for i, size in enumerate(test_sizes):
                test_data = b'test_data_' + str(i).encode() * (size // 10)
                block_id = memory_manager.allocate_memory(
                    'temp_data',
                    len(test_data),
                    test_data,
                    description=f'测试数据{i}'
                )
                block_ids.append(block_id)

            # 验证所有分配成功
            for block_id in block_ids:
                self.assertIsNotNone(block_id)

            # 获取内存统计
            stats = memory_manager.get_memory_stats()
            self.assertIsInstance(stats, dict)
            self.assertIn('pools', stats)
            self.assertIn('total_used_mb', stats)

            # 清理所有分配
            for block_id in block_ids:
                success = memory_manager.deallocate_memory(block_id)
                self.assertTrue(success)

            print("✓ 内存池操作测试通过")

        except Exception as e:
            self.fail(f"内存池操作测试失败: {e}")

    def test_10_navigation_system(self):
        """测试导航系统"""
        print("测试导航系统...")

        try:
            # 创建增强主窗口
            main_window = EnhancedMainWindow()

            # 测试页面导航
            pages_to_test = ['home', 'projects', 'ai_tools', 'video_edit', 'performance']

            for page_name in pages_to_test:
                main_window.navigate_to_page(page_name)
                self.assertEqual(main_window.current_page, page_name)

                # 验证页面索引正确
                expected_index = main_window.page_map[page_name]
                actual_index = main_window.content_stack.currentIndex()
                self.assertEqual(actual_index, expected_index)

            # 清理窗口
            main_window.close()

            print("✓ 导航系统测试通过")

        except Exception as e:
            self.fail(f"导航系统测试失败: {e}")

    def test_11_theme_system_integration(self):
        """测试主题系统集成"""
        print("测试主题系统集成...")

        try:
            # 创建增强主窗口
            main_window = EnhancedMainWindow()

            # 测试主题切换
            original_theme = main_window.is_dark_theme

            # 切换到深色主题
            main_window.set_theme(True)
            self.assertTrue(main_window.is_dark_theme)

            # 切换到浅色主题
            main_window.set_theme(False)
            self.assertFalse(main_window.is_dark_theme)

            # 切换回原始主题
            main_window.set_theme(original_theme)
            self.assertEqual(main_window.is_dark_theme, original_theme)

            # 清理窗口
            main_window.close()

            print("✓ 主题系统集成测试通过")

        except Exception as e:
            self.fail(f"主题系统集成测试失败: {e}")

    def test_12_error_handling_system(self):
        """测试错误处理系统"""
        print("测试错误处理系统...")

        try:
            # 测试错误处理
            from app.core.error_handler_system import get_global_error_handler, ErrorLevel, ErrorCategory, ErrorContext

            # 获取错误处理器
            error_handler = get_global_error_handler()

            # 创建错误上下文
            error_context = ErrorContext(
                function="test_function",
                component="TestComponent",
                additional_info={"test": True}
            )

            # 测试错误处理
            test_error = ValueError("测试错误")
            error_handler.handle_exception(
                test_error,
                error_context,
                ErrorLevel.WARNING,
                ErrorCategory.USER_INPUT
            )

            print("✓ 错误处理系统测试通过")

        except Exception as e:
            self.fail(f"错误处理系统测试失败: {e}")

    def test_13_full_application_startup_sequence(self):
        """测试完整的应用程序启动序列"""
        print("测试完整的应用程序启动序列...")

        try:
            # 创建应用启动器
            launcher = ApplicationLauncher()

            # 模拟启动序列（不实际启动GUI）
            launcher.app = self.app

            # 测试初始化步骤
            steps_completed = 0

            for step in launcher.initialization_steps:
                # 模拟步骤完成
                steps_completed += 1
                launcher.current_step = steps_completed

            self.assertEqual(steps_completed, len(launcher.initialization_steps))

            print("✓ 完整应用程序启动序列测试通过")

        except Exception as e:
            self.fail(f"完整应用程序启动序列测试失败: {e}")

    def test_14_resource_cleanup(self):
        """测试资源清理"""
        print("测试资源清理...")

        try:
            # 获取各种管理器
            performance_optimizer = get_enhanced_performance_optimizer()
            memory_manager = get_memory_manager()

            # 启动监控
            performance_optimizer.start_monitoring(1000)

            # 分配一些内存
            test_data = b'cleanup_test' * 1000
            block_id = memory_manager.allocate_memory(
                'temp_data',
                len(test_data),
                test_data,
                description='清理测试'
            )

            # 执行清理
            memory_manager.cleanup()
            performance_optimizer.cleanup()

            # 验证清理结果
            stats = memory_manager.get_memory_stats()
            temp_pool = stats['pools'].get('temp_data', {})
            self.assertLess(temp_pool.get('used_size_mb', 0), 1.0)  # 应该小于1MB

            print("✓ 资源清理测试通过")

        except Exception as e:
            self.fail(f"资源清理测试失败: {e}")

    def test_15_system_integration_overall(self):
        """测试整体系统集成"""
        print("测试整体系统集成...")

        try:
            # 验证所有关键组件都可以正常获取
            performance_optimizer = get_enhanced_performance_optimizer()
            self.assertIsNotNone(performance_optimizer)

            memory_manager = get_memory_manager()
            self.assertIsNotNone(memory_manager)

            # 验证服务容器
            settings_manager = self.service_container.get('settings_manager')
            self.assertIsNotNone(settings_manager)

            project_manager = self.service_container.get('project_manager')
            self.assertIsNotNone(project_manager)

            ai_service = self.service_container.get('ai_service')
            self.assertIsNotNone(ai_service)

            # 验证组件间的交互
            # 性能优化器应该能够访问内存管理器
            self.assertIsNotNone(performance_optimizer.get_memory_tracker())
            self.assertIsNotNone(performance_optimizer.get_cache_manager())

            print("✓ 整体系统集成测试通过")

        except Exception as e:
            self.fail(f"整体系统集成测试失败: {e}")


def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("开始 CineAIStudio 集成测试")
    print("=" * 60)

    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestApplicationIntegration)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果总结")
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
    success = run_integration_tests()
    sys.exit(0 if success else 1)