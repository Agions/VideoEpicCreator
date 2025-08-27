"""
Main entry point for VideoEpicCreator PyQt6 application
Enhanced with Ant Design UI System
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.main_window import main


if __name__ == "__main__":
    main()
