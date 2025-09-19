#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
特效面板 - 专业视频编辑器的特效管理组件
基于Material Design，提供丰富的特效选择和编辑功能
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QFrame, QProgressBar, QSlider, QSpinBox,
    QComboBox, QCheckBox, QToolBar, QToolButton, QStackedWidget,
    QScrollArea, QSizePolicy, QSpacerItem, QGroupBox, QRadioButton,
    QButtonGroup, QDialog, QFileDialog, QMessageBox, QApplication,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTabWidget,
    QDoubleSpinBox, QColorDialog, QFontComboBox, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker, QPointF, QRectF, QMimeData
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPixmap, QImage, QBrush, QPen,
    QLinearGradient, QRadialGradient, QPainterPath, QTransform,
    QCursor, QFontMetrics, QDragEnterEvent, QDropEvent, QWheelEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QIcon, QPalette, QDrag
)

from ..professional_ui_system import (
    ProfessionalStyleEngine, UITheme, ColorScheme, 
    FontScheme, SpacingScheme, get_color, create_font
)


class EffectType(Enum):
    """特效类型"""
    TRANSITION = "transition"      # 转场特效
    FILTER = "filter"             # 滤镜特效
    COLOR = "color"               # 调色特效
    TRANSFORM = "transform"       # 变换特效
    AUDIO = "audio"               # 音频特效
    TEXT = "text"                 # 文字特效
    PARTICLE = "particle"         # 粒子特效
    BLEND = "blend"               # 混合特效


class EffectCategory(Enum):
    """特效分类"""
    BASIC = "basic"               # 基础特效
    PROFESSIONAL = "professional"  # 专业特效
    AI = "ai"                     # AI特效
    CUSTOM = "custom"             # 自定义特效


@dataclass
class EffectParameter:
    """特效参数"""
    name: str
    display_name: str
    type: str  # "int", "float", "color", "bool", "string", "enum"
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    step: Optional[Any] = None
    description: str = ""
    options: Optional[List[Tuple[str, Any]]] = None  # 用于enum类型


@dataclass
class EffectPreset:
    """特效预设"""
    id: str
    name: str
    type: EffectType
    category: EffectCategory
    icon_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    description: str = ""
    parameters: List[EffectParameter] = None
    is_ai_powered: bool = False
    processing_time: int = 0  # 处理时间（毫秒）
    resource_cost: str = "low"  # 资源消耗：low, medium, high
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class EffectItemDelegate(QStyledItemDelegate):
    """特效项代理 - 自定义绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark_theme = False
        self.thumbnail_size = QSize(100, 80)
    
    def paint(self, painter, option, index):
        """绘制特效项"""
        # 获取特效预设数据
        effect_preset = index.data(Qt.ItemDataRole.UserRole)
        if not effect_preset:
            super().paint(painter, option, index)
            return
        
        # 设置绘制参数
        painter.save()
        
        # 绘制背景
        if option.state & QStyleFactory.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(get_color('selection', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        elif option.state & QStyleFactory.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor(get_color('hover', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        # 绘制缩略图
        thumbnail_rect = QRect(option.rect.x() + 10, option.rect.y() + 10, 
                             self.thumbnail_size.width(), self.thumbnail_size.height())
        
        if effect_preset.thumbnail_path and os.path.exists(effect_preset.thumbnail_path):
            pixmap = QPixmap(effect_preset.thumbnail_path)
            painter.drawPixmap(thumbnail_rect, pixmap.scaled(self.thumbnail_size, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            # 绘制默认图标
            painter.fillRect(thumbnail_rect, QColor(get_color('surface', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.setPen(QColor(get_color('border', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.drawRect(thumbnail_rect)
            
            # 绘制特效类型图标
            icon_text = {
                EffectType.TRANSITION: "🎭",
                EffectType.FILTER: "🎨",
                EffectType.COLOR: "🌈",
                EffectType.TRANSFORM: "🔄",
                EffectType.AUDIO: "🎵",
                EffectType.TEXT: "📝",
                EffectType.PARTICLE: "✨",
                EffectType.BLEND: "🔀"
            }
            
            icon = icon_text.get(effect_preset.type, "⚡")
            painter.setFont(QFont("Arial", 20))
            painter.drawText(thumbnail_rect, Qt.AlignmentFlag.AlignCenter, icon)
        
        # 绘制文本信息
        text_rect = QRect(thumbnail_rect.right() + 10, option.rect.y() + 10,
                         option.rect.width() - thumbnail_rect.width() - 30, option.rect.height() - 20)
        
        # 设置字体
        title_font = create_font(FontScheme.FONT_SIZE_MD, FontScheme.WEIGHT_SEMI_BOLD)
        info_font = create_font(FontScheme.FONT_SIZE_SM, FontScheme.WEIGHT_REGULAR)
        
        # 绘制标题
        painter.setFont(title_font)
        painter.setPen(QColor(get_color('text_primary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        # 文本省略处理
        title_text = effect_preset.name
        title_metrics = QFontMetrics(title_font)
        if title_metrics.horizontalAdvance(title_text) > text_rect.width():
            title_text = title_metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, text_rect.width())
        
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, title_text)
        
        # 绘制描述信息
        info_text = self._get_info_text(effect_preset)
        painter.setFont(info_font)
        painter.setPen(QColor(get_color('text_secondary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
        
        info_metrics = QFontMetrics(info_font)
        if info_metrics.horizontalAdvance(info_text) > text_rect.width():
            info_text = info_metrics.elidedText(info_text, Qt.TextElideMode.ElideRight, text_rect.width())
        
        info_rect = QRect(text_rect.x(), text_rect.y() + 25, text_rect.width(), text_rect.height() - 25)
        painter.drawText(info_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, info_text)
        
        # 绘制AI标记
        if effect_preset.is_ai_powered:
            ai_rect = QRect(option.rect.right() - 40, option.rect.y() + 10, 30, 20)
            painter.fillRect(ai_rect, QColor(get_color('primary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.setPen(QColor(get_color('text_primary', UITheme.DARK if self.is_dark_theme else UITheme.LIGHT)))
            painter.setFont(create_font(FontScheme.FONT_SIZE_XS, FontScheme.WEIGHT_BOLD))
            painter.drawText(ai_rect, Qt.AlignmentFlag.AlignCenter, "AI")
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """返回项目大小"""
        return QSize(250, 100)
    
    def _get_info_text(self, effect_preset: EffectPreset) -> str:
        """获取信息文本"""
        info_parts = []
        
        # 添加分类信息
        category_names = {
            EffectCategory.BASIC: "基础",
            EffectCategory.PROFESSIONAL: "专业",
            EffectCategory.AI: "AI驱动",
            EffectCategory.CUSTOM: "自定义"
        }
        category_name = category_names.get(effect_preset.category, effect_preset.category.value)
        info_parts.append(f"分类: {category_name}")
        
        # 添加处理时间
        if effect_preset.processing_time > 0:
            if effect_preset.processing_time < 1000:
                time_str = f"{effect_preset.processing_time}ms"
            else:
                time_str = f"{effect_preset.processing_time / 1000:.1f}s"
            info_parts.append(f"处理时间: {time_str}")
        
        # 添加资源消耗
        if effect_preset.resource_cost != "low":
            cost_names = {
                "low": "低",
                "medium": "中",
                "high": "高"
            }
            cost_name = cost_names.get(effect_preset.resource_cost, effect_preset.resource_cost)
            info_parts.append(f"资源消耗: {cost_name}")
        
        return " | ".join(info_parts)


class EffectParameterWidget(QWidget):
    """特效参数编辑组件"""
    
    value_changed = pyqtSignal(str, Any)  # 参数值变更信号
    
    def __init__(self, parameter: EffectParameter, parent=None):
        super().__init__(parent)
        self.parameter = parameter
        self.current_value = parameter.default_value
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 参数名称标签
        name_label = QLabel(self.parameter.display_name)
        name_label.setMinimumWidth(100)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        # 根据参数类型创建对应的控件
        if self.parameter.type == "int":
            self.control = QSpinBox()
            self.control.setRange(
                self.parameter.min_value if self.parameter.min_value is not None else -999999,
                self.parameter.max_value if self.parameter.max_value is not None else 999999
            )
            self.control.setValue(int(self.current_value))
            if self.parameter.step:
                self.control.setSingleStep(int(self.parameter.step))
        
        elif self.parameter.type == "float":
            self.control = QDoubleSpinBox()
            self.control.setRange(
                self.parameter.min_value if self.parameter.min_value is not None else -999999.0,
                self.parameter.max_value if self.parameter.max_value is not None else 999999.0
            )
            self.control.setValue(float(self.current_value))
            if self.parameter.step:
                self.control.setSingleStep(float(self.parameter.step))
            self.control.setDecimals(2)
        
        elif self.parameter.type == "bool":
            self.control = QCheckBox()
            self.control.setChecked(bool(self.current_value))
        
        elif self.parameter.type == "color":
            self.control = QPushButton()
            self.control.setFixedSize(50, 25)
            self._update_color_button()
        
        elif self.parameter.type == "string":
            self.control = QLineEdit()
            self.control.setText(str(self.current_value))
        
        elif self.parameter.type == "enum":
            self.control = QComboBox()
            if self.parameter.options:
                for display_name, value in self.parameter.options:
                    self.control.addItem(display_name, value)
                    if value == self.current_value:
                        self.control.setCurrentText(display_name)
        
        else:
            # 默认使用文本输入
            self.control = QLineEdit()
            self.control.setText(str(self.current_value))
        
        layout.addWidget(self.control)
        
        # 添加描述标签
        if self.parameter.description:
            desc_label = QLabel(self.parameter.description)
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """连接信号"""
        if isinstance(self.control, (QSpinBox, QDoubleSpinBox)):
            self.control.valueChanged.connect(self._on_value_changed)
        elif isinstance(self.control, QCheckBox):
            self.control.toggled.connect(self._on_value_changed)
        elif isinstance(self.control, QPushButton):
            self.control.clicked.connect(self._on_color_clicked)
        elif isinstance(self.control, QLineEdit):
            self.control.textChanged.connect(self._on_value_changed)
        elif isinstance(self.control, QComboBox):
            self.control.currentTextChanged.connect(self._on_combo_changed)
    
    def _on_value_changed(self, value):
        """值变更处理"""
        self.current_value = value
        self.value_changed.emit(self.parameter.name, value)
    
    def _on_color_clicked(self):
        """颜色选择处理"""
        color = QColorDialog.getColor(QColor(self.current_value), self, f"选择{self.parameter.display_name}")
        if color.isValid():
            self.current_value = color.name()
            self._update_color_button()
            self.value_changed.emit(self.parameter.name, self.current_value)
    
    def _on_combo_changed(self, text):
        """组合框文本变更处理"""
        index = self.control.findText(text)
        if index >= 0:
            self.current_value = self.control.itemData(index)
            self.value_changed.emit(self.parameter.name, self.current_value)
    
    def _update_color_button(self):
        """更新颜色按钮"""
        if isinstance(self.control, QPushButton):
            self.control.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.current_value};
                    border: 1px solid #666;
                    border-radius: 3px;
                }}
            """)
    
    def get_value(self) -> Any:
        """获取当前值"""
        return self.current_value
    
    def set_value(self, value: Any):
        """设置值"""
        self.current_value = value
        
        if isinstance(self.control, (QSpinBox, QDoubleSpinBox)):
            self.control.setValue(value)
        elif isinstance(self.control, QCheckBox):
            self.control.setChecked(value)
        elif isinstance(self.control, QPushButton):
            self.current_value = value
            self._update_color_button()
        elif isinstance(self.control, QLineEdit):
            self.control.setText(str(value))
        elif isinstance(self.control, QComboBox):
            index = self.control.findData(value)
            if index >= 0:
                self.control.setCurrentIndex(index)


class EffectsPanel(QWidget):
    """特效面板"""
    
    # 信号定义
    effect_selected = pyqtSignal(EffectPreset)  # 特效选中信号
    effect_applied = pyqtSignal(EffectPreset, Dict[str, Any])  # 特效应用信号
    effect_preview_requested = pyqtSignal(EffectPreset, Dict[str, Any])  # 特效预览请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_dark_theme = False
        self.current_effect = None
        self.effect_presets = []
        self.selected_effects = []
        
        self._setup_ui()
        self._load_effect_presets()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # 创建主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(content_splitter)
        
        # 创建特效浏览器
        self.browser_widget = self._create_browser_widget()
        content_splitter.addWidget(self.browser_widget)
        
        # 创建特效编辑器
        self.editor_widget = self._create_editor_widget()
        content_splitter.addWidget(self.editor_widget)
        
        # 设置分割器比例
        content_splitter.setStretchFactor(0, 6)  # 浏览器
        content_splitter.setStretchFactor(1, 4)  # 编辑器
    
    def _create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        
        # 视图切换
        self.grid_view_action = toolbar.addAction("⊞ 网格")
        self.grid_view_action.setToolTip("网格视图")
        self.grid_view_action.setCheckable(True)
        self.grid_view_action.setChecked(True)
        self.grid_view_action.triggered.connect(lambda: self._change_view_mode("grid"))
        
        self.list_view_action = toolbar.addAction("📋 列表")
        self.list_view_action.setToolTip("列表视图")
        self.list_view_action.setCheckable(True)
        self.list_view_action.triggered.connect(lambda: self._change_view_mode("list"))
        
        toolbar.addSeparator()
        
        # 分类过滤
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "转场", "滤镜", "调色", "变换", "音频", "文字", "粒子", "混合"])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        toolbar.addWidget(self.category_combo)
        
        toolbar.addSeparator()
        
        # AI特效过滤
        self.ai_filter_check = QCheckBox("仅显示AI特效")
        self.ai_filter_check.toggled.connect(self._on_ai_filter_changed)
        toolbar.addWidget(self.ai_filter_check)
        
        toolbar.addSeparator()
        
        # 刷新按钮
        refresh_action = toolbar.addAction("🔄 刷新")
        refresh_action.setToolTip("刷新特效库")
        refresh_action.triggered.connect(self._refresh_effects)
        
        return toolbar
    
    def _create_browser_widget(self) -> QWidget:
        """创建特效浏览器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 搜索区域
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 10, 10, 5)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索特效...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)
        
        layout.addWidget(search_widget)
        
        # 特效显示区域
        self.effects_stack = QStackedWidget()
        
        # 网格视图
        self.grid_view = QListWidget()
        self.grid_view.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid_view.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid_view.setDragEnabled(True)
        self.grid_view.itemSelectionChanged.connect(self._on_effect_selection_changed)
        self.grid_view.itemDoubleClicked.connect(self._on_effect_double_clicked)
        self.effects_stack.addWidget(self.grid_view)
        
        # 列表视图
        self.list_view = QListWidget()
        self.list_view.setDragEnabled(True)
        self.list_view.itemSelectionChanged.connect(self._on_effect_selection_changed)
        self.list_view.itemDoubleClicked.connect(self._on_effect_double_clicked)
        self.effects_stack.addWidget(self.list_view)
        
        layout.addWidget(self.effects_stack)
        
        # 设置默认视图
        self.effects_stack.setCurrentIndex(0)  # 网格视图
        
        return widget
    
    def _create_editor_widget(self) -> QWidget:
        """创建特效编辑器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 特效信息区域
        self.info_area = self._create_info_area()
        layout.addWidget(self.info_area)
        
        # 参数编辑区域
        self.params_area = self._create_params_area()
        layout.addWidget(self.params_area)
        
        # 预览和应用按钮
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        self.preview_btn = QPushButton("👁️ 预览")
        self.preview_btn.clicked.connect(self._preview_effect)
        button_layout.addWidget(self.preview_btn)
        
        self.apply_btn = QPushButton("✅ 应用")
        self.apply_btn.clicked.connect(self._apply_effect)
        button_layout.addWidget(self.apply_btn)
        
        button_layout.addStretch()
        
        self.save_preset_btn = QPushButton("💾 保存预设")
        self.save_preset_btn.clicked.connect(self._save_preset)
        button_layout.addWidget(self.save_preset_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def _create_info_area(self) -> QWidget:
        """创建特效信息区域"""
        widget = QWidget()
        widget.setObjectName("effect_info_area")
        widget.setFixedHeight(120)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 特效名称
        self.effect_name_label = QLabel("未选择特效")
        self.effect_name_label.setFont(create_font(FontScheme.FONT_SIZE_LG, FontScheme.WEIGHT_BOLD))
        layout.addWidget(self.effect_name_label)
        
        # 特效描述
        self.effect_desc_label = QLabel("请从左侧选择一个特效")
        self.effect_desc_label.setWordWrap(True)
        self.effect_desc_label.setStyleSheet("color: #888;")
        layout.addWidget(self.effect_desc_label)
        
        # 特效属性
        self.effect_props_label = QLabel("")
        self.effect_props_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.effect_props_label)
        
        return widget
    
    def _create_params_area(self) -> QWidget:
        """创建参数编辑区域"""
        widget = QScrollArea()
        widget.setWidgetResizable(True)
        
        content_widget = QWidget()
        self.params_layout = QVBoxLayout(content_widget)
        self.params_layout.setContentsMargins(15, 15, 15, 15)
        self.params_layout.setSpacing(10)
        
        widget.setWidget(content_widget)
        
        return widget
    
    def _load_effect_presets(self):
        """加载特效预设"""
        # 创建默认特效预设
        default_presets = [
            # 转场特效
            EffectPreset(
                id="fade_transition",
                name="淡入淡出",
                type=EffectType.TRANSITION,
                category=EffectCategory.BASIC,
                description="经典的淡入淡出转场效果",
                parameters=[
                    EffectParameter("duration", "持续时间", "float", 1.0, 0.1, 5.0, 0.1, "转场持续时间（秒）"),
                    EffectParameter("ease_type", "缓动类型", "enum", "ease_in_out", 
                                  options=[("缓入缓出", "ease_in_out"), ("缓入", "ease_in"), ("缓出", "ease_out")])
                ]
            ),
            
            # 滤镜特效
            EffectPreset(
                id="blur_filter",
                name="模糊滤镜",
                type=EffectType.FILTER,
                category=EffectCategory.BASIC,
                description="高斯模糊效果，可以调节模糊程度",
                parameters=[
                    EffectParameter("radius", "模糊半径", "float", 5.0, 0.0, 50.0, 0.5, "模糊半径（像素）"),
                    EffectParameter("iterations", "迭代次数", "int", 1, 1, 5, 1, "模糊迭代次数")
                ]
            ),
            
            # AI特效
            EffectPreset(
                id="ai_style_transfer",
                name="AI风格迁移",
                type=EffectType.FILTER,
                category=EffectCategory.AI,
                is_ai_powered=True,
                description="使用AI技术将图片转换为艺术风格",
                parameters=[
                    EffectParameter("style", "艺术风格", "enum", "van_gogh",
                                  options=[("梵高风格", "van_gogh"), ("毕加索风格", "picasso"), 
                                         ("莫奈风格", "monet"), ("赛尚风格", "cezanne")]),
                    EffectParameter("intensity", "强度", "float", 0.8, 0.0, 1.0, 0.1, "风格强度"),
                    EffectParameter("preserve_colors", "保留颜色", "bool", True, description="是否保留原图颜色")
                ],
                processing_time=3000,
                resource_cost="high"
            ),
            
            # 调色特效
            EffectPreset(
                id="color_grading",
                name="专业调色",
                type=EffectType.COLOR,
                category=EffectCategory.PROFESSIONAL,
                description="专业的颜色分级工具",
                parameters=[
                    EffectParameter("brightness", "亮度", "float", 0.0, -1.0, 1.0, 0.1),
                    EffectParameter("contrast", "对比度", "float", 1.0, 0.0, 3.0, 0.1),
                    EffectParameter("saturation", "饱和度", "float", 1.0, 0.0, 3.0, 0.1),
                    EffectParameter("temperature", "色温", "float", 0.0, -100.0, 100.0, 1.0),
                    EffectParameter("tint", "色调", "float", 0.0, -100.0, 100.0, 1.0)
                ]
            ),
            
            # 文字特效
            EffectPreset(
                id="typewriter",
                name="打字机效果",
                type=EffectType.TEXT,
                category=EffectCategory.BASIC,
                description="逐字符显示的打字机效果",
                parameters=[
                    EffectParameter("text", "文本内容", "string", "Hello World"),
                    EffectParameter("font", "字体", "string", "Arial"),
                    EffectParameter("size", "字体大小", "int", 24, 12, 72, 1),
                    EffectParameter("color", "文字颜色", "color", "#FFFFFF"),
                    EffectParameter("speed", "打字速度", "float", 50.0, 10.0, 200.0, 10.0, "每秒字符数"),
                    EffectParameter("cursor_visible", "显示光标", "bool", True)
                ]
            ),
            
            # 粒子特效
            EffectPreset(
                id="particle_system",
                name="粒子系统",
                type=EffectType.PARTICLE,
                category=EffectCategory.PROFESSIONAL,
                description="动态粒子效果系统",
                parameters=[
                    EffectParameter("particle_count", "粒子数量", "int", 100, 10, 1000, 10),
                    EffectParameter("particle_size", "粒子大小", "float", 2.0, 0.5, 10.0, 0.5),
                    EffectParameter("speed", "速度", "float", 1.0, 0.1, 5.0, 0.1),
                    EffectParameter("lifetime", "生命周期", "float", 3.0, 0.5, 10.0, 0.1),
                    EffectParameter("color", "粒子颜色", "color", "#00BCD4"),
                    EffectParameter("gravity", "重力", "float", 0.1, 0.0, 1.0, 0.01)
                ],
                resource_cost="medium"
            )
        ]
        
        self.effect_presets = default_presets
        self._refresh_effects_display()
    
    def _refresh_effects_display(self):
        """刷新特效显示"""
        self._update_grid_view()
        self._update_list_view()
    
    def _update_grid_view(self):
        """更新网格视图"""
        self.grid_view.clear()
        
        for preset in self.effect_presets:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, preset)
            
            # 设置图标
            if preset.thumbnail_path and os.path.exists(preset.thumbnail_path):
                pixmap = QPixmap(preset.thumbnail_path)
                item.setIcon(QIcon(pixmap))
            else:
                # 使用默认图标
                icon_map = {
                    EffectType.TRANSITION: "🎭",
                    EffectType.FILTER: "🎨",
                    EffectType.COLOR: "🌈",
                    EffectType.TRANSFORM: "🔄",
                    EffectType.AUDIO: "🎵",
                    EffectType.TEXT: "📝",
                    EffectType.PARTICLE: "✨",
                    EffectType.BLEND: "🔀"
                }
                icon = icon_map.get(preset.type, "⚡")
                item.setText(icon)
            
            # 设置文本
            item.setText(preset.name)
            item.setToolTip(self._get_effect_tooltip(preset))
            
            self.grid_view.addItem(item)
        
        # 设置网格大小
        self.grid_view.setGridSize(QSize(120, 120))
    
    def _update_list_view(self):
        """更新列表视图"""
        self.list_view.clear()
        
        for preset in self.effect_presets:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, preset)
            
            # 设置文本
            text = f"{preset.name}"
            if preset.is_ai_powered:
                text += " [AI]"
            
            item.setText(text)
            item.setToolTip(self._get_effect_tooltip(preset))
            
            self.list_view.addItem(item)
    
    def _get_effect_tooltip(self, preset: EffectPreset) -> str:
        """获取特效工具提示"""
        tooltip_lines = [f"名称: {preset.name}"]
        tooltip_lines.append(f"类型: {preset.type.value}")
        tooltip_lines.append(f"分类: {preset.category.value}")
        tooltip_lines.append(f"描述: {preset.description}")
        
        if preset.is_ai_powered:
            tooltip_lines.append("AI驱动: 是")
        
        if preset.processing_time > 0:
            if preset.processing_time < 1000:
                time_str = f"{preset.processing_time}ms"
            else:
                time_str = f"{preset.processing_time / 1000:.1f}s"
            tooltip_lines.append(f"处理时间: {time_str}")
        
        if preset.resource_cost != "low":
            cost_names = {"low": "低", "medium": "中", "high": "高"}
            cost_name = cost_names.get(preset.resource_cost, preset.resource_cost)
            tooltip_lines.append(f"资源消耗: {cost_name}")
        
        return "\n".join(tooltip_lines)
    
    def _apply_styles(self):
        """应用样式"""
        colors = ColorScheme.DARK_THEME if self.is_dark_theme else ColorScheme.LIGHT_THEME
        
        # 面板样式
        self.setStyleSheet(f"""
            EffectsPanel {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_MD}px;
            }}
            
            QToolBar {{
                background-color: {colors['surface_variant']};
                border: none;
                border-bottom: 1px solid {colors['border']};
                border-radius: 0px;
                spacing: {SpacingScheme.GAP_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
            }}
            
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
                min-width: 60px;
            }}
            
            QToolButton:hover {{
                background: {colors['highlight']};
            }}
            
            QToolButton:pressed {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
            
            QToolButton:checked {{
                background: {colors['primary']};
                color: {colors['text_primary']};
            }}
            
            QLineEdit {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
            }}
            
            QLineEdit:focus {{
                border-color: {colors['primary']};
            }}
            
            QComboBox {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
                min-width: 100px;
            }}
            
            QComboBox:hover {{
                border-color: {colors['primary']};
            }}
            
            QCheckBox {{
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
            }}
            
            QPushButton {{
                background-color: {colors['primary']};
                border: none;
                border-radius: {SpacingScheme.RADIUS_SM}px;
                padding: {SpacingScheme.PADDING_SM}px {SpacingScheme.PADDING_MD}px;
                color: {colors['text_primary']};
                font-size: {FontScheme.FONT_SIZE_MD}px;
                font-weight: {FontScheme.WEIGHT_MEDIUM};
            }}
            
            QPushButton:hover {{
                background-color: {colors['primary_dark']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['primary_light']};
            }}
        """)
        
        # 列表视图样式
        list_style = f"""
            QListWidget {{
                background-color: {colors['surface']};
                border: none;
                outline: none;
                font-size: {FontScheme.FONT_SIZE_MD}px;
            }}
            
            QListWidget::item {{
                background-color: transparent;
                border: 1px solid {colors['border']};
                border-radius: {SpacingScheme.RADIUS_SM}px;
                margin: {SpacingScheme.GAP_SM}px;
                padding: {SpacingScheme.PADDING_MD}px;
                color: {colors['text_primary']};
            }}
            
            QListWidget::item:selected {{
                background-color: {colors['selection']};
                border-color: {colors['primary']};
            }}
            
            QListWidget::item:hover {{
                background-color: {colors['hover']};
            }}
        """
        
        self.grid_view.setStyleSheet(list_style)
        self.list_view.setStyleSheet(list_style)
        
        # 信息区域样式
        self.info_area.setStyleSheet(f"""
            QWidget#effect_info_area {{
                background-color: {colors['surface_variant']};
                border: none;
                border-bottom: 1px solid {colors['border']};
            }}
        """)
    
    def _connect_signals(self):
        """连接信号"""
        pass
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.is_dark_theme = is_dark
        self._apply_styles()
    
    def _change_view_mode(self, mode: str):
        """切换视图模式"""
        self.grid_view_action.setChecked(mode == "grid")
        self.list_view_action.setChecked(mode == "list")
        
        if mode == "grid":
            self.effects_stack.setCurrentIndex(0)
        else:
            self.effects_stack.setCurrentIndex(1)
    
    def _on_category_changed(self, category: str):
        """分类变更处理"""
        # TODO: 实现分类过滤
        pass
    
    def _on_ai_filter_changed(self, checked: bool):
        """AI过滤变更处理"""
        # TODO: 实现AI特效过滤
        pass
    
    def _on_search_changed(self, text: str):
        """搜索文本变更处理"""
        # TODO: 实现搜索过滤
        pass
    
    def _on_effect_selection_changed(self):
        """特效选择变更处理"""
        current_view = self.effects_stack.currentWidget()
        if isinstance(current_view, QListWidget):
            selected_items = current_view.selectedItems()
            if selected_items:
                selected_item = selected_items[0]
                effect_preset = selected_item.data(Qt.ItemDataRole.UserRole)
                if effect_preset:
                    self._select_effect(effect_preset)
    
    def _on_effect_double_clicked(self, item):
        """特效双击处理"""
        effect_preset = item.data(Qt.ItemDataRole.UserRole)
        if effect_preset:
            self._select_effect(effect_preset)
            self._apply_effect()
    
    def _select_effect(self, effect_preset: EffectPreset):
        """选择特效"""
        self.current_effect = effect_preset
        
        # 更新信息显示
        self.effect_name_label.setText(effect_preset.name)
        self.effect_desc_label.setText(effect_preset.description)
        
        # 更新属性显示
        props_text = []
        if effect_preset.is_ai_powered:
            props_text.append("🤖 AI驱动")
        
        if effect_preset.processing_time > 0:
            if effect_preset.processing_time < 1000:
                props_text.append(f"⏱️ {effect_preset.processing_time}ms")
            else:
                props_text.append(f"⏱️ {effect_preset.processing_time / 1000:.1f}s")
        
        if effect_preset.resource_cost != "low":
            cost_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            cost_emoji = cost_emoji.get(effect_preset.resource_cost, "⚪")
            props_text.append(f"{cost_emoji} 资源消耗: {effect_preset.resource_cost}")
        
        self.effect_props_label.setText(" | ".join(props_text))
        
        # 创建参数编辑控件
        self._create_parameter_widgets()
        
        # 发射选中信号
        self.effect_selected.emit(effect_preset)
    
    def _create_parameter_widgets(self):
        """创建参数编辑控件"""
        # 清除现有控件
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.current_effect:
            return
        
        # 创建参数控件
        self.parameter_widgets = {}
        for param in self.current_effect.parameters:
            param_widget = EffectParameterWidget(param)
            param_widget.value_changed.connect(self._on_parameter_changed)
            self.params_layout.addWidget(param_widget)
            self.parameter_widgets[param.name] = param_widget
        
        self.params_layout.addStretch()
    
    def _on_parameter_changed(self, param_name: str, value: Any):
        """参数变更处理"""
        # 可以在这里添加实时预览逻辑
        pass
    
    def _get_effect_parameters(self) -> Dict[str, Any]:
        """获取当前特效参数"""
        if not self.current_effect:
            return {}
        
        params = {}
        for param_name, widget in self.parameter_widgets.items():
            params[param_name] = widget.get_value()
        
        return params
    
    def _preview_effect(self):
        """预览特效"""
        if not self.current_effect:
            return
        
        params = self._get_effect_parameters()
        self.effect_preview_requested.emit(self.current_effect, params)
    
    def _apply_effect(self):
        """应用特效"""
        if not self.current_effect:
            return
        
        params = self._get_effect_parameters()
        self.effect_applied.emit(self.current_effect, params)
    
    def _save_preset(self):
        """保存预设"""
        if not self.current_effect:
            return
        
        # 获取预设名称
        name, ok = QInputDialog.getText(self, "保存预设", "请输入预设名称:")
        if ok and name.strip():
            # 创建新的预设副本
            new_preset = EffectPreset(
                id=f"custom_{name.lower().replace(' ', '_')}",
                name=name,
                type=self.current_effect.type,
                category=EffectCategory.CUSTOM,
                description=self.current_effect.description,
                parameters=self.current_effect.parameters.copy()
            )
            
            # 更新参数值为当前值
            for param in new_preset.parameters:
                if param.name in self.parameter_widgets:
                    param.default_value = self.parameter_widgets[param.name].get_value()
            
            # 添加到预设列表
            self.effect_presets.append(new_preset)
            
            # 刷新显示
            self._refresh_effects_display()
            
            QMessageBox.information(self, "成功", f"预设 '{name}' 已保存")
    
    def _refresh_effects(self):
        """刷新特效"""
        self._refresh_effects_display()
    
    def get_selected_effect(self) -> Optional[EffectPreset]:
        """获取当前选中的特效"""
        return self.current_effect
    
    def get_effect_parameters(self) -> Dict[str, Any]:
        """获取特效参数"""
        return self._get_effect_parameters()


# 工厂函数
def create_effects_panel(parent=None) -> EffectsPanel:
    """创建特效面板"""
    return EffectsPanel(parent)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建特效面板
    panel = create_effects_panel()
    panel.setWindowTitle("特效面板测试")
    panel.resize(1000, 700)
    panel.show()
    
    sys.exit(app.exec())