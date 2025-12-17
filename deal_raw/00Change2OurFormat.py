import os
import shutil
import argparse

# src_root = "/data2/konghanlin/internmanip/data/datasets/our_ori_small"
# dst_root = "/data2/konghanlin/internmanip/data/datasets/our_reorganized_data"


# 解析命令行参数
parser = argparse.ArgumentParser(description='重组数据集文件结构')
parser.add_argument('--src_root', required=True, help='源数据根目录路径')
parser.add_argument('--dst_root', required=True, help='目标数据根目录路径')
args = parser.parse_args()

# 使用命令行传入的路径，而不是固定路径
src_root = args.src_root
dst_root = args.dst_root

# 映射表：记录每个长程任务类型（q）
task_type_map = {}
type_counter = 0  # q计数
instance_counter = {}  # 每种类型对应的p计数

for B_name in sorted(os.listdir(src_root)):
    B_path = os.path.join(src_root, B_name)
    if not os.path.isdir(B_path):
        continue

    for C_name in sorted(os.listdir(B_path)):
        C_path = os.path.join(B_path, C_name)
        if not os.path.isdir(C_path):
            continue

        for D_name in sorted(os.listdir(C_path)):
            D_path = os.path.join(C_path, D_name)
            if not os.path.isdir(D_path):
                continue

            # 提取长程任务类型标识（B + 短任务编号部分）
            D_suffix = D_name.split("-")[-1]  # 例如 "8-3" → "3"
            long_task_type_key = f"{B_name}_{D_suffix}"

            # 若该类型尚未记录，则新建 q
            if long_task_type_key not in task_type_map:
                type_counter += 1
                task_type_map[long_task_type_key] = type_counter
                instance_counter[type_counter] = 0

            q = task_type_map[long_task_type_key]
            instance_counter[q] += 1
            p = instance_counter[q]

            # 构造新路径
            dst_long_task_dir = os.path.join(dst_root, str(q), str(p), f"{p}-1")
            os.makedirs(dst_long_task_dir, exist_ok=True)

            print(f"源 D: {D_path}")
            print(f"  -> 新路径: {dst_long_task_dir}\n")

            # 拷贝内容
            for item in os.listdir(D_path):
                s = os.path.join(D_path, item)
                d = os.path.join(dst_long_task_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
