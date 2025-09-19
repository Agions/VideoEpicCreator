#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import subprocess
import tempfile
from pathlib import Path
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class ThumbnailGenerationWorker(QThread):
    """缩略图生成工作线程"""

    # 自定义信号
    thumbnail_generated = pyqtSignal(str, str)  # 参数: 视频路径, 缩略图路径
    error_occurred = pyqtSignal(str, str)  # 参数: 视频路径, 错误信息
    progress_updated = pyqtSignal(int)  # 进度更新信号

    def __init__(self, video_path, output_path, time_pos=None, size=(320, 180)):
        """
        初始化缩略图生成工作线程

        参数:
            video_path: 视频文件路径
            output_path: 输出缩略图路径
            time_pos: 截取时间点(秒)，None则自动选取合适的帧
            size: 缩略图尺寸 (宽, 高)
        """
        super().__init__()
        self.video_path = video_path
        self.output_path = output_path
        self.time_pos = time_pos
        self.size = size
        self.stopped = False

    def run(self):
        """线程执行函数"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            # 生成缩略图
            if self.time_pos is not None:
                # 使用指定时间点生成缩略图
                success = self._generate_at_position()
            else:
                # 自动选择合适的帧生成缩略图
                success = self._generate_auto_frame()

            if success:
                self.thumbnail_generated.emit(self.video_path, self.output_path)
            else:
                self.error_occurred.emit(self.video_path, "缩略图生成失败")

        except Exception as e:
            self.error_occurred.emit(self.video_path, str(e))

    def stop(self):
        """停止线程"""
        self.stopped = True

    def _generate_at_position(self):
        """在指定时间点生成缩略图"""
        try:
            # 使用OpenCV提取视频帧
            cap = cv2.VideoCapture(self.video_path)

            # 检查视频是否成功打开
            if not cap.isOpened():
                raise Exception("无法打开视频文件")

            # 获取视频帧率和总帧数
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 计算指定时间的帧位置
            frame_pos = int(self.time_pos * fps)

            # 确保帧位置不超出范围
            frame_pos = min(frame_pos, total_frames - 1)
            frame_pos = max(0, frame_pos)

            # 设置读取位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

            # 读取指定位置的帧
            ret, frame = cap.read()

            # 释放视频对象
            cap.release()

            if ret:
                # 调整大小
                frame = cv2.resize(frame, self.size)

                # 保存缩略图
                cv2.imwrite(self.output_path, frame)
                return True
            else:
                return False

        except Exception as e:
            print(f"缩略图生成错误: {e}")
            return False

    def _generate_auto_frame(self):
        """自动选择合适的帧生成缩略图"""
        try:
            # 使用OpenCV提取视频帧
            cap = cv2.VideoCapture(self.video_path)

            # 检查视频是否成功打开
            if not cap.isOpened():
                raise Exception("无法打开视频文件")

            # 获取视频总帧数
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 如果是短视频，取前30%位置的帧
            # 否则在10%-30%范围内寻找有代表性的帧
            if total_frames <= 150:  # 约5秒@30fps
                target_pos = int(total_frames * 0.3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_pos)
                ret, frame = cap.read()

                if ret:
                    # 调整大小
                    frame = cv2.resize(frame, self.size)
                    # 保存缩略图
                    cv2.imwrite(self.output_path, frame)
                    cap.release()
                    return True
            else:
                # 在10%-30%范围取多个样本，找到最有代表性的帧
                # 这里用直方图差异作为选择标准
                start_pos = int(total_frames * 0.1)
                end_pos = int(total_frames * 0.3)

                # 每隔一定间隔采样
                sample_interval = (end_pos - start_pos) // 10
                sample_frames = []

                # 采样视频帧
                for i in range(10):
                    # 更新进度
                    self.progress_updated.emit(i * 10)

                    if self.stopped:
                        break

                    pos = start_pos + i * sample_interval
                    cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                    ret, frame = cap.read()

                    if ret:
                        sample_frames.append(frame)

                cap.release()

                if not sample_frames:
                    return False

                # 选择最有代表性的帧（这里简单选择中间的帧，可以扩展为更智能的选择）
                best_frame = sample_frames[len(sample_frames) // 2]

                # 调整大小
                best_frame = cv2.resize(best_frame, self.size)

                # 保存缩略图
                cv2.imwrite(self.output_path, best_frame)
                return True

            return False

        except Exception as e:
            print(f"缩略图自动生成错误: {e}")
            return False


class ThumbnailGenerator(QObject):
    """视频缩略图生成器类"""

    # 自定义信号
    thumbnail_ready = pyqtSignal(str, str)  # 参数: 视频路径, 缩略图路径
    thumbnail_error = pyqtSignal(str, str)  # 参数: 视频路径, 错误信息
    batch_completed = pyqtSignal()  # 批量生成完成信号

    def __init__(self, cache_dir=None):
        """
        初始化缩略图生成器

        参数:
            cache_dir: 缩略图缓存目录，不指定则使用系统临时目录
        """
        super().__init__()

        # 设置缓存目录
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "CineAIStudio", "thumbnails")

        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)

        # 保存当前工作线程
        self.workers = []

    def generate_thumbnail(self, video_path, time_pos=None, size=(320, 180)):
        """
        生成单个视频的缩略图

        参数:
            video_path: 视频文件路径
            time_pos: 截取时间点(秒)，None则自动选取合适的帧
            size: 缩略图尺寸 (宽, 高)

        返回:
            缩略图路径
        """
        # 生成唯一的缩略图文件名
        thumbnail_name = f"{uuid.uuid4().hex}.jpg"
        thumbnail_path = os.path.join(self.cache_dir, thumbnail_name)

        # 创建并启动工作线程
        worker = ThumbnailGenerationWorker(video_path, thumbnail_path, time_pos, size)
        worker.thumbnail_generated.connect(self.thumbnail_ready)
        worker.error_occurred.connect(self.thumbnail_error)

        # 保存并启动线程
        self.workers.append(worker)
        worker.start()

        return thumbnail_path

    def generate_thumbnails_batch(self, video_paths, time_pos=None, size=(320, 180)):
        """批量生成缩略图"""
        for video_path in video_paths:
            self.generate_thumbnail(video_path, time_pos, size)

    def clear_cache(self):
        """清除缩略图缓存"""
        # 停止所有工作线程
        for worker in self.workers:
            worker.stop()
            worker.wait()

        self.workers = []

        # 清空缓存目录
        try:
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            return True
        except Exception as e:
            print(f"清除缓存错误: {e}")
            return False

    def get_cached_thumbnail(self, video_path):
        """获取已缓存的缩略图路径（如果存在）"""
        # 构建视频文件的哈希值作为标识
        import hashlib
        video_hash = hashlib.md5(video_path.encode()).hexdigest()

        # 检查是否存在已缓存的缩略图
        for file in os.listdir(self.cache_dir):
            if file.startswith(video_hash):
                return os.path.join(self.cache_dir, file)

        return None

    def stop_all(self):
        """停止所有缩略图生成任务"""
        for worker in self.workers:
            worker.stop()
            worker.wait()

        self.workers = []
