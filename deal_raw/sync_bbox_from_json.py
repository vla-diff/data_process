#!/usr/bin/env python3
"""
Sync bbox columns in data.csv from data.json Answer fields.

Default behavior:
- Walk datasets/raw/raw_data/**/data.json
- For each index in data.json:
    - Answer is bbox (list of 4 numbers) -> write bbox
    - Answer is empty or "<pred_action>" -> write 0 0 0 0
- Add bbox_x1,bbox_y1,bbox_x2,bbox_y2 columns if missing
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BBOX_COLUMNS = ["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]


def _coerce_index(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        try:
            f = float(s)
        except ValueError:
            return None
        if f.is_integer():
            return int(f)
    return None


def _parse_bbox(answer: Any) -> Optional[List[float]]:
    if isinstance(answer, (list, tuple)):
        if len(answer) != 4:
            return None
        if all(isinstance(v, (int, float)) for v in answer):
            return [float(v) for v in answer]
        return None
    if isinstance(answer, str):
        s = answer.strip()
        if s in ("", "<pred_action>"):
            return None
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list) and len(parsed) == 4 and all(
            isinstance(v, (int, float)) for v in parsed
        ):
            return [float(v) for v in parsed]
    return None


def _build_index_map(json_path: Path) -> Tuple[Dict[int, List[float]], int]:
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError(f"invalid json ({exc})") from exc

    if not isinstance(data, list):
        raise ValueError("json root is not a list")

    index_map: Dict[int, List[float]] = {}
    skipped = 0
    for item in data:
        if not isinstance(item, dict):
            skipped += 1
            continue
        idx = _coerce_index(item.get("index"))
        if idx is None:
            skipped += 1
            continue
        bbox = _parse_bbox(item.get("Answer"))
        if bbox is None:
            index_map[idx] = [0.0, 0.0, 0.0, 0.0]
        else:
            index_map[idx] = bbox
    return index_map, skipped


def _format_bbox_value(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _update_csv(csv_path: Path, index_map: Dict[int, List[float]], dry_run: bool) -> Dict[str, int]:
    stats = {
        "rows": 0,
        "missing_index": 0,
        "extra_index": 0,
        "added_columns": 0,
    }
    tmp_path = csv_path.with_name(csv_path.name + ".tmp")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as in_f:
        reader = csv.reader(in_f)
        header = next(reader, None)
        if header is None:
            raise ValueError("empty csv")

        missing_cols = [c for c in BBOX_COLUMNS if c not in header]
        if missing_cols:
            header = header + missing_cols
            stats["added_columns"] = len(missing_cols)

        col_index = {col: header.index(col) for col in BBOX_COLUMNS}

        if not dry_run:
            out_f = tmp_path.open("w", encoding="utf-8", newline="")
        else:
            out_f = None

        try:
            if out_f:
                writer = csv.writer(out_f)
                writer.writerow(header)

            for row_idx, row in enumerate(reader):
                stats["rows"] += 1
                if len(row) < len(header):
                    row.extend([""] * (len(header) - len(row)))

                bbox = index_map.get(row_idx)
                if bbox is None:
                    stats["missing_index"] += 1
                    bbox = [0.0, 0.0, 0.0, 0.0]

                for col, value in zip(BBOX_COLUMNS, bbox):
                    row[col_index[col]] = _format_bbox_value(float(value))

                if out_f:
                    writer.writerow(row)
        finally:
            if out_f:
                out_f.close()

    if not dry_run:
        tmp_path.replace(csv_path)

    if index_map:
        max_index = max(index_map)
        if max_index + 1 > stats["rows"]:
            stats["extra_index"] = max_index + 1 - stats["rows"]

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync bbox columns in data.csv from data.json Answer fields."
    )
    parser.add_argument(
        "--root",
        default="datasets/raw/raw_data",
        help="Root dir that contains episodes (default: datasets/raw/raw_data).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report only; do not write files.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    json_files = sorted(root.rglob("data.json"))
    if not json_files:
        print(f"No data.json found under {root}", file=sys.stderr)
        return 1

    processed = 0
    skipped = 0
    updated = 0
    for json_path in json_files:
        csv_path = json_path.with_name("data.csv")
        if not csv_path.exists():
            print(f"[SKIP] missing csv: {csv_path}", file=sys.stderr)
            skipped += 1
            continue

        try:
            index_map, skipped_items = _build_index_map(json_path)
        except Exception as exc:
            print(f"[SKIP] {json_path}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        try:
            stats = _update_csv(csv_path, index_map, args.dry_run)
        except Exception as exc:
            print(f"[SKIP] {csv_path}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        rel = json_path.parent.relative_to(root)
        print(
            f"[OK] {rel}: rows={stats['rows']}, "
            f"missing_index={stats['missing_index']}, "
            f"extra_index={stats['extra_index']}, "
            f"added_columns={stats['added_columns']}, "
            f"skipped_items={skipped_items}"
        )

        processed += 1
        updated += 1

    print(
        f"Done. processed={processed}, skipped={skipped}, dry_run={args.dry_run}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
