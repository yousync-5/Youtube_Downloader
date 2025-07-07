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
from transcriber import transcribe_audio, transcribe_audio_check  # Whisper 등으로 자막 생성
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

def main():

    # 1. 유튜브 데이터 

    # 1-1 URL 저장
    youtube_url = input("📺 URL 입력을 바랍니다.: ").strip()


    #당장은 필요치아니함

    movie_name = None
    actor_name = None
    try:
        # 터미널 인코딩 설정
        import sys
        if hasattr(sys.stdin, 'reconfigure'):
            sys.stdin.reconfigure(encoding='utf-8')
        
        movie_input = input("영화 이름을 입력하세요 (선택사항): ")
        if movie_input and movie_input.strip():
            movie_name = movie_input.strip()
            
        actor_input = input("배우 이름을 입력하세요 (선택사항): ")
        if actor_input and actor_input.strip():
            actor_name = actor_input.strip()
            
    except (UnicodeDecodeError, UnicodeError) as e:
        print(f"입력 인코딩 오류: {e}")
        print("기본값을 사용합니다.")
        movie_name = None
        actor_name = None
    except Exception as e:
        print(f"입력 처리 중 오류: {e}")
        movie_name = None
        actor_name = None


    start_time = time.time()  # ⏱️ 시작 시간

    # 1-2 비디오 ID/FileName 추출
    video_id = extract_video_id(youtube_url)
    video_filename = sanitize_filename(video_id)
    print({video_id})
    print({video_filename})
    # 1-3 폴더 경로지정
    mp4_path = os.path.join("downloads", video_filename + ".mp4")
    download_video(youtube_url, mp4_path)
    # 1-4 오디오 추출 및 파일 경로 반환 
    mp3_path, _ = download_audio(youtube_url, video_id, video_filename)
 
    # 1-5 영상이 없을 시 다운로드 실행
    if not os.path.exists(mp4_path):
        download_video(youtube_url, mp4_path)
    else:
        print(f"✅ 영상 파일 이미 존재: {mp4_path}")

    # 2. 데이터 추출

    # 2-1  Demucs로 보컬 추출
    
    start_time = time.time()
    print(f"🕒 보컬 추출 측정시작")
    vocal_path = separate_vocals(mp3_path)
    
    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 보컬 추출 전처리 소요 시간: {elapsed:.2f}초")


    start_time = time.time()
    print(f"🕒 자막 추출 측정시작")
    # 2-2  Whisper로 자막 추출
    segments = transcribe_audio(vocal_path)
    print("🗣️ 정밀분석:")
    for seg in segments:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")
    selected = segments[:]

    if not segments:
        print("❌ No speech detected.")
        return

    # elapsed = time.time() - start_time  # ⏱️ 소요 시간
    # print(f"🕒 자막 추출 전처리 소요 시간: {elapsed:.2f}초")


    check_segment = transcribe_audio_check(vocal_path)


    print("🗣️ First 5 segments:")
    for seg in check_segment:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")


    #예외처리



    # 테스트용
    word_list = format_segments_for_output(segments)
    # print("🗣️ 선택된 문장 리스트:")
    # for i, seg in enumerate(word_list, 1):
    #     print(f"{i:>2}. ⏱️ {seg['start']:.2f}s ~ {seg['end']:.2f}s | 📝 "{seg['text']}"")

    #     if "words" in seg:
    #         for w in seg["words"]:
    #             w_start = round(w["start"], 2)
    #             w_end = round(w["end"], 2)
    #             w_text = w["word"].strip()
    #             print(f"    🔹 {w_start:.2f}s - {w_end:.2f}s: {w_text}")

    

    # 🔡 MFA용 세그먼트 내보내기
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
    
    # MFA 처리를 try-except로 감싸서 오류 시에도 계속 진행
    try:
        run_mfa_align()
        elapsed = time.time() - start_time  # ⏱️ 소요 시간
        print(f"🕒 전처리 소요 시간: {elapsed:.2f}초")
        
        # MFA 결과를 사용한 화자 분리 데이터 생성
        speaker_diarization_data = generate_sentence_json(selected,f"../syncdata/mfa/mfa_output/{video_filename}0.TextGrid" )
        print("✅ MFA 기반 화자 분리 데이터 생성 완료")
    except Exception as e:
        print(f"⚠️ MFA 처리 중 오류 발생: {e}")
        print("🔄 MFA 없이 기본 세그먼트 데이터로 진행합니다...")
        # MFA 없이 기본 segments 데이터 사용
        speaker_diarization_data = []
        for i, seg in enumerate(segments):
            speaker_diarization_data.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2), 
                "text": seg["text"],
                "speaker": f"SPEAKER_{i % 2}"  # 임시로 2명의 화자로 분할
            })
        print("✅ 기본 화자 분리 데이터 생성 완료")

    for seg in speaker_diarization_data:
        seg["start"] = round(float(seg["start"]), 2)
        seg["end"] = round(float(seg["end"]), 2)
    for check in speaker_diarization_data:
        print(check)
    pprint(speaker_diarization_data)

    print("여기 출력값은 정확히 화자분리를 위한 문장 타임 스템프로 활용된다.")

    post_word_data = merge_words_into_segments(speaker_diarization_data, word_list)

    #####################################################
    ## test를 위한 저장
    save_path = Path("cached_data/post_word_data.json")
    save_path.parent.mkdir(parents=True, exist_ok=True)  # 폴더 없으면 생성

    # JSON 저장
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(post_word_data, f, ensure_ascii=False, indent=2)

    print(f"✅ post_word_data 저장 완료: {save_path.resolve()}")
    #####################################################


    print("이번에는 기대를 해봅니다.")

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

    # for seg in result:
    #     print(f"🟢 {seg['start']}s - {seg['end']}s: {seg['text']}")
    #     if "words" in seg:
    #         for w in seg["words"]:
    #             print(f"   🔹 {w['start']}s - {w['end']}s: {w['text']}")


    # print("⏳ 이 시점에서 뽑혀진 textgrid와 segment로 화자를 분리 데이터를 만든 후 폴더를 비우고 화자별로 재요청을 보내야한다")


    #객체 배열이 반환된다. 배열의 내용은 
    #화자분리 로직 위치
    #화자 분리 데이터가 나온다면 오디오도 기준에 맞춰 잘라져야한다. 
 

    # print("만약 이렇게 분할에 성공한다면 지금 즉시 syncdata 파일 내의 데이터들은 지우고 새로 요청을 박자.")


    #화자분리 데이터가 뽑혀야한다. 
########################################################################################

    HF_TOKEN = os.getenv("HF_TOKEN")
    # VOCAL_MP3  = f"split_tokens/vocals_{video_filename}_token_1.mp3"
    # POST_JSON  = "cached_data/post_word_data.json"

    with open(save_path, encoding="utf-8") as f:
    # with open(POST_JSON, encoding="utf-8") as f:
        post_words = json.load(f)

    result = diarize_main_speaker(
        vocal_path     = vocal_path,
        post_word_data = post_words,
        hf_token       = HF_TOKEN,
    )
    # diar_result 구조:  {'label', 'segments', 'start', 'end'}
    main_speaker_label    = result["label"]
    main_speaker_segments = result["segments"]
    final_start_time      = result["start"]
    final_end_time        = result["end"]


    print("👑 Main speaker:", main_speaker_label)
    for i, s in enumerate(main_speaker_segments, 1):
        print(f"[{i}] {s['start']:.2f}-{s['end']:.2f}: {s['text']}")

    speakers = [
        {
            "actor": actor_name,    # 스크립트 초기에 입력받은 배우 이름
            "video_url": youtube_url,
            "token_id": 1,          # 주요 화자는 항상 token_id 1을 가짐
            "speaker_label": main_speaker_label,
            "start_time": final_start_time,
            "end_time": final_end_time,
            "segments": main_speaker_segments
        }
    ]
    # ==================

    # print("해당지점에서 화자분리하다가 터진다/n")
    # speaker = post_word_data
    # split_segments_by_half(post_word_data, youtube_url,actor_name)
    
    
    #S3 채우기 + 화자분리 데이터 분할로직

    vocal_path = Path("separated") / "htdemucs" /video_filename / "vocals.wav"
    no_vocals_path =  Path("separated") / "htdemucs" /video_filename / "no_vocals.wav"
    
    # 추가#
    for speaker in speakers:
        split_audio_by_token([vocal_path, no_vocals_path], speaker, video_filename)


    #새로운 text그
    reset_folder("../syncdata/mfa/corpus", "../syncdata/mfa/mfa_output")
    print("제거성공")
    # 1. 먼저 모든 token에 대해 lab/wav export만 수행
    for s3_data in speakers:
        print(f"▶️ 처리 중: token_id={s3_data['token_id']}")
        
        segments = s3_data["segments"]
        vocal_path = f"./split_tokens/vocals_{video_filename}_token_{s3_data['token_id']}.mp3"
        export_segments_for_mfa(
            vocal_path=vocal_path,
            segments=segments,
            output_base="../syncdata/mfa/corpus",
            filename=video_filename,
            token_num=s3_data["token_id"]
        )

    # 2. MFA 실행은 한 번만
    start_time = time.time()
    print("🕒 측정시작")
    try:
        run_mfa_align()
        elapsed = time.time() - start_time
        print(f"🕒 전처리 소요 시간: {elapsed:.2f}초")
        print("✅ MFA 처리 완료")
    except Exception as e:
        print(f"⚠️ MFA 처리 중 오류 발생: {e}")
        print("🔄 MFA 없이 계속 진행합니다...")

    bucket_name = "testgrid-pitch-bgvoice-yousync"
    # 3. 이후 pitch, 업로드, DB 저장 처리 반복
    for s3_data in speakers:
        token_id = s3_data["token_id"]
        actor = s3_data.get("actor", "unknown")  # 안전하게 actor 값 가져오기, 없으면 "unknown" 사용
        
        # actor가 None이거나 빈 문자열인 경우 기본값 설정
        if not actor or actor.strip() == "":
            actor = "unknown_actor"
        
        print(f"🔍 처리 중인 토큰 정보:")
        print(f"  - token_id: {token_id}")
        print(f"  - actor: '{actor}' (type: {type(actor)})")
        print(f"  - s3_data keys: {list(s3_data.keys())}")

        vocal_path = f"./split_tokens/vocals_{video_filename}_token_{token_id}.mp3"
        bgvoice_path = f"./split_tokens/no_vocals_{video_filename}_token_{token_id}.mp3"

        # pitch 추출
        create_pitch_json_with_token(vocal_path, s3_data)

        # S3 경로 구성
        s3_prefix = f"{actor}/{video_filename}/{token_id}"
        s3_textgird_key = f"{s3_prefix}/textgrid.TextGrid"
        s3_pitchdata_key = f"{s3_prefix}/pitch.json"
        s3_bgvoice_key = f"{s3_prefix}/bgvoice.mp3"
        
        s3_textgrid_path = f"../syncdata/mfa/mfa_output/{video_filename}{token_id}.TextGrid"
        s3_pitchdata_path = f"./pitch_data/reference/{sanitize_filename(actor)}_{video_filename}_{token_id}pitch.json"
        s3_bgvoice_path = bgvoice_path

        # S3 업로드 변수 초기화
        s3_textgrid_url = None
        s3_pitch_url = None
        s3_bgvoice_url = None
        
        # S3 업로드
        try:
            s3_textgrid_url = upload_file_to_s3(s3_textgrid_path, bucket_name, s3_textgird_key)
            print(f"✅ TextGrid S3 업로드 성공: {s3_textgrid_url}")
        except FileNotFoundError as e:
            print(f"❌ TextGrid 파일을 찾을 수 없습니다: {e.filename}")
        except Exception as e:
            print(f"❌ TextGrid S3 업로드 실패: {e}")
            
        try:
            s3_pitch_url = upload_file_to_s3(s3_pitchdata_path, bucket_name, s3_pitchdata_key)
            print(f"✅ Pitch 데이터 S3 업로드 성공: {s3_pitch_url}")
        except FileNotFoundError as e:
            print(f"❌ Pitch 파일을 찾을 수 없습니다: {e.filename}")
        except Exception as e:
            print(f"❌ Pitch S3 업로드 실패: {e}")
            
        try:
            s3_bgvoice_url = upload_file_to_s3(s3_bgvoice_path, bucket_name, s3_bgvoice_key)
            print(f"✅ 배경음성 S3 업로드 성공: {s3_bgvoice_url}")
        except FileNotFoundError as e:
            print(f"❌ 배경음성 파일을 찾을 수 없습니다: {e.filename}")
        except Exception as e:
            print(f"❌ 배경음성 S3 업로드 실패: {e}")

        # DB 저장 (배경음성이 있으면 저장, 피치 데이터는 선택사항)
        print(f"🔍 S3 업로드 결과 확인:")
        print(f"  - TextGrid URL: {s3_textgrid_url}")
        print(f"  - Pitch URL: {s3_pitch_url}")
        print(f"  - 배경음성 URL: {s3_bgvoice_url}")
        
        if s3_bgvoice_url:  # 배경음성만 있어도 저장
            print("🎯 데이터베이스에 토큰 저장 중...")
            try:
                result = make_token(
                    db=db,
                    movie_name = movie_name,
                    actor_name=actor,
                    speaker=s3_data,
                    s3_textgrid_url=s3_textgrid_url if s3_textgrid_url else "",
                    s3_pitch_url=s3_pitch_url if s3_pitch_url else "",
                    s3_bgvoice_url=s3_bgvoice_url,
                )
                if result:
                    print(f"✅ 데이터베이스 저장 성공: Token ID={result.id}")
                else:
                    print("❌ 데이터베이스 저장 실패")
            except Exception as e:
                print(f"❌ 데이터베이스 저장 중 오류: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ 배경음성 파일이 업로드되지 않아 데이터베이스 저장을 건너뜁니다.")
            print("   필요한 파일들:")
            print(f"   - TextGrid: {s3_textgrid_path} ({'존재' if os.path.exists(s3_textgrid_path) else '없음'})")
            print(f"   - Pitch: {s3_pitchdata_path} ({'존재' if os.path.exists(s3_pitchdata_path) else '없음'})")
            print(f"   - 배경음성: {s3_bgvoice_path} ({'존재' if os.path.exists(s3_bgvoice_path) else '없음'})")

    print("🎯 TextGrid 기반 토큰 생성 중...")


    # audio = AudioSegment.from_file(no_vocals_path, format="mp3")


    # amplified = audio + 6 
    # amplified.export("amplified_output.mp3", format="mp3")

    # amplified.export(no_vocals_path,format ='mp3')



    reset_folder("../syncdata/mfa/corpus", "../syncdata/mfa/mfa_output")
    reset_folder("tmp_frames", "downloads", "separated/htdemucs", "pitch_data", "split_tokens")

# 실행
if __name__ == "__main__":
    main()