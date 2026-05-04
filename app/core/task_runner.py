from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.core.pipeline import VideoTranslationPipeline
from app.models import JobManifest, JobTaskType, PipelineRunOptions


def execute_job_task(job_id: str, task_type: JobTaskType, options_payload: dict[str, object] | None = None) -> JobManifest:
    pipeline = VideoTranslationPipeline(AppConfig.load())
    manifest = pipeline.jobs.load_manifest(job_id)
    if manifest is None:
        raise ValueError(f"Không tìm thấy tác vụ: {job_id}")
    if manifest.status == "cancelled":
        return manifest
    options = PipelineRunOptions.model_validate(options_payload or manifest.options or {})
    context = pipeline.jobs.get_context(job_id, input_video=Path(manifest.input_video))
    if task_type == "process":
        return pipeline.process_job(context, options)
    if task_type == "translate":
        return pipeline.translate_transcript(job_id, options)
    if task_type == "render_hardsub":
        return pipeline.render_hardsub(job_id, options)
    if task_type == "render_softsub":
        return pipeline.render_softsub(job_id, options)
    if task_type == "render_voiceover":
        return pipeline.render_voiceover(job_id, options.model_copy(update={"generate_voiceover": True}))
    raise ValueError(f"Không hỗ trợ loại tác vụ: {task_type}")
