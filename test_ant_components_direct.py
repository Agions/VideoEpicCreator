#!/usr/bin/env python3
"""
直接测试Ant Design组件（不通过app模块）
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ant_components():
    """测试Ant Design组件"""
    try:
        print("开始直接测试Ant Design组件...")

        # 测试主题系统
        print("1. 测试主题系统...")
        # 直接导入而不通过app.ui
        from app.ui.styles.ant_design import theme_manager, AntDesignTheme
        theme = theme_manager.get_current_theme()
        print(f"   ✓ 主题颜色: {theme.primary_color.name()}")
        print(f"   ✓ 背景色: {theme.background_color.name()}")
        print(f"   ✓ 文字色: {theme.text_color.name()}")

        # 测试按钮组件
        print("2. 测试按钮组件...")
        from app.ui.widgets.ant_buttons import AntButton, PrimaryButton, TextButton
        button = AntButton("测试按钮")
        primary_button = PrimaryButton("主要按钮")
        text_button = TextButton("文字按钮")
        print(f"   ✓ 按钮创建成功: {button.text()}, {primary_button.text()}, {text_button.text()}")

        # 测试卡片组件
        print("3. 测试卡片组件...")
        from app.ui.widgets.ant_cards import AntCard, CardMeta, CardContent
        card = AntCard()
        meta = CardMeta("测试标题", "测试描述")
        content = CardContent()
        print(f"   ✓ 卡片组件创建成功")

        # 测试输入组件
        print("4. 测试输入组件...")
        from app.ui.widgets.ant_inputs import AntInput, AntTextArea
        input_widget = AntInput()
        textarea_widget = AntTextArea()
        print(f"   ✓ 输入组件创建成功")

        print("\n所有Ant Design组件直接测试通过！")
        return True

    except Exception as e:
        print(f"✗ 组件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ant_components()
