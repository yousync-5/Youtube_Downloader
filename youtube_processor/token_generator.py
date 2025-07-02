"""
토큰 생성 모듈

YouTube 처리 결과를 토큰 형태로 생성하는 기능을 제공.
토큰은 DB 스키마와 독립적인 중간 데이터 구조로 설계됨.
"""

from pathlib import Path
from config import TOKEN_DATA_DIR
from utils import sanitize_filename
    



def make_token(youtube_url, segments, movie_name=None, actor_name=None):
    """
    유연한 토큰 생성 - 스키마 변경에 대응 가능
    
    Args:
        youtube_url (str): YouTube URL
        segments (list): Whisper로 추출한 음성 인식 세그먼트들
        movie_name (str, optional): 영화 이름
        actor_name (str, optional): 배우 이름
    
    Returns:
        dict: 생성된 토큰
        {
            "url": str,
            "actor_name": str,
            "movie_name": str,
            "segments": [
                {
                    "start_time": float,
                    "end_time": float,
                    "script": str
                }
            ],
            "metadata": {
                "total_segments": int,
                "total_duration": float,
                "all_dialogue": str
            }
        }
    """
    
    # 유효한 세그먼트만 필터링
    valid_segments = [seg for seg in segments if seg.get('text', '').strip()]
    
    # 토큰 구조 생성
    token = {
        # 핵심 데이터 (변경 가능성 낮음)
        "url": youtube_url,
        "actor_name": actor_name or "Unknown Actor", 
        "movie_name": movie_name or "Unknown Movie",
        
        # 세그먼트 데이터 (DB Script 테이블의 기본 구조)
        "segments": [
            {
                "start_time": seg.get('start', 0),
                "end_time": seg.get('end', 0),
                "script": seg.get('text', '').strip()
            }
            for seg in valid_segments
        ],
        
        # 메타데이터 (통계/요약 정보)
        "metadata": {
            "total_segments": len(valid_segments),
            "total_duration": valid_segments[-1].get('end', 0) - valid_segments[0].get('start', 0) if valid_segments else 0,
            "all_dialogue": " ".join([seg.get('text', '').strip() for seg in valid_segments])
        }
    }
    
    print(f"  토큰 생성 완료:")
    print(f"  - URL: {youtube_url}")
    print(f"  - 영화: {token['movie_name']}")
    print(f"  - 배우: {token['actor_name']}")
    print(f"  - 세그먼트 수: {token['metadata']['total_segments']}")
    print(f"  - 총 길이: {token['metadata']['total_duration']:.2f}초")
    
    return token

def validate_token(token):
    """
    토큰 유효성 검사
    
    Args:
        token (dict): 검사할 토큰
    
    Returns:
        bool: 유효성 여부
    """
    required_fields = ['url', 'actor_name', 'movie_name', 'segments', 'metadata']
    
    # 필수 필드 확인
    for field in required_fields:
        if field not in token:
            print(f" 토큰 검증 실패: '{field}' 필드 누락")
            return False
    
    # 세그먼트 구조 확인
    if not isinstance(token['segments'], list):
        print(" 토큰 검증 실패: 'segments'가 리스트가 아님")
        return False
    
    # 각 세그먼트 구조 확인
    for i, seg in enumerate(token['segments']):
        required_seg_fields = ['start_time', 'end_time', 'script']
        for field in required_seg_fields:
            if field not in seg:
                print(f" 토큰 검증 실패: 세그먼트 {i}에서 '{field}' 필드 누락")
                return False
    
    print(" 토큰 검증 성공")
    return True

def save_token_to_file(token, filepath):
    """
    토큰을 JSON 파일로 저장
    
    Args:
        token (dict): 저장할 토큰
        filepath (str): 저장할 파일 경로
    
    Returns:
        bool: 저장 성공 여부
    """
    import json
    from pathlib import Path
    
    try:
        # 디렉토리 생성
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # JSON으로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(token, f, ensure_ascii=False, indent=2)
        
        print(f" 토큰 저장 완료: {filepath}")
        return True
        
    except Exception as e:
        print(f" 토큰 저장 실패: {str(e)}")
        return False

def load_token_from_file(filepath):
    """
    JSON 파일에서 토큰 로드
    
    Args:
        filepath (str): 로드할 파일 경로
    
    Returns:
        dict or None: 로드된 토큰 또는 None
    """
    import json
    from pathlib import Path
    
    try:
        if not Path(filepath).exists():
            print(f" 토큰 파일이 존재하지 않음: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            token = json.load(f)
        
        print(f" 토큰 로드 완료: {filepath}")
        return token
        
    except Exception as e:
        print(f" 토큰 로드 실패: {str(e)}")
        return None

def create_token(youtube_url, segments, video_id):
    """
    사용자 입력을 받아 토큰을 생성하고 저장하는 통합 함수
    
    Args:
        youtube_url (str): YouTube URL
        segments (list): Whisper 세그먼트
        video_id (str): 비디오 ID
    
    Returns:
        dict: 생성된 토큰
    """

    print("\n토큰 생성 중...")
    
    # 사용자 입력 받기
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
    
    # 토큰 생성
    token = make_token(youtube_url, segments, movie_name, actor_name)
    
    # 토큰 저장
    TOKEN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    token_filename = f"{sanitize_filename(video_id)}_{sanitize_filename(token['actor_name'])}_{sanitize_filename(token['movie_name'])}_token.json"
    token_filepath = TOKEN_DATA_DIR / token_filename
    
    if save_token_to_file(token, str(token_filepath)):
        return token
    else:
        print("토큰 저장 실패")
        return None

if __name__ == "__main__":
    print("토큰 생성 모듈")
    print("사용 방법:")
    print("from token_generator import make_token, create_token")
    print("token = make_token(youtube_url, segments, movie_name, actor_name)")
    print("token = create_token(youtube_url, segments, video_id)")
