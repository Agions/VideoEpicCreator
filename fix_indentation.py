#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 脚本用于修复video_player.py中的缩进问题

with open('app/ui/video_player.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 确保update_position方法的缩进正确
fixed_lines = []
in_update_position = False

for line in lines:
    if "def update_position" in line:
        in_update_position = True
        fixed_lines.append(line)
    elif in_update_position and "self.position_slider.setValue" in line:
        # 确保这行的缩进是8个空格
        fixed_line = "        " + line.lstrip()
        fixed_lines.append(fixed_line)
    elif in_update_position and "self.update_position_label" in line:
        # 确保这行的缩进是8个空格
        fixed_line = "        " + line.lstrip()
        fixed_lines.append(fixed_line)
    elif in_update_position and "def update_duration" in line:
        in_update_position = False
        fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# 写回文件
with open('app/ui/video_player.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("缩进问题已修复!") 