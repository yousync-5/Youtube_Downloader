"""
프로젝트 구조:
Youtube_Downloader/
├── separated/              # 기준 음성 (Demucs 처리 결과)
│   └── vocals.wav
├── user_uploads/           # 유저 음성 업로드 폴더
│   └── user_audio.wav
├── pitch_data/             # 피치 분석 결과 저장
│   ├── reference/          # 기준 음성 피치 JSON
│   │   └── Movie_Actor_pitch.json
│   └── user/              # 유저 음성 피치 JSON
│       └── user123_video456_pitch.json
└── youtube_processor/      # 처리 스크립트들

주요 기능:
1. create_pitch_json_with_token(): 토큰 기반 기준 음성 피치 분석
2. create_user_pitch_json(): 유저 음성 피치 분석

출력 JSON 형식:
[
  {"time": 0.025, "hz": null},
  {"time": 0.035, "hz": 152.34},
  {"time": 0.045, "hz": 148.76}
]
"""

import sys
import parselmouth
import json
import numpy as np
from pathlib import Path
from config import PITCH_REFERENCE_DIR, PITCH_USER_DIR, USER_UPLOADS_DIR
from utils import extract_video_id, sanitize_filename

def create_pitch_json_with_token(vocal_path, speaker):
    """
    토큰 정보를 기반으로 기준 음성의 피치 JSON 생성 (기준 음성용)
    Args:
        vocal_path (str): 배경음이 제거된 음성 파일 경로
        token (dict): 생성된 토큰 데이터
    Returns:
        str: 생성된 피치 JSON 파일 경로
    """
    print("[DEBUG] create_pitch_json_with_token 진입")
    print(f"[DEBUG] speaker: {speaker}")
    print(f"[DEBUG] vocal_path: {vocal_path}")
    try:
        # 기준 음성 피치 디렉토리 생성
        PITCH_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        safe_actor_name = sanitize_filename(speaker['actor'])
        safe_url = extract_video_id(speaker['video_url'])
        output_filename = f"{safe_actor_name}_{safe_url}_{speaker['token_id']}pitch.json"
        output_path = PITCH_REFERENCE_DIR / output_filename
        print(f"[DEBUG] output_path: {output_path}")
        print(f"기준 음성 피치 분석: {vocal_path}")
        print(f"출력 파일: {output_path}")
        # 오디오 파일 로드
        snd = parselmouth.Sound(vocal_path)
        print(f"오디오 정보: {snd.duration:.2f}초, {snd.sampling_frequency}Hz")
        pitch = snd.to_pitch(time_step=0.1)
        print(f"피치 프레임 수: {pitch.get_number_of_frames()}")
        pitch_data = []
        for i in range(pitch.get_number_of_frames()):
            frame_number = i + 1
            time = pitch.get_time_from_frame_number(frame_number)
            hz = pitch.get_value_at_time(time)
            if hz == 0 or np.isnan(hz):
                hz = None
            else:
                hz = round(hz, 2)
            pitch_data.append({
                "time": round(time, 3),
                "hz": hz
            })
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(pitch_data, f, ensure_ascii=False, indent=2)
        print(f"기준 음성 피치 분석 완료: {len(pitch_data)} 데이터 포인트")
        valid_pitches = [p["hz"] for p in pitch_data if p["hz"] is not None]
        if len(valid_pitches) > 0:
            print(f"유효한 피치 포인트: {len(valid_pitches)}/{len(pitch_data)}")
            print(f"[DEBUG] pitch json 파일 생성 성공: {output_path}, exists: {output_path.exists()}")
            return str(output_path)
        else:
            print("유효한 피치 데이터가 없습니다.")
            print(f"[DEBUG] pitch json 파일 생성 실패: {output_path}, exists: {output_path.exists()}")
            return None
    except Exception as e:
        print(f"[ERROR] 기준 음성 피치 분석 중 오류: {str(e)}")
        print(f"[DEBUG] speaker: {speaker}")
        print(f"[DEBUG] vocal_path: {vocal_path}")
        print(f"[DEBUG] output_path: {output_path if 'output_path' in locals() else 'N/A'}")
        return None

def create_user_pitch_json(user_audio_filename, user_id, dubbing_video_id):
    """
    유저 음성의 피치 JSON 생성 (유저 음성용)
    
    Args:
        user_audio_filename (str): 유저 업로드 폴더의 음성 파일명
        user_id (str): 유저 ID
        dubbing_video_id (str): 더빙 영상 ID
    
    Returns:
        str: 생성된 피치 JSON 파일 경로
    """
    
    try:
        # 유저 음성 파일 경로 구성
        user_vocal_path = USER_UPLOADS_DIR / user_audio_filename
        
        # 파일 존재 확인
        if not user_vocal_path.exists():
            print(f"유저 음성 파일을 찾을 수 없습니다: {user_vocal_path}")
            return None
        
        # 유저 음성 피치 디렉토리 생성
        PITCH_USER_DIR.mkdir(parents=True, exist_ok=True)
        
        # 유저 음성 파일명 생성: 유저id_더빙영상id_pitch.json
        output_filename = f"{user_id}_{dubbing_video_id}_pitch.json"
        
        # 유저 음성 전용 경로
        output_path = PITCH_USER_DIR / output_filename
        
        print(f"유저 음성 피치 분석: {user_vocal_path}")
        print(f"출력 파일: {output_path}")
        
        # 오디오 파일 로드
        snd = parselmouth.Sound(str(user_vocal_path))
        print(f"오디오 정보: {snd.duration:.2f}초, {snd.sampling_frequency}Hz")
        
        # 피치 추출
        pitch = snd.to_pitch(time_step=0.01)
        print(f"피치 프레임 수: {pitch.get_number_of_frames()}")
        
        pitch_data = []
        
        # 피치 데이터 추출
        for i in range(pitch.get_number_of_frames()):
            frame_number = i + 1
            time = pitch.get_time_from_frame_number(frame_number)
            hz = pitch.get_value_at_time(time)
            
            # 0이거나 NaN인 경우 None으로 처리
            if hz == 0 or np.isnan(hz):
                hz = None
            else:
                hz = round(hz, 2)
            
            pitch_data.append({
                "time": round(time, 3), 
                "hz": hz
            })
        
        # JSON으로 저장
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(pitch_data, f, ensure_ascii=False, indent=2)
        
        print(f"유저 음성 피치 분석 완료: {len(pitch_data)} 데이터 포인트")
        
        # 간단한 검증
        valid_pitches = [p["hz"] for p in pitch_data if p["hz"] is not None]
        if len(valid_pitches) > 0:
            print(f"유효한 피치 포인트: {len(valid_pitches)}/{len(pitch_data)}")
            return str(output_path)
        else:
            print("유효한 피치 데이터가 없습니다.")
            return None
            
    except Exception as e:
        print(f"유저 음성 피치 분석 중 오류: {str(e)}")
        return None

if __name__ == "__main__":
    print("이 파일은 직접 실행할 수 없습니다.")
    print("사용 방법:")
    print("기준 음성: create_pitch_json_with_token(vocal_path, token)")
    print("유저 음성: create_user_pitch_json('user_audio.wav', 'user123', 'video456')")
