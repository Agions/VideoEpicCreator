"""
AI model integration system for VideoEpicCreator

This module provides unified interface for multiple AI providers including
OpenAI, Qianwen (Alibaba), and Ollama for content generation.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import time
import aiohttp
import openai
from openai import AsyncOpenAI
import dashscope
from ollama import AsyncClient
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..config.settings import Settings


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    QIANWEN = "qianwen"
    OLLAMA = "ollama"


class ContentType(Enum):
    """Types of content that can be generated"""
    COMMENTARY = "commentary"  # 视频解说
    NARRATIVE = "narrative"    # 叙事内容
    HIGHLIGHT = "highlight"    # 精彩片段描述
    MONOLOGUE = "monologue"    # 独白内容
    SUBTITLE = "subtitle"      # 字幕文本
    ANALYSIS = "analysis"      # 内容分析


@dataclass
class AIRequest:
    """AI request configuration"""
    prompt: str
    content_type: ContentType
    provider: AIProvider
    model: str
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


@dataclass
class AIResponse:
    """AI response data"""
    content: str
    provider: AIProvider
    model: str
    tokens_used: int
    response_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class AIProviderInterface(ABC):
    """Abstract interface for AI providers"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def generate_content(self, request: AIRequest) -> AIResponse:
        """Generate content using the AI provider"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Generate content as a stream"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate the API key"""
        pass


class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    
    async def generate_content(self, request: AIRequest) -> AIResponse:
        """Generate content using OpenAI"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        start_time = time.time()
        
        try:
            system_prompt = self._get_system_prompt(request.content_type)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                timeout=request.timeout
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            response_time = time.time() - start_time
            
            return AIResponse(
                content=content,
                provider=AIProvider.OPENAI,
                model=request.model,
                tokens_used=tokens_used,
                response_time=response_time,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": response.usage.dict() if response.usage else None
                }
            )
        
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=request.model,
                tokens_used=0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def generate_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Generate streaming content using OpenAI"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        system_prompt = self._get_system_prompt(request.content_type)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt}
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            yield f"[ERROR: {str(e)}]"
    
    def get_available_models(self) -> List[str]:
        """Get available OpenAI models"""
        return self.models
    
    def validate_api_key(self) -> bool:
        """Validate OpenAI API key"""
        if not self.api_key:
            return False
        
        try:
            # Simple validation check
            return len(self.api_key) > 20 and self.api_key.startswith("sk-")
        except Exception:
            return False
    
    def _get_system_prompt(self, content_type: ContentType) -> str:
        """Get system prompt based on content type"""
        prompts = {
            ContentType.COMMENTARY: """你是一个专业的视频解说专家，擅长为短视频和短剧创作引人入胜的解说词。
请根据提供的视频内容信息，生成生动有趣、富有感染力的解说词。
要求：
1. 语言简洁有力，富有节奏感
2. 突出视频的亮点和情感
3. 适合短视频平台的风格
4. 控制在适当的长度范围内
5. 能够吸引观众的注意力""",
            
            ContentType.NARRATIVE: """你是一个优秀的叙事创作者，擅长为视频内容创作连贯的叙事文本。
请根据提供的视频内容，创作流畅、有逻辑性的叙事文本。
要求：
1. 故事线清晰，逻辑连贯
2. 情感表达丰富
3. 语言优美，具有文学性
4. 符合视频的节奏和风格
5. 能够引起观众共鸣""",
            
            ContentType.HIGHLIGHT: """你是一个专业的视频内容分析师，擅长识别和描述视频中的精彩片段。
请分析视频内容，识别最精彩的部分并生成描述文本。
要求：
1. 准确识别精彩时刻
2. 描述生动具体
3. 突出亮点和价值
4. 适合用于视频剪辑和推广
5. 语言简洁有力""",
            
            ContentType.MONOLOGUE: """你是一个擅长创作独白文本的专家，能够为角色创作个性化的内心独白。
请根据视频内容和角色特点，创作富有感染力的独白文本。
要求：
1. 符合角色性格和背景
2. 情感真实自然
3. 语言个性化
4. 具有戏剧性效果
5. 能够展现角色内心世界""",
            
            ContentType.SUBTITLE: """你是一个专业的字幕文本创作者，擅长为视频创作准确、易读的字幕。
请根据视频内容，生成适合显示的字幕文本。
要求：
1. 文字简洁明了
2. 阅读节奏适宜
3. 准确传达信息
4. 考虑显示时间和空间
5. 便于观众理解""",
            
            ContentType.ANALYSIS: """你是一个专业的视频内容分析师，能够深入分析视频的各种要素。
请对视频内容进行全面分析，提供专业的分析报告。
要求：
1. 分析全面客观
2. 观点专业深刻
3. 结构清晰有条理
4. 提供有价值的见解
5. 建议实用可行"""
        }
        
        return prompts.get(content_type, "你是一个专业的视频内容创作者。")


class QianwenProvider(AIProviderInterface):
    """Alibaba Qianwen API provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        dashscope.api_key = api_key
        self.models = ["qwen-turbo", "qwen-plus", "qwen-max"]
    
    async def generate_content(self, request: AIRequest) -> AIResponse:
        """Generate content using Qianwen"""
        if not self.api_key:
            raise ValueError("Qianwen API key not configured")
        
        start_time = time.time()
        
        try:
            system_prompt = self._get_system_prompt(request.content_type)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            
            response = await asyncio.to_thread(
                dashscope.Generation.call,
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False
            )
            
            if response.status_code == 200:
                content = response.output.text
                tokens_used = response.usage.total_tokens
                response_time = time.time() - start_time
                
                return AIResponse(
                    content=content,
                    provider=AIProvider.QIANWEN,
                    model=request.model,
                    tokens_used=tokens_used,
                    response_time=response_time,
                    metadata={
                        "request_id": response.request_id,
                        "usage": response.usage.dict()
                    }
                )
            else:
                raise Exception(f"Qianwen API error: {response.message}")
        
        except Exception as e:
            self.logger.error(f"Qianwen API error: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.QIANWEN,
                model=request.model,
                tokens_used=0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def generate_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Generate streaming content using Qianwen"""
        if not self.api_key:
            raise ValueError("Qianwen API key not configured")
        
        system_prompt = self._get_system_prompt(request.content_type)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt}
        ]
        
        try:
            response = await asyncio.to_thread(
                dashscope.Generation.call,
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True
            )
            
            if response.status_code == 200:
                for chunk in response:
                    if chunk.output.text:
                        yield chunk.output.text
            else:
                yield f"[ERROR: {response.message}]"
        
        except Exception as e:
            self.logger.error(f"Qianwen streaming error: {e}")
            yield f"[ERROR: {str(e)}]"
    
    def get_available_models(self) -> List[str]:
        """Get available Qianwen models"""
        return self.models
    
    def validate_api_key(self) -> bool:
        """Validate Qianwen API key"""
        if not self.api_key:
            return False
        
        try:
            return len(self.api_key) > 10
        except Exception:
            return False
    
    def _get_system_prompt(self, content_type: ContentType) -> str:
        """Get system prompt based on content type"""
        # Similar to OpenAI but optimized for Chinese models
        prompts = {
            ContentType.COMMENTARY: """你是一个专业的视频解说专家，特别擅长为短剧和短视频创作精彩的解说词。
请根据视频内容，创作引人入胜、富有感染力的解说词。
要求：
1. 语言生动活泼，富有节奏感
2. 突出视频的亮点和情感
3. 适合中文短视频平台的风格
4. 能够有效吸引观众注意力
5. 内容与视频画面完美配合""",
            
            ContentType.NARRATIVE: """你是一个优秀的叙事创作者，擅长为视频内容创作流畅的叙事文本。
请根据视频内容，创作连贯、有逻辑性的叙事文本。
要求：
1. 故事线清晰，逻辑连贯
2. 情感表达丰富真实
3. 语言优美，具有文学性
4. 符合视频的节奏和风格
5. 能够引起观众强烈共鸣""",
            
            ContentType.HIGHLIGHT: """你是一个专业的视频内容分析师，擅长识别和描述视频中的精彩片段。
请分析视频内容，识别最精彩的部分并生成描述文本。
要求：
1. 准确识别精彩时刻
2. 描述生动具体
3. 突出亮点和价值
4. 适合用于视频剪辑和推广
5. 语言简洁有力""",
            
            ContentType.MONOLOGUE: """你是一个擅长创作独白文本的专家，能够为角色创作个性化的内心独白。
请根据视频内容和角色特点，创作富有感染力的独白文本。
要求：
1. 符合角色性格和背景
2. 情感真实自然
3. 语言个性化
4. 具有戏剧性效果
5. 能够展现角色内心世界""",
            
            ContentType.SUBTITLE: """你是一个专业的字幕文本创作者，擅长为视频创作准确、易读的字幕。
请根据视频内容，生成适合显示的字幕文本。
要求：
1. 文字简洁明了
2. 阅读节奏适宜
3. 准确传达信息
4. 考虑显示时间和空间
5. 便于观众理解""",
            
            ContentType.ANALYSIS: """你是一个专业的视频内容分析师，能够深入分析视频的各种要素。
请对视频内容进行全面分析，提供专业的分析报告。
要求：
1. 分析全面客观
2. 观点专业深刻
3. 结构清晰有条理
4. 提供有价值的见解
5. 建议实用可行"""
        }
        
        return prompts.get(content_type, "你是一个专业的视频内容创作者。")


class OllamaProvider(AIProviderInterface):
    """Ollama local AI provider"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__(base_url=base_url)
        self.client = AsyncClient(host=base_url)
        self.models = ["llama2", "mistral", "codellama", "qwen:7b"]
    
    async def generate_content(self, request: AIRequest) -> AIResponse:
        """Generate content using Ollama"""
        start_time = time.time()
        
        try:
            system_prompt = self._get_system_prompt(request.content_type)
            full_prompt = f"{system_prompt}\n\n用户请求：{request.prompt}"
            
            response = await self.client.generate(
                model=request.model,
                prompt=full_prompt,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                }
            )
            
            content = response['response']
            response_time = time.time() - start_time
            
            return AIResponse(
                content=content,
                provider=AIProvider.OLLAMA,
                model=request.model,
                tokens_used=len(content.split()),  # Approximate
                response_time=response_time,
                metadata={
                    "model_info": response.get('model', ''),
                    "total_duration": response.get('total_duration', 0),
                    "load_duration": response.get('load_duration', 0)
                }
            )
        
        except Exception as e:
            self.logger.error(f"Ollama API error: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.OLLAMA,
                model=request.model,
                tokens_used=0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def generate_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Generate streaming content using Ollama"""
        system_prompt = self._get_system_prompt(request.content_type)
        full_prompt = f"{system_prompt}\n\n用户请求：{request.prompt}"
        
        try:
            async for response in self.client.generate(
                model=request.model,
                prompt=full_prompt,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                },
                stream=True
            ):
                if 'response' in response:
                    yield response['response']
        
        except Exception as e:
            self.logger.error(f"Ollama streaming error: {e}")
            yield f"[ERROR: {str(e)}]"
    
    def get_available_models(self) -> List[str]:
        """Get available Ollama models"""
        try:
            # Try to get actual models from Ollama
            import requests
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except Exception:
            pass
        
        # Return default models
        return self.models
    
    def validate_api_key(self) -> bool:
        """Validate Ollama connection"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_system_prompt(self, content_type: ContentType) -> str:
        """Get system prompt based on content type"""
        # Simplified prompts for local models
        prompts = {
            ContentType.COMMENTARY: "你是一个专业的视频解说专家，请为视频创作精彩的解说词。",
            ContentType.NARRATIVE: "你是一个优秀的叙事创作者，请为视频创作连贯的叙事文本。",
            ContentType.HIGHLIGHT: "你是一个专业的视频内容分析师，请分析视频内容并描述精彩片段。",
            ContentType.MONOLOGUE: "你是一个擅长创作独白文本的专家，请为角色创作内心独白。",
            ContentType.SUBTITLE: "你是一个专业的字幕文本创作者，请为视频创作准确的字幕。",
            ContentType.ANALYSIS: "你是一个专业的视频内容分析师，请分析视频内容并提供见解。"
        }
        
        return prompts.get(content_type, "你是一个专业的视频内容创作者。")


class AIManager(BaseComponent[Dict[str, Any]]):
    """AI service manager for coordinating multiple AI providers"""
    
    def __init__(self, settings: Settings, config: Optional[ComponentConfig] = None):
        super().__init__("ai_manager", config)
        self.settings = settings
        self.providers: Dict[AIProvider, AIProviderInterface] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize AI providers based on settings"""
        ai_settings = self.settings.get_ai_settings()
        
        # Initialize OpenAI provider
        if ai_settings.openai_api_key:
            self.providers[AIProvider.OPENAI] = OpenAIProvider(ai_settings.openai_api_key)
        
        # Initialize Qianwen provider
        if ai_settings.qianwen_api_key:
            self.providers[AIProvider.QIANWEN] = QianwenProvider(ai_settings.qianwen_api_key)
        
        # Initialize Ollama provider
        self.providers[AIProvider.OLLAMA] = OllamaProvider(ai_settings.ollama_base_url)
    
    async def initialize(self) -> bool:
        """Initialize AI manager"""
        try:
            self.logger.info("Initializing AI Manager")
            
            # Validate provider connections
            for provider, instance in self.providers.items():
                if instance.validate_api_key():
                    self.logger.info(f"{provider.value} provider is available")
                else:
                    self.logger.warning(f"{provider.value} provider is not available")
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialization")
            return False
    
    async def start(self) -> bool:
        """Start AI manager"""
        self.set_state(ComponentState.RUNNING)
        return True
    
    async def stop(self) -> bool:
        """Stop AI manager"""
        self.set_state(ComponentState.STOPPED)
        return True
    
    async def cleanup(self) -> bool:
        """Clean up resources"""
        self.providers.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI manager status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "providers": {
                provider.value: {
                    "available": instance.validate_api_key(),
                    "models": instance.get_available_models()
                }
                for provider, instance in self.providers.items()
            },
            "metrics": self.metrics.__dict__
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate_content(
        self,
        prompt: str,
        content_type: ContentType,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate content using specified or default provider"""
        if not self.is_ready():
            raise RuntimeError("AI Manager is not ready")
        
        # Select provider
        if provider is None:
            provider = self._select_best_provider()
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider.value} not available")
        
        # Select model
        if model is None:
            available_models = self.providers[provider].get_available_models()
            model = available_models[0] if available_models else "default"
        
        # Create request
        request = AIRequest(
            prompt=prompt,
            content_type=content_type,
            provider=provider,
            model=model,
            **kwargs
        )
        
        # Generate content
        start_time = time.time()
        response = await self.providers[provider].generate_content(request)
        
        # Update metrics
        self.update_metrics(time.time() - start_time)
        
        if response.error:
            self.handle_error(Exception(response.error), "content_generation")
        
        return response
    
    async def generate_stream(
        self,
        prompt: str,
        content_type: ContentType,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming content"""
        if not self.is_ready():
            raise RuntimeError("AI Manager is not ready")
        
        # Select provider
        if provider is None:
            provider = self._select_best_provider()
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider.value} not available")
        
        # Select model
        if model is None:
            available_models = self.providers[provider].get_available_models()
            model = available_models[0] if available_models else "default"
        
        # Create request
        request = AIRequest(
            prompt=prompt,
            content_type=content_type,
            provider=provider,
            model=model,
            stream=True,
            **kwargs
        )
        
        # Generate streaming content
        async for chunk in self.providers[provider].generate_stream(request):
            yield chunk
    
    def _select_best_provider(self) -> AIProvider:
        """Select the best available provider"""
        ai_settings = self.settings.get_ai_settings()
        
        # Try preferred provider first
        preferred = ai_settings.default_model.lower()
        try:
            preferred_provider = AIProvider(preferred)
            if preferred_provider in self.providers and self.providers[preferred_provider].validate_api_key():
                return preferred_provider
        except ValueError:
            pass
        
        # Fallback to available providers
        for provider in [AIProvider.OPENAI, AIProvider.QIANWEN, AIProvider.OLLAMA]:
            if provider in self.providers and self.providers[provider].validate_api_key():
                return provider
        
        raise RuntimeError("No AI providers available")
    
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        return [
            provider for provider, instance in self.providers.items()
            if instance.validate_api_key()
        ]
    
    def get_provider_models(self, provider: AIProvider) -> List[str]:
        """Get available models for a provider"""
        if provider in self.providers:
            return self.providers[provider].get_available_models()
        return []
    
    def test_provider(self, provider: AIProvider) -> bool:
        """Test if a provider is working"""
        if provider not in self.providers:
            return False
        
        return self.providers[provider].validate_api_key()
    
    async def generate_commentary(
        self,
        video_description: str,
        style: str = "engaging",
        length: str = "medium",
        **kwargs
    ) -> AIResponse:
        """Generate video commentary"""
        prompt = f"""
        视频描述：{video_description}
        
        请为这个视频创作解说词，要求：
        - 风格：{style}
        - 长度：{length}
        - 语言：中文
        - 要生动有趣，富有感染力
        - 突出视频的亮点和情感
        """
        
        return await self.generate_content(
            prompt=prompt,
            content_type=ContentType.COMMENTARY,
            **kwargs
        )
    
    async def generate_narrative(
        self,
        video_content: str,
        tone: str = "professional",
        **kwargs
    ) -> AIResponse:
        """Generate narrative content"""
        prompt = f"""
        视频内容：{video_content}
        
        请为这个视频创作叙事文本，要求：
        - 语气：{tone}
        - 语言：中文
        - 故事线清晰，逻辑连贯
        - 情感表达丰富
        - 语言优美，具有文学性
        """
        
        return await self.generate_content(
            prompt=prompt,
            content_type=ContentType.NARRATIVE,
            **kwargs
        )
    
    async def analyze_video_content(
        self,
        video_description: str,
        **kwargs
    ) -> AIResponse:
        """Analyze video content"""
        prompt = f"""
        请对以下视频内容进行全面分析：
        
        视频描述：{video_description}
        
        分析要求：
        1. 识别视频类型和主题
        2. 分析情感基调和氛围
        3. 识别关键场景和转折点
        4. 评估内容质量和吸引力
        5. 提供改进建议
        """
        
        return await self.generate_content(
            prompt=prompt,
            content_type=ContentType.ANALYSIS,
            **kwargs
        )