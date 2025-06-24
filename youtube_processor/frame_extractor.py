import subprocess
from pathlib import Path
import shutil
from config import FFMPEG_PATH
import numpy as np


def extract_frames_per_segment(video_path, segments, output_folder="tmp_frames"):
    output_dir = Path(output_folder)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    for idx, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        duration = end - start
        if duration <= 0:
            continue

        # 3장 프레임을 균등하게 추출할 시간 지점 계산
        interval = 0.1  # 초
        timestamps = np.arange(start, end, interval)

        for i, ts in enumerate(timestamps):
            out_file = output_dir / f"{idx:03d}_{i+1}.jpg"
            cmd = f'"{FFMPEG_PATH}\\ffmpeg" -ss {ts:.3f} -i "{video_path}" -frames:v 1 -q:v 2 "{out_file}" -y -loglevel quiet'
            subprocess.run(cmd, shell=True, check=True)

        print(f"📸 세그먼트 {idx}: 총 {len(timestamps)}장 추출됨 ({timestamps[0]:.2f}s ~ {timestamps[-1]:.2f}s)")

