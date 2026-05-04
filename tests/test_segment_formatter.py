from app.config import SubtitleConfig
from app.models import TranscriptSegment
from app.subtitles.segment_formatter import format_segments_for_subtitles


def test_segment_formatter_wraps_lines() -> None:
    segment = TranscriptSegment(
        id=1,
        start=0.0,
        end=4.0,
        text="ignored",
        translated_text="Day la mot cau tieng Viet kha dai de kiem tra viec xuong dong cho subtitle.",
    )
    result = format_segments_for_subtitles([segment], SubtitleConfig(max_chars_per_line=20, max_lines=2))
    assert "\n" in result[0].subtitle_text
