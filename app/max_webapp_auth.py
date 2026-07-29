import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InvalidMaxInitDataError(ValueError):
    pass


@dataclass(frozen=True)
class MaxMiniAppUser:
    user_id: int
    auth_date: int
    chat_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


def validate_max_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int,
    now: int | None = None,
) -> MaxMiniAppUser:
    if not init_data or not bot_token:
        raise InvalidMaxInitDataError("MAX init data is missing")

    try:
        pairs = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as exc:
        raise InvalidMaxInitDataError("MAX init data is malformed") from exc

    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise InvalidMaxInitDataError("MAX init data contains duplicate fields")

    params = dict(pairs)
    original_hash = params.pop("hash", None)
    if not original_hash:
        raise InvalidMaxInitDataError("MAX init data hash is missing")

    check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, original_hash):
        raise InvalidMaxInitDataError("MAX init data signature is invalid")

    try:
        auth_date = int(params["auth_date"])
        user_data = json.loads(params["user"])
        user_id = int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidMaxInitDataError("MAX user data is invalid") from exc

    current_time = int(time.time()) if now is None else now
    if auth_date > current_time + 60:
        raise InvalidMaxInitDataError("MAX init data is from the future")
    if current_time - auth_date > max_age_seconds:
        raise InvalidMaxInitDataError("MAX init data has expired")

    chat_id = None
    if params.get("chat"):
        try:
            chat_id = int(json.loads(params["chat"])["id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidMaxInitDataError("MAX chat data is invalid") from exc

    return MaxMiniAppUser(
        user_id=user_id,
        auth_date=auth_date,
        chat_id=chat_id,
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
    )
