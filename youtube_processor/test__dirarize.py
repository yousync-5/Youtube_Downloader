# test_diarize.py
import json
from collections import defaultdict
import torch
from pyannote.audio import Pipeline
import os
from dotenv import load_dotenv

from pyannote.audio import Inference
from visualize import visualize_diarization


load_dotenv()  # .env 파일의 HF_TOKEN 등을 로드

# 하드코딩한 파일 경로 설정
VOCAL_PATH = "separated/htdemucs/4KYfTRe1pC4/vocals.wav"
SEGMENTS_JSON = "cached_data/post_word_data.json"


def test_diarization(vocal_path: str, segments_json: str):
    # 1) post_word_data 불러오기
    with open(segments_json, 'r', encoding='utf-8') as f:
        post_word_data = json.load(f)

    # 2) pyannote 파이프라인 로드
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"▶️ Loading diarization model on {device}")
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=True
    )

    my_embedder = Inference(
        "pyannote/embedding",
        device=device,
        use_auth_token=True,
        duration=0.02,   #한번 임베딩을 추출할 오디오 길이(초) - 작을 수록(짧은 구간 단위 디테일)
        # 다음 윈도우로 얼마나 이동할지 - 작을 수록(겹침 경계 감지 정밀) 
        step=0.02
    )
    # 3. 파이프라인에 덮어쓰기

    pipeline.embedding = my_embedder

    # 분절(segmentation) 윈도우 크기 & 이동(step)
    # pipeline.segmentation.chunk_duration = 0.05   # 긴 윈도우로 작은 잡음 무시
    # pipeline.segmentation.step = 0.05  #윈도우를 얼마나 자주 움직일지 (기본 0.1 s).
    
    # 음성 탐지(VAD) 민감도
    # 발화 시작 감지 임계치 - 작을 수록(낮은 음량도 발화로 간주), 클 수록(큰 목소리만 발화로 인식)
    pipeline.segmentation.onset  = 0.25
    # 발화 종료 감지 임계치 - 작을 수록(짧은 무음 구간만으로도 끊김 처리), 클수록(더 긴 무음 구간이 있어야 발화 종료로 간주)
    pipeline.segmentation.offset = 0.7

    # 최소 발화/ 침묵 길이
    # 최소 발화 길이 - 작을 수록(짧은 단어, 음절도 발화 할당), 클 수록(빈말, 짧은 삑사리 제거)
    pipeline.min_duration_on  = 0.2
    # 최소 침묵 길이 - 작을 수록(짧은 무음에도 발화가 끊긴 것으로 처리), 클 수록(무음 구간이 길어야 발화 중단)
    pipeline.min_duration_off = 0.4

    # 클러스터링 방식 & 파라미터
    # 화자 임베딩 간 거리(혹은 유사도 기준)
    pipeline.clustering.threshold = 0.8

    # 최소 클러스터 샘플 수 - 작을 수록(짧은 발화도 클러스터로 인정), 클 수록(충분히 자주 등장한 발화만 인정)
    # pipeline.clustering.min_samples = 7


    pipeline.to(device)
    print("✅ Model loaded.")


    # 3) 화자 분리 실행
    diarization = pipeline({"audio": vocal_path}, min_speakers=2, max_speakers=2)
    print("✅ Diarization complete.")

    # 시각화
    visualize_diarization(vocal_path, diarization)



    # 4) 세그먼트별 화자 할당
    speaker_segments = defaultdict(list)
    for seg in post_word_data:
        best_speaker, best_overlap = "unknown", 0.0
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            overlap = max(0.0,
                          min(turn.end, seg["end"]) -
                          max(turn.start, seg["start"]))
            if overlap > best_overlap:
                best_overlap, best_speaker = overlap, speaker
        seg["speaker_label"] = best_speaker
        speaker_segments[best_speaker].append(seg)
    
   
    print(f"Detected speakers: {list(speaker_segments.keys())}")

    # 5) 주요 화자 추출
    valid = {sp: segs for sp, segs in speaker_segments.items() if sp != "unknown"}
    if not valid:
        print("❌ No valid speaker found.")
        return

    main_sp, segs = max(valid.items(), key=lambda item: sum(s["end"]-s["start"] for s in item[1]))
    print(f"👑 Main speaker: {main_sp}")

    # 6) 세그먼트 정렬 및 출력
    segs = sorted(segs, key=lambda x: x["start"])
    print("📝 Main speaker segments:")
    for i, s in enumerate(segs, 1):
        print(f"  [{i}] {s['start']:.2f}-{s['end']:.2f} | {s['text']}")

if __name__ == "__main__":
    # 하드코딩된 파일 경로를 사용하여 테스트
    test_diarization(VOCAL_PATH, SEGMENTS_JSON)
