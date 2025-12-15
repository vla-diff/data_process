import pandas as pd
import os
import numpy as np
from scipy.spatial.transform import Rotation as R
import argparse
import json  # 用于读取 bbox.jsonl


# ------------------- quaternion 工具 -------------------
def quat_normalize(q):
    q = np.array(q, dtype=float)
    n = np.linalg.norm(q)
    if n == 0:
        return q
    return q / n


def quat_mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    w = aw * bw - ax * bx - ay * by - az * bz
    x = aw * bx + ax * bw + ay * bz - az * by
    y = aw * by - ax * bz + ay * bw + az * bx
    z = aw * bz + ax * by - ay * bx + az * bw
    return np.array([w, x, y, z], dtype=float)


# ------------------- 命令行参数解析 -------------------
def parse_args():
    parser = argparse.ArgumentParser(description='四元数数据处理脚本')
    parser.add_argument('--parent_folder_path', required=True,
                        help='父文件夹路径')
    parser.add_argument('--output_root', required=True,
                        help='输出根目录路径')
    return parser.parse_args()


args = parse_args()
parent_folder_path = args.parent_folder_path
output_root = args.output_root

# ------------------- 主流程 -------------------
output_root = os.path.join(output_root, "data")
os.makedirs(output_root, exist_ok=True)
print(f"输出目录: {output_root}")

task_type_folders = sorted(
    [f for f in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, f))],
    key=lambda x: int(x)
)

global_episode_index = 0
global_frame_index = 0
task_index = 0

for type_idx, type_folder in enumerate(task_type_folders):
    type_path = os.path.join(parent_folder_path, type_folder)
    chunk_folder = os.path.join(output_root, f"chunk-{type_idx:03d}")
    os.makedirs(chunk_folder, exist_ok=True)

    task_folders = sorted(
        [f for f in os.listdir(type_path)
         if os.path.isdir(os.path.join(type_path, f))],
        key=lambda x: int(x)
    )

    for task_folder in task_folders:
        task_path = os.path.join(type_path, task_folder)
        # print("task_path:", task_path)

        subtask_folders = sorted([
            f for f in os.listdir(task_path)
            if os.path.isdir(os.path.join(task_path, f))
        ])
        # print("subtask_folders:", subtask_folders)
        all_data = []

        # 奇偶决定 grasp
        try:
            folder_num = int(type_folder)
        except ValueError:
            folder_num = 0
        grasp_flag = (folder_num % 2 == 0)

        for folder in subtask_folders:
            grasp = grasp_flag
            csv_file = os.path.join(task_path, folder, "data.csv")

            if not os.path.exists(csv_file):
                print(f"⚠️ 文件不存在: {csv_file}, 已跳过")
                continue

            df = pd.read_csv(csv_file)

            required_columns = ["位置X", "位置Y", "位置Z",
                                "姿态X", "姿态Y", "姿态Z", "姿态W"]
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV 缺少必要列: {csv_file}")

            df = df[required_columns]

            # 默认所有行 bbox 全为 0
            df["bbox_x1"] = 0
            df["bbox_y1"] = 0
            df["bbox_x2"] = 0
            df["bbox_y2"] = 0

            # ✅ 如果当前 data.csv 对应目录下存在 ./images/bbox.jsonl，
            # 则把最后一行的 bbox 设置为该文件中的 boxes[0]
            base_dir = os.path.dirname(csv_file)
            bbox_file = os.path.join(base_dir, "images", "bbox.jsonl")

            if os.path.exists(bbox_file) and not df.empty:
                try:
                    box_applied = False
                    with open(bbox_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            obj = json.loads(line)
                            boxes = obj.get("boxes")
                            # print("boxes:",boxes)
                            # 只取第一个 box，如 [306, 712, 725, 998]
                            if boxes and len(boxes) > 0 and len(boxes[0]) == 4:
                                x1, y1, x2, y2 = boxes[0]
                                df.loc[df.index[-1], "bbox_x1"] = x1/1000*640
                                df.loc[df.index[-1], "bbox_y1"] = y1/1000*480
                                df.loc[df.index[-1], "bbox_x2"] = x2/1000*640
                                df.loc[df.index[-1], "bbox_y2"] = y2/1000*480
                                box_applied = True
                                break
                    if not box_applied:
                        print(f"⚠️ bbox.jsonl 中未找到有效 boxes: {bbox_file}，使用默认 0")
                except Exception as e:
                    print(f"⚠️ 读取 bbox.jsonl 失败: {bbox_file}, 错误: {e}")
            else:
                if not os.path.exists(bbox_file):
                    print(f"⚠️ 找不到 bbox.jsonl: {bbox_file}, 默认 bbox=0")

            df["grasp"] = grasp

            # 保留位置和姿态列 + bbox + grasp
            all_data.append(df)
            # print("all_data:",all_data)

        if not all_data:
            print("⚠️ 无有效数据，跳过任务。")
            continue

        merged_df = pd.concat(all_data, ignore_index=True)

        # 下采样
        sample_interval = 2
        if len(merged_df) > 0:
            # 先记住原始的“真正最后一帧”
            last_row = merged_df.iloc[-1].copy()

            # 正常按步长下采样
            sampled_df = merged_df.iloc[::sample_interval].copy()

            # 如果真正最后一帧的索引不是采样点，
            # 就把“采样后的最后一帧”整行替换成真正最后一帧
            if (len(merged_df) - 1) % sample_interval != 0:
                sampled_df.iloc[-1] = last_row

            merged_df = sampled_df.reset_index(drop=True)

        # ---------- 先转换四元数为欧拉角，再归一化，再合并 ----------
        p0 = np.array([
            merged_df["位置X"].iloc[0],
            merged_df["位置Y"].iloc[0],
            merged_df["位置Z"].iloc[0]
        ], dtype=float)

        q0 = np.array([
            merged_df["姿态X"].iloc[0],
            merged_df["姿态Y"].iloc[0],
            merged_df["姿态Z"].iloc[0],
            merged_df["姿态W"].iloc[0]
        ], dtype=float)
        q0 = quat_normalize(q0)
        R0 = R.from_quat(q0)
        euler0 = R0.as_euler('xyz', degrees=False)

        norm_states = []

        for i in range(len(merged_df)):
            # 平移部分
            pos = np.array([
                merged_df["位置X"].iloc[i],
                merged_df["位置Y"].iloc[i],
                merged_df["位置Z"].iloc[i]
            ], dtype=float)
            rel_pos = pos - p0

            # 四元数→欧拉角
            q = np.array([
                merged_df["姿态X"].iloc[i],
                merged_df["姿态Y"].iloc[i],
                merged_df["姿态Z"].iloc[i],
                merged_df["姿态W"].iloc[i]
            ], dtype=float)
            q = quat_normalize(q)
            R_t = R.from_quat(q)
            euler = R_t.as_euler('xyz', degrees=False)

            # 欧拉角归一化
            rel_euler = euler - euler0
            rel_euler = (rel_euler + np.pi) % (2 * np.pi) - np.pi

            # 拼接位置+欧拉角
            state = np.concatenate([rel_pos, rel_euler]).tolist()
            norm_states.append(state)

        merged_df["state"] = norm_states
        merged_df["bbox"] = merged_df[["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]].values.tolist()

        # ---------- 生成 action.next_position ----------
        actions = []
        for i in range(len(merged_df)):
            if i < len(merged_df) - 1:
                actions.append(merged_df["state"].iloc[i + 1])
            else:
                actions.append(merged_df["state"].iloc[i])
        merged_df["action"] = actions

        # ---------- 索引与保存 ----------
        episode_index = global_episode_index
        global_episode_index += 1

        merged_df["frame_index"] = range(len(merged_df))
        merged_df["index"] = range(global_frame_index, global_frame_index + len(merged_df))
        global_frame_index += len(merged_df)
        merged_df["episode_index"] = episode_index
        merged_df["timestamp"] = np.arange(len(merged_df)) * 0.2 * sample_interval
        merged_df["task_index"] = task_index

        merged_df = merged_df[[
            "index", "episode_index", "frame_index", "timestamp",
            "task_index", "state", "action", "bbox", "grasp"
        ]]

        parquet_file = os.path.join(chunk_folder, f"episode_{episode_index:06d}.parquet")
        merged_df.to_parquet(parquet_file, engine="pyarrow", index=False)

        print(f"✅ 已生成长程任务 {task_folder} 的 parquet 文件: {parquet_file}, 帧数={len(merged_df)}")
        # assert False
    task_index += 1
