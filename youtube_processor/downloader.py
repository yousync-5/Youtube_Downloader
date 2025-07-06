import os
from yt_dlp import YoutubeDL
from config import FFMPEG_PATH, DOWNLOAD_DIR
from utils import sanitize_filename

def download_audio(url, video_id, video_filename):
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    
   # 💡 전달받은 video_filename을 그대로 사용
    output_path = DOWNLOAD_DIR / video_filename

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
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'postprocessors': [{               # ✅ 이거 추가
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],    # ← 이 옵션을 추가하세요!
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH
    }
    print("🎥 Downloading full video...")
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
