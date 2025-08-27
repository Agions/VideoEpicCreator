#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSlider, QCheckBox, QFrame, QGridLayout,
    QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

import time
import os

class ColorGradingPanel(QWidget):
    """智能调色面板"""
    
    color_applied = pyqtSignal(dict)  # 颜色应用信号
    status_updated = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path = ""
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 调色设置区
        color_settings_group = QGroupBox("调色设置")
        color_settings_layout = QGridLayout(color_settings_group)
        
        # 场景类型
        color_settings_layout.addWidget(QLabel("场景类型："), 0, 0)
        self.scene_type_combo = QComboBox()
        self.scene_type_combo.addItems([
            "自动检测", "室内场景", "室外自然", "城市场景", 
            "暗光场景", "明亮场景", "复古风格", "现代风格"
        ])
        color_settings_layout.addWidget(self.scene_type_combo, 0, 1)
        
        # 色彩风格
        color_settings_layout.addWidget(QLabel("色彩风格："), 0, 2)
        self.color_style_combo = QComboBox()
        self.color_style_combo.addItems([
            "电影级色调", "明亮清新", "暖色系", "冷色系",
            "高对比度", "柔和自然", "黑白", "自定义"
        ])
        self.color_style_combo.currentIndexChanged.connect(self._on_color_style_changed)
        color_settings_layout.addWidget(self.color_style_combo, 0, 3)
        
        # 智能匹配
        self.auto_match_check = QCheckBox("智能场景匹配")
        self.auto_match_check.setChecked(True)
        self.auto_match_check.stateChanged.connect(self._on_auto_match_changed)
        color_settings_layout.addWidget(self.auto_match_check, 1, 0, 1, 2)
        
        # 色彩一致性
        self.consistency_check = QCheckBox("保持色彩一致性")
        self.consistency_check.setChecked(True)
        color_settings_layout.addWidget(self.consistency_check, 1, 2, 1, 2)
        
        layout.addWidget(color_settings_group)
        
        # 色彩参数区
        self.color_params_group = QGroupBox("色彩参数")
        color_params_layout = QGridLayout(self.color_params_group)
        
        # 饱和度
        color_params_layout.addWidget(QLabel("饱和度："), 0, 0)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(-100, 100)
        self.saturation_slider.setValue(0)
        self.saturation_slider.valueChanged.connect(self._on_params_changed)
        color_params_layout.addWidget(self.saturation_slider, 0, 1)
        self.saturation_value = QLabel("0")
        color_params_layout.addWidget(self.saturation_value, 0, 2)
        self.saturation_slider.valueChanged.connect(
            lambda v: self.saturation_value.setText(str(v))
        )
        
        # 对比度
        color_params_layout.addWidget(QLabel("对比度："), 1, 0)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(self._on_params_changed)
        color_params_layout.addWidget(self.contrast_slider, 1, 1)
        self.contrast_value = QLabel("0")
        color_params_layout.addWidget(self.contrast_value, 1, 2)
        self.contrast_slider.valueChanged.connect(
            lambda v: self.contrast_value.setText(str(v))
        )
        
        # 亮度
        color_params_layout.addWidget(QLabel("亮度："), 2, 0)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self._on_params_changed)
        color_params_layout.addWidget(self.brightness_slider, 2, 1)
        self.brightness_value = QLabel("0")
        color_params_layout.addWidget(self.brightness_value, 2, 2)
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_value.setText(str(v))
        )
        
        # 色温
        color_params_layout.addWidget(QLabel("色温："), 3, 0)
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(-100, 100)
        self.temperature_slider.setValue(0)
        self.temperature_slider.valueChanged.connect(self._on_params_changed)
        color_params_layout.addWidget(self.temperature_slider, 3, 1)
        self.temperature_value = QLabel("0")
        color_params_layout.addWidget(self.temperature_value, 3, 2)
        self.temperature_slider.valueChanged.connect(
            lambda v: self.temperature_value.setText(str(v))
        )
        
        # 色调
        color_params_layout.addWidget(QLabel("色调："), 4, 0)
        self.tint_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_slider.setRange(-100, 100)
        self.tint_slider.setValue(0)
        self.tint_slider.valueChanged.connect(self._on_params_changed)
        color_params_layout.addWidget(self.tint_slider, 4, 1)
        self.tint_value = QLabel("0")
        color_params_layout.addWidget(self.tint_value, 4, 2)
        self.tint_slider.valueChanged.connect(
            lambda v: self.tint_value.setText(str(v))
        )
        
        layout.addWidget(self.color_params_group)
        
        # 预设选项
        presets_group = QGroupBox("预设方案")
        presets_layout = QHBoxLayout(presets_group)
        
        presets = [
            "电影暖色", "清新自然", "高级灰", "冷色科技",
            "复古胶片", "黑白经典", "明亮鲜艳", "暗调神秘"
        ]
        
        for preset in presets:
            preset_button = QPushButton(preset)
            preset_button.clicked.connect(lambda _, p=preset: self._apply_preset(p))
            presets_layout.addWidget(preset_button)
        
        layout.addWidget(presets_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.load_video_button = QPushButton("加载视频")
        self.load_video_button.clicked.connect(self._load_video)
        button_layout.addWidget(self.load_video_button)
        
        self.analyze_button = QPushButton("分析场景")
        self.analyze_button.clicked.connect(self._analyze_scene)
        button_layout.addWidget(self.analyze_button)
        
        self.apply_button = QPushButton("应用调色")
        self.apply_button.clicked.connect(self._apply_color_grading)
        button_layout.addWidget(self.apply_button)
        
        self.save_preset_button = QPushButton("保存预设")
        self.save_preset_button.clicked.connect(self._save_preset)
        button_layout.addWidget(self.save_preset_button)
        
        layout.addLayout(button_layout)
        
        # 预览区域
        preview_group = QGroupBox("调色预览")
        preview_layout = QHBoxLayout(preview_group)
        
        # 原始预览
        original_layout = QVBoxLayout()
        original_layout.addWidget(QLabel("原始画面"))
        
        self.original_frame = QFrame()
        self.original_frame.setMinimumSize(320, 180)
        self.original_frame.setFrameShape(QFrame.Shape.Box)
        self.original_frame.setStyleSheet("background-color: #000;")
        original_layout.addWidget(self.original_frame)
        
        preview_layout.addLayout(original_layout)
        
        # 调色后预览
        graded_layout = QVBoxLayout()
        graded_layout.addWidget(QLabel("调色后"))
        
        self.graded_frame = QFrame()
        self.graded_frame.setMinimumSize(320, 180)
        self.graded_frame.setFrameShape(QFrame.Shape.Box)
        self.graded_frame.setStyleSheet("background-color: #000;")
        graded_layout.addWidget(self.graded_frame)
        
        preview_layout.addLayout(graded_layout)
        
        layout.addWidget(preview_group)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # 默认禁用参数调整
        self._on_auto_match_changed()
    
    def _on_color_style_changed(self, index):
        """颜色风格变更处理"""
        if self.color_style_combo.currentText() == "自定义":
            self.color_params_group.setEnabled(True)
        else:
            # 应用预设值
            style = self.color_style_combo.currentText()
            if style == "电影级色调":
                self._set_color_params(10, 20, -5, -15, 0)
            elif style == "明亮清新":
                self._set_color_params(20, 10, 15, 5, -5)
            elif style == "暖色系":
                self._set_color_params(15, 5, 5, 30, -10)
            elif style == "冷色系":
                self._set_color_params(5, 10, 0, -30, 5)
            elif style == "高对比度":
                self._set_color_params(25, 50, 0, 0, 0)
            elif style == "柔和自然":
                self._set_color_params(0, -10, 5, 0, 0)
            elif style == "黑白":
                self._set_color_params(-100, 30, 0, 0, 0)
    
    def _set_color_params(self, sat, con, bri, temp, tint):
        """设置色彩参数"""
        self.saturation_slider.setValue(sat)
        self.contrast_slider.setValue(con)
        self.brightness_slider.setValue(bri)
        self.temperature_slider.setValue(temp)
        self.tint_slider.setValue(tint)
    
    def _on_auto_match_changed(self):
        """自动匹配状态变更处理"""
        is_auto = self.auto_match_check.isChecked()
        self.color_params_group.setEnabled(not is_auto)
        self.color_style_combo.setEnabled(not is_auto)
    
    def _on_params_changed(self):
        """参数变更时更新预览"""
        self._update_preview()
    
    def _apply_preset(self, preset):
        """应用预设"""
        if preset == "电影暖色":
            self._set_color_params(20, 30, -5, 30, -5)
        elif preset == "清新自然":
            self._set_color_params(10, 0, 10, 0, 0)
        elif preset == "高级灰":
            self._set_color_params(-20, 10, 0, 0, 0)
        elif preset == "冷色科技":
            self._set_color_params(5, 15, 0, -30, 5)
        elif preset == "复古胶片":
            self._set_color_params(-10, 20, -5, 15, -5)
        elif preset == "黑白经典":
            self._set_color_params(-100, 40, 0, 0, 0)
        elif preset == "明亮鲜艳":
            self._set_color_params(40, 20, 15, 10, 0)
        elif preset == "暗调神秘":
            self._set_color_params(5, 40, -20, -10, 0)
        
        # 更新预览
        self._update_preview()
        
        # 更新状态
        status_text = f"已应用'{preset}'预设"
        self.status_label.setText(status_text)
        self.status_updated.emit(status_text)
    
    def _load_video(self):
        """加载视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        
        if file_path:
            self.video_path = file_path
            self.status_label.setText(f"已加载视频: {os.path.basename(file_path)}")
            
            # 更新原始预览
            # 这里应该从视频中提取帧，作为示例使用纯色背景
            self.original_frame.setStyleSheet("background-color: #345; border: 1px solid #888;")
            
            # 启用分析按钮
            self.analyze_button.setEnabled(True)
    
    def _analyze_scene(self):
        """分析场景颜色"""
        if not self.video_path:
            self.status_label.setText("请先加载视频文件")
            return
        
        self.status_label.setText("正在分析场景颜色...")
        
        # 模拟分析过程
        for i in range(101):
            time.sleep(0.01)  # 模拟处理时间
            if i % 20 == 0:
                self.status_label.setText(f"正在分析场景颜色... {i}%")
        
        # 模拟分析结果
        scene_type = self.scene_type_combo.currentText()
        if scene_type == "自动检测":
            # 随机选择一个场景类型
            import random
            scene_types = ["室内场景", "室外自然", "城市场景", "暗光场景", "明亮场景"]
            detected_type = random.choice(scene_types)
            self.scene_type_combo.setCurrentText(detected_type)
            self.status_label.setText(f"检测到场景类型: {detected_type}")
        
        # 根据场景类型推荐调色方案
        if self.auto_match_check.isChecked():
            self._recommend_color_style()
        
        # 更新预览
        self._update_preview()
        
        # 启用应用按钮
        self.apply_button.setEnabled(True)
    
    def _recommend_color_style(self):
        """根据场景类型推荐调色方案"""
        scene_type = self.scene_type_combo.currentText()
        
        # 场景类型与推荐调色的映射
        recommendations = {
            "室内场景": "柔和自然",
            "室外自然": "明亮清新",
            "城市场景": "高对比度",
            "暗光场景": "电影级色调",
            "明亮场景": "暖色系",
            "复古风格": "复古胶片",
            "现代风格": "冷色系"
        }
        
        recommended_style = recommendations.get(scene_type, "电影级色调")
        self.color_style_combo.setCurrentText(recommended_style)
        self.status_label.setText(f"已推荐'{recommended_style}'调色方案")
    
    def _update_preview(self):
        """更新预览效果"""
        # 在实际应用中，这里应该应用颜色调整到预览帧上
        # 这里使用不同的背景色来模拟效果
        
        # 获取当前参数
        sat = self.saturation_slider.value()
        con = self.contrast_slider.value()
        bri = self.brightness_slider.value()
        temp = self.temperature_slider.value()
        tint = self.tint_slider.value()
        
        # 根据参数计算模拟颜色
        r = min(255, max(0, 50 + bri // 2 + temp // 2))
        g = min(255, max(0, 70 + bri // 2 - abs(temp) // 4 + tint // 4))
        b = min(255, max(0, 80 + bri // 2 - temp // 2))
        
        # 调整饱和度(简化模拟)
        avg = (r + g + b) // 3
        if sat < 0:
            # 降低饱和度(向灰色靠近)
            factor = 1 + sat / 100
            r = int(avg + (r - avg) * factor)
            g = int(avg + (g - avg) * factor)
            b = int(avg + (b - avg) * factor)
        else:
            # 提高饱和度(远离灰色)
            factor = 1 + sat / 100 * 0.5  # 限制最大效果
            r = min(255, max(0, int(avg + (r - avg) * factor)))
            g = min(255, max(0, int(avg + (g - avg) * factor)))
            b = min(255, max(0, int(avg + (b - avg) * factor)))
        
        # 调整对比度(简化模拟)
        if con > 0:
            factor = 1 + con / 100
            r = min(255, max(0, int(avg + (r - avg) * factor)))
            g = min(255, max(0, int(avg + (g - avg) * factor)))
            b = min(255, max(0, int(avg + (b - avg) * factor)))
        else:
            factor = 1 + con / 100
            r = min(255, max(0, int(avg + (r - avg) * factor)))
            g = min(255, max(0, int(avg + (g - avg) * factor)))
            b = min(255, max(0, int(avg + (b - avg) * factor)))
        
        # 应用到预览
        style = f"background-color: rgb({r},{g},{b}); border: 1px solid #888;"
        self.graded_frame.setStyleSheet(style)
    
    def _apply_color_grading(self):
        """应用调色效果"""
        self.status_label.setText("正在应用调色效果...")
        
        # 模拟处理过程
        for i in range(101):
            time.sleep(0.01)  # 模拟处理时间
            if i % 20 == 0:
                self.status_label.setText(f"正在应用调色效果... {i}%")
        
        # 获取当前参数
        color_params = {
            "saturation": self.saturation_slider.value(),
            "contrast": self.contrast_slider.value(),
            "brightness": self.brightness_slider.value(),
            "temperature": self.temperature_slider.value(),
            "tint": self.tint_slider.value(),
            "scene_type": self.scene_type_combo.currentText(),
            "color_style": self.color_style_combo.currentText(),
            "consistency": self.consistency_check.isChecked()
        }
        
        # 发出信号
        self.color_applied.emit(color_params)
        
        self.status_label.setText("调色效果已应用")
    
    def _save_preset(self):
        """保存当前调色预设"""
        preset_name, ok = QFileDialog.getSaveFileName(
            self, "保存调色预设", "", "调色预设文件 (*.lut)"
        )
        
        if ok and preset_name:
            # 获取当前参数
            preset_data = {
                "saturation": self.saturation_slider.value(),
                "contrast": self.contrast_slider.value(),
                "brightness": self.brightness_slider.value(),
                "temperature": self.temperature_slider.value(),
                "tint": self.tint_slider.value(),
                "name": os.path.basename(preset_name).split('.')[0]
            }
            
            # 模拟保存预设
            time.sleep(0.5)
            self.status_label.setText(f"预设已保存: {preset_name}")
    
    def get_color_params(self):
        """获取当前色彩参数"""
        return {
            "saturation": self.saturation_slider.value(),
            "contrast": self.contrast_slider.value(),
            "brightness": self.brightness_slider.value(),
            "temperature": self.temperature_slider.value(),
            "tint": self.tint_slider.value(),
            "scene_type": self.scene_type_combo.currentText(),
            "color_style": self.color_style_combo.currentText()
        }
    
    def load_color_params(self, params):
        """加载色彩参数"""
        self.saturation_slider.setValue(params.get("saturation", 0))
        self.contrast_slider.setValue(params.get("contrast", 0))
        self.brightness_slider.setValue(params.get("brightness", 0))
        self.temperature_slider.setValue(params.get("temperature", 0))
        self.tint_slider.setValue(params.get("tint", 0))
        
        if "scene_type" in params:
            self.scene_type_combo.setCurrentText(params["scene_type"])
        
        if "color_style" in params:
            self.color_style_combo.setCurrentText(params["color_style"])
        
        self._update_preview() 