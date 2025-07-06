from pydub import AudioSegment  # 이걸 추가해야 함
from pathlib import Path

  #당장을 불필요. 테스트용 함수
def split_audio_by_token(mp3_paths, speaker_data,  video_filename ,output_dir="split_tokens"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for mp3_path in mp3_paths:
        audio = AudioSegment.from_file(mp3_path)
        audio_type = Path(mp3_path).stem  # 파일명만 뽑아서 구분용

        token_id = speaker_data["token_id"]
        start_time = speaker_data["start_time"]
        end_time = speaker_data["end_time"]

        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)

        clip = audio[start_ms:end_ms]
        filename = f"{audio_type}_{video_filename}_token_{token_id}.mp3"
        clip.export(output_path / filename, format="mp3")
        print(f"🎧 Saved: {filename} ({start_time}s ~ {end_time}s)")