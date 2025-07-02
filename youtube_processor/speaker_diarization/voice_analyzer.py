# voice_analyzer.py
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import os
from tempfile import NamedTemporaryFile
from pydub import AudioSegment

# 세그먼트 별로 음성 잘라내기 (wav 단위)
def extract_segment_audio(full_audio_path, start, end):
    audio = AudioSegment.from_wav(full_audio_path)
    segment_audio = audio[start * 1000:end * 1000]  # pydub: milliseconds 단위

    tmp = NamedTemporaryFile(delete=False, suffix=".wav")
    segment_audio.export(tmp.name, format="wav")
    return tmp.name

def analyze_voice_speakers(vocal_audio_path, segments, threshold=0.75):
    encoder = VoiceEncoder()

    print("\n🔊 Resemblyzer 로딩 완료, 음성 화자 분석 시작...")
    segment_embeddings = []

    for i, seg in enumerate(segments):
        try:
            seg_wav_path = extract_segment_audio(vocal_audio_path, seg['start'], seg['end'])
            wav = preprocess_wav(seg_wav_path)
            embed = encoder.embed_utterance(wav)
            segment_embeddings.append(embed)
            os.remove(seg_wav_path)
        except Exception as e:
            print(f"⚠️ 세그먼트 {i}: 음성 추출 실패 → {e}")
            segment_embeddings.append(None)

    # 세그먼트 간 화자 비교
    for i in range(1, len(segment_embeddings)):
        prev = segment_embeddings[i - 1]
        curr = segment_embeddings[i]

        if prev is None or curr is None:
            print(f"👂 세그먼트 {i-1} ↔ {i} → ⚠️ 비교 불가 (데이터 없음)")
            continue

        similarity = np.dot(prev, curr) / (np.linalg.norm(prev) * np.linalg.norm(curr))
        same = similarity > threshold
        print(f"👂 세그먼트 {i-1} ↔ {i} → {'✅ 같은 화자' if same else '❌ 다른 화자'} (cosine similarity: {similarity:.3f})")

__all__ = ["analyze_voice_speakers"]
