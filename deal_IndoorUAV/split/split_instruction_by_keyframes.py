#python ../data_process/deal_IndoorUAV/split_instruction_by_keyframes.py   --root datasets/IndoorUAV/hm3d_16/1K7P6ZQS4VM   -
-traj traj_-1#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from volcenginesdkarkruntime import Ark

# ==========================
# Config (aligned with scripts/API.py style)
# ==========================
DEFAULT_API_KEY_ENV = "ARK_API_KEY"
DEFAULT_MODEL_NAME = "doubao-1-5-pro-32k-250115"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_instruction(text: str) -> List[str]:
    parts = re.split(r"[，,]", text)
    return [part.strip() for part in parts if part.strip()]


def build_messages(
    key_frames: List[Tuple[int, str]],
    subtasks: List[str],
) -> List[Dict[str, str]]:
    system_msg = (
        "You map navigation subtasks to key frame ranges. "
        "Only output valid JSON."
    )
    key_frame_lines = ["Key frames (ordered):"]
    for frame_id, desc in key_frames:
        key_frame_lines.append(f"- {frame_id}: {desc}")
    subtask_lines = ["Subtasks (ordered):"]
    for idx, subtask in enumerate(subtasks, start=1):
        subtask_lines.append(f"- {idx}: {subtask}")
    rules = (
        "Rules:\n"
        "1) Use only the key frame IDs listed above.\n"
        "2) Each subtask must map to a contiguous range of key frame IDs in order.\n"
        "3) Cover all key frames in order with no overlaps or gaps across subtasks.\n"
        "4) The first subtask starts at the first key frame; the last ends at the last key frame.\n"
        "5) Output JSON only, using the exact schema below.\n\n"
        "Schema:\n"
        "{\n"
        '  "subtasks": [\n'
        '    {"subtask_index": 1, "start_key_frame": 1, "end_key_frame": 5},\n'
        "    ...\n"
        "  ]\n"
        "}\n"
    )
    user_msg = "\n".join(key_frame_lines + [""] + subtask_lines + ["", rules])
    return [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]


def call_chat_completions(
    client: Ark,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def extract_json(text: str) -> Optional[Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidates = []
    first_curly = text.find("{")
    last_curly = text.rfind("}")
    if first_curly != -1 and last_curly != -1 and last_curly > first_curly:
        candidates.append(text[first_curly : last_curly + 1])
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        candidates.append(text[first_bracket : last_bracket + 1])
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def normalize_mapping(
    data: Any,
    subtasks: List[str],
    key_frame_ids: List[int],
) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("subtasks")
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("LLM output is not a dict or list.")
    if not isinstance(items, list):
        raise ValueError("LLM output missing 'subtasks' list.")

    items_by_index: Dict[int, Dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if "subtask_index" in item:
            try:
                items_by_index[int(item["subtask_index"])] = item
            except (TypeError, ValueError):
                continue

    normalized: List[Dict[str, Any]] = []
    for idx, subtask in enumerate(subtasks, start=1):
        item = items_by_index.get(idx)
        if item is None and len(items) == len(subtasks):
            item = items[idx - 1] if isinstance(items[idx - 1], dict) else None
        if item is None:
            raise ValueError(f"Missing mapping for subtask {idx}.")

        try:
            start_kf = int(item["start_key_frame"])
            end_kf = int(item["end_key_frame"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid key frame range for subtask {idx}.") from exc

        if start_kf not in key_frame_ids or end_kf not in key_frame_ids:
            raise ValueError(f"Key frame ID not found for subtask {idx}.")

        normalized.append(
            {
                "subtask_index": idx,
                "subtask": subtask,
                "start_key_frame": start_kf,
                "end_key_frame": end_kf,
            }
        )

    return normalized


def validate_ranges(
    ranges: List[Dict[str, Any]],
    key_frame_ids: List[int],
) -> List[str]:
    warnings: List[str] = []
    id_to_pos = {kf: i for i, kf in enumerate(key_frame_ids)}
    prev_end_pos = -1
    for item in ranges:
        start_pos = id_to_pos[item["start_key_frame"]]
        end_pos = id_to_pos[item["end_key_frame"]]
        if start_pos > end_pos:
            warnings.append(
                f"Subtask {item['subtask_index']} has start after end."
            )
        if start_pos < prev_end_pos:
            warnings.append(
                f"Subtask {item['subtask_index']} overlaps previous range."
            )
        if prev_end_pos != -1 and start_pos > prev_end_pos + 1:
            warnings.append(
                f"Gap between subtasks {item['subtask_index'] - 1} and {item['subtask_index']}."
            )
        prev_end_pos = end_pos
    if ranges:
        first_pos = id_to_pos[ranges[0]["start_key_frame"]]
        last_pos = id_to_pos[ranges[-1]["end_key_frame"]]
        if first_pos != 0:
            warnings.append("First subtask does not start at first key frame.")
        if last_pos != len(key_frame_ids) - 1:
            warnings.append("Last subtask does not end at last key frame.")
    return warnings


def iter_traj_dirs(root: Path, names: Optional[List[str]]) -> List[Path]:
    if names:
        return [root / name for name in names]
    return sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("traj_")]
    )


def process_traj(
    traj_dir: Path,
    args: argparse.Namespace,
    client: Ark,
) -> str:
    instruction_path = traj_dir / "instruction.json"
    key_frames_path = traj_dir / "key_frames.json"
    if not instruction_path.exists() or not key_frames_path.exists():
        print(f"Skip {traj_dir}: missing instruction/key_frames.", file=sys.stderr)
        return "failed"

    output_path = traj_dir / args.output_name
    if output_path.exists() and not args.overwrite:
        print(f"Skip {traj_dir}: output exists.", file=sys.stderr)
        return "skipped"

    try:
        instruction_json = load_json(instruction_path)
        instruction_text = instruction_json["instruction"]
        key_frames_json = load_json(key_frames_path)
        key_frames = sorted(
            ((int(k), v) for k, v in key_frames_json.items()),
            key=lambda x: x[0],
        )
    except Exception as exc:
        print(f"Skip {traj_dir}: failed to read json ({exc}).", file=sys.stderr)
        return "failed"

    subtasks = split_instruction(instruction_text)
    if not subtasks:
        print(f"Skip {traj_dir}: no subtasks after split.", file=sys.stderr)
        return "failed"

    messages = build_messages(key_frames, subtasks)
    print(
        f"[CALL] {traj_dir} subtasks={len(subtasks)} key_frames={len(key_frames)}"
    )
    sys.stdout.flush()
    content = None
    for attempt in range(args.max_retries + 1):
        try:
            content = call_chat_completions(
                client=client,
                model=args.model,
                messages=messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
            break
        except Exception as exc:
            if attempt >= args.max_retries:
                print(f"{traj_dir}: API error {exc}.", file=sys.stderr)
                return "failed"
            time.sleep(1.5 * (attempt + 1))

    if content is None:
        return "failed"

    data = extract_json(content)
    if data is None:
        print(f"{traj_dir}: failed to parse JSON from response.", file=sys.stderr)
        return "failed"

    key_frame_ids = [kf_id for kf_id, _ in key_frames]
    try:
        mapped = normalize_mapping(data, subtasks, key_frame_ids)
    except ValueError as exc:
        print(f"{traj_dir}: {exc}", file=sys.stderr)
        return "failed"

    warnings = validate_ranges(mapped, key_frame_ids)
    for warning in warnings:
        print(f"{traj_dir}: {warning}", file=sys.stderr)

    output = {
        "instruction": instruction_text,
        "subtasks": mapped,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if args.sleep > 0:
        time.sleep(args.sleep)

    return "written"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split instructions and map subtasks to key frame ranges."
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Root folder that contains trajectory subfolders (traj_*)",
    )
    parser.add_argument(
        "--traj",
        action="append",
        default=None,
        help="Specific trajectory subfolder name(s) to process (repeatable).",
    )
    parser.add_argument(
        "--output-name",
        default="instruction_split.json",
        help="Output JSON filename to write inside each trajectory folder.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE"),
        help="Optional API base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get(DEFAULT_API_KEY_ENV),
        help="API key (or set LLM_API_KEY / OPENAI_API_KEY / ARK_API_KEY).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL", DEFAULT_MODEL_NAME),
        help="Model name for the API call.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Sleep seconds between requests.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens for completion.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Max retries for API errors.",
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Disable proxy environment variables for HTTP requests.",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "Missing API key. Set --api-key or LLM_API_KEY/OPENAI_API_KEY/ARK_API_KEY.",
            file=sys.stderr,
        )
        return 2

    if args.no_proxy:
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"

    client_kwargs = {"api_key": args.api_key, "timeout": args.timeout}
    if args.api_base:
        client_kwargs["base_url"] = args.api_base
    try:
        client = Ark(**client_kwargs)
    except TypeError as exc:
        if "base_url" in str(exc) and "base_url" in client_kwargs:
            client_kwargs.pop("base_url", None)
            client = Ark(**client_kwargs)
        else:
            raise

    traj_dirs = iter_traj_dirs(args.root, args.traj)
    if not traj_dirs:
        print("No trajectory folders found.", file=sys.stderr)
        return 1

    results = []
    for traj_dir in traj_dirs:
        results.append(process_traj(traj_dir, args, client))

    total = len(traj_dirs)
    written = sum(1 for r in results if r == "written")
    failed = sum(1 for r in results if r == "failed")
    print(f"Done. total={total} written={written} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
