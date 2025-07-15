from pydub import AudioSegment  # 이걸 추가해야 함
from pathlib import Path

def split_audio_by_token(mp3_paths, speaker_data, video_filename, output_dir="split_tokens"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for mp3_path in mp3_paths:
        audio = AudioSegment.from_file(mp3_path)
        audio_type = Path(mp3_path).stem  # 파일명만 뽑아서 구분용

        token_id = speaker_data["token_id"]
        segments = speaker_data.get("segments", [])

        # 여러 구간을 이어붙이기
        merged = AudioSegment.empty()
        for seg in segments:
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            merged += audio[start_ms:end_ms]

        filename = f"{audio_type}_{video_filename}_token_{token_id}.mp3"
        merged.export(output_path / filename, format="mp3")
        print(f"🎧 Saved: {filename} (구간 수: {len(segments)})")