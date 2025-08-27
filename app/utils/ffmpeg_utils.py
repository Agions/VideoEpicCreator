#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import json
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FFmpegUtils")


class FFmpegInfoWorker(QThread):
    """FFmpeg信息提取工作线程"""
    
    # 自定义信号
    info_extracted = pyqtSignal(str, dict)  # 参数: 视频路径, 元数据字典
    error_occurred = pyqtSignal(str, str)  # 参数: 视频路径, 错误信息
    
    def __init__(self, file_path, ffmpeg_path="ffmpeg"):
        """
        初始化FFmpeg信息提取工作线程
        
        参数:
            file_path: 视频文件路径
            ffmpeg_path: FFmpeg可执行文件路径
        """
        super().__init__()
        self.file_path = file_path
        self.ffmpeg_path = ffmpeg_path
        
    def run(self):
        """线程执行函数"""
        try:
            # 提取视频信息
            info = self.extract_info()
            
            if info:
                self.info_extracted.emit(self.file_path, info)
            else:
                self.error_occurred.emit(self.file_path, "无法提取视频信息")
                
        except Exception as e:
            self.error_occurred.emit(self.file_path, str(e))
            
    def extract_info(self):
        """提取视频信息"""
        ffprobe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            self.file_path
        ]
        
        try:
            # 执行ffprobe命令
            result = subprocess.run(
                ffprobe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # 解析JSON输出
            data = json.loads(result.stdout)
            
            # 提取有用的信息
            info = {}
            
            # 格式信息
            if "format" in data:
                format_info = data["format"]
                info["duration"] = int(float(format_info.get("duration", 0)) * 1000)  # 转换为毫秒
                info["size"] = int(format_info.get("size", 0))
                info["bit_rate"] = int(format_info.get("bit_rate", 0))
            
            # 流信息
            if "streams" in data:
                # 查找视频流
                for stream in data["streams"]:
                    if stream["codec_type"] == "video":
                        info["width"] = stream.get("width", 0)
                        info["height"] = stream.get("height", 0)
                        
                        # 帧率
                        fps_str = stream.get("avg_frame_rate", "0/1")
                        if "/" in fps_str:
                            num, den = map(int, fps_str.split("/"))
                            info["fps"] = round(num / max(den, 1), 2)
                        else:
                            info["fps"] = float(fps_str)
                        
                        # 编解码器
                        info["codec"] = stream.get("codec_name", "unknown")
                        break
            
            return info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe执行错误: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            logger.error(f"提取视频信息错误: {e}")
            return None


class FFmpegUtils(QObject):
    """FFmpeg工具类"""
    
    # 自定义信号
    metadata_ready = pyqtSignal(str, dict)  # 参数: 视频路径, 元数据字典
    metadata_error = pyqtSignal(str, str)  # 参数: 视频路径, 错误信息
    
    def __init__(self, ffmpeg_path="ffmpeg"):
        """
        初始化FFmpeg工具类
        
        参数:
            ffmpeg_path: FFmpeg可执行文件路径
        """
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self._check_ffmpeg()
        
        # 保存当前工作线程
        self.workers = []
        
    def extract_metadata(self, file_path):
        """
        提取视频元数据
        
        参数:
            file_path: 视频文件路径
            
        返回:
            成功启动提取进程返回True，否则返回False
        """
        if not self.ffmpeg_available:
            self.metadata_error.emit(file_path, "FFmpeg不可用")
            return False
            
        if not os.path.exists(file_path):
            self.metadata_error.emit(file_path, "文件不存在")
            return False
            
        # 创建并启动工作线程
        worker = FFmpegInfoWorker(file_path, self.ffmpeg_path)
        worker.info_extracted.connect(self.metadata_ready)
        worker.error_occurred.connect(self.metadata_error)
        
        # 保存并启动线程
        self.workers.append(worker)
        worker.start()
        
        return True
        
    def extract_metadata_sync(self, file_path):
        """
        同步提取视频元数据（直接返回结果）
        
        参数:
            file_path: 视频文件路径
            
        返回:
            成功返回元数据字典，否则返回空字典
        """
        if not self.ffmpeg_available:
            logger.error("FFmpeg不可用")
            return {}
            
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return {}
            
        # 创建工作线程实例但不作为线程运行
        worker = FFmpegInfoWorker(file_path, self.ffmpeg_path)
        try:
            return worker.extract_info() or {}
        except Exception as e:
            logger.error(f"提取元数据错误: {e}")
            return {}
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            # 执行FFmpeg版本命令
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("FFmpeg不可用，部分功能将受限")
            return False
            
    def cleanup(self):
        """清理工作线程"""
        for worker in self.workers[:]:
            if not worker.isRunning():
                self.workers.remove(worker)
                
    def stop_all(self):
        """停止所有工作线程"""
        for worker in self.workers:
            if worker.isRunning():
                worker.terminate()
                worker.wait()
                
        self.workers = [] 