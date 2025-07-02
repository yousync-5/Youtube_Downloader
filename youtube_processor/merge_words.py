def merge_words_into_segments(segments, word_list):
    """
    각 segment 안에 포함되는 word들을 찾아 words 필드로 삽입해준다.
    - 조건: word.start >= segment.start AND word.end <= segment.end
    - 문장의 시간 범위를 넘는 단어는 포함되지 않음

    Parameters:
    - segments: List[Dict], 각 문장 정보 {'start', 'end', 'text'}
    - word_list: List[Dict], 전체 단어 정보 {'start', 'end', 'word'}

    Returns:
    - List[Dict]: 각 문장에 words 필드가 추가된 리스트
    """
    result = []

    for segment in segments:
        seg_start = float(segment["start"])
        seg_end = float(segment["end"])

        matched_words = []

        for word in word_list:
            if word["start"] >= seg_start and word["end"] <= seg_end:
                # word["words"]가 리스트라면 하위 단어들을 분리해 추가
                if isinstance(word.get("words"), list):
                    for subword in word["words"]:
                        matched_words.append({
                            "start": round(subword["start"], 2),
                            "end": round(subword["end"], 2),
                            "word": subword["word"]
                        })
                else:
                    # 단일 단어인 경우
                    matched_words.append({
                        "start": round(word["start"], 2),
                        "end": round(word["end"], 2),
                        "word": word.get("word", "")
                    })

        new_seg = {
            "start": round(seg_start, 2),
            "end": round(seg_end, 2),
            "text": segment["text"]
        }

        if matched_words:
            new_seg["words"] = matched_words

        result.append(new_seg)

    return result
