#!/usr/bin/env python3
# 检查 data.json 的 bbox 完整性（只检查，不修改文件）
# 1) 是否存在 data.json：一个合适的 bbox 都没有
# 2) 是否存在 data.json：最大 index（最后一个 index）的 bbox 没有
#
# 输出：命中的 data.json 路径（带标签）

import json
import sys
from pathlib import Path


def _parse_index_value(item, fallback: int) -> int:
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


def _has_valid_bbox(answer) -> bool:
    # 兼容多种 Answer 表达形式：str / dict / list / None
    if answer is None:
        return False
    if isinstance(answer, str):
        return answer.strip() != ""
    if isinstance(answer, (list, tuple, dict)):
        return len(answer) > 0
    # 其他类型：只要 truthy 就算有
    return bool(answer)


def main() -> int:
    root = Path("datasets/raw/raw_data")
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    no_bbox_files = set()
    last_index_empty_files = set()

    scanned = 0
    invalid_json = 0
    non_list = 0

    for path in root.rglob("data.json"):
        scanned += 1
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            invalid_json += 1
            print(f"Skip (invalid json): {path} ({exc})", file=sys.stderr)
            continue

        if not isinstance(data, list):
            non_list += 1
            print(f"Skip (not a list): {path}", file=sys.stderr)
            continue

        # 条目为空：视为“一个合适 bbox 都没有”
        if len(data) == 0:
            no_bbox_files.add(path)
            continue

        any_valid_bbox = False
        max_index = None
        max_index_items = []

        for list_idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue

            ans = item.get("Answer")
            if _has_valid_bbox(ans):
                any_valid_bbox = True

            idx_val = _parse_index_value(item, list_idx)
            if (max_index is None) or (idx_val > max_index):
                max_index = idx_val
                max_index_items = [(list_idx, item)]
            elif idx_val == max_index:
                max_index_items.append((list_idx, item))

        if not any_valid_bbox:
            no_bbox_files.add(path)

        # 检查“最后一个 index 的 bbox 没有”
        # max_index_items 里只要有任何一个 Answer 无效，就认为最后 index 缺 bbox
        if max_index is not None and max_index_items:
            for list_idx, item in max_index_items:
                if not _has_valid_bbox(item.get("Answer")):
                    last_index_empty_files.add(path)
                    break

    # 输出结果（stdout）
    for p in sorted(no_bbox_files):
        print(f"[NO_VALID_BBOX] {p}")

    for p in sorted(last_index_empty_files):
        print(f"[LAST_INDEX_EMPTY_BBOX] {p}")

    # 统计（stderr）
    print("", file=sys.stderr)
    print(f"Scanned data.json: {scanned}", file=sys.stderr)
    print(f"Invalid json skipped: {invalid_json}", file=sys.stderr)
    print(f"Non-list skipped: {non_list}", file=sys.stderr)
    print(f"NO_VALID_BBOX files: {len(no_bbox_files)}", file=sys.stderr)
    print(f"LAST_INDEX_EMPTY_BBOX files: {len(last_index_empty_files)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
