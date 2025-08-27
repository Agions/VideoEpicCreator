"""
Dependency Injection and Service Management System

This module provides a comprehensive dependency injection container and service
management system with lifecycle management, configuration, and plugin support.
"""

import asyncio
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref

from .base import BaseComponent, ComponentConfig, ComponentState
from .events import EventSystem, get_event_system

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime options"""
    SINGLETON = "singleton"    # Single instance for entire application
    SCOPED = "scoped"          # Single instance per scope
    TRANSIENT = "transient"    # New instance each time
    MANAGED = "managed"        # Managed by the container with lifecycle


class ServiceState(Enum):
    """Service lifecycle states"""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DISPOSING = "disposing"
    DISPOSED = "disposed"
    ERROR = "error"


@dataclass
class ServiceDescriptor:
    """Service registration descriptor"""
    service_type: Type
    implementation_type: Type
    lifetime: ServiceLifetime
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ServiceScope:
    """Service scope for scoped services"""
    name: str
    parent_scope: Optional['ServiceScope'] = None
    services: Dict[str, Any] = field(default_factory=dict)
    is_disposed: bool = False


class ServiceContainer(ABC):
    """Abstract service container interface"""
    
    @abstractmethod
    def register(self, service_type: Type, implementation_type: Type,
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                 factory: Optional[Callable] = None,
                 config: Optional[Dict[str, Any]] = None,
                 priority: int = 0,
                 tags: Optional[List[str]] = None,
                 description: str = "") -> str:
        """Register a service"""
        pass
    
    @abstractmethod
    def get(self, service_type: Type) -> Any:
        """Get a service instance"""
        pass
    
    @abstractmethod
    def get_by_name(self, service_name: str) -> Any:
        """Get a service by name"""
        pass
    
    @abstractmethod
    def create_scope(self, scope_name: str) -> 'ServiceScope':
        """Create a new scope"""
        pass
    
    @abstractmethod
    async def initialize_all(self) -> bool:
        """Initialize all services"""
        pass
    
    @abstractmethod
    async def start_all(self) -> bool:
        """Start all services"""
        pass
    
    @abstractmethod
    async def stop_all(self) -> bool:
        """Stop all services"""
        pass
    
    @abstractmethod
    async def dispose_all(self) -> bool:
        """Dispose all services"""
        pass


class DependencyResolver:
    """Dependency resolver for constructor injection"""
    
    def __init__(self, container: 'ServiceContainerImpl'):
        self.container = container
        self._logger = logging.getLogger("dependency_resolver")
    
    def resolve_dependencies(self, target_type: Type, scope: Optional[ServiceScope] = None) -> Dict[str, Any]:
        """Resolve dependencies for a type"""
        try:
            # Get constructor signature
            signature = inspect.signature(target_type.__init__)
            parameters = signature.parameters
            
            # Skip 'self' parameter
            if 'self' in parameters:
                del parameters['self']
            
            dependencies = {}
            
            for param_name, param in parameters.items():
                if param_name == 'args' or param_name == 'kwargs':
                    continue
                
                # Get type annotation
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    self._logger.warning(f"No type annotation for parameter {param_name} in {target_type.__name__}")
                    continue
                
                # Resolve dependency
                try:
                    dependency = self.container._resolve_service(param_type, scope)
                    dependencies[param_name] = dependency
                except Exception as e:
                    self._logger.error(f"Failed to resolve dependency {param_name} for {target_type.__name__}: {e}")
                    raise
            
            return dependencies
        
        except Exception as e:
            self._logger.error(f"Error resolving dependencies for {target_type.__name__}: {e}")
            raise
    
    def inject_dependencies(self, instance: Any, scope: Optional[ServiceScope] = None):
        """Inject dependencies into an instance"""
        try:
            # Get type hints for the instance
            type_hints = get_type_hints(instance.__class__)
            
            for attr_name, attr_type in type_hints.items():
                # Skip private attributes and methods
                if attr_name.startswith('_') or inspect.isfunction(getattr(instance.__class__, attr_name, None)):
                    continue
                
                # Check if attribute exists and is None
                if hasattr(instance, attr_name) and getattr(instance, attr_name) is None:
                    try:
                        dependency = self.container._resolve_service(attr_type, scope)
                        setattr(instance, attr_name, dependency)
                    except Exception as e:
                        self._logger.warning(f"Failed to inject {attr_name} into {instance.__class__.__name__}: {e}")
        
        except Exception as e:
            self._logger.error(f"Error injecting dependencies into {instance.__class__.__name__}: {e}")


class ServiceContainerImpl(BaseComponent[Dict[str, Any]], ServiceContainer):
    """Main service container implementation"""
    
    def __init__(self, config: Optional[ComponentConfig] = None):
        super().__init__("service_container", config)
        
        self._services: Dict[str, ServiceDescriptor] = {}
        self._service_states: Dict[str, ServiceState] = {}
        self._service_instances: Dict[str, Any] = {}
        self._scopes: Dict[str, ServiceScope] = {}
        self._type_to_name: Dict[Type, str] = {}
        
        self._dependency_resolver = DependencyResolver(self)
        self._event_system = get_event_system()
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        self._logger = logging.getLogger("service_container")
        
        # Create root scope
        self._root_scope = ServiceScope("root")
        self._current_scope = self._root_scope
    
    async def initialize(self) -> bool:
        """Initialize the service container"""
        try:
            self.logger.info("Initializing Service Container")
            
            # Register self as a service
            self.register(ServiceContainer, ServiceContainerImpl, ServiceLifetime.SINGLETON)
            self._service_instances["ServiceContainer"] = self
            self._service_states["ServiceContainer"] = ServiceState.RUNNING
            
            # Register event system
            self.register(EventSystem, EventSystem, ServiceLifetime.SINGLETON)
            self._service_instances["EventSystem"] = self._event_system
            self._service_states["EventSystem"] = ServiceState.RUNNING
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            return False
    
    async def start(self) -> bool:
        """Start the service container"""
        try:
            # Start all services in dependency order
            startup_order = self._get_service_startup_order()
            
            for service_name in startup_order:
                await self._start_service(service_name)
            
            self.logger.info(f"Started {len(startup_order)} services")
            return True
        
        except Exception as e:
            self.handle_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Stop the service container"""
        try:
            # Stop all services in reverse dependency order
            startup_order = self._get_service_startup_order()
            
            for service_name in reversed(startup_order):
                await self._stop_service(service_name)
            
            self.logger.info("Stopped all services")
            return True
        
        except Exception as e:
            self.handle_error(e, "stop")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up service container"""
        try:
            # Dispose all services
            startup_order = self._get_service_startup_order()
            
            for service_name in reversed(startup_order):
                await self._dispose_service(service_name)
            
            # Clean up scopes
            for scope in self._scopes.values():
                scope.is_disposed = True
            
            self._scopes.clear()
            self._services.clear()
            self._service_states.clear()
            self._service_instances.clear()
            self._type_to_name.clear()
            
            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            self.logger.info("Service container cleaned up")
            return True
        
        except Exception as e:
            self.handle_error(e, "cleanup")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service container status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "services": {
                name: {
                    "state": state.value,
                    "type": descriptor.service_type.__name__,
                    "lifetime": descriptor.lifetime.value,
                    "instance_exists": name in self._service_instances
                }
                for name, (descriptor, state) in zip(self._services.keys(), 
                                                   self._services.values(), 
                                                   self._service_states.values())
            },
            "scopes": {
                name: {
                    "parent": scope.parent_scope.name if scope.parent_scope else None,
                    "services_count": len(scope.services),
                    "is_disposed": scope.is_disposed
                }
                for name, scope in self._scopes.items()
            },
            "statistics": {
                "total_services": len(self._services),
                "running_services": len([s for s in self._service_states.values() if s == ServiceState.RUNNING]),
                "error_services": len([s for s in self._service_states.values() if s == ServiceState.ERROR]),
                "active_scopes": len([s for s in self._scopes.values() if not s.is_disposed])
            },
            "metrics": self.metrics.__dict__
        }
    
    def register(self, service_type: Type, implementation_type: Type,
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                 factory: Optional[Callable] = None,
                 config: Optional[Dict[str, Any]] = None,
                 priority: int = 0,
                 tags: Optional[List[str]] = None,
                 description: str = "") -> str:
        """Register a service"""
        service_name = self._get_service_name(service_type)
        
        if service_name in self._services:
            self.logger.warning(f"Service already registered: {service_name}")
            return service_name
        
        # Create service descriptor
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=lifetime,
            factory=factory,
            config=config or {},
            priority=priority,
            tags=tags or [],
            description=description
        )
        
        # Analyze dependencies
        descriptor.dependencies = self._analyze_dependencies(implementation_type)
        
        # Register service
        self._services[service_name] = descriptor
        self._service_states[service_name] = ServiceState.REGISTERED
        self._type_to_name[service_type] = service_name
        
        self.logger.info(f"Registered service: {service_name} ({lifetime.value})")
        
        # Emit event
        self._event_system.emit("service_registered", {
            "service_name": service_name,
            "service_type": service_type.__name__,
            "lifetime": lifetime.value
        })
        
        return service_name
    
    def get(self, service_type: Type) -> Any:
        """Get a service instance"""
        service_name = self._get_service_name(service_type)
        return self._resolve_service(service_type, self._current_scope)
    
    def get_by_name(self, service_name: str) -> Any:
        """Get a service by name"""
        descriptor = self._services.get(service_name)
        if descriptor is None:
            raise ValueError(f"Service not found: {service_name}")
        
        return self._resolve_service(descriptor.service_type, self._current_scope)
    
    def create_scope(self, scope_name: str) -> ServiceScope:
        """Create a new scope"""
        scope = ServiceScope(scope_name, self._current_scope)
        self._scopes[scope_name] = scope
        return scope
    
    def _get_service_name(self, service_type: Type) -> str:
        """Get service name from type"""
        return service_type.__name__
    
    def _resolve_service(self, service_type: Type, scope: Optional[ServiceScope] = None) -> Any:
        """Resolve a service instance"""
        service_name = self._get_service_name(service_type)
        descriptor = self._services.get(service_name)
        
        if descriptor is None:
            raise ValueError(f"Service not registered: {service_name}")
        
        # Check if already instantiated
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_name in self._service_instances:
                return self._service_instances[service_name]
        
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if scope and service_name in scope.services:
                return scope.services[service_name]
        
        # Create new instance
        instance = self._create_instance(descriptor, scope)
        
        # Store instance
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            self._service_instances[service_name] = instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED and scope:
            scope.services[service_name] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope] = None) -> Any:
        """Create a service instance"""
        try:
            if descriptor.factory:
                # Use factory method
                instance = descriptor.factory()
            else:
                # Use constructor injection
                dependencies = self._dependency_resolver.resolve_dependencies(
                    descriptor.implementation_type, scope
                )
                instance = descriptor.implementation_type(**dependencies)
            
            # Inject properties
            self._dependency_resolver.inject_dependencies(instance, scope)
            
            return instance
        
        except Exception as e:
            self.logger.error(f"Error creating instance of {descriptor.service_type.__name__}: {e}")
            raise
    
    def _analyze_dependencies(self, implementation_type: Type) -> List[str]:
        """Analyze dependencies of a service type"""
        try:
            signature = inspect.signature(implementation_type.__init__)
            parameters = signature.parameters
            
            dependencies = []
            
            for param_name, param in parameters.items():
                if param_name == 'self' or param_name == 'args' or param_name == 'kwargs':
                    continue
                
                param_type = param.annotation
                if param_type != inspect.Parameter.empty:
                    dependencies.append(self._get_service_name(param_type))
            
            return dependencies
        
        except Exception as e:
            self.logger.error(f"Error analyzing dependencies for {implementation_type.__name__}: {e}")
            return []
    
    def _get_service_startup_order(self) -> List[str]:
        """Get service startup order using topological sort"""
        # Build dependency graph
        graph = {}
        in_degree = {}
        
        for service_name, descriptor in self._services.items():
            graph[service_name] = descriptor.dependencies
            in_degree[service_name] = 0
        
        # Calculate in-degree
        for service_name, dependencies in graph.items():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Topological sort
        queue = [name for name in graph if in_degree[name] == 0]
        result = []
        
        while queue:
            # Sort by priority
            queue.sort(key=lambda x: self._services[x].priority, reverse=True)
            
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result
    
    async def _start_service(self, service_name: str):
        """Start a specific service"""
        if service_name not in self._services:
            return
        
        if self._service_states[service_name] == ServiceState.RUNNING:
            return
        
        try:
            descriptor = self._services[service_name]
            
            # Get instance
            instance = self._resolve_service(descriptor.service_type, self._current_scope)
            
            # Initialize if needed
            if self._service_states[service_name] == ServiceState.REGISTERED:
                self._service_states[service_name] = ServiceState.INITIALIZING
                
                if hasattr(instance, 'initialize') and callable(instance.initialize):
                    if await instance.initialize():
                        self._service_states[service_name] = ServiceState.INITIALIZED
                    else:
                        self._service_states[service_name] = ServiceState.ERROR
                        self.logger.error(f"Failed to initialize service: {service_name}")
                        return
                else:
                    self._service_states[service_name] = ServiceState.INITIALIZED
            
            # Start service
            self._service_states[service_name] = ServiceState.STARTING
            
            if hasattr(instance, 'start') and callable(instance.start):
                if await instance.start():
                    self._service_states[service_name] = ServiceState.RUNNING
                    self.logger.info(f"Service started: {service_name}")
                    
                    # Emit event
                    self._event_system.emit("service_started", {
                        "service_name": service_name,
                        "service_type": descriptor.service_type.__name__
                    })
                else:
                    self._service_states[service_name] = ServiceState.ERROR
                    self.logger.error(f"Failed to start service: {service_name}")
            else:
                self._service_states[service_name] = ServiceState.RUNNING
                self.logger.info(f"Service started: {service_name}")
        
        except Exception as e:
            self._service_states[service_name] = ServiceState.ERROR
            self.logger.error(f"Error starting service {service_name}: {e}")
    
    async def _stop_service(self, service_name: str):
        """Stop a specific service"""
        if service_name not in self._services:
            return
        
        if self._service_states[service_name] != ServiceState.RUNNING:
            return
        
        try:
            descriptor = self._services[service_name]
            instance = self._service_instances.get(service_name)
            
            if instance and hasattr(instance, 'stop') and callable(instance.stop):
                self._service_states[service_name] = ServiceState.STOPPING
                
                if await instance.stop():
                    self._service_states[service_name] = ServiceState.STOPPED
                    self.logger.info(f"Service stopped: {service_name}")
                    
                    # Emit event
                    self._event_system.emit("service_stopped", {
                        "service_name": service_name,
                        "service_type": descriptor.service_type.__name__
                    })
                else:
                    self.logger.error(f"Failed to stop service: {service_name}")
            else:
                self._service_states[service_name] = ServiceState.STOPPED
                self.logger.info(f"Service stopped: {service_name}")
        
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {e}")
    
    async def _dispose_service(self, service_name: str):
        """Dispose a specific service"""
        if service_name not in self._services:
            return
        
        try:
            descriptor = self._services[service_name]
            instance = self._service_instances.get(service_name)
            
            if instance and hasattr(instance, 'cleanup') and callable(instance.cleanup):
                self._service_states[service_name] = ServiceState.DISPOSING
                
                if await instance.cleanup():
                    self._service_states[service_name] = ServiceState.DISPOSED
                    self.logger.info(f"Service disposed: {service_name}")
                else:
                    self.logger.error(f"Failed to dispose service: {service_name}")
            else:
                self._service_states[service_name] = ServiceState.DISPOSED
                self.logger.info(f"Service disposed: {service_name}")
        
        except Exception as e:
            self.logger.error(f"Error disposing service {service_name}: {e}")
    
    async def initialize_all(self) -> bool:
        """Initialize all services"""
        startup_order = self._get_service_startup_order()
        
        for service_name in startup_order:
            if self._service_states[service_name] == ServiceState.REGISTERED:
                try:
                    descriptor = self._services[service_name]
                    instance = self._resolve_service(descriptor.service_type, self._current_scope)
                    
                    if hasattr(instance, 'initialize') and callable(instance.initialize):
                        self._service_states[service_name] = ServiceState.INITIALIZING
                        
                        if await instance.initialize():
                            self._service_states[service_name] = ServiceState.INITIALIZED
                        else:
                            self._service_states[service_name] = ServiceState.ERROR
                            self.logger.error(f"Failed to initialize service: {service_name}")
                    else:
                        self._service_states[service_name] = ServiceState.INITIALIZED
                
                except Exception as e:
                    self._service_states[service_name] = ServiceState.ERROR
                    self.logger.error(f"Error initializing service {service_name}: {e}")
        
        return True
    
    async def start_all(self) -> bool:
        """Start all services"""
        return await self.start()
    
    async def stop_all(self) -> bool:
        """Stop all services"""
        return await self.stop()
    
    async def dispose_all(self) -> bool:
        """Dispose all services"""
        return await self.cleanup()
    
    def get_service_descriptor(self, service_name: str) -> Optional[ServiceDescriptor]:
        """Get service descriptor"""
        return self._services.get(service_name)
    
    def get_service_state(self, service_name: str) -> ServiceState:
        """Get service state"""
        return self._service_states.get(service_name, ServiceState.UNREGISTERED)
    
    def get_services_by_tag(self, tag: str) -> List[str]:
        """Get services by tag"""
        return [
            name for name, descriptor in self._services.items()
            if tag in descriptor.tags
        ]
    
    def get_services_by_lifetime(self, lifetime: ServiceLifetime) -> List[str]:
        """Get services by lifetime"""
        return [
            name for name, descriptor in self._services.items()
            if descriptor.lifetime == lifetime
        ]


# Decorators for dependency injection
def inject(service_type: Type):
    """Decorator for property injection"""
    def decorator(cls):
        def __init__(original_init):
            def __init__(self, *args, **kwargs):
                # This will be handled by the dependency resolver
                # The actual injection happens at runtime
                original_init(self, *args, **kwargs)
            return __init__
        
        cls.__init__ = __init__(cls.__init__)
        return cls
    return decorator


def singleton(cls):
    """Decorator to register a class as a singleton service"""
    cls._service_lifetime = ServiceLifetime.SINGLETON
    return cls


def scoped(cls):
    """Decorator to register a class as a scoped service"""
    cls._service_lifetime = ServiceLifetime.SCOPED
    return cls


def transient(cls):
    """Decorator to register a class as a transient service"""
    cls._service_lifetime = ServiceLifetime.TRANSIENT
    return cls


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get the global service container instance"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainerImpl()
    return _service_container


def register_service(service_type: Type, implementation_type: Type,
                     lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                     **kwargs):
    """Register a service with the global container"""
    container = get_service_container()
    return container.register(service_type, implementation_type, lifetime, **kwargs)


def get_service(service_type: Type) -> Any:
    """Get a service from the global container"""
    container = get_service_container()
    return container.get(service_type)