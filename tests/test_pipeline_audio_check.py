from app.core.exceptions import ProcessError
from app.core.pipeline import ensure_video_has_audio
from app.models import VideoMetadata


def test_ensure_video_has_audio_rejects_video_without_audio() -> None:
    metadata = VideoMetadata(duration_sec=43.08, width=1920, height=1080)

    try:
        ensure_video_has_audio(metadata)
    except ProcessError as exc:
        assert "không có luồng âm thanh" in str(exc)
    else:
        raise AssertionError("Expected ProcessError")


def test_ensure_video_has_audio_accepts_video_with_audio() -> None:
    metadata = VideoMetadata(duration_sec=43.08, audio_stream_index=1, audio_codec="aac")

    ensure_video_has_audio(metadata)
