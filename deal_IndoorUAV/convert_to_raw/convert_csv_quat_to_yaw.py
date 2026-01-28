#!/usr/bin/env python3
"""
将现有 CSV 中的四元数列转换为 yaw 列
从: 时间戳(秒),位置X,位置Y,位置Z,姿态X,姿态Y,姿态Z,姿态W,bbox_x1,bbox_y1,bbox_x2,bbox_y2,前摄像头图像
到: 时间戳(秒),位置X,位置Y,位置Z,yaw,bbox_x1,bbox_y1,bbox_x2,bbox_y2,前摄像头图像
"""

import os
import pandas as pd
import numpy as np
from glob import glob
import argparse


def quaternion_to_yaw(qx, qy, qz, qw):
    """从四元数提取 yaw 角度（假设 roll=0, pitch=0）"""
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw_rad = np.arctan2(siny_cosp, cosy_cosp)
    return np.degrees(yaw_rad)


def convert_csv(csv_path):
    """转换单个 CSV 文件"""
    df = pd.read_csv(csv_path)
    
    # 检查是否已经是新格式
    if 'yaw' in df.columns and '姿态X' not in df.columns:
        return False  # 已经转换过
    
    # 计算 yaw
    yaw_values = quaternion_to_yaw(
        df['姿态X'].values,
        df['姿态Y'].values,
        df['姿态Z'].values,
        df['姿态W'].values
    )
    
    # 创建新 DataFrame
    new_df = pd.DataFrame({
        '时间戳(秒)': df['时间戳(秒)'],
        '位置X': df['位置X'],
        '位置Y': df['位置Y'],
        '位置Z': df['位置Z'],
        'yaw': yaw_values,
        'bbox_x1': df['bbox_x1'],
        'bbox_y1': df['bbox_y1'],
        'bbox_x2': df['bbox_x2'],
        'bbox_y2': df['bbox_y2'],
        '前摄像头图像': df['前摄像头图像']
    })
    
    new_df.to_csv(csv_path, index=False)
    return True


def main():
    parser = argparse.ArgumentParser(description='转换 CSV 中的四元数为 yaw')
    parser.add_argument('--intermediate_root', required=True, help='intermediate 数据根目录')
    args = parser.parse_args()
    
    # 查找所有 data.csv 文件
    csv_files = glob(os.path.join(args.intermediate_root, '**/data.csv'), recursive=True)
    
    print(f"找到 {len(csv_files)} 个 CSV 文件")
    
    converted = 0
    skipped = 0
    
    for i, csv_path in enumerate(csv_files):
        if convert_csv(csv_path):
            converted += 1
        else:
            skipped += 1
        
        if (i + 1) % 100 == 0:
            print(f"进度: {i + 1}/{len(csv_files)}")
    
    print(f"✅ 完成! 转换: {converted}, 跳过(已是新格式): {skipped}")


if __name__ == '__main__':
    main()
