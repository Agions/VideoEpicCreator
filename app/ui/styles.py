"""
Ant Design Stylesheet for VideoEpicCreator UI components
Modern, clean design with professional appearance following Ant Design principles
"""

STYLESHEET = """
/* 全局样式 */
QWidget {
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    color: #333;
}

/* 主窗口样式 */
QMainWindow {
    background-color: #f5f5f5;
}

/* 侧边栏样式 */
#sidebar {
    background-color: #001529;
    border-right: 1px solid #002140;
}

#logo_widget {
    background-color: #002140;
    border-bottom: 1px solid #003060;
}

#logo_label {
    color: white;
    font-size: 18px;
    font-weight: bold;
}

#nav_widget {
    background-color: transparent;
}

#nav_button {
    background-color: transparent;
    border: none;
    color: #b0b0b0;
    text-align: left;
    padding-left: 15px;
    border-radius: 4px;
    margin: 2px 0;
}

#nav_button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
}

#nav_button_active {
    background-color: #1890ff;
    color: white;
    border: none;
    text-align: left;
    padding-left: 15px;
    border-radius: 4px;
    margin: 2px 0;
}

#user_widget {
    background-color: #002140;
    border-top: 1px solid #003060;
}

#avatar_label {
    background-color: #1890ff;
    color: white;
    border-radius: 20px;
    font-size: 16px;
}

#username_label {
    color: white;
    font-weight: bold;
    font-size: 14px;
}

#user_type_label {
    color: #b0b0b0;
    font-size: 12px;
}

#settings_btn {
    background-color: transparent;
    border: none;
    color: #b0b0b0;
    border-radius: 15px;
}

#settings_btn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
}

/* 头部样式 */
#header {
    background-color: white;
    border-bottom: 1px solid #e8e8e8;
}

#page_title {
    font-size: 20px;
    font-weight: bold;
    color: #333;
}

#search_input {
    background-color: #f5f5f5;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 0 15px;
    color: #333;
}

#search_input:focus {
    border: 1px solid #1890ff;
    outline: none;
}

#icon_button {
    background-color: transparent;
    border: none;
    color: #666;
    border-radius: 4px;
    font-size: 16px;
}

#icon_button:hover {
    background-color: #f5f5f5;
    color: #1890ff;
}

/* 按钮样式 */
QPushButton {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #40a9ff;
}

QPushButton:pressed {
    background-color: #096dd9;
}

QPushButton:disabled {
    background-color: #d9d9d9;
    color: #b0b0b0;
}

#primary_button {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}

#primary_button:hover {
    background-color: #40a9ff;
}

#secondary_button {
    background-color: white;
    color: #1890ff;
    border: 1px solid #1890ff;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}

#secondary_button:hover {
    background-color: #e6f7ff;
    border-color: #40a9ff;
}

/* 输入框样式 */
QLineEdit {
    background-color: white;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 8px 12px;
    color: #333;
}

QLineEdit:focus {
    border: 1px solid #1890ff;
    outline: none;
}

QLineEdit:hover {
    border-color: #40a9ff;
}

/* 组框样式 */
QGroupBox {
    font-weight: bold;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* 标签页样式 */
QTabWidget::pane {
    border: 1px solid #d9d9d9;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #f5f5f5;
    border: 1px solid #d9d9d9;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom-color: white;
    color: #1890ff;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #e6f7ff;
}

/* 组合框样式 */
QComboBox {
    background-color: white;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #40a9ff;
}

QComboBox:focus {
    border-color: #1890ff;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #666;
}

/* 旋转框样式 */
QSpinBox, QDoubleSpinBox {
    background-color: white;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 80px;
}

QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #40a9ff;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #1890ff;
    outline: none;
}

/* 复选框样式 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #d9d9d9;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:hover {
    border-color: #40a9ff;
}

QCheckBox::indicator:checked {
    background-color: #1890ff;
    border-color: #1890ff;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIgNkw1IDlMMTAgMyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
}

/* 进度条样式 */
QProgressBar {
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    text-align: center;
    background-color: #f5f5f5;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #1890ff;
    border-radius: 3px;
}

/* 滚动条样式 */
QScrollBar:vertical {
    border: none;
    background-color: #f5f5f5;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background-color: transparent;
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: transparent;
}

QScrollBar:horizontal {
    border: none;
    background-color: #f5f5f5;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background-color: transparent;
    width: 0;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background-color: transparent;
}

/* 对话框样式 */
QDialog {
    background-color: white;
    border-radius: 8px;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #f5f5f5;
    border-top: 1px solid #e8e8e8;
}

QStatusBar::item {
    border: none;
}

/* 菜单栏样式 */
QMenuBar {
    background-color: white;
    border-bottom: 1px solid #e8e8e8;
}

QMenuBar::item {
    padding: 8px 12px;
    background-color: transparent;
}

QMenuBar::item:selected {
    background-color: #e6f7ff;
    color: #1890ff;
}

QMenu {
    background-color: white;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
}

QMenu::item {
    padding: 8px 20px;
}

QMenu::item:selected {
    background-color: #e6f7ff;
    color: #1890ff;
}

QMenu::separator {
    height: 1px;
    background-color: #f0f0f0;
    margin: 5px 0;
}

/* 工具提示样式 */
QToolTip {
    background-color: #333;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
}
"""
