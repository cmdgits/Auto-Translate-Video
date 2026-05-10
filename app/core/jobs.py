from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models import JobManifest

MAX_JOB_STEM_LENGTH = 80


def _safe_job_stem(input_name: str) -> str:
    import re

    raw_stem = Path(input_name).stem.strip() or "video"
    safe_stem = re.sub(r'[\\/*?:"<>|]', "_", raw_stem).strip(" ._") or "video"
    if len(safe_stem) > MAX_JOB_STEM_LENGTH:
        safe_stem = safe_stem[:MAX_JOB_STEM_LENGTH].rstrip(" ._") or "video"
    return safe_stem


@dataclass
class JobContext:
    job_id: str
    input_name: str
    input_video: Path
    root_dir: Path
    input_dir: Path
    audio_dir: Path
    data_dir: Path
    subtitles_dir: Path
    renders_dir: Path
    tts_dir: Path
    manifest_path: Path
    extracted_audio_path: Path
    waveform_json_path: Path
    transcript_json_path: Path
    original_srt_path: Path
    srt_path: Path
    vtt_path: Path
    ass_path: Path
    hardsub_video_path: Path
    softsub_video_path: Path
    softsub_command_path: Path
    voiceover_audio_path: Path
    voiceover_video_path: Path
    voiceover_filter_path: Path


class JobManager:
    def __init__(self, jobs_root: Path) -> None:
        self.jobs_root = jobs_root
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def create_context(
        self,
        input_name: str,
        input_video: Path,
        output_root: Path | None = None,
    ) -> JobContext:
        jobs_root = output_root or self.jobs_root
        jobs_root.mkdir(parents=True, exist_ok=True)
        safe_stem = _safe_job_stem(input_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"{safe_stem}_{timestamp}"
        root_dir = jobs_root / job_id
        suffix = 2
        while root_dir.exists():
            job_id = f"{safe_stem}_{timestamp}_{suffix}"
            root_dir = jobs_root / job_id
            suffix += 1
        input_dir = root_dir / "input"
        audio_dir = root_dir / "audio"
        data_dir = root_dir / "data"
        subtitles_dir = root_dir / "subtitles"
        renders_dir = root_dir / "renders"
        tts_dir = root_dir / "tts"
        for directory in (root_dir, input_dir, audio_dir, data_dir, subtitles_dir, renders_dir, tts_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return JobContext(
            job_id=job_id,
            input_name=input_name,
            input_video=input_video,
            root_dir=root_dir,
            input_dir=input_dir,
            audio_dir=audio_dir,
            data_dir=data_dir,
            subtitles_dir=subtitles_dir,
            renders_dir=renders_dir,
            tts_dir=tts_dir,
            manifest_path=root_dir / "manifest.json",
            extracted_audio_path=audio_dir / "source_16k.wav",
            waveform_json_path=data_dir / "waveform.json",
            transcript_json_path=data_dir / "transcript.vi.json",
            original_srt_path=subtitles_dir / "subtitles.original.srt",
            srt_path=subtitles_dir / "subtitles.vi.srt",
            vtt_path=subtitles_dir / "subtitles.vi.vtt",
            ass_path=subtitles_dir / "subtitles.vi.ass",
            hardsub_video_path=renders_dir / "video.hardsub.mp4",
            softsub_video_path=renders_dir / "video.softsub.mkv",
            softsub_command_path=renders_dir / "video.softsub.ffmpeg.txt",
            voiceover_audio_path=audio_dir / "voiceover.vi.m4a",
            voiceover_video_path=renders_dir / "video.voiceover.vi.mp4",
            voiceover_filter_path=tts_dir / "voiceover_mix.ffscript",
        )

    def get_context(self, job_id: str, input_video: Path | None = None, jobs_root: Path | None = None) -> JobContext:
        root = jobs_root or self.jobs_root
        job_root = root / job_id
        manifest = self.load_manifest(job_id, jobs_root=root)
        resolved_input = input_video or (Path(manifest.input_video) if manifest else job_root / "input" / "source.mp4")
        return JobContext(
            job_id=job_id,
            input_name=resolved_input.name,
            input_video=resolved_input,
            root_dir=job_root,
            input_dir=job_root / "input",
            audio_dir=job_root / "audio",
            data_dir=job_root / "data",
            subtitles_dir=job_root / "subtitles",
            renders_dir=job_root / "renders",
            tts_dir=job_root / "tts",
            manifest_path=job_root / "manifest.json",
            extracted_audio_path=job_root / "audio" / "source_16k.wav",
            waveform_json_path=job_root / "data" / "waveform.json",
            transcript_json_path=job_root / "data" / "transcript.vi.json",
            original_srt_path=job_root / "subtitles" / "subtitles.original.srt",
            srt_path=job_root / "subtitles" / "subtitles.vi.srt",
            vtt_path=job_root / "subtitles" / "subtitles.vi.vtt",
            ass_path=job_root / "subtitles" / "subtitles.vi.ass",
            hardsub_video_path=job_root / "renders" / "video.hardsub.mp4",
            softsub_video_path=job_root / "renders" / "video.softsub.mkv",
            softsub_command_path=job_root / "renders" / "video.softsub.ffmpeg.txt",
            voiceover_audio_path=job_root / "audio" / "voiceover.vi.m4a",
            voiceover_video_path=job_root / "renders" / "video.voiceover.vi.mp4",
            voiceover_filter_path=job_root / "tts" / "voiceover_mix.ffscript",
        )

    def write_manifest(self, context: JobContext, manifest: JobManifest) -> None:
        context.manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_manifest(self, manifest: JobManifest) -> JobManifest:
        context = self.get_context(manifest.job_id, input_video=Path(manifest.input_video))
        self.write_manifest(context, manifest)
        return manifest

    def load_manifest(self, job_id: str, jobs_root: Path | None = None) -> JobManifest | None:
        root = jobs_root or self.jobs_root
        manifest_path = root / job_id / "manifest.json"
        if not manifest_path.exists():
            return None
        return JobManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def list_manifests(self) -> list[JobManifest]:
        manifests: list[JobManifest] = []
        for manifest_path in self.jobs_root.glob("*/manifest.json"):
            try:
                manifests.append(JobManifest.model_validate_json(manifest_path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(manifests, key=lambda manifest: manifest.job_id, reverse=True)

    def delete_job(self, job_id: str) -> bool:
        jobs_root = self.jobs_root.resolve()
        job_root = (jobs_root / job_id).resolve()
        if not job_root.is_relative_to(jobs_root):
            return False
        if not job_root.exists() or not job_root.is_dir():
            return False
        shutil.rmtree(job_root)
        return True
