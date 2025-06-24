import whisper_timestamped as wts
from demucs_wrapper import separate_vocals  # ✅ 추가

def transcribe_audio(audio_path):
    # ✅ 1. 배경 제거 → vocals.wav 반환
    vocals_path = separate_vocals(audio_path)

    print("🎙️ Loading WhisperTimestamped model (base)...")
    model = wts.load_model("base")

    print("🧠 Transcribing audio...")
    result = model.transcribe(vocals_path, word_timestamps=True)

    segments = result.get("segments", [])
    print(f"📝 Transcription done. Found {len(segments)} segments.")
    return segments