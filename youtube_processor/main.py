import os
from downloader import download_audio, download_video
from transcriber import transcribe_audio
from frame_extractor import extract_frames_per_segment
from demucs_wrapper import separate_vocals
from who_is_speaker import analyze_speakers
from voice_analyzer import analyze_voice_speakers
from export_for_mfa import export_segments_for_mfa
from voice_to_pitch import create_pitch_json_with_token  # 직접 호출로 변경
from utils import sanitize_filename  # 이미 있다면 생략 가능
from utils import extract_video_id
import time

def make_token(youtube_url, segments, movie_name=None, actor_name=None):
    """
    토큰 생성 함수 (가제)
    
    Args:
        youtube_url (str): YouTube URL
        segments (list): 음성 인식 결과 세그먼트들
        movie_name (str, optional): 영화 이름
        actor_name (str, optional): 배우 이름
    
    Returns:
        dict: 생성된 토큰
    """
    
    # 모든 대사를 하나로 합치기
    all_dialogue = " ".join([seg.get('text', '').strip() for seg in segments if seg.get('text')])
    
    # 토큰 구조 생성
    token = {
        "url": youtube_url,
        "actor_name": actor_name or "Unknown Actor",
        "movie_name": movie_name or "Unknown Movie", 
        "segments": [
            {
                "text": seg.get('text', '').strip(),
                "start": seg.get('start', 0),
                "end": seg.get('end', 0)
            }
            for seg in segments if seg.get('text')
        ],
        "all_dialogue": all_dialogue,
        "total_segments": len(segments),
        "total_duration": segments[-1].get('end', 0) - segments[0].get('start', 0) if segments else 0
    }
    
    print(f"🎯 토큰 생성 완료:")
    print(f"  - URL: {youtube_url}")
    print(f"  - 영화: {token['movie_name']}")
    print(f"  - 배우: {token['actor_name']}")
    print(f"  - 세그먼트 수: {token['total_segments']}")
    print(f"  - 총 길이: {token['total_duration']:.2f}초")
    
    return token

def main():

    # 1. 유튜브 데이터 

    # 1-1 URL 저장
    youtube_url = input("📺 URL 입력을 바랍니다.: ").strip()

    start_time = time.time()  # ⏱️ 시작 시간

    # 1-2 비디오 ID/FileName 추출
    video_id = extract_video_id(youtube_url)
    video_filename = sanitize_filename(video_id)

    # 1-3 폴더 경로지정
    mp4_path = os.path.join("downloads", video_filename + ".mp4")

    # 1-4 오디오 추출 및 파일 경로 반환 
    mp3_path, _ = download_audio(youtube_url, video_id, video_filename)

    # 1-5 영상이 없을 시 다운로드 실행
    if not os.path.exists(mp4_path):
        download_video(youtube_url, mp4_path)
    else:
        print(f"✅ 영상 파일 이미 존재: {mp4_path}")




    # 2. 데이터 추출

    # 2-1  Demucs로 보컬 추출
    vocal_path = separate_vocals(mp3_path)

    # 2-2  Whisper로 자막 추출
    segments = transcribe_audio(vocal_path)

    # 가만 생각해보면 textgrid 정보가 훨씬 상세하다. 그렇다면 여기서 이러는게
    #아니라 mfa에 보내서 데이터를 받고 여기로 데려오는 편이 좋겠다. 


    if not segments:
        print("❌ No speech detected.")
        return

    selected = segments[:]
    print("\n🗣️ First 5 segments:")
    for seg in selected:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")




    #화자 분석은 나중에 한다. 

    # # 🖼️ 프레임 추출
    # extract_frames_per_segment(mp4_path, selected)

    # # 😎 얼굴 기반 화자 분석


    # print("\n🔍 얼굴 기반 화자 분석:")
    # analyze_speakers(num_segments=len(selected), folder="tmp_frames")

    
    elapsed = time.time() - start_time  # ⏱️ 소요 시간
    print(f"🕒 URL 전처리 소요 시간: {elapsed:.2f}초")

    # 3. 토큰 생성 (새로 추가)
    print("\n🎯 토큰 생성 중...")
    
    # 사용자로부터 영화명과 배우명 입력받기 (임시)
    movie_name = input("🎬 영화 이름을 입력하세요 (선택사항): ").strip() or None
    actor_name = input("🎭 배우 이름을 입력하세요 (선택사항): ").strip() or None
    
    token = make_token(youtube_url, segments, movie_name, actor_name)

    # 4. 피치 분석 (토큰 생성 직후)
    print("\n🎵 피치 분석 시작...")
    pitch_json_path = create_pitch_json_with_token(vocal_path, token)
    
    if pitch_json_path:
        print(f"✅ 피치 분석 및 토큰 정보 저장 완료: {pitch_json_path}")
    else:
        print("❌ 피치 분석 실패")

    #화자 분석은 나중에 한다. 

    # 🎧 음성 기반 화자 분석
    # print("\n🧠 음성 기반 화자 분석:")
    # analyze_voice_speakers(vocal_path, selected)

    # 🔡 MFA용 세그먼트 내보내기
    print("\n📦 MFA용 음성/텍스트 export:")
    export_segments_for_mfa(vocal_path, segments, output_base=r"../syncdata/mfa/corpus")
    
    

if __name__ == "__main__":
    main()
