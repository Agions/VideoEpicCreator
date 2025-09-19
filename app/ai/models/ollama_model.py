#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama模型占位文件
用于解决导入问题
"""

from .base_model import BaseAIModel, AIModelConfig, AIResponse


class OllamaModel(BaseAIModel):
    """Ollama模型类（占位实现）"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.model_name = "llama2"
    
    def generate_text(self, prompt: str) -> AIResponse:
        """生成文本（占位实现）"""
        return AIResponse(
            success=True,
            content="这是Ollama模型的占位响应",
            model=self.model_name,
            usage={}
        )