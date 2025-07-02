from pathlib import Path
from pydub import AudioSegment
from utils import run_mfa_align

def export_segments_for_mfa(vocal_path: str, segments: list, output_base: str = "mfa/corpus", filename: str= "full", actor_name: str = 'none', token_num: int = 0):
    """
    전체 음성 + 전체 자막을 1쌍으로 저장하여 MFA 분석 성능을 점검하기 위한 함수
    """
    output_dir = Path(output_base)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        full_audio = AudioSegment.from_file(vocal_path)
    except Exception as e:
        print(f"❌ WAV 파일 로드 실패: {e}")
        return

    try:
        # 오디오 변환 및 저장
        clip = full_audio.set_channels(1).set_frame_rate(16000)
        clip_path = output_dir / f"{filename}{token_num}.wav"
        clip.export(clip_path, format="wav", parameters=["-acodec", "pcm_s16le"])

        # 전체 텍스트 합치기
        full_text = " ".join(seg["text"].strip().upper() for seg in segments if seg.get("text"))

        with open(output_dir / f"{filename}{token_num}.lab", "w", encoding="utf-8") as f:
            f.write(full_text)

        print(f"✅ 음성 및 자막이 저장되었습니다 → {clip_path} / {filename}{token_num}.lab")
        # run_mfa_align()
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
