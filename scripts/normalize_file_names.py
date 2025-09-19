#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件命名规范化脚本
将项目中的文件重命名为规范化的名称，提高代码可读性和维护性

命名规范：
- 使用下划线分隔的snake_case命名
- 消除无意义的命名
- 统一组件命名后缀
- 保持文件功能的明确性
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileNormalizer:
    """文件命名规范化工具"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.rename_map: Dict[str, str] = {}
        self.conflict_files: Set[str] = set()
        self.backup_dir = self.project_root / "backup_files"

    def analyze_file_structure(self) -> Dict[str, List[str]]:
        """分析当前文件结构"""
        logger.info("开始分析文件结构...")

        file_analysis = {
            "ui_components": [],
            "ui_pages": [],
            "core_modules": [],
            "ai_modules": [],
            "problematic_files": [],
            "deprecated_files": []
        }

        # 扫描app目录
        app_dir = self.project_root / "app"
        if app_dir.exists():
            self._scan_directory(app_dir, file_analysis)

        return file_analysis

    def _scan_directory(self, directory: Path, analysis: Dict[str, List[str]]):
        """扫描目录并分类文件"""
        for file_path in directory.rglob("*.py"):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.project_root)
                file_str = str(relative_path)

                # 分类文件
                if "ui/components" in file_str:
                    analysis["ui_components"].append(file_str)
                elif "ui/pages" in file_str:
                    analysis["ui_pages"].append(file_str)
                elif "core" in file_str:
                    analysis["core_modules"].append(file_str)
                elif "ai" in file_str:
                    analysis["ai_modules"].append(file_str)

                # 识别问题文件
                if self._is_problematic_file(file_str):
                    analysis["problematic_files"].append(file_str)

                # 识别废弃文件
                if self._is_deprecated_file(file_str):
                    analysis["deprecated_files"].append(file_str)

    def _is_problematic_file(self, file_path: str) -> bool:
        """识别问题文件"""
        problematic_patterns = [
            r".*_ui\.py$",           # 以_ui结尾但不够具体
            r".*_panel\.py$",        # 通用panel命名
            r".*_widget\.py$",       # 通用widget命名
            r".*_dialog\.py$",       # 通用dialog命名
            r".*_window\.py$",       # 通用window命名
            r"main.*\.py$",          # 重复的main文件
            r".*_manager.*\.py$",    # 重复的manager文件
        ]

        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in problematic_patterns)

    def _is_deprecated_file(self, file_path: str) -> bool:
        """识别废弃文件"""
        deprecated_indicators = [
            "enhanced_main_window",
            "video_player",
            "modern_navigation",
            "new_main_window",
            "timeline_widget",
            "theme_manager",  # 已被unified_theme_system替代
        ]

        return any(indicator in file_path for indicator in deprecated_indicators)

    def generate_rename_plan(self) -> Dict[str, str]:
        """生成重命名计划"""
        logger.info("生成文件重命名计划...")

        rename_plan = {}

        # UI组件重命名规则
        component_rename_rules = {
            # 通用组件重命名
            r"ai_tools_panel\.py$": "ai_tools_component.py",
            r"ai_content_generator\.py$": "content_generator_component.py",
            r"ai_subtitle_generator\.py$": "subtitle_generator_component.py",
            r"ai_scene_analyzer\.py$": "scene_analyzer_component.py",
            r"timeline_editor\.py$": "timeline_editor_component.py",
            r"video_preview_panel\.py$": "video_preview_component.py",
            r"media_library\.py$": "media_library_component.py",
            r"effects_panel\.py$": "effects_component.py",
            r"export_settings_panel\.py$": "export_settings_component.py",
            r"project_panel\.py$": "project_manager_component.py",
            r"keyframe_editor\.py$": "keyframe_editor_component.py",
            r"playback_controls\.py$": "playback_component.py",
            r"loading_indicator\.py$": "loading_component.py",

            # 专业组件重命名
            r"professional_effects_panel\.py$": "professional_effects_component.py",
            r"project_templates_dialog\.py$": "project_templates_dialog_component.py",
            r"project_settings_dialog\.py$": "project_settings_dialog_component.py",
            r"shortcut_manager\.py$": "shortcut_manager_component.py",
            r"multi_view_panel\.py$": "multi_view_component.py",
            r"optimized_timeline_editor\.py$": "optimized_timeline_component.py",
            r"preview_filters\.py$": "preview_filters_component.py",
        }

        # 页面重命名规则
        page_rename_rules = {
            r"home_page\.py$": "home_page.py",  # 保持不变
            r"projects_page\.py$": "projects_page.py",  # 保持不变
            r"ai_tools_page\.py$": "ai_tools_page.py",  # 保持不变
            r"video_editing_page\.py$": "video_editing_page.py",  # 保持不变
            r"export_page\.py$": "export_page.py",  # 保持不变
            r"subtitle_page\.py$": "subtitle_page.py",  # 保持不变
            r"analytics_page\.py$": "analytics_page.py",  # 保持不变
            r"effects_page\.py$": "effects_page.py",  # 保持不变
        }

        # 核心模块重命名规则
        core_rename_rules = {
            r"video_processor\.py$": "video_processor.py",  # 保持不变
            r"project_manager\.py$": "project_manager.py",  # 保持不变
            r"performance_optimizer\.py$": "performance_optimizer.py",  # 保持不变
            r"memory_manager\.py$": "memory_manager.py",  # 保持不变
            r"hardware_acceleration\.py$": "hardware_acceleration.py",  # 保持不变
            r"batch_processor\.py$": "batch_processor.py",  # 保持不变
            r"effects_engine\.py$": "effects_engine.py",  # 保持不变
            r"video_codec_manager\.py$": "video_codec_manager.py",  # 保持不变
            r"video_optimizer\.py$": "video_optimizer.py",  # 保持不变
        }

        # 应用重命名规则
        all_rules = {**component_rename_rules, **page_rename_rules, **core_rename_rules}

        for file_path in self.project_root.rglob("*.py"):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.project_root)
                file_str = str(relative_path)

                for pattern, new_name in all_rules.items():
                    if re.search(pattern, file_str, re.IGNORECASE):
                        old_full_path = self.project_root / file_str
                        new_full_path = old_full_path.parent / new_name

                        if old_full_path != new_full_path:
                            rename_plan[str(old_full_path)] = str(new_full_path)
                        break

        # 检查冲突
        self._check_rename_conflicts(rename_plan)

        return rename_plan

    def _check_rename_conflicts(self, rename_plan: Dict[str, str]):
        """检查重命名冲突"""
        logger.info("检查重命名冲突...")

        target_files = set(rename_plan.values())
        existing_files = set()

        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                existing_files.add(str(file_path))

        conflicts = target_files.intersection(existing_files)
        if conflicts:
            logger.warning(f"发现重命名冲突: {conflicts}")
            self.conflict_files.update(conflicts)

    def backup_files(self, file_list: List[str]):
        """备份文件"""
        logger.info(f"备份 {len(file_list)} 个文件...")

        self.backup_dir.mkdir(exist_ok=True)

        for file_path in file_list:
            src_path = Path(file_path)
            if src_path.exists():
                # 保持目录结构
                relative_path = src_path.relative_to(self.project_root)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(src_path, backup_path)
                logger.info(f"已备份: {file_path}")

    def apply_rename_plan(self, rename_plan: Dict[str, str], dry_run: bool = True):
        """应用重命名计划"""
        logger.info(f"应用重命名计划 (dry_run={dry_run})...")

        if dry_run:
            logger.info("=== 重命名计划 (预览) ===")
            for old_path, new_path in rename_plan.items():
                logger.info(f"重命名: {old_path} -> {new_path}")
            return

        # 创建备份
        files_to_backup = list(rename_plan.keys())
        self.backup_files(files_to_backup)

        # 执行重命名
        successful_renames = []
        failed_renames = []

        for old_path, new_path in rename_plan.items():
            try:
                old_file = Path(old_path)
                new_file = Path(new_path)

                if old_file.exists():
                    # 确保目标目录存在
                    new_file.parent.mkdir(parents=True, exist_ok=True)

                    # 重命名文件
                    old_file.rename(new_file)
                    successful_renames.append((old_path, new_path))
                    logger.info(f"重命名成功: {old_path} -> {new_path}")

                    # 更新引用
                    self._update_file_references(new_path, old_path)
                else:
                    logger.warning(f"源文件不存在: {old_path}")
                    failed_renames.append((old_path, new_path, "源文件不存在"))

            except Exception as e:
                error_msg = f"重命名失败: {str(e)}"
                logger.error(f"{old_path} -> {new_path}: {error_msg}")
                failed_renames.append((old_path, new_path, error_msg))

        # 输出结果
        logger.info("=== 重命名结果 ===")
        logger.info(f"成功重命名: {len(successful_renames)} 个文件")
        logger.info(f"失败重命名: {len(failed_renames)} 个文件")

        if failed_renames:
            logger.warning("失败的文件:")
            for old_path, new_path, error in failed_renames:
                logger.warning(f"  {old_path} -> {new_path}: {error}")

    def _update_file_references(self, new_file_path: str, old_file_path: str):
        """更新文件引用"""
        try:
            old_name = Path(old_file_path).stem
            new_name = Path(new_file_path).stem

            # 获取所有Python文件
            python_files = list(self.project_root.rglob("*.py"))

            for py_file in python_files:
                if py_file == Path(new_file_path):
                    continue  # 跳过刚重命名的文件

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检查是否包含引用
                    if old_name in content:
                        # 更新import语句
                        updated_content = self._update_imports(content, old_file_path, new_file_path)
                        updated_content = self._update_references(updated_content, old_name, new_name)

                        if updated_content != content:
                            with open(py_file, 'w', encoding='utf-8') as f:
                                f.write(updated_content)
                            logger.info(f"更新引用: {py_file} ({old_name} -> {new_name})")

                except Exception as e:
                    logger.warning(f"更新引用失败 {py_file}: {e}")

        except Exception as e:
            logger.error(f"更新文件引用失败: {e}")

    def _update_imports(self, content: str, old_path: str, new_path: str) -> str:
        """更新import语句"""
        old_module_path = old_path.replace('/', '.').replace('.py', '')
        new_module_path = new_path.replace('/', '.').replace('.py', '')

        # 更新直接import
        content = re.sub(
            rf'from\s+{re.escape(old_module_path)}\s+import',
            f'from {new_module_path} import',
            content
        )

        # 更行相对import
        old_relative = old_path.replace('app/', '').replace('.py', '')
        new_relative = new_path.replace('app/', '').replace('.py', '')

        content = re.sub(
            rf'from\s+\.?{re.escape(old_relative)}\s+import',
            f'from .{new_relative} import',
            content
        )

        return content

    def _update_references(self, content: str, old_name: str, new_name: str) -> str:
        """更新文件中的引用"""
        # 更新类名引用
        content = re.sub(
            rf'from\s+\S+{re.escape(old_name)}\s+import',
            f'from {new_name} import',
            content
        )

        # 更新字符串引用
        content = re.sub(
            rf'["\']{re.escape(old_name)}["\']',
            f'"{new_name}"',
            content
        )

        return content

    def cleanup_deprecated_files(self, dry_run: bool = True):
        """清理废弃文件"""
        logger.info(f"清理废弃文件 (dry_run={dry_run})...")

        deprecated_files = [
            "app/ui/enhanced_main_window.py",
            "app/ui/video_player.py",
            "app/ui/modern_navigation.py",
            "app/ui/new_main_window.py",
            "app/ui/timeline_widget.py",
            "app/ui/theme_manager.py",  # 已被unified_theme_system替代
        ]

        files_to_delete = []

        for file_path in deprecated_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                files_to_delete.append(str(full_path))

        if files_to_delete:
            if dry_run:
                logger.info("=== 将删除的文件 ===")
                for file_path in files_to_delete:
                    logger.info(f"删除: {file_path}")
            else:
                # 备份要删除的文件
                self.backup_files(files_to_delete)

                # 删除文件
                for file_path in files_to_delete:
                    try:
                        Path(file_path).unlink()
                        logger.info(f"已删除: {file_path}")
                    except Exception as e:
                        logger.error(f"删除失败 {file_path}: {e}")

    def generate_report(self, analysis: Dict[str, List[str]], rename_plan: Dict[str, str]) -> str:
        """生成规范化报告"""
        report = []
        report.append("=" * 60)
        report.append("CineAIStudio 文件命名规范化报告")
        report.append("=" * 60)
        report.append("")

        # 文件分析
        report.append("📊 文件分析结果:")
        report.append(f"  • UI组件文件: {len(analysis['ui_components'])} 个")
        report.append(f"  • 页面文件: {len(analysis['ui_pages'])} 个")
        report.append(f"  • 核心模块: {len(analysis['core_modules'])} 个")
        report.append(f"  • AI模块: {len(analysis['ai_modules'])} 个")
        report.append(f"  • 问题文件: {len(analysis['problematic_files'])} 个")
        report.append(f"  • 废弃文件: {len(analysis['deprecated_files'])} 个")
        report.append("")

        # 重命名计划
        report.append("🔄 重命名计划:")
        report.append(f"  • 计划重命名: {len(rename_plan)} 个文件")
        if self.conflict_files:
            report.append(f"  • 冲突文件: {len(self.conflict_files)} 个")
        report.append("")

        # 废弃文件
        if analysis["deprecated_files"]:
            report.append("🗑️ 将删除的废弃文件:")
            for file_path in analysis["deprecated_files"]:
                report.append(f"  • {file_path}")
            report.append("")

        # 建议和改进
        report.append("💡 命名规范建议:")
        report.append("  1. 使用snake_case命名所有文件")
        report.append("  2. 组件文件以_component.py结尾")
        report.append("  3. 页面文件以_page.py结尾")
        report.append("  4. 对话框文件以_dialog.py结尾")
        report.append("  5. 避免使用通用名称如panel、widget等")
        report.append("  6. 保持文件名与功能的一致性")
        report.append("")

        # 后续行动
        report.append("🚀 后续行动建议:")
        report.append("  1. 运行规范化脚本 (dry_run=False)")
        report.append("  2. 更新所有引用")
        report.append("  3. 测试应用程序启动")
        report.append("  4. 更新文档和注释")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    """主函数"""
    project_root = os.getcwd()
    normalizer = FileNormalizer(project_root)

    try:
        # 分析文件结构
        analysis = normalizer.analyze_file_structure()

        # 生成重命名计划
        rename_plan = normalizer.generate_rename_plan()

        # 生成报告
        report = normalizer.generate_report(analysis, rename_plan)

        # 输出报告
        print(report)

        # 保存报告到文件
        with open("FILE_NORMALIZATION_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📄 详细报告已保存到: FILE_NORMALIZATION_REPORT.md")

        # 执行规范化 (默认为预览模式)
        dry_run = False  # 设置为False以实际执行重命名

        if dry_run:
            print("\n⚠️ 当前为预览模式，不会实际重命名文件")
            print("要执行实际重命名，请将脚本中的 dry_run = False")
        else:
            print("\n🚀 开始执行文件规范化...")

            # 应用重命名计划
            normalizer.apply_rename_plan(rename_plan, dry_run=dry_run)

            # 清理废弃文件
            normalizer.cleanup_deprecated_files(dry_run=dry_run)

            print("✅ 文件规范化完成")

    except Exception as e:
        logger.error(f"文件规范化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())