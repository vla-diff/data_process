import os
import json
import argparse

# ========== 命令行参数 ==========
parser = argparse.ArgumentParser(description='根据episode.jsonl文件生成tasks.jsonl文件')
parser.add_argument('--episodes_file', required=True, help='输入的episodes.jsonl文件路径')
parser.add_argument('--tasks_file', required=True, help='输出的tasks.jsonl文件路径')
args = parser.parse_args()

episodes_file = args.episodes_file
tasks_file = args.tasks_file

# ========== 自动计算 chunk_size ==========
meta_dir = os.path.dirname(episodes_file)
base_dir = os.path.dirname(meta_dir)
chunk_dir = os.path.join(base_dir, "data", "chunk-000")

parquet_files = [f for f in os.listdir(chunk_dir) if f.endswith(".parquet")]
chunk_size = len(parquet_files)

if chunk_size == 0:
    raise ValueError(f"未在 {chunk_dir} 下找到任何 .parquet 文件！")

print(f"✅ 检测到 chunk_size = {chunk_size} (来自 {chunk_dir})")

# ========== 生成 tasks.jsonl ==========
seen_tasks = set()
task_index = 0
buffer = 0  # ✅ 用整数计数

with open(episodes_file, "r", encoding="utf-8") as f_in, \
     open(tasks_file, "w", encoding="utf-8") as f_out:

    for line in f_in:
        line = line.strip()
        if not line:
            continue

        data = json.loads(line)
        tasks = data.get("tasks", [])
        # print("tasks:", tasks)
        buffer += 1  # ✅ 每处理一个任务就加1

        for task in tasks:
            if buffer >= chunk_size:
                seen_tasks.add(task)
                record = {"task_index": task_index, "task": task}
                task_index += 1

                # 每到 chunk_size 次就写一次当前任务
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                buffer = 0  # ✅ 计数清零

print(f"✅ 已生成 {tasks_file}")
