import os
import numpy as np
import face_recognition

# 세그먼트 ID에 해당하는 3장 프레임에서 평균 인코딩 추출
def get_segment_encoding(segment_id: int, folder="tmp_frames"):
    encodings = []
    for i in range(1, 4):  # _1.jpg, _2.jpg, _3.jpg
        path = os.path.join(folder, f"{segment_id:03d}_{i}.jpg")
        if not os.path.exists(path):
            continue

        image = face_recognition.load_image_file(path)
        faces = face_recognition.face_encodings(image)

        if faces:
            encodings.append(faces[0])
        else:
            print(f"⚠️ 세그먼트 {segment_id}, 프레임 {i}에서 얼굴 인식 실패")

    if not encodings:
        return None  # 얼굴 없음

    return np.mean(encodings, axis=0)

# 전체 세그먼트들에 대해 화자 분석 수행
def analyze_speakers(num_segments: int, folder="tmp_frames", threshold=0.6):
    segment_encodings = []

    for i in range(num_segments):
        encoding = get_segment_encoding(i, folder)
        segment_encodings.append(encoding)

        # 1️⃣ 동일 세그먼트 내 프레임 간 유사도 확인
        if encoding is not None:
            self_distances = []
            for j in range(1, 4):
                path = os.path.join(folder, f"{i:03d}_{j}.jpg")
                if not os.path.exists(path):
                    continue
                image = face_recognition.load_image_file(path)
                faces = face_recognition.face_encodings(image)
                if faces:
                    dist = np.linalg.norm(faces[0] - encoding)
                    self_distances.append(dist)

            if self_distances:
                avg_dist = np.mean(self_distances)
                print(f"🧩 세그먼트 {i}: 내부 유사도 평균 거리 = {avg_dist:.3f}")
                if avg_dist > 0.6:
                    print(f"   ⚠️ 같은 문장 안에서도 서로 다른 인물일 가능성 있음")

        # 2️⃣ 이전 세그먼트와 비교
        if i > 0 and segment_encodings[i - 1] is not None and encoding is not None:
            dist = np.linalg.norm(segment_encodings[i - 1] - encoding)
            same = dist < threshold
            print(f"👥 세그먼트 {i-1} ↔ {i} → {'✅ 같은 화자' if same else '❌ 다른 화자'} (거리: {dist:.3f})")

# 외부에서 호출 가능하도록 함수 노출
__all__ = ["analyze_speakers"]

def cluster_speakers(segment_encodings, threshold=0.6):
    """
    모든 세그먼트의 얼굴 인코딩을 분석하여 화자 그룹을 생성합니다.
    """
    speakers = []  # 화자 그룹들
    speaker_labels = []  # 각 세그먼트의 화자 라벨
    
    for i, encoding in enumerate(segment_encodings):
        if encoding is None:
            speaker_labels.append("UNKNOWN")
            continue
            
        # 기존 화자 그룹과 비교
        assigned = False
        for j, speaker_group in enumerate(speakers):
            # 해당 그룹의 대표 인코딩과 비교
            if np.linalg.norm(speaker_group['encoding'] - encoding) < threshold:
                speaker_labels.append(f"SPEAKER_{j}")
                assigned = True
                break
        
        # 새로운 화자 그룹 생성
        if not assigned:
            speakers.append({'encoding': encoding, 'segments': [i]})
            speaker_labels.append(f"SPEAKER_{len(speakers)-1}")
    
    return speaker_labels, speakers

def analyze_speakers_with_clustering(num_segments, folder="tmp_frames", threshold=0.6):
    """
    얼굴 기반 화자분리를 수행하고, 전체 세그먼트를 화자별로 분류합니다.
    """
    print(f"🧑‍🤝‍🧑 얼굴 기반 화자분리 시작 (세그먼트 {num_segments}개)")
    
    # 1. 모든 세그먼트의 얼굴 인코딩 추출
    segment_encodings = []
    for i in range(num_segments):
        encoding = get_segment_encoding(i, folder)
        segment_encodings.append(encoding)
        if encoding is not None:
            print(f"✅ 세그먼트 {i}: 얼굴 인코딩 추출 성공")
        else:
            print(f"❌ 세그먼트 {i}: 얼굴 인코딩 추출 실패")
    
    # 2. 화자 클러스터링
    speaker_labels, speakers = cluster_speakers(segment_encodings, threshold)
    
    # 3. 결과 출력
    print(f"\n🎭 총 {len(speakers)}명의 화자 발견:")
    for i, speaker in enumerate(speakers):
        print(f"   SPEAKER_{i}: {len(speaker['segments'])}개 세그먼트")
    
    return speaker_labels, speakers

def print_speaker_dialogue(segments, speaker_labels):
    """
    화자별로 분류된 대사를 출력합니다.
    """
    print(f"\n🗣️ 화자별 대사 분류:")
    print("=" * 50)
    
    current_speaker = None
    for i, (seg, label) in enumerate(zip(segments, speaker_labels)):
        if label != current_speaker:
            current_speaker = label
            print(f"\n👤 {label}:")
        
        print(f"   [{seg['start']:.1f}s-{seg['end']:.1f}s] {seg['text']}")
    
    print("=" * 50)
