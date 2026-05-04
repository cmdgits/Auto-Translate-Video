from __future__ import annotations

from celery.exceptions import Ignore

from app.config import AppConfig
from app.core.celery_app import celery_app
from app.core.task_runner import execute_job_task
from app.models import JobTaskType


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def run_job_task(self, job_id: str, task_type: JobTaskType, options_payload: dict[str, object] | None = None) -> dict:
    config = AppConfig.load()
    self.max_retries = max(0, int(config.worker.max_attempts) - 1)
    manifest = execute_job_task(job_id, task_type, options_payload)
    if manifest.status == "cancelled":
        raise Ignore()
    return manifest.model_dump(mode="json")
