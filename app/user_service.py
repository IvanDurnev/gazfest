from datetime import UTC, datetime

from app.extensions import db
from app.models import FestivalUser


def record_bot_started(
    *,
    max_user_id: int,
    chat_id: int,
    timestamp: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
) -> FestivalUser:
    started_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    user = db.session.get(FestivalUser, max_user_id)

    if user is None:
        user = FestivalUser(
            max_user_id=max_user_id,
            chat_id=chat_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            first_started_at=started_at,
            last_started_at=started_at,
        )
        db.session.add(user)
    else:
        user.chat_id = chat_id
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.last_started_at = started_at

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user
