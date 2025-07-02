# compare_speech.py
#!/usr/bin/env python3
import subprocess
import json
import os
import textgrid
import librosa
import numpy as np
from scipy.spatial.distance import cosine

def run_mfa_alignment(corpus_path, dict_path, model_path, output_path):
    """MFA를 사용하여 강제 정렬을 수행합니다."""
    try:
        cmd = [
            "mfa", "align", 
            corpus_path, 
            dict_path, 
            model_path, 
            output_path,
            "--clean"
        ]
        
        print(f"MFA 정렬 실행 중: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("MFA 정렬 완료!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"MFA 정렬 실패: {e}")
        print(f"Error output: {e.stderr}")
        return False

def parse_textgrid(textgrid_path):
    """TextGrid 파일을 파싱하여 음소 정보를 추출합니다."""
    try:
        tg = textgrid.TextGrid.fromFile(textgrid_path)
        
        # 음소 tier 찾기 (보통 'phones' 또는 두 번째 tier)
        phone_tier = None
        for tier in tg.tiers:
            if 'phone' in tier.name.lower() or len(tg.tiers) > 1:
                phone_tier = tier
                break
        
        if phone_tier is None:
            phone_tier = tg.tiers[0]  # 첫 번째 tier 사용
        
        phones = []
        for interval in phone_tier:
            if interval.mark.strip() and interval.mark.strip() != '':
                phones.append({
                    'phone': interval.mark.strip(),
                    'start': interval.minTime,
                    'end': interval.maxTime,
                    'duration': interval.maxTime - interval.minTime
                })
        
        return phones
        
    except Exception as e:
        print(f"TextGrid 파싱 오류: {e}")
        return []

def extract_phone_features(audio_path, phone_info):
    """특정 음소 구간에서 음향 특징을 추출합니다."""
    try:
        y, sr = librosa.load(audio_path)
        
        start_sample = int(phone_info['start'] * sr)
        end_sample = int(phone_info['end'] * sr)
        
        # 음소 구간 추출
        phone_audio = y[start_sample:end_sample]
        
        if len(phone_audio) < 512:  # 너무 짧은 구간 처리
            return None
            
        # MFCC 특징 추출
        mfcc = librosa.feature.mfcc(y=phone_audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)
        
        # 기본 주파수 (F0)
        f0 = librosa.yin(phone_audio, fmin=50, fmax=400)
        f0_mean = np.mean(f0[f0 > 0]) if len(f0[f0 > 0]) > 0 else 0
        
        # 스펙트럴 중심
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=phone_audio, sr=sr))
        
        return {
            'mfcc': mfcc_mean.tolist(),
            'f0_mean': float(f0_mean),
            'spectral_centroid': float(spectral_centroid),
            'duration': phone_info['duration']
        }
        
    except Exception as e:
        print(f"음소 특징 추출 오류: {e}")
        return None

def calculate_text_penalty(ref_text, user_text):
    """텍스트 불일치에 대한 적절한 페널티"""
    ref_words = ref_text.lower().replace(',', '').replace('.', '').split()
    user_words = user_text.lower().replace(',', '').replace('.', '').split()
    
    if len(ref_words) == 0:
        return 0.0
    
    matching_words = 0
    for i, ref_word in enumerate(ref_words):
        if i < len(user_words) and ref_word == user_words[i]:
            matching_words += 1
    
    text_accuracy = matching_words / len(ref_words)
    
    # 더 관대한 텍스트 페널티
    if text_accuracy >= 0.9:    # 90% 이상 정확
        return 1.0              # 페널티 없음
    elif text_accuracy >= 0.7:  # 70% 이상 정확
        return 0.9              # 10% 페널티
    elif text_accuracy >= 0.5:  # 50% 이상 정확
        return 0.7              # 30% 페널티
    elif text_accuracy >= 0.3:  # 30% 이상 정확
        return 0.4              # 60% 페널티
    elif text_accuracy >= 0.1:  # 10% 이상 정확
        return 0.2              # 80% 페널티
    else:                       # 10% 미만
        return 0.05             # 95% 페널티

def compare_phones(ref_features, user_features, ref_phone, user_phone):
    """개선된 음소 비교 - 균형잡힌 평가"""
    if ref_features is None or user_features is None:
        return {'overall_similarity': 0.0, 'error': 'Feature extraction failed'}
    
    # 단어 일치 여부 확인
    words_match = ref_phone.lower() == user_phone.lower()
    
    try:
        # MFCC 코사인 유사도 (더 관대하게)
        mfcc_similarity = 1 - cosine(ref_features['mfcc'], user_features['mfcc'])
        mfcc_similarity = max(0, min(1, mfcc_similarity))  # 0-1 범위 보장
        
        # F0 유사도 (더 관대한 범위)
        f0_diff = abs(ref_features['f0_mean'] - user_features['f0_mean'])
        f0_similarity = 1 / (1 + f0_diff / 200)  # 200Hz로 범위 확대 (더 관대)
        
        # 스펙트럴 중심 유사도 (더 관대하게)
        spec_diff = abs(ref_features['spectral_centroid'] - user_features['spectral_centroid'])
        spec_similarity = 1 / (1 + spec_diff / 2000)  # 2000Hz로 범위 확대
        
        # 길이 유사도 (더 관대하게)
        duration_diff = abs(ref_features['duration'] - user_features['duration'])
        duration_similarity = 1 / (1 + duration_diff * 5)  # 5로 감소 (더 관대)
        
        if words_match:
            # 같은 단어인 경우: 더 관대한 평가
            base_similarity = (
                mfcc_similarity * 0.4 +      # MFCC 중요도 증가
                f0_similarity * 0.2 +        # F0 중요도 감소
                spec_similarity * 0.2 +      # 스펙트럴 중요도 감소
                duration_similarity * 0.2    # 길이 중요도 감소
            )
            
            # 같은 단어면 기본적으로 높은 점수 보장
            base_similarity = max(base_similarity, 0.7)  # 최소 70% 보장
            word_penalty = 1.0
            
        else:
            # 다른 단어인 경우: 엄격한 평가
            base_similarity = (
                mfcc_similarity * 0.25 +
                f0_similarity * 0.25 +
                spec_similarity * 0.25 +
                duration_similarity * 0.25
            )
            word_penalty = 0.1  # 90% 페널티
        
        overall_similarity = base_similarity * word_penalty
        
        return {
            'mfcc_similarity': float(mfcc_similarity),
            'f0_similarity': float(f0_similarity),
            'spectral_similarity': float(spec_similarity),
            'duration_similarity': float(duration_similarity),
            'words_match': words_match,
            'word_penalty': float(word_penalty),
            'base_similarity': float(base_similarity),
            'overall_similarity': float(overall_similarity),
            'f0_difference': float(f0_diff),
            'duration_difference': float(duration_diff)
        }
        
    except Exception as e:
        return {'overall_similarity': 0.0, 'error': str(e)}

def read_lab_file(lab_path):
    """Lab 파일의 텍스트 내용을 읽어옵니다."""
    try:
        with open(lab_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Lab 파일 읽기 오류 ({lab_path}): {e}")
        return "텍스트를 읽을 수 없음"

def calculate_text_accuracy(ref_words, user_words):
    """텍스트 정확도를 계산합니다."""
    ref_word_list = ref_words.lower().replace(',', '').replace('.', '').split()
    user_word_list = user_words.lower().replace(',', '').replace('.', '').split()
    
    matching_words = 0
    total_words = len(ref_word_list)
    
    for i, ref_word in enumerate(ref_word_list):
        if i < len(user_word_list) and ref_word == user_word_list[i]:
            matching_words += 1
    
    accuracy = matching_words / total_words if total_words > 0 else 0
    return {
        "target_word_count": total_words,
        "recognized_word_count": len(user_word_list),
        "matching_words": matching_words,
        "word_accuracy_percentage": round(accuracy * 100, 2)
    }

def generate_pronunciation_feedback(phone_comparisons):
    """발음 피드백을 생성합니다."""
    well_pronounced = []
    needs_practice = []
    
    for comp in phone_comparisons:
        similarity = comp['similarity_metrics'].get('overall_similarity', 0)
        word = comp['reference_phone']
        
        if similarity > 0.85:
            well_pronounced.append(word)
        elif similarity < 0.6:
            needs_practice.append({
                "word": word,
                "score": round(similarity * 100, 1),
                "issues": []
            })
            
            # 구체적인 문제점 분석
            metrics = comp['similarity_metrics']
            if metrics.get('f0_similarity', 1) < 0.7:
                needs_practice[-1]["issues"].append("피치/억양")
            if metrics.get('mfcc_similarity', 1) < 0.7:
                needs_practice[-1]["issues"].append("음색")
            if metrics.get('duration_similarity', 1) < 0.7:
                needs_practice[-1]["issues"].append("발음 길이")
    
    return {
        "well_pronounced_words": well_pronounced,
        "words_needing_practice": needs_practice,
        "total_words_analyzed": len(phone_comparisons)
    }

def get_pronunciation_grade(score):
    """발음 점수에 따른 등급을 반환합니다."""
    if score >= 0.9:
        return "Excellent (90-100%)"
    elif score >= 0.8:
        return "Very Good (80-89%)"
    elif score >= 0.7:
        return "Good (70-79%)"
    elif score >= 0.6:
        return "Fair (60-69%)"
    elif score >= 0.5:
        return "Needs Improvement (50-59%)"
    else:
        return "Poor (<50%)"

def main():
    import os
    import json
    import numpy as np

    # 실제 경로 기반으로 설정 (Windows 경로)
    base_dir = "C:/youtube_downliader/syncdata/mfa"
    corpus_path = os.path.join(base_dir, "corpus")
    dict_path = os.path.join(base_dir, "english_us_arpa.dict")
    model_path = os.path.join(base_dir, "english_us_arpa")
    alignment_output = os.path.join(base_dir, "mfa_output")

    # 기준 및 사용자 발음 파일 (같은 파일 사용)
    ref_audio = os.path.join(corpus_path, "full.wav")
    user_audio = os.path.join(corpus_path, "testspeech.wav")
    ref_lab = os.path.join(corpus_path, "full.lab")
    user_lab = os.path.join(corpus_path, "testspeech.lab")

    output_json = os.path.join(base_dir, "results", "compare_full.json")

    # Lab 파일에서 실제 텍스트 읽기
    ref_text = read_lab_file(ref_lab)
    user_text = read_lab_file(user_lab)

    print("=== MFA 기반 발음 평가 시스템 ===")
    print("기준 발음과 사용자 발음을 비교 분석합니다.")
    print(f"목표 텍스트: {ref_text}")
    print(f"인식된 텍스트: {user_text}")

    text_accuracy = calculate_text_accuracy(ref_text, user_text)

    print("1. 기존 MFA 정렬 결과를 사용합니다...")
    ref_textgrid = os.path.join(alignment_output, "full.TextGrid")
    user_textgrid = os.path.join(alignment_output, "testspeech.TextGrid")

    print("2. TextGrid 파일 파싱 중...")
    ref_phones = parse_textgrid(ref_textgrid) if os.path.exists(ref_textgrid) else []
    user_phones = parse_textgrid(user_textgrid) if os.path.exists(user_textgrid) else []

    if not ref_phones or not user_phones:
        print("TextGrid 파일을 찾을 수 없습니다. 기본 분석을 수행합니다.")
        ref_phones = [{'phone': 'FULL', 'start': 0, 'end': 8, 'duration': 8}]
        user_phones = [{'phone': 'FULL', 'start': 0, 'end': 8, 'duration': 8}]

    print(f"기준 음소 수: {len(ref_phones)}, 사용자 음소 수: {len(user_phones)}")

    print("3. 음소별 특징 추출 및 비교 중...")
    phone_comparisons = []
    min_phones = min(len(ref_phones), len(user_phones))

    for i in range(min_phones):
        ref_phone = ref_phones[i]
        user_phone = user_phones[i]
        print(f"  비교 중: {ref_phone['phone']} vs {user_phone['phone']}")

        ref_features = extract_phone_features(ref_audio, ref_phone)
        user_features = extract_phone_features(user_audio, user_phone)

        comparison = compare_phones(ref_features, user_features, ref_phone['phone'], user_phone['phone'])

        phone_comparisons.append({
            'phone_index': i,
            'reference_phone': ref_phone['phone'],
            'user_phone': user_phone['phone'],
            'reference_duration': ref_phone['duration'],
            'user_duration': user_phone['duration'],
            'similarity_metrics': comparison
        })

    overall_similarities = [comp['similarity_metrics'].get('overall_similarity', 0)
                            for comp in phone_comparisons
                            if 'overall_similarity' in comp['similarity_metrics']]
    base_score = np.mean(overall_similarities) if overall_similarities else 0

    text_penalty = calculate_text_penalty(ref_text, user_text)
    final_score = base_score * text_penalty

    print(f"기본 점수: {base_score:.4f}")
    print(f"텍스트 페널티: {text_penalty:.4f}")
    print(f"최종 점수: {final_score:.4f}")

    feedback = generate_pronunciation_feedback(phone_comparisons)

    results = {
        "analysis_info": {
            "reference_file": "full.wav (기준 발음)",
            "user_file": "testspeech.wav (사용자 발음)",
            "target_text": ref_text,
            "recognized_text": user_text,
            "analysis_date": "2025-06-24",
            "analysis_type": "pronunciation_assessment",
            "total_words_compared": len(phone_comparisons)
        },
        "text_accuracy": text_accuracy,
        "pronunciation_score": {
            "base_score": round(float(base_score), 4),
            "text_penalty_factor": round(float(text_penalty), 4),
            "final_score": round(float(final_score), 4),
            "percentage": round(float(final_score) * 100, 2),
            "grade": get_pronunciation_grade(final_score)
        },
        "detailed_word_analysis": phone_comparisons,
        "pronunciation_feedback": feedback,
        "summary": {
            "words_analyzed": len(phone_comparisons),
            "well_pronounced_count": len(feedback["well_pronounced_words"]),
            "needs_practice_count": len(feedback["words_needing_practice"]),
            "text_accuracy_percentage": text_accuracy["word_accuracy_percentage"],
            "overall_assessment": get_pronunciation_grade(final_score)
        }
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n=== 발음 평가 완료 ===")
    print(f"기본 발음 점수: {base_score:.4f} ({base_score*100:.2f}%)")
    print(f"텍스트 페널티: {text_penalty:.4f}")
    print(f"최종 발음 점수: {final_score:.4f} ({final_score*100:.2f}%)")
    print(f"발음 등급: {get_pronunciation_grade(final_score)}")
    print(f"텍스트 정확도: {text_accuracy['word_accuracy_percentage']}%")
    print(f"분석된 단어 수: {len(phone_comparisons)}")
    print(f"잘 발음된 단어: {len(feedback['well_pronounced_words'])}개")
    print(f"연습 필요 단어: {len(feedback['words_needing_practice'])}개")
    print(f"결과 파일: {output_json}")

if __name__ == "__main__":
    print("비교 시작")
    main()
