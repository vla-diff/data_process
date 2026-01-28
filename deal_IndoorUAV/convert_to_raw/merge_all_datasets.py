#!/usr/bin/env python3
"""
将所有数据集的 episode 文件夹用软链接汇总到一个文件夹
按顺序重新编号: gibson_1/1 -> all/1, gibson_1/945 -> all/945, gibson_2/14 -> all/959, ...
精细化软链接：创建目录结构，内部的文件和子文件夹都是软链接

python /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/merge_all_datasets.py \
    --intermediate_base /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/intermediate_all \
    --output_dir /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/merged_all \
    --datasets gibson_1 gibson_2 hm3d_1 hm3d_2 hm3d_3 hm3d_4 hm3d_5 hm3d_6 hm3d_7 hm3d_8 hm3d_9 hm3d_10 hm3d_11 hm3d_12 hm3d_13 hm3d_14 hm3d_15 hm3d_16 hm3d_17 hm3d_18 mp3d_1 mp3d_2 replica
"""

import os
from pathlib import Path
import argparse


def create_symlink_tree(source_dir: Path, target_dir: Path):
    """
    递归创建目录结构，将最底层的文件和文件夹创建为软链接
    对于文件：直接创建软链接
    对于文件夹：如果内部只有文件/空，则软链接整个文件夹；否则递归处理
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for item in source_dir.iterdir():
        source_item = item.resolve()
        target_item = target_dir / item.name
        
        if target_item.exists() or target_item.is_symlink():
            continue
            
        if item.is_file():
            # 文件直接创建软链接
            os.symlink(source_item, target_item)
        elif item.is_dir():
            # 检查目录内是否还有子目录
            has_subdir = any(sub.is_dir() for sub in item.iterdir())
            if has_subdir:
                # 有子目录，递归处理
                create_symlink_tree(item, target_item)
            else:
                # 没有子目录，直接软链接整个文件夹
                os.symlink(source_item, target_item)


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
        target_path = OUTPUT_DIR / str(global_episode_idx)

        if target_path.exists():
            print(f"⚠️  目标已存在，跳过: {target_path}")
        else:
            # 精细化创建软链接树
            create_symlink_tree(episode_folder, target_path)
            print(f"✅ {dataset_name}/{episode_folder.name} -> all/{global_episode_idx}")

        global_episode_idx += 1

print(f"\n🎯 完成! 总共创建了 {global_episode_idx - 1} 个 episode 目录")
print(f"输出目录: {OUTPUT_DIR}")
