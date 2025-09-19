#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from .api_key_manager import APIKeyManager
from .defaults import DEFAULT_SETTINGS


class SettingsManager(QObject):
    """设置管理器"""

    # 信号
    settings_changed = pyqtSignal(str, object)  # 设置项名称, 新值

    def __init__(self, config_dir: Optional[str] = None):
        super().__init__()

        # 配置目录
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".CineAIStudio")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 配置文件路径
        self.settings_file = self.config_dir / "settings.json"
        self.projects_file = self.config_dir / "projects.json"

        # API密钥管理器
        self.api_key_manager = APIKeyManager(self.config_dir)

        # 当前设置
        self._settings = {}
        self._projects = []

        # 主题管理器（延迟初始化）
        self._theme_manager = None

        # 加载设置
        self.load_settings()
        self.load_projects()

        # 连接主题管理器
        self._connect_theme_manager()

    def load_settings(self):
        """加载设置"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            else:
                self._settings = DEFAULT_SETTINGS.copy()
                self.save_settings()
        except Exception as e:
            print(f"加载设置失败: {e}")
            self._settings = DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """保存设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")

    def get_setting(self, key: str, default=None):
        """获取设置值"""
        keys = key.split('.')
        value = self._settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set_setting(self, key: str, value: Any):
        """设置值"""
        keys = key.split('.')
        current = self._settings

        # 导航到父级字典
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # 设置值
        old_value = current.get(keys[-1])
        current[keys[-1]] = value

        # 保存设置
        self.save_settings()

        # 发射信号
        if old_value != value:
            self.settings_changed.emit(key, value)

            # 特殊处理主题设置
            if key == "app.theme":
                self._handle_theme_change(value)

    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        return self._settings.copy()

    def reset_settings(self):
        """重置设置为默认值"""
        self._settings = DEFAULT_SETTINGS.copy()
        self.save_settings()

    # 项目管理
    def load_projects(self):
        """加载项目列表"""
        try:
            if self.projects_file.exists():
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    self._projects = json.load(f)
            else:
                self._projects = []
        except Exception as e:
            print(f"加载项目列表失败: {e}")
            self._projects = []

    def save_projects(self):
        """保存项目列表"""
        try:
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(self._projects, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存项目列表失败: {e}")

    def get_projects(self) -> list:
        """获取项目列表"""
        return self._projects.copy()

    def add_project(self, project_info: Dict[str, Any]):
        """添加项目"""
        self._projects.append(project_info)
        self.save_projects()

    def remove_project(self, project_id: str):
        """移除项目"""
        self._projects = [p for p in self._projects if p.get('id') != project_id]
        self.save_projects()

    def update_project(self, project_id: str, project_info: Dict[str, Any]):
        """更新项目信息"""
        for i, project in enumerate(self._projects):
            if project.get('id') == project_id:
                self._projects[i] = project_info
                break
        self.save_projects()

    # API密钥管理
    def set_api_key(self, provider: str, api_key: str):
        """设置API密钥"""
        self.api_key_manager.set_api_key(provider, api_key)

    def get_api_key(self, provider: str) -> str:
        """获取API密钥"""
        return self.api_key_manager.get_api_key(provider)

    def get_masked_api_key(self, provider: str) -> str:
        """获取掩码显示的API密钥"""
        return self.api_key_manager.get_masked_api_key(provider)

    def has_api_key(self, provider: str) -> bool:
        """检查是否有API密钥"""
        return self.api_key_manager.has_api_key(provider)

    def remove_api_key(self, provider: str):
        """移除API密钥"""
        self.api_key_manager.remove_api_key(provider)

    # 主题管理
    def _connect_theme_manager(self):
        """连接主题管理器"""
        try:
            # 延迟导入避免循环依赖
            from ..ui.theme_manager import get_theme_manager
            self._theme_manager = get_theme_manager()

            # 应用保存的主题设置
            saved_theme = self.get_setting("app.theme", "light")
            self._theme_manager.set_theme(saved_theme)

        except ImportError as e:
            print(f"⚠️ 无法导入主题管理器: {e}")

    def _handle_theme_change(self, theme_value: str):
        """处理主题变更"""
        if self._theme_manager:
            self._theme_manager.set_theme(theme_value)

    def get_theme_manager(self):
        """获取主题管理器"""
        if self._theme_manager is None:
            self._connect_theme_manager()
        return self._theme_manager
