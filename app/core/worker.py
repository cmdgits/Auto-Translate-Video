from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.jobs import JobContext
from app.core.pipeline import VideoTranslationPipeline
from app.models import JobManifest, JobTaskType, PipelineRunOptions, sanitize_pipeline_options

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueuedTask:
    context: JobContext
    task_type: JobTaskType
    options: PipelineRunOptions


class JobWorkerService:
    def __init__(self, pipeline_factory: Callable[[], VideoTranslationPipeline]) -> None:
        self.pipeline_factory = pipeline_factory
        self._queue: queue.Queue[QueuedTask] = queue.Queue()
        self._active_ids: set[str] = set()
        self._retry_timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._scanner: threading.Thread | None = None
        self._started = False
        self._scanning = False
        self._current_job_id: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._worker = threading.Thread(target=self._run, name="auto-translate-worker-service", daemon=True)
            self._worker.start()

    def start_scanner(self, interval_sec: float = 5.0) -> None:
        self.start()
        with self._lock:
            if self._scanning:
                return
            self._scanning = True
            self._scanner = threading.Thread(
                target=self._scan_loop,
                args=(max(1.0, interval_sec),),
                name="auto-translate-worker-scanner",
                daemon=True,
            )
            self._scanner.start()

    def enqueue(
        self,
        context: JobContext,
        options: PipelineRunOptions,
        task_type: JobTaskType = "process",
        *,
        update_manifest: bool = True,
    ) -> bool:
        self.start()
        with self._lock:
            if context.job_id in self._active_ids:
                return False
            self._active_ids.add(context.job_id)
            if update_manifest:
                self._prepare_manifest(context, task_type, options)
            self._queue.put(QueuedTask(context=context, task_type=task_type, options=options))
            return True

    def enqueue_existing(self, job_id: str, task_type: JobTaskType, options: PipelineRunOptions | None = None) -> JobManifest:
        pipeline = self.pipeline_factory()
        manifest = pipeline.jobs.load_manifest(job_id)
        if manifest is None:
            raise ValueError("Không tìm thấy tác vụ.")
        context = pipeline.jobs.get_context(job_id, input_video=Path(manifest.input_video))
        run_options = options or PipelineRunOptions()
        if not self.enqueue(context, run_options, task_type=task_type, update_manifest=True):
            existing_manifest = pipeline.jobs.load_manifest(job_id)
            return existing_manifest or manifest
        return pipeline.jobs.load_manifest(job_id) or manifest

    def cancel(self, job_id: str) -> JobManifest:
        manifest = self.pipeline_factory().cancel_job(job_id)
        self._finish_task(job_id)
        return manifest

    def resume_pending(self) -> int:
        self.start()
        return self.scan_pending()

    def scan_pending(self) -> int:
        resumed = 0
        pipeline = self.pipeline_factory()
        for manifest in pipeline.jobs.list_manifests():
            if manifest.status not in {"queued", "running"}:
                continue
            if manifest.status == "cancelled":
                continue
            context = pipeline.jobs.get_context(manifest.job_id, input_video=Path(manifest.input_video))
            options = PipelineRunOptions.model_validate(manifest.options or {})
            task_type = manifest.task_type or self._infer_task_type(manifest.stage)
            if self.enqueue(context, options, task_type=task_type, update_manifest=False):
                resumed += 1
        return resumed

    def mark_stale_running_jobs_failed(self) -> int:
        return 0

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "started": self._started,
                "queued_count": self._queue.qsize() + len(self._retry_timers),
                "queued_ids": sorted(self._active_ids),
                "retrying_ids": sorted(self._retry_timers),
                "current_job_id": self._current_job_id,
                "scanner_started": self._scanning,
            }

    def _scan_loop(self, interval_sec: float) -> None:
        while True:
            try:
                self.scan_pending()
            except Exception:
                logger.exception("Worker scanner failed")
            time.sleep(interval_sec)

    def _prepare_manifest(self, context: JobContext, task_type: JobTaskType, options: PipelineRunOptions) -> None:
        pipeline = self.pipeline_factory()
        manifest = pipeline.jobs.load_manifest(context.job_id)
        if manifest is None:
            return
        max_attempts = self._max_attempts(pipeline)
        updated_manifest = manifest.model_copy(
            update={
                "status": "queued",
                "stage": self._stage_for_task(task_type),
                "progress": 0.0,
                "task_type": task_type,
                "options": {**(manifest.options or {}), **sanitize_pipeline_options(options)},
                "retry_attempt": 0,
                "retry_max_attempts": max_attempts,
                "retry_next_at": None,
                "retry_last_error": None,
                "errors": [],
            }
        )
        pipeline.jobs.update_manifest(updated_manifest)

    def _run(self) -> None:
        while True:
            queued_task = self._queue.get()
            with self._lock:
                self._current_job_id = queued_task.context.job_id
            try:
                if self._is_cancelled(queued_task):
                    self._finish_task(queued_task.context.job_id)
                    continue
                self._mark_attempt_started(queued_task)
                self._execute(queued_task)
                self._finish_task(queued_task.context.job_id)
            except Exception as exc:
                logger.exception("Worker task failed: %s", queued_task.context.job_id)
                if self._is_cancelled(queued_task):
                    self._finish_task(queued_task.context.job_id)
                elif self._schedule_retry(queued_task, exc):
                    pass
                else:
                    self._mark_failed(queued_task, exc)
                    self._finish_task(queued_task.context.job_id)
            finally:
                with self._lock:
                    if self._current_job_id == queued_task.context.job_id:
                        self._current_job_id = None
                self._queue.task_done()

    def _execute(self, queued_task: QueuedTask) -> JobManifest:
        pipeline = self.pipeline_factory()
        if queued_task.task_type == "process":
            return pipeline.process_job(queued_task.context, queued_task.options)
        if queued_task.task_type == "translate":
            return pipeline.translate_transcript(queued_task.context.job_id, queued_task.options)
        if queued_task.task_type == "render_hardsub":
            return pipeline.render_hardsub(queued_task.context.job_id, queued_task.options)
        if queued_task.task_type == "render_softsub":
            return pipeline.render_softsub(queued_task.context.job_id, queued_task.options)
        if queued_task.task_type == "render_voiceover":
            options = queued_task.options.model_copy(update={"generate_voiceover": True})
            return pipeline.render_voiceover(queued_task.context.job_id, options)
        raise ValueError(f"Không hỗ trợ loại tác vụ: {queued_task.task_type}")

    def _mark_attempt_started(self, queued_task: QueuedTask) -> None:
        pipeline = self.pipeline_factory()
        manifest = pipeline.jobs.load_manifest(queued_task.context.job_id)
        if manifest is None:
            return
        attempt = max(0, manifest.retry_attempt) + 1
        pipeline.jobs.update_manifest(
            manifest.model_copy(
                update={
                    "status": "queued",
                    "stage": self._stage_for_task(queued_task.task_type),
                    "task_type": queued_task.task_type,
                    "retry_attempt": attempt,
                    "retry_max_attempts": self._max_attempts(pipeline),
                    "retry_next_at": None,
                }
            )
        )

    def _schedule_retry(self, queued_task: QueuedTask, exc: Exception) -> bool:
        pipeline = self.pipeline_factory()
        manifest = pipeline.jobs.load_manifest(queued_task.context.job_id)
        if manifest is None:
            return False
        max_attempts = self._max_attempts(pipeline)
        attempt = max(1, manifest.retry_attempt)
        if attempt >= max_attempts:
            return False
        delay = self._retry_delay(pipeline, attempt)
        next_at = time.time() + delay
        retry_manifest = manifest.model_copy(
            update={
                "status": "queued",
                "stage": "retry_waiting",
                "progress": min(manifest.progress or 0.0, 0.99),
                "task_type": queued_task.task_type,
                "retry_attempt": attempt,
                "retry_max_attempts": max_attempts,
                "retry_next_at": next_at,
                "retry_last_error": str(exc),
                "errors": [f"Lần {attempt}/{max_attempts} lỗi: {exc}. Sẽ thử lại sau {int(delay)} giây."],
            }
        )
        pipeline.jobs.update_manifest(retry_manifest)
        timer = threading.Timer(delay, self._requeue_retry, args=(queued_task,))
        timer.daemon = True
        with self._lock:
            self._retry_timers[queued_task.context.job_id] = timer
        timer.start()
        return True

    def _requeue_retry(self, queued_task: QueuedTask) -> None:
        with self._lock:
            self._retry_timers.pop(queued_task.context.job_id, None)
        if self._is_cancelled(queued_task):
            self._finish_task(queued_task.context.job_id)
            return
        self._queue.put(queued_task)

    def _mark_failed(self, queued_task: QueuedTask, exc: Exception) -> None:
        pipeline = self.pipeline_factory()
        manifest = pipeline.jobs.load_manifest(queued_task.context.job_id)
        if manifest is None:
            return
        pipeline.jobs.update_manifest(
            manifest.model_copy(
                update={
                    "status": "failed",
                    "stage": self._failed_stage_for_task(queued_task.task_type),
                    "progress": 1.0,
                    "retry_last_error": str(exc),
                    "errors": [str(exc)],
                }
            )
        )

    def _finish_task(self, job_id: str) -> None:
        with self._lock:
            self._active_ids.discard(job_id)
            timer = self._retry_timers.pop(job_id, None)
        if timer:
            timer.cancel()

    def _is_cancelled(self, queued_task: QueuedTask) -> bool:
        manifest = self.pipeline_factory().jobs.load_manifest(queued_task.context.job_id)
        return bool(manifest and manifest.status == "cancelled")

    def _max_attempts(self, pipeline: VideoTranslationPipeline) -> int:
        return max(1, int(pipeline.config.worker.max_attempts))

    def _retry_delay(self, pipeline: VideoTranslationPipeline, failed_attempt: int) -> float:
        config = pipeline.config.worker
        delay = float(config.backoff_initial_sec) * (float(config.backoff_factor) ** max(0, failed_attempt - 1))
        return max(0.0, min(delay, float(config.backoff_max_sec)))

    def _infer_task_type(self, stage: str) -> JobTaskType:
        if stage in {"translating", "subtitle_translated", "translation_failed"}:
            return "translate"
        if stage in {"rendering_hardsub", "render_hardsub_failed"}:
            return "render_hardsub"
        if stage in {"rendering_softsub", "render_softsub_failed"}:
            return "render_softsub"
        if stage in {"rendering_voiceover", "render_voiceover_failed"}:
            return "render_voiceover"
        return "process"

    def _stage_for_task(self, task_type: JobTaskType) -> str:
        return {
            "process": "queued",
            "translate": "translating",
            "render_hardsub": "rendering_hardsub",
            "render_softsub": "rendering_softsub",
            "render_voiceover": "rendering_voiceover",
        }[task_type]

    def _failed_stage_for_task(self, task_type: JobTaskType) -> str:
        return {
            "process": "failed",
            "translate": "translation_failed",
            "render_hardsub": "render_hardsub_failed",
            "render_softsub": "render_softsub_failed",
            "render_voiceover": "render_voiceover_failed",
        }[task_type]
