#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级批量处理器 - 专业的视频批量处理和任务管理
"""

import os
import subprocess
import json
import time
import logging
import threading
import queue
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import psutil
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchTaskType(Enum):
    """批量任务类型"""
    COMPRESS = "compress"
    CONVERT = "convert"
    OPTIMIZE = "optimize"
    RESIZE = "resize"
    WATERMARK = "watermark"
    EXTRACT_FRAMES = "extract_frames"
    GENERATE_THUMBNAILS = "generate_thumbnails"
    ANALYZE = "analyze"
    STABILIZE = "stabilize"
    COLOR_CORRECT = "color_correct"
    DENOISE = "denoise"
    UPSCALE = "upscale"
    CUSTOM = "custom"


class BatchPriority(Enum):
    """批量任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class BatchStatus(Enum):
    """批量任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class BatchTask:
    """批量任务"""
    task_id: str
    task_type: BatchTaskType
    input_path: str
    output_path: str
    params: Dict[str, Any]
    priority: BatchPriority = BatchPriority.NORMAL
    status: BatchStatus = BatchStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    processing_time: float = 0.0
    file_size: int = 0
    output_file_size: int = 0
    error_message: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    
    def __lt__(self, other):
        """优先级队列排序"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


@dataclass
class BatchJob:
    """批量任务"""
    job_id: str
    name: str
    description: str
    tasks: List[BatchTask]
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: BatchStatus = BatchStatus.PENDING
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    processing_time: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.total_tasks = len(self.tasks)


@dataclass
class BatchConfig:
    """批量处理配置"""
    max_concurrent_tasks: int = 4
    max_workers_per_task: int = 2
    task_timeout: int = 3600  # 秒
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    progress_update_interval: int = 5  # 秒
    memory_limit_mb: int = 8192  # MB
    disk_space_warning_mb: int = 1024  # MB
    temp_dir: str = "/tmp/batch_processor"
    log_enabled: bool = True
    log_dir: str = "/tmp/batch_processor/logs"
    result_dir: str = "/tmp/batch_processor/results"
    cleanup_enabled: bool = True
    cleanup_days: int = 7


@dataclass
class BatchResult:
    """批量处理结果"""
    job_id: str
    success: bool
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    processing_time: float
    results: List[BatchTask] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    output_dir: Optional[str] = None
    log_file: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        
        # 任务队列
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, BatchTask] = {}
        self.completed_tasks: List[BatchTask] = []
        
        # 作业管理
        self.jobs: Dict[str, BatchJob] = {}
        self.job_lock = threading.Lock()
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_concurrent_tasks)
        self.process_pool = ProcessPoolExecutor(max_workers=self.config.max_workers_per_task)
        
        # 状态管理
        self.running = False
        self.paused = False
        self.shutdown_requested = False
        
        # 统计信息
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_processing_time": 0.0,
            "average_task_time": 0.0,
            "success_rate": 0.0
        }
        
        # 监控和日志
        self.monitor_thread = None
        self.progress_thread = None
        self.cleanup_thread = None
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # 初始化
        self._initialize_directories()
        self._start_monitoring()
        
        logger.info("批量处理器初始化完成")
    
    def _initialize_directories(self):
        """初始化目录结构"""
        directories = [
            self.config.temp_dir,
            self.config.log_dir,
            self.config.result_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        logger.info(f"初始化目录: {directories}")
    
    def _start_monitoring(self):
        """启动监控线程"""
        self.running = True
        
        # 启动任务处理线程
        for i in range(self.config.max_concurrent_tasks):
            worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name=f"BatchWorker-{i}")
            worker_thread.start()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # 启动进度更新线程
        self.progress_thread = threading.Thread(target=self._progress_loop, daemon=True)
        self.progress_thread.start()
        
        # 启动清理线程
        if self.config.cleanup_enabled:
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
        
        logger.info("监控线程已启动")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running and not self.shutdown_requested:
            try:
                if self.paused:
                    time.sleep(1)
                    continue
                
                # 获取任务
                task = self.task_queue.get(timeout=1)
                if task is None:  # 停止信号
                    break
                
                # 检查内存使用
                if not self._check_memory_usage():
                    logger.warning("内存使用过高，延迟处理任务")
                    self.task_queue.put(task)
                    time.sleep(5)
                    continue
                
                # 处理任务
                self._process_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {e}")
                time.sleep(5)
    
    def _process_task(self, task: BatchTask):
        """处理单个任务"""
        start_time = time.time()
        
        try:
            # 更新任务状态
            task.status = BatchStatus.RUNNING
            task.started_at = start_time
            self.active_tasks[task.task_id] = task
            
            # 检查依赖
            if not self._check_dependencies(task):
                task.status = BatchStatus.FAILED
                task.error_message = "依赖任务未完成"
                return
            
            # 获取输入文件大小
            if os.path.exists(task.input_path):
                task.file_size = os.path.getsize(task.input_path)
            
            logger.info(f"开始处理任务: {task.task_id} - {task.task_type.value}")
            
            # 根据任务类型执行处理
            result = self._execute_task(task)
            
            # 更新任务状态
            task.completed_at = time.time()
            task.processing_time = task.completed_at - task.started_at
            
            if result["success"]:
                task.status = BatchStatus.COMPLETED
                if os.path.exists(task.output_path):
                    task.output_file_size = os.path.getsize(task.output_path)
                
                # 更新统计
                self.stats["completed_tasks"] += 1
                self.stats["total_processing_time"] += task.processing_time
                
                logger.info(f"任务完成: {task.task_id}, 耗时: {task.processing_time:.2f}s")
            else:
                task.status = BatchStatus.FAILED
                task.error_message = result.get("error", "未知错误")
                
                # 重试逻辑
                if self.config.retry_enabled and task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = BatchStatus.PENDING
                    task.created_at = time.time() + self.config.retry_delay
                    self.task_queue.put(task)
                    logger.info(f"任务重试: {task.task_id}, 重试次数: {task.retry_count}")
                else:
                    self.stats["failed_tasks"] += 1
                    logger.error(f"任务失败: {task.task_id}, 错误: {task.error_message}")
            
            # 更新作业状态
            self._update_job_status(task)
            
            # 移动到已完成列表
            self.completed_tasks.append(task)
            self.active_tasks.pop(task.task_id, None)
            
        except Exception as e:
            task.status = BatchStatus.FAILED
            task.error_message = str(e)
            task.completed_at = time.time()
            task.processing_time = task.completed_at - task.started_at
            
            self.stats["failed_tasks"] += 1
            logger.error(f"任务处理异常: {task.task_id}, 错误: {e}")
            
            # 更新作业状态
            self._update_job_status(task)
            
            # 移动到已完成列表
            self.completed_tasks.append(task)
            self.active_tasks.pop(task.task_id, None)
    
    def _execute_task(self, task: BatchTask) -> Dict[str, Any]:
        """执行任务"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(task.output_path), exist_ok=True)
            
            # 根据任务类型执行相应操作
            if task.task_type == BatchTaskType.COMPRESS:
                return self._compress_video(task)
            elif task.task_type == BatchTaskType.CONVERT:
                return self._convert_video(task)
            elif task.task_type == BatchTaskType.OPTIMIZE:
                return self._optimize_video(task)
            elif task.task_type == BatchTaskType.RESIZE:
                return self._resize_video(task)
            elif task.task_type == BatchTaskType.WATERMARK:
                return self._add_watermark(task)
            elif task.task_type == BatchTaskType.EXTRACT_FRAMES:
                return self._extract_frames(task)
            elif task.task_type == BatchTaskType.GENERATE_THUMBNAILS:
                return self._generate_thumbnails(task)
            elif task.task_type == BatchTaskType.ANALYZE:
                return self._analyze_video(task)
            elif task.task_type == BatchTaskType.STABILIZE:
                return self._stabilize_video(task)
            elif task.task_type == BatchTaskType.COLOR_CORRECT:
                return self._color_correct_video(task)
            elif task.task_type == BatchTaskType.DENOISE:
                return self._denoise_video(task)
            elif task.task_type == BatchTaskType.UPSCALE:
                return self._upscale_video(task)
            elif task.task_type == BatchTaskType.CUSTOM:
                return self._execute_custom_task(task)
            else:
                return {"success": False, "error": f"不支持的任务类型: {task.task_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _compress_video(self, task: BatchTask) -> Dict[str, Any]:
        """压缩视频"""
        try:
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-c:v", "libx264",
                "-crf", str(task.params.get("crf", 23)),
                "-preset", task.params.get("preset", "medium"),
                "-c:a", "aac",
                "-b:a", f"{task.params.get('audio_bitrate', 128)}k",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "压缩超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_video(self, task: BatchTask) -> Dict[str, Any]:
        """转换视频格式"""
        try:
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-c:v", task.params.get("video_codec", "libx264"),
                "-c:a", task.params.get("audio_codec", "aac"),
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "转换超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _optimize_video(self, task: BatchTask) -> Dict[str, Any]:
        """优化视频"""
        try:
            # 构建优化命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-c:v", "libx264",
                "-crf", str(task.params.get("crf", 23)),
                "-preset", "slow",
                "-tune", "film",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "优化超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _resize_video(self, task: BatchTask) -> Dict[str, Any]:
        """调整视频尺寸"""
        try:
            width = task.params.get("width", 1920)
            height = task.params.get("height", 1080)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", f"scale={width}:{height}",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "调整尺寸超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_watermark(self, task: BatchTask) -> Dict[str, Any]:
        """添加水印"""
        try:
            watermark_path = task.params.get("watermark_path")
            if not watermark_path or not os.path.exists(watermark_path):
                return {"success": False, "error": "水印文件不存在"}
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-i", watermark_path,
                "-filter_complex", "overlay=10:10",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "添加水印超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_frames(self, task: BatchTask) -> Dict[str, Any]:
        """提取视频帧"""
        try:
            frame_rate = task.params.get("frame_rate", 1)
            output_dir = task.output_path
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", f"fps={frame_rate}",
                os.path.join(output_dir, "frame_%04d.jpg")
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "提取帧超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_thumbnails(self, task: BatchTask) -> Dict[str, Any]:
        """生成缩略图"""
        try:
            count = task.params.get("count", 5)
            size = task.params.get("size", "320x180")
            output_dir = task.output_path
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取视频时长
            cmd = ["ffprobe", "-v", "quiet", "-show_format", "-print_format", "json", task.input_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            
            # 生成缩略图
            for i in range(count):
                timestamp = (duration / (count + 1)) * (i + 1)
                output_path = os.path.join(output_dir, f"thumbnail_{i:03d}.jpg")
                
                cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", task.input_path,
                    "-vframes", "1",
                    "-vf", f"scale={size}",
                    "-y", output_path
                ]
                
                subprocess.run(cmd, capture_output=True, text=True)
            
            return {"success": True}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _analyze_video(self, task: BatchTask) -> Dict[str, Any]:
        """分析视频"""
        try:
            # 构建FFprobe命令
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                task.input_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 保存分析结果
                with open(task.output_path, 'w') as f:
                    f.write(result.stdout)
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "分析超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _stabilize_video(self, task: BatchTask) -> Dict[str, Any]:
        """稳定视频"""
        try:
            # 构建FFmpeg命令（简化版）
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", "deshake=rx=64:ry=64:edge=1:blocksize=32",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "稳定超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _color_correct_video(self, task: BatchTask) -> Dict[str, Any]:
        """色彩校正"""
        try:
            brightness = task.params.get("brightness", 0)
            contrast = task.params.get("contrast", 1.0)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", f"eq=brightness={brightness}:contrast={contrast}",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "色彩校正超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _denoise_video(self, task: BatchTask) -> Dict[str, Any]:
        """视频降噪"""
        try:
            strength = task.params.get("strength", 5)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", f"hqdn3d=luma_spatial={strength}:chroma_spatial={strength}",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "降噪超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _upscale_video(self, task: BatchTask) -> Dict[str, Any]:
        """视频放大"""
        try:
            scale_factor = task.params.get("scale_factor", 2.0)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", task.input_path,
                "-vf", f"scale=iw*{scale_factor}:ih*{scale_factor}",
                "-c:a", "copy",
                "-y", task.output_path
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "放大超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_custom_task(self, task: BatchTask) -> Dict[str, Any]:
        """执行自定义任务"""
        try:
            # 获取自定义命令
            custom_command = task.params.get("command", [])
            if not custom_command:
                return {"success": False, "error": "自定义任务缺少命令"}
            
            # 替换占位符
            command = []
            for cmd_part in custom_command:
                cmd_part = cmd_part.replace("{input}", task.input_path)
                cmd_part = cmd_part.replace("{output}", task.output_path)
                command.append(cmd_part)
            
            # 执行命令
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.config.task_timeout)
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "自定义任务超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_dependencies(self, task: BatchTask) -> bool:
        """检查任务依赖"""
        for dep_task_id in task.dependencies:
            # 检查依赖任务是否完成
            dep_completed = any(
                t.task_id == dep_task_id and t.status == BatchStatus.COMPLETED
                for t in self.completed_tasks
            )
            if not dep_completed:
                return False
        return True
    
    def _check_memory_usage(self) -> bool:
        """检查内存使用"""
        memory = psutil.virtual_memory()
        return memory.percent < 90
    
    def _update_job_status(self, task: BatchTask):
        """更新作业状态"""
        with self.job_lock:
            # 查找对应的作业
            for job in self.jobs.values():
                for job_task in job.tasks:
                    if job_task.task_id == task.task_id:
                        # 更新作业统计
                        if task.status == BatchStatus.COMPLETED:
                            job.completed_tasks += 1
                        elif task.status == BatchStatus.FAILED:
                            job.failed_tasks += 1
                        
                        # 更新作业状态
                        if job.completed_tasks + job.failed_tasks == job.total_tasks:
                            job.status = BatchStatus.COMPLETED if job.failed_tasks == 0 else BatchStatus.FAILED
                            job.completed_at = time.time()
                            job.processing_time = job.completed_at - job.started_at if job.started_at else 0
                            
                            # 更新统计
                            self.stats["completed_jobs"] += 1
                            if job.failed_tasks > 0:
                                self.stats["failed_jobs"] += 1
                        
                        break
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running and not self.shutdown_requested:
            try:
                # 检查系统资源
                self._check_system_resources()
                
                # 检查任务超时
                self._check_task_timeouts()
                
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(60)
    
    def _progress_loop(self):
        """进度更新循环"""
        while self.running and not self.shutdown_requested:
            try:
                # 更新进度
                if self.progress_callback:
                    progress = self._get_overall_progress()
                    self.progress_callback(progress)
                
                time.sleep(self.config.progress_update_interval)
                
            except Exception as e:
                logger.error(f"进度更新错误: {e}")
                time.sleep(10)
    
    def _cleanup_loop(self):
        """清理循环"""
        while self.running and not self.shutdown_requested:
            try:
                # 清理临时文件
                self._cleanup_temp_files()
                
                # 清理日志文件
                self._cleanup_log_files()
                
                time.sleep(3600)  # 每小时清理一次
                
            except Exception as e:
                logger.error(f"清理循环错误: {e}")
                time.sleep(3600)
    
    def _check_system_resources(self):
        """检查系统资源"""
        # 检查内存
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            logger.warning(f"内存使用率过高: {memory.percent}%")
        
        # 检查磁盘空间
        disk = psutil.disk_usage('/')
        if disk.free < self.config.disk_space_warning_mb * 1024 * 1024:
            logger.warning(f"磁盘空间不足: {disk.free / (1024*1024*1024):.2f}GB")
        
        # 检查CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            logger.warning(f"CPU使用率过高: {cpu_percent}%")
    
    def _check_task_timeouts(self):
        """检查任务超时"""
        current_time = time.time()
        
        for task_id, task in list(self.active_tasks.items()):
            if task.started_at and current_time - task.started_at > self.config.task_timeout:
                task.status = BatchStatus.FAILED
                task.error_message = "任务超时"
                task.completed_at = current_time
                task.processing_time = task.completed_at - task.started_at
                
                self.stats["failed_tasks"] += 1
                logger.warning(f"任务超时: {task_id}")
                
                # 更新作业状态
                self._update_job_status(task)
                
                # 移动到已完成列表
                self.completed_tasks.append(task)
                self.active_tasks.pop(task_id, None)
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_dir = Path(self.config.temp_dir)
            current_time = time.time()
            
            # 清理超过1天的临时文件
            for file_path in temp_dir.glob("**/*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 86400:  # 1天
                        file_path.unlink()
                        logger.debug(f"清理临时文件: {file_path}")
                        
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def _cleanup_log_files(self):
        """清理日志文件"""
        try:
            log_dir = Path(self.config.log_dir)
            current_time = time.time()
            
            # 清理超过指定天数的日志文件
            for file_path in log_dir.glob("*.log"):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > self.config.cleanup_days * 86400:
                    file_path.unlink()
                    logger.debug(f"清理日志文件: {file_path}")
                    
        except Exception as e:
            logger.error(f"清理日志文件失败: {e}")
    
    def _get_overall_progress(self) -> Dict[str, Any]:
        """获取总体进度"""
        total_tasks = len(self.completed_tasks) + len(self.active_tasks) + self.task_queue.qsize()
        completed_tasks = len([t for t in self.completed_tasks if t.status == BatchStatus.COMPLETED])
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "active_tasks": len(self.active_tasks),
            "pending_tasks": self.task_queue.qsize(),
            "progress_percent": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "active_jobs": len([j for j in self.jobs.values() if j.status == BatchStatus.RUNNING]),
            "completed_jobs": len([j for j in self.jobs.values() if j.status == BatchStatus.COMPLETED])
        }
    
    def create_batch_job(self, name: str, description: str, tasks: List[BatchTask], 
                        config: Dict[str, Any] = None) -> str:
        """创建批量作业"""
        job_id = f"batch_{int(time.time() * 1000)}"
        
        job = BatchJob(
            job_id=job_id,
            name=name,
            description=description,
            tasks=tasks,
            config=config or {}
        )
        
        with self.job_lock:
            self.jobs[job_id] = job
        
        # 将任务添加到队列
        for task in tasks:
            self.task_queue.put(task)
        
        self.stats["total_jobs"] += 1
        self.stats["total_tasks"] += len(tasks)
        
        logger.info(f"创建批量作业: {job_id}, 任务数: {len(tasks)}")
        
        return job_id
    
    def add_task_to_queue(self, task: BatchTask):
        """添加任务到队列"""
        self.task_queue.put(task)
        self.stats["total_tasks"] += 1
        logger.info(f"添加任务到队列: {task.task_id}")
    
    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """获取作业状态"""
        with self.job_lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[BatchJob]:
        """获取所有作业"""
        with self.job_lock:
            return list(self.jobs.values())
    
    def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        with self.job_lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = BatchStatus.CANCELLED
                job.completed_at = time.time()
                
                # 取消队列中的任务
                # 注意：这是一个简化的实现，实际需要更复杂的取消机制
                logger.info(f"已取消作业: {job_id}")
                return True
            return False
    
    def pause_processing(self):
        """暂停处理"""
        self.paused = True
        logger.info("批量处理已暂停")
    
    def resume_processing(self):
        """恢复处理"""
        self.paused = False
        logger.info("批量处理已恢复")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        # 计算成功率
        total = stats["total_tasks"]
        if total > 0:
            stats["success_rate"] = stats["completed_tasks"] / total
        else:
            stats["success_rate"] = 0.0
        
        # 计算平均任务时间
        if stats["completed_tasks"] > 0:
            stats["average_task_time"] = stats["total_processing_time"] / stats["completed_tasks"]
        else:
            stats["average_task_time"] = 0.0
        
        return stats
    
    def get_active_tasks(self) -> List[BatchTask]:
        """获取活跃任务"""
        return list(self.active_tasks.values())
    
    def get_completed_tasks(self, limit: int = 100) -> List[BatchTask]:
        """获取已完成的任务"""
        return self.completed_tasks[-limit:]
    
    def set_callbacks(self, progress_callback=None, completion_callback=None, error_callback=None):
        """设置回调函数"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
    
    def generate_report(self, job_id: str) -> Dict[str, Any]:
        """生成作业报告"""
        job = self.get_job_status(job_id)
        if not job:
            return {"error": "作业不存在"}
        
        report = {
            "job_id": job.job_id,
            "name": job.name,
            "description": job.description,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "status": job.status.value,
            "total_tasks": job.total_tasks,
            "completed_tasks": job.completed_tasks,
            "failed_tasks": job.failed_tasks,
            "processing_time": job.processing_time,
            "success_rate": (job.completed_tasks / job.total_tasks * 100) if job.total_tasks > 0 else 0,
            "tasks": []
        }
        
        # 添加任务详情
        for task in job.tasks:
            task_info = {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": task.status.value,
                "input_path": task.input_path,
                "output_path": task.output_path,
                "processing_time": task.processing_time,
                "file_size": task.file_size,
                "output_file_size": task.output_file_size,
                "error_message": task.error_message
            }
            report["tasks"].append(task_info)
        
        return report
    
    def export_results(self, job_id: str, output_dir: str = None) -> str:
        """导出结果"""
        if not output_dir:
            output_dir = self.config.result_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成报告
        report = self.generate_report(job_id)
        
        # 保存报告
        report_path = os.path.join(output_dir, f"job_{job_id}_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 复制输出文件
        job = self.get_job_status(job_id)
        if job:
            job_output_dir = os.path.join(output_dir, f"job_{job_id}_outputs")
            os.makedirs(job_output_dir, exist_ok=True)
            
            for task in job.tasks:
                if task.status == BatchStatus.COMPLETED and os.path.exists(task.output_path):
                    try:
                        shutil.copy2(task.output_path, job_output_dir)
                    except Exception as e:
                        logger.error(f"复制输出文件失败: {e}")
        
        logger.info(f"结果已导出到: {output_dir}")
        return output_dir
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理批量处理器资源")
        
        # 请求关闭
        self.shutdown_requested = True
        self.running = False
        
        # 停止工作线程
        for i in range(self.config.max_concurrent_tasks):
            self.task_queue.put(None)
        
        # 等待线程结束
        time.sleep(2)
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        # 清理临时文件
        if self.config.cleanup_enabled:
            self._cleanup_temp_files()
            self._cleanup_log_files()
        
        logger.info("批量处理器资源清理完成")