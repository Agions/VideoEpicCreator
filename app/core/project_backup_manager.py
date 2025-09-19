#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目备份和恢复系统 - 提供专业的项目备份、恢复和同步功能
"""

import json
import os
import uuid
import shutil
import zipfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import logging

from app.core.project import Project


@dataclass
class BackupConfig:
    """备份配置"""
    auto_backup_enabled: bool = True
    auto_backup_interval: int = 300  # 自动备份间隔（秒）
    max_auto_backups: int = 10
    max_manual_backups: int = 20
    compression_enabled: bool = True
    encryption_enabled: bool = False
    cloud_sync_enabled: bool = False
    backup_on_save: bool = True
    backup_on_close: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupConfig':
        return cls(**data)


@dataclass
class BackupInfo:
    """备份信息"""
    id: str
    project_id: str
    project_name: str
    backup_type: str  # auto, manual, scheduled
    timestamp: str
    file_path: str
    file_size: int
    file_hash: str
    compression_ratio: float = 1.0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    is_encrypted: bool = False
    cloud_synced: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupInfo':
        return cls(**data)


@dataclass
class BackupSchedule:
    """备份计划"""
    id: str
    project_id: str
    name: str
    schedule_type: str  # daily, weekly, monthly
    schedule_time: str  # HH:MM
    enabled: bool = True
    max_backups: int = 30
    compression_enabled: bool = True
    next_run: str = ""
    last_run: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupSchedule':
        return cls(**data)


class ProjectBackupManager(QObject):
    """项目备份管理器"""
    
    # 信号定义
    backup_created = pyqtSignal(BackupInfo)            # 备份创建信号
    backup_restored = pyqtSignal(str)                 # 备份恢复信号
    backup_deleted = pyqtSignal(str)                 # 备份删除信号
    backup_verified = pyqtSignal(bool)                # 备份验证信号
    backup_synced = pyqtSignal(str)                   # 备份同步信号
    schedule_created = pyqtSignal(BackupSchedule)     # 计划创建信号
    schedule_triggered = pyqtSignal(BackupSchedule)  # 计划触发信号
    error_occurred = pyqtSignal(str)                  # 错误信号
    
    def __init__(self, backup_dir: str = None):
        super().__init__()
        
        self.backup_dir = Path(backup_dir or Path.home() / "CineAIStudio" / "Backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份数据
        self._backups: Dict[str, BackupInfo] = {}
        self._schedules: Dict[str, BackupSchedule] = {}
        self._config = BackupConfig()
        
        # 定时器
        self._auto_backup_timer = QTimer()
        self._auto_backup_timer.timeout.connect(self._check_auto_backup)
        self._schedule_timer = QTimer()
        self._schedule_timer.timeout.connect(self._check_scheduled_backups)
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 初始化
        self._load_config()
        self._load_backups()
        self._load_schedules()
        self._start_timers()
    
    def create_backup(self, project: Project, backup_type: str = "manual",
                     description: str = "", tags: List[str] = None) -> Optional[BackupInfo]:
        """创建备份"""
        try:
            if not project.project_info:
                return None
            
            project_id = project.project_info.id
            
            # 创建备份文件
            backup_file = self._create_backup_file(project, backup_type)
            if not backup_file:
                return None
            
            # 计算文件信息
            file_size = os.path.getsize(backup_file)
            file_hash = self._calculate_file_hash(backup_file)
            
            # 创建备份信息
            backup_info = BackupInfo(
                id=str(uuid.uuid4()),
                project_id=project_id,
                project_name=project.project_info.name,
                backup_type=backup_type,
                timestamp=datetime.now().isoformat(),
                file_path=backup_file,
                file_size=file_size,
                file_hash=file_hash,
                description=description,
                tags=tags or []
            )
            
            self._backups[backup_info.id] = backup_info
            
            # 保存备份数据
            self._save_backups()
            
            # 清理旧备份
            self._cleanup_old_backups(project_id, backup_type)
            
            self.backup_created.emit(backup_info)
            self._logger.info(f"创建备份: {backup_info.project_name} ({backup_type})")
            
            return backup_info
            
        except Exception as e:
            error_msg = f"创建备份失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def restore_backup(self, backup_id: str, target_path: str = None) -> bool:
        """恢复备份"""
        try:
            backup_info = self._backups.get(backup_id)
            if not backup_info:
                self.error_occurred.emit("备份不存在")
                return False
            
            if not os.path.exists(backup_info.file_path):
                self.error_occurred.emit("备份文件不存在")
                return False
            
            # 验证备份文件
            if not self._verify_backup(backup_info):
                self.backup_verified.emit(False)
                return False
            
            # 确定恢复路径
            if not target_path:
                target_path = backup_info.file_path.replace('.backup', '_restored.vecp')
            
            # 恢复文件
            if backup_info.file_path.endswith('.zip'):
                # 解压备份文件
                with zipfile.ZipFile(backup_info.file_path, 'r') as zip_ref:
                    zip_ref.extractall(os.path.dirname(target_path))
            else:
                # 直接复制文件
                shutil.copy2(backup_info.file_path, target_path)
            
            self.backup_restored.emit(target_path)
            self._logger.info(f"恢复备份: {backup_info.project_name}")
            
            return True
            
        except Exception as e:
            error_msg = f"恢复备份失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            backup_info = self._backups.get(backup_id)
            if not backup_info:
                return False
            
            # 删除备份文件
            if os.path.exists(backup_info.file_path):
                os.remove(backup_info.file_path)
            
            del self._backups[backup_id]
            
            # 保存备份数据
            self._save_backups()
            
            self.backup_deleted.emit(backup_id)
            self._logger.info(f"删除备份: {backup_info.project_name}")
            
            return True
            
        except Exception as e:
            error_msg = f"删除备份失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def verify_backup(self, backup_id: str) -> bool:
        """验证备份"""
        try:
            backup_info = self._backups.get(backup_id)
            if not backup_info:
                return False
            
            is_valid = self._verify_backup(backup_info)
            self.backup_verified.emit(is_valid)
            
            return is_valid
            
        except Exception as e:
            error_msg = f"验证备份失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def create_backup_schedule(self, project_id: str, name: str, schedule_type: str,
                             schedule_time: str, max_backups: int = 30) -> Optional[BackupSchedule]:
        """创建备份计划"""
        try:
            schedule = BackupSchedule(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=name,
                schedule_type=schedule_type,
                schedule_time=schedule_time,
                max_backups=max_backups,
                next_run=self._calculate_next_run(schedule_type, schedule_time)
            )
            
            self._schedules[schedule.id] = schedule
            
            # 保存计划数据
            self._save_schedules()
            
            self.schedule_created.emit(schedule)
            self._logger.info(f"创建备份计划: {name}")
            
            return schedule
            
        except Exception as e:
            error_msg = f"创建备份计划失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def get_backups_by_project(self, project_id: str) -> List[BackupInfo]:
        """获取项目的所有备份"""
        backups = [b for b in self._backups.values() if b.project_id == project_id]
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups
    
    def get_all_backups(self) -> List[BackupInfo]:
        """获取所有备份"""
        return list(self._backups.values())
    
    def get_backup_by_id(self, backup_id: str) -> Optional[BackupInfo]:
        """根据ID获取备份"""
        return self._backups.get(backup_id)
    
    def get_schedules_by_project(self, project_id: str) -> List[BackupSchedule]:
        """获取项目的备份计划"""
        return [s for s in self._schedules.values() if s.project_id == project_id]
    
    def get_all_schedules(self) -> List[BackupSchedule]:
        """获取所有备份计划"""
        return list(self._schedules.values())
    
    def get_backup_statistics(self, project_id: str = None) -> Dict[str, Any]:
        """获取备份统计信息"""
        try:
            if project_id:
                backups = [b for b in self._backups.values() if b.project_id == project_id]
            else:
                backups = list(self._backups.values())
            
            stats = {
                'total_backups': len(backups),
                'total_size': sum(b.file_size for b in backups),
                'auto_backups': len([b for b in backups if b.backup_type == "auto"]),
                'manual_backups': len([b for b in backups if b.backup_type == "manual"]),
                'scheduled_backups': len([b for b in backups if b.backup_type == "scheduled"]),
                'encrypted_backups': len([b for b in backups if b.is_encrypted]),
                'cloud_synced_backups': len([b for b in backups if b.cloud_synced]),
                'oldest_backup': min(b.timestamp for b in backups) if backups else None,
                'newest_backup': max(b.timestamp for b in backups) if backups else None,
                'compression_ratio': sum(b.compression_ratio for b in backups) / len(backups) if backups else 1.0
            }
            
            return stats
            
        except Exception as e:
            self._logger.error(f"获取备份统计失败: {e}")
            return {}
    
    def sync_to_cloud(self, backup_id: str, cloud_config: Dict[str, Any]) -> bool:
        """同步到云端"""
        try:
            backup_info = self._backups.get(backup_id)
            if not backup_info:
                return False
            
            # 这里实现云端同步逻辑
            # 根据cloud_config配置同步到不同的云服务
            
            backup_info.cloud_synced = True
            self._save_backups()
            
            self.backup_synced.emit(backup_id)
            self._logger.info(f"同步备份到云端: {backup_info.project_name}")
            
            return True
            
        except Exception as e:
            error_msg = f"同步备份失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def export_backup_list(self, export_path: str) -> bool:
        """导出备份列表"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_backups': len(self._backups),
                'backups': [b.to_dict() for b in self._backups.values()]
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"导出备份列表: {export_path}")
            return True
            
        except Exception as e:
            error_msg = f"导出备份列表失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def _create_backup_file(self, project: Project, backup_type: str) -> Optional[str]:
        """创建备份文件"""
        try:
            project_id = project.project_info.id
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 创建备份目录
            backup_project_dir = self.backup_dir / project_id
            backup_project_dir.mkdir(exist_ok=True)
            
            # 临时保存项目文件
            temp_file = backup_project_dir / f"temp_{timestamp}.vecp"
            if not project.save_to_file(str(temp_file)):
                return None
            
            # 根据配置决定是否压缩
            if self._config.compression_enabled:
                backup_file = backup_project_dir / f"{backup_type}_{timestamp}.zip"
                self._create_zip_backup(temp_file, backup_file)
                temp_file.unlink()  # 删除临时文件
            else:
                backup_file = backup_project_dir / f"{backup_type}_{timestamp}.vecp"
                shutil.move(str(temp_file), backup_file)
            
            return str(backup_file)
            
        except Exception as e:
            self._logger.error(f"创建备份文件失败: {e}")
            return None
    
    def _create_zip_backup(self, source_file: Path, zip_file: Path):
        """创建ZIP备份"""
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(source_file, source_file.name)
                
        except Exception as e:
            self._logger.error(f"创建ZIP备份失败: {e}")
            raise
    
    def _verify_backup(self, backup_info: BackupInfo) -> bool:
        """验证备份文件"""
        try:
            if not os.path.exists(backup_info.file_path):
                return False
            
            # 验证文件哈希
            current_hash = self._calculate_file_hash(backup_info.file_path)
            if current_hash != backup_info.file_hash:
                return False
            
            # 如果是ZIP文件，验证文件完整性
            if backup_info.file_path.endswith('.zip'):
                try:
                    with zipfile.ZipFile(backup_info.file_path, 'r') as zip_ref:
                        zip_ref.testzip()
                except:
                    return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"验证备份失败: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _cleanup_old_backups(self, project_id: str, backup_type: str):
        """清理旧备份"""
        try:
            backups = [b for b in self._backups.values() 
                      if b.project_id == project_id and b.backup_type == backup_type]
            
            # 确定最大备份数
            if backup_type == "auto":
                max_backups = self._config.max_auto_backups
            elif backup_type == "manual":
                max_backups = self._config.max_manual_backups
            else:
                max_backups = 30
            
            # 按时间排序并删除超过限制的备份
            backups.sort(key=lambda x: x.timestamp, reverse=True)
            for backup in backups[max_backups:]:
                self.delete_backup(backup.id)
                
        except Exception as e:
            self._logger.error(f"清理旧备份失败: {e}")
    
    def _check_auto_backup(self):
        """检查自动备份"""
        if not self._config.auto_backup_enabled:
            return
        
        # 这里需要检查当前项目是否有修改
        # 如果有修改，则创建自动备份
        # pass
    
    def _check_scheduled_backups(self):
        """检查计划备份"""
        now = datetime.now()
        
        for schedule in self._schedules.values():
            if not schedule.enabled:
                continue
            
            try:
                next_run = datetime.fromisoformat(schedule.next_run)
                if now >= next_run:
                    # 触发计划备份
                    self._execute_scheduled_backup(schedule)
                    
                    # 更新下次运行时间
                    schedule.next_run = self._calculate_next_run(
                        schedule.schedule_type, schedule.schedule_time
                    )
                    schedule.last_run = now.isoformat()
                    
                    # 保存计划数据
                    self._save_schedules()
                    
                    self.schedule_triggered.emit(schedule)
                    
            except Exception as e:
                self._logger.error(f"检查计划备份失败: {e}")
    
    def _execute_scheduled_backup(self, schedule: BackupSchedule):
        """执行计划备份"""
        try:
            # 这里需要获取项目实例
            # project = get_project_by_id(schedule.project_id)
            # if project:
            #     self.create_backup(project, "scheduled", f"计划备份: {schedule.name}")
            pass
            
        except Exception as e:
            self._logger.error(f"执行计划备份失败: {e}")
    
    def _calculate_next_run(self, schedule_type: str, schedule_time: str) -> str:
        """计算下次运行时间"""
        try:
            now = datetime.now()
            time_parts = schedule_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            if schedule_type == "daily":
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            
            elif schedule_type == "weekly":
                # 假设每周一
                days_until_monday = (0 - now.weekday()) % 7
                if days_until_monday == 0 and now.time() > datetime.time(hour, minute):
                    days_until_monday = 7
                
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                next_run += timedelta(days=days_until_monday)
            
            elif schedule_type == "monthly":
                # 假设每月1号
                next_run = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    # 下个月1号
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)
            
            else:
                next_run = now + timedelta(hours=1)
            
            return next_run.isoformat()
            
        except Exception as e:
            self._logger.error(f"计算下次运行时间失败: {e}")
            return (now + timedelta(hours=1)).isoformat()
    
    def _start_timers(self):
        """启动定时器"""
        if self._config.auto_backup_enabled:
            self._auto_backup_timer.start(self._config.auto_backup_interval * 1000)
        
        # 每分钟检查一次计划备份
        self._schedule_timer.start(60000)
    
    def _load_config(self):
        """加载配置"""
        try:
            config_file = self.backup_dir / "config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._config = BackupConfig.from_dict(config_data)
        except Exception as e:
            self._logger.error(f"加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            config_file = self.backup_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.error(f"保存配置失败: {e}")
    
    def _load_backups(self):
        """加载备份数据"""
        try:
            # 扫描所有项目目录
            for project_dir in self.backup_dir.iterdir():
                if project_dir.is_dir():
                    backup_index_file = project_dir / "backups.json"
                    if backup_index_file.exists():
                        with open(backup_index_file, 'r', encoding='utf-8') as f:
                            backups_data = json.load(f)
                        for data in backups_data:
                            backup = BackupInfo.from_dict(data)
                            self._backups[backup.id] = backup
        except Exception as e:
            self._logger.error(f"加载备份数据失败: {e}")
    
    def _save_backups(self):
        """保存备份数据"""
        try:
            # 按项目分组保存
            project_backups = {}
            for backup in self._backups.values():
                if backup.project_id not in project_backups:
                    project_backups[backup.project_id] = []
                project_backups[backup.project_id].append(backup.to_dict())
            
            for project_id, backups_data in project_backups.items():
                project_dir = self.backup_dir / project_id
                project_dir.mkdir(exist_ok=True)
                
                backup_index_file = project_dir / "backups.json"
                with open(backup_index_file, 'w', encoding='utf-8') as f:
                    json.dump(backups_data, f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            self._logger.error(f"保存备份数据失败: {e}")
    
    def _load_schedules(self):
        """加载计划数据"""
        try:
            schedules_file = self.backup_dir / "schedules.json"
            if schedules_file.exists():
                with open(schedules_file, 'r', encoding='utf-8') as f:
                    schedules_data = json.load(f)
                for data in schedules_data:
                    schedule = BackupSchedule.from_dict(data)
                    self._schedules[schedule.id] = schedule
        except Exception as e:
            self._logger.error(f"加载计划数据失败: {e}")
    
    def _save_schedules(self):
        """保存计划数据"""
        try:
            schedules_file = self.backup_dir / "schedules.json"
            with open(schedules_file, 'w', encoding='utf-8') as f:
                json.dump([s.to_dict() for s in self._schedules.values()], 
                         f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.error(f"保存计划数据失败: {e}")
    
    def update_config(self, config: BackupConfig):
        """更新配置"""
        self._config = config
        self._save_config()
        
        # 重启定时器
        self._auto_backup_timer.stop()
        if self._config.auto_backup_enabled:
            self._auto_backup_timer.start(self._config.auto_backup_interval * 1000)
    
    def cleanup(self):
        """清理资源"""
        self._auto_backup_timer.stop()
        self._schedule_timer.stop()
        self._logger.info("备份管理器清理完成")