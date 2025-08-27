"""
Material Design 3 卡片组件
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from typing import Optional, List, Dict, Any
import math

from .material3 import theme_manager

class MaterialCard(QFrame):
    """Material Design 3 卡片"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._elevation = 1
        self._corner_radius = 12
        self._is_hovered = False
        self._is_pressed = False
        self._clickable = False
        
        # 设置基本属性
        self.setMouseTracking(True)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
        
        # 设置动画
        self._elevation_animation = QPropertyAnimation(self, b"elevation")
        self._elevation_animation.setDuration(200)
        self._elevation_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 设置阴影效果
        self._shadow_effect = QGraphicsDropShadowEffect()
        self._shadow_effect.setBlurRadius(10)
        self._shadow_effect.setColor(QColor(0, 0, 0, 50))
        self._shadow_effect.setOffset(0, 2)
        self.setGraphicsEffect(self._shadow_effect)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置样式
        self.setStyleSheet("""
            MaterialCard {
                background-color: %s;
                border: 1px solid %s;
                border-radius: %dpx;
            }
        """ % (
            theme_manager.get_color("surface"),
            theme_manager.get_color("outline_variant"),
            self._corner_radius
        ))
        
        self._update_shadow()
    
    def _update_shadow(self):
        """更新阴影效果"""
        if self._shadow_effect:
            shadow_color = QColor(0, 0, 0, int(self._elevation * 15))
            self._shadow_effect.setColor(shadow_color)
            self._shadow_effect.setBlurRadius(self._elevation * 8)
            self._shadow_effect.setOffset(0, self._elevation)
    
    def set_clickable(self, clickable: bool):
        """设置是否可点击"""
        self._clickable = clickable
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        if self._clickable:
            self._is_hovered = True
            self._update_elevation()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        if self._clickable:
            self._is_hovered = False
            self._update_elevation()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self._update_elevation()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self._update_elevation()
        super().mouseReleaseEvent(event)
    
    def _update_elevation(self):
        """更新阴影高度"""
        if self._is_pressed:
            target_elevation = 3
        elif self._is_hovered:
            target_elevation = 2
        else:
            target_elevation = 1
        
        if self._elevation != target_elevation:
            self._elevation_animation.setStartValue(self._elevation)
            self._elevation_animation.setEndValue(target_elevation)
            self._elevation_animation.start()
    
    @pyqtProperty(int)
    def elevation(self):
        """阴影高度属性"""
        return self._elevation
    
    @elevation.setter
    def elevation(self, value):
        self._elevation = value
        self._update_shadow()
        self.update()

class ElevatedCard(MaterialCard):
    """提升卡片"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._elevation = 2
        self._corner_radius = 12

class FilledCard(MaterialCard):
    """填充卡片"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._elevation = 0
        self._corner_radius = 0
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置样式
        self.setStyleSheet("""
            FilledCard {
                background-color: %s;
                border: none;
                border-radius: %dpx;
            }
        """ % (
            theme_manager.get_color("surface_variant"),
            self._corner_radius
        ))
        
        self._update_shadow()

class OutlinedCard(MaterialCard):
    """轮廓卡片"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._elevation = 0
        self._corner_radius = 12
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置样式
        self.setStyleSheet("""
            OutlinedCard {
                background-color: %s;
                border: 1px solid %s;
                border-radius: %dpx;
            }
        """ % (
            theme_manager.get_color("surface"),
            theme_manager.get_color("outline"),
            self._corner_radius
        ))
        
        self._update_shadow()

class CardHeader(QWidget):
    """卡片头部"""
    
    def __init__(self, title: str = "", subtitle: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        
        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 8)
        self._layout.setSpacing(4)
        
        # 创建标题标签
        self._title_label = QLabel(title)
        self._title_label.setWordWrap(True)
        self._title_label.setFont(theme_manager.get_font("title_medium"))
        
        # 创建副标题标签
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setFont(theme_manager.get_font("body_medium"))
        
        # 添加到布局
        if title:
            self._layout.addWidget(self._title_label)
        if subtitle:
            self._layout.addWidget(self._subtitle_label)
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置标题颜色
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme_manager.get_color("on_surface")};
                background-color: transparent;
            }}
        """)
        
        # 设置副标题颜色
        self._subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {theme_manager.get_color("on_surface_variant")};
                background-color: transparent;
            }}
        """)
    
    def set_title(self, title: str):
        """设置标题"""
        self._title = title
        self._title_label.setText(title)
        self._title_label.setVisible(bool(title))
    
    def set_subtitle(self, subtitle: str):
        """设置副标题"""
        self._subtitle = subtitle
        self._subtitle_label.setText(subtitle)
        self._subtitle_label.setVisible(bool(subtitle))

class CardContent(QWidget):
    """卡片内容"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 8, 16, 16)
        self._layout.setSpacing(8)
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置样式
        self.setStyleSheet(f"""
            CardContent {{
                background-color: transparent;
                color: {theme_manager.get_color("on_surface")};
            }}
        """)
    
    def add_widget(self, widget: QWidget):
        """添加部件"""
        self._layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加布局"""
        self._layout.addLayout(layout)

class CardActions(QWidget):
    """卡片操作区域"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 设置布局
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 16, 16)
        self._layout.setSpacing(8)
        
        # 添加伸缩器
        self._layout.addStretch()
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet("""
            CardActions {
                background-color: transparent;
            }
        """)
    
    def add_button(self, button):
        """添加按钮"""
        self._layout.addWidget(button)
    
    def add_stretch(self, stretch: int = 1):
        """添加伸缩器"""
        self._layout.addStretch(stretch)

class ListCard(MaterialCard):
    """列表卡片"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items = []
        
        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # 设置滚动区域
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建内容部件
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        
        self._scroll_area.setWidget(self._content_widget)
        self._layout.addWidget(self._scroll_area)
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置滚动区域样式
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {theme_manager.get_color("surface_variant")};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme_manager.get_color("on_surface_variant")};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def add_item(self, item: QWidget):
        """添加列表项"""
        self._content_layout.addWidget(item)
        self._items.append(item)
    
    def add_items(self, items: List[QWidget]):
        """添加多个列表项"""
        for item in items:
            self.add_item(item)
    
    def clear_items(self):
        """清空列表项"""
        for item in self._items:
            self._content_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
    
    def remove_item(self, item: QWidget):
        """移除列表项"""
        if item in self._items:
            self._content_layout.removeWidget(item)
            self._items.remove(item)
            item.deleteLater()