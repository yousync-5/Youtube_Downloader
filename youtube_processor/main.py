import os
from downloader import download_audio, download_video
from transcriber import transcribe_audio
from frame_extractor import extract_frames_per_segment
from demucs_wrapper import separate_vocals
from who_is_speaker import analyze_speakers
from voice_analyzer import analyze_voice_speakers
from export_for_mfa import export_segments_for_mfa
from utils import sanitize_filename  # 이미 있다면 생략 가능

def main():
    youtube_url = input("📺 Enter YouTube video URL: ").strip()

    # ▶️ 유튜브 ID 추출
    video_id = youtube_url.split("v=")[-1].split("&")[0]
    video_filename = sanitize_filename(video_id)
    mp4_path = os.path.join("downloads", video_filename + ".mp4")
    mp3_path, _ = download_audio(youtube_url)

    # 🎞️ 영상이 없다면 별도로 다운로드
    if not os.path.exists(mp4_path):
        download_video(youtube_url, mp4_path)
    else:
        print(f"✅ 영상 파일 이미 존재: {mp4_path}")

    # 🎤 Demucs로 보컬 추출
    vocal_path = separate_vocals(mp3_path)

    # 🧠 Whisper로 자막 추출
    segments = transcribe_audio(vocal_path)
    if not segments:
        print("❌ No speech detected.")
        return

    selected = segments[:]
    print("\n🗣️ First 5 segments:")
    for seg in selected:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")

    # 🖼️ 프레임 추출
    extract_frames_per_segment(mp4_path, selected)

    # 😎 얼굴 기반 화자 분석
    print("\n🔍 얼굴 기반 화자 분석:")
    analyze_speakers(num_segments=len(selected), folder="tmp_frames")

    # 🎧 음성 기반 화자 분석
    print("\n🧠 음성 기반 화자 분석:")
    analyze_voice_speakers(vocal_path, selected)

    # 🔡 MFA용 세그먼트 내보내기
    print("\n📦 MFA용 음성/텍스트 export:")
    export_segments_for_mfa(vocal_path, segments, output_base=r"C:\Users\c4851\syncdata\mfa\corpus")

if __name__ == "__main__":
    main()
