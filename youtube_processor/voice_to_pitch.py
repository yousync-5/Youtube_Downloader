import sys
import parselmouth
import json
import numpy as np
from pathlib import Path
from config import PITCH_DATA_DIR

# 10ms의 time_step = 0.01
def extract_pitch_to_json(wav_path, output_json_path="pitch.json", time_step=0.01):
    """
    WAV 파일에서 피치 정보를 추출하여 JSON으로 저장
    
    Args:
        wav_path: 입력 WAV 파일 경로
        output_json_path: 출력 JSON 파일 경로
        time_step: 피치 분석 시간 간격 (초)
    """
    print(f"🎵 피치 분석 시작: {wav_path}")
    
    try:
        # 오디오 파일 로드
        snd = parselmouth.Sound(wav_path)
        print(f"📊 오디오 정보: {snd.duration:.2f}초, {snd.sampling_frequency}Hz")
        
        # 피치 추출
        pitch = snd.to_pitch(time_step=time_step)
        print(f"📈 피치 프레임 수: {pitch.get_number_of_frames()}")
        
        pitch_data = []
        
        # 최신 Parselmouth API 사용
        for i in range(pitch.get_number_of_frames()):
            # 프레임 번호는 1부터 시작
            frame_number = i + 1
            
            # 시간 정보 추출
            time = pitch.get_time_from_frame_number(frame_number)
            
            # 피치 값 추출 (최신 API)
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
        
        # JSON 파일로 저장
        with open(output_json_path, "w", encoding='utf-8') as f:
            json.dump(pitch_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 피치 데이터 저장 완료: {output_json_path}")
        print(f"📊 총 데이터 포인트: {len(pitch_data)}")
        
        # 통계 정보 출력
        valid_pitches = [p["hz"] for p in pitch_data if p["hz"] is not None]
        if valid_pitches:
            print(f"📈 피치 통계:")
            print(f"  - 유효한 피치 포인트: {len(valid_pitches)}/{len(pitch_data)}")
            print(f"  - 최소 피치: {min(valid_pitches):.2f} Hz")
            print(f"  - 최대 피치: {max(valid_pitches):.2f} Hz")
            print(f"  - 평균 피치: {np.mean(valid_pitches):.2f} Hz")
        else:
            print("⚠️  유효한 피치 데이터가 없습니다.")
        
        return pitch_data
        
    except Exception as e:
        print(f"❌ 피치 추출 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_pitch_json_with_token(vocal_path, token, output_filename=None):
    """
    토큰 정보를 포함한 피치 JSON 생성 함수
    
    Args:
        vocal_path (str): 배경음이 제거된 음성 파일 경로
        token (dict): 생성된 토큰 데이터
        output_filename (str, optional): 출력 파일명 (기본값: 자동 생성)
    
    Returns:
        str: 생성된 피치 JSON 파일 경로
    """
    
    try:
        # 피치 데이터 디렉토리 생성
        PITCH_DATA_DIR.mkdir(exist_ok=True)
        
        # 출력 파일명 생성
        if output_filename is None:
            # 토큰 정보를 기반으로 파일명 생성
            movie_name = token.get('movie_name', 'unknown_movie')
            actor_name = token.get('actor_name', 'unknown_actor')
            # 파일명에 사용할 수 없는 문자 제거
            safe_movie = "".join(c for c in movie_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_actor = "".join(c for c in actor_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"{safe_movie}_{safe_actor}_pitch.json"
        
        # 출력 파일 경로
        output_path = PITCH_DATA_DIR / output_filename
        
        print(f"🎵 토큰 기반 피치 분석 시작: {vocal_path}")
        print(f"📁 출력 파일: {output_path}")
        
        # 피치 데이터 추출
        pitch_data = extract_pitch_to_json(
            wav_path=vocal_path,
            output_json_path=str(output_path),
            time_step=0.01  # 10ms 간격
        )
        
        if pitch_data:
            print(f"✅ 피치 분석 완료: {len(pitch_data)} 데이터 포인트 생성")
            
            # 토큰 정보를 포함한 향상된 데이터 구조 생성
            enhanced_data = {
                "token_info": {
                    "url": token.get('url', ''),
                    "movie_name": token.get('movie_name', ''),
                    "actor_name": token.get('actor_name', ''),
                    "total_segments": len(token.get('segments', [])),
                    "total_dialogue": token.get('all_dialogue', ''),
                    "total_duration": token.get('total_duration', 0)
                },
                "pitch_data": pitch_data,
                "analysis_info": {
                    "vocal_file": vocal_path,
                    "time_step": 0.01,
                    "total_data_points": len(pitch_data)
                }
            }
            
            # 향상된 데이터로 다시 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 토큰 정보 포함 저장 완료: {output_path}")
            
            # 데이터 검증
            valid_pitches = [p["hz"] for p in pitch_data if p["hz"] is not None]
            validation_result = {
                "is_valid": len(valid_pitches) > 0,
                "total_points": len(pitch_data),
                "valid_points": len(valid_pitches),
                "validity_ratio": len(valid_pitches) / len(pitch_data) if pitch_data else 0
            }
            
            print(f"📊 데이터 검증 결과:")
            print(f"  - 총 데이터 포인트: {validation_result['total_points']}")
            print(f"  - 유효한 포인트: {validation_result['valid_points']}")
            print(f"  - 유효성 비율: {validation_result['validity_ratio']:.2%}")
            
            return str(output_path) if validation_result['is_valid'] else None
        else:
            print("❌ 피치 분석 실패")
            return None
            
    except Exception as e:
        print(f"❌ 토큰 기반 피치 분석 중 오류 발생: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python3 voice_to_pitch.py <wav_path>")
        print("예시: python3 voice_to_pitch.py vocals.wav")
        sys.exit(1)

    wav_path = sys.argv[1]
    if not Path(wav_path).is_file():
        print(f"❌ 파일을 찾을 수 없습니다: {wav_path}")
        sys.exit(1)

    # 피치 추출
    pitch_data = extract_pitch_to_json(wav_path)
    
    if pitch_data:
        print(f"\n🎉 완료! JSON 파일을 확인하세요: pitch.json")
    else:
        print("❌ 피치 추출에 실패했습니다.")
