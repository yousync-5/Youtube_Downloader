def split_segments_by_half(segments, video_url):
    """
    segment 리스트를 중간에서 반으로 나누어 화자 2명으로 구성된 speaker JSON 반환
    """
    total_segments = len(segments)
    mid_index = total_segments // 2

    # 두 화자 정의
    speakers = [
        {
            "actor": "Liam_Nessom",
            "video_url": video_url,
            "token_id": 1,
            "start_time": segments[0]["start"],
            "end_time": segments[mid_index - 1]["end"],
            "segments": segments[:mid_index],
        },
        {
            "actor": "Liam_Nesson",
            "video_url": video_url,
            "token_id": 2,
            "start_time": segments[mid_index]["start"],
            "end_time": segments[-1]["end"],
            "segments": segments[mid_index:],
        }
    ]

    return speakers
