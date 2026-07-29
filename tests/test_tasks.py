from unittest.mock import Mock

import httpx

from app.tasks import answer_message


def make_max_client() -> Mock:
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    return client


def test_answer_message_shows_typing_before_openai(monkeypatch):
    events: list[str] = []
    client = make_max_client()
    client.send_action.side_effect = lambda **kwargs: events.append("typing")
    client.send_message.side_effect = lambda **kwargs: events.append("message")

    monkeypatch.setattr("app.tasks.MaxClient", Mock(return_value=client))
    monkeypatch.setattr(
        "app.tasks.generate_festival_answer",
        lambda text: events.append("openai") or "Ответ",
    )

    answer_message.run(text="Вопрос", chat_id=123, user_id=42)

    assert events == ["typing", "openai", "message"]
    client.send_action.assert_called_once_with(
        chat_id=123,
        action="typing_on",
    )
    client.send_message.assert_called_once_with(
        text="Ответ",
        chat_id=123,
        user_id=42,
    )


def test_typing_failure_does_not_prevent_answer(monkeypatch):
    client = make_max_client()
    client.send_action.side_effect = httpx.ConnectError("MAX unavailable")

    monkeypatch.setattr("app.tasks.MaxClient", Mock(return_value=client))
    monkeypatch.setattr(
        "app.tasks.generate_festival_answer",
        lambda text: "Ответ",
    )

    answer_message.run(text="Вопрос", chat_id=123, user_id=42)

    client.send_message.assert_called_once_with(
        text="Ответ",
        chat_id=123,
        user_id=42,
    )


def test_direct_message_without_chat_id_skips_typing(monkeypatch):
    client = make_max_client()

    monkeypatch.setattr("app.tasks.MaxClient", Mock(return_value=client))
    monkeypatch.setattr(
        "app.tasks.generate_festival_answer",
        lambda text: "Ответ",
    )

    answer_message.run(text="Вопрос", chat_id=None, user_id=42)

    client.send_action.assert_not_called()
