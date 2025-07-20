# voice_analyzer.py
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import os
from tempfile import NamedTemporaryFile
from pydub import AudioSegment
from sklearn.cluster import KMeans

# 세그먼트 별로 음성 잘라내기 (wav 단위)
# def extract_segment_audio(full_audio_path, start, end):
#     audio = AudioSegment.from_wav(full_audio_path)
def extract_segment_audio(full_audio_path, start, end):
    # MP3든 WAV든 포맷 자동 감지
    audio = AudioSegment.from_file(full_audio_path)
    segment_audio = audio[start * 1000:end * 1000]  # pydub: milliseconds 단위

    tmp = NamedTemporaryFile(delete=False, suffix=".wav")
    segment_audio.export(tmp.name, format="wav")
    return tmp.name

def analyze_voice_speakers(vocal_audio_path: str, segments: list[dict], threshold: float = 0.75):
    encoder = VoiceEncoder()

    print("\n🔊 Resemblyzer 로딩 완료, 음성 화자 분석 시작...")
    segment_embeddings = []

    for i, seg in enumerate(segments):
        try:
            seg_wav_path = extract_segment_audio(vocal_audio_path, seg.get('start', 0), seg.get('end', 0))
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

def analyze_voice_speakers_with_clustering(vocal_audio_path: str, segments: list[dict], n_speakers: int = 2):
    """
    세그먼트별 음성 임베딩을 추출하고, KMeans로 클러스터링하여 화자 라벨을 반환합니다.
    """
    encoder = VoiceEncoder()
    print("\n🔊 Resemblyzer 로딩 완료, 음성 화자 클러스터링 시작...")
    segment_embeddings = []

    for i, seg in enumerate(segments):
        try:
            seg_wav_path = extract_segment_audio(vocal_audio_path, seg.get('start', 0), seg.get('end', 0))
            wav = preprocess_wav(seg_wav_path)
            embed = encoder.embed_utterance(wav)
            segment_embeddings.append(embed)
            os.remove(seg_wav_path)
        except Exception as e:
            print(f"⚠️ 세그먼트 {i}: 음성 추출 실패 → {e}")
            segment_embeddings.append(None)

    # None 값 제거 및 인덱스 매핑
    valid_indices = [i for i, emb in enumerate(segment_embeddings) if emb is not None]
    valid_embeddings = [emb for emb in segment_embeddings if emb is not None]

    if not valid_embeddings:
        print("❌ 유효한 임베딩이 없습니다.")
        return ["UNKNOWN"] * len(segments), None

    # KMeans 클러스터링
    kmeans = KMeans(n_clusters=n_speakers, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(valid_embeddings)

    # 전체 세그먼트에 라벨 할당
    speaker_labels = ["UNKNOWN"] * len(segments)
    for idx, label in zip(valid_indices, labels):
        speaker_labels[idx] = f"SPEAKER_{label}"

    # 각 화자별 세그먼트 인덱스
    speakers = {}
    for idx, label in zip(valid_indices, labels):
        speakers.setdefault(label, []).append(idx)

    print(f"\n🎤 음성 기반 총 {n_speakers}명 화자 클러스터링 결과:")
    for label, idxs in speakers.items():
        print(f"   SPEAKER_{label}: {len(idxs)}개 세그먼트")

    return speaker_labels, speakers

__all__ = ["analyze_voice_speakers"]
