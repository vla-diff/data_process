#!/usr/bin/env python3
# 用于查找没有成功标注 bbox 的图片（只检查，不修改文件）

import json
import sys
from pathlib import Path


def _parse_index_value(item, fallback):
    if isinstance(item, dict):
        idx = item.get("index")
        if isinstance(idx, int):
            return idx
        if isinstance(idx, str):
            try:
                return int(idx)
            except ValueError:
                return fallback
    return fallback


def main() -> int:
    root = Path("datasets/raw/raw_data")
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    problem_files = set()
    problem_items = 0

    for path in root.rglob("data.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Skip (invalid json): {path} ({exc})", file=sys.stderr)
            continue

        if not isinstance(data, list):
            continue

        for list_idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue

            # 只关心 Answer 为空字符串的情况
            if item.get("Answer") == "":
                json_index = _parse_index_value(item, list_idx)

                print(
                    f"[EMPTY BBOX] {path} | list_idx={list_idx} | index={json_index}"
                )

                problem_files.add(path)
                problem_items += 1

    print(f"\nTotal problem files: {len(problem_files)}", file=sys.stderr)
    print(f"Total problem items: {problem_items}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
