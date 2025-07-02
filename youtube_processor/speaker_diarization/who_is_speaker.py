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
