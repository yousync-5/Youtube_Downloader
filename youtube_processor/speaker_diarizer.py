
# speaker_diarizer.py
from collections import defaultdict
from typing import List, Dict, Any
from pathlib import Path
import torch
from pydub import AudioSegment
from pyannote.audio import Pipeline
from pyannote.core import Annotation
from pyannote.audio import Inference


def diarize_main_speaker(
    vocal_path: str,
    post_word_data: List[Dict[str, Any]],   # ← 반드시 리스트!
    hf_token: str,
    *,                       # 키워드 전용
    min_speakers: int = 2,
    max_speakers: int = 2,
) -> Dict[str, Any]:
    """Whisper 세그먼트(post_word_data)에 화자 라벨을 달고
       대사량이 가장 긴 화자를 반환한다."""

    # ───────────────────────── 0. 입력 WAV 확보 ─────────────────────────
    src = Path(vocal_path)
    if src.suffix.lower() != ".wav":            # MP3 → WAV 16 kHz mono
        wav = src.with_suffix(".wav").with_name(f"{src.stem}_16k_mono.wav")
        if not wav.exists():
            print(f"🔄 {src.name} → {wav.name} (16 kHz mono)")
            AudioSegment.from_file(src).set_frame_rate(16_000)\
                                        .set_channels(1)\
                                        .export(wav, format="wav")
        vocal_path = str(wav)
    # ──────────────────────────────────────────────────────────────────

    print("🔊 diarization start")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
            # 필요하다면 revision="해시값" 고정
        )

        my_embedder = Inference(
            "pyannote/embedding",
            device=device,
            use_auth_token=True,
            duration=0.05,   #한번 임베딩을 추출할 오디오 길이(초) - 작을 수록(짧은 구간 단위 디테일)
            # 다음 윈도우로 얼마나 이동할지 - 작을 수록(겹침 경계 감지 정밀) 
            step=0.05        
        )
        # 3. 파이프라인에 덮어쓰기

        pipeline.embedding = my_embedder


        # *** test_diarize.py 에서 좋았던 튜닝값 ***
        pipeline.segmentation.onset  = 0.25
        pipeline.segmentation.offset = 0.70

        pipeline.min_duration_on  = 0.2
        pipeline.min_duration_off = 0.4
        
        pipeline.clustering.threshold = 0.8

        pipeline.to(device)

        diar = pipeline(
            {"audio": vocal_path},
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

    except Exception as e:
        print("❌ diarization error:", e)
        diar = Annotation()          # 실패 시 빈 결과

    # ─────────────────────── 1. Whisper 세그먼트에 라벨 부여 ───────────────────────
    speaker_segments: dict[str, list] = defaultdict(list)

    for seg in post_word_data:
        best_lbl, best_ov = "unknown", 0.0
        for turn, _, lbl in diar.itertracks(yield_label=True):
            ov = max(0.0, min(turn.end, seg["end"]) - max(turn.start, seg["start"]))
            if ov > best_ov:
                best_ov, best_lbl = ov, lbl
        seg["speaker_label"] = best_lbl
        speaker_segments[best_lbl].append(seg)
    # ──────────────────────────────────────────────────────────────────────────────

    # ─────────────────────── 2. 대사량 기준 주요 화자 선택 ────────────────────────
    main_lbl, main_dur = None, 0.0
    for lbl, segs in speaker_segments.items():
        if lbl == "unknown":
            continue
        dur = sum(s["end"] - s["start"] for s in segs)
        if dur > main_dur:
            main_lbl, main_dur = lbl, dur

    if main_lbl is None:
        raise RuntimeError("주요 화자 탐지 실패")

    main_segs = sorted(speaker_segments[main_lbl], key=lambda s: s["start"])
    # ──────────────────────────────────────────────────────────────────────────────

    return {
        "label":    main_lbl,
        "segments": main_segs,
        "start":    main_segs[0]["start"],
        "end":      main_segs[-1]["end"],
    }
