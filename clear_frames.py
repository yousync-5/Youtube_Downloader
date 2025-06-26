from youtube_processor.utils import reset_folder
from pathlib import Path

reset_folder("tmp_frames")

# 확인용: 폴더 내부에 남아 있는 파일 출력
files = list(Path("tmp_frames").glob("*"))
if files:
    print("⚠️ Still exists:", [f.name for f in files])
else:
    print("✅ Folder is truly empty.")