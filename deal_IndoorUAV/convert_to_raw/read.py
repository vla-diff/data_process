import pandas as pd
import numpy as np
import os

def format_list_column(df, colname):
    """将列中的 list/array 格式化为保留四位小数的字符串"""
    return df[colname].apply(
        lambda x: "[" + ", ".join([f"{float(v):.4f}" for v in eval(x) if str(v) != 'nan']) + "]"
        if isinstance(x, str) and x.startswith("[") else x
    )

def read_parquet(file_path: str, save_csv: bool = True):
    try:
        # 设置显示完整内容，不省略
        pd.set_option("display.max_colwidth", None)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_rows", None)  # 显示所有行（取消行省略）

        # 读取 parquet 文件
        df = pd.read_parquet(file_path)

        # 找出可能是 list 的列（比如 state.position / state.quaternion）
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    df[col] = format_list_column(df, col)
                except Exception:
                    pass

        print(f"✅ 文件 {file_path} 读取成功！")
        print(f"📊 数据维度: {df.shape}")
        print(f"🧾 列名: {list(df.columns)}\n")
        print(df)

        # 🚀 额外功能：保存为 CSV 文件
        if save_csv:
            # 自动生成 csv 文件名
            csv_file = os.path.splitext(file_path)[0] + ".csv"
            df.to_csv(csv_file, index=False, encoding="utf-8")
            print(f"💾 已成功将数据保存为 CSV：{csv_file}")

    except Exception as e:
        print(f"❌ 读取失败: {e}")

if __name__ == "__main__":
    # 🔧 在这里设置 parquet 文件路径
    file_path = r"/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/IndoorUAV_lerobot_all/gibson_2_lerobot/data/chunk-001/episode_000001.parquet"
    read_parquet(file_path)
