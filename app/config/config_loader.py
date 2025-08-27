"""
Configuration loader for VideoEpicCreator

This module provides utilities for loading and validating configuration files
with support for multiple formats and schema validation.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from pydantic import ValidationError


class ConfigLoader:
    """Configuration file loader with validation"""
    
    SUPPORTED_FORMATS = {'.json', '.yaml', '.yml'}
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd()
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
    
    def load_config(self, config_path: Union[str, Path], 
                   schema_class: Optional[type] = None) -> Dict[str, Any]:
        """Load configuration from file with optional schema validation"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_path.suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported configuration format: {config_path.suffix}")
        
        # Load based on file extension
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix == '.json':
                    config_data = json.load(f)
                else:  # .yaml or .yml
                    config_data = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to load configuration file {config_path}: {e}")
        
        # Validate against schema if provided
        if schema_class:
            try:
                config_obj = schema_class(**config_data)
                config_data = config_obj.dict()
            except ValidationError as e:
                raise ValueError(f"Configuration validation failed: {e}")
        
        # Cache the loaded configuration
        cache_key = str(config_path)
        self._loaded_configs[cache_key] = config_data
        
        return config_data
    
    def load_env_config(self, prefix: str = "VIDEOEPIC_") -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                
                # Convert to appropriate type
                if value.lower() in ('true', 'false'):
                    config[config_key] = value.lower() == 'true'
                elif value.isdigit():
                    config[config_key] = int(value)
                elif value.replace('.', '', 1).isdigit():
                    config[config_key] = float(value)
                else:
                    config[config_key] = value
        
        return config
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries"""
        merged = {}
        
        for config in configs:
            if config:
                self._deep_merge(merged, config)
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_cached_config(self, config_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get cached configuration if available"""
        cache_key = str(config_path)
        return self._loaded_configs.get(cache_key)
    
    def clear_cache(self):
        """Clear all cached configurations"""
        self._loaded_configs.clear()
    
    def create_default_config(self, config_path: Union[str, Path], 
                            default_config: Dict[str, Any]) -> None:
        """Create a default configuration file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_path.suffix == '.json':
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def validate_config_structure(self, config: Dict[str, Any], 
                                required_keys: list) -> bool:
        """Validate that configuration has required structure"""
        def check_keys(data: Dict[str, Any], keys: list, current_path: str = "") -> bool:
            for key in keys:
                full_path = f"{current_path}.{key}" if current_path else key
                
                if key not in data:
                    print(f"Missing required key: {full_path}")
                    return False
                
                if isinstance(keys[keys.index(key)], dict):
                    if not isinstance(data[key], dict):
                        print(f"Expected dict at {full_path}, got {type(data[key])}")
                        return False
                    
                    nested_keys = keys[keys.index(key)]
                    if not check_keys(data[key], nested_keys, full_path):
                        return False
            
            return True
        
        return check_keys(config, required_keys)
    
    def get_config_schema(self, config_type: str) -> Dict[str, Any]:
        """Get configuration schema for validation"""
        schemas = {
            'ai': {
                'default_model': str,
                'max_tokens': int,
                'temperature': float,
                'timeout': int,
                'openai_api_key': Optional[str],
                'qianwen_api_key': Optional[str],
                'ollama_base_url': str
            },
            'video': {
                'default_quality': str,
                'preview_resolution': str,
                'export_format': str,
                'ffmpeg_path': str,
                'max_memory_usage': int,
                'cache_size': int
            },
            'ui': {
                'theme': str,
                'language': str,
                'accessibility': bool,
                'window_width': int,
                'window_height': int
            }
        }
        
        return schemas.get(config_type, {})
    
    def migrate_config(self, old_config: Dict[str, Any], 
                      from_version: str, to_version: str) -> Dict[str, Any]:
        """Migrate configuration between versions"""
        # Simple migration logic - in practice, this would be more comprehensive
        migrated = old_config.copy()
        
        if from_version == "1.0" and to_version == "2.0":
            # Example migration: add new fields
            if 'ai' not in migrated:
                migrated['ai'] = {
                    'default_model': 'openai',
                    'max_tokens': 2000,
                    'temperature': 0.7
                }
            
            if 'video' not in migrated:
                migrated['video'] = {
                    'default_quality': 'high',
                    'preview_resolution': '720p'
                }
        
        return migrated