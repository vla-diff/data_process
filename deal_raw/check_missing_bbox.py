#!/usr/bin/env python3
# 查找缺少 data.json 或 data.json 中没有任何有效 bbox 的目录
import json
import sys
from pathlib import Path


def _is_candidate_dir(path: Path) -> bool:
    return (
        (path / "images").is_dir()
        or (path / "instruction.txt").is_file()
        or (path / "data.json").is_file()
    )


def _is_valid_bbox(value) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    for item in value:
        if not isinstance(item, (int, float)):
            return False
    return True


def _has_valid_bbox(data) -> bool:
    if not isinstance(data, list):
        return False
    for item in data:
        if isinstance(item, dict) and _is_valid_bbox(item.get("Answer")):
            return True
    return False


def main() -> int:
    root = Path("datasets/raw/raw_data")
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    missing_json_dirs = []
    no_bbox_dirs = []
    checked_dirs = 0

    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if not _is_candidate_dir(path):
            continue

        checked_dirs += 1
        data_path = path / "data.json"
        if not data_path.is_file():
            missing_json_dirs.append(path)
            continue

        try:
            with data_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Skip (invalid json): {data_path} ({exc})", file=sys.stderr)
            no_bbox_dirs.append(path)
            continue

        if not _has_valid_bbox(data):
            no_bbox_dirs.append(path)

    if missing_json_dirs:
        print("Dirs missing data.json:")
        for path in missing_json_dirs:
            print(path)

    if no_bbox_dirs:
        if missing_json_dirs:
            print()
        print("Dirs with no valid bbox in data.json:")
        for path in no_bbox_dirs:
            print(path)

    print(f"Checked dirs: {checked_dirs}", file=sys.stderr)
    print(f"Missing data.json: {len(missing_json_dirs)}", file=sys.stderr)
    print(f"No valid bbox: {len(no_bbox_dirs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
