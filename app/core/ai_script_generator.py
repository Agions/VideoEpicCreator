#!/usr/bin/env python3
"""
AI视频脚本生成器
专门用于生成高质量的视频脚本内容
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re
import asyncio

from .ai_generator import AIContentGenerator, GenerationRequest, ContentType, AIProvider
from ..utils.config import Config
from ..utils.file_utils import FileUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScriptStyle(Enum):
    """脚本风格枚举"""
    NARRATIVE = "narrative"        # 叙事风格
    EDUCATIONAL = "educational"    # 教育风格
    ENTERTAINING = "entertaining"  # 娱乐风格
    PROMOTIONAL = "promotional"    # 推广风格
    DOCUMENTARY = "documentary"    # 纪录风格
    VLOG = "vlog"                  # Vlog风格
    TUTORIAL = "tutorial"          # 教程风格
    NEWS = "news"                  # 新闻风格

class VideoType(Enum):
    """视频类型枚举"""
    SHORT_VIDEO = "short_video"        # 短视频
    TUTORIAL = "tutorial"             # 教程视频
    PRODUCT_REVIEW = "product_review" # 产品评测
    DOCUMENTARY = "documentary"       # 纪录片
    INTERVIEW = "interview"           # 采访视频
    PRESENTATION = "presentation"     # 演示视频
    STORYTELLING = "storytelling"     # 故事讲述
    LIVESTREAM = "livestream"         # 直播内容

class ScriptSection(Enum):
    """脚本部分枚举"""
    HOOK = "hook"                     # 开场钩子
    INTRODUCTION = "introduction"     # 介绍部分
    MAIN_CONTENT = "main_content"     # 主要内容
    CONCLUSION = "conclusion"         # 结尾部分
    CALL_TO_ACTION = "call_to_action" # 行动号召

@dataclass
class ScriptElement:
    """脚本元素"""
    section: ScriptSection
    content: str
    duration: float
    visual_suggestions: List[str] = None
    audio_suggestions: List[str] = None
    timing_notes: str = ""
    
    def __post_init__(self):
        if self.visual_suggestions is None:
            self.visual_suggestions = []
        if self.audio_suggestions is None:
            self.audio_suggestions = []

@dataclass
class VideoScript:
    """视频脚本"""
    script_id: str
    title: str
    description: str
    target_audience: str
    video_type: VideoType
    script_style: ScriptStyle
    estimated_duration: float
    elements: List[ScriptElement]
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ScriptGenerationRequest:
    """脚本生成请求"""
    topic: str
    video_type: VideoType
    script_style: ScriptStyle
    target_audience: str
    duration: float
    key_points: List[str] = None
    tone: str = "professional"
    language: str = "zh-CN"
    include_visual_suggestions: bool = True
    include_audio_suggestions: bool = True
    custom_requirements: str = ""
    
    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []

class AIScriptGenerator:
    """AI视频脚本生成器"""
    
    def __init__(self, ai_generator: AIContentGenerator, config: Config):
        self.ai_generator = ai_generator
        self.config = config
        self.file_utils = FileUtils()
        
        # 脚本模板
        self.script_templates = self._load_script_templates()
        
        # 生成统计
        self.generation_stats = {
            'total_scripts': 0,
            'successful_scripts': 0,
            'failed_scripts': 0,
            'average_generation_time': 0,
            'style_distribution': {}
        }
    
    async def generate_script(self, request: ScriptGenerationRequest) -> Optional[VideoScript]:
        """生成视频脚本"""
        try:
            logger.info(f"开始生成脚本: {request.topic}")
            
            # 更新统计
            self.generation_stats['total_scripts'] += 1
            
            # 构建生成请求
            generation_request = self._build_generation_request(request)
            
            # 提交生成任务
            task_id = await self.ai_generator.generate_content(generation_request)
            
            # 等待生成完成
            script_data = await self._wait_for_generation(task_id)
            
            if not script_data:
                self.generation_stats['failed_scripts'] += 1
                return None
            
            # 解析生成的脚本
            video_script = self._parse_generated_script(script_data, request)
            
            if video_script:
                self.generation_stats['successful_scripts'] += 1
                self._update_style_stats(request.script_style)
                logger.info(f"脚本生成成功: {video_script.title}")
                return video_script
            else:
                self.generation_stats['failed_scripts'] += 1
                logger.error("脚本解析失败")
                return None
                
        except Exception as e:
            self.generation_stats['failed_scripts'] += 1
            logger.error(f"生成脚本时出错: {e}")
            return None
    
    def _build_generation_request(self, request: ScriptGenerationRequest) -> GenerationRequest:
        """构建AI生成请求"""
        # 构建详细的提示词
        prompt = self._build_script_prompt(request)
        
        # 获取默认参数
        default_params = self.ai_generator.get_default_parameters(ContentType.SCRIPT)
        
        # 调整参数以适应脚本生成
        default_params.update({
            'temperature': 0.8,  # 稍高的创造性
            'max_tokens': 3000,  # 脚本需要更多token
            'top_p': 0.9
        })
        
        return GenerationRequest(
            request_id=f"script_{self.file_utils.get_timestamp()}",
            content_type=ContentType.SCRIPT,
            prompt=prompt,
            provider=AIProvider.OPENAI,  # 默认使用OpenAI
            model="gpt-3.5-turbo",
            parameters=default_params,
            context={
                'video_topic': request.topic,
                'target_audience': request.target_audience,
                'video_type': request.video_type.value,
                'script_style': request.script_style.value,
                'duration': f"{request.duration}秒",
                'tone': request.tone,
                'language': request.language
            },
            priority=1
        )
    
    def _build_script_prompt(self, request: ScriptGenerationRequest) -> str:
        """构建脚本生成提示词"""
        prompt = f"""
请为一个视频创建完整的脚本。

视频主题: {request.topic}
视频类型: {request.video_type.value}
脚本风格: {request.script_style.value}
目标受众: {request.target_audience}
视频时长: {request.duration}秒
语言: {request.language}
语调: {request.tone}
"""
        
        if request.key_points:
            prompt += f"\n关键要点:\n" + "\n".join(f"- {point}" for point in request.key_points)
        
        if request.custom_requirements:
            prompt += f"\n特殊要求:\n{request.custom_requirements}"
        
        prompt += f"""
请按照以下结构生成脚本:

1. 标题: 创建一个吸引人的标题
2. 描述: 简要描述视频内容
3. 标签: 生成3-5个相关标签

脚本结构:
- 开场钩子 (10-15秒): 吸引观众注意力
- 介绍部分 (15-30秒): 介绍主题和背景
- 主要内容 (根据时长分配): 详细阐述主题
- 结尾部分 (10-20秒): 总结要点
- 行动号召 (5-10秒): 引导观众行动

"""
        
        if request.include_visual_suggestions:
            prompt += "为每个部分提供视觉建议。\n"
        
        if request.include_audio_suggestions:
            prompt += "为每个部分提供音频建议。\n"
        
        prompt += """
请以JSON格式返回结果，包含以下字段:
{
  "title": "视频标题",
  "description": "视频描述",
  "tags": ["标签1", "标签2", ...],
  "sections": [
    {
      "section": "hook",
      "content": "开场钩子内容",
      "duration": 15,
      "visual_suggestions": ["视觉建议1", "视觉建议2"],
      "audio_suggestions": ["音频建议1", "音频建议2"],
      "timing_notes": "时间节点说明"
    },
    ...
  ]
}
"""
        
        return prompt
    
    async def _wait_for_generation(self, task_id: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """等待生成完成"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            result = await self.ai_generator.get_generation_status(task_id)
            
            if result and result.status.value in ['completed', 'failed']:
                if result.status.value == 'completed':
                    try:
                        return json.loads(result.content)
                    except json.JSONDecodeError:
                        logger.error("生成结果JSON解析失败")
                        return None
                else:
                    logger.error(f"生成失败: {result.error}")
                    return None
            
            await asyncio.sleep(1)
        
        logger.error("生成超时")
        return None
    
    def _parse_generated_script(self, script_data: Dict[str, Any], request: ScriptGenerationRequest) -> Optional[VideoScript]:
        """解析生成的脚本数据"""
        try:
            # 解析脚本部分
            elements = []
            total_duration = 0
            
            for section_data in script_data.get('sections', []):
                section = ScriptSection(section_data['section'])
                element = ScriptElement(
                    section=section,
                    content=section_data['content'],
                    duration=section_data.get('duration', 10),
                    visual_suggestions=section_data.get('visual_suggestions', []),
                    audio_suggestions=section_data.get('audio_suggestions', []),
                    timing_notes=section_data.get('timing_notes', '')
                )
                elements.append(element)
                total_duration += element.duration
            
            # 创建视频脚本对象
            video_script = VideoScript(
                script_id=f"script_{self.file_utils.get_timestamp()}",
                title=script_data.get('title', request.topic),
                description=script_data.get('description', ''),
                target_audience=request.target_audience,
                video_type=request.video_type,
                script_style=request.script_style,
                estimated_duration=total_duration,
                elements=elements,
                tags=script_data.get('tags', []),
                metadata={
                    'generation_time': self.file_utils.get_timestamp(),
                    'original_request': asdict(request),
                    'ai_provider': 'openai',
                    'model': 'gpt-3.5-turbo'
                }
            )
            
            return video_script
            
        except Exception as e:
            logger.error(f"解析脚本数据时出错: {e}")
            return None
    
    def _load_script_templates(self) -> Dict[str, Any]:
        """加载脚本模板"""
        return {
            VideoType.SHORT_VIDEO: {
                'hook_duration': 3,
                'intro_duration': 10,
                'main_duration': 30,
                'conclusion_duration': 10,
                'cta_duration': 7,
                'total_duration': 60
            },
            VideoType.TUTORIAL: {
                'hook_duration': 5,
                'intro_duration': 15,
                'main_duration': 120,
                'conclusion_duration': 15,
                'cta_duration': 10,
                'total_duration': 165
            },
            VideoType.PRODUCT_REVIEW: {
                'hook_duration': 5,
                'intro_duration': 20,
                'main_duration': 90,
                'conclusion_duration': 15,
                'cta_duration': 10,
                'total_duration': 140
            },
            VideoType.DOCUMENTARY: {
                'hook_duration': 10,
                'intro_duration': 30,
                'main_duration': 300,
                'conclusion_duration': 30,
                'cta_duration': 15,
                'total_duration': 385
            }
        }
    
    def _update_style_stats(self, style: ScriptStyle):
        """更新风格统计"""
        if style.value not in self.generation_stats['style_distribution']:
            self.generation_stats['style_distribution'][style.value] = 0
        
        self.generation_stats['style_distribution'][style.value] += 1
    
    async def generate_script_variations(self, base_request: ScriptGenerationRequest, count: int = 3) -> List[VideoScript]:
        """生成多个脚本变体"""
        variations = []
        
        for i in range(count):
            # 为每个变体调整参数
            variation_request = self._create_variation_request(base_request, i)
            
            script = await self.generate_script(variation_request)
            if script:
                variations.append(script)
        
        return variations
    
    def _create_variation_request(self, base_request: ScriptGenerationRequest, variation_index: int) -> ScriptGenerationRequest:
        """创建变体请求"""
        # 复制基础请求
        variation_request = ScriptGenerationRequest(
            topic=base_request.topic,
            video_type=base_request.video_type,
            script_style=base_request.script_style,
            target_audience=base_request.target_audience,
            duration=base_request.duration,
            key_points=base_request.key_points.copy(),
            tone=base_request.tone,
            language=base_request.language,
            include_visual_suggestions=base_request.include_visual_suggestions,
            include_audio_suggestions=base_request.include_audio_suggestions,
            custom_requirements=base_request.custom_requirements
        )
        
        # 为不同变体添加特殊要求
        variation_requirements = [
            "请采用更轻松活泼的语调，增加一些幽默元素。",
            "请采用更专业正式的语调，强调深度和权威性。",
            "请采用更富有故事性的语调，注重情感共鸣。"
        ]
        
        if variation_index < len(variation_requirements):
            variation_request.custom_requirements += f"\n{variation_requirements[variation_index]}"
        
        return variation_request
    
    async def improve_script(self, script: VideoScript, improvement_focus: str) -> Optional[VideoScript]:
        """改进现有脚本"""
        try:
            # 构建改进请求
            improvement_prompt = f"""
请改进以下视频脚本，重点关注: {improvement_focus}

原始脚本:
标题: {script.title}
描述: {script.description}
目标受众: {script.target_audience}
视频类型: {script.video_type.value}
脚本风格: {script.script_style.value}

脚本内容:
"""
            
            for element in script.elements:
                improvement_prompt += f"""
{element.section.value} (时长: {element.duration}秒):
{element.content}
"""
            
            improvement_prompt += """
请保持脚本的基本结构和核心信息，但在指定的重点方面进行改进。
请以JSON格式返回改进后的脚本，格式与原始脚本相同。
"""
            
            # 创建生成请求
            improvement_request = GenerationRequest(
                request_id=f"improve_{self.file_utils.get_timestamp()}",
                content_type=ContentType.SCRIPT,
                prompt=improvement_prompt,
                provider=AIProvider.OPENAI,
                model="gpt-3.5-turbo",
                parameters=self.ai_generator.get_default_parameters(ContentType.SCRIPT),
                context={
                    'improvement_focus': improvement_focus,
                    'original_script_id': script.script_id
                }
            )
            
            # 提交改进任务
            task_id = await self.ai_generator.generate_content(improvement_request)
            
            # 等待改进完成
            improved_data = await self._wait_for_generation(task_id)
            
            if improved_data:
                # 解析改进后的脚本
                improved_script = self._parse_generated_script(improved_data, 
                    ScriptGenerationRequest(
                        topic=script.title,
                        video_type=script.video_type,
                        script_style=script.script_style,
                        target_audience=script.target_audience,
                        duration=script.estimated_duration
                    )
                )
                
                if improved_script:
                    # 保留原始脚本的ID和元数据
                    improved_script.script_id = script.script_id
                    improved_script.metadata['improved_from'] = script.script_id
                    improved_script.metadata['improvement_focus'] = improvement_focus
                    
                    return improved_script
            
            return None
            
        except Exception as e:
            logger.error(f"改进脚本时出错: {e}")
            return None
    
    def get_script_template(self, video_type: VideoType) -> Dict[str, Any]:
        """获取脚本模板"""
        return self.script_templates.get(video_type, {})
    
    def estimate_script_duration(self, word_count: int, speaking_rate: int = 200) -> float:
        """估算脚本时长"""
        # 默认语速：每分钟200字
        return (word_count / speaking_rate) * 60
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """获取生成统计"""
        return self.generation_stats.copy()
    
    def get_available_styles(self) -> List[ScriptStyle]:
        """获取可用的脚本风格"""
        return list(ScriptStyle)
    
    def get_available_video_types(self) -> List[VideoType]:
        """获取可用的视频类型"""
        return list(VideoType)

def main():
    """主函数"""
    # 测试脚本生成器
    from app.core.ai_generator import AIContentGenerator
    from app.utils.config import Config
    
    # 创建配置和生成器
    config = Config()
    ai_generator = AIContentGenerator(config)
    script_generator = AIScriptGenerator(ai_generator, config)
    
    # 启动AI生成器
    asyncio.run(ai_generator.start())
    
    try:
        # 创建脚本生成请求
        request = ScriptGenerationRequest(
            topic="人工智能在医疗领域的应用",
            video_type=VideoType.SHORT_VIDEO,
            script_style=ScriptStyle.EDUCATIONAL,
            target_audience="科技爱好者和医疗专业人士",
            duration=60,
            key_points=[
                "AI诊断技术",
                "药物研发中的应用",
                "个性化医疗",
                "未来发展趋势"
            ],
            tone="专业且易懂",
            include_visual_suggestions=True,
            include_audio_suggestions=True
        )
        
        print(f"开始生成脚本: {request.topic}")
        
        # 生成脚本
        script = asyncio.run(script_generator.generate_script(request))
        
        if script:
            print(f"✅ 脚本生成成功!")
            print(f"标题: {script.title}")
            print(f"描述: {script.description}")
            print(f"预计时长: {script.estimated_duration}秒")
            print(f"标签: {', '.join(script.tags)}")
            print(f"\n脚本结构:")
            
            for element in script.elements:
                print(f"  {element.section.value}: {element.duration}秒")
                print(f"    {element.content[:100]}...")
                if element.visual_suggestions:
                    print(f"    视觉建议: {', '.join(element.visual_suggestions)}")
                if element.audio_suggestions:
                    print(f"    音频建议: {', '.join(element.audio_suggestions)}")
                print()
            
            # 显示统计信息
            stats = script_generator.get_generation_stats()
            print(f"生成统计: {stats}")
            
        else:
            print("❌ 脚本生成失败")
        
    finally:
        # 停止AI生成器
        asyncio.run(ai_generator.stop())

if __name__ == "__main__":
    main()