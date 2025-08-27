"""
Commentary generation system for VideoEpicCreator

This module provides advanced commentary generation algorithms for short drama videos,
including intelligent content analysis, timing optimization, and style adaptation.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime
import logging

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..ai.providers import AIManager, AIProvider, ContentType
from ..core.video_engine import VideoProcessor, Scene, TimelineSegment
from .drama_analyzer import (
    DramaAnalyzer, DramaContent, SceneAnalysis, CommentaryStrategy,
    DramaGenre, EmotionType, SceneType
)


class CommentaryStyle(Enum):
    """Commentary style types"""
    PROFESSIONAL = "professional"    # 专业解说
    CASUAL = "casual"               # 随性解说
    HUMOROUS = "humorous"           # 幽默解说
    DRAMATIC = "dramatic"           # 戏剧化解说
    ROMANTIC = "romantic"           # 浪漫解说
    EDUCATIONAL = "educational"     # 教育解说
    ENTERTAINING = "entertaining"   # 娱乐解说
    INSPIRATIONAL = "inspirational" # 励志解说
    STORYTELLING = "storytelling"   # 故事化解说
    ANALYTICAL = "analytical"       # 分析型解说


class CommentaryStructure(Enum):
    """Commentary structure types"""
    LINEAR = "linear"               # 线性结构
    THEMATIC = "thematic"           # 主题结构
    EMOTIONAL = "emotional"         # 情感结构
    CHARACTER_FOCUS = "character"   # 角色聚焦
    PLOT_FOCUS = "plot"            # 剧情聚焦
    MIXED = "mixed"                # 混合结构


@dataclass
class CommentarySegment:
    """Individual commentary segment"""
    start_time: float
    end_time: float
    content: str
    style: CommentaryStyle
    emotion: EmotionType
    importance: float
    keywords: List[str]
    delivery_hints: Dict[str, Any]
    transition_hints: Optional[str] = None


@dataclass
class CommentaryScript:
    """Complete commentary script"""
    title: str
    segments: List[CommentarySegment]
    total_duration: float
    style: CommentaryStyle
    structure: CommentaryStructure
    target_audience: str
    language: str
    metadata: Dict[str, Any]


@dataclass
class GenerationOptions:
    """Commentary generation options"""
    style: CommentaryStyle = CommentaryStyle.PROFESSIONAL
    structure: CommentaryStructure = CommentaryStructure.LINEAR
    target_length: Optional[float] = None  # Target duration in seconds
    language: str = "zh-CN"
    include_transitions: bool = True
    emphasis_keywords: List[str] = field(default_factory=list)
    avoid_topics: List[str] = field(default_factory=list)
    personal_touches: List[str] = field(default_factory=list)
    humor_level: float = 0.5  # 0.0 to 1.0
    emotional_depth: float = 0.7  # 0.0 to 1.0
    technical_detail: float = 0.3  # 0.0 to 1.0


class CommentaryGenerator(BaseComponent[Dict[str, Any]]):
    """Advanced commentary generation engine"""
    
    def __init__(
        self,
        ai_manager: AIManager,
        drama_analyzer: DramaAnalyzer,
        video_processor: VideoProcessor,
        config: Optional[ComponentConfig] = None
    ):
        super().__init__("commentary_generator", config)
        self.ai_manager = ai_manager
        self.drama_analyzer = drama_analyzer
        self.video_processor = video_processor
        self.generation_cache: Dict[str, CommentaryScript] = {}
        self.style_templates = self._load_style_templates()
        
    async def initialize(self) -> bool:
        """Initialize commentary generator"""
        try:
            self.logger.info("Initializing Commentary Generator")
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialization")
            return False
    
    async def start(self) -> bool:
        """Start commentary generator"""
        self.set_state(ComponentState.RUNNING)
        return True
    
    async def stop(self) -> bool:
        """Stop commentary generator"""
        self.set_state(ComponentState.STOPPED)
        return True
    
    async def cleanup(self) -> bool:
        """Clean up resources"""
        self.generation_cache.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get commentary generator status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "cache_size": len(self.generation_cache),
            "available_styles": len(self.style_templates),
            "metrics": self.metrics.__dict__
        }
    
    async def generate_commentary(
        self,
        video_path: str,
        options: GenerationOptions,
        progress_callback: Optional[callable] = None
    ) -> CommentaryScript:
        """Generate complete commentary script"""
        try:
            # Check cache first
            cache_key = f"{video_path}_{options.style.value}_{options.structure.value}"
            if cache_key in self.generation_cache:
                return self.generation_cache[cache_key]
            
            self.logger.info(f"Generating commentary for: {video_path}")
            start_time = asyncio.get_event_loop().time()
            
            # Step 1: Analyze video content
            if progress_callback:
                progress_callback(0.1, "分析视频内容...")
            
            drama_content = await self.drama_analyzer.analyze_drama_content(video_path)
            scene_analyses = await self.drama_analyzer.analyze_scenes(video_path, drama_content)
            
            # Step 2: Generate commentary strategy
            if progress_callback:
                progress_callback(0.2, "制定解说策略...")
            
            commentary_strategy = await self.drama_analyzer.generate_commentary_strategy(
                drama_content, {"style": options.style.value}
            )
            
            # Step 3: Generate commentary segments
            if progress_callback:
                progress_callback(0.3, "生成解说片段...")
            
            segments = await self._generate_commentary_segments(
                video_path, drama_content, scene_analyses, options, commentary_strategy
            )
            
            # Step 4: Optimize timing and flow
            if progress_callback:
                progress_callback(0.8, "优化解说时序...")
            
            optimized_segments = await self._optimize_timing_and_flow(segments, options)
            
            # Step 5: Add transitions and polish
            if progress_callback:
                progress_callback(0.9, "完善解说细节...")
            
            final_segments = await self._add_transitions_and_polish(optimized_segments, options)
            
            # Create final script
            total_duration = sum(seg.end_time - seg.start_time for seg in final_segments)
            script = CommentaryScript(
                title=f"{drama_content.title} - {options.style.value}解说",
                segments=final_segments,
                total_duration=total_duration,
                style=options.style,
                structure=options.structure,
                target_audience=drama_content.target_audience,
                language=options.language,
                metadata={
                    "generation_time": datetime.now().isoformat(),
                    "video_path": video_path,
                    "content_analysis": {
                        "genre": drama_content.genre.value,
                        "theme": drama_content.theme,
                        "emotional_complexity": len(set(emotion for _, emotion, _ in drama_content.emotional_arc))
                    },
                    "generation_options": {
                        "style": options.style.value,
                        "structure": options.structure.value,
                        "humor_level": options.humor_level,
                        "emotional_depth": options.emotional_depth
                    }
                }
            )
            
            # Cache result
            self.generation_cache[cache_key] = script
            
            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            self.update_metrics(processing_time)
            
            if progress_callback:
                progress_callback(1.0, "解说生成完成")
            
            self.logger.info(f"Commentary generated in {processing_time:.2f}s")
            return script
        
        except Exception as e:
            self.handle_error(e, "generate_commentary")
            raise
    
    async def _generate_commentary_segments(
        self,
        video_path: str,
        drama_content: DramaContent,
        scene_analyses: List[SceneAnalysis],
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> List[CommentarySegment]:
        """Generate individual commentary segments"""
        try:
            segments = []
            
            # Generate segments based on structure
            if options.structure == CommentaryStructure.LINEAR:
                segments = await self._generate_linear_segments(
                    drama_content, scene_analyses, options, strategy
                )
            elif options.structure == CommentaryStructure.THEMATIC:
                segments = await self._generate_thematic_segments(
                    drama_content, scene_analyses, options, strategy
                )
            elif options.structure == CommentaryStructure.EMOTIONAL:
                segments = await self._generate_emotional_segments(
                    drama_content, scene_analyses, options, strategy
                )
            else:
                # Default to linear
                segments = await self._generate_linear_segments(
                    drama_content, scene_analyses, options, strategy
                )
            
            return segments
        
        except Exception as e:
            self.logger.error(f"Commentary segments generation failed: {e}")
            raise
    
    async def _generate_linear_segments(
        self,
        drama_content: DramaContent,
        scene_analyses: List[SceneAnalysis],
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> List[CommentarySegment]:
        """Generate commentary segments following linear structure"""
        segments = []
        
        # Generate introduction
        intro_segment = await self._generate_introduction(
            drama_content, options, strategy
        )
        segments.append(intro_segment)
        
        # Generate scene-by-scene commentary
        for i, scene_analysis in enumerate(scene_analyses):
            scene_segment = await self._generate_scene_commentary(
                scene_analysis, i, drama_content, options, strategy
            )
            segments.append(scene_segment)
        
        # Generate conclusion
        conclusion_segment = await self._generate_conclusion(
            drama_content, options, strategy
        )
        segments.append(conclusion_segment)
        
        return segments
    
    async def _generate_introduction(
        self,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> CommentarySegment:
        """Generate introduction segment"""
        try:
            prompt = self._build_introduction_prompt(drama_content, options, strategy)
            
            response = await self.ai_manager.generate_content(
                prompt=prompt,
                content_type=ContentType.COMMENTARY,
                max_tokens=300
            )
            
            if response.error:
                content = f"欢迎观看{drama_content.title}，这是一个精彩的{drama_content.genre.value}故事。"
            else:
                content = response.content
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            return CommentarySegment(
                start_time=0.0,
                end_time=10.0,  # 10 second introduction
                content=content,
                style=options.style,
                emotion=EmotionType.EXCITED,
                importance=1.0,
                keywords=keywords,
                delivery_hints={"pace": "medium", "emphasis": "high"},
                transition_hints="自然过渡到主要内容"
            )
        
        except Exception as e:
            self.logger.error(f"Introduction generation failed: {e}")
            return CommentarySegment(
                start_time=0.0,
                end_time=10.0,
                content=f"欢迎观看{drama_content.title}",
                style=options.style,
                emotion=EmotionType.EXCITED,
                importance=1.0,
                keywords=[],
                delivery_hints={},
                transition_hints=""
            )
    
    async def _generate_scene_commentary(
        self,
        scene_analysis: SceneAnalysis,
        scene_index: int,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> CommentarySegment:
        """Generate commentary for a specific scene"""
        try:
            prompt = self._build_scene_prompt(
                scene_analysis, scene_index, drama_content, options, strategy
            )
            
            response = await self.ai_manager.generate_content(
                prompt=prompt,
                content_type=ContentType.COMMENTARY,
                max_tokens=200
            )
            
            if response.error:
                content = f"这是第{scene_index+1}个场景，{scene_analysis.description}"
            else:
                content = response.content
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            return CommentarySegment(
                start_time=scene_analysis.scene.start_time,
                end_time=scene_analysis.scene.end_time,
                content=content,
                style=options.style,
                emotion=scene_analysis.emotion,
                importance=scene_analysis.importance,
                keywords=keywords,
                delivery_hints=self._get_delivery_hints(scene_analysis.emotion, options.style),
                transition_hints=self._get_transition_hint(scene_analysis.scene_type)
            )
        
        except Exception as e:
            self.logger.error(f"Scene commentary generation failed: {e}")
            return CommentarySegment(
                start_time=scene_analysis.scene.start_time,
                end_time=scene_analysis.scene.end_time,
                content=f"第{scene_index+1}个场景",
                style=options.style,
                emotion=scene_analysis.emotion,
                importance=scene_analysis.importance,
                keywords=[],
                delivery_hints={},
                transition_hints=""
            )
    
    async def _generate_conclusion(
        self,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> CommentarySegment:
        """Generate conclusion segment"""
        try:
            prompt = self._build_conclusion_prompt(drama_content, options, strategy)
            
            response = await self.ai_manager.generate_content(
                prompt=prompt,
                content_type=ContentType.COMMENTARY,
                max_tokens=250
            )
            
            if response.error:
                content = f"感谢观看{drama_content.title}，希望您喜欢这个故事。"
            else:
                content = response.content
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            # Calculate conclusion timing
            video_duration = max(scene.end_time for scene in drama_content.emotional_arc) if drama_content.emotional_arc else 60.0
            
            return CommentarySegment(
                start_time=max(0, video_duration - 15.0),
                end_time=video_duration,
                content=content,
                style=options.style,
                emotion=EmotionType.HOPEFUL,
                importance=1.0,
                keywords=keywords,
                delivery_hints={"pace": "slow", "emphasis": "medium"},
                transition_hints=""
            )
        
        except Exception as e:
            self.logger.error(f"Conclusion generation failed: {e}")
            return CommentarySegment(
                start_time=0.0,
                end_time=10.0,
                content=f"感谢观看{drama_content.title}",
                style=options.style,
                emotion=EmotionType.HOPEFUL,
                importance=1.0,
                keywords=[],
                delivery_hints={},
                transition_hints=""
            )
    
    def _build_introduction_prompt(
        self,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> str:
        """Build prompt for introduction generation"""
        style_template = self.style_templates.get(options.style, {})
        
        prompt = f"""
请为以下短剧创作一个引人入胜的开场解说：

视频信息：
- 标题：{drama_content.title}
- 类型：{drama_content.genre.value}
- 主题：{drama_content.theme}
- 目标观众：{drama_content.target_audience}

剧情简介：{drama_content.plot_summary}

解说要求：
- 风格：{style_template.get('description', options.style.value)}
- 语气：{strategy.tone}
- 节奏：{strategy.pace}
- 语言风格：{strategy.language_style}
- 长度：15-20秒
- 要吸引观众注意力
- 为后续内容做好铺垫

请创作一个精彩的开场解说：
"""
        
        return prompt
    
    def _build_scene_prompt(
        self,
        scene_analysis: SceneAnalysis,
        scene_index: int,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> str:
        """Build prompt for scene commentary generation"""
        style_template = self.style_templates.get(options.style, {})
        
        prompt = f"""
请为以下场景创作解说词：

场景信息：
- 场景编号：{scene_index + 1}
- 时间：{scene_analysis.scene.start_time:.1f}s - {scene_analysis.scene.end_time:.1f}s
- 类型：{scene_analysis.scene_type.value}
- 情感：{scene_analysis.emotion.value}
- 重要性：{scene_analysis.importance:.2f}

整体剧情：
- 标题：{drama_content.title}
- 类型：{drama_content.genre.value}

解说要求：
- 风格：{style_template.get('description', options.style.value)}
- 语气：{strategy.tone}
- 语言风格：{strategy.language_style}
- 长度：{scene_analysis.scene.duration:.1f}秒左右
- 要突出场景的重要性和情感
- 与整体剧情保持连贯性

请创作场景解说词：
"""
        
        return prompt
    
    def _build_conclusion_prompt(
        self,
        drama_content: DramaContent,
        options: GenerationOptions,
        strategy: CommentaryStrategy
    ) -> str:
        """Build prompt for conclusion generation"""
        style_template = self.style_templates.get(options.style, {})
        
        prompt = f"""
请为以下短剧创作一个精彩的结尾解说：

视频信息：
- 标题：{drama_content.title}
- 类型：{drama_content.genre.value}
- 主题：{drama_content.theme}
- 目标观众：{drama_content.target_audience}

剧情总结：{drama_content.plot_summary}

解说要求：
- 风格：{style_template.get('description', options.style.value)}
- 语气：{strategy.tone}
- 节奏：{strategy.pace}
- 语言风格：{strategy.language_style}
- 长度：15-20秒
- 要总结故事要点
- 给观众留下深刻印象
- 鼓励互动和分享

请创作一个精彩的结尾解说：
"""
        
        return prompt
    
    async def _optimize_timing_and_flow(
        self,
        segments: List[CommentarySegment],
        options: GenerationOptions
    ) -> List[CommentarySegment]:
        """Optimize segment timing and flow"""
        try:
            optimized_segments = []
            
            # Sort segments by start time
            segments.sort(key=lambda x: x.start_time)
            
            # Adjust timing to avoid overlaps and gaps
            for i, segment in enumerate(segments):
                if i == 0:
                    # First segment
                    optimized_segment = segment
                else:
                    previous_segment = optimized_segments[i-1]
                    
                    # Ensure no overlap
                    if segment.start_time < previous_segment.end_time:
                        segment.start_time = previous_segment.end_time + 0.1
                    
                    # Ensure reasonable gap
                    gap = segment.start_time - previous_segment.end_time
                    if gap > 2.0:  # Gap > 2 seconds
                        segment.start_time = previous_segment.end_time + 0.5
                    
                    optimized_segment = segment
                
                optimized_segments.append(optimized_segment)
            
            return optimized_segments
        
        except Exception as e:
            self.logger.error(f"Timing optimization failed: {e}")
            return segments
    
    async def _add_transitions_and_polish(
        self,
        segments: List[CommentarySegment],
        options: GenerationOptions
    ) -> List[CommentarySegment]:
        """Add transitions and polish commentary"""
        try:
            polished_segments = []
            
            for i, segment in enumerate(segments):
                # Add transition hints if enabled
                if options.include_transitions and i < len(segments) - 1:
                    transition = await self._generate_transition(segment, segments[i+1])
                    segment.transition_hints = transition
                
                # Polish content
                polished_content = await self._polish_content(segment.content, options)
                segment.content = polished_content
                
                polished_segments.append(segment)
            
            return polished_segments
        
        except Exception as e:
            self.logger.error(f"Transition and polish failed: {e}")
            return segments
    
    async def _generate_transition(
        self,
        current_segment: CommentarySegment,
        next_segment: CommentarySegment
    ) -> str:
        """Generate transition between segments"""
        try:
            prompt = f"""
请为以下两个解说片段生成自然的过渡语：

当前片段：
- 内容：{current_segment.content[:100]}...
- 情感：{current_segment.emotion.value}

下个片段：
- 内容：{next_segment.content[:100]}...
- 情感：{next_segment.emotion.value}

请生成1-2句自然的过渡语：
"""
            
            response = await self.ai_manager.generate_content(
                prompt=prompt,
                content_type=ContentType.COMMENTARY,
                max_tokens=50
            )
            
            return response.content if not response.error else ""
        
        except Exception as e:
            self.logger.error(f"Transition generation failed: {e}")
            return ""
    
    async def _polish_content(self, content: str, options: GenerationOptions) -> str:
        """Polish commentary content"""
        try:
            # Basic polishing based on options
            polished = content
            
            # Adjust humor level
            if options.humor_level > 0.7:
                polished = self._add_humor_elements(polished)
            elif options.humor_level < 0.3:
                polished = self._remove_humor_elements(polished)
            
            # Adjust emotional depth
            if options.emotional_depth > 0.7:
                polished = self._enhance_emotional_content(polished)
            
            return polished
        
        except Exception as e:
            self.logger.error(f"Content polishing failed: {e}")
            return content
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        try:
            # Simple keyword extraction
            words = re.findall(r'[\w\u4e00-\u9fff]+', content)
            word_freq = {}
            
            for word in words:
                if len(word) > 1:  # Ignore single characters
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            return [word for word, freq in keywords]
        
        except Exception:
            return []
    
    def _get_delivery_hints(self, emotion: EmotionType, style: CommentaryStyle) -> Dict[str, Any]:
        """Get delivery hints based on emotion and style"""
        hints = {
            "pace": "medium",
            "emphasis": "medium",
            "volume": "medium"
        }
        
        # Adjust based on emotion
        if emotion in [EmotionType.EXCITED, EmotionType.ANGRY]:
            hints["pace"] = "fast"
            hints["volume"] = "high"
        elif emotion in [EmotionType.SAD, EmotionType.NOSTALGIC]:
            hints["pace"] = "slow"
            hints["volume"] = "low"
        
        # Adjust based on style
        if style == CommentaryStyle.HUMOROUS:
            hints["pace"] = "medium-fast"
        elif style == CommentaryStyle.DRAMATIC:
            hints["emphasis"] = "high"
        
        return hints
    
    def _get_transition_hint(self, scene_type: SceneType) -> str:
        """Get transition hint based on scene type"""
        transition_map = {
            SceneType.INTRO: "自然引入故事",
            SceneType.CONFLICT: "突出冲突升级",
            SceneType.CLIMAX: "强调高潮时刻",
            SceneType.RESOLUTION: "平缓过渡到解决",
            SceneType.OUTRO: "温馨收尾",
            SceneType.TRANSITION: "流畅过渡",
            SceneType.FLASHBACK: "时空转换提示",
            SceneType.DIALOGUE: "自然过渡到对话",
            SceneType.ACTION: "动作节奏变化",
            SceneType.EMOTIONAL: "情感转换提示",
            SceneType.COMEDIC: "幽默过渡"
        }
        
        return transition_map.get(scene_type, "自然过渡")
    
    def _add_humor_elements(self, content: str) -> str:
        """Add humor elements to content"""
        # Simple humor enhancement
        humor_words = ["有趣的是", "令人忍俊不禁的是", "出乎意料的是", "戏剧性的是"]
        import random
        
        if random.random() < 0.3:  # 30% chance to add humor
            word = random.choice(humor_words)
            return f"{word}，{content}"
        
        return content
    
    def _remove_humor_elements(self, content: str) -> str:
        """Remove humor elements from content"""
        # Remove obvious humor indicators
        content = re.sub(r'有趣的是|令人忍俊不禁的是|出乎意料的是|戏剧性的是', '', content)
        return content.strip()
    
    def _enhance_emotional_content(self, content: str) -> str:
        """Enhance emotional content"""
        # Add emotional depth
        emotional_words = ["深刻地", "动人地", "真挚地", "感人地"]
        import random
        
        if random.random() < 0.4:  # 40% chance to enhance
            word = random.choice(emotional_words)
            return f"{word}{content}"
        
        return content
    
    def _load_style_templates(self) -> Dict[CommentaryStyle, Dict[str, Any]]:
        """Load style templates"""
        return {
            CommentaryStyle.PROFESSIONAL: {
                "description": "专业解说风格",
                "tone": "正式、客观",
                "pace": "中等",
                "language": "专业术语",
                "examples": ["从专业角度来看", "值得注意的是", "关键在于"]
            },
            CommentaryStyle.CASUAL: {
                "description": "随性解说风格",
                "tone": "轻松、亲切",
                "pace": "自然",
                "language": "口语化",
                "examples": ["说实话", "我觉得", "蛮有意思的是"]
            },
            CommentaryStyle.HUMOROUS: {
                "description": "幽默解说风格",
                "tone": "风趣、活泼",
                "pace": "轻快",
                "language": "幽默表达",
                "examples": ["笑死我了", "太搞笑了", "有意思的是"]
            },
            CommentaryStyle.DRAMATIC: {
                "description": "戏剧化解说风格",
                "tone": "夸张、戏剧性",
                "pace": "有起伏",
                "language": "戏剧性语言",
                "examples": ["震撼人心的是", "戏剧性的是", "令人震惊的是"]
            },
            CommentaryStyle.ROMANTIC: {
                "description": "浪漫解说风格",
                "tone": "温柔、浪漫",
                "pace": "缓慢",
                "language": "浪漫词汇",
                "examples": ["浪漫的是", "温馨的是", "令人心动的是"]
            }
        }
    
    def get_commentary_script(self, video_path: str, style: CommentaryStyle) -> Optional[CommentaryScript]:
        """Get cached commentary script"""
        cache_key = f"{video_path}_{style.value}"
        return self.generation_cache.get(cache_key)
    
    def clear_cache(self):
        """Clear commentary generation cache"""
        self.generation_cache.clear()
        self.logger.info("Commentary generation cache cleared")
    
    async def generate_multiple_styles(
        self,
        video_path: str,
        styles: List[CommentaryStyle],
        progress_callback: Optional[callable] = None
    ) -> Dict[CommentaryStyle, CommentaryScript]:
        """Generate commentary in multiple styles"""
        results = {}
        
        for i, style in enumerate(styles):
            if progress_callback:
                progress_callback(i / len(styles), f"生成{style.value}风格解说...")
            
            options = GenerationOptions(style=style)
            script = await self.generate_commentary(video_path, options)
            results[style] = script
        
        return results
    
    async def export_script(
        self,
        script: CommentaryScript,
        output_path: str,
        format: str = "json"
    ) -> None:
        """Export commentary script to file"""
        try:
            if format.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(script.__dict__, f, indent=2, ensure_ascii=False, default=str)
            
            elif format.lower() == "txt":
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {script.title}\n\n")
                    f.write(f"风格: {script.style.value}\n")
                    f.write(f"结构: {script.structure.value}\n")
                    f.write(f"总时长: {script.total_duration:.1f}秒\n\n")
                    f.write("## 解说内容\n\n")
                    
                    for i, segment in enumerate(script.segments):
                        f.write(f"### 片段 {i+1} ({segment.start_time:.1f}s - {segment.end_time:.1f}s)\n")
                        f.write(f"**情感**: {segment.emotion.value}\n")
                        f.write(f"**重要性**: {segment.importance:.2f}\n")
                        f.write(f"**内容**: {segment.content}\n\n")
            
            self.logger.info(f"Script exported to {output_path}")
        
        except Exception as e:
            self.handle_error(e, "export_script")
            raise