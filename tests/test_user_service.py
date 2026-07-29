from datetime import UTC, datetime

from app.extensions import db
from app.models import FestivalUser
from app.user_service import record_bot_started


def test_record_bot_started_creates_user(app):
    with app.app_context():
        user = record_bot_started(
            max_user_id=42,
            chat_id=123,
            timestamp=1_722_000_000_000,
            first_name="Иван",
            last_name="Иванов",
            username="ivan",
        )

        assert user.max_user_id == 42
        assert user.chat_id == 123
        assert user.first_name == "Иван"
        assert user.first_started_at.replace(tzinfo=UTC) == datetime.fromtimestamp(
            1_722_000_000,
            tz=UTC,
        )
        assert db.session.get(FestivalUser, 42) is user


def test_record_bot_started_updates_existing_user(app):
    with app.app_context():
        record_bot_started(
            max_user_id=42,
            chat_id=123,
            timestamp=1_722_000_000_000,
            first_name="Иван",
            username="ivan",
        )
        user = record_bot_started(
            max_user_id=42,
            chat_id=456,
            timestamp=1_723_000_000_000,
            first_name="Иван",
            last_name="Иванов",
            username="ivan",
        )

        assert db.session.query(FestivalUser).count() == 1
        assert user.chat_id == 456
        assert user.last_name == "Иванов"
        assert user.first_started_at.replace(tzinfo=UTC) == datetime.fromtimestamp(
            1_722_000_000,
            tz=UTC,
        )
        assert user.last_started_at.replace(tzinfo=UTC) == datetime.fromtimestamp(
            1_723_000_000,
            tz=UTC,
        )
