#!/bin/bash

# Master script to convert all IndoorUAV datasets to LeRobot format
# This script processes all datasets in ready_datasets/ folder

set -e  # Exit on error

# Base paths
READY_DATASETS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/ready_datasets"
VLA_INS_ROOT="/inspire/hdd/global_user/konghanlin-253108540238/IndoorUAV/vla_ins"
INTERMEDIATE_BASE="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/intermediate_all"

# Script directory
SCRIPT_DIR="/inspire/hdd/global_user/konghanlin-253108540238/data_process/deal_IndoorUAV/convert_to_raw"

# Create base directories
rm -r $INTERMEDIATE_BASE
mkdir -p $INTERMEDIATE_BASE

# Get list of all datasets
DATASETS=(
    gibson_1
    gibson_2
    hm3d_1
    hm3d_2
    hm3d_3
    hm3d_4
    hm3d_5
    hm3d_6
    hm3d_7
    hm3d_8
    hm3d_9
    hm3d_10
    hm3d_11
    hm3d_12
    hm3d_13
    hm3d_14
    hm3d_15
    hm3d_16
    hm3d_17
    hm3d_18
    mp3d_1
    mp3d_2
    replica
)

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

    IndoorUAV_ROOT="$READY_DATASETS_ROOT/$DATASET_NAME"
    VLA_INS_PATH="$VLA_INS_ROOT/$DATASET_NAME"
    INTERMEDIATE_ROOT="$INTERMEDIATE_BASE/${DATASET_NAME}_intermediate"

    # Check if paths exist
    if [ ! -d "$IndoorUAV_ROOT" ]; then
        echo "❌ ERROR: Gibson root not found: $IndoorUAV_ROOT"
        FAILED_DATASETS+=("$DATASET_NAME (missing gibson root)")
        continue
    fi

    if [ ! -d "$VLA_INS_PATH" ]; then
        echo "❌ ERROR: VLA ins not found: $VLA_INS_PATH"
        FAILED_DATASETS+=("$DATASET_NAME (missing vla_ins)")
        continue
    fi

    

    echo ""
    echo "Converting IndoorUAV to raw format"
    if ! python3 $SCRIPT_DIR/IndoorUAV_to_intermediate.py \
        --IndoorUAV_root $IndoorUAV_ROOT \
        --vla_ins_root $VLA_INS_PATH \
        --output_root $INTERMEDIATE_ROOT; then
        echo "❌ ERROR: Failed at IndoorUAV_to_intermediate for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (IndoorUAV_to_intermediate)")
        continue
    fi

    echo "✅ Successfully processed $DATASET_NAME"
    echo ""
done

echo "=========================================="
echo "Conversion Complete!"
echo "=========================================="
echo "Total datasets processed: ${#DATASETS[@]}"
echo "Failed datasets: ${#FAILED_DATASETS[@]}"

if [ ${#FAILED_DATASETS[@]} -gt 0 ]; then
    echo ""
    echo "Failed datasets:"
    for failed in "${FAILED_DATASETS[@]}"; do
        echo "  - $failed"
    done
    exit 1
else
    echo "All datasets converted successfully!"
    exit 0
fi