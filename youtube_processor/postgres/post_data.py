from .models import Token, Script, ScriptWord, URL, Actor # URL, Actor 모델 import 추가
import time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
import traceback
import numpy as np

def insert_token_with_sentences(db: Session, token_data: dict, sentences_data: list[dict]):
    """
    하나의 Token과 그에 속한 여러 ScriptSentence를 데이터베이스에 저장합니다.
    """
    try:
        # Token 객체 생성
        new_token = Token(**token_data)

        # Token 먼저 세션에 추가
        db.add(new_token)

        
        for sentence_dict in sentences_data:
            words = sentence_dict.pop("words", [])  # 단어 리스트 추출
            sentence = Script(**sentence_dict)
            sentence.token = new_token
            db.add(sentence)

            for word in words:
                word_entry = ScriptWord(
                    word=word["word"].strip(),
                    start_time=word["start"],
                    end_time=word["end"],
                    # probability = float(word.get("probability", 0.0)),  
                    script=sentence  # 관계 연결
                )
                db.add(word_entry)

        print("🎯 Token 데이터:", repr(token_data))
        print("🎯 Sentence 데이터:", [repr(s) for s in sentences_data])

        # 커밋 및 반영
        db.commit()
        db.refresh(new_token)

        print(f"✅ Token 및 문장 삽입 성공: token_id={new_token.id}")
        return new_token

    except Exception as e:
        db.rollback()
        print("❌ 삽입 실패:")
        traceback.print_exc()  # 상세 에러 추적 출력
        return None


def make_token(db: Session, movie_name: str, actor_name: str, speaker: dict,
               s3_textgrid_url: str, s3_pitch_url: str, s3_bgvoice_url: str):
    
    # actor_name 안전장치 - None이나 빈 문자열 방지
    if not actor_name or str(actor_name).strip() == "" or actor_name == "None":
        actor_name = "unknown_actor"
        print(f"⚠️ actor_name이 비어있어서 기본값으로 설정: {actor_name}")
    
    print(f"🔍 make_token 함수 입력값:")
    print(f"  - movie_name: '{movie_name}'")
    print(f"  - actor_name: '{actor_name}' (type: {type(actor_name)})")
    
    # --- Actor 조회 또는 생성 ---
    actor = db.query(Actor).filter(Actor.name == actor_name).first()
    if not actor:
        actor = Actor(name=actor_name)
        db.add(actor)
        db.flush() # Actor ID를 얻기 위해 flush (아직 commit 아님)
        print(f"✅ 새로운 Actor 생성: {actor_name} (ID: {actor.id})")
    else:
        print(f"✅ 기존 Actor 사용: {actor_name} (ID: {actor.id})")

    # --- URL 조회 또는 생성 ---
    youtube_url_str = speaker["video_url"]
    url_entry = db.query(URL).filter(URL.youtube_url == youtube_url_str).first()
    if not url_entry:
        url_entry = URL(youtube_url=youtube_url_str, actor_id=actor.id)
        db.add(url_entry)
        db.flush() # URL ID를 얻기 위해 flush (아직 commit 아님)
        print(f"✅ 새로운 URL 생성: {youtube_url_str}")
    else:
        print(f"✅ 기존 URL 사용: {youtube_url_str}")


    token_data = {
        "token_name": movie_name if movie_name is not None else "", # None 대신 빈 문자열
        "actor_name": actor_name if actor_name is not None else "", # None 대신 빈 문자열
        "category": "스릴러",
        "start_time": float(speaker["start_time"]),
        "end_time": float(speaker["end_time"]),
        "s3_textgrid_url": s3_textgrid_url,
        "s3_pitch_url": s3_pitch_url,
        "s3_bgvoice_url": s3_bgvoice_url,
        "youtube_url": youtube_url_str # URL 객체 대신 문자열 사용
        # view_count는 models.py에 default=0이므로 명시적으로 추가할 필요 없음
    }

    sentences_data = []
    for seg in speaker.get("segments", []):
        try:
            script_clean = seg["text"].encode("utf-8", errors="replace").decode("utf-8")
            sentence_entry = {
                "script": script_clean,
                'start_time': float(seg['start']),
                'end_time': float(seg['end']),
                "words": seg.get("words", [])
            }
            sentences_data.append(sentence_entry)
        except Exception as e:
            print(f"❌ 문장 인코딩 실패: {repr(seg['text'])}")
            traceback.print_exc()

    return insert_token_with_sentences(db, token_data, sentences_data)
