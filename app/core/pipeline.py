from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from app.asr.faster_whisper_backend import FasterWhisperBackend
from app.config import AppConfig
from app.config import RenderConfig
from app.core.exceptions import ConfigurationError, JobCancelledError, ProcessError
from app.core.jobs import JobContext, JobManager
from app.media.audio_extract import extract_audio_to_wav
from app.media.probe import probe_video
from app.media.render import burn_subtitles_into_video, render_video_with_replaced_audio
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


def ensure_video_has_audio(metadata: VideoMetadata) -> None:
    if metadata.audio_stream_index is None:
        raise ProcessError(
            "Video nÃ y khÃ´ng cÃ³ luá»“ng Ã¢m thanh, nÃªn khÃ´ng thá»ƒ tÃ¡ch audio Ä‘á»ƒ nháº­n dáº¡ng giá»ng nÃ³i. "
            "HÃ£y chá»n video cÃ³ audio hoáº·c táº£i láº¡i báº£n cÃ³ Ã¢m thanh."
        )


class VideoTranslationPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.jobs = JobManager(config.directories.jobs_dir)

    def cancel_job(self, job_id: str, reason: str = "TÃ¡c vá»¥ Ä‘Ã£ Ä‘Æ°á»£c dá»«ng theo yÃªu cáº§u.") -> JobManifest:
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
            raise JobCancelledError(manifest.errors[0] if manifest.errors else "TÃ¡c vá»¥ Ä‘Ã£ Ä‘Æ°á»£c dá»«ng.")

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
        return burn_subtitles_into_video(
            context.input_video,
            subtitle_path,
            context.hardsub_video_path,
            self.config.ffmpeg_bin,
            self._render_config_for_options(options),
            duration_sec=duration_sec,
            progress_callback=progress_callback,
        )

    def _render_config_for_options(self, options: PipelineRunOptions | None = None) -> RenderConfig:
        if not options:
            return self.config.render
        updates = {}
        if options.subtitle_cover_mode:
            updates["subtitle_cover_mode"] = options.subtitle_cover_mode
        if options.subtitle_cover_opacity is not None:
            updates["cover_original_subtitles"] = options.subtitle_cover_opacity > 0
            updates["subtitle_cover_opacity"] = max(0.0, min(1.0, float(options.subtitle_cover_opacity)))
        if options.subtitle_cover_height_ratio is not None:
            updates["subtitle_cover_height_ratio"] = max(0.05, min(0.45, float(options.subtitle_cover_height_ratio)))
        return self.config.render.model_copy(update=updates) if updates else self.config.render

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
            background_audio_gain=options.background_audio_gain or self.config.tts.background_audio_gain,
            voiceover_gain=options.voiceover_gain or self.config.tts.voiceover_gain,
            has_original_audio=has_original_audio,
            duration_sec=duration_sec,
            progress_callback=lambda value: emit_voiceover_progress(0.45 + value * 0.2),
        )
        emit_voiceover_progress(0.65)
        hardsub_video = self._render_hardsub_output(
            context,
            options,
            progress_callback=lambda value: emit_voiceover_progress(0.65 + value * 0.2),
        )
        emit_voiceover_progress(0.85)
        return render_video_with_replaced_audio(
            input_video=hardsub_video,
            audio_path=mixed_audio,
            output_video=context.voiceover_video_path,
            ffmpeg_bin=self.config.ffmpeg_bin,
            render_config=self.config.render,
            duration_sec=duration_sec,
            progress_callback=lambda value: emit_voiceover_progress(0.85 + value * 0.15),
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
                "ChÆ°a cÃ³ báº£n nháº­n dáº¡ng giá»ng nÃ³i cho job nÃ y. HÃ£y cháº¡y xá»­ lÃ½ video xong trÆ°á»›c, rá»“i má»›i báº¥m Dá»‹ch láº¡i sang tiáº¿ng Viá»‡t."
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
        )

    def _duration_for_imported_segments(self, segments: list[TranscriptSegment], manifest: JobManifest) -> float:
        metadata_duration = float(manifest.metadata.duration_sec or 0) if manifest.metadata else 0.0
        segment_duration = max((float(segment.end) for segment in segments), default=0.0)
        return max(metadata_duration, segment_duration)

    def _collect_existing_outputs(self, context: JobContext) -> dict[str, str]:
        candidates = {
            "audio_wav": context.extracted_audio_path,
            "transcript_json": context.transcript_json_path,
            "source_subtitle_srt": context.original_srt_path,
            "subtitle_srt": context.srt_path,
            "subtitle_vtt": context.vtt_path,
            "subtitle_ass": context.ass_path,
            "video_hardsub": context.hardsub_video_path,
            "voiceover_audio": context.voiceover_audio_path,
            "video_voiceover": context.voiceover_video_path,
        }
        return {key: str(path) for key, path in candidates.items() if path.exists()}

    def _invalidate_render_outputs(self, context: JobContext) -> None:
        for path in (
            context.hardsub_video_path,
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

