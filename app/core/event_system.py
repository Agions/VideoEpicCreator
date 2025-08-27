"""
事件系统
提供事件发布和订阅功能
"""

from typing import Dict, List, Callable, Any
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

class EventType(Enum):
    """事件类型枚举"""
    PROJECT_CREATED = "project_created"
    PROJECT_LOADED = "project_loaded"
    PROJECT_SAVED = "project_saved"
    VIDEO_LOADED = "video_loaded"
    VIDEO_PROCESSED = "video_processed"
    AI_CONTENT_GENERATED = "ai_content_generated"
    AI_GENERATION_STARTED = "ai_generation_started"
    AI_GENERATION_PROGRESS = "ai_generation_progress"
    AI_GENERATION_COMPLETED = "ai_generation_completed"
    AI_GENERATION_ERROR = "ai_generation_error"
    EXPORT_STARTED = "export_started"
    EXPORT_PROGRESS = "export_progress"
    EXPORT_COMPLETED = "export_completed"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class Event:
    """事件数据结构"""
    type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any] = None
    priority: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._running = False
        self._logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        self._logger.debug(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                self._logger.debug(f"Unsubscribed from {event_type}")
            except ValueError:
                pass
    
    async def publish(self, event: Event):
        """发布事件"""
        await self._event_queue.put(event)
        self._logger.debug(f"Event published: {event.type}")
    
    async def start(self):
        """启动事件处理"""
        self._running = True
        asyncio.create_task(self._process_events())
        self._logger.info("Event bus started")
    
    async def stop(self):
        """停止事件处理"""
        self._running = False
        self._logger.info("Event bus stopped")
    
    async def _process_events(self):
        """处理事件队列"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Error processing event: {e}")
    
    async def _handle_event(self, event: Event):
        """处理单个事件"""
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self._logger.error(f"Error in event handler: {e}")

# 全局事件总线
event_bus = EventBus()