#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VideoEpicCreator 图标生成脚本

此脚本将SVG图标转换为程序所需的PNG格式。
"""

import os
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    print("错误: 缺少必要库 cairosvg，请安装: pip install cairosvg")
    sys.exit(1)


# 图标配置：(文件名, 尺寸列表)
ICON_CONFIG = {
    "app_icon": [(512, 512), (256, 256), (128, 128), (64, 64), (32, 32)],
    "new": [(32, 32)],
    "open": [(32, 32)],
    "save": [(32, 32)],
    "export": [(32, 32)],
    "settings": [(32, 32)],
    "handle": [(16, 64)]
}


def convert_svg_to_png(svg_path, output_path, width=None, height=None):
    """
    将单个SVG文件转换为PNG
    
    参数:
        svg_path: SVG文件路径
        output_path: 输出PNG文件路径
        width: 输出宽度（像素）
        height: 输出高度（像素）
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 设置转换参数
    options = {}
    if width:
        options['output_width'] = width
    if height:
        options['output_height'] = height
    
    # 执行转换
    try:
        cairosvg.svg2png(url=svg_path, write_to=output_path, **options)
        print(f"已转换: {os.path.basename(svg_path)} -> {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"转换失败: {svg_path} - 错误: {e}")
        return False


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 设置SVG和PNG目录
    svg_dir = project_root / "resources" / "icons" / "svg"
    png_dir = project_root / "resources" / "icons"
    
    # 确保PNG目录存在
    os.makedirs(png_dir, exist_ok=True)
    
    # 检查SVG目录是否存在
    if not svg_dir.exists():
        print(f"错误: SVG图标目录不存在: {svg_dir}")
        return
    
    # 处理每个图标
    success_count = 0
    fail_count = 0
    
    for icon_name, sizes in ICON_CONFIG.items():
        svg_path = svg_dir / f"{icon_name}.svg"
        
        if not svg_path.exists():
            print(f"警告: 找不到SVG图标: {svg_path}")
            continue
        
        for width, height in sizes:
            # 为主应用图标创建特殊命名
            if icon_name == "app_icon" and width == height:
                output_path = png_dir / f"{icon_name}_{width}.png"
            else:
                output_path = png_dir / f"{icon_name}.png"
            
            if convert_svg_to_png(str(svg_path), str(output_path), width, height):
                success_count += 1
            else:
                fail_count += 1
    
    print(f"\n转换完成! 成功: {success_count}, 失败: {fail_count}")


if __name__ == "__main__":
    main() 