import os
import shutil
from pathlib import Path
from tqdm import tqdm

# ========== 配置 ==========
SRC_ROOT = Path("/mnt/diff-ali/workspace/wall-x/datasets/raw/raw_data")  # 原数据根目录
DST_ROOT = Path("/mnt/diff-ali/workspace/wall-x/datasets/raw/reorganized_raw_data")            # 输出根目录
DRY_RUN = False   # True: 仅打印，不执行
LINK_MODE = True  # True: 建立软链接而不是复制
# ==========================

def make_unique_path(p: Path) -> Path:
    """防止重复路径"""
    if not p.exists():
        return p
    i = 1
    while True:
        cand = p.with_name(f"{p.name}_{i}")
        if not cand.exists():
            return cand
        i += 1

# 清理旧输出目录
if not DRY_RUN and DST_ROOT.exists():
    print(f"⚠️ 输出目录 {DST_ROOT} 已存在，将覆盖其中内容")
    # 若需安全删除旧目录请启用：
    # shutil.rmtree(DST_ROOT)

DST_ROOT.mkdir(parents=True, exist_ok=True)

# 遍历所有 m
for m_dir in sorted(SRC_ROOT.iterdir()):
    if not m_dir.is_dir():
        continue
    print(f"\n📂 处理长程任务类型 m={m_dir.name}")

    # 读取 instruction.txt
    instr_src = m_dir / "instruction.txt"
    instr_text = instr_src.read_text(encoding="utf-8") if instr_src.exists() else ""

    # 遍历所有 n
    for n_dir in sorted(m_dir.iterdir()):
        if not n_dir.is_dir() or n_dir.name == "instruction.txt":
            continue
        n = n_dir.name

        # 遍历 n 下的 n-p
        for np_dir in sorted(n_dir.iterdir()):
            if not np_dir.is_dir():
                continue

            np_name = np_dir.name  # e.g., 1-1
            try:
                p = int(np_name.split("-")[-1])
            except Exception:
                print(f"⚠️ 跳过异常目录: {np_dir}")
                continue

            # ============ 映射规则 ============
            new_m = (int(m_dir.name) - 1) * 2 + p
            new_n = n
            new_p = 1
            # =================================

            dst_p_dir = DST_ROOT / str(new_m) / str(new_n)
            dst_final = dst_p_dir / f"{new_n}-{new_p}"

            if DRY_RUN:
                print(f"[DRY_RUN] {np_dir} -> {dst_final}")
                continue

            dst_p_dir.mkdir(parents=True, exist_ok=True)

            # 拷贝或软链接
            if LINK_MODE:
                os.symlink(os.path.abspath(np_dir), dst_final, target_is_directory=True)
            else:
                shutil.copytree(np_dir, dst_final, dirs_exist_ok=True)

            # 拷 instruction.txt
            instr_dst = DST_ROOT / str(new_m) / "instruction.txt"
            if instr_text and not instr_dst.exists():
                instr_dst.write_text(instr_text, encoding="utf-8")

print("\n✅ 重组完成。")
print(f"输出目录: {DST_ROOT}")
