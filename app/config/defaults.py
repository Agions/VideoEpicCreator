#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

# 默认设置配置
DEFAULT_SETTINGS = {
    # 应用程序设置
    "app": {
        "version": "1.0.0",
        "language": "zh_CN",
        "theme": "dark",
        "auto_save": True,
        "auto_save_interval": 300,  # 秒
        "check_updates": True
    },

    # 项目设置
    "project": {
        "default_location": str(Path.home() / "CineAIStudio" / "Projects"),
        "auto_backup": True,
        "backup_interval": 600,  # 秒
        "max_backups": 10,
        "recent_projects_count": 10
    },

    # 视频设置
    "video": {
        "default_resolution": "1920x1080",
        "default_fps": 30,
        "default_format": "mp4",
        "preview_quality": "medium",
        "thumbnail_size": 150,
        "cache_thumbnails": True,
        "max_cache_size": 1024  # MB
    },

    # AI模型设置
    "ai_models": {
        "default_model": "智谱AI",
        "timeout": 30,  # 秒
        "max_retries": 3,
        "use_cache": True,
        "cache_duration": 3600,  # 秒

        # 各个模型的默认配置
        "openai": {
            "enabled": False,
            "api_url": "https://api.openai.com/v1",
            "model": "gpt-3.5-turbo",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },

        "qianwen": {
            "enabled": True,
            "api_url": "https://dashscope.aliyuncs.com/api/v1",
            "model": "qwen-turbo",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "wenxin": {
            "enabled": True,
            "api_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
            "model": "ernie-bot-turbo",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "zhipu": {
            "enabled": True,
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "xunfei": {
            "enabled": True,
            "api_url": "https://spark-api.xf-yun.com/v3.1/chat/completions",
            "model": "spark-3.0",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "hunyuan": {
            "enabled": True,
            "api_url": "https://hunyuan.tencentcloudapi.com",
            "model": "hunyuan-lite",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "deepseek": {
            "enabled": True,
            "api_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        },

        "ollama": {
            "enabled": False,
            "api_url": "http://localhost:11434",
            "model": "llama2",
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9
        }
    },

    # 场景检测设置
    "scene_detection": {
        "enabled": True,
        "sensitivity": 0.3,
        "min_scene_length": 1.0,  # 秒
        "detect_cuts": True,
        "detect_motion": True,
        "detect_audio_changes": True,
        "detect_face_changes": True
    },

    # 语音合成设置
    "voice_synthesis": {
        "enabled": True,
        "default_voice": "zh-CN-XiaoxiaoNeural",
        "speed": 1.0,
        "pitch": 0,
        "volume": 1.0,
        "output_format": "wav",
        "sample_rate": 22050
    },

    # 剪映集成设置
    "jianying": {
        "enabled": True,
        "auto_detect_path": True,
        "draft_folder": "",  # 自动检测或用户设置
        "export_format": "json",
        "include_assets": True,
        "asset_copy_mode": "link"  # link, copy, move
    },

    # 导出设置
    "export": {
        "default_format": "mp4",
        "default_quality": "high",
        "default_resolution": "1920x1080",
        "default_fps": 30,
        "hardware_acceleration": True,
        "output_folder": str(Path.home() / "CineAIStudio" / "Exports")
    },

    # 界面设置
    "ui": {
        "window_size": [1280, 720],
        "window_maximized": False,
        "left_panel_width": 300,
        "right_panel_width": 350,
        "timeline_height": 200,
        "show_tooltips": True,
        "animation_enabled": True
    },

    # 性能设置
    "performance": {
        "max_threads": 4,
        "memory_limit": 2048,  # MB
        "gpu_acceleration": True,
        "preview_threads": 2,
        "analysis_threads": 2
    },

    # 日志设置
    "logging": {
        "enabled": True,
        "level": "INFO",
        "max_file_size": 10,  # MB
        "max_files": 5,
        "log_folder": str(Path.home() / "CineAIStudio" / "Logs")
    }
}

# AI模型提供商信息
AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "display_name": "OpenAI (ChatGPT)",
        "website": "https://platform.openai.com/",
        "api_docs": "https://platform.openai.com/docs/",
        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    },

    "qianwen": {
        "name": "通义千问",
        "display_name": "通义千问 (阿里云)",
        "website": "https://dashscope.aliyun.com/",
        "api_docs": "https://help.aliyun.com/zh/dashscope/",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"]
    },

    "wenxin": {
        "name": "文心一言",
        "display_name": "文心一言 (百度)",
        "website": "https://cloud.baidu.com/product/wenxinworkshop",
        "api_docs": "https://cloud.baidu.com/doc/WENXINWORKSHOP/",
        "models": ["ernie-bot", "ernie-bot-turbo", "ernie-bot-4"]
    },

    "zhipu": {
        "name": "智谱AI",
        "display_name": "智谱AI (GLM)",
        "website": "https://open.bigmodel.cn/",
        "api_docs": "https://open.bigmodel.cn/dev/api",
        "models": ["glm-4", "glm-4v", "glm-3-turbo"]
    },

    "xunfei": {
        "name": "讯飞星火",
        "display_name": "讯飞星火 (科大讯飞)",
        "website": "https://xinghuo.xfyun.cn/",
        "api_docs": "https://www.xfyun.cn/doc/spark/Web.html",
        "models": ["spark-3.0", "spark-2.0", "spark-1.5"]
    },

    "hunyuan": {
        "name": "腾讯混元",
        "display_name": "腾讯混元 (腾讯云)",
        "website": "https://cloud.tencent.com/product/hunyuan",
        "api_docs": "https://cloud.tencent.com/document/product/1729",
        "models": ["hunyuan-lite", "hunyuan-standard", "hunyuan-pro"]
    },

    "deepseek": {
        "name": "DeepSeek",
        "display_name": "DeepSeek (深度求索)",
        "website": "https://www.deepseek.com/",
        "api_docs": "https://platform.deepseek.com/api-docs/",
        "models": ["deepseek-chat", "deepseek-coder"]
    },

    "ollama": {
        "name": "Ollama",
        "display_name": "Ollama (本地模型)",
        "website": "https://ollama.ai/",
        "api_docs": "https://github.com/jmorganca/ollama/blob/main/docs/api.md",
        "models": ["llama2", "codellama", "mistral", "neural-chat"]
    }
}

# JianYing路径检测
def get_jianying_paths():
    """获取剪映可能的安装路径"""
    import platform

    system = platform.system()
    paths = []

    if system == "Windows":
        # Windows路径
        paths.extend([
            os.path.expandvars(r"%LOCALAPPDATA%\JianyingPro"),
            os.path.expandvars(r"%APPDATA%\JianyingPro"),
            r"C:\Program Files\JianyingPro",
            r"C:\Program Files (x86)\JianyingPro"
        ])
    elif system == "Darwin":  # macOS
        # macOS路径
        home = os.path.expanduser("~")
        paths.extend([
            f"{home}/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro",
            f"{home}/Movies/JianyingPro",
            "/Applications/JianyingPro.app"
        ])

    # 返回存在的路径
    return [path for path in paths if os.path.exists(path)]
