#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SVG 转 PNG 工具

本脚本用于将 SVG 图标转换为各种尺寸的 PNG 格式，支持指定输出尺寸和质量。
需要安装 cairosvg 库：pip install cairosvg
"""

import os
import sys
import argparse
from pathlib import Path
import cairosvg
from concurrent.futures import ThreadPoolExecutor


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
        print(f"已转换: {svg_path} -> {output_path}")
        return True
    except Exception as e:
        print(f"转换失败: {svg_path} - 错误: {e}")
        return False


def convert_all_svgs(svg_dir, output_dir, sizes=None, recursive=False):
    """
    转换目录中所有SVG文件为PNG
    
    参数:
        svg_dir: SVG文件目录
        output_dir: 输出PNG目录
        sizes: 尺寸列表，如 [(32, 32), (64, 64)]
        recursive: 是否递归处理子目录
    """
    # 设置默认尺寸
    if not sizes:
        sizes = [(32, 32), (64, 64), (128, 128)]
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有SVG文件
    if recursive:
        svg_files = list(Path(svg_dir).rglob("*.svg"))
    else:
        svg_files = list(Path(svg_dir).glob("*.svg"))
    
    if not svg_files:
        print(f"在 {svg_dir} 中未找到SVG文件")
        return
    
    # 为每个SVG文件创建转换任务
    tasks = []
    for svg_file in svg_files:
        rel_path = svg_file.relative_to(svg_dir) if svg_file.is_absolute() else svg_file
        
        for width, height in sizes:
            size_suffix = f"_{width}x{height}" if width != height else f"_{width}"
            output_file = Path(output_dir) / f"{rel_path.stem}{size_suffix}.png"
            
            tasks.append((str(svg_file), str(output_file), width, height))
    
    # 使用线程池执行转换任务
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda args: convert_svg_to_png(*args), tasks
        ))
    
    # 统计结果
    success_count = sum(1 for r in results if r)
    fail_count = len(results) - success_count
    
    print(f"\n转换完成！成功: {success_count}, 失败: {fail_count}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将SVG图标转换为PNG格式")
    
    parser.add_argument("svg_dir", help="SVG文件所在目录")
    parser.add_argument("output_dir", help="PNG输出目录")
    parser.add_argument("--sizes", help="输出尺寸列表，格式为'widthxheight'，多个尺寸用逗号分隔，例如: '32x32,64x64'")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    args = parser.parse_args()
    
    # 解析尺寸参数
    sizes = []
    if args.sizes:
        for size_str in args.sizes.split(","):
            try:
                if "x" in size_str:
                    w, h = map(int, size_str.split("x"))
                    sizes.append((w, h))
                else:
                    s = int(size_str)
                    sizes.append((s, s))
            except ValueError:
                print(f"警告: 无法解析尺寸 '{size_str}'，跳过")
    
    # 执行转换
    convert_all_svgs(args.svg_dir, args.output_dir, sizes, args.recursive)


if __name__ == "__main__":
    main() 