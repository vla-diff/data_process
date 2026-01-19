#!/usr/bin/env python3
import rerun as rr
import pandas as pd
import numpy as np
import cv2

rr.init("gibson_episode_0", spawn=False)

df = pd.read_parquet("/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot_test/data/chunk-000/episode_000000.parquet")
video_path = "/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_lerobot_test/videos/chunk-000/video.front/episode_000000.mp4"

cap = cv2.VideoCapture(video_path)

for idx, row in df.iterrows():
    rr.set_time_sequence("frame", int(idx))

    state = np.array(row['state'])
    action = np.array(row['action'])

    rr.log("state/position_x", rr.Scalar(float(state[0])))
    rr.log("action/position_x", rr.Scalar(float(action[0])))

    ret, frame = cap.read()
    if ret:
        rr.log("camera/front", rr.Image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))

cap.release()

output_file = "/inspire/hdd/global_user/konghanlin-253108540238/datasets/dzb/gibson_episode_0.rrd"
rr.save(output_file)
print(f"✅ Saved to {output_file}")
