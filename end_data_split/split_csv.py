"""
从 raw CSV (datasets/raw/raw_data/.../data.csv) 中读取每个 episode 的位姿，
将四元数转换为欧拉角 yaw，并检测末尾稳定段的起点。

使用方法（仓库根目录）：
    python data_process/end_data_split/split_csv.py

默认：遍历 datasets/raw/raw_data 下所有 data.csv，输出每个 episode 的长度和 stop_frame。
"""

from __future__ import annotations

import math
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R


def quat_normalize(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q, axis=-1, keepdims=True)
    n = np.where(n == 0, 1.0, n)
    return q / n


def load_actions_from_csv(csv_path: Path) -> np.ndarray:
    """
    读取单个 episode 的 data.csv，返回 shape (N, 6) 的数组：
    [pos_x, pos_y, pos_z, roll, pitch, yaw]
    yaw 由四元数转欧拉得到。
    """
    df = pd.read_csv(csv_path)
    required = ["位置X", "位置Y", "位置Z", "姿态X", "姿态Y", "姿态Z", "姿态W"]
    if not all(c in df.columns for c in required):
        raise ValueError(f"{csv_path} 缺少必要列 {required}")

    pos = df[["位置X", "位置Y", "位置Z"]].to_numpy(dtype=float)
    quat = df[["姿态X", "姿态Y", "姿态Z", "姿态W"]].to_numpy(dtype=float)
    quat = quat_normalize(quat)
    euler = R.from_quat(quat).as_euler("xyz", degrees=False)
    actions = np.concatenate([pos, euler], axis=1)  # (N,6)
    return actions


def find_stop_frame(
    actions: np.ndarray,
    *,
    r_pos: float = 0,
    r_yaw: float = 0,
    pos_min: float = 0.2,
    yaw_min: float = 0.4,
    k: int = 2,
    hist_ratio: float = 0.8,
) -> tuple[int, float, float]:
    """
    Return (stop_frame_index, pos_threshold, yaw_threshold).

    逻辑：对每帧与“最终帧”比较的 pos/yaw 差，估计前段尺度，找到末尾连续 k 帧稳定段的起点。
    """
    if actions.shape[0] < 2:
        return 0, pos_min, yaw_min

    pose = actions[:, [0, 1, 2, 5]].copy()
    pose[:, 3] = np.unwrap(pose[:, 3])  # unwrap yaw

    end_pose = pose[-1]
    delta_end = np.abs(pose - end_pose)
    pos_delta = delta_end[:, :3].max(axis=1)
    yaw_delta = delta_end[:, 3]

    hist_end = max(1, int(hist_ratio * len(pos_delta)))
    q_pos = np.percentile(pos_delta[:hist_end], 75)
    q_yaw = np.percentile(yaw_delta[:hist_end], 75)
    pos_th = max(q_pos * r_pos, pos_min)
    yaw_th = max(q_yaw * r_yaw, yaw_min)

    stable = (pos_delta < pos_th) & (yaw_delta < yaw_th)

    stop_idx = len(stable) - 1
    for i in range(len(stable) - k, -1, -1):
        if stable[i : i + k].all():
            stop_idx = i
            continue  # 推到最早的稳定起点
        break
    return stop_idx + 1, pos_th, yaw_th


def iter_episodes(raw_root: Path) -> Iterable[Path]:
    """
    遍历 datasets/raw/raw_data 下的所有 data.csv
    （约定层级 * / * / * /data.csv）
    """
    yield from raw_root.glob("*/*/*/data.csv")


def main() -> None:
    raw_root = Path("datasets/raw/raw_data")
    files = sorted(iter_episodes(raw_root))
    if not files:
        print("No data.csv found under", raw_root)
        return

    for csv_path in files:
        try:
            actions = load_actions_from_csv(csv_path)
        except Exception as e:
            print(f"[SKIP] {csv_path}: {e}")
            continue

        stop_frame, pos_th, yaw_th = find_stop_frame(actions)
        gap = len(actions) - 1 - stop_frame
        rel = csv_path.relative_to(raw_root)
        print(
            f"{rel}: len={len(actions)}, stop_frame={stop_frame}, "
            f"frames_after={gap}, pos_th={pos_th:.4f}, yaw_th={yaw_th:.4f}"
        )

        # 生成同目录下的 json，包含每个 step 的问答
        steps = []
        for idx in range(len(actions)):
            steps.append(
                {
                    "index": idx,
                    "Question": "这是你当前的观测，如果能识别到目标，则输出bbox，否则输出<pred_action>",
                    "Answer": "" if idx >= stop_frame else "<pred_action>",
                }
            )
        json_path = csv_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(steps, f, ensure_ascii=False, indent=2)
        print(f"  -> saved Q/A to {json_path}")


if __name__ == "__main__":
    main()
