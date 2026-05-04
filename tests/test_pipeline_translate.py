from pathlib import Path
import shutil
import uuid
from unittest.mock import patch

from app.config import AppConfig
from app.core.pipeline import VideoTranslationPipeline
from app.models import JobManifest, PipelineRunOptions, TranscriptDocument, TranscriptSegment


def test_pipeline_retranslates_existing_transcript() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"translate_{uuid.uuid4().hex}"
    try:
        config = AppConfig.load().model_copy(
            update={"directories": AppConfig.load().directories.model_copy(update={"jobs_dir": jobs_root})}
        )
        pipeline = VideoTranslationPipeline(config)
        context = pipeline.jobs.get_context("translate_job", input_video=jobs_root / "source.mp4")
        context.root_dir.mkdir(parents=True)
        context.data_dir.mkdir(parents=True)
        context.subtitles_dir.mkdir(parents=True)
        pipeline.jobs.write_manifest(
            context,
            JobManifest(
                job_id=context.job_id,
                status="completed",
                stage="completed",
                input_video=str(context.input_video),
                output_dir=str(context.root_dir),
                detected_language="zh",
            ),
        )
        pipeline._write_transcript_json(
            TranscriptDocument(
                job_id=context.job_id,
                video_path=str(context.input_video),
                detected_language="zh",
                duration_sec=2.0,
                segments=[TranscriptSegment(id=1, start=0.0, end=1.0, text="hello", translated_text="hello")],
            ),
            context.transcript_json_path,
        )

        class FakeTranslator:
            def translate_segments(self, segments, source_language: str, target_language: str):
                return ["xin chào" for _ in segments]

        with patch("app.core.pipeline.build_translator", lambda config, options: FakeTranslator()):
            manifest = pipeline.translate_transcript(context.job_id, PipelineRunOptions(translator_backend="gemini"))

        transcript = pipeline.load_transcript(context.job_id)
        assert manifest.stage == "subtitle_translated"
        assert transcript.segments[0].translated_text == "xin chào"
        assert transcript.segments[0].subtitle_text == "xin chào"
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)


def test_pipeline_saves_imported_subtitles_without_existing_transcript() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"import_subtitle_{uuid.uuid4().hex}"
    try:
        config = AppConfig.load().model_copy(
            update={"directories": AppConfig.load().directories.model_copy(update={"jobs_dir": jobs_root})}
        )
        pipeline = VideoTranslationPipeline(config)
        context = pipeline.jobs.get_context("import_job", input_video=jobs_root / "source.mp4")
        context.root_dir.mkdir(parents=True)
        pipeline.jobs.write_manifest(
            context,
            JobManifest(
                job_id=context.job_id,
                status="completed",
                stage="completed",
                input_video=str(context.input_video),
                output_dir=str(context.root_dir),
                detected_language=None,
            ),
        )

        manifest = pipeline.save_transcript(
            context.job_id,
            [
                TranscriptSegment(
                    id=7,
                    start=1.0,
                    end=2.4,
                    text="Xin chào",
                    translated_text="Xin chào",
                    subtitle_text="Xin chào",
                )
            ],
        )

        transcript = pipeline.load_transcript(context.job_id)
        assert manifest.stage == "subtitle_saved"
        assert manifest.detected_language == "imported"
        assert transcript.duration_sec == 2.4
        assert transcript.segments[0].id == 1
        assert transcript.segments[0].subtitle_text == "Xin chào"
        assert context.srt_path.exists()
        assert context.vtt_path.exists()
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)
