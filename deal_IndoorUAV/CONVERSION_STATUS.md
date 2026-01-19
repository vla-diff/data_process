# IndoorUAV 全数据集转换状态

## 转换任务概览

**开始时间**: 2026-01-19
**任务**: 将 11 个 IndoorUAV 数据集转换为 LeRobot 格式

### 数据集列表

1. gibson_1 (43 scenes)
2. gibson_2 (43 scenes)
3. hm3d_7 (52 scenes)
4. hm3d_8 (52 scenes)
5. hm3d_9 (52 scenes)
6. hm3d_10 (52 scenes)
7. hm3d_11 (52 scenes)
8. hm3d_12 (52 scenes)
9. hm3d_13 (52 scenes)
10. hm3d_16 (52 scenes)
11. hm3d_17 (52 scenes)

**预计总 episodes**: ~10,000+ (每个数据集约 900-1000 episodes)

---

## 转换脚本

### 主脚本
```bash
/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/convert_all_datasets.bash
```

### 监控脚本
```bash
bash /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/check_progress.sh
```

### 查看实时日志
```bash
tail -f /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/conversion_log.txt
```

---

## 输出位置

### 中间数据
```
/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/intermediate_all/
├── gibson_1_intermediate/
│   ├── 1/                          # Episode 1
│   │   ├── instruction.txt         # 任务指令
│   │   ├── source_info.txt         # 源信息(新增)
│   │   └── 1/1/
│   │       ├── data.csv
│   │       └── images/front/
│   ├── 2/
│   └── ...
├── gibson_2_intermediate/
└── ...
```

**source_info.txt 内容示例**:
```
Source Information:
Original trajectory folder: /path/to/gibson_1/Adrian/traj_-1
VLA instruction file: /path/to/vla_ins/gibson_1/Adrian/traj_-1/vla_ins_1.json
Frame range: 11 to 45
Total frames: 35
```

### 最终 LeRobot 格式数据
```
/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/
├── gibson_1_lerobot/
│   ├── data/
│   │   └── chunk-000/
│   │       └── episode_*.parquet
│   ├── videos/
│   │   └── chunk-000/
│   │       └── video.front/
│   │           └── episode_*.mp4
│   └── meta/
│       ├── episodes.jsonl
│       ├── tasks.jsonl
│       └── info.json
├── gibson_2_lerobot/
└── ...
```

---

## 已解决的问题

### 1. Unicode 编码错误
**问题**: 部分 vla_ins JSON 文件包含非 UTF-8 字符
**解决方案**: 添加 latin-1 编码回退机制

### 2. JSON 解析错误
**问题**: 部分 JSON 文件包含无效的转义序列
**解决方案**: 添加错误处理，跳过损坏的文件并记录警告

### 3. 文件损坏处理
**实现**:
- 尝试 UTF-8 编码
- 失败则尝试 latin-1 编码
- 仍失败则跳过该文件并输出警告
- 继续处理其他文件

---

## 转换流程

每个数据集的转换包含 6 个步骤：

1. **gibson_to_intermediate.py**: Gibson → 中间格式
   - 读取 posture.json 和 vla_ins 文件
   - 根据 vla_ins 切分轨迹
   - 转换 yaw 为四元数
   - 生成 CSV 和图像文件夹

2. **1Parquet-csv2par.py**: CSV → Parquet
   - 计算相对位姿
   - 生成 action (下一帧的 state)
   - 添加 bbox 和 grasp 字段

3. **3EpisodeJsonl.py**: 生成 episodes.jsonl
   - 记录每个 episode 的元数据

4. **4Episode2tasks.py**: 生成 tasks.jsonl
   - 提取唯一任务列表

5. **5get_videos.py**: 生成视频文件
   - 从图像序列生成 MP4

6. **6get_info.py**: 生成 info.json
   - 统计数据集信息

---

## 预计时间和资源

### 单个数据集
- **转换时间**: 1-2 小时
- **磁盘占用**:
  - 中间数据: ~10-15 GB
  - 最终数据: ~5-8 GB

### 全部 11 个数据集
- **总转换时间**: 12-24 小时
- **总磁盘占用**:
  - 中间数据: ~110-165 GB
  - 最终数据: ~55-88 GB
- **内存需求**: 8-16 GB

---

## 监控命令

### 检查进程是否运行
```bash
ps aux | grep convert_all_datasets.bash
```

### 查看当前进度
```bash
bash /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/check_progress.sh
```

### 查看最新输出
```bash
tail -50 /tmp/claude/tasks/bf9b6b3.output
```

### 统计已完成的数据集
```bash
ls -la /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/
```

### 查看某个数据集的 episode 数量
```bash
wc -l /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/gibson_1_lerobot/meta/episodes.jsonl
```

---

## 故障排查

### 如果转换中断
1. 检查日志文件找到错误原因
2. 修复问题后重新运行脚本（会自动清理并重新开始）

### 如果磁盘空间不足
1. 删除中间数据文件夹（转换完成后不再需要）
```bash
rm -rf /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/intermediate_all/
```

### 如果需要重新转换某个数据集
1. 删除该数据集的输出文件夹
2. 修改 convert_all_datasets.bash 中的 DATASETS 数组，只保留需要转换的数据集
3. 重新运行脚本

---

## 完成后的验证

### 1. 检查所有数据集是否成功
```bash
for dataset in gibson_1 gibson_2 hm3d_7 hm3d_8 hm3d_9 hm3d_10 hm3d_11 hm3d_12 hm3d_13 hm3d_16 hm3d_17; do
    if [ -f "/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/${dataset}_lerobot/meta/info.json" ]; then
        episodes=$(wc -l < "/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/${dataset}_lerobot/meta/episodes.jsonl")
        echo "✓ $dataset: $episodes episodes"
    else
        echo "✗ $dataset: FAILED"
    fi
done
```

### 2. 生成可视化文件（可选）
```bash
cd /inspire/hdd/global_user/konghanlin-253108540238/wall-x/lerobot

/inspire/hdd/global_user/konghanlin-253108540238/miniconda3/envs/wallxdzb/bin/python \
    -m lerobot.scripts.visualize_dataset \
    --repo-id gibson_1 \
    --root /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/gibson_1_lerobot \
    --episode-index 0 \
    --save 1 \
    --output-dir /inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/ \
    --num-workers 0
```

### 3. 查看转换日志摘要
```bash
grep -E "(✅|❌|Total episodes)" /inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/conversion_log.txt
```

---

## 注意事项

1. **不要中断进程**: 转换过程可能需要 12-24 小时，请确保服务器稳定运行
2. **磁盘空间**: 确保有足够的磁盘空间（至少 200 GB 可用）
3. **内存监控**: 如果出现内存不足，可以考虑减少并行处理的数据集数量
4. **备份**: 转换完成后建议备份最终数据到其他位置

---

## 更新日志

- **2026-01-19**: 开始全数据集转换
  - 修复 Unicode 编码问题
  - 修复 JSON 解析错误
  - 添加错误跳过机制
  - 创建主转换脚本
  - **新增**: 在每个 episode 文件夹下添加 source_info.txt,记录源轨迹路径和帧范围信息
