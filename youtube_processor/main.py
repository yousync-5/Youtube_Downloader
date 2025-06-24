# main.py
from downloader import download_audio, download_video
from transcriber import transcribe_audio
from frame_extractor import extract_frames_per_segment
from demucs_wrapper import separate_vocals           # ✅ 추가
from who_is_speaker import analyze_speakers          # 얼굴 기반
from voice_analyzer import analyze_voice_speakers    # ✅ 음성 기반

def main():
    youtube_url = input("📺 Enter YouTube video URL: ").strip()

    # 1. 오디오/영상 다운로드
    audio_path, video_path = download_audio(youtube_url)

    # 2. Demucs로 음성 분리
    vocal_path = separate_vocals(audio_path)

    # 3. Whisper로 자막 추출 (분리된 보컬 기반)
    segments = transcribe_audio(vocal_path)
    if not segments:
        print("❌ No speech detected.")
        return

    # 4. 앞 5문장 추출
    selected = segments[:]  # 원하는 만큼 자르기 가능
    print("\n🗣️ First 5 segments:")
    for seg in selected:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")

    # 5. 프레임 추출 (얼굴 기반 분석용)
    download_video(youtube_url, video_path)
    extract_frames_per_segment(video_path, selected)

    # 6. 얼굴 기반 화자 분석
    print("\n🔍 얼굴 기반 화자 분석:")
    analyze_speakers(num_segments=len(selected), folder="tmp_frames")

    # 7. 음성 기반 화자 분석
    print("\n🧠 음성 기반 화자 분석:")
    analyze_voice_speakers(vocal_path, selected)

if __name__ == "__main__":
    main()
