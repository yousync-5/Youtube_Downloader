import os
from yt_dlp import YoutubeDL
from config import FFMPEG_PATH, DOWNLOAD_DIR
from utils import sanitize_filename

def download_audio(url):
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    with YoutubeDL({
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'ffmpeg_location': FFMPEG_PATH
    }) as ydl:
        info = ydl.extract_info(url, download=False)
        video_id = info.get("id", "")
        filename = sanitize_filename(video_id)  # ← 여기서 title 제거!
        output_path = DOWNLOAD_DIR / filename

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH
    }

    print(f"🔻 Downloading audio: {video_id}")
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return str(output_path) + ".mp3", str(output_path) + ".mp4"

def download_video(url, output_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH
    }
    print("🎥 Downloading full video...")
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
