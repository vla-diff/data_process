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
mkdir -p $INTERMEDIATE_BASE
mkdir -p $FINAL_BASE

# Get list of all datasets
DATASETS=(gibson_2 ...)
# DATASETS=(gibson_2)

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

    

    echo ""
    echo " Converting IndoorUAV to raw format
    if ! python3 $SCRIPT_DIR/IndoorUAV_to_intermediate.py \
        --IndoorUAV_root $IndoorUAV_ROOT \
        --vla_ins_root $VLA_INS_PATH \
        --output_root $INTERMEDIATE_ROOT; then
        echo "❌ ERROR: Failed at IndoorUAV_to_intermediate for $DATASET_NAME"
        FAILED_DATASETS+=("$DATASET_NAME (IndoorUAV_to_intermediate)")
        continue
    fi
