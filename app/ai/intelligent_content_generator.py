#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能内容生成器 - 集成多种AI生成功能
包括解说生成、混剪风格生成、字幕生成、角色配音等功能
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from .ai_manager import AIManager
from .generators.text_to_speech import TextToSpeechEngine, get_tts_engine
from .models.base_model import AIResponse

logger = logging.getLogger(__name__)


class ContentGenerationType(Enum):
    """内容生成类型"""
    COMMENTARY = "commentary"          # 视频解说
    MONOLOGUE = "monologue"            # 角色独白
    SCRIPT = "script"                  # 脚本生成
    CAPTION = "caption"               # 字幕生成
    HIGHLIGHTS = "highlights"         # 高光时刻
    STORYBOARD = "storyboard"         # 故事板
    TITLE = "title"                   # 标题生成


@dataclass
class ContentGenerationRequest:
    """内容生成请求"""
    request_id: str
    generation_type: ContentGenerationType
    video_info: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[callable] = None
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0


@dataclass
class ContentGenerationResult:
    """内容生成结果"""
    request_id: str
    success: bool
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    processing_time: float = 0.0


class IntelligentContentGenerator(QObject):
    """智能内容生成器"""
    
    # 信号定义
    generation_started = pyqtSignal(str)  # 请求ID
    generation_progress = pyqtSignal(str, float)  # 请求ID, 进度
    generation_completed = pyqtSignal(str, object)  # 请求ID, 结果
    generation_failed = pyqtSignal(str, str)  # 请求ID, 错误信息
    
    def __init__(self, ai_manager: AIManager):
        super().__init__()
        self.ai_manager = ai_manager
        self.tts_engine = get_tts_engine()
        
        # 活动请求
        self.active_requests: Dict[str, ContentGenerationRequest] = {}
        self.request_results: Dict[str, ContentGenerationResult] = {}
        
        # 配置
        self.max_concurrent_requests = 5
        self.default_timeout = 30.0
        
        # 定时器
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_requests)
        self.cleanup_timer.start(60000)  # 每分钟清理一次
        
        logger.info("智能内容生成器初始化完成")
    
    async def generate_commentary(self, 
                                 video_info: Dict[str, Any], 
                                 style: str = "专业解说",
                                 **kwargs) -> ContentGenerationResult:
        """生成视频解说"""
        request_id = f"commentary_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.COMMENTARY,
            video_info=video_info,
            parameters={"style": style, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_monologue(self,
                               video_info: Dict[str, Any],
                               character: str = "主角",
                               emotion: str = "平静",
                               **kwargs) -> ContentGenerationResult:
        """生成角色独白"""
        request_id = f"monologue_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.MONOLOGUE,
            video_info=video_info,
            parameters={"character": character, "emotion": emotion, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_script(self,
                           video_type: str = "短视频",
                           theme: str = "科技",
                           duration: int = 60,
                           **kwargs) -> ContentGenerationResult:
        """生成视频脚本"""
        request_id = f"script_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.SCRIPT,
            video_info={"type": video_type, "theme": theme, "duration": duration},
            parameters={"video_type": video_type, "theme": theme, "duration": duration, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_caption(self,
                             video_content: str,
                             language: str = "zh",
                             **kwargs) -> ContentGenerationResult:
        """生成视频字幕"""
        request_id = f"caption_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.CAPTION,
            video_info={"content": video_content, "language": language},
            parameters={"content": video_content, "language": language, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_highlights(self,
                                video_description: str,
                                count: int = 5,
                                **kwargs) -> ContentGenerationResult:
        """生成高光时刻"""
        request_id = f"highlights_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.HIGHLIGHTS,
            video_info={"description": video_description, "count": count},
            parameters={"description": video_description, "count": count, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_storyboard(self,
                                video_concept: str,
                                scenes: int = 5,
                                **kwargs) -> ContentGenerationResult:
        """生成故事板"""
        request_id = f"storyboard_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.STORYBOARD,
            video_info={"concept": video_concept, "scenes": scenes},
            parameters={"concept": video_concept, "scenes": scenes, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def generate_title(self,
                           video_content: str,
                           style: str = "吸引人",
                           count: int = 5,
                           **kwargs) -> ContentGenerationResult:
        """生成视频标题"""
        request_id = f"title_{int(time.time() * 1000)}"
        request = ContentGenerationRequest(
            request_id=request_id,
            generation_type=ContentGenerationType.TITLE,
            video_info={"content": video_content, "style": style, "count": count},
            parameters={"content": video_content, "style": style, "count": count, **kwargs}
        )
        
        return await self._generate_content(request)
    
    async def _generate_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成内容"""
        start_time = time.time()
        
        try:
            # 发射开始信号
            self.generation_started.emit(request.request_id)
            
            # 根据类型生成内容
            if request.generation_type == ContentGenerationType.COMMENTARY:
                result = await self._generate_commentary_content(request)
            elif request.generation_type == ContentGenerationType.MONOLOGUE:
                result = await self._generate_monologue_content(request)
            elif request.generation_type == ContentGenerationType.SCRIPT:
                result = await self._generate_script_content(request)
            elif request.generation_type == ContentGenerationType.CAPTION:
                result = await self._generate_caption_content(request)
            elif request.generation_type == ContentGenerationType.HIGHLIGHTS:
                result = await self._generate_highlights_content(request)
            elif request.generation_type == ContentGenerationType.STORYBOARD:
                result = await self._generate_storyboard_content(request)
            elif request.generation_type == ContentGenerationType.TITLE:
                result = await self._generate_title_content(request)
            else:
                raise Exception(f"不支持的内容生成类型: {request.generation_type}")
            
            # 计算处理时间
            result.processing_time = time.time() - start_time
            
            # 保存结果
            self.request_results[request.request_id] = result
            
            # 发射完成信号
            if result.success:
                self.generation_completed.emit(request.request_id, result)
            else:
                self.generation_failed.emit(request.request_id, result.error_message)
            
            # 执行回调
            if request.callback:
                request.callback(result)
            
            return result
            
        except Exception as e:
            error_msg = f"内容生成失败: {str(e)}"
            logger.error(error_msg)
            
            result = ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )
            
            self.generation_failed.emit(request.request_id, error_msg)
            return result
    
    async def _generate_commentary_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成解说内容"""
        style = request.parameters.get("style", "专业解说")
        video_info = request.video_info
        
        prompt = f"""
请为以下视频生成{style}风格的解说词：

视频信息：
- 时长：{video_info.get('duration', '未知')}秒
- 类型：{video_info.get('type', '未知')}
- 内容：{video_info.get('content', '未知')}
- 风格：{video_info.get('style', '未知')}

要求：
1. 语言生动有趣，符合短视频特点
2. 解说词时长与视频时长匹配
3. 突出视频亮点和关键信息
4. 风格统一，节奏感强
5. 适合目标观众群体

请生成完整的解说词：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "style": style,
                    "video_info": video_info,
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_monologue_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成独白内容"""
        character = request.parameters.get("character", "主角")
        emotion = request.parameters.get("emotion", "平静")
        video_info = request.video_info
        
        prompt = f"""
请为视频中的{character}角色生成{emotion}情绪的第一人称独白：

视频信息：
- 时长：{video_info.get('duration', '未知')}秒
- 类型：{video_info.get('type', '未知')}
- 内容：{video_info.get('content', '未知')}
- 场景：{video_info.get('scene', '未知')}

角色设定：
- 角色：{character}
- 情绪：{emotion}
- 背景：{request.parameters.get('background', '未知')}

要求：
1. 使用第一人称视角
2. 体现角色的性格特点
3. 表达出指定的情绪
4. 语言自然流畅
5. 符合视频场景和氛围

请生成完整的独白内容：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "character": character,
                    "emotion": emotion,
                    "video_info": video_info,
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_script_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成脚本内容"""
        video_type = request.parameters.get("video_type", "短视频")
        theme = request.parameters.get("theme", "科技")
        duration = request.parameters.get("duration", 60)
        
        prompt = f"""
请为{video_type}视频生成完整的脚本：

视频要求：
- 类型：{video_type}
- 主题：{theme}
- 时长：{duration}秒
- 风格：{request.parameters.get('style', '专业')}
- 目标观众：{request.parameters.get('audience', '大众')}

脚本结构：
1. 开场吸引注意力（5-10秒）
2. 主题引入（10-15秒）
3. 主体内容展开（根据时长调整）
4. 总结和结尾（5-10秒）

要求：
1. 结构清晰，逻辑连贯
2. 语言生动，有感染力
3. 适合视频表现形式
4. 考虑时长限制
5. 包含必要的场景和动作描述

请生成完整的视频脚本：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "video_type": video_type,
                    "theme": theme,
                    "duration": duration,
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_caption_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成字幕内容"""
        content = request.parameters.get("content", "")
        language = request.parameters.get("language", "zh")
        
        prompt = f"""
请为以下视频内容生成{language}字幕：

视频内容：
{content}

要求：
1. 字幕简洁明了，易于阅读
2. 时间轴安排合理
3. 语言通顺自然
4. 符合视频节奏
5. 考虑观众阅读速度

请生成字幕内容（包含时间轴）：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "language": language,
                    "content_length": len(content),
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_highlights_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成高光时刻内容"""
        description = request.parameters.get("description", "")
        count = request.parameters.get("count", 5)
        
        prompt = f"""
请从以下视频中提取{count}个高光时刻：

视频描述：
{description}

要求：
1. 识别视频中的精彩片段
2. 为每个高光时刻提供时间点和描述
3. 说明为什么这些片段值得关注
4. 考虑观众兴趣点
5. 提供剪辑建议

请生成高光时刻列表：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "count": count,
                    "description_length": len(description),
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_storyboard_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成故事板内容"""
        concept = request.parameters.get("concept", "")
        scenes = request.parameters.get("scenes", 5)
        
        prompt = f"""
请为以下视频概念生成{scenes}个场景的故事板：

视频概念：
{concept}

要求：
1. 每个场景包含视觉描述
2. 提供镜头建议（景别、角度等）
3. 包含音频和音效建议
4. 说明场景之间的转场
5. 考虑节奏和情感变化

请生成完整的故事板：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "concept": concept,
                    "scenes": scenes,
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    async def _generate_title_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成标题内容"""
        content = request.parameters.get("content", "")
        style = request.parameters.get("style", "吸引人")
        count = request.parameters.get("count", 5)
        
        prompt = f"""
请为以下视频内容生成{count}个{style}风格的标题：

视频内容：
{content}

要求：
1. 标题简洁有力
2. 能够吸引目标观众
3. 体现视频核心内容
4. 适合平台算法推荐
5. 包含关键词优化

请生成标题列表：
"""
        
        response = await self.ai_manager.generate_text_async(prompt)
        
        if response.success:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=True,
                content=response.content,
                metadata={
                    "style": style,
                    "count": count,
                    "content_length": len(content),
                    "tokens": response.usage.get("total_tokens", 0)
                }
            )
        else:
            return ContentGenerationResult(
                request_id=request.request_id,
                success=False,
                error_message=response.error_message
            )
    
    def _cleanup_old_requests(self):
        """清理旧请求"""
        current_time = time.time()
        expired_requests = [
            request_id for request_id, request in self.active_requests.items()
            if current_time - request.created_at > 3600  # 1小时过期
        ]
        
        for request_id in expired_requests:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
        
        expired_results = [
            result_id for result_id, result in self.request_results.items()
            if current_time - result.processing_time > 3600
        ]
        
        for result_id in expired_results:
            if result_id in self.request_results:
                del self.request_results[result_id]
        
        if expired_requests or expired_results:
            logger.info(f"清理了 {len(expired_requests)} 个过期请求和 {len(expired_results)} 个过期结果")
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """获取请求状态"""
        if request_id in self.active_requests:
            request = self.active_requests[request_id]
            return {
                "request_id": request_id,
                "status": "processing",
                "generation_type": request.generation_type.value,
                "created_at": request.created_at
            }
        elif request_id in self.request_results:
            result = self.request_results[request_id]
            return {
                "request_id": request_id,
                "status": "completed" if result.success else "failed",
                "result": result
            }
        else:
            return {
                "request_id": request_id,
                "status": "not_found"
            }
    
    def get_active_requests(self) -> List[str]:
        """获取活动请求列表"""
        return list(self.active_requests.keys())
    
    def get_recent_results(self, limit: int = 10) -> List[ContentGenerationResult]:
        """获取最近的结果"""
        results = list(self.request_results.values())
        results.sort(key=lambda x: x.processing_time, reverse=True)
        return results[:limit]
    
    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        if request_id in self.active_requests:
            del self.active_requests[request_id]
            logger.info(f"已取消请求: {request_id}")
            return True
        return False
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理智能内容生成器资源")
        
        # 停止定时器
        self.cleanup_timer.stop()
        
        # 清理TTS引擎
        if hasattr(self, 'tts_engine'):
            self.tts_engine.cleanup()
        
        # 清理请求和结果
        self.active_requests.clear()
        self.request_results.clear()
        
        logger.info("智能内容生成器资源清理完成")


# 工厂函数
def create_content_generator(ai_manager: AIManager) -> IntelligentContentGenerator:
    """创建智能内容生成器"""
    return IntelligentContentGenerator(ai_manager)