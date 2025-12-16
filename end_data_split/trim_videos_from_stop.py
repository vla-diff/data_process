"""
For each episode, detect the stop frame from the action sequence (pos + yaw) and
export the video segment starting at that timestamp. The original directory
layout is preserved under an output root.

 LD_LIBRARY_PATH=/home/duanzhibo/ffmpeg/lib python datasets/dzb/our_data_test/trim_videos_from_stop.py   --ffmpeg-bin /home/duanzhibo/ffmpeg/bin/ffmpeg   --ffmpeg-libdir /home/duanzhibo/ffmpeg/lib   --output-root datasets/dzb/our_data_test/videos_trimmed   --annotate-root datasets/dzb/our_data_test/videos_annotated   --no-drawtext --skip-trim


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

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


def find_stop_frame(
    actions: np.ndarray,
    *,
    r_pos: float = 0,
    r_yaw: float = 0,
    pos_min: float = 0.2,
    yaw_min: float = 0.4,
    k: int = 2,
    hist_ratio: float = 0.5,
) -> int:
    """
    Return the start index of the stable tail window (0-based).
    """
    if actions.shape[0] < 2:
        return 0

    pose = actions[:, [0, 1, 2, 5]].copy()
    pose[:, 3] = np.unwrap(pose[:, 3])  # unwrap yaw to avoid jumps

    # Compare每帧到最终帧的差异（而非相邻帧差异），确保末尾段和最终画面接近。
    end_pose = pose[-1]
    delta_end = np.abs(pose - end_pose)
    pos_delta = delta_end[:, :3].max(axis=1)
    yaw_delta = delta_end[:, 3]

    hist_end = max(1, int(hist_ratio * len(pos_delta)))
    q_pos = np.percentile(pos_delta[:hist_end], 75)
    q_yaw = np.percentile(yaw_delta[:hist_end], 75)
    pos_th = max(q_pos * r_pos, pos_min)
    yaw_th = max(q_yaw * r_yaw, yaw_min)
    # print("pos_th:",pos_th)
    # print("yaw_th:",yaw_th)
    stable = (pos_delta < pos_th) & (yaw_delta < yaw_th)
    # print("stable:",stable)
    stop_idx = len(stable) - 1
    # print("len(stable):",len(stable))
    for i in range(len(stable) - k, -1, -1):
        if stable[i : i + k].all():
            stop_idx = i
            continue
        break
    # assert False
    return stop_idx + 1  # convert delta index to frame index


def trim_video(
    in_path: Path,
    out_path: Path,
    start_time: float,
    ffmpeg_bin: str,
    env: dict[str, str] | None,
) -> bool:
    """
    Trim input video from start_time to end, copying stream. Returns success.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start_time:.3f}",
        "-i",
        str(in_path),
        "-c",
        "copy",
        str(out_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode != 0:
        print(f"[FAIL] {in_path.name}: ffmpeg error -> {result.stderr.decode(errors='ignore')[:300]}")
        return False
    return True


def ffmpeg_supports_drawtext(ffmpeg_bin: str, env: dict[str, str] | None) -> bool:
    """
    Check if drawtext filter is available.
    """
    proc = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-filters"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if proc.returncode != 0:
        return False
    return b" drawtext " in proc.stdout


def pick_encoder(ffmpeg_bin: str, env: dict[str, str] | None) -> tuple[list[str], str]:
    """
    Choose an available video encoder and suitable options.
    Preference: libx264 -> h264 (native) -> mpeg4.
    """
    proc = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-encoders"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    enc_text = proc.stdout.decode(errors="ignore")

    def has(enc: str) -> bool:
        return f" {enc} " in enc_text

    if has("libx264"):
        return (["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p"], "libx264")
    if has("h264"):
        return (["-c:v", "h264", "-b:v", "5M", "-pix_fmt", "yuv420p"], "h264")
    if has("mpeg4"):
        return (["-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p"], "mpeg4")
    # Fallback: let ffmpeg pick default, but ensure pix_fmt.
    return (["-pix_fmt", "yuv420p"], "default")


def annotate_video(
    in_path: Path,
    out_path: Path,
    start_time: float,
    ffmpeg_bin: str,
    env: dict[str, str] | None,
    fontfile: Path | None = None,
    use_drawtext: bool = True,
    encoder_opts: list[str] | None = None,
) -> bool:
    """
    Save full-length video but overlay a marker indicating the stop time.
    - Persistent text label (optional, requires drawtext filter).
    - Semi-transparent band appears from start_time onward.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    band_filter = f"drawbox=x=0:y=0:w=iw:h=48:color=red@0.35:t=fill:enable='gte(t,{start_time})'"
    filters = [band_filter]
    if use_drawtext:
        text = f"STOP >= {start_time:.2f}s"
        font_opt = f":fontfile={fontfile}" if fontfile else ""
        filters.append(
            f"drawtext=text='{text}':fontsize=28:fontcolor=white"
            f":box=1:boxcolor=red@0.6:boxborderw=8:x=20:y=20{font_opt}"
        )
    vf = ",".join(filters)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(in_path),
        "-vf",
        vf,
    ]
    if encoder_opts:
        cmd.extend(encoder_opts)
    cmd.extend(["-c:a", "copy", str(out_path)])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode != 0:
        print(f"[FAIL] annotate {in_path.name}: ffmpeg error -> {result.stderr.decode(errors='ignore')[:300]}")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Trim and/or annotate videos from detected stop frame timestamps.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("datasets/dzb/our_data_test/videos_trimmed"),
        help="Directory to store trimmed videos (flattened: episode_xxxxxx.mp4).",
    )
    parser.add_argument(
        "--annotate-root",
        type=Path,
        default=None,
        help="If set, save full-length annotated videos under this directory (flattened).",
    )
    parser.add_argument(
        "--skip-trim",
        action="store_true",
        help="If set, do not write trimmed videos; only annotations (if annotate-root is provided).",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        type=str,
        default="ffmpeg",
        help="Path to ffmpeg binary (defaults to ffmpeg in PATH).",
    )
    parser.add_argument(
        "--ffmpeg-libdir",
        type=Path,
        default=None,
        help="Optional LD_LIBRARY_PATH to prepend when calling ffmpeg (e.g., /home/duanzhibo/ffmpeg/lib).",
    )
    parser.add_argument(
        "--no-drawtext",
        action="store_true",
        help="Disable drawtext overlay; only draw the band (useful if ffmpeg lacks drawtext).",
    )
    args = parser.parse_args()

    if shutil.which(args.ffmpeg_bin) is None and not Path(args.ffmpeg_bin).exists():
        print(f"ffmpeg not found: {args.ffmpeg_bin}. Please install ffmpeg or point --ffmpeg-bin to it.")
        return

    base_dir = Path(__file__).resolve().parent
    data_root = base_dir / "data"
    video_root = base_dir / "videos"
    out_root = args.output_root
    annotate_root = args.annotate_root
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    fontfile = font_path if font_path.exists() else None

    ff_env = os.environ.copy()
    if args.ffmpeg_libdir:
        prev = ff_env.get("LD_LIBRARY_PATH", "")
        ff_env["LD_LIBRARY_PATH"] = f"{args.ffmpeg_libdir}{':' + prev if prev else ''}"

    # Detect drawtext availability unless user turned it off.
    use_drawtext = not args.no_drawtext
    if use_drawtext and not ffmpeg_supports_drawtext(args.ffmpeg_bin, ff_env):
        print("drawtext filter not available in this ffmpeg; falling back to band-only overlay.")
        use_drawtext = False

    encoder_opts, encoder_name = pick_encoder(args.ffmpeg_bin, ff_env)
    print(f"Using encoder: {encoder_name} ({' '.join(encoder_opts)})")

    parquet_files = sorted(data_root.glob("chunk-*/*.parquet"))
    if not parquet_files:
        print("No parquet files found.")
        return

    total = len(parquet_files)
    ok_trim = 0
    ok_ann = 0
    skipped = 0

    for f in parquet_files:
        df = pd.read_parquet(f)
        actions = np.vstack(df["action"].to_numpy())
        stop_frame = find_stop_frame(actions)
        if stop_frame >= len(df):
            stop_frame = len(df) - 1
        start_ts = float(df.iloc[stop_frame]["timestamp"])

        chunk_dir = f.parent.name
        stem = f.stem  # episode_xxxxxx
        in_video = video_root / chunk_dir / "video.front" / f"{stem}.mp4"
        if not in_video.exists():
            print(f"[SKIP] video not found for {f.name}: {in_video}")
            skipped += 1
            continue
        if not args.skip_trim:
            out_video = out_root / f"{stem}.mp4"
            if trim_video(in_video, out_video, start_ts, ffmpeg_bin=args.ffmpeg_bin, env=ff_env):
                ok_trim += 1
                print(f"[OK] trimmed {f.name}: stop_frame={stop_frame}, start_ts={start_ts:.3f} -> {out_video}")
            else:
                skipped += 1
        if annotate_root:
            ann_video = annotate_root / f"{stem}.mp4"
            if annotate_video(
                in_video,
                ann_video,
                start_ts,
                ffmpeg_bin=args.ffmpeg_bin,
                env=ff_env,
                fontfile=fontfile,
                use_drawtext=use_drawtext,
                encoder_opts=encoder_opts,
            ):
                ok_ann += 1
                print(f"[OK] annotated {f.name}: stop_frame={stop_frame}, start_ts={start_ts:.3f} -> {ann_video}")
            else:
                skipped += 1

    print(f"Done. trimmed={ok_trim}, annotated={ok_ann}, skipped={skipped}, total={total}")


if __name__ == "__main__":
    main()
