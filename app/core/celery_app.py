from __future__ import annotations

from celery import Celery

from app.config import AppConfig


def create_celery_app() -> Celery:
    config = AppConfig.load()
    celery_app = Celery(
        "auto_translate_video",
        broker=config.worker.broker_url,
        backend=config.worker.result_backend,
        include=["app.core.celery_tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )
    return celery_app


celery_app = create_celery_app()
