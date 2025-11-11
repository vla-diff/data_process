import pandas as pd
import os
import numpy as np
from scipy.spatial.transform import Rotation as R
import argparse


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
    w = aw*bw - ax*bx - ay*by - az*bz
    x = aw*bx + ax*bw + ay*bz - az*by
    y = aw*by - ax*bz + ay*bw + az*bx
    z = aw*bz + ax*by - ay*bx + az*bw
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
        print("task_path:", task_path)

        subtask_folders = sorted([
            f for f in os.listdir(task_path)
            if os.path.isdir(os.path.join(task_path, f))
        ])
        print("subtask_folders:", subtask_folders)
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
            df["bbox_x1"] = 0
            df["bbox_y1"] = 0
            df["bbox_x2"] = 0
            df["bbox_y2"] = 0
            df["grasp"] = grasp

            # ✅ 不再丢弃原始列（保留位置和姿态列）
            all_data.append(df)

        if not all_data:
            print("⚠️ 无有效数据，跳过任务。")
            continue

        merged_df = pd.concat(all_data, ignore_index=True)

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
        merged_df["timestamp"] = np.arange(len(merged_df)) * 0.2
        merged_df["task_index"] = task_index

        merged_df = merged_df[["index", "episode_index", "frame_index", "timestamp", "task_index", "state", "action", "bbox", "grasp"]]
        
        # ---------- 下采样: 每 1 秒保留一帧 ----------
        # timestamp 是 0.0, 0.2, 0.4, 0.6, ...
        # 因此每隔 5 帧取一帧即可 (1.0s / 0.2s = 5)
        sample_interval = 5
        sampled_df = merged_df.iloc[::sample_interval].reset_index(drop=True)
        merged_df = sampled_df


        parquet_file = os.path.join(chunk_folder, f"episode_{episode_index:06d}.parquet")
        sampled_df.to_parquet(parquet_file, engine="pyarrow", index=False)

        print(f"✅ 已生成长程任务 {task_folder} 的 parquet 文件: {parquet_file}, 帧数={len(merged_df)}")

    task_index += 1

