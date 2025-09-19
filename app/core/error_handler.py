#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一错误处理系统
提供完整的错误处理、日志记录和用户通知功能
"""

import os
import sys
import traceback
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# 导入新的错误处理系统
from .error_handler_system import (
    GlobalErrorHandler, ErrorLevel, ErrorCategory,
    ErrorInfo, ErrorHandlerMixin, global_error_handler
)


# 使用新的错误处理系统的枚举
# 保持向后兼容的别名


@dataclass
class ErrorContext:
    """错误上下文信息"""
    component: str = ""
    function: str = ""
    line_number: int = 0
    file_path: str = ""
    user_action: str = ""
    system_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'component': self.component,
            'function': self.function,
            'line_number': self.line_number,
            'file_path': self.file_path,
            'user_action': self.user_action,
            'system_info': self.system_info
        }


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    code: str
    message: str
    level: ErrorLevel
    category: ErrorCategory
    context: ErrorContext
    exception: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    user_message: str = ""
    solution: str = ""

    def __post_init__(self):
        """初始化后处理"""
        if not self.user_message:
            self.user_message = self._generate_user_message()

        if not self.solution:
            self.solution = self._generate_solution()

    def _generate_user_message(self) -> str:
        """生成用户友好的错误消息"""
        level_messages = {
            ErrorLevel.DEBUG: "调试信息",
            ErrorLevel.INFO: "提示",
            ErrorLevel.WARNING: "警告",
            ErrorLevel.ERROR: "错误",
            ErrorLevel.CRITICAL: "严重错误"
        }

        category_messages = {
            ErrorCategory.SYSTEM: "系统",
            ErrorCategory.UI: "界面",
            ErrorCategory.FILE: "文件",
            ErrorCategory.NETWORK: "网络",
            ErrorCategory.AI: "AI功能",
            ErrorCategory.VIDEO: "视频处理",
            ErrorCategory.AUDIO: "音频处理",
            ErrorCategory.CONFIGURATION: "配置",
            ErrorCategory.CONFIG: "配置",
            ErrorCategory.UNKNOWN: "未知"
        }

        return f"{category_messages.get(self.category, '未知')}{level_messages.get(self.level, '')}：{self.message}"

    def _generate_solution(self) -> str:
        """生成解决方案建议"""
        solutions = {
            ErrorCategory.FILE: "请检查文件路径是否正确，文件是否存在，以及是否有访问权限。",
            ErrorCategory.NETWORK: "请检查网络连接是否正常，或者稍后重试。",
            ErrorCategory.AI: "请检查AI服务配置是否正确，或者尝试使用其他AI模型。",
            ErrorCategory.VIDEO: "请检查视频文件格式是否支持，或者尝试转换格式。",
            ErrorCategory.AUDIO: "请检查音频文件格式是否支持，或者检查音频设备。",
            ErrorCategory.CONFIGURATION: "请检查配置文件是否正确，或者重置为默认配置。",
            ErrorCategory.CONFIG: "请检查配置文件是否正确，或者重置为默认配置。",
        }

        return solutions.get(self.category, "如果问题持续存在，请联系技术支持。")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'error_code': self.code,
            'error_message': self.message,
            'error_level': self.level.value,
            'error_category': self.category.value,
            'context': self.context.to_dict(),
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'user_message': self.user_message,
            'solution': self.solution,
            'exception_type': type(self.exception).__name__ if self.exception else None,
            'exception_message': str(self.exception) if self.exception else None
        }


class ErrorListener:
    """错误监听器接口"""

    def on_error(self, error_info: ErrorInfo) -> None:
        """错误发生时调用"""
        pass


class ErrorHandler(QObject):
    """统一错误处理器"""

    # 信号定义
    error_occurred = pyqtSignal(ErrorInfo)           # 错误发生信号
    error_handled = pyqtSignal(ErrorInfo)            # 错误处理完成信号
    error_count_updated = pyqtSignal(int)           # 错误计数更新信号

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # 错误统计
        self._error_count = 0
        self._error_history: List[ErrorInfo] = []
        self._max_history_size = 1000

        # 错误监听器
        self._listeners: List[ErrorListener] = []

        # 错误过滤器
        self._error_filters: List[Callable[[ErrorInfo], bool]] = []

        # 设置日志
        self._setup_logging()

        # 设置定时清理
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_old_errors)
        self._cleanup_timer.start(3600000)  # 1小时清理一次

        # 错误代码映射
        self._error_codes = self._load_error_codes()

    def _setup_logging(self) -> None:
        """设置日志系统"""
        # 创建日志目录
        log_dir = Path.home() / "CineAIStudio" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)

        # 文件处理器
        log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        # 配置根日志器
        self._logger = logging.getLogger("CineAIStudio.ErrorHandler")
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def _load_error_codes(self) -> Dict[str, str]:
        """加载错误代码映射"""
        return {
            # 系统错误
            "SYS_001": "系统初始化失败",
            "SYS_002": "内存不足",
            "SYS_003": "磁盘空间不足",

            # 文件错误
            "FILE_001": "文件不存在",
            "FILE_002": "文件格式不支持",
            "FILE_003": "文件权限不足",
            "FILE_004": "文件读取失败",
            "FILE_005": "文件写入失败",

            # 网络错误
            "NET_001": "网络连接失败",
            "NET_002": "请求超时",
            "NET_003": "服务器响应错误",

            # AI错误
            "AI_001": "AI服务初始化失败",
            "AI_002": "AI模型加载失败",
            "AI_003": "AI处理失败",
            "AI_004": "AI配额不足",

            # 视频错误
            "VIDEO_001": "视频解码失败",
            "VIDEO_002": "视频编码失败",
            "VIDEO_003": "视频格式不支持",
            "VIDEO_004": "视频处理失败",

            # 音频错误
            "AUDIO_001": "音频解码失败",
            "AUDIO_002": "音频编码失败",
            "AUDIO_003": "音频设备不可用",

            # UI错误
            "UI_001": "界面初始化失败",
            "UI_002": "组件创建失败",
            "UI_003": "用户操作无效",

            # 配置错误
            "CONFIG_001": "配置文件读取失败",
            "CONFIG_002": "配置文件写入失败",
            "CONFIG_003": "配置项无效",
        }

    def handle_error(self, error_info: ErrorInfo) -> None:
        """处理错误

        Args:
            error_info: 错误信息
        """
        try:
            # 同时使用新的全局错误处理器
            new_error_info = global_error_handler._create_error_info(
                message=error_info.message,
                level=error_info.level,
                category=error_info.category,
                context=error_info.context.module if hasattr(error_info.context, 'module') else error_info.context,
                exception=error_info.exception,
                user_action=error_info.context.user_action if hasattr(error_info.context, 'user_action') else None,
                additional_data=error_info.details
            )

            # 让新的全局错误处理器处理错误
            global_error_handler.handle_error(new_error_info, show_dialog=False)

            # 应用错误过滤器
            if self._should_ignore_error(error_info):
                return

            # 记录错误
            self._log_error(error_info)

            # 添加到历史记录
            self._add_to_history(error_info)

            # 更新错误计数
            self._error_count += 1
            self.error_count_updated.emit(self._error_count)

            # 通知监听器
            self._notify_listeners(error_info)

            # 显示给用户
            self._show_error_to_user(error_info)

            # 发射信号
            self.error_occurred.emit(error_info)
            self.error_handled.emit(error_info)

        except Exception as e:
            # 错误处理器本身出错
            print(f"Error handler failed: {str(e)}", file=sys.stderr)

    def handle_exception(self, exception: Exception,
                        context: Optional[ErrorContext] = None,
                        level: ErrorLevel = ErrorLevel.ERROR,
                        category: ErrorCategory = ErrorCategory.UNKNOWN) -> None:
        """处理异常

        Args:
            exception: 异常对象
            context: 错误上下文
            level: 错误级别
            category: 错误分类
        """
        if context is None:
            context = self._create_context_from_exception(exception)

        # 生成错误代码
        error_code = self._generate_error_code(exception, category)

        # 创建错误信息
        error_info = ErrorInfo(
            code=error_code,
            message=str(exception),
            level=level,
            category=category,
            context=context,
            exception=exception
        )

        self.handle_error(error_info)

    def _should_ignore_error(self, error_info: ErrorInfo) -> bool:
        """判断是否应该忽略错误"""
        for filter_func in self._error_filters:
            if filter_func(error_info):
                return True
        return False

    def _log_error(self, error_info: ErrorInfo) -> None:
        """记录错误日志"""
        log_method = getattr(self._logger, error_info.level.value)

        log_message = f"[{error_info.code}] {error_info.message}"
        if error_info.context.component:
            log_message += f" (Component: {error_info.context.component})"
        if error_info.context.function:
            log_message += f" (Function: {error_info.context.function})"

        log_method(log_message, extra=error_info.to_dict())

    def _add_to_history(self, error_info: ErrorInfo) -> None:
        """添加错误到历史记录"""
        self._error_history.append(error_info)

        # 限制历史记录大小
        if len(self._error_history) > self._max_history_size:
            self._error_history = self._error_history[-self._max_history_size:]

    def _notify_listeners(self, error_info: ErrorInfo) -> None:
        """通知错误监听器"""
        for listener in self._listeners:
            try:
                listener.on_error(error_info)
            except Exception as e:
                self._logger.warning(f"Error listener failed: {str(e)}")

    def _show_error_to_user(self, error_info: ErrorInfo) -> None:
        """向用户显示错误"""
        # 只向用户显示重要错误
        if error_info.level in [ErrorLevel.ERROR, ErrorLevel.CRITICAL]:
            self._show_error_dialog(error_info)
        elif error_info.level == ErrorLevel.WARNING:
            self._show_warning_dialog(error_info)

    def _show_error_dialog(self, error_info: ErrorInfo) -> None:
        """显示错误对话框"""
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle("错误")

        # 构建错误消息
        message = error_info.user_message
        if error_info.solution:
            message += f"\n\n解决方案：{error_info.solution}"

        dialog.setText(message)
        dialog.setDetailedText(self._format_error_details(error_info))

        # 添加复制按钮
        copy_button = dialog.addButton("复制错误信息", QMessageBox.ButtonRole.ActionRole)
        copy_button.clicked.connect(lambda: self._copy_error_to_clipboard(error_info))

        dialog.exec()

    def _show_warning_dialog(self, error_info: ErrorInfo) -> None:
        """显示警告对话框"""
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("警告")
        dialog.setText(error_info.user_message)

        if error_info.solution:
            dialog.setInformativeText(error_info.solution)

        dialog.exec()

    def _format_error_details(self, error_info: ErrorInfo) -> str:
        """格式化错误详情"""
        details = []
        details.append(f"错误代码：{error_info.code}")
        details.append(f"错误级别：{error_info.level.value}")
        details.append(f"错误分类：{error_info.category.value}")
        details.append(f"发生时间：{error_info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        if error_info.context.component:
            details.append(f"组件：{error_info.context.component}")
        if error_info.context.function:
            details.append(f"函数：{error_info.context.function}")
        if error_info.context.line_number:
            details.append(f"行号：{error_info.context.line_number}")
        if error_info.context.file_path:
            details.append(f"文件：{error_info.context.file_path}")

        if error_info.exception:
            details.append(f"异常类型：{type(error_info.exception).__name__}")
            details.append(f"异常信息：{str(error_info.exception)}")
            details.append(f"堆栈跟踪：\n{traceback.format_exc()}")

        return "\n".join(details)

    def _copy_error_to_clipboard(self, error_info: ErrorInfo) -> None:
        """复制错误信息到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._format_error_details(error_info))

    def _create_context_from_exception(self, exception: Exception) -> ErrorContext:
        """从异常创建错误上下文"""
        # 获取调用堆栈
        stack = traceback.extract_stack()
        if stack:
            frame = stack[-2] if len(stack) > 1 else stack[-1]
            return ErrorContext(
                function=frame.name,
                line_number=frame.lineno,
                file_path=frame.filename
            )
        return ErrorContext()

    def _generate_error_code(self, exception: Exception, category: ErrorCategory) -> str:
        """生成错误代码"""
        category_prefix = {
            ErrorCategory.SYSTEM: "SYS",
            ErrorCategory.UI: "UI",
            ErrorCategory.FILE: "FILE",
            ErrorCategory.NETWORK: "NET",
            ErrorCategory.AI: "AI",
            ErrorCategory.VIDEO: "VIDEO",
            ErrorCategory.AUDIO: "AUDIO",
            ErrorCategory.CONFIGURATION: "CONFIG",
            ErrorCategory.CONFIG: "CONFIG",
            ErrorCategory.UNKNOWN: "UNK"
        }

        prefix = category_prefix.get(category, "UNK")

        # 根据异常类型生成后缀
        exception_type = type(exception).__name__.upper()
        if exception_type in ["FILENOTFOUNDERROR", "PERMISSIONERROR"]:
            return f"{prefix}_001"
        elif exception_type in ["VALUEERROR", "TYPEERROR"]:
            return f"{prefix}_002"
        elif exception_type in ["CONNECTIONERROR", "TIMEOUTERROR"]:
            return f"{prefix}_003"
        else:
            return f"{prefix}_999"

    def _cleanup_old_errors(self) -> None:
        """清理旧错误记录"""
        # 保留最近7天的错误记录
        cutoff_time = datetime.now().timestamp() - (7 * 24 * 3600)
        self._error_history = [
            error for error in self._error_history
            if error.timestamp.timestamp() > cutoff_time
        ]

    # 公共方法
    def add_listener(self, listener: ErrorListener) -> None:
        """添加错误监听器"""
        self._listeners.append(listener)

    def remove_listener(self, listener: ErrorListener) -> None:
        """移除错误监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def add_error_filter(self, filter_func: Callable[[ErrorInfo], bool]) -> None:
        """添加错误过滤器"""
        self._error_filters.append(filter_func)

    def remove_error_filter(self, filter_func: Callable[[ErrorInfo], bool]) -> None:
        """移除错误过滤器"""
        if filter_func in self._error_filters:
            self._error_filters.remove(filter_func)

    def get_error_count(self) -> int:
        """获取错误总数"""
        return self._error_count

    def get_error_history(self, limit: Optional[int] = None) -> List[ErrorInfo]:
        """获取错误历史记录"""
        if limit is None:
            return self._error_history.copy()
        return self._error_history[-limit:]

    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorInfo]:
        """根据分类获取错误"""
        return [error for error in self._error_history if error.category == category]

    def get_errors_by_level(self, level: ErrorLevel) -> List[ErrorInfo]:
        """根据级别获取错误"""
        return [error for error in self._error_history if error.level == level]

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        stats = {
            'total_errors': self._error_count,
            'by_category': {},
            'by_level': {},
            'recent_errors': len(self._error_history)
        }

        # 按分类统计
        for category in ErrorCategory:
            stats['by_category'][category.value] = len(self.get_errors_by_category(category))

        # 按级别统计
        for level in ErrorLevel:
            stats['by_level'][level.value] = len(self.get_errors_by_level(level))

        return stats

    def export_error_report(self, file_path: str) -> bool:
        """导出错误报告"""
        try:
            report = {
                'export_time': datetime.now().isoformat(),
                'statistics': self.get_error_statistics(),
                'errors': [error.to_dict() for error in self._error_history]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self._logger.error(f"Failed to export error report: {str(e)}")
            return False

    def clear_error_history(self) -> None:
        """清空错误历史记录"""
        self._error_history.clear()
        self._error_count = 0
        self.error_count_updated.emit(0)

    def show_toast(self, title: str, message: str, message_type: str = "info") -> None:
        """显示Toast通知"""
        try:
            from app.ui.components.error_handler import ToastManager, MessageType
            toast_manager = ToastManager()

            # 转换消息类型
            msg_type = MessageType.INFO
            if message_type.lower() == "success":
                msg_type = MessageType.SUCCESS
            elif message_type.lower() == "warning":
                msg_type = MessageType.WARNING
            elif message_type.lower() == "error":
                msg_type = MessageType.ERROR

            toast_manager.show_toast(title, message, msg_type)
        except Exception as e:
            # 如果ToastManager不可用，只记录日志
            self.logger.warning(f"无法显示Toast通知: {e}")

    def cleanup(self) -> None:
        """清理资源"""
        self._cleanup_timer.stop()
        self._listeners.clear()
        self._error_filters.clear()


# 全局错误处理器实例
_global_error_handler = None


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_global_error_handler(handler: ErrorHandler) -> None:
    """设置全局错误处理器"""
    global _global_error_handler
    _global_error_handler = handler


# 错误处理装饰器
def handle_errors(error_category: ErrorCategory = ErrorCategory.UNKNOWN,
                  error_level: ErrorLevel = ErrorLevel.ERROR,
                  show_user: bool = True):
    """错误处理装饰器

    Args:
        error_category: 错误分类
        error_level: 错误级别
        show_user: 是否显示给用户
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_global_error_handler()
                context = ErrorContext(
                    function=func.__name__,
                    component=func.__qualname__.split('.')[0] if '.' in func.__qualname__ else ''
                )
                handler.handle_exception(e, context, error_level, error_category)

                if error_level in [ErrorLevel.ERROR, ErrorLevel.CRITICAL]:
                    raise
                return None
        return wrapper
    return decorator


if __name__ == "__main__":
    # 示例用法
    def test_error_handler():
        """测试错误处理器"""
        handler = ErrorHandler()

        # 创建测试错误
        context = ErrorContext(
            component="TestComponent",
            function="test_function",
            line_number=42
        )

        error_info = ErrorInfo(
            code="TEST_001",
            message="这是一个测试错误",
            level=ErrorLevel.ERROR,
            category=ErrorCategory.SYSTEM,
            context=context
        )

        # 处理错误
        handler.handle_error(error_info)

        # 测试异常处理
        try:
            1 / 0
        except Exception as e:
            handler.handle_exception(e, context)

        print("错误测试完成")

    test_error_handler()
