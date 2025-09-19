#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⚠️ DEPRECATED: 此文件已被统一主题系统替代
请使用 app.ui.unified_theme_system.UnifiedThemeManager

保留此文件仅用于向后兼容，新代码不应使用此模块
计划于下一版本中移除

专业主题管理器 - 提供完整的主题切换和管理功能
支持Material Design深色/浅色主题，以及自定义主题
"""

import warnings
warnings.warn(
    "ProfessionalThemeManager is deprecated. Use UnifiedThemeManager from app.ui.unified_theme_system instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QGroupBox, QComboBox, QSlider,
    QColorDialog, QDialog, QDialogButtonBox, QSpinBox,
    QListWidget, QListWidgetItem, QTabWidget, QStackedWidget,
    QCheckBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QFont, QPalette

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme,
    FontScheme, SpacingScheme, create_style_engine
)


class ThemePreset(Enum):
    """主题预设"""
    DARK_PROFESSIONAL = "dark_professional"
    LIGHT_PROFESSIONAL = "light_professional"
    DARK_HIGH_CONTRAST = "dark_high_contrast"
    LIGHT_HIGH_CONTRAST = "light_high_contrast"
    DARK_AMOLED = "dark_amoled"
    LIGHT_MINIMAL = "light_minimal"
    CUSTOM = "custom"


@dataclass
class ThemeConfig:
    """主题配置"""
    name: str
    preset: ThemePreset
    colors: Dict[str, str]
    fonts: Dict[str, Any]
    spacing: Dict[str, int]
    is_dark: bool = True
    description: str = ""


class ProfessionalThemeManager(QWidget):
    """专业主题管理器"""

    # 信号
    theme_changed = pyqtSignal(ThemeConfig)  # 主题变更信号
    theme_preview_requested = pyqtSignal(ThemeConfig)  # 主题预览请求

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化管理器
        self.style_engine = None
        self.current_theme = None
        self.theme_configs = {}
        self.settings = QSettings("CineAIStudio", "ThemeManager")

        # 加载预设主题
        self._load_preset_themes()

        # 加载自定义主题
        self._load_custom_themes()

        # 设置UI
        self._setup_ui()
        self._connect_signals()

        # 加载上次使用的主题
        self._load_last_theme()

    def _setup_ui(self):
        """设置用户界面"""
        self.setObjectName("theme_manager")

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 标题
        title_label = QLabel("主题管理器")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 预设主题选项卡
        self.preset_tab = self._create_preset_tab()
        self.tab_widget.addTab(self.preset_tab, "预设主题")

        # 自定义主题选项卡
        self.custom_tab = self._create_custom_tab()
        self.tab_widget.addTab(self.custom_tab, "自定义主题")

        # 高级设置选项卡
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级设置")

        # 底部按钮
        button_layout = QHBoxLayout()

        self.preview_btn = QPushButton("👁️ 预览")
        self.preview_btn.clicked.connect(self._preview_theme)
        button_layout.addWidget(self.preview_btn)

        self.apply_btn = QPushButton("✅ 应用")
        self.apply_btn.clicked.connect(self._apply_theme)
        button_layout.addWidget(self.apply_btn)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save_theme)
        button_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.clicked.connect(self._reset_theme)
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

    def _create_preset_tab(self) -> QWidget:
        """创建预设主题选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 预设主题网格
        preset_scroll = QScrollArea()
        preset_scroll.setWidgetResizable(True)
        preset_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        preset_content = QWidget()
        preset_layout = QVBoxLayout(preset_content)
        preset_layout.setSpacing(15)

        # 添加预设主题卡片
        preset_configs = [
            ThemeConfig(
                name="深色专业",
                preset=ThemePreset.DARK_PROFESSIONAL,
                colors=ColorScheme.DARK_THEME,
                fonts={},
                spacing={},
                is_dark=True,
                description="适合专业视频编辑的深色主题"
            ),
            ThemeConfig(
                name="浅色专业",
                preset=ThemePreset.LIGHT_PROFESSIONAL,
                colors=ColorScheme.LIGHT_THEME,
                fonts={},
                spacing={},
                is_dark=False,
                description="明亮清晰的浅色主题"
            ),
            ThemeConfig(
                name="深色高对比度",
                preset=ThemePreset.DARK_HIGH_CONTRAST,
                colors=self._create_high_contrast_dark_colors(),
                fonts={},
                spacing={},
                is_dark=True,
                description="高对比度深色主题，适合弱视用户"
            ),
            ThemeConfig(
                name="浅色高对比度",
                preset=ThemePreset.LIGHT_HIGH_CONTRAST,
                colors=self._create_high_contrast_light_colors(),
                fonts={},
                spacing={},
                is_dark=False,
                description="高对比度浅色主题，增强可读性"
            ),
            ThemeConfig(
                name="AMOLED深色",
                preset=ThemePreset.DARK_AMOLED,
                colors=self._create_amoled_colors(),
                fonts={},
                spacing={},
                is_dark=True,
                description="纯黑背景，适合OLED屏幕"
            ),
            ThemeConfig(
                name="极简浅色",
                preset=ThemePreset.LIGHT_MINIMAL,
                colors=self._create_minimal_light_colors(),
                fonts={},
                spacing={},
                is_dark=False,
                description="极简主义浅色主题"
            )
        ]

        self.preset_cards = {}

        for config in preset_configs:
            card = self._create_theme_card(config)
            self.preset_cards[config.preset] = card
            preset_layout.addWidget(card)

        preset_layout.addStretch()
        preset_scroll.setWidget(preset_content)
        layout.addWidget(preset_scroll)

        return tab

    def _create_custom_tab(self) -> QWidget:
        """创建自定义主题选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 基础设置组
        basic_group = QGroupBox("基础设置")
        basic_layout = QFormLayout(basic_group)

        # 主题名称
        self.theme_name_edit = QLineEdit("我的自定义主题")
        basic_layout.addRow("主题名称:", self.theme_name_edit)

        # 基础颜色
        self.primary_color_btn = QPushButton("选择主色调")
        self.primary_color_btn.clicked.connect(lambda: self._pick_color("primary"))
        basic_layout.addRow("主色调:", self.primary_color_btn)

        self.background_color_btn = QPushButton("选择背景色")
        self.background_color_btn.clicked.connect(lambda: self._pick_color("background"))
        basic_layout.addRow("背景色:", self.background_color_btn)

        self.surface_color_btn = QPushButton("选择表面色")
        self.surface_color_btn.clicked.connect(lambda: self._pick_color("surface"))
        basic_layout.addRow("表面色:", self.surface_color_btn)

        layout.addWidget(basic_group)

        # 文字颜色组
        text_group = QGroupBox("文字颜色")
        text_layout = QFormLayout(text_group)

        self.text_primary_btn = QPushButton("选择主要文字色")
        self.text_primary_btn.clicked.connect(lambda: self._pick_color("text_primary"))
        text_layout.addRow("主要文字:", self.text_primary_btn)

        self.text_secondary_btn = QPushButton("选择次要文字色")
        self.text_secondary_btn.clicked.connect(lambda: self._pick_color("text_secondary"))
        text_layout.addRow("次要文字:", self.text_secondary_btn)

        self.text_disabled_btn = QPushButton("选择禁用文字色")
        self.text_disabled_btn.clicked.connect(lambda: self._pick_color("text_disabled"))
        text_layout.addRow("禁用文字:", self.text_disabled_btn)

        layout.addWidget(text_group)

        # 特殊颜色组
        special_group = QGroupBox("特殊颜色")
        special_layout = QFormLayout(special_group)

        self.success_color_btn = QPushButton("选择成功色")
        self.success_color_btn.clicked.connect(lambda: self._pick_color("success"))
        special_layout.addRow("成功色:", self.success_color_btn)

        self.warning_color_btn = QPushButton("选择警告色")
        self.warning_color_btn.clicked.connect(lambda: self._pick_color("warning"))
        special_layout.addRow("警告色:", self.warning_color_btn)

        self.error_color_btn = QPushButton("选择错误色")
        self.error_color_btn.clicked.connect(lambda: self._pick_color("error"))
        special_layout.addRow("错误色:", self.error_color_btn)

        layout.addWidget(special_group)

        # 当前自定义颜色存储
        self.custom_colors = {}

        return tab

    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 字体设置组
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)

        # 主要字体
        self.primary_font_combo = QComboBox()
        self.primary_font_combo.addItems(["Inter", "Roboto", "Arial", "Helvetica", "Segoe UI"])
        font_layout.addRow("主要字体:", self.primary_font_combo)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(14)
        font_layout.addRow("默认字体大小:", self.font_size_spin)

        # 字体权重
        self.font_weight_combo = QComboBox()
        self.font_weight_combo.addItems(["常规", "中等", "粗体"])
        font_layout.addRow("默认字体权重:", self.font_weight_combo)

        layout.addWidget(font_group)

        # 间距设置组
        spacing_group = QGroupBox("间距设置")
        spacing_layout = QFormLayout(spacing_group)

        # 基础间距单位
        self.spacing_unit_spin = QSpinBox()
        self.spacing_unit_spin.setRange(4, 16)
        self.spacing_unit_spin.setValue(8)
        spacing_layout.addRow("基础间距单位(px):", self.spacing_unit_spin)

        # 圆角半径
        self.border_radius_spin = QSpinBox()
        self.border_radius_spin.setRange(0, 24)
        self.border_radius_spin.setValue(8)
        spacing_layout.addRow("默认圆角半径(px):", self.border_radius_spin)

        layout.addWidget(spacing_group)

        # 动画设置组
        animation_group = QGroupBox("动画设置")
        animation_layout = QFormLayout(animation_group)

        # 动画时长
        self.animation_duration_spin = QSpinBox()
        self.animation_duration_spin.setRange(0, 1000)
        self.animation_duration_spin.setValue(300)
        self.animation_duration_spin.setSuffix(" ms")
        animation_layout.addRow("动画时长:", self.animation_duration_spin)

        # 启用动画
        self.enable_animation_check = QCheckBox("启用动画效果")
        self.enable_animation_check.setChecked(True)
        animation_layout.addRow("", self.enable_animation_check)

        layout.addWidget(animation_group)

        # 高级选项组
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        # 自动主题
        self.auto_theme_check = QCheckBox("跟随系统主题")
        self.auto_theme_check.setChecked(False)
        advanced_layout.addWidget(self.auto_theme_check)

        # 平滑过渡
        self.smooth_transition_check = QCheckBox("平滑主题过渡")
        self.smooth_transition_check.setChecked(True)
        advanced_layout.addWidget(self.smooth_transition_check)

        # 高对比度模式
        self.high_contrast_check = QCheckBox("高对比度模式")
        self.high_contrast_check.setChecked(False)
        advanced_layout.addWidget(self.high_contrast_check)

        layout.addWidget(advanced_group)

        layout.addStretch()

        return tab

    def _create_theme_card(self, config: ThemeConfig) -> QFrame:
        """创建主题卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setFixedHeight(120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        # 应用卡片样式
        self._apply_theme_card_style(card, config)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        # 主题信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 主题名称
        name_label = QLabel(config.name)
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        info_layout.addWidget(name_label)

        # 主题描述
        desc_label = QLabel(config.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(desc_label)

        # 主题类型
        theme_type = "深色" if config.is_dark else "浅色"
        type_label = QLabel(f"类型: {theme_type}")
        type_label.setStyleSheet("color: #666; font-size: 10px;")
        info_layout.addWidget(type_label)

        layout.addLayout(info_layout)

        layout.addStretch()

        # 预览区域
        preview_widget = QWidget()
        preview_widget.setFixedSize(100, 80)
        preview_widget.setObjectName("theme_preview")
        self._apply_theme_preview(preview_widget, config)
        layout.addWidget(preview_widget)

        # 点击事件
        def on_click():
            self._select_theme(config)

        card.mousePressEvent = lambda event: on_click()

        return card

    def _apply_theme_card_style(self, card: QFrame, config: ThemeConfig):
        """应用主题卡片样式"""
        if config.is_dark:
            card.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border: 1px solid #444;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #00BCD4;
                    background-color: #333;
                }
            """)
        else:
            card.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #00BCD4;
                    background-color: #f8f8f8;
                }
            """)

    def _apply_theme_preview(self, widget: QWidget, config: ThemeConfig):
        """应用主题预览"""
        background = config.colors.get("background", "#1a1a1a")
        primary = config.colors.get("primary", "#00BCD4")
        surface = config.colors.get("surface", "#2a2a2a")

        widget.setStyleSheet(f"""
            QWidget#theme_preview {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {background}, stop:0.5 {surface}, stop:1 {background});
                border: 1px solid {primary};
                border-radius: 4px;
            }}
        """)

    def _load_preset_themes(self):
        """加载预设主题"""
        preset_configs = [
            ThemeConfig(
                name="深色专业",
                preset=ThemePreset.DARK_PROFESSIONAL,
                colors=ColorScheme.DARK_THEME,
                fonts={},
                spacing={},
                is_dark=True,
                description="适合专业视频编辑的深色主题"
            ),
            ThemeConfig(
                name="浅色专业",
                preset=ThemePreset.LIGHT_PROFESSIONAL,
                colors=ColorScheme.LIGHT_THEME,
                fonts={},
                spacing={},
                is_dark=False,
                description="明亮清晰的浅色主题"
            ),
            ThemeConfig(
                name="深色高对比度",
                preset=ThemePreset.DARK_HIGH_CONTRAST,
                colors=self._create_high_contrast_dark_colors(),
                fonts={},
                spacing={},
                is_dark=True,
                description="高对比度深色主题，适合弱视用户"
            ),
            ThemeConfig(
                name="浅色高对比度",
                preset=ThemePreset.LIGHT_HIGH_CONTRAST,
                colors=self._create_high_contrast_light_colors(),
                fonts={},
                spacing={},
                is_dark=False,
                description="高对比度浅色主题，增强可读性"
            ),
            ThemeConfig(
                name="AMOLED深色",
                preset=ThemePreset.DARK_AMOLED,
                colors=self._create_amoled_colors(),
                fonts={},
                spacing={},
                is_dark=True,
                description="纯黑背景，适合OLED屏幕"
            ),
            ThemeConfig(
                name="极简浅色",
                preset=ThemePreset.LIGHT_MINIMAL,
                colors=self._create_minimal_light_colors(),
                fonts={},
                spacing={},
                is_dark=False,
                description="极简主义浅色主题"
            )
        ]

        for config in preset_configs:
            self.theme_configs[config.preset] = config

    def _load_custom_themes(self):
        """加载自定义主题"""
        custom_themes_file = Path(__file__).parent / "custom_themes.json"

        if custom_themes_file.exists():
            try:
                with open(custom_themes_file, 'r', encoding='utf-8') as f:
                    themes_data = json.load(f)

                for theme_data in themes_data:
                    config = ThemeConfig(
                        name=theme_data["name"],
                        preset=ThemePreset.CUSTOM,
                        colors=theme_data["colors"],
                        fonts=theme_data.get("fonts", {}),
                        spacing=theme_data.get("spacing", {}),
                        is_dark=theme_data.get("is_dark", True),
                        description=theme_data.get("description", "")
                    )
                    self.theme_configs[f"custom_{theme_data['name']}"] = config

            except Exception as e:
                print(f"加载自定义主题失败: {e}")

    def _load_last_theme(self):
        """加载上次使用的主题"""
        last_theme = self.settings.value("last_theme", "dark_professional")

        if last_theme in self.theme_configs:
            self._select_theme(self.theme_configs[last_theme])
        else:
            # 默认使用深色专业主题
            self._select_theme(self.theme_configs[ThemePreset.DARK_PROFESSIONAL])

    def _select_theme(self, config: ThemeConfig):
        """选择主题"""
        self.current_theme = config

        # 更新UI显示
        self._update_ui_for_theme(config)

        # 预览主题
        self.theme_preview_requested.emit(config)

    def _update_ui_for_theme(self, config: ThemeConfig):
        """更新UI以显示选中主题"""
        # 更新自定义主题选项卡的颜色按钮
        if config.preset == ThemePreset.CUSTOM:
            self.theme_name_edit.setText(config.name)

            # 更新颜色按钮
            color_buttons = {
                "primary": self.primary_color_btn,
                "background": self.background_color_btn,
                "surface": self.surface_color_btn,
                "text_primary": self.text_primary_btn,
                "text_secondary": self.text_secondary_btn,
                "text_disabled": self.text_disabled_btn,
                "success": self.success_color_btn,
                "warning": self.warning_color_btn,
                "error": self.error_color_btn
            }

            for color_name, button in color_buttons.items():
                if color_name in config.colors:
                    color = QColor(config.colors[color_name])
                    button.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
                    self.custom_colors[color_name] = config.colors[color_name]

        # 更新高级设置
        if "fonts" in config.fonts:
            if "primary_font" in config.fonts["fonts"]:
                self.primary_font_combo.setCurrentText(config.fonts["fonts"]["primary_font"])

        # 高亮选中的预设主题卡片
        for preset, card in self.preset_cards.items():
            if preset == config.preset:
                card.setStyleSheet(card.styleSheet() + "QFrame { border: 2px solid #00BCD4; }")
            else:
                # 移除高亮
                original_style = card.styleSheet().replace("QFrame { border: 2px solid #00BCD4; }", "")
                card.setStyleSheet(original_style)

    def _pick_color(self, color_name: str):
        """选择颜色"""
        current_color = self.custom_colors.get(color_name, "#00BCD4")
        color = QColorDialog.getColor(QColor(current_color), self, f"选择{color_name}颜色")

        if color.isValid():
            color_hex = color.name()
            self.custom_colors[color_name] = color_hex

            # 更新按钮样式
            button_map = {
                "primary": self.primary_color_btn,
                "background": self.background_color_btn,
                "surface": self.surface_color_btn,
                "text_primary": self.text_primary_btn,
                "text_secondary": self.text_secondary_btn,
                "text_disabled": self.text_disabled_btn,
                "success": self.success_color_btn,
                "warning": self.warning_color_btn,
                "error": self.error_color_btn
            }

            if color_name in button_map:
                button = button_map[color_name]
                button.setStyleSheet(f"background-color: {color_hex}; color: {'white' if color.lightness() < 128 else 'black'};")

    def _preview_theme(self):
        """预览主题"""
        if self.current_theme:
            self.theme_preview_requested.emit(self.current_theme)

    def _apply_theme(self):
        """应用主题"""
        if self.current_theme:
            # 保存当前主题设置
            self.settings.setValue("last_theme", self.current_theme.preset.value)

            # 发射主题变更信号
            self.theme_changed.emit(self.current_theme)

    def _save_theme(self):
        """保存主题"""
        # 获取当前自定义主题配置
        theme_name = self.theme_name_edit.text().strip()
        if not theme_name:
            QMessageBox.warning(self, "警告", "请输入主题名称")
            return

        # 创建主题配置
        config = ThemeConfig(
            name=theme_name,
            preset=ThemePreset.CUSTOM,
            colors=self.custom_colors.copy(),
            fonts={
                "primary_font": self.primary_font_combo.currentText(),
                "font_size": self.font_size_spin.value(),
                "font_weight": self.font_weight_combo.currentText()
            },
            spacing={
                "unit": self.spacing_unit_spin.value(),
                "border_radius": self.border_radius_spin.value()
            },
            is_dark=self.auto_theme_check.isChecked() or QColor(self.custom_colors.get("background", "#1a1a1a")).lightness() < 128,
            description="用户自定义主题"
        )

        # 保存到文件
        self._save_custom_theme(config)

        # 添加到主题列表
        self.theme_configs[f"custom_{theme_name}"] = config

        QMessageBox.information(self, "成功", f"主题 '{theme_name}' 已保存")

    def _reset_theme(self):
        """重置主题"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置到默认主题吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._select_theme(self.theme_configs[ThemePreset.DARK_PROFESSIONAL])

    def _save_custom_theme(self, config: ThemeConfig):
        """保存自定义主题到文件"""
        custom_themes_file = Path(__file__).parent / "custom_themes.json"

        # 读取现有主题
        existing_themes = []
        if custom_themes_file.exists():
            try:
                with open(custom_themes_file, 'r', encoding='utf-8') as f:
                    existing_themes = json.load(f)
            except:
                existing_themes = []

        # 检查是否已存在同名主题
        existing_themes = [t for t in existing_themes if t.get("name") != config.name]

        # 添加新主题
        theme_data = {
            "name": config.name,
            "colors": config.colors,
            "fonts": config.fonts,
            "spacing": config.spacing,
            "is_dark": config.is_dark,
            "description": config.description
        }

        existing_themes.append(theme_data)

        # 保存文件
        try:
            with open(custom_themes_file, 'w', encoding='utf-8') as f:
                json.dump(existing_themes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存主题失败: {e}")

    def _connect_signals(self):
        """连接信号"""
        # 主题设置变更信号
        self.auto_theme_check.toggled.connect(self._on_auto_theme_changed)
        self.high_contrast_check.toggled.connect(self._on_high_contrast_changed)

    def _on_auto_theme_changed(self, checked):
        """自动主题变更处理"""
        if checked:
            # 检测系统主题
            from PyQt6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            palette = app.palette()
            window_color = palette.color(QPalette.ColorRole.Window)
            is_dark = window_color.lightness() < 128

            # 选择对应的主题
            if is_dark:
                target_theme = ThemePreset.DARK_PROFESSIONAL
            else:
                target_theme = ThemePreset.LIGHT_PROFESSIONAL

            if target_theme in self.theme_configs:
                self._select_theme(self.theme_configs[target_theme])

    def _on_high_contrast_changed(self, checked):
        """高对比度模式变更处理"""
        if checked and self.current_theme:
            # 切换到高对比度版本
            if self.current_theme.is_dark:
                target_theme = ThemePreset.DARK_HIGH_CONTRAST
            else:
                target_theme = ThemePreset.LIGHT_HIGH_CONTRAST

            if target_theme in self.theme_configs:
                self._select_theme(self.theme_configs[target_theme])

    def get_current_theme(self) -> Optional[ThemeConfig]:
        """获取当前主题"""
        return self.current_theme

    def set_style_engine(self, style_engine: ProfessionalStyleEngine):
        """设置样式引擎"""
        self.style_engine = style_engine

    # 预设颜色方案创建方法
    def _create_high_contrast_dark_colors(self) -> Dict[str, str]:
        """创建高对比度深色颜色方案"""
        return {
            "primary": "#FFFFFF",
            "primary_dark": "#E0E0E0",
            "primary_light": "#FFFFFF",
            "video_bg": "#000000",
            "timeline_bg": "#000000",
            "timeline_track": "#1A1A1A",
            "timeline_playhead": "#FFFF00",
            "background": "#000000",
            "surface": "#1A1A1A",
            "surface_variant": "#2A2A2A",
            "card": "#1A1A1A",
            "dialog": "#2A2A2A",
            "text_primary": "#FFFFFF",
            "text_secondary": "#E0E0E0",
            "text_disabled": "#B0B0B0",
            "text_hint": "#909090",
            "border": "#FFFFFF",
            "border_focus": "#FFFF00",
            "border_error": "#FF0000",
            "border_success": "#00FF00",
            "success": "#00FF00",
            "warning": "#FFFF00",
            "error": "#FF0000",
            "info": "#00FFFF",
            "play": "#00FF00",
            "pause": "#FFFF00",
            "stop": "#FF0000",
            "record": "#FF0000",
            "cut": "#FF6600",
            "copy": "#00FFFF",
            "paste": "#00FF00",
            "shadow": "rgba(255, 255, 255, 0.3)",
            "overlay": "rgba(0, 0, 0, 0.8)",
            "highlight": "rgba(255, 255, 255, 0.3)",
            "selection": "rgba(255, 255, 255, 0.5)",
            "gradient_start": "#FFFFFF",
            "gradient_end": "#E0E0E0",
            "ripple": "rgba(255, 255, 255, 0.5)",
            "hover": "rgba(255, 255, 255, 0.2)"
        }

    def _create_high_contrast_light_colors(self) -> Dict[str, str]:
        """创建高对比度浅色颜色方案"""
        return {
            "primary": "#000000",
            "primary_dark": "#333333",
            "primary_light": "#000000",
            "video_bg": "#FFFFFF",
            "timeline_bg": "#FFFFFF",
            "timeline_track": "#F0F0F0",
            "timeline_playhead": "#0000FF",
            "background": "#FFFFFF",
            "surface": "#F0F0F0",
            "surface_variant": "#E0E0E0",
            "card": "#FFFFFF",
            "dialog": "#F0F0F0",
            "text_primary": "#000000",
            "text_secondary": "#333333",
            "text_disabled": "#666666",
            "text_hint": "#808080",
            "border": "#000000",
            "border_focus": "#0000FF",
            "border_error": "#FF0000",
            "border_success": "#00AA00",
            "success": "#00AA00",
            "warning": "#AA6600",
            "error": "#CC0000",
            "info": "#0066CC",
            "play": "#00AA00",
            "pause": "#AA6600",
            "stop": "#CC0000",
            "record": "#CC0000",
            "cut": "#AA3300",
            "copy": "#0066CC",
            "paste": "#00AA00",
            "shadow": "rgba(0, 0, 0, 0.3)",
            "overlay": "rgba(255, 255, 255, 0.9)",
            "highlight": "rgba(0, 0, 0, 0.1)",
            "selection": "rgba(0, 0, 0, 0.2)",
            "gradient_start": "#000000",
            "gradient_end": "#333333",
            "ripple": "rgba(0, 0, 0, 0.2)",
            "hover": "rgba(0, 0, 0, 0.05)"
        }

    def _create_amoled_colors(self) -> Dict[str, str]:
        """创建AMOLED深色颜色方案"""
        return {
            "primary": "#00BCD4",
            "primary_dark": "#0097A7",
            "primary_light": "#B2EBF2",
            "video_bg": "#000000",
            "timeline_bg": "#000000",
            "timeline_track": "#0D0D0D",
            "timeline_playhead": "#FF4081",
            "background": "#000000",
            "surface": "#0D0D0D",
            "surface_variant": "#1A1A1A",
            "card": "#0D0D0D",
            "dialog": "#1A1A1A",
            "text_primary": "#FFFFFF",
            "text_secondary": "#B0BEC5",
            "text_disabled": "#607D8B",
            "text_hint": "#90A4AE",
            "border": "#1A1A1A",
            "border_focus": "#00BCD4",
            "border_error": "#F44336",
            "border_success": "#4CAF50",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3",
            "play": "#4CAF50",
            "pause": "#FF9800",
            "stop": "#F44336",
            "record": "#F44336",
            "cut": "#FF5722",
            "copy": "#2196F3",
            "paste": "#4CAF50",
            "shadow": "rgba(0, 0, 0, 0.5)",
            "overlay": "rgba(0, 0, 0, 0.9)",
            "highlight": "rgba(0, 188, 212, 0.2)",
            "selection": "rgba(0, 188, 212, 0.3)",
            "gradient_start": "#00BCD4",
            "gradient_end": "#0097A7",
            "ripple": "rgba(255, 255, 255, 0.3)",
            "hover": "rgba(255, 255, 255, 0.1)"
        }

    def _create_minimal_light_colors(self) -> Dict[str, str]:
        """创建极简浅色颜色方案"""
        return {
            "primary": "#2C3E50",
            "primary_dark": "#1A252F",
            "primary_light": "#34495E",
            "video_bg": "#FFFFFF",
            "timeline_bg": "#F8F9FA",
            "timeline_track": "#E9ECEF",
            "timeline_playhead": "#E74C3C",
            "background": "#FFFFFF",
            "surface": "#F8F9FA",
            "surface_variant": "#E9ECEF",
            "card": "#FFFFFF",
            "dialog": "#F8F9FA",
            "text_primary": "#2C3E50",
            "text_secondary": "#6C757D",
            "text_disabled": "#ADB5BD",
            "text_hint": "#DEE2E6",
            "border": "#DEE2E6",
            "border_focus": "#2C3E50",
            "border_error": "#E74C3C",
            "border_success": "#27AE60",
            "success": "#27AE60",
            "warning": "#F39C12",
            "error": "#E74C3C",
            "info": "#3498DB",
            "play": "#27AE60",
            "pause": "#F39C12",
            "stop": "#E74C3C",
            "record": "#E74C3C",
            "cut": "#E67E22",
            "copy": "#3498DB",
            "paste": "#27AE60",
            "shadow": "rgba(0, 0, 0, 0.1)",
            "overlay": "rgba(255, 255, 255, 0.95)",
            "highlight": "rgba(44, 62, 80, 0.1)",
            "selection": "rgba(44, 62, 80, 0.15)",
            "gradient_start": "#2C3E50",
            "gradient_end": "#1A252F",
            "ripple": "rgba(44, 62, 80, 0.1)",
            "hover": "rgba(44, 62, 80, 0.05)"
        }


# 工厂函数
def create_theme_manager(parent=None) -> ProfessionalThemeManager:
    """创建主题管理器实例"""
    return ProfessionalThemeManager(parent)


def get_theme_dialog(parent=None) -> QDialog:
    """获取主题设置对话框"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("主题设置")
    dialog.setModal(True)
    dialog.resize(600, 500)

    layout = QVBoxLayout(dialog)

    theme_manager = create_theme_manager(dialog)
    layout.addWidget(theme_manager)

    return dialog


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)

    # 创建主题管理器窗口
    theme_manager = create_theme_manager()
    theme_manager.setWindowTitle("CineAIStudio 主题管理器")
    theme_manager.resize(700, 600)
    theme_manager.show()

    sys.exit(app.exec())
