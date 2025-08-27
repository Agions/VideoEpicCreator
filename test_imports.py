#!/usr/bin/env python3
"""
测试Ant Design组件导入
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    try:
        # 测试主题系统
        from app.ui.styles.ant_design import theme_manager
        print("✓ Ant Design主题系统导入成功")

        # 测试按钮组件
        from app.ui.widgets.ant_buttons import AntButton, PrimaryButton
        print("✓ Ant Design按钮组件导入成功")

        # 测试卡片组件
        from app.ui.widgets.ant_cards import AntCard, CardMeta, CardContent
        print("✓ Ant Design卡片组件导入成功")

        # 测试输入组件
        from app.ui.widgets.ant_inputs import AntInput, AntTextArea
        print("✓ Ant Design输入组件导入成功")

        print("\n所有新创建的Ant Design组件导入测试通过！")
        return True

    except Exception as e:
        print(f"✗ 导入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports()
