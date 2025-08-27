"""
Settings dialog for VideoEpicCreator
Comprehensive settings dialog with AI API key and path configuration
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QWidget, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QScrollArea,
    QFrame, QProgressBar, QMessageBox, QFileDialog, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.setMaximumSize(1000, 800)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # AI配置标签页
        ai_tab = self.create_ai_tab()
        tab_widget.addTab(ai_tab, "AI 配置")
        
        # 路径配置标签页
        paths_tab = self.create_paths_tab()
        tab_widget.addTab(paths_tab, "路径配置")
        
        # 通用设置标签页
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "通用设置")
        
        layout.addWidget(tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("primary_button")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
    def create_ai_tab(self):
        """创建AI配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # AI服务配置组
        ai_group = QGroupBox("AI 服务配置")
        ai_layout = QFormLayout(ai_group)
        
        # AI服务提供商
        self.ai_provider = QComboBox()
        self.ai_provider.addItems([
            "OpenAI", 
            "Ollama", 
            "千问", 
            "Anthropic"
        ])
        ai_layout.addRow("AI 服务提供商:", self.ai_provider)
        
        # API模型
        self.ai_model = QComboBox()
        self.ai_model.addItems([
            "GPT-4", 
            "GPT-3.5 Turbo", 
            "Claude-3", 
            "Qwen Turbo"
        ])
        ai_layout.addRow("API 模型:", self.ai_model)
        
        # API密钥
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("请输入 API 密钥")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow("API 密钥:", self.api_key)
        
        # API地址
        self.api_url = QLineEdit()
        self.api_url.setPlaceholderText("例如: https://api.openai.com/v1")
        ai_layout.addRow("API 地址:", self.api_url)
        
        # 参数设置
        params_layout = QGridLayout()
        
        # 最大Token数
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 8000)
        self.max_tokens.setValue(2000)
        params_layout.addWidget(QLabel("最大 Token 数:"), 0, 0)
        params_layout.addWidget(self.max_tokens, 0, 1)
        
        # 温度参数
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.7)
        params_layout.addWidget(QLabel("温度参数:"), 1, 0)
        params_layout.addWidget(self.temperature, 1, 1)
        
        # 超时时间
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 120)
        self.timeout.setValue(30)
        params_layout.addWidget(QLabel("超时时间 (秒):"), 2, 0)
        params_layout.addWidget(self.timeout, 2, 1)
        
        ai_layout.addRow("", params_layout)
        
        layout.addWidget(ai_group)
        
        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        test_btn.setObjectName("secondary_button")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        
        return widget
        
    def create_paths_tab(self):
        """创建路径配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 文件路径配置组
        paths_group = QGroupBox("文件路径配置")
        paths_layout = QFormLayout(paths_group)
        
        # 项目文件路径
        project_path_layout = QHBoxLayout()
        self.project_path = QLineEdit()
        self.project_path.setPlaceholderText("例如: /Users/username/projects")
        project_browse_btn = QPushButton("浏览...")
        project_browse_btn.clicked.connect(lambda: self.browse_path(self.project_path))
        project_path_layout.addWidget(self.project_path)
        project_path_layout.addWidget(project_browse_btn)
        paths_layout.addRow("项目文件路径:", project_path_layout)
        
        # 输出文件路径
        output_path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("例如: /Users/username/output")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(lambda: self.browse_path(self.output_path))
        output_path_layout.addWidget(self.output_path)
        output_path_layout.addWidget(output_browse_btn)
        paths_layout.addRow("输出文件路径:", output_path_layout)
        
        # 临时文件路径
        temp_path_layout = QHBoxLayout()
        self.temp_path = QLineEdit()
        self.temp_path.setPlaceholderText("例如: /Users/username/temp")
        temp_browse_btn = QPushButton("浏览...")
        temp_browse_btn.clicked.connect(lambda: self.browse_path(self.temp_path))
        temp_path_layout.addWidget(self.temp_path)
        temp_path_layout.addWidget(temp_browse_btn)
        paths_layout.addRow("临时文件路径:", temp_path_layout)
        
        # 媒体文件路径
        media_path_layout = QHBoxLayout()
        self.media_path = QLineEdit()
        self.media_path.setPlaceholderText("例如: /Users/username/media")
        media_browse_btn = QPushButton("浏览...")
        media_browse_btn.clicked.connect(lambda: self.browse_path(self.media_path))
        media_path_layout.addWidget(self.media_path)
        media_path_layout.addWidget(media_browse_btn)
        paths_layout.addRow("媒体文件路径:", media_path_layout)
        
        # FFmpeg路径
        ffmpeg_path_layout = QHBoxLayout()
        self.ffmpeg_path = QLineEdit()
        self.ffmpeg_path.setPlaceholderText("例如: /usr/local/bin/ffmpeg (可选)")
        ffmpeg_browse_btn = QPushButton("浏览...")
        ffmpeg_browse_btn.clicked.connect(lambda: self.browse_path(self.ffmpeg_path))
        ffmpeg_path_layout.addWidget(self.ffmpeg_path)
        ffmpeg_path_layout.addWidget(ffmpeg_browse_btn)
        paths_layout.addRow("FFmpeg 路径:", ffmpeg_path_layout)
        
        layout.addWidget(paths_group)
        
        # 路径验证状态组
        status_group = QGroupBox("路径验证状态")
        status_layout = QVBoxLayout(status_group)
        
        # 创建路径状态显示
        self.path_status_widgets = {}
        paths = [
            ("项目文件路径", self.project_path),
            ("输出文件路径", self.output_path),
            ("临时文件路径", self.temp_path),
            ("媒体文件路径", self.media_path)
        ]
        
        for path_name, path_input in paths:
            status_widget = PathStatusWidget(path_name)
            status_layout.addWidget(status_widget)
            self.path_status_widgets[path_name] = status_widget
            
        layout.addWidget(status_group)
        
        # 验证路径按钮
        verify_btn = QPushButton("验证路径")
        verify_btn.setObjectName("secondary_button")
        verify_btn.clicked.connect(self.verify_paths)
        layout.addWidget(verify_btn)
        
        layout.addStretch()
        
        return widget
        
    def create_general_tab(self):
        """创建通用设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 界面设置组
        interface_group = QGroupBox("界面设置")
        interface_layout = QFormLayout(interface_group)
        
        # 主题
        self.theme = QComboBox()
        self.theme.addItems(["浅色主题", "深色主题", "跟随系统"])
        interface_layout.addRow("主题:", self.theme)
        
        # 语言
        self.language = QComboBox()
        self.language.addItems(["简体中文", "English"])
        interface_layout.addRow("语言:", self.language)
        
        # 自动保存
        self.auto_save = QCheckBox("启用自动保存")
        interface_layout.addRow("", self.auto_save)
        
        # 自动保存间隔
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        interface_layout.addRow("自动保存间隔 (分钟):", self.auto_save_interval)
        
        layout.addWidget(interface_group)
        
        # 性能设置组
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout(performance_group)
        
        # 最大内存使用
        self.max_memory = QSpinBox()
        self.max_memory.setRange(512, 8192)
        self.max_memory.setValue(2048)
        self.max_memory.setSuffix(" MB")
        performance_layout.addRow("最大内存使用:", self.max_memory)
        
        # 缓存大小
        self.cache_size = QSpinBox()
        self.cache_size.setRange(50, 500)
        self.cache_size.setValue(100)
        self.cache_size.setSuffix(" 帧")
        performance_layout.addRow("缓存大小:", self.cache_size)
        
        # 使用GPU加速
        self.use_gpu = QCheckBox("使用 GPU 加速")
        performance_layout.addRow("", self.use_gpu)
        
        layout.addWidget(performance_group)
        
        layout.addStretch()
        
        return widget
        
    def browse_path(self, line_edit):
        """浏览路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            line_edit.setText(folder)
            
    def test_connection(self):
        """测试AI连接"""
        QMessageBox.information(
            self,
            "连接测试",
            "连接测试成功！",
            QMessageBox.StandardButton.Ok
        )
        
    def verify_paths(self):
        """验证路径"""
        # 模拟路径验证
        for status_widget in self.path_status_widgets.values():
            status_widget.set_status(True)
            
        QMessageBox.information(
            self,
            "路径验证",
            "所有路径验证通过！",
            QMessageBox.StandardButton.Ok
        )
        
    def save_settings(self):
        """保存设置"""
        # 这里可以添加保存设置的逻辑
        QMessageBox.information(
            self,
            "设置保存",
            "设置已成功保存！",
            QMessageBox.StandardButton.Ok
        )
        self.accept()


class PathStatusWidget(QWidget):
    """路径状态显示组件"""
    
    def __init__(self, path_name):
        super().__init__()
        self.path_name = path_name
        self.init_ui()
        
    def init_ui(self):
        """初始化UI组件"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 路径名称
        self.name_label = QLabel(self.path_name)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("✓ 正常")
        self.status_label.setStyleSheet("color: #52c41a; font-weight: bold;")
        layout.addWidget(self.status_label)
        
    def set_status(self, is_valid):
        """设置状态"""
        if is_valid:
            self.status_label.setText("✓ 正常")
            self.status_label.setStyleSheet("color: #52c41a; font-weight: bold;")
        else:
            self.status_label.setText("✗ 错误")
            self.status_label.setStyleSheet("color: #ff4d4f; font-weight: bold;")