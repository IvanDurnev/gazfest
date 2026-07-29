import hmac

from flask import Blueprint, current_app, jsonify, render_template, request
from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.application_service import (
    DuplicateApplicationError,
    ParticipationApplicationRequest,
    create_participation_application,
    list_participation_applications,
)
from app.max_webapp_auth import (
    InvalidMaxInitDataError,
    MaxMiniAppUser,
    validate_max_init_data,
)
from app.models import BotStartedUpdate, MessageCreatedUpdate
from app.tasks import (
    answer_message,
    register_user_and_send_main_menu,
    send_main_menu,
)

api = Blueprint("api", __name__)


def get_redis() -> Redis:
    return Redis.from_url(
        current_app.config["REDIS_URL"],
        decode_responses=True,
    )


@api.get("/health")
def health():
    return jsonify(status="ok")


@api.get("/max/miniapp")
def miniapp():
    return render_template("miniapp.html")


def get_max_miniapp_user() -> MaxMiniAppUser | None:
    try:
        return validate_max_init_data(
            request.headers.get("X-Max-WebApp-Data", ""),
            bot_token=current_app.config["MAX_BOT_TOKEN"],
            max_age_seconds=current_app.config["MAX_MINIAPP_AUTH_MAX_AGE_SECONDS"],
        )
    except InvalidMaxInitDataError:
        return None


def unauthorized_miniapp_response():
    return (
        jsonify(
            error="unauthorized",
            message="Откройте приложение заново через бот в MAX.",
        ),
        401,
    )


def serialize_application(application):
    return {
        "id": application.id,
        "activity": application.activity,
        "first_name": application.first_name,
        "last_name": application.last_name,
        "age": application.age,
        "equipment": application.equipment,
        "equipment_other": application.equipment_other,
        "phone": application.phone,
        "performance_description": application.performance_description,
        "status": application.status,
        "created_at": application.created_at.isoformat(),
    }


@api.get("/max/miniapp/applications")
def get_applications():
    max_user = get_max_miniapp_user()
    if max_user is None:
        return unauthorized_miniapp_response()

    try:
        applications = list_participation_applications(max_user.user_id)
    except SQLAlchemyError:
        current_app.logger.exception("Could not load participation applications")
        return (
            jsonify(
                error="database_unavailable",
                message="Не удалось загрузить заявки. Попробуйте ещё раз.",
            ),
            503,
        )

    return jsonify(
        applications=[
            serialize_application(application) for application in applications
        ]
    )


@api.post("/max/miniapp/applications")
def create_application():
    max_user = get_max_miniapp_user()
    if max_user is None:
        return unauthorized_miniapp_response()

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="invalid_json"), 400

    try:
        application_data = ParticipationApplicationRequest.model_validate(payload)
    except ValidationError:
        return (
            jsonify(
                error="invalid_application",
                message="Проверьте правильность заполнения полей.",
            ),
            422,
        )

    try:
        application = create_participation_application(
            application_data,
            max_user=max_user,
        )
    except DuplicateApplicationError:
        return (
            jsonify(
                error="duplicate_application",
                message="Вы уже подали заявку на эту активность.",
            ),
            409,
        )
    except SQLAlchemyError:
        current_app.logger.exception("Could not save participation application")
        return (
            jsonify(
                error="database_unavailable",
                message="Не удалось сохранить заявку. Попробуйте ещё раз.",
            ),
            503,
        )

    return (
        jsonify(
            status="created",
            application_id=application.id,
        ),
        201,
    )


@api.post("/max/webhook")
def max_webhook():
    expected_secret = current_app.config["MAX_WEBHOOK_SECRET"]
    received_secret = request.headers.get("X-Max-Bot-Api-Secret", "")

    if not expected_secret or not hmac.compare_digest(
        received_secret,
        expected_secret,
    ):
        return jsonify(error="unauthorized"), 401

    if not request.is_json:
        return jsonify(error="JSON body required"), 415

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="invalid JSON body"), 400

    update_type = payload.get("update_type")

    if update_type == "bot_started":
        try:
            update = BotStartedUpdate.model_validate(payload)
        except ValidationError:
            return jsonify(error="invalid bot_started payload"), 400

        deduplication_key = f"max:started:{update.chat_id}:{update.timestamp}"
        try:
            is_new = get_redis().set(
                deduplication_key,
                "1",
                nx=True,
                ex=86_400,
            )
        except RedisError:
            current_app.logger.exception("Redis is unavailable")
            return jsonify(error="queue unavailable"), 503

        if not is_new:
            return jsonify(status="duplicate"), 200

        try:
            register_user_and_send_main_menu.delay(
                max_user_id=update.user.user_id,
                chat_id=update.chat_id,
                timestamp=update.timestamp,
                first_name=update.user.first_name,
                last_name=update.user.last_name,
                username=update.user.username,
            )
        except Exception:
            get_redis().delete(deduplication_key)
            current_app.logger.exception("Could not enqueue main menu")
            return jsonify(error="queue unavailable"), 503

        return jsonify(status="queued"), 200

    if update_type != "message_created":
        return jsonify(status="ignored"), 200

    try:
        update = MessageCreatedUpdate.model_validate(payload)
    except ValidationError:
        return jsonify(error="invalid message_created payload"), 400

    message = update.message
    text = message.body.text

    if message.sender is None or message.sender.is_bot or not text:
        return jsonify(status="ignored"), 200

    try:
        is_new = get_redis().set(
            f"max:update:{message.body.mid}",
            "1",
            nx=True,
            ex=86_400,
        )
    except RedisError:
        current_app.logger.exception("Redis is unavailable")
        return jsonify(error="queue unavailable"), 503

    if not is_new:
        return jsonify(status="duplicate"), 200

    task = (
        send_main_menu if text.strip().lower() in {"/start", "меню"} else answer_message
    )
    task_kwargs = {
        "chat_id": message.recipient.chat_id,
        "user_id": message.sender.user_id,
    }
    if task is answer_message:
        task_kwargs["text"] = text

    try:
        task.delay(**task_kwargs)
    except Exception:
        get_redis().delete(f"max:update:{message.body.mid}")
        current_app.logger.exception("Could not enqueue message")
        return jsonify(error="queue unavailable"), 503

    return jsonify(status="queued"), 200
