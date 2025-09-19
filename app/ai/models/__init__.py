"""
AI Models module

Contains integrations for various AI model providers:
- OpenAI (GPT-3.5, GPT-4)
- 通义千问 (Qianwen)
- 文心一言 (Wenxin)
- 智谱AI (Zhipu GLM)
- 讯飞星火 (Xunfei Spark)
- 腾讯混元 (Hunyuan)
- DeepSeek
- Ollama (Local models)
- Custom API integrations
"""

from .base_model import BaseAIModel, AIModelConfig, AIResponse
# from .openai_model import OpenAIModel  # 暂时注释掉，文件不存在
from .qianwen_model import QianwenModel
from .wenxin_model import WenxinModel
# from .ollama_model import OllamaModel  # 暂时注释掉，文件不存在
from .zhipu_model import ZhipuModel
from .xunfei_model import XunfeiModel
from .hunyuan_model import HunyuanModel
from .deepseek_model import DeepSeekModel

__all__ = [
    'BaseAIModel', 'AIModelConfig', 'AIResponse',
    # 'OpenAIModel',  # 暂时注释掉，文件不存在
    'QianwenModel', 'WenxinModel', 
    # 'OllamaModel',  # 暂时注释掉，文件不存在
    'ZhipuModel', 'XunfeiModel', 'HunyuanModel', 'DeepSeekModel'
]
