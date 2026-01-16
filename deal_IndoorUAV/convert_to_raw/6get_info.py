import os
import cv2
import json
import glob
import pandas as pd
import argparse

# 解析命令行参数
parser = argparse.ArgumentParser(description='数据处理脚本，支持命令行指定输出根目录')
parser.add_argument('--output', required=True, help='输出根目录路径')
args = parser.parse_args()

# 从命令行参数获取输出目录路径
output = args.output
# 根目录

# output = r"/data2/konghanlin/internmanip/data/datasets/output_small"
data_root = os.path.join(output, "data")
video_root = os.path.join(output, "videos")
meta_root = os.path.join(output, "meta")


# 1. 找 total_chunks
chunk_dirs = sorted([d for d in os.listdir(data_root) if d.startswith("chunk-")])
total_chunks = len(chunk_dirs)

if total_chunks == 0:
    raise RuntimeError("❌ 没有找到任何 chunk 文件夹")
# 1.1 计算 chunk_size（每个 chunk 中 parquet 文件数量）
first_chunk = os.path.join(data_root, chunk_dirs[0])
first_chunk_parquet_files = sorted(glob.glob(os.path.join(first_chunk, "*.parquet")))
if not first_chunk_parquet_files:
    raise RuntimeError(f"❌ {first_chunk} 中没有 parquet 文件")
chunk_size = len(first_chunk_parquet_files)
# 2. 找最后一个 chunk 的最后一个 parquet 文件
last_chunk = os.path.join(data_root, chunk_dirs[-1])
parquet_files = sorted(glob.glob(os.path.join(last_chunk, "*.parquet")))
if not parquet_files:
    raise RuntimeError(f"❌ {last_chunk} 中没有 parquet 文件")
last_parquet = parquet_files[-1]

# 用 pandas 读取
df = pd.read_parquet(last_parquet)

# total_episodes = 最后一个 parquet 文件中的 episode_index
if "episode_index" not in df.columns:
    raise RuntimeError(f"❌ {last_parquet} 中没有 episode_index 列")
total_episodes = int(df["episode_index"].iloc[-1])

# total_frames = 最后一条 index
if "index" not in df.columns:
    raise RuntimeError(f"❌ {last_parquet} 中没有 index 列")
total_frames = int(df["index"].iloc[-1])

# 3. total_videos = 递归统计 output/video 下所有 mp4 文件
total_videos = sum([len(files) for r, d, files in os.walk(video_root) if any(f.endswith(".mp4") for f in files)])

# 4. total_tasks = tasks.jsonl 里的任务数量
tasks_file = os.path.join(meta_root, "tasks.jsonl")
if not os.path.exists(tasks_file):
    raise FileNotFoundError(f"❌ {tasks_file} 不存在")

task_count = 0
with open(tasks_file, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            task_count += 1
total_tasks = task_count  # 因为从0开始编号，所以数量 = 最大编号 + 1

# 5. 用一个样例视频读取宽高 fps
sample_video = None
for root, dirs, files in os.walk(video_root):
    for f in files:
        if f.endswith(".mp4"):
            sample_video = os.path.join(root, f)
            break
    if sample_video:
        break

if not sample_video:
    raise FileNotFoundError("❌ 没有找到任何视频文件！")

cap = cv2.VideoCapture(sample_video)
if not cap.isOpened():
    raise RuntimeError(f"❌ 无法打开视频: {sample_video}")

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
channels = 3  # 假设 RGB
cap.release()

# 6. 构造 meta.json
meta = {
    "codebase_version": "v2.0",
    "robot_type": "UAV",
    "total_episodes": total_episodes+1,
    "total_frames": total_frames+1,
    "total_tasks": total_tasks,
    "total_videos": total_videos,
    "total_chunks": total_chunks,
    "chunks_size": chunk_size,
    "fps": float(fps/2),
    "splits": {
        "train": f"0:{total_episodes+1}"
    },
    "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
    "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
    "features": {
        "video.front": {
            "dtype": "video",
            "shape": [
                height,
                width,
                channels
            ],
            "names": [
                "height",
                "width",
                "channels"
            ],
            "info": {
                "video.fps": float(fps),
                "video.height": height,
                "video.width": width,
                "video.channels": channels,
                "video.codec": "mpeg4",       # 默认写 mpeg4
                "video.pix_fmt": "yuv420p",  # 默认写 yuv420p
                "video.is_depth_map": False,
                "has_audio": False
            }
        },
        "timestamp": { 
        "dtype": "float64",
        "shape": [1]
        },
        "state": { 
            "dtype": "float32",
            "shape": [6]
        },
        "action": { 
            "dtype": "float32",
            "shape": [6]
        },
        "frame_index": { 
            "dtype": "int32",
            "shape": [1]
        },
        "index": { 
            "dtype": "int32",
            "shape": [1]
        },
        "episode_index": { 
            "dtype": "int32",
            "shape": [1]
        },
        "task_index": {
            "dtype": "int32",
            "shape": [1]
        },
        "bbox": {
            "dtype": "float32",
            "shape": [4]
        },
        "grasp": {
            "dtype": "bool",
            "shape": [1]
        }
    }
}

# 保存 meta.json
output = os.path.join(output, "meta/info.json")
with open(output, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=4)

print(f"✅ 已生成 info.json")
print(f"    total_chunks={total_chunks}, total_episodes={total_episodes}, total_frames={total_frames}, total_videos={total_videos}, total_tasks={total_tasks}")



'''
"video.front_first": {
            "dtype": "video",
            "shape": [
                height,
                width,
                channels
            ],
            "names": [
                "height",
                "width",
                "channels"
            ],
            "info": {
                "video.fps": float(fps),
                "video.height": height,
                "video.width": width,
                "video.channels": channels,
                "video.codec": "mpeg4",       # 默认写 mpeg4
                "video.pix_fmt": "yuv420p",  # 默认写 yuv420p
                "video.is_depth_map": False,
                "has_audio": False
            }
        },
'''