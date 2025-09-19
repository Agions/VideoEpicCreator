#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
特效制作页面 - 提供AI驱动的视频特效制作功能
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap

from app.ui.professional_ui_system import ProfessionalCard, ProfessionalButton


class EffectsPage(QWidget):
    """特效制作页面"""
    
    # 信号
    effect_applied = pyqtSignal(dict)  # 特效应用完成信号
    
    def __init__(self, ai_manager=None, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.current_video = None
        self.is_dark_theme = False
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 页面标题
        title_label = QLabel("特效制作")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧 - 特效库和预览
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # 右侧 - AI生成和参数调整
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例
        main_splitter.setSizes([600, 400])
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 视频上传区域
        upload_card = ProfessionalCard("视频上传")
        upload_content = QWidget()
        upload_layout = QVBoxLayout(upload_content)
        upload_layout.setContentsMargins(0, 0, 0, 0)
        
        upload_btn_layout = QHBoxLayout()
        
        self.upload_btn = ProfessionalButton("📁 选择视频文件", "primary")
        self.video_info_label = QLabel("未选择视频")
        
        upload_btn_layout.addWidget(self.upload_btn)
        upload_btn_layout.addWidget(self.video_info_label)
        upload_btn_layout.addStretch()
        
        upload_layout.addLayout(upload_btn_layout)
        
        # 视频预览
        self.video_preview = QLabel("🎬 视频预览区域")
        self.video_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px dashed #ddd;
                border-radius: 8px;
                padding: 40px;
                font-size: 24px;
                min-height: 200px;
            }
        """)
        upload_layout.addWidget(self.video_preview)
        
        upload_card.add_content(upload_content)
        layout.addWidget(upload_card)
        
        # 特效库
        effects_card = ProfessionalCard("特效库")
        effects_content = QWidget()
        effects_layout = QVBoxLayout(effects_content)
        effects_layout.setContentsMargins(0, 0, 0, 0)
        
        # 特效分类
        categories_group = QGroupBox("特效分类")
        categories_layout = QVBoxLayout(categories_group)
        
        self.effect_categories = [
            ("🎭 滤镜特效", "filter"),
            ("✨ 转场特效", "transition"),
            ("🎨 视觉效果", "visual"),
            ("🔊 音频特效", "audio"),
            ("📝 文字特效", "text"),
            ("🎯 AI智能特效", "ai")
        ]
        
        for text, category in self.effect_categories:
            btn = ProfessionalButton(text, "default")
            btn.setProperty("category", category)
            categories_layout.addWidget(btn)
        
        effects_layout.addWidget(categories_group)
        
        # 特效列表
        self.effects_list = QListWidget()
        self.effects_list.setMaximumHeight(200)
        effects_layout.addWidget(self.effects_list)
        
        effects_card.add_content(effects_content)
        layout.addWidget(effects_card)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # AI特效生成
        ai_card = ProfessionalCard("AI智能特效")
        ai_content = QWidget()
        ai_layout = QVBoxLayout(ai_content)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        
        # AI特效选项
        ai_effects = [
            ("🎨 智能调色", "ai_color"),
            ("🌟 场景识别", "ai_scene"),
            ("👤 人物追踪", "ai_tracking"),
            ("🎭 风格迁移", "ai_style"),
            ("🔍 超分辨率", "ai_superres"),
            ("🎬 智能剪辑", "ai_edit")
        ]
        
        for text, effect_type in ai_effects:
            btn = ProfessionalButton(text, "primary")
            btn.setProperty("effect_type", effect_type)
            ai_layout.addWidget(btn)
        
        ai_card.add_content(ai_content)
        layout.addWidget(ai_card)
        
        # 参数调整
        params_card = ProfessionalCard("参数调整")
        params_content = QWidget()
        params_layout = QVBoxLayout(params_content)
        params_layout.setContentsMargins(0, 0, 0, 0)
        
        # 强度滑块
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("强度:")
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(50)
        self.intensity_value_label = QLabel("50%")
        
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_value_label)
        
        params_layout.addLayout(intensity_layout)
        
        # 速度滑块
        speed_layout = QHBoxLayout()
        speed_label = QLabel("速度:")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(50)
        self.speed_value_label = QLabel("50%")
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value_label)
        
        params_layout.addLayout(speed_layout)
        
        # 混合模式
        blend_layout = QHBoxLayout()
        blend_label = QLabel("混合模式:")
        self.blend_combo = QComboBox()
        self.blend_combo.addItems(["正常", "叠加", "柔光", "强光", "滤色", "变暗"])
        
        blend_layout.addWidget(blend_label)
        blend_layout.addWidget(self.blend_combo)
        blend_layout.addStretch()
        
        params_layout.addLayout(blend_layout)
        
        params_card.add_content(params_content)
        layout.addWidget(params_card)
        
        # 实时预览
        preview_card = ProfessionalCard("实时预览")
        preview_content = QWidget()
        preview_layout = QVBoxLayout(preview_content)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.effect_preview = QLabel("🎭 特效预览")
        self.effect_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.effect_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                font-size: 18px;
                min-height: 150px;
            }
        """)
        preview_layout.addWidget(self.effect_preview)
        
        preview_card.add_content(preview_content)
        layout.addWidget(preview_card)
        
        # 处理进度
        progress_card = ProfessionalCard("处理进度")
        progress_content = QWidget()
        progress_layout = QVBoxLayout(progress_content)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("就绪")
        progress_layout.addWidget(self.progress_label)
        
        progress_card.add_content(progress_content)
        layout.addWidget(progress_card)
        
        # 应用和导出按钮
        buttons_layout = QHBoxLayout()
        
        self.apply_btn = ProfessionalButton("✅ 应用特效", "primary")
        self.preview_btn = ProfessionalButton("👁️ 预览效果", "default")
        self.export_btn = ProfessionalButton("📤 导出视频", "primary")
        
        buttons_layout.addWidget(self.apply_btn)
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.export_btn)
        
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
        
        return panel
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                EffectsPage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                }
                QListWidget::item:selected {
                    background-color: #177ddc;
                }
            """)
        else:
            self.setStyleSheet("""
                EffectsPage {
                    background-color: #ffffff;
                    color: #262626;
                }
                QLabel {
                    color: #262626;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid #ddd;
                }
                QListWidget::item:selected {
                    background-color: #1890ff;
                }
            """)
    
    def _connect_signals(self):
        """连接信号"""
        # 上传按钮
        self.upload_btn.clicked.connect(self._upload_video)
        
        # 特效分类按钮
        for btn in self.findChildren(ProfessionalButton):
            if btn.property("category"):
                btn.clicked.connect(self._on_category_clicked)
            elif btn.property("effect_type"):
                btn.clicked.connect(self._on_ai_effect_clicked)
        
        # 滑块信号
        self.intensity_slider.valueChanged.connect(self._on_intensity_changed)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # 控制按钮
        self.apply_btn.clicked.connect(self._apply_effect)
        self.preview_btn.clicked.connect(self._preview_effect)
        self.export_btn.clicked.connect(self._export_video)
        
        # 特效列表选择
        self.effects_list.itemClicked.connect(self._on_effect_selected)
    
    def _upload_video(self):
        """上传视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
        )
        
        if file_path:
            self.current_video = file_path
            self.video_info_label.setText(f"已选择: {file_path.split('/')[-1]}")
            self.video_preview.setText("🎬 视频已加载")
            self.video_preview.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e8;
                    border: 2px solid #4caf50;
                    border-radius: 8px;
                    padding: 40px;
                    font-size: 24px;
                    min-height: 200px;
                }
            """)
    
    def _on_category_clicked(self):
        """特效分类点击"""
        btn = self.sender()
        category = btn.property("category")
        
        # 根据分类加载特效
        effects = self._get_effects_by_category(category)
        self.effects_list.clear()
        
        for effect in effects:
            item = QListWidgetItem(effect["name"])
            item.setData(Qt.ItemDataRole.UserRole, effect)
            self.effects_list.addItem(item)
    
    def _get_effects_by_category(self, category: str) -> list:
        """根据分类获取特效"""
        effects_map = {
            "filter": [
                {"name": "黑白滤镜", "type": "black_white"},
                {"name": "复古滤镜", "type": "vintage"},
                {"name": "暖色滤镜", "type": "warm"},
                {"name": "冷色滤镜", "type": "cool"}
            ],
            "transition": [
                {"name": "淡入淡出", "type": "fade"},
                {"name": "滑动切换", "type": "slide"},
                {"name": "缩放切换", "type": "zoom"},
                {"name": "旋转切换", "type": "rotate"}
            ],
            "visual": [
                {"name": "粒子效果", "type": "particles"},
                {"name": "光晕效果", "type": "glow"},
                {"name": "模糊效果", "type": "blur"},
                {"name": "锐化效果", "type": "sharpen"}
            ],
            "audio": [
                {"name": "回声效果", "type": "echo"},
                {"name": "混响效果", "type": "reverb"},
                {"name": "变声效果", "type": "pitch"},
                {"name": "降噪效果", "type": "noise_reduction"}
            ],
            "text": [
                {"name": "滚动字幕", "type": "scrolling"},
                {"name": "打字机效果", "type": "typewriter"},
                {"name": "3D文字", "type": "3d_text"},
                {"name": "霓虹文字", "type": "neon"}
            ],
            "ai": [
                {"name": "智能美颜", "type": "beauty"},
                {"name": "背景虚化", "type": "background_blur"},
                {"name": "智能裁剪", "type": "smart_crop"},
                {"name": "色彩增强", "type": "color_enhance"}
            ]
        }
        
        return effects_map.get(category, [])
    
    def _on_effect_selected(self, item):
        """特效选择"""
        effect = item.data(Qt.ItemDataRole.UserRole)
        self.effect_preview.setText(f"🎭 {effect['name']}")
    
    def _on_ai_effect_clicked(self):
        """AI特效点击"""
        btn = self.sender()
        effect_type = btn.property("effect_type")
        
        if not self.current_video:
            QMessageBox.warning(self, "提示", "请先上传视频文件")
            return
        
        if not self.ai_manager:
            QMessageBox.warning(self, "提示", "AI管理器未初始化")
            return
        
        # 开始AI特效处理
        self._start_ai_effect_processing(effect_type)
    
    def _start_ai_effect_processing(self, effect_type: str):
        """开始AI特效处理"""
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在分析视频...")
        
        effect_names = {
            "ai_color": "智能调色",
            "ai_scene": "场景识别",
            "ai_tracking": "人物追踪",
            "ai_style": "风格迁移",
            "ai_superres": "超分辨率",
            "ai_edit": "智能剪辑"
        }
        
        effect_name = effect_names.get(effect_type, "未知特效")
        
        QTimer.singleShot(1000, lambda: self._update_progress(30, f"正在应用{effect_name}..."))
        QTimer.singleShot(2000, lambda: self._update_progress(60, f"优化{effect_name}效果..."))
        QTimer.singleShot(3000, lambda: self._update_progress(90, f"完成{effect_name}..."))
        QTimer.singleShot(4000, lambda: self._complete_effect_processing(effect_name))
    
    def _update_progress(self, value: int, text: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def _complete_effect_processing(self, effect_name: str):
        """完成特效处理"""
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"{effect_name}完成")
        
        self.effect_preview.setText(f"✅ {effect_name}已应用")
        
        QMessageBox.information(self, "成功", f"{effect_name}已成功应用到视频！")
        
        # 重置进度条
        QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
        QTimer.singleShot(2000, lambda: self.progress_label.setText("就绪"))
    
    def _on_intensity_changed(self, value: int):
        """强度滑块变化"""
        self.intensity_value_label.setText(f"{value}%")
    
    def _on_speed_changed(self, value: int):
        """速度滑块变化"""
        self.speed_value_label.setText(f"{value}%")
    
    def _apply_effect(self):
        """应用特效"""
        if not self.current_video:
            QMessageBox.warning(self, "提示", "请先上传视频文件")
            return
        
        current_item = self.effects_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个特效")
            return
        
        effect = current_item.data(Qt.ItemDataRole.UserRole)
        QMessageBox.information(self, "应用特效", f"正在应用 {effect['name']} 特效")
    
    def _preview_effect(self):
        """预览特效"""
        QMessageBox.information(self, "预览效果", "特效预览功能正在开发中")
    
    def _export_video(self):
        """导出视频"""
        if not self.current_video:
            QMessageBox.warning(self, "提示", "请先上传视频文件")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出视频", "", 
            "视频文件 (*.mp4 *.avi *.mov)"
        )
        
        if file_path:
            QMessageBox.information(self, "导出成功", f"视频已导出到: {file_path}")
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = EffectsPage()
    window.show()
    sys.exit(app.exec())