from app.models import TranscriptDocument, TranscriptSegment
from app.subtitles.srt_writer import format_srt_timestamp


def test_format_srt_timestamp() -> None:
    assert format_srt_timestamp(65.432) == "00:01:05,432"


def test_transcript_document_roundtrip() -> None:
    document = TranscriptDocument(
        job_id="job-1",
        video_path="input.mp4",
        detected_language="en",
        duration_sec=12.5,
        segments=[
            TranscriptSegment(
                id=1,
                start=0.0,
                end=2.0,
                text="Hello",
                translated_text="Xin chao",
            )
        ],
    )
    assert document.segments[0].translated_text == "Xin chao"

