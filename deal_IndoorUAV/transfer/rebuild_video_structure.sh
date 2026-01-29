#!/bin/bash
#这个脚本仅仅用于把IndoorUAV数据集的全部链接到同一文件夹下的视频文件恢复原文件结构，没测试过

# 扁平化的视频目录（下载下来的文件）
SRC_DIR="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/videos_flat"
# 目标目录（重建原始结构）
DST_DIR="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all/videos_rebuilt"

mkdir -p "$DST_DIR"

count=0
for filepath in "$SRC_DIR"/*.mp4; do
    [ -e "$filepath" ] || continue
    
    filename=$(basename "$filepath")
    # 从 episode_017538.mp4 提取数字 017538
    episode_num=$(echo "$filename" | sed -n 's/episode_\([0-9]*\)\.mp4/\1/p')
    
    if [ -z "$episode_num" ]; then
        echo "警告: 无法解析文件名 $filename，跳过"
        continue
    fi
    
    # 去掉前导零得到 chunk 编号
    chunk_num=$(echo "$episode_num" | sed 's/^0*//')
    [ -z "$chunk_num" ] && chunk_num=0
    
    # 构建目标路径: chunk-000/video.front/episode_000000.mp4
    chunk_dir=$(printf "chunk-%03d" "$chunk_num")
    target_dir="$DST_DIR/$chunk_dir/video.front"
    
    mkdir -p "$target_dir"
    ln -sf "$(realpath "$filepath")" "$target_dir/$filename"
    
    ((count++))
    if (( count % 5000 == 0 )); then
        echo "已处理 $count 个文件..."
    fi
done

echo "完成！共处理 $count 个文件"
