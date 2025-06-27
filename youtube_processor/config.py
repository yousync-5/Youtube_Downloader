from pathlib import Path

FFMPEG_PATH = r"C:\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe"
FPS = 2.0  # 초당 추출할 프레임 수
DOWNLOAD_DIR = Path('downloads')
USER_UPLOADS_DIR = Path('user_uploads')  # 유저 음성 업로드 디렉토리
PITCH_DATA_DIR = Path('pitch_data')  # 피치 데이터 저장 디렉토리
PITCH_REFERENCE_DIR = PITCH_DATA_DIR / 'reference'  # 기준 음성 피치
PITCH_USER_DIR = PITCH_DATA_DIR / 'user'  # 유저 음성 피치