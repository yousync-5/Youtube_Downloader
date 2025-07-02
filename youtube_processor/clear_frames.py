from .utils import reset_folder  # ✅ 상대경로 import
from pathlib import Path

reset_folder("tmp_frames", "downloads", "separated/htdemucs", "pitch_data", "split_tokens")

# 확인용: 폴더 내부에 남아 있는 파일 출력
tmp_dir = Path(__file__).parent / "tmp_frames"  # ✅ 폴더 경로 기준 보정
files = list(tmp_dir.glob("*"))
if files:
    print("⚠️ Still exists:", [f.name for f in files])
else:
    print("✅ Folder is truly empty.")
