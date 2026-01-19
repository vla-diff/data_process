#!/bin/bash

# Script to check conversion progress

echo "=========================================="
echo "Conversion Progress Check"
echo "=========================================="
echo ""

# Check if conversion is still running
if ps aux | grep -q "[c]onvert_all_datasets.bash"; then
    echo "✓ Conversion process is running"
else
    echo "✗ Conversion process is not running"
fi

echo ""
echo "Last 30 lines of output:"
echo "----------------------------------------"
tail -30 /tmp/claude/tasks/b19d61a.output

echo ""
echo "=========================================="
echo "Checking completed datasets:"
echo "=========================================="

FINAL_BASE="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/lerobot_all"

if [ -d "$FINAL_BASE" ]; then
    for dataset_dir in "$FINAL_BASE"/*_lerobot; do
        if [ -d "$dataset_dir" ]; then
            dataset_name=$(basename "$dataset_dir" | sed 's/_lerobot$//')
            if [ -f "$dataset_dir/meta/episodes.jsonl" ]; then
                episode_count=$(wc -l < "$dataset_dir/meta/episodes.jsonl")
                echo "✓ $dataset_name: $episode_count episodes"
            else
                echo "⚠ $dataset_name: in progress..."
            fi
        fi
    done
else
    echo "No output directory yet"
fi

echo ""
echo "=========================================="
