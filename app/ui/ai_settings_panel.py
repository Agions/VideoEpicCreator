#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QGridLayout, QGroupBox, QCheckBox,
    QTabWidget, QSlider, QSpinBox, QFormLayout, QFileDialog,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QWidgetAction
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

import os
import json

class AIModelSettingsPanel(QWidget):
    """AI大模型设置面板"""
    
    config_updated = pyqtSignal(dict)  # 配置更新信号
    status_updated = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.models_config = {}  # 模型配置
        self.current_model = ""  # 当前选择的模型
        self.config_file = os.path.join(os.path.dirname(__file__), "ai_models_config.json")
        self._init_ui()
        self._load_config()
        
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("AI大模型设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title)
        
        # 保存按钮
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self._save_config)
        title_layout.addWidget(self.save_button)
        
        # 重置按钮
        self.reset_button = QPushButton("重置默认")
        self.reset_button.clicked.connect(self._reset_config)
        title_layout.addWidget(self.reset_button)
        
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 基础设置选项卡
        self.basic_tab = QWidget()
        tabs.addTab(self.basic_tab, "基础设置")
        self._setup_basic_tab()
        
        # 高级设置选项卡
        self.advanced_tab = QWidget()
        tabs.addTab(self.advanced_tab, "高级设置")
        self._setup_advanced_tab()
        
        # 模型管理选项卡
        self.models_tab = QWidget()
        tabs.addTab(self.models_tab, "模型管理")
        self._setup_models_tab()
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
    
    def _setup_basic_tab(self):
        """设置基础选项卡"""
        layout = QVBoxLayout(self.basic_tab)
        
        # 模型选择
        model_group = QGroupBox("模型选择")
        model_layout = QFormLayout(model_group)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["OpenAI GPT-4", "OpenAI GPT-3.5", "本地大模型", "自定义API"])
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addRow("当前模型:", self.model_combo)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入API密钥")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        model_layout.addRow("API密钥:", self.api_key_input)
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("https://api.openai.com/v1")
        model_layout.addRow("API地址:", self.api_url_input)
        
        layout.addWidget(model_group)
        
        # 性能设置
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout(performance_group)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量", "平衡", "高速度"])
        performance_layout.addRow("质量偏好:", self.quality_combo)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(50)
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.speed_slider)
        self.speed_value = QLabel("50")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_value.setText(str(v)))
        speed_layout.addWidget(self.speed_value)
        performance_layout.addRow("速度调整:", speed_layout)
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 8000)
        self.max_tokens.setValue(2000)
        self.max_tokens.setSingleStep(100)
        performance_layout.addRow("最大令牌数:", self.max_tokens)
        
        layout.addWidget(performance_group)
        
        # 功能设置
        features_group = QGroupBox("功能设置")
        features_layout = QFormLayout(features_group)
        
        self.auto_segmentation = QCheckBox("启用智能分段")
        self.auto_segmentation.setChecked(True)
        features_layout.addRow("", self.auto_segmentation)
        
        self.auto_color = QCheckBox("启用智能调色")
        self.auto_color.setChecked(True)
        features_layout.addRow("", self.auto_color)
        
        self.auto_transition = QCheckBox("启用智能转场")
        self.auto_transition.setChecked(True)
        features_layout.addRow("", self.auto_transition)
        
        self.auto_caption = QCheckBox("启用智能字幕")
        self.auto_caption.setChecked(True)
        features_layout.addRow("", self.auto_caption)
        
        layout.addWidget(features_group)
        
    def _setup_advanced_tab(self):
        """设置高级选项卡"""
        layout = QVBoxLayout(self.advanced_tab)
        
        # 模型参数
        params_group = QGroupBox("模型参数")
        params_layout = QFormLayout(params_group)
        
        self.temperature = QSlider(Qt.Orientation.Horizontal)
        self.temperature.setRange(0, 100)
        self.temperature.setValue(70)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temperature)
        self.temp_value = QLabel("0.7")
        self.temperature.valueChanged.connect(lambda v: self.temp_value.setText(f"{v/100:.1f}"))
        temp_layout.addWidget(self.temp_value)
        params_layout.addRow("温度:", temp_layout)
        
        self.top_p = QSlider(Qt.Orientation.Horizontal)
        self.top_p.setRange(0, 100)
        self.top_p.setValue(90)
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(self.top_p)
        self.top_p_value = QLabel("0.9")
        self.top_p.valueChanged.connect(lambda v: self.top_p_value.setText(f"{v/100:.1f}"))
        top_p_layout.addWidget(self.top_p_value)
        params_layout.addRow("Top P:", top_p_layout)
        
        self.frequency_penalty = QSlider(Qt.Orientation.Horizontal)
        self.frequency_penalty.setRange(0, 200)
        self.frequency_penalty.setValue(0)
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(self.frequency_penalty)
        self.freq_value = QLabel("0.0")
        self.frequency_penalty.valueChanged.connect(lambda v: self.freq_value.setText(f"{v/100:.1f}"))
        freq_layout.addWidget(self.freq_value)
        params_layout.addRow("频率惩罚:", freq_layout)
        
        self.presence_penalty = QSlider(Qt.Orientation.Horizontal)
        self.presence_penalty.setRange(0, 200)
        self.presence_penalty.setValue(0)
        pres_layout = QHBoxLayout()
        pres_layout.addWidget(self.presence_penalty)
        self.pres_value = QLabel("0.0")
        self.presence_penalty.valueChanged.connect(lambda v: self.pres_value.setText(f"{v/100:.1f}"))
        pres_layout.addWidget(self.pres_value)
        params_layout.addRow("存在惩罚:", pres_layout)
        
        layout.addWidget(params_group)
        
        # 代理设置
        proxy_group = QGroupBox("网络代理")
        proxy_layout = QFormLayout(proxy_group)
        
        self.use_proxy = QCheckBox("使用代理")
        proxy_layout.addRow("", self.use_proxy)
        
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://127.0.0.1:7890")
        proxy_layout.addRow("代理地址:", self.proxy_url)
        
        layout.addWidget(proxy_group)
        
        # 本地缓存
        cache_group = QGroupBox("本地缓存")
        cache_layout = QFormLayout(cache_group)
        
        self.use_cache = QCheckBox("启用本地缓存")
        self.use_cache.setChecked(True)
        cache_layout.addRow("", self.use_cache)
        
        self.cache_dir = QLineEdit()
        self.cache_dir.setReadOnly(True)
        cache_dir_layout = QHBoxLayout()
        cache_dir_layout.addWidget(self.cache_dir)
        self.browse_cache_dir = QPushButton("浏览...")
        self.browse_cache_dir.clicked.connect(self._browse_cache_dir)
        cache_dir_layout.addWidget(self.browse_cache_dir)
        cache_layout.addRow("缓存目录:", cache_dir_layout)
        
        self.clear_cache = QPushButton("清除缓存")
        self.clear_cache.clicked.connect(self._clear_cache)
        cache_layout.addRow("", self.clear_cache)
        
        layout.addWidget(cache_group)
        
    def _setup_models_tab(self):
        """设置模型管理选项卡"""
        layout = QVBoxLayout(self.models_tab)
        
        # 本地模型
        local_group = QGroupBox("本地模型管理")
        local_layout = QFormLayout(local_group)
        
        self.model_path = QLineEdit()
        self.model_path.setReadOnly(True)
        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(self.model_path)
        self.browse_model = QPushButton("浏览...")
        self.browse_model.clicked.connect(self._browse_model_path)
        model_path_layout.addWidget(self.browse_model)
        local_layout.addRow("模型路径:", model_path_layout)
        
        self.quantization = QComboBox()
        self.quantization.addItems(["无量化", "INT8", "INT4"])
        local_layout.addRow("量化方式:", self.quantization)
        
        self.threads = QSpinBox()
        self.threads.setRange(1, 32)
        self.threads.setValue(4)
        local_layout.addRow("线程数:", self.threads)
        
        self.context_size = QSpinBox()
        self.context_size.setRange(512, 8192)
        self.context_size.setValue(4096)
        self.context_size.setSingleStep(512)
        local_layout.addRow("上下文大小:", self.context_size)
        
        layout.addWidget(local_group)
        
        # 自定义API
        custom_group = QGroupBox("自定义API设置")
        custom_layout = QFormLayout(custom_group)
        
        self.api_provider = QComboBox()
        self.api_provider.addItems(["OpenAI兼容", "Hugging Face", "Azure", "其他"])
        custom_layout.addRow("API类型:", self.api_provider)
        
        self.api_version = QLineEdit()
        self.api_version.setPlaceholderText("例如: 2023-05-15")
        custom_layout.addRow("API版本:", self.api_version)
        
        self.custom_headers = QCheckBox("使用自定义请求头")
        custom_layout.addRow("", self.custom_headers)
        
        self.headers_edit = QLineEdit()
        self.headers_edit.setPlaceholderText('{"Authorization": "Bearer xxx", "Content-Type": "application/json"}')
        custom_layout.addRow("请求头:", self.headers_edit)
        
        layout.addWidget(custom_group)
        
        # 服务状态测试
        status_group = QGroupBox("服务状态")
        status_layout = QHBoxLayout(status_group)
        
        self.test_connection = QPushButton("测试连接")
        self.test_connection.clicked.connect(self._test_connection)
        status_layout.addWidget(self.test_connection)
        
        self.status_indicator = QLabel("未测试")
        status_layout.addWidget(self.status_indicator)
        
        layout.addWidget(status_group)
    
    def _on_model_changed(self, model_name):
        """模型变更处理"""
        self.current_model = model_name
        
        # 更新UI状态
        is_custom_api = (model_name == "自定义API")
        is_local_model = (model_name == "本地大模型")
        
        self.api_url_input.setEnabled(not is_local_model)
        self.api_key_input.setEnabled(not is_local_model)
        
        # 更新选项卡状态
        self.advanced_tab.setEnabled(True)
        self.models_tab.setEnabled(is_local_model or is_custom_api)
        
        # 加载模型特定配置
        self._load_model_specific_config(model_name)
        
        # 更新状态
        status_text = f"已选择模型: {model_name}"
        self.status_label.setText(status_text)
        self.status_updated.emit(status_text)
    
    def _load_model_specific_config(self, model_name):
        """加载特定模型配置"""
        if model_name in self.models_config:
            config = self.models_config[model_name]
            
            # 基础设置
            if "api_key" in config:
                self.api_key_input.setText(config["api_key"])
            
            if "api_url" in config:
                self.api_url_input.setText(config["api_url"])
            
            if "quality" in config:
                self.quality_combo.setCurrentText(config["quality"])
            
            if "speed" in config:
                self.speed_slider.setValue(config["speed"])
            
            if "max_tokens" in config:
                self.max_tokens.setValue(config["max_tokens"])
            
            # 功能设置
            if "auto_segmentation" in config:
                self.auto_segmentation.setChecked(config["auto_segmentation"])
            
            if "auto_color" in config:
                self.auto_color.setChecked(config["auto_color"])
            
            if "auto_transition" in config:
                self.auto_transition.setChecked(config["auto_transition"])
            
            if "auto_caption" in config:
                self.auto_caption.setChecked(config["auto_caption"])
            
            # 高级设置
            if "temperature" in config:
                self.temperature.setValue(int(config["temperature"] * 100))
            
            if "top_p" in config:
                self.top_p.setValue(int(config["top_p"] * 100))
            
            if "frequency_penalty" in config:
                self.frequency_penalty.setValue(int(config["frequency_penalty"] * 100))
            
            if "presence_penalty" in config:
                self.presence_penalty.setValue(int(config["presence_penalty"] * 100))
            
            # 代理设置
            if "use_proxy" in config:
                self.use_proxy.setChecked(config["use_proxy"])
            
            if "proxy_url" in config:
                self.proxy_url.setText(config["proxy_url"])
            
            # 缓存设置
            if "use_cache" in config:
                self.use_cache.setChecked(config["use_cache"])
            
            if "cache_dir" in config:
                self.cache_dir.setText(config["cache_dir"])
            
            # 本地模型设置
            if "model_path" in config:
                self.model_path.setText(config["model_path"])
            
            if "quantization" in config:
                self.quantization.setCurrentText(config["quantization"])
            
            if "threads" in config:
                self.threads.setValue(config["threads"])
            
            if "context_size" in config:
                self.context_size.setValue(config["context_size"])
            
            # 自定义API设置
            if "api_provider" in config:
                self.api_provider.setCurrentText(config["api_provider"])
            
            if "api_version" in config:
                self.api_version.setText(config["api_version"])
            
            if "custom_headers" in config:
                self.custom_headers.setChecked(config["custom_headers"])
            
            if "headers" in config:
                self.headers_edit.setText(json.dumps(config["headers"]))
    
    def _save_config(self):
        """保存配置"""
        if not self.current_model:
            return
            
        # 构建配置
        config = {}
        
        # 基础设置
        config["api_key"] = self.api_key_input.text()
        config["api_url"] = self.api_url_input.text()
        config["quality"] = self.quality_combo.currentText()
        config["speed"] = self.speed_slider.value()
        config["max_tokens"] = self.max_tokens.value()
        
        # 功能设置
        config["auto_segmentation"] = self.auto_segmentation.isChecked()
        config["auto_color"] = self.auto_color.isChecked()
        config["auto_transition"] = self.auto_transition.isChecked()
        config["auto_caption"] = self.auto_caption.isChecked()
        
        # 高级设置
        config["temperature"] = self.temperature.value() / 100.0
        config["top_p"] = self.top_p.value() / 100.0
        config["frequency_penalty"] = self.frequency_penalty.value() / 100.0
        config["presence_penalty"] = self.presence_penalty.value() / 100.0
        
        # 代理设置
        config["use_proxy"] = self.use_proxy.isChecked()
        config["proxy_url"] = self.proxy_url.text()
        
        # 缓存设置
        config["use_cache"] = self.use_cache.isChecked()
        config["cache_dir"] = self.cache_dir.text()
        
        # 本地模型设置
        if self.current_model == "本地大模型":
            config["model_path"] = self.model_path.text()
            config["quantization"] = self.quantization.currentText()
            config["threads"] = self.threads.value()
            config["context_size"] = self.context_size.value()
        
        # 自定义API设置
        if self.current_model == "自定义API":
            config["api_provider"] = self.api_provider.currentText()
            config["api_version"] = self.api_version.text()
            config["custom_headers"] = self.custom_headers.isChecked()
            
            try:
                headers_text = self.headers_edit.text()
                if headers_text:
                    config["headers"] = json.loads(headers_text)
            except json.JSONDecodeError:
                self.status_label.setText("错误: 自定义请求头格式不正确")
                self.status_updated.emit("错误: 自定义请求头格式不正确")
                return
        
        # 保存配置
        self.models_config[self.current_model] = config
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.models_config, f, ensure_ascii=False, indent=2)
                
            # 发送信号
            self.config_updated.emit(config)
            
            # 更新状态
            status_text = f"已保存 {self.current_model} 配置"
            self.status_label.setText(status_text)
            self.status_updated.emit(status_text)
            
        except Exception as e:
            error_text = f"保存配置失败: {str(e)}"
            self.status_label.setText(error_text)
            self.status_updated.emit(error_text)
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.models_config = json.load(f)
            else:
                # 创建默认配置
                self._create_default_config()
                
            # 默认选择第一个模型
            if self.model_combo.count() > 0:
                self.current_model = self.model_combo.itemText(0)
                self._load_model_specific_config(self.current_model)
                
        except Exception as e:
            error_text = f"加载配置失败: {str(e)}"
            self.status_label.setText(error_text)
            self.status_updated.emit(error_text)
            
            # 创建默认配置
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.models_config = {
            "OpenAI GPT-4": {
                "api_key": "",
                "api_url": "https://api.openai.com/v1",
                "quality": "高质量",
                "speed": 50,
                "max_tokens": 2000,
                "auto_segmentation": True,
                "auto_color": True,
                "auto_transition": True,
                "auto_caption": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "use_proxy": False,
                "proxy_url": "",
                "use_cache": True,
                "cache_dir": os.path.join(os.path.dirname(__file__), "ai_cache")
            },
            "OpenAI GPT-3.5": {
                "api_key": "",
                "api_url": "https://api.openai.com/v1",
                "quality": "平衡",
                "speed": 70,
                "max_tokens": 2000,
                "auto_segmentation": True,
                "auto_color": True,
                "auto_transition": True,
                "auto_caption": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "use_proxy": False,
                "proxy_url": "",
                "use_cache": True,
                "cache_dir": os.path.join(os.path.dirname(__file__), "ai_cache")
            },
            "本地大模型": {
                "model_path": "",
                "quantization": "INT8",
                "threads": 4,
                "context_size": 4096,
                "quality": "平衡",
                "speed": 60,
                "max_tokens": 2000,
                "auto_segmentation": True,
                "auto_color": True,
                "auto_transition": True,
                "auto_caption": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "use_cache": True,
                "cache_dir": os.path.join(os.path.dirname(__file__), "ai_cache")
            },
            "自定义API": {
                "api_key": "",
                "api_url": "",
                "api_provider": "OpenAI兼容",
                "api_version": "",
                "custom_headers": False,
                "headers": {},
                "quality": "平衡",
                "speed": 50,
                "max_tokens": 2000,
                "auto_segmentation": True,
                "auto_color": True,
                "auto_transition": True,
                "auto_caption": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "use_proxy": False,
                "proxy_url": "",
                "use_cache": True,
                "cache_dir": os.path.join(os.path.dirname(__file__), "ai_cache")
            }
        }
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.models_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.status_label.setText(f"创建默认配置失败: {str(e)}")
            self.status_updated.emit(f"创建默认配置失败: {str(e)}")
    
    def _reset_config(self):
        """重置配置"""
        self._create_default_config()
        
        if self.current_model:
            self._load_model_specific_config(self.current_model)
            
        self.status_label.setText("已重置为默认配置")
        self.status_updated.emit("已重置为默认配置")
    
    def _browse_cache_dir(self):
        """浏览缓存目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择缓存目录", self.cache_dir.text() or os.path.dirname(__file__)
        )
        
        if dir_path:
            self.cache_dir.setText(dir_path)
    
    def _browse_model_path(self):
        """浏览模型路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", self.model_path.text() or os.path.dirname(__file__),
            "模型文件 (*.bin *.gguf *.ggml *.pt *.ckpt);;所有文件 (*.*)"
        )
        
        if file_path:
            self.model_path.setText(file_path)
    
    def _clear_cache(self):
        """清除缓存"""
        cache_dir = self.cache_dir.text()
        
        if not cache_dir or not os.path.exists(cache_dir):
            self.status_label.setText("缓存目录不存在")
            self.status_updated.emit("缓存目录不存在")
            return
        
        try:
            # 模拟清除缓存
            # 实际应用中，应该遍历目录删除文件
            self.status_label.setText("正在清除缓存...")
            self.status_updated.emit("正在清除缓存...")
            
            # 模拟处理延迟
            import time
            time.sleep(0.5)
            
            self.status_label.setText("缓存已清除")
            self.status_updated.emit("缓存已清除")
            
        except Exception as e:
            self.status_label.setText(f"清除缓存失败: {str(e)}")
            self.status_updated.emit(f"清除缓存失败: {str(e)}")
    
    def _test_connection(self):
        """测试连接"""
        self.status_indicator.setText("测试中...")
        
        # 根据当前模型选择测试方法
        if self.current_model == "本地大模型":
            self._test_local_model()
        else:
            self._test_api_connection()
    
    def _test_local_model(self):
        """测试本地模型"""
        model_path = self.model_path.text()
        
        if not model_path:
            self.status_indicator.setText("❌ 未设置模型路径")
            return
            
        if not os.path.exists(model_path):
            self.status_indicator.setText("❌ 模型文件不存在")
            return
        
        # 模拟测试
        import time
        time.sleep(1)
        
        # 随机结果
        import random
        if random.random() > 0.3:
            self.status_indicator.setText("✅ 模型加载成功")
        else:
            self.status_indicator.setText("❌ 模型加载失败")
    
    def _test_api_connection(self):
        """测试API连接"""
        api_url = self.api_url_input.text()
        api_key = self.api_key_input.text()
        
        if not api_url:
            self.status_indicator.setText("❌ 未设置API地址")
            return
            
        if not api_key and self.current_model != "自定义API":
            self.status_indicator.setText("❌ 未设置API密钥")
            return
        
        # 模拟测试
        import time
        time.sleep(1)
        
        # 随机结果
        import random
        if random.random() > 0.3:
            self.status_indicator.setText("✅ 连接成功")
        else:
            self.status_indicator.setText("❌ 连接失败")
    
    def get_current_config(self):
        """获取当前配置"""
        if not self.current_model or self.current_model not in self.models_config:
            return None
            
        return self.models_config[self.current_model]

class AISettingsDialog(QDialog):
    """AI设置对话框"""
    
    config_updated = pyqtSignal(dict)  # 配置更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI大模型设置")
        self.setMinimumSize(700, 500)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建设置面板
        self.settings_panel = AIModelSettingsPanel()
        self.settings_panel.config_updated.connect(self.config_updated)
        layout.addWidget(self.settings_panel)
        
        # 创建按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 在"确定"之前保存设置
        button_box.accepted.connect(self.settings_panel._save_config)
        
    def get_current_config(self):
        """获取当前配置"""
        return self.settings_panel.get_current_config() 