from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.example.yaml"
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
CONFIG_ENV_VAR = "AUTOTRANSLATE_CONFIG"
WORKER_BACKEND_ENV_VAR = "AUTOTRANSLATE_WORKER_BACKEND"


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _resolve_binary(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    if len(path.parts) > 1:
        return str((PROJECT_ROOT / path).resolve())
    return value


class DirectoriesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobs_dir: Path = Field(default=Path("workspace_data/jobs"))
    uploads_dir: Path = Field(default=Path("workspace_data/uploads"))
    temp_dir: Path = Field(default=Path("workspace_data/tmp"))

    def resolve(self) -> "DirectoriesConfig":
        return DirectoriesConfig(
            jobs_dir=_resolve_path(self.jobs_dir),
            uploads_dir=_resolve_path(self.uploads_dir),
            temp_dir=_resolve_path(self.temp_dir),
        )


class ASRConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend: str = "faster-whisper"
    model_size: str = "tiny"
    device: str = "auto"
    compute_type: str = "auto"
    beam_size: int = 1
    cpu_threads: int = 4
    num_workers: int = 1
    vad_filter: bool = True
    word_timestamps: bool = False


class TranslationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend: str = "echo"
    source_language: str = "auto"
    target_language: str = "vi"
    batch_size: int = 8
    libretranslate_url: str | None = None
    libretranslate_api_key: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    gemini_base_url: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None

    @classmethod
    def from_sources(cls, data: dict[str, Any]) -> "TranslationConfig":
        config = cls.model_validate(data)
        env_overrides = {
            "llm_base_url": os.getenv("AUTOTRANSLATE_LLM_BASE_URL"),
            "llm_api_key": os.getenv("AUTOTRANSLATE_LLM_API_KEY"),
            "llm_model": os.getenv("AUTOTRANSLATE_LLM_MODEL"),
            "openai_base_url": os.getenv("AUTOTRANSLATE_OPENAI_BASE_URL"),
            "openai_api_key": os.getenv("AUTOTRANSLATE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "openai_model": os.getenv("AUTOTRANSLATE_OPENAI_MODEL"),
            "gemini_base_url": os.getenv("AUTOTRANSLATE_GEMINI_BASE_URL"),
            "gemini_api_key": os.getenv("AUTOTRANSLATE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"),
            "gemini_model": os.getenv("AUTOTRANSLATE_GEMINI_MODEL"),
            "libretranslate_url": os.getenv("AUTOTRANSLATE_LIBRETRANSLATE_URL"),
            "libretranslate_api_key": os.getenv("AUTOTRANSLATE_LIBRETRANSLATE_API_KEY"),
        }
        updates = {key: value for key, value in env_overrides.items() if value}
        return config.model_copy(update=updates)


class SubtitleConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration_sec: float = 1.1
    max_duration_sec: float = 7.0


class RenderConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    encoder: str = "auto"
    quality_preset: str = "balanced"
    video_codec: str = "libx264"
    preset: str = "medium"
    crf: int = 20
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    cover_original_subtitles: bool = True
    subtitle_cover_mode: str = "blur"
    subtitle_cover_height_ratio: float = 0.07
    subtitle_cover_opacity: float = 0.72
    subtitle_font_size: float = 32
    subtitle_position_x: float = 50
    subtitle_position_y: float = 8


class TTSConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend: str = "edge-tts"
    voice: str = "vi-VN-HoaiMyNeural"
    rate_floor: int = -35
    rate_ceil: int = 45
    background_audio_gain: float = 0.0
    voiceover_gain: float = 1.4
    speaker_voice_map: dict[str, str] = Field(default_factory=dict)


class WorkerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    web_enabled: bool = True
    backend: str = "thread"
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    max_attempts: int = 3
    backoff_initial_sec: float = 5.0
    backoff_factor: float = 2.0
    backoff_max_sec: float = 60.0


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_name: str = "Auto Translate Video"
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    directories: DirectoriesConfig = Field(default_factory=DirectoriesConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    subtitles: SubtitleConfig = Field(default_factory=SubtitleConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "AppConfig":
        load_dotenv()
        raw_path = config_path or os.getenv(CONFIG_ENV_VAR) or (LOCAL_CONFIG_PATH if LOCAL_CONFIG_PATH.exists() else DEFAULT_CONFIG_PATH)
        file_path = _resolve_path(raw_path)
        data: dict[str, Any] = {}
        if file_path.exists():
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        config = cls.model_validate(
            {
                **data,
                "directories": data.get("directories", {}),
                "asr": data.get("asr", {}),
                "translation": TranslationConfig.from_sources(data.get("translation", {})).model_dump(),
                "subtitles": data.get("subtitles", {}),
                "render": data.get("render", {}),
                "tts": data.get("tts", {}),
                "worker": data.get("worker", {}),
            }
        )
        worker_backend_override = os.getenv(WORKER_BACKEND_ENV_VAR)
        worker_config = config.worker
        if worker_backend_override:
            worker_config = worker_config.model_copy(update={"backend": worker_backend_override.strip().lower()})
        return config.model_copy(
            update={
                "directories": config.directories.resolve(),
                "ffmpeg_bin": _resolve_binary(config.ffmpeg_bin),
                "ffprobe_bin": _resolve_binary(config.ffprobe_bin),
                "worker": worker_config,
            }
        )
