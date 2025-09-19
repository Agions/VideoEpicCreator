#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据分析页面 - 提供AI驱动的数据分析和洞察功能
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QSplitter, QStackedWidget,
    QGroupBox, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QDialog, QDialogButtonBox, QFormLayout, QDateEdit,
    QTimeEdit, QCalendarWidget, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QDate, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush

# Optional QtCharts import for data visualization
try:
    from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
    QTCHARTS_AVAILABLE = True
except ImportError:
    QTCHARTS_AVAILABLE = False
    # Create placeholder classes that accept any method call
    class _Placeholder:
        def __init__(self, *args, **kwargs): pass
        def __getattr__(self, name): 
            return lambda *args, **kwargs: self
        def __call__(self, *args, **kwargs): 
            return self
    
    class ChartTheme:
        Light = 0
        Dark = 1
    class AnimationOption:
        SeriesAnimations = 0
        GridAxisAnimations = 1
    class QChart(_Placeholder):
        AnimationOption = AnimationOption
    class QPainter:
        class RenderHint:
            Antialiasing = 0
    class QChartView(QWidget):
        def __init__(self, chart=None):
            QWidget.__init__(self)
        
        def __getattr__(self, name):
            return lambda *args, **kwargs: self
    class QLineSeries(_Placeholder):
        pass
    class QBarSeries(_Placeholder):
        pass
    class QBarSet(_Placeholder):
        pass
    class QValueAxis(_Placeholder):
        pass
    class QBarCategoryAxis(_Placeholder):
        pass

from app.ui.professional_ui_system import ProfessionalCard, ProfessionalButton
from app.ui.components.loading_component import LoadingOverlay
from app.ui.components.error_handler import ToastManager, MessageType
import random


class AnalyticsPage(QWidget):
    """数据分析页面"""
    
    # 信号定义
    analysis_completed = pyqtSignal(dict)          # 分析完成信号
    report_generated = pyqtSignal(str)            # 报告生成信号
    data_exported = pyqtSignal(str)               # 数据导出信号
    insights_discovered = pyqtSignal(list)        # 洞察发现信号
    
    def __init__(self, ai_manager=None, project_manager=None, backup_manager=None, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.project_manager = project_manager
        self.backup_manager = backup_manager
        self.is_dark_theme = False
        
        # 分析数据
        self.analysis_data = {}
        self.current_analysis_type = "overview"
        self.current_time_range = "7days"
        self.real_time_mode = True
        
        # 组件初始化
        self.loading_overlay = LoadingOverlay(self)
        self.error_handler = ToastManager(self)
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        self._init_sample_data()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 页面标题区域
        header_layout = QHBoxLayout()
        
        title_label = QLabel("数据分析中心")
        title_label.setProperty("class", "page-title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setProperty("class", "tool-btn")
        self.refresh_btn.clicked.connect(self._refresh_data)
        header_layout.addWidget(self.refresh_btn)
        
        # 开始分析按钮
        self.start_analysis_btn = QPushButton("🚀 开始分析")
        self.start_analysis_btn.setProperty("class", "primary-btn")
        header_layout.addWidget(self.start_analysis_btn)
        
        # 导出按钮
        self.export_pdf_btn = QPushButton("📄 导出PDF")
        self.export_pdf_btn.setProperty("class", "tool-btn")
        header_layout.addWidget(self.export_pdf_btn)
        
        self.export_excel_btn = QPushButton("📊 导出Excel")
        self.export_excel_btn.setProperty("class", "tool-btn")
        header_layout.addWidget(self.export_excel_btn)
        
        # 分享按钮
        self.share_report_btn = QPushButton("🔗 分享报告")
        self.share_report_btn.setProperty("class", "tool-btn")
        header_layout.addWidget(self.share_report_btn)
        
        layout.addLayout(header_layout)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("class", "analytics-tabs")
        
        # 综合分析标签页
        self.overview_tab = self._create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "📊 综合分析")
        
        # 项目统计标签页
        self.projects_tab = self._create_projects_tab()
        self.tab_widget.addTab(self.projects_tab, "📁 项目统计")
        
        # 性能分析标签页
        self.performance_tab = self._create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "⚡ 性能分析")
        
        # AI洞察标签页
        self.ai_insights_tab = self._create_ai_insights_tab()
        self.tab_widget.addTab(self.ai_insights_tab, "🤖 AI洞察")
        
        # 用户行为标签页
        self.user_behavior_tab = self._create_user_behavior_tab()
        self.tab_widget.addTab(self.user_behavior_tab, "👥 用户行为")
        
        layout.addWidget(self.tab_widget)
        
        # 连接标签切换信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # 添加加载遮罩
        self.loading_overlay.hide()
    
    def _create_overview_tab(self) -> QWidget:
        """创建综合分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 关键指标卡片
        metrics_card = ProfessionalCard()
        metrics_layout = QGridLayout()
        metrics_content = QWidget()
        metrics_content.setLayout(metrics_layout)
        metrics_card.add_content(metrics_content)
        
        # 生成关键指标
        self.metrics_widgets = {}
        metrics_data = self._generate_metrics_data()
        
        for i, (key, data) in enumerate(metrics_data.items()):
            metric_widget = self._create_metric_widget(data)
            metrics_layout.addWidget(metric_widget, i // 4, i % 4)
            self.metrics_widgets[key] = metric_widget
        
        layout.addWidget(metrics_card)
        
        # 图表区域
        charts_layout = QHBoxLayout()
        
        # 趋势图表
        self.trend_chart = self._create_trend_chart()
        charts_layout.addWidget(self.trend_chart, 2)
        
        # 分布图表
        self.distribution_chart = self._create_distribution_chart()
        charts_layout.addWidget(self.distribution_chart, 1)
        
        layout.addLayout(charts_layout)
        
        # AI洞察区域
        insights_card = ProfessionalCard("🤖 AI智能洞察")
        insights_content = QWidget()
        insights_layout = QVBoxLayout(insights_content)
        insights_layout.setContentsMargins(0, 0, 0, 0)
        
        self.insights_text = QTextEdit()
        self.insights_text.setPlaceholderText("AI将分析数据并提供智能洞察...")
        self.insights_text.setProperty("class", "insights-text")
        self.insights_text.setMaximumHeight(200)
        insights_layout.addWidget(self.insights_text)
        
        insights_card.add_content(insights_content)
        layout.addWidget(insights_card)
        
        return widget
    
    def _create_projects_tab(self) -> QWidget:
        """创建项目统计标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 项目统计概览
        stats_card = ProfessionalCard("项目统计概览")
        stats_content = QWidget()
        stats_layout = QGridLayout(stats_content)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.project_stats_widgets = {}
        project_stats = self._generate_project_stats()
        
        for i, (key, data) in enumerate(project_stats.items()):
            stat_widget = self._create_stat_widget(data)
            stats_layout.addWidget(stat_widget, i // 3, i % 3)
            self.project_stats_widgets[key] = stat_widget
        
        stats_card.add_content(stats_content)
        layout.addWidget(stats_card)
        
        # 项目分布图表
        self.project_distribution_chart = self._create_project_distribution_chart()
        layout.addWidget(self.project_distribution_chart)
        
        # 项目详情表格
        self.projects_table = self._create_projects_table()
        layout.addWidget(self.projects_table)
        
        return widget
    
    def _create_performance_tab(self) -> QWidget:
        """创建性能分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 性能指标
        perf_card = ProfessionalCard("性能指标")
        perf_content = QWidget()
        perf_layout = QGridLayout(perf_content)
        perf_layout.setContentsMargins(0, 0, 0, 0)
        
        self.performance_metrics = {}
        perf_data = self._generate_performance_data()
        
        for i, (key, data) in enumerate(perf_data.items()):
            metric_widget = self._create_performance_metric_widget(data)
            perf_layout.addWidget(metric_widget, i // 3, i % 3)
            self.performance_metrics[key] = metric_widget
        
        perf_card.add_content(perf_content)
        layout.addWidget(perf_card)
        
        # 性能趋势图
        self.performance_trend_chart = self._create_performance_trend_chart()
        layout.addWidget(self.performance_trend_chart)
        
        # 系统资源使用情况
        self.resource_usage_chart = self._create_resource_usage_chart()
        layout.addWidget(self.resource_usage_chart)
        
        return widget
    
    def _create_ai_insights_tab(self) -> QWidget:
        """创建AI洞察标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # AI洞察控制面板
        control_card = ProfessionalCard("AI洞察控制面板")
        control_content = QWidget()
        control_layout = QHBoxLayout(control_content)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分析深度选择
        depth_layout = QVBoxLayout()
        depth_label = QLabel("分析深度")
        depth_layout.addWidget(depth_label)
        
        self.analysis_depth_combo = QComboBox()
        self.analysis_depth_combo.addItems(["基础分析", "深度分析", "专业分析"])
        depth_layout.addWidget(self.analysis_depth_combo)
        
        control_layout.addLayout(depth_layout)
        
        # 洞察类型选择
        type_layout = QVBoxLayout()
        type_label = QLabel("洞察类型")
        type_layout.addWidget(type_label)
        
        self.insight_type_combo = QComboBox()
        self.insight_type_combo.addItems(["趋势预测", "异常检测", "优化建议", "模式识别"])
        type_layout.addWidget(self.insight_type_combo)
        
        control_layout.addLayout(type_layout)
        
        # 生成洞察按钮
        self.generate_insights_btn = ProfessionalButton("🧠 生成洞察", "primary")
        self.generate_insights_btn.clicked.connect(self._generate_ai_insights)
        control_layout.addWidget(self.generate_insights_btn)
        
        control_layout.addStretch()
        control_card.add_content(control_content)
        layout.addWidget(control_card)
        
        # 洞察结果区域
        insights_result_card = ProfessionalCard("洞察结果")
        insights_result_content = QWidget()
        insights_result_layout = QVBoxLayout(insights_result_content)
        insights_result_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ai_insights_display = QTextEdit()
        self.ai_insights_display.setProperty("class", "ai-insights-display")
        insights_result_layout.addWidget(self.ai_insights_display)
        
        insights_result_card.add_content(insights_result_content)
        layout.addWidget(insights_result_card)
        
        # 洞察历史
        history_card = ProfessionalCard("洞察历史")
        history_content = QWidget()
        history_layout = QVBoxLayout(history_content)
        history_layout.setContentsMargins(0, 0, 0, 0)
        
        self.insights_history = QListWidget()
        self.insights_history.setProperty("class", "insights-history")
        history_layout.addWidget(self.insights_history)
        
        history_card.add_content(history_content)
        layout.addWidget(history_card)
        
        return widget
    
    def _create_user_behavior_tab(self) -> QWidget:
        """创建用户行为标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 用户行为统计
        behavior_card = ProfessionalCard("用户行为统计")
        behavior_content = QWidget()
        behavior_layout = QGridLayout(behavior_content)
        behavior_layout.setContentsMargins(0, 0, 0, 0)
        
        self.behavior_metrics = {}
        behavior_data = self._generate_behavior_data()
        
        for i, (key, data) in enumerate(behavior_data.items()):
            metric_widget = self._create_behavior_metric_widget(data)
            behavior_layout.addWidget(metric_widget, i // 3, i % 3)
            self.behavior_metrics[key] = metric_widget
        
        behavior_card.add_content(behavior_content)
        layout.addWidget(behavior_card)
        
        # 行为模式图表
        self.behavior_pattern_chart = self._create_behavior_pattern_chart()
        layout.addWidget(self.behavior_pattern_chart)
        
        # 热力图
        self.heatmap_chart = self._create_heatmap_chart()
        layout.addWidget(self.heatmap_chart)
        
        return widget
    
    def _generate_metrics_data(self) -> Dict[str, Dict]:
        """生成关键指标数据"""
        return {
            'total_projects': {
                'title': '总项目数',
                'value': '156',
                'change': '+12%',
                'icon': '📁',
                'color': '#1890ff'
            },
            'active_projects': {
                'title': '活跃项目',
                'value': '89',
                'change': '+8%',
                'icon': '⚡',
                'color': '#52c41a'
            },
            'total_videos': {
                'title': '总视频数',
                'value': '1,234',
                'change': '+23%',
                'icon': '🎬',
                'color': '#722ed1'
            },
            'total_duration': {
                'title': '总时长',
                'value': '456h',
                'change': '+15%',
                'icon': '⏱️',
                'color': '#fa8c16'
            },
            'ai_usage': {
                'title': 'AI使用率',
                'value': '78%',
                'change': '+5%',
                'icon': '🤖',
                'color': '#13c2c2'
            },
            'export_count': {
                'title': '导出次数',
                'value': '892',
                'change': '+34%',
                'icon': '📤',
                'color': '#f5222d'
            },
            'storage_used': {
                'title': '存储使用',
                'value': '45GB',
                'change': '+18%',
                'icon': '💾',
                'color': '#eb2f96'
            },
            'user_satisfaction': {
                'title': '用户满意度',
                'value': '92%',
                'change': '+3%',
                'icon': '😊',
                'color': '#52c41a'
            }
        }
    
    def _generate_project_stats(self) -> Dict[str, Dict]:
        """生成项目统计数据"""
        return {
            'completed_projects': {
                'title': '已完成',
                'value': '67',
                'percentage': 43,
                'color': '#52c41a'
            },
            'in_progress': {
                'title': '进行中',
                'value': '89',
                'percentage': 57,
                'color': '#1890ff'
            },
            'on_hold': {
                'title': '暂停',
                'value': '12',
                'percentage': 8,
                'color': '#fa8c16'
            },
            'avg_project_size': {
                'title': '平均项目大小',
                'value': '287MB',
                'color': '#722ed1'
            },
            'avg_completion_time': {
                'title': '平均完成时间',
                'value': '3.2天',
                'color': '#13c2c2'
            },
            'success_rate': {
                'title': '成功率',
                'value': '94%',
                'color': '#52c41a'
            }
        }
    
    def _generate_performance_data(self) -> Dict[str, Dict]:
        """生成性能数据"""
        return {
            'cpu_usage': {
                'title': 'CPU使用率',
                'value': '45%',
                'status': 'normal',
                'color': '#52c41a'
            },
            'memory_usage': {
                'title': '内存使用',
                'value': '67%',
                'status': 'warning',
                'color': '#faad14'
            },
            'disk_usage': {
                'title': '磁盘使用',
                'value': '78%',
                'status': 'warning',
                'color': '#faad14'
            },
            'render_speed': {
                'title': '渲染速度',
                'value': '120fps',
                'status': 'good',
                'color': '#52c41a'
            },
            'ai_response_time': {
                'title': 'AI响应时间',
                'value': '1.2s',
                'status': 'good',
                'color': '#52c41a'
            },
            'network_latency': {
                'title': '网络延迟',
                'value': '23ms',
                'status': 'excellent',
                'color': '#52c41a'
            }
        }
    
    def _generate_behavior_data(self) -> Dict[str, Dict]:
        """生成用户行为数据"""
        return {
            'daily_active_users': {
                'title': '日活跃用户',
                'value': '1,234',
                'change': '+15%',
                'icon': '👤'
            },
            'avg_session_time': {
                'title': '平均会话时长',
                'value': '45min',
                'change': '+8%',
                'icon': '⏰'
            },
            'feature_usage': {
                'title': '功能使用率',
                'value': '78%',
                'change': '+12%',
                'icon': '🎯'
            },
            'error_rate': {
                'title': '错误率',
                'value': '2.3%',
                'change': '-0.5%',
                'icon': '⚠️'
            },
            'user_retention': {
                'title': '用户留存率',
                'value': '85%',
                'change': '+5%',
                'icon': '📈'
            },
            'support_requests': {
                'title': '支持请求',
                'value': '23',
                'change': '-12%',
                'icon': '🛟'
            }
        }
    
    def _create_metric_widget(self, data: Dict) -> QWidget:
        """创建指标组件"""
        widget = QWidget()
        widget.setProperty("class", "metric-widget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel(data['title'])
        title_label.setProperty("class", "metric-title")
        layout.addWidget(title_label)
        
        # 值和图标
        value_layout = QHBoxLayout()
        
        icon_label = QLabel(data['icon'])
        icon_label.setProperty("class", "metric-icon")
        value_layout.addWidget(icon_label)
        
        value_label = QLabel(data['value'])
        value_label.setProperty("class", "metric-value")
        value_layout.addWidget(value_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # 变化
        if 'change' in data:
            change_label = QLabel(data['change'])
            change_label.setProperty("class", "metric-change")
            layout.addWidget(change_label)
        
        return widget
    
    def _create_stat_widget(self, data: Dict) -> QWidget:
        """创建统计组件"""
        widget = QWidget()
        widget.setProperty("class", "stat-widget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel(data['title'])
        title_label.setProperty("class", "stat-title")
        layout.addWidget(title_label)
        
        # 值
        value_label = QLabel(data['value'])
        value_label.setProperty("class", "stat-value")
        layout.addWidget(value_label)
        
        # 百分比
        if 'percentage' in data:
            percentage_label = QLabel(f"{data['percentage']}%")
            percentage_label.setProperty("class", "stat-percentage")
            layout.addWidget(percentage_label)
        
        return widget
    
    def _create_performance_metric_widget(self, data: Dict) -> QWidget:
        """创建性能指标组件"""
        widget = QWidget()
        widget.setProperty("class", "performance-metric-widget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel(data['title'])
        title_label.setProperty("class", "performance-title")
        layout.addWidget(title_label)
        
        # 值
        value_label = QLabel(data['value'])
        value_label.setProperty("class", f"performance-value status-{data['status']}")
        layout.addWidget(value_label)
        
        return widget
    
    def _create_behavior_metric_widget(self, data: Dict) -> QWidget:
        """创建用户行为指标组件"""
        widget = QWidget()
        widget.setProperty("class", "behavior-metric-widget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题和图标
        header_layout = QHBoxLayout()
        
        if 'icon' in data:
            icon_label = QLabel(data['icon'])
            icon_label.setProperty("class", "behavior-icon")
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(data['title'])
        title_label.setProperty("class", "behavior-title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 值
        value_label = QLabel(data['value'])
        value_label.setProperty("class", "behavior-value")
        layout.addWidget(value_label)
        
        # 变化
        if 'change' in data:
            change_label = QLabel(data['change'])
            change_label.setProperty("class", "behavior-change")
            layout.addWidget(change_label)
        
        return widget
    
    def _create_trend_chart(self) -> QChartView:
        """创建趋势图表"""
        chart = QChart()
        chart.setTitle("数据趋势")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # 创建折线系列
        series = QLineSeries()
        series.setName("活跃项目")
        
        # 生成示例数据
        for i in range(30):
            x = i
            y = 50 + random.randint(-20, 30) + (i * 2)
            series.append(x, y)
        
        chart.addSeries(series)
        
        # 设置坐标轴
        axisX = QValueAxis()
        axisX.setTitle("天数")
        axisX.setRange(0, 30)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setTitle("数量")
        axisY.setRange(0, 150)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_distribution_chart(self) -> QChartView:
        """创建分布图表"""
        chart = QChart()
        chart.setTitle("项目分布")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # 创建柱状系列
        set0 = QBarSet("项目数")
        set0.append([67, 89, 12, 45, 23])
        
        series = QBarSeries()
        series.append(set0)
        chart.addSeries(series)
        
        # 设置分类轴
        categories = ["已完成", "进行中", "暂停", "计划中", "审核中"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setRange(0, 100)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_project_distribution_chart(self) -> QChartView:
        """创建项目分布图表"""
        chart = QChart()
        chart.setTitle("项目类型分布")
        
        # 创建饼图数据
        set0 = QBarSet("数量")
        set0.append([45, 32, 28, 15, 12, 8])
        
        series = QBarSeries()
        series.append(set0)
        chart.addSeries(series)
        
        categories = ["解说", "混剪", "教程", "Vlog", "宣传", "其他"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setRange(0, 50)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_performance_trend_chart(self) -> QChartView:
        """创建性能趋势图表"""
        chart = QChart()
        chart.setTitle("系统性能趋势")
        
        # 创建多个系列
        cpu_series = QLineSeries()
        cpu_series.setName("CPU使用率")
        cpu_series.setColor(QColor("#1890ff"))
        
        memory_series = QLineSeries()
        memory_series.setName("内存使用率")
        memory_series.setColor(QColor("#52c41a"))
        
        # 生成示例数据
        for i in range(24):
            cpu_series.append(i, 30 + random.randint(-10, 20))
            memory_series.append(i, 50 + random.randint(-15, 25))
        
        chart.addSeries(cpu_series)
        chart.addSeries(memory_series)
        
        # 设置坐标轴
        axisX = QValueAxis()
        axisX.setTitle("小时")
        axisX.setRange(0, 24)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        cpu_series.attachAxis(axisX)
        memory_series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setTitle("使用率 (%)")
        axisY.setRange(0, 100)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        cpu_series.attachAxis(axisY)
        memory_series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_resource_usage_chart(self) -> QChartView:
        """创建资源使用图表"""
        chart = QChart()
        chart.setTitle("资源使用情况")
        
        set0 = QBarSet("当前使用")
        set0.append([45, 67, 78, 23])
        set0.setColor(QColor("#1890ff"))
        
        set1 = QBarSet("总容量")
        set1.append([100, 100, 100, 100])
        set1.setColor(QColor("#f0f0f0"))
        
        series = QBarSeries()
        series.append(set0)
        series.append(set1)
        chart.addSeries(series)
        
        categories = ["CPU", "内存", "磁盘", "网络"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setRange(0, 100)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_behavior_pattern_chart(self) -> QChartView:
        """创建用户行为模式图表"""
        chart = QChart()
        chart.setTitle("用户行为模式")
        
        # 创建折线系列
        active_series = QLineSeries()
        active_series.setName("活跃用户")
        active_series.setColor(QColor("#52c41a"))
        
        session_series = QLineSeries()
        session_series.setName("会话时长")
        session_series.setColor(QColor("#1890ff"))
        
        # 生成示例数据
        for i in range(7):
            active_series.append(i, 800 + random.randint(-200, 400))
            session_series.append(i, 40 + random.randint(-10, 20))
        
        chart.addSeries(active_series)
        chart.addSeries(session_series)
        
        # 设置坐标轴
        categories = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        active_series.attachAxis(axisX)
        session_series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setRange(0, 1500)
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        active_series.attachAxis(axisY)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_heatmap_chart(self) -> QChartView:
        """创建热力图"""
        chart = QChart()
        chart.setTitle("使用时间热力图")
        
        # 创建热力图数据
        heatmap_data = []
        for hour in range(24):
            for day in range(7):
                # 模拟使用强度
                intensity = random.randint(0, 100)
                heatmap_data.append(intensity)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view
    
    def _create_projects_table(self) -> QTableWidget:
        """创建项目表格"""
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "项目名称", "类型", "状态", "进度", "大小", "创建时间", "修改时间", "操作"
        ])
        
        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 填充示例数据
        self._populate_projects_table(table)
        
        return table
    
    def _populate_projects_table(self, table: QTableWidget):
        """填充项目表格数据"""
        sample_data = [
            ["电影解说合集", "解说", "进行中", "75%", "2.3GB", "2024-01-10", "2024-01-15", "查看"],
            ["短视频混剪", "混剪", "已完成", "100%", "856MB", "2024-01-08", "2024-01-14", "查看"],
            ["软件教程系列", "教程", "计划中", "25%", "1.2GB", "2024-01-12", "2024-01-13", "查看"],
            ["产品演示", "演示", "进行中", "60%", "324MB", "2024-01-05", "2024-01-12", "查看"],
            ["日常Vlog", "Vlog", "已完成", "100%", "567MB", "2024-01-01", "2024-01-11", "查看"]
        ]
        
        table.setRowCount(len(sample_data))
        for row, data in enumerate(sample_data):
            for col, text in enumerate(data):
                if col == 7:  # 操作列
                    btn = QPushButton(text)
                    btn.setProperty("class", "table-action-btn")
                    table.setCellWidget(row, col, btn)
                else:
                    item = QTableWidgetItem(text)
                    table.setItem(row, col, item)
    
    def _init_sample_data(self):
        """初始化示例数据"""
        # 初始化AI洞察内容
        initial_insights = """🤖 AI智能洞察分析结果：

📈 关键发现：
• 项目总数稳步增长，月增长率达12%
• AI功能使用率达到78%，用户接受度高
• 视频处理效率提升23%，性能优化显著
• 用户满意度达92%，产品质量优秀

💡 优化建议：
• 建议增加更多AI辅助功能
• 优化大文件处理性能
• 加强用户培训和支持
• 考虑增加协作功能

🎯 预测趋势：
• 基于当前数据，预计下月项目数将增长15-20%
• AI使用率有望突破85%
• 用户留存率将保持稳定增长"""
        
        self.insights_text.setPlainText(initial_insights)
    
    def _connect_signals(self):
        """连接信号"""
        self.refresh_btn.clicked.connect(self._refresh_data)
        self.generate_insights_btn.clicked.connect(self._generate_ai_insights)
        
        # 导出按钮信号
        if hasattr(self, 'export_pdf_btn'):
            self.export_pdf_btn.clicked.connect(lambda: self._export_report("pdf"))
        if hasattr(self, 'export_excel_btn'):
            self.export_excel_btn.clicked.connect(lambda: self._export_report("excel"))
        if hasattr(self, 'share_report_btn'):
            self.share_report_btn.clicked.connect(self._share_report)
    
    def _on_tab_changed(self, index: int):
        """标签切换事件"""
        tab_names = ["综合分析", "项目统计", "性能分析", "AI洞察", "用户行为"]
        if index < len(tab_names):
            self._refresh_tab_data(tab_names[index])
    
    def _refresh_tab_data(self, tab_name: str):
        """刷新标签数据"""
        self.loading_overlay.show_loading(f"正在刷新{tab_name}数据...")
        
        # 模拟数据刷新
        QTimer.singleShot(1000, self._complete_refresh)
    
    def _refresh_data(self):
        """刷新所有数据"""
        self.loading_overlay.show_loading("正在刷新数据...")
        
        # 模拟数据刷新
        QTimer.singleShot(1500, self._complete_refresh)
    
    def _complete_refresh(self):
        """完成刷新"""
        self.loading_overlay.complete_loading()
        
        # 更新所有数据
        self._update_all_metrics()
        self._update_charts()
        
        self.error_handler.show_toast("刷新完成", "数据已更新", MessageType.SUCCESS)
    
    def _update_all_metrics(self):
        """更新所有指标"""
        # 更新关键指标
        new_metrics_data = self._generate_metrics_data()
        for key, widget in self.metrics_widgets.items():
            if key in new_metrics_data:
                self._update_metric_widget(widget, new_metrics_data[key])
        
        # 更新项目统计
        new_project_stats = self._generate_project_stats()
        for key, widget in self.project_stats_widgets.items():
            if key in new_project_stats:
                self._update_stat_widget(widget, new_project_stats[key])
        
        # 更新性能指标
        new_perf_data = self._generate_performance_data()
        for key, widget in self.performance_metrics.items():
            if key in new_perf_data:
                self._update_performance_metric_widget(widget, new_perf_data[key])
        
        # 更新用户行为指标
        new_behavior_data = self._generate_behavior_data()
        for key, widget in self.behavior_metrics.items():
            if key in new_behavior_data:
                self._update_behavior_metric_widget(widget, new_behavior_data[key])
    
    def _update_metric_widget(self, widget: QWidget, data: Dict):
        """更新指标组件"""
        # 更新值
        value_labels = widget.findChildren(QLabel)
        for label in value_labels:
            if label.property("class") == "metric-value":
                label.setText(data['value'])
            elif label.property("class") == "metric-change":
                if 'change' in data:
                    label.setText(data['change'])
    
    def _update_stat_widget(self, widget: QWidget, data: Dict):
        """更新统计组件"""
        value_labels = widget.findChildren(QLabel)
        for label in value_labels:
            if label.property("class") == "stat-value":
                label.setText(data['value'])
            elif label.property("class") == "stat-percentage":
                if 'percentage' in data:
                    label.setText(f"{data['percentage']}%")
    
    def _update_performance_metric_widget(self, widget: QWidget, data: Dict):
        """更新性能指标组件"""
        value_labels = widget.findChildren(QLabel)
        for label in value_labels:
            if label.property("class") == "performance-value":
                label.setText(data['value'])
                # 更新状态样式
                label.setProperty("class", f"performance-value status-{data['status']}")
    
    def _update_behavior_metric_widget(self, widget: QWidget, data: Dict):
        """更新用户行为指标组件"""
        value_labels = widget.findChildren(QLabel)
        for label in value_labels:
            if label.property("class") == "behavior-value":
                label.setText(data['value'])
            elif label.property("class") == "behavior-change":
                if 'change' in data:
                    label.setText(data['change'])
    
    def _update_charts(self):
        """更新图表"""
        # 这里可以重新生成图表数据
        pass
    
    def _generate_ai_insights(self):
        """生成AI洞察"""
        self.generate_insights_btn.setText("🧠 分析中...")
        self.generate_insights_btn.setEnabled(False)
        
        self.loading_overlay.show_loading("AI正在分析数据...")
        
        # 模拟AI分析过程
        QTimer.singleShot(3000, self._complete_ai_insights)
    
    def _complete_ai_insights(self):
        """完成AI洞察生成"""
        analysis_depth = self.analysis_depth_combo.currentText()
        insight_type = self.insight_type_combo.currentText()
        
        # 生成AI洞察内容
        insights = self._generate_ai_insights_content(analysis_depth, insight_type)
        
        self.ai_insights_display.setPlainText(insights)
        
        # 添加到历史记录
        self._add_to_insights_history(insight_type, insights)
        
        self.loading_overlay.complete_loading()
        self.generate_insights_btn.setText("🧠 生成洞察")
        self.generate_insights_btn.setEnabled(True)
        
        self.error_handler.show_toast("分析完成", "AI洞察已生成", MessageType.SUCCESS)
    
    def _generate_ai_insights_content(self, depth: str, insight_type: str) -> str:
        """生成AI洞察内容"""
        base_insights = {
            "趋势预测": """📈 趋势预测分析：

🔮 未来30天预测：
• 项目数量预计增长18-25%
• AI使用率将达到85-90%
• 视频处理效率提升30%
• 用户满意度有望突破95%

⚡ 增长驱动因素：
• AI功能持续优化
• 用户体验改善
• 市场推广效果显著
• 用户口碑传播

📊 关键指标预测：
• 日活跃用户：1,500-1,800
• 项目完成率：提升至88%
• 平均处理时间：缩短至2.8天
• 系统稳定性：99.5%以上""",
            
            "异常检测": """🔍 异常检测结果：

⚠️ 发现异常模式：
• 内存使用率在下午2-4点异常升高
• 某些项目文件大小超过正常范围
• 网络延迟在特定时段出现波动
• 错误率在周末有所上升

🔧 建议处理方案：
• 优化内存管理算法
• 增加大文件处理优化
• 改善网络连接稳定性
• 加强周末系统监控

📈 异常影响评估：
• 当前异常对用户体验影响较小
• 建议优先处理内存优化
• 需要持续监控网络状况
• 整体系统稳定性良好""",
            
            "优化建议": """💡 优化建议报告：

🎯 短期优化（1-2周）：
• 优化数据库查询性能
• 改进用户界面响应速度
• 增加错误处理机制
• 优化内存使用效率

🚀 中期优化（1-2月）：
• 引入更先进的AI模型
• 重构部分核心模块
• 增加自动化测试覆盖
• 优化文件存储结构

🏗️ 长期优化（3-6月）：
• 架构升级和重构
• 引入微服务架构
• 增加分布式处理能力
• 完善监控和告警系统

📊 预期收益：
• 性能提升40-60%
• 用户满意度提升10-15%
• 系统稳定性提升至99.9%
• 运营成本降低20-30%""",
            
            "模式识别": """🔍 模式识别分析：

👥 用户行为模式：
• 高峰使用时间：上午9-11点，晚上7-9点
• 平均会话时长：45分钟
• 最常用功能：视频编辑、AI处理、项目导出
• 用户留存率：85%（行业领先）

📈 使用趋势模式：
• 周末使用量比工作日高25%
• 月底项目创建数量增加
• AI功能使用率持续上升
• 移动端使用比例增长

🎯 功能使用模式：
• 80%的用户使用核心功能
• AI功能使用率达78%
• 协作功能使用率较低（12%）
• 高级功能使用率逐步提升

💡 改进建议：
• 优化高峰时段性能
• 增加周末专属功能
• 加强AI功能推广
• 改进协作功能体验"""
        }
        
        insights = base_insights.get(insight_type, "正在分析...")
        
        # 根据分析深度调整内容详细程度
        if depth == "基础分析":
            insights = insights.split('\n\n')[0] + "\n\n[基础分析模式 - 显示核心洞察]"
        elif depth == "专业分析":
            insights += f"\n\n[专业分析模式 - 深度数据挖掘]\n分析深度：{depth}\n洞察类型：{insight_type}\n分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return insights
    
    def _add_to_insights_history(self, insight_type: str, content: str):
        """添加到洞察历史"""
        item = QListWidgetItem()
        item.setText(f"{datetime.now().strftime('%m-%d %H:%M')} - {insight_type}")
        item.setData(Qt.ItemDataRole.UserRole, {
            'type': insight_type,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        self.insights_history.insertItem(0, item)
        
        # 限制历史记录数量
        if self.insights_history.count() > 50:
            self.insights_history.takeItem(self.insights_history.count() - 1)
    
    def _export_report(self, format_type: str):
        """导出报告"""
        format_names = {"pdf": "PDF", "excel": "Excel", "json": "JSON"}
        format_name = format_names.get(format_type, "未知格式")
        
        self.loading_overlay.show_loading(f"正在导出{format_name}报告...")
        
        # 模拟导出过程
        QTimer.singleShot(2000, lambda: self._complete_export(format_type, format_name))
    
    def _complete_export(self, format_type: str, format_name: str):
        """完成导出"""
        self.loading_overlay.complete_loading()
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analytics_report_{timestamp}.{format_type}"
        
        self.data_exported.emit(filename)
        self.error_handler.show_toast("导出完成", f"报告已导出为 {format_name} 格式", MessageType.SUCCESS)
    
    def _share_report(self):
        """分享报告"""
        self.loading_overlay.show_loading("正在准备分享...")
        
        # 模拟分享过程
        QTimer.singleShot(1500, self._complete_share)
    
    def _complete_share(self):
        """完成分享"""
        self.loading_overlay.complete_loading()
        self.error_handler.show_toast("分享成功", "分析报告已准备分享", MessageType.SUCCESS)
    
    def _apply_styles(self):
        """应用样式"""
        if self.is_dark_theme:
            self.setStyleSheet("""
                AnalyticsPage {
                    background-color: #1f1f1f;
                    color: #ffffff;
                }
                
                .page-title {
                    font-size: 28px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 20px;
                }
                
                .tool-btn {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: #ffffff;
                    font-size: 14px;
                }
                
                .tool-btn:hover {
                    background-color: #177ddc;
                    border-color: #177ddc;
                }
                
                .analytics-tabs {
                    background-color: transparent;
                }
                
                .analytics-tabs::pane {
                    border: none;
                }
                
                .analytics-tabs::tab-bar {
                    left: 0px;
                }
                
                .analytics-tabs QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 10px 20px;
                    margin-right: 5px;
                }
                
                .analytics-tabs QTabBar::tab:selected {
                    background-color: #177ddc;
                    border-color: #177ddc;
                }
                
                .analytics-tabs QTabBar::tab:hover {
                    background-color: #4096ff;
                }
                
                .card-title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 10px;
                }
                
                .metric-widget, .stat-widget, .performance-metric-widget, .behavior-metric-widget {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 12px;
                    min-height: 120px;
                }
                
                .metric-title, .stat-title, .performance-title, .behavior-title {
                    font-size: 14px;
                    font-weight: bold;
                    color: #ffffff;
                }
                
                .metric-value, .stat-value, .performance-value, .behavior-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #ffffff;
                }
                
                .metric-icon, .behavior-icon {
                    font-size: 24px;
                }
                
                .metric-change, .behavior-change {
                    font-size: 12px;
                    color: #52c41a;
                }
                
                .performance-value.status-normal {
                    color: #52c41a;
                }
                
                .performance-value.status-warning {
                    color: #faad14;
                }
                
                .performance-value.status-good {
                    color: #52c41a;
                }
                
                .performance-value.status-excellent {
                    color: #1890ff;
                }
                
                .insights-text, .ai-insights-display {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                    padding: 15px;
                    color: #ffffff;
                    font-size: 13px;
                    line-height: 1.6;
                }
                
                .insights-history {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                    color: #ffffff;
                }
                
                .insights-history::item {
                    padding: 8px;
                    border-bottom: 1px solid #444;
                }
                
                .insights-history::item:selected {
                    background-color: #177ddc;
                }
                
                .table-action-btn {
                    background-color: #177ddc;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                
                .table-action-btn:hover {
                    background-color: #4096ff;
                }
                
                QTableWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                    gridline-color: #444;
                    alternate-background-color: #1f1f1f;
                }
                
                QTableWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #444;
                }
                
                QTableWidget::item:selected {
                    background-color: #177ddc;
                    color: #ffffff;
                }
                
                QHeaderView::section {
                    background-color: #1f1f1f;
                    color: #ffffff;
                    padding: 8px;
                    border: none;
                    border-bottom: 2px solid #444;
                    font-weight: bold;
                }
                
                QChart {
                    background-color: transparent;
                    color: #ffffff;
                }
                
                QChartView {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                AnalyticsPage {
                    background-color: #ffffff;
                    color: #262626;
                }
                
                .page-title {
                    font-size: 28px;
                    font-weight: bold;
                    color: #262626;
                    margin-bottom: 20px;
                }
                
                .tool-btn {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: #262626;
                    font-size: 14px;
                }
                
                .tool-btn:hover {
                    background-color: #1890ff;
                    color: white;
                    border-color: #1890ff;
                }
                
                .analytics-tabs {
                    background-color: transparent;
                }
                
                .analytics-tabs::pane {
                    border: none;
                }
                
                .analytics-tabs::tab-bar {
                    left: 0px;
                }
                
                .analytics-tabs QTabBar::tab {
                    background-color: #f5f5f5;
                    color: #262626;
                    border: 1px solid #ddd;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 10px 20px;
                    margin-right: 5px;
                }
                
                .analytics-tabs QTabBar::tab:selected {
                    background-color: #1890ff;
                    color: white;
                    border-color: #1890ff;
                }
                
                .analytics-tabs QTabBar::tab:hover {
                    background-color: #e6f7ff;
                }
                
                .card-title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #262626;
                    margin-bottom: 10px;
                }
                
                .metric-widget, .stat-widget, .performance-metric-widget, .behavior-metric-widget {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 12px;
                    min-height: 120px;
                    /* box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); */
                }
                
                .metric-title, .stat-title, .performance-title, .behavior-title {
                    font-size: 14px;
                    font-weight: bold;
                    color: #262626;
                }
                
                .metric-value, .stat-value, .performance-value, .behavior-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #262626;
                }
                
                .metric-icon, .behavior-icon {
                    font-size: 24px;
                }
                
                .metric-change, .behavior-change {
                    font-size: 12px;
                    color: #52c41a;
                }
                
                .performance-value.status-normal {
                    color: #52c41a;
                }
                
                .performance-value.status-warning {
                    color: #faad14;
                }
                
                .performance-value.status-good {
                    color: #52c41a;
                }
                
                .performance-value.status-excellent {
                    color: #1890ff;
                }
                
                .insights-text, .ai-insights-display {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    color: #262626;
                    font-size: 13px;
                    line-height: 1.6;
                }
                
                .insights-history {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    color: #262626;
                }
                
                .insights-history::item {
                    padding: 8px;
                    border-bottom: 1px solid #f0f0f0;
                }
                
                .insights-history::item:selected {
                    background-color: #1890ff;
                    color: white;
                }
                
                .table-action-btn {
                    background-color: #1890ff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                
                .table-action-btn:hover {
                    background-color: #4096ff;
                }
                
                QTableWidget {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid #ddd;
                    gridline-color: #f0f0f0;
                    alternate-background-color: #fafafa;
                }
                
                QTableWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #f0f0f0;
                }
                
                QTableWidget::item:selected {
                    background-color: #1890ff;
                    color: white;
                }
                
                QHeaderView::section {
                    background-color: #fafafa;
                    color: #262626;
                    padding: 8px;
                    border: none;
                    border-bottom: 2px solid #f0f0f0;
                    font-weight: bold;
                }
                
                QChart {
                    background-color: transparent;
                    color: #262626;
                }
                
                QChartView {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
            """)
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()
        
        # 更新子组件主题
        for chart in self.findChildren(QChartView):
            chart.setStyleSheet("")
    
    def _connect_signals(self):
        """连接信号"""
        # 分析类型按钮
        for btn in self.findChildren(ProfessionalButton):
            if btn.property("analysis_type"):
                btn.clicked.connect(self._on_analysis_clicked)
            elif btn.property("time_range"):
                btn.clicked.connect(self._on_time_range_clicked)
        
        # 开始分析按钮
        self.start_analysis_btn.clicked.connect(self._start_analysis)
        
        # 导出按钮
        self.export_pdf_btn.clicked.connect(lambda: self._export_report("pdf"))
        self.export_excel_btn.clicked.connect(lambda: self._export_report("excel"))
        self.share_report_btn.clicked.connect(self._share_report)
    
    def _on_analysis_clicked(self):
        """分析类型点击"""
        btn = self.sender()
        analysis_type = btn.property("analysis_type")
        
        analysis_names = {
            "overview": "整体数据概览",
            "audience": "观众分析",
            "performance": "性能表现",
            "content": "内容效果",
            "cost": "成本分析",
            "competition": "竞争分析"
        }
        
        analysis_name = analysis_names.get(analysis_type, "未知分析")
        QMessageBox.information(self, "分析类型", f"已选择: {analysis_name}")
    
    def _on_time_range_clicked(self):
        """时间范围点击"""
        btn = self.sender()
        time_range = btn.property("time_range")
        
        time_names = {
            "7days": "最近7天",
            "30days": "最近30天",
            "90days": "最近90天",
            "year": "今年",
            "custom": "自定义"
        }
        
        time_name = time_names.get(time_range, "未知时间")
        QMessageBox.information(self, "时间范围", f"已选择: {time_name}")
    
    def _start_analysis(self):
        """开始分析"""
        self.start_analysis_btn.setText("🔄 分析中...")
        self.start_analysis_btn.setEnabled(False)
        
        # 模拟分析过程
        QTimer.singleShot(2000, lambda: self._update_analysis_progress())
        QTimer.singleShot(4000, lambda: self._complete_analysis())
    
    def _update_analysis_progress(self):
        """更新分析进度"""
        self.insights_text.setPlainText("正在分析数据...")
        self.chart_placeholder.setText("📈 正在生成图表...")
    
    def _complete_analysis(self):
        """完成分析"""
        # 生成AI洞察
        insights = """🤖 AI智能洞察分析结果：

📈 关键发现：
• 观众留存率较高（78.2%），说明内容质量良好
• 互动率有提升空间，建议增加互动元素
• 分享率表现优秀，用户愿意传播内容

💡 优化建议：
• 建议在视频前30秒增加吸引力内容
• 可以尝试更多互动话题提高评论率
• 考虑在高峰时段发布新内容

🎯 预测趋势：
• 基于当前数据，预计下周播放量将增长15-20%
• 建议继续当前的内容策略"""
        
        self.insights_text.setPlainText(insights)
        self.chart_placeholder.setText("📈 趋势图表已生成")
        
        self.start_analysis_btn.setText("🚀 开始分析")
        self.start_analysis_btn.setEnabled(True)
        
        QMessageBox.information(self, "分析完成", "数据分析已完成！")
    
    def _export_report(self, format_type: str):
        """导出报告"""
        format_names = {"pdf": "PDF", "excel": "Excel"}
        format_name = format_names.get(format_type, "未知格式")
        
        QMessageBox.information(self, "导出报告", f"正在导出{format_name}格式报告...")
    
    def _share_report(self):
        """分享报告"""
        QMessageBox.information(self, "分享报告", "正在准备分享分析报告...")
    
    def set_theme(self, is_dark_theme: bool):
        """设置主题"""
        self.is_dark_theme = is_dark_theme
        self._apply_styles()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = AnalyticsPage()
    window.show()
    sys.exit(app.exec())