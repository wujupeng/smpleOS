from __future__ import annotations

import os

from celery import Celery

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "aeroforge_cae",
    broker=REDIS_URL,
    backend=REDIS_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
    task_routes={
        "cae_center.infrastructure.celery_tasks.cfd_tasks.*": {"queue": "cfd"},
        "cae_center.infrastructure.celery_tasks.fea_tasks.*": {"queue": "fea"},
        "cae_center.infrastructure.celery_tasks.flutter_tasks.*": {"queue": "flutter"},
        "cae_center.infrastructure.celery_tasks.thermal_tasks.*": {"queue": "thermal"},
        "cae_center.infrastructure.celery_tasks.multiphysics_tasks.*": {"queue": "multiphysics"},
    },
    task_queues={
        "urgent": {
            "exchange": "urgent",
            "routing_key": "urgent",
        },
        "cfd": {
            "exchange": "cfd",
            "routing_key": "cfd",
        },
        "fea": {
            "exchange": "fea",
            "routing_key": "fea",
        },
        "flutter": {
            "exchange": "flutter",
            "routing_key": "flutter",
        },
        "thermal": {
            "exchange": "thermal",
            "routing_key": "thermal",
        },
        "multiphysics": {
            "exchange": "multiphysics",
            "routing_key": "multiphysics",
        },
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)