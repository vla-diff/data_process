#!/bin/bash

# Master script to convert all IndoorUAV datasets to LeRobot format
# This script processes all datasets in ready_datasets/ folder

set -e  # Exit on error

# Base paths
READY_DATASETS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/ready_datasets"
VLA_INS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/vla_ins"
INTERMEDIATE_BASE="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw/intermediate_all"
FINAL_BASE="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all"

# Script directory
SCRIPT_DIR="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw"

# Create base directories
mkdir -p $INTERMEDIATE_BASE
mkdir -p $FINAL_BASE

# Get list of all datasets
# DATASETS=(gibson_1 gibson_2 hm3d_7 hm3d_8 hm3d_9 hm3d_10 hm3d_11 hm3d_12 hm3d_13 hm3d_16 hm3d_17)
DATASETS=(gibson_2)

echo "=========================================="
echo "Converting ${#DATASETS[@]} datasets to LeRobot format"
echo "=========================================="
echo ""

# Track statistics
TOTAL_EPISODES=0
FAILED_DATASETS=()

# Process each dataset
for DATASET_NAME in "${DATASETS[@]}"; do
    echo "=========================================="
    echo "Processing dataset: $DATASET_NAME"
    echo "=========================================="

    GIBSON_ROOT="$READY_DATASETS_ROOT/$DATASET_NAME"
    VLA_INS_PATH="$VLA_INS_ROOT/$DATASET_NAME"
    INTERMEDIATE_ROOT="$INTERMEDIATE_BASE/${DATASET_NAME}_intermediate"
    FINAL_ROOT="$FINAL_BASE/${DATASET_NAME}_lerobot"

    # Check if paths exist
    if [ ! -d "$GIBSON_ROOT" ]; then
        echo "❌ ERROR: Gibson root not found: $GIBSON_ROOT"
        FAILED_DATASETS+=("$DATASET_NAME (missing gibson root)")
        continue
    fi

    if [ ! -d "$VLA_INS_PATH" ]; then
        echo "❌ ERROR: VLA ins not found: $VLA_INS_PATH"
        FAILED_DATASETS+=("$DATASET_NAME (missing vla_ins)")
        continue
    fi

    # Clean up previous outputs for this dataset
    rm -rf $FINAL_ROOT
    mkdir -p $FINAL_ROOT

    # echo ""
    # echo "Step 0: Converting Gibson to intermediate format..."
    # if ! python3 $SCRIPT_DIR/gibson_to_intermediate.py \
    #     --gibson_root $GIBSON_ROOT \
    #     --vla_ins_root $VLA_INS_PATH \
    #     --output_root $INTERMEDIATE_ROOT; then
    #     echo "❌ ERROR: Failed at gibson_to_intermediate for $DATASET_NAME"
    #     FAILED_DATASETS+=("$DATASET_NAME (gibson_to_intermediate)")
    #     continue
    # fi

    echo ""
    echo "Step 1: Converting CSV to Parquet..."
    if ! python3 $SCRIPT_DIR/1Parquet-csv2par.py \
        --parent_folder_path $INTERMEDIATE_ROOT \
        --output_root $FINAL_ROOT; then
        echo "❌ ERROR: Failed at csv2par for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (csv2par)")
        continue
    fi

    echo ""
    echo "Step 3: Generating episodes.jsonl..."
    if ! python3 $SCRIPT_DIR/3EpisodeJsonl.py \
        --output_root $FINAL_ROOT/data \
        --reorg_root $INTERMEDIATE_ROOT \
        --output_file $FINAL_ROOT/meta/episodes.jsonl; then
        echo "❌ ERROR: Failed at episodes.jsonl for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (episodes.jsonl)")
        continue
    fi

    echo ""
    echo "Step 4: Generating tasks.jsonl..."
    if ! python3 $SCRIPT_DIR/4Episode2tasks.py \
        --episodes_file $FINAL_ROOT/meta/episodes.jsonl \
        --tasks_file $FINAL_ROOT/meta/tasks.jsonl; then
        echo "❌ ERROR: Failed at tasks.jsonl for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (tasks.jsonl)")
        continue
    fi

    echo ""
    echo "Step 5: Generating videos..."
    if ! python3 $SCRIPT_DIR/5get_videos.py \
        --root_dir $INTERMEDIATE_ROOT \
        --output_dir $FINAL_ROOT/videos; then
        echo "❌ ERROR: Failed at videos for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (videos)")
        continue
    fi

    echo ""
    echo "Step 6: Generating info.json..."
    if ! python3 $SCRIPT_DIR/6get_info.py \
        --output $FINAL_ROOT; then
        echo "❌ ERROR: Failed at info.json for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (info.json)")
        continue
    fi

    # Count episodes for this dataset
    DATASET_EPISODES=$(wc -l < $FINAL_ROOT/meta/episodes.jsonl)
    TOTAL_EPISODES=$((TOTAL_EPISODES + DATASET_EPISODES))

    echo ""
    echo "✅ Successfully converted $DATASET_NAME: $DATASET_EPISODES episodes"
    echo ""
done

echo ""
echo "=========================================="
echo "Conversion Summary"
echo "=========================================="
echo "Total datasets processed: ${#DATASETS[@]}"
echo "Total episodes generated: $TOTAL_EPISODES"

if [ ${#FAILED_DATASETS[@]} -eq 0 ]; then
    echo "✅ All datasets converted successfully!"
else
    echo ""
    echo "⚠️  Failed datasets (${#FAILED_DATASETS[@]}):"
    for failed in "${FAILED_DATASETS[@]}"; do
        echo "  - $failed"
    done
fi

echo ""
echo "Output locations:"
echo "  - Intermediate data: $INTERMEDIATE_BASE"
echo "  - Final LeRobot data: $FINAL_BASE"
echo "=========================================="
