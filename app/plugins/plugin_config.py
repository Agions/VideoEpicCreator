#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件配置系统
提供插件配置管理、验证和UI生成功能
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
                            QCheckBox, QTextEdit, QGroupBox, QScrollArea,
                            QPushButton, QFormLayout, QSlider, QColorDialog)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QRegularExpressionValidator

from .plugin_system import PluginMetadata, PluginContext

logger = logging.getLogger(__name__)


@dataclass
class ConfigField:
    """配置字段定义"""
    name: str                           # 字段名
    label: str                          # 显示标签
    type: str                           # 字段类型
    description: str = ""                # 描述
    default: Any = None                 # 默认值
    required: bool = False              # 是否必需
    min_value: Optional[Union[int, float]] = None  # 最小值
    max_value: Optional[Union[int, float]] = None  # 最大值
    options: List[Dict[str, Any]] = field(default_factory=list)  # 选项列表
    pattern: str = ""                   # 正则表达式
    placeholder: str = ""               # 占位符文本
    advanced: bool = False             # 是否高级选项


@dataclass
class ConfigSection:
    """配置分区"""
    name: str                           # 分区名
    label: str                          # 显示标签
    description: str = ""                # 描述
    fields: List[ConfigField] = field(default_factory=list)  # 字段列表
    collapsible: bool = True            # 是否可折叠


class PluginConfigSchema:
    """插件配置架构"""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.sections: List[ConfigSection] = []
        self.global_settings: List[ConfigField] = []

    def add_section(self, section: ConfigSection):
        """添加配置分区"""
        self.sections.append(section)

    def add_field(self, section_name: str, field: ConfigField):
        """添加配置字段"""
        for section in self.sections:
            if section.name == section_name:
                section.fields.append(field)
                break
        else:
            # 创建新分区
            section = ConfigSection(name=section_name, label=section_name)
            section.fields.append(field)
            self.sections.append(section)

    def get_field(self, field_name: str) -> Optional[ConfigField]:
        """获取字段定义"""
        for section in self.sections:
            for field in section.fields:
                if field.name == field_name:
                    return field
        return None

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证配置"""
        errors = []

        for section in self.sections:
            for field in section.fields:
                value = config.get(field.name, field.default)

                # 检查必需字段
                if field.required and value is None:
                    errors.append(f"必需字段 '{field.label}' 未设置")
                    continue

                # 类型验证
                if value is not None:
                    try:
                        self._validate_field_type(field, value)
                    except ValueError as e:
                        errors.append(f"字段 '{field.label}': {str(e)}")

                # 范围验证
                if value is not None and field.min_value is not None:
                    if value < field.min_value:
                        errors.append(f"字段 '{field.label}' 值不能小于 {field.min_value}")

                if value is not None and field.max_value is not None:
                    if value > field.max_value:
                        errors.append(f"字段 '{field.label}' 值不能大于 {field.max_value}")

                # 正则验证
                if field.pattern and isinstance(value, str):
                    import re
                    if not re.match(field.pattern, value):
                        errors.append(f"字段 '{field.label}' 格式不正确")

        return len(errors) == 0, errors

    def _validate_field_type(self, field: ConfigField, value: Any):
        """验证字段类型"""
        type_map = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'text': str,
            'select': str,
            'multiselect': list,
            'color': str,
            'file': str,
            'directory': str
        }

        expected_type = type_map.get(field.type)
        if expected_type and not isinstance(value, expected_type):
            raise ValueError(f"期望类型 {expected_type.__name__}, 实际类型 {type(value).__name__}")

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        config = {}
        for section in self.sections:
            for field in section.fields:
                config[field.name] = field.default
        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plugin_name": self.plugin_name,
            "sections": [asdict(section) for section in self.sections]
        }


class ConfigWidgetFactory:
    """配置控件工厂"""

    @staticmethod
    def create_widget(field: ConfigField, parent=None) -> QWidget:
        """创建配置控件"""
        if field.type == 'string':
            return ConfigWidgetFactory._create_string_widget(field, parent)
        elif field.type == 'integer':
            return ConfigWidgetFactory._create_integer_widget(field, parent)
        elif field.type == 'float':
            return ConfigWidgetFactory._create_float_widget(field, parent)
        elif field.type == 'boolean':
            return ConfigWidgetFactory._create_boolean_widget(field, parent)
        elif field.type == 'text':
            return ConfigWidgetFactory._create_text_widget(field, parent)
        elif field.type == 'select':
            return ConfigWidgetFactory._create_select_widget(field, parent)
        elif field.type == 'color':
            return ConfigWidgetFactory._create_color_widget(field, parent)
        else:
            return ConfigWidgetFactory._create_string_widget(field, parent)

    @staticmethod
    def _create_string_widget(field: ConfigField, parent) -> QLineEdit:
        """创建字符串输入控件"""
        widget = QLineEdit(parent)
        if field.placeholder:
            widget.setPlaceholderText(field.placeholder)
        if field.pattern:
            validator = QRegularExpressionValidator(field.pattern)
            widget.setValidator(validator)
        if field.default:
            widget.setText(str(field.default))
        return widget

    @staticmethod
    def _create_integer_widget(field: ConfigField, parent) -> QSpinBox:
        """创建整数输入控件"""
        widget = QSpinBox(parent)
        if field.min_value is not None:
            widget.setMinimum(field.min_value)
        if field.max_value is not None:
            widget.setMaximum(field.max_value)
        if field.default is not None:
            widget.setValue(field.default)
        return widget

    @staticmethod
    def _create_float_widget(field: ConfigField, parent) -> QDoubleSpinBox:
        """创建浮点数输入控件"""
        widget = QDoubleSpinBox(parent)
        if field.min_value is not None:
            widget.setMinimum(field.min_value)
        if field.max_value is not None:
            widget.setMaximum(field.max_value)
        widget.setDecimals(2)
        if field.default is not None:
            widget.setValue(field.default)
        return widget

    @staticmethod
    def _create_boolean_widget(field: ConfigField, parent) -> QCheckBox:
        """创建布尔值控件"""
        widget = QCheckBox(field.label, parent)
        if field.default is not None:
            widget.setChecked(field.default)
        return widget

    @staticmethod
    def _create_text_widget(field: ConfigField, parent) -> QTextEdit:
        """创建文本输入控件"""
        widget = QTextEdit(parent)
        if field.placeholder:
            widget.setPlaceholderText(field.placeholder)
        if field.default:
            widget.setPlainText(str(field.default))
        widget.setMaximumHeight(100)
        return widget

    @staticmethod
    def _create_select_widget(field: ConfigField, parent) -> QComboBox:
        """创建选择控件"""
        widget = QComboBox(parent)
        for option in field.options:
            if isinstance(option, dict):
                widget.addItem(option.get('label', option.get('value')), option.get('value'))
            else:
                widget.addItem(str(option), option)

        if field.default is not None:
            index = widget.findData(field.default)
            if index >= 0:
                widget.setCurrentIndex(index)
        return widget

    @staticmethod
    def _create_color_widget(field: ConfigField, parent) -> QWidget:
        """创建颜色选择控件"""
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(container)
        button = QPushButton("选择", container)
        button.setMaximumWidth(60)

        def choose_color():
            from PyQt6.QtGui import QColor
            current_color = QColor(line_edit.text())
            color = QColorDialog.getColor(current_color, container)
            if color.isValid():
                line_edit.setText(color.name())

        button.clicked.connect(choose_color)
        layout.addWidget(line_edit)
        layout.addWidget(button)

        if field.default:
            line_edit.setText(field.default)

        return container


class PluginConfigWidget(QWidget):
    """插件配置界面"""

    config_changed = pyqtSignal(dict)  # 新配置值

    def __init__(self, schema: PluginConfigSchema, parent=None):
        super().__init__(parent)
        self.schema = schema
        self.widgets: Dict[str, QWidget] = {}
        self.current_config = schema.get_default_config()
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 添加配置分区
        for section in self.schema.sections:
            group_box = self._create_section_widget(section)
            scroll_layout.addWidget(group_box)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # 添加按钮
        button_layout = QHBoxLayout()
        reset_button = QPushButton("重置", self)
        save_button = QPushButton("保存", self)

        reset_button.clicked.connect(self.reset_config)
        save_button.clicked.connect(self.save_config)

        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def _create_section_widget(self, section: ConfigSection) -> QGroupBox:
        """创建分区控件"""
        group_box = QGroupBox(section.label, self)
        if section.description:
            group_box.setToolTip(section.description)

        layout = QFormLayout(group_box)

        for field in section.fields:
            label = QLabel(field.label + ("*" if field.required else ""), self)
            if field.description:
                label.setToolTip(field.description)

            widget = ConfigWidgetFactory.create_widget(field, self)
            self.widgets[field.name] = widget

            layout.addRow(label, widget)

            # 连接值变化信号
            self._connect_widget_signals(widget, field.name)

        return group_box

    def _connect_widget_signals(self, widget: QWidget, field_name: str):
        """连接控件信号"""
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda: self._on_config_changed(field_name))
        elif isinstance(widget, QTextEdit):
            widget.textChanged.connect(lambda: self._on_config_changed(field_name))
        elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(lambda: self._on_config_changed(field_name))
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda: self._on_config_changed(field_name))
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(lambda: self._on_config_changed(field_name))

    def _on_config_changed(self, field_name: str):
        """配置变化处理"""
        widget = self.widgets[field_name]

        # 获取控件值
        if isinstance(widget, QLineEdit):
            value = widget.text()
        elif isinstance(widget, QTextEdit):
            value = widget.toPlainText()
        elif isinstance(widget, QSpinBox):
            value = widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            value = widget.value()
        elif isinstance(widget, QComboBox):
            value = widget.currentData()
        elif isinstance(widget, QCheckBox):
            value = widget.isChecked()
        else:
            value = None

        self.current_config[field_name] = value
        self.config_changed.emit(self.current_config)

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = {}
        for field_name, widget in self.widgets.items():
            if isinstance(widget, QLineEdit):
                config[field_name] = widget.text()
            elif isinstance(widget, QTextEdit):
                config[field_name] = widget.toPlainText()
            elif isinstance(widget, QSpinBox):
                config[field_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                config[field_name] = widget.value()
            elif isinstance(widget, QComboBox):
                config[field_name] = widget.currentData()
            elif isinstance(widget, QCheckBox):
                config[field_name] = widget.isChecked()
            else:
                # 处理复合控件
                if hasattr(widget, 'findChild'):
                    line_edit = widget.findChild(QLineEdit)
                    if line_edit:
                        config[field_name] = line_edit.text()

        return config

    def set_config(self, config: Dict[str, Any]):
        """设置配置值"""
        self.current_config.update(config)

        for field_name, value in config.items():
            if field_name in self.widgets:
                widget = self.widgets[field_name]

                if isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value is not None else "")
                elif isinstance(widget, QTextEdit):
                    widget.setPlainText(str(value) if value is not None else "")
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value) if value is not None else 0)
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value) if value is not None else 0.0)
                elif isinstance(widget, QComboBox):
                    index = widget.findData(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value) if value is not None else False)

    def reset_config(self):
        """重置配置"""
        default_config = self.schema.get_default_config()
        self.set_config(default_config)

    def save_config(self):
        """保存配置"""
        config = self.get_config()
        is_valid, errors = self.schema.validate_config(config)

        if is_valid:
            self.config_changed.emit(config)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "配置错误", "\n".join(errors))


class PluginConfigManager:
    """插件配置管理器"""

    def __init__(self, context: PluginContext):
        self.context = context
        self.config_dir = context.config_dir / "plugins"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.schemas: Dict[str, PluginConfigSchema] = {}

    def register_schema(self, plugin_name: str, schema: PluginConfigSchema):
        """注册配置架构"""
        self.schemas[plugin_name] = schema

    def get_config(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        config_file = self.config_dir / f"{plugin_name}.json"

        if not config_file.exists():
            # 返回默认配置
            if plugin_name in self.schemas:
                return self.schemas[plugin_name].get_default_config()
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 验证配置
            if plugin_name in self.schemas:
                schema = self.schemas[plugin_name]
                is_valid, errors = schema.validate_config(config)
                if not is_valid:
                    logger.warning(f"插件 {plugin_name} 配置验证失败: {errors}")
                    # 返回默认配置
                    return schema.get_default_config()

            return config

        except Exception as e:
            logger.error(f"加载插件配置失败: {plugin_name} - {e}")
            if plugin_name in self.schemas:
                return self.schemas[plugin_name].get_default_config()
            return {}

    def save_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """保存插件配置"""
        try:
            # 验证配置
            if plugin_name in self.schemas:
                schema = self.schemas[plugin_name]
                is_valid, errors = schema.validate_config(config)
                if not is_valid:
                    logger.error(f"插件配置验证失败: {plugin_name} - {errors}")
                    return False

            config_file = self.config_dir / f"{plugin_name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"插件配置已保存: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"保存插件配置失败: {plugin_name} - {e}")
            return False

    def create_config_widget(self, plugin_name: str) -> Optional[PluginConfigWidget]:
        """创建配置界面"""
        if plugin_name not in self.schemas:
            return None

        schema = self.schemas[plugin_name]
        config = self.get_config(plugin_name)

        widget = PluginConfigWidget(schema)
        widget.set_config(config)

        # 连接保存信号
        widget.config_changed.connect(
            lambda new_config: self.save_config(plugin_name, new_config)
        )

        return widget

    def delete_config(self, plugin_name: str) -> bool:
        """删除插件配置"""
        try:
            config_file = self.config_dir / f"{plugin_name}.json"
            if config_file.exists():
                config_file.unlink()
                logger.info(f"插件配置已删除: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"删除插件配置失败: {plugin_name} - {e}")
            return False