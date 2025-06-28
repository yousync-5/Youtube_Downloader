from praatio import textgrid
import re
import math

def normalize(text):
    return re.sub(r"[^\w']", "", text.lower())

def generate_sentence_json(whisper_segments, textgrid_path):
    tg = textgrid.openTextgrid(textgrid_path, includeEmptyIntervals=True)
    words_tier = tg.getTier("words")
    word_entries = words_tier.entries
    word_labels = []    
    for entry in word_entries:
        word = entry[2]
        cleaned = normalize(word)
        word_labels.append(cleaned)

    results = []
    for segment in whisper_segments:
        raw_text = segment["text"]
        whisper_words = [normalize(w) for w in raw_text.split()]
        match_len = len(whisper_words)
        found = False

        # 슬라이딩 윈도우로 정확한 단어 시퀀스 탐색
        for i in range(0, len(word_labels) - match_len + 1):
            if word_labels[i:i+match_len] == whisper_words:
                matched_entries = word_entries[i:i+match_len]
                start = matched_entries[0][0]
                end = matched_entries[-1][1]
                text = " ".join(label for (_, _, label) in matched_entries)
                results.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text
                })
                found = True
                break
        
        if not found:
            print(f"⚠️ 정확 매칭 실패 → '{raw_text}' → 원본 유지")
            results.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": raw_text.strip()
            })

    result = redistribute_gaps(results)

    return result

def redistribute_gaps(segments):
    adjusted = []

    for i, seg in enumerate(segments):
        start = float(seg["start"])
        end = float(seg["end"])

        # 첫 문장은 start를 반내림
        if i == 0:
            start = math.floor(start)
        else:
            # 앞 문장과의 간격을 반으로 나누어 분배
            prev_end = float(adjusted[-1]["end"])
            gap = start - prev_end
            adjustment = gap / 2

            # 앞 문장의 end 보정
            adjusted[-1]["end"] = round(prev_end + adjustment, 2)
            # 현재 문장의 start 보정
            start = round(start - adjustment, 2)

        # 마지막 문장은 end를 반올림
        if i == len(segments) - 1:
            end = math.ceil(end)

        adjusted.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": seg["text"]
        })

    return adjusted