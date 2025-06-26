import whisper_timestamped as whisper

def transcribe_audio(audio_path):
    model = whisper.load_model("base")  # tiny, base, small, medium, large
    result = whisper.transcribe(model, audio_path)
    
    for segment in result["segments"]:
        print(f"[{segment['start']:.2f} → {segment['end']:.2f}] {segment['text']}")

    return result
