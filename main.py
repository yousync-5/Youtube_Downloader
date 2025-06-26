import face_recognition
import os
base_dir = "youtube_processor"
sub_dir = "tmp_frames"
filename = "002_2.jpg"

full_path = os.path.join(base_dir, sub_dir, filename)

image = face_recognition.load_image_file(full_path)
face_locations = face_recognition.face_locations(image)

print(f"총 {len(face_locations)}명의 얼굴을 감지했습니다.")