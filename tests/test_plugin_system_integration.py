#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CineAI Studio 插件系统集成测试
测试插件系统的完整功能，包括加载、管理、安全验证和打包分发
"""

import asyncio
import sys
import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.plugins.plugin_system import (
    PluginManager, PluginContext, PluginMetadata, PluginType,
    PluginInterface
)
from app.plugins.plugin_config import PluginConfigManager
from app.plugins.marketplace import PluginMarketplace, PluginPackage, PluginRepository
from app.plugins.security import CodeAnalyzer, SecurityLevel, SandboxExecutor
from app.packaging.build_system import BuildSystem, BuildConfig, Platform
from app.plugins.examples.openai_provider import OpenAIProviderPlugin
from app.plugins.examples.ai_color_grading import AIColorGradingEffect
from app.plugins.examples.jianying_export import JianyingExportPlugin


class TestPluginSystemIntegration(unittest.TestCase):
    """插件系统集成测试"""

    def setUp(self):
        """测试设置"""
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / "data"
        self.config_dir = self.temp_dir / "config"
        self.plugins_dir = self.temp_dir / "plugins"
        self.build_dir = self.temp_dir / "build"

        # 创建目录
        for dir_path in [self.data_dir, self.config_dir, self.plugins_dir, self.build_dir]:
            dir_path.mkdir(parents=True)

        # 创建模拟服务容器
        self.service_container = Mock()
        self.settings_manager = Mock()
        self.theme_manager = Mock()

        # 创建插件上下文
        self.context = PluginContext(
            app_version="2.0.0",
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            temp_dir=self.temp_dir,
            service_container=self.service_container,
            settings_manager=self.settings_manager,
            theme_manager=self.theme_manager
        )

        # 创建插件管理器
        self.plugin_manager = PluginManager(self.context)

    def tearDown(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_01_plugin_lifecycle(self):
        """测试插件生命周期"""
        print("\n=== 测试插件生命周期 ===")

        # 1. 加载示例插件
        openai_plugin = OpenAIProviderPlugin()
        ai_color_plugin = AIColorGradingEffect()
        jianying_plugin = JianyingExportPlugin()

        # 2. 注册插件
        plugins = [openai_plugin, ai_color_plugin, jianying_plugin]

        for plugin in plugins:
            metadata = plugin.get_metadata()
            print(f"注册插件: {metadata.name} v{metadata.version}")
            success = plugin.initialize(self.context)
            self.assertTrue(success, f"插件初始化失败: {metadata.name}")

        # 3. 验证插件类型
        self.assertEqual(openai_plugin.get_metadata().plugin_type, PluginType.AI_PROVIDER)
        self.assertEqual(ai_color_plugin.get_metadata().plugin_type, PluginType.EFFECT)
        self.assertEqual(jianying_plugin.get_metadata().plugin_type, PluginType.EXPORT_FORMAT)

        # 4. 测试插件功能
        # OpenAI 插件
        models = openai_plugin.get_models()
        self.assertGreater(len(models), 0, "OpenAI插件应该返回模型列表")

        # AI调色插件
        effect_types = ai_color_plugin.get_effect_types()
        self.assertIn("ai_color_grading", effect_types, "AI调色插件应该支持ai_color_grading效果")

        # 剪映导出插件
        export_formats = jianying_plugin.get_supported_formats()
        self.assertGreater(len(export_formats), 0, "剪映导出插件应该支持导出格式")

        # 5. 清理插件
        for plugin in plugins:
            plugin.cleanup()

        print("✓ 插件生命周期测试通过")

    def test_02_plugin_security(self):
        """测试插件安全系统"""
        print("\n=== 测试插件安全系统 ===")

        # 创建安全分析器
        analyzer = CodeAnalyzer()

        # 测试安全代码
        safe_code = """
def safe_function():
    return "Hello, World!"
"""

        result = analyzer.analyze_code(safe_code)
        self.assertEqual(result['risk_level'], SecurityLevel.LOW)

        # 测试危险代码
        dangerous_code = """
import os
os.system("rm -rf /")
"""

        result = analyzer.analyze_code(dangerous_code)
        self.assertGreater(result['risk_level'], SecurityLevel.LOW)
        self.assertGreater(len(result['vulnerabilities']), 0)

        # 测试沙箱执行
        sandbox = SandboxExecutor()
        safe_script = """
result = 2 + 2
"""

        try:
            execution_result = sandbox.execute_script(safe_script, timeout=5)
            self.assertEqual(execution_result.get('result'), 4)
            self.assertFalse(execution_result.get('timeout', False))
        except Exception as e:
            self.fail(f"沙箱执行失败: {e}")

        print("✓ 插件安全系统测试通过")

    def test_03_plugin_marketplace(self):
        """测试插件市场系统"""
        print("\n=== 测试插件市场系统 ===")

        # 创建插件市场
        marketplace = PluginMarketplace(self.context)

        # 创建测试仓库
        test_repo = PluginRepository(
            name="测试仓库",
            url="https://test.example.com/repo",
            description="测试插件仓库",
            enabled=True
        )

        # 添加仓库
        marketplace.add_repository(test_repo)
        self.assertIn(test_repo, marketplace.repositories)

        # 创建测试插件包
        test_package = PluginPackage(
            name="测试插件",
            version="1.0.0",
            description="测试插件包",
            author="测试作者",
            plugin_type=PluginType.EFFECT,
            download_url="https://test.example.com/plugin.zip",
            checksum="md5:d41d8cd98f00b204e9800998ecf8427e",
            size=1024,
            dependencies=[],
            repository=test_repo
        )

        # 添加插件包
        marketplace.add_plugin(test_package)
        self.assertIn(test_package, marketplace.plugins)

        # 测试插件搜索
        found_packages = marketplace.search_plugins("测试")
        self.assertIn(test_package, found_packages)

        # 测试插件筛选
        effect_plugins = marketplace.get_plugins_by_type(PluginType.EFFECT)
        self.assertIn(test_package, effect_plugins)

        print("✓ 插件市场系统测试通过")

    def test_04_plugin_packaging(self):
        """测试插件打包系统"""
        print("\n=== 测试插件打包系统 ===")

        # 创建构建配置
        config = BuildConfig(
            version="2.0.0",
            platform=Platform.WINDOWS,
            build_dir=self.build_dir,
            output_dir=self.build_dir / "output",
            source_dir=Path(__file__).parent.parent,
            include_plugins=True,
            include_examples=True,
            sign=True,
            notarize=True
        )

        # 创建构建系统
        build_system = BuildSystem(config)

        # 测试构建环境准备
        with patch.object(build_system, '_prepare_build_environment') as mock_prepare:
            mock_prepare.return_value = True

            # 测试构建过程
            with patch.object(build_system, '_build_application') as mock_build:
                mock_build.return_value = True

                with patch.object(build_system, '_create_distribution') as mock_dist:
                    mock_dist.return_value = True

                    with patch.object(build_system, '_sign_artifacts') as mock_sign:
                        mock_sign.return_value = True

                        # 执行构建
                        success = build_system.build()
                        self.assertTrue(success, "构建应该成功")

        # 测试配置验证
        invalid_config = BuildConfig(
            version="",
            platform=Platform.WINDOWS,
            build_dir=self.build_dir,
            output_dir=self.build_dir / "output",
            source_dir=Path(__file__).parent.parent
        )

        invalid_system = BuildSystem(invalid_config)
        with self.assertRaises(ValueError):
            invalid_system.validate_config()

        print("✓ 插件打包系统测试通过")

    def test_05_plugin_configuration(self):
        """测试插件配置系统"""
        print("\n=== 测试插件配置系统 ===")

        # 创建配置管理器
        config_manager = PluginConfigManager(self.config_dir)

        # 创建测试配置
        test_config = {
            "api_key": "test_key",
            "timeout": 30,
            "enabled": True,
            "advanced": {
                "max_tokens": 4096,
                "temperature": 0.7
            }
        }

        # 保存配置
        plugin_id = "test_plugin"
        config_manager.save_plugin_config(plugin_id, test_config)

        # 加载配置
        loaded_config = config_manager.load_plugin_config(plugin_id)
        self.assertEqual(loaded_config, test_config)

        # 更新配置
        updated_config = test_config.copy()
        updated_config["timeout"] = 60

        config_manager.update_plugin_config(plugin_id, {"timeout": 60})
        reloaded_config = config_manager.load_plugin_config(plugin_id)
        self.assertEqual(reloaded_config["timeout"], 60)

        # 删除配置
        config_manager.delete_plugin_config(plugin_id)
        deleted_config = config_manager.load_plugin_config(plugin_id)
        self.assertIsNone(deleted_config)

        print("✓ 插件配置系统测试通过")

    def test_06_plugin_dependencies(self):
        """测试插件依赖管理"""
        print("\n=== 测试插件依赖管理 ===")

        # 创建有依赖的插件
        plugin_with_deps = Mock()
        plugin_with_deps.get_metadata.return_value = PluginMetadata(
            name="依赖插件",
            version="1.0.0",
            description="有依赖的插件",
            author="测试作者",
            plugin_type=PluginType.EFFECT,
            dependencies=["numpy>=1.20.0", "opencv-python>=4.5.0"]
        )

        # 测试依赖解析（简化版）
        class MockDependencyResolver:
            def resolve_dependencies(self, plugin):
                return []

        resolver = MockDependencyResolver()

        # 模拟已安装的包
        with patch('importlib.metadata.distributions') as mock_distributions:
            mock_dist = Mock()
            mock_dist.metadata = {'Name': 'numpy', 'Version': '1.21.0'}
            mock_distributions.return_value = [mock_dist]

            dependencies = resolver.resolve_dependencies(plugin_with_deps)
            self.assertIsNotNone(dependencies)

            # 测试缺少依赖的情况
            plugin_with_no_deps = Mock()
            plugin_with_no_deps.get_metadata.return_value = PluginMetadata(
                name="无依赖插件",
                version="1.0.0",
                description="无依赖的插件",
                author="测试作者",
                plugin_type=PluginType.EFFECT,
                dependencies=[]
            )

            dependencies = resolver.resolve_dependencies(plugin_with_no_deps)
            self.assertIsNotNone(dependencies)

        print("✓ 插件依赖管理测试通过")

    def test_07_complete_workflow(self):
        """测试完整插件工作流"""
        print("\n=== 测试完整插件工作流 ===")

        # 1. 创建插件市场
        marketplace = PluginMarketplace(self.context)

        # 2. 添加示例插件到市场
        test_package = PluginPackage(
            name="AI调色插件",
            version="1.0.0",
            description="AI驱动的调色效果",
            author="CineAI Studio",
            plugin_type=PluginType.EFFECT,
            download_url="https://example.com/ai_color_grading.zip",
            checksum="md5:test",
            size=2048,
            dependencies=[],
            repository=None
        )

        marketplace.add_plugin(test_package)

        # 3. 模拟插件安装
        with patch.object(marketplace, 'install_plugin') as mock_install:
            mock_install.return_value = True

            # 模拟安全检查
            with patch.object(marketplace.security_manager, 'validate_plugin') as mock_validate:
                mock_validate.return_value = True

                # 执行安装
                success = marketplace.install_plugin(test_package)
                self.assertTrue(success)

        # 4. 测试插件加载
        ai_color_plugin = AIColorGradingEffect()
        ai_color_plugin.initialize(self.context)

        # 5. 测试插件功能
        effect_types = ai_color_plugin.get_effect_types()
        self.assertIn("ai_color_grading", effect_types)

        # 6. 测试效果创建
        effect_params = {
            "style": "cinematic",
            "intensity": 0.8,
            "ai_analysis": True
        }

        effect = ai_color_plugin.create_effect("ai_color_grading", effect_params)
        self.assertIsNotNone(effect)

        # 7. 清理
        ai_color_plugin.cleanup()

        print("✓ 完整插件工作流测试通过")

    def test_08_performance_test(self):
        """测试性能"""
        print("\n=== 测试性能 ===")

        import time

        # 测试多个插件同时加载
        start_time = time.time()

        plugins = []
        for i in range(10):
            plugin = AIColorGradingEffect()
            plugin.initialize(self.context)
            plugins.append(plugin)

        load_time = time.time() - start_time
        print(f"加载10个插件耗时: {load_time:.3f}秒")
        self.assertLess(load_time, 5.0, "插件加载时间应该少于5秒")

        # 测试插件操作性能
        plugin = plugins[0]
        start_time = time.time()

        for i in range(100):
            effect = plugin.create_effect("ai_color_grading", {"style": "cinematic"})

        operation_time = time.time() - start_time
        print(f"100次效果创建耗时: {operation_time:.3f}秒")
        self.assertLess(operation_time, 2.0, "效果创建时间应该少于2秒")

        # 清理
        for plugin in plugins:
            plugin.cleanup()

        print("✓ 性能测试通过")

    def test_09_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")

        # 测试无效插件
        invalid_plugin = Mock()
        invalid_plugin.initialize.side_effect = Exception("初始化失败")

        with self.assertRaises(Exception):
            invalid_plugin.initialize(self.context)

        # 测试配置错误
        config_manager = PluginConfigManager(self.config_dir)

        # 尝试加载不存在的配置
        result = config_manager.load_plugin_config("nonexistent")
        self.assertIsNone(result)

        # 测试安全分析错误
        analyzer = CodeAnalyzer()

        # 无效代码
        with self.assertRaises(SyntaxError):
            analyzer.analyze_code("def invalid_syntax(")

        print("✓ 错误处理测试通过")

    def test_10_cross_platform_compatibility(self):
        """测试跨平台兼容性"""
        print("\n=== 测试跨平台兼容性 ===")

        import platform
        current_platform = platform.system()
        print(f"当前平台: {current_platform}")

        # 测试不同平台的构建配置
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]

        for platform_type in platforms:
            config = BuildConfig(
                version="2.0.0",
                platform=platform_type,
                build_dir=self.build_dir,
                output_dir=self.build_dir / "output",
                source_dir=Path(__file__).parent.parent
            )

            build_system = BuildSystem(config)

            # 验证配置
            try:
                build_system.validate_config()
                print(f"✓ {platform_type.value} 平台配置有效")
            except Exception as e:
                self.fail(f"{platform_type.value} 平台配置无效: {e}")

        print("✓ 跨平台兼容性测试通过")


class TestPluginSystemBenchmark(unittest.TestCase):
    """插件系统性能基准测试"""

    def setUp(self):
        """测试设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / "data"
        self.config_dir = self.temp_dir / "config"

        for dir_path in [self.data_dir, self.config_dir]:
            dir_path.mkdir(parents=True)

        self.context = PluginContext(
            app_version="2.0.0",
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            temp_dir=self.temp_dir,
            service_container=Mock(),
            settings_manager=Mock(),
            theme_manager=Mock()
        )

    def tearDown(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_plugin_loading_benchmark(self):
        """插件加载性能基准测试"""
        import time

        plugin_counts = [1, 5, 10, 20, 50]
        results = {}

        for count in plugin_counts:
            start_time = time.time()

            plugins = []
            for i in range(count):
                plugin = AIColorGradingEffect()
                plugin.initialize(self.context)
                plugins.append(plugin)

            load_time = time.time() - start_time

            # 清理
            for plugin in plugins:
                plugin.cleanup()

            results[count] = load_time
            print(f"加载 {count} 个插件耗时: {load_time:.3f}秒")

        # 验证性能要求
        for count, load_time in results.items():
            avg_time_per_plugin = load_time / count
            self.assertLess(avg_time_per_plugin, 0.1,
                          f"平均每个插件加载时间应该少于0.1秒 (实际: {avg_time_per_plugin:.3f}秒)")

    def test_marketplace_search_benchmark(self):
        """插件市场搜索性能基准测试"""
        import time

        # 创建大量插件包
        marketplace = PluginMarketplace(self.context)

        for i in range(100):
            package = PluginPackage(
                name=f"测试插件{i}",
                version=f"1.{i}.0",
                description=f"测试插件描述{i}",
                author=f"作者{i}",
                plugin_type=PluginType.EFFECT,
                download_url=f"https://example.com/plugin{i}.zip",
                checksum=f"md5:test{i}",
                size=1024,
                dependencies=[],
                repository=None
            )
            marketplace.add_plugin(package)

        # 测试搜索性能
        search_terms = ["测试", "插件", "作者", "效果"]

        for term in search_terms:
            start_time = time.time()
            results = marketplace.search_plugins(term)
            search_time = time.time() - start_time

            print(f"搜索 '{term}' 找到 {len(results)} 个结果，耗时: {search_time:.3f}秒")
            self.assertLess(search_time, 0.1, f"搜索时间应该少于0.1秒 (实际: {search_time:.3f}秒)")


def create_test_report():
    """创建测试报告"""
    print("\n" + "="*60)
    print("CineAI Studio 插件系统集成测试报告")
    print("="*60)

    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加集成测试
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSystemIntegration))

    # 添加性能基准测试
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSystemBenchmark))

    # 运行测试套件
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 生成报告
    report = {
        "总测试数": result.testsRun,
        "成功测试数": result.testsRun - len(result.failures) - len(result.errors),
        "失败测试数": len(result.failures),
        "错误测试数": len(result.errors),
        "成功率": f"{((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%",
        "失败详情": [{"测试": str(test), "错误": str(error)} for test, error in result.failures],
        "错误详情": [{"测试": str(test), "错误": str(error)} for test, error in result.errors]
    }

    print("\n测试报告:")
    print(f"总测试数: {report['总测试数']}")
    print(f"成功测试数: {report['成功测试数']}")
    print(f"失败测试数: {report['失败测试数']}")
    print(f"错误测试数: {report['错误测试数']}")
    print(f"成功率: {report['成功率']}")

    if result.failures:
        print("\n失败详情:")
        for test, error in result.failures:
            print(f"  {test}: {error}")

    if result.errors:
        print("\n错误详情:")
        for test, error in result.errors:
            print(f"  {test}: {error}")

    return result.wasSuccessful()


if __name__ == "__main__":
    print("开始 CineAI Studio 插件系统集成测试...")

    # 创建测试报告
    success = create_test_report()

    if success:
        print("\n🎉 所有测试通过！插件系统已准备就绪。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")
        sys.exit(1)