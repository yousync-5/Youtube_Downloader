from praatio import textgrid
import re
import math
from typing import List, Dict

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


def generate_sentence_with_words(
    whisper_segments: List[Dict],
    textgrid_path: str
) -> List[Dict]:
    """
    TextGrid 기반 word 리스트를 추가해서 sentence JSON을 반환.
    기존 generate_sentence_json과는 별개로 사용합니다.
    """
    # 1) 먼저 기존 로직으로 문장 타이밍만 뽑기
    base_segments = generate_sentence_json(whisper_segments, textgrid_path)

    # 2) TextGrid에서 word tier 읽기
    from praatio import textgrid
    tg = textgrid.openTextgrid(textgrid_path, includeEmptyIntervals=True)
    words_tier = tg.getTier("words").entries  # List[(start, end, label)]

    # 3) 각 문장에 대해 word 매핑
    for sent in base_segments:
        sent_start, sent_end = sent["start"], sent["end"]
        sent_words = []
        for w_start, w_end, label in words_tier:
            if w_start >= sent_start and w_end <= sent_end and label.strip():
                sent_words.append({
                    "start": round(w_start, 2),
                    "end":   round(w_end,   2),
                    "word":  label.strip()
                })
        sent["words"] = sent_words

    # 4) 시간 조정(필요시)
    return redistribute_gaps(base_segments)