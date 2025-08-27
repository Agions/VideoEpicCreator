# Plugin Architecture System

The VideoEpicCreator plugin architecture provides a comprehensive, extensible system for adding custom functionality through plugins.

## Overview

The plugin system includes:

- **Base Plugin Framework**: Abstract base classes and lifecycle management
- **Plugin Discovery**: Automatic discovery and loading of plugins
- **Dependency Injection**: Service container with automatic dependency resolution
- **Configuration Management**: Schema-based configuration with validation
- **Security & Sandboxing**: Code validation and isolated execution
- **Version Management**: Semantic versioning and compatibility checking
- **Integration System**: Event-driven hooks and extension points

## Plugin Types

### 1. AI Model Plugins
Extend AI capabilities with custom models and providers.

### 2. Generator Plugins
Add new content generation types and transformers.

### 3. UI Component Plugins
Extend the user interface with custom components and themes.

### 4. Service Plugins
Add new services and background processing capabilities.

## Creating a Plugin

### 1. Basic Plugin Structure

```python
from app.plugins.base_plugin import BasePlugin, PluginInfo, PluginType, PluginContext
from app.plugins.plugin_config import create_config_schema, ConfigSchema

class MyPlugin(BasePlugin):
    def __init__(self, context: PluginContext):
        super().__init__(context)
    
    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            plugin_id="my_plugin",
            name="My Plugin",
            version="1.0.0",
            description="My custom plugin",
            author="Your Name",
            plugin_type=PluginType.SERVICE,
            dependencies=[],
            permissions=["network.access"]
        )
    
    def initialize(self):
        super().initialize()
        # Plugin initialization code
    
    def enable(self):
        super().enable()
        # Plugin enable code
    
    def disable(self):
        super().disable()
        # Plugin disable code
```

### 2. Adding Configuration

```python
def get_config_schema(self) -> Dict[str, ConfigSchema]:
    definition = {
        "api_key": {
            "type": str,
            "required": False,
            "description": "API key for the service"
        },
        "timeout": {
            "type": int,
            "required": False,
            "default": 30,
            "min_value": 1,
            "max_value": 300
        }
    }
    return create_config_schema(definition)
```

### 3. Adding Hooks

```python
def get_hook_handlers(self) -> Dict[str, callable]:
    return {
        "ai_model_pre_process": self.preprocess_request,
        "ai_model_post_process": self.postprocess_response
    }
    
def preprocess_request(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    # Preprocess logic
    return processed_request
```

## Plugin Lifecycle

1. **Discovery**: Plugin system discovers plugins in configured directories
2. **Validation**: Security and compatibility checks are performed
3. **Loading**: Plugin classes are loaded and instantiated
4. **Initialization**: Plugin.initialize() is called
5. **Enabling**: Plugin.enable() is called when activated
6. **Runtime**: Plugin processes hooks and provides services
7. **Disabling**: Plugin.disable() is called when deactivated
8. **Unloading**: Plugin is removed from the system

## Dependency Injection

Plugins can use dependency injection to access system services:

```python
from app.plugins.dependency_injection import inject

class MyPlugin(BasePlugin):
    @inject
    def __init__(self, context: PluginContext, settings_manager: SettingsManager):
        super().__init__(context)
        self.settings_manager = settings_manager
```

## Configuration Management

Plugins can define configuration schemas that are automatically validated:

```python
def get_config_schema(self) -> Dict[str, ConfigSchema]:
    return {
        "api_url": ConfigSchema(
            type=str,
            required=True,
            default="https://api.example.com",
            validation_rules=["url"]
        ),
        "timeout": ConfigSchema(
            type=int,
            required=False,
            default=30,
            min_value=1,
            max_value=300
        )
    }
```

## Security Features

- **Code Validation**: AST-based static analysis
- **Sandboxing**: Restricted execution environment
- **Permission System**: Fine-grained access control
- **Resource Limits**: CPU, memory, and network restrictions

## Version Management

The system supports semantic versioning with compatibility checking:

```python
from app.plugins.version_management import PluginVersion, PluginDependency

dependencies = [
    PluginDependency(
        plugin_id="required_plugin",
        version_constraints=[VersionConstraint(VersionConstraintOperator.GE, "1.0.0")],
        optional=False
    )
]
```

## Hook System

Plugins can extend system functionality through hooks:

### Available Hooks

- **AI Model Hooks**: `ai_model_pre_process`, `ai_model_post_process`, `ai_model_validate`
- **Generator Hooks**: `generator_pre_generate`, `generator_post_generate`, `generator_validate_content`
- **UI Hooks**: `ui_component_created`, `ui_menu_customize`, `ui_toolbar_customize`
- **Service Hooks**: `service_pre_init`, `service_post_init`, `service_pre_call`, `service_post_call`

## Example Plugins

See the `examples/` directory for complete plugin implementations:

- `example_ai_model_plugin.py`: AI model plugin example
- More examples coming soon...

## Installation

1. Create your plugin in a Python file or directory
2. Place it in one of the configured plugin directories
3. The plugin system will automatically discover and load it

## Best Practices

1. **Use dependency injection** instead of direct service access
2. **Implement proper error handling** in all hook handlers
3. **Provide configuration schemas** for user-configurable options
4. **Use semantic versioning** for compatibility
5. **Implement health checks** for monitoring
6. **Follow the plugin lifecycle** properly
7. **Use the logging system** for debugging
8. **Test your plugins** thoroughly

## API Reference

### Core Classes

- `BasePlugin`: Abstract base class for all plugins
- `PluginInfo`: Plugin metadata and configuration
- `PluginContext`: Runtime environment for plugins
- `PluginManager`: Central plugin management system

### Integration Classes

- `PluginHookManager`: Hook management and execution
- `AIModelPluginIntegration`: AI model plugin integration
- `GeneratorPluginIntegration`: Generator plugin integration
- `UIPluginIntegration`: UI component plugin integration
- `ServicePluginIntegration`: Service plugin integration

### Utility Classes

- `ServiceContainer`: Dependency injection container
- `ConfigManager`: Configuration management
- `VersionManager`: Version compatibility management
- `PluginSecurityManager`: Security and sandboxing

## Troubleshooting

### Common Issues

1. **Plugin not loading**: Check file permissions and syntax
2. **Dependency errors**: Verify all required dependencies are available
3. **Configuration errors**: Check configuration schema validation
4. **Permission errors**: Verify plugin has required permissions
5. **Version conflicts**: Check version compatibility constraints

### Debugging

Enable debug logging for detailed plugin system information:

```python
import logging
logging.getLogger('app.plugins').setLevel(logging.DEBUG)
```

## Contributing

When creating plugins for VideoEpicCreator:

1. Follow the plugin structure and lifecycle
2. Use the provided integration points
3. Implement proper error handling
4. Provide comprehensive configuration options
5. Include documentation and examples
6. Test thoroughly across different scenarios

## Support

For plugin development support:

- Check the API documentation
- Review example plugins
- Use the logging system for debugging
- Contact the development team for assistance