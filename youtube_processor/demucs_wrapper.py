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

    # Python 실행 환경에서 demucs 경로 동적으로 찾기
    import sys
    python_bin_dir = Path(sys.executable).parent
    possible_demucs_paths = [
        python_bin_dir / "demucs",  # 같은 Python 환경
        Path.home() / "Library/Python/3.9/bin/demucs",  # 사용자 Python 패키지
        Path("/usr/local/bin/demucs"),  # 시스템 설치
        Path("/opt/homebrew/bin/demucs"),  # Homebrew 설치
    ]
    
    demucs_path = None
    for path in possible_demucs_paths:
        if path.exists():
            demucs_path = str(path)
            print(f"✅ demucs 발견: {demucs_path}")
            break
    
    if not demucs_path:
        raise FileNotFoundError("demucs 명령어를 찾을 수 없습니다. 다음 경로들을 확인했습니다:\n" + 
                              "\n".join(f"  - {p}" for p in possible_demucs_paths))
    
    cmd = [
        demucs_path,
        "-o", str(output_root),
        "--two-stems", "vocals",
        audio_path
    ]
    
    print(f"🚀 demucs 실행: demucs -o {output_root} --two-stems vocals {Path(audio_path).name}")
    subprocess.run(cmd, check=True, text=True)

    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 보컬 분리 소요 시간: {elapsed:.2f}초")

    # 경로에서 파일 이름만을 추출
    basename = Path(audio_path).name.split('.')[0]  # ✅ 점(.) 제거

    # separated/                 ← output_root
    #└── htdemucs/              ← 모델 이름
    #   └── test_audio/        ← 오디오 파일 이름 (확장자 제거)
    #      ├── vocals.wav     ← 🎤 추출된 보컬
    #     └── no_vocals.wav  ← 🎵 배경음
    vocals_path = output_dir / "htdemucs" / basename / "vocals.wav"

    # 실제로 생성되었는지 검증
    if not vocals_path.exists():
        raise FileNotFoundError(f"❌ vocals.wav not found at {vocals_path}")

    print(f"✅ 보컬 추출 완료 → {vocals_path}")
    return str(vocals_path)
