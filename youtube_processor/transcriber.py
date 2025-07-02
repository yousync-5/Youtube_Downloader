import whisper_timestamped as wts
import json

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


def transcribe_audio(vocals_path):
    print("🎙️자막추출 기본 모델 호출 ")
    model = wts.load_model("base")

    print("🧠 음성 데이터 텍스트 변환중...")
    result = model.transcribe(
        vocals_path,
        word_timestamps=True,
        temperature=0.0,                             # 무작위성 제거
        best_of=3,                                   # 후보 중 1개만 고려
        beam_size=3,                                 # Beam search 비활성화 (greedy decoding)
        compression_ratio_threshold=float('inf'),    # 길이 제한 없음 (짤리는 것 방지)
        logprob_threshold= -5,             # 확률 기준 비활성화
        no_speech_threshold=0.5                       # 무음 제거 기준 비활성화
    )

    segments = result.get("segments", [])
    print(f"📝 총 {len(segments)} 개의 문장 추출.")

    # 각 segment 내 단어 타임스탬프 검사 및 보정
    for seg in segments:
        words = seg.get('words', [])
        fixed_words = validate_and_fix_timestamps(words)
        seg['words'] = fixed_words

    return segments

def transcribe_audio_check(vocals_path):
    print("🎙️자막추출 기본 모델 호출 ")
    model = wts.load_model("base")

    print("🧠 음성 데이터 텍스트 변환중...")
    result = model.transcribe(vocals_path, word_timestamps=True)

    segments = result.get("segments", [])
    print(f"📝 총 {len(segments)} 개의 문장 추출.")
    return segments