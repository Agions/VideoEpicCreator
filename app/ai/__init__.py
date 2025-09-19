#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI功能模块初始化
统一AI服务入口点
"""

# 导入新的统一AI服务
from .ai_service import AIService, create_ai_service
from .interfaces import (
    IAIService, AIRequest, AIResponse, AIModelHealth, AIUsageStats,
    AITaskType, AIPriority, AIRequestStatus,
    create_ai_request, create_text_generation_request,
    create_content_analysis_request, create_commentary_request,
    create_monologue_request
)
from .workers import AIWorker, AIWorkerPool, create_worker_pool

# 导入传统AI管理器（向后兼容）
from .ai_manager import AIManager, create_ai_manager
try:
    from .enhanced_ai_manager import EnhancedAIManager, create_enhanced_ai_manager
except ImportError:
    EnhancedAIManager = None
    create_enhanced_ai_manager = None
try:
    from .optimized_ai_manager import OptimizedAIManager, create_optimized_ai_manager
except ImportError:
    OptimizedAIManager = None
    create_optimized_ai_manager = None

# 导入模型管理器
try:
    from .optimized_model_manager import OptimizedModelManager
except ImportError:
    OptimizedModelManager = None
try:
    from .optimized_cost_manager import OptimizedCostManager
except ImportError:
    OptimizedCostManager = None
try:
    from .intelligent_load_balancer import IntelligentLoadBalancer
except ImportError:
    IntelligentLoadBalancer = None

# 导入内容生成器
try:
    from .intelligent_content_generator import IntelligentContentGenerator, create_content_generator
except ImportError:
    IntelligentContentGenerator = None
    create_content_generator = None

# 导入基础模型
from .models.base_model import BaseAIModel, AIModelConfig, AIResponse as LegacyAIResponse

# 导入具体模型实现
try:
    from .models.openai_model import OpenAIModel
except ImportError:
    OpenAIModel = None
from .models.qianwen_model import QianwenModel
from .models.wenxin_model import WenxinModel
from .models.zhipu_model import ZhipuModel
from .models.xunfei_model import XunfeiModel
from .models.hunyuan_model import HunyuanModel
from .models.deepseek_model import DeepSeekModel
try:
    from .models.ollama_model import OllamaModel
except ImportError:
    OllamaModel = None

# 导入生成器
try:
    from .generators.text_to_speech import TextToSpeechEngine, get_tts_engine
except ImportError:
    TextToSpeechEngine = None
    get_tts_engine = None
try:
    from .generators.commentary_generator import CommentaryGenerator
except ImportError:
    CommentaryGenerator = None
try:
    from .generators.compilation_generator import CompilationGenerator
except ImportError:
    CompilationGenerator = None
try:
    from .generators.monologue_generator import MonologueGenerator
except ImportError:
    MonologueGenerator = None

# 导入分析器
try:
    from .scene_detector import SceneDetector
except ImportError:
    SceneDetector = None
try:
    from .content_generator import ContentGenerator
except ImportError:
    ContentGenerator = None

# 版本信息
__version__ = "2.1.0"
__author__ = "CineAIStudio Team"

# 推荐的创建函数（使用新的统一AI服务）
def create_unified_ai_service(settings_manager):
    """创建统一AI服务（推荐使用）"""
    return create_ai_service(settings_manager)

# 默认创建函数（向后兼容，但内部使用新服务）
def create_default_ai_manager(settings_manager):
    """创建默认AI管理器（向后兼容，推荐使用create_unified_ai_service）"""
    return create_ai_service(settings_manager)

# 导出的主要类和函数
__all__ = [
    # 新的统一AI服务
    "AIService",
    "create_ai_service",
    "create_unified_ai_service",

    # AI接口和数据模型
    "IAIService",
    "AIRequest",
    "AIResponse",
    "AIModelHealth",
    "AIUsageStats",
    "AITaskType",
    "AIPriority",
    "AIRequestStatus",

    # 便利函数
    "create_ai_request",
    "create_text_generation_request",
    "create_content_analysis_request",
    "create_commentary_request",
    "create_monologue_request",

    # 工作线程
    "AIWorker",
    "AIWorkerPool",
    "create_worker_pool",

    # 传统AI管理器（向后兼容）
    "AIManager",
    "create_ai_manager",
    "create_default_ai_manager",

    # 基础模型
    "BaseAIModel",
    "AIModelConfig",
    "LegacyAIResponse",

    # 具体模型
    "QianwenModel",
    "WenxinModel",
    "ZhipuModel",
    "XunfeiModel",
    "HunyuanModel",
    "DeepSeekModel",

    # 版本信息
    "__version__",
    "__author__"
]

# 动态添加可选导入到__all__
if EnhancedAIManager:
    __all__.extend(["EnhancedAIManager", "create_enhanced_ai_manager"])
if OptimizedAIManager:
    __all__.extend(["OptimizedAIManager", "create_optimized_ai_manager"])
if OptimizedModelManager:
    __all__.append("OptimizedModelManager")
if OptimizedCostManager:
    __all__.append("OptimizedCostManager")
if IntelligentLoadBalancer:
    __all__.append("IntelligentLoadBalancer")
if IntelligentContentGenerator:
    __all__.extend(["IntelligentContentGenerator", "create_content_generator"])
if OpenAIModel:
    __all__.append("OpenAIModel")
if OllamaModel:
    __all__.append("OllamaModel")
if TextToSpeechEngine:
    __all__.extend(["TextToSpeechEngine", "get_tts_engine"])
if CommentaryGenerator:
    __all__.append("CommentaryGenerator")
if CompilationGenerator:
    __all__.append("CompilationGenerator")
if MonologueGenerator:
    __all__.append("MonologueGenerator")
if SceneDetector:
    __all__.append("SceneDetector")
if ContentGenerator:
    __all__.append("ContentGenerator")
