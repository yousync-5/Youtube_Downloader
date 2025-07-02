
def format_segments_for_output(segments):
    cleaned = []
    for seg in segments:
        cleaned_seg = {
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "words": [
                {
                    "word": w["word"].strip(),
                    "start": w["start"],
                    "end": w["end"]
                }
                for w in seg.get("words", [])
            ]
        }
        cleaned.append(cleaned_seg)
    return cleaned
