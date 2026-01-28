#!/usr/bin/env python3
import argparse
import csv
import math
import os


def quat_multiply(q1, q2):
    # Hamilton product (x, y, z, w)
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    return (x, y, z, w)


def quat_normalize(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n == 0.0:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / n, y / n, z / n, w / n)


def unity_to_ros_position(x, y, z):
    # Matches plugin_patch/ImageMsgSerializer.cs UnityToRosPosition
    return (x, y, z)


def unity_yaw_to_ros_quat(yaw_rad):
    # Unity yaw (around Y) -> Unity quaternion
    sy = math.sin(yaw_rad / 2.0)
    cy = math.cos(yaw_rad / 2.0)
    q_unity = (0.0, sy, 0.0, cy)

    # Matches plugin_patch/ImageMsgSerializer.cs UnityToRosRotation
    q1 = (-q_unity[0], -q_unity[2], -q_unity[1], q_unity[3])  # (-x, -z, -y, w)
    s = math.sin(math.radians(90.0) / 2.0)
    c = math.cos(math.radians(90.0) / 2.0)
    q90 = (0.0, 0.0, s, c)  # Quaternion.Euler(0, 0, 90)

    q_ros = quat_multiply(q1, q90)
    q_ros = quat_normalize(q_ros)

    # Standardize to w >= 0
    if q_ros[3] < 0.0:
        q_ros = tuple(-v for v in q_ros)

    return q_ros


def detect_yaw_unit(yaw_val):
    # Heuristic: if magnitude looks like degrees, assume degrees
    if abs(yaw_val) > (2.0 * math.pi + 0.1):
        return "deg"
    return "rad"


def convert_csv(input_csv, output_csv, yaw_unit="auto"):
    same_path = os.path.abspath(input_csv) == os.path.abspath(output_csv)
    tmp_path = output_csv + ".tmp" if same_path else output_csv

    with open(input_csv, "r", newline="") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames or []

        def pick(keys):
            for k in keys:
                if k in fieldnames:
                    return k
            return None

        k_time = pick(["时间戳(秒)", "timestamp", "time"])
        k_x = pick(["位置X", "x", "pos_x"])
        k_y = pick(["位置Y", "y", "pos_y"])
        k_z = pick(["位置Z", "z", "pos_z"])
        k_yaw = pick(["yaw", "Yaw"])

        missing = [k for k in [k_time, k_x, k_y, k_z, k_yaw] if k is None]
        if missing:
            raise ValueError(f"缺少必要列: {missing} (文件: {input_csv})")

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)

        with open(tmp_path, "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow([
                "时间戳(秒)", "位置X", "位置Y", "位置Z",
                "姿态X", "姿态Y", "姿态Z", "姿态W"
            ])

            for row in reader:
                try:
                    t = float(row[k_time])
                    ux = float(row[k_x])
                    uy = float(row[k_y])
                    uz = float(row[k_z])
                    yaw_raw = float(row[k_yaw])
                except (TypeError, ValueError):
                    continue

                unit = yaw_unit
                if unit == "auto":
                    unit = detect_yaw_unit(yaw_raw)
                yaw_rad = math.radians(yaw_raw) if unit == "deg" else yaw_raw

                rx, ry, rz = unity_to_ros_position(ux, uy, uz)
                qx, qy, qz, qw = unity_yaw_to_ros_quat(yaw_rad)

                writer.writerow([
                    f"{t:.3f}",
                    f"{rx:.3f}", f"{ry:.3f}", f"{rz:.3f}",
                    f"{qx:.6f}", f"{qy:.6f}", f"{qz:.6f}", f"{qw:.6f}",
                ])

    if same_path:
        os.replace(tmp_path, output_csv)


def main():
    parser = argparse.ArgumentParser(
        description="批量将 Unity 原生 xyz+yaw 的 CSV 转为 xyz+四元数格式"
    )
    parser.add_argument(
        "--input-root",
        default="/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/merged_all",
        help="输入数据根目录 (默认: indoor_uav_data)"
    )
    parser.add_argument(
        "--output-root",
        "--output-path",
        dest="output_root",
        default="/home/bozhi/Desktop/DataCollect/all_data2",
        help="输出数据根目录 (默认: all_data2; 未使用 --overwrite 时生效)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="原地覆盖 input-root 下的 data.csv"
    )

    args = parser.parse_args()

    input_root = os.path.abspath(args.input_root)
    output_root = os.path.abspath(args.output_root)

    converted = 0
    for dirpath, _dirnames, filenames in os.walk(input_root):
        if "data.csv" not in filenames:
            continue

        input_csv = os.path.join(dirpath, "data.csv")
        rel = os.path.relpath(input_csv, input_root)
        parts = rel.split(os.sep)
        if len(parts) < 2:
            continue

        if args.overwrite:
            output_csv = input_csv
        else:
            leaf = parts[-2]
            out_leaf = f"{leaf}-1"
            out_dir = os.path.join(output_root, *parts[:-2], out_leaf)
            output_csv = os.path.join(out_dir, "data.csv")

        convert_csv(input_csv, output_csv, yaw_unit="auto")
        converted += 1
        print("converted:", converted)

    print(f"完成: 转换 {converted} 个 CSV")


if __name__ == "__main__":
    main()
