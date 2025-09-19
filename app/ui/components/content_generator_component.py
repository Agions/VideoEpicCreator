#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业AI内容生成器组件 - 支持多种内容生成场景
包括解说生成、脚本生成、文案创作等功能
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QGridLayout, QGroupBox, QCheckBox,
    QTabWidget, QSlider, QSpinBox, QFormLayout, QFileDialog,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QProgressBar, QTextEdit,
    QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QToolButton, QMenu,
    QApplication, QSizePolicy, QSpacerItem, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QTimeEdit,
    QSystemTrayIcon, QStatusBar, QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QTime, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QTextCharFormat, QDesktopServices, QAction

from app.ai.ai_service import AIService
from app.ai.interfaces import AITaskType, AIRequest, AIResponse, create_text_generation_request
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class ContentType(Enum):
    """内容类型"""
    COMMENTARY = "commentary"        # 视频解说
    SCRIPT = "script"                 # 脚本创作
    COPYWRITING = "copywriting"       # 文案创作
    CAPTION = "caption"               # 字幕文案
    DESCRIPTION = "description"       # 视频描述
    TITLE = "title"                   # 标题生成
    HASHTAG = "hashtag"               # 标签生成
    SUMMARY = "summary"               # 内容摘要


class ContentStyle(Enum):
    """内容风格"""
    PROFESSIONAL = "professional"     # 专业风格
    CASUAL = "casual"                 # 随意风格
    HUMOROUS = "humorous"             # 幽默风格
    EMOTIONAL = "emotional"           # 情感风格
    SUSPENSEFUL = "suspenseful"       # 悬疑风格
    EDUCATIONAL = "educational"       # 教育风格
    ENTERTAINING = "entertaining"     # 娱乐风格
    INSPIRATIONAL = "inspirational"   # 励志风格


class ContentLength(Enum):
    """内容长度"""
    SHORT = "short"                   # 短内容 (50-100字)
    MEDIUM = "medium"                 # 中等内容 (100-300字)
    LONG = "long"                     # 长内容 (300-500字)
    EXTENDED = "extended"             # 扩展内容 (500+字)


class TargetAudience(Enum):
    """目标受众"""
    GENERAL = "general"               # 普通受众
    YOUTH = "youth"                   # 年轻人
    PROFESSIONAL = "professional"     # 专业人士
    CHILDREN = "children"             # 儿童
    ELDERLY = "elderly"               # 老年人
    STUDENTS = "students"             # 学生
    BUSINESS = "business"             # 商务人士


@dataclass
class ContentGenerationRequest:
    """内容生成请求"""
    request_id: str
    content_type: ContentType
    prompt: str
    style: ContentStyle
    length: ContentLength
    target_audience: TargetAudience
    context: str = ""
    keywords: List[str] = None
    requirements: List[str] = None
    model: str = "auto"
    temperature: float = 0.7
    max_tokens: int = 1000
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.keywords is None:
            self.keywords = []
        if self.requirements is None:
            self.requirements = []


@dataclass
class ContentGenerationResponse:
    """内容生成响应"""
    request_id: str
    success: bool
    content: str = ""
    title: str = ""
    summary: str = ""
    keywords: List[str] = None
    metadata: Dict[str, Any] = None
    error_message: str = ""
    tokens_used: int = 0
    generation_time: float = 0.0
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.metadata is None:
            self.metadata = {}


class ContentTemplate:
    """内容模板"""
    
    def __init__(self, name: str, content_type: ContentType, 
                 template: str, description: str = ""):
        self.name = name
        self.content_type = content_type
        self.template = template
        self.description = description
        self.variables = self._extract_variables()
        
    def _extract_variables(self) -> List[str]:
        """提取模板变量"""
        import re
        pattern = r'\{\{(\w+)\}\}'
        return re.findall(pattern, self.template)
        
    def render(self, **kwargs) -> str:
        """渲染模板"""
        result = self.template
        for var in self.variables:
            value = kwargs.get(var, f"{{{var}}}")
            result = result.replace(f"{{{{{var}}}}}", str(value))
        return result


class AIContentGenerator(QWidget):
    """AI内容生成器"""
    
    # 信号定义
    generation_started = pyqtSignal(str)              # 生成开始
    generation_progress = pyqtSignal(str, float)      # 生成进度
    generation_completed = pyqtSignal(str, ContentGenerationResponse)  # 生成完成
    generation_error = pyqtSignal(str, str)          # 生成错误
    content_saved = pyqtSignal(str, str)             # 内容保存
    template_applied = pyqtSignal(ContentTemplate)   # 模板应用
    
    def __init__(self, ai_service: AIService, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)

        self.ai_service = ai_service
        self.settings_manager = settings_manager
        
        # 样式引擎
        self.style_engine = ProfessionalStyleEngine()
        
        # 内容模板
        self.templates = self._create_templates()
        
        # 请求管理
        self.active_requests: Dict[str, ContentGenerationRequest] = {}
        self.request_counter = 0
        
        # 生成历史
        self.generation_history: List[ContentGenerationResponse] = []
        
        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 快速生成标签页
        quick_tab = self._create_quick_tab()
        self.tab_widget.addTab(quick_tab, "⚡ 快速生成")
        
        # 高级设置标签页
        advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(advanced_tab, "⚙️ 高级设置")
        
        # 模板库标签页
        templates_tab = self._create_templates_tab()
        self.tab_widget.addTab(templates_tab, "📋 模板库")
        
        # 历史记录标签页
        history_tab = self._create_history_tab()
        self.tab_widget.addTab(history_tab, "📚 历史记录")
        
        main_layout.addWidget(self.tab_widget)
        
        # 进度显示
        self.progress_widget = self._create_progress_widget()
        self.progress_widget.setVisible(False)
        main_layout.addWidget(self.progress_widget)
        
    def _create_quick_tab(self) -> QWidget:
        """创建快速生成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 内容类型选择
        type_group = QGroupBox("内容类型")
        type_layout = QHBoxLayout(type_group)
        
        self.content_type_combo = QComboBox()
        self._populate_content_types()
        type_layout.addWidget(self.content_type_combo)
        
        type_layout.addStretch()
        layout.addWidget(type_group)
        
        # 输入区域
        input_group = QGroupBox("内容输入")
        input_layout = QVBoxLayout(input_group)
        
        # 主题/提示词
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("请输入要生成内容的主题或描述...")
        self.prompt_input.setMinimumHeight(120)
        input_layout.addWidget(self.prompt_input)
        
        # 快速选项
        options_layout = QHBoxLayout()
        
        # 风格选择
        style_layout = QVBoxLayout()
        style_layout.addWidget(QLabel("风格:"))
        self.style_combo = QComboBox()
        self._populate_styles()
        style_layout.addWidget(self.style_combo)
        options_layout.addLayout(style_layout)
        
        # 长度选择
        length_layout = QVBoxLayout()
        length_layout.addWidget(QLabel("长度:"))
        self.length_combo = QComboBox()
        self._populate_lengths()
        length_layout.addWidget(self.length_combo)
        options_layout.addLayout(length_layout)
        
        # 受众选择
        audience_layout = QVBoxLayout()
        audience_layout.addWidget(QLabel("受众:"))
        self.audience_combo = QComboBox()
        self._populate_audiences()
        audience_layout.addWidget(self.audience_combo)
        options_layout.addLayout(audience_layout)
        
        options_layout.addStretch()
        input_layout.addLayout(options_layout)
        
        layout.addWidget(input_group)
        
        # 生成按钮
        button_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("🚀 开始生成")
        self.generate_btn.setObjectName("primary_button")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.clicked.connect(self._start_generation)
        button_layout.addWidget(self.generate_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 结果显示
        self.result_display = QTextEdit()
        self.result_display.setPlaceholderText("生成的内容将在这里显示...")
        self.result_display.setMinimumHeight(200)
        layout.addWidget(self.result_display)
        
        # 结果操作
        result_actions = QHBoxLayout()
        
        copy_btn = QPushButton("📋 复制")
        copy_btn.clicked.connect(self._copy_result)
        result_actions.addWidget(copy_btn)
        
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._edit_result)
        result_actions.addWidget(edit_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save_result)
        result_actions.addWidget(save_btn)
        
        regenerate_btn = QPushButton("🔄 重新生成")
        regenerate_btn.clicked.connect(self._regenerate_result)
        result_actions.addWidget(regenerate_btn)
        
        result_actions.addStretch()
        layout.addLayout(result_actions)
        
        layout.addStretch()
        
        return widget
        
    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 详细设置
        settings_group = QGroupBox("详细设置")
        settings_layout = QFormLayout(settings_group)
        
        # 模型选择
        self.model_combo = QComboBox()
        self._populate_models()
        settings_layout.addRow("AI模型:", self.model_combo)
        
        # 温度设置
        temperature_layout = QHBoxLayout()
        
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(70)
        self.temperature_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        temperature_layout.addWidget(self.temperature_slider)
        
        self.temperature_label = QLabel("0.7")
        temperature_layout.addWidget(self.temperature_label)
        
        settings_layout.addRow("创造性:", temperature_layout)
        
        # 最大词数
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 2000)
        self.max_tokens_spin.setValue(1000)
        self.max_tokens_spin.setSuffix(" tokens")
        settings_layout.addRow("最大词数:", self.max_tokens_spin)
        
        # 上下文信息
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("提供额外的上下文信息，帮助AI更好地理解需求...")
        self.context_input.setMaximumHeight(100)
        settings_layout.addRow("上下文:", self.context_input)
        
        # 关键词
        keywords_layout = QHBoxLayout()
        
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("输入关键词，用逗号分隔")
        keywords_layout.addWidget(self.keywords_input)
        
        add_keyword_btn = QPushButton("添加")
        add_keyword_btn.clicked.connect(self._add_keyword)
        keywords_layout.addWidget(add_keyword_btn)
        
        settings_layout.addRow("关键词:", keywords_layout)
        
        # 关键词列表
        self.keywords_list = QListWidget()
        self.keywords_list.setMaximumHeight(80)
        settings_layout.addRow("", self.keywords_list)
        
        layout.addWidget(settings_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # 特殊要求
        self.requirements_input = QTextEdit()
        self.requirements_input.setPlaceholderText("输入特殊要求，每行一个...")
        self.requirements_input.setMaximumHeight(80)
        advanced_layout.addWidget(self.requirements_input)
        
        # 生成选项
        options_layout = QHBoxLayout()
        
        self.auto_format_check = QCheckBox("自动格式化")
        self.auto_format_check.setChecked(True)
        options_layout.addWidget(self.auto_format_check)
        
        self.include_emoji_check = QCheckBox("包含表情符号")
        self.include_emoji_check.setChecked(False)
        options_layout.addWidget(self.include_emoji_check)
        
        self.add_hashtags_check = QCheckBox("添加标签")
        self.add_hashtags_check.setChecked(False)
        options_layout.addWidget(self.add_hashtags_check)
        
        options_layout.addStretch()
        advanced_layout.addLayout(options_layout)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        
        return widget
        
    def _create_templates_tab(self) -> QWidget:
        """创建模板库标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 模板分类
        category_group = QGroupBox("模板分类")
        category_layout = QHBoxLayout(category_group)
        
        self.template_category_combo = QComboBox()
        self.template_category_combo.addItems(["全部", "解说模板", "脚本模板", "文案模板", "标题模板"])
        self.template_category_combo.currentTextChanged.connect(self._filter_templates)
        category_layout.addWidget(self.template_category_combo)
        
        category_layout.addStretch()
        
        # 搜索框
        self.template_search_input = QLineEdit()
        self.template_search_input.setPlaceholderText("搜索模板...")
        self.template_search_input.textChanged.connect(self._filter_templates)
        category_layout.addWidget(self.template_search_input)
        
        layout.addWidget(category_group)
        
        # 模板列表
        templates_group = QGroupBox("可用模板")
        templates_layout = QVBoxLayout(templates_group)
        
        self.template_table = QTableWidget()
        self.template_table.setColumnCount(4)
        self.template_table.setHorizontalHeaderLabels(["模板名称", "类型", "描述", "操作"])
        self.template_table.horizontalHeader().setStretchLastSection(True)
        self.template_table.itemSelectionChanged.connect(self._on_template_selected)
        templates_layout.addWidget(self.template_table)
        
        layout.addWidget(templates_group)
        
        # 模板详情
        details_group = QGroupBox("模板详情")
        details_layout = QVBoxLayout(details_group)
        
        self.template_details = QTextBrowser()
        self.template_details.setMaximumHeight(150)
        self.template_details.setPlaceholderText("选择模板查看详情")
        details_layout.addWidget(self.template_details)
        
        # 模板操作
        template_actions = QHBoxLayout()
        
        self.use_template_btn = QPushButton("📝 使用模板")
        self.use_template_btn.clicked.connect(self._use_template)
        template_actions.addWidget(self.use_template_btn)
        
        self.edit_template_btn = QPushButton("✏️ 编辑模板")
        self.edit_template_btn.clicked.connect(self._edit_template)
        template_actions.addWidget(self.edit_template_btn)
        
        template_actions.addStretch()
        details_layout.addLayout(template_actions)
        
        layout.addWidget(details_group)
        
        # 初始化模板列表
        self._populate_template_table()
        
        return widget
        
    def _create_history_tab(self) -> QWidget:
        """创建历史记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 历史记录列表
        history_group = QGroupBox("生成历史")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["时间", "类型", "风格", "长度", "状态", "操作"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.itemSelectionChanged.connect(self._on_history_selected)
        history_layout.addWidget(self.history_table)
        
        layout.addWidget(history_group)
        
        # 历史详情
        details_group = QGroupBox("历史详情")
        details_layout = QVBoxLayout(details_group)
        
        self.history_details = QTextBrowser()
        self.history_details.setMaximumHeight(200)
        self.history_details.setPlaceholderText("选择历史记录查看详情")
        details_layout.addWidget(self.history_details)
        
        # 历史操作
        history_actions = QHBoxLayout()
        
        self.load_history_btn = QPushButton("📝 加载内容")
        self.load_history_btn.clicked.connect(self._load_history_content)
        history_actions.addWidget(self.load_history_btn)
        
        self.delete_history_btn = QPushButton("🗑️ 删除记录")
        self.delete_history_btn.clicked.connect(self._delete_history_record)
        history_actions.addWidget(self.delete_history_btn)
        
        clear_all_btn = QPushButton("🗑️ 清空历史")
        clear_all_btn.clicked.connect(self._clear_all_history)
        history_actions.addWidget(clear_all_btn)
        
        history_actions.addStretch()
        details_layout.addLayout(history_actions)
        
        layout.addWidget(details_group)
        
        # 初始化历史记录
        self._populate_history_table()
        
        return widget
        
    def _create_progress_widget(self) -> QWidget:
        """创建进度显示组件"""
        widget = QFrame()
        widget.setObjectName("progress_widget")
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 详细信息
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detail_label)
        
        # 取消按钮
        cancel_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.clicked.connect(self._cancel_generation)
        cancel_layout.addWidget(self.cancel_btn)
        
        cancel_layout.addStretch()
        layout.addLayout(cancel_layout)
        
        return widget
        
    def _create_templates(self) -> List[ContentTemplate]:
        """创建内容模板"""
        templates = []
        
        # 解说模板
        templates.append(ContentTemplate(
            "短视频解说",
            ContentType.COMMENTARY,
            """【开场】
大家好，今天给大家带来{{主题}}。

【内容】
{{要点1}}
{{要点2}}
{{要点3}}

【结尾】
好了，今天的分享就到这里，喜欢的话记得点赞关注哦！""",
            "适用于短视频的通用解说模板"
        ))
        
        templates.append(ContentTemplate(
            "产品介绍",
            ContentType.COMMENTARY,
            """【产品亮点】
今天为大家介绍{{产品名称}}，它的最大特点是{{主要特点}}。

【功能展示】
{{功能1}}
{{功能2}}
{{功能3}}

【使用体验】
使用{{产品名称}}的感受是{{使用感受}}，特别适合{{适用人群}}。

【总结】
总的来说，{{产品名称}}是一款{{总结评价}}的产品。""",
            "产品介绍类视频解说模板"
        ))
        
        # 脚本模板
        templates.append(ContentTemplate(
            "教程脚本",
            ContentType.SCRIPT,
            """【开场】
（0-10秒）
主持人热情开场，介绍今天的主题：{{主题}}

【准备工作】
（10-30秒）
展示需要的工具和材料：{{准备材料}}

【步骤讲解】
（30-180秒）
步骤1：{{步骤1}}
步骤2：{{步骤2}}
步骤3：{{步骤3}}

【总结】
（180-200秒）
总结要点，鼓励观众尝试""",
            "教程类视频脚本模板"
        ))
        
        templates.append(ContentTemplate(
            "故事脚本",
            ContentType.SCRIPT,
            """【开场】
（场景：{{开场场景}}）
{{主角}}正在{{开场动作}}，突然{{转折事件}}。

【发展】
（场景：{{发展场景}}）
{{主角}}遇到了{{困难}}，开始{{应对措施}}。

【高潮】
（场景：{{高潮场景}}）
{{主角}}{{关键行动}}，最终{{结果}}。

【结尾】
（场景：{{结尾场景}}）
{{主角}}{{最终状态}}，{{主题思想}}。""",
            "故事类视频脚本模板"
        ))
        
        # 文案模板
        templates.append(ContentTemplate(
            "推广文案",
            ContentType.COPYWRITING,
            """🔥 {{产品名称}}震撼来袭！🔥

✨ 核心优势：
{{优势1}}
{{优势2}}
{{优势3}}

🎯 适用人群：
{{适用人群}}

🚀 限时优惠：{{优惠信息}}

📱 立即咨询：{{联系方式}}

#{{产品名称}} #{{行业标签}} #{{推广标签}}""",
            "产品推广文案模板"
        ))
        
        return templates
        
    def _populate_content_types(self):
        """填充内容类型下拉框"""
        self.content_type_combo.clear()
        for content_type in ContentType:
            self.content_type_combo.addItem(content_type.value.capitalize())
            
    def _populate_styles(self):
        """填充风格下拉框"""
        self.style_combo.clear()
        for style in ContentStyle:
            self.style_combo.addItem(style.value.capitalize())
            
    def _populate_lengths(self):
        """填充长度下拉框"""
        self.length_combo.clear()
        for length in ContentLength:
            self.length_combo.addItem(length.value.capitalize())
            
    def _populate_audiences(self):
        """填充受众下拉框"""
        self.audience_combo.clear()
        for audience in TargetAudience:
            self.audience_combo.addItem(audience.value.capitalize())
            
    def _populate_models(self):
        """填充模型下拉框"""
        self.model_combo.clear()
        self.model_combo.addItem("🤖 自动选择", "auto")
        
        # 添加可用模型
        available_models = [
            ("gpt-4", "GPT-4"),
            ("gpt-3.5", "GPT-3.5"),
            ("claude", "Claude"),
            ("qianwen", "通义千问"),
            ("wenxin", "文心一言"),
            ("zhipu", "智谱AI")
        ]
        
        for model_id, model_name in available_models:
            self.model_combo.addItem(model_name, model_id)
            
    def _populate_template_table(self):
        """填充模板表格"""
        self.template_table.setRowCount(len(self.templates))
        
        for i, template in enumerate(self.templates):
            # 模板名称
            name_item = QTableWidgetItem(template.name)
            self.template_table.setItem(i, 0, name_item)
            
            # 类型
            type_item = QTableWidgetItem(template.content_type.value.capitalize())
            self.template_table.setItem(i, 1, type_item)
            
            # 描述
            desc_item = QTableWidgetItem(template.description)
            self.template_table.setItem(i, 2, desc_item)
            
            # 操作
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            preview_btn = QPushButton("👁️")
            preview_btn.setMaximumWidth(40)
            preview_btn.clicked.connect(lambda checked, t=template: self._preview_template(t))
            actions_layout.addWidget(preview_btn)
            
            use_btn = QPushButton("📝")
            use_btn.setMaximumWidth(40)
            use_btn.clicked.connect(lambda checked, t=template: self._use_template_direct(t))
            actions_layout.addWidget(use_btn)
            
            self.template_table.setCellWidget(i, 3, actions_widget)
            
    def _populate_history_table(self):
        """填充历史记录表格"""
        self.history_table.setRowCount(len(self.generation_history))
        
        for i, response in enumerate(self.generation_history):
            # 时间
            time_item = QTableWidgetItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(response.metadata.get('created_at', time.time()))))
            self.history_table.setItem(i, 0, time_item)
            
            # 类型
            type_item = QTableWidgetItem(response.metadata.get('content_type', 'Unknown'))
            self.history_table.setItem(i, 1, type_item)
            
            # 风格
            style_item = QTableWidgetItem(response.metadata.get('style', 'Unknown'))
            self.history_table.setItem(i, 2, style_item)
            
            # 长度
            length_item = QTableWidgetItem(f"{len(response.content)} 字符")
            self.history_table.setItem(i, 3, length_item)
            
            # 状态
            status_item = QTableWidgetItem("成功" if response.success else "失败")
            self.history_table.setItem(i, 4, status_item)
            
            # 操作
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            load_btn = QPushButton("📝")
            load_btn.setMaximumWidth(40)
            load_btn.clicked.connect(lambda checked, r=response: self._load_history_response(r))
            actions_layout.addWidget(load_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setMaximumWidth(40)
            delete_btn.clicked.connect(lambda checked, idx=i: self._delete_history_item(idx))
            actions_layout.addWidget(delete_btn)
            
            self.history_table.setCellWidget(i, 5, actions_widget)
            
    def _connect_signals(self):
        """连接信号"""
        # 滑块变化
        self.temperature_slider.valueChanged.connect(self._update_temperature_label)
        
        # 模板相关
        self.template_category_combo.currentTextChanged.connect(self._filter_templates)
        self.template_search_input.textChanged.connect(self._filter_templates)
        
    def _update_temperature_label(self, value):
        """更新温度标签"""
        temperature = value / 100.0
        self.temperature_label.setText(f"{temperature:.2f}")
        
    def _filter_templates(self):
        """过滤模板"""
        category = self.template_category_combo.currentText()
        search_text = self.template_search_input.text().lower()
        
        for i in range(self.template_table.rowCount()):
            name_item = self.template_table.item(i, 0)
            type_item = self.template_table.item(i, 1)
            
            if name_item and type_item:
                name = name_item.text().lower()
                content_type = type_item.text().lower()
                
                # 检查分类匹配
                category_match = (category == "全部" or category.lower() in content_type)
                
                # 检查搜索文本匹配
                search_match = (not search_text or search_text in name)
                
                # 显示或隐藏行
                self.template_table.setRowHidden(i, not (category_match and search_match))
                
    def _on_template_selected(self):
        """模板选择"""
        current_row = self.template_table.currentRow()
        if current_row >= 0 and current_row < len(self.templates):
            template = self.templates[current_row]
            self._show_template_details(template)
            
    def _show_template_details(self, template: ContentTemplate):
        """显示模板详情"""
        details = f"""
<h3>{template.name}</h3>
<p><strong>类型:</strong> {template.content_type.value}</p>
<p><strong>描述:</strong> {template.description}</p>
<p><strong>变量:</strong> {', '.join(template.variables)}</p>
<h4>模板内容:</h4>
<pre>{template.template}</pre>
"""
        self.template_details.setHtml(details)
        
    def _on_history_selected(self):
        """历史记录选择"""
        current_row = self.history_table.currentRow()
        if current_row >= 0 and current_row < len(self.generation_history):
            response = self.generation_history[current_row]
            self._show_history_details(response)
            
    def _show_history_details(self, response: ContentGenerationResponse):
        """显示历史详情"""
        details = f"""
<h3>生成详情</h3>
<p><strong>请求ID:</strong> {response.request_id}</p>
<p><strong>内容类型:</strong> {response.metadata.get('content_type', 'Unknown')}</p>
<p><strong>风格:</strong> {response.metadata.get('style', 'Unknown')}</p>
<p><strong>长度:</strong> {len(response.content)} 字符</p>
<p><strong>用时:</strong> {response.generation_time:.2f} 秒</p>
<p><strong>Token数:</strong> {response.tokens_used}</p>
<h4>生成内容:</h4>
<pre>{response.content}</pre>
"""
        self.history_details.setHtml(details)
        
    def _add_keyword(self):
        """添加关键词"""
        keyword = self.keywords_input.text().strip()
        if keyword:
            self.keywords_list.addItem(keyword)
            self.keywords_input.clear()
            
    def _start_generation(self):
        """开始生成内容"""
        prompt = self.prompt_input.toPlainText()
        if not prompt.strip():
            QMessageBox.warning(self, "警告", "请输入生成提示")
            return
            
        # 创建生成请求
        request = self.create_generation_request(prompt)
        self.active_requests[request.request_id] = request
        
        # 显示进度
        self.progress_widget.setVisible(True)
        self.status_label.setText("正在生成内容...")
        self.generate_btn.setEnabled(False)
        
        # 发送信号
        self.generation_started.emit(request.request_id)

        # 开始生成
        asyncio.create_task(self.execute_generation(request))

        # 连接AI服务信号
        self._connect_ai_service_signals()
        
    def create_generation_request(self, prompt: str) -> ContentGenerationRequest:
        """创建生成请求"""
        # 获取关键词
        keywords = []
        for i in range(self.keywords_list.count()):
            keywords.append(self.keywords_list.item(i).text())
        
        return ContentGenerationRequest(
            request_id=f"content_{self.request_counter}",
            content_type=ContentType(self.content_type_combo.currentText().lower()),
            prompt=prompt,
            style=ContentStyle(self.style_combo.currentText().lower()),
            length=ContentLength(self.length_combo.currentText().lower()),
            target_audience=TargetAudience(self.audience_combo.currentText().lower()),
            context=self.context_input.toPlainText(),
            keywords=keywords,
            requirements=self.requirements_input.toPlainText().split('\n'),
            model=self.model_combo.currentData(),
            temperature=self.temperature_slider.value() / 100.0,
            max_tokens=self.max_tokens_spin.value()
        )
        
    async def execute_generation(self, request: ContentGenerationRequest):
        """执行内容生成"""
        start_time = time.time()
        
        try:
            self.generation_progress.emit(request.request_id, 0.0)

            # 构建提示词
            prompt = self.build_generation_prompt(request)

            # 调用AI服务
            ai_request = create_text_generation_request(
                prompt=prompt,
                provider=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            # 提交请求并获取结果
            self.ai_service.submit_request(ai_request)

            # 等待结果（这里需要实现异步等待机制）
            response = await self._wait_for_ai_response(ai_request.request_id)

            if response.success:
                # 后处理生成的内容
                content = self.post_process_content(response.content, request)

                # 创建响应对象
                generation_response = ContentGenerationResponse(
                    request_id=request.request_id,
                    success=True,
                    content=content,
                    keywords=self.extract_keywords(content),
                    metadata={
                        "content_type": request.content_type.value,
                        "style": request.style.value,
                        "length": request.length.value,
                        "target_audience": request.target_audience.value,
                        "model": request.model,
                        "created_at": time.time()
                    },
                    tokens_used=response.usage.get("total_tokens", 0),
                    generation_time=time.time() - start_time
                )
                
                # 更新UI
                self.result_display.setText(content)
                self.status_label.setText("生成完成")
                
                # 添加到历史记录
                self.generation_history.append(generation_response)
                self._populate_history_table()
                
                # 发送信号
                self.generation_completed.emit(request.request_id, generation_response)
                
            else:
                raise Exception(response.error_message or "AI生成失败")
                
        except Exception as e:
            error_response = ContentGenerationResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e)
            )
            
            self.generation_error.emit(request.request_id, str(e))
            self.status_label.setText(f"生成失败: {str(e)}")
            
        finally:
            # 清理请求
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            # 隐藏进度条（延迟）
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
            self.generate_btn.setEnabled(True)
            
    def build_generation_prompt(self, request: ContentGenerationRequest) -> str:
        """构建生成提示词"""
        prompt = f"""
请生成一段{request.content_type.value}内容，要求如下：

主题：{request.prompt}
风格：{request.style.value}
长度：{request.length.value}
目标受众：{request.target_audience.value}
"""
        
        if request.context:
            prompt += f"\n上下文信息：{request.context}"
            
        if request.keywords:
            prompt += f"\n关键词：{', '.join(request.keywords)}"
            
        if request.requirements:
            prompt += f"\n特殊要求：\n"
            for req in request.requirements:
                if req.strip():
                    prompt += f"- {req.strip()}\n"
        
        # 添加具体的生成指导
        prompt += "\n请生成高质量、符合要求的内容。"
        
        if request.content_type == ContentType.COMMENTARY:
            prompt += "内容应该适合作为视频解说，语言生动有趣。"
        elif request.content_type == ContentType.SCRIPT:
            prompt += "内容应该包含场景描述和对话，适合视频拍摄。"
        elif request.content_type == ContentType.COPYWRITING:
            prompt += "内容应该具有吸引力，能够促进转化。"
            
        return prompt
        
    def post_process_content(self, content: str, request: ContentGenerationRequest) -> str:
        """后处理生成的内容"""
        processed = content.strip()
        
        # 自动格式化
        if self.auto_format_check.isChecked():
            processed = self.auto_format_text(processed)
            
        # 添加表情符号
        if self.include_emoji_check.isChecked():
            processed = self.add_emojis(processed, request.style)
            
        # 添加标签
        if self.add_hashtags_check.isChecked():
            processed = self.add_hashtags(processed, request.keywords)
            
        return processed
        
    def auto_format_text(self, text: str) -> str:
        """自动格式化文本"""
        # 简单的格式化处理
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # 确保句子结尾有标点
                if line and line[-1] not in '.。!！?？':
                    line += '。'
                formatted_lines.append(line)
                
        return '\n\n'.join(formatted_lines)
        
    def add_emojis(self, text: str, style: ContentStyle) -> str:
        """添加表情符号"""
        emoji_map = {
            ContentStyle.HUMOROUS: ["😄", "🎉", "🤣", "😂"],
            ContentStyle.EMOTIONAL: ["❤️", "😊", "🥰", "😍"],
            ContentStyle.INSPIRATIONAL: ["✨", "🌟", "💪", "🚀"],
            ContentStyle.PROFESSIONAL: ["💼", "📊", "🎯", "📈"]
        }
        
        emojis = emoji_map.get(style, ["✨"])
        
        # 简单地在段落开头添加表情符号
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            if line.strip() and i % 2 == 0:  # 每隔一行添加表情符号
                emoji = emojis[i % len(emojis)]
                result_lines.append(f"{emoji} {line}")
            else:
                result_lines.append(line)
                
        return '\n'.join(result_lines)
        
    def add_hashtags(self, text: str, keywords: List[str]) -> str:
        """添加标签"""
        if not keywords:
            return text
            
        hashtags = [f"#{keyword}" for keyword in keywords[:5]]  # 最多5个标签
        hashtags_text = " ".join(hashtags)
        
        return f"{text}\n\n{hashtags_text}"
        
    def extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b\w+\b', content.lower())
        
        # 过滤常见词
        stop_words = {'的', '了', '是', '在', '我', '你', '他', '她', '它', '这', '那', '有', '就', '不', '和', '也', '都', '要', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 统计词频
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
            
        # 返回频率最高的词
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:10]]
        
    def _preview_template(self, template: ContentTemplate):
        """预览模板"""
        QMessageBox.information(self, "模板预览", f"模板：{template.name}\n\n{template.template}")
        
    def _use_template_direct(self, template: ContentTemplate):
        """直接使用模板"""
        self._use_template(template)
        
    def _use_template(self):
        """使用选中的模板"""
        current_row = self.template_table.currentRow()
        if current_row >= 0 and current_row < len(self.templates):
            template = self.templates[current_row]
            self._apply_template(template)
            
    def _apply_template(self, template: ContentTemplate):
        """应用模板"""
        # 切换到快速生成标签页
        self.tab_widget.setCurrentIndex(0)
        
        # 设置内容类型
        index = self.content_type_combo.findText(template.content_type.value.capitalize())
        if index >= 0:
            self.content_type_combo.setCurrentIndex(index)
            
        # 在提示词输入框中显示模板
        self.prompt_input.setText(template.template)
        
        # 高亮显示模板变量
        self.highlight_template_variables()
        
        # 发送信号
        self.template_applied.emit(template)
        
        QMessageBox.information(self, "模板应用", f"已应用模板：{template.name}\n\n请将模板中的变量替换为实际内容。")
        
    def highlight_template_variables(self):
        """高亮显示模板变量"""
        # 这里可以实现模板变量的高亮显示
        pass
        
    def _edit_template(self):
        """编辑模板"""
        QMessageBox.information(self, "编辑模板", "模板编辑功能开发中...")
        
    def _load_history_content(self):
        """加载历史内容"""
        current_row = self.history_table.currentRow()
        if current_row >= 0 and current_row < len(self.generation_history):
            response = self.generation_history[current_row]
            self._load_history_response(response)
            
    def _load_history_response(self, response: ContentGenerationResponse):
        """加载历史响应"""
        # 切换到快速生成标签页
        self.tab_widget.setCurrentIndex(0)
        
        # 设置内容类型
        content_type = response.metadata.get('content_type', 'commentary')
        index = self.content_type_combo.findText(content_type.capitalize())
        if index >= 0:
            self.content_type_combo.setCurrentIndex(index)
            
        # 显示内容
        self.result_display.setText(response.content)
        
        QMessageBox.information(self, "历史加载", "已加载历史内容到结果区域。")
        
    def _delete_history_record(self):
        """删除历史记录"""
        current_row = self.history_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "确认删除", "确定要删除这条历史记录吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._delete_history_item(current_row)
                
    def _delete_history_item(self, index: int):
        """删除历史记录项"""
        if 0 <= index < len(self.generation_history):
            del self.generation_history[index]
            self._populate_history_table()
            
    def _clear_all_history(self):
        """清空所有历史"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.generation_history.clear()
            self._populate_history_table()
            
    def _copy_result(self):
        """复制结果"""
        content = self.result_display.toPlainText()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            QMessageBox.information(self, "成功", "内容已复制到剪贴板")
            
    def _edit_result(self):
        """编辑结果"""
        self.result_display.setReadOnly(False)
        self.result_display.setStyleSheet("border: 2px solid #1890ff;")
        QMessageBox.information(self, "编辑模式", "现在可以编辑内容，编辑完成后点击其他区域保存。")
        
    def _save_result(self):
        """保存结果"""
        content = self.result_display.toPlainText()
        if not content:
            QMessageBox.warning(self, "警告", "没有可保存的内容")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存内容", "", "文本文件 (*.txt);;Markdown文件 (*.md);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.content_saved.emit(file_path, content)
                QMessageBox.information(self, "成功", f"内容已保存到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{str(e)}")
                
    def _regenerate_result(self):
        """重新生成结果"""
        if self.prompt_input.toPlainText():
            reply = QMessageBox.question(
                self, "确认重新生成", "确定要重新生成内容吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._start_generation()
        else:
            QMessageBox.warning(self, "警告", "请先输入生成提示")
            
    def _cancel_generation(self):
        """取消生成"""
        # 取消所有活跃的生成请求
        for request_id in list(self.active_requests.keys()):
            self.generation_error.emit(request_id, "用户取消")
            
        self.active_requests.clear()
        self.progress_widget.setVisible(False)
        self.status_label.setText("已取消")
        self.generate_btn.setEnabled(True)
        
    def _load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_setting("content_generator", {})
        
        # 应用设置
        if "default_model" in settings:
            index = self.model_combo.findData(settings["default_model"])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
                
        if "default_temperature" in settings:
            temperature = int(settings["default_temperature"] * 100)
            self.temperature_slider.setValue(temperature)
            
        if "default_style" in settings:
            index = self.style_combo.findText(settings["default_style"].capitalize())
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
                
    def _save_settings(self):
        """保存设置"""
        settings = {
            "default_model": self.model_combo.currentData(),
            "default_temperature": self.temperature_slider.value() / 100.0,
            "default_style": self.style_combo.currentText().lower()
        }
        
        self.settings_manager.set_setting("content_generator", settings)
        
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings()
        super().closeEvent(event)

    def _connect_ai_service_signals(self):
        """连接AI服务信号"""
        # 连接AI服务的信号到组件的信号处理
        self.ai_service.worker_finished.connect(self._on_ai_response)
        self.ai_service.worker_error.connect(self._on_ai_error)

    async def _wait_for_ai_response(self, request_id: str, timeout: float = 60.0) -> AIResponse:
        """等待AI响应"""
        import asyncio

        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.ai_service.get_request_status(request_id)
            if status.get('status') == 'completed':
                return status.get('response', AIResponse(request_id=request_id, success=False, error_message="No response"))
            elif status.get('status') == 'failed':
                return AIResponse(request_id=request_id, success=False, error_message=status.get('error', 'Unknown error'))

            await asyncio.sleep(0.1)

        return AIResponse(request_id=request_id, success=False, error_message="Timeout")

    def _on_ai_response(self, request_id: str, response: AIResponse):
        """处理AI响应"""
        if request_id in self.active_requests:
            request = self.active_requests[request_id]

            if response.success:
                # 后处理生成的内容
                content = self.post_process_content(response.content, request)

                # 创建响应对象
                generation_response = ContentGenerationResponse(
                    request_id=request_id,
                    success=True,
                    content=content,
                    keywords=self.extract_keywords(content),
                    metadata={
                        "content_type": request.content_type.value,
                        "style": request.style.value,
                        "length": request.length.value,
                        "target_audience": request.target_audience.value,
                        "model": request.model,
                        "created_at": time.time()
                    },
                    tokens_used=response.usage.get("total_tokens", 0),
                    generation_time=response.processing_time
                )

                # 更新UI
                self.result_display.setText(content)
                self.status_label.setText("生成完成")

                # 添加到历史记录
                self.generation_history.append(generation_response)
                self._populate_history_table()

                # 发送信号
                self.generation_completed.emit(request_id, generation_response)
            else:
                self.generation_error.emit(request_id, response.error_message)
                self.status_label.setText(f"生成失败: {response.error_message}")

            # 清理请求
            del self.active_requests[request_id]

            # 隐藏进度条（延迟）
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
            self.generate_btn.setEnabled(True)

    def _on_ai_error(self, request_id: str, error_message: str):
        """处理AI错误"""
        if request_id in self.active_requests:
            self.generation_error.emit(request_id, error_message)
            self.status_label.setText(f"生成失败: {error_message}")

            # 清理请求
            del self.active_requests[request_id]

            # 隐藏进度条（延迟）
            QTimer.singleShot(2000, lambda: self.progress_widget.setVisible(False))
            self.generate_btn.setEnabled(True)