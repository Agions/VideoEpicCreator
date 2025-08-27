"""
Event system for VideoEpicCreator

This module provides a comprehensive event system for decoupled communication
between components with support for prioritization, async handling, and event filtering.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Event data structure"""
    event_type: str
    data: Any = None
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.source is None:
            self.source = "unknown"


@dataclass
class EventHandler:
    """Event handler wrapper"""
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL
    filter_func: Optional[Callable[[Event], bool]] = None
    async_handler: bool = False
    once: bool = False
    active: bool = True
    call_count: int = 0
    max_calls: Optional[int] = None
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class EventSystem:
    """Central event system for the application"""
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger("videoepiccreator.events")
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self._running = False
        self._stats = {
            "events_emitted": 0,
            "events_handled": 0,
            "handlers_registered": 0,
            "errors": 0
        }
    
    def register_handler(self, event_type: str, handler: Callable, 
                        priority: EventPriority = EventPriority.NORMAL,
                        filter_func: Optional[Callable[[Event], bool]] = None,
                        async_handler: bool = False,
                        once: bool = False,
                        max_calls: Optional[int] = None) -> str:
        """Register an event handler"""
        with self._lock:
            event_handler = EventHandler(
                handler=handler,
                priority=priority,
                filter_func=filter_func,
                async_handler=async_handler,
                once=once,
                max_calls=max_calls
            )
            
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            
            self._handlers[event_type].append(event_handler)
            self._handlers[event_type].sort(key=lambda h: h.priority.value, reverse=True)
            
            self._stats["handlers_registered"] += 1
            self.logger.debug(f"Registered handler for {event_type}: {event_handler.handler_id}")
            
            return event_handler.handler_id
    
    def register_global_handler(self, handler: Callable,
                               priority: EventPriority = EventPriority.NORMAL,
                               filter_func: Optional[Callable[[Event], bool]] = None,
                               async_handler: bool = False,
                               once: bool = False,
                               max_calls: Optional[int] = None) -> str:
        """Register a global event handler (receives all events)"""
        with self._lock:
            event_handler = EventHandler(
                handler=handler,
                priority=priority,
                filter_func=filter_func,
                async_handler=async_handler,
                once=once,
                max_calls=max_calls
            )
            
            self._global_handlers.append(event_handler)
            self._global_handlers.sort(key=lambda h: h.priority.value, reverse=True)
            
            self._stats["handlers_registered"] += 1
            self.logger.debug(f"Registered global handler: {event_handler.handler_id}")
            
            return event_handler.handler_id
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister an event handler by ID"""
        with self._lock:
            # Check specific event handlers
            for event_type, handlers in self._handlers.items():
                for handler in handlers[:]:
                    if handler.handler_id == handler_id:
                        handlers.remove(handler)
                        self.logger.debug(f"Unregistered handler for {event_type}: {handler_id}")
                        return True
            
            # Check global handlers
            for handler in self._global_handlers[:]:
                if handler.handler_id == handler_id:
                    self._global_handlers.remove(handler)
                    self.logger.debug(f"Unregistered global handler: {handler_id}")
                    return True
            
            return False
    
    def unregister_all_handlers(self, event_type: Optional[str] = None):
        """Unregister all handlers for a specific event type or all handlers"""
        with self._lock:
            if event_type:
                if event_type in self._handlers:
                    del self._handlers[event_type]
                    self.logger.debug(f"Unregistered all handlers for {event_type}")
            else:
                self._handlers.clear()
                self._global_handlers.clear()
                self.logger.debug("Unregistered all handlers")
    
    def emit(self, event_type: str, data: Any = None, source: Optional[str] = None,
            priority: EventPriority = EventPriority.NORMAL,
            metadata: Optional[Dict[str, Any]] = None) -> Event:
        """Emit an event"""
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            priority=priority,
            metadata=metadata or {}
        )
        
        return self.emit_event(event)
    
    def emit_event(self, event: Event) -> Event:
        """Emit a pre-constructed event"""
        with self._lock:
            self._stats["events_emitted"] += 1
            
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
        
        # Log event emission
        self.logger.debug(f"Emitted event: {event.event_type} from {event.source}")
        
        # Process handlers
        self._process_event(event)
        
        return event
    
    def _process_event(self, event: Event):
        """Process event through all applicable handlers"""
        handlers_to_process = []
        
        with self._lock:
            # Get specific handlers for this event type
            specific_handlers = self._handlers.get(event.event_type, [])
            
            # Combine with global handlers
            all_handlers = specific_handlers + self._global_handlers
            
            # Filter active handlers that pass the filter function
            for handler in all_handlers:
                if (handler.active and 
                    (handler.max_calls is None or handler.call_count < handler.max_calls) and
                    (handler.filter_func is None or handler.filter_func(event))):
                    handlers_to_process.append(handler)
        
        # Process handlers
        for handler in handlers_to_process:
            try:
                if handler.async_handler:
                    # Run async handler
                    asyncio.create_task(self._run_async_handler(handler, event))
                else:
                    # Run sync handler
                    self._executor.submit(self._run_sync_handler, handler, event)
                
                with self._lock:
                    handler.call_count += 1
                    self._stats["events_handled"] += 1
                
                # Remove one-time handlers
                if handler.once:
                    self.unregister_handler(handler.handler_id)
                
            except Exception as e:
                with self._lock:
                    self._stats["errors"] += 1
                self.logger.error(f"Error processing event {event.event_type} with handler {handler.handler_id}: {e}")
    
    async def _run_async_handler(self, handler: EventHandler, event: Event):
        """Run an async event handler"""
        try:
            if asyncio.iscoroutinefunction(handler.handler):
                await handler.handler(event)
            else:
                # Wrap sync function in async
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._executor, handler.handler, event)
        except Exception as e:
            self.logger.error(f"Error in async handler {handler.handler_id}: {e}")
    
    def _run_sync_handler(self, handler: EventHandler, event: Event):
        """Run a sync event handler"""
        try:
            handler.handler(event)
        except Exception as e:
            self.logger.error(f"Error in sync handler {handler.handler_id}: {e}")
    
    def emit_sync(self, event_type: str, data: Any = None, source: Optional[str] = None,
                 priority: EventPriority = EventPriority.NORMAL,
                 metadata: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Emit an event and wait for all synchronous handlers to complete"""
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            priority=priority,
            metadata=metadata or {}
        )
        
        return self.emit_event_sync(event)
    
    def emit_event_sync(self, event: Event) -> List[Any]:
        """Emit a pre-constructed event and wait for synchronous handlers"""
        with self._lock:
            self._stats["events_emitted"] += 1
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
        
        results = []
        
        # Get handlers to process
        handlers_to_process = []
        with self._lock:
            specific_handlers = self._handlers.get(event.event_type, [])
            all_handlers = specific_handlers + self._global_handlers
            
            for handler in all_handlers:
                if (handler.active and not handler.async_handler and
                    (handler.max_calls is None or handler.call_count < handler.max_calls) and
                    (handler.filter_func is None or handler.filter_func(event))):
                    handlers_to_process.append(handler)
        
        # Process handlers synchronously
        for handler in handlers_to_process:
            try:
                result = handler.handler(event)
                results.append(result)
                
                with self._lock:
                    handler.call_count += 1
                    self._stats["events_handled"] += 1
                
                if handler.once:
                    self.unregister_handler(handler.handler_id)
                    
            except Exception as e:
                with self._lock:
                    self._stats["errors"] += 1
                self.logger.error(f"Error processing event {event.event_type} with handler {handler.handler_id}: {e}")
        
        return results
    
    def get_event_history(self, event_type: Optional[str] = None, 
                          limit: Optional[int] = None) -> List[Event]:
        """Get event history, optionally filtered by event type"""
        with self._lock:
            history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_handler_count(self, event_type: Optional[str] = None) -> int:
        """Get count of registered handlers"""
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type, []))
            else:
                total = sum(len(handlers) for handlers in self._handlers.values())
                return total + len(self._global_handlers)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event system statistics"""
        with self._lock:
            return {
                **self._stats,
                "handler_count": self.get_handler_count(),
                "event_types": list(self._handlers.keys()),
                "history_size": len(self._event_history),
                "global_handlers": len(self._global_handlers)
            }
    
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._event_history.clear()
            self.logger.debug("Event history cleared")
    
    def reset_stats(self):
        """Reset event system statistics"""
        with self._lock:
            self._stats = {
                "events_emitted": 0,
                "events_handled": 0,
                "handlers_registered": 0,
                "errors": 0
            }
            self.logger.debug("Event system stats reset")
    
    def start(self):
        """Start the event system"""
        self._running = True
        self.logger.info("Event system started")
    
    def stop(self):
        """Stop the event system"""
        self._running = False
        self._executor.shutdown(wait=True)
        self.logger.info("Event system stopped")
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Global event system instance
_event_system: Optional[EventSystem] = None


def get_event_system() -> EventSystem:
    """Get the global event system instance"""
    global _event_system
    if _event_system is None:
        _event_system = EventSystem()
    return _event_system


def emit(event_type: str, data: Any = None, source: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None) -> Event:
    """Emit an event using the global event system"""
    return get_event_system().emit(event_type, data, source, priority, metadata)


def register_handler(event_type: str, handler: Callable, 
                     priority: EventPriority = EventPriority.NORMAL,
                     filter_func: Optional[Callable[[Event], bool]] = None,
                     async_handler: bool = False,
                     once: bool = False,
                     max_calls: Optional[int] = None) -> str:
    """Register an event handler using the global event system"""
    return get_event_system().register_handler(
        event_type, handler, priority, filter_func, async_handler, once, max_calls
    )