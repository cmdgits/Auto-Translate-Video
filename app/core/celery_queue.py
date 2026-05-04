from __future__ import annotations

from pathlib import Path

from app.core.pipeline import VideoTranslationPipeline
from app.core.worker import JobWorkerService
from app.models import JobManifest, JobTaskType, PipelineRunOptions, sanitize_pipeline_options


class CeleryJobQueue:
    def __init__(self, pipeline: VideoTranslationPipeline) -> None:
        self.pipeline = pipeline

    def start(self) -> None:
        return None

    def enqueue(
        self,
        context,
        options: PipelineRunOptions,
        task_type: JobTaskType = "process",
        *,
        update_manifest: bool = True,
    ) -> bool:
        if update_manifest:
            manifest = self.pipeline.jobs.load_manifest(context.job_id)
            if manifest:
                self.pipeline.jobs.update_manifest(self._queued_manifest(manifest, task_type, options))
        self._send_task(context.job_id, task_type, options)
        return True

    def enqueue_existing(self, job_id: str, task_type: JobTaskType, options: PipelineRunOptions | None = None) -> JobManifest:
        manifest = self.pipeline.jobs.load_manifest(job_id)
        if manifest is None:
            raise ValueError("Không tìm thấy tác vụ.")
        run_options = options or PipelineRunOptions()
        queued_manifest = self._queued_manifest(manifest, task_type, run_options)
        self.pipeline.jobs.update_manifest(queued_manifest)
        self._send_task(job_id, task_type, run_options)
        return self.pipeline.jobs.load_manifest(job_id) or queued_manifest

    def cancel(self, job_id: str) -> JobManifest:
        return self.pipeline.cancel_job(job_id)

    def resume_pending(self) -> int:
        resumed = 0
        for manifest in self.pipeline.jobs.list_manifests():
            if manifest.status not in {"queued", "running"}:
                continue
            task_type = manifest.task_type or JobWorkerService(lambda: self.pipeline)._infer_task_type(manifest.stage)
            options = PipelineRunOptions.model_validate(manifest.options or {})
            self._send_task(manifest.job_id, task_type, options)
            resumed += 1
        return resumed

    def snapshot(self) -> dict[str, object]:
        active_ids = [manifest.job_id for manifest in self.pipeline.jobs.list_manifests() if manifest.status in {"queued", "running"}]
        return {
            "started": True,
            "backend": "celery",
            "queued_count": len(active_ids),
            "queued_ids": active_ids,
        }

    def _queued_manifest(self, manifest: JobManifest, task_type: JobTaskType, options: PipelineRunOptions) -> JobManifest:
        return manifest.model_copy(
            update={
                "status": "queued",
                "stage": self._stage_for_task(task_type),
                "progress": 0.0,
                "task_type": task_type,
                "options": {**(manifest.options or {}), **sanitize_pipeline_options(options)},
                "retry_attempt": 0,
                "retry_max_attempts": max(1, int(self.pipeline.config.worker.max_attempts)),
                "retry_next_at": None,
                "retry_last_error": None,
                "errors": [],
            }
        )

    def _send_task(self, job_id: str, task_type: JobTaskType, options: PipelineRunOptions) -> None:
        from app.core.celery_tasks import run_job_task

        run_job_task.delay(job_id, task_type, options.model_dump(mode="json", exclude_none=True))

    def _stage_for_task(self, task_type: JobTaskType) -> str:
        return {
            "process": "queued",
            "translate": "translating",
            "render_hardsub": "rendering_hardsub",
            "render_softsub": "rendering_softsub",
            "render_voiceover": "rendering_voiceover",
        }[task_type]
