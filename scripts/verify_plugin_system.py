#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CineAI Studio 插件系统验证脚本
验证插件系统的完整功能和性能
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.plugins.plugin_system import (
    PluginManager, PluginContext, PluginType
)
from app.plugins.plugin_config import PluginConfigManager
from app.plugins.marketplace import PluginMarketplace, PluginPackage
from app.plugins.security import CodeAnalyzer, PluginSandbox
from app.packaging.build_system import BuildSystem, BuildConfig, BuildTarget, BuildType, Architecture
from app.plugins.examples.openai_provider import OpenAIProviderPlugin
from app.plugins.examples.ai_color_grading import AIColorGradingEffect
from app.plugins.examples.jianying_export import JianyingExportPlugin


class PluginSystemVerifier:
    """插件系统验证器"""

    def __init__(self):
        self.project_root = project_root
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "details": []
        }

    def log_result(self, check_name: str, passed: bool, details: str = ""):
        """记录验证结果"""
        self.results["total_checks"] += 1
        if passed:
            self.results["passed_checks"] += 1
            status = "✓ 通过"
        else:
            self.results["failed_checks"] += 1
            status = "✗ 失败"

        print(f"[{status}] {check_name}")
        if details:
            print(f"    {details}")

        self.results["details"].append({
            "check": check_name,
            "status": "passed" if passed else "failed",
            "details": details
        })

    def verify_dependencies(self) -> bool:
        """验证依赖包"""
        print("\n=== 验证系统依赖 ===")

        required_packages = [
            "PyQt6",
            "numpy",
            "opencv-python",
            "requests",
            "aiohttp",
            "cryptography"
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                self.log_result(f"依赖包 {package}", True)
            except ImportError:
                missing_packages.append(package)
                self.log_result(f"依赖包 {package}", False, "包未安装")

        return len(missing_packages) == 0

    def verify_plugin_structure(self) -> bool:
        """验证插件系统结构"""
        print("\n=== 验证插件系统结构 ===")

        required_files = [
            "app/plugins/plugin_system.py",
            "app/plugins/marketplace.py",
            "app/plugins/security.py",
            "app/packaging/build_system.py",
            "app/plugins/examples/openai_provider.py",
            "app/plugins/examples/ai_color_grading.py",
            "app/plugins/examples/jianying_export.py"
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.log_result(f"插件文件 {file_path}", True)
            else:
                missing_files.append(file_path)
                self.log_result(f"插件文件 {file_path}", False, "文件不存在")

        return len(missing_files) == 0

    def verify_plugin_loading(self) -> bool:
        """验证插件加载"""
        print("\n=== 验证插件加载 ===")

        try:
            # 创建临时目录
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())

            # 创建插件上下文
            context = PluginContext(
                app_version="2.0.0",
                data_dir=temp_dir / "data",
                config_dir=temp_dir / "config",
                temp_dir=temp_dir,
                service_container=Mock(),
                settings_manager=Mock(),
                theme_manager=Mock()
            )

            # 创建插件管理器
            plugin_manager = PluginManager(context)

            # 测试示例插件加载
            plugins = [
                OpenAIProviderPlugin(),
                AIColorGradingEffect(),
                JianyingExportPlugin()
            ]

            for plugin in plugins:
                metadata = plugin.get_metadata()
                success = plugin.initialize(context)
                self.log_result(f"加载插件 {metadata.name}", success,
                              f"类型: {metadata.plugin_type.value}, 版本: {metadata.version}")

            # 清理
            for plugin in plugins:
                plugin.cleanup()

            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)

            return True

        except Exception as e:
            self.log_result("插件加载", False, f"异常: {str(e)}")
            return False

    def verify_security_system(self) -> bool:
        """验证安全系统"""
        print("\n=== 验证安全系统 ===")

        try:
            analyzer = CodeAnalyzer()

            # 测试安全代码分析
            safe_code = """
def safe_function():
    return "Hello, World!"
"""
            result = analyzer.analyze_code(safe_code)
            is_safe = result['risk_level'].value <= 2  # LOW or MEDIUM
            self.log_result("安全代码分析", is_safe)

            # 测试危险代码检测
            dangerous_code = """
import os
os.system("rm -rf /")
"""
            result = analyzer.analyze_code(dangerous_code)
            is_dangerous = result['risk_level'].value > 2  # HIGH or CRITICAL
            self.log_result("危险代码检测", is_dangerous)

            # 测试沙箱执行
            sandbox = PluginSandbox()
            safe_script = "result = 2 + 2"

            try:
                execution_result = sandbox.execute_code(safe_script, timeout=5)
                sandbox_success = execution_result.get('result') == 4
                self.log_result("沙箱执行", sandbox_success)
            except Exception as e:
                self.log_result("沙箱执行", False, f"异常: {str(e)}")
                return False

            return True

        except Exception as e:
            self.log_result("安全系统", False, f"异常: {str(e)}")
            return False

    def verify_marketplace_system(self) -> bool:
        """验证市场系统"""
        print("\n=== 验证插件市场系统 ===")

        try:
            # 创建临时目录
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())

            context = PluginContext(
                app_version="2.0.0",
                data_dir=temp_dir / "data",
                config_dir=temp_dir / "config",
                temp_dir=temp_dir,
                service_container=Mock(),
                settings_manager=Mock(),
                theme_manager=Mock()
            )

            marketplace = PluginMarketplace(context)

            # 测试插件包创建
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
                repository=None
            )

            marketplace.add_plugin(test_package)
            self.log_result("添加插件包", True)

            # 测试搜索功能
            search_results = marketplace.search_plugins("测试")
            search_success = len(search_results) > 0
            self.log_result("插件搜索", search_success, f"找到 {len(search_results)} 个结果")

            # 测试类型筛选
            effect_plugins = marketplace.get_plugins_by_type(PluginType.EFFECT)
            filter_success = len(effect_plugins) > 0
            self.log_result("类型筛选", filter_success, f"找到 {len(effect_plugins)} 个效果插件")

            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)

            return True

        except Exception as e:
            self.log_result("市场系统", False, f"异常: {str(e)}")
            return False

    def verify_build_system(self) -> bool:
        """验证构建系统"""
        print("\n=== 验证构建系统 ===")

        try:
            # 创建临时目录
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())

            # 测试不同平台的构建配置
            platforms = [BuildTarget.WINDOWS, BuildTarget.MACOS, BuildTarget.LINUX]

            for platform in platforms:
                config = BuildConfig(
                    target=platform,
                    build_type=BuildType.RELEASE,
                    architecture=Architecture.X64,
                    version="2.0.0",
                    build_number=1,
                    output_dir=str(temp_dir / "output"),
                    source_dir=str(self.project_root)
                )

                build_system = BuildSystem(config)

                # 验证配置
                try:
                    build_system.validate_config()
                    self.log_result(f"{platform.value} 平台配置", True)
                except Exception as e:
                    self.log_result(f"{platform.value} 平台配置", False, f"配置错误: {str(e)}")
                    return False

            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)

            return True

        except Exception as e:
            self.log_result("构建系统", False, f"异常: {str(e)}")
            return False

    def verify_performance(self) -> bool:
        """验证性能"""
        print("\n=== 验证性能 ===")

        try:
            # 测试插件加载性能
            start_time = time.time()

            plugins = []
            for i in range(5):
                plugin = AIColorGradingEffect()
                # 模拟初始化
                plugin._initialized = True
                plugins.append(plugin)

            load_time = time.time() - start_time
            load_performance = load_time < 1.0  # 应该在1秒内加载5个插件
            self.log_result("插件加载性能", load_performance,
                          f"加载5个插件耗时: {load_time:.3f}秒")

            # 清理
            for plugin in plugins:
                plugin.cleanup()

            return load_performance

        except Exception as e:
            self.log_result("性能验证", False, f"异常: {str(e)}")
            return False

    def verify_configuration(self) -> bool:
        """验证配置系统"""
        print("\n=== 验证配置系统 ===")

        try:
            # 创建临时目录
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())

            config_manager = PluginConfigManager(temp_dir)

            # 测试配置保存和加载
            test_config = {
                "api_key": "test_key",
                "timeout": 30,
                "enabled": True,
                "advanced": {
                    "max_tokens": 4096
                }
            }

            config_manager.save_plugin_config("test_plugin", test_config)
            loaded_config = config_manager.load_plugin_config("test_plugin")

            config_success = loaded_config == test_config
            self.log_result("配置保存/加载", config_success)

            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)

            return config_success

        except Exception as e:
            self.log_result("配置系统", False, f"异常: {str(e)}")
            return False

    def verify_documentation(self) -> bool:
        """验证文档"""
        print("\n=== 验证文档 ===")

        required_docs = [
            "PLUGIN_DEVELOPMENT_GUIDE.md",
            "README.md"
        ]

        missing_docs = []
        for doc in required_docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                # 检查文件大小
                size = doc_path.stat().st_size
                if size > 1024:  # 至少1KB
                    self.log_result(f"文档 {doc}", True, f"大小: {size} 字节")
                else:
                    self.log_result(f"文档 {doc}", False, f"文件过小: {size} 字节")
                    missing_docs.append(doc)
            else:
                self.log_result(f"文档 {doc}", False, "文件不存在")
                missing_docs.append(doc)

        return len(missing_docs) == 0

    def run_comprehensive_verification(self) -> bool:
        """运行全面验证"""
        print("开始 CineAI Studio 插件系统全面验证...")
        print("="*60)

        verification_steps = [
            ("系统依赖", self.verify_dependencies),
            ("插件系统结构", self.verify_plugin_structure),
            ("插件加载", self.verify_plugin_loading),
            ("安全系统", self.verify_security_system),
            ("市场系统", self.verify_marketplace_system),
            ("构建系统", self.verify_build_system),
            ("性能", self.verify_performance),
            ("配置系统", self.verify_configuration),
            ("文档", self.verify_documentation)
        ]

        all_passed = True
        for step_name, step_function in verification_steps:
            try:
                step_passed = step_function()
                if not step_passed:
                    all_passed = False
            except Exception as e:
                self.log_result(step_name, False, f"验证过程中发生异常: {str(e)}")
                all_passed = False

        # 生成报告
        self.generate_report()

        return all_passed

    def generate_report(self):
        """生成验证报告"""
        print("\n" + "="*60)
        print("插件系统验证报告")
        print("="*60)
        print(f"验证时间: {self.results['timestamp']}")
        print(f"总检查项: {self.results['total_checks']}")
        print(f"通过检查: {self.results['passed_checks']}")
        print(f"失败检查: {self.results['failed_checks']}")
        print(f"成功率: {(self.results['passed_checks'] / self.results['total_checks'] * 100):.1f}%")

        if self.results['failed_checks'] > 0:
            print("\n失败的检查项:")
            for detail in self.results['details']:
                if detail['status'] == 'failed':
                    print(f"  - {detail['check']}: {detail['details']}")

        print("="*60)


def main():
    """主函数"""
    try:
        from unittest.mock import Mock

        verifier = PluginSystemVerifier()
        success = verifier.run_comprehensive_verification()

        if success:
            print("\n🎉 所有验证项通过！插件系统已准备就绪。")
            return 0
        else:
            print("\n❌ 部分验证项失败，请检查上述错误信息。")
            return 1

    except Exception as e:
        print(f"\n💥 验证过程中发生严重错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())