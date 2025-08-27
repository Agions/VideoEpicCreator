"""
Ant Design 风格卡片组件
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from typing import Optional, List
import math

from ..styles.ant_design import theme_manager

class AntCard(QFrame):
    """Ant Design 风格卡片"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = "default"  # default, small
        self._bordered = True
        self._hoverable = False
        self._loading = False
        self._cover = None
        self._actions = None

        self._hovered = False

        # 设置基本属性
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置样式
        border_style = f"1px solid {theme.border_color.name()}" if self._bordered else "none"
        border_radius = theme.border_radius_lg

        self.setStyleSheet(f"""
            AntCard {{
                background-color: {theme.background_color.name()};
                border: {border_style};
                border-radius: {border_radius}px;
            }}
        """)

        self.update()

    def setSize(self, size: str):
        """设置卡片大小"""
        self._size = size
        self._apply_theme()

    def setBordered(self, bordered: bool):
        """设置是否有边框"""
        self._bordered = bordered
        self._apply_theme()

    def setHoverable(self, hoverable: bool):
        """设置是否可悬停"""
        self._hoverable = hoverable
        if hoverable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def setLoading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
        self.update()

    def setCover(self, widget: QWidget):
        """设置封面"""
        if self._cover:
            self._layout.removeWidget(self._cover)
            self._cover.deleteLater()

        self._cover = widget
        if widget:
            self._layout.insertWidget(0, widget)

    def setActions(self, actions: List[QWidget]):
        """设置操作按钮"""
        if self._actions:
            self._layout.removeWidget(self._actions)
            self._actions.deleteLater()

        if actions:
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(12, 12, 12, 12)
            actions_layout.setSpacing(8)

            for action in actions:
                actions_layout.addWidget(action)

            actions_layout.addStretch()
            self._layout.addWidget(actions_widget)
            self._actions = actions_widget

    def enterEvent(self, event):
        """鼠标进入事件"""
        if self._hoverable:
            self._hovered = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        if self._hoverable:
            self._hovered = False
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        theme = theme_manager.get_current_theme()

        # 绘制背景
        rect = self.rect()
        border_radius = theme.border_radius_lg

        # 背景色
        bg_color = theme.background_color
        if self._hoverable and self._hovered:
            bg_color = theme.background_color_light

        painter.setBrush(QBrush(bg_color))

        # 边框
        if self._bordered:
            border_color = theme.border_color
            painter.setPen(QPen(border_color, 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawRoundedRect(rect, border_radius, border_radius)

        # 绘制加载状态
        if self._loading:
            self._draw_loading_indicator(painter, rect)

    def _draw_loading_indicator(self, painter: QPainter, rect):
        """绘制加载指示器"""
        theme = theme_manager.get_current_theme()

        # 简化的加载指示器
        painter.setPen(QPen(theme.primary_color, 2))
        painter.setBrush(QBrush())

        center = rect.center()
        radius = min(rect.width(), rect.height()) // 4
        painter.drawEllipse(center, radius, radius)

class CardMeta(QWidget):
    """卡片元信息"""

    def __init__(self, title: str = "", description: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._description = description

        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(8)

        # 创建标题标签
        self._title_label = QLabel(title)
        self._title_label.setFont(theme_manager.get_font("lg"))
        self._title_label.setStyleSheet(f"color: {theme_manager.get_color('heading').name()};")

        # 创建描述标签
        self._description_label = QLabel(description)
        self._description_label.setFont(theme_manager.get_font("base"))
        self._description_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary').name()};")
        self._description_label.setWordWrap(True)

        # 添加到布局
        if title:
            self._layout.addWidget(self._title_label)
        if description:
            self._layout.addWidget(self._description_label)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置标题颜色
        self._title_label.setStyleSheet(f"color: {theme.heading_color.name()};")

        # 设置描述颜色
        self._description_label.setStyleSheet(f"color: {theme.text_color_secondary.name()};")

    def setTitle(self, title: str):
        """设置标题"""
        self._title = title
        self._title_label.setText(title)
        self._title_label.setVisible(bool(title))

    def setDescription(self, description: str):
        """设置描述"""
        self._description = description
        self._description_label.setText(description)
        self._description_label.setVisible(bool(description))

class CardContent(QWidget):
    """卡片内容"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 0, 24, 0)
        self._layout.setSpacing(16)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置样式
        self.setStyleSheet(f"background-color: {theme.background_color.name()};")

    def addWidget(self, widget: QWidget):
        """添加部件"""
        self._layout.addWidget(widget)

    def addLayout(self, layout):
        """添加布局"""
        self._layout.addLayout(layout)

class CardGrid(QScrollArea):
    """卡片网格"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cards = []
        self._column_count = 3

        # 设置基本属性
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 创建内容部件
        self._content_widget = QWidget()
        self._grid_layout = QHBoxLayout(self._content_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(16)

        self.setWidget(self._content_widget)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置滚动区域样式
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {theme.background_color_light.name()};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.border_color.name()};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def setColumnCount(self, count: int):
        """设置列数"""
        self._column_count = count
        self._update_layout()

    def addCard(self, card: AntCard):
        """添加卡片"""
        self._cards.append(card)
        self._update_layout()

    def addCards(self, cards: List[AntCard]):
        """添加多个卡片"""
        self._cards.extend(cards)
        self._update_layout()

    def clearCards(self):
        """清空卡片"""
        for card in self._cards:
            card.setParent(None)
        self._cards.clear()
        self._update_layout()

    def _update_layout(self):
        """更新布局"""
        # 清空现有布局
        for i in reversed(range(self._grid_layout.count())):
            widget = self._grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 重新添加卡片
        for card in self._cards:
            self._grid_layout.addWidget(card)

# 特殊卡片类型
class BorderedCard(AntCard):
    """带边框卡片"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setBordered(True)

class HoverableCard(AntCard):
    """可悬停卡片"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setHoverable(True)

class LoadingCard(AntCard):
    """加载中卡片"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setLoading(True)
