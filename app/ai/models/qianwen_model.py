#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from .base_model import BaseAIModel, AIModelConfig, AIResponse


class QianwenModel(BaseAIModel):
    """通义千问模型集成"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.session = None
        self.model_name = "qwen-max"  # 默认使用最新版本
    
    async def initialize(self) -> bool:
        """初始化通义千问连接"""
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
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # 测试连接
            if await self._test_connection():
                self._initialized = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"通义千问初始化失败: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """测试API连接"""
        try:
            # 发送一个简单的测试请求
            test_data = {
                "model": self.model_name,
                "input": {
                    "messages": [
                        {"role": "user", "content": "你好"}
                    ]
                },
                "parameters": {
                    "max_tokens": 10
                }
            }
            
            url = f"{self.config.api_url}/chat/completions"
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
                "model": kwargs.get("model", self.model_name),
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "top_p": kwargs.get("top_p", self.config.top_p),
                    "stream": False
                }
            }
            
            # 发送请求
            url = f"{self.config.api_url}/chat/completions"
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 解析响应
                    output = result.get('output', {})
                    choices = output.get('choices', [])
                    
                    if choices:
                        content = choices[0].get('message', {}).get('content', '')
                        
                        # 获取使用统计
                        usage = result.get('usage', {})
                        
                        return AIResponse(
                            success=True,
                            content=content,
                            usage={
                                "prompt_tokens": usage.get('input_tokens', 0),
                                "completion_tokens": usage.get('output_tokens', 0),
                                "total_tokens": usage.get('total_tokens', 0)
                            },
                            metadata={
                                "model": result.get('model', ''),
                                "request_id": result.get('request_id', ''),
                                "finish_reason": choices[0].get('finish_reason', '')
                            }
                        )
                    else:
                        return AIResponse(
                            success=False,
                            error_message="响应中没有生成内容"
                        )
                else:
                    error_data = await response.json()
                    error_message = error_data.get('message', f"请求失败: {response.status}")
                    
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
    
    async def generate_monologue(self, video_info: Dict[str, Any], character: str = "主角", emotion: str = "平静") -> AIResponse:
        """生成第一人称独白"""
        prompt = f"""
请为以下短剧视频生成{character}的第一人称独白：

视频信息：
- 时长：{video_info.get('duration', '未知')}
- 场景：{video_info.get('scenes', '未知')}
- 人物：{video_info.get('characters', '未知')}
- 剧情：{video_info.get('plot', '未知')}

要求：
1. 角色视角：{character}
2. 情感基调：{emotion}
3. 第一人称叙述
4. 符合角色性格
5. 贴合剧情发展

请生成独白文本：
"""
        return await self.generate_text(prompt)
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self._initialized and self.session is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.name,
            "type": "cloud",
            "provider": "阿里云通义千问",
            "api_url": self.config.api_url,
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
        
        # 通义千问特定验证
        if not self.config.api_key:
            return False
        
        if not self.config.api_url:
            return False
        
        return True
    
    def set_model(self, model_name: str):
        """设置模型名称"""
        available_models = ["qwen-turbo", "qwen-plus", "qwen-max"]
        if model_name in available_models:
            self.model_name = model_name
    
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
