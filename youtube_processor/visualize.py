# visualize.py
import matplotlib.pyplot as plt
import librosa, librosa.display

def visualize_diarization(audio_path, diarization, vad_timeline=None):
    """
    audio_path:  파형을 그릴 오디오 파일 경로
    diarization: pyannote.audio Pipeline 결과 (Annotation)
    vad_timeline: (Optional) pyannote.core.Timeline. 
                  None 이면 diarization.get_timeline() 사용
    """
    # 1) 오디오 로드
    y, sr = librosa.load(audio_path, sr=None)

    # 2) Figure & waveform
    plt.figure(figsize=(14, 4))
    librosa.display.waveshow(y, sr=sr, alpha=0.6)
    plt.xlabel("Time (s)")
    plt.title("Waveform with VAD & Speaker Labels")

    # 3) VAD Timeline 준비
    #    전달받지 않았다면 diarization 결과에서 speech 타임라인으로 대체
    if vad_timeline is None:
        # .get_timeline() 은 모든 speaker segment 합친 Timeline 객체
        vad_timeline = diarization.get_timeline()

    # 4) VAD 마스크 (회색 박스)
    for seg in vad_timeline.support():
        plt.axvspan(seg.start, seg.end, color='grey', alpha=0.3,
                    label='_nolegend_')

    # 5) 화자별 영역 (색상 자동 할당)
    cmap = plt.get_cmap("tab10")
    colors = {}
    for segment, _, speaker in diarization.itertracks(yield_label=True):
        if speaker not in colors:
            colors[speaker] = cmap(len(colors) % cmap.N)
        plt.axvspan(segment.start, segment.end,
                    color=colors[speaker], alpha=0.5,
                    label=speaker
                    if speaker not in plt.gca().get_legend_handles_labels()[1]
                    else "_nolegend_")

    # 6) 범례
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.show()
