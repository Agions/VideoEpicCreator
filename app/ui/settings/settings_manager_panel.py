#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置管理面板
实现专业的设置菜单系统，集成到主界面的设置菜单中

设置分类：
├── 通用设置
│   ├── 界面主题
│   ├── 语言设置
│   ├── 启动选项
│   └── 自动更新
├── AI服务设置
│   ├── 模型配置
│   ├── API密钥
│   ├── 成本控制
│   └── 负载均衡
├── 视频处理设置
│   ├── 硬件加速
│   ├── 编解码器
│   ├── 性能优化
│   └── 缓存设置
├── 项目设置
│   ├── 默认路径
│   ├── 自动保存
│   ├── 版本控制
│   └── 备份设置
└── 高级设置
    ├── 日志级别
    ├── 调试模式
    ├── 网络配置
    └── 重置设置
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSplitter, QStackedWidget,
    QGroupBox, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QSlider, QTabWidget, QFormLayout,
    QDialog, QDialogButtonBox, QMessageBox, QProgressBar, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings
from PyQt6.QtGui import QFont, QIcon, QPainter, QColor

from app.ui.components.base_component import BaseComponent
from app.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsCategory(Enum):
    """设置分类"""
    GENERAL = "general"           # 通用设置
    AI_SERVICES = "ai_services"   # AI服务设置
    VIDEO_PROCESSING = "video_processing"  # 视频处理设置
    PROJECTS = "projects"         # 项目设置
    ADVANCED = "advanced"         # 高级设置


class SettingType(Enum):
    """设置项类型"""
    BOOLEAN = "boolean"           # 布尔值
    STRING = "string"             # 字符串
    INTEGER = "integer"           # 整数
    FLOAT = "float"               # 浮点数
    COMBO = "combo"               # 下拉选择
    MULTILINE = "multiline"       # 多行文本
    PASSWORD = "password"         # 密码
    PATH = "path"                 # 路径选择
    COLOR = "color"               # 颜色选择


@dataclass
class SettingItem:
    """设置项定义"""
    key: str
    title: str
    description: str = ""
    type: SettingType = SettingType.STRING
    default_value: Any = None
    options: List[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    validator: Optional[Callable] = None
    category: SettingsCategory = SettingsCategory.GENERAL
    section: str = "通用"
    visible: bool = True
    enabled: bool = True

    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.default_value is None:
            self.default_value = self._get_default_by_type()

    def _get_default_by_type(self) -> Any:
        """根据类型获取默认值"""
        defaults = {
            SettingType.BOOLEAN: False,
            SettingType.STRING: "",
            SettingType.INTEGER: 0,
            SettingType.FLOAT: 0.0,
            SettingType.COMBO: self.options[0] if self.options else "",
            SettingType.MULTILINE: "",
            SettingType.PASSWORD: "",
            SettingType.PATH: "",
            SettingType.COLOR: "#000000"
        }
        return defaults.get(self.type, "")


@dataclass
class SettingSection:
    """设置分组"""
    id: str
    title: str
    icon: Optional[str] = None
    description: str = ""
    items: List[SettingItem] = field(default_factory=list)


class SettingsPanelWidget(BaseComponent):
    """设置面板控件"""

    # 信号定义
    setting_changed = pyqtSignal(str, object)  # 设置改变信号
    settings_applied = pyqtSignal()             # 设置应用信号
    settings_reset = pyqtSignal()              # 设置重置信号

    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self.settings_manager: Optional[SettingsManager] = None
        self.setting_widgets: Dict[str, QWidget] = {}
        self.setting_items: Dict[str, SettingItem] = {}
        self.current_values: Dict[str, Any] = {}
        self.modified_settings: Dict[str, Any] = {}

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 应用设置面板样式
        self.setObjectName("settingsPanelWidget")

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 创建侧边栏
        self.sidebar = self._create_sidebar()
        self.sidebar.setFixedWidth(200)
        splitter.addWidget(self.sidebar)

        # 创建主内容区域
        self.content_area = self._create_content_area()
        splitter.addWidget(self.content_area)

        # 设置分割器比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 600])

    def _create_sidebar(self) -> QWidget:
        """创建侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("settingsSidebar")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title_label = QLabel("设置")
        title_label.setObjectName("settingsTitle")
        title_label.setFixedHeight(50)
        layout.addWidget(title_label)

        # 分类列表
        self.category_list = self._create_category_list()
        layout.addWidget(self.category_list)

        layout.addStretch()

        return sidebar

    def _create_category_list(self) -> QWidget:
        """创建分类列表"""
        container = QWidget()
        container.setObjectName("categoryContainer")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 创建分类按钮
        categories = [
            ("general", "通用设置", "⚙️"),
            ("ai_services", "AI服务", "🤖"),
            ("video_processing", "视频处理", "🎬"),
            ("projects", "项目管理", "📁"),
            ("advanced", "高级设置", "⚡")
        ]

        self.category_buttons = {}
        for category_id, title, icon in categories:
            button = QPushButton(f"  {icon}  {title}")
            button.setObjectName("categoryButton")
            button.setProperty("category", category_id)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, cid=category_id: self._on_category_clicked(cid))
            layout.addWidget(button)
            self.category_buttons[category_id] = button

        # 默认选中第一个
        self.category_buttons["general"].setChecked(True)

        return container

    def _create_content_area(self) -> QScrollArea:
        """创建主内容区域"""
        scroll_area = QScrollArea()
        scroll_area.setObjectName("settingsContentArea")
        scroll_area.setWidgetResizable(True)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(16)

        scroll_area.setWidget(self.content_widget)
        return scroll_area

    def _setup_connections(self):
        """设置信号连接"""
        pass

    def set_settings_manager(self, settings_manager: SettingsManager):
        """设置设置管理器"""
        self.settings_manager = settings_manager
        self._load_default_settings()

    def _load_default_settings(self):
        """加载默认设置项"""
        # 通用设置
        general_settings = [
            SettingItem(
                key="ui.theme",
                title="界面主题",
                description="选择应用界面主题",
                type=SettingType.COMBO,
                default_value="professional_dark",
                options=["professional_light", "professional_dark", "high_contrast_light", "high_contrast_dark"]
            ),
            SettingItem(
                key="ui.language",
                title="界面语言",
                description="选择界面显示语言",
                type=SettingType.COMBO,
                default_value="zh_CN",
                options=["zh_CN", "en_US"]
            ),
            SettingItem(
                key="ui.show_splash",
                title="显示启动画面",
                description="应用启动时显示启动画面",
                type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingItem(
                key="ui.auto_check_updates",
                title="自动检查更新",
                description="启动时自动检查是否有新版本",
                type=SettingType.BOOLEAN,
                default_value=True
            )
        ]

        # AI服务设置
        ai_settings = [
            SettingItem(
                key="ai.default_provider",
                title="默认AI提供商",
                description="选择默认使用的AI服务提供商",
                type=SettingType.COMBO,
                default_value="openai",
                options=["openai", "qianwen", "wenxin", "zhipuai", "xunfei", "hunyuan", "deepseek", "ollama"]
            ),
            SettingItem(
                key="ai.budget_limit",
                title="月度预算限制",
                description="设置AI服务的月度使用预算限制（美元）",
                type=SettingType.FLOAT,
                default_value=100.0,
                min_value=0.0,
                max_value=10000.0,
                step=10.0
            ),
            SettingItem(
                key="ai.enable_cost_optimization",
                title="启用成本优化",
                description="自动优化AI模型选择以降低成本",
                type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingItem(
                key="ai.cache_responses",
                title="缓存AI响应",
                description="缓存AI生成的响应以提高性能",
                type=SettingType.BOOLEAN,
                default_value=True
            )
        ]

        # 视频处理设置
        video_settings = [
            SettingItem(
                key="video.hardware_acceleration",
                title="启用硬件加速",
                description="使用GPU加速视频处理",
                type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingItem(
                key="video.default_codec",
                title="默认编码器",
                description="选择默认的视频编码器",
                type=SettingType.COMBO,
                default_value="h264",
                options=["h264", "h265", "prores", "dnxhd"]
            ),
            SettingItem(
                key="video.preview_quality",
                title="预览质量",
                description="视频预览的质量等级",
                type=SettingType.COMBO,
                default_value="high",
                options=["low", "medium", "high", "ultra"]
            ),
            SettingItem(
                key="video.cache_size",
                title="缓存大小(GB)",
                description="视频处理缓存大小",
                type=SettingType.INTEGER,
                default_value=8,
                min_value=1,
                max_value=64,
                step=1
            )
        ]

        # 项目设置
        project_settings = [
            SettingItem(
                key="project.default_path",
                title="默认项目路径",
                description="新项目的默认保存路径",
                type=SettingType.PATH,
                default_value=""
            ),
            SettingItem(
                key="project.auto_save",
                title="自动保存",
                description="定期自动保存项目",
                type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingItem(
                key="project.auto_save_interval",
                title="自动保存间隔(分钟)",
                description="自动保存的时间间隔",
                type=SettingType.INTEGER,
                default_value=5,
                min_value=1,
                max_value=60,
                step=1
            ),
            SettingItem(
                key="project.create_backups",
                title="创建备份",
                description="自动创建项目备份",
                type=SettingType.BOOLEAN,
                default_value=True
            )
        ]

        # 高级设置
        advanced_settings = [
            SettingItem(
                key="advanced.log_level",
                title="日志级别",
                description="应用程序的日志记录级别",
                type=SettingType.COMBO,
                default_value="INFO",
                options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            ),
            SettingItem(
                key="advanced.enable_debug_mode",
                title="启用调试模式",
                description="启用调试模式以获取详细信息",
                type=SettingType.BOOLEAN,
                default_value=False
            ),
            SettingItem(
                key="advanced.max_thread_count",
                title="最大线程数",
                description="处理任务的最大线程数",
                type=SettingType.INTEGER,
                default_value=8,
                min_value=1,
                max_value=32,
                step=1
            ),
            SettingItem(
                key="advanced.enable_gpu_acceleration",
                title="启用GPU加速",
                description="启用GPU加速计算（如果可用）",
                type=SettingType.BOOLEAN,
                default_value=True
            )
        ]

        # 组织设置项
        self.all_settings = {
            SettingsCategory.GENERAL: general_settings,
            SettingsCategory.AI_SERVICES: ai_settings,
            SettingsCategory.VIDEO_PROCESSING: video_settings,
            SettingsCategory.PROJECTS: project_settings,
            SettingsCategory.ADVANCED: advanced_settings
        }

        # 加载当前分类
        self._load_category_settings(SettingsCategory.GENERAL)

    def _load_category_settings(self, category: SettingsCategory):
        """加载指定分类的设置"""
        # 清空当前内容
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.deleteLater()

        # 加载设置项
        if category in self.all_settings:
            settings_items = self.all_settings[category]

            # 按section分组
            sections = {}
            for item in settings_items:
                if item.section not in sections:
                    sections[item.section] = []
                sections[item.section].append(item)

            # 创建分组容器
            for section_title, items in sections.items():
                group_box = self._create_settings_group(section_title, items)
                self.content_layout.addWidget(group_box)

        # 添加底部按钮
        self.content_layout.addStretch()
        button_layout = self._create_action_buttons()
        self.content_layout.addLayout(button_layout)

    def _create_settings_group(self, title: str, items: List[SettingItem]) -> QGroupBox:
        """创建设置分组"""
        group_box = QGroupBox(title)
        group_box.setObjectName("settingsGroupBox")

        layout = QFormLayout(group_box)
        layout.setSpacing(12)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for item in items:
            if not item.visible:
                continue

            # 创建标签
            label = QLabel(item.title)
            label.setObjectName("settingLabel")
            if item.description:
                label.setToolTip(item.description)

            # 创建控件
            widget = self._create_setting_widget(item)
            widget.setEnabled(item.enabled)
            widget.setProperty("settingKey", item.key)

            # 添加到布局
            layout.addRow(label, widget)

            # 保存引用
            self.setting_widgets[item.key] = widget
            self.setting_items[item.key] = item

            # 加载当前值
            current_value = self._get_setting_value(item)
            self._set_widget_value(widget, item, current_value)
            self.current_values[item.key] = current_value

        return group_box

    def _create_setting_widget(self, item: SettingItem) -> QWidget:
        """创建设置控件"""
        if item.type == SettingType.BOOLEAN:
            widget = QCheckBox()
            widget.stateChanged.connect(lambda state, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.STRING:
            widget = QLineEdit()
            widget.textChanged.connect(lambda text, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.INTEGER:
            widget = QSpinBox()
            if item.min_value is not None:
                widget.setMinimum(int(item.min_value))
            if item.max_value is not None:
                widget.setMaximum(int(item.max_value))
            if item.step is not None:
                widget.setSingleStep(int(item.step))
            widget.valueChanged.connect(lambda value, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.FLOAT:
            widget = QDoubleSpinBox()
            if item.min_value is not None:
                widget.setMinimum(item.min_value)
            if item.max_value is not None:
                widget.setMaximum(item.max_value)
            if item.step is not None:
                widget.setSingleStep(item.step)
            widget.valueChanged.connect(lambda value, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.COMBO:
            widget = QComboBox()
            widget.addItems(item.options)
            widget.currentTextChanged.connect(lambda text, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.MULTILINE:
            widget = QTextEdit()
            widget.textChanged.connect(lambda: self._on_setting_changed(item.key))

        elif item.type == SettingType.PASSWORD:
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.textChanged.connect(lambda text, key=item.key: self._on_setting_changed(key))

        elif item.type == SettingType.PATH:
            path_widget = QWidget()
            path_layout = QHBoxLayout(path_widget)
            path_layout.setContentsMargins(0, 0, 0, 0)

            line_edit = QLineEdit()
            browse_button = QPushButton("浏览...")

            path_layout.addWidget(line_edit)
            path_layout.addWidget(browse_button)

            line_edit.textChanged.connect(lambda text, key=item.key: self._on_setting_changed(key))
            browse_button.clicked.connect(lambda: self._browse_for_path(line_edit))

            widget = path_widget

        else:
            widget = QLineEdit()
            widget.textChanged.connect(lambda text, key=item.key: self._on_setting_changed(key))

        return widget

    def _get_setting_value(self, item: SettingItem) -> Any:
        """获取设置值"""
        if self.settings_manager:
            return self.settings_manager.get_setting(item.key, item.default_value)
        return item.default_value

    def _set_widget_value(self, widget: QWidget, item: SettingItem, value: Any):
        """设置控件值"""
        if item.type == SettingType.BOOLEAN:
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))

        elif item.type in [SettingType.STRING, SettingType.PASSWORD, SettingType.MULTILINE]:
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))

        elif item.type == SettingType.INTEGER:
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))

        elif item.type == SettingType.FLOAT:
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))

        elif item.type == SettingType.COMBO:
            if isinstance(widget, QComboBox):
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)

    def _on_setting_changed(self, key: str):
        """设置值改变处理"""
        widget = self.setting_widgets.get(key)
        item = self.setting_items.get(key)

        if widget and item:
            new_value = self._get_widget_value(widget, item)
            old_value = self.current_values.get(key)

            if new_value != old_value:
                self.modified_settings[key] = new_value
                self.setting_changed.emit(key, new_value)

    def _get_widget_value(self, widget: QWidget, item: SettingItem) -> Any:
        """获取控件值"""
        if item.type == SettingType.BOOLEAN:
            return widget.isChecked() if isinstance(widget, QCheckBox) else False

        elif item.type in [SettingType.STRING, SettingType.PASSWORD]:
            return widget.text() if isinstance(widget, QLineEdit) else ""

        elif item.type == SettingType.MULTILINE:
            return widget.toPlainText() if isinstance(widget, QTextEdit) else ""

        elif item.type == SettingType.INTEGER:
            return widget.value() if isinstance(widget, QSpinBox) else 0

        elif item.type == SettingType.FLOAT:
            return widget.value() if isinstance(widget, QDoubleSpinBox) else 0.0

        elif item.type == SettingType.COMBO:
            return widget.currentText() if isinstance(widget, QComboBox) else ""

        return None

    def _browse_for_path(self, line_edit: QLineEdit):
        """浏览路径"""
        from PyQt6.QtWidgets import QFileDialog

        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", line_edit.text()
        )

        if directory:
            line_edit.setText(directory)

    def _on_category_clicked(self, category_id: str):
        """分类点击处理"""
        # 更新按钮状态
        for button in self.category_buttons.values():
            button.setChecked(False)
        self.category_buttons[category_id].setChecked(True)

        # 加载对应分类的设置
        category_map = {
            "general": SettingsCategory.GENERAL,
            "ai_services": SettingsCategory.AI_SERVICES,
            "video_processing": SettingsCategory.VIDEO_PROCESSING,
            "projects": SettingsCategory.PROJECTS,
            "advanced": SettingsCategory.ADVANCED
        }

        if category_id in category_map:
            self._load_category_settings(category_map[category_id])

    def _create_action_buttons(self) -> QHBoxLayout:
        """创建操作按钮"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # 应用按钮
        apply_button = QPushButton("应用")
        apply_button.setObjectName("applyButton")
        apply_button.clicked.connect(self._apply_settings)
        layout.addWidget(apply_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancelButton")
        cancel_button.clicked.connect(self._cancel_changes)
        layout.addWidget(cancel_button)

        # 重置按钮
        reset_button = QPushButton("重置")
        reset_button.setObjectName("resetButton")
        reset_button.clicked.connect(self._reset_settings)
        layout.addWidget(reset_button)

        layout.addStretch()

        return layout

    def _apply_settings(self):
        """应用设置"""
        if not self.modified_settings:
            return

        try:
            if self.settings_manager:
                for key, value in self.modified_settings.items():
                    self.settings_manager.set_setting(key, value)

            self.settings_applied.emit()
            self.modified_settings.clear()

            QMessageBox.information(self, "设置", "设置已成功应用")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用设置失败: {str(e)}")

    def _cancel_changes(self):
        """取消更改"""
        self.modified_settings.clear()

        # 恢复原始值
        for key, widget in self.setting_widgets.items():
            item = self.setting_items.get(key)
            if item:
                original_value = self.current_values.get(key)
                self._set_widget_value(widget, item, original_value)

    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "重置设置",
            "确定要重置所有设置为默认值吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.settings_manager:
                    self.settings_manager.reset_to_defaults()

                self.settings_reset.emit()
                self.modified_settings.clear()

                # 重新加载当前分类
                for button in self.category_buttons.values():
                    if button.isChecked():
                        category_id = button.property("category")
                        self._on_category_clicked(category_id)
                        break

                QMessageBox.information(self, "设置", "设置已重置为默认值")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置设置失败: {str(e)}")


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(900, 600)

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建设置面板
        self.settings_panel = SettingsPanelWidget()
        self.settings_panel.set_settings_manager(self.settings_manager)
        layout.addWidget(self.settings_panel)

        # 连接信号
        self.settings_panel.settings_applied.connect(self.accept)
        self.settings_panel.settings_reset.connect(self._on_settings_reset)

    def _on_settings_reset(self):
        """设置重置处理"""
        # 重新加载设置
        self.settings_panel._load_default_settings()