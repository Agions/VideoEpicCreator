#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI AI服务提供商插件
提供GPT-4、GPT-3.5等模型的访问和集成
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from app.plugins.plugin_system import AIProviderPlugin, PluginMetadata, PluginContext
from app.ai.interfaces import IAIModelProvider
from app.ai.models.base_model import AIModelInfo, ModelHealthStatus, AIRequestStatus

logger = logging.getLogger(__name__)


class OpenAIModel(Enum):
    """OpenAI模型枚举"""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_3_5_TURBO_16K = "gpt-3.5-turbo-16k"


@dataclass
class OpenAIConfig:
    """OpenAI配置"""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    organization: str = ""
    timeout: int = 30
    max_retries: int = 3
    default_model: str = OpenAIModel.GPT_4O.value
    temperature: float = 0.7
    max_tokens: int = 4000
    enable_streaming: bool = True


class OpenAIWorker(QObject):
    """OpenAI工作线程"""

    request_completed = pyqtSignal(dict, object)  # result, error
    streaming_response = pyqtSignal(str)

    def __init__(self, config: OpenAIConfig):
        super().__init__()
        self.config = config
        self._running = False

    def generate_text(self, prompt: str, model: str, options: Dict[str, Any]):
        """生成文本"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            if self.config.organization:
                headers["OpenAI-Organization"] = self.config.organization

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": options.get("temperature", self.config.temperature),
                "max_tokens": options.get("max_tokens", self.config.max_tokens),
                "stream": options.get("stream", self.config.enable_streaming)
            }

            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                result = response.json()
                self.request_completed.emit(result, None)
            else:
                error = {
                    "status_code": response.status_code,
                    "message": response.text
                }
                self.request_completed.emit(None, error)

        except Exception as e:
            error = {
                "exception": str(e),
                "type": type(e).__name__
            }
            self.request_completed.emit(None, error)

    def validate_api_key(self, api_key: str):
        """验证API密钥"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.config.base_url}/models",
                headers=headers,
                timeout=10
            )

            is_valid = response.status_code == 200
            models = []

            if is_valid:
                models_data = response.json().get("data", [])
                models = [model["id"] for model in models_data]

            self.request_completed.emit({"valid": is_valid, "models": models}, None)

        except Exception as e:
            self.request_completed.emit(None, {"exception": str(e)})


class OpenAIProviderPlugin(AIProviderPlugin):
    """OpenAI AI服务提供商插件"""

    def __init__(self):
        super().__init__()
        self._config = OpenAIConfig()
        self._worker = None
        self._thread = None

    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        return PluginMetadata(
            name="OpenAI Provider",
            version="1.0.0",
            description="提供OpenAI GPT模型的AI服务集成，支持GPT-4、GPT-4o等最新模型",
            author="CineAI Studio Team",
            email="support@cineaistudio.com",
            website="https://cineaistudio.com",
            plugin_type=PluginType.AI_PROVIDER,
            category="AI Service Provider",
            tags=["OpenAI", "GPT", "ChatGPT", "AI", "Text Generation"],
            dependencies=["requests>=2.25.0"],
            min_app_version="2.0.0",
            api_version="1.0",
            priority=PluginPriority.HIGH,
            enabled=True,
            config_schema={
                "sections": [
                    {
                        "name": "authentication",
                        "label": "认证设置",
                        "description": "OpenAI API认证配置",
                        "fields": [
                            {
                                "name": "api_key",
                                "label": "API密钥",
                                "type": "string",
                                "description": "OpenAI API密钥",
                                "required": True,
                                "placeholder": "sk-..."
                            },
                            {
                                "name": "organization",
                                "label": "组织ID",
                                "type": "string",
                                "description": "OpenAI组织ID（可选）",
                                "required": False,
                                "placeholder": "org-..."
                            }
                        ]
                    },
                    {
                        "name": "general",
                        "label": "常规设置",
                        "description": "OpenAI服务常规配置",
                        "fields": [
                            {
                                "name": "base_url",
                                "label": "API地址",
                                "type": "string",
                                "description": "OpenAI API基础地址",
                                "default": "https://api.openai.com/v1"
                            },
                            {
                                "name": "timeout",
                                "label": "超时时间",
                                "type": "integer",
                                "description": "API请求超时时间（秒）",
                                "default": 30,
                                "min_value": 5,
                                "max_value": 120
                            },
                            {
                                "name": "max_retries",
                                "label": "最大重试次数",
                                "type": "integer",
                                "description": "API请求失败时的最大重试次数",
                                "default": 3,
                                "min_value": 0,
                                "max_value": 10
                            }
                        ]
                    },
                    {
                        "name": "model_settings",
                        "label": "模型设置",
                        "description": "默认模型参数配置",
                        "fields": [
                            {
                                "name": "default_model",
                                "label": "默认模型",
                                "type": "select",
                                "description": "默认使用的AI模型",
                                "default": "gpt-4o",
                                "options": [
                                    {"value": "gpt-4o", "label": "GPT-4o (最新)"},
                                    {"value": "gpt-4o-mini", "label": "GPT-4o Mini (快速)"},
                                    {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
                                    {"value": "gpt-4", "label": "GPT-4"},
                                    {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"}
                                ]
                            },
                            {
                                "name": "temperature",
                                "label": "创造性参数",
                                "type": "float",
                                "description": "控制文本生成的创造性（0.0-2.0）",
                                "default": 0.7,
                                "min_value": 0.0,
                                "max_value": 2.0,
                                "step": 0.1
                            },
                            {
                                "name": "max_tokens",
                                "label": "最大令牌数",
                                "type": "integer",
                                "description": "生成文本的最大令牌数",
                                "default": 4000,
                                "min_value": 1,
                                "max_value": 128000
                            },
                            {
                                "name": "enable_streaming",
                                "label": "启用流式输出",
                                "type": "boolean",
                                "description": "是否启用流式文本输出",
                                "default": True
                            }
                        ]
                    }
                ]
            }
        )

    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        try:
            self._context = context

            # 加载插件配置
            plugin_config = context.settings_manager.get_plugin_config("openai_provider")
            if plugin_config:
                self._update_config_from_dict(plugin_config)

            logger.info("OpenAI Provider插件初始化成功")
            return True

        except Exception as e:
            logger.error(f"OpenAI Provider插件初始化失败: {e}")
            return False

    def cleanup(self):
        """清理插件资源"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        logger.info("OpenAI Provider插件已清理")

    def get_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        models = []

        for model in OpenAIModel:
            model_info = self.get_model_info(model.value)
            models.append({
                "id": model.value,
                "name": model_info.name,
                "description": model_info.description,
                "capabilities": model_info.capabilities,
                "pricing": model_info.pricing,
                "context_window": model_info.max_context_length,
                "supports_streaming": model_info.supports_streaming,
                "supports_json": model_info.supports_json_mode
            })

        return models

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """获取模型信息"""
        model_info = AIModelInfo(
            provider="OpenAI",
            model_id=model_id,
            name=self._get_model_display_name(model_id),
            description=self._get_model_description(model_id),
            max_context_length=self._get_model_context_length(model_id),
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision="gpt-4o" in model_id,
            pricing=self._get_model_pricing(model_id),
            capabilities=self._get_model_capabilities(model_id)
        )

        return asdict(model_info)

    def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        if not api_key or not api_key.startswith("sk-"):
            return False

        try:
            # 创建工作线程进行验证
            self._setup_worker()

            # 使用事件等待验证结果
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            future = asyncio.Future()

            def on_result(result, error):
                if error:
                    future.set_result(False)
                else:
                    future.set_result(result.get("valid", False))

            self._worker.request_completed.connect(on_result)
            self._worker.validate_api_key(api_key)

            # 等待结果（最多10秒）
            try:
                result = loop.run_until_complete(asyncio.wait_for(future, timeout=10))
                return result
            except asyncio.TimeoutError:
                return False
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"验证API密钥时发生错误: {e}")
            return False

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """估算成本"""
        pricing = self._get_model_pricing(model_id)
        if not pricing:
            return 0.0

        input_cost = (input_tokens / 1000) * pricing.get("input", 0.0)
        output_cost = (output_tokens / 1000) * pricing.get("output", 0.0)

        return input_cost + output_cost

    def generate_text(self, prompt: str, model_id: str = None, options: Dict[str, Any] = None) -> Any:
        """生成文本"""
        if not self._config.api_key:
            raise ValueError("API密钥未设置")

        model_id = model_id or self._config.default_model
        options = options or {}

        # 设置工作线程
        self._setup_worker()

        # 使用事件等待结果
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        future = asyncio.Future()

        def on_result(result, error):
            if error:
                future.set_exception(Exception(str(error)))
            else:
                # 解析OpenAI响应
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")

                    # 构造返回对象
                    response = type('Response', (), {
                        'success': True,
                        'content': content,
                        'model': model_id,
                        'usage': result.get("usage", {}),
                        'finish_reason': choices[0].get("finish_reason")
                    })()

                    future.set_result(response)
                else:
                    future.set_exception(Exception("No response from OpenAI"))

        self._worker.request_completed.connect(on_result)
        self._worker.generate_text(prompt, model_id, options)

        try:
            return loop.run_until_complete(asyncio.wait_for(future, timeout=self._config.timeout))
        except asyncio.TimeoutError:
            raise Exception("请求超时")
        finally:
            loop.close()

    def _setup_worker(self):
        """设置工作线程"""
        if not self._thread:
            self._thread = QThread()
            self._worker = OpenAIWorker(self._config)
            self._worker.moveToThread(self._thread)
            self._thread.start()

    def _update_config_from_dict(self, config_dict: Dict[str, Any]):
        """从字典更新配置"""
        for key, value in config_dict.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def _get_model_display_name(self, model_id: str) -> str:
        """获取模型显示名称"""
        names = {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-3.5-turbo-16k": "GPT-3.5 Turbo 16K"
        }
        return names.get(model_id, model_id)

    def _get_model_description(self, model_id: str) -> str:
        """获取模型描述"""
        descriptions = {
            "gpt-4o": "OpenAI最新的多模态AI模型，支持文本、图像和音频输入",
            "gpt-4o-mini": "GPT-4o的轻量版本，速度更快，成本更低",
            "gpt-4-turbo": "GPT-4的优化版本，具有更长的上下文窗口",
            "gpt-4": "OpenAI最强大的AI模型，具有先进的推理能力",
            "gpt-3.5-turbo": "快速且经济的AI模型，适用于大多数文本生成任务",
            "gpt-3.5-turbo-16k": "具有16K上下文窗口的GPT-3.5 Turbo版本"
        }
        return descriptions.get(model_id, "OpenAI AI模型")

    def _get_model_context_length(self, model_id: str) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384
        }
        return context_lengths.get(model_id, 4096)

    def _get_model_pricing(self, model_id: str) -> Dict[str, float]:
        """获取模型定价（USD per 1K tokens）"""
        pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
        }
        return pricing.get(model_id, {"input": 0.0, "output": 0.0})

    def _get_model_capabilities(self, model_id: str) -> List[str]:
        """获取模型能力"""
        capabilities = {
            "gpt-4o": ["text", "vision", "code", "reasoning", "multilingual"],
            "gpt-4o-mini": ["text", "code", "reasoning", "multilingual"],
            "gpt-4-turbo": ["text", "code", "reasoning", "multilingual"],
            "gpt-4": ["text", "code", "reasoning", "multilingual"],
            "gpt-3.5-turbo": ["text", "code", "multilingual"],
            "gpt-3.5-turbo-16k": ["text", "code", "multilingual", "long_context"]
        }
        return capabilities.get(model_id, ["text"])

    def on_config_changed(self, new_config: Dict[str, Any]):
        """配置变化回调"""
        self._update_config_from_dict(new_config)

        # 如果API密钥变化，重新初始化工作线程
        if "api_key" in new_config:
            if self._thread and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait()
            self._thread = None
            self._worker = None

    def get_status(self) -> Dict[str, Any]:
        """获取插件状态"""
        return {
            "state": self._state.value,
            "version": self.metadata.version,
            "enabled": self.metadata.enabled,
            "configured": bool(self._config.api_key),
            "default_model": self._config.default_model,
            "available_models": len(self.get_models())
        }


# 插件注册
plugin_class = OpenAIProviderPlugin