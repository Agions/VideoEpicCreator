#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
应用启动器 - 负责应用程序的初始化和启动
整合所有服务和组件，提供统一的启动入口
"""

import os
import sys
import logging
import time
import traceback
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import QTimer, Qt, QThreadPool, QSettings, QTranslator
from PyQt6.QtGui import QPixmap, QFont, QIcon

from app.config.settings_manager import SettingsManager
from app.core.project_manager import ProjectManager
from app.ai import create_unified_ai_service
from app.core.service_container import ServiceContainer
from app.core.unified_media_manager import UnifiedMediaManager
from app.core.intelligent_video_processing_engine import IntelligentVideoProcessingEngine

from app.ui.main_window_management import ManagementMainWindow
from app.ui.unified_theme_system import UnifiedThemeManager, ThemeType
from app.core.performance_optimizer import (
    get_enhanced_performance_optimizer,
    start_enhanced_performance_monitoring
)
from app.core.memory_manager import get_memory_manager, start_memory_monitoring


# 配置日志
def setup_logging():
    """设置日志配置"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'cineai_studio.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 设置第三方库日志级别
    logging.getLogger('PyQt6').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


class ApplicationLauncher:
    """应用启动器 - 负责应用程序的初始化和启动"""

    def __init__(self):
        self.logger = setup_logging()
        self.app: Optional[QApplication] = None
        self.main_window: Optional[ManagementMainWindow] = None
        self.splash_screen: Optional[QSplashScreen] = None
        self.service_container: Optional[ServiceContainer] = None

        # 初始化状态
        self.initialization_steps = [
            "初始化应用程序",
            "创建服务容器",
            "初始化设置管理器",
            "初始化主题系统",
            "初始化AI服务",
            "初始化项目管理器",
            "初始化媒体管理器",
            "初始化视频处理引擎",
            "初始化性能监控",
            "初始化内存管理",
            "创建主窗口",
            "完成初始化"
        ]
        self.current_step = 0

    def launch(self, args: List[str]) -> int:
        """启动应用程序"""
        try:
            self.logger.info("启动 CineAIStudio 应用程序...")

            # 步骤1: 初始化应用程序
            self.update_progress("初始化应用程序")
            self.app = QApplication(args)
            self.app.setApplicationName("CineAIStudio")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("CineAIStudio Team")

            # 显示启动画面（必须在QApplication创建后）
            self.show_splash_screen()

            # 设置应用程序样式
            self.setup_application_style()

            # 步骤2: 创建服务容器
            self.update_progress("创建服务容器")
            self.service_container = ServiceContainer()

            # 步骤3: 初始化设置管理器
            self.update_progress("初始化设置管理器")
            self.initialize_settings_manager()

            # 步骤4: 初始化主题系统
            self.update_progress("初始化主题系统")
            self.initialize_theme_system()

            # 应用主题（在QApplication创建后）
            self.apply_theme()

            # 步骤5: 初始化AI服务
            self.update_progress("初始化AI服务")
            self.initialize_ai_services()

            # 步骤6: 初始化项目管理器
            self.update_progress("初始化项目管理器")
            self.initialize_project_manager()

            # 步骤7: 初始化媒体管理器
            self.update_progress("初始化媒体管理器")
            self.initialize_media_manager()

            # 步骤8: 初始化视频处理引擎
            self.update_progress("初始化视频处理引擎")
            self.initialize_video_processing_engine()

            # 步骤9: 初始化性能监控
            self.update_progress("初始化性能监控")
            self.initialize_performance_monitoring()

            # 步骤10: 初始化内存管理
            self.update_progress("初始化内存管理")
            self.initialize_memory_management()

            # 步骤11: 创建主窗口
            self.update_progress("创建主窗口")
            self.create_main_window()

            # 步骤12: 完成初始化
            self.update_progress("完成初始化")
            self.finalize_initialization()

            # 关闭启动画面
            self.hide_splash_screen()

            # 显示主窗口
            self.show_main_window()

            # 运行应用程序
            self.logger.info("应用程序启动完成")
            return self.app.exec()

        except Exception as e:
            self.logger.error(f"应用程序启动失败: {e}")
            self.logger.error(traceback.format_exc())

            # 显示错误对话框
            if self.app:
                QMessageBox.critical(
                    None,
                    "启动失败",
                    f"应用程序启动失败:\n\n{str(e)}\n\n请查看日志文件获取详细信息。"
                )

            return 1

    def show_splash_screen(self):
        """显示启动画面"""
        try:
            # 创建启动画面
            splash_pixmap = QPixmap(400, 200)
            splash_pixmap.fill(Qt.GlobalColor.white)

            # 创建启动画面窗口
            self.splash_screen = QSplashScreen(splash_pixmap)
            self.splash_screen.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
            self.splash_screen.show()

            # 设置启动画面样式
            self.splash_screen.showMessage(
                "正在启动 CineAIStudio...",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.black
            )

            self.app.processEvents() if self.app else None

        except Exception as e:
            self.logger.warning(f"显示启动画面失败: {e}")

    def hide_splash_screen(self):
        """隐藏启动画面"""
        if self.splash_screen:
            self.splash_screen.finish(self.main_window)
            self.splash_screen = None

    def update_progress(self, step_message: str):
        """更新启动进度"""
        self.current_step += 1
        progress = (self.current_step / len(self.initialization_steps)) * 100

        if self.splash_screen:
            self.splash_screen.showMessage(
                f"{step_message}... ({self.current_step}/{len(self.initialization_steps)})",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.black
            )

        self.logger.info(f"初始化进度: {step_message} ({progress:.1f}%)")

        if self.app:
            self.app.processEvents()

    def setup_application_style(self):
        """设置应用程序样式"""
        try:
            # 设置应用程序字体
            font = QFont("Segoe UI", 10)
            self.app.setFont(font)

            # 设置应用程序图标
            icon_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'resources',
                'icons',
                'app_icon.png'
            )
            if os.path.exists(icon_path):
                self.app.setWindowIcon(QIcon(icon_path))

            # 设置高DPI支持
            self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            self.app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

        except Exception as e:
            self.logger.warning(f"设置应用程序样式失败: {e}")

    def initialize_settings_manager(self):
        """初始化设置管理器"""
        try:
            settings_manager = SettingsManager()
            self.service_container.register_instance('settings_manager', settings_manager)
            self.logger.info("设置管理器初始化完成")

        except Exception as e:
            self.logger.error(f"初始化设置管理器失败: {e}")
            raise

    def initialize_theme_system(self):
        """初始化主题系统"""
        try:
            theme_manager = UnifiedThemeManager()
            self.service_container.register_instance('theme_manager', theme_manager)

            # 加载主题设置，但不立即应用（等待QApplication创建）
            settings_manager = self.service_container.get('settings_manager')
            is_dark_theme = settings_manager.get_setting('ui.dark_theme', False)

            # 保存主题选择，稍后应用
            self._theme_type = ThemeType.DARK if is_dark_theme else ThemeType.LIGHT

            self.logger.info("主题系统初始化完成")

        except Exception as e:
            self.logger.error(f"初始化主题系统失败: {e}")
            raise

    def initialize_ai_services(self):
        """初始化AI服务"""
        try:
            settings_manager = self.service_container.get('settings_manager')
            ai_service = create_unified_ai_service(settings_manager)
            self.service_container.register_instance('ai_service', ai_service)
            self.logger.info("AI服务初始化完成")

        except Exception as e:
            self.logger.error(f"初始化AI服务失败: {e}")
            # AI服务初始化失败不影响应用启动
            self.logger.warning("AI服务初始化失败，部分AI功能可能不可用")
            # 创建一个空的AI服务占位符
            from app.ai.interfaces import IAIService, AIResponse, AIRequest
            class DummyAIService(IAIService):
                def process_request(self, request: AIRequest):
                    return AIResponse(request.request_id, False, "AI服务不可用")
                def submit_request(self, request: AIRequest):
                    return request.request_id
                def get_request_status(self, request_id: str):
                    return {"status": "failed"}
                def cancel_request(self, request_id: str):
                    return False
                def get_health_status(self):
                    return {}
                def get_usage_stats(self):
                    from app.ai.interfaces import AIUsageStats
                    return AIUsageStats()
                def get_available_providers(self):
                    return []
                def set_budget_limit(self, limit: float):
                    pass
                def cleanup(self):
                    pass

            dummy_service = DummyAIService()
            self.service_container.register_instance('ai_service', dummy_service)

    def initialize_project_manager(self):
        """初始化项目管理器"""
        try:
            project_manager = ProjectManager()
            self.service_container.register_instance('project_manager', project_manager)
            self.logger.info("项目管理器初始化完成")

        except Exception as e:
            self.logger.error(f"初始化项目管理器失败: {e}")
            raise

    def initialize_media_manager(self):
        """初始化媒体管理器"""
        try:
            media_manager = UnifiedMediaManager()
            self.service_container.register_instance('media_manager', media_manager)
            self.logger.info("媒体管理器初始化完成")

        except Exception as e:
            self.logger.error(f"初始化媒体管理器失败: {e}")
            raise

    def initialize_video_processing_engine(self):
        """初始化视频处理引擎"""
        try:
            video_engine = IntelligentVideoProcessingEngine()
            self.service_container.register_instance('video_engine', video_engine)
            self.logger.info("视频处理引擎初始化完成")

        except Exception as e:
            self.logger.error(f"初始化视频处理引擎失败: {e}")
            raise

    def initialize_performance_monitoring(self):
        """初始化性能监控"""
        try:
            # 延迟启动性能监控，避免影响启动速度
            QTimer.singleShot(3000, self._start_performance_monitoring)
            self.logger.info("性能监控初始化完成")

        except Exception as e:
            self.logger.error(f"初始化性能监控失败: {e}")
            # 性能监控失败不影响应用启动
            self.logger.warning("性能监控初始化失败，性能监控功能可能不可用")

    def _start_performance_monitoring(self):
        """启动性能监控"""
        try:
            start_enhanced_performance_monitoring(1000)
            self.logger.info("性能监控已启动")
        except Exception as e:
            self.logger.error(f"启动性能监控失败: {e}")

    def initialize_memory_management(self):
        """初始化内存管理"""
        try:
            # 延迟启动内存监控
            QTimer.singleShot(2000, self._start_memory_monitoring)
            self.logger.info("内存管理初始化完成")

        except Exception as e:
            self.logger.error(f"初始化内存管理失败: {e}")
            # 内存管理失败不影响应用启动
            self.logger.warning("内存管理初始化失败，内存优化功能可能不可用")

    def apply_theme(self):
        """应用主题"""
        try:
            if hasattr(self, '_theme_type') and self.service_container:
                theme_manager = self.service_container.get('theme_manager')
                if theme_manager:
                    theme_manager.set_theme(self._theme_type)
                    self.logger.info(f"主题已应用: {self._theme_type}")
        except Exception as e:
            self.logger.error(f"应用主题失败: {e}")

    def _start_memory_monitoring(self):
        """启动内存监控"""
        try:
            start_memory_monitoring(2000)
            self.logger.info("内存监控已启动")
        except Exception as e:
            self.logger.error(f"启动内存监控失败: {e}")

    def create_main_window(self):
        """创建主窗口"""
        try:
            # 从服务容器获取依赖
            settings_manager = self.service_container.get('settings_manager')
            project_manager = self.service_container.get('project_manager')
            ai_service = self.service_container.get('ai_service')

            # 创建主窗口
            self.main_window = ManagementMainWindow(settings_manager, project_manager, ai_service)

            # 注册主窗口到服务容器
            self.service_container.register_instance('main_window', self.main_window)

            self.logger.info("主窗口创建完成")

        except Exception as e:
            self.logger.error(f"创建主窗口失败: {e}")
            raise

    def finalize_initialization(self):
        """完成初始化"""
        try:
            # 设置全局异常处理
            self.setup_global_exception_handling()

            # 设置信号处理
            self.setup_signal_handling()

            # 初始化完成后的设置
            self.post_initialization_setup()

            self.logger.info("应用程序初始化完成")

        except Exception as e:
            self.logger.error(f"完成初始化失败: {e}")
            raise

    def setup_global_exception_handling(self):
        """设置全局异常处理"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            self.logger.critical(
                f"未捕获的异常: {exc_type.__name__}: {exc_value}",
                exc_info=(exc_type, exc_value, exc_traceback)
            )

            # 在主线程中显示错误对话框
            if self.main_window:
                QTimer.singleShot(0, lambda: self.show_critical_error(
                    f"发生未处理的异常:\n\n{exc_type.__name__}: {exc_value}"
                ))

        sys.excepthook = handle_exception

    def setup_signal_handling(self):
        """设置信号处理"""
        try:
            import signal

            def signal_handler(signum, frame):
                self.logger.info(f"接收到信号 {signum}，准备关闭应用程序")
                if self.main_window:
                    self.main_window.close()

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        except Exception as e:
            self.logger.warning(f"设置信号处理失败: {e}")

    def post_initialization_setup(self):
        """初始化完成后的设置"""
        try:
            # 设置线程池
            thread_pool = QThreadPool.globalInstance()
            thread_pool.setMaxThreadCount(8)

            # 应用最后的主题设置
            theme_manager = self.service_container.get('theme_manager')
            if self.main_window:
                theme_manager.set_theme("professional_dark")

            # 恢复上次的工作状态
            self.restore_session()

        except Exception as e:
            self.logger.warning(f"初始化后设置失败: {e}")

    def restore_session(self):
        """恢复会话"""
        try:
            settings_manager = self.service_container.get('settings_manager')

            # 恢复窗口几何状态
            geometry = settings_manager.get_setting('window.geometry')
            if geometry and self.main_window:
                self.main_window.restoreGeometry(geometry)

            state = settings_manager.get_setting('window.state')
            if state and self.main_window:
                self.main_window.restoreState(state)

            # 恢复最近打开的项目
            recent_project = settings_manager.get_setting('recent_project')
            if recent_project and self.main_window:
                project_manager = self.service_container.get('project_manager')
                try:
                    project_manager.load_project(recent_project)
                except Exception as e:
                    self.logger.warning(f"恢复最近项目失败: {e}")

        except Exception as e:
            self.logger.warning(f"恢复会话失败: {e}")

    def show_main_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()

            # 如果有启动参数，处理启动参数
            if len(sys.argv) > 1:
                self.handle_startup_arguments(sys.argv[1:])

    def handle_startup_arguments(self, args: List[str]):
        """处理启动参数"""
        try:
            for arg in args:
                if arg.endswith('.cineai') or arg.endswith('.json'):
                    # 打开项目文件
                    project_manager = self.service_container.get('project_manager')
                    project_manager.load_project(arg)
                    break
                elif arg == '--performance':
                    # 启动到性能监控页面
                    if self.main_window:
                        self.main_window.navigate_to_page('performance')
                elif arg == '--debug':
                    # 启用调试模式
                    logging.getLogger().setLevel(logging.DEBUG)
                    self.logger.info("调试模式已启用")

        except Exception as e:
            self.logger.warning(f"处理启动参数失败: {e}")

    def show_critical_error(self, message: str):
        """显示严重错误"""
        if self.app:
            QMessageBox.critical(
                None,
                "严重错误",
                f"应用程序遇到严重错误:\n\n{message}\n\n应用程序即将关闭。"
            )

        if self.main_window:
            self.main_window.close()


def main():
    """主函数"""
    try:
        # 创建启动器
        launcher = ApplicationLauncher()

        # 启动应用程序
        exit_code = launcher.launch(sys.argv)

        # 退出
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n应用程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()