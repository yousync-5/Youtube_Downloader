from pyannote.audio import Pipeline
from pathlib import Path
import subprocess
import sys

# Hugging Face 토큰 입력 (절대 공유하지 마세요!)
TOKEN = "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"  # 발급받은 토큰


# 분석할 mp3 파일 경로
mp3_file = Path(r"C:\youtude-downloader\downloads\나탈리_포트만의_현실_사랑_명대사_(클로저)_S6KnqDc-tis.mp3")

# 파일 존재 확인
if not mp3_file.exists():
    print(f"❌ 파일이 존재하지 않습니다: {mp3_file.resolve()}")
    sys.exit(1)

# mp3 → wav 변환 함수
def convert_mp3_to_wav(mp3_path, wav_path):
    subprocess.run(['ffmpeg', '-y', '-i', str(mp3_path), str(wav_path)], check=True)

# wav 파일 경로 생성
wav_file = mp3_file.with_suffix(".wav")

# mp3를 wav로 변환
print(f"🔄 Converting {mp3_file} → {wav_file} ...")
convert_mp3_to_wav(mp3_file, wav_file)
print("✅ Conversion done.")

# 모델 로드
print("🧠 Loading speaker diarization pipeline...")
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=TOKEN)

# 화자 분리 수행
print(f"🎙️ Running speaker diarization on {wav_file} ...")
diarization = pipeline(wav_file)

# 3초 이상 발화 구간만 필터링 출력
print("\n🗣️ Speaker segments (3초 이상 발화만):")
for turn, _, speaker in diarization.itertracks(yield_label=True):
    duration = turn.end - turn.start
    if duration >= 5.0:
        print(f"[{turn.start:.1f}s - {turn.end:.1f}s] Speaker {speaker}")
