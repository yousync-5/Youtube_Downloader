# extract_frames.py
# 이 스크립트는 동영상 파일로부터:
# 일정 간격으로 프레임 이미지(JPG)를 추출하고
# 오디오를 16kHz 1채널 WAV 형식으로 추출하는 작업을 수행한다.
# subprocess: 외부 명령어(여기선 ffmapeg)를 실행하기 위해 사용.
# pathlib : 파일 경로 조작을 편리하게 해주는 모듈
# shutil : 디렉토리 삭제 등 고수준 파일 작업
# sys : 실행 시 입력된 인자(argv)를 처리하기 위해 사용
import subprocess, pathlib, shutil, sys

# ▶ 사용법 :  python extract_frames.py 입력 비디오 파일.mp4 2
# 2: 초당 추출할 프레임 수(fps)
# 첫 번째 인자: 비디오 파일 경로를 가져와 Path 객체로 변환
video = pathlib.Path(sys.argv[1])
# 두 번째 인자가 있으면 프레임 추출 속도(fps)로 사용
# 없으면 기본값 2.0 fps를 사용
fps   = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0         # 기본 2 fps
# tmp_frames라는 임시 디렉토리를 만들 준비
# 기존에 있다면 삭제하고 새로 생성(오래된 파일 방지)
tmp = pathlib.Path("tmp_frames")
if tmp.exists():
    shutil.rmtree(tmp)
tmp.mkdir()

# 어떤 영상 파일을 몇 fps로 처리할지 콘솔에 출력
print(f"▶ 영상: {video.name}  |  프레임추출: {fps} fps")

# 1. JPG 프레임
# ffmpeg 명령어 문자열 생성
# -i {video}: 입력 파일
# -r {fps}: 초당 프레임 수(속도)
# "{tmp}/%06d.jpg": 이름을 000001.jpg, 000002.jpg 형식으로 저장
# -y: 덮어쓰기 허용
# -loglevel quiet: 로그 생량
cmd_frames = f"ffmpeg -y -loglevel quiet -i \"{video}\" -r {fps} \"{tmp}/%06d.jpg\""
# 위의 ffmpeg 명령어 실행
subprocess.run(cmd_frames, shell=True, check=True)

# 2. WAV 오디오 (16 kHz · 1채널)
# 비디오에서 오디오만 추출
# -ar 16000: 16 kHz 샘플링 레이트
# -ac 1: 모노(1채널) 오디오
# 결과는 audio.wav
cmd_audio  = f"ffmpeg -y -loglevel quiet -i \"{video}\" -ar 16000 -ac 1 \"{tmp}/audio.wav\""
# 오디오 추출 명령 실행
subprocess.run(cmd_audio,  shell=True, check=True)

# tmp_frames 폴더 안의 .jpg 파일 개수(= 프레임 수)계산
n = len(list(tmp.glob('*.jpg')))
# 프레임 개수와 오디오 추출이 완료되었음을 알림
print(f"✅ 프레임 {n}장 · 오디오 추출 완료 →  {tmp}")

# 해상도 조정 옵션 추가 가능