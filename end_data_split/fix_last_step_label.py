#!/usr/bin/env python3
# 修复：如果 data.json 里“最后一个 index”的 bbox 为空，
# 则用离它最近的正常 bbox 赋值给它（会修改文件）。
#
# 默认会生成 .bak 备份；可用 --no-backup 关闭；--dry-run 只预览不写盘。

import argparse
import copy
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
    if answer is None:
        return False
    if isinstance(answer, str):
        return answer.strip() != ""
    if isinstance(answer, (list, tuple, dict)):
        return len(answer) > 0
    return bool(answer)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="datasets/raw/raw_data", help="数据根目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要修改的内容，不写文件")
    ap.add_argument("--no-backup", action="store_true", help="不生成 .bak 备份")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    scanned = 0
    fixed_files = 0
    fixed_items = 0
    cannot_fix_files = 0
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
            continue

        if len(data) == 0:
            continue

        # 先扫描：找 max_index 以及每条的 index、bbox 是否有效
        rows = []
        max_index = None

        for list_idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            idx_val = _parse_index_value(item, list_idx)
            ans = item.get("Answer")
            valid = _has_valid_bbox(ans)
            rows.append((list_idx, idx_val, valid))

            if max_index is None or idx_val > max_index:
                max_index = idx_val

        if max_index is None:
            continue

        # 找“最后一个 index”的空 bbox 条目
        last_empty_list_idx = []
        for list_idx, idx_val, valid in rows:
            if idx_val == max_index and not valid:
                last_empty_list_idx.append(list_idx)

        if not last_empty_list_idx:
            continue  # 最后一个 index 不为空，无需修复

        # 找“离 max_index 最近”的正常 bbox（排除 max_index 本身）
        best = None  # (distance, -idx_val, list_idx, answer_copy)
        for list_idx, idx_val, valid in rows:
            if not valid:
                continue
            if idx_val == max_index:
                continue
            ans = data[list_idx].get("Answer")
            dist = abs(idx_val - max_index)
            cand = (dist, -idx_val, list_idx, copy.deepcopy(ans))
            if best is None or cand < best:
                best = cand

        if best is None:
            cannot_fix_files += 1
            print(f"[CANNOT_FIX_NO_VALID_BBOX] {path} | max_index={max_index}", file=sys.stderr)
            continue

        _, src_neg_idx, src_list_idx, src_answer = best
        src_idx_val = -src_neg_idx

        # 执行赋值
        changes = 0
        for li in last_empty_list_idx:
            data[li]["Answer"] = copy.deepcopy(src_answer)
            changes += 1

        if changes == 0:
            continue

        # 输出修改信息
        print(
            f"[FIX] {path} | max_index={max_index} | filled={changes} "
            f"| source_index={src_idx_val} | source_list_idx={src_list_idx}"
        )

        if args.dry_run:
            continue

        # 备份
        if not args.no_backup:
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                if not bak.exists():
                    bak.write_bytes(path.read_bytes())
            except Exception as exc:
                print(f"[WARN] Backup failed: {bak} ({exc})", file=sys.stderr)

        # 写回
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as exc:
            print(f"[FAILED_WRITE] {path} ({exc})", file=sys.stderr)
            continue

        fixed_files += 1
        fixed_items += changes

    print("", file=sys.stderr)
    print(f"Scanned data.json: {scanned}", file=sys.stderr)
    print(f"Invalid json skipped: {invalid_json}", file=sys.stderr)
    print(f"Non-list skipped: {non_list}", file=sys.stderr)
    print(f"Fixed files: {fixed_files}", file=sys.stderr)
    print(f"Fixed items: {fixed_items}", file=sys.stderr)
    print(f"Cannot-fix files: {cannot_fix_files}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
