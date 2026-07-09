from celery import Celery
from kombu import Queue
from config import settings

celery_app = Celery(
    "worker",
    broker=settings.rabbitmq_url,
    backend="redis://redis:6379"
)

celery_app.conf.queues = (
    Queue("evaluation"),
    Queue("ingestion")
)

celery_app.conf.task_default_queue = "evaluation"