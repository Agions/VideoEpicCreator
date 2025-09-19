#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
键盘快捷键管理器 - 提供全局键盘快捷键支持
支持自定义快捷键、冲突检测和快捷键帮助
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QKeySequenceEdit, QMessageBox,
    QCheckBox, QComboBox, QGroupBox, QScrollArea,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings, QEvent, QObject
from PyQt6.QtGui import QKeySequence, QShortcutEvent, QAction, QShortcut

from .base_component import BaseComponent, ComponentConfig


class ShortcutCategory(Enum):
    """快捷键分类枚举"""
    GENERAL = "general"          # 通用
    NAVIGATION = "navigation"    # 导航
    EDITING = "editing"         # 编辑
    PROJECT = "project"         # 项目
    PLAYBACK = "playback"       # 播放
    VIEW = "view"              # 视图
    TOOLS = "tools"            # 工具
    CUSTOM = "custom"          # 自定义


@dataclass
class ShortcutAction:
    """快捷键动作数据类"""
    id: str
    name: str
    description: str
    category: ShortcutCategory
    default_key: str
    current_key: str
    context: str = "global"  # global, window, widget
    enabled: bool = True
    callback: Optional[Callable] = None
    override: bool = False  # 是否允许覆盖系统快捷键


class ShortcutConflictError(Exception):
    """快捷键冲突异常"""
    pass


class ShortcutManager(BaseComponent):
    """快捷键管理器"""
    
    shortcut_triggered = pyqtSignal(str, str)  # 快捷键触发信号 (action_id, context)
    shortcut_conflict = pyqtSignal(str, str, str)  # 快捷键冲突信号 (action_id, existing_action_id, key_sequence)
    
    def __init__(self, parent=None, config: Optional[ComponentConfig] = None):
        if config is None:
            config = ComponentConfig(
                name="ShortcutManager",
                theme_support=True,
                auto_save=True
            )
        super().__init__(parent, config)
        
        self.shortcuts: Dict[str, ShortcutAction] = {}
        self.active_shortcuts: Dict[str, QShortcut] = {}
        self.conflicts: List[Dict[str, str]] = []
        self.settings = QSettings("CineAIStudio", "ShortcutManager")
        
        self._load_default_shortcuts()
        self._load_user_shortcuts()
        self._register_global_shortcuts()
    
    def _setup_ui(self):
        """设置UI"""
        # 管理器不需要UI，只管理快捷键
        pass
    
    def _load_default_shortcuts(self):
        """加载默认快捷键"""
        default_shortcuts = [
            # 通用快捷键
            ShortcutAction(
                id="new_project",
                name="新建项目",
                description="创建新的视频项目",
                category=ShortcutCategory.GENERAL,
                default_key="Ctrl+N",
                current_key="Ctrl+N"
            ),
            ShortcutAction(
                id="open_project",
                name="打开项目",
                description="打开现有项目",
                category=ShortcutCategory.GENERAL,
                default_key="Ctrl+O",
                current_key="Ctrl+O"
            ),
            ShortcutAction(
                id="save_project",
                name="保存项目",
                description="保存当前项目",
                category=ShortcutCategory.GENERAL,
                default_key="Ctrl+S",
                current_key="Ctrl+S"
            ),
            ShortcutAction(
                id="save_as",
                name="另存为",
                description="项目另存为",
                category=ShortcutCategory.GENERAL,
                default_key="Ctrl+Shift+S",
                current_key="Ctrl+Shift+S"
            ),
            ShortcutAction(
                id="preferences",
                name="首选项",
                description="打开应用程序设置",
                category=ShortcutCategory.GENERAL,
                default_key="Ctrl+,",
                current_key="Ctrl+,"
            ),
            ShortcutAction(
                id="help",
                name="帮助",
                description="显示帮助信息",
                category=ShortcutCategory.GENERAL,
                default_key="F1",
                current_key="F1"
            ),
            
            # 导航快捷键
            ShortcutAction(
                id="next_page",
                name="下一页",
                description="切换到下一个页面",
                category=ShortcutCategory.NAVIGATION,
                default_key="Ctrl+Tab",
                current_key="Ctrl+Tab"
            ),
            ShortcutAction(
                id="prev_page",
                name="上一页",
                description="切换到上一个页面",
                category=ShortcutCategory.NAVIGATION,
                default_key="Ctrl+Shift+Tab",
                current_key="Ctrl+Shift+Tab"
            ),
            ShortcutAction(
                id="home_page",
                name="首页",
                description="返回首页",
                category=ShortcutCategory.NAVIGATION,
                default_key="Alt+Home",
                current_key="Alt+Home"
            ),
            
            # 编辑快捷键
            ShortcutAction(
                id="undo",
                name="撤销",
                description="撤销上一步操作",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+Z",
                current_key="Ctrl+Z"
            ),
            ShortcutAction(
                id="redo",
                name="重做",
                description="重做上一步操作",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+Y",
                current_key="Ctrl+Y"
            ),
            ShortcutAction(
                id="cut",
                name="剪切",
                description="剪切选中内容",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+X",
                current_key="Ctrl+X"
            ),
            ShortcutAction(
                id="copy",
                name="复制",
                description="复制选中内容",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+C",
                current_key="Ctrl+C"
            ),
            ShortcutAction(
                id="paste",
                name="粘贴",
                description="粘贴内容",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+V",
                current_key="Ctrl+V"
            ),
            ShortcutAction(
                id="delete",
                name="删除",
                description="删除选中内容",
                category=ShortcutCategory.EDITING,
                default_key="Delete",
                current_key="Delete"
            ),
            ShortcutAction(
                id="select_all",
                name="全选",
                description="选择所有内容",
                category=ShortcutCategory.EDITING,
                default_key="Ctrl+A",
                current_key="Ctrl+A"
            ),
            
            # 播放快捷键
            ShortcutAction(
                id="play_pause",
                name="播放/暂停",
                description="播放或暂停视频",
                category=ShortcutCategory.PLAYBACK,
                default_key="Space",
                current_key="Space"
            ),
            ShortcutAction(
                id="stop",
                name="停止",
                description="停止播放",
                category=ShortcutCategory.PLAYBACK,
                default_key=".",
                current_key="."
            ),
            ShortcutAction(
                id="seek_forward",
                name="快进",
                description="向前快进5秒",
                category=ShortcutCategory.PLAYBACK,
                default_key="Right",
                current_key="Right"
            ),
            ShortcutAction(
                id="seek_backward",
                name="快退",
                description="向后快退5秒",
                category=ShortcutCategory.PLAYBACK,
                default_key="Left",
                current_key="Left"
            ),
            ShortcutAction(
                id="seek_forward_large",
                name="大步快进",
                description="向前快进30秒",
                category=ShortcutCategory.PLAYBACK,
                default_key="Shift+Right",
                current_key="Shift+Right"
            ),
            ShortcutAction(
                id="seek_backward_large",
                name="大步快退",
                description="向后快退30秒",
                category=ShortcutCategory.PLAYBACK,
                default_key="Shift+Left",
                current_key="Shift+Left"
            ),
            
            # 视图快捷键
            ShortcutAction(
                id="fullscreen",
                name="全屏",
                description="切换全屏模式",
                category=ShortcutCategory.VIEW,
                default_key="F11",
                current_key="F11"
            ),
            ShortcutAction(
                id="zoom_in",
                name="放大",
                description="放大视图",
                category=ShortcutCategory.VIEW,
                default_key="Ctrl++",
                current_key="Ctrl++"
            ),
            ShortcutAction(
                id="zoom_out",
                name="缩小",
                description="缩小视图",
                category=ShortcutCategory.VIEW,
                default_key="Ctrl+-",
                current_key="Ctrl+-"
            ),
            ShortcutAction(
                id="zoom_reset",
                name="重置缩放",
                description="重置缩放级别",
                category=ShortcutCategory.VIEW,
                default_key="Ctrl+0",
                current_key="Ctrl+0"
            ),
            
            # 工具快捷键
            ShortcutAction(
                id="toggle_tools",
                name="显示/隐藏工具栏",
                description="切换工具栏显示",
                category=ShortcutCategory.TOOLS,
                default_key="Ctrl+T",
                current_key="Ctrl+T"
            ),
            ShortcutAction(
                id="toggle_timeline",
                name="显示/隐藏时间轴",
                description="切换时间轴显示",
                category=ShortcutCategory.TOOLS,
                default_key="Ctrl+L",
                current_key="Ctrl+L"
            ),
            ShortcutAction(
                id="toggle_properties",
                name="显示/隐藏属性",
                description="切换属性面板显示",
                category=ShortcutCategory.TOOLS,
                default_key="Ctrl+P",
                current_key="Ctrl+P"
            )
        ]
        
        for shortcut in default_shortcuts:
            self.shortcuts[shortcut.id] = shortcut
    
    def _load_user_shortcuts(self):
        """加载用户自定义快捷键"""
        try:
            user_shortcuts = self.settings.value("user_shortcuts", {})
            if user_shortcuts:
                for action_id, key_sequence in user_shortcuts.items():
                    if action_id in self.shortcuts:
                        self.shortcuts[action_id].current_key = key_sequence
        except Exception as e:
            self._handle_error(f"加载用户快捷键失败: {e}", "LOAD_ERROR")
    
    def _save_user_shortcuts(self):
        """保存用户自定义快捷键"""
        try:
            user_shortcuts = {
                action_id: shortcut.current_key
                for action_id, shortcut in self.shortcuts.items()
                if shortcut.current_key != shortcut.default_key
            }
            self.settings.setValue("user_shortcuts", user_shortcuts)
            self.settings.sync()
        except Exception as e:
            self._handle_error(f"保存用户快捷键失败: {e}", "SAVE_ERROR")
    
    def _register_global_shortcuts(self):
        """注册全局快捷键"""
        if not self.parent():
            return
        
        for action_id, shortcut in self.shortcuts.items():
            if shortcut.enabled and shortcut.context == "global":
                self._register_shortcut(action_id, shortcut)
    
    def _register_shortcut(self, action_id: str, shortcut: ShortcutAction):
        """注册单个快捷键"""
        if not self.parent():
            return
        
        try:
            # 检查冲突
            conflict = self._check_conflict(action_id, shortcut.current_key)
            if conflict:
                self.shortcut_conflict.emit(action_id, conflict, shortcut.current_key)
                self._logger.warning(f"快捷键冲突: {action_id} 与 {conflict} 冲突")
                return
            
            # 创建快捷键
            qshortcut = QShortcut(QKeySequence(shortcut.current_key), self.parent())
            if shortcut.callback:
                qshortcut.activated.connect(shortcut.callback)
            else:
                qshortcut.activated.connect(lambda: self._on_shortcut_triggered(action_id))
            
            self.active_shortcuts[action_id] = qshortcut
            
        except Exception as e:
            self._handle_error(f"注册快捷键失败 {action_id}: {e}", "REGISTER_ERROR")
    
    def _check_conflict(self, action_id: str, key_sequence: str) -> Optional[str]:
        """检查快捷键冲突"""
        for existing_id, existing_shortcut in self.shortcuts.items():
            if (existing_id != action_id and 
                existing_shortcut.current_key == key_sequence and
                existing_shortcut.enabled):
                return existing_id
        return None
    
    def _on_shortcut_triggered(self, action_id: str):
        """快捷键触发处理"""
        shortcut = self.shortcuts.get(action_id)
        if shortcut:
            self.shortcut_triggered.emit(action_id, shortcut.context)
            self._logger.info(f"快捷键触发: {shortcut.name} ({shortcut.current_key})")
    
    def register_callback(self, action_id: str, callback: Callable):
        """注册快捷键回调函数"""
        if action_id in self.shortcuts:
            self.shortcuts[action_id].callback = callback
            
            # 如果快捷键已激活，更新回调
            if action_id in self.active_shortcuts:
                self.active_shortcuts[action_id].activated.connect(callback)
    
    def add_shortcut(self, key_sequence: str, description: str, callback: Callable) -> str:
        """添加新的快捷键"""
        import uuid
        
        # 生成唯一的action_id
        action_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # 创建新的快捷键动作
        action = ShortcutAction(
            id=action_id,
            name=description,
            description=description,
            category=ShortcutCategory.CUSTOM,
            default_key=key_sequence,
            current_key=key_sequence,
            callback=callback
        )
        
        # 添加到快捷键字典
        self.shortcuts[action_id] = action
        
        # 注册快捷键
        self._register_shortcut(action_id, action)
        
        return action_id
    
    def set_shortcut(self, action_id: str, key_sequence: str, check_conflict: bool = True) -> bool:
        """设置快捷键"""
        if action_id not in self.shortcuts:
            return False
        
        # 检查冲突
        if check_conflict:
            conflict = self._check_conflict(action_id, key_sequence)
            if conflict:
                return False
        
        # 更新快捷键
        self.shortcuts[action_id].current_key = key_sequence
        
        # 重新注册快捷键
        if action_id in self.active_shortcuts:
            self.active_shortcuts[action_id].deleteLater()
            del self.active_shortcuts[action_id]
        
        if self.shortcuts[action_id].enabled:
            self._register_shortcut(action_id, self.shortcuts[action_id])
        
        # 保存设置
        self._save_user_shortcuts()
        
        return True
    
    def get_shortcut(self, action_id: str) -> Optional[ShortcutAction]:
        """获取快捷键"""
        return self.shortcuts.get(action_id)
    
    def get_all_shortcuts(self) -> Dict[str, ShortcutAction]:
        """获取所有快捷键"""
        return self.shortcuts.copy()
    
    def get_shortcuts_by_category(self, category: ShortcutCategory) -> List[ShortcutAction]:
        """按分类获取快捷键"""
        return [s for s in self.shortcuts.values() if s.category == category]
    
    def enable_shortcut(self, action_id: str, enabled: bool = True):
        """启用/禁用快捷键"""
        if action_id not in self.shortcuts:
            return
        
        self.shortcuts[action_id].enabled = enabled
        
        if enabled:
            self._register_shortcut(action_id, self.shortcuts[action_id])
        elif action_id in self.active_shortcuts:
            self.active_shortcuts[action_id].deleteLater()
            del self.active_shortcuts[action_id]
    
    def reset_shortcut(self, action_id: str):
        """重置快捷键到默认值"""
        if action_id not in self.shortcuts:
            return
        
        shortcut = self.shortcuts[action_id]
        self.set_shortcut(action_id, shortcut.default_key)
    
    def reset_all_shortcuts(self):
        """重置所有快捷键到默认值"""
        for action_id in self.shortcuts:
            self.reset_shortcut(action_id)
    
    def export_shortcuts(self, file_path: str):
        """导出快捷键配置"""
        try:
            config = {
                action_id: {
                    "name": shortcut.name,
                    "current_key": shortcut.current_key,
                    "enabled": shortcut.enabled
                }
                for action_id, shortcut in self.shortcuts.items()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self._handle_error(f"导出快捷键配置失败: {e}", "EXPORT_ERROR")
            return False
    
    def import_shortcuts(self, file_path: str):
        """导入快捷键配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for action_id, shortcut_config in config.items():
                if action_id in self.shortcuts:
                    self.shortcuts[action_id].current_key = shortcut_config.get("current_key", self.shortcuts[action_id].default_key)
                    self.shortcuts[action_id].enabled = shortcut_config.get("enabled", True)
            
            # 重新注册快捷键
            self._unregister_all_shortcuts()
            self._register_global_shortcuts()
            
            # 保存设置
            self._save_user_shortcuts()
            
            return True
        except Exception as e:
            self._handle_error(f"导入快捷键配置失败: {e}", "IMPORT_ERROR")
            return False
    
    def _unregister_all_shortcuts(self):
        """注销所有快捷键"""
        for shortcut in self.active_shortcuts.values():
            shortcut.deleteLater()
        self.active_shortcuts.clear()
    
    def show_shortcut_help(self):
        """显示快捷键帮助"""
        dialog = ShortcutHelpDialog(self.shortcuts, self.parent())
        dialog.exec()
    
    def cleanup(self):
        """清理资源"""
        self._unregister_all_shortcuts()
        super().cleanup()


class ShortcutSettingsDialog(QDialog):
    """快捷键设置对话框"""
    
    def __init__(self, shortcut_manager: ShortcutManager, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        self.setWindowTitle("快捷键设置")
        self.setModal(True)
        self.resize(700, 500)
        
        self._setup_ui()
        self._load_shortcuts()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 说明
        info_label = QLabel("双击快捷键进行编辑，点击冲突按钮查看详情")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)
        
        # 快捷键表格
        self.shortcut_table = QTableWidget()
        self.shortcut_table.setColumnCount(4)
        self.shortcut_table.setHorizontalHeaderLabels(["操作", "快捷键", "分类", "状态"])
        self.shortcut_table.horizontalHeader().setStretchLastSection(True)
        self.shortcut_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.shortcut_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shortcut_table.itemDoubleClicked.connect(self._on_edit_shortcut)
        
        layout.addWidget(self.shortcut_table)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("重置选中")
        reset_btn.clicked.connect(self._reset_selected)
        button_layout.addWidget(reset_btn)
        
        reset_all_btn = QPushButton("重置全部")
        reset_all_btn.clicked.connect(self._reset_all)
        button_layout.addWidget(reset_all_btn)
        
        export_btn = QPushButton("导出配置")
        export_btn.clicked.connect(self._export_config)
        button_layout.addWidget(export_btn)
        
        import_btn = QPushButton("导入配置")
        import_btn.clicked.connect(self._import_config)
        button_layout.addWidget(import_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_shortcuts(self):
        """加载快捷键到表格"""
        shortcuts = self.shortcut_manager.get_all_shortcuts()
        self.shortcut_table.setRowCount(len(shortcuts))
        
        category_names = {
            ShortcutCategory.GENERAL: "通用",
            ShortcutCategory.NAVIGATION: "导航",
            ShortcutCategory.EDITING: "编辑",
            ShortcutCategory.PLAYBACK: "播放",
            ShortcutCategory.VIEW: "视图",
            ShortcutCategory.TOOLS: "工具",
            ShortcutCategory.CUSTOM: "自定义"
        }
        
        for row, (action_id, shortcut) in enumerate(shortcuts.items()):
            # 操作名称
            name_item = QTableWidgetItem(shortcut.name)
            name_item.setData(Qt.ItemDataRole.UserRole, action_id)
            self.shortcut_table.setItem(row, 0, name_item)
            
            # 快捷键
            key_item = QTableWidgetItem(shortcut.current_key)
            self.shortcut_table.setItem(row, 1, key_item)
            
            # 分类
            category_item = QTableWidgetItem(category_names.get(shortcut.category, "其他"))
            self.shortcut_table.setItem(row, 2, category_item)
            
            # 状态
            status_text = "启用" if shortcut.enabled else "禁用"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor("#4caf50" if shortcut.enabled else "#f44336"))
            self.shortcut_table.setItem(row, 3, status_item)
    
    def _on_edit_shortcut(self, item):
        """编辑快捷键"""
        row = item.row()
        action_id = self.shortcut_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        dialog = ShortcutEditDialog(self.shortcut_manager, action_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_shortcuts()
    
    def _reset_selected(self):
        """重置选中的快捷键"""
        current_row = self.shortcut_table.currentRow()
        if current_row >= 0:
            action_id = self.shortcut_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            self.shortcut_manager.reset_shortcut(action_id)
            self._load_shortcuts()
    
    def _reset_all(self):
        """重置所有快捷键"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有快捷键到默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.shortcut_manager.reset_all_shortcuts()
            self._load_shortcuts()
    
    def _export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出快捷键配置", "shortcuts.json", "JSON文件 (*.json)"
        )
        
        if file_path:
            if self.shortcut_manager.export_shortcuts(file_path):
                QMessageBox.information(self, "导出成功", "快捷键配置已导出")
            else:
                QMessageBox.warning(self, "导出失败", "导出快捷键配置失败")
    
    def _import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入快捷键配置", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            if self.shortcut_manager.import_shortcuts(file_path):
                self._load_shortcuts()
                QMessageBox.information(self, "导入成功", "快捷键配置已导入")
            else:
                QMessageBox.warning(self, "导入失败", "导入快捷键配置失败")


class ShortcutEditDialog(QDialog):
    """快捷键编辑对话框"""
    
    def __init__(self, shortcut_manager: ShortcutManager, action_id: str, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        self.action_id = action_id
        self.shortcut = shortcut_manager.get_shortcut(action_id)
        
        self.setWindowTitle(f"编辑快捷键 - {self.shortcut.name}")
        self.setModal(True)
        self.resize(400, 300)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 信息
        info_group = QGroupBox("快捷键信息")
        info_layout = QFormLayout(info_group)
        
        name_label = QLabel(self.shortcut.name)
        name_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("操作名称:", name_label)
        
        desc_label = QLabel(self.shortcut.description)
        desc_label.setWordWrap(True)
        info_layout.addRow("描述:", desc_label)
        
        category_names = {
            ShortcutCategory.GENERAL: "通用",
            ShortcutCategory.NAVIGATION: "导航",
            ShortcutCategory.EDITING: "编辑",
            ShortcutCategory.PLAYBACK: "播放",
            ShortcutCategory.VIEW: "视图",
            ShortcutCategory.TOOLS: "工具",
            ShortcutCategory.CUSTOM: "自定义"
        }
        category_label = QLabel(category_names.get(self.shortcut.category, "其他"))
        info_layout.addRow("分类:", category_label)
        
        layout.addWidget(info_group)
        
        # 快捷键设置
        key_group = QGroupBox("快捷键设置")
        key_layout = QFormLayout(key_group)
        
        self.key_edit = QKeySequenceEdit()
        key_layout.addRow("快捷键:", self.key_edit)
        
        self.enabled_check = QCheckBox("启用此快捷键")
        key_layout.addRow("", self.enabled_check)
        
        layout.addWidget(key_group)
        
        # 冲突警告
        self.conflict_label = QLabel()
        self.conflict_label.setStyleSheet("color: #f44336; font-size: 12px;")
        self.conflict_label.setWordWrap(True)
        layout.addWidget(self.conflict_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_shortcut)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.key_edit.keySequenceChanged.connect(self._check_conflict)
    
    def _load_data(self):
        """加载数据"""
        self.key_edit.setKeySequence(QKeySequence(self.shortcut.current_key))
        self.enabled_check.setChecked(self.shortcut.enabled)
    
    def _check_conflict(self):
        """检查冲突"""
        key_sequence = self.key_edit.keySequence().toString()
        if not key_sequence:
            self.conflict_label.clear()
            return
        
        conflict = self.shortcut_manager._check_conflict(self.action_id, key_sequence)
        if conflict:
            conflict_shortcut = self.shortcut_manager.get_shortcut(conflict)
            self.conflict_label.setText(f"⚠️ 与 '{conflict_shortcut.name}' 冲突")
        else:
            self.conflict_label.clear()
    
    def _reset_to_default(self):
        """重置为默认值"""
        self.key_edit.setKeySequence(QKeySequence(self.shortcut.default_key))
        self.conflict_label.clear()
    
    def _save_shortcut(self):
        """保存快捷键"""
        key_sequence = self.key_edit.keySequence().toString()
        
        if key_sequence:
            conflict = self.shortcut_manager._check_conflict(self.action_id, key_sequence)
            if conflict:
                QMessageBox.warning(self, "快捷键冲突", 
                                 f"此快捷键与 '{self.shortcut_manager.get_shortcut(conflict).name}' 冲突")
                return
        
        # 设置快捷键
        if self.shortcut_manager.set_shortcut(self.action_id, key_sequence, check_conflict=False):
            self.shortcut_manager.enable_shortcut(self.action_id, self.enabled_check.isChecked())
            self.accept()
        else:
            QMessageBox.warning(self, "保存失败", "保存快捷键失败")


class ShortcutHelpDialog(QDialog):
    """快捷键帮助对话框"""
    
    def __init__(self, shortcuts: Dict[str, ShortcutAction], parent=None):
        super().__init__(parent)
        self.shortcuts = shortcuts
        self.setWindowTitle("快捷键帮助")
        self.setModal(True)
        self.resize(600, 500)
        
        self._setup_ui()
        self._load_shortcuts()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("快捷键帮助")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 按分类创建选项卡
        category_names = {
            ShortcutCategory.GENERAL: "通用",
            ShortcutCategory.NAVIGATION: "导航", 
            ShortcutCategory.EDITING: "编辑",
            ShortcutCategory.PLAYBACK: "播放",
            ShortcutCategory.VIEW: "视图",
            ShortcutCategory.TOOLS: "工具",
            ShortcutCategory.CUSTOM: "自定义"
        }
        
        for category in ShortcutCategory:
            if category != ShortcutCategory.CUSTOM or any(s.category == category for s in self.shortcuts.values()):
                category_widget = self._create_category_widget(category)
                self.tab_widget.addTab(category_widget, category_names.get(category, "其他"))
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedSize(100, 32)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def _create_category_widget(self, category: ShortcutCategory) -> QWidget:
        """创建分类选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 表格
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["操作", "快捷键", "描述"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        # 筛选该分类的快捷键
        category_shortcuts = [s for s in self.shortcuts.values() if s.category == category and s.enabled]
        table.setRowCount(len(category_shortcuts))
        
        for row, shortcut in enumerate(category_shortcuts):
            # 操作名称
            name_item = QTableWidgetItem(shortcut.name)
            table.setItem(row, 0, name_item)
            
            # 快捷键
            key_item = QTableWidgetItem(shortcut.current_key)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, key_item)
            
            # 描述
            desc_item = QTableWidgetItem(shortcut.description)
            desc_item.setForeground(QColor("#666"))
            table.setItem(row, 2, desc_item)
        
        layout.addWidget(table)
        
        return widget
    
    def _load_shortcuts(self):
        """加载快捷键"""
        pass


# 工厂函数
def create_shortcut_manager(parent=None) -> ShortcutManager:
    """创建快捷键管理器"""
    return ShortcutManager(parent)


def get_shortcut_dialog(shortcut_manager: ShortcutManager, parent=None) -> ShortcutSettingsDialog:
    """获取快捷键设置对话框"""
    return ShortcutSettingsDialog(shortcut_manager, parent)


def get_shortcut_help_dialog(shortcuts: Dict[str, ShortcutAction], parent=None) -> ShortcutHelpDialog:
    """获取快捷键帮助对话框"""
    return ShortcutHelpDialog(shortcuts, parent)


# 全局实例
_global_shortcut_manager = None


def get_global_shortcut_manager() -> ShortcutManager:
    """获取全局快捷键管理器"""
    global _global_shortcut_manager
    if _global_shortcut_manager is None:
        _global_shortcut_manager = create_shortcut_manager()
    return _global_shortcut_manager


# 便捷函数
def register_shortcut(action_id: str, callback: Callable):
    """注册全局快捷键回调"""
    get_global_shortcut_manager().register_callback(action_id, callback)


def set_shortcut(action_id: str, key_sequence: str) -> bool:
    """设置全局快捷键"""
    return get_global_shortcut_manager().set_shortcut(action_id, key_sequence)


def get_shortcut(action_id: str) -> Optional[ShortcutAction]:
    """获取全局快捷键"""
    return get_global_shortcut_manager().get_shortcut(action_id)


def show_shortcut_help():
    """显示快捷键帮助"""
    get_global_shortcut_manager().show_shortcut_help()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
    
    app = QApplication(sys.argv)
    
    # 测试窗口
    window = QWidget()
    window.setWindowTitle("快捷键管理器测试")
    window.resize(400, 300)
    
    layout = QVBoxLayout(window)
    
    label = QLabel("测试快捷键功能")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    # 创建快捷键管理器
    shortcut_manager = create_shortcut_manager(window)
    
    # 注册测试回调
    def test_callback():
        print("快捷键触发!")
        label.setText("快捷键已触发!")
    
    shortcut_manager.register_callback("new_project", test_callback)
    
    # 测试按钮
    settings_btn = QPushButton("快捷键设置")
    settings_btn.clicked.connect(lambda: ShortcutSettingsDialog(shortcut_manager, window).exec())
    layout.addWidget(settings_btn)
    
    help_btn = QPushButton("快捷键帮助")
    help_btn.clicked.connect(shortcut_manager.show_shortcut_help)
    layout.addWidget(help_btn)
    
    window.show()
    sys.exit(app.exec())