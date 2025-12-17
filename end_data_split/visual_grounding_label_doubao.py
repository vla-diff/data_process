"""
读取 raw_data 下的 instruction.txt 解析目标（Catch/Put），按奇偶选择目标，
对 data.json 中 Answer 为空的帧调用多模态模型识别目标 bbox，填回 data.json。

规则：
- 路径形如 datasets/raw/raw_data/n/m/m-p/data.json
- instruction.txt 位于 datasets/raw/raw_data/n/instruction.txt
- m-p 里的 p 为奇数 -> 取 Catch 目标；偶数 -> 取 Put 目标
- 仅处理 data.json 中 Answer 为空的条目，对应图片为 images/front/camera0_{index:05d}.jpg

运行：python data_process/end_data_split/visual_grounding_label_doubao.py
"""

from __future__ import annotations

import base64
import json
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

from openai import OpenAI

# ==========================
# 配置
# ==========================
API_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
API_KEY_ENV = ""  # 请在环境变量中设置
MODEL_NAME = "doubao-seed-1-6-vision-250815"
MAX_CONCURRENT_REQUESTS = 8  # 控制并发请求数
SLEEP_BETWEEN_BATCHES = 0.0  # 如需节流可调大

RAW_ROOT = Path("datasets/raw/raw_data")
PROMPT_TEMPLATE = "图像是你当前的观测，如果能识别到{target}，则只给出的bounding box，格式：[x1, y1, x2, y2]，其他什么都不要输出。如果无法识别到{target}，则什么都不输出。如果图像中有多个可能的{target},标注最靠近图像中心的{target}整体。"


# ==========================
# 工具函数
# ==========================
def parse_task(task_str: str) -> Tuple[str, str, str]:
    """
    匹配英文格式：Catch: xxx. Put: yyy
    """
    match = re.search(r"(.*)Catch:\s*(.*)\.\s*Put:\s*(.*)", task_str)
    if match:
        instruction = match.group(1).strip()
        catch_target = match.group(2).strip()
        put_target = match.group(3).strip()
        return instruction, catch_target, put_target
    else:
        print("无法提取目标，原文：",task_str)
        assert False


def encode_image_to_base64(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_bbox_from_response(text: str) -> Optional[List[int]]:
    patterns = [
        r'bounding box[：:]\s*\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]',
        r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return [int(m.group(i)) for i in range(1, 5)]
    return None


def call_api(image_path: Path, target: str, client: OpenAI) -> Optional[List[int]]:
    """
    调用多模态模型获取 bbox，返回 [x1,x2,y1,y2] 或 None
    """
    try:
        base64_image = encode_image_to_base64(image_path)
        prompt = PROMPT_TEMPLATE.format(target=target)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        # doubao 返回 choices[].message.content
        raw_text = resp.choices[0].message.content or ""
        return parse_bbox_from_response(raw_text)
    except Exception as e:
        print(f"[ERROR] 调用模型失败 {image_path.name}: {e}")
        return None


async def process_step(
    semaphore: asyncio.Semaphore,
    executor: ThreadPoolExecutor,
    image_path: Path,
    target: str,
    client: OpenAI,
) -> Optional[List[int]]:
    loop = asyncio.get_event_loop()
    async with semaphore:
        return await loop.run_in_executor(executor, call_api, image_path, target, client)


def pick_target(folder_name: str, catch_target: str, put_target: str) -> str:
    """
    folder_name 形如 '3-1'，取 '-' 后面的数字 p，奇数返回 catch，偶数返回 put。
    """
    if "-" not in folder_name:
        return catch_target or put_target
    try:
        p_str = folder_name.split("-")[-1]
        p = int(p_str)
    except Exception:
        return catch_target or put_target
    return catch_target if p % 2 == 1 else put_target


async def process_episode(
    data_path: Path,
    client: OpenAI,
    semaphore: asyncio.Semaphore,
    executor: ThreadPoolExecutor,
) -> None:
    """
    对单个 episode (data.json) 填充 bbox。
    """
    try:
        n_dir = data_path.parents[2].name  # raw_data/<n>/<m>/<m-p>/data.json
        mp_dir = data_path.parent.name
    except IndexError:
        print(f"[SKIP] 无法解析路径: {data_path}")
        return
    # if n_dir != "16": #需要单独标某类任务时用
    #     print(f"[SKIP] n != 16: {data_path}")
    #     return

    instr_path = RAW_ROOT / n_dir / "instruction.txt"
    if not instr_path.exists():
        print(f"[SKIP] 缺少 instruction.txt: {instr_path}")
        return
    instruction_text = instr_path.read_text(encoding="utf-8").strip()
    _, catch_target, put_target = parse_task(instruction_text)
    target = pick_target(mp_dir, catch_target, put_target)
    if not target:
        print(f"[SKIP] 未解析到目标: {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        steps = json.load(f)

    tasks = []
    idx_map = {}
    for step in steps:
        ans = step.get("Answer")
        if ans == "<pred_action>":
            continue  # 显式占位跳过
        if ans:  # 已有答案（例如 bbox），跳过
            continue
        idx = step.get("index")
        if idx is None:
            continue
        img_path = data_path.parent / "images" / "front" / f"camera0_{idx:05d}.jpg"

        if not img_path.exists():
            print(f"  [SKIP] 缺少图片: {img_path}")
            continue
        task = asyncio.create_task(process_step(semaphore, executor, img_path, target, client))
        tasks.append(task)
        idx_map[task] = step

    if not tasks:
        print(f"[OK] {data_path}: 无需处理（无待标注或均为占位符）")
        return

    print(f"[PROCESS] {data_path} target={target} 待处理 {len(tasks)} 张")

    results = await asyncio.gather(*tasks)
    for task, bbox in zip(tasks, results):
        step = idx_map[task]
        idx = step.get("index")
        if bbox:
            step["Answer"] = bbox
            step["target"] = target
            step["prompt"] = PROMPT_TEMPLATE.format(target=target)
            step["image_path"] = str(data_path.parent / "images" / "front" / f"camera0_{idx:05d}.jpg")
            print(f"  [OK] index={idx} bbox={bbox}")
        else:
            print(f"  [FAIL] index={idx} 未获得 bbox")

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(steps, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] 更新 {data_path}")


async def main() -> None:
    api_key = API_KEY_ENV
    if not api_key:
        raise RuntimeError(f"请设置环境变量 {API_KEY_ENV} 为你的豆包 API Key")
    client = OpenAI(base_url=API_BASE_URL, api_key=api_key)
    data_files = sorted(RAW_ROOT.glob("*/*/*/data.json"))
    if not data_files:
        print(f"未找到 data.json，路径：{RAW_ROOT}")
        return

    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    for data_path in data_files:
        await process_episode(data_path, client, semaphore, executor)
        if SLEEP_BETWEEN_BATCHES:
            await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

    executor.shutdown(wait=True)


if __name__ == "__main__":
    asyncio.run(main())
