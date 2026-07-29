import logging

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from sqlalchemy.exc import SQLAlchemyError

from app.celery_app import celery
from app.config import Config
from app.max_client import MaxClient
from app.openai_client import generate_festival_answer

logger = logging.getLogger(__name__)


@celery.task(
    autoretry_for=(
        httpx.HTTPError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    ),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def answer_message(
    text: str,
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    with MaxClient(
        token=Config.MAX_BOT_TOKEN,
        base_url=Config.MAX_API_BASE_URL,
        ca_cert_path=Config.MAX_CA_CERT_PATH,
    ) as client:
        if chat_id is not None:
            try:
                client.send_action(chat_id=chat_id, action="typing_on")
            except httpx.HTTPError:
                # The typing indicator is optional and must not prevent a reply.
                logger.warning(
                    "Could not send typing indicator to MAX",
                    exc_info=True,
                )

        answer = generate_festival_answer(text)

        client.send_message(
            text=answer,
            chat_id=chat_id,
            user_id=user_id,
        )


@celery.task(
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_main_menu(
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    send_main_menu_message(chat_id=chat_id, user_id=user_id)


def send_main_menu_message(
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    with MaxClient(
        token=Config.MAX_BOT_TOKEN,
        base_url=Config.MAX_API_BASE_URL,
        ca_cert_path=Config.MAX_CA_CERT_PATH,
    ) as client:
        bot = client.get_me()
        username = bot.get("username")
        if not username:
            raise ValueError("MAX bot username is missing")

        client.send_message(
            text=(
                "Добро пожаловать на ГАЗ!ФЕСТ 💙\n\n"
                "Откройте приложение, чтобы посмотреть программу, "
                "активности и фестивальное лото."
            ),
            chat_id=chat_id,
            user_id=user_id,
            attachments=[
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {
                                    "type": "open_app",
                                    "text": "Открыть приложение",
                                    "web_app": username,
                                }
                            ]
                        ]
                    },
                }
            ],
        )


@celery.task(
    autoretry_for=(httpx.HTTPError, SQLAlchemyError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def register_user_and_send_main_menu(
    *,
    max_user_id: int,
    chat_id: int,
    timestamp: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
) -> None:
    # Import locally to avoid a circular import while Flask registers routes.
    from app import create_app
    from app.user_service import record_bot_started

    app = create_app()
    with app.app_context():
        record_bot_started(
            max_user_id=max_user_id,
            chat_id=chat_id,
            timestamp=timestamp,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )

    send_main_menu_message(chat_id=chat_id, user_id=max_user_id)
