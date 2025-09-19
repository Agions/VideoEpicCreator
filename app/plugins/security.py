#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件安全和沙箱机制
提供插件的安全检查、权限控制、资源限制和沙箱隔离功能
"""

import ast
import importlib
import inspect
import logging
import os
import psutil
import resource
import signal
import subprocess
import sys
import threading
import time
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""
    NONE = 0           # 无安全限制
    LOW = 1            # 低安全级别，基本检查
    MEDIUM = 2         # 中等安全级别，权限控制
    HIGH = 3           # 高安全级别，沙箱隔离
    MAXIMUM = 4        # 最高安全级别，完全隔离


class Permission(Enum):
    """插件权限"""
    NETWORK = "network"                    # 网络访问
    FILE_READ = "file_read"                # 文件读取
    FILE_WRITE = "file_write"              # 文件写入
    PROCESS_EXECUTE = "process_execute"    # 进程执行
    SYSTEM_ACCESS = "system_access"        # 系统访问
    HARDWARE_ACCESS = "hardware_access"    # 硬件访问
    CAMERA_ACCESS = "camera_access"        # 摄像头访问
    MICROPHONE_ACCESS = "microphone_access"  # 麦克风访问
    LOCATION_ACCESS = "location_access"    # 位置访问
    CONTACTS_ACCESS = "contacts_access"    # 联系人访问
    CLIPBOARD_ACCESS = "clipboard_access"  # 剪贴板访问


class SecurityRisk(Enum):
    """安全风险级别"""
    SAFE = 0           # 安全
    LOW_RISK = 1      # 低风险
    MEDIUM_RISK = 2   # 中等风险
    HIGH_RISK = 3     # 高风险
    CRITICAL = 4      # 严重风险


@dataclass
class SecurityPolicy:
    """安全策略"""
    level: SecurityLevel = SecurityLevel.MEDIUM
    allowed_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    allowed_file_paths: List[str] = field(default_factory=list)
    blocked_file_paths: List[str] = field(default_factory=list)
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    max_execution_time: int = 300  # 秒
    enable_sandbox: bool = True
    enable_code_signing: bool = True
    enable_signature_verification: bool = True


@dataclass
class SecurityReport:
    """安全检查报告"""
    plugin_id: str
    risk_level: SecurityRisk
    vulnerabilities: List[Dict[str, Any]]
    permission_issues: List[Dict[str, Any]]
    resource_usage: Dict[str, Any]
    security_score: int
    recommendations: List[str]
    timestamp: str


class CodeAnalyzer:
    """代码安全分析器"""

    def __init__(self):
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input', 'raw_input',
            'os.system', 'os.popen', 'os.exec', 'os.spawn',
            'subprocess.run', 'subprocess.Popen', 'subprocess.call',
            'commands.getstatusoutput', 'commands.getoutput',
            'pickle.load', 'pickle.loads', 'cPickle.load', 'cPickle.loads',
            'marshal.load', 'marshal.loads',
            'ctypes.', 'win32api.', 'win32con.', 'win32gui.',
            'socket.socket', 'urllib.', 'urllib2.', 'requests.',
            'shutil.rmtree', 'os.remove', 'os.unlink', 'os.rmdir',
            'tempfile.mktemp', 'tempfile.NamedTemporaryFile'
        }

        self.suspicious_patterns = [
            ('password', '密码相关'),
            ('token', '令牌相关'),
            ('key', '密钥相关'),
            ('secret', '机密相关'),
            ('credential', '凭证相关'),
            ('auth', '认证相关'),
            ('login', '登录相关'),
            ('hack', '黑客相关'),
            ('crack', '破解相关'),
            ('exploit', '漏洞利用'),
            ('backdoor', '后门'),
            ('trojan', '木马'),
            ('virus', '病毒'),
            ('malware', '恶意软件')
        ]

    def analyze_code(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """分析代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                'syntax_error': str(e),
                'risk_level': SecurityRisk.HIGH_RISK,
                'vulnerabilities': [{'type': 'syntax_error', 'message': str(e)}]
            }

        vulnerabilities = []
        permission_requests = set()

        # 分析AST
        self._analyze_ast(tree, vulnerabilities, permission_requests)

        # 检查危险函数调用
        self._check_dangerous_functions(code, vulnerabilities)

        # 检查可疑模式
        self._check_suspicious_patterns(code, vulnerabilities)

        # 计算风险级别
        risk_level = self._calculate_risk_level(vulnerabilities)

        return {
            'risk_level': risk_level,
            'vulnerabilities': vulnerabilities,
            'permission_requests': list(permission_requests),
            'code_size': len(code),
            'file_path': file_path
        }

    def _analyze_ast(self, node: ast.AST, vulnerabilities: List[Dict], permissions: Set[Permission]):
        """分析抽象语法树"""
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    self._check_import(alias.name, vulnerabilities, permissions)
            elif isinstance(child, ast.ImportFrom):
                if child.module:
                    self._check_import(child.module, vulnerabilities, permissions)
            elif isinstance(child, ast.Call):
                self._check_function_call(child, vulnerabilities, permissions)
            elif isinstance(child, ast.Attribute):
                self._check_attribute_access(child, vulnerabilities, permissions)

    def _check_import(self, module_name: str, vulnerabilities: List[Dict], permissions: Set[Permission]):
        """检查导入模块"""
        dangerous_modules = {
            'os': '操作系统访问',
            'sys': '系统模块',
            'subprocess': '进程执行',
            'commands': '命令执行',
            'ctypes': 'C库调用',
            'win32api': 'Windows API',
            'socket': '网络套接字',
            'urllib': 'URL访问',
            'urllib2': 'URL访问',
            'requests': 'HTTP请求',
            'pickle': '对象序列化',
            'marshal': '对象序列化',
            'shutil': '文件操作',
            'tempfile': '临时文件',
            'glob': '文件模式匹配'
        }

        if module_name in dangerous_modules:
            vulnerabilities.append({
                'type': 'dangerous_import',
                'module': module_name,
                'description': f"导入危险模块: {dangerous_modules[module_name]}",
                'line': getattr(module_name, 'lineno', 0)
            })

            # 添加权限请求
            if module_name in ['socket', 'urllib', 'urllib2', 'requests']:
                permissions.add(Permission.NETWORK)
            elif module_name in ['os', 'sys', 'subprocess', 'commands']:
                permissions.add(Permission.SYSTEM_ACCESS)
            elif module_name in ['shutil', 'tempfile', 'glob']:
                permissions.add(Permission.FILE_WRITE)

    def _check_function_call(self, node: ast.Call, vulnerabilities: List[Dict], permissions: Set[Permission]):
        """检查函数调用"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.dangerous_functions:
                vulnerabilities.append({
                    'type': 'dangerous_function',
                    'function': func_name,
                    'description': f"调用危险函数: {func_name}",
                    'line': node.lineno
                })

                # 添加权限请求
                if func_name in ['eval', 'exec']:
                    permissions.add(Permission.SYSTEM_ACCESS)
                elif func_name in ['open', 'file']:
                    permissions.add(Permission.FILE_READ)
                elif func_name in ['os.system', 'subprocess.run']:
                    permissions.add(Permission.PROCESS_EXECUTE)

    def _check_attribute_access(self, node: ast.Attribute, vulnerabilities: List[Dict], permissions: Set[Permission]):
        """检查属性访问"""
        if isinstance(node.value, ast.Name):
            full_name = f"{node.value.id}.{node.attr}"
            if any(dangerous in full_name for dangerous in self.dangerous_functions):
                vulnerabilities.append({
                    'type': 'dangerous_attribute',
                    'attribute': full_name,
                    'description': f"访问危险属性: {full_name}",
                    'line': node.lineno
                })

    def _check_dangerous_functions(self, code: str, vulnerabilities: List[Dict]):
        """检查危险函数使用"""
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for func in self.dangerous_functions:
                if func in line:
                    # 排除注释和字符串
                    stripped_line = line.strip()
                    if not stripped_line.startswith('#') and not stripped_line.startswith('"') and not stripped_line.startswith("'"):
                        vulnerabilities.append({
                            'type': 'dangerous_function',
                            'function': func,
                            'description': f"在第{i}行使用危险函数: {func}",
                            'line': i
                        })

    def _check_suspicious_patterns(self, code: str, vulnerabilities: List[Dict]):
        """检查可疑模式"""
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, description in self.suspicious_patterns:
                if pattern.lower() in line.lower():
                    # 排除注释
                    stripped_line = line.strip()
                    if not stripped_line.startswith('#'):
                        vulnerabilities.append({
                            'type': 'suspicious_pattern',
                            'pattern': pattern,
                            'description': f"在第{i}行发现可疑模式: {description}",
                            'line': i
                        })

    def _calculate_risk_level(self, vulnerabilities: List[Dict]) -> SecurityRisk:
        """计算风险级别"""
        if not vulnerabilities:
            return SecurityRisk.SAFE

        # 根据漏洞类型和数量计算风险
        high_risk_count = sum(1 for v in vulnerabilities if v['type'] in ['dangerous_function', 'dangerous_import'])
        medium_risk_count = sum(1 for v in vulnerabilities if v['type'] in ['suspicious_pattern'])
        low_risk_count = len(vulnerabilities) - high_risk_count - medium_risk_count

        if high_risk_count >= 3:
            return SecurityRisk.CRITICAL
        elif high_risk_count >= 1:
            return SecurityRisk.HIGH_RISK
        elif medium_risk_count >= 3:
            return SecurityRisk.MEDIUM_RISK
        elif medium_risk_count >= 1 or low_risk_count >= 5:
            return SecurityRisk.LOW_RISK
        else:
            return SecurityRisk.SAFE


class ResourceMonitor:
    """资源监控器"""

    def __init__(self, plugin_id: str, limits: Dict[str, Any]):
        self.plugin_id = plugin_id
        self.limits = limits
        self.process = None
        self.monitoring = False
        self.start_time = None
        self.peak_memory = 0
        self.total_cpu_time = 0
        self.network_bytes_sent = 0
        self.network_bytes_received = 0

    def start_monitoring(self, process):
        """开始监控"""
        self.process = process
        self.start_time = time.time()
        self.monitoring = True

        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)

    def _monitor_resources(self):
        """监控资源使用"""
        while self.monitoring and self.process:
            try:
                # 内存使用
                memory_info = self.process.memory_info()
                current_memory = memory_info.rss / 1024 / 1024  # MB
                self.peak_memory = max(self.peak_memory, current_memory)

                # CPU使用
                cpu_percent = self.process.cpu_percent()
                self.total_cpu_time += cpu_percent

                # 检查限制
                if 'max_memory_mb' in self.limits and current_memory > self.limits['max_memory_mb']:
                    logger.warning(f"插件 {self.plugin_id} 内存使用超限: {current_memory:.1f}MB > {self.limits['max_memory_mb']}MB")
                    self._enforce_limit('memory')

                if 'max_cpu_percent' in self.limits and cpu_percent > self.limits['max_cpu_percent']:
                    logger.warning(f"插件 {self.plugin_id} CPU使用超限: {cpu_percent:.1f}% > {self.limits['max_cpu_percent']}%")
                    self._enforce_limit('cpu')

                # 检查执行时间
                if self.start_time and 'max_execution_time' in self.limits:
                    execution_time = time.time() - self.start_time
                    if execution_time > self.limits['max_execution_time']:
                        logger.warning(f"插件 {self.plugin_id} 执行时间超限: {execution_time:.1f}s > {self.limits['max_execution_time']}s")
                        self._enforce_limit('time')

                time.sleep(1)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

    def _enforce_limit(self, limit_type: str):
        """强制执行限制"""
        try:
            if limit_type == 'memory':
                # 内存超限，降低进程优先级
                try:
                    self.process.nice(10)
                except:
                    pass
            elif limit_type == 'cpu':
                # CPU超限，限制CPU亲和性
                try:
                    self.process.cpu_affinity([0])  # 限制到第一个CPU核心
                except:
                    pass
            elif limit_type == 'time':
                # 时间超限，终止进程
                self.process.terminate()
                self.monitoring = False
        except:
            pass

    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用统计"""
        execution_time = 0
        if self.start_time:
            execution_time = time.time() - self.start_time

        return {
            'peak_memory_mb': self.peak_memory,
            'total_cpu_time': self.total_cpu_time,
            'execution_time': execution_time,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_received': self.network_bytes_received
        }


class PluginSandbox:
    """插件沙箱"""

    def __init__(self, plugin_id: str, security_policy: SecurityPolicy):
        self.plugin_id = plugin_id
        self.security_policy = security_policy
        self.resource_monitor = None
        self.allowed_paths = set(security_policy.allowed_file_paths)
        self.blocked_paths = set(security_policy.blocked_file_paths)
        self.allowed_domains = set(security_policy.allowed_domains)
        self.blocked_domains = set(security_policy.blocked_domains)

    def execute_plugin(self, plugin_code: str, plugin_globals: Dict = None) -> Any:
        """在沙箱中执行插件"""
        if not self.security_policy.enable_sandbox:
            # 如果不启用沙箱，直接执行
            exec(plugin_code, plugin_globals or {})
            return None

        # 创建受限的执行环境
        restricted_globals = self._create_restricted_globals(plugin_globals or {})

        try:
            # 执行插件代码
            exec(plugin_code, restricted_globals)
            return restricted_globals.get('__result__')
        except Exception as e:
            logger.error(f"插件 {self.plugin_id} 执行失败: {e}")
            raise

    def _create_restricted_globals(self, original_globals: Dict) -> Dict:
        """创建受限的全局变量"""
        # 基础内置函数
        safe_builtins = {
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
            'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate', 'filter',
            'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'iter',
            'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow',
            'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
            'str', 'sum', 'tuple', 'zip', '__import__'
        }

        # 创建受限的globals
        restricted_globals = {
            '__builtins__': {name: getattr(__builtins__, name) for name in safe_builtins if hasattr(__builtins__, name)},
            '__name__': '__main__',
            '__file__': f'<sandbox_{self.plugin_id}>',
            '__package__': None,
            '__doc__': None,
            '__result__': None
        }

        # 添加安全的模块
        safe_modules = {
            'math': math,
            'random': random,
            'datetime': datetime,
            'json': json,
            're': re,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            'operator': operator,
            'decimal': decimal,
            'fractions': fractions,
            'statistics': statistics,
            'typing': typing
        }

        # 根据权限添加模块
        if Permission.NETWORK in self.security_policy.allowed_permissions:
            # 允许网络访问的模块
            safe_modules.update({
                'urllib.parse': urllib.parse,
                'urllib.error': urllib.error,
            })

        restricted_globals.update(safe_modules)

        # 添加原始globals中的安全变量
        for key, value in original_globals.items():
            if not key.startswith('_') and key not in ['os', 'sys', 'subprocess', 'importlib']:
                restricted_globals[key] = value

        return restricted_globals

    def check_file_access(self, file_path: str, mode: str = 'r') -> bool:
        """检查文件访问权限"""
        path = Path(file_path)

        # 检查是否在允许路径中
        if self.allowed_paths:
            if not any(str(path).startswith(allowed) for allowed in self.allowed_paths):
                return False

        # 检查是否在阻止路径中
        if self.blocked_paths:
            if any(str(path).startswith(blocked) for blocked in self.blocked_paths):
                return False

        # 检查读写权限
        if 'w' in mode or 'a' in mode or '+' in mode:
            return Permission.FILE_WRITE in self.security_policy.allowed_permissions
        else:
            return Permission.FILE_READ in self.security_policy.allowed_permissions

    def check_network_access(self, url: str) -> bool:
        """检查网络访问权限"""
        if Permission.NETWORK not in self.security_policy.allowed_permissions:
            return False

        # 检查域名白名单
        if self.allowed_domains:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc not in self.allowed_domains:
                return False

        # 检查域名黑名单
        if self.blocked_domains:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc in self.blocked_domains:
                return False

        return True


class PluginSecurityManager:
    """插件安全管理器"""

    def __init__(self, security_policy: SecurityPolicy = None):
        self.security_policy = security_policy or SecurityPolicy()
        self.code_analyzer = CodeAnalyzer()
        self.active_sandboxes: Dict[str, PluginSandbox] = {}
        self.resource_monitors: Dict[str, ResourceMonitor] = {}
        self.security_reports: Dict[str, SecurityReport] = {}

    def analyze_plugin_security(self, plugin_id: str, plugin_path: str) -> SecurityReport:
        """分析插件安全性"""
        vulnerabilities = []
        permission_issues = []
        security_score = 100

        # 扫描插件文件
        plugin_files = self._scan_plugin_files(plugin_path)

        # 分析每个文件
        for file_path in plugin_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()

                analysis_result = self.code_analyzer.analyze_code(code, file_path)
                vulnerabilities.extend(analysis_result['vulnerabilities'])

                # 检查权限问题
                self._check_permission_issues(analysis_result, permission_issues)

                # 计算安全分数
                security_score -= len(analysis_result['vulnerabilities']) * 5

            except Exception as e:
                logger.error(f"分析文件失败 {file_path}: {e}")
                vulnerabilities.append({
                    'type': 'file_analysis_error',
                    'file': str(file_path),
                    'message': str(e)
                })
                security_score -= 10

        # 确定风险级别
        risk_level = self._determine_risk_level(vulnerabilities, permission_issues)

        # 生成建议
        recommendations = self._generate_recommendations(vulnerabilities, permission_issues)

        # 创建安全报告
        report = SecurityReport(
            plugin_id=plugin_id,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            permission_issues=permission_issues,
            resource_usage={},
            security_score=max(0, security_score),
            recommendations=recommendations,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
        )

        self.security_reports[plugin_id] = report
        return report

    def create_sandbox(self, plugin_id: str) -> PluginSandbox:
        """创建插件沙箱"""
        sandbox = PluginSandbox(plugin_id, self.security_policy)
        self.active_sandboxes[plugin_id] = sandbox
        return sandbox

    def execute_in_sandbox(self, plugin_id: str, code: str, globals_dict: Dict = None) -> Any:
        """在沙箱中执行代码"""
        if plugin_id not in self.active_sandboxes:
            sandbox = self.create_sandbox(plugin_id)
        else:
            sandbox = self.active_sandboxes[plugin_id]

        return sandbox.execute_plugin(code, globals_dict)

    def monitor_plugin_resources(self, plugin_id: str, process):
        """监控插件资源使用"""
        if plugin_id in self.resource_monitors:
            self.resource_monitors[plugin_id].stop_monitoring()

        monitor = ResourceMonitor(plugin_id, self.security_policy.resource_limits)
        monitor.start_monitoring(process)
        self.resource_monitors[plugin_id] = monitor

    def stop_monitoring(self, plugin_id: str):
        """停止监控插件"""
        if plugin_id in self.resource_monitors:
            self.resource_monitors[plugin_id].stop_monitoring()
            del self.resource_monitors[plugin_id]

    def get_plugin_security_report(self, plugin_id: str) -> Optional[SecurityReport]:
        """获取插件安全报告"""
        return self.security_reports.get(plugin_id)

    def is_plugin_safe(self, plugin_id: str) -> bool:
        """检查插件是否安全"""
        report = self.security_reports.get(plugin_id)
        if not report:
            return False

        return report.risk_level in [SecurityRisk.SAFE, SecurityRisk.LOW_RISK]

    def get_plugin_permissions(self, plugin_id: str) -> Set[Permission]:
        """获取插件所需权限"""
        report = self.security_reports.get(plugin_id)
        if not report:
            return set()

        # 从漏洞分析中提取权限需求
        permissions = set()
        for vuln in report.vulnerabilities:
            if 'permission_requests' in vuln:
                permissions.update(vuln['permission_requests'])

        return permissions

    def _scan_plugin_files(self, plugin_path: str) -> List[Path]:
        """扫描插件文件"""
        plugin_dir = Path(plugin_path)
        python_files = []

        for pattern in ['*.py', '**/*.py']:
            python_files.extend(plugin_dir.glob(pattern))

        return python_files

    def _check_permission_issues(self, analysis_result: Dict, permission_issues: List[Dict]):
        """检查权限问题"""
        requested_permissions = analysis_result.get('permission_requests', [])

        for permission in requested_permissions:
            if permission not in self.security_policy.allowed_permissions:
                permission_issues.append({
                    'type': 'missing_permission',
                    'permission': permission.value,
                    'description': f"插件需要 {permission.value} 权限但未授权"
                })

    def _determine_risk_level(self, vulnerabilities: List[Dict], permission_issues: List[Dict]) -> SecurityRisk:
        """确定风险级别"""
        total_issues = len(vulnerabilities) + len(permission_issues)

        if total_issues == 0:
            return SecurityRisk.SAFE
        elif total_issues <= 2:
            return SecurityRisk.LOW_RISK
        elif total_issues <= 5:
            return SecurityRisk.MEDIUM_RISK
        elif total_issues <= 10:
            return SecurityRisk.HIGH_RISK
        else:
            return SecurityRisk.CRITICAL

    def _generate_recommendations(self, vulnerabilities: List[Dict], permission_issues: List[Dict]) -> List[str]:
        """生成安全建议"""
        recommendations = []

        # 基于漏洞类型生成建议
        vuln_types = [v['type'] for v in vulnerabilities]
        permission_types = [p['type'] for p in permission_issues]

        if 'dangerous_function' in vuln_types:
            recommendations.append("避免使用危险的系统函数，考虑使用更安全的替代方案")

        if 'dangerous_import' in vuln_types:
            recommendations.append("避免导入不安全的模块，使用提供的API替代")

        if 'suspicious_pattern' in vuln_types:
            recommendations.append("移除可疑的代码模式，确保代码意图清晰")

        if 'missing_permission' in permission_types:
            recommendations.append("在插件配置中声明所需的权限")

        if not recommendations:
            recommendations.append("插件代码安全性良好，继续保持")

        return recommendations

    def cleanup_plugin(self, plugin_id: str):
        """清理插件资源"""
        # 停止沙箱
        if plugin_id in self.active_sandboxes:
            del self.active_sandboxes[plugin_id]

        # 停止监控
        self.stop_monitoring(plugin_id)

        # 清理安全报告
        if plugin_id in self.security_reports:
            del self.security_reports[plugin_id]

        logger.info(f"插件 {plugin_id} 安全资源已清理")