#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CineAI Studio 构建和打包系统
提供应用程序的构建、打包、签名和分发功能
"""

import os
import sys
import shutil
import hashlib
import json
import logging
import platform
import subprocess
import tempfile
import zipfile
import tarfile
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class BuildTarget(Enum):
    """构建目标平台"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class BuildType(Enum):
    """构建类型"""
    DEBUG = "debug"
    RELEASE = "release"
    BETA = "beta"


class Architecture(Enum):
    """处理器架构"""
    X86 = "x86"
    X86_64 = "x86_64"
    ARM64 = "arm64"
    UNIVERSAL = "universal"


@dataclass
class BuildConfig:
    """构建配置"""
    target: BuildTarget
    build_type: BuildType
    architecture: Architecture
    version: str
    build_number: int
    output_dir: str = "dist"
    source_dir: str = "."
    include_tests: bool = False
    include_docs: bool = True
    include_examples: bool = True
    strip_symbols: bool = True
    optimize: bool = True
    compress: bool = True
    sign: bool = True
    notarize: bool = True  # macOS公证
    create_installer: bool = True
    portable: bool = False


@dataclass
class BuildArtifact:
    """构建产物"""
    name: str
    path: str
    size: int
    checksum: str
    build_time: str
    platform: str
    architecture: str
    version: str
    build_number: int


class BuildSystem:
    """构建系统"""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.artifacts: List[BuildArtifact] = []
        self.build_log: List[str] = []
        self.temp_dir = None

    def build(self) -> bool:
        """执行构建"""
        start_time = time.time()
        self.log(f"开始构建: {self.config.target.value} {self.config.architecture.value}")

        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="cineai_build_")
            self.log(f"创建临时目录: {self.temp_dir}")

            # 准备构建环境
            if not self._prepare_build_environment():
                return False

            # 安装依赖
            if not self._install_dependencies():
                return False

            # 构建应用程序
            if not self._build_application():
                return False

            # 复制资源文件
            if not self._copy_resources():
                return False

            # 优化和压缩
            if self.config.optimize:
                if not self._optimize_build():
                    return False

            # 创建分发包
            if not self._create_distribution():
                return False

            # 签名（如果需要）
            if self.config.sign:
                if not self._sign_artifacts():
                    return False

            # 公证（macOS）
            if self.config.notarize and self.config.target == BuildTarget.MACOS:
                if not self._notarize_artifacts():
                    return False

            # 创建安装程序
            if self.config.create_installer:
                if not self._create_installer():
                    return False

            build_time = time.time() - start_time
            self.log(f"构建完成，耗时: {build_time:.1f}秒")
            return True

        except Exception as e:
            self.log(f"构建失败: {str(e)}", level="ERROR")
            return False
        finally:
            # 清理临时目录
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log("清理临时目录完成")

    def _prepare_build_environment(self) -> bool:
        """准备构建环境"""
        self.log("准备构建环境...")

        # 检查Python版本
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.log("需要Python 3.8或更高版本", level="ERROR")
            return False

        # 检查必要的工具
        required_tools = self._get_required_tools()
        for tool in required_tools:
            if not self._check_tool_available(tool):
                self.log(f"缺少必要工具: {tool}", level="ERROR")
                return False

        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)

        self.log("构建环境准备完成")
        return True

    def _get_required_tools(self) -> List[str]:
        """获取必需的工具"""
        tools = ["python", "pip"]

        if self.config.target == BuildTarget.WINDOWS:
            tools.extend(["pyinstaller", "nsis"])
        elif self.config.target == BuildTarget.MACOS:
            tools.extend(["py2app", "codesign", "xcrun"])
        elif self.config.target == BuildTarget.LINUX:
            tools.extend(["pyinstaller", "fpm"])

        return tools

    def _check_tool_available(self, tool: str) -> bool:
        """检查工具是否可用"""
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _install_dependencies(self) -> bool:
        """安装依赖"""
        self.log("安装依赖...")

        # 升级pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

        # 安装项目依赖
        requirements_file = Path(self.config.source_dir) / "requirements.txt"
        if requirements_file.exists():
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.log(f"安装依赖失败: {result.stderr}", level="ERROR")
                return False

        self.log("依赖安装完成")
        return True

    def _build_application(self) -> bool:
        """构建应用程序"""
        self.log("构建应用程序...")

        if self.config.target == BuildTarget.WINDOWS:
            return self._build_windows()
        elif self.config.target == BuildTarget.MACOS:
            return self._build_macos()
        elif self.config.target == BuildTarget.LINUX:
            return self._build_linux()
        else:
            self.log(f"不支持的构建目标: {self.config.target}", level="ERROR")
            return False

    def _build_windows(self) -> bool:
        """构建Windows版本"""
        self.log("构建Windows版本...")

        # 创建PyInstaller配置
        spec_file = self._create_pyinstaller_spec()

        # 运行PyInstaller
        cmd = [
            "pyinstaller",
            "--clean",
            "--noconfirm",
            spec_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.log(f"PyInstaller构建失败: {result.stderr}", level="ERROR")
            return False

        self.log("Windows版本构建完成")
        return True

    def _build_macos(self) -> bool:
        """构建macOS版本"""
        self.log("构建macOS版本...")

        # 创建py2app配置
        setup_py = self._create_py2app_setup()

        # 运行py2app
        cmd = [
            sys.executable,
            "setup.py",
            "py2app"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.log(f"py2app构建失败: {result.stderr}", level="ERROR")
            return False

        self.log("macOS版本构建完成")
        return True

    def _build_linux(self) -> bool:
        """构建Linux版本"""
        self.log("构建Linux版本...")

        # 创建PyInstaller配置
        spec_file = self._create_pyinstaller_spec()

        # 运行PyInstaller
        cmd = [
            "pyinstaller",
            "--clean",
            "--noconfirm",
            spec_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.log(f"PyInstaller构建失败: {result.stderr}", level="ERROR")
            return False

        self.log("Linux版本构建完成")
        return True

    def _create_pyinstaller_spec(self) -> str:
        """创建PyInstaller配置文件"""
        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['{self.config.source_dir}'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('app/plugins', 'app/plugins'),
        ('app/ui', 'app/ui'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'numpy',
        'opencv-python',
        'requests',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive={not self.config.compress},
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CineAIStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip={self.config.strip_symbols},
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.icns' if platform.system() == 'Darwin' else 'resources/icons/app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip={self.config.strip_symbols},
    upx=True,
    upx_exclude=[],
    name='CineAIStudio',
)
"""

        spec_file = os.path.join(self.temp_dir, "CineAIStudio.spec")
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        return spec_file

    def _create_py2app_setup(self) -> str:
        """创建py2app配置文件"""
        setup_content = f"""from setuptools import setup
import py2app

setup(
    name="CineAIStudio",
    version="{self.config.version}",
    app=["main.py"],
    data_files=[
        ("resources", ["resources"]),
        ("app/plugins", ["app/plugins"]),
        ("app/ui", ["app/ui"]),
    ],
    options={{"py2app": {{"iconfile": "resources/icons/app_icon.icns",
                "includes": ["PyQt6", "numpy", "cv2", "requests", "PIL"],
                "packages": ["app"],
                "optimize": 1 if self.config.optimize else 0}}}},
    setup_requires=["py2app"],
)
"""

        setup_file = os.path.join(self.temp_dir, "setup.py")
        with open(setup_file, 'w', encoding='utf-8') as f:
            f.write(setup_content)

        return setup_file

    def _copy_resources(self) -> bool:
        """复制资源文件"""
        self.log("复制资源文件...")

        source_dir = Path(self.config.source_dir)
        build_dir = Path(self.config.output_dir) / "build"

        # 复制资源目录
        resources_dir = source_dir / "resources"
        if resources_dir.exists():
            target_resources = build_dir / "resources"
            shutil.copytree(resources_dir, target_resources)
            self.log("资源文件复制完成")

        # 复制插件目录
        plugins_dir = source_dir / "app" / "plugins"
        if plugins_dir.exists():
            target_plugins = build_dir / "app" / "plugins"
            shutil.copytree(plugins_dir, target_plugins)
            self.log("插件文件复制完成")

        # 复制文档
        if self.config.include_docs:
            docs_dir = source_dir / "docs"
            if docs_dir.exists():
                target_docs = build_dir / "docs"
                shutil.copytree(docs_dir, target_docs)
                self.log("文档文件复制完成")

        return True

    def _optimize_build(self) -> bool:
        """优化构建"""
        self.log("优化构建...")

        build_dir = Path(self.config.output_dir) / "build"

        # 移除不必要的文件
        for pattern in ["*.pyc", "*.pyo", "*.pyd", "__pycache__", "*.pyx", "*.pxd"]:
            for file_path in build_dir.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()

        # 压缩资源
        if self.config.compress:
            for resource_dir in ["resources", "app/plugins", "app/ui"]:
                dir_path = build_dir / resource_dir
                if dir_path.exists():
                    self._compress_directory(dir_path)

        self.log("构建优化完成")
        return True

    def _compress_directory(self, directory: Path):
        """压缩目录"""
        zip_path = directory.parent / f"{directory.name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(directory)
                    zipf.write(file_path, arcname)

        # 删除原目录
        shutil.rmtree(directory)

    def _create_distribution(self) -> bool:
        """创建分发包"""
        self.log("创建分发包...")

        build_dir = Path(self.config.output_dir) / "build"

        if self.config.target == BuildTarget.WINDOWS:
            return self._create_windows_distribution(build_dir)
        elif self.config.target == BuildTarget.MACOS:
            return self._create_macos_distribution(build_dir)
        elif self.config.target == BuildTarget.LINUX:
            return self._create_linux_distribution(build_dir)

        return False

    def _create_windows_distribution(self, build_dir: Path) -> bool:
        """创建Windows分发包"""
        self.log("创建Windows分发包...")

        # 创建ZIP包
        if self.config.portable:
            zip_name = f"CineAIStudio-{self.config.version}-windows-{self.config.architecture.value}-portable.zip"
            zip_path = Path(self.config.output_dir) / zip_name

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in build_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(build_dir)
                        zipf.write(file_path, arcname)

            self.artifacts.append(self._create_artifact(zip_name, zip_path))
            self.log(f"创建便携版ZIP包: {zip_name}")

        # 创建安装程序
        if self.config.create_installer and not self.config.portable:
            self._create_windows_installer(build_dir)

        return True

    def _create_macos_distribution(self, build_dir: Path) -> bool:
        """创建macOS分发包"""
        self.log("创建macOS分发包...")

        # 创建DMG文件
        dmg_name = f"CineAIStudio-{self.config.version}-macos-{self.config.architecture.value}.dmg"
        dmg_path = Path(self.config.output_dir) / dmg_name

        # 使用create-dmg工具创建DMG
        try:
            cmd = [
                "create-dmg",
                "--volname", f"CineAIStudio {self.config.version}",
                "--volicon", "resources/icons/app_icon.icns",
                "--window-pos", "200", "120",
                "--window-size", "800", "400",
                "--icon-size", "100",
                "--icon", "CineAIStudio.app", "200", "190",
                "--app-drop-link", "600", "185",
                str(dmg_path),
                str(build_dir)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.artifacts.append(self._create_artifact(dmg_name, dmg_path))
                self.log(f"创建DMG文件: {dmg_name}")
            else:
                self.log(f"创建DMG失败: {result.stderr}", level="ERROR")

        except FileNotFoundError:
            self.log("create-dmg工具未找到，跳过DMG创建")

        return True

    def _create_linux_distribution(self, build_dir: Path) -> bool:
        """创建Linux分发包"""
        self.log("创建Linux分发包...")

        # 创建tar.gz包
        tar_name = f"CineAIStudio-{self.config.version}-linux-{self.config.architecture.value}.tar.gz"
        tar_path = Path(self.config.output_dir) / tar_name

        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(build_dir, arcname="CineAIStudio")

        self.artifacts.append(self._create_artifact(tar_name, tar_path))
        self.log(f"创建tar.gz包: {tar_name}")

        # 创建DEB包（Ubuntu/Debian）
        if self.config.create_installer:
            self._create_deb_package(build_dir)

        # 创建RPM包（RedHat/Fedora）
        if self.config.create_installer:
            self._create_rpm_package(build_dir)

        return True

    def _create_windows_installer(self, build_dir: Path):
        """创建Windows安装程序"""
        self.log("创建Windows安装程序...")

        # 创建NSIS脚本
        nsis_script = self._create_nsis_script()

        # 运行NSIS
        try:
            cmd = ["makensis", nsis_script]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                installer_name = f"CineAIStudio-{self.config.version}-windows-{self.config.architecture.value}-setup.exe"
                installer_path = Path(self.config.output_dir) / installer_name
                self.artifacts.append(self._create_artifact(installer_name, installer_path))
                self.log(f"创建安装程序: {installer_name}")
            else:
                self.log(f"NSIS构建失败: {result.stderr}", level="ERROR")

        except FileNotFoundError:
            self.log("NSIS工具未找到，跳过安装程序创建")

    def _create_nsis_script(self) -> str:
        """创建NSIS脚本"""
        script_content = f"""OutFile "CineAIStudio-{self.config.version}-windows-{self.config.architecture.value}-setup.exe"
InstallDir "$PROGRAMFILES\\CineAIStudio"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "CineAIStudio"
    SetOutPath "$INSTDIR"
    File /r "build\\*.*"
    CreateDirectory "$SMPROGRAMS\\CineAIStudio"
    CreateShortCut "$SMPROGRAMS\\CineAIStudio\\CineAIStudio.lnk" "$INSTDIR\\CineAIStudio.exe"
SectionEnd
"""

        script_file = os.path.join(self.temp_dir, "installer.nsi")
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)

        return script_file

    def _create_deb_package(self, build_dir: Path):
        """创建DEB包"""
        self.log("创建DEB包...")

        # 使用fpm工具
        try:
            cmd = [
                "fpm",
                "-s", "dir",
                "-t", "deb",
                "-n", "cineaistudio",
                "-v", self.config.version,
                "--description", "CineAI Studio - AI视频编辑软件",
                "--url", "https://cineaistudio.com",
                "--license", "MIT",
                "--maintainer", "CineAI Studio Team <support@cineaistudio.com>",
                "--category", "video",
                "-C", str(build_dir),
                ".=/usr/share/cineaistudio"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                deb_name = f"cineaistudio_{self.config.version}_amd64.deb"
                self.artifacts.append(self._create_artifact(deb_name, Path(self.config.output_dir) / deb_name))
                self.log(f"创建DEB包: {deb_name}")
            else:
                self.log(f"DEB包创建失败: {result.stderr}", level="ERROR")

        except FileNotFoundError:
            self.log("fpm工具未找到，跳过DEB包创建")

    def _create_rpm_package(self, build_dir: Path):
        """创建RPM包"""
        self.log("创建RPM包...")

        # 使用fpm工具
        try:
            cmd = [
                "fpm",
                "-s", "dir",
                "-t", "rpm",
                "-n", "cineaistudio",
                "-v", self.config.version,
                "--description", "CineAI Studio - AI视频编辑软件",
                "--url", "https://cineaistudio.com",
                "--license", "MIT",
                "--maintainer", "CineAI Studio Team <support@cineaistudio.com>",
                "--category", "Applications/Multimedia",
                "-C", str(build_dir),
                ".=/usr/share/cineaistudio"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                rpm_name = f"cineaistudio-{self.config.version}-1.x86_64.rpm"
                self.artifacts.append(self._create_artifact(rpm_name, Path(self.config.output_dir) / rpm_name))
                self.log(f"创建RPM包: {rpm_name}")
            else:
                self.log(f"RPM包创建失败: {result.stderr}", level="ERROR")

        except FileNotFoundError:
            self.log("fpm工具未找到，跳过RPM包创建")

    def _sign_artifacts(self) -> bool:
        """签名构建产物"""
        self.log("签名构建产物...")

        if self.config.target == BuildTarget.WINDOWS:
            return self._sign_windows_artifacts()
        elif self.config.target == BuildTarget.MACOS:
            return self._sign_macos_artifacts()
        elif self.config.target == BuildTarget.LINUX:
            return self._sign_linux_artifacts()

        return True

    def _sign_windows_artifacts(self) -> bool:
        """签名Windows产物"""
        self.log("签名Windows产物...")

        # 使用signtool签名
        try:
            for artifact in self.artifacts:
                if artifact.path.endswith('.exe') or artifact.path.endswith('.dll'):
                    cmd = [
                        "signtool",
                        "sign",
                        "/f", "codesign.pfx",
                        "/p", "your_password",
                        "/t", "http://timestamp.digicert.com",
                        artifact.path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log(f"签名成功: {artifact.name}")
                    else:
                        self.log(f"签名失败: {artifact.name} - {result.stderr}", level="ERROR")
                        return False

        except FileNotFoundError:
            self.log("signtool工具未找到，跳过签名")

        return True

    def _sign_macos_artifacts(self) -> bool:
        """签名macOS产物"""
        self.log("签名macOS产物...")

        try:
            for artifact in self.artifacts:
                if artifact.path.endswith('.app') or artifact.path.endswith('.dmg'):
                    cmd = [
                        "codesign",
                        "--deep",
                        "--force",
                        "--verify",
                        "--verbose",
                        "--sign", "Developer ID Application: Your Company (Your Team ID)",
                        artifact.path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log(f"签名成功: {artifact.name}")
                    else:
                        self.log(f"签名失败: {artifact.name} - {result.stderr}", level="ERROR")
                        return False

        except FileNotFoundError:
            self.log("codesign工具未找到，跳过签名")

        return True

    def _sign_linux_artifacts(self) -> bool:
        """签名Linux产物"""
        self.log("签名Linux产物...")

        # Linux通常使用GPG签名
        try:
            for artifact in self.artifacts:
                cmd = [
                    "gpg",
                    "--detach-sign",
                    "--armor",
                    artifact.path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log(f"签名成功: {artifact.name}")
                else:
                    self.log(f"签名失败: {artifact.name} - {result.stderr}", level="ERROR")
                    return False

        except FileNotFoundError:
            self.log("gpg工具未找到，跳过签名")

        return True

    def _notarize_artifacts(self) -> bool:
        """公证macOS产物"""
        self.log("公证macOS产物...")

        try:
            for artifact in self.artifacts:
                if artifact.path.endswith('.dmg'):
                    # 上传到Apple进行公证
                    cmd = [
                        "xcrun",
                        "altool",
                        "--notarize-app",
                        "--primary-bundle-id", "com.cineaistudio.CineAIStudio",
                        "--username", "your_apple_id@example.com",
                        "--password", "your_app_password",
                        "--file", artifact.path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log(f"公证成功: {artifact.name}")
                    else:
                        self.log(f"公证失败: {artifact.name} - {result.stderr}", level="ERROR")
                        return False

        except FileNotFoundError:
            self.log("altool工具未找到，跳过公证")

        return True

    def _create_installer(self) -> bool:
        """创建安装程序"""
        self.log("创建安装程序...")

        # 安装程序创建已在各平台特定方法中处理
        return True

    def _create_artifact(self, name: str, path: Path) -> BuildArtifact:
        """创建构建产物记录"""
        file_size = path.stat().st_size
        checksum = self._calculate_checksum(path)

        return BuildArtifact(
            name=name,
            path=str(path),
            size=file_size,
            checksum=checksum,
            build_time=datetime.now().isoformat(),
            platform=self.config.target.value,
            architecture=self.config.architecture.value,
            version=self.config.version,
            build_number=self.config.build_number
        )

    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {level}: {message}"
        self.build_log.append(log_entry)
        print(log_entry)

        if level == "ERROR":
            logger.error(message)

    def get_build_report(self) -> Dict[str, Any]:
        """获取构建报告"""
        return {
            "config": asdict(self.config),
            "artifacts": [asdict(artifact) for artifact in self.artifacts],
            "build_log": self.build_log,
            "build_time": datetime.now().isoformat(),
            "success": len(self.artifacts) > 0
        }

    def save_build_report(self, filename: str):
        """保存构建报告"""
        report = self.get_build_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


class ReleaseManager:
    """发布管理器"""

    def __init__(self, output_dir: str = "dist"):
        self.output_dir = Path(output_dir)
        self.release_notes: Dict[str, str] = {}
        self.changelogs: Dict[str, str] = {}

    def create_release(self, version: str, artifacts: List[BuildArtifact], release_notes: str = "") -> Dict[str, Any]:
        """创建发布版本"""
        release_info = {
            "version": version,
            "release_date": datetime.now().isoformat(),
            "artifacts": [asdict(artifact) for artifact in artifacts],
            "release_notes": release_notes,
            "platforms": list(set(artifact.platform for artifact in artifacts)),
            "total_size": sum(artifact.size for artifact in artifacts) // (1024 * 1024),  # MB
            "download_count": 0
        }

        # 保存发布信息
        release_file = self.output_dir / f"release_{version}.json"
        with open(release_file, 'w', encoding='utf-8') as f:
            json.dump(release_info, f, ensure_ascii=False, indent=2)

        self.release_notes[version] = release_notes
        return release_info

    def generate_update_manifest(self) -> Dict[str, Any]:
        """生成更新清单"""
        manifest = {
            "latest_version": "",
            "releases": [],
            "generated_at": datetime.now().isoformat()
        }

        # 收集所有发布版本
        release_files = list(self.output_dir.glob("release_*.json"))
        latest_version = "0.0.0"

        for release_file in release_files:
            with open(release_file, 'r', encoding='utf-8') as f:
                release_info = json.load(f)
                manifest["releases"].append(release_info)

                # 更新最新版本
                if release_info["version"] > latest_version:
                    latest_version = release_info["version"]

        manifest["latest_version"] = latest_version

        # 保存更新清单
        manifest_file = self.output_dir / "update_manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return manifest

    def create_checksums_file(self) -> str:
        """创建校验和文件"""
        checksums = {}

        for file_path in self.output_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                relative_path = file_path.relative_to(self.output_dir)
                checksum = self._calculate_file_checksum(file_path)
                checksums[str(relative_path)] = checksum

        checksums_file = self.output_dir / "checksums.txt"
        with open(checksums_file, 'w', encoding='utf-8') as f:
            for file_path, checksum in checksums.items():
                f.write(f"{checksum}  {file_path}\n")

        return str(checksums_file)

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()