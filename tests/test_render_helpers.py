from pathlib import Path
import shutil
import uuid

from app.config import RenderConfig
from app.media.render import build_hardsub_filter, escape_subtitle_filter_path
from app.models import TranscriptDocument, TranscriptSegment
from app.subtitles.ass_writer import write_ass


def test_escape_subtitle_filter_path_escapes_windows_drive() -> None:
    path = Path(r"C:\Temp Files\demo,clip[1].srt")
    escaped = escape_subtitle_filter_path(path)
    assert r"\:" in escaped
    assert r"\," in escaped
    assert r"\[" in escaped
    assert r"\]" in escaped


def test_build_hardsub_filter_covers_original_subtitles() -> None:
    subtitle_path = Path(r"C:\Temp Files\demo.srt")
    video_filter = build_hardsub_filter(
        subtitle_path,
        RenderConfig(
            cover_original_subtitles=True,
            subtitle_cover_height_ratio=0.2,
            subtitle_cover_opacity=0.8,
        ),
    )

    assert video_filter.startswith("split[base][blur_src]")
    assert "crop=w=iw*0.760:h=ih*0.200:x=iw*0.120:y=ih*0.800" in video_filter
    assert "boxblur=" in video_filter
    assert "overlay=x=(W-w)/2:y=H-h" in video_filter
    assert "subtitles='" in video_filter


def test_build_hardsub_filter_can_use_box_cover() -> None:
    subtitle_path = Path(r"C:\Temp Files\demo.srt")
    video_filter = build_hardsub_filter(
        subtitle_path,
        RenderConfig(
            cover_original_subtitles=True,
            subtitle_cover_mode="box",
            subtitle_cover_height_ratio=0.2,
            subtitle_cover_opacity=0.8,
        ),
    )

    assert video_filter.startswith("drawbox=")
    assert "h=ih*0.200" in video_filter
    assert "color=black@0.800" in video_filter
    assert "subtitles='" in video_filter


def test_build_hardsub_filter_uses_ass_without_charenc() -> None:
    video_filter = build_hardsub_filter(Path(r"C:\Temp Files\demo.ass"), RenderConfig(cover_original_subtitles=False))

    assert "subtitles='" in video_filter
    assert "charenc" not in video_filter


def test_write_ass_uses_subtitle_style() -> None:
    output_dir = Path("workspace_data") / "test_runs" / f"ass_writer_{uuid.uuid4().hex}"
    try:
        output_path = output_dir / "styled.ass"
        write_ass(
            TranscriptDocument(
                job_id="job",
                video_path="video.mp4",
                detected_language="vi",
                duration_sec=2.0,
                segments=[TranscriptSegment(id=1, start=0, end=2, text="Xin chào")],
            ),
            output_path,
            font_size=40,
            position_x_percent=30,
            bottom_percent=20,
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Style: Default,Arial,40" in content
        assert r"{\pos(384,576)}Xin chào" in content
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_build_hardsub_filter_allows_transparent_cover() -> None:
    video_filter = build_hardsub_filter(
        Path(r"C:\Temp Files\demo.ass"),
        RenderConfig(
            cover_original_subtitles=True,
            subtitle_cover_mode="box",
            subtitle_cover_height_ratio=0.3,
            subtitle_cover_opacity=0.25,
        ),
    )

    assert "h=ih*0.300" in video_filter
    assert "color=black@0.250" in video_filter
