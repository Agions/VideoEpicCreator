#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSlider, QCheckBox, QSpinBox, QTabWidget,
    QGroupBox, QScrollArea, QFrame, QSplitter, QGridLayout,
    QTextEdit, QProgressBar, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon

from app.ui.color_grading import ColorGradingPanel
from app.ui.transition_panel import TransitionPanel
from app.ui.mix_style_panel import MixStylePanel
from app.ui.ai_settings_panel import AIModelSettingsPanel

import time
import os

class VideoSegment:
    """视频片段类，存储片段的基本信息"""
    def __init__(self, start=0, end=0, content_type="未分类", confidence=0.0, tags=None):
        self.start_time = start  # 开始时间(秒)
        self.end_time = end      # 结束时间(秒)
        self.content_type = content_type  # 内容类型
        self.confidence = confidence  # 置信度
        self.tags = tags or []   # 标签列表
        self.selected = False    # 是否被选中
    
    @property
    def duration(self):
        """获取片段时长"""
        return self.end_time - self.start_time
    
    def __str__(self):
        """字符串表示"""
        return f"{self.time_str(self.start_time)} - {self.time_str(self.end_time)} ({self.content_type})"
    
    @staticmethod
    def time_str(seconds):
        """将秒转换为时间字符串"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"


class SegmentItem(QWidget):
    """视频片段项UI组件"""
    clicked = pyqtSignal(object)  # 点击信号
    
    def __init__(self, segment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 时间信息
        time_label = QLabel(f"{self.segment.time_str(self.segment.start_time)} - {self.segment.time_str(self.segment.end_time)}")
        time_label.setFixedWidth(180)
        layout.addWidget(time_label)
        
        # 类型信息
        type_label = QLabel(self.segment.content_type)
        type_label.setFixedWidth(80)
        layout.addWidget(type_label)
        
        # 标签信息
        tags_text = ", ".join(self.segment.tags) if self.segment.tags else "无标签"
        tags_label = QLabel(tags_text)
        layout.addWidget(tags_label)
        
        # 置信度
        confidence_label = QLabel(f"{int(self.segment.confidence * 100)}%")
        confidence_label.setFixedWidth(50)
        layout.addWidget(confidence_label)
        
        # 设置选中样式
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        if self.segment.selected:
            self.setStyleSheet("background-color: #e0f0ff; border-radius: 4px;")
        else:
            self.setStyleSheet("")
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.segment.selected = not self.segment.selected
        self.update_style()
        self.clicked.emit(self.segment)
        super().mousePressEvent(event)


class SegmentTimeline(QWidget):
    """片段时间轴可视化组件"""
    segment_selected = pyqtSignal(object)  # 片段选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []
        self.total_duration = 0
        self.selected_segment = None
        self.setMinimumHeight(100)
        self.setMouseTracking(True)
    
    def set_segments(self, segments, total_duration):
        """设置片段列表和总时长"""
        self.segments = segments
        self.total_duration = total_duration
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        if not self.segments or self.total_duration == 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制背景
        painter.fillRect(0, 0, width, height, QColor("#f0f0f0"))
        
        # 绘制片段
        for segment in self.segments:
            start_pos = int(segment.start_time / self.total_duration * width)
            end_pos = int(segment.end_time / self.total_duration * width)
            segment_width = max(end_pos - start_pos, 2)
            
            # 根据内容类型选择颜色
            color = self.get_segment_color(segment.content_type)
            
            # 绘制片段矩形
            if segment.selected:
                # 选中状态
                painter.fillRect(start_pos, 10, segment_width, height - 20, color.lighter(120))
                painter.setPen(QPen(QColor("#0078d7"), 2))
                painter.drawRect(start_pos, 10, segment_width, height - 20)
            else:
                # 正常状态
                painter.fillRect(start_pos, 10, segment_width, height - 20, color)
    
    def get_segment_color(self, content_type):
        """根据内容类型获取颜色"""
        color_map = {
            "人物对话": QColor("#4caf50"),
            "动作场景": QColor("#f44336"),
            "环境镜头": QColor("#2196f3"),
            "过渡镜头": QColor("#ff9800"),
            "特写镜头": QColor("#9c27b0"),
            "未分类": QColor("#9e9e9e")
        }
        return color_map.get(content_type, QColor("#9e9e9e"))
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if not self.segments or self.total_duration == 0:
            return
            
        # 计算点击位置对应的时间
        click_time = (event.position().x() / self.width()) * self.total_duration
        
        # 查找对应的片段
        for segment in self.segments:
            if segment.start_time <= click_time <= segment.end_time:
                # 更新选中状态
                for seg in self.segments:
                    seg.selected = (seg == segment)
                
                self.selected_segment = segment
                self.segment_selected.emit(segment)
                self.update()
                break


class SmartEditPanel(QWidget):
    """智能编辑面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path = ""
        self.video_duration = 0  # 视频总时长(秒)
        self.segments = []  # 视频片段列表
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("智能编辑")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #2c2c2c;
                color: #999;
                padding: 8px 16px;
                border: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #fff;
            }
        """)
        
        # 调色标签页
        self.color_tab = QWidget()
        self._setup_color_tab()
        self.tab_widget.addTab(self.color_tab, "智能调色")
        
        # 转场标签页
        self.transition_tab = QWidget()
        self._setup_transition_tab()
        self.tab_widget.addTab(self.transition_tab, "智能转场")
        
        # 混剪风格标签页
        self.mix_style_tab = QWidget()
        self._setup_mix_style_tab()
        self.tab_widget.addTab(self.mix_style_tab, "混剪风格")
        
        # AI大模型设置标签页
        self.ai_settings_tab = QWidget()
        self._setup_ai_settings_tab()
        self.tab_widget.addTab(self.ai_settings_tab, "AI大模型")
        
        layout.addWidget(self.tab_widget)
        
        # 状态标签
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #999;")
        layout.addWidget(self.status_label)
    
    def _setup_color_tab(self):
        """设置调色标签页"""
        layout = QVBoxLayout(self.color_tab)
        self.color_panel = ColorGradingPanel()
        self.color_panel.color_applied.connect(self._on_color_applied)
        layout.addWidget(self.color_panel)
    
    def _setup_transition_tab(self):
        """设置转场标签页"""
        layout = QVBoxLayout(self.transition_tab)
        self.transition_panel = TransitionPanel()
        self.transition_panel.status_updated.connect(self._on_status_updated)
        layout.addWidget(self.transition_panel)
    
    def _setup_mix_style_tab(self):
        """设置混剪风格标签页"""
        layout = QVBoxLayout(self.mix_style_tab)
        self.mix_style_panel = MixStylePanel()
        self.mix_style_panel.preset_applied.connect(self._on_preset_applied)
        self.mix_style_panel.status_updated.connect(self._on_status_updated)
        layout.addWidget(self.mix_style_panel)
    
    def _setup_ai_settings_tab(self):
        """设置AI大模型设置标签页"""
        layout = QVBoxLayout(self.ai_settings_tab)
        self.ai_settings_panel = AIModelSettingsPanel()
        self.ai_settings_panel.status_updated.connect(self._on_status_updated)
        layout.addWidget(self.ai_settings_panel)
    
    def _on_color_applied(self, color_params):
        """处理调色应用事件"""
        # 更新状态标签
        status_text = f"已应用调色: {color_params.get('color_style', '自定义')}"
        self.status_label.setText(status_text)
        
    def _on_status_updated(self, message):
        """处理状态更新"""
        self.status_label.setText(message)
        
    def _on_preset_applied(self, preset):
        """处理预设应用"""
        # 更新调色面板
        if "color" in preset:
            self.color_panel.apply_preset(preset["color"])
            
        # 更新转场面板
        if "transition" in preset:
            self.transition_panel.apply_preset(preset["transition"])
            
        self.status_label.setText(f"已应用混剪风格预设：{preset['name']}")
    
    # 以下是智能分段功能的方法
    def open_video(self):
        """打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        
        if file_path:
            self.video_path = file_path
            self.status_label.setText(f"已加载视频: {os.path.basename(file_path)}")
            
            # 模拟获取视频时长
            self.video_duration = 300  # 5分钟，实际应该从视频文件获取
            self.duration_label.setText(VideoSegment.time_str(self.video_duration))
            
            # 启用分析按钮
            self.analyze_button.setEnabled(True)
    
    def start_analysis(self):
        """开始分析视频内容"""
        if not self.video_path:
            self.status_label.setText("请先打开视频文件")
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.status_label.setText("正在分析视频内容...")
        
        # 禁用按钮
        self.analyze_button.setEnabled(False)
        self.open_button.setEnabled(False)
        
        # 模拟分析进度
        for i in range(101):
            time.sleep(0.03)  # 模拟处理时间
            self.progress_bar.setValue(i)
            if i % 10 == 0:
                self.status_label.setText(f"正在分析视频内容... {i}%")
        
        # 模拟生成分段结果
        self.generate_demo_segments()
        
        # 更新界面
        self.update_segments_list()
        self.timeline_widget.set_segments(self.segments, self.video_duration)
        self.segments_count_label.setText(str(len(self.segments)))
        
        # 更新状态
        self.status_label.setText(f"分析完成，共找到 {len(self.segments)} 个片段")
        self.progress_bar.setVisible(False)
        
        # 启用按钮
        self.analyze_button.setEnabled(True)
        self.open_button.setEnabled(True)
        self.export_button.setEnabled(True)
    
    def generate_demo_segments(self):
        """生成演示用的分段数据"""
        self.segments = []
        
        # 人物对话片段
        self.segments.append(VideoSegment(0, 25, "人物对话", 0.92, ["介绍", "开场", "问候"]))
        self.segments.append(VideoSegment(60, 85, "人物对话", 0.88, ["交流", "讨论", "核心内容"]))
        self.segments.append(VideoSegment(180, 215, "人物对话", 0.90, ["总结", "结论"]))
        
        # 动作场景片段
        self.segments.append(VideoSegment(25, 40, "动作场景", 0.85, ["快速", "转场"]))
        self.segments.append(VideoSegment(120, 150, "动作场景", 0.80, ["高潮", "紧张"]))
        
        # 环境镜头片段
        self.segments.append(VideoSegment(40, 60, "环境镜头", 0.75, ["环境", "背景"]))
        self.segments.append(VideoSegment(150, 180, "环境镜头", 0.78, ["场景切换"]))
        
        # 过渡镜头片段
        self.segments.append(VideoSegment(85, 95, "过渡镜头", 0.70, ["过渡"]))
        self.segments.append(VideoSegment(215, 225, "过渡镜头", 0.72, ["结尾过渡"]))
        
        # 特写镜头片段
        self.segments.append(VideoSegment(95, 120, "特写镜头", 0.82, ["细节", "强调"]))
        self.segments.append(VideoSegment(225, 240, "特写镜头", 0.84, ["结束特写"]))
        
        # 未分类片段
        self.segments.append(VideoSegment(240, 300, "未分类", 0.50, ["其他内容"]))
    
    def update_segments_list(self):
        """更新片段列表显示"""
        self.segments_list.clear()
        
        for segment in self.segments:
            # 创建自定义项
            item = QListWidgetItem()
            widget = SegmentItem(segment)
            widget.clicked.connect(self.refresh_ui)
            
            # 设置项大小
            item.setSizeHint(widget.sizeHint())
            
            # 添加到列表
            self.segments_list.addItem(item)
            self.segments_list.setItemWidget(item, widget)
    
    def refresh_ui(self):
        """刷新界面"""
        # 更新时间轴
        self.timeline_widget.update()
        
        # 刷新列表项样式
        for i in range(self.segments_list.count()):
            item = self.segments_list.item(i)
            widget = self.segments_list.itemWidget(item)
            if isinstance(widget, SegmentItem):
                widget.update_style()
    
    def on_segment_selected(self, segment):
        """处理片段选中事件"""
        # 更新详情区域
        details = f"""
时间范围: {VideoSegment.time_str(segment.start_time)} - {VideoSegment.time_str(segment.end_time)}
时长: {VideoSegment.time_str(segment.duration)}
内容类型: {segment.content_type}
置信度: {int(segment.confidence * 100)}%
标签: {', '.join(segment.tags) if segment.tags else '无标签'}

建议用途:
- 该片段适合用于{self.get_usage_suggestion(segment)}
- 推荐转场效果: {self.get_transition_suggestion(segment)}
- 配色建议: {self.get_color_suggestion(segment)}
        """
        
        self.details_text.setText(details.strip())
        
        # 刷新列表状态
        self.refresh_ui()
    
    def get_usage_suggestion(self, segment):
        """根据片段类型获取用途建议"""
        suggestions = {
            "人物对话": "展示人物交流、表达观点或情感传递",
            "动作场景": "展示动态内容、吸引观众注意力或增加节奏感",
            "环境镜头": "场景介绍、氛围营造或情境转换",
            "过渡镜头": "连接不同场景、平滑过渡或节奏调整",
            "特写镜头": "强调细节、表达情感或突出关键元素",
            "未分类": "补充内容或自由发挥"
        }
        return suggestions.get(segment.content_type, "多种用途")
    
    def get_transition_suggestion(self, segment):
        """根据片段类型获取转场建议"""
        suggestions = {
            "人物对话": "淡入淡出、叠化",
            "动作场景": "快速切换、滑动、缩放",
            "环境镜头": "慢速淡入淡出、全景扫描",
            "过渡镜头": "擦除、翻转、旋转",
            "特写镜头": "缩放聚焦、径向模糊",
            "未分类": "标准切换"
        }
        return suggestions.get(segment.content_type, "标准切换")
    
    def get_color_suggestion(self, segment):
        """根据片段类型获取配色建议"""
        suggestions = {
            "人物对话": "自然色调、柔和对比",
            "动作场景": "高对比度、饱和度增强",
            "环境镜头": "和谐色彩、色调统一",
            "过渡镜头": "中性色调、渐变过渡",
            "特写镜头": "强调色、焦点色彩突出",
            "未分类": "原始色调"
        }
        return suggestions.get(segment.content_type, "原始色调")
    
    def select_all_segments(self):
        """选择所有片段"""
        for segment in self.segments:
            segment.selected = True
        self.refresh_ui()
    
    def deselect_all_segments(self):
        """取消选择所有片段"""
        for segment in self.segments:
            segment.selected = False
        self.refresh_ui()
    
    def delete_selected_segments(self):
        """删除选中的片段"""
        self.segments = [seg for seg in self.segments if not seg.selected]
        self.update_segments_list()
        self.timeline_widget.set_segments(self.segments, self.video_duration)
        self.segments_count_label.setText(str(len(self.segments)))
        self.details_text.clear()
    
    def export_segments(self):
        """导出分段信息"""
        if not self.segments:
            self.status_label.setText("没有可导出的分段")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分段信息", "", "JSON文件 (*.json);;CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        
        if file_path:
            # 模拟导出
            time.sleep(0.5)
            self.status_label.setText(f"已导出分段信息到: {file_path}") 