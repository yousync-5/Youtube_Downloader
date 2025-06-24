import os
import subprocess
from pathlib import Path

def separate_vocals(audio_path: str, output_root="separated") -> str:
    output_dir = Path(output_root)
    output_dir.mkdir(exist_ok=True)

    print(f"🎧 Demucs로 보컬 분리 중...")

    cmd = [
        "demucs",
        "-o", str(output_root),
        "--two-stems", "vocals",
        audio_path
    ]
    subprocess.run(cmd, check=True)

    # 원본 이름 추출 (확장자 없이)
    #basename = Path(audio_path).stem
    basename = Path(audio_path).name.split('.')[0]  # ✅ 점(.) 제거
    vocals_path = output_dir / "htdemucs" / basename / "vocals.wav"

    if not vocals_path.exists():
        raise FileNotFoundError(f"❌ vocals.wav not found at {vocals_path}")

    print(f"✅ 보컬 추출 완료 → {vocals_path}")
    return str(vocals_path)
