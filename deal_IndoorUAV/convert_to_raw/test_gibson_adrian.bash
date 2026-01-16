#!/bin/bash

GIBSON_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/ready_datasets/gibson_1"
VLA_INS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/vla_ins/gibson_1"
INTERMEDIATE_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_lerobot/gibson_intermediate_test"
FINAL_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot_test"

rm -rf $INTERMEDIATE_ROOT $FINAL_ROOT
mkdir -p $INTERMEDIATE_ROOT $FINAL_ROOT

echo "0. Converting Gibson to intermediate format (Adrian only)..."
python3 gibson_to_intermediate.py --gibson_root $GIBSON_ROOT --vla_ins_root $VLA_INS_ROOT --output_root $INTERMEDIATE_ROOT --test_scene Adrian

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

echo "✅ Test conversion complete!"
