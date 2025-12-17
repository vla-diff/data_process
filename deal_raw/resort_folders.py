from pathlib import Path
import os
import shutil
from tqdm import tqdm

# ========== 配置 ==========
ROOT = Path("/mnt/diff-ali/workspace/wall-x/datasets/raw_data")  # 原目录
DRY_RUN = False   # True 时仅打印，不执行
# ==========================

# 获取现有的文件夹（只取纯数字名称的）
folders = sorted([p for p in ROOT.iterdir() if p.is_dir() and p.name.isdigit()],
                 key=lambda x: int(x.name))

print(f"共找到 {len(folders)} 个文件夹。")

# 重新编号
for i, old_dir in enumerate(tqdm(folders, desc="Renaming", unit="folder"), start=1):
    new_dir = ROOT / str(i)
    if old_dir == new_dir:
        continue  # 名称已正确
    if DRY_RUN:
        print(f"[DRY_RUN] {old_dir.name} -> {new_dir.name}")
    else:
        # 如果目标目录存在则加后缀防冲突
        if new_dir.exists():
            new_dir = ROOT / f"{i}_new"
        shutil.move(str(old_dir), str(new_dir))

print("\n✅ 重命名完成！")
