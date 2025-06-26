import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name

def extract_video_id(youtube_url):
    query = urlparse(youtube_url).query
    params = parse_qs(query)
    return params.get('v', [None])[0]


def run_mfa_align():
    command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "-v", "/c/youtude-downloader/syncdata/mfa:/data",
        "mmcauliffe/montreal-forced-aligner:latest",
        "mfa", "align",
        "/data/corpus", "/data/english_us_arpa.dict", "/data/english_us_arpa", "/data/mfa_output"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Error:", result.stderr)



# def reset_folder(folder="tmp_frames"):
#     path = Path(folder).resolve()  # 절대경로로 변환
#     print(f"📂 Deleting folder: {path}")  # 🔍 실제 경로 출력
#     if path.exists():
#         shutil.rmtree(path)
#     path.mkdir()
#     print(f"🧹 Folder '{folder}/' reset")