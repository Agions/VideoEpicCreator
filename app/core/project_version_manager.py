#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目版本控制系统 - 提供专业的项目版本管理功能
"""

import json
import os
import uuid
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal
import logging

from app.core.project import Project, ProjectInfo


@dataclass
class VersionCommit:
    """版本提交记录"""
    id: str
    project_id: str
    version: str
    message: str
    author: str
    timestamp: str
    file_hash: str
    file_size: int
    changes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionCommit':
        return cls(**data)


@dataclass
class VersionBranch:
    """版本分支"""
    name: str
    project_id: str
    commit_id: str
    created_at: str
    created_by: str
    description: str = ""
    is_main: bool = False
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionBranch':
        return cls(**data)


@dataclass
class VersionTag:
    """版本标签"""
    name: str
    project_id: str
    commit_id: str
    created_at: str
    created_by: str
    description: str = ""
    release_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionTag':
        return cls(**data)


class ProjectVersionManager(QObject):
    """项目版本管理器"""
    
    # 信号定义
    commit_created = pyqtSignal(VersionCommit)         # 提交创建信号
    commit_reverted = pyqtSignal(VersionCommit)       # 提交回滚信号
    branch_created = pyqtSignal(VersionBranch)         # 分支创建信号
    branch_merged = pyqtSignal(str, str)               # 分支合并信号
    tag_created = pyqtSignal(VersionTag)               # 标签创建信号
    version_restored = pyqtSignal(str)                  # 版本恢复信号
    error_occurred = pyqtSignal(str)                   # 错误信号
    
    def __init__(self, versions_dir: str = None):
        super().__init__()
        
        self.versions_dir = Path(versions_dir or Path.home() / "CineAIStudio" / "Versions")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # 版本数据
        self._commits: Dict[str, VersionCommit] = {}
        self._branches: Dict[str, VersionBranch] = {}
        self._tags: Dict[str, VersionTag] = {}
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
    
    def create_commit(self, project: Project, version: str, message: str, 
                     author: str = "User", changes: Dict[str, Any] = None) -> Optional[VersionCommit]:
        """创建版本提交"""
        try:
            if not project.project_info:
                return None
            
            project_id = project.project_info.id
            
            # 保存项目文件
            commit_file = self._save_project_version(project, version)
            if not commit_file:
                return None
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(commit_file)
            file_size = os.path.getsize(commit_file)
            
            # 创建提交记录
            commit = VersionCommit(
                id=str(uuid.uuid4()),
                project_id=project_id,
                version=version,
                message=message,
                author=author,
                timestamp=datetime.now().isoformat(),
                file_hash=file_hash,
                file_size=file_size,
                changes=changes or {}
            )
            
            # 获取当前分支的最新提交作为父提交
            current_branch = self._get_current_branch(project_id)
            if current_branch:
                commit.parent_id = current_branch.commit_id
            
            # 保存提交记录
            self._commits[commit.id] = commit
            
            # 更新分支指向
            if current_branch:
                current_branch.commit_id = commit.id
                self._branches[current_branch.name] = current_branch
            
            # 保存版本数据
            self._save_version_data(project_id)
            
            self.commit_created.emit(commit)
            self._logger.info(f"创建版本提交: {project_id} v{version}")
            
            return commit
            
        except Exception as e:
            error_msg = f"创建版本提交失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def create_branch(self, project_id: str, branch_name: str, 
                     from_commit_id: str = None, description: str = "",
                     created_by: str = "User") -> Optional[VersionBranch]:
        """创建分支"""
        try:
            # 检查分支名称是否已存在
            if branch_name in self._branches:
                self.error_occurred.emit(f"分支 '{branch_name}' 已存在")
                return None
            
            # 确定基础提交
            if not from_commit_id:
                # 使用当前分支的最新提交
                current_branch = self._get_current_branch(project_id)
                from_commit_id = current_branch.commit_id if current_branch else None
            
            # 创建分支
            branch = VersionBranch(
                name=branch_name,
                project_id=project_id,
                commit_id=from_commit_id,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                description=description,
                is_main=False,
                is_active=True
            )
            
            self._branches[branch_name] = branch
            
            # 保存版本数据
            self._save_version_data(project_id)
            
            self.branch_created.emit(branch)
            self._logger.info(f"创建分支: {branch_name}")
            
            return branch
            
        except Exception as e:
            error_msg = f"创建分支失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def merge_branch(self, project_id: str, source_branch: str, 
                    target_branch: str = "main", message: str = "",
                    author: str = "User") -> bool:
        """合并分支"""
        try:
            source = self._branches.get(source_branch)
            target = self._branches.get(target_branch)
            
            if not source or not target:
                self.error_occurred.emit("分支不存在")
                return False
            
            if source.project_id != project_id or target.project_id != project_id:
                self.error_occurred.emit("项目ID不匹配")
                return False
            
            # 简单合并：将目标分支指向源分支的提交
            target.commit_id = source.commit_id
            
            # 保存版本数据
            self._save_version_data(project_id)
            
            self.branch_merged.emit(source_branch, target_branch)
            self._logger.info(f"合并分支: {source_branch} -> {target_branch}")
            
            return True
            
        except Exception as e:
            error_msg = f"合并分支失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def create_tag(self, project_id: str, tag_name: str, commit_id: str,
                  description: str = "", release_notes: str = "",
                  created_by: str = "User") -> Optional[VersionTag]:
        """创建标签"""
        try:
            # 检查标签名称是否已存在
            if tag_name in self._tags:
                self.error_occurred.emit(f"标签 '{tag_name}' 已存在")
                return None
            
            # 检查提交是否存在
            if commit_id not in self._commits:
                self.error_occurred.emit("提交不存在")
                return None
            
            # 创建标签
            tag = VersionTag(
                name=tag_name,
                project_id=project_id,
                commit_id=commit_id,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                description=description,
                release_notes=release_notes
            )
            
            self._tags[tag_name] = tag
            
            # 保存版本数据
            self._save_version_data(project_id)
            
            self.tag_created.emit(tag)
            self._logger.info(f"创建标签: {tag_name}")
            
            return tag
            
        except Exception as e:
            error_msg = f"创建标签失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def restore_version(self, project_id: str, commit_id: str) -> Optional[str]:
        """恢复到指定版本"""
        try:
            commit = self._commits.get(commit_id)
            if not commit:
                self.error_occurred.emit("提交不存在")
                return None
            
            if commit.project_id != project_id:
                self.error_occurred.emit("项目ID不匹配")
                return None
            
            # 查找版本文件
            version_file = self._get_version_file(project_id, commit_id)
            if not version_file or not os.path.exists(version_file):
                self.error_occurred.emit("版本文件不存在")
                return None
            
            self.version_restored.emit(commit_id)
            self._logger.info(f"恢复版本: {commit_id}")
            
            return version_file
            
        except Exception as e:
            error_msg = f"恢复版本失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def get_commit_history(self, project_id: str, branch: str = None, 
                          limit: int = 50) -> List[VersionCommit]:
        """获取提交历史"""
        try:
            commits = []
            
            # 确定起始提交
            if branch:
                branch_obj = self._branches.get(branch)
                if not branch_obj or branch_obj.project_id != project_id:
                    return []
                current_commit_id = branch_obj.commit_id
            else:
                # 获取所有相关提交
                current_commit_id = None
            
            # 构建提交历史
            if current_commit_id:
                current_id = current_commit_id
                while current_id and len(commits) < limit:
                    commit = self._commits.get(current_id)
                    if not commit:
                        break
                    
                    if commit.project_id == project_id:
                        commits.append(commit)
                    
                    current_id = commit.parent_id
            else:
                # 获取项目的所有提交
                for commit in self._commits.values():
                    if commit.project_id == project_id:
                        commits.append(commit)
                
                # 按时间排序
                commits.sort(key=lambda x: x.timestamp, reverse=True)
                commits = commits[:limit]
            
            return commits
            
        except Exception as e:
            self._logger.error(f"获取提交历史失败: {e}")
            return []
    
    def get_branches(self, project_id: str) -> List[VersionBranch]:
        """获取项目分支"""
        return [b for b in self._branches.values() if b.project_id == project_id]
    
    def get_tags(self, project_id: str) -> List[VersionTag]:
        """获取项目标签"""
        return [t for t in self._tags.values() if t.project_id == project_id]
    
    def get_commit_by_id(self, commit_id: str) -> Optional[VersionCommit]:
        """根据ID获取提交"""
        return self._commits.get(commit_id)
    
    def get_branch_by_name(self, branch_name: str) -> Optional[VersionBranch]:
        """根据名称获取分支"""
        return self._branches.get(branch_name)
    
    def get_tag_by_name(self, tag_name: str) -> Optional[VersionTag]:
        """根据名称获取标签"""
        return self._tags.get(tag_name)
    
    def get_version_diff(self, commit_id1: str, commit_id2: str) -> Dict[str, Any]:
        """获取版本差异"""
        try:
            commit1 = self._commits.get(commit_id1)
            commit2 = self._commits.get(commit_id2)
            
            if not commit1 or not commit2:
                return {}
            
            diff = {
                'commit1': commit1.to_dict(),
                'commit2': commit2.to_dict(),
                'time_diff': self._calculate_time_diff(commit1.timestamp, commit2.timestamp),
                'size_diff': commit2.file_size - commit1.file_size,
                'changes_summary': self._summarize_changes(commit1.changes, commit2.changes)
            }
            
            return diff
            
        except Exception as e:
            self._logger.error(f"获取版本差异失败: {e}")
            return {}
    
    def delete_branch(self, branch_name: str) -> bool:
        """删除分支"""
        try:
            branch = self._branches.get(branch_name)
            if not branch:
                return False
            
            # 不能删除主分支
            if branch.is_main:
                self.error_occurred.emit("不能删除主分支")
                return False
            
            del self._branches[branch_name]
            
            # 保存版本数据
            self._save_version_data(branch.project_id)
            
            self._logger.info(f"删除分支: {branch_name}")
            return True
            
        except Exception as e:
            error_msg = f"删除分支失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_tag(self, tag_name: str) -> bool:
        """删除标签"""
        try:
            tag = self._tags.get(tag_name)
            if not tag:
                return False
            
            del self._tags[tag_name]
            
            # 保存版本数据
            self._save_version_data(tag.project_id)
            
            self._logger.info(f"删除标签: {tag_name}")
            return True
            
        except Exception as e:
            error_msg = f"删除标签失败: {e}"
            self._logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def _save_project_version(self, project: Project, version: str) -> Optional[str]:
        """保存项目版本"""
        try:
            project_dir = self.versions_dir / project.project_info.id
            project_dir.mkdir(exist_ok=True)
            
            version_file = project_dir / f"v{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.vecp"
            
            # 保存项目
            if project.save_to_file(str(version_file)):
                return str(version_file)
            
            return None
            
        except Exception as e:
            self._logger.error(f"保存项目版本失败: {e}")
            return None
    
    def _get_version_file(self, project_id: str, commit_id: str) -> Optional[str]:
        """获取版本文件路径"""
        try:
            commit = self._commits.get(commit_id)
            if not commit:
                return None
            
            project_dir = self.versions_dir / project_id
            if not project_dir.exists():
                return None
            
            # 查找对应的版本文件
            for file in project_dir.glob("*.vecp"):
                file_hash = self._calculate_file_hash(file)
                if file_hash == commit.file_hash:
                    return str(file)
            
            return None
            
        except Exception as e:
            self._logger.error(f"获取版本文件失败: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_current_branch(self, project_id: str) -> Optional[VersionBranch]:
        """获取当前分支"""
        # 优先返回主分支
        main_branch = self._branches.get("main")
        if main_branch and main_branch.project_id == project_id:
            return main_branch
        
        # 返回项目的任意活动分支
        for branch in self._branches.values():
            if branch.project_id == project_id and branch.is_active:
                return branch
        
        # 创建主分支
        if "main" not in self._branches:
            main_branch = VersionBranch(
                name="main",
                project_id=project_id,
                commit_id="",
                created_at=datetime.now().isoformat(),
                created_by="System",
                description="主分支",
                is_main=True,
                is_active=True
            )
            self._branches["main"] = main_branch
        
        return main_branch
    
    def _save_version_data(self, project_id: str):
        """保存版本数据"""
        try:
            project_dir = self.versions_dir / project_id
            project_dir.mkdir(exist_ok=True)
            
            # 保存提交数据
            commits_file = project_dir / "commits.json"
            project_commits = {k: v.to_dict() for k, v in self._commits.items() 
                             if v.project_id == project_id}
            with open(commits_file, 'w', encoding='utf-8') as f:
                json.dump(project_commits, f, indent=2, ensure_ascii=False)
            
            # 保存分支数据
            branches_file = project_dir / "branches.json"
            project_branches = {k: v.to_dict() for k, v in self._branches.items() 
                              if v.project_id == project_id}
            with open(branches_file, 'w', encoding='utf-8') as f:
                json.dump(project_branches, f, indent=2, ensure_ascii=False)
            
            # 保存标签数据
            tags_file = project_dir / "tags.json"
            project_tags = {k: v.to_dict() for k, v in self._tags.items() 
                          if v.project_id == project_id}
            with open(tags_file, 'w', encoding='utf-8') as f:
                json.dump(project_tags, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self._logger.error(f"保存版本数据失败: {e}")
    
    def _load_version_data(self, project_id: str):
        """加载版本数据"""
        try:
            project_dir = self.versions_dir / project_id
            if not project_dir.exists():
                return
            
            # 加载提交数据
            commits_file = project_dir / "commits.json"
            if commits_file.exists():
                with open(commits_file, 'r', encoding='utf-8') as f:
                    commits_data = json.load(f)
                for k, v in commits_data.items():
                    self._commits[k] = VersionCommit.from_dict(v)
            
            # 加载分支数据
            branches_file = project_dir / "branches.json"
            if branches_file.exists():
                with open(branches_file, 'r', encoding='utf-8') as f:
                    branches_data = json.load(f)
                for k, v in branches_data.items():
                    self._branches[k] = VersionBranch.from_dict(v)
            
            # 加载标签数据
            tags_file = project_dir / "tags.json"
            if tags_file.exists():
                with open(tags_file, 'r', encoding='utf-8') as f:
                    tags_data = json.load(f)
                for k, v in tags_data.items():
                    self._tags[k] = VersionTag.from_dict(v)
                    
        except Exception as e:
            self._logger.error(f"加载版本数据失败: {e}")
    
    def _calculate_time_diff(self, timestamp1: str, timestamp2: str) -> str:
        """计算时间差"""
        try:
            time1 = datetime.fromisoformat(timestamp1)
            time2 = datetime.fromisoformat(timestamp2)
            diff = abs(time2 - time1)
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}天{hours}小时"
            elif hours > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{minutes}分钟"
                
        except Exception:
            return "未知"
    
    def _summarize_changes(self, changes1: Dict[str, Any], changes2: Dict[str, Any]) -> Dict[str, Any]:
        """总结变更"""
        try:
            summary = {
                'added': [],
                'modified': [],
                'removed': []
            }
            
            # 简单的变更分析
            all_keys = set(changes1.keys()) | set(changes2.keys())
            
            for key in all_keys:
                if key not in changes1:
                    summary['added'].append(key)
                elif key not in changes2:
                    summary['removed'].append(key)
                elif changes1[key] != changes2[key]:
                    summary['modified'].append(key)
            
            return summary
            
        except Exception as e:
            self._logger.error(f"总结变更失败: {e}")
            return {'added': [], 'modified': [], 'removed': []}
    
    def get_version_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取版本统计信息"""
        try:
            project_commits = [c for c in self._commits.values() if c.project_id == project_id]
            project_branches = [b for b in self._branches.values() if b.project_id == project_id]
            project_tags = [t for t in self._tags.values() if t.project_id == project_id]
            
            stats = {
                'total_commits': len(project_commits),
                'total_branches': len(project_branches),
                'total_tags': len(project_tags),
                'total_size': sum(c.file_size for c in project_commits),
                'first_commit': min(c.timestamp for c in project_commits) if project_commits else None,
                'latest_commit': max(c.timestamp for c in project_commits) if project_commits else None,
                'active_branches': len([b for b in project_branches if b.is_active]),
                'authors': list(set(c.author for c in project_commits))
            }
            
            return stats
            
        except Exception as e:
            self._logger.error(f"获取版本统计失败: {e}")
            return {}
    
    def cleanup_old_versions(self, project_id: str, max_versions: int = 50):
        """清理旧版本"""
        try:
            project_dir = self.versions_dir / project_id
            if not project_dir.exists():
                return
            
            # 获取所有版本文件
            version_files = list(project_dir.glob("*.vecp"))
            version_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除超过限制的版本文件
            for file in version_files[max_versions:]:
                try:
                    file.unlink()
                    self._logger.info(f"删除旧版本文件: {file}")
                except Exception as e:
                    self._logger.error(f"删除版本文件失败 {file}: {e}")
                    
        except Exception as e:
            self._logger.error(f"清理旧版本失败: {e}")