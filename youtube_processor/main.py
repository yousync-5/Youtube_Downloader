# 기본 유틸리티 모듈
import os  # 운영체제 경로 관련
import time  # 시간 측정 및 대기
from pathlib import Path  # 경로 객체화를 위한 표준 모듈
from pprint import pprint  # 디버깅용 데이터 이쁘게 출력

#다운로드 관련(Youtube)
from downloader import download_audio, download_video # 유튜브 영상 및 오디오 다운로드

#오디오 처리/분리
from demucs_wrapper import separate_vocals  # 배경음/음성 분리 (Demucs 사용)
from pydub import AudioSegment  # mp3/wav 변환 등 오디오 조작
from speaker_diarization.split_mp3 import split_audio_by_token  # Token 단위로 오디오 나누기

#자막 생성 및 처리
from transcriber import transcribe_audio #, transcribe_audio_check  # Whisper 등으로 자막 생성
from level_up_textgrid import generate_sentence_json  # TextGrid 자막 → 문장 JSON 변환
from export_for_mfa import export_segments_for_mfa  # MFA 학습용 자막/음성 데이터 포맷팅
from format_segments_for_output import format_segments_for_output

#화자 분석/분리
from speaker_diarization.who_is_speaker import analyze_speakers  # 얼굴 + 자막 + 음성 기반 화자 식별
from speaker_diarization.voice_analyzer import analyze_voice_speakers  # 음성 기반 화자 분리 (e.g., pyannote)
from speaker_diarization.frame_extractor import extract_frames_per_segment  # 자막 구간 기반 프레임 추출
from speaker_diarization.split_segment import split_segments_by_half # 화자분리 함수 
from merge_words import merge_words_into_segments
#음성 피치 분석
from voice_to_pitch import create_pitch_json_with_token  # 구간별 pitch(음높이) 추출 및 저장

#s3 업로드
from upload_file_to_s3 import upload_file_to_s3  # AWS S3 업로드


#유틸 함수 모음
from utils import sanitize_filename, extract_video_id, reset_folder, run_mfa_align, generate_presigned_url   # 경로 정리, 유튜브 ID 추출, 폴더 초기화 등

#토큰 및 db관련 로직
from token_generator import create_token  # Token 생성 (음성+자막 묶음)

from sqlalchemy.orm import sessionmaker, Session  # DB 세션 관련
from postgres.models import Token, Script  # ORM 모델 정의
from postgres.post_data import make_token  # Token + 문장 → DB 저장 함수

from dotenv import load_dotenv
load_dotenv()
from postgres.database import engine  # SQLAlchemy DB 엔진

# 음성 기반 화자 분리

# from pyannote.audio import Pipeline
# from collections import defaultdict # defaultdict가 없다면 추가
# from pyannote.audio.pipelines import SpeakerDiarization
from speaker_diarizer import diarize_main_speaker
import json # 다운로드용

import torch
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# DB 엔진에 연결된 세션 팩토리 생성 (autocommit=False, autoflush=True 기본값 사용)
SessionLocal = sessionmaker(bind=engine)

# 실제 사용할 DB 세션 인스턴스 생성 (이걸로 쿼리 수행)
db = SessionLocal()

def main_pipeline(youtube_url, movie_name=None, actor_name=None):
    start_time = time.time()  # ⏱️ 시작 시간

    video_id = extract_video_id(youtube_url)
    video_filename = sanitize_filename(video_id)
    print({video_id})
    print({video_filename})
    mp4_path = os.path.join("downloads", video_filename + ".mp4")
    download_video(youtube_url, mp4_path)
    mp3_path, _ = download_audio(youtube_url, video_id, video_filename)

    if not os.path.exists(mp4_path):
        download_video(youtube_url, mp4_path)
    else:
        print(f"✅ 영상 파일 이미 존재: {mp4_path}")

    # 2-1  Demucs로 보컬 추출
    start_time = time.time()
    print(f"🕒 보컬 추출 측정시작")
    vocal_path = separate_vocals(mp3_path)
    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 보컬 추출 전처리 소요 시간: {elapsed:.2f}초")

    start_time = time.time()
    print(f"🕒 자막 추출 측정시작")
    segments = transcribe_audio(vocal_path)
    print("🗣️ 정밀분석:")
    for seg in segments:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")
    selected = segments[:]

    if not segments:
        print("❌ No speech detected.")
        return None

    word_list = format_segments_for_output(segments)

    print("📦 MFA용 음성/텍스트 export:")
    print("📦 첫번째 MFA분석 목적은 화자분리 데이터를 만들기 위함이다. ")
    print("⏳ TextGrid 생성 완료를 기다리는 중...")
    export_segments_for_mfa(
        vocal_path=vocal_path,
        segments=segments,
        output_base="../syncdata/mfa/corpus",
        filename=video_filename,
        token_num=0
    )
    start_time = time.time()
    print(f"🕒 측정시작")
    run_mfa_align()
    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 전처리 소요 시간: {elapsed:.2f}초")

    speaker_diarization_data = generate_sentence_json(selected, f"../syncdata/mfa/mfa_output/{video_filename}0.TextGrid")
    for seg in speaker_diarization_data:
        seg["start"] = round(float(seg["start"]), 2)
        seg["end"] = round(float(seg["end"]), 2)
    for check in speaker_diarization_data:
        print(check)
    pprint(speaker_diarization_data)
    print("여기 출력값은 정확히 화자분리를 위한 문장 타임 스템프로 활용된다.")

    extract_frames_per_segment(mp4_path, speaker_diarization_data, output_folder="tmp_frames")
    print("✅ 세그먼트별 프레임 이미지 추출 완료: tmp_frames/")

    from speaker_diarization.who_is_speaker import analyze_speakers_with_clustering, print_speaker_dialogue
    from speaker_diarization.voice_analyzer import analyze_voice_speakers_with_clustering
    face_labels, _ = analyze_speakers_with_clustering(
        len(speaker_diarization_data),
        folder="tmp_frames",
        threshold=0.6
    )
    n_speakers = 0
    # FastAPI에서는 입력 대신 기본값/추론 사용
    n_speakers = len(set([l for l in face_labels if l != "UNKNOWN"]))
    if n_speakers < 1:
        n_speakers = 2
    voice_labels, _ = analyze_voice_speakers_with_clustering(
        vocal_path, speaker_diarization_data, n_speakers=n_speakers
    )
    final_labels = []
    for f, v in zip(face_labels, voice_labels):
        if f == v:
            final_labels.append(f)
        elif f == "UNKNOWN":
            final_labels.append(v)
        elif v == "UNKNOWN":
            final_labels.append(f)
        else:
            final_labels.append(v)  # 음성 우선
    for i, (seg, label) in enumerate(zip(speaker_diarization_data, final_labels)):
        seg['speaker'] = label
    print("\n=== 얼굴+음성 융합 화자분리 결과 ===")
    print_speaker_dialogue(speaker_diarization_data, final_labels)

    post_word_data = merge_words_into_segments(speaker_diarization_data, word_list)
    for seg in post_word_data:
        match = next(
            (s for s in speaker_diarization_data
             if abs(s['start'] - seg['start']) < 0.01 and abs(s['end'] - seg['end']) < 0.01),
            None
        )
        if match and 'speaker' in match:
            seg['speaker'] = match['speaker']
        else:
            seg['speaker'] = 'UNKNOWN'

    save_path = Path("cached_data/post_word_data.json")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(post_word_data, f, ensure_ascii=False, indent=2)
    print(f"✅ post_word_data 저장 완료: {save_path.resolve()}")

    for seg in post_word_data:
        start = seg["start"]
        end = seg["end"]
        print(f'📝 {start:.2f} ~ {end:.2f}: {seg["text"]}')
        if "words" in seg:
            for word in seg["words"]:
                w_start = word["start"]
                w_end = word["end"]
                w_text = word["word"]
                print(f'    🔹 {w_start:6.2f}s - {w_end:6.2f}s: {w_text}')

    HF_TOKEN = os.getenv("HF_TOKEN")
    with open(save_path, encoding="utf-8") as f:
        post_words = json.load(f)
    result = diarize_main_speaker(
        vocal_path     = vocal_path,
        post_word_data = post_words,
        hf_token       = HF_TOKEN,
    )
    main_speaker_label    = result["label"]
    main_speaker_segments = result["segments"]
    final_start_time      = result["start"]
    final_end_time        = result["end"]
    print("👑 Main speaker:", main_speaker_label)
    for i, s in enumerate(main_speaker_segments, 1):
        print(f"[{i}] {s['start']:.2f}-{s['end']:.2f}: {s['text']}")

    from collections import defaultdict
    speaker_segments = defaultdict(list)
    for seg in post_word_data:
        speaker = seg['speaker']
        speaker_segments[speaker].append(seg)
    speaker_name_map = {
        "SPEAKER_0": "Natalie Portman",
        "SPEAKER_1": "Jude Law",
        "UNKNOWN": "Unknown"
    }
    speakers = []
    for idx, (speaker_label, segs) in enumerate(speaker_segments.items(), 1):
        segs = sorted(segs, key=lambda s: s['start'])
        start_time = segs[0]['start']
        end_time = segs[-1]['end']
        token_name = speaker_name_map.get(speaker_label, speaker_label)
        speakers.append({
            "actor": token_name,
            "video_url": youtube_url,
            "token_id": idx,
            "speaker_label": speaker_label,
            "start_time": start_time,
            "end_time": end_time,
            "segments": segs
        })
    token_ids = []
    for s3_data in speakers:
        vocal_path_obj = Path("separated") / "htdemucs" / video_filename / "vocals.wav"
        no_vocals_path_obj = Path("separated") / "htdemucs" / video_filename / "no_vocals.wav"
        split_audio_by_token([vocal_path_obj, no_vocals_path_obj], s3_data, video_filename)
        segments = s3_data["segments"]
        vocal_path_token = f"./split_tokens/vocals_{video_filename}_token_{s3_data['token_id']}.mp3"
        export_segments_for_mfa(
            vocal_path=vocal_path_token,
            segments=segments,
            output_base="../syncdata/mfa/corpus",
            filename=video_filename,
            token_num=s3_data["token_id"]
        )
    start_time = time.time()
    print("🕒 측정시작")
    run_mfa_align()
    elapsed = time.time() - start_time
    print(f"🕒 전처리 소요 시간: {elapsed:.2f}초")
    bucket_name = "testgrid-pitch-bgvoice-yousync"
    for s3_data in speakers:
        token_id = s3_data["token_id"]
        actor = s3_data["actor"]
        vocal_path = f"separated/htdemucs/{video_filename}/vocals.wav"  # 전체 보컬 오디오 사용
        bgvoice_path = f"./split_tokens/no_vocals_{video_filename}_token_{token_id}.mp3"
        create_pitch_json_with_token(vocal_path, s3_data)
        s3_prefix = f"{actor}/{video_filename}/{token_id}"
        s3_textgird_key = f"{s3_prefix}/textgrid.TextGrid"
        s3_pitchdata_key = f"{s3_prefix}/pitch.json"
        s3_bgvoice_key = f"{s3_prefix}/bgvoice.mp3"
        s3_textgrid_path = f"../syncdata/mfa/mfa_output/{video_filename}{token_id}.TextGrid"
        s3_pitchdata_path = f"./pitch_data/reference/{sanitize_filename(actor)}_{video_filename}_{token_id}pitch.json"
        s3_bgvoice_path = bgvoice_path
        try:
            s3_textgrid_url = upload_file_to_s3(s3_textgrid_path, bucket_name, s3_textgird_key)
            s3_pitch_url = upload_file_to_s3(s3_pitchdata_path, bucket_name, s3_pitchdata_key)
            s3_bgvoice_url = upload_file_to_s3(s3_bgvoice_path, bucket_name, s3_bgvoice_key)
        except FileNotFoundError as e:
            print(f"❌ 로컬 파일을 찾을 수 없습니다: {e.filename}")
            continue
        except Exception as e:
            print(f"❌ 예기치 않은 오류 발생: {e}")
            continue
        if s3_textgrid_url and s3_pitch_url and s3_bgvoice_url:
            token = make_token(
                db=db,
                movie_name=movie_name,
                actor_name=actor,
                speaker=s3_data,
                audio_path=vocal_path,
                s3_textgrid_url=s3_textgrid_url,
                s3_pitch_url=s3_pitch_url,
                s3_bgvoice_url=s3_bgvoice_url,
            )
            if token is not None and hasattr(token, 'id'):
                token_ids.append(token.id)
    print("🎯 TextGrid 기반 토큰 생성 중...")
    reset_folder("../syncdata/mfa/corpus", "../syncdata/mfa/mfa_output")
    reset_folder("tmp_frames", "downloads", "separated/htdemucs", "cached_data","pitch_data", "split_tokens")
    # 실제 DB에 저장된 첫 번째 토큰의 id를 반환
    if token_ids:
        return token_ids  # 여러 화자의 token_id 리스트 반환
    return []

# 기존 main()은 FastAPI 등에서 필요 없으므로 생략하거나, 아래처럼 남겨둘 수 있습니다.
if __name__ == "__main__":
    import traceback
    s_time = time.time()  # ⏱️ 시작 시간
    try:
        # main() 대신 main_pipeline을 직접 호출할 수 있음
        youtube_url = input("📺 URL 입력을 바랍니다.: ").strip()
        main_pipeline(youtube_url)
    except Exception as e:
        print("❌ 예외 발생:", e)
        traceback.print_exc()
    e_time = time.time() - s_time  # ⏱️ 소요 시간
    print(f"🕒 전체 전처리 소요 시간: {e_time:.2f}초")