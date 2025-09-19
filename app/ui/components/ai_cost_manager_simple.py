#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的AI成本管理器 - 不使用QtCharts
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QGridLayout, QGroupBox, QCheckBox,
    QTabWidget, QSlider, QSpinBox, QFormLayout, QFileDialog,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QProgressBar, QTextEdit,
    QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QToolButton, QMenu,
    QApplication, QSizePolicy, QSpacerItem, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QCalendarWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize, QPoint, QDate
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen, QBrush

from app.ai.enhanced_ai_manager import EnhancedAIManager
from app.ai.cost_manager import ChineseLLMCostManager, CostTier
from app.config.settings_manager import SettingsManager
from ..professional_ui_system import ProfessionalStyleEngine, ColorScheme, FontScheme


class CostPeriod(Enum):
    """成本统计周期"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


@dataclass
class BudgetInfo:
    """预算信息"""
    total_amount: float
    used_amount: float = 0.0
    period: CostPeriod = CostPeriod.MONTH
    start_date: datetime = None
    end_date: datetime = None
    
    def __post_init__(self):
        if self.start_date is None:
            self.start_date = datetime.now()
        if self.end_date is None:
            # 根据周期设置结束日期
            if self.period == CostPeriod.TODAY:
                self.end_date = self.start_date.replace(hour=23, minute=59, second=59)
            elif self.period == CostPeriod.WEEK:
                self.end_date = self.start_date + timedelta(days=7)
            elif self.period == CostPeriod.MONTH:
                self.end_date = self.start_date + timedelta(days=30)
            elif self.period == CostPeriod.YEAR:
                self.end_date = self.start_date + timedelta(days=365)
    
    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        return min(100.0, (self.used_amount / self.total_amount) * 100)
    
    @property
    def remaining_amount(self) -> float:
        """剩余金额"""
        return max(0.0, self.total_amount - self.used_amount)
    
    @property
    def is_over_budget(self) -> bool:
        """是否超预算"""
        return self.used_amount > self.total_amount


@dataclass
class CostAlert:
    """成本警报"""
    id: str
    type: str  # "budget_over", "threshold_reached", "anomaly_detected"
    message: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    amount: float = 0.0
    threshold: float = 0.0
    acknowledged: bool = False


class AICostManager(QWidget):
    """AI成本管理器"""
    
    # 信号定义
    budget_updated = pyqtSignal(object)  # 预算更新
    cost_alert_triggered = pyqtSignal(object)  # 成本警报触发
    export_completed = pyqtSignal(str, str)  # 导出完成
    settings_changed = pyqtSignal(dict)  # 设置变更
    
    def __init__(self, ai_manager: EnhancedAIManager, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.settings_manager = settings_manager
        self.cost_manager = ai_manager.cost_manager
        
        # 预算管理
        self.budgets: Dict[str, BudgetInfo] = {}
        self.current_budget: BudgetInfo = None
        
        # 成本警报
        self.alerts: List[CostAlert] = []
        
        # 统计数据
        self.cost_history: List[Dict] = []
        
        # 初始化UI
        self.setup_ui()
        self.load_settings()
        self.start_cost_monitoring()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 预算管理选项卡
        budget_tab = self.create_budget_tab()
        tab_widget.addTab(budget_tab, "预算管理")
        
        # 成本统计选项卡
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "成本统计")
        
        # 警报管理选项卡
        alerts_tab = self.create_alerts_tab()
        tab_widget.addTab(alerts_tab, "警报管理")
        
        # 设置选项卡
        settings_tab = self.create_settings_tab()
        tab_widget.addTab(settings_tab, "设置")
        
        layout.addWidget(tab_widget)
    
    def create_budget_tab(self) -> QWidget:
        """创建预算管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 预算设置组
        budget_group = QGroupBox("预算设置")
        budget_layout = QFormLayout(budget_group)
        
        # 预算金额
        self.budget_amount_input = QDoubleSpinBox()
        self.budget_amount_input.setRange(0, 1000000)
        self.budget_amount_input.setSuffix(" 元")
        self.budget_amount_input.setValue(1000)
        budget_layout.addRow("预算金额:", self.budget_amount_input)
        
        # 预算周期
        self.budget_period_combo = QComboBox()
        self.budget_period_combo.addItems(["今日", "本周", "本月", "本年", "自定义"])
        budget_layout.addRow("预算周期:", self.budget_period_combo)
        
        # 自定义日期范围
        date_range_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate())
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate().addDays(30))
        date_range_layout.addWidget(QLabel("开始:"))
        date_range_layout.addWidget(self.start_date_edit)
        date_range_layout.addWidget(QLabel("结束:"))
        date_range_layout.addWidget(self.end_date_edit)
        budget_layout.addRow("日期范围:", date_range_layout)
        
        # 设置预算按钮
        set_budget_btn = QPushButton("设置预算")
        set_budget_btn.clicked.connect(self.set_budget)
        budget_layout.addRow(set_budget_btn)
        
        layout.addWidget(budget_group)
        
        # 预算状态显示
        status_group = QGroupBox("预算状态")
        status_layout = QVBoxLayout(status_group)
        
        # 预算进度条
        self.budget_progress = QProgressBar()
        self.budget_progress.setRange(0, 100)
        self.budget_progress.setValue(0)
        status_layout.addWidget(self.budget_progress)
        
        # 预算信息标签
        self.budget_info_label = QLabel("当前预算: 未设置")
        status_layout.addWidget(self.budget_info_label)
        
        layout.addWidget(status_group)
        
        # 预算历史
        history_group = QGroupBox("预算历史")
        history_layout = QVBoxLayout(history_group)
        
        self.budget_history_table = QTableWidget()
        self.budget_history_table.setColumnCount(4)
        self.budget_history_table.setHorizontalHeaderLabels(["周期", "预算金额", "使用金额", "使用率"])
        self.budget_history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.budget_history_table)
        
        layout.addWidget(history_group)
        
        layout.addStretch()
        
        return widget
    
    def create_stats_tab(self) -> QWidget:
        """创建成本统计选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 统计周期选择
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("统计周期:"))
        
        self.stats_period_combo = QComboBox()
        self.stats_period_combo.addItems(["今日", "本周", "本月", "本年", "自定义"])
        self.stats_period_combo.currentTextChanged.connect(self.update_stats)
        period_layout.addWidget(self.stats_period_combo)
        
        period_layout.addStretch()
        layout.addLayout(period_layout)
        
        # 成本概览
        overview_group = QGroupBox("成本概览")
        overview_layout = QGridLayout(overview_group)
        
        # 总成本
        overview_layout.addWidget(QLabel("总成本:"), 0, 0)
        self.total_cost_label = QLabel("¥0.00")
        self.total_cost_label.setFont(FontScheme.FONT_SIZE_LG)
        overview_layout.addWidget(self.total_cost_label, 0, 1)
        
        # 平均成本
        overview_layout.addWidget(QLabel("平均成本:"), 1, 0)
        self.avg_cost_label = QLabel("¥0.00")
        overview_layout.addWidget(self.avg_cost_label, 1, 1)
        
        # 最高成本
        overview_layout.addWidget(QLabel("最高成本:"), 2, 0)
        self.max_cost_label = QLabel("¥0.00")
        overview_layout.addWidget(self.max_cost_label, 2, 1)
        
        # 请求次数
        overview_layout.addWidget(QLabel("请求次数:"), 0, 2)
        self.request_count_label = QLabel("0")
        overview_layout.addWidget(self.request_count_label, 0, 3)
        
        # 成功次数
        overview_layout.addWidget(QLabel("成功次数:"), 1, 2)
        self.success_count_label = QLabel("0")
        overview_layout.addWidget(self.success_count_label, 1, 3)
        
        # 失败次数
        overview_layout.addWidget(QLabel("失败次数:"), 2, 2)
        self.failure_count_label = QLabel("0")
        overview_layout.addWidget(self.failure_count_label, 2, 3)
        
        layout.addWidget(overview_group)
        
        # 模型成本分布
        model_group = QGroupBox("模型成本分布")
        model_layout = QVBoxLayout(model_group)
        
        self.model_cost_table = QTableWidget()
        self.model_cost_table.setColumnCount(4)
        self.model_cost_table.setHorizontalHeaderLabels(["模型", "请求数", "总成本", "平均成本"])
        self.model_cost_table.horizontalHeader().setStretchLastSection(True)
        model_layout.addWidget(self.model_cost_table)
        
        layout.addWidget(model_group)
        
        # 成本历史
        history_group = QGroupBox("成本历史")
        history_layout = QVBoxLayout(history_group)
        
        self.cost_history_table = QTableWidget()
        self.cost_history_table.setColumnCount(5)
        self.cost_history_table.setHorizontalHeaderLabels(["时间", "模型", "类型", "成本", "状态"])
        self.cost_history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.cost_history_table)
        
        layout.addWidget(history_group)
        
        layout.addStretch()
        
        return widget
    
    def create_alerts_tab(self) -> QWidget:
        """创建警报管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 警报设置
        settings_group = QGroupBox("警报设置")
        settings_layout = QFormLayout(settings_group)
        
        # 预算阈值
        self.budget_threshold_spin = QSpinBox()
        self.budget_threshold_spin.setRange(50, 100)
        self.budget_threshold_spin.setValue(80)
        self.budget_threshold_spin.setSuffix("%")
        settings_layout.addRow("预算使用阈值:", self.budget_threshold_spin)
        
        # 异常检测
        self.anomaly_detection_check = QCheckBox("启用异常检测")
        self.anomaly_detection_check.setChecked(True)
        settings_layout.addRow(self.anomaly_detection_check)
        
        # 邮件通知
        self.email_notification_check = QCheckBox("邮件通知")
        settings_layout.addRow(self.email_notification_check)
        
        layout.addWidget(settings_group)
        
        # 警报列表
        alerts_group = QGroupBox("警报列表")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels(["时间", "类型", "严重程度", "消息", "状态"])
        self.alerts_table.horizontalHeader().setStretchLastSection(True)
        alerts_layout.addWidget(self.alerts_table)
        
        # 警报操作按钮
        alert_buttons_layout = QHBoxLayout()
        
        acknowledge_btn = QPushButton("确认警报")
        acknowledge_btn.clicked.connect(self.acknowledge_selected_alerts)
        alert_buttons_layout.addWidget(acknowledge_btn)
        
        clear_btn = QPushButton("清除警报")
        clear_btn.clicked.connect(self.clear_alerts)
        alert_buttons_layout.addWidget(clear_btn)
        
        alert_buttons_layout.addStretch()
        alerts_layout.addLayout(alert_buttons_layout)
        
        layout.addWidget(alerts_group)
        
        layout.addStretch()
        
        return widget
    
    def create_settings_tab(self) -> QWidget:
        """创建设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 成本优化设置
        optimization_group = QGroupBox("成本优化")
        optimization_layout = QFormLayout(optimization_group)
        
        # 自动模型选择
        self.auto_model_check = QCheckBox("自动选择最优成本模型")
        self.auto_model_check.setChecked(True)
        optimization_layout.addRow(self.auto_model_check)
        
        # 成本限制
        self.cost_limit_input = QDoubleSpinBox()
        self.cost_limit_input.setRange(0, 1000000)
        self.cost_limit_input.setSuffix(" 元")
        self.cost_limit_input.setValue(100)
        optimization_layout.addRow("单次成本限制:", self.cost_limit_input)
        
        # 批量处理阈值
        self.batch_threshold_spin = QSpinBox()
        self.batch_threshold_spin.setRange(1, 100)
        self.batch_threshold_spin.setValue(10)
        optimization_layout.addRow("批量处理阈值:", self.batch_threshold_spin)
        
        layout.addWidget(optimization_group)
        
        # 数据管理
        data_group = QGroupBox("数据管理")
        data_layout = QVBoxLayout(data_group)
        
        # 数据保留期
        retention_layout = QHBoxLayout()
        retention_layout.addWidget(QLabel("数据保留期:"))
        
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(7, 365)
        self.retention_spin.setValue(30)
        self.retention_spin.setSuffix(" 天")
        retention_layout.addWidget(self.retention_spin)
        
        retention_layout.addStretch()
        data_layout.addLayout(retention_layout)
        
        # 数据操作按钮
        data_buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(self.export_data)
        data_buttons_layout.addWidget(export_btn)
        
        clear_btn = QPushButton("清除数据")
        clear_btn.clicked.connect(self.clear_data)
        data_buttons_layout.addWidget(clear_btn)
        
        data_buttons_layout.addStretch()
        data_layout.addLayout(data_buttons_layout)
        
        layout.addWidget(data_group)
        
        # 保存设置按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return widget
    
    def set_budget(self):
        """设置预算"""
        try:
            amount = self.budget_amount_input.value()
            period_text = self.budget_period_combo.currentText()
            
            # 映射周期
            period_map = {
                "今日": CostPeriod.TODAY,
                "本周": CostPeriod.WEEK,
                "本月": CostPeriod.MONTH,
                "本年": CostPeriod.YEAR,
                "自定义": CostPeriod.CUSTOM
            }
            
            period = period_map[period_text]
            
            # 创建预算
            if period == CostPeriod.CUSTOM:
                start_date = self.start_date_edit.date().toPyDate()
                end_date = self.end_date_edit.date().toPyDate()
                budget = BudgetInfo(
                    total_amount=amount,
                    period=period,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time())
                )
            else:
                budget = BudgetInfo(
                    total_amount=amount,
                    period=period
                )
            
            self.current_budget = budget
            self.budgets[period.value] = budget
            
            # 更新显示
            self.update_budget_display()
            
            # 保存设置
            self.save_settings()
            
            QMessageBox.information(self, "成功", "预算设置成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置预算失败: {str(e)}")
    
    def update_budget_display(self):
        """更新预算显示"""
        if self.current_budget:
            # 更新进度条
            usage_percentage = self.current_budget.usage_percentage
            self.budget_progress.setValue(int(usage_percentage))
            
            # 根据使用率设置颜色
            if usage_percentage >= 90:
                self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
            elif usage_percentage >= 70:
                self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
            else:
                self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            
            # 更新信息标签
            info_text = f"当前预算: ¥{self.current_budget.total_amount:.2f} | "
            info_text += f"已使用: ¥{self.current_budget.used_amount:.2f} | "
            info_text += f"剩余: ¥{self.current_budget.remaining_amount:.2f} | "
            info_text += f"使用率: {usage_percentage:.1f}%"
            
            self.budget_info_label.setText(info_text)
            
            # 检查是否需要触发警报
            self.check_budget_alerts()
    
    def check_budget_alerts(self):
        """检查预算警报"""
        if not self.current_budget:
            return
        
        threshold = self.budget_threshold_spin.value()
        usage_percentage = self.current_budget.usage_percentage
        
        # 预算超支警报
        if self.current_budget.is_over_budget:
            alert = CostAlert(
                id=f"budget_over_{int(time.time())}",
                type="budget_over",
                message=f"预算已超支 ¥{self.current_budget.used_amount - self.current_budget.total_amount:.2f}",
                severity="critical",
                timestamp=datetime.now(),
                amount=self.current_budget.used_amount,
                threshold=self.current_budget.total_amount
            )
            self.add_alert(alert)
        
        # 预算阈值警报
        elif usage_percentage >= threshold:
            alert = CostAlert(
                id=f"threshold_{int(time.time())}",
                type="threshold_reached",
                message=f"预算使用已达到 {usage_percentage:.1f}%",
                severity="high",
                timestamp=datetime.now(),
                amount=self.current_budget.used_amount,
                threshold=threshold
            )
            self.add_alert(alert)
    
    def add_alert(self, alert: CostAlert):
        """添加警报"""
        self.alerts.append(alert)
        self.update_alerts_display()
        self.cost_alert_triggered.emit(alert)
    
    def update_alerts_display(self):
        """更新警报显示"""
        self.alerts_table.setRowCount(len(self.alerts))
        
        for i, alert in enumerate(self.alerts):
            # 时间
            self.alerts_table.setItem(i, 0, QTableWidgetItem(
                alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            # 类型
            self.alerts_table.setItem(i, 1, QTableWidgetItem(alert.type))
            
            # 严重程度
            severity_item = QTableWidgetItem(alert.severity)
            if alert.severity == "critical":
                severity_item.setBackground(QColor("#F44336"))
            elif alert.severity == "high":
                severity_item.setBackground(QColor("#FF9800"))
            elif alert.severity == "medium":
                severity_item.setBackground(QColor("#2196F3"))
            else:
                severity_item.setBackground(QColor("#4CAF50"))
            
            self.alerts_table.setItem(i, 2, severity_item)
            
            # 消息
            self.alerts_table.setItem(i, 3, QTableWidgetItem(alert.message))
            
            # 状态
            status_text = "已确认" if alert.acknowledged else "未确认"
            self.alerts_table.setItem(i, 4, QTableWidgetItem(status_text))
    
    def acknowledge_selected_alerts(self):
        """确认选中的警报"""
        selected_items = self.alerts_table.selectedItems()
        if not selected_items:
            return
        
        selected_rows = set(item.row() for item in selected_items)
        
        for row in selected_rows:
            if row < len(self.alerts):
                self.alerts[row].acknowledged = True
        
        self.update_alerts_display()
    
    def clear_alerts(self):
        """清除所有警报"""
        self.alerts.clear()
        self.update_alerts_display()
    
    def update_stats(self):
        """更新统计信息"""
        # 获取统计数据
        period_text = self.stats_period_combo.currentText()
        
        # 这里应该根据选择的周期从数据库获取实际数据
        # 现在使用模拟数据
        total_cost = 156.78
        avg_cost = 12.34
        max_cost = 45.67
        request_count = 89
        success_count = 87
        failure_count = 2
        
        # 更新概览
        self.total_cost_label.setText(f"¥{total_cost:.2f}")
        self.avg_cost_label.setText(f"¥{avg_cost:.2f}")
        self.max_cost_label.setText(f"¥{max_cost:.2f}")
        self.request_count_label.setText(str(request_count))
        self.success_count_label.setText(str(success_count))
        self.failure_count_label.setText(str(failure_count))
        
        # 更新模型成本分布
        self.update_model_cost_stats()
        
        # 更新成本历史
        self.update_cost_history_display()
    
    def update_model_cost_stats(self):
        """更新模型成本统计"""
        # 模拟数据
        model_stats = [
            {"model": "通义千问", "requests": 45, "cost": 78.90, "avg_cost": 1.75},
            {"model": "文心一言", "requests": 23, "cost": 45.67, "avg_cost": 1.99},
            {"model": "智谱AI", "requests": 15, "cost": 23.45, "avg_cost": 1.56},
            {"model": "讯飞星火", "requests": 6, "cost": 8.76, "avg_cost": 1.46},
        ]
        
        self.model_cost_table.setRowCount(len(model_stats))
        
        for i, stat in enumerate(model_stats):
            self.model_cost_table.setItem(i, 0, QTableWidgetItem(stat["model"]))
            self.model_cost_table.setItem(i, 1, QTableWidgetItem(str(stat["requests"])))
            self.model_cost_table.setItem(i, 2, QTableWidgetItem(f"¥{stat['cost']:.2f}"))
            self.model_cost_table.setItem(i, 3, QTableWidgetItem(f"¥{stat['avg_cost']:.2f}"))
    
    def update_cost_history_display(self):
        """更新成本历史显示"""
        # 模拟数据
        history_data = [
            {"time": "2024-01-15 10:30:00", "model": "通义千问", "type": "文本生成", "cost": 2.34, "status": "成功"},
            {"time": "2024-01-15 10:25:00", "model": "文心一言", "type": "字幕生成", "cost": 1.89, "status": "成功"},
            {"time": "2024-01-15 10:20:00", "model": "智谱AI", "type": "场景分析", "cost": 3.45, "status": "成功"},
        ]
        
        self.cost_history_table.setRowCount(len(history_data))
        
        for i, data in enumerate(history_data):
            self.cost_history_table.setItem(i, 0, QTableWidgetItem(data["time"]))
            self.cost_history_table.setItem(i, 1, QTableWidgetItem(data["model"]))
            self.cost_history_table.setItem(i, 2, QTableWidgetItem(data["type"]))
            self.cost_history_table.setItem(i, 3, QTableWidgetItem(f"¥{data['cost']:.2f}"))
            self.cost_history_table.setItem(i, 4, QTableWidgetItem(data["status"]))
    
    def export_data(self):
        """导出数据"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出成本数据", "", "JSON文件 (*.json);;CSV文件 (*.csv)"
            )
            
            if file_path:
                # 准备导出数据
                export_data = {
                    "budgets": {
                        period: {
                            "total_amount": budget.total_amount,
                            "used_amount": budget.used_amount,
                            "period": budget.period.value,
                            "start_date": budget.start_date.isoformat() if budget.start_date else None,
                            "end_date": budget.end_date.isoformat() if budget.end_date else None,
                        }
                        for period, budget in self.budgets.items()
                    },
                    "alerts": [
                        {
                            "id": alert.id,
                            "type": alert.type,
                            "message": alert.message,
                            "severity": alert.severity,
                            "timestamp": alert.timestamp.isoformat(),
                            "amount": alert.amount,
                            "threshold": alert.threshold,
                            "acknowledged": alert.acknowledged,
                        }
                        for alert in self.alerts
                    ],
                    "cost_history": self.cost_history,
                    "export_time": datetime.now().isoformat()
                }
                
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                else:
                    # CSV导出逻辑
                    import csv
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        if self.cost_history:
                            writer = csv.DictWriter(f, fieldnames=self.cost_history[0].keys())
                            writer.writeheader()
                            writer.writerows(self.cost_history)
                
                QMessageBox.information(self, "成功", "数据导出成功")
                self.export_completed.emit(file_path, "success")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出数据失败: {str(e)}")
    
    def clear_data(self):
        """清除数据"""
        reply = QMessageBox.question(
            self, "确认", "确定要清除所有成本数据吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.budgets.clear()
            self.current_budget = None
            self.alerts.clear()
            self.cost_history.clear()
            
            # 清除显示
            self.budget_progress.setValue(0)
            self.budget_info_label.setText("当前预算: 未设置")
            self.update_alerts_display()
            self.update_stats()
            
            QMessageBox.information(self, "成功", "数据清除成功")
    
    def start_cost_monitoring(self):
        """开始成本监控"""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_costs)
        self.monitor_timer.start(60000)  # 每分钟检查一次
        
        # 立即执行一次
        self.monitor_costs()
    
    def monitor_costs(self):
        """监控成本"""
        try:
            # 更新当前预算使用情况
            if self.current_budget:
                # 从成本管理器获取实际使用情况
                current_cost = self.cost_manager.get_total_cost()
                self.current_budget.used_amount = current_cost
                self.update_budget_display()
            
            # 检查异常
            if self.anomaly_detection_check.isChecked():
                self.detect_anomalies()
            
        except Exception as e:
            print(f"成本监控错误: {e}")
    
    def detect_anomalies(self):
        """检测异常"""
        # 实现异常检测逻辑
        # 这里可以检测成本突增、异常请求模式等
        pass
    
    def load_settings(self):
        """加载设置"""
        try:
            settings = self.settings_manager.get_settings("ai_cost_manager", {})
            
            # 加载预算设置
            if "budgets" in settings:
                for period, budget_data in settings["budgets"].items():
                    budget = BudgetInfo(
                        total_amount=budget_data["total_amount"],
                        used_amount=budget_data.get("used_amount", 0.0),
                        period=CostPeriod(budget_data["period"]),
                        start_date=datetime.fromisoformat(budget_data["start_date"]) if budget_data.get("start_date") else None,
                        end_date=datetime.fromisoformat(budget_data["end_date"]) if budget_data.get("end_date") else None
                    )
                    self.budgets[period] = budget
                
                # 设置当前预算
                if self.budgets:
                    self.current_budget = list(self.budgets.values())[0]
                    self.update_budget_display()
            
            # 加载警报设置
            if "alert_threshold" in settings:
                self.budget_threshold_spin.setValue(settings["alert_threshold"])
            
            if "anomaly_detection" in settings:
                self.anomaly_detection_check.setChecked(settings["anomaly_detection"])
            
            # 加载优化设置
            if "auto_model_selection" in settings:
                self.auto_model_check.setChecked(settings["auto_model_selection"])
            
            if "cost_limit" in settings:
                self.cost_limit_input.setValue(settings["cost_limit"])
            
            if "batch_threshold" in settings:
                self.batch_threshold_spin.setValue(settings["batch_threshold"])
            
            if "data_retention_days" in settings:
                self.retention_spin.setValue(settings["data_retention_days"])
            
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            settings = {
                "budgets": {
                    period: {
                        "total_amount": budget.total_amount,
                        "used_amount": budget.used_amount,
                        "period": budget.period.value,
                        "start_date": budget.start_date.isoformat() if budget.start_date else None,
                        "end_date": budget.end_date.isoformat() if budget.end_date else None,
                    }
                    for period, budget in self.budgets.items()
                },
                "alert_threshold": self.budget_threshold_spin.value(),
                "anomaly_detection": self.anomaly_detection_check.isChecked(),
                "auto_model_selection": self.auto_model_check.isChecked(),
                "cost_limit": self.cost_limit_input.value(),
                "batch_threshold": self.batch_threshold_spin.value(),
                "data_retention_days": self.retention_spin.value(),
            }
            
            self.settings_manager.save_settings("ai_cost_manager", settings)
            self.settings_changed.emit(settings)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        return {
            "total_cost": self.cost_manager.get_total_cost(),
            "current_budget": self.current_budget,
            "budget_usage": self.current_budget.usage_percentage if self.current_budget else 0,
            "alert_count": len([a for a in self.alerts if not a.acknowledged]),
            "model_costs": self.cost_manager.get_model_costs(),
        }
    
    def closeEvent(self, event):
        """关闭事件"""
        if hasattr(self, 'monitor_timer'):
            self.monitor_timer.stop()
        event.accept()