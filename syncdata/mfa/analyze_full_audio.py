import os
import subprocess
import json
import librosa
import numpy as np
import textgrid
from pathlib import Path
from datetime import datetime

# 🧩 설정
BASE_DIR = Path(r"C:\Users\c4851\syncdata\mfa")
CORPUS_DIR = BASE_DIR / "corpus"
DICT_PATH = BASE_DIR / "english_us_arpa.dict"
MODEL_PATH = BASE_DIR / "english_us_arpa"
OUTPUT_DIR = BASE_DIR / "mfa_output"
RESULT_JSON = BASE_DIR / "results" / "speaker1_profile.json"
AUDIO_FILE = CORPUS_DIR / "full.wav"
TEXTGRID_FILE = OUTPUT_DIR / "full.TextGrid"

def run_mfa():
    """MFA 실행"""
    cmd = [
        "mfa", "align",
        str(CORPUS_DIR),
        str(DICT_PATH),
        str(MODEL_PATH),
        str(OUTPUT_DIR),
        "--clean"
    ]
    print("📢 MFA 실행 중...")
    subprocess.run(cmd, check=True)
    print("✅ MFA 완료")

def parse_textgrid(textgrid_path):
    """TextGrid 파싱"""
    tg = textgrid.TextGrid.fromFile(textgrid_path)
    for tier in tg.tiers:
        if "phone" in tier.name.lower() or len(tg.tiers) == 1:
            return [{
                "phone": i.mark,
                "start": i.minTime,
                "end": i.maxTime,
                "duration": i.maxTime - i.minTime
            } for i in tier if i.mark.strip()]
    return []

def extract_features(audio_path, phone):
    """음소 특징 추출"""
    y, sr = librosa.load(audio_path, sr=None)
    s, e = int(phone["start"] * sr), int(phone["end"] * sr)
    segment = y[s:e]

    if len(segment) < 256:
        return None

    mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13)
    f0 = librosa.yin(segment, fmin=50, fmax=400)
    centroid = librosa.feature.spectral_centroid(y=segment, sr=sr)

    return {
        "phone": phone["phone"],
        "start": phone["start"],
        "end": phone["end"],
        "duration": phone["duration"],
        "mfcc_mean": np.mean(mfcc, axis=1).tolist(),
        "f0_mean": float(np.mean(f0[f0 > 0])) if np.any(f0 > 0) else 0,
        "spectral_centroid": float(np.mean(centroid))
    }

def analyze():
    # 1. MFA 실행
    run_mfa()

    # 2. TextGrid → 음소 추출
    phones = parse_textgrid(TEXTGRID_FILE)
    print(f"🔍 {len(phones)}개 음소 추출됨")

    # 3. 음소별 특징 추출
    features = []
    for i, p in enumerate(phones):
        f = extract_features(AUDIO_FILE, p)
        if f:
            features.append(f)
        else:
            print(f"⚠️ {p['phone']} 무시됨 (짧거나 오류)")

    # 4. JSON 저장
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "audio_file": str(AUDIO_FILE),
            "analyzed_at": datetime.now().isoformat(),
            "phones": features
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ 결과 저장됨: {RESULT_JSON}")

if __name__ == "__main__":
    analyze()
