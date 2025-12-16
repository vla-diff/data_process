from pathlib import Path
import shutil
import os
from tqdm import tqdm

# ========== 配置 ==========
SRC_ROOT = Path("datasets/raw/reorganized_raw_data")
TRAIN_ROOT = Path("datasets/raw/train_data")
TEST_ROOT = Path("datasets/raw/test_data")

DRY_RUN = False      # True: 仅打印，不执行
LINK_MODE = True     # True: 使用软链接，False: 复制文件夹
# ==========================


def copy_or_link(src, dst):
    """根据模式选择软链接或复制"""
    if LINK_MODE:
        os.symlink(os.path.abspath(src), dst, target_is_directory=True)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)


def rename_inner_folder(task_dir: Path, new_task_id: int):
    """
    将 n-p 改为 new_task_id-1，例如 30-1 -> 1-1
    """
    for sub in task_dir.iterdir():
        if sub.is_dir() and "-" in sub.name:
            old_name = sub.name
            new_name = f"{new_task_id}-1"
            new_path = sub.parent / new_name
            if new_path.exists():
                continue
            if DRY_RUN:
                print(f"[DRY_RUN] rename inner {old_name} -> {new_name}")
            else:
                sub.rename(new_path)


def make_dir(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


print(f"📂 源目录: {SRC_ROOT}")
print(f"📁 训练集输出: {TRAIN_ROOT}")
print(f"📁 测试集输出: {TEST_ROOT}")

# make_dir(TRAIN_ROOT)
make_dir(TEST_ROOT)

# 遍历每个任务类型
for type_dir in sorted(SRC_ROOT.iterdir()):
    if not type_dir.is_dir():
        continue
    type_name = type_dir.name
    print(f"\n处理任务类型 {type_name}")

    sub_tasks = sorted([p for p in type_dir.iterdir() if p.is_dir()], key=lambda x: int(x.name))
    if not sub_tasks:
        continue

    last_task = sub_tasks[-1]
    other_tasks = sub_tasks[:-1]
    instr_src = type_dir / "instruction.txt"

    # ---------------- 处理训练集 ----------------
    train_type_dir = TRAIN_ROOT / type_name
    make_dir(train_type_dir)

    if instr_src.exists():
        shutil.copy(instr_src, train_type_dir / "instruction.txt")

    for i, t in enumerate(other_tasks, start=1):
        dst_t = train_type_dir / str(i)
        if DRY_RUN:
            print(f"[DRY_RUN] TRAIN: {t} -> {dst_t}")
            continue
        copy_or_link(t, dst_t)
        rename_inner_folder(dst_t, i)

    # ---------------- 处理测试集 ----------------
    test_type_dir = TEST_ROOT / type_name
    make_dir(test_type_dir)

    if instr_src.exists():
        shutil.copy(instr_src, test_type_dir / "instruction.txt")

    dst_last = test_type_dir / "1"   # 重新编号为1
    if DRY_RUN:
        print(f"[DRY_RUN] TEST: {last_task} -> {dst_last}")
        continue
    copy_or_link(last_task, dst_last)
    rename_inner_folder(dst_last, 1)

print("\n✅ 数据集划分与重命名完成（含内部文件夹重命名）。")
print(f"训练集: {TRAIN_ROOT}")
print(f"测试集: {TEST_ROOT}")
print(f"模式: {'软链接' if LINK_MODE else '复制'}")
