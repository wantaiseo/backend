"""
CiteKit – Celery Application
Job orchestration with Redis broker
"""

import sys
from celery import Celery
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "geo_compiler",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Windows-specific settings to avoid multiprocessing issues
if sys.platform == "win32":
    celery_app.conf.update(
        worker_pool="solo",  # Use solo pool on Windows
    )
