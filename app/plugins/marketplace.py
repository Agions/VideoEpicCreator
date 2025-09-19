#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件市场和分发系统
提供插件的发现、安装、更新和分发功能
"""

import json
import hashlib
import shutil
import zipfile
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QMessageBox

from app.plugins.plugin_system import PluginManager, PluginMetadata, PluginType
from app.plugins.plugin_config import PluginConfigManager

logger = logging.getLogger(__name__)


class PluginSourceType(Enum):
    """插件源类型"""
    OFFICIAL = "official"        # 官方源
    COMMUNITY = "community"      # 社区源
    PERSONAL = "personal"        # 个人源
    THIRD_PARTY = "third_party"  # 第三方源


class PluginReleaseChannel(Enum):
    """插件发布渠道"""
    STABLE = "stable"            # 稳定版
    BETA = "beta"               # 测试版
    ALPHA = "alpha"             # 开发版
    NIGHTLY = "nightly"         # 每夜版


@dataclass
class PluginSource:
    """插件源配置"""
    name: str
    url: str
    type: PluginSourceType
    description: str = ""
    enabled: bool = True
    priority: int = 0
    last_update: Optional[str] = None
    auth_token: Optional[str] = None
    verify_ssl: bool = True


@dataclass
class PluginPackage:
    """插件包信息"""
    id: str
    name: str
    version: str
    description: str
    author: str
    source: str
    download_url: str
    file_size: int
    checksum: str
    dependencies: List[str]
    compatibility: Dict[str, str]
    release_channel: PluginReleaseChannel
    publish_date: str
    download_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = None
    screenshots: List[str] = None
    changelog: str = ""
    min_app_version: str = ""
    max_app_version: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.screenshots is None:
            self.screenshots = []


@dataclass
class MarketplaceConfig:
    """插件市场配置"""
    sources: List[PluginSource] = None
    auto_update: bool = True
    update_interval: int = 3600  # 秒
    preferred_release_channel: PluginReleaseChannel = PluginReleaseChannel.STABLE
    install_path: str = ""
    cache_enabled: bool = True
    cache_max_size: int = 1024 * 1024 * 1024  # 1GB
    enable_beta_updates: bool = False

    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class PluginMarketplaceAPI(QObject):
    """插件市场API客户端"""

    repository_updated = pyqtSignal(str)  # source_name
    package_discovered = pyqtSignal(PluginPackage)
    download_progress = pyqtSignal(str, int, int)  # package_id, downloaded, total
    download_completed = pyqtSignal(str, str)  # package_id, file_path
    download_failed = pyqtSignal(str, str)  # package_id, error
    update_available = pyqtSignal(str, PluginPackage)  # plugin_id, new_package

    def __init__(self, config: MarketplaceConfig):
        super().__init__()
        self.config = config
        self._network_manager = QNetworkAccessManager()
        self._session = None
        self._packages: Dict[str, List[PluginPackage]] = {}  # source_name -> packages
        self._cache_dir = Path.home() / ".cineai_studio" / "marketplace_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化API客户端"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "CineAIStudio/2.0"}
        )

    async def cleanup(self):
        """清理资源"""
        if self._session:
            await self._session.close()

    async def update_repository(self, source: PluginSource) -> bool:
        """更新插件仓库"""
        try:
            # 构建仓库URL
            repo_url = f"{source.url.rstrip('/')}/repository.json"

            # 下载仓库信息
            async with self._session.get(repo_url, ssl=source.verify_ssl) as response:
                if response.status == 200:
                    repo_data = await response.json()
                    packages = self._parse_repository_data(repo_data, source)
                    self._packages[source.name] = packages

                    # 缓存仓库数据
                    cache_file = self._cache_dir / f"{source.name}_repository.json"
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(repo_data, f, ensure_ascii=False, indent=2)

                    source.last_update = datetime.now().isoformat()
                    self.repository_updated.emit(source.name)
                    return True
                else:
                    logger.error(f"更新仓库失败: {source.name} - HTTP {response.status}")
                    return False

        except Exception as e:
            logger.error(f"更新仓库异常: {source.name} - {e}")
            return False

    async def search_packages(self, query: str, plugin_type: Optional[PluginType] = None) -> List[PluginPackage]:
        """搜索插件包"""
        results = []

        for source_name, packages in self._packages.items():
            for package in packages:
                # 检查搜索条件
                if query.lower() in package.name.lower() or \
                   query.lower() in package.description.lower() or \
                   any(query.lower() in tag.lower() for tag in package.tags):

                    # 检查插件类型（如果有指定）
                    if plugin_type:
                        # 这里需要根据包信息判断插件类型
                        # 简化处理，假设包ID包含类型信息
                        if plugin_type.value not in package.id:
                            continue

                    results.append(package)

        # 按下载量和评分排序
        results.sort(key=lambda p: (p.download_count, p.rating), reverse=True)
        return results

    async def get_package_info(self, package_id: str, source_name: str) -> Optional[PluginPackage]:
        """获取包详细信息"""
        packages = self._packages.get(source_name, [])
        for package in packages:
            if package.id == package_id:
                return package
        return None

    async def download_package(self, package: PluginPackage, download_dir: Path) -> Optional[Path]:
        """下载插件包"""
        try:
            download_url = package.download_url
            file_path = download_dir / f"{package.id}-{package.version}.zip"

            # 检查是否已下载
            if file_path.exists():
                # 验证文件完整性
                if self._verify_file_checksum(file_path, package.checksum):
                    self.download_completed.emit(package.id, str(file_path))
                    return file_path
                else:
                    file_path.unlink()

            # 下载文件
            async with self._session.get(download_url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            # 更新进度
                            progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                            self.download_progress.emit(package.id, downloaded, total_size)

                    # 验证文件完整性
                    if self._verify_file_checksum(file_path, package.checksum):
                        self.download_completed.emit(package.id, str(file_path))
                        return file_path
                    else:
                        file_path.unlink()
                        self.download_failed.emit(package.id, "文件校验失败")
                        return None

                else:
                    self.download_failed.emit(package.id, f"下载失败: HTTP {response.status}")
                    return None

        except Exception as e:
            self.download_failed.emit(package.id, str(e))
            return None

    async def check_updates(self, installed_plugins: Dict[str, Dict[str, Any]]) -> List[Tuple[str, PluginPackage]]:
        """检查插件更新"""
        updates = []

        for plugin_id, plugin_info in installed_plugins.items():
            current_version = plugin_info.get("version", "0.0.0")

            # 在所有源中查找更新
            for source_name, packages in self._packages.items():
                for package in packages:
                    if package.id == plugin_id and self._is_newer_version(package.version, current_version):
                        # 检查兼容性
                        if self._check_compatibility(package, plugin_info):
                            updates.append((plugin_id, package))
                            break

        return updates

    def _parse_repository_data(self, repo_data: Dict[str, Any], source: PluginSource) -> List[PluginPackage]:
        """解析仓库数据"""
        packages = []

        for package_data in repo_data.get("packages", []):
            try:
                package = PluginPackage(
                    id=package_data["id"],
                    name=package_data["name"],
                    version=package_data["version"],
                    description=package_data.get("description", ""),
                    author=package_data.get("author", ""),
                    source=source.name,
                    download_url=package_data["download_url"],
                    file_size=package_data.get("file_size", 0),
                    checksum=package_data.get("checksum", ""),
                    dependencies=package_data.get("dependencies", []),
                    compatibility=package_data.get("compatibility", {}),
                    release_channel=PluginReleaseChannel(package_data.get("release_channel", "stable")),
                    publish_date=package_data.get("publish_date", ""),
                    download_count=package_data.get("download_count", 0),
                    rating=package_data.get("rating", 0.0),
                    rating_count=package_data.get("rating_count", 0),
                    tags=package_data.get("tags", []),
                    screenshots=package_data.get("screenshots", []),
                    changelog=package_data.get("changelog", ""),
                    min_app_version=package_data.get("min_app_version", ""),
                    max_app_version=package_data.get("max_app_version", "")
                )
                packages.append(package)
            except Exception as e:
                logger.error(f"解析包数据失败: {e}")

        return packages

    def _verify_file_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """验证文件校验和"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest() == expected_checksum
        except Exception:
            return False

    def _is_newer_version(self, new_version: str, current_version: str) -> bool:
        """检查是否为新版本"""
        try:
            # 简单的版本比较
            new_parts = [int(x) for x in new_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]

            # 补齐版本号长度
            max_len = max(len(new_parts), len(current_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))

            return new_parts > current_parts
        except Exception:
            return False

    def _check_compatibility(self, package: PluginPackage, plugin_info: Dict[str, Any]) -> bool:
        """检查插件兼容性"""
        # 检查应用版本兼容性
        app_version = plugin_info.get("app_version", "2.0.0")
        if package.min_app_version and app_version < package.min_app_version:
            return False
        if package.max_app_version and app_version > package.max_app_version:
            return False

        return True


class PluginInstaller(QObject):
    """插件安装器"""

    install_progress = pyqtSignal(str, int)  # package_id, progress
    install_completed = pyqtSignal(str, bool)  # package_id, success
    install_failed = pyqtSignal(str, str)  # package_id, error

    def __init__(self, install_path: str):
        super().__init__()
        self.install_path = Path(install_path)
        self.install_path.mkdir(parents=True, exist_ok=True)

    def install_package(self, package_path: Path, package: PluginPackage) -> bool:
        """安装插件包"""
        try:
            self.install_progress.emit(package.id, 0)

            # 创建临时目录
            temp_dir = self.install_path / "temp"
            temp_dir.mkdir(exist_ok=True)

            try:
                # 解压插件包
                self.install_progress.emit(package.id, 20)
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # 验证插件包结构
                self.install_progress.emit(package.id, 40)
                if not self._validate_package_structure(temp_dir, package):
                    self.install_failed.emit(package.id, "插件包结构无效")
                    return False

                # 检查依赖
                self.install_progress.emit(package.id, 60)
                if not self._check_dependencies(package):
                    self.install_failed.emit(package.id, "依赖检查失败")
                    return False

                # 安装插件文件
                self.install_progress.emit(package.id, 80)
                plugin_dir = self.install_path / package.id
                if plugin_dir.exists():
                    shutil.rmtree(plugin_dir)

                shutil.move(temp_dir, plugin_dir)

                self.install_progress.emit(package.id, 100)
                self.install_completed.emit(package.id, True)
                return True

            finally:
                # 清理临时目录
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            self.install_failed.emit(package.id, str(e))
            return False

    def uninstall_package(self, package_id: str) -> bool:
        """卸载插件包"""
        try:
            plugin_dir = self.install_path / package_id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            return True
        except Exception as e:
            logger.error(f"卸载插件失败: {package_id} - {e}")
            return False

    def _validate_package_structure(self, package_dir: Path, package: PluginPackage) -> bool:
        """验证插件包结构"""
        # 检查是否包含plugin.py或__init__.py
        if not (package_dir / "plugin.py").exists() and not (package_dir / "__init__.py").exists():
            logger.error(f"插件包缺少主文件: {package.id}")
            return False

        # 检查metadata.json（可选）
        metadata_file = package_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    # 验证元数据
                    if metadata.get("id") != package.id:
                        logger.error(f"插件ID不匹配: {package.id}")
                        return False
            except Exception as e:
                logger.error(f"读取元数据失败: {e}")
                return False

        return True

    def _check_dependencies(self, package: PluginPackage) -> bool:
        """检查依赖"""
        # 检查Python依赖
        import importlib.util
        for dep in package.dependencies:
            try:
                spec = importlib.util.find_spec(dep)
                if spec is None:
                    logger.error(f"缺少依赖: {dep}")
                    return False
            except Exception:
                logger.error(f"检查依赖失败: {dep}")
                return False

        return True


class PluginMarketplace(QObject):
    """插件市场主类"""

    def __init__(self, plugin_manager: PluginManager, config_manager: PluginConfigManager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.config_manager = config_manager
        self.config = self._load_config()
        self.api = PluginMarketplaceAPI(self.config)
        self.installer = PluginInstaller(self.config.install_path)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._auto_update_check)

        # 连接信号
        self.api.download_completed.connect(self._on_download_completed)
        self.installer.install_completed.connect(self._on_install_completed)
        self.installer.install_failed.connect(self._on_install_failed)

    async def initialize(self):
        """初始化插件市场"""
        await self.api.initialize()

        # 加载缓存的仓库数据
        self._load_cached_repositories()

        # 启动自动更新检查
        if self.config.auto_update:
            self._update_timer.start(self.config.update_interval * 1000)

    async def cleanup(self):
        """清理资源"""
        await self.api.cleanup()

    async def refresh_sources(self):
        """刷新所有插件源"""
        for source in self.config.sources:
            if source.enabled:
                await self.api.update_repository(source)

    async def search_plugins(self, query: str, plugin_type: Optional[PluginType] = None) -> List[PluginPackage]:
        """搜索插件"""
        return await self.api.search_packages(query, plugin_type)

    async def get_plugin_details(self, package_id: str, source_name: str) -> Optional[PluginPackage]:
        """获取插件详情"""
        return await self.api.get_package_info(package_id, source_name)

    async def install_plugin(self, package: PluginPackage) -> bool:
        """安装插件"""
        # 下载插件包
        download_dir = Path.home() / ".cineai_studio" / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        package_path = await self.api.download_package(package, download_dir)
        if not package_path:
            return False

        # 安装插件
        success = self.installer.install_package(package_path, package)

        # 清理下载文件
        if package_path.exists():
            package_path.unlink()

        return success

    async def uninstall_plugin(self, package_id: str) -> bool:
        """卸载插件"""
        return self.installer.uninstall_package(package_id)

    async def check_updates(self) -> List[Tuple[str, PluginPackage]]:
        """检查插件更新"""
        installed_plugins = self.plugin_manager.get_all_plugins()
        return await self.api.check_updates(installed_plugins)

    async def update_plugin(self, package_id: str, new_package: PluginPackage) -> bool:
        """更新插件"""
        # 先卸载旧版本
        await self.uninstall_plugin(package_id)

        # 安装新版本
        return await self.install_plugin(new_package)

    def add_source(self, source: PluginSource) -> bool:
        """添加插件源"""
        # 检查是否已存在
        for existing_source in self.config.sources:
            if existing_source.name == source.name:
                return False

        self.config.sources.append(source)
        self._save_config()
        return True

    def remove_source(self, source_name: str) -> bool:
        """移除插件源"""
        self.config.sources = [s for s in self.config.sources if s.name != source_name]
        self._save_config()
        return True

    def _load_config(self) -> MarketplaceConfig:
        """加载配置"""
        config_file = Path.home() / ".cineai_studio" / "marketplace_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return MarketplaceConfig(**data)
            except Exception as e:
                logger.error(f"加载市场配置失败: {e}")

        # 返回默认配置
        return MarketplaceConfig(
            install_path=str(Path.home() / ".cineai_studio" / "plugins"),
            sources=[
                PluginSource(
                    name="官方源",
                    url="https://plugins.cineaistudio.com",
                    type=PluginSourceType.OFFICIAL,
                    description="CineAI Studio官方插件源",
                    enabled=True,
                    priority=10
                )
            ]
        )

    def _save_config(self):
        """保存配置"""
        config_file = Path.home() / ".cineai_studio" / "marketplace_config.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存市场配置失败: {e}")

    def _load_cached_repositories(self):
        """加载缓存的仓库数据"""
        cache_dir = Path.home() / ".cineai_studio" / "marketplace_cache"
        if not cache_dir.exists():
            return

        for source in self.config.sources:
            cache_file = cache_dir / f"{source.name}_repository.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        repo_data = json.load(f)
                        packages = self.api._parse_repository_data(repo_data, source)
                        self.api._packages[source.name] = packages
                except Exception as e:
                    logger.error(f"加载缓存仓库失败: {source.name} - {e}")

    def _auto_update_check(self):
        """自动更新检查"""
        if not self.config.auto_update:
            return

        asyncio.create_task(self.refresh_sources())

    def _on_download_completed(self, package_id: str, file_path: str):
        """下载完成回调"""
        logger.info(f"插件下载完成: {package_id}")

    def _on_install_completed(self, package_id: str, success: bool):
        """安装完成回调"""
        if success:
            logger.info(f"插件安装成功: {package_id}")
            # 重新加载插件
            plugin_path = self.config.install_path / package_id
            self.plugin_manager.load_plugin(str(plugin_path))
        else:
            logger.error(f"插件安装失败: {package_id}")

    def _on_install_failed(self, package_id: str, error: str):
        """安装失败回调"""
        logger.error(f"插件安装失败: {package_id} - {error}")