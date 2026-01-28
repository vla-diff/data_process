#!/usr/bin/env python3
"""
将所有数据集的 episode 文件夹用软链接汇总到一个文件夹
按顺序重新编号: gibson_1/1 -> all/1, gibson_1/945 -> all/945, gibson_2/14 -> all/959, ...
"""

import os
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description='合并所有数据集的 episode 文件夹')
parser.add_argument('--intermediate_base', required=True, help='中间数据根目录')
parser.add_argument('--output_dir', required=True, help='输出的汇总文件夹')
parser.add_argument('--datasets', nargs='+', required=True, help='数据集列表,按顺序')
args = parser.parse_args()

INTERMEDIATE_BASE = Path(args.intermediate_base)
OUTPUT_DIR = Path(args.output_dir)
DATASETS = args.datasets

# 创建输出目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

global_episode_idx = 1  # 从1开始编号

for dataset_name in DATASETS:
    dataset_dir = INTERMEDIATE_BASE / f"{dataset_name}_intermediate"

    if not dataset_dir.exists():
        print(f"⚠️  数据集不存在，跳过: {dataset_dir}")
        continue

    print(f"\n处理数据集: {dataset_name}")

    # 获取所有 episode 文件夹并按数字排序
    episode_folders = sorted([d for d in dataset_dir.iterdir() if d.is_dir()],
                            key=lambda x: int(x.name))

    for episode_folder in episode_folders:
        source_path = episode_folder.resolve()  # 获取绝对路径
        target_path = OUTPUT_DIR / str(global_episode_idx)

        # 创建软链接
        if target_path.exists():
            print(f"⚠️  目标已存在，跳过: {target_path}")
        else:
            os.symlink(source_path, target_path)
            print(f"✅ {dataset_name}/{episode_folder.name} -> all/{global_episode_idx}")

        global_episode_idx += 1

print(f"\n🎯 完成! 总共创建了 {global_episode_idx - 1} 个软链接")
print(f"输出目录: {OUTPUT_DIR}")
