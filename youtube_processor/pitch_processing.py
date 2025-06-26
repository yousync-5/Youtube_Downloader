"""
🎵 피치 비교 및 유사도 분석 모듈 (pitch_processing.py)

📋 목적:
- 기준 음성(더빙 원본)과 사용자 음성의 피치 패턴을 비교 분석
- 세그먼트별로 피치 유사도를 계산하여 발음/억양 평가에 활용
- DTW(Dynamic Time Warping) 알고리즘을 사용한 정밀한 피치 매칭

🔧 주요 기능:
1. 피치 JSON 데이터 로드 및 전처리
2. 시간 구간별 피치 세그먼트 추출
3. Z-score 정규화를 통한 피치 데이터 표준화
4. DTW 거리 계산을 통한 피치 패턴 유사도 측정
5. 세그먼트별 유사도 점수 생성 및 JSON 출력

🎯 사용 시나리오:
- 더빙 연습 앱에서 사용자의 발음/억양 평가
- 기준 배우의 피치 패턴과 학습자 피치 패턴 비교
- 세그먼트별 상세한 피치 유사도 피드백 제공

📊 입력 데이터:
- ref_pitch.json: 기준 음성의 피치 데이터 (voice_to_pitch.py로 생성)
- user_pitch.json: 사용자 음성의 피치 데이터
- segments.json: 대사 세그먼트 정보 (시작/끝 시간, 텍스트)

📈 출력 데이터:
- pitch_score.json: 세그먼트별 피치 유사도 점수 (0.0~1.0)

⚠️ 현재 상태: 미사용 (향후 더빙 평가 시스템에서 활용 예정)
🔗 연관 파일: voice_to_pitch.py (피치 데이터 생성), main.py (토큰 생성)
"""

import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_pitch_segment(pitch_data, start, end):
    return [
        p["hz"] for p in pitch_data
        if p["time"] >= start and p["time"] <= end and p["hz"] is not None
    ]

def zscore_normalize(arr):
    import numpy as np
    arr = np.array(arr)
    mean = np.mean(arr)
    std = np.std(arr)
    return ((arr - mean) / std).tolist() if std > 0 else [0.0] * len(arr)

def compute_dtw_distance(a, b):
    import numpy as np
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    distance, _ = fastdtw(a, b, dist=euclidean)
    return distance

def analyze_pitch_similarity(ref_pitch_path, user_pitch_path, segments_path):
    ref_pitch = load_json(ref_pitch_path)
    user_pitch = load_json(user_pitch_path)
    segments = load_json(segments_path)

    results = []

    for seg in segments:
        start, end, text = seg["start"], seg["end"], seg["text"]

        ref_segment = extract_pitch_segment(ref_pitch, start, end)
        user_segment = extract_pitch_segment(user_pitch, start, end)

        if not ref_segment or not user_segment:
            similarity = None
        else:
            ref_norm = zscore_normalize(ref_segment)
            user_norm = zscore_normalize(user_segment)
            dist = compute_dtw_distance(ref_norm, user_norm)
            similarity = max(0.0, 1.0 - dist / len(ref_norm))  # rough scoring

        results.append({
            "text": text,
            "start": start,
            "end": end,
            "similarity": round(similarity, 3) if similarity is not None else None
        })

    with open("pitch_score.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("✅ pitch_score.json 생성 완료")

if __name__ == "__main__":
    analyze_pitch_similarity(
        ref_pitch_path="ref/pitch.json",
        user_pitch_path="user/pitch.json",
        segments_path="ref/segments.json"
    )