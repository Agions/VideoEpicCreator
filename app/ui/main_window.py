"""
Ant Design 主窗口
现代化视频编辑工具的主界面
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QScrollArea,
    QSplitter, QMenuBar, QStatusBar, QToolBar, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap, QPalette, QColor

from .sidebar import Sidebar
from .header import Header
from .dashboard import Dashboard
from .ant_dashboard import AntDashboard
from .settings_dialog import SettingsDialog
from .jianying_dialog import JianyingIntegrationDialog
from .styles import STYLESHEET
from .styles.ant_design import theme_manager
from .widgets.ant_buttons import AntButton, PrimaryButton, TextButton
from .widgets.ant_cards import AntCard, CardMeta, CardContent


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoEpicCreator")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(STYLESHEET)

        # 初始化UI组件
        self.init_ui()
        self.init_menu()
        self.init_status_bar()

    def init_ui(self):
        """初始化UI组件"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.navigation_clicked.connect(self.on_navigation_clicked)
        self.sidebar.settings_clicked.connect(self.show_settings)
        splitter.addWidget(self.sidebar)

        # 右侧内容区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部导航栏
        self.header = Header()
        self.header.settings_clicked.connect(self.show_settings)
        right_layout.addWidget(self.header)

        # 内容堆栈
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack)

        # 添加页面
        self.dashboard = AntDashboard()
        self.content_stack.addWidget(self.dashboard)

        # 添加其他页面占位符
        self.projects_page = self.create_placeholder_page("项目管理")
        self.editor_page = self.create_placeholder_page("视频编辑器")
        self.ai_studio_page = self.create_placeholder_page("AI工作室")
        self.import_page = self.create_placeholder_page("导入媒体")
        self.export_page = self.create_placeholder_page("导出视频")

        self.content_stack.addWidget(self.projects_page)
        self.content_stack.addWidget(self.editor_page)
        self.content_stack.addWidget(self.ai_studio_page)
        self.content_stack.addWidget(self.import_page)
        self.content_stack.addWidget(self.export_page)

        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([250, 950])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建项目(&N)", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)

        open_action = QAction("打开项目(&O)", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)

        save_as_action = QAction("另存为(&A)", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        jianying_action = QAction("剪映集成(&J)", self)
        jianying_action.setShortcut("Ctrl+J")
        jianying_action.triggered.connect(self.show_jianying_integration)
        tools_menu.addAction(jianying_action)

        tools_menu.addSeparator()

        settings_action = QAction("设置(&S)", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def init_status_bar(self):
        """初始化状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # 添加状态信息
        self.status_label = QLabel("就绪")
        status_bar.addPermanentWidget(self.status_label)

        # 添加内存使用情况
        self.memory_label = QLabel("内存: 256MB")
        status_bar.addPermanentWidget(self.memory_label)

    def create_placeholder_page(self, title):
        """创建占位符页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #666; margin-top: 100px;")

        layout.addWidget(label)

        return widget

    def on_navigation_clicked(self, page_name):
        """处理导航点击事件"""
        page_map = {
            "dashboard": 0,
            "projects": 1,
            "editor": 2,
            "ai_studio": 3,
            "import": 4,
            "export": 5
        }

        if page_name in page_map:
            self.content_stack.setCurrentIndex(page_map[page_name])
            self.status_label.setText(f"当前页面: {page_name}")

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_jianying_integration(self):
        """显示剪映集成对话框"""
        dialog = JianyingIntegrationDialog(self)
        dialog.exec()

    def show_about(self):
        """显示关于对话框"""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "关于 VideoEpicCreator",
            "VideoEpicCreator v1.0.0\n\n"
            "一个现代化的视频创作工具\n\n"
            "© 2024 VideoEpicCreator Team"
        )

    def closeEvent(self, event):
        """处理关闭事件"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出 VideoEpicCreator 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式获得更现代的外观

    # 设置应用程序信息
    app.setApplicationName("VideoEpicCreator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VideoEpicCreator")

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
