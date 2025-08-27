"""
Ant Design 风格按钮组件
"""

from PyQt6.QtWidgets import QPushButton, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QCursor
from typing import Optional
import math

from ..styles.ant_design import theme_manager

class AntButton(QPushButton):
    """Ant Design 风格按钮基类"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._type = "default"  # default, primary, dashed, link, text
        self._size = "default"  # default, large, small
        self._shape = "default"  # default, circle, round
        self._loading = False
        self._disabled = False
        self._ghost = False

        self._hovered = False
        self._pressed = False

        # 设置基本属性
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

        # 设置动画
        self._animation = QPropertyAnimation(self, b"opacity")
        self._animation.setDuration(int(theme_manager.get_animation_duration("base") * 1000))
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置字体
        font = theme_manager.get_font("base" if self._size == "default" else self._size)
        self.setFont(font)

        # 设置基础样式
        self.setStyleSheet("""
            AntButton {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)

        self.update()

    def setType(self, type_name: str):
        """设置按钮类型"""
        self._type = type_name
        self.update()

    def setSize(self, size: str):
        """设置按钮大小"""
        self._size = size
        self._apply_theme()

    def setShape(self, shape: str):
        """设置按钮形状"""
        self._shape = shape
        self.update()

    def setLoading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
        self.update()

    def setGhost(self, ghost: bool):
        """设置幽灵按钮"""
        self._ghost = ghost
        self.update()

    def enterEvent(self, event):
        """鼠标进入事件"""
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        theme = theme_manager.get_current_theme()

        # 获取按钮状态颜色
        bg_color, border_color, text_color = self._get_colors()

        # 计算圆角
        corner_radius = self._get_corner_radius()

        # 绘制按钮背景
        rect = self.rect()
        adjusted_rect = rect.adjusted(2, 2, -2, -2)

        # 绘制背景
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(adjusted_rect, corner_radius, corner_radius)

        # 绘制加载状态
        if self._loading:
            self._draw_loading_indicator(painter, adjusted_rect)
        else:
            # 绘制文本
            painter.setPen(QPen(text_color))
            painter.setFont(self.font())
            painter.drawText(adjusted_rect, Qt.AlignmentFlag.AlignCenter, self.text())

    def _get_colors(self):
        """获取按钮颜色"""
        theme = theme_manager.get_current_theme()

        # 默认颜色
        bg_color = theme.background_color
        border_color = theme.border_color
        text_color = theme.text_color

        if self._disabled:
            bg_color = theme.background_color
            border_color = theme.border_color
            text_color = theme.disabled_color
        elif self._type == "primary":
            if self._pressed:
                bg_color = theme.primary_color_active
                border_color = theme.primary_color_active
                text_color = QColor("#ffffff")
            elif self._hovered:
                bg_color = theme.primary_color_hover
                border_color = theme.primary_color_hover
                text_color = QColor("#ffffff")
            else:
                bg_color = theme.primary_color
                border_color = theme.primary_color
                text_color = QColor("#ffffff")
        elif self._type == "dashed":
            bg_color = theme.background_color
            border_color = theme.border_color if not self._hovered else theme.primary_color
            text_color = theme.text_color if not self._hovered else theme.primary_color
            if self._pressed:
                text_color = theme.primary_color_active
        elif self._type == "link":
            bg_color = QColor("transparent")
            border_color = QColor("transparent")
            text_color = theme.primary_color if not self._hovered else theme.primary_color_hover
            if self._pressed:
                text_color = theme.primary_color_active
        elif self._type == "text":
            bg_color = QColor("transparent")
            border_color = QColor("transparent")
            text_color = theme.text_color if not self._hovered else theme.primary_color
            if self._pressed:
                text_color = theme.primary_color_active
        else:  # default
            if self._pressed:
                bg_color = theme.background_color_light
                border_color = theme.primary_color_active
                text_color = theme.primary_color_active
            elif self._hovered:
                bg_color = theme.background_color_light
                border_color = theme.primary_color_hover
                text_color = theme.primary_color_hover
            else:
                bg_color = theme.background_color
                border_color = theme.border_color
                text_color = theme.text_color

        # 幽灵按钮处理
        if self._ghost and self._type in ["primary", "default"]:
            bg_color = QColor("transparent")
            if self._type == "primary":
                text_color = theme.primary_color
                border_color = theme.primary_color

        return bg_color, border_color, text_color

    def _get_corner_radius(self):
        """获取圆角"""
        theme = theme_manager.get_current_theme()

        if self._shape == "circle":
            return min(self.width(), self.height()) // 2
        elif self._shape == "round":
            return theme.border_radius_lg
        else:
            return theme.border_radius_base

    def _draw_loading_indicator(self, painter: QPainter, rect):
        """绘制加载指示器"""
        theme = theme_manager.get_current_theme()

        # 简化的加载指示器
        painter.setPen(QPen(theme.primary_color, 2))
        painter.setBrush(QBrush())

        center = rect.center()
        radius = min(rect.width(), rect.height()) // 4
        painter.drawEllipse(center, radius, radius)

    @pyqtProperty(float)
    def opacity(self):
        """透明度属性"""
        return 1.0

    @opacity.setter
    def opacity(self, value):
        self.setWindowOpacity(value)

class PrimaryButton(AntButton):
    """主要按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setType("primary")

class DashedButton(AntButton):
    """虚线按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setType("dashed")

class LinkButton(AntButton):
    """链接按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setType("link")

class TextButton(AntButton):
    """文字按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setType("text")

class GhostButton(AntButton):
    """幽灵按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setGhost(True)

# 大小变体
class LargeButton(AntButton):
    """大按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setSize("large")

class SmallButton(AntButton):
    """小按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setSize("small")

# 形状变体
class RoundButton(AntButton):
    """圆角按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setShape("round")

class CircleButton(AntButton):
    """圆形按钮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setShape("circle")
