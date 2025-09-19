#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

from .ai_service import AIService
from .interfaces import AITaskType, create_text_generation_request
from .scene_detector import SceneDetector, SceneInfo
from app.core.video_manager import VideoClip


@dataclass
class ContentSegment:
    """内容片段"""
    start_time: float      # 开始时间（秒）
    end_time: float        # 结束时间（秒）
    content_type: str      # 内容类型：commentary, monologue, transition
    text: str              # 文本内容
    voice_settings: Dict[str, Any] = None  # 语音设置
    scene_info: Optional[SceneInfo] = None  # 关联的场景信息
    
    def __post_init__(self):
        if self.voice_settings is None:
            self.voice_settings = {}


@dataclass
class GeneratedContent:
    """生成的内容"""
    video: VideoClip
    editing_mode: str      # commentary, compilation, monologue
    segments: List[ContentSegment]
    total_duration: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentGenerator(QObject):
    """AI内容生成器"""
    
    # 信号
    generation_progress = pyqtSignal(int)           # 生成进度
    segment_generated = pyqtSignal(ContentSegment)  # 片段生成完成
    generation_completed = pyqtSignal(GeneratedContent)  # 生成完成
    
    def __init__(self, ai_service: AIService):
        super().__init__()

        self.ai_service = ai_service
        self.scene_detector = SceneDetector()
        
        # 生成模板
        self.commentary_templates = {
            "幽默风趣": {
                "opening": "哈喽大家好，今天给大家带来一个超级有趣的短剧！",
                "scene_intro": "接下来这个场景真的太{emotion}了！",
                "highlight": "注意看这里，{description}，简直不要太{feeling}！",
                "transition": "然后呢，剧情发生了神转折...",
                "ending": "好了，今天的短剧就到这里，喜欢的话记得点赞关注哦！"
            },
            "专业分析": {
                "opening": "今天我们来分析一下这部短剧的精彩之处。",
                "scene_intro": "这个场景展现了{theme}的主题。",
                "highlight": "这里的{element}处理得非常巧妙，{analysis}。",
                "transition": "接下来的情节发展值得我们关注。",
                "ending": "总的来说，这部短剧在{aspect}方面表现出色。"
            },
            "情感解读": {
                "opening": "这个短剧真的触动了我的心弦。",
                "scene_intro": "看到这里，我感受到了{emotion}。",
                "highlight": "这个瞬间，{description}，让人{feeling}。",
                "transition": "情感的变化在这里达到了高潮。",
                "ending": "希望这个故事也能给你带来感动。"
            }
        }
        
        self.monologue_templates = {
            "主角视角": {
                "opening": "我从来没想过，我的生活会发生这样的变化...",
                "reflection": "回想起{event}，我{feeling}...",
                "conflict": "当{situation}发生时，我{reaction}...",
                "resolution": "最终，我明白了{lesson}...",
                "ending": "现在的我，{current_state}..."
            },
            "配角视角": {
                "opening": "作为一个旁观者，我见证了这一切...",
                "observation": "我看到{character}{action}，{feeling}...",
                "insight": "也许{character}没有意识到，{insight}...",
                "support": "我想对{character}说，{message}...",
                "ending": "每个人都有自己的故事，{reflection}..."
            }
        }
    
    async def generate_commentary(self, video: VideoClip, style: str = "幽默风趣", 
                                 scene_analysis: bool = True) -> GeneratedContent:
        """生成解说内容"""
        self.generation_progress.emit(0)
        
        # 1. 场景检测（如果需要）
        scenes = []
        if scene_analysis:
            self.generation_progress.emit(20)
            scenes = await self.scene_detector.detect_scenes(video)
        
        # 2. 生成解说文本
        self.generation_progress.emit(40)
        segments = await self._generate_commentary_segments(video, scenes, style)
        
        # 3. 优化和调整
        self.generation_progress.emit(80)
        optimized_segments = await self._optimize_segments(segments)
        
        # 4. 创建最终内容
        self.generation_progress.emit(100)
        content = GeneratedContent(
            video=video,
            editing_mode="commentary",
            segments=optimized_segments,
            total_duration=video.duration,
            metadata={
                "style": style,
                "scene_count": len(scenes),
                "segment_count": len(optimized_segments)
            }
        )
        
        self.generation_completed.emit(content)
        return content
    
    async def generate_compilation(self, video: VideoClip, style: str = "高能燃向",
                                 highlight_ratio: float = 0.3) -> GeneratedContent:
        """生成混剪内容"""
        self.generation_progress.emit(0)
        
        # 1. 检测精彩片段
        self.generation_progress.emit(30)
        highlights = await self.scene_detector.detect_highlights(video)
        
        # 2. 选择最佳片段
        self.generation_progress.emit(60)
        selected_scenes = self._select_compilation_scenes(highlights, highlight_ratio)
        
        # 3. 生成转场和连接文本
        self.generation_progress.emit(80)
        segments = await self._generate_compilation_segments(selected_scenes, style)
        
        # 4. 创建最终内容
        self.generation_progress.emit(100)
        content = GeneratedContent(
            video=video,
            editing_mode="compilation",
            segments=segments,
            total_duration=sum(s.end_time - s.start_time for s in segments),
            metadata={
                "style": style,
                "highlight_ratio": highlight_ratio,
                "original_duration": video.duration
            }
        )
        
        self.generation_completed.emit(content)
        return content
    
    async def generate_monologue(self, video: VideoClip, character: str = "主角",
                               emotion: str = "平静叙述") -> GeneratedContent:
        """生成独白内容"""
        self.generation_progress.emit(0)
        
        # 1. 场景分析
        self.generation_progress.emit(25)
        scenes = await self.scene_detector.detect_scenes(video)
        emotional_scenes = await self.scene_detector.detect_emotional_moments(video)
        
        # 2. 生成独白文本
        self.generation_progress.emit(60)
        segments = await self._generate_monologue_segments(video, scenes, emotional_scenes, character, emotion)
        
        # 3. 情感调整
        self.generation_progress.emit(85)
        adjusted_segments = await self._adjust_emotional_tone(segments, emotion)
        
        # 4. 创建最终内容
        self.generation_progress.emit(100)
        content = GeneratedContent(
            video=video,
            editing_mode="monologue",
            segments=adjusted_segments,
            total_duration=video.duration,
            metadata={
                "character": character,
                "emotion": emotion,
                "emotional_scene_count": len(emotional_scenes)
            }
        )
        
        self.generation_completed.emit(content)
        return content
    
    async def _generate_commentary_segments(self, video: VideoClip, scenes: List[SceneInfo], 
                                          style: str) -> List[ContentSegment]:
        """生成解说片段"""
        segments = []
        template = self.commentary_templates.get(style, self.commentary_templates["幽默风趣"])
        
        # 开场白
        opening_text = await self._generate_ai_text(
            f"为短剧《{video.name}》生成{style}的开场白，要求简洁有趣，吸引观众注意。"
        )
        segments.append(ContentSegment(
            start_time=0,
            end_time=3,
            content_type="commentary",
            text=opening_text or template["opening"]
        ))
        
        # 为每个场景生成解说
        for i, scene in enumerate(scenes):
            if scene.scene_type in ["high_energy", "action", "emotional"]:
                # 生成场景解说
                scene_text = await self._generate_scene_commentary(scene, style)
                
                segments.append(ContentSegment(
                    start_time=scene.start_time,
                    end_time=min(scene.start_time + 5, scene.end_time),
                    content_type="commentary",
                    text=scene_text,
                    scene_info=scene
                ))
                
                # 发射信号
                self.segment_generated.emit(segments[-1])
        
        # 结尾
        if segments:
            ending_text = await self._generate_ai_text(
                f"为短剧解说生成{style}的结尾，要求呼吁点赞关注。"
            )
            segments.append(ContentSegment(
                start_time=video.duration - 3,
                end_time=video.duration,
                content_type="commentary",
                text=ending_text or template["ending"]
            ))
        
        return segments
    
    async def _generate_scene_commentary(self, scene: SceneInfo, style: str) -> str:
        """生成场景解说"""
        prompt = f"""
为以下场景生成{style}的解说：
场景类型：{scene.scene_type}
场景时长：{scene.end_time - scene.start_time:.1f}秒
场景描述：{scene.description}

要求：
1. 风格：{style}
2. 长度：20-30字
3. 生动有趣，符合短视频观众喜好
"""
        
        ai_request = create_text_generation_request(prompt=prompt)
        response = await self.ai_service.process_request(ai_request)
        return response.content if response.success else f"这里是{scene.scene_type}场景"
    
    async def _generate_compilation_segments(self, scenes: List[SceneInfo], style: str) -> List[ContentSegment]:
        """生成混剪片段"""
        segments = []
        
        for i, scene in enumerate(scenes):
            # 添加场景片段
            segments.append(ContentSegment(
                start_time=scene.start_time,
                end_time=scene.end_time,
                content_type="scene",
                text="",
                scene_info=scene
            ))
            
            # 添加转场文本（如果不是最后一个场景）
            if i < len(scenes) - 1:
                transition_text = await self._generate_transition_text(scene, scenes[i + 1], style)
                segments.append(ContentSegment(
                    start_time=scene.end_time,
                    end_time=scene.end_time + 1,
                    content_type="transition",
                    text=transition_text
                ))
        
        return segments
    
    async def _generate_monologue_segments(self, video: VideoClip, scenes: List[SceneInfo],
                                         emotional_scenes: List[SceneInfo], character: str, 
                                         emotion: str) -> List[ContentSegment]:
        """生成独白片段"""
        segments = []
        template = self.monologue_templates.get(character, self.monologue_templates["主角视角"])
        
        # 开场独白
        opening_text = await self._generate_ai_text(
            f"以{character}的视角，用{emotion}的语调，为短剧生成开场独白。"
        )
        segments.append(ContentSegment(
            start_time=0,
            end_time=5,
            content_type="monologue",
            text=opening_text or template["opening"]
        ))
        
        # 为情感场景生成独白
        for scene in emotional_scenes:
            monologue_text = await self._generate_emotional_monologue(scene, character, emotion)
            segments.append(ContentSegment(
                start_time=scene.start_time,
                end_time=min(scene.start_time + 8, scene.end_time),
                content_type="monologue",
                text=monologue_text,
                scene_info=scene
            ))
        
        return segments
    
    async def _generate_emotional_monologue(self, scene: SceneInfo, character: str, emotion: str) -> str:
        """生成情感独白"""
        prompt = f"""
以{character}的视角，用{emotion}的语调，为以下情感场景生成第一人称独白：
场景描述：{scene.description}
场景时长：{scene.end_time - scene.start_time:.1f}秒

要求：
1. 第一人称视角
2. 情感基调：{emotion}
3. 长度：30-50字
4. 贴合剧情发展
"""
        
        ai_request = create_text_generation_request(prompt=prompt)
        response = await self.ai_service.process_request(ai_request)
        return response.content if response.success else "此时此刻，我的内心五味杂陈..."
    
    def _select_compilation_scenes(self, highlights: List[SceneInfo], ratio: float) -> List[SceneInfo]:
        """选择混剪场景"""
        # 按置信度排序
        sorted_highlights = sorted(highlights, key=lambda x: x.confidence, reverse=True)
        
        # 选择指定比例的场景
        target_count = max(1, int(len(sorted_highlights) * ratio))
        return sorted_highlights[:target_count]
    
    async def _generate_transition_text(self, scene1: SceneInfo, scene2: SceneInfo, style: str) -> str:
        """生成转场文本"""
        prompt = f"为从{scene1.scene_type}场景到{scene2.scene_type}场景的转场生成{style}的过渡文本，要求简短有力。"
        ai_request = create_text_generation_request(prompt=prompt)
        response = await self.ai_service.process_request(ai_request)
        return response.content if response.success else "接下来..."
    
    async def _optimize_segments(self, segments: List[ContentSegment]) -> List[ContentSegment]:
        """优化片段"""
        # 这里可以添加片段优化逻辑，比如调整时间、合并重叠等
        return segments
    
    async def _adjust_emotional_tone(self, segments: List[ContentSegment], emotion: str) -> List[ContentSegment]:
        """调整情感基调"""
        # 这里可以添加情感调整逻辑
        return segments
    
    async def _generate_ai_text(self, prompt: str) -> str:
        """生成AI文本"""
        ai_request = create_text_generation_request(prompt=prompt)
        response = await self.ai_service.process_request(ai_request)
        return response.content if response.success else ""
