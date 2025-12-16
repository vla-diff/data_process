"""
Compute the start step of the “end segment” for each episode, based on action
stability in camera position (xyz) and yaw.

Run from repo root:
    python datasets/dzb/our_data_test/detect_stop_frames.py


核心可调参数及效果（都在 find_stop_frame 的默认值里改）：

r_pos, r_yaw（相对阈值系数）：减小→更苛刻，stop 更靠后；增大→更宽松，stop 更靠前。常用范围：r_pos 0.1–0.2，r_yaw 0.15–0.3。
pos_min, yaw_min（绝对下限）：抬高→更宽松；降低→更苛刻。建议：pos_min 0.002–0.005（米），yaw_min 0.005–0.01（弧度）。
k（连续稳定帧数）：增大→更苛刻（需要更长稳定段）；减小→更宽松。一般 2–4。
hist_ratio（用于估计“正常动作”尺度的前段比例）：减小会让阈值受尾部影响更大，容易宽松；增大则更依赖前段动作，可能更苛刻。一般 0.7–0.85。
调参思路：

如果 stop 判得太早：降低 r_pos/r_yaw，或降低 pos_min/yaw_min，或把 k 调大。
如果 stop 判得太晚/判不到：提高 r_pos/r_yaw 或下限，或把 k 调小。
yaw 变化较大的 episode，如果不想阈值被拉得过高，可把 r_yaw 降一些，同时把 yaw_min 提到 0.007–0.01 以避免过严。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path


def find_stop_frame(
    actions: np.ndarray,
    *,
    r_pos: float = 0,
    r_yaw: float = 0,
    pos_min: float = 0.2,
    yaw_min: float = 0.4,
    k: int = 2,
    hist_ratio: float = 0.5,
) -> tuple[int, float, float]:
    """
    Return (stop_frame_index, pos_threshold, yaw_threshold).

    The stop_frame_index is where a stable window of length k starts,
    judging stability by comparing recent deltas against typical deltas
    from the first hist_ratio portion of the trajectory.
    """

    if actions.shape[0] < 2:
        return 0, pos_min, yaw_min

    pose = actions[:, [0, 1, 2, 5]].copy()
    pose[:, 3] = np.unwrap(pose[:, 3])  # unwrap yaw to avoid jumps

    delta = np.abs(np.diff(pose, axis=0))
    pos_delta = delta[:, :3].max(axis=1)
    yaw_delta = delta[:, 3]

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
            continue
        break
    return stop_idx + 1, pos_th, yaw_th


def main() -> None:
    data_root = Path(__file__).resolve().parent / "data"
    files = sorted(data_root.glob("chunk-*/*.parquet"))
    if not files:
        print("No parquet files found under", data_root)
        return

    for f in files:
        df = pd.read_parquet(f)
        actions = np.vstack(df["action"].to_numpy())
        stop_frame, pos_th, yaw_th = find_stop_frame(actions)
        gap = len(df) - 1 - stop_frame
        print(
            f"{f.name}: len={len(df)}, stop_frame={stop_frame}, "
            f"frames_after={gap}, pos_th={pos_th:.4f}, yaw_th={yaw_th:.4f}"
        )


if __name__ == "__main__":
    main()
