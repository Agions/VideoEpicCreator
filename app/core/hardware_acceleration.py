#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业级硬件加速管理器 - 专业的硬件加速管理和优化
"""

import os
import subprocess
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import psutil
import platform

logger = logging.getLogger(__name__)


class HardwareType(Enum):
    """硬件类型"""
    CPU = "cpu"
    GPU = "gpu"
    INTEL_QSV = "intel_qsv"
    AMD_VCE = "amd_vce"
    NVIDIA_NVENC = "nvidia_nvenc"
    APPLE_VIDEOTOOLBOX = "apple_videotoolbox"
    OPENCL = "opencl"
    CUDA = "cuda"
    VULKAN = "vulkan"


class AccelerationMode(Enum):
    """加速模式"""
    NONE = "none"
    HARDWARE = "hardware"
    HYBRID = "hybrid"
    FULL_HARDWARE = "full_hardware"


@dataclass
class HardwareInfo:
    """硬件信息"""
    hardware_type: HardwareType
    name: str
    vendor: str
    model: str
    capabilities: List[str]
    memory_size: int  # MB
    max_resolution: str
    max_fps: int
    supported_codecs: List[str]
    is_available: bool = True
    performance_score: float = 0.0
    cores: int = 1  # 添加cores属性，默认为1


@dataclass
class AccelerationConfig:
    """加速配置"""
    hardware_type: HardwareType
    enabled: bool = True
    priority: int = 0
    max_concurrent_tasks: int = 1
    memory_limit: int = 0  # MB, 0 = no limit
    power_limit: int = 0  # W, 0 = no limit
    temperature_limit: int = 0  # °C, 0 = no limit
    preferred_codecs: List[str] = field(default_factory=list)
    optimization_params: Dict[str, Any] = field(default_factory=dict)


class HardwareAccelerationManager:
    """硬件加速管理器"""
    
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        
        # 硬件信息
        self.hardware_info: Dict[HardwareType, HardwareInfo] = {}
        self.acceleration_configs: Dict[HardwareType, AccelerationConfig] = {}
        
        # 硬件使用状态
        self.hardware_usage: Dict[HardwareType, Dict[str, Any]] = {}
        self.usage_lock = threading.Lock()
        
        # 性能监控
        self.performance_stats = {
            "total_accelerated_tasks": 0,
            "successful_accelerations": 0,
            "failed_accelerations": 0,
            "average_speedup": 1.0,
            "power_consumption": 0.0,
            "temperature_stats": {}
        }
        
        # 硬件监控线程
        self.monitor_thread = None
        self.monitor_running = False
        
        # 初始化硬件检测
        self._detect_hardware()
        self._initialize_configs()
        self._start_monitoring()
        
        logger.info("硬件加速管理器初始化完成")
    
    def _detect_hardware(self):
        """检测可用硬件"""
        logger.info("开始检测硬件...")
        
        # 检测CPU
        self._detect_cpu()
        
        # 检测GPU
        self._detect_gpu()
        
        # 检测专用硬件加速器
        self._detect_intel_qsv()
        self._detect_nvidia_nvenc()
        self._detect_amd_vce()
        self._detect_apple_videotoolbox()
        self._detect_opencl()
        self._detect_cuda()
        self._detect_vulkan()
        
        logger.info(f"检测到 {len(self.hardware_info)} 个硬件设备")
    
    def _detect_cpu(self):
        """检测CPU信息"""
        try:
            cpu_info = {
                "name": platform.processor(),
                "vendor": "Unknown",
                "model": platform.machine(),
                "cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency": psutil.cpu_freq().max if psutil.cpu_freq() else 0
            }
            
            # 获取CPU内存信息
            memory = psutil.virtual_memory()
            
            hardware = HardwareInfo(
                hardware_type=HardwareType.CPU,
                name=cpu_info["name"] or "CPU",
                vendor=cpu_info["vendor"],
                model=cpu_info["model"],
                capabilities=["multithreading", "simd", "general_purpose"],
                memory_size=memory.total // (1024 * 1024),  # MB
                max_resolution="8K",
                max_fps=120,
                supported_codecs=["libx264", "libx265", "libvpx", "libvpx-vp9"],
                performance_score=1.0,
                cores=psutil.cpu_count()  # 添加CPU核心数
            )
            
            self.hardware_info[HardwareType.CPU] = hardware
            logger.info(f"检测到CPU: {hardware.name}, {hardware.memory_size}MB, {hardware.cores}核心")
            
        except Exception as e:
            logger.error(f"检测CPU失败: {e}")
    
    def _detect_gpu(self):
        """检测GPU信息"""
        try:
            # 尝试检测NVIDIA GPU
            try:
                result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for i, line in enumerate(lines):
                        name, memory = line.split(', ')
                        hardware = HardwareInfo(
                            hardware_type=HardwareType.GPU,
                            name=name.strip(),
                            vendor="NVIDIA",
                            model=f"GPU-{i}",
                            capabilities=["cuda", "opengl", "compute"],
                            memory_size=int(memory.strip()),
                            max_resolution="8K",
                            max_fps=240,
                            supported_codecs=["h264_nvenc", "hevc_nvenc"],
                            performance_score=2.0
                        )
                        self.hardware_info[f"{HardwareType.GPU}_{i}"] = hardware
                        logger.info(f"检测到NVIDIA GPU: {hardware.name}, {hardware.memory_size}MB")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # 尝试检测AMD GPU
            try:
                result = subprocess.run(["rocm-smi", "--showproductname"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # 解析AMD GPU信息
                    logger.info("检测到AMD GPU")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # 检测集成GPU
            if platform.system() == "Darwin":
                # macOS系统
                try:
                    result = subprocess.run(["system_profiler", "SPDisplaysDataType"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # 解析macOS GPU信息
                        logger.info("检测到macOS GPU")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                    
        except Exception as e:
            logger.error(f"检测GPU失败: {e}")
    
    def _detect_intel_qsv(self):
        """检测Intel Quick Sync Video"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-encoders"], 
                                  capture_output=True, text=True, timeout=10)
            if "h264_qsv" in result.stdout or "hevc_qsv" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.INTEL_QSV,
                    name="Intel Quick Sync Video",
                    vendor="Intel",
                    model="QSV",
                    capabilities=["hardware_encoding", "low_power", "real_time"],
                    memory_size=512,  # 共享内存
                    max_resolution="4K",
                    max_fps=60,
                    supported_codecs=["h264_qsv", "hevc_qsv"],
                    performance_score=1.8
                )
                self.hardware_info[HardwareType.INTEL_QSV] = hardware
                logger.info("检测到Intel Quick Sync Video")
                
        except Exception as e:
            logger.error(f"检测Intel QSV失败: {e}")
    
    def _detect_nvidia_nvenc(self):
        """检测NVIDIA NVENC"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-encoders"], 
                                  capture_output=True, text=True, timeout=10)
            if "h264_nvenc" in result.stdout or "hevc_nvenc" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.NVIDIA_NVENC,
                    name="NVIDIA NVENC",
                    vendor="NVIDIA",
                    model="NVENC",
                    capabilities=["hardware_encoding", "high_quality", "real_time"],
                    memory_size=0,  # 使用GPU内存
                    max_resolution="8K",
                    max_fps=120,
                    supported_codecs=["h264_nvenc", "hevc_nvenc", "av1_nvenc"],
                    performance_score=2.5
                )
                self.hardware_info[HardwareType.NVIDIA_NVENC] = hardware
                logger.info("检测到NVIDIA NVENC")
                
        except Exception as e:
            logger.error(f"检测NVIDIA NVENC失败: {e}")
    
    def _detect_amd_vce(self):
        """检测AMD VCE"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-encoders"], 
                                  capture_output=True, text=True, timeout=10)
            if "h264_amf" in result.stdout or "hevc_amf" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.AMD_VCE,
                    name="AMD VCE",
                    vendor="AMD",
                    model="VCE",
                    capabilities=["hardware_encoding", "low_power"],
                    memory_size=0,  # 使用GPU内存
                    max_resolution="4K",
                    max_fps=60,
                    supported_codecs=["h264_amf", "hevc_amf"],
                    performance_score=1.6
                )
                self.hardware_info[HardwareType.AMD_VCE] = hardware
                logger.info("检测到AMD VCE")
                
        except Exception as e:
            logger.error(f"检测AMD VCE失败: {e}")
    
    def _detect_apple_videotoolbox(self):
        """检测Apple VideoToolbox"""
        if platform.system() == "Darwin":
            try:
                result = subprocess.run([self.ffmpeg_path, "-encoders"], 
                                      capture_output=True, text=True, timeout=10)
                if "h264_videotoolbox" in result.stdout or "hevc_videotoolbox" in result.stdout:
                    hardware = HardwareInfo(
                        hardware_type=HardwareType.APPLE_VIDEOTOOLBOX,
                        name="Apple VideoToolbox",
                        vendor="Apple",
                        model="VideoToolbox",
                        capabilities=["hardware_encoding", "low_power", "integrated"],
                        memory_size=0,  # 使用系统内存
                        max_resolution="8K",
                        max_fps=120,
                        supported_codecs=["h264_videotoolbox", "hevc_videotoolbox"],
                        performance_score=1.7
                    )
                    self.hardware_info[HardwareType.APPLE_VIDEOTOOLBOX] = hardware
                    logger.info("检测到Apple VideoToolbox")
                    
            except Exception as e:
                logger.error(f"检测Apple VideoToolbox失败: {e}")
    
    def _detect_opencl(self):
        """检测OpenCL支持"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-filters"], 
                                  capture_output=True, text=True, timeout=10)
            if "opencl" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.OPENCL,
                    name="OpenCL",
                    vendor="Khronos",
                    model="OpenCL",
                    capabilities=["compute", "parallel_processing"],
                    memory_size=0,  # 使用设备内存
                    max_resolution="8K",
                    max_fps=60,
                    supported_codecs=[],
                    performance_score=1.2
                )
                self.hardware_info[HardwareType.OPENCL] = hardware
                logger.info("检测到OpenCL支持")
                
        except Exception as e:
            logger.error(f"检测OpenCL失败: {e}")
    
    def _detect_cuda(self):
        """检测CUDA支持"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-hwaccels"], 
                                  capture_output=True, text=True, timeout=10)
            if "cuda" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.CUDA,
                    name="CUDA",
                    vendor="NVIDIA",
                    model="CUDA",
                    capabilities=["compute", "parallel_processing", "gpu_acceleration"],
                    memory_size=0,  # 使用GPU内存
                    max_resolution="8K",
                    max_fps=120,
                    supported_codecs=[],
                    performance_score=2.2
                )
                self.hardware_info[HardwareType.CUDA] = hardware
                logger.info("检测到CUDA支持")
                
        except Exception as e:
            logger.error(f"检测CUDA失败: {e}")
    
    def _detect_vulkan(self):
        """检测Vulkan支持"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-hwaccels"], 
                                  capture_output=True, text=True, timeout=10)
            if "vulkan" in result.stdout:
                hardware = HardwareInfo(
                    hardware_type=HardwareType.VULKAN,
                    name="Vulkan",
                    vendor="Khronos",
                    model="Vulkan",
                    capabilities=["compute", "graphics", "cross_platform"],
                    memory_size=0,  # 使用设备内存
                    max_resolution="8K",
                    max_fps=120,
                    supported_codecs=[],
                    performance_score=1.4
                )
                self.hardware_info[HardwareType.VULKAN] = hardware
                logger.info("检测到Vulkan支持")
                
        except Exception as e:
            logger.error(f"检测Vulkan失败: {e}")
    
    def _initialize_configs(self):
        """初始化硬件配置"""
        for hardware_type, hardware in self.hardware_info.items():
            config = AccelerationConfig(
                hardware_type=hardware_type,
                enabled=True,
                priority=self._get_default_priority(hardware_type),
                max_concurrent_tasks=self._get_default_max_tasks(hardware_type),
                preferred_codecs=hardware.supported_codecs
            )
            self.acceleration_configs[hardware_type] = config
        
        logger.info(f"初始化了 {len(self.acceleration_configs)} 个硬件配置")
    
    def _get_default_priority(self, hardware_type: HardwareType) -> int:
        """获取默认优先级"""
        priority_map = {
            HardwareType.NVIDIA_NVENC: 10,
            HardwareType.CUDA: 9,
            HardwareType.INTEL_QSV: 8,
            HardwareType.APPLE_VIDEOTOOLBOX: 7,
            HardwareType.AMD_VCE: 6,
            HardwareType.GPU: 5,
            HardwareType.OPENCL: 4,
            HardwareType.VULKAN: 3,
            HardwareType.CPU: 1
        }
        return priority_map.get(hardware_type, 0)
    
    def _get_default_max_tasks(self, hardware_type: HardwareType) -> int:
        """获取默认最大并发任务数"""
        if hardware_type in [HardwareType.CPU, HardwareType.GPU]:
            return 4
        elif hardware_type in [HardwareType.NVIDIA_NVENC, HardwareType.CUDA]:
            return 2
        else:
            return 1
    
    def _start_monitoring(self):
        """启动硬件监控"""
        self.monitor_running = True
        
        def monitor_loop():
            while self.monitor_running:
                try:
                    self._update_hardware_usage()
                    self._check_hardware_health()
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"硬件监控错误: {e}")
                    time.sleep(10)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("硬件监控线程已启动")
    
    def _update_hardware_usage(self):
        """更新硬件使用状态"""
        with self.usage_lock:
            # 更新CPU使用率
            if HardwareType.CPU in self.hardware_info:
                cpu_percent = psutil.cpu_percent(interval=1)
                self.hardware_usage[HardwareType.CPU] = {
                    "usage_percent": cpu_percent,
                    "temperature": self._get_cpu_temperature(),
                    "power_usage": self._get_cpu_power()
                }
            
            # 更新GPU使用率
            if HardwareType.GPU in self.hardware_info:
                gpu_usage = self._get_gpu_usage()
                self.hardware_usage[HardwareType.GPU] = gpu_usage
            
            # 更新其他硬件使用率
            for hardware_type in self.hardware_info:
                if hardware_type not in self.hardware_usage:
                    self.hardware_usage[hardware_type] = {
                        "usage_percent": 0,
                        "temperature": 0,
                        "power_usage": 0
                    }
    
    def _check_hardware_health(self):
        """检查硬件健康状态"""
        for hardware_type, usage in self.hardware_usage.items():
            # 检查温度
            if usage.get("temperature", 0) > 85:
                logger.warning(f"{hardware_type.value} 温度过高: {usage['temperature']}°C")
            
            # 检查使用率
            if usage.get("usage_percent", 0) > 95:
                logger.warning(f"{hardware_type.value} 使用率过高: {usage['usage_percent']}%")
            
            # 检查电源状态
            if usage.get("power_usage", 0) > 300:  # 300W
                logger.warning(f"{hardware_type.value} 功耗过高: {usage['power_usage']}W")
    
    def _get_cpu_temperature(self) -> float:
        """获取CPU温度"""
        try:
            if platform.system() == "Linux":
                # Linux系统
                temp_files = [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/thermal/thermal_zone1/temp",
                    "/sys/class/thermal/thermal_zone2/temp"
                ]
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        with open(temp_file, 'r') as f:
                            temp = float(f.read().strip()) / 1000
                            return temp
            elif platform.system() == "Darwin":
                # macOS系统
                result = subprocess.run(["sysctl", "-n", "machdep.xcpm.cpu_thermal_state"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return float(result.stdout.strip())
            elif platform.system() == "Windows":
                # Windows系统
                try:
                    import wmi
                    c = wmi.WMI()
                    for temperature in c.Win32_TemperatureProbe():
                        if temperature.CurrentTemperature:
                            return temperature.CurrentTemperature / 10.0 - 273.15
                except:
                    pass
        except Exception as e:
            logger.debug(f"获取CPU温度失败: {e}")
        
        return 0.0
    
    def _get_cpu_power(self) -> float:
        """获取CPU功耗"""
        try:
            if platform.system() == "Linux":
                # Linux系统
                rapl_files = [
                    "/sys/class/powercap/intel-rapl:0/energy_uj",
                    "/sys/class/powercap/intel-rapl:0/power_uw"
                ]
                for rapl_file in rapl_files:
                    if os.path.exists(rapl_file):
                        with open(rapl_file, 'r') as f:
                            return float(f.read().strip()) / 1000000  # 转换为W
        except Exception as e:
            logger.debug(f"获取CPU功耗失败: {e}")
        
        return 0.0
    
    def _get_gpu_usage(self) -> Dict[str, Any]:
        """获取GPU使用状态"""
        try:
            # 尝试使用nvidia-smi
            result = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,power.draw", 
                                    "--format=csv,noheader,nounits"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    usage, temp, power = lines[0].split(', ')
                    return {
                        "usage_percent": float(usage.strip()),
                        "temperature": float(temp.strip()),
                        "power_usage": float(power.strip())
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return {
            "usage_percent": 0,
            "temperature": 0,
            "power_usage": 0
        }
    
    def get_available_hardware(self) -> List[HardwareType]:
        """获取可用硬件列表"""
        return [hw_type for hw_type, info in self.hardware_info.items() if info.is_available]
    
    def get_hardware_info(self, hardware_type: HardwareType) -> Optional[HardwareInfo]:
        """获取硬件信息"""
        return self.hardware_info.get(hardware_type)
    
    def get_hardware_usage(self, hardware_type: HardwareType) -> Dict[str, Any]:
        """获取硬件使用状态"""
        with self.usage_lock:
            return self.hardware_usage.get(hardware_type, {})
    
    def recommend_hardware(self, task_type: str, requirements: Dict[str, Any]) -> Optional[HardwareType]:
        """推荐硬件"""
        available_hardware = self.get_available_hardware()
        
        # 根据任务类型筛选
        suitable_hardware = []
        for hw_type in available_hardware:
            hw_info = self.hardware_info[hw_type]
            
            if task_type == "video_encoding":
                if any(codec in hw_info.supported_codecs for codec in requirements.get("codecs", [])):
                    suitable_hardware.append(hw_type)
            elif task_type == "video_decoding":
                suitable_hardware.append(hw_type)
            elif task_type == "general_processing":
                suitable_hardware.append(hw_type)
        
        if not suitable_hardware:
            return HardwareType.CPU
        
        # 根据优先级排序
        suitable_hardware.sort(key=lambda x: self.acceleration_configs[x].priority, reverse=True)
        
        # 检查硬件使用率
        for hw_type in suitable_hardware:
            usage = self.get_hardware_usage(hw_type)
            config = self.acceleration_configs[hw_type]
            
            if usage.get("usage_percent", 0) < 80:  # 使用率低于80%
                return hw_type
        
        # 如果所有硬件都很忙，返回优先级最高的
        return suitable_hardware[0] if suitable_hardware else HardwareType.CPU
    
    def get_acceleration_params(self, hardware_type: HardwareType, 
                                codec: str) -> Dict[str, Any]:
        """获取加速参数"""
        params = {
            "hardware_acceleration": True,
            "hwaccel": "auto"
        }
        
        if hardware_type == HardwareType.NVIDIA_NVENC:
            params.update({
                "hwaccel": "cuda",
                "extra_params": ["-tune", "ll", "-rc", "vbr_hq", "-cq", "23"]
            })
        elif hardware_type == HardwareType.INTEL_QSV:
            params.update({
                "hwaccel": "qsv",
                "extra_params": ["-global_quality", "23", "-preset", "veryfast"]
            })
        elif hardware_type == HardwareType.APPLE_VIDEOTOOLBOX:
            params.update({
                "hwaccel": "videotoolbox",
                "extra_params": ["-q:v", "23", "-allow_sw", "1"]
            })
        elif hardware_type == HardwareType.AMD_VCE:
            params.update({
                "hwaccel": "amf",
                "extra_params": ["-quality", "quality", "-rc", "cbr", "-b:v", "5000k"]
            })
        elif hardware_type == HardwareType.CUDA:
            params.update({
                "hwaccel": "cuda",
                "extra_params": ["-preset", "slow", "-rc", "vbr_hq"]
            })
        
        return params
    
    def update_config(self, hardware_type: HardwareType, config: AccelerationConfig):
        """更新硬件配置"""
        self.acceleration_configs[hardware_type] = config
        logger.info(f"更新 {hardware_type.value} 配置")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.performance_stats.copy()
        
        # 计算成功率
        total = stats["total_accelerated_tasks"]
        if total > 0:
            stats["success_rate"] = stats["successful_accelerations"] / total
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def record_acceleration(self, hardware_type: HardwareType, success: bool, 
                          processing_time: float, speedup: float = 1.0):
        """记录加速结果"""
        self.performance_stats["total_accelerated_tasks"] += 1
        
        if success:
            self.performance_stats["successful_accelerations"] += 1
            
            # 更新平均加速比
            current_avg = self.performance_stats["average_speedup"]
            successful_count = self.performance_stats["successful_accelerations"]
            self.performance_stats["average_speedup"] = (
                (current_avg * (successful_count - 1) + speedup) / successful_count
            )
        else:
            self.performance_stats["failed_accelerations"] += 1
        
        logger.info(f"硬件加速记录: {hardware_type.value}, 成功: {success}, "
                   f"加速比: {speedup:.2f}x")
    
    def is_hardware_available(self, hardware_type: HardwareType) -> bool:
        """检查硬件是否可用"""
        if hardware_type not in self.hardware_info:
            return False
        
        hw_info = self.hardware_info[hardware_type]
        if not hw_info.is_available:
            return False
        
        # 检查使用率
        usage = self.get_hardware_usage(hardware_type)
        config = self.acceleration_configs[hardware_type]
        
        return usage.get("usage_percent", 0) < 90
    
    def get_optimal_settings(self, task_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """获取最优设置"""
        task_type = task_requirements.get("type", "general_processing")
        codec = task_requirements.get("codec", "libx264")
        quality = task_requirements.get("quality", "medium")
        speed = task_requirements.get("speed", "medium")
        
        # 推荐硬件
        recommended_hw = self.recommend_hardware(task_type, {"codecs": [codec]})
        
        # 获取加速参数
        accel_params = self.get_acceleration_params(recommended_hw, codec)
        
        # 根据质量和速度调整参数
        if quality == "high":
            if recommended_hw in [HardwareType.NVIDIA_NVENC, HardwareType.INTEL_QSV]:
                accel_params["extra_params"].extend(["-rc", "vbr_hq", "-cq", "20"])
            else:
                accel_params["extra_params"].extend(["-crf", "20"])
        elif quality == "low":
            if recommended_hw in [HardwareType.NVIDIA_NVENC, HardwareType.INTEL_QSV]:
                accel_params["extra_params"].extend(["-cq", "28"])
            else:
                accel_params["extra_params"].extend(["-crf", "28"])
        
        # 根据速度调整预设
        if speed == "fast":
            accel_params["extra_params"].extend(["-preset", "veryfast"])
        elif speed == "slow":
            accel_params["extra_params"].extend(["-preset", "slow"])
        
        return {
            "hardware_type": recommended_hw,
            "acceleration_params": accel_params,
            "optimization_tips": self._get_optimization_tips(recommended_hw, task_requirements)
        }
    
    def _get_optimization_tips(self, hardware_type: HardwareType, 
                               requirements: Dict[str, Any]) -> List[str]:
        """获取优化建议"""
        tips = []
        
        if hardware_type == HardwareType.NVIDIA_NVENC:
            tips.append("使用NVENC时，建议开启-rc vbr_hq以获得更好的质量")
            tips.append("对于4K视频，建议使用hevc_nvenc编码器")
        elif hardware_type == HardwareType.INTEL_QSV:
            tips.append("使用QSV时，建议设置-look_ahead 1以提高质量")
            tips.append("对于低延迟场景，建议使用-preset veryfast")
        elif hardware_type == HardwareType.CPU:
            tips.append("CPU编码时，建议使用多线程: -threads 0")
            tips.append("对于高质量编码，建议使用-preset slow")
        
        return tips
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理硬件加速管理器资源")
        
        # 停止监控
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("硬件加速管理器资源清理完成")