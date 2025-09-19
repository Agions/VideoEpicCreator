#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CineAIStudio 应用程序入口
使用增强应用启动器的版本
"""

import sys
import traceback

# 导入新的应用启动器
from app.application_launcher import ApplicationLauncher


def main() -> int:
    """主程序入口函数"""
    try:
        # 创建并启动应用程序
        launcher = ApplicationLauncher()
        return launcher.launch(sys.argv)

    except KeyboardInterrupt:
        print("\n应用程序被用户中断")
        return 0

    except Exception as e:
        print(f"应用程序启动失败: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
