from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime
from collections.abc import Callable
from dataclasses import dataclass

from app.core.jobs import JobContext
from app.core.pipeline import VideoTranslationPipeline
from app.models import JobManifest, PipelineRunOptions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueuedJob:
    context: JobContext
    options: PipelineRunOptions


class JobQueue:
    def __init__(self, pipeline_factory: Callable[[], VideoTranslationPipeline]) -> None:
        self.pipeline_factory = pipeline_factory
        self._queue: queue.Queue[QueuedJob] = queue.Queue()
        self._queued_ids: set[str] = set()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._worker = threading.Thread(target=self._run, name="auto-translate-job-worker", daemon=True)
            self._worker.start()

    def enqueue(self, context: JobContext, options: PipelineRunOptions) -> bool:
        self.start()
        with self._lock:
            if context.job_id in self._queued_ids:
                return False
            self._queued_ids.add(context.job_id)
            self._queue.put(QueuedJob(context=context, options=options))
            return True

    def resume_pending(self) -> int:
        self.start()
        resumed = 0
        pipeline = self.pipeline_factory()
        for manifest in pipeline.jobs.list_manifests():
            if manifest.status not in {"queued", "running"}:
                continue
            context = pipeline.jobs.get_context(manifest.job_id)
            options = PipelineRunOptions.model_validate(manifest.options or {})
            if self.enqueue(context, options):
                resumed += 1
        return resumed

    def mark_stale_running_jobs_failed(self) -> int:
        marked = 0
        pipeline = self.pipeline_factory()
        for manifest in pipeline.jobs.list_manifests():
            if manifest.status not in {"queued", "running"}:
                continue
            updated_manifest = manifest.model_copy(
                update={
                    "status": "failed",
                    "stage": "failed",
                    "progress": 1.0,
                    "errors": [
                        "Tác vụ bị dừng giữa chừng do server/app đã tắt hoặc bị treo. Hãy xoá tác vụ này và chạy lại với model tiny/base."
                    ],
                    "timings": {
                        **manifest.timings,
                        "marked_stale_at": datetime.now().timestamp(),
                    },
                }
            )
            pipeline.jobs.update_manifest(updated_manifest)
            marked += 1
        return marked

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "started": self._started,
                "queued_count": self._queue.qsize(),
                "queued_ids": sorted(self._queued_ids),
            }

    def _run(self) -> None:
        while True:
            queued_job = self._queue.get()
            try:
                self.pipeline_factory().process_job(queued_job.context, queued_job.options)
            except Exception:
                logger.exception("Background job failed: %s", queued_job.context.job_id)
            finally:
                with self._lock:
                    self._queued_ids.discard(queued_job.context.job_id)
                self._queue.task_done()
