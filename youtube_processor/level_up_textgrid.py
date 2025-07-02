from praatio import textgrid
import re
import math

def normalize(text):
    return re.sub(r"[^\w']", "", text.lower())

def generate_sentence_json(whisper_segments, textgrid_path):
    tg = textgrid.openTextgrid(textgrid_path, includeEmptyIntervals=True)
    words_tier = tg.getTier("words")
    word_entries = words_tier.entries

    results = []

    for segment in whisper_segments:
        seg_start = segment["start"]
        seg_end = segment["end"]
        raw_text = segment["text"].strip()

        # TextGrid 상에서 해당 Whisper 문장과 겹치는 단어가 하나라도 있는지 확인
        matched = any(
            start < seg_end and end > seg_start
            for (start, end, label) in word_entries
            if normalize(label)  # 비어 있지 않은 항목만
        )

        if matched:
            results.append({
                "start": round(seg_start, 2),
                "end": round(seg_end, 2),
                "text": raw_text
            })
        else:
            print(f"⚠️ 문장 매칭 실패 (제외됨): \"{raw_text}\"")

    return redistribute_gaps(results)

def redistribute_gaps(segments):
    adjusted = []

    for i, seg in enumerate(segments):
        start = float(seg["start"])
        end = float(seg["end"])

        # 첫 문장은 start를 반내림
        if i == 0:
            start = math.floor(start)
        else:
            prev_end = float(adjusted[-1]["end"])
            gap = start - prev_end
            adjustment = gap / 2
            adjusted[-1]["end"] = round(prev_end + adjustment, 2)
            start = round(start - adjustment, 2)

        if i == len(segments) - 1:
            end = math.ceil(end)

        adjusted.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": seg["text"]
        })

    return adjusted
