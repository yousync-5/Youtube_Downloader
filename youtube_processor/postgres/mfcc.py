# import librosa
# import numpy as np
# from pathlib import Path
# from sklearn.metrics.pairwise import cosine_similarity

# def extract_mfcc_from_audio(audio_path: str, sr: int = 16000) -> tuple[np.ndarray, np.ndarray]:
#     """
#     음성에서 mfcc를 추출하는 함수
#     """
#     y, _ = librosa.load(audio_path, sr=sr)

#     mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
#     mfcc = mfcc.T

#     duration = librosa.get_duration(y=y, sr=sr)
#     n_frames = mfcc.shape[0]
#     frame_times = np.linspace(0, duration, num=n_frames)

#     return mfcc, frame_times

# def extract_mfcc_segment(mfcc: np.ndarray, frame_times: np.ndarray, start_time: float, end_time: float) -> np.ndarray:
#     """
#     시작, 끝 시간을 입력 받아 mfcc 행렬을 추출
#     """
#     start_idx = np.searchsorted(frame_times, start_time, side = "left")
#     end_idx = np.searchsorted(frame_times, end_time, side = "right")

#         # 🔻 보정: 비어 있으면 한 프레임이라도 포함
#     if end_idx <= start_idx:
#         end_idx = min(start_idx + 1, mfcc.shape[0])

    
#     return mfcc[start_idx:end_idx]

import librosa
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

def extract_mfcc_from_audio(audio_path: str, sr: int = 16000, start_time_offset: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """
    음성에서 mfcc를 추출하는 함수
    """
    print(f"[MFCC_DEBUG] extract_mfcc_from_audio 시작 - 파일: {audio_path}")
    
    y, _ = librosa.load(audio_path, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc = mfcc.T

    duration = librosa.get_duration(y=y, sr=sr)
    n_frames = mfcc.shape[0]
    frame_times = np.linspace(0, duration, num=n_frames)
    
    # start_time_offset이 있으면 frame_times 조정
    if start_time_offset > 0:
        frame_times = frame_times + start_time_offset
        print(f"[MFCC_DEBUG] frame_times 조정: +{start_time_offset}초 추가")
        print(f"[MFCC_DEBUG] 조정된 frame_times 범위: {frame_times[0]:.3f}~{frame_times[-1]:.3f}초")

    print(f"[MFCC_DEBUG] MFCC 추출 완료 - shape: {mfcc.shape}, 길이: {duration:.3f}초")
    return mfcc, frame_times

def extract_mfcc_segment(mfcc: np.ndarray, frame_times: np.ndarray, start_time: float, end_time: float) -> np.ndarray:
    """
    시작, 끝 시간을 입력 받아 mfcc 행렬을 추출
    """
    print(f"[MFCC_DEBUG] segment 추출 - 시간: {start_time:.3f}~{end_time:.3f}초")
    
    start_idx = np.searchsorted(frame_times, start_time, side = "left")
    end_idx = np.searchsorted(frame_times, end_time, side = "right")
    
    print(f"[MFCC_DEBUG] 인덱스: {start_idx}~{end_idx}, 결과 shape: {mfcc[start_idx:end_idx].shape}")
    return mfcc[start_idx:end_idx]


def compare_mfcc_segments(cached_segments: list[dict], user_mfcc: np.ndarray, user_frame_times: np.ndarray) -> list[dict]:
    """
    기준 음성의 mfcc 행렬과 유저 음성의 mfcc 행렬을 서로 비교하여 유사도 점수를 계산
    """
    print(f"[MFCC_DEBUG] compare_mfcc_segments 시작 - 세그먼트 수: {len(cached_segments)}")
    print(f"[MFCC_DEBUG] user_mfcc shape: {user_mfcc.shape}")
    
    results = []

    # 모든 세그먼트에 대해 반복     
    for i, segment in enumerate(cached_segments):
        word = segment["word"]
        start = segment["start_time"]
        end = segment["end_time"]
        
        print(f"[MFCC_DEBUG] === {i+1}번째 단어: '{word}' ({start}~{end}초) ===")
        
        if segment["mfcc"] is None:
            print(f"[MFCC_DEBUG] '{word}': 기준 MFCC가 None → similarity = 0.0")
            similarity = 0.0
        else:
            ref_mfcc = np.array(segment["mfcc"])
            user_segment = extract_mfcc_segment(user_mfcc, user_frame_times, start, end)

            print(f"[MFCC_DEBUG] '{word}': 기준 MFCC shape = {ref_mfcc.shape}")
            print(f"[MFCC_DEBUG] '{word}': 유저 segment shape = {user_segment.shape}")

            if ref_mfcc.shape[0] == 0 or user_segment.shape[0] == 0:
                print(f"[MFCC_DEBUG] '{word}': 빈 세그먼트 감지 → similarity = 0.0")
                similarity = 0.0
            else:
                ref_avg = np.mean(ref_mfcc, axis = 0, keepdims=True)
                user_avg = np.mean(user_segment, axis = 0, keepdims=True)
                
                print(f"[MFCC_DEBUG] '{word}': ref_avg shape = {ref_avg.shape}")
                print(f"[MFCC_DEBUG] '{word}': user_avg shape = {user_avg.shape}")
                
                similarity = cosine_similarity(ref_avg, user_avg)[0][0]
                print(f"[MFCC_DEBUG] '{word}': cosine similarity = {similarity:.6f}")
        
        results.append({
            "word": word,
            "similarity": similarity
        })

    print(f"[MFCC_DEBUG] compare_mfcc_segments 완료 - 결과 수: {len(results)}")
    return results