#!/bin/bash

# 定义路径参数
SRC_ROOT="../datasets/raw/test_data" #源数据根目录路径
DST_ROOT=$SRC_ROOT
FINAL_ROOT="../datasets/dzb/our_data_test" #最终输出根目录路径

rm -r $FINAL_ROOT
mkdir -p $FINAL_ROOT

echo "1"
python3 1Parquet-csv2par.py --parent_folder_path $DST_ROOT --output_root $FINAL_ROOT

echo "3"
python3 3EpisodeJsonl.py --output_root $FINAL_ROOT/data --reorg_root $DST_ROOT --output_file $FINAL_ROOT/meta/episodes.jsonl #从.parquet读取index_length

echo "4"
python3 4Episode2tasks.py --episodes_file $FINAL_ROOT/meta/episodes.jsonl --tasks_file $FINAL_ROOT/meta/tasks.jsonl

echo "5"
python3 5get_videos.py --root_dir $DST_ROOT --output_dir $FINAL_ROOT/videos

# echo "2"
# python3 2StatsJson-get_stats.py --root $FINAL_ROOT   似乎不需要跑这个，后续测试一下

echo "6"
python3 6get_info.py --output $FINAL_ROOT