"""
AI Content Generator Factory

This module provides a factory pattern for creating AI content generators
with support for different content types, providers, and generation strategies.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from .providers import AIProvider, AIRequest, AIResponse, ContentType
from .enhanced_ai_manager import EnhancedAIManager, LoadBalancingStrategy
from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..core.events import EventSystem, get_event_system
from ..config.settings import Settings


class GeneratorType(Enum):
    """Types of content generators"""
    COMMENTARY = "commentary"
    NARRATIVE = "narrative"
    HIGHLIGHT = "highlight"
    MONOLOGUE = "monologue"
    SUBTITLE = "subtitle"
    ANALYSIS = "analysis"
    DIALOGUE = "dialogue"
    DESCRIPTION = "description"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


class GenerationStrategy(Enum):
    """Content generation strategies"""
    SINGLE_SHOT = "single_shot"           # Generate in one request
    CHUNKED = "chunked"                  # Generate in chunks
    ITERATIVE = "iterative"              # Generate with iterative refinement
    HIERARCHICAL = "hierarchical"        # Generate with hierarchical structure
    COLLABORATIVE = "collaborative"      # Generate using multiple providers


@dataclass
class GenerationRequest:
    """Content generation request"""
    content_type: ContentType
    generator_type: GeneratorType
    input_data: Dict[str, Any]
    options: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    constraints: List[str] = field(default_factory=list)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def get_input_text(self) -> str:
        """Get the main input text from input_data"""
        return self.input_data.get("text", "")


@dataclass
class GenerationResult:
    """Content generation result"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    generation_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    provider_used: Optional[AIProvider] = None
    model_used: Optional[str] = None
    iterations: int = 1
    warnings: List[str] = field(default_factory=list)


class ContentGenerator(ABC):
    """Abstract base class for content generators"""
    
    def __init__(self, generator_type: GeneratorType, ai_manager: EnhancedAIManager):
        self.generator_type = generator_type
        self.ai_manager = ai_manager
        self.logger = logging.getLogger(f"generator.{generator_type.value}")
        self.event_system = get_event_system()
    
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate content based on request"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate content as a stream"""
        pass
    
    @abstractmethod
    def validate_request(self, request: GenerationRequest) -> List[str]:
        """Validate generation request"""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate generation cost"""
        pass
    
    def preprocess_input(self, request: GenerationRequest) -> GenerationRequest:
        """Preprocess input data"""
        # Default implementation - can be overridden
        return request
    
    def postprocess_output(self, content: str, request: GenerationRequest) -> str:
        """Postprocess generated content"""
        # Default implementation - can be overridden
        return content


class CommentaryGenerator(ContentGenerator):
    """Generator for video commentary"""
    
    def __init__(self, ai_manager: EnhancedAIManager):
        super().__init__(GeneratorType.COMMENTARY, ai_manager)
        self.style_templates = self._load_style_templates()
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate video commentary"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate request
            validation_errors = self.validate_request(request)
            if validation_errors:
                return GenerationResult(
                    content="",
                    warnings=validation_errors,
                    generation_time=0.0
                )
            
            # Preprocess input
            processed_request = self.preprocess_input(request)
            
            # Build prompt
            prompt = self._build_commentary_prompt(processed_request)
            
            # Generate content
            response = await self.ai_manager.generate_content_enhanced(
                prompt=prompt,
                content_type=ContentType.COMMENTARY,
                use_cache=True,
                **request.options
            )
            
            # Postprocess output
            content = self.postprocess_output(response.content, processed_request)
            
            # Calculate metrics
            generation_time = asyncio.get_event_loop().time() - start_time
            
            result = GenerationResult(
                content=content,
                metadata={
                    "style": request.options.get("style", "professional"),
                    "tone": request.options.get("tone", "neutral"),
                    "target_audience": request.options.get("target_audience", "general")
                },
                generation_time=generation_time,
                tokens_used=response.tokens_used,
                cost=response.tokens_used * 0.002,  # Estimate cost
                provider_used=response.provider,
                model_used=response.model,
                quality_score=self._calculate_quality_score(content, request)
            )
            
            # Emit event
            self.event_system.emit("commentary_generated", {
                "request_id": id(request),
                "generation_time": generation_time,
                "quality_score": result.quality_score
            })
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error generating commentary: {e}")
            return GenerationResult(
                content="",
                warnings=[f"Generation failed: {str(e)}"],
                generation_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate commentary as a stream"""
        # Validate request
        validation_errors = self.validate_request(request)
        if validation_errors:
            yield f"Error: {', '.join(validation_errors)}"
            return
        
        # Preprocess input
        processed_request = self.preprocess_input(request)
        
        # Build prompt
        prompt = self._build_commentary_prompt(processed_request)
        
        # Generate streaming content
        async for chunk in self.ai_manager.generate_stream_enhanced(
            prompt=prompt,
            content_type=ContentType.COMMENTARY,
            **request.options
        ):
            yield chunk
    
    def validate_request(self, request: GenerationRequest) -> List[str]:
        """Validate commentary generation request"""
        errors = []
        
        # Check required fields
        if "video_description" not in request.input_data:
            errors.append("video_description is required")
        
        if "duration" not in request.input_data:
            errors.append("duration is required")
        
        # Check constraints
        max_length = request.constraints.get("max_length", 1000)
        if max_length > 5000:
            errors.append("max_length cannot exceed 5000 characters")
        
        return errors
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate commentary generation cost"""
        # Estimate based on input size and output requirements
        input_tokens = len(request.get_input_text()) / 4  # Rough estimate
        output_tokens = request.options.get("max_tokens", 500)
        
        # Use average cost per token
        return (input_tokens + output_tokens) * 0.002
    
    def _build_commentary_prompt(self, request: GenerationRequest) -> str:
        """Build commentary generation prompt"""
        video_description = request.input_data.get("video_description", "")
        duration = request.input_data.get("duration", 60)
        style = request.options.get("style", "professional")
        tone = request.options.get("tone", "neutral")
        
        style_template = self.style_templates.get(style, {})
        
        prompt = f"""
你是一个专业的视频解说专家，擅长为短视频和短剧创作引人入胜的解说词。

视频信息：
- 描述：{video_description}
- 时长：{duration}秒
- 风格：{style_template.get('description', style)}
- 语气：{tone}

解说要求：
1. 语言简洁有力，富有节奏感
2. 突出视频的亮点和情感
3. 适合短视频平台的风格
4. 控制在适当的长度范围内
5. 能够吸引观众的注意力
6. {style_template.get('requirements', '')}

请为这个视频创作精彩的解说词：
"""
        
        return prompt
    
    def _calculate_quality_score(self, content: str, request: GenerationRequest) -> float:
        """Calculate quality score for generated commentary"""
        score = 0.0
        
        # Length appropriateness
        if 100 <= len(content) <= 1000:
            score += 0.3
        
        # Keyword presence
        keywords = ["精彩", "亮点", "情感", "吸引", "观众"]
        keyword_count = sum(1 for keyword in keywords if keyword in content)
        score += min(0.3, keyword_count * 0.1)
        
        # Structure and flow
        if "。" in content and "，" in content:
            score += 0.2
        
        # Engagement indicators
        engagement_words = ["大家", "我们", "一起", "来看", "感受"]
        engagement_count = sum(1 for word in engagement_words if word in content)
        score += min(0.2, engagement_count * 0.05)
        
        return min(1.0, score)
    
    def _load_style_templates(self) -> Dict[str, Dict[str, str]]:
        """Load commentary style templates"""
        return {
            "professional": {
                "description": "专业解说风格",
                "requirements": "使用专业术语，保持客观中立的语气",
                "tone": "正式、客观"
            },
            "casual": {
                "description": "随性解说风格",
                "requirements": "语言轻松自然，像朋友聊天一样",
                "tone": "轻松、亲切"
            },
            "humorous": {
                "description": "幽默解说风格",
                "requirements": "加入幽默元素，让观众感到愉快",
                "tone": "风趣、活泼"
            },
            "dramatic": {
                "description": "戏剧化解说风格",
                "requirements": "使用夸张的表达，增强戏剧效果",
                "tone": "夸张、戏剧性"
            }
        }


class NarrativeGenerator(ContentGenerator):
    """Generator for narrative content"""
    
    def __init__(self, ai_manager: EnhancedAIManager):
        super().__init__(GeneratorType.NARRATIVE, ai_manager)
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate narrative content"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate request
            validation_errors = self.validate_request(request)
            if validation_errors:
                return GenerationResult(
                    content="",
                    warnings=validation_errors,
                    generation_time=0.0
                )
            
            # Preprocess input
            processed_request = self.preprocess_input(request)
            
            # Build prompt
            prompt = self._build_narrative_prompt(processed_request)
            
            # Generate content
            response = await self.ai_manager.generate_content_enhanced(
                prompt=prompt,
                content_type=ContentType.NARRATIVE,
                use_cache=True,
                **request.options
            )
            
            # Postprocess output
            content = self.postprocess_output(response.content, processed_request)
            
            # Calculate metrics
            generation_time = asyncio.get_event_loop().time() - start_time
            
            result = GenerationResult(
                content=content,
                metadata={
                    "narrative_type": request.options.get("narrative_type", "linear"),
                    "perspective": request.options.get("perspective", "third_person")
                },
                generation_time=generation_time,
                tokens_used=response.tokens_used,
                cost=response.tokens_used * 0.002,
                provider_used=response.provider,
                model_used=response.model,
                quality_score=self._calculate_quality_score(content, request)
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error generating narrative: {e}")
            return GenerationResult(
                content="",
                warnings=[f"Generation failed: {str(e)}"],
                generation_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate narrative as a stream"""
        # Similar implementation to CommentaryGenerator
        pass
    
    def validate_request(self, request: GenerationRequest) -> List[str]:
        """Validate narrative generation request"""
        errors = []
        
        if "story_elements" not in request.input_data:
            errors.append("story_elements is required")
        
        return errors
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate narrative generation cost"""
        input_tokens = len(request.get_input_text()) / 4
        output_tokens = request.options.get("max_tokens", 800)
        return (input_tokens + output_tokens) * 0.002
    
    def _build_narrative_prompt(self, request: GenerationRequest) -> str:
        """Build narrative generation prompt"""
        story_elements = request.input_data.get("story_elements", "")
        narrative_type = request.options.get("narrative_type", "linear")
        
        prompt = f"""
你是一个优秀的叙事创作者，擅长为视频内容创作连贯的叙事文本。

故事元素：{story_elements}
叙事类型：{narrative_type}

请创作一个连贯、有逻辑性的叙事文本，要求：
1. 故事线清晰，逻辑连贯
2. 情感表达丰富
3. 语言优美，具有文学性
4. 符合视频的节奏和风格
5. 能够引起观众共鸣

请开始创作：
"""
        
        return prompt
    
    def _calculate_quality_score(self, content: str, request: GenerationRequest) -> float:
        """Calculate quality score for narrative"""
        score = 0.0
        
        # Narrative structure
        if "开始" in content or "开头" in content:
            score += 0.2
        
        if "发展" in content or "中间" in content:
            score += 0.2
        
        if "结束" in content or "结尾" in content:
            score += 0.2
        
        # Emotional content
        emotional_words = ["情感", "感受", "心情", "情绪"]
        emotional_count = sum(1 for word in emotional_words if word in content)
        score += min(0.2, emotional_count * 0.05)
        
        # Coherence
        if "并且" in content or "然后" in content or "因此" in content:
            score += 0.2
        
        return min(1.0, score)


class HighlightGenerator(ContentGenerator):
    """Generator for highlight descriptions"""
    
    def __init__(self, ai_manager: EnhancedAIManager):
        super().__init__(GeneratorType.HIGHLIGHT, ai_manager)
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate highlight description"""
        # Implementation similar to other generators
        pass
    
    def validate_request(self, request: GenerationRequest) -> List[str]:
        """Validate highlight generation request"""
        errors = []
        
        if "highlight_moments" not in request.input_data:
            errors.append("highlight_moments is required")
        
        return errors
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate highlight generation cost"""
        return len(request.get_input_text()) / 4 * 0.002


class ContentGeneratorFactory:
    """Factory for creating content generators"""
    
    def __init__(self, ai_manager: EnhancedAIManager):
        self.ai_manager = ai_manager
        self._generators: Dict[GeneratorType, Type[ContentGenerator]] = {
            GeneratorType.COMMENTARY: CommentaryGenerator,
            GeneratorType.NARRATIVE: NarrativeGenerator,
            GeneratorType.HIGHLIGHT: HighlightGenerator,
        }
        self._instances: Dict[GeneratorType, ContentGenerator] = {}
        self.logger = logging.getLogger("content_generator_factory")
    
    def register_generator(self, generator_type: GeneratorType, generator_class: Type[ContentGenerator]):
        """Register a new generator type"""
        self._generators[generator_type] = generator_class
        self.logger.info(f"Registered generator: {generator_type.value}")
    
    def create_generator(self, generator_type: GeneratorType) -> ContentGenerator:
        """Create a generator instance"""
        if generator_type not in self._generators:
            raise ValueError(f"Unknown generator type: {generator_type.value}")
        
        # Return cached instance if available
        if generator_type in self._instances:
            return self._instances[generator_type]
        
        # Create new instance
        generator_class = self._generators[generator_type]
        instance = generator_class(self.ai_manager)
        
        # Cache instance
        self._instances[generator_type] = instance
        
        return instance
    
    def get_available_generators(self) -> List[GeneratorType]:
        """Get list of available generator types"""
        return list(self._generators.keys())
    
    def get_generator_info(self, generator_type: GeneratorType) -> Dict[str, Any]:
        """Get information about a generator type"""
        if generator_type not in self._generators:
            return {}
        
        generator_class = self._generators[generator_type]
        return {
            "type": generator_type.value,
            "class": generator_class.__name__,
            "description": generator_class.__doc__ or "",
            "supported_content_types": self._get_supported_content_types(generator_class)
        }
    
    def _get_supported_content_types(self, generator_class: Type[ContentGenerator]) -> List[ContentType]:
        """Get supported content types for a generator class"""
        # This could be determined by inspecting the class or using metadata
        return [ContentType.COMMENTARY]  # Default


class ContentGenerationOrchestrator(BaseComponent[Dict[str, Any]]):
    """Orchestrator for complex content generation workflows"""
    
    def __init__(self, ai_manager: EnhancedAIManager, config: Optional[ComponentConfig] = None):
        super().__init__("content_generation_orchestrator", config)
        self.ai_manager = ai_manager
        self.factory = ContentGeneratorFactory(ai_manager)
        self._active_generations = {}
        self.logger = logging.getLogger("content_generation_orchestrator")
    
    async def initialize(self) -> bool:
        """Initialize the orchestrator"""
        try:
            self.logger.info("Initializing Content Generation Orchestrator")
            
            # Register default generators
            self._register_default_generators()
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            return False
    
    async def start(self) -> bool:
        """Start the orchestrator"""
        self.set_state(ComponentState.RUNNING)
        return True
    
    async def stop(self) -> bool:
        """Stop the orchestrator"""
        # Cancel active generations
        for generation_id in list(self._active_generations.keys()):
            await self.cancel_generation(generation_id)
        
        self.set_state(ComponentState.STOPPED)
        return True
    
    async def cleanup(self) -> bool:
        """Clean up orchestrator resources"""
        self._active_generations.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "active_generations": len(self._active_generations),
            "available_generators": [gt.value for gt in self.factory.get_available_generators()],
            "metrics": self.metrics.__dict__
        }
    
    def _register_default_generators(self):
        """Register default generators"""
        # Generators are already registered in the factory
        pass
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResult:
        """Generate content using appropriate generator"""
        generation_id = id(request)
        self._active_generations[generation_id] = request
        
        try:
            # Get generator
            generator = self.factory.create_generator(request.generator_type)
            
            # Validate request
            validation_errors = generator.validate_request(request)
            if validation_errors:
                return GenerationResult(
                    content="",
                    warnings=validation_errors,
                    generation_time=0.0
                )
            
            # Generate content
            result = await generator.generate(request)
            
            # Store result
            self._active_generations[generation_id] = result
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return GenerationResult(
                content="",
                warnings=[f"Generation failed: {str(e)}"],
                generation_time=0.0
            )
        
        finally:
            if generation_id in self._active_generations:
                del self._active_generations[generation_id]
    
    async def generate_content_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate content as a stream"""
        generation_id = id(request)
        self._active_generations[generation_id] = request
        
        try:
            # Get generator
            generator = self.factory.create_generator(request.generator_type)
            
            # Validate request
            validation_errors = generator.validate_request(request)
            if validation_errors:
                yield f"Error: {', '.join(validation_errors)}"
                return
            
            # Generate streaming content
            async for chunk in generator.generate_stream(request):
                yield chunk
        
        except Exception as e:
            self.logger.error(f"Error generating streaming content: {e}")
            yield f"Error: {str(e)}"
        
        finally:
            if generation_id in self._active_generations:
                del self._active_generations[generation_id]
    
    async def generate_batch(self, requests: List[GenerationRequest]) -> List[GenerationResult]:
        """Generate content for multiple requests"""
        tasks = []
        
        for request in requests:
            task = asyncio.create_task(self.generate_content(request))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(GenerationResult(
                    content="",
                    warnings=[f"Generation failed: {str(result)}"],
                    generation_time=0.0
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def cancel_generation(self, generation_id: int):
        """Cancel an active generation"""
        if generation_id in self._active_generations:
            # This would need to be implemented with proper cancellation support
            del self._active_generations[generation_id]
            self.logger.info(f"Cancelled generation: {generation_id}")
    
    def get_generation_status(self, generation_id: int) -> Optional[Dict[str, Any]]:
        """Get status of an active generation"""
        if generation_id in self._active_generations:
            request = self._active_generations[generation_id]
            return {
                "generation_id": generation_id,
                "generator_type": request.generator_type.value,
                "content_type": request.content_type.value,
                "status": "active"
            }
        return None
    
    def estimate_batch_cost(self, requests: List[GenerationRequest]) -> float:
        """Estimate total cost for batch generation"""
        total_cost = 0.0
        
        for request in requests:
            try:
                generator = self.factory.create_generator(request.generator_type)
                cost = generator.estimate_cost(request)
                total_cost += cost
            except Exception:
                # Skip invalid requests
                continue
        
        return total_cost
    
    def get_generator_recommendations(self, request: GenerationRequest) -> List[GeneratorType]:
        """Get recommended generator types for a request"""
        recommendations = []
        
        # Simple recommendation logic
        if "video_description" in request.input_data:
            recommendations.append(GeneratorType.COMMENTARY)
        
        if "story_elements" in request.input_data:
            recommendations.append(GeneratorType.NARRATIVE)
        
        if "highlight_moments" in request.input_data:
            recommendations.append(GeneratorType.HIGHLIGHT)
        
        return recommendations