#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QGridLayout, QGroupBox, QFileDialog,
    QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QCheckBox,
    QScrollArea, QTextEdit, QTabWidget, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont

import os
import json
import time
import random
import uuid

class MixStylePresetItem(QWidget):
    """混剪风格预设项组件"""
    
    selected = pyqtSignal(str)  # 传递预设ID
    
    def __init__(self, preset_id, name, description, thumbnail_color, parent=None):
        super().__init__(parent)
        self.preset_id = preset_id
        self.name = name
        self.description = description
        self.thumbnail_color = thumbnail_color
        self.is_selected = False
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 缩略图
        thumbnail = QFrame()
        thumbnail.setMinimumSize(120, 80)
        thumbnail.setMaximumSize(120, 80)
        thumbnail.setFrameShape(QFrame.Shape.Box)
        thumbnail.setStyleSheet(f"background-color: {self.thumbnail_color};")
        layout.addWidget(thumbnail)
        
        # 预设名称
        name_label = QLabel(self.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        # 预设描述
        description_label = QLabel(self.description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #777777; font-size: 11px;")
        description_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(description_label)
        
        # 设置最小尺寸
        self.setMinimumSize(140, 170)
        self.setMaximumSize(140, 170)
        
        # 更新样式
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        if self.is_selected:
            self.setStyleSheet("background-color: #D6E8FA; border: 1px solid #0078D7; border-radius: 5px;")
        else:
            self.setStyleSheet("background-color: #F2F2F2; border: 1px solid #D9D9D9; border-radius: 5px;")
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.is_selected = True
        self.update_style()
        self.selected.emit(self.preset_id)
        super().mousePressEvent(event)


class NewPresetDialog(QDialog):
    """新建预设对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建混剪风格预设")
        self.resize(400, 500)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 基本信息区域
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("预设名称")
        info_layout.addRow("名称:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("描述预设的风格特点和使用场景")
        self.description_edit.setMaximumHeight(80)
        info_layout.addRow("描述:", self.description_edit)
        
        layout.addWidget(info_group)
        
        # 选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 分段设置
        segment_tab = QWidget()
        segment_layout = QFormLayout(segment_tab)
        
        self.segment_threshold = QSpinBox()
        self.segment_threshold.setRange(1, 10)
        self.segment_threshold.setValue(5)
        segment_layout.addRow("分段灵敏度:", self.segment_threshold)
        
        self.segment_types = QListWidget()
        self.segment_types.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.segment_types.addItems(["人物对话", "动作场景", "环境镜头", "过渡镜头", "特写镜头"])
        for i in range(self.segment_types.count()):
            self.segment_types.item(i).setSelected(True)
        self.segment_types.setMaximumHeight(100)
        segment_layout.addRow("保留片段类型:", self.segment_types)
        
        self.ai_optimize = QCheckBox("使用AI优化分段结果")
        self.ai_optimize.setChecked(True)
        segment_layout.addRow("", self.ai_optimize)
        
        tabs.addTab(segment_tab, "分段设置")
        
        # 调色设置
        color_tab = QWidget()
        color_layout = QFormLayout(color_tab)
        
        self.color_style = QComboBox()
        self.color_style.addItems(["自动检测", "电影级色调", "明亮清新", "复古风格", "黑白经典", "高对比度"])
        color_layout.addRow("色彩风格:", self.color_style)
        
        self.saturation = QSlider(Qt.Orientation.Horizontal)
        self.saturation.setRange(-100, 100)
        self.saturation.setValue(0)
        color_layout.addRow("饱和度:", self.saturation)
        
        self.contrast = QSlider(Qt.Orientation.Horizontal)
        self.contrast.setRange(-100, 100)
        self.contrast.setValue(0)
        color_layout.addRow("对比度:", self.contrast)
        
        tabs.addTab(color_tab, "调色设置")
        
        # 转场设置
        transition_tab = QWidget()
        transition_layout = QFormLayout(transition_tab)
        
        self.transition_style = QComboBox()
        self.transition_style.addItems(["标准", "快节奏", "平滑", "创意", "混合"])
        transition_layout.addRow("转场风格:", self.transition_style)
        
        self.transition_types = QListWidget()
        self.transition_types.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        transition_types = ["淡入淡出", "左擦除", "右擦除", "缩放进入", "缩放退出", "旋转", "模糊", "闪白"]
        self.transition_types.addItems(transition_types)
        for i in range(self.transition_types.count()):
            self.transition_types.item(i).setSelected(True)
        self.transition_types.setMaximumHeight(100)
        transition_layout.addRow("使用转场类型:", self.transition_types)
        
        self.transition_duration = QSpinBox()
        self.transition_duration.setRange(5, 60)
        self.transition_duration.setValue(15)
        transition_layout.addRow("转场时长(帧):", self.transition_duration)
        
        tabs.addTab(transition_tab, "转场设置")
        
        # 节奏设置
        rhythm_tab = QWidget()
        rhythm_layout = QFormLayout(rhythm_tab)
        
        self.rhythm_mode = QComboBox()
        self.rhythm_mode.addItems(["节拍检测", "节奏感知", "语音停顿", "混合模式"])
        rhythm_layout.addRow("分析模式:", self.rhythm_mode)
        
        self.rhythm_sensitivity = QSpinBox()
        self.rhythm_sensitivity.setRange(1, 10)
        self.rhythm_sensitivity.setValue(5)
        rhythm_layout.addRow("灵敏度:", self.rhythm_sensitivity)
        
        self.min_interval = QSpinBox()
        self.min_interval.setRange(1, 10)
        self.min_interval.setValue(2)
        rhythm_layout.addRow("最小间隔(秒):", self.min_interval)
        
        tabs.addTab(rhythm_tab, "节奏设置")
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_settings(self):
        """获取设置数据"""
        segment_types = []
        for i in range(self.segment_types.count()):
            if self.segment_types.item(i).isSelected():
                segment_types.append(self.segment_types.item(i).text())
        
        transition_types = []
        for i in range(self.transition_types.count()):
            if self.transition_types.item(i).isSelected():
                transition_types.append(self.transition_types.item(i).text())
        
        settings = {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "segment": {
                "threshold": self.segment_threshold.value(),
                "types": segment_types,
                "ai_optimize": self.ai_optimize.isChecked()
            },
            "color": {
                "style": self.color_style.currentText(),
                "saturation": self.saturation.value(),
                "contrast": self.contrast.value()
            },
            "transition": {
                "style": self.transition_style.currentText(),
                "types": transition_types,
                "duration": self.transition_duration.value()
            },
            "rhythm": {
                "mode": self.rhythm_mode.currentText(),
                "sensitivity": self.rhythm_sensitivity.value(),
                "min_interval": self.min_interval.value()
            }
        }
        
        return settings


class MixStylePanel(QWidget):
    """自定义混剪风格面板"""
    
    apply_style = pyqtSignal(dict)  # 应用风格信号
    preset_applied = pyqtSignal(dict)  # 应用预设信号
    status_updated = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presets = {}  # 预设数据
        self.current_preset_id = None  # 当前选中的预设ID
        self.preset_items = {}  # 预设UI项
        
        # 随机色彩列表，用于预设缩略图
        self.colors = [
            "#4285F4", "#EA4335", "#FBBC05", "#34A853",  # Google colors
            "#007BFF", "#6610F2", "#6F42C1", "#E83E8C",  # Bootstrap colors
            "#FF6B6B", "#4ECDC4", "#556270", "#C7F464",  # Flat UI
            "#264653", "#2A9D8F", "#E9C46A", "#F4A261"   # Earth tones
        ]
        
        self.presets_file = os.path.join(os.path.dirname(__file__), "mix_style_presets.json")
        
        self.init_ui()
        self._load_presets()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 顶部区域 - 预设管理
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel("自定义混剪风格:"))
        
        # 新建按钮
        self.new_button = QPushButton("新建预设")
        self.new_button.clicked.connect(self._on_create_preset)
        top_layout.addWidget(self.new_button)
        
        # 删除按钮
        self.delete_button = QPushButton("删除预设")
        self.delete_button.clicked.connect(self._on_delete_preset)
        self.delete_button.setEnabled(False)
        top_layout.addWidget(self.delete_button)
        
        # 导入/导出按钮
        self.import_button = QPushButton("导入预设")
        self.import_button.clicked.connect(self._on_import_preset)
        top_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("导出预设")
        self.export_button.clicked.connect(self._on_export_preset)
        self.export_button.setEnabled(False)
        top_layout.addWidget(self.export_button)
        
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # 中间区域 - 预设列表
        presets_group = QGroupBox("可用混剪风格预设")
        presets_layout = QVBoxLayout(presets_group)
        
        # 滚动区域
        self.presets_scroll = QScrollArea()
        self.presets_scroll.setWidgetResizable(True)
        self.presets_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.presets_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建预设容器
        self.presets_container = QWidget()
        self.presets_layout = QHBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(10)
        self.presets_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.presets_scroll.setWidget(self.presets_container)
        presets_layout.addWidget(self.presets_scroll)
        
        # 无预设时的提示
        self.no_presets_label = QLabel('暂无自定义预设，点击"新建预设"创建您的第一个混剪风格。')
        self.no_presets_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_presets_label.setStyleSheet("color: #777777; padding: 20px;")
        presets_layout.addWidget(self.no_presets_label)
        
        layout.addWidget(presets_group)
        
        # 下部区域 - 预设详情
        self.details_group = QGroupBox("预设详情")
        details_layout = QVBoxLayout(self.details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        # 应用按钮
        self.apply_button = QPushButton("应用混剪风格")
        self.apply_button.clicked.connect(self._on_apply_preset)
        self.apply_button.setEnabled(False)
        details_layout.addWidget(self.apply_button)
        
        layout.addWidget(self.details_group)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
    
    def _load_presets(self):
        """从本地存储加载预设"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    self.presets = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载预设时出错：{str(e)}")
            self.presets = {}
        
        # 更新UI
        self.update_presets_ui()
    
    def update_presets_ui(self):
        """更新预设列表UI"""
        # 清空现有项
        while self.presets_layout.count():
            item = self.presets_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 更新空状态显示
        if not self.presets:
            self.no_presets_label.show()
            self.presets_scroll.setVisible(False)
            self.delete_button.setEnabled(False)
            self.export_button.setEnabled(False)
        else:
            self.no_presets_label.hide()
            self.presets_scroll.setVisible(True)
            self.delete_button.setEnabled(True)
            self.export_button.setEnabled(True)
        
        # 添加预设项
        for preset_id, preset in self.presets.items():
            item = MixStylePresetItem(
                preset_id, 
                preset["name"], 
                preset["description"], 
                preset.get("color", random.choice(self.colors))
            )
            item.selected.connect(self._on_preset_selected)
            self.presets_layout.addWidget(item)
            self.preset_items[preset_id] = item
        
        # 添加弹性空间
        self.presets_layout.addStretch()
    
    def _on_preset_selected(self, preset_id):
        """处理预设选中事件"""
        # 更新其他预设的选中状态
        for pid, item in self.preset_items.items():
            if pid != preset_id:
                item.is_selected = False
                item.update_style()
        
        self.current_preset_id = preset_id
        preset = self.presets[preset_id]
        
        # 更新按钮状态
        self.delete_button.setEnabled(not preset_id.startswith("builtin_"))
        self.export_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        
        # 更新预设详情
        details = f"""
<h3>{preset['name']}</h3>
<p>{preset['description']}</p>

<h4>分段设置</h4>
<ul>
  <li>分段灵敏度: {preset['segment']['threshold']}</li>
  <li>保留片段类型: {', '.join(preset['segment']['types'])}</li>
  <li>AI优化: {'是' if preset['segment']['ai_optimize'] else '否'}</li>
</ul>

<h4>调色设置</h4>
<ul>
  <li>色彩风格: {preset['color']['style']}</li>
  <li>饱和度调整: {preset['color']['saturation']}</li>
  <li>对比度调整: {preset['color']['contrast']}</li>
</ul>

<h4>转场设置</h4>
<ul>
  <li>转场风格: {preset['transition']['style']}</li>
  <li>转场类型: {', '.join(preset['transition']['types'])}</li>
  <li>转场时长: {preset['transition']['duration']}帧</li>
</ul>

<h4>节奏设置</h4>
<ul>
  <li>分析模式: {preset['rhythm']['mode']}</li>
  <li>灵敏度: {preset['rhythm']['sensitivity']}</li>
  <li>最小间隔: {preset['rhythm']['min_interval']}秒</li>
</ul>
        """
        
        self.details_text.setHtml(details)
        
        # 更新状态
        self.status_label.setText(f"已选择混剪风格: {preset['name']}")
    
    def _on_create_preset(self):
        """创建新预设"""
        dialog = NewPresetDialog(self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            
            # 检查名称是否为空
            if not settings["name"]:
                QMessageBox.warning(self, "创建失败", "预设名称不能为空")
                return
            
            # 生成唯一ID
            preset_id = f"custom_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # 随机选择一个颜色
            color = random.choice(self.colors)
            
            # 创建预设
            preset = settings.copy()
            preset["id"] = preset_id
            preset["color"] = color
            
            # 保存预设
            self.presets[preset_id] = preset
            
            # 更新UI
            self.update_presets_ui()
            
            # 自动选中新创建的预设
            if preset_id in self.preset_items:
                self.preset_items[preset_id].is_selected = True
                self.preset_items[preset_id].update_style()
                self._on_preset_selected(preset_id)
            
            # 保存到文件
            self._save_presets()
            
            self.status_label.setText(f"已创建混剪风格预设: {preset['name']}")
    
    def _on_delete_preset(self):
        """删除预设"""
        if not self.current_preset_id:
            return
        
        # 内置预设不允许删除
        if self.current_preset_id.startswith("builtin_"):
            QMessageBox.warning(self, "删除失败", "内置预设不允许删除")
            return
        
        preset = self.presets.get(self.current_preset_id)
        if not preset:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", 
            f'确定要删除预设 "{preset["name"]}" 吗？此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除预设
            del self.presets[self.current_preset_id]
            
            # 更新UI
            self.current_preset_id = None
            self.update_presets_ui()
            
            # 清空详情
            self.details_text.clear()
            
            # 禁用按钮
            self.delete_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            
            # 更新状态
            self.status_label.setText("已删除预设")
            
            # 保存到文件
            self._save_presets()
    
    def _on_import_preset(self):
        """导入预设"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入混剪风格预设", "", "JSON文件 (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_presets = json.load(f)
            
            # 检查格式是否正确
            if not isinstance(imported_presets, dict):
                raise ValueError("导入的文件格式不正确")
            
            # 导入预设
            imported_count = 0
            for preset_id, preset in imported_presets.items():
                # 跳过内置预设
                if preset_id.startswith("builtin_"):
                    continue
                
                # 检查基本字段
                required_fields = ["name", "description", "segment", "color", "transition", "rhythm"]
                if not all(field in preset for field in required_fields):
                    continue
                
                # 生成新ID避免冲突
                new_id = f"custom_{int(time.time())}_{random.randint(1000, 9999)}"
                preset["id"] = new_id
                
                # 保存预设
                self.presets[new_id] = preset
                imported_count += 1
            
            # 更新UI
            self.update_presets_ui()
            
            # 更新状态
            self.status_label.setText(f"已导入 {imported_count} 个混剪风格预设")
            
            # 保存到文件
            self._save_presets()
            
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入预设失败: {str(e)}")
    
    def _on_export_preset(self):
        """导出预设"""
        if not self.current_preset_id:
            return
        
        preset = self.presets.get(self.current_preset_id)
        if not preset:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出混剪风格预设", f"{preset['name']}.json", "JSON文件 (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # 导出单个预设
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({self.current_preset_id: preset}, f, ensure_ascii=False, indent=2)
            
            self.status_label.setText(f"已导出混剪风格预设: {preset['name']}")
            
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出预设失败: {str(e)}")
    
    def _on_apply_preset(self):
        """应用预设"""
        if not self.current_preset_id:
            return
        
        preset = self.presets.get(self.current_preset_id)
        if not preset:
            return
        
        # 确认应用
        reply = QMessageBox.question(
            self, "确认应用", 
            f'即将应用混剪风格 "{preset["name"]}"，这将覆盖当前的分段、调色和转场设置。是否继续？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 发送应用信号
            self.apply_style.emit(preset)
            
            # 更新状态
            self.status_label.setText(f"已应用混剪风格: {preset['name']}")
            
            # 弹出提示
            QMessageBox.information(self, "应用成功", f'已成功应用混剪风格 "{preset["name"]}"。请切换到相应选项卡查看效果。')
    
    def _save_presets(self):
        """保存预设到本地存储"""
        try:
            with open(self.presets_file, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存预设时出错：{str(e)}")
    
    def get_current_preset(self):
        """获取当前选中的预设"""
        if not self.current_preset_id:
            return None
        
        return self.presets.get(self.current_preset_id) 