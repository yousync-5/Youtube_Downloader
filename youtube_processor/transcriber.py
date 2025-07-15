import whisper_timestamped as wts
import json
import torch

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")                  # cuda:0 여야 합니다

def validate_and_fix_timestamps(words):
    fixed_words = []
    prev_end = 0.0

    for w in words:
        start = float(w.get('start', 0.0))
        end = float(w.get('end', 0.0))
        word = w.get('text') or w.get('word', '')

        if start >= end:
            print(f"⚠️ 무효 단어 타임스탬프 (start >= end): {word}")
            continue

        if start < prev_end:
            if end <= prev_end:
                print(f"⚠️ {word} 단어 시간 전체가 이전과 겹침 → 무시")
                continue
            else:
                # 겹치는 부분만 밀기
                print(f"⚠️ {word} 단어 start 보정: {start:.2f} → {prev_end:.2f}")
                start = prev_end

        fixed_words.append({
            'word': word,
            'start': start,
            'end': end
        })

        prev_end = max(prev_end, end)

    return fixed_words


def split_long_segment(seg,
                       max_len=8.0,
                       pause_thresh=0.3):
    """
    하나의 seg(문장 덩어리)가 너무 길면
    단어 간 무음(pause) 기준으로 잘게 나눠서 리스트로 반환.
    """
    if (seg["end"] - seg["start"]) < max_len or "words" not in seg:
        return [seg]

    results, cur = [], {"start": seg["start"], "words": []}
    prev_end = seg["start"]

    for w in seg["words"]:
        pause = w["start"] - prev_end
        if pause > pause_thresh and cur["words"]:
            # 새 조각 완료
            cur["end"]  = prev_end
            cur["text"] = " ".join(t["word"] for t in cur["words"])
            results.append(cur)
            # 다음 조각 시작
            cur = {"start": w["start"], "words": []}

        cur["words"].append(w)
        prev_end = w["end"]

    # 마지막 조각
    if cur["words"]:
        cur["end"]  = prev_end
        cur["text"] = " ".join(t["word"] for t in cur["words"])
        results.append(cur)

    return results


def transcribe_audio(vocals_path):
    print("🎙️자막추출 기본 모델 호출 ")
    model = wts.load_model("base").to(device)

    print("🧠 음성 데이터 텍스트 변환중...")
    # result = model.transcribe(
    #     vocals_path,
    #     word_timestamps=True,
    #     language="en",
    #     temperature=0.0,                             # 무작위성 제거
    #     best_of=3,                                   # 후보 중 1개만 고려
    #     beam_size=3,                                 # Beam search 비활성화 (greedy decoding)
    #     compression_ratio_threshold=float('inf'),    # 길이 제한 없음 (짤리는 것 방지)
    #     logprob_threshold= -5,                       # 확률 기준 비활성화
    #     no_speech_threshold=0.5                      # 무음 제거 기준 비활성화
    # )
    result = model.transcribe(
        vocals_path,
        word_timestamps=True,
        language="en",
        temperature=0.0,
        best_of=3,
        beam_size=3,
        compression_ratio_threshold=float('inf'),
        logprob_threshold=-5,
        no_speech_threshold=0.5
    )

    segments = result.get("segments", [])
    print(f"📝 총 {len(segments)} 개의 문장 추출.")

    # 각 segment 내 단어 타임스탬프 검사 및 보정
    for seg in segments:
        words = seg.get('words', [])
        fixed_words = validate_and_fix_timestamps(words)
        seg['words'] = fixed_words

        # ── 🔻 추가: 긴 세그먼트 재분할 ─────────────────────
    # refined = []
    # for seg in segments:
    #     refined.extend(
    #         split_long_segment(seg,
    #                            max_len=4.0,        # 8초 초과면 분할
    #                            pause_thresh=0.30)  # 0.3초 무음 기준
    #     )
    
    # print(f"📝 2차(분할 후) 세그먼트 {len(refined)}개")
    
    # # 🔸 여기서 id 부여 (1부터 순차)
    # for idx, seg in enumerate(refined, start=1):
    #     seg["id"] = idx

    # return refined
    
    return segments

def transcribe_audio_check(vocals_path):
    print("🎙️자막추출 기본 모델 호출 ")
    model = wts.load_model("base").to(device)

    print("🧠 음성 데이터 텍스트 변환중...")
    result = model.transcribe(
        vocals_path, 
        word_timestamps=True,
        language="en"
    )

    segments = result.get("segments", [])
    print(f"📝 총 {len(segments)} 개의 문장 추출.")
    return segments