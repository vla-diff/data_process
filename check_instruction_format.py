#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

ROOT_DIR = "/mnt/diff-ali/workspace/wall-x/datasets/raw_data"

def ensure_period(s: str) -> str:
    """保证字符串以句点（. 或 。）结尾，不是则补一个 ."""
    s = s.rstrip()  # 去掉尾部空格
    if s.endswith('.') or s.endswith('。'):
        return s
    return s + '.'

def fix_instruction_file(path):
    """
    读取并尝试修正 instruction.txt 的格式。
    返回: (ok: bool, msg: str)
      ok=True 表示格式最终是合法的（包括自动修复成功）
      ok=False 表示无法修复，需要人工处理
    """
    if not os.path.isfile(path):  # 检查文件是否存在
        return False, "缺少 instruction.txt 文件",False

    try:
        with open(path, "r", encoding="utf-8") as f:
            original_content = f.read()
    except UnicodeDecodeError:
        return False, "文件不是 UTF-8 编码，无法处理", original_content

    if not original_content.strip():
        return False, "文件内容为空",False

    # 去掉首尾空白（包含换行），中间内容原样保留
    content = original_content.strip()

    # 简单查找 Catch: / Put: 的位置
    idx_catch = content.find("Catch:")
    idx_put = content.find("Put:")

    if idx_catch == -1 or idx_put == -1 or idx_put <= idx_catch:
        return False, "无法找到正确的 Catch: / Put: 位置，未修改",False

    prefix = content[:idx_catch].rstrip()  # 前缀去掉尾部空格
    catch_raw = content[idx_catch + len("Catch:"):idx_put]
    put_raw = content[idx_put + len("Put:"):]

    catch_part = catch_raw.strip()
    put_part = put_raw.strip()

    # 三部分都必须非空
    if not prefix:
        return False, "前缀说明部分为空，无法自动修复",False
    if not catch_part:
        return False, "Catch: 后内容为空，无法自动修复",False
    if not put_part:
        return False, "Put: 后内容为空，无法自动修复",False

    # 保证每一段都以句点结尾
    prefix_fixed = ensure_period(prefix)
    catch_fixed = ensure_period(catch_part)
    put_fixed = ensure_period(put_part)

    # 重新拼装为标准格式：XXX. Catch: AAA. Put: BBB.
    new_line = f"{prefix_fixed} Catch: {catch_fixed} Put: {put_fixed}"

    # 比较是否已是标准格式（忽略结尾换行差异）
    if original_content.rstrip("\r\n") == new_line:
        return True, "格式正确，无需修改", new_line

    # 需要修改：先写备份
    bak_path = path + ".bak"
    if not os.path.exists(bak_path):
        with open(bak_path, "w", encoding="utf-8") as f:
            f.write(original_content)

    # 再写入修正后的内容，统一加一个换行
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_line + "\n")
    
    return True, "已自动修复格式", new_line

def main():
    if not os.path.isdir(ROOT_DIR):
        print(f"根目录不存在: {ROOT_DIR}")
        return

    all_ok = True

    for name in sorted(os.listdir(ROOT_DIR)):
        subdir = os.path.join(ROOT_DIR, name)
        if not os.path.isdir(subdir):
            continue

        instr_path = os.path.join(subdir, "instruction.txt")
        ok, msg, new_line = fix_instruction_file(instr_path)

        status = "OK" if ok else "ERROR"
        if not ok:
            all_ok = False

        print(f"[{status}] {subdir} -> {msg}  修复为: {new_line}")

    if all_ok:
        print("\n全部子目录的 instruction.txt 最终格式均正确 ✅")
    else:
        print("\n存在无法自动修复的 instruction.txt，请检查上面的 ERROR 项 ❌")

if __name__ == "__main__":
    main()
