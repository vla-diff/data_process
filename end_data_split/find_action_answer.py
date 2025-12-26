#!/usr/bin/env python3
# 用于查找没有成功标注 bbox 的图片（只检查，不修改文件）
# 并统计 bbox 的 Index 数目分布

import json
import sys
from collections import Counter
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


def _is_valid_bbox(answer):
    """判断 Answer 是否是有效的 bbox（包含 4 个数字的列表）"""
    if not isinstance(answer, list):
        return False
    if len(answer) != 4:
        return False
    return all(isinstance(x, (int, float)) for x in answer)


def main() -> int:
    root = Path("datasets/raw/raw_data")
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    problem_files = set()
    problem_items = 0

    # 统计 bbox index 的计数器
    bbox_index_counter = Counter()  # 有 bbox 的 index 统计
    empty_index_counter = Counter()  # 空 bbox 的 index 统计
    total_items = 0

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

            total_items += 1
            json_index = _parse_index_value(item, list_idx)
            answer = item.get("Answer")

            # 判断是否是有效的 bbox（包含 4 个数字的列表）
            if _is_valid_bbox(answer):
                # 有效的 bbox
                bbox_index_counter[json_index] += 1
            else:
                # 无效或空的 bbox
                print(
                    f"[INVALID BBOX] {path} | list_idx={list_idx} | index={json_index} | Answer={answer}"
                )

                problem_files.add(path)
                problem_items += 1
                empty_index_counter[json_index] += 1

    # 输出统计信息
    print("\n" + "=" * 60, file=sys.stderr)
    print("统计结果:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    print(f"\n总条目数: {total_items}", file=sys.stderr)
    print(f"有效 bbox 数目: {sum(bbox_index_counter.values())}", file=sys.stderr)
    print(f"空 bbox 数目: {problem_items}", file=sys.stderr)
    print(f"问题文件数: {len(problem_files)}", file=sys.stderr)

    print("action:bbox=",total_items-sum(bbox_index_counter.values()),":",sum(bbox_index_counter.values()))
    # # 输出有效 bbox 的 index 分布
    # if bbox_index_counter:
    #     print("\n有效 bbox 的 Index 分布:", file=sys.stderr)
    #     for idx in sorted(bbox_index_counter.keys()):
    #         print(f"  Index {idx}: {bbox_index_counter[idx]} 个", file=sys.stderr)

    # # 输出空 bbox 的 index 分布
    # if empty_index_counter:
    #     print("\n空 bbox 的 Index 分布:", file=sys.stderr)
    #     for idx in sorted(empty_index_counter.keys()):
    #         print(f"  Index {idx}: {empty_index_counter[idx]} 个", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
