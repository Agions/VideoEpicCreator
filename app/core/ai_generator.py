#!/usr/bin/env python3
"""
AI内容生成器
集成多种AI模型提供智能视频内容生成服务
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# AI服务提供商
try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

try:
    from qianwen import QianwenClient
except ImportError:
    QianwenClient = None

try:
    import ollama
except ImportError:
    ollama = None

from ..utils.config import Config
from ..utils.file_utils import FileUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIProvider(Enum):
    """AI服务提供商枚举"""
    OPENAI = "openai"
    QIANWEN = "qianwen"
    OLLAMA = "ollama"

class ContentType(Enum):
    """内容类型枚举"""
    SCRIPT = "script"           # 视频脚本
    NARRATION = "narration"     # 旁白/解说
    CAPTION = "caption"         # 字幕
    TITLE = "title"             # 标题
    DESCRIPTION = "description" # 描述
    HASHTAGS = "hashtags"       # 标签
    MUSIC_SUGGESTION = "music_suggestion"  # 音乐建议
    VISUAL_STYLE = "visual_style"          # 视觉风格建议

class GenerationStatus(Enum):
    """生成状态枚举"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class GenerationRequest:
    """生成请求"""
    request_id: str
    content_type: ContentType
    prompt: str
    provider: AIProvider
    model: str
    parameters: Dict[str, Any]
    context: Dict[str, Any] = None
    priority: int = 0
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.context is None:
            self.context = {}

@dataclass
class GenerationResult:
    """生成结果"""
    request_id: str
    status: GenerationStatus
    content: str = ""
    metadata: Dict[str, Any] = None
    error: str = ""
    started_at: float = None
    completed_at: float = None
    duration: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.started_at is None:
            self.started_at = time.time()
        if self.completed_at is None:
            self.completed_at = time.time()
        self.duration = self.completed_at - self.started_at

class AIContentGenerator:
    """AI内容生成器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.file_utils = FileUtils()
        
        # 初始化AI客户端
        self.clients = {}
        self._init_ai_clients()
        
        # 请求队列和处理
        self.request_queue = asyncio.Queue()
        self.active_requests = {}
        self.completed_requests = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 生成统计
        self.generation_stats = {
            'total_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'average_duration': 0,
            'provider_stats': {}
        }
        
        # 启动处理器
        self._running = False
        self.processor_task = None
    
    def _init_ai_clients(self):
        """初始化AI客户端"""
        try:
            # OpenAI客户端
            if openai and self.config.get('openai_api_key'):
                self.clients[AIProvider.OPENAI] = AsyncOpenAI(
                    api_key=self.config.get('openai_api_key')
                )
                logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            logger.warning(f"OpenAI客户端初始化失败: {e}")
        
        try:
            # 千问客户端
            if QianwenClient and self.config.get('qianwen_api_key'):
                self.clients[AIProvider.QIANWEN] = QianwenClient(
                    api_key=self.config.get('qianwen_api_key')
                )
                logger.info("千问客户端初始化成功")
        except Exception as e:
            logger.warning(f"千问客户端初始化失败: {e}")
        
        try:
            # Ollama客户端
            if ollama:
                self.clients[AIProvider.OLLAMA] = ollama
                logger.info("Ollama客户端初始化成功")
        except Exception as e:
            logger.warning(f"Ollama客户端初始化失败: {e}")
    
    async def start(self):
        """启动生成器"""
        if self._running:
            return
        
        self._running = True
        self.processor_task = asyncio.create_task(self._process_requests())
        logger.info("AI内容生成器已启动")
    
    async def stop(self):
        """停止生成器"""
        if not self._running:
            return
        
        self._running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        logger.info("AI内容生成器已停止")
    
    async def generate_content(self, request: GenerationRequest) -> str:
        """生成内容"""
        try:
            # 验证请求
            if not self._validate_request(request):
                raise ValueError("无效的生成请求")
            
            # 更新统计
            self.generation_stats['total_requests'] += 1
            
            # 将请求加入队列
            await self.request_queue.put(request)
            self.active_requests[request.request_id] = request
            
            logger.info(f"内容生成请求已加入队列: {request.request_id}")
            return request.request_id
            
        except Exception as e:
            logger.error(f"生成内容时出错: {e}")
            raise
    
    async def get_generation_status(self, request_id: str) -> Optional[GenerationResult]:
        """获取生成状态"""
        # 检查活跃请求
        if request_id in self.active_requests:
            request = self.active_requests[request_id]
            return GenerationResult(
                request_id=request_id,
                status=GenerationStatus.GENERATING
            )
        
        # 检查已完成请求
        if request_id in self.completed_requests:
            return self.completed_requests[request_id]
        
        return None
    
    async def cancel_generation(self, request_id: str) -> bool:
        """取消生成请求"""
        if request_id in self.active_requests:
            # 从活跃请求中移除
            request = self.active_requests.pop(request_id)
            
            # 创建取消结果
            result = GenerationResult(
                request_id=request_id,
                status=GenerationStatus.CANCELLED
            )
            self.completed_requests[request_id] = result
            
            logger.info(f"生成请求已取消: {request_id}")
            return True
        
        return False
    
    async def _process_requests(self):
        """处理生成请求"""
        while self._running:
            try:
                # 从队列获取请求
                request = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                
                # 处理请求
                asyncio.create_task(self._handle_generation_request(request))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理请求时出错: {e}")
    
    async def _handle_generation_request(self, request: GenerationRequest):
        """处理单个生成请求"""
        try:
            # 创建结果对象
            result = GenerationResult(
                request_id=request.request_id,
                status=GenerationStatus.GENERATING,
                started_at=time.time()
            )
            
            # 根据提供商调用相应的生成方法
            if request.provider == AIProvider.OPENAI:
                content = await self._generate_with_openai(request)
            elif request.provider == AIProvider.QIANWEN:
                content = await self._generate_with_qianwen(request)
            elif request.provider == AIProvider.OLLAMA:
                content = await self._generate_with_ollama(request)
            else:
                raise ValueError(f"不支持的AI提供商: {request.provider}")
            
            # 更新结果
            result.status = GenerationStatus.COMPLETED
            result.content = content
            result.completed_at = time.time()
            result.duration = result.completed_at - result.started_at
            
            # 更新统计
            self.generation_stats['completed_requests'] += 1
            self._update_provider_stats(request.provider, True, result.duration)
            
            logger.info(f"内容生成完成: {request.request_id}")
            
        except Exception as e:
            # 更新结果为失败
            result.status = GenerationStatus.FAILED
            result.error = str(e)
            result.completed_at = time.time()
            result.duration = result.completed_at - result.started_at
            
            # 更新统计
            self.generation_stats['failed_requests'] += 1
            self._update_provider_stats(request.provider, False, result.duration)
            
            logger.error(f"内容生成失败: {request.request_id}, 错误: {e}")
        
        finally:
            # 从活跃请求中移除
            self.active_requests.pop(request.request_id, None)
            
            # 添加到已完成请求
            self.completed_requests[request.request_id] = result
            
            # 清理旧请求（保留最近1000个）
            if len(self.completed_requests) > 1000:
                oldest_keys = sorted(self.completed_requests.keys())[:100]
                for key in oldest_keys:
                    self.completed_requests.pop(key, None)
    
    async def _generate_with_openai(self, request: GenerationRequest) -> str:
        """使用OpenAI生成内容"""
        if AIProvider.OPENAI not in self.clients:
            raise ValueError("OpenAI客户端未初始化")
        
        client = self.clients[AIProvider.OPENAI]
        
        # 构建提示词
        prompt = self._build_prompt(request)
        
        # 调用OpenAI API
        response = await client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt(request.content_type)},
                {"role": "user", "content": prompt}
            ],
            temperature=request.parameters.get('temperature', 0.7),
            max_tokens=request.parameters.get('max_tokens', 1000),
            top_p=request.parameters.get('top_p', 1.0),
            frequency_penalty=request.parameters.get('frequency_penalty', 0),
            presence_penalty=request.parameters.get('presence_penalty', 0)
        )
        
        return response.choices[0].message.content.strip()
    
    async def _generate_with_qianwen(self, request: GenerationRequest) -> str:
        """使用千问生成内容"""
        if AIProvider.QIANWEN not in self.clients:
            raise ValueError("千问客户端未初始化")
        
        client = self.clients[AIProvider.QIANWEN]
        
        # 构建提示词
        prompt = self._build_prompt(request)
        
        # 调用千问API
        response = await client.generate(
            model=request.model,
            prompt=prompt,
            temperature=request.parameters.get('temperature', 0.7),
            max_tokens=request.parameters.get('max_tokens', 1000)
        )
        
        return response['content'].strip()
    
    async def _generate_with_ollama(self, request: GenerationRequest) -> str:
        """使用Ollama生成内容"""
        if AIProvider.OLLAMA not in self.clients:
            raise ValueError("Ollama客户端未初始化")
        
        # 构建提示词
        prompt = self._build_prompt(request)
        
        # 调用Ollama API
        response = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            lambda: self.clients[AIProvider.OLLAMA].generate(
                model=request.model,
                prompt=prompt,
                options={
                    "temperature": request.parameters.get('temperature', 0.7),
                    "top_p": request.parameters.get('top_p', 1.0),
                    "max_tokens": request.parameters.get('max_tokens', 1000)
                }
            )
        )
        
        return response['response'].strip()
    
    def _build_prompt(self, request: GenerationRequest) -> str:
        """构建提示词"""
        base_prompt = request.prompt
        
        # 添加上下文信息
        if request.context:
            context_info = []
            if 'video_topic' in request.context:
                context_info.append(f"视频主题: {request.context['video_topic']}")
            if 'target_audience' in request.context:
                context_info.append(f"目标受众: {request.context['target_audience']}")
            if 'video_style' in request.context:
                context_info.append(f"视频风格: {request.context['video_style']}")
            if 'duration' in request.context:
                context_info.append(f"视频时长: {request.context['duration']}")
            
            if context_info:
                base_prompt += f"\n\n背景信息:\n" + "\n".join(context_info)
        
        # 根据内容类型添加特定要求
        if request.content_type == ContentType.SCRIPT:
            base_prompt += "\n\n请生成一个完整的视频脚本，包括开场、主体和结尾。"
        elif request.content_type == ContentType.NARRATION:
            base_prompt += "\n\n请生成适合旁白的文本，语言要自然流畅。"
        elif request.content_type == ContentType.CAPTION:
            base_prompt += "\n\n请生成简短的字幕文本，每行不超过20个字符。"
        elif request.content_type == ContentType.TITLE:
            base_prompt += "\n\n请生成吸引人的标题，长度不超过30个字符。"
        
        return base_prompt
    
    def _get_system_prompt(self, content_type: ContentType) -> str:
        """获取系统提示词"""
        system_prompts = {
            ContentType.SCRIPT: "你是一个专业的视频脚本创作专家，擅长创作引人入胜的视频内容。",
            ContentType.NARRATION: "你是一个专业的旁白配音专家，擅长创作自然流畅的解说文本。",
            ContentType.CAPTION: "你是一个专业的字幕制作专家，擅长创作简洁明了的字幕文本。",
            ContentType.TITLE: "你是一个专业的标题创作专家，擅长创作吸引人的视频标题。",
            ContentType.DESCRIPTION: "你是一个专业的视频描述专家，擅长创作详细的视频描述。",
            ContentType.HASHTAGS: "你是一个专业的标签专家，擅长创作相关的社交媒体标签。",
            ContentType.MUSIC_SUGGESTION: "你是一个专业的音乐推荐专家，擅长推荐适合视频的背景音乐。",
            ContentType.VISUAL_STYLE: "你是一个专业的视觉风格专家，擅长建议视频的视觉风格。"
        }
        
        return system_prompts.get(content_type, "你是一个专业的内容创作专家。")
    
    def _validate_request(self, request: GenerationRequest) -> bool:
        """验证请求"""
        if not request.request_id:
            return False
        
        if not request.prompt:
            return False
        
        if request.provider not in self.clients:
            return False
        
        if not request.model:
            return False
        
        return True
    
    def _update_provider_stats(self, provider: AIProvider, success: bool, duration: float):
        """更新提供商统计"""
        if provider.value not in self.generation_stats['provider_stats']:
            self.generation_stats['provider_stats'][provider.value] = {
                'total_requests': 0,
                'completed_requests': 0,
                'failed_requests': 0,
                'average_duration': 0
            }
        
        stats = self.generation_stats['provider_stats'][provider.value]
        stats['total_requests'] += 1
        
        if success:
            stats['completed_requests'] += 1
        else:
            stats['failed_requests'] += 1
        
        # 更新平均时长
        if stats['completed_requests'] > 0:
            total_duration = stats['average_duration'] * (stats['completed_requests'] - 1) + duration
            stats['average_duration'] = total_duration / stats['completed_requests']
    
    def get_available_providers(self) -> List[AIProvider]:
        """获取可用的AI提供商"""
        return list(self.clients.keys())
    
    def get_provider_models(self, provider: AIProvider) -> List[str]:
        """获取提供商的可用模型"""
        models = {
            AIProvider.OPENAI: [
                "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
            ],
            AIProvider.QIANWEN: [
                "qwen-turbo", "qwen-plus", "qwen-max", "qwen-7b-chat"
            ],
            AIProvider.OLLAMA: [
                "llama2", "mistral", "codellama", "phi3"
            ]
        }
        
        return models.get(provider, [])
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """获取生成统计"""
        return self.generation_stats.copy()
    
    def get_default_parameters(self, content_type: ContentType) -> Dict[str, Any]:
        """获取默认参数"""
        default_params = {
            'temperature': 0.7,
            'max_tokens': 1000,
            'top_p': 1.0,
            'frequency_penalty': 0,
            'presence_penalty': 0
        }
        
        # 根据内容类型调整参数
        if content_type == ContentType.SCRIPT:
            default_params['max_tokens'] = 2000
        elif content_type == ContentType.CAPTION:
            default_params['max_tokens'] = 500
        elif content_type == ContentType.TITLE:
            default_params['max_tokens'] = 100
        
        return default_params

def main():
    """主函数"""
    # 测试AI内容生成器
    from app.utils.config import Config
    
    # 创建配置
    config = Config()
    
    # 创建生成器
    generator = AIContentGenerator(config)
    
    # 启动生成器
    asyncio.run(generator.start())
    
    try:
        # 测试生成请求
        request = GenerationRequest(
            request_id="test_001",
            content_type=ContentType.SCRIPT,
            prompt="创建一个关于AI技术发展的短视频脚本",
            provider=AIProvider.OPENAI,
            model="gpt-3.5-turbo",
            parameters=generator.get_default_parameters(ContentType.SCRIPT),
            context={
                'video_topic': 'AI技术发展',
                'target_audience': '科技爱好者',
                'duration': '60秒'
            }
        )
        
        print(f"提交生成请求: {request.request_id}")
        
        # 提交请求
        request_id = asyncio.run(generator.generate_content(request))
        print(f"请求已提交，ID: {request_id}")
        
        # 等待生成完成
        import time
        time.sleep(5)
        
        # 获取结果
        result = asyncio.run(generator.get_generation_status(request_id))
        if result:
            print(f"生成状态: {result.status}")
            print(f"生成内容: {result.content[:200]}...")
            print(f"生成时长: {result.duration:.2f}秒")
        else:
            print("未找到生成结果")
        
        # 显示统计信息
        stats = generator.get_generation_stats()
        print(f"生成统计: {stats}")
        
    finally:
        # 停止生成器
        asyncio.run(generator.stop())

if __name__ == "__main__":
    main()