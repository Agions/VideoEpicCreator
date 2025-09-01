# VideoEpicCreator

<div align="center">

![VideoEpicCreator Logo](https://img.shields.io/badge/VideoEpicCreator-v1.0.0-blue?style=for-the-badge&logo=video&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5%2B-green?style=for-the-badge&logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**AI 驱动的专业视频创作工具**

[📖 文档] 
[🚀 快速开始](#-快速开始) •
[🎯 功能特性](#-功能特性) •
[📸 界面截图](#-界面截图) •
[🤝 贡献指南](#-贡献指南)

</div>

---

## 🎯 项目概述

VideoEpicCreator 是一款尖端的 AI 驱动视频编辑应用程序，结合了专业视频处理能力和智能内容生成功能。采用现代化架构和行业领先技术构建，让用户能够通过 AI 驱动的解说、混剪和旁白功能创建精彩的视频内容。

### ✨ 核心亮点

- 🤖 **AI 集成**：支持 OpenAI、Ollama 和千问 AI 模型
- 🎬 **专业编辑**：功能齐全的视频编辑器，集成 FFmpeg
- 🌐 **多语言**：完整的国际化支持（中文/英文）
- ♿ **无障碍**：符合 WCAG AA 标准的界面，完整的键盘导航
- 🚀 **性能优化**：先进的内存管理和优化技术
- 📱 **现代界面**：Ant Design 设计，响应式组件

---

## 🚀 快速开始

### 系统要求

- **Python**: 3.10 或更高版本
- **FFmpeg**: 已安装并在 PATH 中可用
- **内存**: 最少 4GB RAM（推荐 8GB）
- **存储**: 安装需要 2GB 可用空间

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/Agions/VideoEpicCreator.git
cd VideoEpicCreator

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .

# 安装可选的 TTS 增强功能
pip install edge-tts
```

### 环境配置

在项目根目录创建 `.env` 文件：

```env
# AI 服务 API 密钥
OPENAI_API_KEY=your_openai_api_key_here
QIANWEN_API_KEY=your_qianwen_api_key_here

# 应用设置
LOG_LEVEL=INFO
MAX_MEMORY_USAGE=2048  # MB
CACHE_SIZE=100  # 预览帧数
```

### 运行应用程序

```bash
# 启动应用
python main.py

# 调试模式启动
python main.py --debug

# 使用已安装的命令
videoepiccreator
```

---

## 🎯 功能特性

### 🤖 AI 驱动的内容生成

| 功能                   | 描述                                 | AI 模型              |
| ---------------------- | ------------------------------------ | -------------------- |
| **AI 解说**      | 生成智能视频解说，具有上下文分析能力 | OpenAI, Ollama, 千问 |
| **智能混剪**     | 自动创建精彩集锦和混剪内容           | OpenAI, Ollama, 千问 |
| **第一人称独白** | 创建角色驱动的叙事和故事             | OpenAI, Ollama, 千问 |
| **文本转语音**   | 将生成的文本转换为自然的语音         | edge-tts, Azure TTS  |

### 🎬 专业视频编辑

#### 核心编辑功能

- **多格式支持**：MP4, AVI, MOV, WMV, FLV, MKV, WebM
- **实时预览**：高级缓存和优化技术
- **时间线编辑器**：专业多轨道时间线
- **特效与转场**：全面的特效库
- **音频处理**：多轨道音频支持

#### 高级处理功能

- **帧精确编辑**：精确的剪切和修剪操作
- **格式转换**：高质量转码
- **分辨率缩放**：智能放大和缩小
- **批量处理**：高效的大批量操作

### 📱 现代化用户界面

#### 设计系统

- **Ant Design**：企业级产品设计体系
- **响应式布局**：适配不同屏幕尺寸
- **深色/浅色主题**：完整的主题支持
- **可定制组件**：模块化 UI 架构

#### 无障碍功能

- **键盘导航**：完整的键盘可访问性
- **屏幕阅读器支持**：兼容屏幕阅读器
- **高对比度**：符合 WCAG AA 标准的配色方案
- **可调整界面**：可调整的界面元素

### 🔧 导出与集成

#### 导出选项

- **剪映集成**：直接导出到剪映/剪映专业版
- **多种格式**：各种输出格式和质量选项
- **批量导出**：同时导出多个项目
- **自定义预设**：保存和重用导出设置

#### 项目管理

- **模板系统**：预配置的项目模板
- **自动保存**：自动项目保存和恢复
- **版本控制**：项目历史和版本管理

---

## 🏗️ 架构设计

### 重构后的架构

VideoEpicCreator 已经过全面重构，采用现代化的模块化架构，实现高内聚低耦合的设计原则。

### 核心设计原则

- **高内聚**：相关功能紧密组织在一起
- **低耦合**：模块间依赖最小化
- **依赖注入**：提高可测试性和可维护性
- **事件驱动**：通过事件解耦模块间通信
- **异步处理**：非阻塞操作提升性能

### 标准化模块结构

```
app/
├── core/                 # 核心功能模块
│   ├── base.py           # 基础类和接口
│   ├── utils.py          # 通用工具函数
│   ├── project.py        # 项目管理系统
│   ├── video_engine.py   # 视频处理引擎
│   ├── workflow.py       # 工作流管理
│   └── events.py         # 事件系统
├── ai/                   # AI 服务模块
│   ├── providers.py      # AI 提供商接口
│   ├── services.py       # AI 服务实现
│   ├── models.py         # AI 数据模型
│   ├── ai_manager.py     # AI 服务协调器
│   └── generators/       # 内容生成器
├── services/             # 业务服务模块
│   ├── service_manager.py # 服务管理器
│   ├── export_service.py # 导出服务
│   ├── subtitle_service.py # 字幕服务
│   └── tts_service.py    # 语音合成服务
├── config/               # 配置管理
│   ├── settings_manager.py # 设置管理
│   └── api_key_manager.py # API 密钥管理
└── utils/                # 工具函数
    ├── ffmpeg_utils.py   # FFmpeg 工具
    └── logger.py         # 日志系统
```

### 关键改进

#### 1. 模块化设计
- **清晰边界**：每个模块职责明确
- **标准化接口**：统一的基类和接口定义
- **插件化架构**：支持第三方扩展

#### 2. 服务管理
- **统一管理**：集中式服务注册和生命周期管理
- **健康检查**：服务状态监控和故障恢复
- **依赖注入**：降低模块间耦合

#### 3. 事件系统
- **松耦合通信**：模块间通过事件通信
- **优先级处理**：支持事件优先级
- **异步处理**：非阻塞事件传播

#### 4. 错误处理
- **统一异常处理**：结构化错误处理机制
- **恢复策略**：自动错误恢复和重试
- **日志记录**：详细的错误日志和调试信息

#### 5. 性能优化
- **内存管理**：智能内存监控和清理
- **缓存系统**：多级缓存提升性能
- **异步处理**：非阻塞操作和并发处理

#### 关键技术

| 组件                     | 技术                  | 用途                      |
| ------------------------- | --------------------- | ------------------------- |
| **UI 框架**              | PyQt6                 | 现代、跨平台 GUI          |
| **UI 设计**              | Ant Design            | 企业级设计体系            |
| **视频处理**              | FFmpeg                | 专业视频编辑              |
| **AI 集成**              | OpenAI/Ollama/千问   | 内容生成                  |
| **架构**                 | MVVM                  | 关注点分离                |
| **性能**                 | PSUTIL                | 系统监控                  |
| **国际化**               | Qt i18n               | 多语言支持                |

---

## 📚 API 文档

### 核心类

#### VideoEditor

```python
from app.core.video_editor import VideoEditor

editor = VideoEditor()
result = editor.compose_video(
    input_paths=["video1.mp4", "video2.mp4"],
    output_path="output.mp4",
    options={
        "resolution": "1920x1080",
        "fps": 30,
        "quality": "high"
    }
)
```

#### AIManager

```python
from app.ai.ai_manager import AIManager

ai_manager = AIManager()
result = await ai_manager.generate_content(
    prompt="为这个视频创建一个令人兴奋的解说",
    model="openai",
    content_type="commentary"
)
```

#### ProjectManager

```python
from app.core.project_manager import ProjectManager

pm = ProjectManager()
project = pm.create_project(
    name="我的视频项目",
    template="highlight_reel"
)
pm.save_project(project, "project.json")
```

### 配置

#### 设置管理

```python
from app.config.settings_manager import SettingsManager

settings = SettingsManager()
settings.set("ai.model", "openai")
settings.set("video.quality", "high")
settings.save()
```

#### API 密钥管理

```python
from app.config.api_key_manager import APIKeyManager

key_manager = APIKeyManager()
key_manager.set_key("openai", "your-api-key")
key_manager.set_key("qianwen", "your-qianwen-key")
```

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行覆盖率测试
pytest --cov=app --cov-report=html

# 运行特定测试类别
pytest -m unit        # 仅单元测试
pytest -m integration # 仅集成测试
pytest -m e2e         # 仅端到端测试

# 运行性能测试
pytest -m slow        # 性能基准测试
```

### 测试结构

```
tests/
├── unit/               # 单元测试
│   ├── test_ai_manager.py
│   ├── test_video_editor.py
│   └── test_project_manager.py
├── integration/        # 集成测试
│   ├── test_ai_integration.py
│   └── test_export_workflow.py
├── e2e/               # 端到端测试
│   ├── test_full_workflow.py
│   └── test_ui_interactions.py
└── performance/       # 性能测试
    ├── test_memory_usage.py
    └── test_rendering_performance.py
```

---

## 📊 性能

### 基准测试

| 操作                          | 平均时间     | 内存使用     | CPU 使用率 |
| ----------------------------- | ------------ | ------------ | ---------- |
| **视频加载 (1GB)**           | 2.3s         | 150MB        | 25%        |
| **AI 解说生成**              | 8.5s         | 300MB        | 45%        |
| **视频导出 (1080p)**         | 45s          | 200MB        | 80%        |
| **预览生成**                 | 0.5s         | 50MB         | 15%        |

### 优化功能

- **内存管理**：自动清理和监控
- **缓存系统**：多级缓存以获得最佳性能
- **后台处理**：非阻塞操作
- **资源管理**：高效的资源利用

---

## 🔧 配置

### 环境变量

| 变量                | 描述               | 默认值     |
| ------------------- | ------------------ | ---------- |
| `OPENAI_API_KEY`    | OpenAI API 密钥    | 必需       |
| `QIANWEN_API_KEY`   | 千问 API 密钥      | 必需       |
| `LOG_LEVEL`         | 日志级别           | `INFO`     |
| `MAX_MEMORY_USAGE`  | 内存限制（MB）     | `2048`     |
| `CACHE_SIZE`        | 预览缓存大小       | `100`      |
| `FFMPEG_PATH`       | 自定义 FFmpeg 路径 | `ffmpeg`   |

### 设置文件

```json
{
  "ai": {
    "default_model": "openai",
    "max_tokens": 2000,
    "temperature": 0.7
  },
  "video": {
    "default_quality": "high",
    "preview_resolution": "720p",
    "export_format": "mp4"
  },
  "ui": {
    "theme": "dark",
    "language": "zh_CN",
    "accessibility": true
  }
}
```

---

## 🤝 贡献

我们欢迎贡献！详情请参阅我们的[贡献指南](CONTRIBUTING.md)。

### 开发设置

```bash
# 克隆和设置
git clone https://github.com/Agions/VideoEpicCreator.git
cd VideoEpicCreator
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# 安装预提交钩子
pre-commit install

# 运行测试
pytest
```

### 代码规范

- **Python**：遵循 PEP 8
- **类型提示**：所有新代码必须使用
- **测试**：保持 80% 以上的覆盖率
- **文档**：记录所有公共 API

---

## 📄 许可证

本项目基于 MIT 许可证开源 - 详情请参阅 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- **OpenAI** 提供强大的 AI 模型
- **Ollama** 提供本地 AI 模型支持
- **阿里巴巴千问** 提供中文 AI 能力
- **FFmpeg** 提供专业视频处理
- **PyQt6** 提供优秀的 UI 框架
- **Material Design** 提供设计系统灵感

---

## 📞 支持

- **文档**：[完整文档](https://github.com/Agions/VideoEpicCreator/docs)
- **问题**：[GitHub Issues](https://github.com/Agions/VideoEpicCreator/issues)
- **讨论**：[GitHub Discussions](https://github.com/Agions/VideoEpicCreator/discussions)
- **邮件**：agions@qq.com

---

<div align="center">

**由 Agions 和贡献者用 ❤️ 制作**

如果你觉得这个项目有帮助，请[⭐ Star 这个项目](https://github.com/Agions/VideoEpicCreator)！

</div>
