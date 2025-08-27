"""
Configuration management system for VideoEpicCreator

This module provides a comprehensive configuration management system
with environment variable support, type validation, and secure storage.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


@dataclass
class AISettings:
    """AI configuration settings"""
    default_model: str = "openai"
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 30
    
    # Model-specific settings
    openai_api_key: Optional[str] = None
    qianwen_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"


@dataclass
class VideoSettings:
    """Video processing settings"""
    default_quality: str = "high"
    preview_resolution: str = "720p"
    export_format: str = "mp4"
    ffmpeg_path: str = "ffmpeg"
    max_memory_usage: int = 2048  # MB
    cache_size: int = 100  # preview frames


@dataclass
class UISettings:
    """User interface settings"""
    theme: str = "dark"
    language: str = "zh_CN"
    accessibility: bool = True
    window_width: int = 1200
    window_height: int = 800


class SettingsConfig(BaseModel):
    """Main configuration model"""
    ai: AISettings = Field(default_factory=AISettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    ui: UISettings = Field(default_factory=UISettings)
    
    # General settings
    log_level: str = "INFO"
    debug_mode: bool = False
    auto_save: bool = True
    auto_save_interval: int = 300  # seconds
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level: {v}')
        return v.upper()


class Settings:
    """Main settings manager"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self._config: Optional[SettingsConfig] = None
        self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path"""
        return Path.home() / ".videoepiccreator" / "config.yaml"
    
    def _load_config(self):
        """Load configuration from file and environment variables"""
        config_data = {}
        
        # Load from file if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if self.config_path.suffix.lower() == '.json':
                        config_data = json.load(f)
                    else:
                        config_data = yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
        
        # Override with environment variables
        env_config = self._load_env_config()
        config_data = {**config_data, **env_config}
        
        # Create configuration object
        self._config = SettingsConfig(**config_data)
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_mapping = {
            'OPENAI_API_KEY': ['ai', 'openai_api_key'],
            'QIANWEN_API_KEY': ['ai', 'qianwen_api_key'],
            'OLLAMA_BASE_URL': ['ai', 'ollama_base_url'],
            'LOG_LEVEL': ['log_level'],
            'MAX_MEMORY_USAGE': ['video', 'max_memory_usage'],
            'CACHE_SIZE': ['video', 'cache_size'],
            'FFMPEG_PATH': ['video', 'ffmpeg_path'],
            'UI_THEME': ['ui', 'theme'],
            'UI_LANGUAGE': ['ui', 'language'],
        }
        
        config = {}
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate nested dictionary
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert to appropriate type
                final_key = config_path[-1]
                if final_key in ['max_memory_usage', 'cache_size', 'timeout', 'auto_save_interval']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif final_key in ['temperature']:
                    try:
                        value = float(value)
                    except ValueError:
                        continue
                elif final_key in ['debug_mode', 'auto_save', 'accessibility']:
                    value = value.lower() in ['true', '1', 'yes', 'on']
                
                current[final_key] = value
        
        return config
    
    def save(self):
        """Save current configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = self._config.dict()
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            if self.config_path.suffix.lower() == '.json':
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    value = getattr(value, k)
            return value
        except (AttributeError, KeyError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config_obj = self._config
        
        # Navigate to parent object
        for k in keys[:-1]:
            if isinstance(config_obj, dict):
                if k not in config_obj:
                    config_obj[k] = {}
                config_obj = config_obj[k]
            else:
                config_obj = getattr(config_obj, k)
        
        # Set final value
        final_key = keys[-1]
        if isinstance(config_obj, dict):
            config_obj[final_key] = value
        else:
            setattr(config_obj, final_key, value)
    
    def get_ai_settings(self) -> AISettings:
        """Get AI settings"""
        return self._config.ai
    
    def get_video_settings(self) -> VideoSettings:
        """Get video settings"""
        return self._config.video
    
    def get_ui_settings(self) -> UISettings:
        """Get UI settings"""
        return self._config.ui
    
    def update_ai_settings(self, **kwargs):
        """Update AI settings"""
        for key, value in kwargs.items():
            if hasattr(self._config.ai, key):
                setattr(self._config.ai, key, value)
    
    def update_video_settings(self, **kwargs):
        """Update video settings"""
        for key, value in kwargs.items():
            if hasattr(self._config.video, key):
                setattr(self._config.video, key, value)
    
    def update_ui_settings(self, **kwargs):
        """Update UI settings"""
        for key, value in kwargs.items():
            if hasattr(self._config.ui, key):
                setattr(self._config.ui, key, value)
    
    @property
    def config(self) -> SettingsConfig:
        """Get the full configuration object"""
        return self._config
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self._config = SettingsConfig()
        self.save()
    
    def export_config(self, path: Union[str, Path]):
        """Export configuration to a file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = self._config.dict()
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix.lower() == '.json':
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
    
    def import_config(self, path: Union[str, Path]):
        """Import configuration from a file"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                config_data = yaml.safe_load(f)
        
        # Validate and update configuration
        new_config = SettingsConfig(**config_data)
        self._config = new_config
        self.save()