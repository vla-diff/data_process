# IndoorUAV (Gibson) 数据集转换为 LeRobot 格式

## 概述

本文档说明如何将 Gibson 室内无人机数据集转换为 LeRobot 格式，用于训练具身智能模型。

---

## 数据结构

### 输入数据结构

**1. Gibson 原始数据** (`ready_datasets/gibson_1/`)
```
gibson_1/
├── Adrian/                     # 场景名称 (43个场景)
│   ├── traj_1/                 # 轨迹文件夹
│   │   ├── posture.json        # [[x, y, z, yaw], ...] 位姿数据
│   │   ├── instruction.json    # {"instruction": "长指令"}
│   │   ├── screenshots/        # 1.png, 2.png, ... 图像
│   │   ├── real_action.json    # 动作标注
│   │   └── annotation.json     # 动作类型标注
│   └── traj_2/
└── ...
```

**2. VLA 短指令数据** (`vla_ins/gibson_1/`)
```
vla_ins/gibson_1/
├── Adrian/
│   ├── traj_1/
│   │   ├── vla_ins_1.json      # {"instruction": "短指令", "source": [start, end]}
│   │   ├── vla_ins_2.json
│   │   └── ...
│   └── ...
└── ...
```

### 输出数据结构 (LeRobot 格式)

```
output/
├── data/
│   ├── chunk-000/
│   │   ├── episode_000000.parquet  # 包含 state, action, bbox, grasp
│   │   └── ...
│   └── ...
├── videos/
│   ├── chunk-000/
│   │   └── video.front/
│   │       ├── episode_000000.mp4
│   │       └── ...
│   └── ...
└── meta/
    ├── episodes.jsonl          # 每个 episode 的元数据
    ├── tasks.jsonl             # 任务列表
    └── info.json               # 数据集统计信息
```

---

## 转换流程

### 阶段1: Gibson → 中间格式

**脚本**: `gibson_to_intermediate.py`

**功能**:
1. 读取 `posture.json` 和 `vla_ins_*.json`
2. 根据 vla_ins 的 `source` 字段切分长轨迹为短 episode
3. 将 yaw 角度转换为四元数 (pitch=0, roll=0)
4. 生成 CSV 文件和图像文件夹

**关键转换**:
- **位姿**: `[x, y, z, yaw]` → `[x, y, z, qx=0, qy=0, qz, qw]`
- **bbox**: 占位符 `[0, 0, 0, 0]`
- **grasp**: 全部设为 `False`
- **指令**: 使用 vla_ins 的短指令

**输出结构**:
```
gibson_intermediate/
├── 1/                          # Episode 1
│   ├── instruction.txt
│   └── 1/                      # 小任务
│       └── 1/                  # 子任务
│           ├── data.csv
│           └── images/front/
└── ...
```

### 阶段2: 中间格式 → LeRobot 格式

使用现有的 6 个脚本依次处理：

1. **1Parquet-csv2par.py**: CSV → Parquet
   - 计算相对位姿 (state)
   - 生成 action (下一帧的 state)
   - 添加 bbox 和 grasp 字段

2. **3EpisodeJsonl.py**: 生成 episodes.jsonl
   - 从 parquet 读取帧数
   - 从 instruction.txt 读取任务描述

3. **4Episode2tasks.py**: 生成 tasks.jsonl
   - 提取唯一任务列表

4. **5get_videos.py**: 生成视频文件
   - 从图像序列生成 MP4 视频

5. **6get_info.py**: 生成 info.json
   - 统计数据集信息 (总帧数、episode数等)

---

## 使用方法

### 测试转换 (单个场景)

```bash
cd /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw

bash test_gibson_adrian.bash
```

**输出**:
- 中间数据: `gibson_intermediate_test/`
- 最终数据: `/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot_test/`
- 23 个 episodes (Adrian 场景)

### 完整转换 (所有场景)

修改 `test_gibson_adrian.bash`，移除 `--test_scene Adrian` 参数：

```bash
#!/bin/bash

GIBSON_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/ready_datasets/gibson_1"
VLA_INS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/vla_ins/gibson_1"
INTERMEDIATE_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/gibson_intermediate"
FINAL_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot"

rm -rf $INTERMEDIATE_ROOT $FINAL_ROOT
mkdir -p $INTERMEDIATE_ROOT $FINAL_ROOT

echo "0. Converting Gibson to intermediate format..."
python3 gibson_to_intermediate.py --gibson_root $GIBSON_ROOT --vla_ins_root $VLA_INS_ROOT --output_root $INTERMEDIATE_ROOT

echo "1. Converting CSV to Parquet..."
python3 1Parquet-csv2par.py --parent_folder_path $INTERMEDIATE_ROOT --output_root $FINAL_ROOT

echo "3. Generating episodes.jsonl..."
python3 3EpisodeJsonl.py --output_root $FINAL_ROOT/data --reorg_root $INTERMEDIATE_ROOT --output_file $FINAL_ROOT/meta/episodes.jsonl

echo "4. Generating tasks.jsonl..."
python3 4Episode2tasks.py --episodes_file $FINAL_ROOT/meta/episodes.jsonl --tasks_file $FINAL_ROOT/meta/tasks.jsonl

echo "5. Generating videos..."
python3 5get_videos.py --root_dir $INTERMEDIATE_ROOT --output_dir $FINAL_ROOT/videos

echo "6. Generating info.json..."
python3 6get_info.py --output $FINAL_ROOT

echo "✅ Conversion complete! Total episodes: 946"
```

**预期输出**:
- **946 episodes** (所有场景的所有 vla_ins)
- 约 100-150 GB 磁盘空间

---

## 数据格式说明

### Parquet 文件字段

| 字段 | 类型 | 维度 | 说明 |
|------|------|------|------|
| `index` | int | 1 | 全局帧索引 |
| `episode_index` | int | 1 | Episode 索引 |
| `frame_index` | int | 1 | Episode 内帧索引 |
| `timestamp` | float | 1 | 时间戳 (秒) |
| `task_index` | int | 1 | 任务索引 |
| `state` | float32 | 6 | [x, y, z, roll, pitch, yaw] 相对位姿 |
| `action` | float32 | 6 | 下一帧的 state |
| `bbox` | float32 | 4 | [x1, y1, x2, y2] 占位符 [0,0,0,0] |
| `grasp` | bool | 1 | 抓取状态 (固定为 False) |

### 关键设计决策

1. **只有 yaw 旋转**: Gibson 数据只包含 yaw 角度，pitch 和 roll 设为 0
2. **无 bbox 数据**: 使用占位符 [0, 0, 0, 0]
3. **无抓取动作**: grasp 固定为 False
4. **短指令切分**: 每个 vla_ins 对应一个独立的 episode
5. **相对位姿**: state 是相对于 episode 第一帧的位姿差

---

## 可视化验证

### 生成 .rrd 文件

```bash
cd /inspire/hdd/global_user/konghanlin-253108540238/wall-x/lerobot

/inspire/hdd/global_user/konghanlin-253108540238/miniconda3/envs/wallxdzb/bin/python \
    -m lerobot.scripts.visualize_dataset \
    --repo-id gibson_test \
    --root /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot_test \
    --episode-index 0 \
    --save 1 \
    --output-dir /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/ \
    --num-workers 0
```

**注意**: 需要修改 `visualize_dataset.py` 第286行，添加 `video_backend="pyav"`

### 本地查看

```bash
rerun gibson_test_episode_0.rrd
```

---

## 常见问题

### Q1: 为什么 episode 数量是 946 而不是 236？
**A**: 每个 vla_ins 文件对应一个 episode。236 是长轨迹数量，946 是切分后的短 episode 数量。

### Q2: 为什么 bbox 都是 [0, 0, 0, 0]？
**A**: Gibson 数据集没有目标检测框标注，使用占位符。如需真实 bbox，需要运行目标检测模型。

### Q3: 为什么 grasp 都是 False？
**A**: Gibson 是导航任务，没有抓取动作。

### Q4: state 和 action 的区别？
**A**:
- `state[i]`: 第 i 帧相对于第 0 帧的位姿差
- `action[i]`: 第 i+1 帧的 state (即下一步要到达的位姿)

### Q5: 转换失败怎么办？
**A**: 检查：
1. 路径是否正确
2. vla_ins 文件是否存在
3. posture.json 和 screenshots 是否完整
4. 磁盘空间是否充足

---

## 文件清单

### 转换脚本
- `gibson_to_intermediate.py` - 主转换脚本
- `1Parquet-csv2par.py` - CSV → Parquet
- `3EpisodeJsonl.py` - 生成 episodes.jsonl
- `4Episode2tasks.py` - 生成 tasks.jsonl
- `5get_videos.py` - 生成视频
- `6get_info.py` - 生成 info.json
- `test_gibson_adrian.bash` - 测试脚本

### 配置文件
- `GIBSON_CONVERSION_PLAN.md` - 详细设计文档

### 输出示例
- `gibson_lerobot_test/` - 测试输出 (23 episodes)
- `gibson_test_episode_0.rrd` - 可视化文件

---

## 性能指标

- **转换速度**: ~1-2 小时 (全部 946 episodes)
- **磁盘占用**:
  - 中间数据: ~100-150 GB
  - 最终数据: ~50-80 GB
- **内存需求**: 8-16 GB

---

## 更新日志

- **2026-01-16**: 初始版本，支持 Gibson 数据集转换
- 修复 instruction.txt 重复问题
- 添加 pyav 视频后端支持
