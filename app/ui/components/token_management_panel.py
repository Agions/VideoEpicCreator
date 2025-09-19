#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
令牌管理面板 - 显示和管理AI令牌使用情况
集成令牌预算、优化建议和实时监控
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QSpinBox, QComboBox, QTextEdit,
    QFrame, QSplitter, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from app.ai.interfaces import ITokenManager, ITokenOptimizer
from app.ai.ai_service import AIService


class TokenManagementPanel(QWidget):
    """令牌管理面板"""

    def __init__(self, ai_service: AIService, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.token_manager = getattr(ai_service, 'token_manager', None)
        self.token_optimizer = getattr(ai_service, 'token_optimizer', None)

        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建标签页
        tab_widget = QTabWidget()

        # 概览页面
        overview_tab = self.create_overview_tab()
        tab_widget.addTab(overview_tab, "概览")

        # 预算管理页面
        budget_tab = self.create_budget_tab()
        tab_widget.addTab(budget_tab, "预算管理")

        # 优化建议页面
        optimization_tab = self.create_optimization_tab()
        tab_widget.addTab(optimization_tab, "优化建议")

        # 历史记录页面
        history_tab = self.create_history_tab()
        tab_widget.addTab(history_tab, "使用历史")

        layout.addWidget(tab_widget)

    def create_overview_tab(self) -> QWidget:
        """创建概览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 总体统计组
        stats_group = QGroupBox("令牌使用统计")
        stats_layout = QGridLayout(stats_group)

        # 统计标签
        self.total_budget_label = QLabel("总预算: 0")
        self.total_used_label = QLabel("已使用: 0")
        self.total_reserved_label = QLabel("已预留: 0")
        self.total_available_label = QLabel("可用: 0")
        self.usage_percentage_label = QLabel("使用率: 0%")

        # 进度条
        self.usage_progress = QProgressBar()
        self.usage_progress.setRange(0, 100)

        # 添加到布局
        stats_layout.addWidget(QLabel("总预算:"), 0, 0)
        stats_layout.addWidget(self.total_budget_label, 0, 1)
        stats_layout.addWidget(QLabel("已使用:"), 0, 2)
        stats_layout.addWidget(self.total_used_label, 0, 3)

        stats_layout.addWidget(QLabel("已预留:"), 1, 0)
        stats_layout.addWidget(self.total_reserved_label, 1, 1)
        stats_layout.addWidget(QLabel("可用:"), 1, 2)
        stats_layout.addWidget(self.total_available_label, 1, 3)

        stats_layout.addWidget(QLabel("使用率:"), 2, 0)
        stats_layout.addWidget(self.usage_percentage_label, 2, 1)
        stats_layout.addWidget(self.usage_progress, 2, 2, 1, 2)

        layout.addWidget(stats_group)

        # 提供商效率排名
        provider_group = QGroupBox("提供商效率排名")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_table = QTableWidget()
        self.provider_table.setColumnCount(3)
        self.provider_table.setHorizontalHeaderLabels(["提供商", "效率分数", "状态"])
        self.provider_table.horizontalHeader().setStretchLastSection(True)

        provider_layout.addWidget(self.provider_table)
        layout.addWidget(provider_group)

        # 快速操作按钮
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.create_budget_btn = QPushButton("创建预算")
        self.create_budget_btn.clicked.connect(self.create_budget_dialog)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.create_budget_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        layout.addStretch()

        return widget

    def create_budget_tab(self) -> QWidget:
        """创建预算管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预算列表
        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(6)
        self.budget_table.setHorizontalHeaderLabels([
            "预算名称", "总令牌", "已使用", "已预留", "使用率", "周期"
        ])
        self.budget_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.budget_table)

        # 预算操作
        budget_controls = QGroupBox("预算操作")
        controls_layout = QGridLayout(budget_controls)

        controls_layout.addWidget(QLabel("预算名称:"), 0, 0)
        self.budget_name_input = QTextEdit()
        self.budget_name_input.setMaximumHeight(60)
        controls_layout.addWidget(self.budget_name_input, 0, 1)

        controls_layout.addWidget(QLabel("令牌数量:"), 1, 0)
        self.token_count_input = QSpinBox()
        self.token_count_input.setRange(1000, 10000000)
        self.token_count_input.setValue(1000000)
        controls_layout.addWidget(self.token_count_input, 1, 1)

        controls_layout.addWidget(QLabel("周期:"), 2, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["daily", "weekly", "monthly", "yearly"])
        controls_layout.addWidget(self.period_combo, 2, 1)

        self.add_budget_btn = QPushButton("添加预算")
        self.add_budget_btn.clicked.connect(self.add_budget)
        controls_layout.addWidget(self.add_budget_btn, 3, 1)

        layout.addWidget(budget_controls)

        return widget

    def create_optimization_tab(self) -> QWidget:
        """创建优化建议标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 优化设置
        settings_group = QGroupBox("优化设置")
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel("优化策略:"), 0, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["conservative", "balanced", "aggressive"])
        self.strategy_combo.currentTextChanged.connect(self.change_optimization_strategy)
        settings_layout.addWidget(self.strategy_combo, 0, 1)

        layout.addWidget(settings_group)

        # 优化建议
        suggestions_group = QGroupBox("优化建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        suggestions_layout.addWidget(self.suggestions_text)

        layout.addWidget(suggestions_group)

        # 优化统计
        stats_group = QGroupBox("优化统计")
        stats_layout = QGridLayout(stats_group)

        self.total_optimized_label = QLabel("总优化次数: 0")
        self.total_saved_label = QLabel("总节省令牌: 0")
        self.cache_hit_rate_label = QLabel("缓存命中率: 0%")

        stats_layout.addWidget(self.total_optimized_label, 0, 0)
        stats_layout.addWidget(self.total_saved_label, 0, 1)
        stats_layout.addWidget(self.cache_hit_rate_label, 1, 0, 1, 2)

        layout.addWidget(stats_group)

        return widget

    def create_history_tab(self) -> QWidget:
        """创建使用历史标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "提供商", "任务类型", "令牌使用", "成本"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.history_table)

        return widget

    def setup_timers(self):
        """设置定时器"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # 30秒刷新一次

        # 初始刷新
        self.refresh_data()

    def refresh_data(self):
        """刷新数据"""
        if not self.token_manager:
            return

        try:
            # 更新概览数据
            self.update_overview()

            # 更新预算列表
            self.update_budget_list()

            # 更新优化建议
            self.update_optimization_suggestions()

            # 更新历史记录
            self.update_history()

        except Exception as e:
            print(f"刷新令牌数据失败: {e}")

    def update_overview(self):
        """更新概览数据"""
        try:
            stats = self.token_manager.get_token_budget_status()

            # 更新统计标签
            self.total_budget_label.setText(f"{stats['total_budget']:,}")
            self.total_used_label.setText(f"{stats['total_used']:,}")
            self.total_reserved_label.setText(f"{stats['total_reserved']:,}")
            self.total_available_label.setText(f"{stats['total_available']:,}")

            usage_percentage = stats['usage_percentage']
            self.usage_percentage_label.setText(f"{usage_percentage:.1f}%")
            self.usage_progress.setValue(int(usage_percentage))

            # 更新颜色
            if usage_percentage >= 90:
                self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            elif usage_percentage >= 70:
                self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")

            # 更新提供商效率排名
            self.update_provider_ranking()

        except Exception as e:
            print(f"更新概览失败: {e}")

    def update_provider_ranking(self):
        """更新提供商效率排名"""
        try:
            rankings = self.token_manager.get_provider_efficiency_ranking()

            self.provider_table.setRowCount(len(rankings))

            for i, (provider, efficiency) in enumerate(rankings):
                self.provider_table.setItem(i, 0, QTableWidgetItem(provider))
                self.provider_table.setItem(i, 1, QTableWidgetItem(f"{efficiency:.2f}"))

                # 状态指示
                status_item = QTableWidgetItem("优秀")
                status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                self.provider_table.setItem(i, 2, status_item)

        except Exception as e:
            print(f"更新提供商排名失败: {e}")

    def update_budget_list(self):
        """更新预算列表"""
        try:
            stats = self.token_manager.get_token_budget_status()
            budgets = stats.get('budgets', {})

            self.budget_table.setRowCount(len(budgets))

            for i, (name, budget) in enumerate(budgets.items()):
                self.budget_table.setItem(i, 0, QTableWidgetItem(name))
                self.budget_table.setItem(i, 1, QTableWidgetItem(f"{budget['total_tokens']:,}"))
                self.budget_table.setItem(i, 2, QTableWidgetItem(f"{budget['used_tokens']:,}"))
                self.budget_table.setItem(i, 3, QTableWidgetItem(f"{budget['reserved_tokens']:,}"))

                if budget['total_tokens'] > 0:
                    usage_rate = (budget['used_tokens'] + budget['reserved_tokens']) / budget['total_tokens'] * 100
                else:
                    usage_rate = 0

                rate_item = QTableWidgetItem(f"{usage_rate:.1f}%")
                if usage_rate >= 90:
                    rate_item.setBackground(QColor(255, 200, 200))  # 浅红色
                elif usage_rate >= 70:
                    rate_item.setBackground(QColor(255, 255, 200))  # 浅黄色

                self.budget_table.setItem(i, 4, rate_item)
                self.budget_table.setItem(i, 5, QTableWidgetItem(budget['period']))

        except Exception as e:
            print(f"更新预算列表失败: {e}")

    def update_optimization_suggestions(self):
        """更新优化建议"""
        try:
            if hasattr(self.ai_service, 'get_token_optimization_suggestions'):
                suggestions = self.ai_service.get_token_optimization_suggestions()

                if suggestions:
                    suggestions_text = ""
                    for suggestion in suggestions:
                        suggestions_text += f"• {suggestion.get('message', '无描述')}\n"
                        if 'potential_savings' in suggestion:
                            suggestions_text += f"  预计节省: {suggestion['potential_savings']:.0f} tokens\n"
                        suggestions_text += "\n"

                    self.suggestions_text.setText(suggestions_text)
                else:
                    self.suggestions_text.setText("暂无优化建议")

                # 更新优化统计
                stats = self.ai_service.get_token_management_stats()
                if 'optimization' in stats:
                    opt_stats = stats['optimization']
                    self.total_optimized_label.setText(f"总优化次数: {opt_stats.get('total_optimized', 0)}")
                    self.total_saved_label.setText(f"总节省令牌: {opt_stats.get('total_saved_tokens', 0):,}")

                    cache_hit_rate = stats.get('cache_hit_rate', 0)
                    self.cache_hit_rate_label.setText(f"缓存命中率: {cache_hit_rate:.1%}")

        except Exception as e:
            print(f"更新优化建议失败: {e}")

    def update_history(self):
        """更新历史记录"""
        try:
            if hasattr(self.token_manager, 'get_usage_summary'):
                summary = self.token_manager.get_usage_summary()
                provider_stats = summary.get('provider_stats', {})

                self.history_table.setRowCount(len(provider_stats))

                for i, (provider, stats) in enumerate(provider_stats.items()):
                    self.history_table.setItem(i, 0, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
                    self.history_table.setItem(i, 1, QTableWidgetItem(provider))
                    self.history_table.setItem(i, 2, QTableWidgetItem("综合"))
                    self.history_table.setItem(i, 3, QTableWidgetItem(f"{stats['tokens']:,}"))
                    self.history_table.setItem(i, 4, QTableWidgetItem(f"¥{stats['cost']:.2f}"))

        except Exception as e:
            print(f"更新历史记录失败: {e}")

    def create_budget_dialog(self):
        """创建预算对话框"""
        # 简单实现，可以扩展为完整的对话框
        QMessageBox.information(self, "创建预算", "请在'预算管理'标签页中创建新预算")

    def add_budget(self):
        """添加新预算"""
        try:
            name = self.budget_name_input.toPlainText().strip()
            tokens = self.token_count_input.value()
            period = self.period_combo.currentText()

            if not name:
                QMessageBox.warning(self, "错误", "请输入预算名称")
                return

            if self.token_manager:
                self.token_manager.create_budget(name, tokens, period)

                # 清空输入
                self.budget_name_input.clear()
                self.token_count_input.setValue(1000000)

                # 刷新数据
                self.refresh_data()

                QMessageBox.information(self, "成功", f"预算 '{name}' 创建成功")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建预算失败: {e}")

    def change_optimization_strategy(self, strategy: str):
        """更改优化策略"""
        try:
            if hasattr(self.ai_service, 'set_optimization_strategy'):
                success = self.ai_service.set_optimization_strategy(strategy)
                if success:
                    QMessageBox.information(self, "成功", f"优化策略已更改为: {strategy}")
                else:
                    QMessageBox.warning(self, "警告", "更改优化策略失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"更改优化策略失败: {e}")