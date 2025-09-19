#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AIModelConfig:
    """AI模型配置"""
    name: str
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    enabled: bool = False
    use_proxy: bool = False
    proxy_url: str = ""
    custom_headers: Dict[str, str] = None
    # 讯飞星火专用
    api_secret: str = ""
    app_id: str = ""
    timeout: int = 30
    
    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


@dataclass
class AIResponse:
    """AI响应结果"""
    success: bool
    content: str = ""
    error_message: str = ""
    usage: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
        if self.metadata is None:
            self.metadata = {}


class BaseAIModel(ABC):
    """AI模型基类"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.name = config.name
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化模型连接"""
        pass
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本内容"""
        pass
    
    @abstractmethod
    async def analyze_content(self, content: str, analysis_type: str = "general") -> AIResponse:
        """分析内容"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查模型是否可用"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.config.enabled:
            return False
        
        # 基础验证
        if not self.config.name:
            return False
            
        return True
    
    def update_config(self, new_config: AIModelConfig):
        """更新配置"""
        self.config = new_config
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"
    
    def __repr__(self):
        return self.__str__()
