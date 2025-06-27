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
    # 현재 프로젝트 루트에서 상대 경로로 syncdata 찾기
    current_dir = Path(__file__).parent  # youtube_processor 디렉토리
    project_root = current_dir.parent  # Youtube_Downloader 디렉토리
    mfa_data_path = project_root / "syncdata" / "mfa"
    
    # 절대 경로로 변환 (Docker가 요구)
    mfa_data_absolute = mfa_data_path.resolve()
    
    print(f"Docker MFA 경로: {mfa_data_absolute}")
    
    # 새로 생성한 컨테이너 사용
    container_name = "mfa-container"
    print(f"컨테이너 사용: {container_name}")
    
    # 컨테이너에서 MFA 실행
    command = [
        "docker", "exec", container_name,
        "mfa", "align", "--verbose",
        "/data/corpus", "/data/english_us_arpa.dict", "/data/english_us_arpa", "/data/mfa_output"
    ]
    
    print(f"MFA 명령어 실행: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    print("MFA 출력:")
    print(result.stdout)
    if result.returncode != 0:
        print("MFA 에러:")
        print(result.stderr)
    else:
        print("MFA 정렬 완료!")



# def reset_folder(folder="tmp_frames"):
#     path = Path(folder).resolve()  # 절대경로로 변환
#     print(f"📂 Deleting folder: {path}")  # 🔍 실제 경로 출력
#     if path.exists():
#         shutil.rmtree(path)
#     path.mkdir()
#     print(f"🧹 Folder '{folder}/' reset")