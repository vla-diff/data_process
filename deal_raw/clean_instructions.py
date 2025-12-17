import os
import re

base_dir = "/mnt/diff-ali/workspace/wall-x/datasets/raw_data"

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if filename == "instruction.txt":
            file_path = os.path.join(root, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = [
                re.sub(r"^\s*轨迹\s*\d+\s*:\s*", "", line)
                for line in lines
            ]

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            print(f"✅ 已清理: {file_path}")

print("🎉 所有 instruction.txt 文件已处理完成！")
