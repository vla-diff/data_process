# Gibson Dataset to LeRobot Format Conversion Plan

## 1. Data Structure Analysis

### 1.1 Original Data Structure (tmp_symlink_only_last)
```
tmp_symlink_only_last/
├── 1/                          # Task type folder
│   ├── instruction.txt         # Task instruction
│   └── 1 -> symlink to /path/to/1/30/  # Episode folder (symlink)
│       ├── 1-1/                # Subtask folder
│       │   ├── data.csv        # Position, quaternion, bbox data
│       │   └── images/front/   # Front camera images
│       └── 1-2/
├── 2/
└── ...
```

**Key fields in data.csv:**
- 时间戳(秒), 位置X, 位置Y, 位置Z
- 姿态X, 姿态Y, 姿态Z, 姿态W (quaternion)
- bbox_x1, bbox_y1, bbox_x2, bbox_y2
- 前摄像头图像 (front camera image filename)

### 1.2 Gibson Dataset Structure
```
ready_datasets/gibson_1/
├── Adrian/                     # Scene name
│   ├── traj_1/                 # Trajectory folder
│   │   ├── instruction.json    # {"instruction": "..."} (long instruction)
│   │   ├── posture.json        # [[x, y, z, yaw], ...] ~190 frames
│   │   ├── real_action.json    # {"frame": [{"frame": 1, "actions": {...}}, ...]}
│   │   ├── annotation.json     # Action type annotations
│   │   ├── key_frames.json     # Key frame indices
│   │   ├── instruction_pro.json # Processed instruction
│   │   ├── screenshots/        # 1.png, 2.png, ... (190 images)
│   │   └── saved_transformations/ # Transformation matrices
│   ├── traj_2/
│   └── ...
├── Albertville/
└── ... (43 scenes total)

vla_ins/gibson_1/
├── Adrian/                     # Scene name
│   ├── traj_1/                 # Trajectory folder
│   │   ├── vla_ins_1.json      # {"instruction": "...", "source": [start_frame, end_frame]}
│   │   ├── vla_ins_2.json      # Short instruction with frame range
│   │   └── ...
│   └── ...
└── ...
```

**Total short trajectories:** 946 (vla_ins files)

**Key differences:**
- Gibson uses **[x, y, z, yaw]** format (4D: 3D position + 1D yaw-only rotation)
- Original data uses **[x, y, z, qx, qy, qz, qw]** format (7D: 3D position + 4D quaternion)
- Gibson has **screenshots/** folder instead of **images/front/**
- Gibson has **posture.json** instead of **data.csv**
- Gibson has **NO bbox data** → **Use placeholder [0, 0, 0, 0]**
- Gibson has **NO grasp flag** → **Set all to False**
- Gibson has **only yaw rotation** → **Assume pitch=0, roll=0**

### 1.3 Target LeRobot Format
```
output/
├── data/
│   ├── chunk-000/
│   │   ├── episode_000000.parquet
│   │   ├── episode_000001.parquet
│   │   └── ...
│   ├── chunk-001/
│   └── ...
├── videos/
│   ├── chunk-000/
│   │   └── video.front/
│   │       ├── episode_000000.mp4
│   │       └── ...
│   └── ...
└── meta/
    ├── episodes.jsonl
    ├── tasks.jsonl
    └── info.json
```

**Parquet columns:**
- index, episode_index, frame_index, timestamp
- task_index, state (6D), action (6D), bbox (4D), grasp (bool)

---

## 2. Key Conversion Challenges

### 2.1 Trajectory Splitting (CRITICAL)
- **Original:** Each episode is a complete long trajectory
- **Gibson:** Each long trajectory must be split into multiple short episodes based on vla_ins files
- **Solution:**
  - Read all vla_ins_*.json files for each trajectory
  - Each vla_ins file defines one episode with:
    - Short instruction from vla_ins file
    - Frame range [start_frame, end_frame] from "source" field
    - Subset of posture.json and screenshots
  - **Result:** 946 episodes total (not 236)

### 2.2 Coordinate System Differences
- **Original:** Uses quaternion (姿态X, Y, Z, W) for full 3D rotation
- **Gibson:** Uses only yaw angle (single rotation around Z-axis)
- **Solution:** Convert yaw to quaternion with pitch=0, roll=0
  - Quaternion: [qx=0, qy=0, qz=sin(yaw/2), qw=cos(yaw/2)]
  - Or Euler angles: [roll=0, pitch=0, yaw=yaw]

### 2.3 Missing Data Fields (FIXED)
- **bbox:** Use placeholder **[0, 0, 0, 0]**
- **grasp:** Set all to **False**

### 2.4 Image Organization
- **Original:** `images/front/camera0_00000.jpg`
- **Gibson:** `screenshots/1.png, 2.png, ...`
- **Solution:** Copy screenshots in frame range to match expected format

### 2.5 Action Representation
- **Original:** action = next_state (6D: position + euler angles)
- **Gibson:** Compute action from consecutive frames in posture.json
- **Solution:** action[i] = state[i+1] (same as original pipeline)

---

## 3. Implementation Plan

### 3.1 Script 1: Convert Gibson to Intermediate Format
**File:** `gibson_to_intermediate.py`

**Purpose:** Convert Gibson data to match the original data structure, splitting long trajectories into short episodes

**Steps:**
1. Iterate through all scenes (Adrian, Albertville, ...)
2. For each trajectory (traj_1, traj_2, ...):
   - Read `posture.json` → full trajectory poses [[x, y, z, yaw], ...]
   - Read all `vla_ins/scene/traj/vla_ins_*.json` files
   - For each vla_ins file:
     - Extract short instruction
     - Extract frame range [start_frame, end_frame] from "source"
     - Slice posture.json[start_frame:end_frame+1]
     - Convert yaw to quaternion (pitch=0, roll=0)
     - Generate data.csv with columns:
       - 时间戳(秒): relative time from 0
       - 位置X, 位置Y, 位置Z: from posture
       - 姿态X, 姿态Y, 姿态Z, 姿态W: quaternion with qx=0, qy=0
       - bbox_x1, bbox_y1, bbox_x2, bbox_y2: **[0, 0, 0, 0]**
       - 前摄像头图像: camera0_*.jpg
     - Copy screenshots[start_frame:end_frame+1] to images/front/

**Output structure:**
```
gibson_intermediate/
├── 1/                          # Episode 1 (大任务1)
│   ├── instruction.txt         # Instruction from vla_ins file
│   └── 1/                      # 小任务1 (always 1)
│       └── 1/                  # 子任务1 (always 1)
│           ├── data.csv
│           └── images/front/
├── 2/                          # Episode 2 (大任务2)
│   ├── instruction.txt
│   └── 1/
│       └── 1/
│           ├── data.csv
│           └── images/front/
└── ...
```

**Note:**
- Each vla_ins becomes one episode (946 total)
- Structure: episode_idx/1/1/ (大任务/小任务/子任务)
- Each episode folder has its own instruction.txt from the corresponding vla_ins file

### 3.2 Script 2-6: Reuse Existing Pipeline
Once the intermediate format is created, reuse the existing scripts:

**Script 2:** `1Parquet-csv2par.py`
- Input: `gibson_intermediate/`
- Output: `output/data/chunk-*/episode_*.parquet`
- **Modifications:** Set grasp=False (line 107)

**Script 3:** `3EpisodeJsonl.py`
- Input: `output/data/`, `gibson_intermediate/`
- Output: `output/meta/episodes.jsonl`
- **No modifications needed**

**Script 4:** `4Episode2tasks.py`
- Input: `output/meta/episodes.jsonl`
- Output: `output/meta/tasks.jsonl`
- **No modifications needed**

**Script 5:** `5get_videos.py`
- Input: `gibson_intermediate/`
- Output: `output/videos/chunk-*/video.front/episode_*.mp4`
- **No modifications needed**

**Script 6:** `6get_info.py`
- Input: `output/`
- Output: `output/meta/info.json`
- **No modifications needed**

### 3.3 New Master Script
**File:** `convert_gibson_all.bash`

```bash
#!/bin/bash

GIBSON_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/ready_datasets/gibson_1"
VLA_INS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/vla_ins/gibson_1"
INTERMEDIATE_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_lerobot/gibson_intermediate"
FINAL_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot"

rm -rf $INTERMEDIATE_ROOT $FINAL_ROOT
mkdir -p $INTERMEDIATE_ROOT $FINAL_ROOT

# Step 0: Convert Gibson to intermediate format
echo "0. Converting Gibson to intermediate format..."
python3 gibson_to_intermediate.py --gibson_root $GIBSON_ROOT --vla_ins_root $VLA_INS_ROOT --output_root $INTERMEDIATE_ROOT

# Step 1: Convert CSV to Parquet
echo "1. Converting CSV to Parquet..."
python3 1Parquet-csv2par.py --parent_folder_path $INTERMEDIATE_ROOT --output_root $FINAL_ROOT

# Step 3: Generate episodes.jsonl
echo "3. Generating episodes.jsonl..."
python3 3EpisodeJsonl.py --output_root $FINAL_ROOT/data --reorg_root $INTERMEDIATE_ROOT --output_file $FINAL_ROOT/meta/episodes.jsonl

# Step 4: Generate tasks.jsonl
echo "4. Generating tasks.jsonl..."
python3 4Episode2tasks.py --episodes_file $FINAL_ROOT/meta/episodes.jsonl --tasks_file $FINAL_ROOT/meta/tasks.jsonl

# Step 5: Generate videos
echo "5. Generating videos..."
python3 5get_videos.py --root_dir $INTERMEDIATE_ROOT --output_dir $FINAL_ROOT/videos

# Step 6: Generate info.json
echo "6. Generating info.json..."
python3 6get_info.py --output $FINAL_ROOT

echo "✅ Conversion complete! Total episodes: 946"
```

---

## 4. Detailed Implementation: gibson_to_intermediate.py

### 4.1 Key Functions

**1. Yaw to Quaternion Conversion (pitch=0, roll=0)**
```python
def yaw_to_quaternion(yaw_degrees):
    """Convert yaw angle (degrees) to quaternion [qx, qy, qz, qw]
    Assumes pitch=0, roll=0 (only rotation around Z-axis)
    """
    yaw_rad = np.radians(yaw_degrees)
    qx = 0.0
    qy = 0.0
    qz = np.sin(yaw_rad / 2)
    qw = np.cos(yaw_rad / 2)
    return [qx, qy, qz, qw]
```

**2. Process Single VLA Instruction (Episode)**
```python
def process_vla_ins(scene_name, traj_folder, vla_ins_file, posture_data,
                    output_folder, scene_idx, episode_idx):
    # Read vla_ins file
    vla_ins = json.load(open(vla_ins_file))
    instruction = vla_ins["instruction"]
    start_frame, end_frame = vla_ins["source"]

    # Slice posture data
    posture_slice = posture_data[start_frame:end_frame+1]

    # Create output structure
    output_path = output_folder / str(scene_idx) / str(episode_idx) / "1"
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate data.csv
    rows = []
    for i, [x, y, z, yaw] in enumerate(posture_slice):
        qx, qy, qz, qw = yaw_to_quaternion(yaw)
        timestamp = i * 0.2  # Assuming 5 fps
        image_name = f"camera0_{i:05d}.jpg"

        rows.append({
            "时间戳(秒)": timestamp,
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
            "前摄像头图像": image_name
        })

    df = pd.DataFrame(rows)
    df.to_csv(output_path / "data.csv", index=False)

    # Copy screenshots to images/front/
    images_folder = output_path / "images" / "front"
    images_folder.mkdir(parents=True, exist_ok=True)

    screenshots = sorted((traj_folder / "screenshots").glob("*.png"),
                         key=lambda x: int(x.stem))
    for i, frame_idx in enumerate(range(start_frame, end_frame+1)):
        src = screenshots[frame_idx]
        dst = images_folder / f"camera0_{i:05d}.jpg"
        shutil.copy(src, dst)

    return instruction
```

**3. Main Loop**
```python
def main(gibson_root, vla_ins_root, output_root):
    gibson_root = Path(gibson_root)
    vla_ins_root = Path(vla_ins_root)
    output_root = Path(output_root)

    scenes = sorted([d for d in gibson_root.iterdir() if d.is_dir()])

    global_episode_idx = 0

    for scene_idx, scene in enumerate(scenes):
        print(f"Processing scene {scene_idx+1}: {scene.name}")

        trajectories = sorted([d for d in scene.iterdir()
                              if d.is_dir() and d.name.startswith("traj_")])

        first_instruction = None

        for traj in trajectories:
            # Read full posture.json
            posture_file = traj / "posture.json"
            if not posture_file.exists():
                continue
            posture_data = json.load(open(posture_file))

            # Find corresponding vla_ins files
            vla_ins_dir = vla_ins_root / scene.name / traj.name
            if not vla_ins_dir.exists():
                continue

            vla_ins_files = sorted(vla_ins_dir.glob("vla_ins_*.json"),
                                  key=lambda x: int(x.stem.split('_')[-1]))

            for vla_ins_file in vla_ins_files:
                instruction = process_vla_ins(
                    scene.name, traj, vla_ins_file, posture_data,
                    output_root, scene_idx + 1, global_episode_idx + 1
                )

                if first_instruction is None:
                    first_instruction = instruction

                global_episode_idx += 1

        # Save instruction.txt for scene (use first instruction)
        if first_instruction:
            scene_folder = output_root / str(scene_idx + 1)
            scene_folder.mkdir(parents=True, exist_ok=True)
            with open(scene_folder / "instruction.txt", "w") as f:
                f.write(first_instruction)

    print(f"✅ Total episodes created: {global_episode_idx}")
```

### 4.2 Handling Edge Cases
- **Missing files:** Skip if posture.json or vla_ins files missing
- **Frame range validation:** Ensure start_frame < end_frame and within bounds
- **Screenshot indexing:** Screenshots are 1-indexed (1.png, 2.png), adjust accordingly

---

## 5. Modifications to Existing Scripts

### 5.1 1Parquet-csv2par.py
**Line 107:** Change grasp flag logic
```python
# Original:
grasp_flag = (folder_num % 2 == 0)

# Modified:
grasp_flag = False  # Gibson has no grasp action
```

**No other changes needed**

---

## 6. Validation Steps

After conversion, verify:

1. **Episode count:** Should be 946 (total vla_ins files)
2. **Frame counts:** Check random episodes match vla_ins source ranges
3. **Video generation:** Verify videos play correctly
4. **Parquet schema:** Ensure all columns present (state, action, bbox=[0,0,0,0], grasp=False)
5. **Metadata:** Check episodes.jsonl, tasks.jsonl, info.json

**Validation commands:**
```bash
# Count episodes
find output/data -name "*.parquet" | wc -l  # Should be 946

# Check random parquet
python3 -c "import pandas as pd; df = pd.read_parquet('output/data/chunk-000/episode_000000.parquet'); print(df[['bbox', 'grasp']].head())"

# Verify bbox and grasp values
python3 -c "import pandas as pd; df = pd.read_parquet('output/data/chunk-000/episode_000000.parquet'); print('bbox:', df['bbox'].iloc[0]); print('grasp:', df['grasp'].unique())"
```

---

## 7. Estimated Resource Requirements

- **Disk space:**
  - Intermediate format: ~100-150 GB (946 episodes with images + CSV)
  - Final format: ~50-80 GB (parquet + videos)
- **Processing time:**
  - Step 0 (conversion): ~1-2 hours
  - Steps 1-6 (pipeline): ~2-3 hours
- **Memory:** 8-16 GB RAM sufficient

---

## 8. Key Decisions Summary

### Fixed Parameters
1. **bbox:** Always [0, 0, 0, 0] (no object detection)
2. **grasp:** Always False (no grasp action in Gibson)
3. **Rotation:** Only yaw, pitch=0, roll=0
4. **Action:** Computed from consecutive posture frames

### Critical Changes from Original Plan
1. **Episode splitting:** 946 episodes (not 236) based on vla_ins files
2. **Short instructions:** Use vla_ins instructions (not long trajectory instructions)
3. **Frame slicing:** Each episode uses subset of frames from source trajectory

### Data Flow
```
ready_datasets/gibson_1 + vla_ins/gibson_1
    ↓ (gibson_to_intermediate.py)
gibson_intermediate/
    ↓ (existing pipeline: 1Parquet-csv2par.py → ... → 6get_info.py)
gibson_lerobot/
```

---

## 9. Next Steps

1. Review and approve this updated plan
2. Implement `gibson_to_intermediate.py`
3. Modify `1Parquet-csv2par.py` (line 107: grasp=False)
4. Test on 1-2 scenes first
5. Run full conversion pipeline
6. Validate output (946 episodes, correct bbox/grasp values)
