"""
读取 datasets/raw/raw_data 下的每个 data.json，按照其中的 image_path / Answer / target
在对应图片上绘制 bbox，并输出到指定目录，保持原有相对目录结构。

运行示例（仓库根目录）：
    python data_process/end_data_split/draw_bboxes.py \
        --output-root datasets/raw/annotated
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

RAW_ROOT = Path("datasets/raw/raw_data")


def parse_bbox(ans) -> List[int] | None:
    """将 Answer 解析为 [x1,y1,x2,y2]，无法解析则返回 None。"""
    if ans is None:
        return None
    if isinstance(ans, list) and len(ans) == 4:
        try:
            return [int(float(x)) for x in ans]
        except Exception:
            return None
    return None


def convert_bbox_to_image_space(bbox: List[int], img_w: int, img_h: int) -> List[int] | None:
    """
    将 bbox 转成像素坐标，并确保顺序和边界合法。
    如果坐标明显大于图像尺寸（如 0-1000 归一化），按 1000->width/height 缩放。
    """
    if not bbox:
        return None
    x1, y1, x2, y2 = bbox

    # 如任一坐标超出图像尺寸，尝试按 0-1000 缩放到像素
    # if max(bbox) > max(img_w, img_h) or x1 > img_w or x2 > img_w or y1 > img_h or y2 > img_h:
    x1 = int(x1 / 1000 * img_w)
    x2 = int(x2 / 1000 * img_w)
    y1 = int(y1 / 1000 * img_h)
    y2 = int(y2 / 1000 * img_h)

    # 排序、裁剪
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    x1 = max(0, min(x1, img_w - 1))
    x2 = max(0, min(x2, img_w - 1))
    y1 = max(0, min(y1, img_h - 1))
    y2 = max(0, min(y2, img_h - 1))

    # 确保有面积
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def draw_and_save(image_path: Path, bbox: List[int], target: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)
        converted = convert_bbox_to_image_space(bbox, img.width, img.height)
        if not converted:
            raise ValueError("bbox invalid after conversion/clamp")
        x1, y1, x2, y2 = converted
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        # 文本放在右上角
        font = ImageFont.load_default()
        text = target or ""
        if text:
            try:
                # Pillow>=8.0 推荐 textbbox
                bbox_text = draw.textbbox((0, 0), text, font=font)
                text_w, text_h = bbox_text[2] - bbox_text[0], bbox_text[3] - bbox_text[1]
            except Exception:
                # 兼容旧版本
                text_w, text_h = font.getsize(text)
            pad = 4
            pos = (img.width - text_w - pad, pad)
            draw.rectangle(
                [pos[0] - pad, pos[1] - pad, pos[0] + text_w + pad, pos[1] + text_h + pad],
                fill="red",
            )
            draw.text(pos, text, fill="white", font=font)
        img.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw bboxes from data.json onto images.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("datasets/raw/annotated"),
        help="输出根目录，内部保持与原始图片相同的相对路径。",
    )
    args = parser.parse_args()

    data_files = sorted(RAW_ROOT.glob("*/*/*/data.json"))
    if not data_files:
        print(f"未找到 data.json，路径：{RAW_ROOT}")
        return

    total = ok = skipped = 0
    for data_path in data_files:
        with open(data_path, "r", encoding="utf-8") as f:
            steps = json.load(f)
        for step in steps:
            ans = step.get("Answer")
            bbox = parse_bbox(ans)
            if not bbox:
                continue
            img_path = step.get("image_path")
            target = step.get("target", "")
            if not img_path:
                continue
            img_path = Path(img_path)
            if not img_path.exists():
                print(f"[SKIP] 图片不存在: {img_path}")
                skipped += 1
                continue
            try:
                rel = img_path.relative_to(RAW_ROOT)
            except ValueError:
                # 如果 image_path 不是 RAW_ROOT 下的绝对路径，则以文件名保存
                rel = Path(img_path.name)
            out_path = args.output_root / rel
            try:
                draw_and_save(img_path, bbox, target, out_path)
                ok += 1
            except Exception as e:
                print(f"[FAIL] 绘制失败 {img_path}: {e}")
                skipped += 1
            total += 1

    print(f"完成。成功 {ok}, 跳过/失败 {skipped}, 总计 {total}")


if __name__ == "__main__":
    main()
