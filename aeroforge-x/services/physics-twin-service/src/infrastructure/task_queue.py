import os

from celery import Celery


celery_app = Celery(
    "physics_twin",
    broker=os.getenv("CELERY_BROKER", "redis://localhost:6379/2"),
    backend=os.getenv("CELERY_BACKEND", "redis://localhost:6379/3")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=14400,
    task_time_limit=14460
)