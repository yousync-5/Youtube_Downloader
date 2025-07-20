from pathlib import Path
from pydub import AudioSegment
import re
from utils import run_mfa_align


def normalize_text(text: str) -> str:
    # 축약형 처리
    substitutions = {
        "HE'S": "HE IS",
        "SHE'S": "SHE IS",
        "I'M": "I AM",
        "DON'T": "DO NOT",
        "DIDN'T": "DID NOT",
        "WASN'T": "WAS NOT",
        "AREN'T": "ARE NOT",
        "WON'T": "WILL NOT",
        "COULDN'T": "COULD NOT",
        "IT'S": "IT IS",
        "THAT'S": "THAT IS",
        "WE'RE": "WE ARE",
        "YOU'RE": "YOU ARE",
        "THEY'RE": "THEY ARE",
        "I'LL": "I WILL",
        "WE'LL": "WE WILL",
        "YOU'LL": "YOU WILL",
        "HE'LL": "HE WILL",
        "SHE'LL": "SHE WILL",
        "CAN'T": "CANNOT",
    }
    for k, v in substitutions.items():
        text = text.replace(k, v)
    return text


def split_into_sentences(text: str) -> list[str]:
    # 마침표, 느낌표, 물음표 뒤에서 잘라서 문장 단위로 나눔
    return re.split(r'(?<=[.?!])\s+', text)


def export_segments_for_mfa(vocal_path: str, segments: list, output_base: str = "mfa/corpus", filename: str = "full", actor_name: str = 'none', token_num: int = 0):
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
        # 항상 token_num을 붙여서 파일명 생성
        clip_path = output_dir / f"{filename}{token_num}.wav"
        clip.export(clip_path, format="wav", parameters=["-acodec", "pcm_s16le"])

        # 전체 텍스트 정제 및 문장 분리
        # 기존: raw_text = " ".join(seg["text"].strip().upper() for seg in segments if seg.get("text"))
        # clean_text = normalize_text(raw_text)
        # sentences = split_into_sentences(clean_text)
        # 수정: Whisper segment별로 한 줄씩 저장
        sentences = [seg["text"].strip().upper() for seg in segments if seg.get("text")]
        # .lab 파일 저장 (문장당 한 줄)
        lab_path = output_dir / f"{filename}{token_num}.lab"
        with open(lab_path, "w", encoding="utf-8") as f:
            for line in sentences:
                f.write(line + "\n")

        print(f"✅ 음성 및 자막이 저장되었습니다 → {clip_path.name} / {lab_path.name}")
        # run_mfa_align()

    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
