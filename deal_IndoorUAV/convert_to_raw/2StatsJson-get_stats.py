import os
import glob
import json
import pandas as pd
import numpy as np
import cv2
from tqdm import tqdm
import argparse

def convert_to_native(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(v) for v in obj]
    else:
        return obj
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process some paths.')
    parser.add_argument('--root', 
                       type=str, 
                       required=True,
                       help='Root directory path')
    return parser.parse_args()

args = parse_args()
root_path = args.root
# ---------- 原始数据和视频根目录 ----------
data_root = f"{root_path}/data"       # parquet 根目录
video_root = f"{root_path}/videos"    # video.front 根目录
output_jsonl = f"{root_path}/meta/episodes_stats.jsonl"

# ---------- 获取所有 parquet 文件 ----------
parquet_files = sorted(glob.glob(os.path.join(data_root, "chunk-*", "*.parquet")))

episode_stats_list = []

for pq_file in tqdm(parquet_files):
    df = pd.read_parquet(pq_file)
    episode_index = int(df["episode_index"].iloc[0])
    stats = {}

    # -------- 对所有列计算统计值 --------
    for feature in df.columns:
        arr = df[feature].to_numpy()

        if isinstance(arr[0], (list, np.ndarray)):
            arr = np.stack(arr).astype(np.float32)
            min_val = arr.min(axis=0).tolist()
            max_val = arr.max(axis=0).tolist()
            mean_val = arr.mean(axis=0).tolist()
            std_val = arr.std(axis=0).tolist()
        else:
            arr = arr.astype(np.float32)
            min_val = [float(arr.min())]
            max_val = [float(arr.max())]
            mean_val = [float(arr.mean())]
            std_val = [float(arr.std())]

        stats[feature] = {
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "std": std_val,
            "count": [len(arr)]
        }

    # -------- video.front 统计 --------
    chunk_name = os.path.basename(os.path.dirname(pq_file))
    episode_file = os.path.basename(pq_file)
    episode_num = episode_file.split("_")[-1].split(".")[0]
    video_path = os.path.join(video_root, chunk_name, "video.front", f"episode_{episode_num}.mp4")
    # video_path = os.path.join(video_root, chunk_name, "front", f"episode_{episode_num}.mp4")
    print("video_path:",video_path)
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.astype(np.float32) / 255.0
            frames.append(frame)
        cap.release()

        frames = np.array(frames)
        per_channel = frames.mean(axis=(1, 2))  # shape (num_frames, C)

        # 每个通道再套一层 []
        min_val_fmt = [[v] for v in per_channel.min(axis=0)]
        max_val_fmt = [[v] for v in per_channel.max(axis=0)]
        mean_val_fmt = [[v] for v in per_channel.mean(axis=0)]
        std_val_fmt = [[v] for v in per_channel.std(axis=0)]

        stats["video.front"] = {
            "min": min_val_fmt,
            "max": max_val_fmt,
            "mean": mean_val_fmt,
            "std": std_val_fmt,
            "count": [frames.shape[0]]
        }

        stats["timestamp"] = {
            "min": [0.0],
            "max": [float((frames.shape[0]-1)/5.0)],
            "mean": [float(((frames.shape[0]-1)/2)/5.0)],
            "std": [float(np.std(np.linspace(0, (frames.shape[0]-1)/5.0, frames.shape[0])))],
            "count": [frames.shape[0]]
        }

    episode_stats_list.append({
        "episode_index": episode_index,
        "stats": stats
    })

# 按 episode_index 排序
episode_stats_list.sort(key=lambda x: x["episode_index"])

# 写文件
with open(output_jsonl, "w") as f:
    for ep in episode_stats_list:
        ep_native = convert_to_native(ep)
        f.write(json.dumps(ep_native) + "\n")

print(f"Saved {len(episode_stats_list)} episodes to {output_jsonl}")
