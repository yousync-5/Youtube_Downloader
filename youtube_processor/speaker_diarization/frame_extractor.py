import subprocess
from pathlib import Path
import shutil
from config import FFMPEG_PATH
import numpy as np


def extract_frames_per_segment(video_path, segments, output_folder="tmp_frames"):
    output_dir = Path(output_folder)
    print(f"[DEBUG] video_path: {video_path}, exists: {Path(video_path).exists()}")
    print(f"[DEBUG] FFMPEG_PATH: {FFMPEG_PATH}, exists: {Path(FFMPEG_PATH).exists()}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    for idx, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        duration = end - start
        print(f"[DEBUG] Segment {idx}: start={start}, end={end}, duration={duration}")
        if duration <= 0:
            print(f"[WARNING] Segment {idx} duration <= 0, skip.")
            continue

        # 3장 프레임을 균등하게 추출할 시간 지점 계산
        interval = 0.1  # 초
        timestamps = np.arange(start, end, interval)
        print(f"[DEBUG] Segment {idx}: timestamps={timestamps}")

        for i, ts in enumerate(timestamps):
            out_file = output_dir / f"{idx:03d}_{i+1}.jpg"
            cmd = f'"{FFMPEG_PATH}" -ss {ts:.3f} -i "{video_path}" -frames:v 1 -q:v 2 "{out_file}" -y -loglevel quiet'
            try:
                subprocess.run(cmd, shell=True, check=True)
            except Exception as e:
                print(f"[ERROR] ffmpeg 실행 실패 (segment {idx}, ts={ts}): {e}")
                print(f"[ERROR] 실행한 명령어: {cmd}")
        if len(timestamps) > 0:
            print(f"📸 세그먼트 {idx}: 총 {len(timestamps)}장 추출됨 ({timestamps[0]:.2f}s ~ {timestamps[-1]:.2f}s)")
        else:
            print(f"[WARNING] Segment {idx}: timestamps 비어 있음.")

