import os
import zipfile
from pathlib import Path
from tqdm import tqdm

# ========== 配置 ==========
ROOT_DIR = Path("/data2/konghanlin/new_wallx/datasets/ori_datasets")  # 根目录
DELETE_ZIP = True   # 是否删除原 zip 文件
# ==========================

# 遍历所有子目录
for m_dir in sorted([p for p in ROOT_DIR.iterdir() if p.is_dir()]):
    print(f"\n📂 处理目录: {m_dir}")
    zip_files = sorted(m_dir.glob("*.zip"))

    for zip_path in tqdm(zip_files, desc=f"{m_dir.name}", unit="file"):
        try:
            extract_dir = m_dir / zip_path.stem  # 解压到与 zip 同名文件夹
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if DELETE_ZIP:
                zip_path.unlink()  # 删除 zip 文件

        except Exception as e:
            print(f"❌ 解压失败: {zip_path}，错误: {e}")

print("\n✅ 所有文件已解压完成。")
