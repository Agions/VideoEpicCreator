"""
Modular Architecture Structure for VideoEpicCreator

This module defines the comprehensive modular architecture with clear separation
of concerns, dependency management, and plugin support.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import importlib
import inspect
from abc import ABC, abstractmethod

from .base import BaseComponent, ComponentConfig, ComponentState
from .mvvm import MVVMContainer, get_mvvm_container
from .events import EventSystem, get_event_system


class ModuleType(Enum):
    """Module types"""
    CORE = "core"              # Core system modules
    AI = "ai"                 # AI service modules
    SERVICES = "services"     # External service modules
    PLUGINS = "plugins"       # Plugin modules
    UI = "ui"                 # User interface modules
    UTILS = "utils"           # Utility modules


class ModuleState(Enum):
    """Module lifecycle states"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModuleDependency:
    """Module dependency specification"""
    module_name: str
    version_range: str = "*"  # Semantic version range
    optional: bool = False
    description: str = ""


@dataclass
class ModuleInfo:
    """Module metadata"""
    name: str
    version: str
    description: str
    author: str
    module_type: ModuleType
    dependencies: List[ModuleDependency] = field(default_factory=list)
    entry_point: str = ""
    config_schema: Optional[Dict[str, Any]] = None
    api_version: str = "1.0.0"
    minimum_core_version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    icon: Optional[str] = None


@dataclass
class ModuleConfig:
    """Module configuration"""
    enabled: bool = True
    auto_start: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Startup priority (higher = earlier)


class ModuleInterface(ABC):
    """Interface for all modules"""
    
    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """Get module information"""
        pass
    
    @abstractmethod
    async def initialize(self, module_manager: 'ModuleManager') -> bool:
        """Initialize the module"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the module"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the module"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up module resources"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get module status"""
        pass
    
    @abstractmethod
    def get_config(self) -> ModuleConfig:
        """Get module configuration"""
        pass
    
    @abstractmethod
    def update_config(self, config: ModuleConfig):
        """Update module configuration"""
        pass


class ModuleManager(BaseComponent[Dict[str, Any]]):
    """Central module manager for the application"""
    
    def __init__(self, config: Optional[ComponentConfig] = None):
        super().__init__("module_manager", config)
        
        self._modules: Dict[str, ModuleInterface] = {}
        self._module_states: Dict[str, ModuleState] = {}
        self._module_configs: Dict[str, ModuleConfig] = {}
        self._module_dependencies: Dict[str, List[str]] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
        
        self._event_system = get_event_system()
        self._mvvm_container = get_mvvm_container()
        
        # Module directories
        self._module_dirs = {
            ModuleType.CORE: Path(__file__).parent.parent / "core",
            ModuleType.AI: Path(__file__).parent.parent / "ai",
            ModuleType.SERVICES: Path(__file__).parent.parent / "services",
            ModuleType.PLUGINS: Path(__file__).parent.parent / "plugins",
            ModuleType.UI: Path(__file__).parent.parent / "ui",
            ModuleType.UTILS: Path(__file__).parent.parent / "utils"
        }
        
        self._logger = logging.getLogger("module_manager")
    
    async def initialize(self) -> bool:
        """Initialize the module manager"""
        try:
            self.logger.info("Initializing Module Manager")
            
            # Discover all modules
            await self._discover_modules()
            
            # Load module configurations
            await self._load_module_configs()
            
            # Build dependency graph
            self._build_dependency_graph()
            
            # Validate dependencies
            if not self._validate_dependencies():
                self.logger.error("Dependency validation failed")
                return False
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            return False
    
    async def start(self) -> bool:
        """Start the module manager"""
        try:
            # Start modules in dependency order
            startup_order = self._get_startup_order()
            
            for module_name in startup_order:
                if self._module_configs[module_name].auto_start:
                    await self._start_module(module_name)
            
            self.logger.info(f"Started {len(startup_order)} modules")
            return True
        
        except Exception as e:
            self.handle_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Stop the module manager"""
        try:
            # Stop modules in reverse dependency order
            startup_order = self._get_startup_order()
            
            for module_name in reversed(startup_order):
                await self._stop_module(module_name)
            
            self.logger.info("Stopped all modules")
            return True
        
        except Exception as e:
            self.handle_error(e, "stop")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up module manager resources"""
        try:
            # Cleanup all modules
            for module_name in list(self._modules.keys()):
                await self._cleanup_module(module_name)
            
            self._modules.clear()
            self._module_states.clear()
            self._module_configs.clear()
            self._module_dependencies.clear()
            self._dependency_graph.clear()
            
            self.logger.info("Module manager cleaned up")
            return True
        
        except Exception as e:
            self.handle_error(e, "cleanup")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get module manager status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "modules": {
                name: {
                    "state": state.value,
                    "enabled": self._module_configs[name].enabled,
                    "info": self._modules[name].module_info.__dict__
                }
                for name, state in self._module_states.items()
            },
            "dependency_graph": self._dependency_graph,
            "statistics": {
                "total_modules": len(self._modules),
                "loaded_modules": len([s for s in self._module_states.values() if s == ModuleState.LOADED]),
                "started_modules": len([s for s in self._module_states.values() if s == ModuleState.STARTED]),
                "error_modules": len([s for s in self._module_states.values() if s == ModuleState.ERROR])
            },
            "metrics": self.metrics.__dict__
        }
    
    async def _discover_modules(self):
        """Discover all available modules"""
        for module_type, module_dir in self._module_dirs.items():
            if not module_dir.exists():
                self.logger.warning(f"Module directory not found: {module_dir}")
                continue
            
            await self._scan_module_directory(module_type, module_dir)
    
    async def _scan_module_directory(self, module_type: ModuleType, module_dir: Path):
        """Scan a directory for modules"""
        for item in module_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                await self._try_load_module(module_type, item)
    
    async def _try_load_module(self, module_type: ModuleType, module_path: Path):
        """Try to load a module from directory"""
        try:
            # Check for module manifest
            manifest_path = module_path / "module.json"
            if not manifest_path.exists():
                self.logger.debug(f"No manifest found for module: {module_path.name}")
                return
            
            # Load manifest
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # Create module info
            module_info = ModuleInfo(
                name=manifest_data["name"],
                version=manifest_data["version"],
                description=manifest_data.get("description", ""),
                author=manifest_data.get("author", ""),
                module_type=module_type,
                dependencies=[
                    ModuleDependency(**dep) for dep in manifest_data.get("dependencies", [])
                ],
                entry_point=manifest_data.get("entry_point", "main"),
                config_schema=manifest_data.get("config_schema"),
                api_version=manifest_data.get("api_version", "1.0.0"),
                minimum_core_version=manifest_data.get("minimum_core_version", "1.0.0"),
                tags=manifest_data.get("tags", []),
                icon=manifest_data.get("icon")
            )
            
            # Validate module info
            if not self._validate_module_info(module_info):
                self.logger.warning(f"Invalid module info for: {module_info.name}")
                return
            
            # Load module class
            module_class = await self._load_module_class(module_path, module_info.entry_point)
            if module_class is None:
                return
            
            # Create module instance
            module_instance = module_class()
            
            # Register module
            self._register_module(module_info, module_instance)
            
            self.logger.info(f"Loaded module: {module_info.name} v{module_info.version}")
        
        except Exception as e:
            self.logger.error(f"Error loading module from {module_path}: {e}")
    
    async def _load_module_class(self, module_path: Path, entry_point: str) -> Optional[Type[ModuleInterface]]:
        """Load module class from path"""
        try:
            # Add module path to Python path
            module_path_str = str(module_path.parent)
            if module_path_str not in sys.path:
                sys.path.insert(0, module_path_str)
            
            # Import module
            module_name = module_path.name
            spec = importlib.util.spec_from_file_location(module_name, module_path / f"{entry_point}.py")
            if spec is None or spec.loader is None:
                self.logger.error(f"Could not load module spec for: {module_name}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find module class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, ModuleInterface) and 
                    obj != ModuleInterface):
                    return obj
            
            self.logger.error(f"No ModuleInterface class found in: {module_name}")
            return None
        
        except Exception as e:
            self.logger.error(f"Error loading module class: {e}")
            return None
    
    def _validate_module_info(self, module_info: ModuleInfo) -> bool:
        """Validate module information"""
        # Check required fields
        if not module_info.name or not module_info.version:
            return False
        
        # Check name format
        if not module_info.name.replace("_", "").replace("-", "").isalnum():
            return False
        
        # Check version format
        if not self._is_valid_version(module_info.version):
            return False
        
        return True
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid"""
        import re
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+)?(\+[a-zA-Z0-9-]+)?$'
        return re.match(pattern, version) is not None
    
    def _register_module(self, module_info: ModuleInfo, module_instance: ModuleInterface):
        """Register a module"""
        module_name = module_info.name
        
        self._modules[module_name] = module_instance
        self._module_states[module_name] = ModuleState.LOADED
        self._module_configs[module_name] = ModuleConfig()
        
        # Store dependencies
        self._module_dependencies[module_name] = [
            dep.module_name for dep in module_info.dependencies
        ]
        
        # Emit event
        self._event_system.emit("module_loaded", {
            "module_name": module_name,
            "module_info": module_info.__dict__
        })
    
    async def _load_module_configs(self):
        """Load module configurations"""
        # Load from configuration files or database
        # This is a simplified implementation
        for module_name in self._modules:
            self._module_configs[module_name] = ModuleConfig()
    
    def _build_dependency_graph(self):
        """Build module dependency graph"""
        self._dependency_graph.clear()
        
        for module_name, dependencies in self._module_dependencies.items():
            self._dependency_graph[module_name] = dependencies.copy()
    
    def _validate_dependencies(self) -> bool:
        """Validate module dependencies"""
        for module_name, dependencies in self._module_dependencies.items():
            for dep_name in dependencies:
                if dep_name not in self._modules:
                    self.logger.error(f"Missing dependency: {module_name} -> {dep_name}")
                    return False
        
        # Check for circular dependencies
        if self._has_circular_dependencies():
            self.logger.error("Circular dependencies detected")
            return False
        
        return True
    
    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._dependency_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self._dependency_graph:
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def _get_startup_order(self) -> List[str]:
        """Get module startup order using topological sort"""
        in_degree = {node: 0 for node in self._dependency_graph}
        
        # Calculate in-degree
        for node in self._dependency_graph:
            for neighbor in self._dependency_graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1
        
        # Topological sort
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            # Sort by priority
            queue.sort(key=lambda x: self._module_configs[x].priority, reverse=True)
            
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self._dependency_graph.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result
    
    async def _start_module(self, module_name: str):
        """Start a specific module"""
        if module_name not in self._modules:
            self.logger.error(f"Module not found: {module_name}")
            return
        
        if self._module_states[module_name] == ModuleState.STARTED:
            return
        
        try:
            module = self._modules[module_name]
            config = self._module_configs[module_name]
            
            if not config.enabled:
                self.logger.info(f"Module disabled: {module_name}")
                return
            
            # Initialize module
            if self._module_states[module_name] == ModuleState.LOADED:
                if await module.initialize(self):
                    self._module_states[module_name] = ModuleState.INITIALIZED
                else:
                    self._module_states[module_name] = ModuleState.ERROR
                    self.logger.error(f"Failed to initialize module: {module_name}")
                    return
            
            # Start module
            if await module.start():
                self._module_states[module_name] = ModuleState.STARTED
                self.logger.info(f"Module started: {module_name}")
                
                # Emit event
                self._event_system.emit("module_started", {
                    "module_name": module_name,
                    "module_info": module.module_info.__dict__
                })
            else:
                self._module_states[module_name] = ModuleState.ERROR
                self.logger.error(f"Failed to start module: {module_name}")
        
        except Exception as e:
            self._module_states[module_name] = ModuleState.ERROR
            self.logger.error(f"Error starting module {module_name}: {e}")
    
    async def _stop_module(self, module_name: str):
        """Stop a specific module"""
        if module_name not in self._modules:
            return
        
        if self._module_states[module_name] != ModuleState.STARTED:
            return
        
        try:
            module = self._modules[module_name]
            
            if await module.stop():
                self._module_states[module_name] = ModuleState.STOPPED
                self.logger.info(f"Module stopped: {module_name}")
                
                # Emit event
                self._event_system.emit("module_stopped", {
                    "module_name": module_name,
                    "module_info": module.module_info.__dict__
                })
            else:
                self.logger.error(f"Failed to stop module: {module_name}")
        
        except Exception as e:
            self.logger.error(f"Error stopping module {module_name}: {e}")
    
    async def _cleanup_module(self, module_name: str):
        """Cleanup a specific module"""
        if module_name not in self._modules:
            return
        
        try:
            module = self._modules[module_name]
            await module.cleanup()
            
            self._module_states[module_name] = ModuleState.UNLOADED
            self.logger.info(f"Module cleaned up: {module_name}")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up module {module_name}: {e}")
    
    def get_module(self, module_name: str) -> Optional[ModuleInterface]:
        """Get a module by name"""
        return self._modules.get(module_name)
    
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """Get module information by name"""
        module = self._modules.get(module_name)
        return module.module_info if module else None
    
    def get_module_state(self, module_name: str) -> ModuleState:
        """Get module state"""
        return self._module_states.get(module_name, ModuleState.UNLOADED)
    
    def get_module_config(self, module_name: str) -> Optional[ModuleConfig]:
        """Get module configuration"""
        return self._module_configs.get(module_name)
    
    def update_module_config(self, module_name: str, config: ModuleConfig):
        """Update module configuration"""
        if module_name in self._module_configs:
            self._module_configs[module_name] = config
            
            # Notify module
            module = self._modules.get(module_name)
            if module:
                module.update_config(config)
            
            self.logger.info(f"Updated configuration for module: {module_name}")
    
    def enable_module(self, module_name: str):
        """Enable a module"""
        if module_name in self._module_configs:
            self._module_configs[module_name].enabled = True
            self.logger.info(f"Enabled module: {module_name}")
    
    def disable_module(self, module_name: str):
        """Disable a module"""
        if module_name in self._module_configs:
            self._module_configs[module_name].enabled = False
            self.logger.info(f"Disabled module: {module_name}")
    
    def reload_module(self, module_name: str) -> bool:
        """Reload a module (not implemented)"""
        self.logger.warning("Module reload not implemented")
        return False
    
    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleInterface]:
        """Get all modules of a specific type"""
        return [
            module for name, module in self._modules.items()
            if module.module_info.module_type == module_type
        ]
    
    def get_dependency_tree(self, module_name: str) -> Dict[str, List[str]]:
        """Get dependency tree for a module"""
        if module_name not in self._dependency_graph:
            return {}
        
        tree = {}
        visited = set()
        
        def build_tree(node):
            if node in visited:
                return
            
            visited.add(node)
            tree[node] = self._dependency_graph.get(node, [])
            
            for dep in tree[node]:
                if dep not in visited:
                    build_tree(dep)
        
        build_tree(module_name)
        return tree
    
    def get_all_module_info(self) -> List[ModuleInfo]:
        """Get information for all modules"""
        return [module.module_info for module in self._modules.values()]


# Global module manager instance
_module_manager: Optional[ModuleManager] = None


def get_module_manager() -> ModuleManager:
    """Get the global module manager instance"""
    global _module_manager
    if _module_manager is None:
        _module_manager = ModuleManager()
    return _module_manager


def register_module(module_class: Type[ModuleInterface]):
    """Decorator to register a module class"""
    def decorator(cls):
        # This would be used in module files to auto-register
        # Implementation would depend on how modules are discovered
        return cls
    return decorator