from celery import Celery

from app.config import Config

celery = Celery(
    "gaz",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.tasks.answer_message": {"queue": "answers"},
        "app.tasks.send_main_menu": {"queue": "system"},
        "app.tasks.register_user_and_send_main_menu": {"queue": "system"},
    },
)
