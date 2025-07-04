import os
import subprocess

def ffmpeg_merge(video_path, audio_path, start, end, output_path):
    command = [
        "ffmpeg",
        "-y",  # overwrite
        "-ss", str(start),
        "-to", str(end),
        "-i", video_path,
        "-ss", str(start),
        "-to", str(end),
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 🚀 실행 예시
segments = [
     {
    "start": 146.5,
    "end": 153.7,
    "text": "Manners maketh man."
  },
  {
    "start": 162.00,
    "end": 163.2,
    "text": "Do you know what that means?"
  }
]

os.makedirs("split_sentence_ffmpeg", exist_ok=True)

for i, seg in enumerate(segments):
    output_file = f"split_sentence_ffmpeg/taken_{i+1:03d}.mp4"
    ffmpeg_merge(
        video_path="downloaded/HDJEyqNw-9k.mp4",
        audio_path="downloaded/HDJEyqNw-9k.mp3",
        start=seg["start"],
        end=seg["end"],
        output_path=output_file
    )
    print(f"🎬 {output_file} 저장 완료")
