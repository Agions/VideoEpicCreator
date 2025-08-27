"""
Material Design 3 按钮组件
"""

from PyQt6.QtWidgets import (
    QPushButton, QFrame, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QCursor
from typing import Optional, Callable
import math

from .material3 import theme_manager

class MaterialButton(QPushButton):
    """Material Design 3 按钮"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._elevation = 2
        self._corner_radius = 8
        self._ripple_color = QColor(theme_manager.get_color("on_primary"))
        self._ripple_opacity = 0.0
        self._ripple_radius = 0.0
        self._ripple_center = None
        self._is_hovered = False
        self._is_pressed = False
        
        # 设置基本属性
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
        
        # 设置动画
        self._elevation_animation = QPropertyAnimation(self, b"elevation")
        self._elevation_animation.setDuration(200)
        self._elevation_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self._ripple_animation = QPropertyAnimation(self, b"rippleOpacity")
        self._ripple_animation.setDuration(300)
        self._ripple_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置字体
        self.setFont(theme_manager.get_font("label_large"))
        
        # 设置颜色
        self.setStyleSheet("""
            MaterialButton {
                background-color: transparent;
                border: none;
                color: %s;
                padding: 8px 24px;
                text-align: center;
            }
        """ % theme_manager.get_color("on_primary"))
        
        self.update()
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovered = True
        self._update_elevation()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self._update_elevation()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self._ripple_center = event.pos()
            self._ripple_radius = 0.0
            self._ripple_animation.setStartValue(0.0)
            self._ripple_animation.setEndValue(0.3)
            self._ripple_animation.start()
            self._update_elevation()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self._ripple_animation.setStartValue(self._ripple_opacity)
            self._ripple_animation.setEndValue(0.0)
            self._ripple_animation.start()
            self._update_elevation()
        super().mouseReleaseEvent(event)
    
    def _update_elevation(self):
        """更新阴影高度"""
        if self._is_pressed:
            target_elevation = 8
        elif self._is_hovered:
            target_elevation = 4
        else:
            target_elevation = 2
        
        if self._elevation != target_elevation:
            self._elevation_animation.setStartValue(self._elevation)
            self._elevation_animation.setEndValue(target_elevation)
            self._elevation_animation.start()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = theme_manager.get_current_theme()
        
        # 绘制按钮背景
        rect = self.rect()
        
        # 创建渐变背景
        bg_color = QColor(theme_manager.get_color("primary_container"))
        if self._is_pressed:
            bg_color = bg_color.darker(110)
        elif self._is_hovered:
            bg_color = bg_color.lighter(110)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self._corner_radius, self._corner_radius)
        
        # 绘制阴影
        if self._elevation > 0:
            shadow_color = QColor(0, 0, 0, int(self._elevation * 10))
            shadow_rect = rect.adjusted(2, 2, -2, -2)
            painter.setBrush(QBrush(shadow_color))
            painter.drawRoundedRect(shadow_rect, self._corner_radius, self._corner_radius)
        
        # 绘制涟漪效果
        if self._ripple_opacity > 0 and self._ripple_center:
            painter.setBrush(QBrush(self._ripple_color))
            painter.setOpacity(self._ripple_opacity)
            painter.drawEllipse(self._ripple_center, self._ripple_radius, self._ripple_radius)
            painter.setOpacity(1.0)
        
        # 绘制文本
        painter.setPen(QPen(QColor(theme_manager.get_color("on_primary_container"))))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
    
    @pyqtProperty(float)
    def elevation(self):
        """阴影高度属性"""
        return self._elevation
    
    @elevation.setter
    def elevation(self, value):
        self._elevation = value
        self.update()
    
    @pyqtProperty(float)
    def rippleOpacity(self):
        """涟漪透明度属性"""
        return self._ripple_opacity
    
    @rippleOpacity.setter
    def rippleOpacity(self, value):
        self._ripple_opacity = value
        self.update()
    
    @pyqtProperty(float)
    def rippleRadius(self):
        """涟漪半径属性"""
        return self._ripple_radius
    
    @rippleRadius.setter
    def rippleRadius(self, value):
        self._ripple_radius = value
        self.update()

class ElevatedButton(MaterialButton):
    """提升按钮"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._elevation = 2
        self._corner_radius = 12

class FilledButton(MaterialButton):
    """填充按钮"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._elevation = 0
        self._corner_radius = 20

class OutlinedButton(MaterialButton):
    """轮廓按钮"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._elevation = 0
        self._corner_radius = 20
        self._has_outline = True
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = theme_manager.get_current_theme()
        
        # 绘制按钮背景
        rect = self.rect()
        
        # 创建透明背景
        painter.setBrush(QBrush(QColor(theme_manager.get_color("surface"))))
        painter.setPen(QPen(QColor(theme_manager.get_color("outline")), 1))
        painter.drawRoundedRect(rect, self._corner_radius, self._corner_radius)
        
        # 绘制涟漪效果
        if self._ripple_opacity > 0 and self._ripple_center:
            painter.setBrush(QBrush(QColor(theme_manager.get_color("on_surface"))))
            painter.setOpacity(self._ripple_opacity)
            painter.drawEllipse(self._ripple_center, self._ripple_radius, self._ripple_radius)
            painter.setOpacity(1.0)
        
        # 绘制文本
        painter.setPen(QPen(QColor(theme_manager.get_color("primary"))))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

class TextButton(QPushButton):
    """文本按钮"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._is_hovered = False
        self._is_pressed = False
        
        # 设置基本属性
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFlat(True)
        
        # 应用主题
        self._apply_theme()
        
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()
        
        # 设置字体
        self.setFont(theme_manager.get_font("label_large"))
        
        # 设置颜色
        self.setStyleSheet("""
            TextButton {
                background-color: transparent;
                border: none;
                color: %s;
                padding: 8px 12px;
                text-align: center;
            }
        """ % theme_manager.get_color("primary"))
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = theme_manager.get_current_theme()
        
        # 绘制文本
        rect = self.rect()
        
        # 设置文本颜色
        if self._is_pressed:
            text_color = QColor(theme_manager.get_color("primary")).darker(110)
        elif self._is_hovered:
            text_color = QColor(theme_manager.get_color("primary")).lighter(110)
        else:
            text_color = QColor(theme_manager.get_color("primary"))
        
        painter.setPen(QPen(text_color))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())