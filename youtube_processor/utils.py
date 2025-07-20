# import re
# import shutil
# import subprocess
# from pathlib import Path
# from urllib.parse import urlparse, parse_qs
# import boto3
# from botocore.exceptions import ClientError
# def sanitize_filename(name):
#     name = re.sub(r'[\\/*?:"<>|]', '', name)
#     name = re.sub(r'\s+', '_', name)
#     return name

# def extract_video_id(youtube_url):
#     query = urlparse(youtube_url).query
#     params = parse_qs(query)
#     return params.get('v', [None])[0]


# def run_mfa_align():
#     # 현재 프로젝트 루트에서 상대 경로로 syncdata 찾기
#     current_dir = Path(__file__).parent  # youtube_processor 디렉토리
#     project_root = current_dir.parent  # Youtube_Downloader 디렉토리
#     mfa_data_path = project_root / "syncdata" / "mfa"
    
#     # 절대 경로로 변환 (Docker가 요구)
#     mfa_data_absolute = mfa_data_path.resolve()
    
#     print(f"Docker MFA 경로: {mfa_data_absolute}")
    
#     # 새로 생성한 컨테이너 사용
#     container_name = "mfa-container"
#     print(f"컨테이너 사용: {container_name}")
    
#     # 컨테이너에서 MFA 실행
#     command = [
#         "docker", "run", "--rm", "--platform", "linux/amd64",
#         "-v", "/c/Users/wonsa/Desktop/youtube_data/youtube-downloader/syncdata/mfa:/data",
#         "mmcauliffe/montreal-forced-aligner:latest",
#         "mfa", "align",
#         "/data/corpus", "/data/english_us_arpa.dict", "/data/english_us_arpa", "/data/mfa_output",
#         "--clean",
#         "--beam", "100",
#         "--retry_beam", "400",
#         "--phone_boundary_method", "strict",
#         "--output_format", "long_textgrid"
#     ]

#     try:
#         result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")

#         print(result.stdout)
#     except subprocess.CalledProcessError as e:
#         print("❌ MFA 실행 중 오류 발생!")
#         print("📤 stdout:\n", e.stdout)
#         print("📥 stderr:\n", e.stderr)


# def reset_folder(*folders, remove_only_files=False):
#     for folder in folders:
#         path = Path(__file__).parent / folder  # 모듈 기준 상대경로로 보정
#         print(f"📂 Resetting folder: {path.resolve()}")
#         if path.exists():
#             if remove_only_files:
#                 # 폴더는 유지, 내부 내용 삭제
#                 for child in path.iterdir():
#                     if child.is_file():
#                         child.unlink()
#                     elif child.is_dir():
#                         shutil.rmtree(child)
#             else:
#                 # 폴더 자체를 삭제 후 재생성
#                 shutil.rmtree(path)
#                 path.mkdir(parents=True, exist_ok=True)
#         else:
#             # 폴더가 없으면 생성
#             path.mkdir(parents=True, exist_ok=True)
#         print(f"🧹 Folder '{folder}/' reset")

# def generate_presigned_url(bucket: str, key: str, expiration: int = 3600):
#     """
#     Presigned URL을 생성합니다.

#     :param bucket: S3 버킷 이름
#     :param key: S3 객체의 Key (폴더/파일명 포함)
#     :param expiration: URL 유효 시간 (초, 기본 1시간)
#     :return: presigned URL 문자열 또는 None (실패 시)
#     """
#     # S3 클라이언트 생성
#     s3 = boto3.client('s3', region_name='ap-northeast-2') 

#     try:
#         # presigned URL 생성
#         response = s3.generate_presigned_url(
#             ClientMethod="get_object",
#             Params={"Bucket": bucket, "Key": key},
#             ExpiresIn=expiration,
#         )
#         return response

#     except ClientError as e:
#         # 오류 발생 시 에러 출력 및 None 반환
#         print("❌ Presigned URL 생성 실패:", e)
#         return None

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import boto3
from botocore.exceptions import ClientError


def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name


def extract_video_id(youtube_url):
    query = urlparse(youtube_url).query
    params = parse_qs(query)
    return params.get('v', [None])[0]


def reset_folder(*folders, remove_only_files=False):
    for folder in folders:
        path = Path(__file__).parent / folder
        print(f"📂 Resetting folder: {path.resolve()}")
        if path.exists():
            if remove_only_files:
                for child in path.iterdir():
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        shutil.rmtree(child)
            else:
                shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        print(f"🧹 Folder '{folder}/' reset")


def run_mfa_align():
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    mfa_data_path = project_root / "syncdata" / "mfa"
    mfa_data_absolute = mfa_data_path.resolve()
    print(f"Docker MFA 경로: {mfa_data_absolute}")
    # 디버깅: corpus, mfa_output 폴더 파일 리스트 출력
    print("[DEBUG] corpus 폴더 파일:", list((mfa_data_path / "corpus").glob("*")))
    print("[DEBUG] mfa_output 폴더 파일 (실행 전):", list((mfa_data_path / "mfa_output").glob("*")))
    host_mount = str(mfa_data_absolute).replace('C:', '/c').replace('\\', '/')
    command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "-v", f"{host_mount}:/data",
        "mmcauliffe/montreal-forced-aligner:latest",
        "mfa", "align",
        "/data/corpus", "/data/english_us_arpa.dict", "/data/english_us_arpa", "/data/mfa_output",
        "--clean", "--beam", "100", "--retry_beam", "400",
        "--phone_boundary_method", "strict", "--output_format", "long_textgrid"
    ]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if process.stdout is not None:
            for raw_line in process.stdout:
                try:
                    line = raw_line.decode('utf-8')
                except UnicodeDecodeError:
                    line = raw_line.decode('utf-8', errors='ignore')
                print(line, end='')
        process.wait()
        # 디버깅: mfa_output 폴더 파일 리스트 출력 (실행 후)
        print("[DEBUG] mfa_output 폴더 파일 (실행 후):", list((mfa_data_path / "mfa_output").glob("*")))
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
    except subprocess.CalledProcessError as e:
        print("❌ MFA 실행 중 오류 발생!")
        print("명령:", e.cmd)
        raise


def generate_presigned_url(bucket: str, key: str, expiration: int = 3600):
    s3 = boto3.client('s3', region_name='ap-northeast-2')
    try:
        response = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration,
        )
        return response
    except ClientError as e:
        print("❌ Presigned URL 생성 실패:", e)
        return None
