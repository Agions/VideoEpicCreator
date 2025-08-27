"""
Ant Design 风格输入组件
"""

from PyQt6.QtWidgets import (
    QLineEdit, QTextEdit, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from typing import Optional

from ..styles.ant_design import theme_manager

class AntInput(QLineEdit):
    """Ant Design 风格输入框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = "default"  # default, large, small
        self._bordered = True
        self._allow_clear = False
        self._placeholder = ""
        self._prefix = None
        self._suffix = None
        self._focused = False

        # 设置基本属性
        self.setMouseTracking(True)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

        # 连接焦点事件
        self.textChanged.connect(self._on_text_changed)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置字体
        font = theme_manager.get_font("base" if self._size == "default" else self._size)
        self.setFont(font)

        # 设置样式
        border_style = f"1px solid {theme.border_color.name()}" if self._bordered else "none"
        border_radius = theme.border_radius_base
        bg_color = theme.background_color

        self.setStyleSheet(f"""
            AntInput {{
                background-color: {bg_color.name()};
                border: {border_style};
                border-radius: {border_radius}px;
                padding: 4px 11px;
                color: {theme.text_color.name()};
            }}
            AntInput:focus {{
                border-color: {theme.primary_color.name()};
                box-shadow: 0 0 0 2px {theme.primary_color_outline.name()};
            }}
            AntInput:disabled {{
                background-color: {theme.background_color_light.name()};
                color: {theme.disabled_color.name()};
            }}
        """)

    def setSize(self, size: str):
        """设置输入框大小"""
        self._size = size
        self._apply_theme()

    def setBordered(self, bordered: bool):
        """设置是否有边框"""
        self._bordered = bordered
        self._apply_theme()

    def setAllowClear(self, allow_clear: bool):
        """设置是否允许清除"""
        self._allow_clear = allow_clear

    def setPlaceholderText(self, text: str):
        """设置占位符文本"""
        self._placeholder = text
        super().setPlaceholderText(text)

    def setPrefix(self, prefix: str):
        """设置前缀"""
        self._prefix = prefix
        self._update_layout()

    def setSuffix(self, suffix: str):
        """设置后缀"""
        self._suffix = suffix
        self._update_layout()

    def _update_layout(self):
        """更新布局"""
        # 这里可以实现前缀和后缀的布局逻辑
        pass

    def _on_text_changed(self, text: str):
        """文本改变事件"""
        if self._allow_clear and text:
            # 可以在这里添加清除按钮的逻辑
            pass

    def focusInEvent(self, event):
        """获得焦点事件"""
        self._focused = True
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """失去焦点事件"""
        self._focused = False
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event):
        """绘制事件"""
        # 先调用父类的绘制事件
        super().paintEvent(event)

        # 如果需要自定义绘制，可以在这里添加
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

class AntTextArea(QTextEdit):
    """Ant Design 风格文本域"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = "default"  # default, large, small
        self._bordered = True
        self._auto_size = False
        self._min_rows = 3
        self._max_rows = 6

        # 设置基本属性
        self.setMouseTracking(True)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置字体
        font = theme_manager.get_font("base" if self._size == "default" else self._size)
        self.setFont(font)

        # 设置样式
        border_style = f"1px solid {theme.border_color.name()}" if self._bordered else "none"
        border_radius = theme.border_radius_base
        bg_color = theme.background_color

        self.setStyleSheet(f"""
            AntTextArea {{
                background-color: {bg_color.name()};
                border: {border_style};
                border-radius: {border_radius}px;
                padding: 4px 11px;
                color: {theme.text_color.name()};
            }}
            AntTextArea:focus {{
                border-color: {theme.primary_color.name()};
                box-shadow: 0 0 0 2px {theme.primary_color_outline.name()};
            }}
            AntTextArea:disabled {{
                background-color: {theme.background_color_light.name()};
                color: {theme.disabled_color.name()};
            }}
        """)

    def setSize(self, size: str):
        """设置文本域大小"""
        self._size = size
        self._apply_theme()

    def setBordered(self, bordered: bool):
        """设置是否有边框"""
        self._bordered = bordered
        self._apply_theme()

    def setAutoSize(self, auto_size: bool):
        """设置自动调整大小"""
        self._auto_size = auto_size

    def setMinRows(self, rows: int):
        """设置最小行数"""
        self._min_rows = rows

    def setMaxRows(self, rows: int):
        """设置最大行数"""
        self._max_rows = rows

class InputGroup(QFrame):
    """输入框组合"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._compact = False

        # 设置布局
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置样式
        self.setStyleSheet(f"""
            InputGroup {{
                border: 1px solid {theme.border_color.name()};
                border-radius: {theme.border_radius_base}px;
                background-color: {theme.background_color.name()};
            }}
        """)

    def setCompact(self, compact: bool):
        """设置紧凑模式"""
        self._compact = compact
        self._layout.setSpacing(0 if compact else 8)

    def addWidget(self, widget: QWidget, stretch: int = 0):
        """添加部件"""
        self._layout.addWidget(widget, stretch)

    def addLayout(self, layout, stretch: int = 0):
        """添加布局"""
        self._layout.addLayout(layout, stretch)

class InputGroupAddon(QLabel):
    """输入框组合附加内容"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)

        # 应用主题
        self._apply_theme()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        """应用主题"""
        theme = theme_manager.get_current_theme()

        # 设置样式
        self.setStyleSheet(f"""
            InputGroupAddon {{
                background-color: {theme.background_color_light.name()};
                border: 1px solid {theme.border_color.name()};
                padding: 0 11px;
                color: {theme.text_color_secondary.name()};
                font-size: {theme.font_size_base}px;
            }}
        """)

class SearchInput(AntInput):
    """搜索输入框"""

    search = pyqtSignal(str)  # 搜索信号

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText("请输入搜索内容")

        # 连接回车事件
        self.returnPressed.connect(self._on_return_pressed)

    def _on_return_pressed(self):
        """回车事件"""
        self.search.emit(self.text())

    def keyPressEvent(self, event):
        """按键事件"""
        super().keyPressEvent(event)
        # 可以在这里添加其他按键处理逻辑

# 大小变体
class LargeInput(AntInput):
    """大输入框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSize("large")

class SmallInput(AntInput):
    """小输入框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSize("small")

# 无边框变体
class BorderlessInput(AntInput):
    """无边框输入框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setBordered(False)
