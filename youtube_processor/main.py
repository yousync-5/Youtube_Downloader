# 기본 유틸리티 모듈
import os  # 운영체제 경로 관련
import time  # 시간 측정 및 대기
from pathlib import Path  # 경로 객체화를 위한 표준 모듈
from pprint import pprint  # 디버깅용 데이터 이쁘게 출력
from typing import Optional
import glob

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

def adjust_segment_boundaries_forward(segments):
    """
    문장 사이 텀을 앞 문장에 붙이기
    """
    if not segments:
        return segments
    
    adjusted_segments = []
    
    for i, seg in enumerate(segments):
        current_start = seg['start']
        current_end = seg['end']
        
        # 다음 문장과의 간격을 현재 문장에 붙이기
        if i < len(segments) - 1:
            next_start = segments[i+1]['start']
            gap = next_start - current_end
            if gap > 0:  # 텀이 있으면
                current_end += gap  # 현재 문장 끝을 뒤로 확장
                print(f"[DEBUG] 문장 {i+1}: 텀 {gap:.2f}초를 앞 문장에 붙임 ({current_start:.2f}s - {current_end:.2f}s)")
        
        adjusted_segments.append({
            **seg,
            'start': current_start,
            'end': current_end
        })
    
    return adjusted_segments

def main_pipeline(youtube_url: str, movie_name: Optional[str] = None, actor_name: Optional[str] = None, start: Optional[float] = None, end: Optional[float] = None, n_speakers: Optional[int] = None, token_name: Optional[str] = None) -> Optional[list[int]]:
    try:
        print(f"[DEBUG] main_pipeline called with start={start}, end={end}")
        start_time = time.time()  # ⏱️ 시작 시간

        video_id = extract_video_id(youtube_url)
        video_filename = sanitize_filename(video_id)
        print({video_id})
        print({video_filename})
        mp4_path = os.path.join("downloads", video_filename + ".mp4")
        download_video(youtube_url, mp4_path)
        mp3_path, _ = download_audio(youtube_url, video_id, video_filename)
        
        # start~end 구간만 잘리기
        if start is not None and end is not None:
            print(f"🔪 오디오 {start}~{end}초 구간만 추출합니다.")
            audio = AudioSegment.from_file(mp3_path)
            trimmed = audio[int(start * 1000):int(end * 1000)]  # ms 단위
            trimmed_path = os.path.join("downloads", f"{video_filename}_trimmed_{start}_{end}.mp3")
            trimmed.export(trimmed_path, format="mp3")
            mp3_path = trimmed_path  # 이후 분리/분석에 이 파일 사용
            print(f"✅ 잘린 오디오 저장: {trimmed_path}")

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
            print(f"[{seg.get('start', 0):.1f}s - {seg.get('end', 0):.1f}s]: {seg.get('text', '')}")
        
        # 문장 간 텀을 앞 문장에 붙이기
        print("🔧 문장 간 텀을 앞 문장에 붙이는 중...")
        segments = adjust_segment_boundaries_forward(segments)
        print("🗣️ 텀 조정 후:")
        for seg in segments:
            print(f"[{seg.get('start', 0):.1f}s - {seg.get('end', 0):.1f}s]: {seg.get('text', '')}")
        
        selected = segments[:]

        if not segments:
            print("❌ No speech detected.")
            return None

        word_list = format_segments_for_output(segments)

        # === 화자 수가 1명일 때: 화자분리/이미지 추출 등 스킵 ===
        if n_speakers == 1:
            print("👤 화자 1명: 화자분리/이미지 추출 등 스킵, 모든 데이터 S3/DB 저장")
            speaker_label = "SPEAKER_0"
            for seg in segments:
                seg['speaker'] = speaker_label
            post_word_data = merge_words_into_segments(segments, word_list)
            for seg in post_word_data:
                seg['speaker'] = speaker_label
            save_path = Path("cached_data/post_word_data.json")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(post_word_data, f, ensure_ascii=False, indent=2)
            print(f"✅ post_word_data 저장 완료: {save_path.resolve()}")
            # 1. TextGrid 생성
            export_segments_for_mfa(
                vocal_path=vocal_path,
                segments=segments,
                output_base="../syncdata/mfa/corpus",
                filename=video_filename,
                token_num=0
            )
            # 1.5. MFA align 실행 (TextGrid 생성)
            run_mfa_align()
            textgrid_path = f"../syncdata/mfa/mfa_output/{video_filename}0.TextGrid"
            # 2. 피치 데이터 생성
            print(f"[DEBUG] create_pitch_json_with_token 호출: vocal_path={vocal_path}, actor_name={actor_name}, pitch_path=./pitch_data/reference/{sanitize_filename(actor_name)}_{video_filename}_0pitch.json")
            create_pitch_json_with_token(
                vocal_path,
                {
                    "actor": actor_name,
                    "segments": post_word_data,
                    "speaker_label": speaker_label,
                    "video_url": youtube_url,  # 반드시 포함
                    "token_id": 0              # 반드시 포함
                }
            )
            pitch_path = f"./pitch_data/reference/{sanitize_filename(actor_name)}_{video_filename}_0pitch.json"
            print(f"[DEBUG] pitch_path: {pitch_path}, exists: {os.path.exists(pitch_path)}")
            # 3. S3 업로드
            bucket_name = "testgrid-pitch-bgvoice-yousync"
            s3_textgrid_url = upload_file_to_s3(textgrid_path, bucket_name, f"{actor_name}/{video_filename}/0/textgrid.TextGrid")
            s3_pitch_url = upload_file_to_s3(pitch_path, bucket_name, f"{actor_name}/{video_filename}/0/pitch.json")
            
            # 보컬 음성 업로드
            print(f"[DEBUG] vocal_path: {vocal_path}, exists: {os.path.exists(vocal_path)}")
            s3_vocal_url = upload_file_to_s3(
                vocal_path,
                bucket_name,
                f"{actor_name}/{video_filename}/0/vocal.wav"
            )
            
            # bgvoice 경로를 실제 분리된 오디오 폴더에서 가져오기
            bgvoice_dir = Path(vocal_path).parent
            bgvoice_path = str(bgvoice_dir / "no_vocals.wav")
            print(f"[DEBUG] bgvoice_path: {bgvoice_path}, exists: {os.path.exists(bgvoice_path)}")
            s3_bgvoice_url = upload_file_to_s3(
                bgvoice_path,
                bucket_name,
                f"{actor_name}/{video_filename}/0/bgvoice.wav"
            )
            s3_textgrid_url = s3_textgrid_url or ""
            s3_pitch_url = s3_pitch_url or ""
            s3_vocal_url = s3_vocal_url or ""
            s3_bgvoice_url = s3_bgvoice_url or ""
            
            # 타임스탬프 조정 (start 시간 추가) - DB 저장 직전에만
            if start is not None:
                print(f"[DEBUG] 타임스탬프 조정: 모든 시간에 +{start}초 추가")
                for seg in post_word_data:
                    seg['start'] += start
                    seg['end'] += start
                    if 'words' in seg:
                        for word in seg['words']:
                            word['start'] += start
                            word['end'] += start
            
            # 4. DB 저장
            token = make_token(
                db=db,
                movie_name=token_name or "",  # token_name을 movie_name 인자로 전달
                actor_name=actor_name or "",
                speaker={
                    "actor": actor_name or "",
                    "segments": post_word_data,
                    "speaker_label": speaker_label,
                    "video_url": youtube_url,
                    "start_time": start,
                    "end_time": end,
                },
                audio_path=vocal_path,
                s3_textgrid_url=s3_textgrid_url,
                s3_pitch_url=s3_pitch_url,
                s3_bgvoice_url=s3_bgvoice_url,
            )
            if token is not None and hasattr(token, 'id'):
                print(f"✅ DB 저장 완료, token id: {token.id}")
                try:
                    token_id = int(token.id)
                except Exception:
                    token_id = token.id
                if not isinstance(token_id, int):
                    return []
                return [token_id]
            return []

        # === 기존 화자분리 전체 파이프라인 ===
        print("👥 화자 2명 이상: 전체 파이프라인 실행")
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
            seg["start"] = round(float(seg.get("start", 0)), 2)
            seg["end"] = round(float(seg.get("end", 0)), 2)
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
            n_speakers=2
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
            segment_start = seg.get("start", 0)
            segment_end = seg.get("end", 0)
            print(f'📝 {segment_start:.2f} ~ {segment_end:.2f}: {seg.get("text", "")}')
            if "words" in seg:
                for word in seg["words"]:
                    w_start = word.get("start", 0)
                    w_end = word.get("end", 0)
                    w_text = word.get("word", "")
                    print(f'    🔹 {w_start:6.2f}s - {w_end:6.2f}s: {w_text}')

        HF_TOKEN = os.getenv("HF_TOKEN")
        with open(save_path, encoding="utf-8") as f:
            post_words = json.load(f)
        result = diarize_main_speaker(
            vocal_path     = vocal_path,
            post_word_data = post_words,
            hf_token       = HF_TOKEN or "",
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
        # actor_name이 콤마로 구분된 문자열로 들어온 경우 동적으로 speaker_name_map 생성
        actor_names = [name.strip() for name in (actor_name or "").split(",") if name.strip()]
        speaker_name_map = {
            f"SPEAKER_{i}": actor_names[i] if i < len(actor_names) else f"SPEAKER_{i}"
            for i in range(len(actor_names))
        }
        speaker_name_map["UNKNOWN"] = "Unknown"
        speakers = []
        for speaker_label, segs in speaker_segments.items():
            segs = sorted(segs, key=lambda s: s['start'])
            start_time = segs[0]['start']
            end_time = segs[-1]['end']
            token_name = speaker_name_map.get(speaker_label, speaker_label)
            # token_id는 SPEAKER_0, SPEAKER_1 등에서 숫자만 추출
            if speaker_label.startswith("SPEAKER_") and speaker_label.split('_')[-1].isdigit():
                token_id = int(speaker_label.split('_')[-1])
            else:
                token_id = 0
            speakers.append({
                "actor": token_name,
                "video_url": youtube_url,
                "token_id": token_id,
                "speaker_label": speaker_label,
                "start_time": start_time,
                "end_time": end_time,
                "segments": segs
            })
        token_ids = []
        # 전체 트리밍 구간의 Demucs 분리 폴더 경로 (정수형으로 맞춤)
        start_int = int(float(start)) if start is not None else 0
        end_int = int(float(end)) if end is not None else 0
        # Demucs 분리 폴더명에서 start, end를 제거하고 video_filename만 사용
        # Demucs 분리 폴더명은 항상 입력 오디오 파일명(stem)과 동일하게 맞춘다
        demucs_dir = f"separated/htdemucs/{Path(mp3_path).stem}"
        vocal_path = os.path.join(demucs_dir, "vocals.wav")
        bgvoice_path = os.path.join(demucs_dir, "no_vocals.wav")
        print(f"[DEBUG] demucs_dir: {demucs_dir}")
        print(f"[DEBUG] vocal_path: {vocal_path}")
        print(f"[DEBUG] bgvoice_path: {bgvoice_path}")
        for s3_data in speakers:
            actor = s3_data["actor"]
            # Demucs 분리 폴더 자동 탐색
            vocal_glob = f"separated/htdemucs/{Path(mp3_path).stem}/vocals.wav"
            no_vocal_glob = f"separated/htdemucs/{Path(mp3_path).stem}/no_vocals.wav"
            vocal_matches = glob.glob(vocal_glob)
            no_vocal_matches = glob.glob(no_vocal_glob)
            if vocal_matches:
                vocal_path = vocal_matches[0]
            else:
                print(f"[ERROR] vocals.wav 파일을 찾을 수 없습니다: {vocal_glob}")
                vocal_path = None
            if no_vocal_matches:
                bgvoice_path = no_vocal_matches[0]
            else:
                print(f"[ERROR] no_vocals.wav 파일을 찾을 수 없습니다: {no_vocal_glob}")
                bgvoice_path = None
            # 화자별 pitch 분석 및 pitch.json 경로 생성
            pitch_path = f"./pitch_data/reference/{sanitize_filename(actor)}_{video_filename}_{s3_data['token_id']}pitch.json"
            print(f"[DEBUG] create_pitch_json_with_token (multi-speaker) 호출: vocal_path={vocal_path}, actor={actor}, pitch_path={pitch_path}")
            if vocal_path is not None:
                create_pitch_json_with_token(
                    vocal_path,
                    {
                        "actor": actor,
                        "segments": s3_data["segments"],
                        "speaker_label": s3_data["speaker_label"],
                        "video_url": youtube_url,
                        "token_id": s3_data["token_id"]
                    }
                )
            # split_audio_by_token에 전체 구간 파일 경로 전달
            if vocal_path is not None and bgvoice_path is not None and os.path.exists(vocal_path) and os.path.exists(bgvoice_path):
                split_audio_by_token([vocal_path, bgvoice_path], s3_data, video_filename)
            else:
                print(f"[ERROR] split_audio_by_token에 넘길 파일이 부족합니다: {vocal_path}, {bgvoice_path}")
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
        # 1. 분석(MFCC, TextGrid, pitch 등)은 start를 더하지 않은 상태(0~구간길이)로 진행
        analysis_speakers = []
        for speaker in speakers:
            # deepcopy로 분석용 세그먼트 분리 (start를 더하지 않은 상태)
            import copy
            analysis_speaker = copy.deepcopy(speaker)
            for seg in analysis_speaker["segments"]:
                # start, end에서 start 오프셋을 빼서 0~구간길이로 맞춤
                seg['start'] = float(seg['start']) - float(start or 0)
                seg['end'] = float(seg['end']) - float(start or 0)
                if 'words' in seg:
                    for word in seg['words']:
                        word['start'] = float(word['start']) - float(start or 0)
                        word['end'] = float(word['end']) - float(start or 0)
            analysis_speakers.append(analysis_speaker)
        # 이후 분석(MFCC, pitch, TextGrid 등)은 analysis_speakers 사용

        # 2. DB/S3 저장 직전에만 start를 더해서 원본 타임스탬프(33~55초 등)로 변환
        for s3_data in speakers:
            token_id = s3_data["token_id"]
            actor = s3_data["actor"]
            if start is not None:
                print(f"[DEBUG] 화자 {token_id} 타임스탬프 조정: 모든 시간에 +{start}초 추가 (DB/S3 저장용)")
                for seg in s3_data["segments"]:
                    seg['start'] = float(seg['start']) + float(start)
                    seg['end'] = float(seg['end']) + float(start)
                    if 'words' in seg:
                        for word in seg['words']:
                            word['start'] = float(word['start']) + float(start)
                            word['end'] = float(word['end']) + float(start)
            # 이후 DB/S3 저장 코드 (make_token 등) 그대로 진행
            # Demucs 분리 폴더 자동 탐색 (mp3_path.stem 사용)
            demucs_dir = f"separated/htdemucs/{Path(mp3_path).stem}"
            vocal_glob = f"{demucs_dir}/vocals.wav"
            no_vocal_glob = f"{demucs_dir}/no_vocals.wav"
            print(f"[DEBUG] vocal_glob: {vocal_glob}")
            print(f"[DEBUG] no_vocal_glob: {no_vocal_glob}")
            vocal_matches = glob.glob(vocal_glob)
            no_vocal_matches = glob.glob(no_vocal_glob)
            if vocal_matches:
                vocal_path = vocal_matches[0]
            else:
                print(f"[ERROR] vocals.wav 파일을 찾을 수 없습니다: {vocal_glob}")
                vocal_path = None
            if no_vocal_matches:
                bgvoice_path = no_vocal_matches[0]
            else:
                print(f"[ERROR] no_vocals.wav 파일을 찾을 수 없습니다: {no_vocal_glob}")
                bgvoice_path = None
            # 이후 코드에서 vocal_path, bgvoice_path 사용
            # S3/DB 업로드 복구 및 에러 핸들링 추가
            s3_prefix = f"{actor}/{video_filename}/{token_id}"
            s3_textgird_key = f"{s3_prefix}/textgrid.TextGrid"
            s3_pitchdata_key = f"{s3_prefix}/pitch.json"
            s3_bgvoice_key = f"{s3_prefix}/bgvoice.wav"
            s3_textgrid_path = f"../syncdata/mfa/mfa_output/{video_filename}{token_id}.TextGrid"
            s3_pitchdata_path = f"./pitch_data/reference/{sanitize_filename(actor)}_{video_filename}_{token_id}pitch.json"
            s3_bgvoice_path = bgvoice_path
            s3_textgrid_url = s3_pitch_url = s3_bgvoice_url = None
            missing = False
            if not os.path.exists(s3_textgrid_path):
                print(f"[ERROR] TextGrid 파일이 없습니다: {s3_textgrid_path}")
                missing = True
            if not os.path.exists(s3_pitchdata_path):
                print(f"[ERROR] pitch.json 파일이 없습니다: {s3_pitchdata_path}")
                missing = True
            if not (s3_bgvoice_path and isinstance(s3_bgvoice_path, str) and os.path.exists(s3_bgvoice_path)):
                print(f"[ERROR] bgvoice.wav 파일이 없습니다: {s3_bgvoice_path}")
                missing = True
            if not (vocal_path and isinstance(vocal_path, str) and os.path.exists(vocal_path)):
                print(f"[ERROR] vocal.wav 파일이 없습니다: {vocal_path}")
                missing = True
            if missing:
                print(f"[SKIP] 화자 {actor} (token_id={token_id})의 S3/DB 저장을 건너뜁니다.")
                continue
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
            if s3_textgrid_url and s3_pitch_url and s3_bgvoice_url and vocal_path is not None:
                token = make_token(
                    db=db,
                    movie_name=movie_name or "",
                    actor_name=actor,
                    speaker=s3_data,
                    audio_path=vocal_path,
                    s3_textgrid_url=s3_textgrid_url,
                    s3_pitch_url=s3_pitch_url,
                    s3_bgvoice_url=s3_bgvoice_url,
                )
                if token is not None and hasattr(token, 'id'):
                    print(f"✅ DB 저장 완료, token id: {token.id}")
                    token_id_val = token.id
                    # Only append if token_id_val is a real int (not a SQLAlchemy Column object)
                    if isinstance(token_id_val, int):
                        token_ids.append(token_id_val)
                    else:
                        try:
                            # Some SQLAlchemy objects may be convertible to int, but skip if not
                            converted = int(token_id_val)
                            token_ids.append(converted)
                        except Exception:
                            print(f"[WARN] token.id가 int로 변환 불가 또는 Column 객체임: {token_id_val} (type={type(token_id_val)})")
        print(" TextGrid 기반 토큰 생성 중...")
        reset_folder("../syncdata/mfa/corpus", "../syncdata/mfa/mfa_output")
        reset_folder("tmp_frames", "downloads", "separated/htdemucs", "cached_data","pitch_data", "split_tokens")
        # 실제 DB에 저장된 첫 번째 토큰의 id를 반환
        if token_ids:
            return token_ids  # 여러 화자의 token_id 리스트 반환
        return []
    except Exception as e:
        import traceback
        print("❌ main_pipeline 내부 예외 발생:", e)
        traceback.print_exc()
        raise

# 기존 main()은 FastAPI 등에서 필요 없으므로 생략하거나, 아래처럼 남겨둘 수 있습니다.
if __name__ == "__main__":
    import traceback
    s_time = time.time()  # ⏱️ 시작 시간
    try:
        # ====== JSON 파일에서 여러 건 처리 (데모용) ======
        try:
            with open("data.json", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                url = item["url"]
                start = item["start"]
                end = item["end"]
                n_speakers = item["n_speakers"]
                token_name = item.get("token_name", "")

                if n_speakers == 1:
                    actor = item["actor"]
                    print(f"\n==== {actor} ({url}) {start}~{end}s, 화자수: {n_speakers} ====")
                    main_pipeline(url, actor_name=actor, start=start, end=end, n_speakers=n_speakers, token_name=token_name)
                elif n_speakers == 2:
                    actor1 = item["actor1"]
                    actor2 = item["actor2"]
                    print(f"\n==== {actor1}, {actor2} ({url}) {start}~{end}s, 화자수: {n_speakers} ====")
                    # 두 명의 이름을 콤마로 연결해서 넘김
                    main_pipeline(
                        url,
                        actor_name=f"{actor1},{actor2}",
                        start=start,
                        end=end,
                        n_speakers=n_speakers,
                        token_name=token_name
                    )
                else:
                    print(f"지원하지 않는 화자 수: {n_speakers}")
        except FileNotFoundError:
            print("data.json 파일이 없습니다. 기존 input() 방식으로 실행합니다.")
            # youtube_url = input("📺 URL 입력을 바랍니다.: ").strip()
            # main_pipeline(youtube_url)
    except Exception as e:
        print("❌ 예외 발생:", e)
        traceback.print_exc()
    e_time = time.time() - s_time  # ⏱️ 소요 시간
    print(f"🕒 전체 전처리 소요 시간: {e_time:.2f}초")