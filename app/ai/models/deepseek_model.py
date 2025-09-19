#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from typing import Dict, List, Optional, Any
import aiohttp
from .base_model import BaseAIModel, AIModelConfig, AIResponse


class DeepSeekModel(BaseAIModel):
    """DeepSeek模型实现"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_url = config.api_url or "https://api.deepseek.com/v1"
        self.model = config.model or "deepseek-chat"
        
    async def initialize(self) -> bool:
        """初始化模型"""
        try:
            # 测试API连接
            test_response = await self._make_request("chat/completions", {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            })
            
            self._initialized = test_response.get("choices") is not None
            return self._initialized
            
        except Exception as e:
            print(f"DeepSeek模型初始化失败: {e}")
            return False
    
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "stream": False
            }
            
            response = await self._make_request("chat/completions", request_data)
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model,
                    usage=response.get("usage", {})
                )
            else:
                return AIResponse(
                    success=False,
                    error_message="DeepSeek返回格式错误"
                )
                
        except Exception as e:
            return AIResponse(
                success=False,
                error_message=f"DeepSeek文本生成失败: {str(e)}"
            )
    
    async def analyze_content(self, content: str, analysis_type: str = "general") -> AIResponse:
        """分析内容"""
        try:
            if analysis_type == "video_script":
                prompt = f"请分析以下视频脚本的内容结构、情感色彩和关键信息：\n\n{content}"
            elif analysis_type == "subtitle":
                prompt = f"请分析以下字幕内容，提取关键信息和情感表达：\n\n{content}"
            else:
                prompt = f"请分析以下内容：\n\n{content}"
            
            return await self.generate_text(prompt)
            
        except Exception as e:
            return AIResponse(
                success=False,
                error_message=f"DeepSeek内容分析失败: {str(e)}"
            )
    
    async def generate_subtitles(self, video_content: str, **kwargs) -> AIResponse:
        """生成字幕"""
        try:
            prompt = f"""
请为以下视频内容生成合适的字幕：

视频内容描述：{video_content}

要求：
1. 字幕要简洁明了，易于阅读
2. 时间节点要合理分布
3. 语言要生动有趣
4. 符合短视频特点

请以JSON格式返回，包含时间戳和字幕内容。
"""
            
            return await self.generate_text(prompt, **kwargs)
            
        except Exception as e:
            return AIResponse(
                success=False,
                error_message=f"DeepSeek字幕生成失败: {str(e)}"
            )
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.api_url.rstrip('/')}/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                json=data, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return bool(self.api_key and self.config.enabled)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "deepseek",
            "model": self.model,
            "api_url": self.api_url,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "initialized": self._initialized
        }
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return ["deepseek-chat", "deepseek-coder"]
