from celery import Celery
from kombu import Queue
from config import settings

celery_app = Celery(
    "worker",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["src.api.task"]
)
celery_app.set_default()

celery_app.conf.queues = (
    Queue("evaluation"),
    Queue("ingestion")
)

celery_app.conf.task_default_queue = "evaluation"