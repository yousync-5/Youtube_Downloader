import subprocess
import time
import os
import sys
from pathlib import Path

def separate_vocals(audio_path: str, output_root="separated") -> str:
    
    #해당 디렉토리가 존재하지 않으면 설치하겠다.
    output_dir = Path(output_root)
    output_dir.mkdir(exist_ok=True)

    print(f"🎧 Demucs로 보컬 분리 중...")

    start_time = time.time()  # ⏱️ 시작 시간

    cmd = [
        "demucs",
        "-o", str(output_root),
        "--two-stems", "vocals",
        "--device", "cpu",
        audio_path
    ]
    
    print(f"🚀 demucs 실행: demucs -o {output_root} --two-stems vocals --device cpu {Path(audio_path).name}")
    subprocess.run(cmd, check=True, text=True)

    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 보컬 분리 소요 시간: {elapsed:.2f}초")

    # 경로에서 파일 이름만을 추출
    basename = Path(audio_path).stem  # 확장자만 제거, 소수점 포함 이름도 유지
    # separated/                 ← output_root
    #└── htdemucs/              ← 모델 이름
    #   └── test_audio/        ← 오디오 파일 이름 (확장자 제거)
    #      ├── vocals.wav     ← 🎤 추출된 보컬
    #     └── no_vocals.wav  ← 🎵 배경음
    vocals_path = output_dir / "htdemucs" / basename / "vocals.wav"
    
    # 실제로 생성되었는지 검증
    import glob
    print(f"[DEBUG] vocals_path to check: {vocals_path}")
    print(f"[DEBUG] vocals_path absolute: {vocals_path.resolve() if hasattr(vocals_path, 'resolve') else vocals_path}")
    print(f"[DEBUG] Directory contents: {list(vocals_path.parent.glob('*'))}")
    if not vocals_path.exists():
        raise FileNotFoundError(f"❌ vocals.wav not found at {vocals_path}")

    print(f"✅ 보컬 추출 완료 → {vocals_path}")
    return str(vocals_path)
