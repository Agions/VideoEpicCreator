"""
MVVM Architecture Implementation for VideoEpicCreator

This module provides a comprehensive MVVM (Model-View-ViewModel) architecture
implementation with reactive data binding, command patterns, and state management.
"""

import asyncio
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import threading
from weakref import WeakSet, WeakKeyDictionary

from .base import BaseComponent, ComponentConfig, ComponentState
from .events import EventSystem, Event, EventPriority, get_event_system

T = TypeVar('T')


class ViewModelState(Enum):
    """ViewModel lifecycle states"""
    CREATED = "created"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISPOSED = "disposed"


class BindingMode(Enum):
    """Data binding modes"""
    ONE_WAY = "one_way"          # Model -> View
    TWO_WAY = "two_way"          # Model <-> View
    ONE_TIME = "one_time"        # Model -> View (once)
    ONE_WAY_TO_SOURCE = "one_way_to_source"  # View -> Model


@dataclass
class PropertyChangedEventArgs:
    """Property change event arguments"""
    property_name: str
    old_value: Any
    new_value: Any
    source: 'ObservableObject'


class ObservableObject:
    """Base class for objects that support property change notifications"""
    
    def __init__(self):
        self._property_changed_handlers = []
        self._properties = {}
    
    def add_property_changed_handler(self, handler: Callable[[PropertyChangedEventArgs], None]):
        """Add property change handler"""
        self._property_changed_handlers.append(handler)
    
    def remove_property_changed_handler(self, handler: Callable[[PropertyChangedEventArgs], None]):
        """Remove property change handler"""
        if handler in self._property_changed_handlers:
            self._property_changed_handlers.remove(handler)
    
    def notify_property_changed(self, property_name: str, old_value: Any, new_value: Any):
        """Notify listeners that a property has changed"""
        if old_value == new_value:
            return
        
        args = PropertyChangedEventArgs(property_name, old_value, new_value, self)
        
        # Update internal property cache
        self._properties[property_name] = new_value
        
        # Notify handlers
        for handler in self._property_changed_handlers[:]:
            try:
                handler(args)
            except Exception as e:
                logging.error(f"Error in property changed handler: {e}")
    
    def get_property(self, property_name: str, default_value: Any = None) -> Any:
        """Get property value"""
        return self._properties.get(property_name, default_value)
    
    def set_property(self, property_name: str, value: Any):
        """Set property value and notify changes"""
        old_value = self._properties.get(property_name)
        if old_value != value:
            self._properties[property_name] = value
            self.notify_property_changed(property_name, old_value, value)


class Command(ABC):
    """Abstract command interface for MVVM pattern"""
    
    @abstractmethod
    def can_execute(self, parameter: Any = None) -> bool:
        """Check if command can be executed"""
        pass
    
    @abstractmethod
    def execute(self, parameter: Any = None):
        """Execute the command"""
        pass
    
    @abstractmethod
    def add_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Add can execute changed handler"""
        pass
    
    @abstractmethod
    def remove_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Remove can execute changed handler"""
        pass


class RelayCommand(Command):
    """Generic relay command implementation"""
    
    def __init__(self, execute_action: Callable[[Any], None], 
                 can_execute_func: Optional[Callable[[Any], bool]] = None):
        self._execute_action = execute_action
        self._can_execute_func = can_execute_func
        self._can_execute_changed_handlers = []
    
    def can_execute(self, parameter: Any = None) -> bool:
        """Check if command can be executed"""
        if self._can_execute_func is None:
            return True
        return self._can_execute_func(parameter)
    
    def execute(self, parameter: Any = None):
        """Execute the command"""
        if self.can_execute(parameter):
            self._execute_action(parameter)
    
    def add_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Add can execute changed handler"""
        self._can_execute_changed_handlers.append(handler)
    
    def remove_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Remove can execute changed handler"""
        if handler in self._can_execute_changed_handlers:
            self._can_execute_changed_handlers.remove(handler)
    
    def raise_can_execute_changed(self):
        """Raise can execute changed event"""
        for handler in self._can_execute_changed_handlers[:]:
            try:
                handler()
            except Exception as e:
                logging.error(f"Error in can execute changed handler: {e}")


class AsyncCommand(Command):
    """Async command implementation"""
    
    def __init__(self, execute_action: Callable[[Any], asyncio.Future],
                 can_execute_func: Optional[Callable[[Any], bool]] = None):
        self._execute_action = execute_action
        self._can_execute_func = can_execute_func
        self._can_execute_changed_handlers = []
        self._is_executing = False
    
    def can_execute(self, parameter: Any = None) -> bool:
        """Check if command can be executed"""
        if self._is_executing:
            return False
        if self._can_execute_func is None:
            return True
        return self._can_execute_func(parameter)
    
    def execute(self, parameter: Any = None):
        """Execute the command asynchronously"""
        if self.can_execute(parameter):
            self._is_executing = True
            self.raise_can_execute_changed()
            
            async def execute_async():
                try:
                    await self._execute_action(parameter)
                finally:
                    self._is_executing = False
                    self.raise_can_execute_changed()
            
            # Create and return task
            return asyncio.create_task(execute_async())
        
        return None
    
    def add_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Add can execute changed handler"""
        self._can_execute_changed_handlers.append(handler)
    
    def remove_can_execute_changed_handler(self, handler: Callable[[], None]):
        """Remove can execute changed handler"""
        if handler in self._can_execute_changed_handlers:
            self._can_execute_changed_handlers.remove(handler)
    
    def raise_can_execute_changed(self):
        """Raise can execute changed event"""
        for handler in self._can_execute_changed_handlers[:]:
            try:
                handler()
            except Exception as e:
                logging.error(f"Error in can execute changed handler: {e}")


class Binding:
    """Data binding between ViewModel and View"""
    
    def __init__(self, source: ObservableObject, source_property: str,
                 target: Any, target_property: str,
                 mode: BindingMode = BindingMode.ONE_WAY,
                 converter: Optional[Callable[[Any], Any]] = None):
        self.source = source
        self.source_property = source_property
        self.target = target
        self.target_property = target_property
        self.mode = mode
        self.converter = converter or (lambda x: x)
        self.is_active = True
        
        # Set up binding
        self._setup_binding()
    
    def _setup_binding(self):
        """Set up the binding based on mode"""
        if self.mode in [BindingMode.ONE_WAY, BindingMode.TWO_WAY, BindingMode.ONE_TIME]:
            # Source to target binding
            self.source.add_property_changed_handler(self._on_source_property_changed)
            
            # Initial sync
            source_value = self.source.get_property(self.source_property)
            self._update_target(source_value)
        
        if self.mode in [BindingMode.TWO_WAY, BindingMode.ONE_WAY_TO_SOURCE]:
            # Target to source binding (if target supports it)
            if hasattr(self.target, 'add_property_changed_handler'):
                self.target.add_property_changed_handler(self._on_target_property_changed)
    
    def _on_source_property_changed(self, args: PropertyChangedEventArgs):
        """Handle source property change"""
        if args.property_name == self.source_property and self.is_active:
            self._update_target(args.new_value)
    
    def _on_target_property_changed(self, args: PropertyChangedEventArgs):
        """Handle target property change"""
        if args.property_name == self.target_property and self.is_active:
            self._update_source(args.new_value)
    
    def _update_target(self, value: Any):
        """Update target property"""
        try:
            converted_value = self.converter(value)
            
            if hasattr(self.target, 'set_property'):
                self.target.set_property(self.target_property, converted_value)
            else:
                setattr(self.target, self.target_property, converted_value)
        except Exception as e:
            logging.error(f"Error updating target property: {e}")
    
    def _update_source(self, value: Any):
        """Update source property"""
        try:
            converted_value = self.converter(value)
            self.source.set_property(self.source_property, converted_value)
        except Exception as e:
            logging.error(f"Error updating source property: {e}")
    
    def dispose(self):
        """Dispose the binding"""
        self.is_active = False
        
        # Remove event handlers
        self.source.remove_property_changed_handler(self._on_source_property_changed)
        
        if hasattr(self.target, 'remove_property_changed_handler'):
            self.target.remove_property_changed_handler(self._on_target_property_changed)


class ViewModel(ObservableObject, BaseComponent[T]):
    """Base ViewModel class implementing MVVM pattern"""
    
    def __init__(self, name: str, config: Optional[ComponentConfig] = None):
        ObservableObject.__init__(self)
        BaseComponent.__init__(self, name, config)
        
        self.state = ViewModelState.CREATED
        self._commands: Dict[str, Command] = {}
        self._bindings: List[Binding] = []
        self._event_system = get_event_system()
        self._logger = logging.getLogger(f"mvvm.viewmodel.{name}")
        
        # Initialize properties
        self.set_property("is_busy", False)
        self.set_property("is_initialized", False)
        self.set_property("error_message", "")
        self.set_property("progress", 0.0)
    
    async def initialize(self) -> bool:
        """Initialize the ViewModel"""
        try:
            self._logger.info(f"Initializing ViewModel: {self.name}")
            
            # Initialize commands
            await self._initialize_commands()
            
            # Set state
            self.state = ViewModelState.INITIALIZED
            self.set_property("is_initialized", True)
            
            # Emit event
            self._event_system.emit("viewmodel_initialized", {
                "viewmodel": self.name,
                "state": self.state.value
            })
            
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            self.set_property("error_message", str(e))
            return False
    
    async def start(self) -> bool:
        """Start the ViewModel"""
        try:
            self.state = ViewModelState.ACTIVE
            self.set_property("is_active", True)
            
            self._event_system.emit("viewmodel_activated", {
                "viewmodel": self.name,
                "state": self.state.value
            })
            
            return True
        
        except Exception as e:
            self.handle_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Stop the ViewModel"""
        try:
            self.state = ViewModelState.INACTIVE
            self.set_property("is_active", False)
            
            self._event_system.emit("viewmodel_deactivated", {
                "viewmodel": self.name,
                "state": self.state.value
            })
            
            return True
        
        except Exception as e:
            self.handle_error(e, "stop")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up ViewModel resources"""
        try:
            # Dispose all bindings
            for binding in self._bindings:
                binding.dispose()
            self._bindings.clear()
            
            # Clear commands
            self._commands.clear()
            
            # Set state
            self.state = ViewModelState.DISPOSED
            
            # Emit event
            self._event_system.emit("viewmodel_disposed", {
                "viewmodel": self.name,
                "state": self.state.value
            })
            
            return True
        
        except Exception as e:
            self.handle_error(e, "cleanup")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get ViewModel status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "is_busy": self.get_property("is_busy"),
            "is_initialized": self.get_property("is_initialized"),
            "error_message": self.get_property("error_message"),
            "progress": self.get_property("progress"),
            "commands_count": len(self._commands),
            "bindings_count": len(self._bindings),
            "metrics": self.metrics.__dict__
        }
    
    def register_command(self, name: str, command: Command):
        """Register a command"""
        self._commands[name] = command
        self._logger.debug(f"Registered command: {name}")
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name"""
        return self._commands.get(name)
    
    def add_binding(self, binding: Binding):
        """Add a data binding"""
        self._bindings.append(binding)
        self._logger.debug(f"Added binding: {binding.source_property} -> {binding.target_property}")
    
    def remove_binding(self, binding: Binding):
        """Remove a data binding"""
        if binding in self._bindings:
            binding.dispose()
            self._bindings.remove(binding)
            self._logger.debug(f"Removed binding: {binding.source_property} -> {binding.target_property}")
    
    def set_busy(self, busy: bool, message: str = ""):
        """Set busy state"""
        self.set_property("is_busy", busy)
        if message:
            self.set_property("status_message", message)
        
        self._event_system.emit("viewmodel_busy_changed", {
            "viewmodel": self.name,
            "is_busy": busy,
            "message": message
        })
    
    def set_progress(self, progress: float, message: str = ""):
        """Set progress value"""
        progress = max(0.0, min(1.0, progress))
        self.set_property("progress", progress)
        
        if message:
            self.set_property("status_message", message)
        
        self._event_system.emit("viewmodel_progress_changed", {
            "viewmodel": self.name,
            "progress": progress,
            "message": message
        })
    
    def set_error(self, error: str):
        """Set error message"""
        self.set_property("error_message", error)
        self.set_busy(False)
        
        self._event_system.emit("viewmodel_error", {
            "viewmodel": self.name,
            "error": error
        })
    
    def clear_error(self):
        """Clear error message"""
        self.set_property("error_message", "")
    
    async def _initialize_commands(self):
        """Initialize commands (to be overridden by subclasses)"""
        pass
    
    def create_command(self, execute_action: Callable[[Any], None],
                      can_execute_func: Optional[Callable[[Any], bool]] = None,
                      name: Optional[str] = None) -> RelayCommand:
        """Create and register a relay command"""
        command = RelayCommand(execute_action, can_execute_func)
        
        if name:
            self.register_command(name, command)
        
        return command
    
    def create_async_command(self, execute_action: Callable[[Any], asyncio.Future],
                           can_execute_func: Optional[Callable[[Any], bool]] = None,
                           name: Optional[str] = None) -> AsyncCommand:
        """Create and register an async command"""
        command = AsyncCommand(execute_action, can_execute_func)
        
        if name:
            self.register_command(name, command)
        
        return command


class ViewBase:
    """Base View class for MVVM pattern"""
    
    def __init__(self, viewmodel: ViewModel):
        self.viewmodel = viewmodel
        self._bindings: List[Binding] = []
        self._logger = logging.getLogger(f"mvvm.view.{viewmodel.name}")
    
    def bind(self, source_property: str, target_property: str,
             mode: BindingMode = BindingMode.ONE_WAY,
             converter: Optional[Callable[[Any], Any]] = None):
        """Create a binding between ViewModel and View"""
        binding = Binding(
            source=self.viewmodel,
            source_property=source_property,
            target=self,
            target_property=target_property,
            mode=mode,
            converter=converter
        )
        
        self._bindings.append(binding)
        return binding
    
    def unbind_all(self):
        """Remove all bindings"""
        for binding in self._bindings:
            binding.dispose()
        self._bindings.clear()
    
    def get_command(self, command_name: str) -> Optional[Command]:
        """Get command from ViewModel"""
        return self.viewmodel.get_command(command_name)
    
    def show_error(self, message: str):
        """Show error message (to be implemented by subclasses)"""
        self._logger.error(f"Error: {message}")
    
    def show_busy(self, busy: bool, message: str = ""):
        """Show busy state (to be implemented by subclasses)"""
        self._logger.info(f"Busy: {busy}, Message: {message}")
    
    def update_progress(self, progress: float, message: str = ""):
        """Update progress (to be implemented by subclasses)"""
        self._logger.info(f"Progress: {progress:.2f}, Message: {message}")


class ModelBase(ObservableObject):
    """Base Model class for MVVM pattern"""
    
    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id
        self._logger = logging.getLogger(f"mvvm.model.{model_id}")
        
        # Initialize common properties
        self.set_property("id", model_id)
        self.set_property("created_at", None)
        self.set_property("updated_at", None)
        self.set_property("is_valid", True)
        self.set_property("validation_errors", [])
    
    def validate(self) -> List[str]:
        """Validate the model (to be implemented by subclasses)"""
        return []
    
    def is_valid(self) -> bool:
        """Check if model is valid"""
        errors = self.validate()
        self.set_property("validation_errors", errors)
        self.set_property("is_valid", len(errors) == 0)
        return len(errors) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self._properties.copy()
    
    def from_dict(self, data: Dict[str, Any]):
        """Load model from dictionary"""
        for key, value in data.items():
            self.set_property(key, value)
    
    def save_to_file(self, file_path: Path):
        """Save model to file"""
        try:
            data = self.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self._logger.info(f"Model saved to {file_path}")
        
        except Exception as e:
            self._logger.error(f"Error saving model to {file_path}: {e}")
            raise
    
    def load_from_file(self, file_path: Path):
        """Load model from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.from_dict(data)
            self._logger.info(f"Model loaded from {file_path}")
        
        except Exception as e:
            self._logger.error(f"Error loading model from {file_path}: {e}")
            raise


class MVVMContainer:
    """Container for managing MVVM components"""
    
    def __init__(self, event_system: Optional[EventSystem] = None):
        self.event_system = event_system or get_event_system()
        self._viewmodels: Dict[str, ViewModel] = {}
        self._views: Dict[str, ViewBase] = {}
        self._models: Dict[str, ModelBase] = {}
        self._logger = logging.getLogger("mvvm.container")
    
    def register_viewmodel(self, viewmodel: ViewModel):
        """Register a ViewModel"""
        self._viewmodels[viewmodel.name] = viewmodel
        self._logger.debug(f"Registered ViewModel: {viewmodel.name}")
    
    def register_view(self, view: ViewBase):
        """Register a View"""
        view_name = view.viewmodel.name
        self._views[view_name] = view
        self._logger.debug(f"Registered View for: {view_name}")
    
    def register_model(self, model: ModelBase):
        """Register a Model"""
        self._models[model.model_id] = model
        self._logger.debug(f"Registered Model: {model.model_id}")
    
    def get_viewmodel(self, name: str) -> Optional[ViewModel]:
        """Get ViewModel by name"""
        return self._viewmodels.get(name)
    
    def get_view(self, viewmodel_name: str) -> Optional[ViewBase]:
        """Get View by ViewModel name"""
        return self._views.get(viewmodel_name)
    
    def get_model(self, model_id: str) -> Optional[ModelBase]:
        """Get Model by ID"""
        return self._models.get(model_id)
    
    def create_binding(self, viewmodel_name: str, model_id: str,
                      viewmodel_property: str, model_property: str,
                      mode: BindingMode = BindingMode.TWO_WAY):
        """Create binding between ViewModel and Model"""
        viewmodel = self.get_viewmodel(viewmodel_name)
        model = self.get_model(model_id)
        
        if viewmodel and model:
            binding = Binding(
                source=model,
                source_property=model_property,
                target=viewmodel,
                target_property=viewmodel_property,
                mode=mode
            )
            
            self._logger.debug(f"Created binding: {model_id}.{model_property} <-> {viewmodel_name}.{viewmodel_property}")
            return binding
        
        return None
    
    async def initialize_all(self):
        """Initialize all registered ViewModels"""
        for viewmodel in self._viewmodels.values():
            await viewmodel.initialize()
    
    async def start_all(self):
        """Start all registered ViewModels"""
        for viewmodel in self._viewmodels.values():
            await viewmodel.start()
    
    async def stop_all(self):
        """Stop all registered ViewModels"""
        for viewmodel in self._viewmodels.values():
            await viewmodel.stop()
    
    async def cleanup_all(self):
        """Clean up all registered ViewModels"""
        for viewmodel in self._viewmodels.values():
            await viewmodel.cleanup()
    
    def get_status(self) -> Dict[str, Any]:
        """Get container status"""
        return {
            "viewmodels": {name: vm.get_status() for name, vm in self._viewmodels.items()},
            "views": {name: {"viewmodel": view.viewmodel.name} for name, view in self._views.items()},
            "models": {model_id: model.to_dict() for model_id, model in self._models.items()},
            "statistics": {
                "viewmodels_count": len(self._viewmodels),
                "views_count": len(self._views),
                "models_count": len(self._models)
            }
        }


# Global MVVM container instance
_mvvm_container: Optional[MVVMContainer] = None


def get_mvvm_container() -> MVVMContainer:
    """Get the global MVVM container instance"""
    global _mvvm_container
    if _mvvm_container is None:
        _mvvm_container = MVVMContainer()
    return _mvvm_container