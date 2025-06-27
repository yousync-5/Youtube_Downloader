from pydub import AudioSegment  # 이걸 추가해야 함
from pathlib import Path
  #당장을 불필요. 테스트용 함수
  
def split_mp3_by_segments(mp3_path, segments, output_dir="split_segments"):
        audio = AudioSegment.from_file(mp3_path)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, seg in enumerate(segments):
            start_ms = int(seg['start'] * 1000)
            end_ms = int(seg['end'] * 1000)
            text = seg['text']

            clip = audio[start_ms:end_ms]
            clip.export(output_path / f"seg_{i+1:02d}.mp3", format="mp3")

            # 텍스트 파일로도 저장
            with open(output_path / f"seg_{i+1:02d}.txt", "w", encoding="utf-8") as f:
                f.write(text)

            print(f"✅ Saved: seg_{i+1:02d}.mp3  ({seg['start']}s ~ {seg['end']}s)")
