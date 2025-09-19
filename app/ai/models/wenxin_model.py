#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from .base_model import BaseAIModel, AIModelConfig, AIResponse


class WenxinModel(BaseAIModel):
    """文心一言模型集成"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.session = None
        self.access_token = None
        self.model_name = "ernie-bot-4"  # 默认使用最新版本
    
    async def initialize(self) -> bool:
        """初始化文心一言连接"""
        try:
            if not self.validate_config():
                return False
            
            # 获取访问令牌
            if not await self._get_access_token():
                return False
            
            # 创建HTTP会话
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # 测试连接
            if await self._test_connection():
                self._initialized = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"文心一言初始化失败: {e}")
            return False
    
    async def _get_access_token(self) -> bool:
        """获取访问令牌"""
        try:
            # 文心一言使用API Key和Secret Key获取access_token
            # 这里假设api_key格式为 "api_key:secret_key"
            if ':' in self.config.api_key:
                api_key, secret_key = self.config.api_key.split(':', 1)
            else:
                # 如果没有分隔符，假设整个字符串是API Key
                api_key = self.config.api_key
                secret_key = ""
            
            # 获取access_token的URL
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            
            params = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.access_token = data.get("access_token")
                        return bool(self.access_token)
                    else:
                        print(f"获取access_token失败: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"获取access_token异常: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """测试API连接"""
        try:
            # 发送一个简单的测试请求
            test_data = {
                "messages": [
                    {"role": "user", "content": "你好"}
                ],
                "max_output_tokens": 10
            }
            
            url = f"{self.config.api_url}/chat/{self.model_name}?access_token={self.access_token}"
            async with self.session.post(url, json=test_data) as response:
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
            # 准备消息格式
            messages = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            # 准备请求数据
            data = {
                "messages": messages,
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "stream": False
            }
            
            # 发送请求
            model = kwargs.get("model", self.model_name)
            url = f"{self.config.api_url}/chat/{model}?access_token={self.access_token}"
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 检查是否有错误
                    if "error_code" in result:
                        return AIResponse(
                            success=False,
                            error_message=result.get("error_msg", "未知错误")
                        )
                    
                    # 解析响应
                    content = result.get('result', '')
                    usage = result.get('usage', {})
                    
                    return AIResponse(
                        success=True,
                        content=content,
                        usage={
                            "prompt_tokens": usage.get('prompt_tokens', 0),
                            "completion_tokens": usage.get('completion_tokens', 0),
                            "total_tokens": usage.get('total_tokens', 0)
                        },
                        metadata={
                            "id": result.get('id', ''),
                            "object": result.get('object', ''),
                            "created": result.get('created', 0),
                            "is_truncated": result.get('is_truncated', False),
                            "need_clear_history": result.get('need_clear_history', False)
                        }
                    )
                else:
                    error_data = await response.json()
                    error_message = error_data.get('error_msg', f"请求失败: {response.status}")
                    
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
        # 根据分析类型构建提示词
        prompts = {
            "general": f"请分析以下内容的主要特点和要点：\n\n{content}",
            "emotion": f"请分析以下内容的情感色彩和情绪表达：\n\n{content}",
            "scene": f"请分析以下视频场景的内容和特点，包括人物、环境、动作等：\n\n{content}",
            "dialogue": f"请分析以下对话的内容和人物关系：\n\n{content}",
            "summary": f"请总结以下内容的核心要点：\n\n{content}",
            "keywords": f"请提取以下内容的关键词：\n\n{content}"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        return await self.generate_text(prompt)
    
    async def generate_commentary(self, video_info: Dict[str, Any], style: str = "幽默风趣") -> AIResponse:
        """生成视频解说"""
        prompt = f"""
请为以下短剧视频生成{style}的解说内容：

视频信息：
- 时长：{video_info.get('duration', '未知')}
- 场景：{video_info.get('scenes', '未知')}
- 人物：{video_info.get('characters', '未知')}
- 剧情：{video_info.get('plot', '未知')}

要求：
1. 解说风格：{style}
2. 语言生动有趣
3. 突出剧情亮点
4. 适合短视频观众
5. 控制在适当长度

请生成解说文本：
"""
        return await self.generate_text(prompt)
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self._initialized and self.session is not None and self.access_token is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.name,
            "type": "cloud",
            "provider": "百度文心一言",
            "api_url": self.config.api_url,
            "model": self.model_name,
            "initialized": self._initialized,
            "has_token": bool(self.access_token),
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
        
        # 文心一言特定验证
        if not self.config.api_key:
            return False
        
        if not self.config.api_url:
            return False
        
        return True
    
    def set_model(self, model_name: str):
        """设置模型名称"""
        available_models = ["ernie-bot", "ernie-bot-turbo", "ernie-bot-4"]
        if model_name in available_models:
            self.model_name = model_name
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self.access_token = None
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
