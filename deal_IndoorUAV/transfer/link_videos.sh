#!/bin/bash
#这个脚本仅仅用于将IndoorUAV数据集的文件夹中的视频文件全部链接到同一文件夹下，方便上传到modelscope
# 源目录
SRC_DIR="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/important_IndoorUAV_videos"
# 目标目录（软链接存放位置）
DST_DIR="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/videos_flat"

mkdir -p "$DST_DIR"

count=0
find "$SRC_DIR" -type f -name "*.mp4" | while read -r filepath; do
    filename=$(basename "$filepath")
    ln -sf "$filepath" "$DST_DIR/$filename"
    ((count++))
    if (( count % 5000 == 0 )); then
        echo "已处理 $count 个文件..."
    fi
done

echo "完成！共创建软链接: $(ls -1 "$DST_DIR" | wc -l) 个"
