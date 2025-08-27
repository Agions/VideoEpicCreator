"""
Short drama content analysis system for VideoEpicCreator

This module provides specialized AI-driven analysis for short drama videos,
including content understanding, emotional analysis, and commentary generation.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime
import logging

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..ai.providers import AIManager, AIProvider, ContentType
from ..core.video_engine import VideoProcessor, Scene, TimelineSegment


class DramaGenre(Enum):
    """Short drama genres"""
    ROMANCE = "romance"        # 爱情
    COMEDY = "comedy"         # 喜剧
    DRAMA = "drama"           # 剧情
    ACTION = "action"         # 动作
    THRILLER = "thriller"     # 惊悚
    HORROR = "horror"         # 恐怖
    FANTASY = "fantasy"       # 奇幻
    SCIFI = "scifi"          # 科幻
    FAMILY = "family"         # 家庭
    YOUTH = "youth"           # 青春
    WORKPLACE = "workplace"   # 职场
    HISTORICAL = "historical" # 古装
    MODERN = "modern"         # 现代


class EmotionType(Enum):
    """Emotion types in drama content"""
    HAPPY = "happy"           # 开心
    SAD = "sad"              # 悲伤
    ANGRY = "angry"          # 愤怒
    SURPRISED = "surprised"  # 惊讶
    FEAR = "fear"            # 恐惧
    DISGUST = "disgust"      # 厌恶
    EXCITED = "excited"      # 兴奋
    ROMANTIC = "romantic"    # 浪漫
    NOSTALGIC = "nostalgic"  # 怀旧
    HOPEFUL = "hopeful"      # 希望
    CONFUSED = "confused"    # 困惑
    DETERMINED = "determined" # 坚定


class SceneType(Enum):
    """Types of scenes in short dramas"""
    INTRO = "intro"           # 开场
    CONFLICT = "conflict"     # 冲突
    CLIMAX = "climax"        # 高潮
    RESOLUTION = "resolution" # 解决
    OUTRO = "outro"          # 结尾
    TRANSITION = "transition" # 过渡
    FLASHBACK = "flashback"  # 闪回
    DIALOGUE = "dialogue"     # 对话
    ACTION = "action"        # 动作
    EMOTIONAL = "emotional"   # 情感
    COMEDIC = "comedic"      # 喜剧


@dataclass
class DramaContent:
    """Short drama content analysis result"""
    title: str
    genre: DramaGenre
    theme: str
    plot_summary: str
    main_characters: List[str]
    key_events: List[str]
    emotional_arc: List[Tuple[float, EmotionType, float]]  # (time, emotion, intensity)
    pacing_analysis: Dict[str, Any]
    target_audience: str
    content_rating: str


@dataclass
class SceneAnalysis:
    """Detailed scene analysis"""
    scene: Scene
    scene_type: SceneType
    emotion: EmotionType
    intensity: float  # 0.0 to 1.0
    importance: float  # 0.0 to 1.0
    description: str
    dialogue_summary: str
    visual_elements: List[str]
    audio_elements: List[str]
    character_actions: List[str]
    key_moments: List[str]


@dataclass
class CommentaryStrategy:
    """Strategy for generating commentary"""
    style: str  # "professional", "casual", "humorous", "dramatic", "romantic"
    tone: str   # "enthusiastic", "calm", "serious", "playful"
    pace: str   # "fast", "medium", "slow"
    focus: List[str]  # "plot", "emotion", "character", "visual", "audio"
    language_style: str  # "formal", "conversational", "poetic", "technical"
    audience_engagement: str  # "educational", "entertaining", "inspiring"


class DramaAnalyzer(BaseComponent[Dict[str, Any]]):
    """Short drama content analyzer using AI"""
    
    def __init__(
        self,
        ai_manager: AIManager,
        video_processor: VideoProcessor,
        config: Optional[ComponentConfig] = None
    ):
        super().__init__("drama_analyzer", config)
        self.ai_manager = ai_manager
        self.video_processor = video_processor
        self.content_cache: Dict[str, DramaContent] = {}
        
    async def initialize(self) -> bool:
        """Initialize drama analyzer"""
        try:
            self.logger.info("Initializing Drama Analyzer")
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialization")
            return False
    
    async def start(self) -> bool:
        """Start drama analyzer"""
        self.set_state(ComponentState.RUNNING)
        return True
    
    async def stop(self) -> bool:
        """Stop drama analyzer"""
        self.set_state(ComponentState.STOPPED)
        return True
    
    async def cleanup(self) -> bool:
        """Clean up resources"""
        self.content_cache.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get drama analyzer status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "cache_size": len(self.content_cache),
            "metrics": self.metrics.__dict__
        }
    
    async def analyze_drama_content(
        self,
        video_path: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> DramaContent:
        """Analyze short drama content comprehensively"""
        try:
            # Check cache first
            if video_path in self.content_cache:
                return self.content_cache[video_path]
            
            self.logger.info(f"Analyzing drama content: {video_path}")
            start_time = asyncio.get_event_loop().time()
            
            # Extract scenes from video
            scenes = await self.video_processor.extract_scenes(video_path)
            
            # Extract video frames for visual analysis
            with tempfile.TemporaryDirectory() as temp_dir:
                frame_paths = await self.video_processor.extract_frames(
                    video_path, temp_dir, interval=5.0, max_frames=20
                )
                
                # Generate content description from frames
                visual_description = await self._analyze_visual_content(frame_paths)
            
            # Create video content description for AI analysis
            video_description = await self._create_video_description(
                video_path, scenes, visual_description
            )
            
            # Use AI to analyze content
            content_analysis = await self._ai_analyze_content(video_description, additional_context)
            
            # Analyze emotional progression
            emotional_arc = await self._analyze_emotional_arc(scenes, content_analysis)
            
            # Create drama content object
            drama_content = DramaContent(
                title=content_analysis.get("title", "未命名短剧"),
                genre=DramaGenre(content_analysis.get("genre", "drama")),
                theme=content_analysis.get("theme", ""),
                plot_summary=content_analysis.get("plot_summary", ""),
                main_characters=content_analysis.get("main_characters", []),
                key_events=content_analysis.get("key_events", []),
                emotional_arc=emotional_arc,
                pacing_analysis=content_analysis.get("pacing_analysis", {}),
                target_audience=content_analysis.get("target_audience", "一般观众"),
                content_rating=content_analysis.get("content_rating", "G")
            )
            
            # Cache result
            self.content_cache[video_path] = drama_content
            
            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            self.update_metrics(processing_time)
            
            self.logger.info(f"Drama analysis completed in {processing_time:.2f}s")
            return drama_content
        
        except Exception as e:
            self.handle_error(e, "analyze_drama_content")
            raise
    
    async def analyze_scenes(
        self,
        video_path: str,
        drama_content: DramaContent
    ) -> List[SceneAnalysis]:
        """Analyze individual scenes in detail"""
        try:
            scenes = await self.video_processor.extract_scenes(video_path)
            scene_analyses = []
            
            for i, scene in enumerate(scenes):
                # Analyze scene using AI
                scene_analysis = await self._analyze_single_scene(
                    scene, i, drama_content
                )
                scene_analyses.append(scene_analysis)
            
            return scene_analyses
        
        except Exception as e:
            self.handle_error(e, "analyze_scenes")
            raise
    
    async def generate_commentary_strategy(
        self,
        drama_content: DramaContent,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> CommentaryStrategy:
        """Generate optimal commentary strategy based on content analysis"""
        try:
            # Analyze content characteristics
            content_characteristics = self._analyze_content_characteristics(drama_content)
            
            # Get user preferences or use defaults
            if user_preferences:
                style = user_preferences.get("style", self._determine_optimal_style(content_characteristics))
                tone = user_preferences.get("tone", self._determine_optimal_tone(content_characteristics))
                pace = user_preferences.get("pace", self._determine_optimal_pace(drama_content))
            else:
                style = self._determine_optimal_style(content_characteristics)
                tone = self._determine_optimal_tone(content_characteristics)
                pace = self._determine_optimal_pace(drama_content)
            
            # Determine focus areas
            focus = self._determine_focus_areas(drama_content, content_characteristics)
            
            # Determine language style
            language_style = self._determine_language_style(drama_content, user_preferences)
            
            # Determine audience engagement approach
            audience_engagement = self._determine_audience_engagement(drama_content)
            
            strategy = CommentaryStrategy(
                style=style,
                tone=tone,
                pace=pace,
                focus=focus,
                language_style=language_style,
                audience_engagement=audience_engagement
            )
            
            return strategy
        
        except Exception as e:
            self.handle_error(e, "generate_commentary_strategy")
            raise
    
    async def _analyze_visual_content(self, frame_paths: List[str]) -> str:
        """Analyze visual content from extracted frames"""
        try:
            # For now, create a simple description based on frame count
            # In a full implementation, this would use computer vision
            frame_count = len(frame_paths)
            
            description = f"视频包含{frame_count}个关键帧画面。"
            
            if frame_count > 0:
                description += "画面内容包括人物、场景和动作元素。"
            
            return description
        
        except Exception as e:
            self.logger.error(f"Visual content analysis failed: {e}")
            return "无法分析视频画面内容。"
    
    async def _create_video_description(
        self,
        video_path: str,
        scenes: List[Scene],
        visual_description: str
    ) -> str:
        """Create comprehensive video description for AI analysis"""
        try:
            video_info = await self.video_processor.get_video_info(video_path)
            
            description = f"""
视频基本信息：
- 时长：{video_info.duration:.1f}秒
- 分辨率：{video_info.width}x{video_info.height}
- 帧率：{video_info.fps}fps
- 场景数量：{len(scenes)}

场景信息：
"""
            
            for i, scene in enumerate(scenes[:5]):  # Limit to first 5 scenes
                description += f"场景{i+1}：{scene.start_time:.1f}s-{scene.end_time:.1f}s（{scene.duration:.1f}秒）\n"
            
            description += f"\n视觉内容分析：\n{visual_description}"
            
            return description
        
        except Exception as e:
            self.logger.error(f"Video description creation failed: {e}")
            return "无法创建视频描述。"
    
    async def _ai_analyze_content(
        self,
        video_description: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use AI to analyze video content"""
        try:
            prompt = f"""
请分析以下短剧视频内容，提供详细的分析报告：

视频信息：
{video_description}

分析要求：
1. 识别视频类型（爱情、喜剧、剧情、动作、惊悚、奇幻、科幻等）
2. 提取主题和核心故事线
3. 识别主要角色
4. 总结关键剧情事件
5. 分析节奏和结构
6. 评估目标观众群体
7. 提供内容评级建议

请以JSON格式返回分析结果，包含以下字段：
- title: 视频标题
- genre: 类型
- theme: 主题
- plot_summary: 剧情摘要
- main_characters: 主要角色列表
- key_events: 关键事件列表
- pacing_analysis: 节奏分析
- target_audience: 目标观众
- content_rating: 内容评级
"""
            
            if additional_context:
                prompt += f"\n额外上下文信息：{json.dumps(additional_context, ensure_ascii=False)}"
            
            response = await self.ai_manager.generate_content(
                prompt=prompt,
                content_type=ContentType.ANALYSIS
            )
            
            if response.error:
                raise Exception(f"AI analysis failed: {response.error}")
            
            # Parse JSON response
            try:
                content_data = json.loads(response.content)
                return content_data
            except json.JSONDecodeError:
                # Fallback to basic analysis
                return {
                    "title": "未命名短剧",
                    "genre": "drama",
                    "theme": "待分析",
                    "plot_summary": response.content,
                    "main_characters": [],
                    "key_events": [],
                    "pacing_analysis": {},
                    "target_audience": "一般观众",
                    "content_rating": "G"
                }
        
        except Exception as e:
            self.logger.error(f"AI content analysis failed: {e}")
            raise
    
    async def _analyze_emotional_arc(
        self,
        scenes: List[Scene],
        content_analysis: Dict[str, Any]
    ) -> List[Tuple[float, EmotionType, float]]:
        """Analyze emotional progression throughout the video"""
        try:
            emotional_arc = []
            
            # Basic emotional arc based on scene position and content
            for i, scene in enumerate(scenes):
                # Determine emotion based on scene position
                if i == 0:
                    emotion = EmotionType.HOPEFUL  # Beginning
                elif i == len(scenes) - 1:
                    emotion = EmotionType.HOPEFUL  # Ending
                elif i < len(scenes) * 0.3:
                    emotion = EmotionType.EXCITED  # Development
                elif i < len(scenes) * 0.7:
                    emotion = EmotionType.ANGRY if "conflict" in content_analysis.get("genre", "") else EmotionType.CONFUSED
                else:
                    emotion = EmotionType.HOPEFUL  # Resolution
                
                # Intensity varies by scene importance
                intensity = min(1.0, scene.importance * 1.5)
                
                emotional_arc.append((scene.start_time, emotion, intensity))
            
            return emotional_arc
        
        except Exception as e:
            self.logger.error(f"Emotional arc analysis failed: {e}")
            return []
    
    async def _analyze_single_scene(
        self,
        scene: Scene,
        scene_index: int,
        drama_content: DramaContent
    ) -> SceneAnalysis:
        """Analyze a single scene in detail"""
        try:
            # Determine scene type based on position and content
            scene_type = self._determine_scene_type(scene_index, len(drama_content.key_events))
            
            # Determine emotion based on emotional arc
            emotion = self._get_dominant_emotion(drama_content.emotional_arc, scene)
            
            # Calculate importance based on duration and position
            importance = min(1.0, (scene.duration / 10.0) * (1.0 + abs(scene_index - len(drama_content.key_events)/2) / len(drama_content.key_events)))
            
            # Generate scene description
            description = f"场景{scene_index+1}：{scene.duration:.1f}秒的{scene_type.value}场景"
            
            return SceneAnalysis(
                scene=scene,
                scene_type=scene_type,
                emotion=emotion,
                intensity=min(1.0, importance),
                importance=importance,
                description=description,
                dialogue_summary="",
                visual_elements=[],
                audio_elements=[],
                character_actions=[],
                key_moments=[]
            )
        
        except Exception as e:
            self.logger.error(f"Scene analysis failed: {e}")
            raise
    
    def _analyze_content_characteristics(self, drama_content: DramaContent) -> Dict[str, Any]:
        """Analyze content characteristics for strategy generation"""
        return {
            "genre": drama_content.genre.value,
            "emotional_complexity": len(set(emotion for _, emotion, _ in drama_content.emotional_arc)),
            "pace_complexity": len(drama_content.key_events) / max(drama_content.plot_summary.count("。"), 1),
            "character_count": len(drama_content.main_characters),
            "target_audience": drama_content.target_audience
        }
    
    def _determine_optimal_style(self, characteristics: Dict[str, Any]) -> str:
        """Determine optimal commentary style"""
        genre = characteristics.get("genre", "drama")
        
        style_map = {
            "romance": "romantic",
            "comedy": "humorous",
            "drama": "dramatic",
            "action": "professional",
            "thriller": "dramatic",
            "horror": "dramatic",
            "fantasy": "dramatic",
            "scifi": "professional",
            "family": "casual",
            "youth": "casual"
        }
        
        return style_map.get(genre, "professional")
    
    def _determine_optimal_tone(self, characteristics: Dict[str, Any]) -> str:
        """Determine optimal commentary tone"""
        emotional_complexity = characteristics.get("emotional_complexity", 1)
        
        if emotional_complexity > 3:
            return "enthusiastic"
        elif emotional_complexity > 1:
            return "calm"
        else:
            return "serious"
    
    def _determine_optimal_pace(self, drama_content: DramaContent) -> str:
        """Determine optimal commentary pace"""
        avg_scene_duration = np.mean([scene.duration for scene in drama_content.emotional_arc]) if drama_content.emotional_arc else 5.0
        
        if avg_scene_duration < 3.0:
            return "fast"
        elif avg_scene_duration < 8.0:
            return "medium"
        else:
            return "slow"
    
    def _determine_focus_areas(self, drama_content: DramaContent, characteristics: Dict[str, Any]) -> List[str]:
        """Determine focus areas for commentary"""
        focus = []
        
        # Always include plot
        focus.append("plot")
        
        # Add emotion if complex emotional arc
        if characteristics.get("emotional_complexity", 0) > 2:
            focus.append("emotion")
        
        # Add character if multiple characters
        if characteristics.get("character_count", 0) > 1:
            focus.append("character")
        
        # Add visual for visual-heavy genres
        if characteristics.get("genre") in ["action", "fantasy", "scifi"]:
            focus.append("visual")
        
        return focus
    
    def _determine_language_style(self, drama_content: DramaContent, user_preferences: Optional[Dict[str, Any]]) -> str:
        """Determine language style"""
        if user_preferences and "language_style" in user_preferences:
            return user_preferences["language_style"]
        
        # Default based on genre
        genre_map = {
            "romance": "poetic",
            "comedy": "conversational",
            "drama": "dramatic",
            "action": "technical",
            "family": "conversational"
        }
        
        return genre_map.get(drama_content.genre.value, "conversational")
    
    def _determine_audience_engagement(self, drama_content: DramaContent) -> str:
        """Determine audience engagement approach"""
        if "年轻" in drama_content.target_audience or drama_content.genre == DramaGenre.COMEDY:
            return "entertaining"
        elif drama_content.genre in [DramaGenre.DRAMA, DramaGenre.HISTORICAL]:
            return "educational"
        else:
            return "inspiring"
    
    def _determine_scene_type(self, scene_index: int, total_events: int) -> SceneType:
        """Determine scene type based on position"""
        if scene_index == 0:
            return SceneType.INTRO
        elif scene_index == total_events - 1:
            return SceneType.OUTRO
        elif scene_index < total_events * 0.3:
            return SceneType.TRANSITION
        elif scene_index < total_events * 0.7:
            return SceneType.CONFLICT
        else:
            return SceneType.RESOLUTION
    
    def _get_dominant_emotion(
        self,
        emotional_arc: List[Tuple[float, EmotionType, float]],
        scene: Scene
    ) -> EmotionType:
        """Get dominant emotion for a scene"""
        scene_emotions = [
            emotion for time, emotion, intensity in emotional_arc
            if scene.start_time <= time <= scene.end_time
        ]
        
        if scene_emotions:
            return scene_emotions[0]  # First emotion in scene
        else:
            return EmotionType.NEUTRAL if hasattr(EmotionType, 'NEUTRAL') else EmotionType.HOPEFUL
    
    def get_content_analysis(self, video_path: str) -> Optional[DramaContent]:
        """Get cached content analysis"""
        return self.content_cache.get(video_path)
    
    def clear_cache(self):
        """Clear content analysis cache"""
        self.content_cache.clear()
        self.logger.info("Content analysis cache cleared")
    
    async def generate_content_insights(
        self,
        drama_content: DramaContent,
        scene_analyses: List[SceneAnalysis]
    ) -> Dict[str, Any]:
        """Generate insights from content analysis"""
        try:
            insights = {
                "content_strengths": [],
                "improvement_suggestions": [],
                "audience_reactions": [],
                "engagement_opportunities": []
            }
            
            # Analyze content strengths
            if len(drama_content.emotional_arc) > 5:
                insights["content_strengths"].append("情感层次丰富，能够引起观众共鸣")
            
            if len(set(scene.scene_type for scene in scene_analyses)) > 3:
                insights["content_strengths"].append("场景类型多样，内容结构完整")
            
            # Generate improvement suggestions
            if len(drama_content.main_characters) < 2:
                insights["improvement_suggestions"].append("可以增加角色互动以丰富内容")
            
            if np.mean([scene.duration for scene in scene_analyses]) < 3.0:
                insights["improvement_suggestions"].append("节奏较快，可以适当延长关键场景")
            
            # Predict audience reactions
            if drama_content.genre == DramaGenre.COMEDY:
                insights["audience_reactions"].append("观众可能会在幽默场景产生积极反应")
            
            if any(emotion == EmotionType.SAD for _, emotion, _ in drama_content.emotional_arc):
                insights["audience_reactions"].append("情感场景可能会引起观众共鸣")
            
            # Identify engagement opportunities
            if len(drama_content.key_events) > 3:
                insights["engagement_opportunities"].append("可以在关键剧情转折点加强观众互动")
            
            return insights
        
        except Exception as e:
            self.handle_error(e, "generate_content_insights")
            return {}


# Import tempfile for temporary directory creation
import tempfile