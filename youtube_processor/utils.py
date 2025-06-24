import re
import shutil
from pathlib import Path
def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name

def reset_folder(folder="tmp_frames"):
    path = Path(folder).resolve()  # 절대경로로 변환
    print(f"📂 Deleting folder: {path}")  # 🔍 실제 경로 출력
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    print(f"🧹 Folder '{folder}/' reset")