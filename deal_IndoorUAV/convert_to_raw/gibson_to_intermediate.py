import json
import pandas as pd
import numpy as np
import shutil
import argparse
from pathlib import Path

def yaw_to_quaternion(yaw_degrees):
    """Convert yaw to quaternion with pitch=0, roll=0"""
    yaw_rad = np.radians(yaw_degrees)
    return [0.0, 0.0, np.sin(yaw_rad / 2), np.cos(yaw_rad / 2)]

def process_vla_ins(traj_folder, vla_ins_file, posture_data, output_folder, episode_idx):
    try:
        with open(vla_ins_file, 'r', encoding='utf-8') as f:
            vla_ins = json.load(f)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        # Try with different encoding if utf-8 fails
        try:
            with open(vla_ins_file, 'r', encoding='latin-1') as f:
                vla_ins = json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError) as e2:
            # Skip this file if it's corrupted
            print(f"  ⚠️  Skipping corrupted file: {vla_ins_file} (Error: {e2})")
            return None

    instruction = vla_ins["instruction"]
    start_frame, end_frame = vla_ins["source"]

    posture_slice = posture_data[start_frame:end_frame+1]

    # Create episode folder and save instruction
    episode_folder = output_folder / str(episode_idx)
    episode_folder.mkdir(parents=True, exist_ok=True)
    with open(episode_folder / "instruction.txt", "w") as f:
        f.write(instruction)

    # Save source information
    source_info = f"""Source Information:
Original trajectory folder: {traj_folder}
VLA instruction file: {vla_ins_file}
Frame range: {start_frame} to {end_frame}
Total frames: {end_frame - start_frame + 1}
"""
    with open(episode_folder / "source_info.txt", "w") as f:
        f.write(source_info)

    output_path = episode_folder / "1" / "1"
    output_path.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, [x, y, z, yaw] in enumerate(posture_slice):
        qx, qy, qz, qw = yaw_to_quaternion(yaw)
        rows.append({
            "时间戳(秒)": i * 0.2,
            "位置X": x,
            "位置Y": y,
            "位置Z": z,
            "姿态X": qx,
            "姿态Y": qy,
            "姿态Z": qz,
            "姿态W": qw,
            "bbox_x1": 0.0,
            "bbox_y1": 0.0,
            "bbox_x2": 0.0,
            "bbox_y2": 0.0,
            "前摄像头图像": f"camera0_{i:05d}.jpg"
        })

    pd.DataFrame(rows).to_csv(output_path / "data.csv", index=False)

    images_folder = output_path / "images" / "front"
    images_folder.mkdir(parents=True, exist_ok=True)

    screenshots = sorted((traj_folder / "screenshots").glob("*.png"), key=lambda x: int(x.stem))
    for i, frame_idx in enumerate(range(start_frame, end_frame+1)):
        shutil.copy(screenshots[frame_idx-1], images_folder / f"camera0_{i:05d}.jpg")

    return instruction

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gibson_root', required=True)
    parser.add_argument('--vla_ins_root', required=True)
    parser.add_argument('--output_root', required=True)
    parser.add_argument('--test_scene', default=None, help='Process only this scene for testing')
    args = parser.parse_args()

    gibson_root = Path(args.gibson_root)
    vla_ins_root = Path(args.vla_ins_root)
    output_root = Path(args.output_root)

    scenes = sorted([d for d in gibson_root.iterdir() if d.is_dir()])
    if args.test_scene:
        scenes = [s for s in scenes if s.name == args.test_scene]

    global_episode_idx = 0

    for scene_idx, scene in enumerate(scenes):
        print(f"Processing scene {scene_idx+1}: {scene.name}")

        trajectories = sorted([d for d in scene.iterdir() if d.is_dir() and d.name.startswith("traj_")])

        for traj in trajectories:
            posture_file = traj / "posture.json"
            if not posture_file.exists():
                continue
            posture_data = json.load(open(posture_file))

            vla_ins_dir = vla_ins_root / scene.name / traj.name
            if not vla_ins_dir.exists():
                continue

            vla_ins_files = sorted(vla_ins_dir.glob("vla_ins_*.json"), key=lambda x: int(x.stem.split('_')[-1]))

            for vla_ins_file in vla_ins_files:
                result = process_vla_ins(traj, vla_ins_file, posture_data, output_root, global_episode_idx + 1)
                if result is not None:  # Only increment if processing succeeded
                    global_episode_idx += 1
                    print(f"  Episode {global_episode_idx}: {traj.name}/{vla_ins_file.name}")

    print(f"✅ Total episodes created: {global_episode_idx}")

if __name__ == "__main__":
    main()
