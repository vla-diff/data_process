#python ../data_process/deal_IndoorUAV/make_subtask_videos.py   --traj-dir datasets/IndoorUAV/hm3d_16/1K7P6ZQS4VM/traj_-1 --fps 10

#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_frame_index(path: Path) -> Optional[int]:
    stem = path.stem
    if stem.isdigit():
        return int(stem)
    match = re.search(r"(\d+)$", stem)
    if match:
        return int(match.group(1))
    return None


def collect_frames(screenshots_dir: Path) -> List[Tuple[int, Path]]:
    frames: List[Tuple[int, Path]] = []
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
        for path in screenshots_dir.glob(pattern):
            idx = parse_frame_index(path)
            if idx is None:
                continue
            frames.append((idx, path))
    frames.sort(key=lambda x: x[0])
    return frames


def link_frames(paths: List[Path], dest_dir: Path) -> None:
    for idx, path in enumerate(paths, start=1):
        source = path.resolve()
        ext = source.suffix.lower()
        name = f"{idx:06d}{ext}"
        target = dest_dir / name
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)


def run_ffmpeg(
    frames_dir: Path,
    output_path: Path,
    fps: int,
    overwrite: bool,
    ext: str,
) -> None:
    pattern = str(frames_dir / f"%06d{ext}")
    cmd = ["ffmpeg"]
    cmd.append("-y" if overwrite else "-n")
    cmd += [
        "-framerate",
        str(fps),
        "-start_number",
        "1",
        "-i",
        pattern,
        "-r",
        str(fps),
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def resolve_paths(
    traj_dir: Optional[Path],
    instruction_split: Optional[Path],
    screenshots_dir: Optional[Path],
    output_dir: Optional[Path],
) -> Tuple[Path, Path, Path]:
    if traj_dir is not None:
        instruction_split = instruction_split or traj_dir / "instruction_split.json"
        screenshots_dir = screenshots_dir or traj_dir / "screenshots"
        output_dir = output_dir or traj_dir / "subtask_videos"
    if instruction_split is None or screenshots_dir is None or output_dir is None:
        raise ValueError("Please provide --traj-dir or all of --instruction-split, --screenshots, --output-dir.")
    return instruction_split, screenshots_dir, output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build per-subtask videos from screenshots using instruction_split.json."
    )
    parser.add_argument(
        "--traj-dir",
        type=Path,
        help="Trajectory folder containing instruction_split.json and screenshots.",
    )
    parser.add_argument(
        "--instruction-split",
        type=Path,
        help="Path to instruction_split.json.",
    )
    parser.add_argument(
        "--screenshots",
        type=Path,
        help="Path to screenshots folder.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output folder for videos (default: traj_dir/subtask_videos).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frames per second for output videos.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing videos.",
    )
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found in PATH.", flush=True)
        return 2

    try:
        instruction_split, screenshots_dir, output_dir = resolve_paths(
            args.traj_dir,
            args.instruction_split,
            args.screenshots,
            args.output_dir,
        )
    except ValueError as exc:
        print(str(exc), flush=True)
        return 2

    if not instruction_split.exists():
        print(f"Missing instruction_split.json: {instruction_split}", flush=True)
        return 1
    if not screenshots_dir.exists():
        print(f"Missing screenshots folder: {screenshots_dir}", flush=True)
        return 1

    split_data = load_json(instruction_split)
    subtasks = split_data.get("subtasks", [])
    if not isinstance(subtasks, list) or not subtasks:
        print("No subtasks found in instruction_split.json.", flush=True)
        return 1

    frames = collect_frames(screenshots_dir)
    if not frames:
        print(f"No images found in {screenshots_dir}", flush=True)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    frame_index_to_path = {idx: path for idx, path in frames}
    frame_indices = [idx for idx, _ in frames]
    min_idx, max_idx = frame_indices[0], frame_indices[-1]

    written = 0
    for idx, item in enumerate(subtasks, start=1):
        try:
            start_kf = int(item["start_key_frame"])
            end_kf = int(item["end_key_frame"])
        except (KeyError, TypeError, ValueError):
            print(f"Skip subtask {idx}: invalid key frame range.", flush=True)
            continue

        if start_kf > end_kf:
            start_kf, end_kf = end_kf, start_kf

        start_kf = max(start_kf, min_idx)
        end_kf = min(end_kf, max_idx)

        selected_paths: List[Path] = []
        for frame_id in range(start_kf, end_kf + 1):
            path = frame_index_to_path.get(frame_id)
            if path:
                selected_paths.append(path)

        if not selected_paths:
            print(
                f"Skip subtask {idx}: no frames for range {start_kf}-{end_kf}.",
                flush=True,
            )
            continue

        output_name = f"subtask_{idx:02d}_{start_kf}-{end_kf}.mp4"
        output_path = output_dir / output_name
        if output_path.exists() and not args.overwrite:
            print(f"Skip {output_path}: exists.", flush=True)
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            link_frames(selected_paths, tmp_path)
            ext = selected_paths[0].suffix.lower()
            try:
                run_ffmpeg(tmp_path, output_path, args.fps, args.overwrite, ext)
                written += 1
                print(f"[OK] {output_path}", flush=True)
            except subprocess.CalledProcessError as exc:
                print(f"[FAIL] {output_path}: {exc}", flush=True)

    print(f"Done. written={written}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
