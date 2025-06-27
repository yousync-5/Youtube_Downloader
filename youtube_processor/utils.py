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
        "/data/corpus", "/data/english_us_arpa.dict", "/data/english_us_arpa", "/data/mfa_output",
        "--clean",
        "--beam", "10",
        "--retry_beam", "40",
        "--phone_boundary_method", "strict",
        "--output_format", "long_textgrid"
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True,  encoding="utf-8")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ MFA 실행 중 오류 발생!")
        print("📤 stdout:\n", e.stdout)
        print("📥 stderr:\n", e.stderr)


def reset_folder(*folders, remove_only_files=False):
    for folder in folders:
        path = Path(__file__).parent / folder  # 모듈 기준 상대경로로 보정
        print(f"📂 Resetting folder: {path.resolve()}")
        if path.exists():
            if remove_only_files:
                # 폴더는 유지, 내부 내용 삭제
                for child in path.iterdir():
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        shutil.rmtree(child)
            else:
                # 폴더 자체를 삭제 후 재생성
                shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)
        else:
            # 폴더가 없으면 생성
            path.mkdir(parents=True, exist_ok=True)
        print(f"🧹 Folder '{folder}/' reset")