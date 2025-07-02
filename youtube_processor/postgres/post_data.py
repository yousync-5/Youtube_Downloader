from .models import Token, ScriptSentence, ScriptWord
from sqlalchemy.orm import Session
import traceback  # ← 에러 출력용
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
            sentence = ScriptSentence(**sentence_dict)
            sentence.token = new_token
            db.add(sentence)

            for word in words:
                word_entry = ScriptWord(
                    word=word["word"].strip(),
                    start_time=word["start"],
                    end_time=word["end"],
                    # probability = float(word.get("probability", 0.0)),  
                    sentence=sentence  # 관계 연결
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


def make_token(db: Session, actor_name: str, speaker: dict,
               s3_textgrid_url: str, s3_pitch_url: str, s3_bgvoice_url: str):
    token_data = {
        "token_name": "확인용",
        "actor_name": actor_name,
        "category": "스릴러",  # 만약 Token 모델에 'category' 컬럼이 없으면 이 줄 삭제 필요
        "start_time": float(speaker["start_time"]),  # numpy → float 변환
        "end_time": float(speaker["end_time"]),
        "s3_textgrid_url": s3_textgrid_url,
        "s3_pitch_url": s3_pitch_url,
        "s3_bgvoice_url": s3_bgvoice_url,
        "youtube_url": speaker["video_url"]
    }

    sentences_data = []
    for seg in speaker.get("segments", []):
        try:
            script_clean = seg["text"].encode("utf-8", errors="replace").decode("utf-8")
            sentence_entry = {
                "script": script_clean,
                'start_time': float(np.float64(3.98)),       # 🔧 반드시 float() 처리
                'end_time': float(np.float64(24.66)),
                "words": seg.get("words", [])
            }
            sentences_data.append(sentence_entry)
        except Exception as e:
            print(f"❌ 문장 인코딩 실패: {repr(seg['text'])}")
            traceback.print_exc()

    return insert_token_with_sentences(db, token_data, sentences_data)
