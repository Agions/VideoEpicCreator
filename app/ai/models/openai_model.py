#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI模型集成
"""

import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from .base_model import BaseAIModel, AIModelConfig, AIResponse


class OpenAIModel(BaseAIModel):
    """OpenAI模型集成"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.session = None
        self.model_name = config.model or "gpt-3.5-turbo"
    
    async def initialize(self) -> bool:
        """初始化OpenAI连接"""
        try:
            if not self.validate_config():
                return False
            
            # 创建HTTP会话
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 添加自定义头部
            if self.config.custom_headers:
                headers.update(self.config.custom_headers)
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            
            # 测试连接
            if await self._test_connection():
                self._initialized = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"OpenAI初始化失败: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """测试API连接"""
        try:
            test_data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            async with self.session.post("https://api.openai.com/v1/chat/completions", json=test_data) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本内容"""
        if not self._initialized:
            return AIResponse(
                success=False,
                error_message="模型未初始化"
            )
        
        try:
            messages = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            data = {
                "model": kwargs.get("model", self.model_name),
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "stream": False
            }
            
            async with self.session.post("https://api.openai.com/v1/chat/completions", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    choice = result.get("choices", [{}])[0]
                    content = choice.get("message", {}).get("content", "")
                    usage = result.get("usage", {})
                    
                    return AIResponse(
                        success=True,
                        content=content,
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0)
                        },
                        metadata={
                            "model": result.get("model", ""),
                            "finish_reason": choice.get("finish_reason", "")
                        }
                    )
                else:
                    error_data = await response.json()
                    error_message = error_data.get("error", {}).get("message", f"请求失败: {response.status}")
                    
                    return AIResponse(
                        success=False,
                        error_message=error_message
                    )
                    
        except Exception as e:
            return AIResponse(
                success=False,
                error_message=f"生成文本失败: {str(e)}"
            )
    
    async def analyze_content(self, content: str, analysis_type: str = "general") -> AIResponse:
        """分析内容"""
        prompts = {
            "general": f"请分析以下内容的主要特点和要点：\n\n{content}",
            "emotion": f"请分析以下内容的情感色彩和情绪表达：\n\n{content}",
            "scene": f"请分析以下视频场景的内容和特点：\n\n{content}",
            "dialogue": f"请分析以下对话的内容和人物关系：\n\n{content}",
            "summary": f"请总结以下内容的核心要点：\n\n{content}",
            "keywords": f"请提取以下内容的关键词：\n\n{content}"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        return await self.generate_text(prompt)
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self._initialized and self.session is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.name,
            "type": "cloud",
            "provider": "OpenAI",
            "model": self.model_name,
            "initialized": self._initialized,
            "config": {
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p
            }
        }
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not super().validate_config():
            return False
        
        if not self.config.api_key:
            return False
        
        return True
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self._initialized = False
    
    def __del__(self):
        """析构函数"""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except:
                pass