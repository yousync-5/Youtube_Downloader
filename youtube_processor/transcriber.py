import whisper_timestamped as wts

def transcribe_audio(vocals_path):
    print("🎙️자막추출 기본 모델 호출 ")
    model = wts.load_model("base")

    print("🧠 음성 데이터 텍스트 변환중...")
    result = model.transcribe(vocals_path, word_timestamps=True)

    segments = result.get("segments", [])
    print(f"📝 총 {len(segments)} 개의 문장 추출.")
    return segments