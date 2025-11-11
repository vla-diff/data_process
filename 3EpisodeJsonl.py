# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# 生成 episodes.jsonl：
# - 每个长程任务 p 对应一个 episode
# - 读取对应 q 下的 instruction.txt 作为任务
# - length = p/p-1 下所有 data.csv 的行数（去掉标题行）累加
# """

# from pathlib import Path
# import csv
# import json
# import os

# # # ========== 配置 ==========
# # REORG_ROOT = Path("/data2/konghanlin/internmanip/data/datasets/our_reorganized_data")
# # OUTPUT_FILE = r"/data2/konghanlin/internmanip/data/datasets/output_small/meta/episodes.jsonl"
# # # ========================

# import argparse

# # 解析命令行参数
# parser = argparse.ArgumentParser(description='生成episodes.jsonl文件的脚本')
# parser.add_argument('--reorg_root', required=True, help='重组数据的根目录路径')
# parser.add_argument('--output_file', required=True, help='生成的episodes.jsonl文件路径')
# args = parser.parse_args()

# # ========== 配置（从命令行参数读取） ==========
# REORG_ROOT = Path(args.reorg_root)
# OUTPUT_FILE = args.output_file
# # ========================

# episode_index = 0
# lines = []

# # 遍历 q
# for q_dir in sorted([p for p in REORG_ROOT.iterdir() if p.is_dir()], key=lambda x: int(x.name)):
#     instr_file = q_dir / "instruction.txt"
#     if not instr_file.exists():
#         print(f"[WARN] {instr_file} 不存在，跳过")
#         continue
#     with open(instr_file, "r", encoding="utf-8") as f:
#         task_instr = f.read().strip()

#     # 遍历 p
#     for p_dir in sorted([p for p in q_dir.iterdir() if p.is_dir()], key=lambda x: int(x.name)):
#         # p-1 下的 data.csv 统计行数
#         total_length = 0
#         for short_task_dir in sorted([p for p in p_dir.iterdir() if p.is_dir()]):
#             data_csv = short_task_dir / "data.csv"
#             if not data_csv.exists():
#                 print(f"[WARN] {data_csv} 不存在，跳过")
#                 continue
#             with open(data_csv, "r", encoding="utf-8") as f:
#                 reader = csv.reader(f)
#                 next(reader, None)  # 跳过标题行
#                 count = sum(1 for _ in reader)
#                 total_length += count

#         episode = {
#             "episode_index": episode_index,
#             "tasks": [task_instr],
#             "length": total_length
#         }
#         lines.append(json.dumps(episode, ensure_ascii=False))
#         episode_index += 1

# os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
# # 写入 episodes.jsonl
# with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#     f.write("\n".join(lines))

# print(f"✅ 完成，已生成 {OUTPUT_FILE}，共 {episode_index} 个 episode")




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 从.parquet读取step_length
"""
# 生成 episodes.jsonl：
# - 每个 .parquet 文件对应一个 episode
# - 从对应的 instruction.txt 中读取任务描述
# - length = parquet 文件的行数
"""

import os
import json
from pathlib import Path
import argparse
import pandas as pd

# ---------------- 参数解析 ----------------
parser = argparse.ArgumentParser(description='根据 .parquet 文件生成 episodes.jsonl')
parser.add_argument('--output_root', required=True, help='存放 .parquet 文件的根目录 (通常是包含 chunk-* 的 data 目录)')
parser.add_argument('--reorg_root', required=True, help='包含 instruction.txt 的原始重组数据目录')
parser.add_argument('--output_file', required=True, help='输出 episodes.jsonl 文件路径')
args = parser.parse_args()

OUTPUT_ROOT = Path(args.output_root)
REORG_ROOT = Path(args.reorg_root)
OUTPUT_FILE = Path(args.output_file)

os.makedirs(OUTPUT_FILE.parent, exist_ok=True)

episode_index = 0
lines = []

# ---------------- 搜索 .parquet 文件 ----------------
chunk_folders = sorted([p for p in OUTPUT_ROOT.iterdir() if p.is_dir() and p.name.startswith("chunk-")])
if not chunk_folders:
    raise FileNotFoundError(f"未找到任何 chunk-* 目录，请检查路径：{OUTPUT_ROOT}")

for chunk_folder in chunk_folders:
    parquet_files = sorted(chunk_folder.glob("episode_*.parquet"))
    if not parquet_files:
        print(f"[WARN] {chunk_folder} 中未找到 parquet 文件")
        continue

    for pq_file in parquet_files:
        try:
            # 读取 parquet 文件，统计 step 数
            df = pd.read_parquet(pq_file)
            length = len(df)

            # 从文件名或目录推断任务索引（根据你的结构）
            # 假设 chunk-000 对应 reorg_root 下的 0，chunk-001 对应 1 ...
            type_idx = int(chunk_folder.name.split('-')[-1])+1
            q_dir = REORG_ROOT / str(type_idx)
            instr_file = q_dir / "instruction.txt"

            if instr_file.exists():
                with open(instr_file, "r", encoding="utf-8") as f:
                    instruction = f.read().strip()
            else:
                instruction = f"[未找到指令: {instr_file}]"
                assert False

            episode = {
                "episode_index": episode_index,
                "tasks": [instruction],
                "length": length
            }

            lines.append(json.dumps(episode, ensure_ascii=False))
            print(f"✅ {pq_file.name} → episode_index={episode_index}, step={length}")
            episode_index += 1

        except Exception as e:
            print(f"❌ 处理失败: {pq_file}, 错误: {e}")

# ---------------- 写出 JSONL ----------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n🎯 已生成 {OUTPUT_FILE}，共 {episode_index} 个 episode")
