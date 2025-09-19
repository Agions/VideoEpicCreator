#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能仪表盘组件 - 提供系统性能监控和优化界面
"""

import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QProgressBar, QComboBox, QSpinBox,
    QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QFormLayout, QCheckBox, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap

from app.core.performance_optimizer import (
    get_enhanced_performance_optimizer,
    PerformanceLevel
)
from app.core.memory_manager import get_memory_manager


class CircularProgressBar(QWidget):
    """圆形进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.max_value = 100
        self.text = ""
        self.colors = {
            'normal': QColor(76, 175, 80),
            'warning': QColor(255, 152, 0),
            'critical': QColor(244, 67, 54)
        }

    def set_value(self, value: float, text: str = ""):
        """设置值"""
        self.value = min(value, self.max_value)
        self.text = text
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算尺寸
        width = self.width()
        height = self.height()
        side = min(width, height)
        painter.translate(width / 2, height / 2)
        painter.scale(side / 200, side / 200)

        # 绘制背景圆
        pen = QPen(QColor(230, 230, 230), 8)
        painter.setPen(pen)
        painter.drawEllipse(-90, -90, 180, 180)

        # 绘制进度圆弧
        pen.setWidth(8)
        if self.value < 70:
            pen.setColor(self.colors['normal'])
        elif self.value < 90:
            pen.setColor(self.colors['warning'])
        else:
            pen.setColor(self.colors['critical'])

        painter.setPen(pen)
        painter.drawArc(-90, -90, 180, 180, 90 * 16, -int(self.value * 3.6 * 16))

        # 绘制文本
        painter.setPen(QColor(50, 50, 50))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(-50, -50, 100, 100), Qt.AlignmentFlag.AlignCenter,
                        f"{self.value:.1f}%")

        if self.text:
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(QRect(-50, 20, 100, 30), Qt.AlignmentFlag.AlignCenter, self.text)


class MemoryPoolWidget(QWidget):
    """内存池显示组件"""

    def __init__(self, pool_name: str, parent=None):
        super().__init__(parent)
        self.pool_name = pool_name
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 池名称
        name_label = QLabel(self.pool_name.replace('_', ' ').title())
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(name_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 详细信息
        self.detail_label = QLabel("0 MB / 0 MB")
        self.detail_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.detail_label)

    def update_info(self, used_mb: float, total_mb: float, block_count: int):
        """更新信息"""
        percentage = (used_mb / total_mb) * 100 if total_mb > 0 else 0
        self.progress_bar.setValue(int(percentage))
        self.detail_label.setText(f"{used_mb:.1f} MB / {total_mb:.1f} MB ({block_count} 块)")

        # 根据使用率改变颜色
        if percentage > 90:
            color = "#F44336"
        elif percentage > 70:
            color = "#FF9800"
        else:
            color = "#4CAF50"

        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)


class PerformanceMetricsWidget(QWidget):
    """性能指标显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.performance_optimizer = get_enhanced_performance_optimizer()
        self.memory_manager = get_memory_manager()
        self.setup_ui()
        self.setup_timers()

    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 实时监控选项卡
        real_time_widget = self.create_real_time_widget()
        tab_widget.addTab(real_time_widget, "实时监控")

        # 内存管理选项卡
        memory_widget = self.create_memory_widget()
        tab_widget.addTab(memory_widget, "内存管理")

        # 性能报告选项卡
        report_widget = self.create_report_widget()
        tab_widget.addTab(report_widget, "性能报告")

        # 优化设置选项卡
        settings_widget = self.create_settings_widget()
        tab_widget.addTab(settings_widget, "优化设置")

    def create_real_time_widget(self) -> QWidget:
        """创建实时监控组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 关键指标区域
        metrics_layout = QGridLayout()

        # CPU使用率
        cpu_widget = self.create_metric_card("CPU使用率", "cpu_progress")
        metrics_layout.addWidget(cpu_widget, 0, 0)

        # 内存使用率
        memory_widget = self.create_metric_card("内存使用率", "memory_progress")
        metrics_layout.addWidget(memory_widget, 0, 1)

        # 线程数
        threads_widget = self.create_metric_card("活动线程", "threads_label")
        metrics_layout.addWidget(threads_widget, 0, 2)

        # FPS
        fps_widget = self.create_metric_card("帧率", "fps_label")
        metrics_layout.addWidget(fps_widget, 1, 0)

        # UI响应时间
        response_widget = self.create_metric_card("UI响应时间", "response_label")
        metrics_layout.addWidget(response_widget, 1, 1)

        # 运行时间
        uptime_widget = self.create_metric_card("运行时间", "uptime_label")
        metrics_layout.addWidget(uptime_widget, 1, 2)

        layout.addLayout(metrics_layout)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.start_monitoring)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        self.optimize_btn = QPushButton("立即优化")
        self.optimize_btn.clicked.connect(self.optimize_now)
        control_layout.addWidget(self.optimize_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 警告日志
        log_group = QGroupBox("警告日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return widget

    def create_memory_widget(self) -> QWidget:
        """创建内存管理组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 内存池概览
        pools_group = QGroupBox("内存池概览")
        pools_layout = QGridLayout(pools_group)

        # 创建内存池组件
        self.memory_pools = {}
        pool_names = ['video_frames', 'preview_cache', 'effects_processing',
                     'ai_models', 'temp_data', 'thumbnails']

        for i, pool_name in enumerate(pool_names):
            pool_widget = MemoryPoolWidget(pool_name)
            self.memory_pools[pool_name] = pool_widget
            row = i // 3
            col = i % 3
            pools_layout.addWidget(pool_widget, row, col)

        layout.addWidget(pools_group)

        # 内存操作按钮
        memory_control_layout = QHBoxLayout()

        cleanup_btn = QPushButton("清理内存")
        cleanup_btn.clicked.connect(self.cleanup_memory)
        memory_control_layout.addWidget(cleanup_btn)

        optimize_btn = QPushButton("视频优化")
        optimize_btn.clicked.connect(self.optimize_for_video)
        memory_control_layout.addWidget(optimize_btn)

        clear_cache_btn = QPushButton("清除缓存")
        clear_cache_btn.clicked.connect(self.clear_cache)
        memory_control_layout.addWidget(clear_cache_btn)

        memory_control_layout.addStretch()
        layout.addLayout(memory_control_layout)

        # 内存详情表格
        detail_group = QGroupBox("内存详情")
        detail_layout = QVBoxLayout(detail_group)

        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(6)
        self.memory_table.setHorizontalHeaderLabels([
            "池名称", "总大小(MB)", "已用(MB)", "使用率", "块数量", "操作"
        ])
        self.memory_table.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.memory_table)

        layout.addWidget(detail_group)

        return widget

    def create_report_widget(self) -> QWidget:
        """创建性能报告组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 报告控制
        report_control_layout = QHBoxLayout()

        generate_btn = QPushButton("生成报告")
        generate_btn.clicked.connect(self.generate_report)
        report_control_layout.addWidget(generate_btn)

        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_report)
        report_control_layout.addWidget(export_btn)

        report_control_layout.addStretch()
        layout.addLayout(report_control_layout)

        # 报告内容
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)

        return widget

    def create_settings_widget(self) -> QWidget:
        """创建优化设置组件"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 性能配置文件
        self.profile_combo = QComboBox()
        self.profile_combo.addItems([
            "省电模式", "平衡模式", "高性能模式", "最高性能模式"
        ])
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        layout.addRow("性能配置:", self.profile_combo)

        # 自动清理
        self.auto_cleanup_check = QCheckBox()
        self.auto_cleanup_check.setChecked(True)
        self.auto_cleanup_check.stateChanged.connect(self.toggle_auto_cleanup)
        layout.addRow("自动清理:", self.auto_cleanup_check)

        # 清理间隔
        self.cleanup_interval_spin = QSpinBox()
        self.cleanup_interval_spin.setRange(10, 3600)
        self.cleanup_interval_spin.setValue(60)
        self.cleanup_interval_spin.setSuffix(" 秒")
        self.cleanup_interval_spin.valueChanged.connect(self.change_cleanup_interval)
        layout.addRow("清理间隔:", self.cleanup_interval_spin)

        # 内存限制
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(1024, 32768)
        self.memory_limit_spin.setValue(8192)
        self.memory_limit_spin.setSuffix(" MB")
        self.memory_limit_spin.valueChanged.connect(self.change_memory_limit)
        layout.addRow("内存限制:", self.memory_limit_spin)

        # 警告阈值
        self.warning_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.warning_threshold_slider.setRange(50, 95)
        self.warning_threshold_slider.setValue(80)
        self.warning_threshold_slider.valueChanged.connect(self.change_warning_threshold)
        layout.addRow("警告阈值:", self.warning_threshold_slider)

        self.warning_label = QLabel("80%")
        layout.addRow("", self.warning_label)

        return widget

    def create_metric_card(self, title: str, widget_name: str) -> QWidget:
        """创建指标卡片"""
        card = QWidget()
        card.setFixedHeight(120)
        layout = QVBoxLayout(card)

        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        # 指标显示
        if widget_name.endswith("_progress"):
            widget = CircularProgressBar()
        else:
            widget = QLabel("0")
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setStyleSheet("font-size: 18px; font-weight: bold;")

        setattr(self, widget_name, widget)
        layout.addWidget(widget)

        # 卡片样式
        card.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        return card

    def setup_timers(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.setInterval(1000)  # 每秒更新一次

        self.memory_update_timer = QTimer()
        self.memory_update_timer.timeout.connect(self.update_memory_info)
        self.memory_update_timer.setInterval(2000)  # 每2秒更新一次

    def start_monitoring(self):
        """开始监控"""
        self.performance_optimizer.start_monitoring()
        self.update_timer.start()
        self.memory_update_timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.add_log("性能监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.performance_optimizer.stop_monitoring()
        self.update_timer.stop()
        self.memory_update_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("性能监控已停止")

    def update_metrics(self):
        """更新性能指标"""
        try:
            monitor = self.performance_optimizer.get_monitor()
            current_metrics = monitor.get_current_metrics()

            if current_metrics:
                # 更新CPU使用率
                self.cpu_progress.set_value(current_metrics.cpu_percent, "CPU")

                # 更新内存使用率
                self.memory_progress.set_value(current_metrics.memory_percent, "Memory")

                # 更新线程数
                self.threads_label.setText(str(current_metrics.thread_count))

                # 更新FPS
                if current_metrics.fps:
                    self.fps_label.setText(f"{current_metrics.fps:.1f}")

                # 更新UI响应时间
                if current_metrics.ui_response_time:
                    self.response_label.setText(f"{current_metrics.ui_response_time:.1f}ms")

                # 更新运行时间
                uptime = time.time() - current_metrics.timestamp.timestamp() + 1
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                self.uptime_label.setText(f"{hours}h {minutes}m")

                # 检查警告
                if current_metrics.cpu_percent > 80:
                    self.add_log(f"警告: CPU使用率过高 {current_metrics.cpu_percent:.1f}%")
                if current_metrics.memory_percent > 85:
                    self.add_log(f"警告: 内存使用率过高 {current_metrics.memory_percent:.1f}%")

        except Exception as e:
            self.add_log(f"更新指标错误: {e}")

    def update_memory_info(self):
        """更新内存信息"""
        try:
            stats = self.memory_manager.get_memory_stats()

            # 更新内存池信息
            for pool_name, pool_info in stats['pools'].items():
                if pool_name in self.memory_pools:
                    self.memory_pools[pool_name].update_info(
                        pool_info['used_size_mb'],
                        pool_info['total_size_mb'],
                        pool_info['block_count']
                    )

            # 更新内存详情表格
            self.update_memory_table(stats)

        except Exception as e:
            self.add_log(f"更新内存信息错误: {e}")

    def update_memory_table(self, stats: Dict[str, Any]):
        """更新内存详情表格"""
        self.memory_table.setRowCount(len(stats['pools']))

        for row, (pool_name, pool_info) in enumerate(stats['pools'].items()):
            # 池名称
            self.memory_table.setItem(row, 0, QTableWidgetItem(pool_name.replace('_', ' ').title()))

            # 总大小
            self.memory_table.setItem(row, 1, QTableWidgetItem(f"{pool_info['total_size_mb']:.1f}"))

            # 已用大小
            self.memory_table.setItem(row, 2, QTableWidgetItem(f"{pool_info['used_size_mb']:.1f}"))

            # 使用率
            usage_item = QTableWidgetItem(f"{pool_info['usage_percent']:.1f}%")
            if pool_info['usage_percent'] > 90:
                usage_item.setBackground(QColor(244, 67, 54))
            elif pool_info['usage_percent'] > 70:
                usage_item.setBackground(QColor(255, 152, 0))
            self.memory_table.setItem(row, 3, usage_item)

            # 块数量
            self.memory_table.setItem(row, 4, QTableWidgetItem(str(pool_info['block_count'])))

            # 操作按钮
            btn = QPushButton("清理")
            btn.clicked.connect(lambda checked, p=pool_name: self.cleanup_pool(p))
            self.memory_table.setCellWidget(row, 5, btn)

    def cleanup_memory(self):
        """清理内存"""
        try:
            results = self.memory_manager.perform_cleanup()
            self.add_log(f"内存清理完成: 释放 {(results['memory_before'] - results['memory_after']) / 1024 / 1024:.2f} MB")
        except Exception as e:
            self.add_log(f"内存清理失败: {e}")

    def cleanup_pool(self, pool_name: str):
        """清理指定池"""
        try:
            pool = self.memory_manager.pools.get(pool_name)
            if pool:
                # 清理50%的空间
                target_size = pool.total_size * 0.5
                self.memory_manager._cleanup_pool(pool, target_size)
                self.add_log(f"池 {pool_name} 清理完成")
        except Exception as e:
            self.add_log(f"清理池 {pool_name} 失败: {e}")

    def optimize_for_video(self):
        """为视频处理优化"""
        try:
            self.memory_manager.optimize_for_video_processing()
            self.add_log("视频处理内存优化完成")
        except Exception as e:
            self.add_log(f"视频优化失败: {e}")

    def clear_cache(self):
        """清除缓存"""
        try:
            # 清理预览缓存和临时数据
            for pool_name in ['preview_cache', 'temp_data', 'thumbnails']:
                pool = self.memory_manager.pools.get(pool_name)
                if pool:
                    self.memory_manager._cleanup_pool(pool, 0)
            self.add_log("缓存清理完成")
        except Exception as e:
            self.add_log(f"缓存清理失败: {e}")

    def optimize_now(self):
        """立即优化"""
        try:
            results = self.performance_optimizer.optimize_system()
            self.add_log(f"系统优化完成: 释放 {results['memory_freed_mb']} MB, 清理 {results['threads_cleaned']} 个线程")
        except Exception as e:
            self.add_log(f"系统优化失败: {e}")

    def change_profile(self, profile_name: str):
        """更改性能配置文件"""
        profile_map = {
            "省电模式": "power_saver",
            "平衡模式": "balanced",
            "高性能模式": "performance",
            "最高性能模式": "maximum"
        }

        try:
            self.performance_optimizer.set_performance_profile(profile_map[profile_name])
            self.add_log(f"性能配置已切换到: {profile_name}")
        except Exception as e:
            self.add_log(f"切换配置失败: {e}")

    def toggle_auto_cleanup(self, state: int):
        """切换自动清理"""
        enabled = state == Qt.CheckState.Checked.value
        self.memory_manager.auto_cleanup_enabled = enabled
        self.add_log(f"自动清理已{'启用' if enabled else '禁用'}")

    def change_cleanup_interval(self, interval: int):
        """更改清理间隔"""
        self.memory_manager.cleanup_interval = interval
        self.add_log(f"清理间隔已设置为: {interval} 秒")

    def change_memory_limit(self, limit_mb: int):
        """更改内存限制"""
        self.memory_manager.global_memory_limit = limit_mb * 1024 * 1024
        self.add_log(f"内存限制已设置为: {limit_mb} MB")

    def change_warning_threshold(self, value: int):
        """更改警告阈值"""
        self.warning_label.setText(f"{value}%")
        threshold = value / 100.0
        self.memory_manager.warning_threshold = threshold
        self.add_log(f"警告阈值已设置为: {value}%")

    def generate_report(self):
        """生成性能报告"""
        try:
            report = self.performance_optimizer.get_enhanced_performance_report()
            memory_stats = self.memory_manager.get_memory_stats()

            report_text = f"""
性能报告 - {time.strftime('%Y-%m-%d %H:%M:%S')}
========================================

当前配置
- 性能配置: {report['current_profile']}
- 监控状态: {'启用' if report['monitoring_enabled'] else '禁用'}

系统资源
- CPU使用率: {report['current_metrics']['cpu_percent']:.1f}%
- 内存使用率: {report['current_metrics']['memory_percent']:.1f}%
- 内存使用量: {report['current_metrics']['memory_used_mb']:.1f} MB
- 平均CPU使用率: {report['average_metrics']['cpu_percent']:.1f}%
- 平均内存使用率: {report['average_metrics']['memory_percent']:.1f}%

内存池状态
"""

            for pool_name, pool_info in memory_stats['pools'].items():
                report_text += f"- {pool_name}: {pool_info['used_size_mb']:.1f}/{pool_info['total_size_mb']:.1f} MB ({pool_info['usage_percent']:.1f}%)\n"

            report_text += f"""
缓存统计
- 总缓存大小: {memory_stats['cache_stats']['total_size_mb']:.1f} MB
- 缓存数量: {memory_stats['cache_stats']['cache_count']}
- 使用率: {memory_stats['cache_stats']['usage_percent']:.1f}%

优化建议
"""

            for recommendation in report['recommendations']:
                report_text += f"- {recommendation}\n"

            self.report_text.setText(report_text)
            self.add_log("性能报告已生成")

        except Exception as e:
            self.add_log(f"生成报告失败: {e}")

    def export_report(self):
        """导出报告"""
        try:
            report_text = self.report_text.toPlainText()
            filename = f"performance_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_text)

            self.add_log(f"报告已导出到: {filename}")
        except Exception as e:
            self.add_log(f"导出报告失败: {e}")

    def add_log(self, message: str):
        """添加日志"""
        timestamp = time.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.append(log_entry)

        # 限制日志长度
        if self.log_text.document().lineCount() > 100:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 10)
            cursor.removeSelectedText()