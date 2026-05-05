from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "completed", "failed", "completed_with_errors", "cancelled"]
JobTaskType = Literal["process", "translate", "render_hardsub", "render_softsub", "render_voiceover"]


class VideoMetadata(BaseModel):
    duration_sec: float = 0.0
    width: int | None = None
    height: int | None = None
    audio_stream_index: int | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    translated_text: str | None = None
    subtitle_text: str | None = None
    speaker: str | None = None
    voice_name: str | None = None


class TranscriptDocument(BaseModel):
    job_id: str
    video_path: str
    detected_language: str
    duration_sec: float
    segments: list[TranscriptSegment] = Field(default_factory=list)


class SubtitleTrackOption(BaseModel):
    title: str = ""
    language: str = "und"
    content: str
    file_name: str | None = None
    is_default: bool = False


class PipelineRunOptions(BaseModel):
    output_root: str | None = None
    asr_model_size: str | None = None
    translator_backend: str | None = None
    source_language: str | None = None
    target_language: str = "vi"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    gemini_base_url: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    libretranslate_url: str | None = None
    libretranslate_api_key: str | None = None
    glossary_text: str | None = None
    glossary_json_path: str | None = None
    render_hardsub: bool = False
    generate_voiceover: bool = False
    voice_name: str | None = None
    voiceover_gain: float | None = None
    background_audio_gain: float | None = None
    render_encoder: Literal["cpu", "nvidia", "intel", "amd"] | None = None
    render_preset: Literal["fast", "balanced", "quality"] | None = None
    subtitle_font_size: float | None = None
    subtitle_position_x: float | None = None
    subtitle_position_y: float | None = None
    subtitle_cover_mode: Literal["blur", "box"] | None = None
    subtitle_cover_opacity: float | None = None
    subtitle_cover_height_ratio: float | None = None
    extra_subtitle_tracks: list[SubtitleTrackOption] = Field(default_factory=list)


SENSITIVE_OPTION_KEYS = {
    "llm_api_key",
    "openai_api_key",
    "gemini_api_key",
    "libretranslate_api_key",
}


def sanitize_pipeline_options(options: PipelineRunOptions | dict[str, object]) -> dict[str, object]:
    if isinstance(options, PipelineRunOptions):
        values = options.model_dump(mode="json", exclude_none=True)
    else:
        values = {key: value for key, value in options.items() if value is not None}

    sanitized: dict[str, object] = {}
    for key, value in values.items():
        if key in SENSITIVE_OPTION_KEYS:
            sanitized[f"{key}_configured"] = bool(value)
        elif key == "extra_subtitle_tracks" and isinstance(value, list):
            sanitized[key] = [
                {
                    "title": str(track.get("title") or "") if isinstance(track, dict) else "",
                    "language": str(track.get("language") or "und") if isinstance(track, dict) else "und",
                    "file_name": str(track.get("file_name") or "") if isinstance(track, dict) else "",
                    "is_default": bool(track.get("is_default")) if isinstance(track, dict) else False,
                    "size": len(str(track.get("content") or "")) if isinstance(track, dict) else 0,
                }
                for track in value
            ]
        elif key in {"asr_device_used", "asr_compute_type_used"}:
            sanitized[key] = str(value)
        else:
            sanitized[key] = value
    return sanitized


class TranscriptUpdateRequest(BaseModel):
    segments: list[TranscriptSegment]


class JobManifest(BaseModel):
    job_id: str
    status: JobStatus
    stage: str
    progress: float = 0.0
    input_video: str
    output_dir: str
    detected_language: str | None = None
    errors: list[str] = Field(default_factory=list)
    outputs: dict[str, str | None] = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)
    metadata: VideoMetadata | None = None
    options: dict[str, object] = Field(default_factory=dict)
    task_type: JobTaskType | None = None
    retry_attempt: int = 0
    retry_max_attempts: int = 1
    retry_next_at: float | None = None
    retry_last_error: str | None = None
