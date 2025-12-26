#!/bin/bash

SRC=/home/duanzhibo/wall-x/datasets/raw/raw_data
DST=/home/duanzhibo/wall-x/datasets/raw/raw_data_zips

mkdir -p "$DST"

for class_dir in "$SRC"/*/; do
    class_name=$(basename "$class_dir")
    echo "Processing class: $class_name"

    mkdir -p "$DST/$class_name"

    for sub_dir in "$class_dir"*/; do
        sub_name=$(basename "$sub_dir")
        out_zip="$DST/$class_name/$sub_name.zip"

        echo "  Compressing $class_name/$sub_name → $out_zip"

        (
            cd "$sub_dir" || exit
            zip -rq "$out_zip" .
        )
    done
done

echo "✅ All done."
