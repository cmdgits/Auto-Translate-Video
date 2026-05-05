from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Callable

from app.asr.faster_whisper_backend import FasterWhisperBackend
from app.config import AppConfig
from app.config import RenderConfig
from app.core.exceptions import ConfigurationError, DependencyError, JobCancelledError, ProcessError
from app.core.jobs import JobContext, JobManager
from app.media.audio_extract import extract_audio_to_wav
from app.media.probe import probe_video
from app.media.render import (
    build_mux_subtitle_tracks_command_string,
    burn_subtitles_into_video,
    mux_subtitle_tracks_into_video,
    render_video_with_replaced_audio,
)
from app.media.waveform import write_waveform_json
from app.models import (
    JobManifest,
    PipelineRunOptions,
    TranscriptDocument,
    TranscriptSegment,
    VideoMetadata,
    sanitize_pipeline_options,
)
from app.subtitles.segment_formatter import format_segments_for_subtitles
from app.subtitles.ass_writer import write_ass
from app.subtitles.srt_writer import write_srt
from app.subtitles.vtt_writer import write_vtt
from app.translate.factory import build_translator
from app.tts.edge_tts_backend import EdgeTTSBackend
from app.tts.voiceover import mix_voiceover_audio

ProgressHook = Callable[[JobManifest], None]
SUBTITLE_LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_-]{2,12}$")


def ensure_video_has_audio(metadata: VideoMetadata) -> None:
    if metadata.audio_stream_index is None:
        raise ProcessError(
            "Video này không có luồng âm thanh, nên không thể tách audio để nhận dạng giọng nói. "
            "Hãy chọn video có audio hoặc tải lại bản có âm thanh."
        )


class VideoTranslationPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.jobs = JobManager(config.directories.jobs_dir)
        self._detected_render_encoders: list[str] | None = None

    def cancel_job(self, job_id: str, reason: str = "Tác vụ đã được dừng theo yêu cầu.") -> JobManifest:
        context, manifest = self._require_job(job_id)
        if manifest.status not in {"queued", "running"}:
            return manifest
        cancelled_manifest = manifest.model_copy(
            update={
                "status": "cancelled",
                "stage": "cancelled",
                "progress": 1.0,
                "errors": [reason],
                "outputs": self._collect_existing_outputs(context),
            }
        )
        self._emit(context, cancelled_manifest, None)
        return cancelled_manifest

    def _raise_if_cancelled(self, context: JobContext) -> None:
        manifest = self.jobs.load_manifest(context.job_id)
        if manifest and manifest.status == "cancelled":
            raise JobCancelledError(manifest.errors[0] if manifest.errors else "Tác vụ đã được dừng.")

    def _emit_running(self, context: JobContext, manifest: JobManifest, progress_hook: ProgressHook | None) -> None:
        self._raise_if_cancelled(context)
        self._emit(context, manifest, progress_hook)

    def create_job_context(self, input_name: str, input_video: Path, output_root: Path | None = None) -> JobContext:
        return self.jobs.create_context(input_name=input_name, input_video=input_video, output_root=output_root)

    def process(
        self,
        input_video: Path,
        options: PipelineRunOptions | None = None,
        progress_hook: ProgressHook | None = None,
    ) -> JobManifest:
        run_options = options or PipelineRunOptions()
        output_root = Path(run_options.output_root).resolve() if run_options.output_root else None
        context = self.create_job_context(input_video.name, input_video, output_root)
        return self.process_job(context, run_options, progress_hook)

    def process_job(
        self,
        context: JobContext,
        options: PipelineRunOptions | None = None,
        progress_hook: ProgressHook | None = None,
    ) -> JobManifest:
        run_options = options or PipelineRunOptions()
        existing_manifest = self.jobs.load_manifest(context.job_id)
        manifest = existing_manifest or JobManifest(
            job_id=context.job_id,
            status="queued",
            stage="queued",
            progress=0.0,
            input_video=str(context.input_video),
            output_dir=str(context.root_dir),
            options=sanitize_pipeline_options(run_options),
        )
        if existing_manifest is None:
            self._emit(context, manifest, progress_hook)
        timings: dict[str, float] = {}
        started_at = time.perf_counter()

        try:
            self._raise_if_cancelled(context)
            manifest = manifest.model_copy(update={"status": "running", "stage": "probing", "progress": 0.08})
            self._emit_running(context, manifest, progress_hook)
            metadata = probe_video(context.input_video, self.config.ffprobe_bin)
            manifest = manifest.model_copy(update={"metadata": metadata})
            ensure_video_has_audio(metadata)
            self._raise_if_cancelled(context)

            manifest = manifest.model_copy(
                update={
                    "stage": "extracting_audio",
                    "progress": 0.2,
                }
            )
            self._emit_running(context, manifest, progress_hook)
            extract_audio_to_wav(context.input_video, context.extracted_audio_path, self.config.ffmpeg_bin)
            write_waveform_json(context.extracted_audio_path, context.waveform_json_path)
            self._raise_if_cancelled(context)

            manifest = manifest.model_copy(update={"stage": "transcribing", "progress": 0.48})
            self._emit_running(context, manifest, progress_hook)
            asr_started = time.perf_counter()
            asr_backend = FasterWhisperBackend(self.config.asr, run_options.asr_model_size)

            def on_asr_progress(asr_progress: float) -> None:
                nonlocal manifest
                self._raise_if_cancelled(context)
                manifest = manifest.model_copy(update={"progress": min(0.48 + asr_progress * 0.2, 0.68)})
                self._emit_running(context, manifest, progress_hook)

            transcript = asr_backend.transcribe(
                audio_path=context.extracted_audio_path,
                job_id=context.job_id,
                video_path=context.input_video,
                duration_sec=metadata.duration_sec,
                progress_hook=on_asr_progress,
            )
            timings["asr_sec"] = round(time.perf_counter() - asr_started, 3)
            manifest_options = {
                **(manifest.options or {}),
                "asr_device_used": asr_backend.selected_device or "unknown",
                "asr_compute_type_used": asr_backend.selected_compute_type or "unknown",
            }
            manifest = manifest.model_copy(update={"options": manifest_options})
            if asr_backend.warnings:
                manifest = manifest.model_copy(update={"errors": [*(manifest.errors or []), *asr_backend.warnings]})
            self._raise_if_cancelled(context)
            self._write_transcript_json(transcript, context.transcript_json_path)
            manifest = manifest.model_copy(update={"outputs": self._collect_existing_outputs(context)})

            manifest = manifest.model_copy(
                update={
                    "stage": "translating",
                    "progress": 0.7,
                    "detected_language": transcript.detected_language,
                }
            )
            self._emit_running(context, manifest, progress_hook)
            translate_started = time.perf_counter()
            translator = build_translator(self.config.translation, run_options)
            source_language = (
                run_options.source_language
                or (transcript.detected_language if transcript.detected_language != "unknown" else None)
                or self.config.translation.source_language
                or "auto"
            )

            def on_translate_progress(translate_progress: float) -> None:
                nonlocal manifest
                self._raise_if_cancelled(context)
                manifest = manifest.model_copy(update={"progress": min(0.7 + translate_progress * 0.11, 0.81)})
                self._emit_running(context, manifest, progress_hook)

            translations = translator.translate_segments(
                transcript.segments,
                source_language=source_language,
                target_language=run_options.target_language or self.config.translation.target_language,
                progress_callback=on_translate_progress,
            )
            self._raise_if_cancelled(context)
            for segment, translated in zip(transcript.segments, translations, strict=False):
                segment.translated_text = translated
            timings["translate_sec"] = round(time.perf_counter() - translate_started, 3)

            manifest = manifest.model_copy(update={"stage": "writing_subtitles", "progress": 0.82})
            self._emit_running(context, manifest, progress_hook)
            transcript = self._write_transcript_assets(transcript, context, preserve_existing=False)
            outputs = self._collect_existing_outputs(context)

            render_errors: list[str] = []
            if run_options.render_hardsub:
                try:
                    manifest = manifest.model_copy(update={"stage": "rendering_hardsub", "progress": 0.82})
                    self._emit_running(context, manifest, progress_hook)
                    render_started = time.perf_counter()

                    def on_hardsub_progress(progress: float) -> None:
                        nonlocal manifest
                        self._raise_if_cancelled(context)
                        manifest = manifest.model_copy(
                            update={"progress": min(0.82 + progress * 0.09, 0.91)}
                        )
                        self._emit_running(context, manifest, progress_hook)

                    self._render_hardsub_output(context, run_options, on_hardsub_progress)
                    self._raise_if_cancelled(context)
                    timings["render_hardsub_sec"] = round(time.perf_counter() - render_started, 3)
                except Exception as exc:  # pragma: no cover - runtime dependency path
                    render_errors.append(f"Hardsub render loi: {exc}")
                outputs = self._collect_existing_outputs(context)

            if run_options.generate_voiceover:
                try:
                    manifest = manifest.model_copy(update={"stage": "rendering_voiceover", "progress": 0.91})
                    self._emit_running(context, manifest, progress_hook)
                    render_started = time.perf_counter()
                    has_original_audio = bool(manifest.metadata and manifest.metadata.audio_stream_index is not None)

                    def on_voiceover_progress(progress: float) -> None:
                        nonlocal manifest
                        self._raise_if_cancelled(context)
                        manifest = manifest.model_copy(
                            update={"progress": min(0.91 + progress * 0.08, 0.99)}
                        )
                        self._emit_running(context, manifest, progress_hook)

                    self._render_voiceover_output(
                        context,
                        transcript,
                        run_options,
                        render_errors,
                        has_original_audio,
                        on_voiceover_progress,
                    )
                    self._raise_if_cancelled(context)
                    timings["render_voiceover_sec"] = round(time.perf_counter() - render_started, 3)
                except Exception as exc:  # pragma: no cover - runtime dependency path
                    render_errors.append(f"Voice-over render loi: {exc}")
                outputs = self._collect_existing_outputs(context)

            timings["total_sec"] = round(time.perf_counter() - started_at, 3)
            status = "completed" if not render_errors else "completed_with_errors"
            final_manifest = manifest.model_copy(
                update={
                    "status": status,
                    "stage": "completed" if status == "completed" else "completed_with_errors",
                    "progress": 1.0,
                    "detected_language": transcript.detected_language,
                    "outputs": outputs,
                    "timings": timings,
                    "errors": render_errors,
                }
            )
            self._raise_if_cancelled(context)
            self._emit(context, final_manifest, progress_hook)
            return final_manifest
        except JobCancelledError as exc:
            timings["total_sec"] = round(time.perf_counter() - started_at, 3)
            cancelled_manifest = manifest.model_copy(
                update={
                    "status": "cancelled",
                    "stage": "cancelled",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                    "timings": timings,
                }
            )
            self._emit(context, cancelled_manifest, progress_hook)
            return cancelled_manifest
        except Exception as exc:
            timings["total_sec"] = round(time.perf_counter() - started_at, 3)
            failed_manifest = manifest.model_copy(
                update={
                    "status": "failed",
                    "stage": "failed",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "timings": timings,
                }
            )
            self._emit(context, failed_manifest, progress_hook)
            raise

    def load_transcript(self, job_id: str) -> TranscriptDocument:
        context, _ = self._require_job(job_id)
        return self._read_transcript(context)

    def save_transcript(self, job_id: str, segments: list[TranscriptSegment]) -> JobManifest:
        context, manifest = self._require_job(job_id)
        if context.transcript_json_path.exists():
            transcript = self._read_transcript(context)
        else:
            transcript = TranscriptDocument(
                job_id=context.job_id,
                video_path=str(context.input_video),
                detected_language=manifest.detected_language or "imported",
                duration_sec=self._duration_for_imported_segments(segments, manifest),
                segments=[],
            )
        transcript.segments = self._normalize_segments(segments, transcript.duration_sec)
        transcript = self._write_transcript_assets(transcript, context, preserve_existing=True)
        self._invalidate_render_outputs(context)
        updated_manifest = manifest.model_copy(
            update={
                "status": "completed",
                "stage": "subtitle_saved",
                "progress": 1.0,
                "detected_language": transcript.detected_language,
                "outputs": self._collect_existing_outputs(context),
                "errors": [],
            }
        )
        self._emit(context, updated_manifest, None)
        return updated_manifest

    def translate_transcript(self, job_id: str, options: PipelineRunOptions | None = None) -> JobManifest:
        run_options = options or PipelineRunOptions()
        context, manifest = self._require_job(job_id)
        running_manifest = manifest.model_copy(
            update={
                "status": "running",
                "stage": "translating",
                "progress": 0.0,
            }
        )
        self._emit(context, running_manifest, None)
        started_at = time.perf_counter()

        try:
            self._raise_if_cancelled(context)
            transcript = self._read_transcript(context)
            translator = build_translator(self.config.translation, run_options)
            source_language = (
                run_options.source_language
                or (transcript.detected_language if transcript.detected_language != "unknown" else None)
                or self.config.translation.source_language
                or "auto"
            )
            current_manifest = running_manifest

            def on_translate_progress(translate_progress: float) -> None:
                nonlocal current_manifest
                self._raise_if_cancelled(context)
                current_manifest = current_manifest.model_copy(
                    update={"progress": min(0.05 + translate_progress * 0.9, 0.95)}
                )
                self._emit_running(context, current_manifest, None)

            translations = translator.translate_segments(
                transcript.segments,
                source_language=source_language,
                target_language=run_options.target_language or self.config.translation.target_language,
                progress_callback=on_translate_progress,
            )
            self._raise_if_cancelled(context)
            for segment, translated in zip(transcript.segments, translations, strict=False):
                segment.translated_text = translated
                segment.subtitle_text = None
            transcript = self._write_transcript_assets(transcript, context, preserve_existing=False)
            self._invalidate_render_outputs(context)
            timings = {**manifest.timings, "translate_sec": round(time.perf_counter() - started_at, 3)}
            updated_manifest = running_manifest.model_copy(
                update={
                    "status": "completed",
                    "stage": "subtitle_translated",
                    "progress": 1.0,
                    "detected_language": transcript.detected_language,
                    "outputs": self._collect_existing_outputs(context),
                    "timings": timings,
                    "errors": [],
                    "options": {**manifest.options, **sanitize_pipeline_options(run_options)},
                }
            )
            self._raise_if_cancelled(context)
            self._emit(context, updated_manifest, None)
            return updated_manifest
        except JobCancelledError as exc:
            cancelled_manifest = running_manifest.model_copy(
                update={
                    "status": "cancelled",
                    "stage": "cancelled",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, cancelled_manifest, None)
            return cancelled_manifest
        except Exception as exc:
            failed_manifest = running_manifest.model_copy(
                update={
                    "status": "completed_with_errors",
                    "stage": "translation_failed",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, failed_manifest, None)
            raise

    def render_hardsub(self, job_id: str, options: PipelineRunOptions | None = None) -> JobManifest:
        context, manifest = self._require_job(job_id)
        running_manifest = manifest.model_copy(
            update={
                "status": "running",
                "stage": "rendering_hardsub",
                "progress": 0.0,
            }
        )
        self._emit(context, running_manifest, None)
        started_at = time.perf_counter()

        try:
            self._raise_if_cancelled(context)
            transcript = self._read_transcript(context)
            self._write_transcript_assets(transcript, context, preserve_existing=True)
            current_manifest = running_manifest

            def on_hardsub_progress(progress: float) -> None:
                nonlocal current_manifest
                self._raise_if_cancelled(context)
                current_manifest = current_manifest.model_copy(
                    update={"progress": min(progress, 0.999)}
                )
                self._emit_running(context, current_manifest, None)

            self._render_hardsub_output(context, options, on_hardsub_progress)
            self._raise_if_cancelled(context)
            timings = {**manifest.timings, "render_hardsub_sec": round(time.perf_counter() - started_at, 3)}
            updated_manifest = running_manifest.model_copy(
                update={
                    "status": "completed",
                    "stage": "completed",
                    "progress": 1.0,
                    "outputs": self._collect_existing_outputs(context),
                    "timings": timings,
                    "errors": [],
                }
            )
            self._raise_if_cancelled(context)
            self._emit(context, updated_manifest, None)
            return updated_manifest
        except JobCancelledError as exc:
            cancelled_manifest = running_manifest.model_copy(
                update={
                    "status": "cancelled",
                    "stage": "cancelled",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, cancelled_manifest, None)
            return cancelled_manifest
        except Exception as exc:
            failed_manifest = running_manifest.model_copy(
                update={
                    "status": "completed_with_errors",
                    "stage": "render_hardsub_failed",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, failed_manifest, None)
            raise

    def render_softsub(self, job_id: str, options: PipelineRunOptions | None = None) -> JobManifest:
        run_options = options or PipelineRunOptions()
        context, manifest = self._require_job(job_id)
        running_manifest = manifest.model_copy(
            update={
                "status": "running",
                "stage": "rendering_softsub",
                "progress": 0.0,
            }
        )
        self._emit(context, running_manifest, None)
        started_at = time.perf_counter()

        try:
            self._raise_if_cancelled(context)
            transcript = self._read_transcript(context)
            self._write_transcript_assets(transcript, context, preserve_existing=True)
            current_manifest = running_manifest

            def on_softsub_progress(progress: float) -> None:
                nonlocal current_manifest
                self._raise_if_cancelled(context)
                current_manifest = current_manifest.model_copy(update={"progress": min(progress, 0.999)})
                self._emit_running(context, current_manifest, None)

            self._render_softsub_output(context, run_options, on_softsub_progress)
            self._raise_if_cancelled(context)
            timings = {**manifest.timings, "render_softsub_sec": round(time.perf_counter() - started_at, 3)}
            updated_manifest = running_manifest.model_copy(
                update={
                    "status": "completed",
                    "stage": "completed",
                    "progress": 1.0,
                    "outputs": self._collect_existing_outputs(context),
                    "timings": timings,
                    "errors": [],
                }
            )
            self._raise_if_cancelled(context)
            self._emit(context, updated_manifest, None)
            return updated_manifest
        except JobCancelledError as exc:
            cancelled_manifest = running_manifest.model_copy(
                update={
                    "status": "cancelled",
                    "stage": "cancelled",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, cancelled_manifest, None)
            return cancelled_manifest
        except Exception as exc:
            failed_manifest = running_manifest.model_copy(
                update={
                    "status": "completed_with_errors",
                    "stage": "render_softsub_failed",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, failed_manifest, None)
            raise

    def render_voiceover(self, job_id: str, options: PipelineRunOptions | None = None) -> JobManifest:
        run_options = options or PipelineRunOptions(generate_voiceover=True)
        context, manifest = self._require_job(job_id)
        running_manifest = manifest.model_copy(
            update={
                "status": "running",
                "stage": "rendering_voiceover",
                "progress": 0.0,
            }
        )
        self._emit(context, running_manifest, None)
        started_at = time.perf_counter()

        try:
            self._raise_if_cancelled(context)
            transcript = self._read_transcript(context)
            self._write_transcript_assets(transcript, context, preserve_existing=True)
            render_warnings: list[str] = []
            has_original_audio = bool(manifest.metadata and manifest.metadata.audio_stream_index is not None)
            current_manifest = running_manifest

            def on_voiceover_progress(progress: float) -> None:
                nonlocal current_manifest
                self._raise_if_cancelled(context)
                current_manifest = current_manifest.model_copy(
                    update={"progress": min(progress, 0.999)}
                )
                self._emit_running(context, current_manifest, None)

            self._render_voiceover_output(
                context,
                transcript,
                run_options,
                render_warnings,
                has_original_audio,
                on_voiceover_progress,
            )
            self._raise_if_cancelled(context)
            timings = {**manifest.timings, "render_voiceover_sec": round(time.perf_counter() - started_at, 3)}
            updated_manifest = running_manifest.model_copy(
                update={
                    "status": "completed_with_errors" if render_warnings else "completed",
                    "stage": "completed",
                    "progress": 1.0,
                    "outputs": self._collect_existing_outputs(context),
                    "timings": timings,
                    "errors": render_warnings,
                }
            )
            self._raise_if_cancelled(context)
            self._emit(context, updated_manifest, None)
            return updated_manifest
        except JobCancelledError as exc:
            cancelled_manifest = running_manifest.model_copy(
                update={
                    "status": "cancelled",
                    "stage": "cancelled",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, cancelled_manifest, None)
            return cancelled_manifest
        except Exception as exc:
            failed_manifest = running_manifest.model_copy(
                update={
                    "status": "completed_with_errors",
                    "stage": "render_voiceover_failed",
                    "progress": 1.0,
                    "errors": [str(exc)],
                    "outputs": self._collect_existing_outputs(context),
                }
            )
            self._emit(context, failed_manifest, None)
            raise

    def _render_hardsub_output(
        self,
        context: JobContext,
        options: PipelineRunOptions | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        if not context.srt_path.exists():
            raise ProcessError("Chua co file SRT de burn subtitle.")
        subtitle_path = context.srt_path
        if options and any(
            value is not None
            for value in (options.subtitle_font_size, options.subtitle_position_x, options.subtitle_position_y)
        ):
            transcript = self._read_transcript(context)
            subtitle_path = write_ass(
                transcript,
                context.ass_path,
                font_size=options.subtitle_font_size or 32,
                position_x_percent=options.subtitle_position_x or 50,
                bottom_percent=options.subtitle_position_y or 8,
            )
        duration_sec = self._duration_for_context(context)
        return self._run_video_render_with_auto_encoder(
            lambda render_config: burn_subtitles_into_video(
                context.input_video,
                subtitle_path,
                context.hardsub_video_path,
                self.config.ffmpeg_bin,
                render_config,
                duration_sec=duration_sec,
                progress_callback=progress_callback,
            ),
            options,
        )

    def _render_softsub_output(
        self,
        context: JobContext,
        options: PipelineRunOptions | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        if not context.original_srt_path.exists() or not context.srt_path.exists():
            raise ProcessError("Chưa có đủ phụ đề gốc và phụ đề tiếng Việt để mux softsub.")
        duration_sec = self._duration_for_context(context)
        subtitle_tracks = [
            (context.srt_path, "vie", "Phụ đề tiếng Việt"),
            (context.original_srt_path, "und", "Phụ đề gốc"),
        ]
        extra_tracks, default_subtitle_index = self._write_extra_subtitle_tracks(context, options, len(subtitle_tracks))
        subtitle_tracks.extend(extra_tracks)

        def render_softsub_with_config(active_render_config: RenderConfig) -> Path:
            context.softsub_command_path.write_text(
                build_mux_subtitle_tracks_command_string(
                    context.input_video,
                    subtitle_tracks,
                    context.softsub_video_path,
                    self.config.ffmpeg_bin,
                    active_render_config,
                    default_subtitle_index=default_subtitle_index,
                ),
                encoding="utf-8",
            )
            return mux_subtitle_tracks_into_video(
                context.input_video,
                subtitle_tracks,
                context.softsub_video_path,
                self.config.ffmpeg_bin,
                active_render_config,
                duration_sec=duration_sec,
                progress_callback=progress_callback,
                default_subtitle_index=default_subtitle_index,
            )

        return self._run_video_render_with_auto_encoder(
            render_softsub_with_config,
            options,
        )

    def _write_extra_subtitle_tracks(
        self,
        context: JobContext,
        options: PipelineRunOptions | None,
        base_track_count: int,
    ) -> tuple[list[tuple[Path, str, str]], int]:
        extra_tracks = list((options.extra_subtitle_tracks if options else []) or [])[:12]
        if not extra_tracks:
            return [], 0

        extra_dir = context.subtitles_dir / "extra_tracks"
        extra_dir.mkdir(parents=True, exist_ok=True)
        subtitle_tracks: list[tuple[Path, str, str]] = []
        default_subtitle_index = 0
        has_extra_default = False
        for index, track in enumerate(extra_tracks, start=1):
            content = str(track.content or "").strip()
            if not content:
                continue
            language = str(track.language or "und").strip().lower() or "und"
            if not SUBTITLE_LANGUAGE_RE.match(language):
                language = "und"
            title = str(track.title or track.file_name or f"Phụ đề {index}").strip() or f"Phụ đề {index}"
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(track.file_name or title).stem).strip("._") or f"track_{index}"
            suffix = Path(track.file_name or "").suffix.lower()
            if suffix not in {".srt", ".vtt", ".ass"}:
                suffix = ".srt"
            output_path = extra_dir / f"{index:02d}_{safe_name}{suffix}"
            output_path.write_text(content.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")
            subtitle_tracks.append((output_path, language, title))
            if track.is_default and not has_extra_default:
                default_subtitle_index = base_track_count + len(subtitle_tracks) - 1
                has_extra_default = True
        return subtitle_tracks, default_subtitle_index

    def _render_config_for_options(
        self,
        options: PipelineRunOptions | None = None,
        encoder: str | None = None,
        preset: str | None = None,
    ) -> RenderConfig:
        updates = self._render_encoder_updates(encoder=encoder, preset=preset)
        if not options:
            return self.config.render.model_copy(update=updates) if updates else self.config.render
        if options.subtitle_cover_mode:
            cover_mode = str(options.subtitle_cover_mode).strip().lower()
            updates["subtitle_cover_mode"] = cover_mode
            if cover_mode in {"none", "off", "disabled"}:
                updates["subtitle_cover_opacity"] = 0.0
        if options.subtitle_cover_opacity is not None:
            updates["cover_original_subtitles"] = options.subtitle_cover_opacity > 0
            updates["subtitle_cover_opacity"] = max(0.0, min(1.0, float(options.subtitle_cover_opacity)))
        if options.subtitle_cover_height_ratio is not None:
            updates["subtitle_cover_height_ratio"] = max(0.03, min(0.16, float(options.subtitle_cover_height_ratio)))
        if options.subtitle_cover_width_ratio is not None:
            updates["subtitle_cover_width_ratio"] = max(0.28, min(0.96, float(options.subtitle_cover_width_ratio)))
        if options.subtitle_font_size is not None:
            updates["subtitle_font_size"] = max(8.0, min(64.0, float(options.subtitle_font_size)))
        if options.subtitle_position_x is not None:
            updates["subtitle_position_x"] = max(10.0, min(90.0, float(options.subtitle_position_x)))
        if options.subtitle_position_y is not None:
            updates["subtitle_position_y"] = max(3.0, min(45.0, float(options.subtitle_position_y)))
        return self.config.render.model_copy(update=updates) if updates else self.config.render

    def _candidate_render_encoder_names(self, requested_encoder: str | None = None) -> list[str]:
        selected = (requested_encoder or self.config.render.encoder or "auto").strip().lower()
        if selected in {"nvidia", "intel", "amd", "cpu"}:
            return [selected] if selected == "cpu" else [selected, "cpu"]
        detected_encoders = self._detect_render_encoder_names()
        if detected_encoders:
            return [*detected_encoders, "cpu"]
        return ["cpu"]

    def _detect_render_encoder_names(self) -> list[str]:
        if self._detected_render_encoders is not None:
            return self._detected_render_encoders
        detected: list[str] = []
        gpu_text = self._read_windows_gpu_names().lower()
        if "nvidia" in gpu_text or "geforce" in gpu_text or "quadro" in gpu_text or "rtx" in gpu_text or "gtx" in gpu_text:
            detected.append("nvidia")
        if "intel" in gpu_text or "iris" in gpu_text or "arc" in gpu_text or "uhd graphics" in gpu_text:
            detected.append("intel")
        if "amd" in gpu_text or "radeon" in gpu_text:
            detected.append("amd")
        self._detected_render_encoders = detected
        return detected

    def _read_windows_gpu_names(self) -> str:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join [Environment]::NewLine",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        if completed.returncode != 0:
            return ""
        return completed.stdout or ""

    def _run_video_render_with_auto_encoder(
        self,
        renderer: Callable[[RenderConfig], Path],
        options: PipelineRunOptions | None = None,
        base_render_config: RenderConfig | None = None,
    ) -> Path:
        requested_encoder = options.render_encoder if options and options.render_encoder else None
        requested_preset = options.render_preset if options and options.render_preset else None
        errors: list[str] = []
        for encoder in self._candidate_render_encoder_names(requested_encoder):
            active_config = self._render_config_for_options(options, encoder=encoder, preset=requested_preset)
            if base_render_config:
                active_config = base_render_config.model_copy(
                    update={
                        "encoder": active_config.encoder,
                        "quality_preset": active_config.quality_preset,
                        "video_codec": active_config.video_codec,
                        "preset": active_config.preset,
                        "crf": active_config.crf,
                    }
                )
            try:
                return renderer(active_config)
            except DependencyError:
                raise
            except ProcessError as exc:
                if encoder == "cpu" or requested_encoder:
                    if errors:
                        raise ProcessError("\n\n".join([*errors, str(exc)])) from exc
                    raise
                errors.append(f"Không dùng được {encoder.upper()} GPU, tự chuyển sang encoder khác. Chi tiết: {exc}")
        raise ProcessError("Không xuất được video bằng GPU hoặc CPU.")

    def _render_encoder_updates(self, encoder: str | None = None, preset: str | None = None) -> dict[str, object]:
        selected_encoder = (encoder or "cpu").strip().lower()
        selected_preset = (preset or self.config.render.quality_preset or "balanced").strip().lower()
        selected_encoder = selected_encoder if selected_encoder in {"cpu", "nvidia", "intel", "amd"} else "cpu"
        selected_preset = selected_preset if selected_preset in {"fast", "balanced", "quality"} else "balanced"

        cpu_presets = {
            "fast": {"video_codec": "libx264", "preset": "veryfast", "crf": 22},
            "balanced": {"video_codec": "libx264", "preset": "medium", "crf": 20},
            "quality": {"video_codec": "libx264", "preset": "slow", "crf": 18},
        }
        hardware_presets = {
            "nvidia": {
                "fast": {"video_codec": "h264_nvenc", "preset": "fast", "crf": 23},
                "balanced": {"video_codec": "h264_nvenc", "preset": "medium", "crf": 20},
                "quality": {"video_codec": "h264_nvenc", "preset": "slow", "crf": 18},
            },
            "intel": {
                "fast": {"video_codec": "h264_qsv", "preset": "veryfast", "crf": 23},
                "balanced": {"video_codec": "h264_qsv", "preset": "medium", "crf": 20},
                "quality": {"video_codec": "h264_qsv", "preset": "slow", "crf": 18},
            },
            "amd": {
                "fast": {"video_codec": "h264_amf", "preset": "speed", "crf": 23},
                "balanced": {"video_codec": "h264_amf", "preset": "balanced", "crf": 20},
                "quality": {"video_codec": "h264_amf", "preset": "quality", "crf": 18},
            },
        }
        updates = (hardware_presets.get(selected_encoder, cpu_presets)).get(selected_preset, cpu_presets["balanced"])
        return {**updates, "encoder": selected_encoder, "quality_preset": selected_preset}

    def _render_voiceover_output(
        self,
        context: JobContext,
        transcript: TranscriptDocument,
        options: PipelineRunOptions,
        warnings: list[str] | None = None,
        has_original_audio: bool = True,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        def emit_voiceover_progress(value: float) -> None:
            if progress_callback:
                progress_callback(value)

        emit_voiceover_progress(0.02)
        tts_backend = EdgeTTSBackend(self.config.tts, voice_name=options.voice_name)
        clips = tts_backend.synthesize_segments(
            transcript.segments,
            context.tts_dir,
            progress_callback=lambda value: emit_voiceover_progress(0.02 + value * 0.43),
        )
        emit_voiceover_progress(0.45)
        if tts_backend.warnings:
            if warnings is not None:
                warnings.extend(tts_backend.warnings)
        duration_sec = self._duration_for_context(context)
        mixed_audio = mix_voiceover_audio(
            input_video=context.input_video,
            clips=clips,
            output_audio=context.voiceover_audio_path,
            filter_script_path=context.voiceover_filter_path,
            ffmpeg_bin=self.config.ffmpeg_bin,
            render_config=self.config.render,
            background_audio_gain=(
                options.background_audio_gain
                if options.background_audio_gain is not None
                else self.config.tts.background_audio_gain
            ),
            voiceover_gain=(
                options.voiceover_gain if options.voiceover_gain is not None else self.config.tts.voiceover_gain
            ),
            has_original_audio=has_original_audio,
            duration_sec=duration_sec,
            progress_callback=lambda value: emit_voiceover_progress(0.45 + value * 0.2),
        )
        emit_voiceover_progress(0.65)
        return render_video_with_replaced_audio(
            input_video=context.input_video,
            audio_path=mixed_audio,
            output_video=context.voiceover_video_path,
            ffmpeg_bin=self.config.ffmpeg_bin,
            render_config=self.config.render,
            duration_sec=duration_sec,
            progress_callback=lambda value: emit_voiceover_progress(0.65 + value * 0.35),
        )

    def _duration_for_context(self, context: JobContext) -> float:
        manifest = self.jobs.load_manifest(context.job_id)
        if manifest and manifest.metadata and manifest.metadata.duration_sec:
            return float(manifest.metadata.duration_sec)
        if context.transcript_json_path.exists():
            transcript = self._read_transcript(context)
            segment_duration = max((float(segment.end) for segment in transcript.segments), default=0.0)
            return max(float(transcript.duration_sec or 0), segment_duration)
        return 0.0

    def _require_job(self, job_id: str) -> tuple[JobContext, JobManifest]:
        manifest = self.jobs.load_manifest(job_id)
        if manifest is None:
            raise ConfigurationError(f"Khong tim thay job '{job_id}'.")
        context = self.jobs.get_context(job_id, input_video=Path(manifest.input_video))
        return context, manifest

    def _read_transcript(self, context: JobContext) -> TranscriptDocument:
        if not context.transcript_json_path.exists():
            raise ProcessError(
                "Chưa có bản nhận dạng giọng nói cho job này. Hãy chạy xử lý video xong trước, rồi mới bấm Dịch lại sang tiếng Việt."
            )
        return TranscriptDocument.model_validate_json(context.transcript_json_path.read_text(encoding="utf-8"))

    def _write_transcript_assets(
        self,
        transcript: TranscriptDocument,
        context: JobContext,
        preserve_existing: bool,
    ) -> TranscriptDocument:
        transcript.segments = format_segments_for_subtitles(
            transcript.segments,
            self.config.subtitles,
            preserve_existing=preserve_existing,
        )
        self._write_transcript_json(transcript, context.transcript_json_path)
        write_srt(transcript, context.original_srt_path, text_mode="source")
        write_srt(transcript, context.srt_path)
        write_vtt(transcript, context.vtt_path)
        return transcript

    def _normalize_segments(self, segments: list[TranscriptSegment], duration_sec: float) -> list[TranscriptSegment]:
        if not segments:
            raise ProcessError("Can it nhat mot segment de luu transcript.")

        normalized: list[TranscriptSegment] = []
        ordered_segments = sorted(segments, key=lambda item: (item.start, item.end, item.id))
        for index, segment in enumerate(ordered_segments, start=1):
            start = max(0.0, float(segment.start))
            end = max(start + 0.2, float(segment.end))
            if duration_sec > 0:
                start = min(start, max(duration_sec - 0.2, 0.0))
                end = min(end, duration_sec)
                if end <= start:
                    end = min(duration_sec, start + 0.2)
                    start = max(0.0, end - 0.2)
            normalized.append(
                self._normalized_transcript_segment(
                    segment=segment,
                    index=index,
                    start=start,
                    end=end,
                )
            )
        return normalized

    def _normalized_transcript_segment(
        self,
        segment: TranscriptSegment,
        index: int,
        start: float,
        end: float,
    ) -> TranscriptSegment:
        source_text = " ".join(segment.text.split())
        translated_text = " ".join((segment.translated_text or segment.text).split())
        subtitle_text = (segment.subtitle_text or "").strip()
        if translated_text and translated_text != source_text and " ".join(subtitle_text.split()) == source_text:
            subtitle_text = translated_text
        return TranscriptSegment(
            id=index,
            start=round(start, 3),
            end=round(end, 3),
            text=source_text,
            translated_text=translated_text,
            subtitle_text=subtitle_text or None,
            speaker=(segment.speaker or "").strip() or None,
            voice_name=(segment.voice_name or "").strip() or None,
        )

    def _duration_for_imported_segments(self, segments: list[TranscriptSegment], manifest: JobManifest) -> float:
        metadata_duration = float(manifest.metadata.duration_sec or 0) if manifest.metadata else 0.0
        segment_duration = max((float(segment.end) for segment in segments), default=0.0)
        return max(metadata_duration, segment_duration)

    def _collect_existing_outputs(self, context: JobContext) -> dict[str, str]:
        candidates = {
            "audio_wav": context.extracted_audio_path,
            "waveform_json": context.waveform_json_path,
            "transcript_json": context.transcript_json_path,
            "source_subtitle_srt": context.original_srt_path,
            "subtitle_srt": context.srt_path,
            "subtitle_vtt": context.vtt_path,
            "subtitle_ass": context.ass_path,
            "video_hardsub": context.hardsub_video_path,
            "video_softsub": context.softsub_video_path,
            "video_softsub_ffmpeg": context.softsub_command_path,
            "voiceover_audio": context.voiceover_audio_path,
            "video_voiceover": context.voiceover_video_path,
        }
        return {key: str(path) for key, path in candidates.items() if path.exists()}

    def _invalidate_render_outputs(self, context: JobContext) -> None:
        for path in (
            context.hardsub_video_path,
            context.softsub_video_path,
            context.softsub_command_path,
            context.voiceover_audio_path,
            context.voiceover_video_path,
            context.voiceover_filter_path,
        ):
            if path.exists():
                path.unlink()

    def _write_transcript_json(self, transcript: TranscriptDocument, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(transcript.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _emit(self, context: JobContext, manifest: JobManifest, progress_hook: ProgressHook | None) -> None:
        self.jobs.write_manifest(context, manifest)
        if progress_hook:
            progress_hook(manifest)

