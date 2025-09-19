#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一错误处理系统 - 提供全面的错误管理和日志记录
"""

import sys
import traceback
import logging
from typing import Optional, Dict, Any, List, Callable, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget


class ErrorLevel(Enum):
    """错误级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """错误类别枚举"""
    SYSTEM = "SYSTEM"
    UI = "UI"
    AI = "AI"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE = "FILE"
    NETWORK = "NETWORK"
    CONFIGURATION = "CONFIGURATION"
    USER_INPUT = "USER_INPUT"
    CONFIG = "CONFIG"  # 兼容性别名
    UNKNOWN = "UNKNOWN"  # 兼容性别名


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_id: str
    level: ErrorLevel
    category: ErrorCategory
    message: str
    context: str
    timestamp: datetime
    exception_type: Optional[Type[Exception]] = None
    stack_trace: Optional[str] = None
    user_action: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_id': self.error_id,
            'level': self.level.value,
            'category': self.category.value,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'exception_type': self.exception_type.__name__ if self.exception_type else None,
            'stack_trace': self.stack_trace,
            'user_action': self.user_action,
            'additional_data': self.additional_data or {}
        }


class ErrorSignalEmitter(QObject):
    """错误信号发射器"""
    
    # 信号定义
    error_occurred = pyqtSignal(ErrorInfo)  # 错误发生信号
    error_handled = pyqtSignal(str)  # 错误处理完成信号
    error_reported = pyqtSignal(ErrorInfo)  # 错误报告信号


class GlobalErrorHandler:
    """全局错误处理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._error_history: List[ErrorInfo] = []
        self._error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._signal_emitter = ErrorSignalEmitter()
        self._logger = self._setup_logger()
        
        # 设置全局异常处理
        sys.excepthook = self._global_exception_handler
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('CineAIStudio.ErrorHandler')
        logger.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建文件处理器
        file_handler = logging.FileHandler('cineai_studio_errors.log')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        error_info = self._create_error_info(
            exception=exc_value,
            level=ErrorLevel.CRITICAL,
            category=ErrorCategory.SYSTEM,
            context="全局异常处理器",
            user_action="系统运行时"
        )
        
        self.handle_error(error_info)
        
        # 显示错误对话框
        if hasattr(self, '_main_window'):
            QMessageBox.critical(
                self._main_window,
                "严重错误",
                f"程序遇到严重错误:\n\n{error_info.message}\n\n详细信息已记录到日志文件。"
            )
    
    def _create_error_info(
        self,
        message: str,
        level: ErrorLevel,
        category: ErrorCategory,
        context: str,
        exception: Optional[Exception] = None,
        user_action: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """创建错误信息对象"""
        import uuid
        
        error_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        exception_type = None
        stack_trace = None
        
        if exception:
            exception_type = type(exception)
            stack_trace = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        
        return ErrorInfo(
            error_id=error_id,
            level=level,
            category=category,
            message=message,
            context=context,
            timestamp=timestamp,
            exception_type=exception_type,
            stack_trace=stack_trace,
            user_action=user_action,
            additional_data=additional_data
        )
    
    def handle_error(
        self,
        error_info: ErrorInfo,
        show_dialog: bool = True,
        parent_widget: Optional[QWidget] = None
    ) -> None:
        """处理错误"""
        # 记录错误
        self._log_error(error_info)
        
        # 添加到错误历史
        self._error_history.append(error_info)
        
        # 发射错误信号
        self._signal_emitter.error_occurred.emit(error_info)
        
        # 调用类别特定的错误回调
        if error_info.category in self._error_callbacks:
            for callback in self._error_callbacks[error_info.category]:
                try:
                    callback(error_info)
                except Exception as e:
                    self._logger.error(f"错误回调执行失败: {e}")
        
        # 显示错误对话框
        if show_dialog:
            self._show_error_dialog(error_info, parent_widget)
        
        # 发射错误处理完成信号
        self._signal_emitter.error_handled.emit(error_info.error_id)
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """记录错误到日志"""
        log_message = f"[{error_info.category.value}] {error_info.context}: {error_info.message}"
        
        if error_info.user_action:
            log_message += f" (用户操作: {error_info.user_action})"
        
        if error_info.stack_trace:
            log_message += f"\n堆栈跟踪:\n{error_info.stack_trace}"
        
        # 根据错误级别记录
        if error_info.level == ErrorLevel.DEBUG:
            self._logger.debug(log_message)
        elif error_info.level == ErrorLevel.INFO:
            self._logger.info(log_message)
        elif error_info.level == ErrorLevel.WARNING:
            self._logger.warning(log_message)
        elif error_info.level == ErrorLevel.ERROR:
            self._logger.error(log_message)
        elif error_info.level == ErrorLevel.CRITICAL:
            self._logger.critical(log_message)
    
    def _show_error_dialog(self, error_info: ErrorInfo, parent_widget: Optional[QWidget] = None) -> None:
        """显示错误对话框"""
        # 根据错误级别选择对话框类型
        if error_info.level == ErrorLevel.DEBUG or error_info.level == ErrorLevel.INFO:
            QMessageBox.information(
                parent_widget or self._get_main_window(),
                "信息",
                error_info.message
            )
        elif error_info.level == ErrorLevel.WARNING:
            QMessageBox.warning(
                parent_widget or self._get_main_window(),
                "警告",
                error_info.message
            )
        elif error_info.level == ErrorLevel.ERROR or error_info.level == ErrorLevel.CRITICAL:
            detailed_message = error_info.message
            if error_info.context:
                detailed_message += f"\n\n上下文: {error_info.context}"
            if error_info.user_action:
                detailed_message += f"\n\n用户操作: {error_info.user_action}"
            
            QMessageBox.critical(
                parent_widget or self._get_main_window(),
                "错误",
                detailed_message
            )
    
    def _get_main_window(self) -> Optional[QWidget]:
        """获取主窗口"""
        return getattr(self, '_main_window', None)
    
    def set_main_window(self, main_window: QWidget) -> None:
        """设置主窗口"""
        self._main_window = main_window
    
    def register_error_callback(
        self,
        category: ErrorCategory,
        callback: Callable[[ErrorInfo], None]
    ) -> None:
        """注册错误回调函数"""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def get_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        level: Optional[ErrorLevel] = None,
        limit: Optional[int] = None
    ) -> List[ErrorInfo]:
        """获取错误历史"""
        filtered_errors = self._error_history
        
        # 按类别过滤
        if category:
            filtered_errors = [e for e in filtered_errors if e.category == category]
        
        # 按级别过滤
        if level:
            filtered_errors = [e for e in filtered_errors if e.level == level]
        
        # 限制数量
        if limit:
            filtered_errors = filtered_errors[-limit:]
        
        return filtered_errors
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self._error_history:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_level': {},
                'recent_errors': []
            }
        
        # 按类别统计
        by_category = {}
        for error in self._error_history:
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
        
        # 按级别统计
        by_level = {}
        for error in self._error_history:
            level = error.level.value
            by_level[level] = by_level.get(level, 0) + 1
        
        # 最近错误
        recent_errors = [e.to_dict() for e in self._error_history[-10:]]
        
        return {
            'total_errors': len(self._error_history),
            'by_category': by_category,
            'by_level': by_level,
            'recent_errors': recent_errors
        }
    
    def clear_error_history(self) -> None:
        """清空错误历史"""
        self._error_history.clear()
        self._logger.info("错误历史已清空")
    
    def export_error_report(self, file_path: str) -> bool:
        """导出错误报告"""
        try:
            import json
            
            report = {
                'export_time': datetime.now().isoformat(),
                'statistics': self.get_error_statistics(),
                'errors': [e.to_dict() for e in self._error_history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"错误报告已导出到: {file_path}")
            return True
            
        except Exception as e:
            self._logger.error(f"导出错误报告失败: {e}")
            return False
    
    @property
    def signal_emitter(self) -> ErrorSignalEmitter:
        """获取信号发射器"""
        return self._signal_emitter


class ErrorHandlerMixin:
    """错误处理混入类"""
    
    def __init__(self):
        self._error_context = self.__class__.__name__
        self._global_handler = GlobalErrorHandler()
    
    def set_error_context(self, context: str) -> None:
        """设置错误上下文"""
        self._error_context = context
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        user_action: Optional[str] = None,
        show_dialog: bool = True,
        level: ErrorLevel = ErrorLevel.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM
    ) -> None:
        """处理错误"""
        error_info = self._global_handler._create_error_info(
            message=str(error),
            level=level,
            category=category,
            context=context or self._error_context,
            exception=error,
            user_action=user_action
        )
        
        self._global_handler.handle_error(error_info, show_dialog, getattr(self, 'parent', lambda: None)())
    
    def handle_error_safe(
        self,
        message: str,
        context: Optional[str] = None,
        user_action: Optional[str] = None,
        show_dialog: bool = True,
        level: ErrorLevel = ErrorLevel.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM
    ) -> None:
        """安全处理错误（无异常）"""
        error_info = self._global_handler._create_error_info(
            message=message,
            level=level,
            category=category,
            context=context or self._error_context,
            user_action=user_action
        )
        
        self._global_handler.handle_error(error_info, show_dialog, getattr(self, 'parent', lambda: None)())
    
    def safe_execute(
        self,
        func: Callable,
        *args,
        context: Optional[str] = None,
        user_action: Optional[str] = None,
        show_dialog: bool = True,
        **kwargs
    ) -> Any:
        """安全执行函数"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(
                error=e,
                context=context or f"执行 {func.__name__}",
                user_action=user_action,
                show_dialog=show_dialog
            )
            return None


# 创建全局错误处理器实例
global_error_handler = GlobalErrorHandler()


def handle_error(
    error: Exception,
    context: str = "未知上下文",
    user_action: Optional[str] = None,
    show_dialog: bool = True,
    level: ErrorLevel = ErrorLevel.ERROR,
    category: ErrorCategory = ErrorCategory.SYSTEM
) -> None:
    """全局错误处理函数"""
    global_error_handler.handle_error(
        error_info=global_error_handler._create_error_info(
            message=str(error),
            level=level,
            category=category,
            context=context,
            exception=error,
            user_action=user_action
        ),
        show_dialog=show_dialog
    )


def safe_execute(
    func: Callable,
    *args,
    context: Optional[str] = None,
    user_action: Optional[str] = None,
    show_dialog: bool = True,
    **kwargs
) -> Any:
    """全局安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(
            error=e,
            context=context or f"执行 {func.__name__}",
            user_action=user_action,
            show_dialog=show_dialog
        )
        return None