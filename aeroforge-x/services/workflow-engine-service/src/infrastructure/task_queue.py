import os

from celery import Celery


celery_app = Celery(
    "workflow_engine",
    broker=os.getenv("CELERY_BROKER", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_BACKEND", "redis://localhost:6379/1")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1
)