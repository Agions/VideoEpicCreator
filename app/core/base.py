"""
基础类和接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

class AppState(Enum):
    """应用状态枚举"""
    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    ERROR = "error"
    COMPLETED = "completed"

@dataclass
class BaseModel:
    """基础数据模型"""
    id: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = datetime.now().timestamp()
        if self.updated_at == 0:
            self.updated_at = datetime.now().timestamp()
        if self.metadata is None:
            self.metadata = {}

class ViewModel(ABC):
    """视图模型基类"""
    
    def __init__(self):
        self._state = AppState.IDLE
        self._observers = []
        self._data = {}
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add_observer(self, observer):
        """添加观察者"""
        self._observers.append(observer)
    
    def remove_observer(self, observer):
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, event_type: str, data: Any = None):
        """通知观察者"""
        for observer in self._observers:
            if hasattr(observer, 'on_view_model_changed'):
                observer.on_view_model_changed(event_type, data)
    
    @property
    def state(self) -> AppState:
        return self._state
    
    @state.setter
    def state(self, value: AppState):
        if self._state != value:
            self._state = value
            self.notify_observers('state_changed', value)
    
    def update_data(self, key: str, value: Any):
        """更新数据"""
        self._data[key] = value
        self.notify_observers('data_updated', {key: value})
    
    def get_data(self, key: str, default=None):
        """获取数据"""
        return self._data.get(key, default)

class ServiceInterface(ABC):
    """服务接口"""
    
    @abstractmethod
    async def start(self):
        """启动服务"""
        pass
    
    @abstractmethod
    async def stop(self):
        """停止服务"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass