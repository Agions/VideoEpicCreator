#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级视频优化器 - 专业的视频质量优化和性能调优
"""

import os
import subprocess
import json
import time
import logging
import cv2
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """优化类型"""
    QUALITY = "quality"
    PERFORMANCE = "performance"
    SIZE = "size"
    BALANCED = "balanced"
    STREAMING = "streaming"
    MOBILE = "mobile"
    HDR = "hdr"


class VideoArtifact(Enum):
    """视频伪影类型"""
    BLOCKING = "blocking"
    RINGING = "ringing"
    MOSQUITO = "mosquito"
    BLUR = "blur"
    NOISE = "noise"
    BANDING = "banding"
    ALIASING = "aliasing"
    COMPRESSION = "compression"


@dataclass
class VideoQualityMetrics:
    """视频质量指标"""
    psnr: float = 0.0  # 峰值信噪比
    ssim: float = 0.0  # 结构相似性
    mse: float = 0.0   # 均方误差
    bitrate: int = 0   # 比特率 (kbps)
    file_size: int = 0  # 文件大小 (bytes)
    resolution: str = ""
    fps: float = 0.0
    duration: float = 0.0
    artifacts: Dict[VideoArtifact, float] = field(default_factory=dict)
    
    @property
    def quality_score(self) -> float:
        """质量评分 (0-100)"""
        if self.psnr > 0:
            psnr_score = min(100, self.psnr / 0.4)  # PSNR 40+ = 100分
        else:
            psnr_score = 0
        
        if self.ssim > 0:
            ssim_score = self.ssim * 100
        else:
            ssim_score = 0
        
        # 综合评分
        return (psnr_score * 0.6 + ssim_score * 0.4)


@dataclass
class OptimizationProfile:
    """优化配置文件"""
    name: str
    type: OptimizationType
    target_quality: float  # 0-100
    max_bitrate: int  # kbps
    min_bitrate: int  # kbps
    target_resolution: str
    target_fps: int
    codec: str
    preset: str
    crf: int
    keyframe_interval: int
    audio_bitrate: int  # kbps
    advanced_params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    output_path: Optional[str] = None
    original_metrics: Optional[VideoQualityMetrics] = None
    optimized_metrics: Optional[VideoQualityMetrics] = None
    processing_time: float = 0.0
    file_size_reduction: float = 0.0  # 百分比
    quality_improvement: float = 0.0  # 百分比
    performance_improvement: float = 0.0  # 百分比
    optimization_params: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class VideoOptimizer:
    """视频优化器"""
    
    def __init__(self, ffmpeg_path: str, ffprobe_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # 优化配置文件
        self.profiles: Dict[str, OptimizationProfile] = {}
        self._initialize_profiles()
        
        # 优化会话管理
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}
        self.optimization_lock = threading.Lock()
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 性能统计
        self.stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "failed_optimizations": 0,
            "average_quality_improvement": 0.0,
            "average_size_reduction": 0.0,
            "total_processing_time": 0.0
        }
        
        # 质量分析缓存
        self.quality_cache: Dict[str, VideoQualityMetrics] = {}
        self.cache_lock = threading.Lock()
        
        logger.info("视频优化器初始化完成")
    
    def _initialize_profiles(self):
        """初始化优化配置文件"""
        # 高质量配置
        self.profiles["high_quality"] = OptimizationProfile(
            name="high_quality",
            type=OptimizationType.QUALITY,
            target_quality=90,
            max_bitrate=8000,
            min_bitrate=1000,
            target_resolution="1920x1080",
            target_fps=60,
            codec="libx265",
            preset="slow",
            crf=18,
            keyframe_interval=250,
            audio_bitrate=192,
            advanced_params={
                "tune": "film",
                "profile": "high",
                "pix_fmt": "yuv420p10le",
                "x265-params": "aq-mode=3:aq-strength=1.5"
            },
            description="最高质量优化，适合专业视频制作"
        )
        
        # 平衡配置
        self.profiles["balanced"] = OptimizationProfile(
            name="balanced",
            type=OptimizationType.BALANCED,
            target_quality=80,
            max_bitrate=5000,
            min_bitrate=500,
            target_resolution="1920x1080",
            target_fps=30,
            codec="libx264",
            preset="medium",
            crf=23,
            keyframe_interval=250,
            audio_bitrate=128,
            advanced_params={
                "tune": "film",
                "profile": "high",
                "pix_fmt": "yuv420p"
            },
            description="平衡质量和文件大小，适合一般用途"
        )
        
        # 性能配置
        self.profiles["performance"] = OptimizationProfile(
            name="performance",
            type=OptimizationType.PERFORMANCE,
            target_quality=70,
            max_bitrate=3000,
            min_bitrate=300,
            target_resolution="1280x720",
            target_fps=30,
            codec="libx264",
            preset="fast",
            crf=26,
            keyframe_interval=125,
            audio_bitrate=96,
            advanced_params={
                "tune": "fastdecode",
                "profile": "main",
                "pix_fmt": "yuv420p"
            },
            description="性能优先，适合实时处理和低延迟场景"
        )
        
        # 文件大小优化配置
        self.profiles["size_optimized"] = OptimizationProfile(
            name="size_optimized",
            type=OptimizationType.SIZE,
            target_quality=65,
            max_bitrate=2000,
            min_bitrate=200,
            target_resolution="1280x720",
            target_fps=24,
            codec="libx265",
            preset="slow",
            crf=28,
            keyframe_interval=250,
            audio_bitrate=64,
            advanced_params={
                "tune": "grain",
                "profile": "main",
                "pix_fmt": "yuv420p"
            },
            description="文件大小优先，适合存储和传输"
        )
        
        # 流媒体配置
        self.profiles["streaming"] = OptimizationProfile(
            name="streaming",
            type=OptimizationType.STREAMING,
            target_quality=75,
            max_bitrate=4000,
            min_bitrate=400,
            target_resolution="1920x1080",
            target_fps=30,
            codec="libx264",
            preset="medium",
            crf=24,
            keyframe_interval=60,  # 2秒关键帧间隔
            audio_bitrate=128,
            advanced_params={
                "tune": "zerolatency",
                "profile": "high",
                "pix_fmt": "yuv420p",
                "movflags": "+faststart"
            },
            description="流媒体优化，适合在线播放"
        )
        
        # 移动设备配置
        self.profiles["mobile"] = OptimizationProfile(
            name="mobile",
            type=OptimizationType.MOBILE,
            target_quality=70,
            max_bitrate=1500,
            min_bitrate=150,
            target_resolution="1280x720",
            target_fps=30,
            codec="libx264",
            preset="fast",
            crf=26,
            keyframe_interval=125,
            audio_bitrate=96,
            advanced_params={
                "tune": "fastdecode",
                "profile": "baseline",
                "pix_fmt": "yuv420p"
            },
            description="移动设备优化，适合手机和平板"
        )
        
        # HDR配置
        self.profiles["hdr"] = OptimizationProfile(
            name="hdr",
            type=OptimizationType.HDR,
            target_quality=85,
            max_bitrate=10000,
            min_bitrate=2000,
            target_resolution="3840x2160",
            target_fps=60,
            codec="libx265",
            preset="slow",
            crf=20,
            keyframe_interval=250,
            audio_bitrate=256,
            advanced_params={
                "tune": "film",
                "profile": "main10",
                "pix_fmt": "yuv420p10le",
                "x265-params": "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc"
            },
            description="HDR视频优化，适合高动态范围内容"
        )
        
        logger.info(f"初始化了 {len(self.profiles)} 个优化配置文件")
    
    def get_profile(self, profile_name: str) -> Optional[OptimizationProfile]:
        """获取优化配置文件"""
        return self.profiles.get(profile_name)
    
    def list_profiles(self) -> List[OptimizationProfile]:
        """列出所有优化配置文件"""
        return list(self.profiles.values())
    
    def analyze_video_quality(self, video_path: str) -> VideoQualityMetrics:
        """分析视频质量"""
        # 检查缓存
        with self.cache_lock:
            if video_path in self.quality_cache:
                return self.quality_cache[video_path]
        
        try:
            # 获取视频基本信息
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # 获取文件大小
            file_size = os.path.getsize(video_path)
            
            # 获取比特率
            bitrate = int(file_size * 8 / duration / 1000) if duration > 0 else 0
            
            # 分析视频质量
            psnr_values = []
            ssim_values = []
            mse_values = []
            
            # 采样分析（每30帧分析一次）
            sample_rate = max(1, frame_count // 100)  # 最多分析100帧
            
            prev_frame = None
            for i in range(0, frame_count, sample_rate):
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 转换为灰度图进行分析
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # 计算PSNR
                    mse = np.mean((gray - prev_frame) ** 2)
                    if mse > 0:
                        psnr = 20 * np.log10(255.0 / np.sqrt(mse))
                    else:
                        psnr = float('inf')
                    
                    # 计算SSIM
                    ssim = self._calculate_ssim(gray, prev_frame)
                    
                    psnr_values.append(psnr)
                    ssim_values.append(ssim)
                    mse_values.append(mse)
                
                prev_frame = gray
                
                # 分析伪影
                artifacts = self._detect_artifacts(frame)
            
            cap.release()
            
            # 计算平均值
            avg_psnr = np.mean(psnr_values) if psnr_values else 0
            avg_ssim = np.mean(ssim_values) if ssim_values else 0
            avg_mse = np.mean(mse_values) if mse_values else 0
            
            # 创建质量指标
            metrics = VideoQualityMetrics(
                psnr=avg_psnr,
                ssim=avg_ssim,
                mse=avg_mse,
                bitrate=bitrate,
                file_size=file_size,
                resolution=f"{width}x{height}",
                fps=fps,
                duration=duration,
                artifacts=artifacts
            )
            
            # 缓存结果
            with self.cache_lock:
                self.quality_cache[video_path] = metrics
            
            logger.info(f"视频质量分析完成: {video_path}, PSNR: {avg_psnr:.2f}, SSIM: {avg_ssim:.4f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"分析视频质量失败: {e}")
            return VideoQualityMetrics()
    
    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """计算结构相似性"""
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        
        mu1 = cv2.GaussianBlur(img1.astype(float), (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(img2.astype(float), (11, 11), 1.5)
        
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.GaussianBlur(img1.astype(float) ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(img2.astype(float) ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(img1.astype(float) * img2.astype(float), (11, 11), 1.5) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        
        return np.mean(ssim_map)
    
    def _detect_artifacts(self, frame: np.ndarray) -> Dict[VideoArtifact, float]:
        """检测视频伪影"""
        artifacts = {}
        
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 检测块效应（blocking）
        block_size = 8
        h_blocks = gray.shape[0] // block_size
        w_blocks = gray.shape[1] // block_size
        
        blocking_score = 0
        for i in range(h_blocks):
            for j in range(w_blocks):
                block = gray[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
                # 计算块内方差
                block_variance = np.var(block)
                if block_variance < 100:  # 低方差可能是块效应
                    blocking_score += 1
        
        artifacts[VideoArtifact.BLOCKING] = blocking_score / (h_blocks * w_blocks)
        
        # 检测噪声
        noise = cv2.Laplacian(gray, cv2.CV_64F)
        noise_variance = np.var(noise)
        artifacts[VideoArtifact.NOISE] = min(1.0, noise_variance / 1000)
        
        # 检测模糊
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        artifacts[VideoArtifact.BLUR] = max(0, 1 - blur_score / 1000)
        
        # 检测带状效应（banding）
        # 通过直方图分析检测带状效应
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_normalized = hist / np.sum(hist)
        
        # 计算直方图的"尖峰度"
        peaks = 0
        for i in range(1, 255):
            if hist_normalized[i] > hist_normalized[i-1] and hist_normalized[i] > hist_normalized[i+1]:
                if hist_normalized[i] > 0.01:  # 显著的峰值
                    peaks += 1
        
        artifacts[VideoArtifact.BANDING] = min(1.0, peaks / 20)
        
        return artifacts
    
    def recommend_profile(self, video_info: Dict[str, Any], 
                         requirements: Dict[str, Any]) -> Optional[str]:
        """推荐优化配置文件"""
        # 获取当前视频质量
        current_quality = video_info.get("quality_score", 75)
        current_bitrate = video_info.get("bitrate", 5000)
        current_resolution = video_info.get("resolution", "1920x1080")
        
        # 分析需求
        target_quality = requirements.get("target_quality", current_quality)
        target_size = requirements.get("target_size", 0)  # MB
        optimization_type = requirements.get("type", OptimizationType.BALANCED)
        
        # 根据需求筛选配置文件
        suitable_profiles = []
        
        for profile_name, profile in self.profiles.items():
            if profile.type == optimization_type:
                # 检查质量要求
                if profile.target_quality >= target_quality - 10:
                    # 检查文件大小要求
                    if target_size > 0:
                        estimated_size = (profile.max_bitrate * 1000 * video_info.get("duration", 60)) / 8 / 1024 / 1024
                        if estimated_size <= target_size * 1.2:  # 允许20%误差
                            suitable_profiles.append(profile_name)
                    else:
                        suitable_profiles.append(profile_name)
        
        # 如果没有找到合适的配置文件，使用平衡配置
        if not suitable_profiles:
            suitable_profiles = ["balanced"]
        
        # 选择最适合的配置文件
        if optimization_type == OptimizationType.QUALITY:
            return "high_quality"
        elif optimization_type == OptimizationType.SIZE:
            return "size_optimized"
        elif optimization_type == OptimizationType.PERFORMANCE:
            return "performance"
        elif optimization_type == OptimizationType.STREAMING:
            return "streaming"
        elif optimization_type == OptimizationType.MOBILE:
            return "mobile"
        elif optimization_type == OptimizationType.HDR:
            return "hdr"
        else:
            return "balanced"
    
    def optimize_video(self, video_path: str, profile_name: str, 
                       output_path: str = None, progress_callback=None) -> OptimizationResult:
        """优化视频"""
        start_time = time.time()
        session_id = f"optimize_{int(time.time() * 1000)}"
        
        try:
            # 获取配置文件
            profile = self.get_profile(profile_name)
            if not profile:
                raise ValueError(f"未找到配置文件: {profile_name}")
            
            # 设置输出路径
            if not output_path:
                output_path = video_path.replace(f".{Path(video_path).suffix}", f"_optimized.{profile_name}.mp4")
            
            # 分析原始视频质量
            original_metrics = self.analyze_video_quality(video_path)
            
            # 创建优化会话
            with self.optimization_lock:
                self.active_optimizations[session_id] = {
                    "video_path": video_path,
                    "output_path": output_path,
                    "profile": profile,
                    "start_time": start_time,
                    "status": "optimizing"
                }
            
            # 构建优化命令
            cmd = self._build_optimization_command(video_path, output_path, profile)
            
            logger.info(f"开始优化视频: {video_path} -> {output_path}")
            logger.info(f"使用配置文件: {profile_name}")
            logger.debug(f"优化命令: {' '.join(cmd)}")
            
            # 执行优化
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            processing_time = time.time() - start_time
            
            if result.returncode == 0:
                # 优化成功
                optimized_metrics = self.analyze_video_quality(output_path)
                
                # 计算改进指标
                file_size_reduction = (original_metrics.file_size - optimized_metrics.file_size) / original_metrics.file_size * 100
                quality_improvement = (optimized_metrics.quality_score - original_metrics.quality_score) / original_metrics.quality_score * 100
                
                # 更新统计
                self.stats["total_optimizations"] += 1
                self.stats["successful_optimizations"] += 1
                self.stats["total_processing_time"] += processing_time
                
                # 更新平均改进
                successful_count = self.stats["successful_optimizations"]
                current_avg_quality = self.stats["average_quality_improvement"]
                current_avg_size = self.stats["average_size_reduction"]
                
                self.stats["average_quality_improvement"] = (
                    (current_avg_quality * (successful_count - 1) + quality_improvement) / successful_count
                )
                self.stats["average_size_reduction"] = (
                    (current_avg_size * (successful_count - 1) + file_size_reduction) / successful_count
                )
                
                logger.info(f"视频优化完成: {output_path}")
                logger.info(f"文件大小减少: {file_size_reduction:.2f}%")
                logger.info(f"质量改进: {quality_improvement:.2f}%")
                logger.info(f"处理时间: {processing_time:.2f}s")
                
                return OptimizationResult(
                    success=True,
                    output_path=output_path,
                    original_metrics=original_metrics,
                    optimized_metrics=optimized_metrics,
                    processing_time=processing_time,
                    file_size_reduction=file_size_reduction,
                    quality_improvement=quality_improvement,
                    optimization_params={
                        "profile": profile_name,
                        "codec": profile.codec,
                        "preset": profile.preset,
                        "crf": profile.crf,
                        "bitrate": profile.max_bitrate
                    }
                )
            else:
                # 优化失败
                self.stats["total_optimizations"] += 1
                self.stats["failed_optimizations"] += 1
                
                logger.error(f"视频优化失败: {result.stderr}")
                
                return OptimizationResult(
                    success=False,
                    processing_time=processing_time,
                    warnings=[f"优化失败: {result.stderr}"]
                )
        
        except subprocess.TimeoutExpired:
            self.stats["total_optimizations"] += 1
            self.stats["failed_optimizations"] += 1
            
            logger.error(f"视频优化超时: {video_path}")
            
            return OptimizationResult(
                success=False,
                processing_time=time.time() - start_time,
                warnings=["优化超时"]
            )
        
        except Exception as e:
            self.stats["total_optimizations"] += 1
            self.stats["failed_optimizations"] += 1
            
            logger.error(f"视频优化异常: {e}")
            
            return OptimizationResult(
                success=False,
                processing_time=time.time() - start_time,
                warnings=[f"优化异常: {str(e)}"]
            )
        
        finally:
            # 清理会话
            with self.optimization_lock:
                self.active_optimizations.pop(session_id, None)
    
    def _build_optimization_command(self, input_path: str, output_path: str, 
                                  profile: OptimizationProfile) -> List[str]:
        """构建优化命令"""
        cmd = [self.ffmpeg_path, "-i", input_path]
        
        # 视频编码参数
        cmd.extend(["-c:v", profile.codec])
        
        # 预设
        if profile.preset:
            cmd.extend(["-preset", profile.preset])
        
        # 调优参数
        if profile.advanced_params.get("tune"):
            cmd.extend(["-tune", profile.advanced_params["tune"]])
        
        # 配置文件
        if profile.advanced_params.get("profile"):
            cmd.extend(["-profile:v", profile.advanced_params["profile"]])
        
        # CRF或比特率
        if profile.crf > 0:
            cmd.extend(["-crf", str(profile.crf)])
        
        if profile.max_bitrate > 0:
            cmd.extend(["-b:v", f"{profile.max_bitrate}k"])
            cmd.extend(["-maxrate:v", f"{profile.max_bitrate}k"])
            cmd.extend(["-bufsize:v", f"{profile.max_bitrate * 2}k"])
        
        # 关键帧间隔
        cmd.extend(["-g", str(profile.keyframe_interval)])
        
        # 像素格式
        if profile.advanced_params.get("pix_fmt"):
            cmd.extend(["-pix_fmt", profile.advanced_params["pix_fmt"]])
        
        # 分辨率
        if profile.target_resolution and profile.target_resolution != "keep":
            cmd.extend(["-vf", f"scale={profile.target_resolution}"])
        
        # 帧率
        if profile.target_fps > 0:
            cmd.extend(["-r", str(profile.target_fps)])
        
        # 音频编码参数
        cmd.extend(["-c:a", "aac"])
        cmd.extend(["-b:a", f"{profile.audio_bitrate}k"])
        
        # 高级参数
        if profile.advanced_params.get("x265-params"):
            cmd.extend(["-x265-params", profile.advanced_params["x265-params"]])
        
        # 流媒体参数
        if profile.advanced_params.get("movflags"):
            cmd.extend(["-movflags", profile.advanced_params["movflags"]])
        
        # 输出文件
        cmd.extend(["-y", output_path])
        
        return cmd
    
    def create_custom_profile(self, name: str, profile_data: Dict[str, Any]) -> bool:
        """创建自定义优化配置文件"""
        try:
            profile = OptimizationProfile(
                name=name,
                type=OptimizationType(profile_data.get("type", "balanced")),
                target_quality=profile_data.get("target_quality", 80),
                max_bitrate=profile_data.get("max_bitrate", 5000),
                min_bitrate=profile_data.get("min_bitrate", 500),
                target_resolution=profile_data.get("target_resolution", "1920x1080"),
                target_fps=profile_data.get("target_fps", 30),
                codec=profile_data.get("codec", "libx264"),
                preset=profile_data.get("preset", "medium"),
                crf=profile_data.get("crf", 23),
                keyframe_interval=profile_data.get("keyframe_interval", 250),
                audio_bitrate=profile_data.get("audio_bitrate", 128),
                advanced_params=profile_data.get("advanced_params", {}),
                description=profile_data.get("description", "")
            )
            
            self.profiles[name] = profile
            logger.info(f"创建自定义配置文件: {name}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建自定义配置文件失败: {e}")
            return False
    
    def batch_optimize(self, video_paths: List[str], profile_name: str, 
                      output_dir: str = None, max_workers: int = 2) -> List[OptimizationResult]:
        """批量优化视频"""
        results = []
        
        # 创建输出目录
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 使用线程池进行批量处理
        from concurrent.futures import as_completed
        
        futures = []
        for video_path in video_paths:
            if output_dir:
                output_path = os.path.join(output_dir, f"optimized_{os.path.basename(video_path)}")
            else:
                output_path = None
            
            future = self.thread_pool.submit(self.optimize_video, video_path, profile_name, output_path)
            futures.append(future)
        
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                result = future.result(timeout=1800)
                results.append(result)
            except Exception as e:
                logger.error(f"批量优化任务失败: {e}")
                results.append(OptimizationResult(
                    success=False,
                    warnings=[f"批量优化失败: {str(e)}"]
                ))
        
        return results
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计"""
        stats = self.stats.copy()
        
        # 计算成功率
        total = stats["total_optimizations"]
        if total > 0:
            stats["success_rate"] = stats["successful_optimizations"] / total
        else:
            stats["success_rate"] = 0.0
        
        # 计算平均处理时间
        if stats["successful_optimizations"] > 0:
            stats["average_processing_time"] = stats["total_processing_time"] / stats["successful_optimizations"]
        else:
            stats["average_processing_time"] = 0.0
        
        return stats
    
    def get_active_optimizations(self) -> Dict[str, Any]:
        """获取活跃的优化会话"""
        with self.optimization_lock:
            return self.active_optimizations.copy()
    
    def cancel_optimization(self, session_id: str) -> bool:
        """取消优化会话"""
        with self.optimization_lock:
            if session_id in self.active_optimizations:
                self.active_optimizations[session_id]["status"] = "cancelled"
                logger.info(f"已取消优化会话: {session_id}")
                return True
            return False
    
    def clear_cache(self):
        """清空质量分析缓存"""
        with self.cache_lock:
            self.quality_cache.clear()
        logger.info("质量分析缓存已清空")
    
    def get_optimization_recommendations(self, video_path: str) -> Dict[str, Any]:
        """获取优化建议"""
        try:
            # 分析视频质量
            metrics = self.analyze_video_quality(video_path)
            
            recommendations = []
            
            # 基于质量给出建议
            if metrics.quality_score < 60:
                recommendations.append({
                    "type": "quality",
                    "message": "视频质量较低，建议使用高质量配置文件进行优化",
                    "profile": "high_quality"
                })
            elif metrics.quality_score > 90:
                recommendations.append({
                    "type": "size",
                    "message": "视频质量很高，可以考虑压缩以节省空间",
                    "profile": "size_optimized"
                })
            
            # 基于文件大小给出建议
            if metrics.file_size > 100 * 1024 * 1024:  # 100MB
                recommendations.append({
                    "type": "size",
                    "message": "文件较大，建议使用文件大小优化配置",
                    "profile": "size_optimized"
                })
            
            # 基于分辨率给出建议
            if metrics.resolution == "3840x2160":  # 4K
                recommendations.append({
                    "type": "performance",
                    "message": "4K视频，建议使用性能优化配置以提高处理速度",
                    "profile": "performance"
                })
            
            # 基于伪影检测给出建议
            if metrics.artifacts.get(VideoArtifact.NOISE, 0) > 0.5:
                recommendations.append({
                    "type": "quality",
                    "message": "检测到较多噪声，建议使用降噪处理",
                    "profile": "high_quality"
                })
            
            if metrics.artifacts.get(VideoArtifact.BLUR, 0) > 0.5:
                recommendations.append({
                    "type": "quality",
                    "message": "检测到模糊问题，建议使用锐化处理",
                    "profile": "high_quality"
                })
            
            return {
                "current_metrics": {
                    "quality_score": metrics.quality_score,
                    "file_size_mb": metrics.file_size / (1024 * 1024),
                    "bitrate_kbps": metrics.bitrate,
                    "resolution": metrics.resolution,
                    "duration_s": metrics.duration
                },
                "recommendations": recommendations,
                "available_profiles": [p.name for p in self.profiles.values()]
            }
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理视频优化器资源")
        
        # 取消所有活跃优化
        with self.optimization_lock:
            for session_id in list(self.active_optimizations.keys()):
                self.cancel_optimization(session_id)
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        # 清空缓存
        self.clear_cache()
        
        logger.info("视频优化器资源清理完成")